# Feature: CDD Model Configuration

> Label: "CDD Dashboard: Model Configuration"
> Category: "CDD Dashboard"
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/models_configuration.md


## 1. Overview
The CDD Dashboard exposes agent model configuration (model, effort, permissions) via an interactive Models section in the Status view, and provides API endpoints for persisting changes to `config.json`. This feature depends on the config schema defined in `features/models_configuration.md`.


## 2. Requirements

### 2.1 Dashboard Models Section

*   **Location:** A new collapsible section below the Workspace section in the Status view.
*   **Visual Separation:** The Models section MUST be visually separated from the Workspace section above it with a vertical gap matching the spacing used between the Active/Complete feature sections and the Workspace section. This gap MUST be rendered as margin or padding between the two section containers -- not solely by the section heading underline -- so that a visible empty space exists between the bottom of the Workspace box and the top of the Models section heading. Each section in the Status view -- Active, Complete, Workspace, Models -- MUST have its own visible boundary so that sections are never visually merged.
*   **Default State:** Collapsed by default.
*   **State Persistence:** The Models section expanded/collapsed state MUST be persisted to the same `localStorage` key used by all other sections (`purlin-section-states`). On page load, the saved state is restored, overriding the collapsed default. Each toggle updates the stored state immediately. This is the same mechanism described in `cdd_status_monitor.md` Section 2.2.2.
*   **Collapsed Badge:** When collapsed, the section heading displays a summary of the configured models, grouped by count and label. Format: `"<count>x <label>"` segments joined by `" | "`. Examples:
    *   All same model: `"3x Sonnet 4.6"`
    *   Two groups: `"1x Opus 4.6 | 2x Sonnet 4.6"`
    *   All different: `"1x Opus 4.6 | 1x Sonnet 4.6 | 1x Haiku 4.5"`
    *   The segments are ordered by count descending, then alphabetically by label.
*   **Section Body:** Three rows, one per agent (Architect, Builder, QA). Each row contains:
    1.  **Agent Name:** Inter 500, 12px, uppercase, `var(--purlin-primary)` color.
    2.  **Model Dropdown:** Lists models from the `models` array in config. Active selection matches config value.
    3.  **Effort Dropdown:** Options: `low`, `medium`, `high`. Visible only when the selected model has `capabilities.effort: true`.
    4.  **YOLO Checkbox:** Labeled "YOLO". Visible only when the selected model has `capabilities.permissions: true`. Checked = `bypass_permissions: true` (agent skips permission prompts). Unchecked = `bypass_permissions: false` (agent asks before using tools).
