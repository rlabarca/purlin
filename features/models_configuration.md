# Feature: Model Configuration

> Label: "Tool: Model Configuration"
> Category: "Install, Update & Scripts"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 2: Roles and Responsibilities)


## 1. Overview
Purlin agents (Architect, Builder, QA) are launched via shell scripts that invoke the Claude CLI. This feature makes agent runtime parameters (model, effort, permissions) configurable via `config.json`. Claude is the sole supported LLM provider.


## 2. Requirements

### 2.1 Config Schema

*   **`models` Array:** The `config.json` file MUST contain a `models` array at the top level. Each entry defines a Claude model available for assignment to agents.
*   **Model Object:** Each model entry MUST have:
    *   `id` (string): The model identifier passed to the CLI (e.g., `"claude-sonnet-4-6"`).
    *   `label` (string): Human-readable display name (e.g., `"Sonnet 4.6"`).
    *   `capabilities` (object): Controls which dashboard controls appear for this model.
        *   `effort` (boolean): Whether the effort dropdown is shown.
        *   `permissions` (boolean): Whether the bypass-permissions checkbox is shown.
*   **`agents` Section:** The `config.json` file MUST contain an `agents` object with keys `"architect"`, `"builder"`, and `"qa"`. Each agent entry MUST have:
    *   `model` (string): Model ID from the `models` array.
    *   `effort` (string): One of `"low"`, `"medium"`, `"high"`. Only meaningful when the model's `capabilities.effort` is `true`.
    *   `bypass_permissions` (boolean): Whether to skip permission prompts. Only meaningful when the model's `capabilities.permissions` is `true`.
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
        "architect": { "model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true },
        "builder":   { "model": "claude-opus-4-6",   "effort": "high", "bypass_permissions": true },
        "qa":        { "model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": true }
    }
}
```

### 2.2 Launcher Script Behavior

*   **Config Reading:** Each launcher script (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) MUST read agent configuration from `config.json` at startup.
*   **Claude Only:** All launchers dispatch exclusively to the Claude CLI. No provider field exists in config; Claude is implicit.
*   **Dynamic CLI Arguments:**
    *   If `model` is set, pass `--model <model>`.
    *   If `effort` is set, pass `--effort <effort>`.
    *   If `bypass_permissions` is `true`, pass `--dangerously-skip-permissions`.
    *   If `bypass_permissions` is `false`, pass role-specific `--allowedTools` flags.
*   **Role-Specific Tool Restrictions** (when `bypass_permissions` is `false`):
    *   **Architect:** `"Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep"`
    *   **Builder:** No `--allowedTools` flag (default permissions, user confirms each tool use).
    *   **QA:** `"Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit"`
*   **Fallback:** If `config.json` is missing or the `agents` section is absent, launchers MUST fall back to hardcoded defaults (Claude with default model, role-specific permissions).
*   **Session Prompt:** Each role passes its concatenated instruction prompt file and a role-specific opening message.

### 2.3 Bootstrap Generation

*   **Updated Launchers:** `tools/bootstrap.sh` Section 5 (Launcher Script Generation) MUST generate launchers (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) with config-reading, Claude dispatch, and role-specific tool restrictions as described in Section 2.2.
*   **No `.claude/agents/` Generation:** Bootstrap MUST NOT generate Claude-specific agent configuration files. Agent configuration is in `config.json`.


## 3. Scenarios

### Automated Scenarios

#### Scenario: Launcher Reads Agent Config from Config JSON
    Given config.json contains agents.architect with model "claude-sonnet-4-6"
    And agents.architect has effort "high" and bypass_permissions false
    When the Architect launcher script is executed
    Then it invokes the claude CLI with --model claude-sonnet-4-6 --effort high
    And it passes --allowedTools with the Architect role restrictions

#### Scenario: Launcher Falls Back When Config is Missing
    Given config.json does not contain an agents section
    When the Architect launcher script is executed
    Then it invokes the claude CLI with current hardcoded defaults
    And the Architect role restrictions are applied

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.


## Implementation Notes
See [models_configuration.impl.md](models_configuration.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
