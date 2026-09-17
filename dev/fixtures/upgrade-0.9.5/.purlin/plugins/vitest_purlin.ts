/**
 * Purlin proof reporter for Vitest (TypeScript-native).
 *
 * Collects proof markers from test names and emits feature-scoped proof JSON
 * files next to the corresponding spec files.
 *
 * Tested with Vitest 2.x and 3.x. Proofs are collected in `onFinished(files)`,
 * the reporter hook whose shape is stable across Vitest 2 → 4. (Vitest 1.x's
 * `onTaskUpdate(packs)` is intentionally NOT used: in Vitest 2+ a pack became
 * `[id, result, meta]` where `result` is a TaskResult without `name`/`file`, so
 * relying on it silently produced zero proof files while tests passed.)
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

/**
 * Minimal shape of the task tree Vitest passes to `onFinished(files)`.
 * Vitest 2+ passes an array of file tasks; each task may have nested `tasks`
 * (suites and tests). Test tasks carry `name` and a `result` with `state`;
 * the file task carries `filepath`.
 */
interface VitestTask {
  type?: string;
  name?: string;
  filepath?: string;
  file?: { filepath?: string };
  result?: { state?: string };
  tasks?: VitestTask[];
}

interface Reporter {
  onInit?: () => void;
  onFinished?: (files?: VitestTask[]) => void;
}

const PROOF_MARKER_RE = /\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?\]/;

class PurlinVitestReporter implements Reporter {
  private proofs: Map<string, ProofEntry[]> = new Map();
  private rootDir: string;

  constructor() {
    this.rootDir = process.cwd();
  }

  onFinished(files?: VitestTask[]): void {
    if (files && files.length) {
      for (const file of files) {
        this.collect(file, file);
      }
    }
    this.writeProofFiles();
  }

  /**
   * Recursively walk the file → suite → test task tree, collecting proof
   * markers from each test task's name. `file` is the enclosing file task,
   * carried down so `test_file` can be resolved from its `filepath`.
   */
  private collect(task: VitestTask, file: VitestTask): void {
    if (task.tasks && task.tasks.length) {
      for (const child of task.tasks) {
        this.collect(child, file);
      }
    }

    if (task.type !== "test" && task.type !== "custom") return;

    // Only record tasks that produced a terminal pass/fail result.
    // Skipped, todo, and unrun tasks have no meaningful proof status.
    const state = task.result?.state;
    if (state !== "pass" && state !== "fail") return;

    const name = task.name ?? "";
    const match = name.match(PROOF_MARKER_RE);
    if (!match) return;

    const [, feature, proofId, ruleId, tier = "unit"] = match;
    const key = `${feature}:${tier}`;

    if (!this.proofs.has(key)) {
      this.proofs.set(key, []);
    }

    const filepath = file.filepath ?? file.file?.filepath;
    const testFile = filepath
      ? path.relative(this.rootDir, filepath)
      : "unknown";

    this.proofs.get(key)!.push({
      feature,
      id: proofId,
      rule: ruleId,
      test_file: testFile,
      test_name: name,
      status: state === "pass" ? "pass" : "fail",
      tier,
    });
  }

  private writeProofFiles(): void {
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
