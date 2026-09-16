/**
 * Purlin proof reporter for Vitest (TypeScript-native).
 *
 * The reporter reads proof markers from test names during a run and writes
 * what it observed to `.purlin/runtime/proofs/<feature>.<tier>.json`. Proof
 * files are runtime: they are gitignored, so two runs on two branches never
 * conflict and nothing about a run is committed. The record `purlin:audit`
 * writes is what says where a run happened, and it says it once per run.
 *
 * Two hooks, one collection. `onTestRunEnd(testModules, errors, reason)` is
 * the reporter hook Vitest 3 and later call, and it is the primary path.
 * `onFinished(files)` is kept for Vitest 1 and 2, which have no
 * `onTestRunEnd`. Whichever fires first writes the files; the second finds
 * the work done and returns.
 *
 * Marker syntax in test files:
 *   it("validates credentials [proof:auth_login:PROOF-1:RULE-1:unit]", ...)
 *   it("validates credentials [proof:auth_login:PROOF-1:RULE-1]", ...)  // unit
 *
 * The operating system a proof must be proved on is a property of the spec,
 * not of the test: write @env(windows), @env(macos) or @env(linux) on the
 * proof line. The retired `:on(...)` marker keyword is refused rather than
 * ignored, so a name carrying one fails the run with a line saying what to
 * write instead.
 *
 * The project root is the nearest ancestor of the working directory holding
 * `specs/` or `.purlin/`, and every `test_file` it writes is relative to it
 * with `/` separators on every operating system.
 *
 * A run that saw markers and wrote no entry at all fails: it exits non-zero
 * with one line naming the features whose evidence went missing.
 *
 * The reporter uses node's builtins and vitest itself and nothing else.
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

interface ProofEntry {
  feature: string;
  id: string;
  rule: string;
  test_file: string;
  test_name: string;
  status: "pass" | "fail";
  tier: string;
}

const PROOF_DIR = path.join(".purlin", "runtime", "proofs");

// ── The project root ────────────────────────────────────────────────────────
// Everything the reporter addresses by a project-relative path is rooted here
// and not at the working directory, so a run started from a subdirectory
// writes into the project's own tree instead of making a second one beside it.

function isDir(p: string): boolean {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

// The nearest ancestor of `start`, `start` itself included, that holds a
// `specs/` or a `.purlin/` directory; null when none does.
function findRoot(start: string): string | null {
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
function projectRoot(start: string): string {
  return findRoot(start) || path.resolve(start);
}

// Sort a proof file's entries by (id, test_file, test_name) under plain
// ordinal string comparison, applied after the merge and right before
// serialization, so two runs of the same tests in any collection order write
// byte-identical files.
function sortProofEntries(entries: ProofEntry[]): ProofEntry[] {
  const ordinal = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
  return entries.slice().sort(
    (x, y) =>
      ordinal(x.id ?? "", y.id ?? "") ||
      ordinal(x.test_file ?? "", y.test_file ?? "") ||
      ordinal(x.test_name ?? "", y.test_name ?? "")
  );
}

// `filePath` written relative to the project root with "/" separators on
// every OS. Whatever shape vitest handed over is resolved against the working
// directory first, so an absolute path and a relative one naming the same file
// record the same value. A file outside `root` is made relative to the nearest
// project root above the file itself, and left absolute when there is none,
// rather than rewritten with "../".
function toPosix(p: string): string {
  return p.split(path.sep).join("/").replace(/\\/g, "/");
}

function relativeTestFile(root: string, filePath: string): string {
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

/**
 * Minimal shape of the task tree Vitest 1 and 2 pass to `onFinished(files)`:
 * an array of file tasks, each with nested `tasks` (suites and tests). Test
 * tasks carry `name` and a `result` with `state`; the file task carries
 * `filepath`.
 */
interface VitestTask {
  type?: string;
  name?: string;
  filepath?: string;
  file?: { filepath?: string };
  result?: { state?: string };
  tasks?: VitestTask[];
}

/**
 * Minimal shape of the reported test modules Vitest 3 and later pass to
 * `onTestRunEnd(testModules, errors, reason)`. A module names its file and
 * yields its tests through `children.allTests()`; each test carries a
 * `result()` whose `state` is `passed`, `failed`, `skipped` or `pending`.
 */
interface VitestTestCase {
  type?: string;
  name?: string;
  fullName?: string;
  module?: { moduleId?: string };
  result?: () => { state?: string } | undefined;
}

