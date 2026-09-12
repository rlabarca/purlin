// Purlin proof logger for .NET test projects (xUnit / NUnit / MSTest).
//
// A custom `dotnet test` logger. Register it with:
//
//     dotnet test --logger purlin
//
// The assembly MUST be named `*.TestLogger.dll` (e.g. Purlin.TestLogger.dll) —
// the .NET test platform only scans assemblies matching that suffix for loggers.
// Reference this logger project from the test project so the DLL lands in the
// test output directory, where vstest discovers it by FriendlyName ("purlin").
//
// It collects the `PurlinProof` test trait during the run and writes
// write-scoped proof JSON files next to the matching spec, implementing the
// shared proof-plugin contract (see specs/_anchors/proof_common.md):
//   - resolve the spec directory by scanning specs/**/*.md (RULE-1)
//   - write <feature>.proofs-<tier>.json into that directory (RULE-2)
//   - fall back to specs/ with a stderr warning when no spec matches (RULE-3, RULE-9)
//   - write-scoped overwrite keyed by (feature, tier, test_file): keep other features
//     and this feature's other test files, replace only what this run ran (RULE-4),
//     reaping entries whose test file no longer exists (RULE-11)
//   - a skipped test writes no entry (RULE-13) and keeps the entry it already had,
//     even when a sibling test in the same file did execute (RULE-18)
//   - emit all 7 fields (RULE-5); status is "pass"/"fail" only (RULE-6)
//   - no markers collected -> write nothing (RULE-7)
//
// The marker is a test trait rather than a parsed string because traits are the
// framework-neutral metadata channel in the .NET test platform: xUnit's [Trait],
// NUnit's [Category]/[Property], and MSTest's [TestProperty] all surface as
// TestCase.Traits. The trait value is colon-delimited:
// "feature:PROOF-N:RULE-N[:tier][:on(a, b)]" (tier optional, defaults to "unit";
// on(...) may follow the tier or stand in its place).
//
//     [Fact]
//     [Trait("PurlinProof", "my_feature:PROOF-1:RULE-1:unit")]
//     public void DoesTheThing() { Assert.Equal(200, Login("alice", "secret")); }
//
//     [Fact]
//     [Trait("PurlinProof", "my_feature:PROOF-2:RULE-2:unit:on(windows-2022)")]
//     public void LocksNatively() { ... }
//
// A marker that declares on(...) writes its entry to
// <feature>.proofs-<tier>@<host>.json, where <host> is PURLIN_PLATFORM when set
// and otherwise the detected OS family (windows, macos, linux); every entry in
// that file carries an eighth field, "platform", equal to <host>. A marker with
// no on(...) writes the agnostic <feature>.proofs-<tier>.json with the seven
// standard fields, whatever PURLIN_PLATFORM says. The logger never evaluates
// version constraints.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Client;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Logging;

namespace Purlin
{
    [FriendlyName("purlin")]
    [ExtensionUri("logger://purlin/proof/v1")]
    public class PurlinProofLogger : ITestLoggerWithParameters
    {
        private const string TraitName = "PurlinProof";

        private sealed class Proof
        {
            public string Feature = "";
            public string Id = "";
            public string Rule = "";
            public string TestFile = "";
            public string TestName = "";
            public string Status = "";
            public string Tier = "";
            public string Platform = "";   // "" when the marker declares no platforms
        }

        private readonly List<Proof> _proofs = new List<Proof>();

        // SkipKey(feature, id, test_file) for every marked test this run skipped,
        // so an existing entry for it survives the write-scoped overwrite instead
        // of being reaped by a sibling test in the same file (RULE-18).
        private readonly HashSet<string> _skipped = new HashSet<string>(StringComparer.Ordinal);

        // The identity of a skipped marked test: (feature, id, test_file).
        private static string SkipKey(string feature, string id, string testFile)
        {
            return feature + "\u0000" + id + "\u0000" + testFile;
        }

        // The project root: the nearest ancestor of the working directory that
        // contains a `specs/` directory. vstest runs the logger with the test
        // project directory as the CWD, which is usually nested under the repo
        // root (e.g. tests/MyProject.Tests), so we walk up to locate specs/.
        private string _root = Directory.GetCurrentDirectory();

        // ITestLogger
        public void Initialize(TestLoggerEvents events, string testRunDirectory)
        {
            _root = FindRoot(Directory.GetCurrentDirectory());
            Subscribe(events);
        }

        // ITestLoggerWithParameters
        public void Initialize(TestLoggerEvents events, Dictionary<string, string?> parameters)
        {
            _root = FindRoot(Directory.GetCurrentDirectory());
            Subscribe(events);
        }

        private void Subscribe(TestLoggerEvents events)
        {
            events.TestResult += OnTestResult;
            events.TestRunComplete += OnTestRunComplete;
        }

