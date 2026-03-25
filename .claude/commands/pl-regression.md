**Purlin mode: QA**

If no mode is currently active, this skill activates QA mode.
If Engineer or PM mode is active, confirm mode switch with the user before proceeding.

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

Compare regression test results against baselines. Read `tests/<feature>/regression.json` results, compare to expected outcomes, and report:
- PASS: result matches baseline
- REGRESSION: result differs from baseline (flag for investigation)
- NEW: no baseline exists (establish baseline)
