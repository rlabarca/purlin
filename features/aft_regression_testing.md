# Feature: AFT Regression Testing

> Label: "AFT Regression Testing"
> Category: "Automated Feedback Tests"
> Prerequisite: features/arch_automated_feedback_tests.md

[Complete]

## 1. Overview

Provides infrastructure for running full AFT regression suites outside the build cycle. The Builder focuses on fast unit tests during Step 3; full AFT regression (Agent, Web) runs at user-chosen intervals, owned end-to-end by QA. QA authors the harness scripts, composes the regression set, and prints a clear copy-pasteable command for the user to run in an external terminal. Results feed back into the discovery system and enrich `tests.json` with scenario-level context so the Builder can batch-fix failures without re-running the suite.

---

## 2. Requirements

### 2.1 Runner Script

A shell script at `dev/aft_runner.sh` (Purlin-dev-specific, not consumer-facing) that dispatches AFT harnesses in two modes:

- **Watch mode:** `./dev/aft_runner.sh --watch` polls `.purlin/runtime/aft_trigger.json` at 1-second intervals. When a trigger file appears, the runner executes the specified harness, writes `.purlin/runtime/aft_result.json`, deletes the trigger, and resumes polling. SIGINT prints a summary of all executions in the session.
- **Once mode:** `./dev/aft_runner.sh --once <harness> [args...]` runs a single harness invocation and exits with the harness exit code.
- Per-execution timeout defaults to 300 seconds, configurable via `--timeout <seconds>`.
- Generic dispatch: the runner supports any harness that follows the `--write-results` convention. It does not hardcode harness paths.

**Trigger format** (`.purlin/runtime/aft_trigger.json`):

```json
{
  "harness": "dev/test_agent_interactions.sh",
  "args": ["--write-results"],
  "requested_at": "2026-03-18T14:30:00Z"
}
```

**Result format** (`.purlin/runtime/aft_result.json`):

```json
{
  "harness": "dev/test_agent_interactions.sh",
  "exit_code": 0,
  "started_at": "2026-03-18T14:30:01Z",
  "completed_at": "2026-03-18T14:32:15Z",
  "tests_json_path": "tests/aft_agent/tests.json",
  "summary": "21/21 passed"
}
```

### 2.2 QA Regression Skill

A QA-owned slash command at `.claude/commands/pl-regression.md`. QA owns the regression tier end-to-end: authoring harness scripts, composing regression sets, and triaging results.

**Harness authorship:** QA writes and maintains the harness scripts that test behavioral scenarios (agent interaction flows, web UI regression, API contract checks). Harness scripts are behavioral verification artifacts, not application code. They live alongside other QA verification scripts. The Builder does NOT write regression harnesses.

**Skill flow:**

1. Read feature status via `tools/cdd/status.sh --role qa`.
2. Identify regression-eligible features: features with AFT metadata (`> AFT Agent:` or `> AFT Web:`) that have STALE, FAIL, or NOT_RUN test results.
3. Present interactive options to the user: "Found N features eligible for regression. Run all, or select? [all / 1,2,... / skip]".
4. Compose an external command based on user selection (either a single `--once` invocation or a trigger file for watch mode).
5. Print the command in a clearly formatted, self-contained, copy-pasteable block. The user MUST be able to copy the entire command and paste it into a separate terminal without modification. Example format:
   ```
   Run this in a separate terminal:

       ./dev/aft_runner.sh --once dev/test_agent_interactions.sh --write-results

   Tell me when it finishes.
   ```
6. After user confirms completion: read `tests.json` files for each regression-tested feature, create `[BUG]` discovery sidecar entries for any failures, print a summary, and run `tools/cdd/status.sh`.

**UX invariant:** Whenever the QA agent asks the user to run anything in an external terminal -- whether through this skill or ad-hoc during triage -- it MUST print the exact, complete command. Never describe what to run; print the literal command. The user should never have to assemble a command from prose.

### 2.3 Enriched Result Format

