# Feature: CDD Agent Configuration

> Label: "CDD Dashboard: Agent Configuration"
> Category: "CDD Dashboard"
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/models_configuration.md


## 1. Overview
The CDD Dashboard exposes agent model configuration (model, effort, permissions) via an interactive Agents section in the Status view, and provides API endpoints for persisting changes to `config.json`. This feature depends on the config schema defined in `features/models_configuration.md`.


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
*   **Section Header Row:** A non-data row at the top of the section body containing column labels for the control columns. Labels for narrow checkbox columns display on two lines to conserve horizontal space (e.g., "YOLO" centered; "Startup" / "Sequence" on two lines). The header row MUST span all control columns and remain visually aligned with the agent data rows below. The `cdd_startup_controls.md` feature appends two additional column headers to this row: **Startup** / **Sequence** and **Suggest** / **Next** (each on two lines).
*   **Section Body:** Three rows, one per agent (Architect, Builder, QA). Each row contains:
    1.  **Agent Name:** Inter 500, 12px, uppercase, `var(--purlin-primary)` color.
    2.  **Model Dropdown:** Lists models from the `models` array in config. Active selection matches config value.
    3.  **Effort Dropdown:** Options: `low`, `medium`, `high`. Visible only when the selected model has `capabilities.effort: true`.
    4.  **YOLO Checkbox:** No inline label (identified solely by the column header). Checked = `bypass_permissions: true` (agent skips permission prompts). Unchecked = `bypass_permissions: false` (agent asks before using tools). Visible only when the selected model has `capabilities.permissions: true`.
