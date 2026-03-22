**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-regression instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Overview

Regression Testing skill. QA owns the regression tier end-to-end: authoring scenario declarations, composing regression sets, and triaging results. Scenario files and harness scripts are behavioral verification artifacts, not application code -- the Builder does NOT write or modify them.

This skill is a **state machine** that detects the current project state and enters the appropriate mode automatically.

**MANDATORY UX RULE:** Whenever you ask the user to run something in an external terminal -- whether through this skill or ad-hoc during triage -- you MUST print the exact, complete, copy-pasteable command. Never describe what to run in prose. The user should never have to assemble a command from your output.

---

## State Detection

Run `${TOOLS_ROOT}/cdd/status.sh --role qa` and parse the output. Then evaluate these conditions in priority order:

### Prerequisite Check: Harness Runner Framework

Before any mode, check whether the harness runner framework exists:
- Check for `${TOOLS_ROOT}/test_support/harness_runner.py`.
- If missing: print the **"harness runner missing" handoff message** (see Handoff Messages below) and STOP. No authoring or running is possible without the framework.

### Mode Selection

1. **Author mode** -- Features need scenario files:
   - Feature has `### Regression Testing` section or `## Regression Guidance` section or `> Web Test:` metadata.
   - Builder status is DONE (implementation exists to test against).
   - No corresponding `tests/qa/scenarios/<feature_name>.json` exists.
   - If any features match: enter Author mode.

2. **Run mode** -- Existing scenarios need execution:
   - `tests/qa/scenarios/<feature_name>.json` exists for the feature.
   - AND: `tests.json` has `status: "FAIL"` (FAIL), OR `tests.json` is missing/has `total: 0` (NOT_RUN), OR feature source was modified after `tests.json` mtime (STALE).
   - If any features match and no Author mode features exist: enter Run mode.

3. **Process mode** -- Unprocessed results exist:
   - `tests.json` was recently updated (mtime newer than last Critic run).
   - AND: results have not been triaged (no corresponding discovery sidecar entries for failures).
   - If matched: enter Process mode.

4. **No work** -- Print: "No regression work found. All scenarios are authored and results are current." and stop.

**Priority:** Author mode takes precedence when both authoring and running are needed. This ensures all scenarios exist before running.

---

## Author Mode

One feature at a time. Sequential processing to conserve context.

### Step A1 -- Present Authoring Plan

Print a summary of features needing scenario authoring:
```
Regression Authoring: N features need scenario files

  1. instruction_audit — has Regression Testing section
  2. cdd_startup — has Regression Guidance section
  3. pl_web_test — has Web Test metadata

Begin authoring? [yes / skip to run mode]
```

If user skips, fall through to Run mode (if eligible features exist) or stop.

### Step A2 -- Author Scenario File (per feature)

For each feature in the authoring list:

1. Read the feature spec. Focus on `### Regression Testing`, `## Regression Guidance`, `> Web Test:`, and the Gherkin scenarios.
2. **Evaluate fixture needs** (see Fixture Integration below).
3. Compose the scenario JSON file following the schema in `features/regression_testing.md` Section 2.7:
   - Set `harness_type` based on the feature's test pattern (`agent_behavior`, `web_test`, or `custom_script`).
   - Map Gherkin scenarios to scenario entries with appropriate assertions and tiers.
   - Include `fixture_tag` if fixtures are available, or `setup_commands` for simple inline state.
4. Write the file to `tests/qa/scenarios/<feature_name>.json`.
5. Commit: `git commit -m "qa(<feature_name>): author regression scenario"`.
6. Print progress: `"Authored M/N scenarios. K remaining."`.
7. Move to next feature.

### Step A3 -- Generate Consumer Wrapper (first authoring session only)

If `tests/qa/run_all.sh` does not exist, generate the thin wrapper:

```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$(git rev-parse --show-toplevel)/${TOOLS_ROOT}/test_support/run_regression.sh" --scenarios-dir "$SCRIPT_DIR/scenarios"
```

