# Feature: purlin:regression Regression Testing

> Label: "Agent Skills: QA: purlin:regression Regression Testing"
> Category: "Agent Skills: QA"
> Prerequisite: purlin_mode_system.md

## 1. Overview

The `purlin:regression` skill consolidates regression test operations (run, author, evaluate) into a single command with subcommands. It replaces the old `purlin:regression-run`, `purlin:regression-author`, and `purlin:regression-evaluate` skills.

---

## 2. Requirements

### 2.1 Auto-Detect (Bare Invocation)

Bare `purlin:regression` (no subcommand) MUST first print a **health summary** showing regression status counts (N PASS, N STALE, N FAIL, N NOT_RUN, total), then auto-detect the natural next step and execute it. If zero scenario files exist, print `"No regression scenarios authored yet."` instead of counts. The detection logic scans project state and picks the first matching rule:

1. **No scenario files exist** for any feature with QA scenarios, regression guidance, or web test metadata (Engineer DONE) → run `author`.
2. **Scenario files exist with STALE, FAIL, or NOT_RUN results** → run `run`.
3. **Fresh results exist that haven't been evaluated** → run `evaluate`. "Evaluated" means the feature's discovery sidecar contains a `[DISCOVERY]` or `[BUG]` entry referencing this regression result, OR the result is PASS (no entry needed). Fresh FAIL/STALE results without a corresponding sidecar entry are unevaluated.
4. **Everything is green** (all PASS, all evaluated) → print status summary and stop.

When a feature argument is provided (`purlin:regression <feature>`), apply the same detection logic scoped to that single feature.

After completing the auto-detected step, print a hint for what comes next:

```
Next: purlin:regression           (auto-detects next step)
  or: purlin:regression run       (re-run suites)
```

This allows a new user to repeatedly invoke `purlin:regression` to walk through the full author → run → evaluate cycle without knowing the subcommand names.

### 2.2 Subcommands

- `run [feature]` -- Execute regression suites via the harness runner.
- `author [feature]` -- Author regression JSON for untagged QA scenarios. Propose automation, write JSON, tag `@auto` or `@manual`.
- `evaluate [feature]` -- Compare results against baselines. Document FAIL results in companion files with scenario name, expected/actual, attempt count, and suggested fix.

Subcommands override auto-detection. Power users who know the step they want can invoke it directly.

### 2.3 Failure Documentation

- When `evaluate` finds a FAIL, MUST write a `[DISCOVERY]` entry to the companion file.
- On re-evaluation: mark `[RESOLVED]` if now PASS, update attempt count if still FAIL.

### 2.4 Consolidation

- Old skill files (`pl-regression-run.md`, `pl-regression-author.md`, `pl-regression-evaluate.md`) MUST be deleted.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Bare invocation auto-detects author step

    Given features with regression guidance exist
    And no scenario JSON files have been authored for them
    When purlin:regression is invoked with no subcommand
    Then QA runs the author workflow
    And prints a hint for the next step

#### Scenario: Bare invocation auto-detects run step

    Given scenario JSON files exist for regression-eligible features
    And their regression results are STALE or NOT_RUN
    When purlin:regression is invoked with no subcommand
    Then QA runs the suites with STALE/NOT_RUN results
    And auto-evaluates on completion

#### Scenario: Bare invocation auto-detects evaluate step

    Given fresh regression results exist with FAIL status
    And no companion file entry documents the failure
    When purlin:regression is invoked with no subcommand
    Then QA evaluates the results and writes discovery entries

#### Scenario: Bare invocation reports green status

    Given all regression suites have PASS status
    And all results have been evaluated
    When purlin:regression is invoked with no subcommand
    Then a status summary is printed
    And no subcommand is executed

#### Scenario: Evaluate documents failure in companion file

    Given regression results show FAIL for "skill_behavior_regression"
    When purlin:regression evaluate is invoked
    Then features/skill_behavior_regression.impl.md contains a [DISCOVERY] entry
    And the entry includes the scenario name and actual output

#### Scenario: Re-evaluate marks resolved

    Given a previously failing regression now passes
    When purlin:regression evaluate is invoked
    Then the companion file entry is marked [RESOLVED]

### Manual Scenarios (Human Verification Required)

None.