*   **Column Alignment:** All agent rows MUST use a consistent grid layout so that the left edges and widths of each control column (Model, Effort, YOLO) are identical across all three rows and aligned with the column header row above. Use CSS Grid or fixed-width columns -- not auto-sized flexbox -- to guarantee alignment. When a control is hidden due to capability flags, its column space MUST be preserved (use `visibility: hidden` or an empty placeholder) so that visible controls in adjacent columns do not shift.
*   **Flicker-Free Updates:** When agent configuration is updated (via user interaction or auto-refresh), the Agents section MUST update without visible flicker. The implementation MUST diff incoming state against current DOM values and only update controls whose values have changed. Full section re-renders on every refresh cycle are prohibited.
*   **Pending-Write Lock:** When a user changes a control value, that control is considered "pending" from the moment of user interaction until the `POST /config/agents` response is received. While any control is pending, the auto-refresh cycle MUST NOT overwrite its value with server-returned state. Only non-pending controls are updated by auto-refresh during this window. Once the server acknowledges the write (success or error), all pending locks are released.
*   **Styling:** All controls follow existing dashboard patterns:
    *   `<select>`: `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size.
    *   Checkbox: Native with `accent-color: var(--purlin-accent)`.
    *   On focus: `border-color: var(--purlin-accent)`.

### 2.2 Dashboard API Endpoints

*   **`POST /config/agents`:** Accepts a JSON body with the full `agents` object. Validates that model IDs exist in the `models` array and effort values are one of `low`/`medium`/`high`. Writes atomically (temp file + rename). Returns updated config on success, 400 on validation failure.


## 3. Scenarios

### Automated Scenarios
None. All scenarios for this feature require the running CDD Dashboard server and human interaction to verify.

### Manual Scenarios (Human Verification Required)
These scenarios require the running CDD Dashboard server and human interaction to verify.

#### Scenario: Agents Section Displays Current Config
    Given the dashboard is loaded with valid config.json
    When the user expands the Agents section
    Then three rows are displayed for Architect, Builder, and QA
    And each row shows the configured model, effort, and YOLO state

#### Scenario: Capability-Aware Control Visibility
    Given an agent is configured with a model that has capabilities.effort false
    When the user views that agent's row
    Then the effort dropdown is hidden
    And the bypass checkbox is hidden if capabilities.permissions is also false

#### Scenario: Config Changes Persist via API
    Given the user changes the Builder model to "claude-opus-4-6"
    When the change is debounced and sent to POST /config/agents
    Then config.json is updated with the new model for builder
    And relaunching the Builder uses the new model

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
    Given the user checks the YOLO control for the Builder agent
    And the config write is debounced or the POST /config/agents request is in-flight
    When the 5-second auto-refresh fires and returns the pre-change config value
    Then the YOLO checkbox remains checked
    And the control does not visibly revert to unchecked and then flip back to checked

#### Scenario: Agents Section State Persists Across Reloads
    Given the user expands the Agents section
    When the page is reloaded
    Then the Agents section is still expanded
    And the expanded/collapsed state is read from localStorage


## Visual Specification

### Screen: CDD Dashboard -- Agent Config Section
- **Reference:** N/A
- [ ] Agents section heading ("Agent Config") has a visible underline separator matching Active/Complete/Workspace headings
- [ ] A visible vertical gap separates the bottom of the Workspace box from the top of the Agents section, matching the gap between Active/Complete sections and Workspace
- [ ] Agents section has a chevron indicator (right=collapsed, down=expanded)
- [ ] Collapsed state shows grouped model badge (e.g., "3x Sonnet 4.6" or "1x Opus 4.6 | 2x Sonnet 4.6")
- [ ] A column header row appears above the agent data rows with a label cell for each control column
- [ ] "YOLO" column header is displayed in a fixed-width cell with text centered; no inline label appears beside the checkbox in agent rows
- [ ] Agent data rows contain no inline labels for any checkbox controls; identification is solely via the column header row
- [ ] Agent name labels are Inter 500, 12px, uppercase, using `var(--purlin-primary)` color
- [ ] Column header row is visually aligned with the control columns in the agent data rows below it
- [ ] Model dropdowns are left-edge aligned across all three agent rows
- [ ] Effort dropdowns are left-edge aligned across all three agent rows
- [ ] All dropdowns in the same column have identical widths across rows
- [ ] When a control is hidden (capability-gated), its column space is preserved so adjacent controls do not shift
- [ ] YOLO checkboxes are center-aligned under the "YOLO" column header
- [ ] Dropdown styling matches existing dashboard selects: `var(--purlin-bg)` bg, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px
- [ ] Checkbox uses `accent-color: var(--purlin-accent)`
- [ ] On 5-second auto-refresh, the Agents section does not flicker or visibly re-render
- [ ] Changing a control value does not cause it to visibly revert and re-apply while the config write is in-flight
- [ ] Changing a dropdown value does not cause other rows or columns to shift or resize
- [ ] Section collapse/expand state persists across page reloads via localStorage


## Implementation Notes

### Agent Row Grid Layout
Uses CSS Grid with a column header row and three agent data rows. The header row contains column label cells; narrow checkbox column headers use two-line text (via `<br>` or CSS line wrapping) to fit within their fixed widths. Suggested column definition: `grid-template-columns: 64px 140px 80px 60px` (agent-name | model | effort | YOLO). Hidden capability-gated controls use `visibility: hidden` (not `display: none`) to preserve column space and prevent layout shift. No inline label appears adjacent to checkboxes in the agent data rows.

### YOLO Checkbox Semantics
The YOLO checkbox has no inline label; it is identified solely by the column header. Its checked state maps directly to `bypass_permissions` in config.json. Checked = agent skips permission prompts (`bypass_permissions: true`). Unchecked = agent asks before using tools (`bypass_permissions: false`).

### Pending-Write Lock
Uses a `pendingWrites` Map (key: control identifier like `"builder.bypass_permissions"`, value: the user's pending DOM value). On user interaction, the event handler stores the value via `pendingWrites.set()`. In `diffUpdateAgentRows()`, controls present in the Map are skipped. When `POST /config/agents` resolves (success or error), the Map is cleared.

### Flicker-Free Refresh
On 5-second auto-refresh, `initAgentsSection()` compares incoming config JSON against the cached `agentsConfig` before deciding whether to re-render. If config is unchanged, rendering is skipped entirely. If changed, `diffUpdateAgentRows()` updates only the controls whose values differ.

### Badge Grouping
Both the server-side Python badge and client-side JS badge use the same algorithm: group model labels by count, sort by count descending then alphabetically, format as `"<count>x <label>"` segments joined by `" | "`.

### DOM Identifiers
All HTML IDs, CSS classes, JS variable names, and localStorage section-name entries for this section use the `agents` prefix (e.g., `agents-section`, `initAgentsSection()`, `agentsConfig`). If a prior implementation pass used `models`-prefixed identifiers, the Builder MUST rename them back. The `purlin-section-states` localStorage key itself is unchanged; only the section name entry within that object changes from `"models"` (if applicable) back to `"agents"`.

### Test Directory
The automated test suite lives at `tests/cdd_agent_configuration/`. If a prior implementation pass renamed this to `tests/cdd_model_configuration/`, rename it back. The `tests.json` file inside should be preserved.
