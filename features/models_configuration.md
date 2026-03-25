# Feature: Model Configuration

> Label: "Tool: Model Configuration"
> Category: "Install, Update & Scripts"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 2: Roles and Responsibilities)


## 1. Overview
Purlin agents (PM, Engineer, QA, PM) are launched via shell scripts that invoke the Claude CLI. This feature makes agent runtime parameters (model, effort, permissions) configurable via `config.json`. Claude is the sole supported LLM provider.


## 2. Requirements

### 2.1 Config Schema

*   **`models` Array:** The `config.json` file MUST contain a `models` array at the top level. Each entry defines a Claude model available for assignment to agents.
*   **Model Object:** Each model entry MUST have:
    *   `id` (string): The model identifier passed to the CLI (e.g., `"claude-sonnet-4-6"`).
    *   `label` (string): Human-readable display name (e.g., `"Sonnet 4.6"`).
    *   `capabilities` (object): Controls which dashboard controls appear for this model.
        *   `effort` (boolean): Whether the effort dropdown is shown.
        *   `permissions` (boolean): Whether the bypass-permissions checkbox is shown.
    *   `warning` (string, optional): When present, a prominent cost/capability warning displayed at all configuration surfaces where this model is selectable. Omit for models with no special warnings.
    *   `warning_dismissible` (boolean, optional, default `false`): When `true`, the user can acknowledge the warning to suppress it permanently in their local config. When `false` or absent, the warning always displays and cannot be dismissed.
*   **`acknowledged_warnings` Array (optional):** The config MAY contain an `acknowledged_warnings` array at the top level. Each entry is a model ID (string) whose warning the user has dismissed. Stored in `config.local.json` only. When a model's `id` appears in this array AND the model has `warning_dismissible: true`, the warning is suppressed at all surfaces.
*   **`agents` Section:** The `config.json` file MUST contain an `agents` object with keys `"architect"`, `"builder"`, `"qa"`, and optionally `"pm"`. Each agent entry MUST have:
    *   `model` (string): Model ID from the `models` array.
    *   `effort` (string): One of `"low"`, `"medium"`, `"high"`. Only meaningful when the model's `capabilities.effort` is `true`.
    *   `bypass_permissions` (boolean): Whether to skip permission prompts. Only meaningful when the model's `capabilities.permissions` is `true`.
    *   `find_work` (boolean, optional): Whether the agent runs its startup work-finding protocol. Default `true`. See `agent_launchers_common.md` Section 2.3.
    *   `auto_start` (boolean, optional): Whether the agent begins executing its work plan without waiting for user approval. Default `false`. See `agent_launchers_common.md` Section 2.3.
*   **Canonical Schema:** The following structure is the reference for both `config.json` and `purlin-config-sample/config.json`. Engineer mode MUST update both files to match, removing the former `llm_providers` wrapper and any `provider` fields from `agents.*` entries:

```json
{
    "models": [
        {
            "id": "claude-opus-4-6",
            "label": "Opus 4.6",
            "capabilities": { "effort": true, "permissions": true }
        },
        {
            "id": "claude-sonnet-4-6",
            "label": "Sonnet 4.6",
            "capabilities": { "effort": true, "permissions": true }
        },
        {
            "id": "claude-haiku-4-5-20251001",
            "label": "Haiku 4.5",
            "capabilities": { "effort": true, "permissions": true }
        },
        {
            "id": "claude-opus-4-6[1m]",
            "label": "Opus 4.6 [1M]",
            "capabilities": { "effort": true, "permissions": true },
            "warning": "Extended context (1M tokens). On Pro plans, this uses additional paid credits beyond your subscription.",
            "warning_dismissible": true
        }
    ],
    "agents": {
        "architect": { "model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true, "find_work": true, "auto_start": false },
        "builder":   { "model": "claude-opus-4-6",   "effort": "high", "bypass_permissions": true, "find_work": true, "auto_start": false },
        "qa":        { "model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": true, "find_work": true, "auto_start": false },
        "pm":        { "model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": true, "find_work": true, "auto_start": false }
    }
}
```

### 2.2 Model Warning Display and Acknowledgment

*   When an agent is assigned a model with a non-empty `warning` field, AND the model ID is NOT in the `acknowledged_warnings` array, the warning text MUST be displayed at: CDD Dashboard (confirmation modal on model selection) and agent launcher (stderr at startup).
*   Warning text is taken verbatim from the model's `warning` field -- no hardcoded messages.
*   **Acknowledgment is automatic** -- no explicit dismiss action or skill command is required from the user. Each surface auto-acknowledges when the user proceeds:
    *   **CDD Dashboard:** When a model with an un-acknowledged warning is selected, a confirmation modal appears with the warning text and "I Understand" / "Cancel" buttons. "I Understand" saves the model selection AND adds the model ID to `acknowledged_warnings`. "Cancel" reverts the dropdown to the previous model. The warning is shown once per model -- after acknowledgment, selecting the same model again does not trigger the modal.
    *   **Launcher:** The warning is printed to stderr on the first launch with that model. The launcher auto-acknowledges by writing the model ID to `acknowledged_warnings` in `config.local.json` before invoking `claude`. Subsequent launches with the same model do not show the warning.
*   When `warning_dismissible` is `false`, the warning is displayed on every access and cannot be auto-acknowledged. The `acknowledged_warnings` array is not modified.
*   Acknowledgment is per-user (stored in gitignored `config.local.json`) and per-model (keyed by model ID).

### 2.3 Launcher Integration
*   Launcher scripts read agent configuration from this schema at startup. Launcher behavior (config reading, CLI dispatch, prompt assembly, tool restrictions) is defined in `agent_launchers_common.md` and the per-role launcher feature specs.
*   Launcher generation by `tools/init.sh` is defined in `project_init.md`.
*   No `.claude/agents/` generation. Agent configuration lives in `config.json`.


## 3. Scenarios

### Automated Scenarios

#### Scenario: Config Schema Validates All Agent Roles
    Given config.json contains agents with keys architect, builder, qa, and pm
    When each agent entry is read
    Then it has model (string), effort (string), and bypass_permissions (boolean) fields
    And the model value references an id from the models array

#### Scenario: Model With Warning Field Triggers Display at Configuration Surfaces
    Given a model entry has a non-empty warning field
    And the model ID is not in the acknowledged_warnings array
    When an agent is assigned that model
    Then the warning text is displayed at the CDD Dashboard (confirmation modal)
    And the warning text is displayed at the agent launcher (stderr at startup)
    And no other configuration surface displays the warning

#### Scenario: Acknowledged Warning is Suppressed on Subsequent Access
    Given a model entry has warning_dismissible true
    And the model ID appears in the acknowledged_warnings array in config.local.json
    When an agent is assigned that model
    Then the warning is not displayed at any configuration surface

#### Scenario: Non-Dismissible Warning Always Displays
    Given a model entry has a warning field and warning_dismissible false
    And the model ID appears in the acknowledged_warnings array
    When an agent is assigned that model
    Then the warning is still displayed at all configuration surfaces
    And the acknowledged_warnings array is not modified

#### Scenario: PM Agent Entry is Optional
    Given config.json contains agents with keys architect, builder, and qa
    And no pm key exists in agents
    When the PM launcher reads config
    Then it falls back to default PM values (model claude-sonnet-4-6, effort medium)

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