Enhance `tests.json` detail entries with optional fields (backward-compatible with existing consumers):

- `scenario_ref` -- Feature file path and scenario name (e.g., `features/aft_agent.md:Single-turn agent test`).
- `expected` -- Human-readable expected behavior from the Gherkin Then step.
- `actual_excerpt` -- First ~500 characters of actual output when the test fails.

These fields give the Builder enough context to batch-fix failures without re-running the regression suite.

### 2.4 Builder Consumption Pattern

The Builder does NOT trigger or author regression tests. The Builder's only role in the regression tier is consuming results to fix application code. The user tells the Builder "regression results are ready." The Builder then:

1. Reads `tests.json` files for features with updated results.
2. Uses enriched fields (`scenario_ref`, `expected`, `actual_excerpt`) to diagnose and fix application code in one pass.
3. Re-runs only unit tests (Step 3 tier) to confirm fixes, without re-running the full regression suite.
4. Does NOT modify the harness scripts themselves. If a harness expectation is stale, the Builder flags it for QA to update.

### 2.5 Staleness Detection

A regression result is stale when the feature's source code was modified since the `tests.json` file's mtime. The QA regression skill uses staleness to prioritize re-testing: stale features appear first in the eligible list and are marked with a `[STALE]` indicator.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Watch mode polls and executes trigger

    Given the runner is started in watch mode
    When a trigger file is written to .purlin/runtime/aft_trigger.json
    Then the runner executes the specified harness
    And writes a result file to .purlin/runtime/aft_result.json
    And deletes the trigger file
    And resumes polling

#### Scenario: Once mode runs single harness invocation

    Given the runner is invoked with --once dev/test_agent_interactions.sh --write-results
    When the harness completes
    Then the runner exits with the harness exit code
    And a result file is written to .purlin/runtime/aft_result.json

#### Scenario: Watch mode timeout kills long-running harness

    Given the runner is started with --watch --timeout 5
    When a trigger specifies a harness that runs longer than 5 seconds
    Then the runner kills the harness process
    And writes a result file with a non-zero exit code
    And resumes polling

#### Scenario: Watch mode SIGINT prints session summary

    Given the runner is in watch mode and has completed 3 executions
    When the user sends SIGINT
    Then the runner prints a summary of all 3 executions with pass/fail counts
    And exits cleanly

#### Scenario: Runner handles malformed trigger gracefully

    Given the runner is in watch mode
    When a trigger file contains invalid JSON
    Then the runner logs an error message
    And deletes the malformed trigger file
    And resumes polling without crashing

#### Scenario: QA skill identifies regression-eligible features

    Given the project has 5 features with AFT metadata
    And 2 features have STALE test results
    And 1 feature has FAIL test results
    When the QA agent invokes the regression skill
    Then the skill lists 3 eligible features sorted by staleness
    And presents the interactive selection prompt

#### Scenario: QA skill composes external command for selected features

    Given the QA agent selects features 1 and 3 from the eligible list
    When the skill composes the regression command
    Then the command uses --once mode for single features or writes a trigger file for watch mode
    And the composed command includes the correct harness path and args

#### Scenario: QA skill creates BUG discoveries for regression failures

    Given regression results show 2 failed scenarios across 2 features
    When the QA agent reads the regression results
    Then a [BUG] discovery sidecar entry is created for each failed feature
    And each entry includes the scenario_ref and actual_excerpt from enriched results

#### Scenario: Enriched results include scenario-level context

    Given a harness writes tests.json with enriched fields
    When the result file is read
    Then each detail entry contains scenario_ref with feature path and scenario name
    And failed entries contain expected and actual_excerpt fields

#### Scenario: Staleness detection prioritizes re-testing

    Given feature A has tests.json from 2 hours ago and source modified 1 hour ago
    And feature B has tests.json from 1 hour ago and no source modifications
    When the QA skill computes the eligible list
    Then feature A appears first with a STALE indicator
    And feature B does not appear in the eligible list

### Manual Scenarios (Human Verification Required)

None.
