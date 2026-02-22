# Feature: CDD Agent Configuration

> Label: "CDD Dashboard: Agent Configuration"
> Category: "CDD Dashboard"
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/agent_configuration.md


## 1. Overview
The CDD Dashboard exposes agent runtime configuration (provider, model, effort, permissions) via an interactive Agents section in the Status view, and provides API endpoints for persisting changes to `config.json`. This feature depends on the config schema and provider detection tooling defined in `features/agent_configuration.md`.


## 2. Requirements

### 2.1 Dashboard Agents Section

*   **Location:** A new collapsible section below the Workspace section in the Status view.
*   **Visual Separation:** The Agents section MUST be visually separated from the Workspace section above it with a vertical gap matching the spacing used between the Active/Complete feature sections and the Workspace section. This gap MUST be rendered as margin or padding between the two section containers -- not solely by the section heading underline -- so that a visible empty space exists between the bottom of the Workspace box and the top of the Agents section heading. Each section in the Status view -- Active, Complete, Workspace, Agents -- MUST have its own visible boundary so that sections are never visually merged.
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
*   **Pending-Write Lock:** When a user changes a control value, that control is considered "pending" from the moment of user interaction until the `POST /config/agents` response is received. While any control is pending, the auto-refresh cycle MUST NOT overwrite its value with server-returned state — even if the server returns the pre-change value (i.e., the write has not yet landed). Only non-pending controls are updated by auto-refresh during this window. Once the server acknowledges the write (success or error), all pending locks are released and subsequent refreshes resume normal behavior. This prevents the visible bounce: user changes value → refresh reverts it → write lands → it changes again.
*   **Detect Providers Button:** Placed at the bottom-right of the Agents section body (inside the collapsible, below agent rows), right-aligned within the section container. Styled as a secondary button matching the `btn-critic` pattern. Calls `POST /detect-providers`. Displays a confirmation dialog listing detected providers and model counts. "Apply" merges detected providers into `llm_providers` in config (additive -- never removes existing entries).
*   **Styling:** All controls follow existing dashboard patterns:
    *   `<select>`: `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size.
    *   Checkbox: Native with `accent-color: var(--purlin-accent)`.
    *   On focus: `border-color: var(--purlin-accent)`.

### 2.2 Dashboard API Endpoints

*   **`POST /config/agents`:** Accepts a JSON body with the full `agents` object. Validates that model IDs exist in `llm_providers` and effort values are one of `low`/`medium`/`high`. Writes atomically (temp file + rename). Returns updated config on success, 400 on validation failure.
*   **`POST /detect-providers`:** Runs `tools/detect-providers.sh` server-side. Returns the aggregated JSON array from the script output. No config modification (the dashboard "Apply" action calls `POST /config/agents` separately after user confirmation).


## 3. Scenarios

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

#### Scenario: Pending Change is Not Overwritten by Auto-Refresh
    Given the user unchecks "Ask Permission" for the Builder agent
    And the config write is debounced or the POST /config/agents request is in-flight
    When the 5-second auto-refresh fires and returns the pre-change config value
    Then the "Ask Permission" checkbox remains unchecked
    And the control does not visibly revert to checked and then flip back to unchecked

#### Scenario: Agents Section State Persists Across Reloads
    Given the user expands the Agents section
    When the page is reloaded
    Then the Agents section is still expanded
    And the expanded/collapsed state is read from localStorage


## Visual Specification

### Screen: CDD Dashboard -- Agents Section
- **Reference:** N/A
- [ ] Agents section heading ("AGENTS") has a visible underline separator matching Active/Complete/Workspace headings
- [ ] A visible vertical gap separates the bottom of the Workspace box from the top of the Agents section, matching the gap between Active/Complete sections and Workspace
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
- [ ] Changing a control value does not cause it to visibly revert and re-apply while the config write is in-flight
- [ ] Changing a dropdown value does not cause other rows or columns to shift or resize
- [ ] Detect Providers button is right-aligned within the Agents section container
- [ ] Detect Providers button matches `btn-critic` styling pattern
- [ ] Section collapse/expand state persists across page reloads via localStorage


## Implementation Notes

### Agent Row Grid Layout
Uses CSS Grid (`grid-template-columns: 64px 100px 140px 80px auto`) for consistent column alignment across all three agent rows. Hidden capability-gated controls use `visibility: hidden` (not `display: none`) to preserve column space and prevent layout shift.

### Ask Permission Checkbox Semantics
The checkbox is labeled "Ask Permission" (user-facing behavior) and its checked state is the inverse of `bypass_permissions` in config.json. Checked = agent asks before using tools (`bypass_permissions: false`). Unchecked = agent skips permission prompts (`bypass_permissions: true`).

### Pending-Write Lock
Uses a `pendingWrites` Map (key: control identifier like `"builder.bypass_permissions"`, value: the user's pending DOM value). On user interaction, the event handler stores the value via `pendingWrites.set()`. In `diffUpdateAgentRows()`, controls present in the Map are skipped. When `POST /config/agents` resolves (success or error), the Map is cleared.

**[BUG FIX] DOM nuke during refresh:** The 5-second `refreshStatus()` replaces `status-view` innerHTML entirely, destroying agent dropdown DOM (and the user's selection). `initAgentsSection()` then calls `renderAgentsRows()` from cached config, reverting the selection. Using a Map (not a Set) allows `applyPendingWrites()` to restore pending values after any full re-render. This function is called in both the synchronous cache-restore path and the async fetch path of `initAgentsSection()`. Without this, dropdown changes intermittently revert when the refresh cycle fires between user interaction and the config write completing.

### Flicker-Free Refresh
On 5-second auto-refresh, `initAgentsSection()` compares incoming config JSON against the cached `agentsConfig` before deciding whether to re-render. If config is unchanged, rendering is skipped entirely. If changed, `diffUpdateAgentRows()` updates only the controls whose values differ, avoiding full innerHTML replacement.

### Badge Grouping
Both the server-side Python badge (used for initial HTML) and client-side JS badge (used after config changes) use the same algorithm: group model labels by count, sort by count descending then alphabetically, format as `"<count>x <label>"` segments joined by `" | "`.

### Pre-existing _send_json Bug Fix
Fixed a pre-existing bug where `_send_json()` was called without the required `status` argument on the `/status.json` and `/workspace.json` GET routes. The function signature requires `(self, status, data)` but these two call sites were passing only `data`.
