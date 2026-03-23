# Feature: Skill Behavior Regression Testing

> Label: "Tool: Skill Behavior Regression"
> Category: "Test Infrastructure"
> Prerequisite: features/arch_testing.md
> Prerequisite: features/regression_testing.md
> Prerequisite: features/test_fixture_repo.md
> Test Fixtures: https://github.com/rlabarca/purlin-fixtures

[Complete]

## 1. Overview

Regression tests that verify Purlin agents behave correctly after instruction file changes. Uses `claude --print` to invoke agents against fixture-based consumer project states and asserts on output patterns. This is the highest-impact missing test coverage -- instruction edits are the primary source of behavioral regressions, and nothing currently catches them automatically.

These tests are long-running (5-10 minutes for the full suite), run infrequently (pre-release or after instruction changes), and use the Haiku model for cost efficiency.

---

## 2. Requirements

### 2.1 Fixture Tags in purlin-fixtures

Consumer project state snapshots stored in the `purlin-fixtures` repo:

| Tag | State Description |
|-----|-------------------|
| `main/skill_behavior/mixed-lifecycle` | Consumer project with 3 TODO features, 2 TESTING, 2 COMPLETE features. All roles configured in config.json. Critic report pre-generated. Includes HOW_WE_WORK_BASE + all role bases + project overrides. |
| `main/skill_behavior/fresh-init` | Freshly initialized consumer project (post project_init). No feature specs yet. Default config with all roles at defaults. |
| `main/skill_behavior/architect-backlog` | Consumer project with Architect action items: spec gate FAILs on 2 features, 1 untracked file in features/, 1 SPEC_PROPOSAL pending in a companion file. |

Each fixture tag contains a complete `.purlin/` config, `features/` directory, `instructions/` directory (base files), `tests/` directory with pre-generated `critic.json` files, and any other files the scenario requires. The fixture state MUST be self-contained -- tests should not depend on external network or the current Purlin repo state.

### 2.2 Scenario JSON

**Location:** `tests/qa/scenarios/skill_behavior_regression.json`

**Schema:** Follows `features/regression_testing.md` Section 2.7.

- `harness_type`: `agent_behavior`
- `frequency`: `pre-release`
- 9 scenarios across 3 tiers (see Section 3)

### 2.3 Invocation Mechanism

Each scenario invokes Claude via the `agent_behavior` harness:

1. Check out fixture tag from `purlin-fixtures` repo via `fixture checkout`.
2. Construct a 4-layer system prompt from the fixture's instruction files:
   - Layer 1: `instructions/HOW_WE_WORK_BASE.md`
   - Layer 2: `instructions/<ROLE>_BASE.md`
   - Layer 3: `.purlin/HOW_WE_WORK_OVERRIDES.md`
   - Layer 4: `.purlin/<ROLE>_OVERRIDES.md`
3. Run `claude --print --no-session-persistence --model claude-haiku-4-5-20251001 --append-system-prompt-file <prompt-file> --output-format json "<trigger>"` with CWD set to the fixture checkout directory.
4. Extract `.result` from JSON response via `jq -r '.result'`.
5. Evaluate assertions against the extracted text.
6. Clean up fixture via `fixture cleanup`.

### 2.4 Model and Cost

- **Model:** `claude-haiku-4-5-20251001` (cost-effective for regression, ~$0.01-0.05 per invocation)
- **Per-suite cost:** ~$0.10-0.50 for 9 scenarios
- **Per-scenario time:** 30-60 seconds (API round-trip + inference)
- **Full suite time:** 5-10 minutes

### 2.5 Execution Model

- **Frequency:** Pre-release verification, after instruction file changes, or manual trigger. NOT per-feature.
- **Invocation options:**
  1. QA invokes `/pl-regression-run --frequency pre-release` to include this suite in the eligible list
  2. User runs `dev/run_skill_regression.sh` directly from CLI
  3. Direct harness invocation: `python3 tools/test_support/harness_runner.py tests/qa/scenarios/skill_behavior_regression.json`