interface VitestTestModule {
  moduleId?: string;
  children?: { allTests?: () => Iterable<VitestTestCase> };
}

interface Reporter {
  onInit?: () => void;
  onFinished?: (files?: VitestTask[]) => void;
  onTestRunEnd?: (
    testModules?: VitestTestModule[],
    errors?: unknown[],
    reason?: string
  ) => void;
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
  // instead of being reaped by a sibling test in the same file.
  private skipped: Set<string> = new Set();
  // Every feature a marker named, whether or not it produced an entry.
  private seenFeatures: Set<string> = new Set();
  // Names carrying the retired `:on(...)` keyword, named in the one line the
  // run fails with.
  private retired: string[] = [];
  // True once the files have been written, so the two hooks never write twice.
  private done = false;
  // Resolved once, from the working directory vitest was started in, and used
  // for the existence check and every `test_file` this run writes.
  private root: string;

  constructor() {
    this.root = projectRoot(process.cwd());
  }

  // The current API: Vitest 3 and later.
  onTestRunEnd(testModules?: VitestTestModule[]): void {
    if (this.done) return;
    for (const testModule of testModules || []) {
      const tests = testModule.children?.allTests?.();
      if (!tests) continue;
      for (const testCase of tests) {
        const filepath = testCase.module?.moduleId ?? testModule.moduleId ?? "";
        const state = testCase.result?.()?.state;
        this.record(testCase.name ?? "", filepath, state);
      }
    }
    this.writeProofFiles();
  }

  // Kept for Vitest 1 and 2, which have no `onTestRunEnd`.
  onFinished(files?: VitestTask[]): void {
    if (this.done) return;
    for (const file of files || []) {
      this.collect(file, file);
    }
    this.writeProofFiles();
  }

  /**
   * Recursively walk the file to suite to test task tree, collecting proof
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
    const filepath = file.filepath ?? file.file?.filepath ?? "";
    this.record(task.name ?? "", filepath, task.result?.state);
  }

  /**
   * One marked test's observation. `state` is the framework's own word for
   * what happened; only a terminal `pass`/`passed` or `fail`/`failed` records
   * an entry.
   */
  private record(name: string, filepath: string, state?: string): void {
    const match = name.match(PROOF_MARKER_RE);
    if (!match) return;

    const [, feature, proofId, ruleId, tier = "unit", onList] = match;
    const testFile = filepath ? relativeTestFile(this.root, filepath) : "unknown";
    this.seenFeatures.add(feature);

    if (onList !== undefined) {
      this.retired.push(`${feature} ${proofId}`);
      return;
    }

    const passed = state === "pass" || state === "passed";
    const failed = state === "fail" || state === "failed";
    if (!passed && !failed) {
      // Skipped, todo and unrun tasks have no meaningful proof status, so they
      // emit no entry and protect the entry they would have written from this
      // run's reap.
      this.skipped.add(skipKey(feature, proofId, testFile));
      return;
    }

    const key = `${feature}:${tier}`;
    if (!this.proofs.has(key)) this.proofs.set(key, []);
    this.proofs.get(key)!.push({
      feature,
      id: proofId,
      rule: ruleId,
      test_file: testFile,
      test_name: name,
      status: passed ? "pass" : "fail",
      tier,
    });
  }

  private writeProofFiles(): void {
    this.done = true;

    if (this.retired.length) {
      fail(
        "purlin: the :on(...) marker keyword is not read any more; write " +
          "@env(windows), @env(macos) or @env(linux) on the proof line in the " +
          `spec instead: ${[...new Set(this.retired)].sort().join(", ")}`
      );
      return;
    }
    if (this.proofs.size === 0) {
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

    for (const [key, newEntries] of this.proofs.entries()) {
      const [feature, tier] = key.split(":");
      const filePath = path.join(directory, `${feature}.${tier}.json`);

      let existing: ProofEntry[] = [];
      if (fs.existsSync(filePath)) {
        try {
          existing = JSON.parse(fs.readFileSync(filePath, "utf8")).proofs || [];
        } catch {
          existing = [];
        }
      }

      // Write-scoped overwrite keyed by (feature, tier, test_file); the file
      // carries the tier, so within it the key is (feature, test_file).
      // Entries whose test file no longer exists are reaped. Each path it
      // wrote is resolved from the project root, the same root it was
      // relativized against.
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
function fail(message: string): void {
  process.stderr.write(message + "\n");
  process.exitCode = 1;
}

export default PurlinVitestReporter;