Adjust the path to match the project's `tools_root` configuration. Commit: `git commit -m "qa: generate regression runner wrapper"`.

### Step A4 -- Authoring Complete

After all features are authored, print the **"authoring complete" handoff message** (see Handoff Messages below). Then run `${TOOLS_ROOT}/cdd/status.sh`.

---

## Run Mode

Existing scenarios need execution. This is the legacy Steps 2-3 flow.

### Step R1 -- Discovery

Identify regression-eligible features with existing scenario files that need running:
- `tests.json` has `status: "FAIL"` (FAIL)
- `tests.json` is missing or has `total: 0` (NOT_RUN)
- Feature source was modified after `tests.json` mtime (STALE)

For staleness: compare feature file mtime against `tests/<feature>/tests.json` mtime.

Sort: STALE first, then FAIL, then NOT_RUN.

### Step R2 -- Present Options

If zero features are eligible:
- Print: "No regression-eligible features found. All regression results are current."
- Stop.

If features are found:
```
Found N features eligible for regression:

  1. [STALE] instruction_audit -- last tested 2h ago, source modified 1h ago
  2. [FAIL]  pl_web_test -- 3/5 scenarios failing
  3. [NOT_RUN] new_feature -- no test results

Run all, select specific features, or skip? [all / 1,2,... / skip]
```

Wait for user selection.

### Step R3 -- Compose Command

Based on user selection, compose the run command.

**Single feature (if scenario file exists):**
```
${TOOLS_ROOT}/test_support/run_regression.sh --scenarios-dir tests/qa/scenarios
```

Or for the consumer wrapper:
```
./tests/qa/run_all.sh
```

**Fallback for features with custom harness paths** (from `### Regression Testing` section):
```
./<harness_path> --write-results
```

**Multiple features (sequential chain, if no meta-runner):**
```
./<harness1_path> --write-results && ./<harness2_path> --write-results
```

Print the command in a clearly formatted, self-contained, copy-pasteable block:
```
Run this in a separate terminal:

    ./tests/qa/run_all.sh

Tell me when it finishes.
```

### Step R3.5 -- Productive Wait

After printing the command block, offer concurrent work:

```
While tests run, I can:
  - Author regression scenarios for other features
  - Review open discoveries
  - Generate a QA report (/pl-qa-report)

Say "continue" for other work, or tell me when tests finish.
```

If the user says "continue", proceed with regression authoring for other features (if any) or discovery review. When the user reports test completion, enter Process Mode for the completed results.

---

## Process Mode

After the user confirms test execution is complete.

### Step P1 -- Read Results

1. Read `tests/<feature>/tests.json` for each regression-tested feature.
2. For each feature with failures:
   - Read enriched fields (`scenario_ref`, `expected`, `actual_excerpt`) from test detail entries.
   - Create a `[BUG]` entry in the feature's discovery sidecar (`features/<name>.discoveries.md`):
     ```
     ### [BUG] Regression failure: <scenario_ref> (Discovered: YYYY-MM-DD)
     - **Scenario:** <scenario_ref>
     - **Observed Behavior:** <actual_excerpt (first ~500 chars)>
     - **Expected Behavior:** <expected>
     - **Action Required:** Builder
     - **Status:** OPEN
     - **Source:** Regression test (auto-detected)
     ```

### Step P2 -- Tier Distribution

Compute assertion tier distribution across all detail entries:
- Count entries by `assertion_tier` value (1, 2, 3, or untagged if field is absent).
- If more than 50% of entries have `assertion_tier: 1`, flag the suite with `[SHALLOW]`.

### Step P3 -- Summary

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

### Step P4 -- Refresh

Run `${TOOLS_ROOT}/cdd/status.sh` to refresh the Critic report.

Print the **"results processed" handoff message** if failures were found (see Handoff Messages below).

---

## Fixture Integration (Author Mode)

During Step A2, per feature, apply this decision logic:

1. Does the `### Regression Testing` section reference fixture tags?
   - Yes: Run `${TOOLS_ROOT}/test_support/fixture.sh list` to check if tags exist.
   - Tags exist: Use them in the scenario JSON `fixture_tag` field. Update `tests/qa/fixture_usage.json`.
   - Tags missing: Note the gap. The Critic already flags this as a Builder action item.

2. No explicit fixture tags, but scenario needs controlled state?
   - Simple state (single config, no git history): Use `setup_commands` in the scenario JSON.
   - Complex state (multiple branches, divergent history): Print a recommendation to the user:
     ```
     Feature "<name>" needs complex git state fixtures.
     Dynamic creation would be slow and fragile.

     Recommendation: Set up a persistent fixture repo.
       1. Create an empty git repo (local or remote)
       2. Set fixture_repo_url in .purlin/config.local.json
       3. Direct Builder to create fixture tags (--qa)

     Record this recommendation? [yes / skip]
     ```
   - If yes: Write to `tests/qa/fixture_recommendations.md` and commit.

3. Announce fixture usage: `"Using fixture tag main/<feature>/<slug> (local repo)"`

---

## Handoff Messages

These are **mandatory** -- print the appropriate message at each transition.

### After Authoring Complete (Step A4)

```
Regression scenarios authored: N features.

NEXT STEPS:
  1. Run regression tests:
         ./tests/qa/run_all.sh
  2. When tests finish, launch Builder to process results and fix failures.
  3. After Builder fixes, re-run tests:
         ./tests/qa/run_all.sh
  4. When all tests pass, launch QA to process final results.
```

### Harness Runner Framework Missing (Prerequisite Check)

```
Cannot author regression scenarios -- the harness runner framework
has not been built yet.

NEXT STEP:
  Launch Builder with --qa flag:
      Run ./pl-run-builder.sh -qa
      The Builder will build the harness runner framework.
  After Builder finishes, re-run QA to author scenarios.
```

### Fixtures Needed But Missing

```
N features need fixture repos before regression scenarios can be authored.
Recorded recommendations in tests/qa/fixture_recommendations.md.

NEXT STEP:
  Launch Builder with --qa flag:
      Run ./pl-run-builder.sh -qa
      Tell it: "Create fixture tags for features listed in
      tests/qa/fixture_recommendations.md"
  After Builder finishes, re-run QA to continue authoring.
```

### Results Processed with Failures (Step P4)

```
Regression results processed: N failures found, BUG discoveries created.

NEXT STEPS:
  1. Launch Builder to process regression failures and fix code bugs.
  2. After Builder fixes, re-run tests:
         ./tests/qa/run_all.sh
  3. When all tests pass, launch QA to process final results.
```

---

## Context Management

- Each scenario file is independent (no cross-feature state).
- QA loads one spec at a time (~200 lines), writes one JSON file (~30 lines), commits.
- Estimated capacity: 20-30 features per session before context pressure.
- Mid-session checkpoint: use `/pl-resume save` to capture regression authoring state.
- If context runs out mid-feature (scenario file not yet committed), the next session re-discovers the gap and re-authors from scratch. This is acceptable because authoring one file is fast.
- No separate queue file. Progress is tracked by file existence: `tests/qa/scenarios/<feature_name>.json` present = authored.

---

## Enriched Results Format

When reading `tests.json` detail entries, look for these optional fields (backward-compatible):

- `scenario_ref` -- Feature file path and scenario name (e.g., `features/instruction_audit.md:Single-turn detection`)
- `expected` -- Human-readable expected behavior from the Gherkin Then step
- `actual_excerpt` -- First ~500 characters of actual output when the test fails
- `assertion_tier` -- Integer (1, 2, or 3) indicating assertion quality tier per `features/arch_testing.md` Section 2.5:
  - **Tier 1:** Keyword presence (e.g., "table|findings") -- vulnerable to incidental matches
  - **Tier 2:** Specific finding (e.g., exact file name or defect identifier)
  - **Tier 3:** State verification (inspects agent's stated intent to produce artifacts)

These fields are written by the harness runner framework when processing scenario JSON files.
