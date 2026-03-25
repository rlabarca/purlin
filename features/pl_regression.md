# Feature: /pl-regression Regression Testing

> Label: "Agent Skills: QA: /pl-regression Regression Testing"
> Category: "Agent Skills: QA"
> Prerequisite: features/purlin_mode_system.md

## 1. Overview

The `/pl-regression` skill consolidates regression test operations (run, author, evaluate) into a single command with subcommands. It replaces the old `/pl-regression-run`, `/pl-regression-author`, and `/pl-regression-evaluate` skills.

---

## 2. Requirements

### 2.1 Subcommands

- `run [feature]` -- Execute regression suites via the harness runner.
- `author [feature]` -- Author regression JSON for untagged QA scenarios. Propose automation, write JSON, tag `@auto` or `@manual`.
- `evaluate [feature]` -- Compare results against baselines. Document FAIL results in companion files with scenario name, expected/actual, attempt count, and suggested fix.

### 2.2 Failure Documentation

- When `evaluate` finds a FAIL, MUST write a `[DISCOVERY]` entry to the companion file.
- On re-evaluation: mark `[RESOLVED]` if now PASS, update attempt count if still FAIL.

### 2.3 Consolidation

- Old skill files (`pl-regression-run.md`, `pl-regression-author.md`, `pl-regression-evaluate.md`) MUST be deleted.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Evaluate documents failure in companion file

    Given regression results show FAIL for "skill_behavior_regression"
    When /pl-regression evaluate is invoked
    Then features/skill_behavior_regression.impl.md contains a [DISCOVERY] entry
    And the entry includes the scenario name and actual output

#### Scenario: Re-evaluate marks resolved

    Given a previously failing regression now passes
    When /pl-regression evaluate is invoked
    Then the companion file entry is marked [RESOLVED]

### Manual Scenarios (Human Verification Required)

None.
