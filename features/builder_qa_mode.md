# Feature: Builder QA Mode

> Label: "Tool: Builder QA Mode"
> Category: "Install, Update & Scripts"
> Prerequisite: features/builder_agent_launcher.md
> Prerequisite: features/config_layering.md

[TODO]

## 1. Overview

A `-qa` launcher flag that switches the Builder into QA builder mode, scoping its feature visibility to test infrastructure only. When active, the Builder sees only "Test Infrastructure" category features; all other features are invisible. When inactive (default), Test Infrastructure features are completely hidden from the Builder's find_work, work plan, and action items.

This separation prevents test infrastructure work from mixing into normal feature-building sessions. The human explicitly opts in to test infrastructure work by running the launcher with `-qa`.

---

## 2. Requirements

### 2.1 `-qa` Launcher Flag

- The Builder agent launcher script (`pl-run-builder.sh`) accepts a `-qa` flag.
- When `-qa` is passed, the launcher sets an internal environment variable `PURLIN_BUILDER_QA=true`.
- The env var is internal plumbing between the launcher and `serve.py`. Users never set it manually -- they use the `-qa` flag.
- No `qa_mode` config key exists. The `-qa` flag is the sole entry point.

### 2.2 Internal Plumbing

- `tools/cdd/serve.py` reads the `PURLIN_BUILDER_QA` environment variable during `--startup builder`.
- When `PURLIN_BUILDER_QA=true`: The startup briefing filters to Test Infrastructure features only. The Builder sees `[QA Builder Mode]` in the startup header.
- When the env var is absent or not `true`: Normal mode. Test Infrastructure features are excluded from find_work.

### 2.3 Normal Mode Recommendation

In normal mode (no `-qa` flag):
- The Builder works on non-Test-Infrastructure features.
- The startup briefing includes a `test_infrastructure_pending` count: the number of TODO Test Infrastructure features.
- After the Builder completes all normal TODO items, if `test_infrastructure_pending > 0`, the briefing recommends: "N Test Infrastructure features pending. Use `./pl-run-builder.sh -qa` for a focused session."

### 2.4 Feature Filtering

The filter is applied at the earliest point in the startup protocol, before features are presented in find_work or delivery plan:

- **`-qa` flag active (`PURLIN_BUILDER_QA=true`):** Include only features where `category == "Test Infrastructure"`.
- **Normal mode:** Exclude all features where `category == "Test Infrastructure"`.

This filtering applies to:
- `tools/cdd/status.sh --startup builder` output consumption (feature list).
- Delivery plan feature set (if `--continuous` is active).
- Critic action items (only items for visible features are shown).

### 2.5 Composability with Continuous Mode

The `-qa` flag and `--continuous` flag are orthogonal:

- `-qa` alone: Builder works on test infrastructure features one at a time in a normal session.
- `-qa --continuous`: Builder enters continuous phase mode scoped to test infrastructure features only.
- `--continuous` alone (no `-qa`): Normal continuous mode, test infrastructure features excluded.

### 2.6 Launcher Integration

#### Purlin Repository

`pl-run-builder.sh` includes a case statement that handles the `-qa` flag:
```
-qa) export PURLIN_BUILDER_QA=true ;;
```

#### Consumer Projects

`tools/init.sh`'s `generate_launcher()` function includes `-qa` flag handling in the generated builder launcher. Consumer projects get the flag on next `pl-update-purlin` via launcher refresh mode.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Default mode hides test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And PURLIN_BUILDER_QA is not set
    When the Builder runs startup find_work
    Then 8 features appear in the work plan
    And the 2 Test Infrastructure features are not listed

#### Scenario: -qa flag shows only test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And PURLIN_BUILDER_QA=true is set (via -qa flag)
    When the Builder runs startup find_work
    Then only the 2 Test Infrastructure features appear in the work plan
    And the 8 non-test features are not listed

#### Scenario: -qa flag prints header indicator

    Given PURLIN_BUILDER_QA=true is set
    When the Builder prints its startup command table
    Then the header includes "[QA Builder Mode]"

#### Scenario: Normal mode shows test_infrastructure_pending count

    Given the project has 3 Test Infrastructure features in TODO state
    And PURLIN_BUILDER_QA is not set
    When the Builder reads the startup briefing
    Then `test_infrastructure_pending` is 3

#### Scenario: Normal mode recommends -qa after zero TODO

    Given the Builder has completed all non-Test-Infrastructure TODO features
    And test_infrastructure_pending is 2
    When the Builder presents the work plan
    Then the plan includes a recommendation: "2 Test Infrastructure features pending. Use ./pl-run-builder.sh -qa for a focused session."

#### Scenario: -qa flag composes with continuous mode

    Given PURLIN_BUILDER_QA=true is set
    And the continuous phase flag is active
    And there are 4 Test Infrastructure features in TODO state
    When the Builder creates a delivery plan
    Then the plan contains only Test Infrastructure features
    And phase analysis operates on the filtered set

### QA Scenarios

None.
