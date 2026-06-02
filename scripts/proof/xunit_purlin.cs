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
// feature-scoped proof JSON files next to the matching spec, implementing the
// shared proof-plugin contract (see specs/_anchors/proof_common.md):
//   - resolve the spec directory by scanning specs/**/*.md (RULE-1)
//   - write <feature>.proofs-<tier>.json into that directory (RULE-2)
//   - fall back to specs/ with a stderr warning when no spec matches (RULE-3, RULE-9)
//   - feature-scoped overwrite: keep other features, replace this one (RULE-4)
//   - emit all 7 fields (RULE-5); status is "pass"/"fail" only (RULE-6)
//   - no markers collected -> write nothing (RULE-7)
//
// The marker is a test trait rather than a parsed string because traits are the
// framework-neutral metadata channel in the .NET test platform: xUnit's [Trait],
// NUnit's [Category]/[Property], and MSTest's [TestProperty] all surface as
// TestCase.Traits. The trait value is colon-delimited: "feature:PROOF-N:RULE-N:tier"
// (tier optional, defaults to "unit").
//
//     [Fact]
//     [Trait("PurlinProof", "my_feature:PROOF-1:RULE-1:unit")]
//     public void DoesTheThing() { Assert.Equal(200, Login("alice", "secret")); }

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
        }

        private readonly List<Proof> _proofs = new List<Proof>();

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

            // RULE-4: a skipped test is not recorded at all.
            if (result.Outcome == TestOutcome.Skipped) return;

            // RULE-1: "feature:PROOF-N:RULE-N:tier" — tier defaults to "unit".
            string[] parts = marker.Split(':');
            if (parts.Length < 3) return;
            string feature = parts[0];
            string id = parts[1];
            string rule = parts[2];
            string tier = parts.Length >= 4 && parts[3].Length > 0 ? parts[3] : "unit";

            // RULE-5: test_file relative to the project root; test_name fully-qualified.
            string testFile = MakeRelative(_root, tc.CodeFilePath ?? "");
            string testName = !string.IsNullOrEmpty(tc.FullyQualifiedName)
                ? tc.FullyQualifiedName
                : tc.DisplayName ?? "";

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

            // Group by (feature, tier) — one file per group.
            int filesWritten = 0;
            foreach (var group in _proofs.GroupBy(p => (p.Feature, p.Tier)))
            {
                string feature = group.Key.Feature;
                string tier = group.Key.Tier;

                // RULE-3 / RULE-9: fall back to specs/ with a stderr warning.
                if (!specDirs.TryGetValue(feature, out string? specDir))
                {
                    Console.Error.WriteLine(
                        $"WARNING: No spec found for feature \"{feature}\" — writing proofs to " +
                        $"specs/{feature}.proofs-{tier}.json. Create a spec with: purlin:spec {feature}");
                    specDir = specsRoot;
                }

                string path = Path.Combine(specDir, $"{feature}.proofs-{tier}.json");

                // RULE-4: feature-scoped overwrite — keep other features, drop this one's old entries.
                var kept = new List<Dictionary<string, string>>();
                if (File.Exists(path))
                {
                    foreach (var entry in ReadProofs(path))
                    {
                        if (!entry.TryGetValue("feature", out string? f) || f != feature)
                            kept.Add(entry);
                    }
                }

                var ordered = new List<Dictionary<string, string>>(kept);
                foreach (Proof p in group)
                {
                    // RULE-5: all 7 fields, canonical order.
                    ordered.Add(new Dictionary<string, string>
                    {
                        ["feature"] = p.Feature,
                        ["id"] = p.Id,
                        ["rule"] = p.Rule,
                        ["test_file"] = p.TestFile,
                        ["test_name"] = p.TestName,
                        ["status"] = p.Status,
                        ["tier"] = p.Tier,
                    });
                }

                string json = Serialize(tier, ordered);

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

        private static string Serialize(string tier, List<Dictionary<string, string>> proofs)
        {
            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"tier\": ").Append(JsonStr(tier)).Append(",\n");
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
                // Normalize separators so proof files are portable.
                return Path.GetRelativePath(root, file).Replace('\\', '/');
            }
            catch (Exception)
            {
                return file;
            }
        }
    }
}
