# Feature: Regression Run

> Label: "/pl-regression-run Regression Run"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/regression_testing.md

[TODO]

## 1. Overview

The QA skill for executing existing regression scenarios. Discovers regression-eligible features (FAIL, NOT_RUN, or STALE test results), presents options to the user, and composes a copy-pasteable command for external terminal execution. Supports frequency filtering (per-feature vs pre-release) and offers productive wait suggestions while tests run.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Arguments

- `--frequency per-feature` (default): standard-frequency suites only.
- `--frequency pre-release`: include all suites including long-running ones.

### 2.3 Discovery

- Identify features with existing scenario JSON and stale/failing/missing test results.
- Sort: STALE first, then FAIL, then NOT_RUN.

### 2.4 Command Composition

- Compose copy-pasteable command block for external terminal execution.
- Support single-feature and multi-feature (sequential chain) commands.

### 2.5 Productive Wait

- After printing the command, offer concurrent work suggestions.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-regression-run
    Then the command responds with a redirect message

#### Scenario: No eligible features reports clean state

    Given all regression results are current
    When /pl-regression-run is invoked
    Then the output says "No regression-eligible features found"

#### Scenario: Frequency filter excludes pre-release suites by default

    Given a scenario file with frequency "pre-release"
    When /pl-regression-run is invoked without --frequency flag
    Then the pre-release suite is excluded from the eligible list

#### Scenario: Command block is copy-pasteable

    Given feature_a and feature_b are eligible
    When the user selects both
    Then a complete, copy-pasteable command is printed in a formatted block

### QA Scenarios

None.
