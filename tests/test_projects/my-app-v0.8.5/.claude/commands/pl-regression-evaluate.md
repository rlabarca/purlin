**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-regression-evaluate instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Overview

Process regression results after execution. Creates BUG discoveries for failures and reports assertion quality metrics.

---

## Step 1 -- Read Results

Read `tests/<feature>/regression.json` for features with recently updated regression results (mtime newer than last Critic run, from `${TOOLS_ROOT}/cdd/status.sh` output).

If no recently updated results are found, print: "No unprocessed regression results found." and stop.

---

## Step 2 -- Create Discoveries for Failures

For each feature with failures, read enriched fields (`scenario_ref`, `expected`, `actual_excerpt`) from test detail entries. Create a `[BUG]` entry in the feature's discovery sidecar (`features/<name>.discoveries.md`):

```
### [BUG] Regression failure: <scenario_ref> (Discovered: YYYY-MM-DD)
- **Scenario:** <scenario_ref>
- **Observed Behavior:** <actual_excerpt (first ~500 chars)>
- **Expected Behavior:** <expected>
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected)
```

---

## Step 3 -- Tier Distribution

Compute assertion tier distribution across all detail entries:
- Count entries by `assertion_tier` value (1, 2, 3, or untagged if field is absent).
- If more than 50% of entries have `assertion_tier: 1`, flag the suite with `[SHALLOW]`.

---

## Step 4 -- Summary

Print results:

```
Regression Results:
  PASS feature_a: 5/5 passed
  FAIL feature_b: 3/5 passed -- 2 BUG discoveries created

Tier Distribution: T1=3  T2=12  T3=6  (untagged=0)
```

If `[SHALLOW]` applies, append:

```
[SHALLOW] -- >50% of assertions are Tier 1 (keyword-presence only).
  Tier 1 assertions are vulnerable to false positives. Consider upgrading to Tier 2/3.
```

---

## Step 5 -- Refresh and Handoff

Run `${TOOLS_ROOT}/cdd/status.sh` to refresh the Critic report.

If failures were found, print the handoff message:

```
Regression results processed: N failures found, BUG discoveries created.

NEXT STEPS:
  1. Launch Builder to process regression failures and fix code bugs.
  2. After Builder fixes, re-run tests:
         ./tests/qa/run_all.sh
  3. When all tests pass, launch QA to process final results.
```

---

## Enriched Results Format

When reading `regression.json` detail entries, look for these optional fields (backward-compatible):

- `scenario_ref` -- Feature file path and scenario name (e.g., `features/instruction_audit.md:Single-turn detection`)
- `expected` -- Human-readable expected behavior from the Gherkin Then step
- `actual_excerpt` -- First ~500 characters of actual output when the test fails
- `assertion_tier` -- Integer (1, 2, or 3) indicating assertion quality tier per `features/arch_testing.md` Section 2.5:
  - **Tier 1:** Keyword presence (e.g., "table|findings") -- vulnerable to incidental matches
  - **Tier 2:** Specific finding (e.g., exact file name or defect identifier)
  - **Tier 3:** State verification (inspects agent's stated intent to produce artifacts)
