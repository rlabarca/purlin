# Feature: Model Configuration

> Label: "Tool: Model Configuration"
> Category: "Install, Update & Scripts"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 2: Roles and Responsibilities)


## 1. Overview
Purlin agents (Architect, Builder, QA, PM) are launched via shell scripts that invoke the Claude CLI. This feature makes agent runtime parameters (model, effort, permissions) configurable via `config.json`. Claude is the sole supported LLM provider.


## 2. Requirements

### 2.1 Config Schema

*   **`models` Array:** The `config.json` file MUST contain a `models` array at the top level. Each entry defines a Claude model available for assignment to agents.
*   **Model Object:** Each model entry MUST have:
    *   `id` (string): The model identifier passed to the CLI (e.g., `"claude-sonnet-4-6"`).
    *   `label` (string): Human-readable display name (e.g., `"Sonnet 4.6"`).
    *   `capabilities` (object): Controls which dashboard controls appear for this model.
        *   `effort` (boolean): Whether the effort dropdown is shown.
        *   `permissions` (boolean): Whether the bypass-permissions checkbox is shown.
*   **`agents` Section:** The `config.json` file MUST contain an `agents` object with keys `"architect"`, `"builder"`, `"qa"`, and optionally `"pm"`. Each agent entry MUST have:
    *   `model` (string): Model ID from the `models` array.
    *   `effort` (string): One of `"low"`, `"medium"`, `"high"`. Only meaningful when the model's `capabilities.effort` is `true`.
    *   `bypass_permissions` (boolean): Whether to skip permission prompts. Only meaningful when the model's `capabilities.permissions` is `true`.
    *   `find_work` (boolean, optional): Whether the agent runs its startup work-finding protocol. Default `true`. See `agent_launchers_common.md` Section 2.3.
    *   `auto_start` (boolean, optional): Whether the agent begins executing its work plan without waiting for user approval. Default `false`. See `agent_launchers_common.md` Section 2.3.
*   **Canonical Schema:** The following structure is the reference for both `config.json` and `purlin-config-sample/config.json`. The Builder MUST update both files to match, removing the former `llm_providers` wrapper and any `provider` fields from `agents.*` entries:

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

### 2.2 Launcher Integration
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

#### Scenario: PM Agent Entry is Optional
    Given config.json contains agents with keys architect, builder, and qa
    And no pm key exists in agents
    When the PM launcher reads config
    Then it falls back to default PM values (model claude-sonnet-4-6, effort medium)

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

