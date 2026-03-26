# Feature: Regression Evaluation

> Label: "/pl-regression-evaluate Regression Evaluation"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/regression_testing.md

[TODO]

## 1. Overview

The QA skill for processing regression test results after execution. Reads enriched `regression.json` results, creates BUG discoveries for failures, computes assertion tier distribution metrics, flags shallow assertion suites, and prints a structured summary with handoff guidance for the Engineer.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Result Reading

- Read `tests/<feature>/tests.json` for features with recently updated results.
- If no recently updated results exist, report "No unprocessed regression results found."

### 2.3 Failure Processing

- For each feature with failures: read enriched fields (scenario_ref, expected, actual_excerpt).
- Create `[BUG]` discovery entries in the feature's discovery sidecar with full context.

### 2.4 Tier Distribution

- Compute assertion tier distribution (Tier 1, 2, 3, untagged) across all results.
- Flag suites with >50% Tier 1 assertions as `[SHALLOW]`.

### 2.5 Summary and Handoff

- Print structured summary: per-feature PASS/FAIL with counts.
- Run `status.sh` to refresh Critic report.
- If failures found, print handoff message directing to launch Engineer.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given a Engineer agent session
    When the agent invokes /pl-regression-evaluate
    Then the command responds with a redirect message

#### Scenario: No unprocessed results reports clean state

    Given no recently updated tests.json files exist
    When /pl-regression-evaluate is invoked
    Then the output says "No unprocessed regression results found"

#### Scenario: Failures create BUG discoveries

    Given feature_a has 2 failed scenarios in tests.json
    When /pl-regression-evaluate processes results
    Then 2 BUG discoveries are created in feature_a.discoveries.md

#### Scenario: Shallow suite flagged when more than 50 percent Tier 1

    Given a suite with 6 Tier 1 and 4 Tier 2 assertions
    When tier distribution is computed
    Then the suite is flagged as [SHALLOW]

### QA Scenarios

None.
