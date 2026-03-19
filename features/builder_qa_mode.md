# Feature: Builder QA Mode

> Label: "Tool: Builder QA Mode"
> Category: "Install, Update & Scripts"
> Prerequisite: features/builder_agent_launcher.md
> Prerequisite: features/config_layering.md

[Complete]

## 1. Overview

A simple boolean flag that switches the Builder into QA builder mode, scoping its feature visibility to test infrastructure only. When active, the Builder sees only "Test Infrastructure" category features; all other features are invisible. When inactive (default), Test Infrastructure features are completely hidden from the Builder's find_work, work plan, and action items.

This separation prevents test infrastructure work from mixing into normal feature-building sessions. The human explicitly opts in to test infrastructure work by setting the flag.

---

## 2. Requirements

### 2.1 QA Mode Flag

- A `qa_mode` boolean in Builder agent config. Default: `false`.
- When `qa_mode: false` (default): The Builder completely ignores "Test Infrastructure" category features. They do not appear in find_work results, the work plan, or action items. The Builder behaves as if they do not exist.
- When `qa_mode: true`: The Builder enters QA builder mode. find_work shows ONLY "Test Infrastructure" category features. Normal application features are invisible. The startup print sequence shows `[QA Builder Mode]` to make the mode visible.

### 2.2 Configuration Sources

The `qa_mode` flag can be set via three mechanisms, in priority order:

1. **Environment variable:** `PURLIN_BUILDER_QA=true` overrides all other sources.
2. **Local config:** `.purlin/config.local.json` under `"agents": {"builder": {"qa_mode": true}}`.
3. **Project config:** `.purlin/config.json` under `"agents": {"builder": {"qa_mode": false}}` (default).

The `/pl-agent-config` command can toggle `qa_mode` in the local config file.

### 2.3 Startup Integration

When the Builder reads its startup flags (Section 2.0.1 of BUILDER_BASE.md), it also reads `qa_mode`:

1. Check `PURLIN_BUILDER_QA` environment variable. If set to `true`, `qa_mode` is true.
2. Otherwise, read from resolved config (local then project).
3. If `qa_mode: true`, prepend `[QA Builder Mode]` to the startup print sequence header.
4. Apply the feature filter before any other startup processing (find_work, delivery plan creation, continuous mode phasing).

### 2.4 Feature Filtering

The filter is applied at the earliest point in the startup protocol, before features are presented in find_work or delivery plan:

- **`qa_mode: true`:** Include only features where `category == "Test Infrastructure"`.
- **`qa_mode: false`:** Exclude all features where `category == "Test Infrastructure"`.

This filtering applies to:
- `tools/cdd/status.sh --startup builder` output consumption (feature list).
- Delivery plan feature set (if `--continuous` is active).
- Critic action items (only items for visible features are shown).

### 2.5 Composability with Continuous Mode

The `--qa` flag and `--continuous` flag are orthogonal:

- `--qa` alone: Builder works on test infrastructure features one at a time in a normal session.
- `--qa --continuous`: Builder enters continuous phase mode scoped to test infrastructure features only. Delivery plan, phase analysis, inter-phase Critic -- all operate within the QA-filtered feature set.
- `--continuous` alone (no `--qa`): Normal continuous mode, test infrastructure features excluded.

The continuous phase builder already respects the feature set from find_work, so the composition is natural. `qa_mode` filters the feature set BEFORE continuous phase analysis.

### 2.6 Launcher Integration

The Builder agent launcher script (`tools/launchers/builder.sh` or equivalent) reads the `PURLIN_BUILDER_QA` environment variable and passes it through to the Claude session. No special launcher changes are required -- the env var is read at Builder startup protocol time, not launcher time.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Default mode hides test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And qa_mode is false (default)
    When the Builder runs startup find_work
    Then 8 features appear in the work plan
    And the 2 Test Infrastructure features are not listed

#### Scenario: QA mode shows only test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And qa_mode is true
    When the Builder runs startup find_work
    Then only the 2 Test Infrastructure features appear in the work plan
    And the 8 non-test features are not listed

#### Scenario: QA mode prints header indicator

    Given qa_mode is true
    When the Builder prints its startup command table
    Then the header includes "[QA Builder Mode]"

#### Scenario: Environment variable overrides config

    Given .purlin/config.json has qa_mode: false
    And PURLIN_BUILDER_QA=true is set in the environment
    When the Builder reads startup flags
    Then qa_mode is true
    And only Test Infrastructure features are visible

#### Scenario: QA mode composes with continuous mode

    Given qa_mode is true
    And the continuous phase flag is active
    And there are 4 Test Infrastructure features in TODO state
    When the Builder creates a delivery plan
    Then the plan contains only Test Infrastructure features
    And phase analysis operates on the filtered set

#### Scenario: Agent config command toggles QA mode

    Given qa_mode is currently false in .purlin/config.local.json
    When the user runs /pl-agent-config and sets qa_mode to true
    Then .purlin/config.local.json contains "qa_mode": true under builder
    And the next Builder session will enter QA builder mode

### Manual Scenarios (Human Verification Required)

None.
