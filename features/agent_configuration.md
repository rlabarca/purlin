# Feature: Agent Configuration

> Label: "Tool: Agent Configuration"
> Category: "Agent Configuration"
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_status_monitor.md


## 1. Overview
Purlin agents (Architect, Builder, QA) are launched via shell scripts that invoke an LLM CLI. This feature makes agent runtime parameters (provider, model, effort, permissions) configurable via `config.json` and the CDD Dashboard, with a provider-agnostic architecture that supports Claude today and is extensible to other LLM providers.


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

*   **Config Reading:** Each launcher script (`run_claude_architect.sh`, `run_claude_builder.sh`, `run_claude_qa.sh`) MUST read agent configuration from `config.json` at startup.
*   **Provider Dispatch:** The launcher MUST dispatch to the correct CLI based on the configured `provider`. Only `claude` is invocable; other providers produce an informative error message.
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

### 2.5 Dashboard Agents Section

*   **Location:** A new collapsible section below the Workspace section in the Status view.
*   **Visual Separation:** The Agents section MUST be visually separated from the Workspace section above it with the same treatment used between all other sections (section heading with underline separator via `border-bottom` on `h3`, consistent with Active/Complete/Workspace separation). Each section in the Status view -- Active, Complete, Workspace, Agents -- MUST have its own visible boundary so that sections are never visually merged.
*   **Default State:** Collapsed by default.
*   **State Persistence:** The Agents section expanded/collapsed state MUST be persisted to the same `localStorage` key used by all other sections (`purlin-section-states`). On page load, the saved state is restored, overriding the collapsed default. Each toggle updates the stored state immediately. This is the same mechanism described in `cdd_status_monitor.md` Section 2.2.2.
*   **Collapsed Badge:** When collapsed, the section heading displays a summary of the configured models, grouped by count and label. Format: `"<count>x <label>"` segments joined by `" | "`. Examples:
    *   All same model: `"3x Sonnet 4.6"`
    *   Two groups: `"1x Opus 4.6 | 2x Sonnet 4.6"`
    *   All different: `"1x Opus 4.6 | 1x Sonnet 4.6 | 1x Haiku 4.5"`
    *   The segments are ordered by count descending, then alphabetically by label.
*   **Section Body:** Three rows, one per agent (Architect, Builder, QA). Each row contains:
    1.  **Agent Name:** Inter 500, 12px, uppercase, `var(--purlin-primary)` color.
    2.  **Provider Dropdown:** Lists keys from `llm_providers`. Changing the provider repopulates the model dropdown with that provider's models.
    3.  **Model Dropdown:** Lists models from the selected provider. Active selection matches config value.
    4.  **Effort Dropdown:** Options: `low`, `medium`, `high`. Visible only when the selected model has `capabilities.effort: true`.
    5.  **Ask Permission Checkbox:** Labeled "Ask Permission". Visible only when the selected model has `capabilities.permissions: true`. Checked = `bypass_permissions: false` (agent will ask before using tools). Unchecked = `bypass_permissions: true` (agent skips permission prompts). The checkbox label describes the user-facing behavior (asking permission), not the internal config key.