        private void OnTestResult(object? sender, TestResultEventArgs e)
        {
            TestResult result = e.Result;
            TestCase tc = result.TestCase;

            // RULE-1 / RULE-3: only tests carrying the PurlinProof trait are collected.
            string? marker = null;
            foreach (Trait t in tc.Traits)
            {
                if (string.Equals(t.Name, TraitName, StringComparison.Ordinal))
                {
                    marker = t.Value;
                    break;
                }
            }
            if (marker == null) return;

            // RULE-1: "feature:PROOF-N:RULE-N[:tier][:on(a, b)]" — tier defaults to "unit".
            string[] parts = marker.Split(':');
            if (parts.Length < 3) return;
            string feature = parts[0];
            string id = parts[1];
            string rule = parts[2];
            string tier = "unit";
            bool declared = false;
            for (int i = 3; i < parts.Length; i++)
            {
                string part = parts[i].Trim();
                if (part.StartsWith("on(", StringComparison.Ordinal) && part.EndsWith(")", StringComparison.Ordinal))
                {
                    string inner = part.Substring(3, part.Length - 4);
                    declared = inner.Split(',').Any(p => p.Trim().Length > 0);
                }
                else if (part.Length > 0 && i == 3)
                {
                    tier = part;
                }
            }
            string platform = declared ? HostPlatform() : "";

            // RULE-5: test_file relative to the project root; test_name fully-qualified.
            string testFile = MakeRelative(_root, tc.CodeFilePath ?? "");
            string testName = !string.IsNullOrEmpty(tc.FullyQualifiedName)
                ? tc.FullyQualifiedName
                : tc.DisplayName ?? "";

            // RULE-13: a skipped test is not recorded at all. RULE-18: and the
            // entry it would have written is protected from this run's reap.
            if (result.Outcome == TestOutcome.Skipped)
            {
                _skipped.Add(SkipKey(feature, id, testFile));
                return;
            }

            // RULE-4 / RULE-6: Passed -> "pass"; every other non-skipped outcome -> "fail".
            string status = result.Outcome == TestOutcome.Passed ? "pass" : "fail";

            _proofs.Add(new Proof
            {
                Feature = feature,
                Id = id,
                Rule = rule,
                TestFile = testFile,
                TestName = testName,
                Status = status,
                Tier = tier,
                Platform = platform,
            });
        }

        private void OnTestRunComplete(object? sender, TestRunCompleteEventArgs e)
        {
            // RULE-7: no markers collected -> write nothing.
            if (_proofs.Count == 0) return;

            string specsRoot = Path.Combine(_root, "specs");

            // RULE-1: feature -> spec directory, matched by spec filename stem.
            var specDirs = new Dictionary<string, string>(StringComparer.Ordinal);
            if (Directory.Exists(specsRoot))
            {
                foreach (string spec in Directory.EnumerateFiles(specsRoot, "*.md", SearchOption.AllDirectories))
                {
                    string stem = Path.GetFileNameWithoutExtension(spec);
                    specDirs[stem] = Path.GetDirectoryName(spec) ?? specsRoot;
                }
            }

            // Group by (feature, tier, platform) — one file per group.
            int filesWritten = 0;
            foreach (var group in _proofs.GroupBy(p => (p.Feature, p.Tier, p.Platform)))
            {
                string feature = group.Key.Feature;
                string tier = group.Key.Tier;
                string platform = group.Key.Platform;
                string suffix = platform.Length > 0 ? $"{tier}@{platform}" : tier;

                // RULE-3 / RULE-9: fall back to specs/ with a stderr warning.
                if (!specDirs.TryGetValue(feature, out string? specDir))
                {
                    Console.Error.WriteLine(
                        $"WARNING: No spec found for feature \"{feature}\" — writing proofs to " +
                        $"specs/{feature}.proofs-{suffix}.json. Create a spec with: purlin:spec {feature}");
                    specDir = specsRoot;
                }

                string path = Path.Combine(specDir, $"{feature}.proofs-{suffix}.json");

                // RULE-4: write-scoped overwrite keyed by (feature, tier, platform, test_file):
                // the file carries tier and platform, so within it the key is (feature,
                // test_file). Keep other features, keep this feature's entries from test
                // files this run did not execute, and reap entries whose test file is gone
                // (RULE-11).
                var runFiles = new HashSet<string>(group.Select(p => p.TestFile));
                // What this run wrote, so a skipped test's protection never keeps an
                // entry the run has just replaced (RULE-18: only an executed test
                // replaces its entry).
                var runWrote = new HashSet<string>(
                    group.Select(p => SkipKey(p.Id, p.TestFile, p.TestName)), StringComparer.Ordinal);
                var kept = new List<Dictionary<string, string>>();
                if (File.Exists(path))
                {
                    foreach (var entry in ReadProofs(path))
                    {
                        if (!entry.TryGetValue("feature", out string? f) || f != feature)
                        {
                            kept.Add(entry);
                            continue;
                        }
                        entry.TryGetValue("test_file", out string? tf);
                        entry.TryGetValue("id", out string? eid);
                        entry.TryGetValue("test_name", out string? ename);
                        if (string.IsNullOrEmpty(tf) || !File.Exists(tf)) continue;
                        // RULE-18: an entry whose test this run skipped is kept with its
                        // old status, even though a sibling test in the same file ran,
                        // unless this run wrote that entry afresh.
                        bool skipped = _skipped.Contains(SkipKey(feature, eid ?? "", tf))
                            && !runWrote.Contains(SkipKey(eid ?? "", tf, ename ?? ""));
                        if (!runFiles.Contains(tf) || skipped)
                            kept.Add(entry);
                    }
                }

                var ordered = new List<Dictionary<string, string>>(kept);
                foreach (Proof p in group)
                {
                    // RULE-5: all 7 fields, canonical order; an 8th, platform, in a scoped file.
                    var fields = new Dictionary<string, string>
                    {
                        ["feature"] = p.Feature,
                        ["id"] = p.Id,
                        ["rule"] = p.Rule,
                        ["test_file"] = p.TestFile,
                        ["test_name"] = p.TestName,
                        ["status"] = p.Status,
                        ["tier"] = p.Tier,
                    };
                    if (platform.Length > 0) fields["platform"] = platform;
                    ordered.Add(fields);
                }

                string json = Serialize(tier, platform, ordered);

                // Atomic write: tmp + rename.
                string fullDir = Path.GetDirectoryName(Path.GetFullPath(path)) ?? ".";
                Directory.CreateDirectory(fullDir);
                string tmp = path + ".tmp";
                File.WriteAllText(tmp, json);
                if (File.Exists(path)) File.Delete(path);
                File.Move(tmp, path);
                filesWritten++;
            }

            // Emitted during the run (TestRunComplete fires inside the test platform
            // process) — this line is the in-process collection signal that
            // distinguishes the logger from a post-run .trx parse.
            Console.Error.WriteLine(
                $"[PurlinProofLogger] collected {_proofs.Count} proof(s) in-process; wrote {filesWritten} file(s).");
        }

