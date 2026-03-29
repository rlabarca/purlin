---
name: regression
description: This skill activates QA mode. If another mode is active, confirm switch first
---

**Purlin mode: QA**

---

## Usage

```
purlin:regression                    — Auto-detect and run the next step
purlin:regression [feature]          — Auto-detect next step for one feature
purlin:regression run [feature]      — Execute regression test suite
purlin:regression author [feature]   — Author regression test scenarios
purlin:regression evaluate [feature] — Evaluate regression results against baselines
```

## Auto-Detect (Bare Invocation)

When invoked without a subcommand, first print a health summary, then auto-detect and execute the next step.

**Health summary** (always print first):
```
Regression Health: 8 PASS, 2 STALE, 1 FAIL, 1 NOT_RUN (12 total)
```
Scan `tests/qa/scenarios/*.json` and check each feature's `tests/<feature>/regression.json`. Count results by status. If zero scenario files exist, print `"No regression scenarios authored yet."` instead.

**Auto-detect** — execute the first matching rule:

1. **Author needed:** Features with `### QA Scenarios`, `## Regression Guidance`, or `> Web Test:` metadata, Engineer status DONE, but no `tests/qa/scenarios/<feature>.json` → run `author`. QA does not need PM's Regression Guidance to author — QA Scenarios alone are sufficient.
2. **Run needed:** Scenario files exist with STALE, FAIL, or NOT_RUN results → run `run`.
3. **Evaluate needed:** Fresh results exist that haven't been documented (FAIL with no companion file entry, or results newer than last evaluation) → run `evaluate`.
4. **All green:** Health summary is sufficient. Stop.

After completing the detected step, print:
```
Next: purlin:regression    (auto-detects next step)
```

## Subcommands

### run

Execute regression test suites. Invokes `${CLAUDE_PLUGIN_ROOT}/scripts/test_support/harness_runner.py` directly.

If a feature argument is provided, scope to that feature. Otherwise, discover all suites with STALE, FAIL, or NOT_RUN results and run them (smoke tier first).

#### Protocol

1. **Discover suites.** Scan `tests/qa/scenarios/*.json`. For each, check `tests/<feature>/regression.json` for status. Sort: STALE first, then FAIL, then NOT_RUN. Within each group, smoke tier first.

2. **Present plan.** Show the user which suites will run, their harness types, and estimated duration. Wait for confirmation (unless `auto_start` is `true`).

3. **Execute suites.** All harness types run in-session — including `agent_behavior`. The `claude --print` invocations within `agent_behavior` suites are non-interactive subprocesses and do not conflict with the active session.
   - **Fast suites** (`web_test`, `custom_script`, or single-scenario `agent_behavior`): run synchronously for immediate feedback.
   - **Slow suites** (multi-scenario `agent_behavior`, estimated >30s): run via `run_in_background` so QA is not blocked. QA may continue other work and will be notified on completion.

4. **Auto-evaluate.** When a suite completes (foreground or background notification), immediately read the `regression.json` results and run the evaluate protocol (see below). Do not wait for the user to invoke `purlin:regression evaluate` separately.

### author

Author new regression test scenarios. For each untagged QA Scenario in the feature spec:
1. Propose automation (regression JSON structure)
2. If automatable, write the regression JSON and tag the scenario `@auto`
3. If not automatable, tag `@manual` and document why

Uses Explore subagents for parallel scenario authoring when multiple features are in scope.

### evaluate

Evaluate regression results — read the result files, report status, and document failures for the Engineer.

#### Protocol

1. **Read results.** For each in-scope feature, read:
   - `tests/<feature>/regression.json` (per-feature regressions)
   - `tests/qa/scenarios/<feature>.json` (QA-authored regressions)
   - Check both `status`, `passed`, `failed`, and per-scenario `results` array.

2. **Classify each suite:**
   - **PASS**: all scenarios passed. No action needed.
   - **FAIL**: one or more scenarios failed. Document the failure (see step 3).
   - **NEW**: no prior baseline exists. Establish baseline from current results.

3. **Document failures in companion file.** For each FAIL suite, append a `[DISCOVERY]` entry to `features/<feature>.impl.md` with:
   - The scenario name that failed
   - The assertion pattern that was expected
   - The actual output that was produced (quote the relevant portion)
   - How many times this failure has persisted (if re-evaluating after a fix attempt, note "still failing after <N> attempts")
   - Suggested fix direction (is the assertion too narrow? is the code wrong? is the test environment missing something?)

   Format:
   ```markdown
   **[DISCOVERY]** Regression FAIL: <scenario_name> (<passed>/<total>)
   **Expected:** <assertion pattern or description>
   **Actual:** "<quoted actual output>"
   **Attempts:** <N> (first seen <date> / still failing as of <date>)
   **Suggested fix:** <what the Engineer should investigate>
   ```

   This gives the Engineer everything they need to fix it without running QA mode themselves.

4. **Report summary.**
   ```
   Regression Evaluation
   ━━━━━━━━━━━━━━━━━━━━━
   PASS: N suites
   FAIL: M suites (details written to companion files)
   NEW:  K suites (baselines established)
   ━━━━━━━━━━━━━━━━━━━━━
   ```

5. **Re-evaluation after fix.** When evaluating a suite that previously failed:
   - If now PASS: update the companion file entry to `[RESOLVED]` with the date.
   - If still FAIL: update the companion file entry with incremented attempt count and the new actual output (it may have changed).

6. **Commit** regression results and any companion file updates: `git commit -m "qa(regression): evaluate <feature|batch>"`.
   For the `author` subcommand, commit new baselines: `git commit -m "qa(regression): author baselines for <feature>"`.
   For the `run` subcommand, commit updated `regression.json` results: `git commit -m "qa(regression): run <feature|all>"`.
   Run `purlin_scan` after commit.
