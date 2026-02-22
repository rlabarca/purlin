# Feature: Agent Configuration

> Label: "Tool: Agent Configuration"
> Category: "Install, Update & Scripts"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 2: Roles and Responsibilities)


## 1. Overview
Purlin agents (Architect, Builder, QA) are launched via shell scripts that invoke an LLM CLI. This feature makes agent runtime parameters (provider, model, effort, permissions) configurable via `config.json`, with a provider-agnostic architecture that supports Claude today and is extensible to other LLM providers.


## 2. Requirements

### 2.1 Config Schema

*   **`llm_providers` Section:** The `config.json` file MUST contain an `llm_providers` object. Each key is a provider identifier (e.g., `"claude"`, `"gemini"`). Each provider contains a `models` array.
*   **Model Object:** Each model entry MUST have:
    *   `id` (string): The model identifier passed to the CLI (e.g., `"claude-sonnet-4-6"`).
    *   `label` (string): Human-readable display name (e.g., `"Sonnet 4.6"`).
    *   `capabilities` (object): Controls which dashboard controls appear for this model.
        *   `effort` (boolean): Whether the effort dropdown is shown.
        *   `permissions` (boolean): Whether the bypass-permissions checkbox is shown.
*   **`agents` Section:** The `config.json` file MUST contain an `agents` object with keys `"architect"`, `"builder"`, and `"qa"`. Each agent entry MUST have:
    *   `provider` (string): Key into `llm_providers` (e.g., `"claude"`).
    *   `model` (string): Model ID from the provider's model list.
    *   `effort` (string): One of `"low"`, `"medium"`, `"high"`. Only meaningful when the model's `capabilities.effort` is `true`.
    *   `bypass_permissions` (boolean): Whether to skip permission prompts. Only meaningful when the model's `capabilities.permissions` is `true`.

### 2.2 Provider Probe Scripts

*   **Directory:** Provider probe scripts live at `tools/providers/<provider>.sh`.
*   **Contract:** Each script MUST output a JSON object to stdout with the following fields:
    *   `provider` (string): The provider identifier.
    *   `available` (boolean): Whether the provider's CLI/API is detected.
    *   `version` (string, optional): Version info if available.
    *   `models` (array): List of model objects with `id`, `label`, and `capabilities`.
    *   `setup_hint` (string): Instructions for setting up the provider.
*   **Exit Code:** Always 0 (even if provider is unavailable). Errors are communicated via `available: false`.
*   **Claude Probe (`tools/providers/claude.sh`):** Checks for the `claude` CLI via `command -v`. Extracts version via `claude --version`. Returns a static model list (the CLI has no model enumeration command).
*   **Gemini Probe (`tools/providers/gemini.sh`):** Checks for `GOOGLE_API_KEY` or `GEMINI_API_KEY` environment variables, and for the `gemini` CLI via `command -v`. Returns a static model list.

### 2.3 Provider Detection Aggregator

*   **Script:** `tools/detect-providers.sh` runs all scripts in `tools/providers/` and outputs a single JSON array to stdout.
*   **Auto-Discovery:** The aggregator MUST glob `tools/providers/*.sh` rather than hardcoding provider names.
*   **Error Isolation:** If a single probe script fails (non-zero exit or invalid JSON), the aggregator MUST skip it and continue with remaining providers. It MUST NOT abort entirely.

### 2.4 Launcher Script Behavior

*   **Config Reading:** Each launcher script (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) MUST read agent configuration from `config.json` at startup.
*   **Provider Dispatch:** The launcher MUST dispatch to the correct CLI based on the configured `provider`. Supported providers are `claude` and `gemini`. Unsupported providers produce a clear error message with setup instructions.
*   **Dynamic CLI Arguments:** For the `claude` provider:
    *   If `model` is set, pass `--model <model>`.
    *   If `effort` is set, pass `--effort <effort>`.
    *   If `bypass_permissions` is `true`, pass `--dangerously-skip-permissions`.
    *   If `bypass_permissions` is `false`, pass role-specific `--allowedTools` flags.
*   **Role-Specific Tool Restrictions** (when `bypass_permissions` is `false`):
    *   **Architect:** `"Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep"`
    *   **Builder:** No `--allowedTools` flag (default permissions, user confirms each tool use).
    *   **QA:** `"Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit"`
*   **Fallback:** If `config.json` is missing or the `agents` section is absent, launchers MUST fall back to current hardcoded behavior (Claude with default model, role-specific permissions).
*   **Session Prompt:** Each role passes its concatenated instruction prompt file and a role-specific opening message.

### 2.5 Bootstrap Generation

*   **Updated Launchers:** `tools/bootstrap.sh` Section 5 (Launcher Script Generation) MUST generate launchers (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) with config-reading, provider dispatch, and role-specific tool restrictions as described in Section 2.4.
*   **No `.claude/agents/` Generation:** Bootstrap MUST NOT generate Claude-specific agent configuration files. Agent configuration is provider-agnostic and lives in `config.json`.


## 3. Scenarios

### Automated Scenarios

#### Scenario: Launcher Reads Agent Config from Config JSON
    Given config.json contains agents.architect with provider "claude" and model "claude-sonnet-4-6"
    And agents.architect has effort "high" and bypass_permissions false
    When the Architect launcher script is executed
    Then it invokes the claude CLI with --model claude-sonnet-4-6 --effort high
    And it passes --allowedTools with the Architect role restrictions

#### Scenario: Launcher Falls Back When Config is Missing
    Given config.json does not contain an agents section
    When the Architect launcher script is executed
    Then it invokes the claude CLI with current hardcoded defaults
    And the Architect role restrictions are applied

#### Scenario: Launcher Handles Unsupported Provider
    Given config.json contains agents.builder with provider "gemini"
    When the Builder launcher script is executed
    Then it prints an error message listing supported providers
    And exits with a non-zero status code

#### Scenario: Claude Probe Detects Installed CLI
    Given the claude CLI is installed and on PATH
    When tools/providers/claude.sh is executed
    Then it outputs JSON with available true
    And the models array contains Claude model entries with capabilities

#### Scenario: Gemini Probe Detects API Key
    Given the GOOGLE_API_KEY environment variable is set
    When tools/providers/gemini.sh is executed
    Then it outputs JSON with available true
    And the models array contains Gemini model entries

#### Scenario: Probe Handles Missing Provider Gracefully
    Given the claude CLI is not installed
    When tools/providers/claude.sh is executed
    Then it outputs JSON with available false
    And exit code is 0

#### Scenario: Aggregator Collects All Providers
    Given probe scripts exist in tools/providers/
    When tools/detect-providers.sh is executed
    Then it outputs a JSON array with one entry per probe script in tools/providers/
    And each entry contains provider, available, and models fields

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.


## Implementation Notes
See [agent_configuration.impl.md](agent_configuration.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