*   **Column Alignment:** All agent rows MUST use a consistent grid layout so that the left edges and widths of each control column (Model, Effort, YOLO) are identical across all three rows. Use CSS Grid or fixed-width columns -- not auto-sized flexbox -- to guarantee alignment. When a control is hidden due to capability flags, its column space MUST be preserved (use `visibility: hidden` or an empty placeholder) so that visible controls in adjacent columns do not shift.
*   **Flicker-Free Updates:** When model configuration is updated (via user interaction or auto-refresh), the Models section MUST update without visible flicker. The implementation MUST diff incoming state against current DOM values and only update controls whose values have changed. Full section re-renders on every refresh cycle are prohibited.
*   **Pending-Write Lock:** When a user changes a control value, that control is considered "pending" from the moment of user interaction until the `POST /config/models` response is received. While any control is pending, the auto-refresh cycle MUST NOT overwrite its value with server-returned state. Only non-pending controls are updated by auto-refresh during this window. Once the server acknowledges the write (success or error), all pending locks are released.
*   **Styling:** All controls follow existing dashboard patterns:
    *   `<select>`: `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size.
    *   Checkbox: Native with `accent-color: var(--purlin-accent)`.
    *   On focus: `border-color: var(--purlin-accent)`.

### 2.2 Dashboard API Endpoints

*   **`POST /config/models`:** Accepts a JSON body with the full `agents` object. Validates that model IDs exist in the `models` array and effort values are one of `low`/`medium`/`high`. Writes atomically (temp file + rename). Returns updated config on success, 400 on validation failure.


## 3. Scenarios

### Automated Scenarios
None. All scenarios for this feature require the running CDD Dashboard server and human interaction to verify.

### Manual Scenarios (Human Verification Required)
These scenarios require the running CDD Dashboard server and human interaction to verify.

#### Scenario: Models Section Displays Current Config
    Given the dashboard is loaded with valid config.json
    When the user expands the Models section
    Then three rows are displayed for Architect, Builder, and QA
    And each row shows the configured model, effort, and YOLO state

#### Scenario: Capability-Aware Control Visibility
    Given an agent is configured with a model that has capabilities.effort false
    When the user views that agent's row
    Then the effort dropdown is hidden
    And the bypass checkbox is hidden if capabilities.permissions is also false

#### Scenario: Config Changes Persist via API
    Given the user changes the Builder model to "claude-opus-4-6"
    When the change is debounced and sent to POST /config/models
    Then config.json is updated with the new model for builder
    And relaunching the Builder uses the new model

#### Scenario: Collapsed Badge Shows Uniform Model Summary
    Given all three agents are configured with the same model "claude-sonnet-4-6"
    When the Models section is collapsed
    Then the badge displays "3x Sonnet 4.6"

#### Scenario: Collapsed Badge Shows Grouped Model Summary
    Given the Architect uses "claude-opus-4-6" and Builder and QA use "claude-sonnet-4-6"
    When the Models section is collapsed
    Then the badge displays "2x Sonnet 4.6 | 1x Opus 4.6"

#### Scenario: Models Section is Visually Separated from Workspace
    Given the dashboard is loaded with valid config.json
    When the Status view is displayed
    Then the Models section heading has a visible underline separator
    And the Models section is visually distinct from the Workspace section above it

#### Scenario: Pending Change is Not Overwritten by Auto-Refresh
    Given the user checks "YOLO" for the Builder agent
    And the config write is debounced or the POST /config/models request is in-flight
    When the 5-second auto-refresh fires and returns the pre-change config value
    Then the "YOLO" checkbox remains checked
    And the control does not visibly revert to unchecked and then flip back to checked

#### Scenario: Models Section State Persists Across Reloads
    Given the user expands the Models section
    When the page is reloaded
    Then the Models section is still expanded
    And the expanded/collapsed state is read from localStorage


## Visual Specification

### Screen: CDD Dashboard -- Models Section
- **Reference:** N/A
- [ ] Models section heading ("MODELS") has a visible underline separator matching Active/Complete/Workspace headings
- [ ] A visible vertical gap separates the bottom of the Workspace box from the top of the Models section, matching the gap between Active/Complete sections and Workspace
- [ ] Models section has a chevron indicator (right=collapsed, down=expanded)
- [ ] Collapsed state shows grouped model badge (e.g., "3x Sonnet 4.6" or "1x Opus 4.6 | 2x Sonnet 4.6")
- [ ] Agent name labels are Inter 500, 12px, uppercase, using `var(--purlin-primary)` color
- [ ] Model dropdowns are left-edge aligned across all three agent rows
- [ ] Effort dropdowns are left-edge aligned across all three agent rows
- [ ] All dropdowns in the same column have identical widths across rows
- [ ] When a control is hidden (capability-gated), its column space is preserved so adjacent controls do not shift
- [ ] Permission checkbox is labeled "YOLO"
- [ ] "YOLO" checkbox is checked when the agent skips permission prompts (bypass_permissions=true)
- [ ] Dropdown styling matches existing dashboard selects: `var(--purlin-bg)` bg, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px
- [ ] Checkbox uses `accent-color: var(--purlin-accent)`
- [ ] On 5-second auto-refresh, the Models section does not flicker or visibly re-render
- [ ] Changing a control value does not cause it to visibly revert and re-apply while the config write is in-flight
- [ ] Changing a dropdown value does not cause other rows or columns to shift or resize
- [ ] Section collapse/expand state persists across page reloads via localStorage


## Implementation Notes

### Model Row Grid Layout
Uses CSS Grid with three control columns: Model, Effort, YOLO. Suggested column definition: `grid-template-columns: 64px 140px 80px auto` (agent-name | model | effort | yolo). The provider column from the previous design is removed. Hidden capability-gated controls use `visibility: hidden` (not `display: none`) to preserve column space and prevent layout shift.

### YOLO Checkbox Semantics
The checkbox is labeled "YOLO" and its checked state maps directly to `bypass_permissions` in config.json. Checked = agent skips permission prompts (`bypass_permissions: true`). Unchecked = agent asks before using tools (`bypass_permissions: false`).

### Pending-Write Lock
Uses a `pendingWrites` Map (key: control identifier like `"builder.bypass_permissions"`, value: the user's pending DOM value). On user interaction, the event handler stores the value via `pendingWrites.set()`. In `diffUpdateModelRows()`, controls present in the Map are skipped. When `POST /config/models` resolves (success or error), the Map is cleared.

### Flicker-Free Refresh
On 5-second auto-refresh, `initModelsSection()` compares incoming config JSON against the cached `modelsConfig` before deciding whether to re-render. If config is unchanged, rendering is skipped entirely. If changed, `diffUpdateModelRows()` updates only the controls whose values differ.

### Badge Grouping
Both the server-side Python badge and client-side JS badge use the same algorithm: group model labels by count, sort by count descending then alphabetically, format as `"<count>x <label>"` segments joined by `" | "`.

### API Endpoint Rename
The config write endpoint is renamed from `POST /config/agents` to `POST /config/models`. The Builder MUST update both the server route and all client-side `fetch` calls accordingly.

### Section and DOM Identifier Rename
All HTML IDs, CSS classes, JS variable names, and localStorage keys that previously used "agents" for this section MUST be renamed to "models". The Builder MUST audit the dashboard source for any `agents`-prefixed identifiers in this context and rename them systematically. The `purlin-section-states` localStorage key itself is unchanged; only the section name entry within that object changes from `"agents"` to `"models"`.

### Test Directory Rename
`tests/cdd_agent_configuration/` MUST be renamed to `tests/cdd_model_configuration/` to match the new feature name. The `tests.json` file inside should be preserved.
