// Purlin proof logger for .NET xUnit test projects.
//
// A custom `dotnet test` logger. Register it with:
//
//     dotnet test --logger purlin
//
// The assembly MUST be named `*.TestLogger.dll` (e.g. Purlin.TestLogger.dll):
// vstest only scans assemblies matching that suffix for loggers.
// Reference this logger project from the test project so the DLL lands in the
// test output directory, where vstest discovers it by FriendlyName ("purlin").
//
// The logger collects the `PurlinProof` test trait during the run and writes
// what it observed to `.purlin/runtime/proofs/<feature>.<tier>.json`. Proof
// files are runtime: they are gitignored, so two runs on two branches never
// conflict and nothing about a run is committed. The record `purlin:audit`
// writes is what says where a run happened, and it says it once per run.
//
// The marker is a test trait rather than a parsed string because TestCase.Traits
// is the metadata channel vstest hands every logger. The logger
// reads exactly one trait name, "PurlinProof", compared ordinally: a trait named
// "Category", "Property", "TestProperty", or "PurlinProof" spelled in any other
// casing is not a marker and is ignored. Only xUnit is supported; NUnit and
// MSTest support is not claimed. The trait value is colon-delimited:
// "feature:PROOF-N:RULE-N[:tier]" (tier optional, defaults to "unit").
//
//     [Fact]
//     [Trait("PurlinProof", "my_feature:PROOF-1:RULE-1:unit")]
//     public void DoesTheThing() { Assert.Equal(200, Login("alice", "secret")); }
//
// The operating system a proof must be proved on is a property of the spec, not
// of the test: write @env(windows), @env(macos) or @env(linux) on the proof line.
// The retired `:on(...)` trait keyword is refused rather than ignored, so a
// trait carrying one fails the run with a line saying what to write instead.
//
// The project root is the nearest ancestor of the working directory holding
// `specs/` or `.purlin/`, and every `test_file` it writes is relative to it with
// `/` separators on every operating system. The test host's working directory is
// the test output folder, well below the root, so nothing here is resolved from
// it.
//
// A run that saw traits and wrote no entry at all fails: it prints one line
// naming the features whose evidence went missing and sets a non-zero exit code.

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

        // SkipKey(feature, id, test_file) for every marked test this run skipped,
        // so an existing entry for it survives the write-scoped overwrite instead
        // of being reaped by a sibling test in the same file.
        private readonly HashSet<string> _skipped = new HashSet<string>(StringComparer.Ordinal);

        // Every feature a trait named, whether or not it produced an entry. A run
        // that saw traits and wrote nothing is a failure, not silence.
        private readonly SortedSet<string> _seenFeatures = new SortedSet<string>(StringComparer.Ordinal);

        // Traits carrying the retired `:on(...)` keyword, named in the one line
        // the run fails with.
        private readonly SortedSet<string> _retired = new SortedSet<string>(StringComparer.Ordinal);

        // The identity of a skipped marked test: (feature, id, test_file).
        private static string SkipKey(string feature, string id, string testFile)
        {
            return feature + "\u0000" + id + "\u0000" + testFile;
        }

        // The project root: the nearest ancestor of the working directory, that
        // directory included, holding a `specs/` or a `.purlin/` directory. vstest
        // runs the logger with the test output folder as the CWD, well below the
        // repo root, so every project-relative path the logger reads or writes is
        // resolved from here instead.
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

            // Only tests carrying the PurlinProof trait are collected.
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

            // "feature:PROOF-N:RULE-N[:tier]": tier defaults to "unit".
            string[] parts = marker.Split(':');
            if (parts.Length < 3) return;
            string feature = parts[0];
            string id = parts[1];
            string rule = parts[2];
            string tier = "unit";
            bool retired = false;
            for (int i = 3; i < parts.Length; i++)
            {
                string part = parts[i].Trim();
                if (part.StartsWith("on(", StringComparison.Ordinal))
                {
                    retired = true;
                }
                else if (part.Length > 0 && i == 3)
                {
                    tier = part;
                }
            }

            _seenFeatures.Add(feature);
            if (retired)
            {
                _retired.Add(feature + " " + id);
                return;
            }

            // test_file relative to the project root; test_name fully-qualified.
            string testFile = MakeRelative(_root, tc.CodeFilePath ?? "");
            string testName = !string.IsNullOrEmpty(tc.FullyQualifiedName)
                ? tc.FullyQualifiedName
                : tc.DisplayName ?? "";

            // A skipped test writes no entry, and the entry it would have
            // written is protected from this run's reap.
            if (result.Outcome == TestOutcome.Skipped)
            {
                _skipped.Add(SkipKey(feature, id, testFile));
                return;
            }

            // Passed -> "pass"; every other non-skipped outcome -> "fail".
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
            if (_retired.Count > 0)
            {
                Fail("purlin: the :on(...) trait keyword is not read any more; write "
                     + "@env(windows), @env(macos) or @env(linux) on the proof line in "
                     + "the spec instead: " + string.Join(", ", _retired));
                return;
            }
            if (_proofs.Count == 0)
            {
                if (_seenFeatures.Count > 0)
                {
                    Fail("purlin: traits were seen and no proof entry was written for "
                         + string.Join(", ", _seenFeatures)
                         + "; the proof files on disk describe an earlier run.");
                }
                return;
            }

            string directory = Path.Combine(_root, ".purlin", "runtime", "proofs");
            Directory.CreateDirectory(directory);

            // Group by (feature, tier): one file per group.
            int filesWritten = 0;
            foreach (var group in _proofs.GroupBy(p => (p.Feature, p.Tier)))
            {
                string feature = group.Key.Feature;
                string tier = group.Key.Tier;
                string path = Path.Combine(directory, $"{feature}.{tier}.json");

                // Write-scoped overwrite keyed by (feature, tier, test_file): the
                // file carries the tier, so within it the key is (feature,
                // test_file). Keep other features, keep this feature's entries from
                // test files this run did not execute, and reap entries whose test
                // file is gone.
                var runFiles = new HashSet<string>(group.Select(p => p.TestFile));
                // What this run wrote, so a skipped test's protection never keeps an
                // entry the run has just replaced: only an executed test replaces
                // its entry.
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
                        // The existence check resolves each path from the project
                        // root, the same root it was relativized against: the test
                        // host's working directory is the test output folder, so a
                        // cwd-relative check reaps every entry.
                        if (string.IsNullOrEmpty(tf)
                            || !File.Exists(Path.Combine(_root, tf))) continue;
                        // An entry whose test this run skipped is kept with its old
                        // status, even though a sibling test in the same file ran,
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

                // Sorted by (id, test_file, test_name), ordinal, after the merge, so
                // the collection order never reaches the file.
                ordered = SortProofEntries(ordered);

                string json = Serialize(tier, ordered);

                // Atomic write: tmp + rename. The temp name carries this process id,
                // so two plugins writing the same file concurrently never share a
                // temp path, and the overwrite is one atomic move rather than a
                // delete followed by a move.
                string tmp = path + "." + Environment.ProcessId + ".tmp";
                File.WriteAllText(tmp, json);
                File.Move(tmp, path, true);
                filesWritten++;
            }

            // Emitted during the run (TestRunComplete fires inside the vstest
            // process): this line is the in-process collection signal that
            // distinguishes the logger from a post-run .trx parse.
            Console.Error.WriteLine(
                $"[PurlinProofLogger] collected {_proofs.Count} proof(s) in-process; wrote {filesWritten} file(s).");
        }

        // Print one line and make the run exit non-zero.
        private static void Fail(string message)
        {
            Console.Error.WriteLine(message);
            Environment.ExitCode = 1;
        }

        // Walk up from `start`, `start` itself included, to the nearest ancestor
        // holding a `specs/` or a `.purlin/` directory; null when none does. A
        // project whose specs live elsewhere still has `.purlin/`, and a fresh
        // project has `specs/` before it has anything else, so either is enough to
        // recognise the root.
        private static string? FindRootOrNull(string start)
        {
            var dir = new DirectoryInfo(start);
            while (dir != null)
            {
                if (Directory.Exists(Path.Combine(dir.FullName, "specs"))
                    || Directory.Exists(Path.Combine(dir.FullName, ".purlin")))
                    return dir.FullName;
                dir = dir.Parent;
            }
            return null;
        }

        // The project root of `start`, falling back to `start` itself.
        private static string FindRoot(string start)
        {
            return FindRootOrNull(start) ?? start;
        }

        // The roots a written path is measured from, in order: the project being
        // written to, then the project the source file itself lives in.
        private static IEnumerable<string> RootCandidates(string root, string abs)
        {
            yield return root;
            string? own = FindRootOrNull(Path.GetDirectoryName(abs) ?? root);
            if (own != null && !string.Equals(own, root, StringComparison.Ordinal))
                yield return own;
        }

        // A relative path that climbs out of the base it was measured from.
        private static bool ClimbsOut(string rel)
        {
            return rel.Length == 0 || Path.IsPathRooted(rel) || rel == ".."
                || rel.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal);
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
                // Corrupt or unreadable file is treated as empty: the run still
                // records fresh proofs.
            }
            return result;
        }

        // Sort a proof file's entries by (id, test_file, test_name) under plain
        // ordinal string comparison, applied after the merge and right before
        // serialization, so two runs of the same tests in any collection order
        // write byte-identical files.
        private static List<Dictionary<string, string>> SortProofEntries(
            List<Dictionary<string, string>> proofs)
        {
            return proofs
                .OrderBy(e => Field(e, "id"), StringComparer.Ordinal)
                .ThenBy(e => Field(e, "test_file"), StringComparer.Ordinal)
                .ThenBy(e => Field(e, "test_name"), StringComparer.Ordinal)
                .ToList();
        }

        private static string Field(Dictionary<string, string> entry, string name)
        {
            return entry.TryGetValue(name, out string? v) && v != null ? v : "";
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

        // `file` written relative to the project root. The path vstest
        // hands over is absolute; a relative one is resolved against `root` first,
        // so both spellings write the same value. A file outside `root` is
        // measured from the nearest project root above the file itself, and left
        // absolute when there is none, rather than rewritten with "../" segments:
        // under the merge key a path that differs by invocation form does not
        // collapse, it accumulates a second entry.
        private static string MakeRelative(string root, string file)
        {
            if (string.IsNullOrEmpty(file)) return file;
            try
            {
                string abs = Path.GetFullPath(file, root);
                string chosen = abs;
                foreach (string candidate in RootCandidates(root, abs))
                {
                    string rel = Path.GetRelativePath(candidate, abs);
                    if (!ClimbsOut(rel)) { chosen = rel; break; }
                }
                // Forward slashes on every OS so proof files are portable.
                return chosen.Replace('\\', '/');
            }
            catch (Exception)
            {
                return file.Replace('\\', '/');
            }
        }
    }
}