*   **Column Alignment:** All agent rows MUST use a consistent grid layout so that the left edges and widths of each control column (Provider, Model, Effort, Ask Permission) are identical across all three rows. Use CSS Grid or fixed-width columns -- not auto-sized flexbox -- to guarantee alignment. When a control is hidden due to capability flags, its column space MUST be preserved (use `visibility: hidden` or an empty placeholder) so that visible controls in adjacent columns do not shift.
*   **Flicker-Free Updates:** When agent configuration is updated (via user interaction or auto-refresh), the Agents section MUST update without visible flicker. The implementation MUST diff incoming state against current DOM values and only update controls whose values have changed. Full section re-renders on every refresh cycle are prohibited. This follows the same stability principle as the feature status tables (Section 2.3 of `cdd_status_monitor.md`).
*   **Detect Providers Button:** Placed at the bottom of the Agents section body (inside the collapsible, below agent rows). Styled as a secondary button matching the `btn-critic` pattern. Calls `POST /detect-providers`. Displays a confirmation dialog listing detected providers and model counts. "Apply" merges detected providers into `llm_providers` in config (additive -- never removes existing entries).
*   **Styling:** All controls follow existing dashboard patterns:
    *   `<select>`: `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size.
    *   Checkbox: Native with `accent-color: var(--purlin-accent)`.
    *   On focus: `border-color: var(--purlin-accent)`.

### 2.6 Dashboard API Endpoints

*   **`POST /config/agents`:** Accepts a JSON body with the full `agents` object. Validates that model IDs exist in `llm_providers` and effort values are one of `low`/`medium`/`high`. Writes atomically (temp file + rename). Returns updated config on success, 400 on validation failure.
*   **`POST /detect-providers`:** Runs `tools/detect-providers.sh` server-side. Returns the aggregated JSON array from the script output. No config modification (the dashboard "Apply" action calls `POST /config/agents` separately after user confirmation).

### 2.7 Bootstrap Generation

*   **Updated Launchers:** `tools/bootstrap.sh` Section 5 (Launcher Script Generation) MUST generate launchers with config-reading, provider dispatch, and role-specific tool restrictions as described in Section 2.4.
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
These scenarios require the running CDD Dashboard server and human interaction to verify.

#### Scenario: Agents Section Displays Current Config
    Given the dashboard is loaded with valid config.json
    When the user expands the Agents section
    Then three rows are displayed for Architect, Builder, and QA
    And each row shows the configured provider, model, effort, and ask-permission state

#### Scenario: Capability-Aware Control Visibility
    Given an agent is configured with a model that has capabilities.effort false
    When the user views that agent's row
    Then the effort dropdown is hidden
    And the bypass checkbox is hidden if capabilities.permissions is also false

#### Scenario: Provider Change Repopulates Models
    Given an agent row has provider "claude" selected
    When the user changes the provider dropdown to "gemini"
    Then the model dropdown repopulates with Gemini models
    And effort/bypass controls update based on the first Gemini model's capabilities

#### Scenario: Config Changes Persist via API
    Given the user changes the Builder model to "claude-opus-4-6"
    When the change is debounced and sent to POST /config/agents
    Then config.json is updated with the new model for builder
    And relaunching the Builder uses the new model

#### Scenario: Detect Providers Workflow
    Given the user clicks "Detect Providers" in the Agents section
    When the server runs tools/detect-providers.sh
    Then a confirmation dialog shows detected providers and model counts
    And clicking "Apply" merges new providers into llm_providers in config.json

#### Scenario: Collapsed Badge Shows Uniform Model Summary
    Given all three agents are configured with the same model "claude-sonnet-4-6"
    When the Agents section is collapsed
    Then the badge displays "3x Sonnet 4.6"

#### Scenario: Collapsed Badge Shows Grouped Model Summary
    Given the Architect uses "claude-opus-4-6" and Builder and QA use "claude-sonnet-4-6"
    When the Agents section is collapsed
    Then the badge displays "2x Sonnet 4.6 | 1x Opus 4.6"

#### Scenario: Agents Section is Visually Separated from Workspace
    Given the dashboard is loaded with valid config.json
    When the Status view is displayed
    Then the Agents section heading has a visible underline separator
    And the Agents section is visually distinct from the Workspace section above it

#### Scenario: Agents Section State Persists Across Reloads
    Given the user expands the Agents section
    When the page is reloaded
    Then the Agents section is still expanded
    And the expanded/collapsed state is read from localStorage


## Visual Specification

### Screen: CDD Dashboard -- Agents Section
- **Reference:** N/A
- [ ] Agents section heading ("AGENTS") has a visible underline separator matching Active/Complete/Workspace headings
- [ ] Agents section is visually separated from Workspace with the same spacing and border treatment as between feature sections and Workspace
- [ ] Agents section has a chevron indicator (right=collapsed, down=expanded)
- [ ] Collapsed state shows grouped model badge (e.g., "3x Sonnet 4.6" or "1x Opus 4.6 | 2x Sonnet 4.6")
- [ ] Agent name labels are Inter 500, 12px, uppercase, using `var(--purlin-primary)` color
- [ ] Provider dropdowns are left-edge aligned across all three agent rows
- [ ] Model dropdowns are left-edge aligned across all three agent rows
- [ ] Effort dropdowns are left-edge aligned across all three agent rows
- [ ] All dropdowns in the same column have identical widths across rows
- [ ] When a control is hidden (capability-gated), its column space is preserved so adjacent controls do not shift
- [ ] Permission checkbox is labeled "Ask Permission" (not "Bypass")
- [ ] "Ask Permission" checkbox is checked when the agent asks before using tools (bypass_permissions=false)
- [ ] Dropdown styling matches existing dashboard selects: `var(--purlin-bg)` bg, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px
- [ ] Checkbox uses `accent-color: var(--purlin-accent)`
- [ ] On 5-second auto-refresh, the Agents section does not flicker or visibly re-render
- [ ] Changing a dropdown value does not cause other rows or columns to shift or resize
- [ ] Detect Providers button matches `btn-critic` styling pattern
- [ ] Section collapse/expand state persists across page reloads via localStorage


## Implementation Notes
See [agent_configuration.impl.md](agent_configuration.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
