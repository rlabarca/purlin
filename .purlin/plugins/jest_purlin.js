/**
 * Purlin proof reporter for Jest.
 *
 * Collects proof markers from test names and emits write-scoped proof JSON
 * files next to the corresponding spec files.
 *
 * Usage in tests:
 *   // Helper to create proof descriptor
 *   const proof = (proofId, ruleId, opts) => ({ proofId, ruleId, ...opts });
 *
 *   it("fetches weather data", proof("PROOF-1", "RULE-1"), async () => { ... });
 *
 * Or use the docblock convention:
 *   // @proof current_weather PROOF-1 RULE-1
 *   it("fetches weather data", async () => { ... });
 *
 * Marker syntax in test titles:
 *   [proof:feature:PROOF-N:RULE-N]                      tier "unit"
 *   [proof:feature:PROOF-N:RULE-N:integration]          explicit tier
 *   [proof:feature:PROOF-N:RULE-N:unit:on(windows-2022)] platforms declared
 *   [proof:feature:PROOF-N:RULE-N:on(windows, macos)]   tier omitted, platforms declared
 *
 * A marker that declares on(...) writes its entry to
 * <feature>.proofs-<tier>@<host>.json, where <host> is PURLIN_PLATFORM when set
 * and otherwise the detected OS family (windows, macos, linux); every entry in
 * that file carries an eighth field, "platform", equal to <host>. A marker with
 * no on(...) writes the agnostic <feature>.proofs-<tier>.json with the seven
 * standard fields, whatever PURLIN_PLATFORM says. The reporter never evaluates
 * version constraints.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { globSync } = require("glob");

const PROOF_MARKER_RE =
  /\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?(?::on\(([^)]*)\))?\]/;

const FAMILIES = { win32: "windows", darwin: "macos", linux: "linux" };

// Jest statuses for a test it did not execute. proof_common RULE-13 forbids
// writing "fail" for one, and RULE-18 keeps its committed entry.
const SKIPPED_STATUSES = new Set(["skipped", "pending", "todo", "disabled"]);

// The identity of a skipped marked test: (feature, id, test_file).
function skipKey(feature, proofId, testFile) {
  return `${feature}\u0000${proofId}\u0000${testFile}`;
}

// PURLIN_PLATFORM when set, else the OS family. The only place the reporter
// looks at the host; nothing else in it branches on the operating system.
function hostPlatform() {
  const env = (process.env.PURLIN_PLATFORM || "").trim();
  if (env) return env;
  const sys = os.platform();
  return FAMILIES[sys] || sys;
}

// Project-relative with "/" separators on every OS (proof_common RULE-15).
function relativeTestFile(rootDir, filePath) {
  return path.relative(rootDir, filePath).split(path.sep).join("/").replace(/\\/g, "/");
}

class PurlinProofReporter {
  constructor(globalConfig, reporterOptions) {
    this.globalConfig = globalConfig;
    this.options = reporterOptions || {};
    this.proofs = {}; // keyed by `${feature}:${tier}:${platform}` (platform "" when agnostic)
    // skipKey(feature, id, test_file) for every marked test this run skipped, so
    // an existing entry for it survives the write-scoped overwrite instead of
    // being reaped by a sibling test in the same file (proof_common RULE-18).
    this.skipped = new Set();
  }

  onTestResult(test, testResult) {
    const rootDir = this.globalConfig.rootDir;

    for (const result of testResult.testResults) {
      // Parse proof markers from test title:
      // [proof:feature:PROOF-N:RULE-N[:tier][:on(a, b)]]
      const match = result.title.match(PROOF_MARKER_RE);
      if (!match) continue;

      const [, feature, proofId, ruleId, tier = "unit", onList] = match;
      const testFile = relativeTestFile(rootDir, testResult.testFilePath);

      // A test jest did not execute records nothing: it emits no entry
      // (proof_common RULE-13) and protects the entry it would have written
      // from this run's reap (RULE-18).
      if (SKIPPED_STATUSES.has(result.status)) {
        this.skipped.add(skipKey(feature, proofId, testFile));
        continue;
      }

      const declared = (onList || "").split(",").map((s) => s.trim()).filter(Boolean);
      const platform = declared.length ? hostPlatform() : "";
      const key = `${feature}:${tier}:${platform}`;

      if (!this.proofs[key]) this.proofs[key] = [];

      const entry = {
        feature,
        id: proofId,
        rule: ruleId,
        test_file: testFile,
        test_name: result.title,
        status: result.status === "passed" ? "pass" : "fail",
        tier,
      };
      if (platform) entry.platform = platform;
      this.proofs[key].push(entry);
    }
  }

  onRunComplete() {
    if (Object.keys(this.proofs).length === 0) return;

    // Build feature -> spec directory mapping
    const specDirs = {};
    const specs = globSync("specs/**/*.md");
    for (const spec of specs) {
      const stem = path.basename(spec, ".md");
      specDirs[stem] = path.dirname(spec);
    }

    for (const [key, newEntries] of Object.entries(this.proofs)) {
      const [feature, tier, platform] = key.split(":");
      const suffix = platform ? `${tier}@${platform}` : tier;
      let specDir = specDirs[feature];
      if (!specDir) {
        process.stderr.write(`WARNING: No spec found for feature "${feature}" — writing proofs to specs/${feature}.proofs-${suffix}.json. Create a spec with: purlin:spec ${feature}\n`);
        specDir = "specs";
      }
      const filePath = path.join(specDir, `${feature}.proofs-${suffix}.json`);

      // Load existing file
      let existing = [];
      if (fs.existsSync(filePath)) {
        try {
          existing = JSON.parse(fs.readFileSync(filePath, "utf8")).proofs || [];
        } catch {
          existing = [];
        }
      }

      // Write-scoped overwrite keyed by (feature, tier, platform, test_file), per
      // proof_common RULE-4 (the file carries tier and platform, so within it the
      // key is (feature, test_file)), plus orphan reaping of vanished test files (RULE-11).
      const runFiles = new Set(newEntries.map((e) => e.test_file));
      // What this run wrote, so a skipped test's protection never keeps an entry
      // the run has just replaced (RULE-18: only an executed test replaces its
      // entry).
      const runWrote = new Set(
        newEntries.map((e) => skipKey(e.id, e.test_file, e.test_name))
      );
      const kept = existing.filter((e) => {
        if (e.feature !== feature) return true;
        if (!e.test_file || !fs.existsSync(e.test_file)) return false;
        if (!runFiles.has(e.test_file)) return true;
        // The file ran. RULE-18: an entry whose test the run skipped is kept
        // with its old status, unless this run wrote it afresh.
        return (
          this.skipped.has(skipKey(feature, e.id, e.test_file)) &&
          !runWrote.has(skipKey(e.id, e.test_file, e.test_name))
        );
      });

      const payload = platform
        ? { tier, platform, proofs: [...kept, ...newEntries] }
        : { tier, proofs: [...kept, ...newEntries] };

      // Atomic write: tmp + rename
      const tmpPath = filePath + ".tmp";
      fs.writeFileSync(tmpPath, JSON.stringify(payload, null, 2) + "\n");
      fs.renameSync(tmpPath, filePath);
    }
  }
}

module.exports = PurlinProofReporter;
