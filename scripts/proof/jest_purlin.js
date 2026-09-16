/**
 * Purlin proof reporter for Jest.
 *
 * The reporter reads proof markers from test titles during a run and writes
 * what it observed to `.purlin/runtime/proofs/<feature>.<tier>.json`. Proof
 * files are runtime: they are gitignored, so two runs on two branches never
 * conflict and nothing about a run is committed. The record `purlin:audit`
 * writes is what says where a run happened, and it says it once per run.
 *
 * Marker syntax in test titles:
 *   [proof:feature:PROOF-N:RULE-N]               tier "unit"
 *   [proof:feature:PROOF-N:RULE-N:integration]   explicit tier
 *
 * The operating system a proof must be proved on is a property of the spec,
 * not of the test: write @env(windows), @env(macos) or @env(linux) on the
 * proof line. The retired `:on(...)` marker keyword is refused rather than
 * ignored, so a title carrying one fails the run with a line saying what to
 * write instead.
 *
 * The project root is the nearest ancestor of jest's own rootDir holding
 * `specs/` or `.purlin/`, and every `test_file` it writes is relative to it
 * with `/` separators on every operating system, so running jest from a
 * subdirectory writes into the project's own tree.
 *
 * A run that saw markers and wrote no entry at all fails: it exits non-zero
 * with one line naming the features whose evidence went missing.
 *
 * The reporter uses node's builtins and nothing else, so it runs in a project
 * with an empty `node_modules`.
 */

const fs = require("fs");
const path = require("path");

const PROOF_MARKER_RE =
  /\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?(?::on\(([^)]*)\))?\]/;

const PROOF_DIR = path.join(".purlin", "runtime", "proofs");

// Jest statuses for a test it did not execute. A skipped test writes no
// entry, and the entry it already had is kept.
const SKIPPED_STATUSES = new Set(["skipped", "pending", "todo", "disabled"]);

// The identity of a skipped marked test: (feature, id, test_file).
function skipKey(feature, proofId, testFile) {
  return `${feature}\u0000${proofId}\u0000${testFile}`;
}

// ── The project root ────────────────────────────────────────────────────────
// Everything the reporter addresses by a project-relative path is rooted here
// and not at the working directory, so a run started from a subdirectory
// writes into the project's own tree instead of making a second one beside it.

