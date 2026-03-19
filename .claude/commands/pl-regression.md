**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-regression instead." and stop.

---

## Overview

Regression Testing skill. QA owns the regression tier end-to-end: authoring harness scripts, composing regression sets, and triaging results. Harness scripts are behavioral verification artifacts, not application code — the Builder does NOT write or modify regression harnesses.

This skill identifies regression-eligible features and composes external commands for the user to execute in a separate terminal.

**MANDATORY UX RULE:** Whenever you ask the user to run something in an external terminal — whether through this skill or ad-hoc during triage — you MUST print the exact, complete, copy-pasteable command. Never describe what to run in prose. The user should never have to assemble a command from your output. This applies to every interaction, not just Step 3.

---

## Execution Protocol

### Step 1 — Discovery

1. Run `tools/cdd/status.sh --role qa` and parse the output.
2. Identify regression-eligible features: features with `> Web Test:` metadata or a `### Regression Testing` section that meet any of these criteria:
   - `tests.json` has `status: "FAIL"` (FAIL)
   - `tests.json` is missing or has `total: 0` (NOT_RUN)
   - Feature source was modified after `tests.json` mtime (STALE)
3. For staleness detection: compare the feature file's mtime against `tests/<feature>/tests.json` mtime. If the feature file is newer, mark as `[STALE]`.
4. Sort the eligible list: STALE features first, then FAIL, then NOT_RUN.

### Step 2 — Present Options

If zero features are eligible:
- Print: "No regression-eligible features found. All regression results are current."
- Stop.

If features are found:
- Print a numbered list with status indicators:
  ```
  Found N features eligible for regression:

    1. [STALE] instruction_audit — last tested 2h ago, source modified 1h ago
    2. [FAIL]  pl_web_test — 3/5 scenarios failing
    3. [NOT_RUN] new_feature — no test results

  Run all, select specific features, or skip? [all / 1,2,... / skip]
  ```
- Wait for user selection.

### Step 3 — Compose Command

Based on user selection, compose **direct harness invocations** — do NOT use `dev/regression_runner.sh` (that is a Purlin-dev convenience, not part of the consumer contract).

**Harness mapping:**
- Features with `### Regression Testing` section → use the harness path specified in the section directly (e.g., `./tests/qa/test_agent_interactions.sh --write-results`)
- Features with `> Web Test:` → Compose a `/pl-web-test` invocation (runs inside Claude session, not external)

**Single feature:**
```
./<harness_path> --write-results
```

**Multiple features (sequential chain):**
```
./<harness1_path> --write-results && ./<harness2_path> --write-results
```

Print the command in a clearly formatted, self-contained, copy-pasteable block. The user MUST be able to copy the entire command and paste it into a separate terminal without modification. Example format:
```
Run this in a separate terminal:

    ./tests/qa/test_agent_interactions.sh --write-results

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
     - **Source:** Regression test (auto-detected)
     ```
3. Compute assertion tier distribution across all detail entries:
   - Count entries by `assertion_tier` value (1, 2, 3, or untagged if field is absent).
   - If more than 50% of entries have `assertion_tier: 1`, flag the suite with `[SHALLOW]`.
4. Print a summary:
   ```
   Regression Results:
     ✓ feature_a: 5/5 passed
     ✗ feature_b: 3/5 passed — 2 BUG discoveries created

   Tier Distribution: T1=3  T2=12  T3=6  (untagged=0)
   ```
   If `[SHALLOW]` applies, append:
   ```
   ⚠ [SHALLOW] — >50% of assertions are Tier 1 (keyword-presence only).
     Tier 1 assertions are vulnerable to false positives. Consider upgrading to Tier 2/3.
   ```
5. Run `tools/cdd/status.sh` to refresh the Critic report.

---

## Enriched Results Format

When reading `tests.json` detail entries, look for these optional fields (backward-compatible):

- `scenario_ref` — Feature file path and scenario name (e.g., `features/instruction_audit.md:Single-turn detection`)
- `expected` — Human-readable expected behavior from the Gherkin Then step
- `actual_excerpt` — First ~500 characters of actual output when the test fails
- `assertion_tier` — Integer (1, 2, or 3) indicating assertion quality tier per `features/arch_testing.md` Section 2.5:
  - **Tier 1:** Keyword presence (e.g., "table|findings") — vulnerable to incidental matches
  - **Tier 2:** Specific finding (e.g., exact file name or defect identifier)
  - **Tier 3:** State verification (inspects agent's stated intent to produce artifacts)

These fields are written by regression harnesses that support the `--write-results` convention.
