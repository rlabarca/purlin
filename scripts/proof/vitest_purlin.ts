/**
 * Purlin proof reporter for Vitest (TypeScript-native).
 *
 * Collects proof markers from test names and emits write-scoped proof JSON
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
 *   it("locks natively [proof:auth_login:PROOF-2:RULE-2:unit:on(windows-2022)]", () => { ... });
 *   it("locks natively [proof:auth_login:PROOF-2:RULE-2:on(windows, macos)]", () => { ... }); // tier omitted
 *
 * A marker that declares on(...) writes its entry to
 * <feature>.proofs-<tier>@<host>.json, where <host> is PURLIN_PLATFORM when set
 * and otherwise the detected OS family (windows, macos, linux); every entry in
 * that file carries an eighth field, "platform", equal to <host>. A marker with
 * no on(...) writes the agnostic <feature>.proofs-<tier>.json with the seven
 * standard fields, whatever PURLIN_PLATFORM says. The reporter never evaluates
 * version constraints.
 *
 * At the end of the run, the same moment the proof files are written, the
 * reporter writes or merges the project's run marker
 * .purlin/runtime/test_run.json (proof_common RULE-19), so a receipt issued in
 * a consumer project can record which run its evidence came from. Every marked
 * task the run did not execute is recorded there under skipped_proofs as
 * {feature, id, test_file, test_name, reason} (proof_common RULE-20); a task
 * with no terminal state carries no message, so reason is null.
 *
 * Configuration in vitest.config.ts:
 *   import { defineConfig } from 'vitest/config';
 *   export default defineConfig({
 *     test: {
 *       reporters: ['default', './scripts/proof/vitest_purlin.ts'],
 *     },
 *   });
 */

import { execFileSync } from "child_process";
import * as fs from "fs";
import * as os from "os";
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
  platform?: string;
}

const FAMILIES: Record<string, string> = { win32: "windows", darwin: "macos", linux: "linux" };

// PURLIN_PLATFORM when set, else the OS family. The only place the reporter
// looks at the host; nothing else in it branches on the operating system.
function hostPlatform(): string {
  const env = (process.env.PURLIN_PLATFORM || "").trim();
  if (env) return env;
  const sys = os.platform();
  return FAMILIES[sys] || sys;
}

// ── The run marker (proof_common RULE-19) ───────────────────────────────────
// Written or merged at the same moment the proof files are written, so a
// consumer receipt can record which run its evidence came from.

const RUN_MARKER_REL = path.join(".purlin", "runtime", "test_run.json");