- **Results:** Written to `tests/skill_behavior_regression/tests.json` (standard enriched format per `regression_testing.md` Section 2.3)

### 2.6 Dev Runner Script (Purlin-Dev Only)

**Location:** `dev/run_skill_regression.sh`

A convenience wrapper for running the skill behavior suite directly:

- Resolves project root and fixture repo
- Runs setup script if fixture repo is missing
- Invokes `tools/test_support/harness_runner.py tests/qa/scenarios/skill_behavior_regression.json`
- Prints summary with pass/fail counts
- Exits with 0 if all pass, 1 if any fail

### 2.7 Assertion Strategy

All assertions MUST be Tier 2 or higher (structural patterns, not keyword-only):

- **Command table detection:** `(?s)━+.*━+` (Unicode border characters spanning content)
- **Role refusal patterns:** `(?i)(never|must not|cannot|zero.code|architect.owned|spec.files|do not write)`
- **Status summary patterns:** `(?i)(TODO|TESTING|COMPLETE).*\d+`
- **Skill-specific patterns:** `/pl-spec`, `/pl-build`, `/pl-verify` presence or absence depending on role
- **Negative assertions:** Verify that role-inappropriate commands do NOT appear (e.g., Architect output must not contain `/pl-build`)

### 2.8 Regression Testing

Regression tests verify that Purlin agents start up correctly, enforce role boundaries, and dispatch skills properly when operating in consumer projects.

- **Approach:** Agent behavior harness with fixture-based consumer project states
- **Scenarios covered:** All 9 scenarios in Section 3

### 2.9 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/skill_behavior/mixed-lifecycle` | Standard consumer project with mixed feature lifecycle states |
| `main/skill_behavior/fresh-init` | Empty consumer project post-initialization |
| `main/skill_behavior/architect-backlog` | Consumer project with pending Architect work |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Architect startup prints command table on mixed-lifecycle project

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the ARCHITECT role
    When claude --print is invoked with "Begin Architect session."
    Then the output contains a command table with Unicode border characters
    And the output references /pl-spec
    And the output references /pl-anchor

#### Scenario: Builder startup identifies TODO features on mixed-lifecycle project

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the BUILDER role
    When claude --print is invoked with "Begin Builder session."
    Then the output contains a command table with Unicode border characters
    And the output identifies TODO features by name
    And the output proposes a work plan or execution order

#### Scenario: QA startup identifies TESTING features on mixed-lifecycle project

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the QA role
    When claude --print is invoked with "Begin QA session."
    Then the output identifies TESTING features
    And the output proposes a verification order or plan

#### Scenario: Architect refuses to write code

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the ARCHITECT role
    When claude --print is invoked with "Edit main.py and fix the import statement on line 5."
    Then the output refuses the request
    And the output references the zero-code mandate or states it never writes code

#### Scenario: Builder refuses to edit spec files

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the BUILDER role
    When claude --print is invoked with "Update features/auth.md and add a new scenario for password reset."
    Then the output refuses the request
    And the output indicates spec files are Architect-owned

#### Scenario: QA refuses to write application code

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the QA role
    When claude --print is invoked with "Fix the bug in utils.py by changing the return value on line 12."
    Then the output refuses the request
    And the output references the zero-code mandate or states it cannot write code

#### Scenario: Status skill produces structured summary

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the ARCHITECT role
    When claude --print is invoked with "/pl-status"
    Then the output contains feature counts by lifecycle status
    And the output references TODO, TESTING, or COMPLETE states

#### Scenario: Architect help shows correct commands

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the ARCHITECT role
    When claude --print is invoked with "/pl-help"
    Then the output contains /pl-spec
    And the output contains /pl-anchor
    And the output does not contain /pl-build
    And the output does not contain /pl-verify

#### Scenario: Builder help shows correct commands

    Given the fixture tag main/skill_behavior/mixed-lifecycle is checked out
    And a 4-layer system prompt is constructed for the BUILDER role
    When claude --print is invoked with "/pl-help"
    Then the output contains /pl-build
    And the output does not contain /pl-spec
    And the output does not contain /pl-anchor

### QA Scenarios

None.
