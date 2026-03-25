**Purlin command: Purlin agent only (replaces /pl-regression-run, /pl-regression-author, /pl-regression-evaluate)**
**Purlin mode: QA**

Legacy agents: Use /pl-regression-run, /pl-regression-author, or /pl-regression-evaluate instead.
Purlin agent: This skill activates QA mode. If another mode is active, confirm switch first.

---

## Usage

```
/pl-regression run [feature]      — Execute regression test suite
/pl-regression author [feature]   — Author regression test scenarios
/pl-regression evaluate [feature] — Evaluate regression results against baselines
```

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

## Subcommands

### run

Execute regression test suites. Invokes `${TOOLS_ROOT}/test_support/run_regression.sh` or `${TOOLS_ROOT}/test_support/harness_runner.py`.

If a feature argument is provided, scope to that feature. Otherwise, run all suites with `@auto` scenarios.

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