function isDir(p) {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

// The nearest ancestor of `start`, `start` itself included, that holds a
// `specs/` or a `.purlin/` directory; null when none does.
function findRoot(start) {
  let dir = path.resolve(start);
  for (;;) {
    if (isDir(path.join(dir, "specs")) || isDir(path.join(dir, ".purlin"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

// The project root of `start`: the nearest ancestor holding `specs/` or
// `.purlin/`, and `start` itself when no ancestor holds either.
function projectRoot(start) {
  return findRoot(start) || path.resolve(start);
}

// Sort a proof file's entries by (id, test_file, test_name) under plain
// ordinal string comparison, applied after the merge and right before
// serialization, so two runs of the same tests in any collection order write
// byte-identical files.
function sortProofEntries(entries) {
  const ordinal = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  return entries.slice().sort(
    (x, y) =>
      ordinal(x.id ?? "", y.id ?? "") ||
      ordinal(x.test_file ?? "", y.test_file ?? "") ||
      ordinal(x.test_name ?? "", y.test_name ?? "")
  );
}

// `filePath` written relative to the project root with "/" separators on
// every OS. Whatever shape jest handed over is resolved against the working
// directory first, so an absolute path and a relative one naming the same file
// record the same value. A file outside `root` is made relative to the nearest
// project root above the file itself, and left absolute when there is none,
// rather than rewritten with "../".
function toPosix(p) {
  return p.split(path.sep).join("/").replace(/\\/g, "/");
}

function relativeTestFile(root, filePath) {
  if (!filePath) return filePath;
  const abs = path.resolve(filePath);
  for (const base of [root, findRoot(path.dirname(abs))]) {
    if (!base) continue;
    const rel = path.relative(base, abs);
    if (rel && !path.isAbsolute(rel) && rel !== ".."
        && !rel.startsWith(".." + path.sep)) {
      return toPosix(rel);
    }
  }
  return toPosix(abs);
}

class PurlinProofReporter {
  constructor(globalConfig, reporterOptions) {
    this.globalConfig = globalConfig;
    this.options = reporterOptions || {};
    // Resolved once, and used for the existence check and every `test_file`
    // this run writes. The walk starts at jest's own `rootDir`, which is where
    // jest says this run lives and a firmer statement than the reporter
    // process's working directory; `rootDir` is not itself the project root
    // when jest was started from a subdirectory, which is what the walk is for.
    this.root = projectRoot((globalConfig && globalConfig.rootDir) || process.cwd());
    this.proofs = {}; // keyed by `${feature}:${tier}`
    // skipKey(feature, id, test_file) for every marked test this run skipped,
    // so an existing entry for it survives the write-scoped overwrite instead
    // of being reaped by a sibling test in the same file.
    this.skipped = new Set();
    // Every feature a marker named, whether or not it produced an entry.
    this.seenFeatures = new Set();
    // Titles carrying the retired `:on(...)` keyword, named in the one line
    // the run fails with.
    this.retired = [];
  }

  onTestResult(test, testResult) {
    for (const result of testResult.testResults) {
      const match = result.title.match(PROOF_MARKER_RE);
      if (!match) continue;

      const [, feature, proofId, ruleId, tier = "unit", onList] = match;
      const testFile = relativeTestFile(this.root, testResult.testFilePath);
      this.seenFeatures.add(feature);

      if (onList !== undefined) {
        this.retired.push(`${feature} ${proofId}`);
        continue;
      }

      // A test jest did not execute records nothing: it emits no entry and
      // protects the entry it would have written from this run's reap.
      if (SKIPPED_STATUSES.has(result.status)) {
        this.skipped.add(skipKey(feature, proofId, testFile));
        continue;
      }

      const key = `${feature}:${tier}`;
      if (!this.proofs[key]) this.proofs[key] = [];
      this.proofs[key].push({
        feature,
        id: proofId,
        rule: ruleId,
        test_file: testFile,
        test_name: result.title,
        status: result.status === "passed" ? "pass" : "fail",
        tier,
      });
    }
  }

  onRunComplete() {
    if (this.retired.length) {
      fail(
        "purlin: the :on(...) marker keyword is not read any more; write " +
          "@env(windows), @env(macos) or @env(linux) on the proof line in the " +
          `spec instead: ${[...new Set(this.retired)].sort().join(", ")}`
      );
      return;
    }
    if (Object.keys(this.proofs).length === 0) {
      if (this.seenFeatures.size) {
        fail(
          "purlin: markers were seen and no proof entry was written for " +
            `${[...this.seenFeatures].sort().join(", ")}; the proof files on ` +
            "disk describe an earlier run."
        );
      }
      return;
    }

    const root = this.root;
    const directory = path.join(root, PROOF_DIR);
    fs.mkdirSync(directory, { recursive: true });

    for (const [key, newEntries] of Object.entries(this.proofs)) {
      const [feature, tier] = key.split(":");
      const filePath = path.join(directory, `${feature}.${tier}.json`);

      let existing = [];
      if (fs.existsSync(filePath)) {
        try {
          existing = JSON.parse(fs.readFileSync(filePath, "utf8")).proofs || [];
        } catch {
          existing = [];
        }
      }

      // Write-scoped overwrite keyed by (feature, tier, test_file); the file
      // carries the tier, so within it the key is (feature, test_file). Entries
      // whose test file no longer exists are reaped. Each path it wrote is
      // resolved from the project root, the same root it was relativized
      // against.
      const runFiles = new Set(newEntries.map((e) => e.test_file));
      // What this run wrote, so a skipped test's protection never keeps an
      // entry the run has just replaced: only an executed test replaces its
      // entry.
      const runWrote = new Set(
        newEntries.map((e) => skipKey(e.id, e.test_file, e.test_name))
      );
      const kept = existing.filter((e) => {
        if (e.feature !== feature) return true;
        if (!e.test_file || !fs.existsSync(path.resolve(root, e.test_file))) return false;
        if (!runFiles.has(e.test_file)) return true;
        return (
          this.skipped.has(skipKey(feature, e.id, e.test_file)) &&
          !runWrote.has(skipKey(e.id, e.test_file, e.test_name))
        );
      });

      const payload = { tier, proofs: sortProofEntries([...kept, ...newEntries]) };

      // Atomic write: tmp + rename. The temp name carries this process id, so
      // two plugins writing the same file concurrently never share a temp path.
      const tmpPath = `${filePath}.${process.pid}.tmp`;
      fs.writeFileSync(tmpPath, JSON.stringify(payload, null, 2) + "\n");
      fs.renameSync(tmpPath, filePath);
    }
  }
}

// Print one line and make the run exit non-zero.
function fail(message) {
  process.stderr.write(message + "\n");
  process.exitCode = 1;
}

module.exports = PurlinProofReporter;