// HEAD in `root`, or null when `root` is not inside a git work tree.
function runMarkerCommit(root: string): string | null {
  try {
    const out = execFileSync("git", ["rev-parse", "HEAD"], {
      cwd: root,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    return out.trim() || null;
  } catch {
    return null;
  }
}

interface SkippedProof {
  feature: string;
  id: string;
  test_file: string;
  test_name: string;
  reason: string | null;
}

// Union of two skipped_proofs lists keyed by (feature, id, test_file,
// test_name) (proof_common RULE-20). An entry already in the marker wins, so a
// plugin that ran earlier at this commit keeps the reason it observed.
function mergeSkippedProofs(existing: any, fresh: SkippedProof[]): any[] {
  const out = (Array.isArray(existing) ? existing : []).filter(
    (e: any) => e && typeof e === "object" && !Array.isArray(e)
  );
  const key = (e: any) => JSON.stringify([e.feature ?? null, e.id ?? null,
                                          e.test_file ?? null, e.test_name ?? null]);
  const seen = new Set(out.map(key));
  for (const entry of fresh || []) {
    if (seen.has(key(entry))) continue;
    seen.add(key(entry));
    out.push(entry);
  }
  return out;
}

// A synchronous pause, so a read that landed mid-replace can be retried.
function runMarkerPause(ms: number): void {
  try {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
  } catch {
    // Atomics.wait is unavailable here: retry immediately instead.
  }
}

/**
 * Write or merge `<root>/.purlin/runtime/test_run.json` (RULE-19).
 *
 * Nothing is written when `<root>/.purlin` is absent: that is not a Purlin
 * project. An existing marker whose `commit` equals this run's commit is
 * merged into: `test_files` unioned, the three counts summed, this run
 * appended to `runs`, `ok` and-ed, and every other top-level field carried
 * through untouched. A marker naming another commit is replaced. The file is
 * written to a temp file in the same directory and renamed over the target, so
 * a concurrent reader sees one whole marker or the other; a read that lands on
 * unparsable JSON is retried before this run starts a fresh marker.
 * `skippedProofs` is unioned by (feature, id, test_file, test_name) and written
 * only when the union is non-empty, so a run that skipped nothing adds no key
 * (RULE-20).
 */
function writeRunMarker(root: string, sweep: string, testFiles: string[],
                        passed: number, failed: number, skipped: number,
                        skippedProofs: SkippedProof[] = []): void {
  if (!fs.existsSync(path.join(root, ".purlin"))) return;
  const markerPath = path.join(root, RUN_MARKER_REL);
  fs.mkdirSync(path.dirname(markerPath), { recursive: true });
  const commit = runMarkerCommit(root);
  const at = new Date().toISOString();
  const files = [
    ...new Set(
      testFiles
        .filter(Boolean)
        .map((f: string) => String(f).split(path.sep).join("/").replace(/\\/g, "/"))
    ),
  ].sort();

  let marker: any = {};
  for (let attempt = 0; attempt < 3; attempt++) {
    if (!fs.existsSync(markerPath)) break;
    try {
      const existing: any = JSON.parse(fs.readFileSync(markerPath, "utf8"));
      if (existing && typeof existing === "object" && !Array.isArray(existing)
          && (existing.commit === undefined ? null : existing.commit) === commit) {
        marker = existing;
      }
      break;
    } catch {
      runMarkerPause(50); // a concurrent writer is mid-replace
    }
  }

  const runs = Array.isArray(marker.runs) ? marker.runs.slice() : [];
  runs.push({ plugin: sweep, at, test_files: files, passed, failed, skipped });
  Object.assign(marker, {
    at,
    commit,
    sweep,
    test_files: [...new Set([...(marker.test_files || []), ...files])].sort(),
    passed: (marker.passed || 0) + passed,
    failed: (marker.failed || 0) + failed,
    skipped: (marker.skipped || 0) + skipped,
    ok: (marker.ok === undefined ? true : Boolean(marker.ok)) && failed === 0,
    runs,
  });
  const mergedSkips = mergeSkippedProofs(marker.skipped_proofs, skippedProofs);
  if (mergedSkips.length) marker.skipped_proofs = mergedSkips;

  const tmp = `${markerPath}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(marker, null, 2) + "\n");
  fs.renameSync(tmp, markerPath);
}

// Project-relative with "/" separators on every OS (proof_common RULE-15).
function relativeTestFile(rootDir: string, filePath: string): string {
  return path.relative(rootDir, filePath).split(path.sep).join("/").replace(/\\/g, "/");
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

const PROOF_MARKER_RE =
  /\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?(?::on\(([^)]*)\))?\]/;

// The identity of a skipped marked test: (feature, id, test_file).
function skipKey(feature: string, proofId: string, testFile: string): string {
  return `${feature}\u0000${proofId}\u0000${testFile}`;
}

class PurlinVitestReporter implements Reporter {
  private proofs: Map<string, ProofEntry[]> = new Map();
  // skipKey(feature, id, test_file) for every marked task this run did not
  // execute, so an existing entry for it survives the write-scoped overwrite
  // instead of being reaped by a sibling test in the same file (RULE-18).
  private skipped: Set<string> = new Set();
  // One {feature, id, test_file, test_name, reason} per marked task this run
  // did not execute, for the run marker's skipped_proofs (RULE-20). A task
  // with no terminal state carries no message, so reason is null.
  private skippedProofs: Map<string, SkippedProof> = new Map();
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

    const name = task.name ?? "";
    const match = name.match(PROOF_MARKER_RE);
    if (!match) return;

    const [, feature, proofId, ruleId, tier = "unit", onList] = match;

    const filepath = file.filepath ?? file.file?.filepath;
    const testFile = filepath
      ? relativeTestFile(this.rootDir, filepath)
      : "unknown";

    // Only record tasks that produced a terminal pass/fail result. Skipped,
    // todo, and unrun tasks have no meaningful proof status, so they emit no
    // entry (proof_common RULE-13) and protect the entry they would have
    // written from this run's reap (RULE-18).
    const state = task.result?.state;
    if (state !== "pass" && state !== "fail") {
      this.skipped.add(skipKey(feature, proofId, testFile));
      // RULE-20: and the run marker records that it did not run. A vitest task
      // with no terminal state carries no message, so the reason this contract
      // asks for is null rather than invented.
      this.skippedProofs.set(
        `${feature}\u0000${proofId}\u0000${testFile}\u0000${name}`,
        { feature, id: proofId, test_file: testFile, test_name: name,
          reason: null }
      );
      return;
    }

    const declared = (onList || "").split(",").map((s) => s.trim()).filter(Boolean);
    const platform = declared.length ? hostPlatform() : "";
    const key = `${feature}:${tier}:${platform}`;

    if (!this.proofs.has(key)) {
      this.proofs.set(key, []);
    }

    const entry: ProofEntry = {
      feature,
      id: proofId,
      rule: ruleId,
      test_file: testFile,
      test_name: name,
      status: state === "pass" ? "pass" : "fail",
      tier,
    };
    if (platform) entry.platform = platform;
    this.proofs.get(key)!.push(entry);
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
      const [feature, tier, platform] = key.split(":");
      const suffix = platform ? `${tier}@${platform}` : tier;
      let specDir = specDirs[feature];
      if (!specDir) {
        process.stderr.write(
          `WARNING: No spec found for feature "${feature}" — writing proofs to specs/${feature}.proofs-${suffix}.json. Create a spec with: purlin:spec ${feature}\n`
        );
        specDir = "specs";
      }
      const filePath = path.join(specDir, `${feature}.proofs-${suffix}.json`);

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

    // RULE-19: the run marker, written at the same moment as the proof
    // files. The counts are this run's marked results: one per entry it
    // recorded, plus the marked tasks with no terminal state.
    const entries: ProofEntry[] = [];
    for (const group of this.proofs.values()) entries.push(...group);
    writeRunMarker(
      this.rootDir,
      "vitest_purlin",
      entries.map((e) => e.test_file),
      entries.filter((e) => e.status === "pass").length,
      entries.filter((e) => e.status !== "pass").length,
      this.skipped.size,
      [...this.skippedProofs.values()]
    );
  }
}

export default PurlinVitestReporter;
