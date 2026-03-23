# Feature: Regression Scenario Authoring

> Label: "/pl-regression-author Regression Scenario Authoring"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/regression_testing.md

[TODO]

## 1. Overview

The QA skill for creating regression scenario JSON files from feature specs. Discovers features that have reached Builder DONE status with no existing scenario file, then sequentially authors scenario JSON for each feature following the schema defined in the regression testing spec. Supports fixture integration with three-tier fixture repo resolution and generates consumer wrapper scripts on first use.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Prerequisite Check

- Check for harness runner framework at `tools/test_support/harness_runner.py`.
- If missing: print handoff message directing user to launch Builder and STOP.

### 2.3 Feature Discovery

- Run `status.sh --role qa` to identify features needing authoring: has Regression Testing or Regression Guidance section or Web Test metadata, Builder status is DONE, and no `tests/qa/scenarios/<feature_name>.json` exists.

### 2.4 Scenario Authoring

- Process one feature at a time to conserve context.
- Read feature spec, evaluate fixture needs, compose scenario JSON following the regression testing schema.
- Set `harness_type` based on test pattern (agent_behavior, web_test, custom_script).
- Write to `tests/qa/scenarios/<feature_name>.json` and commit per feature.

### 2.5 Consumer Wrapper

- On first authoring session: generate `tests/qa/run_all.sh` wrapper if absent.

### 2.6 Fixture Integration

- Three-tier fixture repo resolution: per-feature metadata, project-level config, convention path.
- Decision tree for fixture needs: inline setup_commands for simple state, fixture tags for complex state.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-regression-author
    Then the command responds with a redirect message

#### Scenario: Missing harness runner blocks authoring

    Given harness_runner.py does not exist
    When /pl-regression-author is invoked
    Then a handoff message is printed directing to launch Builder
    And no scenario files are created

#### Scenario: Feature discovery identifies eligible features

    Given feature_a has Builder DONE status and Regression Guidance section
    And no tests/qa/scenarios/feature_a.json exists
    When /pl-regression-author discovers features
    Then feature_a is listed as needing scenario authoring

#### Scenario: Scenario JSON follows regression schema

    Given feature_a is selected for authoring
    When the scenario JSON is composed
    Then it includes harness_type, scenario entries with assertions
    And it is written to tests/qa/scenarios/feature_a.json

### QA Scenarios

None.
