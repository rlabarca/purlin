# Feature: Agent Session Entry (Shared)

> Label: "Tool: Agent Session Entry (Shared)"
> Category: "Install, Update & Scripts"
> Prerequisite: models_configuration.md (config drives model selection)
> Prerequisite: config_layering.md (purlin:resume reads resolved config, not raw config.json)


## 1. Overview

Defines the shared mechanical requirements for Purlin agent session entry and mode switching. Shell launcher scripts (`pl-run-<role>.sh`) are retired. Sessions are now started by running `claude` directly -- the Purlin plugin auto-activates via MCP hooks (SessionStart, SessionEnd, PreToolUse, etc.).

Session entry is handled by the `purlin:resume` skill, which detects project state and performs context setup. Mode switching is handled by the `purlin:mode` skill.

**Retired:** `pl-run.sh`, `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`. These shell launcher scripts are no longer generated or used. Init and refresh modes remove them if found.


## 2. Requirements

### 2.1 Session Entry via Plugin

*   **Entry point:** Users start sessions by running `claude`. The Purlin plugin auto-activates via the MCP server registered in `.claude/settings.json`.
*   **`purlin:resume` skill:** On session start, this skill reads resolved config, detects project state (scan, delivery plan, pending work), and sets the operating mode.
*   **Project root detection:** Uses `PURLIN_PROJECT_ROOT` env var if set, otherwise detects from `.purlin/` directory presence.
*   **Agent role:** The operating mode (Engineer, PM, QA) is managed by plugin state rather than an `AGENT_ROLE` env var exported by a shell launcher.

### 2.2 Prompt Assembly

1.  The plugin assembles the system prompt by concatenating instruction files in order: `instructions/PURLIN_BASE.md`, mode-specific base (e.g., `instructions/ENGINEER_BASE.md`).
2.  If `PURLIN_OVERRIDES.md` (General section) exists, append it.
3.  If mode-specific overrides exist in `.purlin/PURLIN_OVERRIDES.md`, append the relevant section.
4.  Each appended file is preceded by newline separation.

### 2.3 Config Reading

*   Read agent settings (`model`, `effort`, `bypass_permissions`, `find_work`, `auto_start`, `model_warning`, `model_warning_dismissed`) from the **resolved config** using the config resolver (see `config_layering.md` Section 2.1 and 2.2).
*   The `purlin:resume` skill calls the config resolver and applies the resolved settings.
*   **Role fallback:** When the requested role (e.g., `purlin`) is absent from `agents` in the resolved config, the resolver falls back to `agents.builder` if present. This supports consumer projects that have not yet added an `agents.purlin` block.
*   Default values when the resolver is unavailable or config is absent: empty model, empty effort, bypass false, find_work true, auto_start false, empty model_warning, model_warning_dismissed false.

### 2.4 Model Warning Display

*   When the assigned model has a non-empty warning field AND the warning has not been dismissed, the `purlin:resume` skill MUST display the warning before proceeding.
*   Auto-acknowledge the warning by calling the config resolver's `acknowledge_warning` function, which adds the model ID to `acknowledged_warnings` in `config.local.json`. This ensures the warning is shown only once per model.
*   When the warning has been acknowledged, no warning is displayed.

### 2.5 Mode Switching

*   The `purlin:mode` skill allows switching between Engineer, PM, and QA modes within a running session.
*   Mode switching updates the active instruction set and applicable overrides without restarting the session.
*   Plugin hooks (PreToolUse) enforce write-access boundaries based on the current mode.

### 2.6 Plugin Hooks

The Purlin plugin registers hooks that replace launcher-based mechanisms:

*   **SessionStart:** Triggers `purlin:resume` for context setup and work discovery.
*   **SessionEnd:** Handles cleanup (server shutdown, state persistence).
*   **PreToolUse:** Enforces mode-specific write-access boundaries (mode guard).

### 2.7 Role-Specific Details

Each mode's behavior is defined by:
*   **Write-access boundaries** (enforced by PreToolUse hook based on current mode).
*   **Instruction files** (mode-specific base and overrides).
*   **Default config values** (fallback when `agents.purlin` is absent from config).


## 3. Scenarios

### Unit Tests

#### Scenario: Plugin Auto-Activates on Session Start
    Given a consumer project has Purlin configured with .purlin/ and .claude/settings.json
    When the user runs "claude" to start a session
    Then the Purlin plugin auto-activates via the registered MCP server
    And purlin:resume runs to set up session context

#### Scenario: purlin:resume Reads Resolved Config
    Given config.json and config.local.json exist with agent settings
    When purlin:resume runs during session entry
    Then it reads agent settings from the resolved config
    And it does not read config.json directly

#### Scenario: purlin:resume Displays Warning and Auto-Acknowledges on First Run
    Given the agent's assigned model has a non-empty warning field with warning_dismissible true
    And the model ID is not in the acknowledged_warnings array
    When purlin:resume runs during session entry
    Then it displays the warning text before proceeding
    And the model ID is added to acknowledged_warnings in config.local.json

#### Scenario: purlin:resume Suppresses Warning on Subsequent Runs
    Given the agent's assigned model has a non-empty warning field
    And the model ID appears in the acknowledged_warnings array
    And the model has warning_dismissible true
    When purlin:resume runs during session entry
    Then no warning is displayed

#### Scenario: purlin:resume Falls Back When Config is Absent
    Given config.json does not contain an agents section
    And the config resolver returns defaults
    When purlin:resume runs during session entry
    Then it uses default values (empty model, empty effort, bypass false)

#### Scenario: purlin:mode Switches Operating Mode
    Given a session is active in Engineer mode
    When the user invokes purlin:mode with target mode "PM"
    Then the active mode switches to PM
    And the instruction set updates to PM-specific files
    And the PreToolUse hook enforces PM write-access boundaries

#### Scenario: PreToolUse Hook Enforces Mode Boundaries
    Given a session is active in PM mode
    When the agent attempts to write a code file
    Then the PreToolUse hook blocks the write
    And reports a mode boundary violation

### QA Scenarios

None.
