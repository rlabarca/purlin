/**
 * Purlin proof reporter for Vitest (TypeScript-native).
 *
 * Collects proof markers from test names and emits feature-scoped proof JSON
 * files next to the corresponding spec files.
 *
 * Marker syntax in test files:
 *   it("validates credentials [proof:auth_login:PROOF-1:RULE-1:unit]", () => { ... });
 *   it("validates credentials [proof:auth_login:PROOF-1:RULE-1]", () => { ... }); // tier defaults to "unit"
 *
 * Configuration in vitest.config.ts:
 *   import { defineConfig } from 'vitest/config';
 *   export default defineConfig({
 *     test: {
 *       reporters: ['default', './scripts/proof/vitest_purlin.ts'],
 *     },
 *   });
 */

import * as fs from "fs";
import * as path from "path";
import { globSync } from "glob";

interface ProofEntry {
  feature: string;
  id: string;
  rule: string;
  test_file: string;
  test_name: string;
  status: "pass" | "fail";
  tier: string;
}

interface Reporter {
  onInit?: () => void;
  onFinished?: (files?: any[]) => void;
  onTaskUpdate?: (packs: any[]) => void;
}

const PROOF_MARKER_RE = /\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?\]/;

class PurlinVitestReporter implements Reporter {
  private proofs: Map<string, ProofEntry[]> = new Map();
  private rootDir: string;

  constructor() {
    this.rootDir = process.cwd();
  }

  onTaskUpdate(packs: any[]): void {
    for (const pack of packs) {
      const [id, result] = pack;
      if (!result?.state || result.state === "run") continue;

      const task = result;
      const name = task.name || "";
      const match = name.match(PROOF_MARKER_RE);
      if (!match) continue;

      const [, feature, proofId, ruleId, tier = "unit"] = match;
      const key = `${feature}:${tier}`;

      if (!this.proofs.has(key)) {
        this.proofs.set(key, []);
      }

      const testFile = task.file?.filepath
        ? path.relative(this.rootDir, task.file.filepath)
        : "unknown";

      this.proofs.get(key)!.push({
        feature,
        id: proofId,
        rule: ruleId,
        test_file: testFile,
        test_name: name,
        status: result.state === "pass" ? "pass" : "fail",
        tier,
      });
    }
  }

  onFinished(): void {
    if (this.proofs.size === 0) return;

    // Build feature -> spec directory mapping
    const specDirs: Record<string, string> = {};
    const specs = globSync("specs/**/*.md");
    for (const spec of specs) {
      const stem = path.basename(spec, ".md");
      specDirs[stem] = path.dirname(spec);
    }

    for (const [key, newEntries] of this.proofs.entries()) {
      const [feature, tier] = key.split(":");
      let specDir = specDirs[feature];
      if (!specDir) {
        process.stderr.write(
          `WARNING: No spec found for feature "${feature}" — writing proofs to specs/${feature}.proofs-${tier}.json. Create a spec with: purlin:spec ${feature}\n`
        );
        specDir = "specs";
      }
      const filePath = path.join(specDir, `${feature}.proofs-${tier}.json`);

      // Load existing file
      let existing: ProofEntry[] = [];
      if (fs.existsSync(filePath)) {
        try {
          existing =
            JSON.parse(fs.readFileSync(filePath, "utf8")).proofs || [];
        } catch {
          existing = [];
        }
      }

      // Purge this feature's old entries, keep others
      const kept = existing.filter((e) => e.feature !== feature);

      // Atomic write: tmp + rename
      const tmpPath = filePath + ".tmp";
      fs.writeFileSync(
        tmpPath,
        JSON.stringify(
          { tier, proofs: [...kept, ...newEntries] },
          null,
          2
        ) + "\n"
      );
      fs.renameSync(tmpPath, filePath);
    }
  }
}

export default PurlinVitestReporter;
