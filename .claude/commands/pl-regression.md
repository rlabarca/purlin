**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-regression instead." and stop.

---

## Overview

AFT Regression Testing skill. QA owns the regression tier end-to-end: authoring harness scripts, composing regression sets, and triaging results. Harness scripts are behavioral verification artifacts, not application code — the Builder does NOT write or modify regression harnesses.

This skill identifies regression-eligible features and composes external commands for the user to execute in a separate terminal.

---

## Execution Protocol

### Step 1 — Discovery

1. Run `tools/cdd/status.sh --role qa` and parse the output.
2. Identify regression-eligible features: features with AFT metadata (`> AFT Agent:` or `> AFT Web:`) that meet any of these criteria:
   - `tests.json` has `status: "FAIL"` (FAIL)
   - `tests.json` is missing or has `total: 0` (NOT_RUN)
   - Feature source was modified after `tests.json` mtime (STALE)
3. For staleness detection: compare the feature file's mtime against `tests/<feature>/tests.json` mtime. If the feature file is newer, mark as `[STALE]`.
4. Sort the eligible list: STALE features first, then FAIL, then NOT_RUN.

### Step 2 — Present Options

If zero features are eligible:
- Print: "No regression-eligible features found. All AFT results are current."
- Stop.

If features are found:
- Print a numbered list with status indicators:
  ```
  Found N features eligible for regression:

    1. [STALE] aft_agent — last tested 2h ago, source modified 1h ago
    2. [FAIL]  pl_aft_web — 3/5 scenarios failing
    3. [NOT_RUN] new_feature — no test results

  Run all, select specific features, or skip? [all / 1,2,... / skip]
  ```
- Wait for user selection.

### Step 3 — Compose Command

Based on user selection:

**Single feature:**
```
dev/aft_runner.sh --once <harness> --write-results
```

**Multiple features:**
Write a trigger file for watch mode, or compose multiple `--once` invocations:
```
# Option A: Sequential
dev/aft_runner.sh --once <harness1> --write-results && dev/aft_runner.sh --once <harness2> --write-results

# Option B: Watch mode (for long-running suites)
# Write trigger to .purlin/runtime/aft_trigger.json, then:
dev/aft_runner.sh --watch
```

**Harness mapping:**
- Features with `> AFT Agent:` → `dev/test_agent_interactions.sh --write-results`
- Features with `> AFT Web:` → Compose a `/pl-aft-web` invocation (runs inside Claude session, not external)

Print the command in a clearly formatted, self-contained, copy-pasteable block. The user MUST be able to copy the entire command and paste it into a separate terminal without modification. Example format:
```
Run this in a separate terminal:

    ./dev/aft_runner.sh --once dev/test_agent_interactions.sh --write-results

Tell me when it finishes.
```

### Step 4 — Process Results

After the user confirms completion:

1. Read `tests/<feature>/tests.json` for each regression-tested feature.
2. For each feature with failures:
   - Read enriched fields (`scenario_ref`, `expected`, `actual_excerpt`) from test detail entries.
   - Create a `[BUG]` entry in the feature's discovery sidecar (`features/<name>.discoveries.md`):
     ```
     ### [BUG] Regression failure: <scenario_ref>
     - **Status:** OPEN
     - **Scenario:** <scenario_ref>
     - **Expected:** <expected>
     - **Actual:** <actual_excerpt (first ~500 chars)>
     - **Source:** AFT regression (auto-detected)
     ```
3. Print a summary:
   ```
   Regression Results:
     ✓ feature_a: 5/5 passed
     ✗ feature_b: 3/5 passed — 2 BUG discoveries created
   ```
4. Run `tools/cdd/status.sh` to refresh the Critic report.

---

## Enriched Results Format

When reading `tests.json` detail entries, look for these optional fields (backward-compatible):

- `scenario_ref` — Feature file path and scenario name (e.g., `features/aft_agent.md:Single-turn agent test`)
- `expected` — Human-readable expected behavior from the Gherkin Then step
- `actual_excerpt` — First ~500 characters of actual output when the test fails

These fields are written by AFT harnesses that support the `--write-results` convention.
