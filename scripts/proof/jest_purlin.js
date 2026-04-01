/**
 * Purlin proof reporter for Jest.
 *
 * Collects proof markers from test names and emits feature-scoped proof JSON
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
 */

const fs = require("fs");
const path = require("path");
const { globSync } = require("glob");

class PurlinProofReporter {
  constructor(globalConfig, reporterOptions) {
    this.globalConfig = globalConfig;
    this.options = reporterOptions || {};
    this.proofs = {}; // keyed by `${feature}:${tier}`
  }

  onTestResult(test, testResult) {
    const rootDir = this.globalConfig.rootDir;

    for (const result of testResult.testResults) {
      // Parse proof markers from test title: [proof:feature:PROOF-N:RULE-N:tier]
      const match = result.title.match(
        /\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?\]/
      );
      if (!match) continue;

      const [, feature, proofId, ruleId, tier = "default"] = match;
      const key = `${feature}:${tier}`;

      if (!this.proofs[key]) this.proofs[key] = [];

      this.proofs[key].push({
        feature,
        id: proofId,
        rule: ruleId,
        test_file: path.relative(rootDir, testResult.testFilePath),
        test_name: result.title,
        status: result.status === "passed" ? "pass" : "fail",
        tier,
      });
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
      const [feature, tier] = key.split(":");
      const specDir = specDirs[feature] || "specs";
      const filePath = path.join(specDir, `${feature}.proofs-${tier}.json`);

      // Load existing file
      let existing = [];
      if (fs.existsSync(filePath)) {
        try {
          existing = JSON.parse(fs.readFileSync(filePath, "utf8")).proofs || [];
        } catch {
          existing = [];
        }
      }

      // Purge this feature's old entries, keep others
      const kept = existing.filter((e) => e.feature !== feature);

      fs.writeFileSync(
        filePath,
        JSON.stringify({ tier, proofs: [...kept, ...newEntries] }, null, 2) +
          "\n"
      );
    }
  }
}

module.exports = PurlinProofReporter;