        // Walk up from `start` to the nearest ancestor containing a `specs/`
        // directory. Falls back to `start` if none is found.
        private static string FindRoot(string start)
        {
            var dir = new DirectoryInfo(start);
            while (dir != null)
            {
                if (Directory.Exists(Path.Combine(dir.FullName, "specs")))
                    return dir.FullName;
                dir = dir.Parent;
            }
            return start;
        }

        private static List<Dictionary<string, string>> ReadProofs(string path)
        {
            var result = new List<Dictionary<string, string>>();
            try
            {
                using JsonDocument doc = JsonDocument.Parse(File.ReadAllText(path));
                if (doc.RootElement.TryGetProperty("proofs", out JsonElement proofs)
                    && proofs.ValueKind == JsonValueKind.Array)
                {
                    foreach (JsonElement entry in proofs.EnumerateArray())
                    {
                        var dict = new Dictionary<string, string>();
                        foreach (JsonProperty prop in entry.EnumerateObject())
                            dict[prop.Name] = prop.Value.ToString();
                        result.Add(dict);
                    }
                }
            }
            catch (Exception)
            {
                // Corrupt/unreadable file is treated as empty — the run still records fresh proofs.
            }
            return result;
        }

        // PURLIN_PLATFORM when set, else the OS family. The only place the logger
        // looks at the host; nothing else in it branches on the operating system.
        private static string HostPlatform()
        {
            string env = (Environment.GetEnvironmentVariable("PURLIN_PLATFORM") ?? "").Trim();
            if (env.Length > 0) return env;
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) return "windows";
            if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX)) return "macos";
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux)) return "linux";
            return RuntimeInformation.OSDescription.Split(' ')[0].ToLowerInvariant();
        }

        private static string Serialize(string tier, string platform, List<Dictionary<string, string>> proofs)
        {
            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"tier\": ").Append(JsonStr(tier)).Append(",\n");
            if (platform.Length > 0)
                sb.Append("  \"platform\": ").Append(JsonStr(platform)).Append(",\n");
            sb.Append("  \"proofs\": [");
            for (int i = 0; i < proofs.Count; i++)
            {
                sb.Append(i == 0 ? "\n" : ",\n");
                sb.Append("    {\n");
                var entry = proofs[i];
                int j = 0;
                foreach (var kv in entry)
                {
                    sb.Append("      ").Append(JsonStr(kv.Key)).Append(": ").Append(JsonStr(kv.Value));
                    sb.Append(++j < entry.Count ? ",\n" : "\n");
                }
                sb.Append("    }");
            }
            sb.Append(proofs.Count > 0 ? "\n  ]\n" : "]\n");
            sb.Append("}\n");
            return sb.ToString();
        }

        private static string JsonStr(string s)
        {
            var sb = new StringBuilder();
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
            return sb.ToString();
        }

        private static string MakeRelative(string root, string file)
        {
            if (string.IsNullOrEmpty(file)) return file;
            try
            {
                // Forward slashes on every OS (proof_common RULE-15) so proof files are portable.
                return Path.GetRelativePath(root, file).Replace('\\', '/');
            }
            catch (Exception)
            {
                return file.Replace('\\', '/');
            }
        }
    }
}
