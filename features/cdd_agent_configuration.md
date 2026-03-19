# Feature: CDD Agent Configuration

> Label: "CDD Agent Configuration"
> Category: "CDD Dashboard"
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/models_configuration.md
> Prerequisite: features/config_layering.md
> Prerequisite: features/test_fixture_repo.md
> Web Test: http://localhost:9086
> Web Start: /pl-cdd


## 1. Overview
The CDD Dashboard exposes agent model configuration (model, effort, permissions) via an interactive Agents section in the Status view, and provides API endpoints for persisting changes to `config.local.json` (the gitignored local config). Reads use the config resolver (local config with shared fallback). This feature depends on the config schema defined in `features/models_configuration.md` and the config layering system defined in `features/config_layering.md`.


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
*   **Section Body:** Four rows, one per agent (PM, Architect, Builder, QA). Each row contains:
    1.  **Agent Name:** Inter 500, 12px, uppercase, `var(--purlin-primary)` color.
    2.  **Model Dropdown:** Lists models from the `models` array in config. Active selection matches config value.
    3.  **Effort Dropdown:** Options: `low`, `medium`, `high`. Visible only when the selected model has `capabilities.effort: true`.
    4.  **YOLO Checkbox:** No inline label (identified solely by the column header). Checked = `bypass_permissions: true` (agent skips permission prompts). Unchecked = `bypass_permissions: false` (agent asks before using tools). Visible only when the selected model has `capabilities.permissions: true`.
*   **Column Alignment:** All agent rows MUST use a consistent grid layout so that the left edges and widths of each control column (Model, Effort, YOLO) are identical across all four rows and aligned with the column header row above. Use CSS Grid or fixed-width columns -- not auto-sized flexbox -- to guarantee alignment. When a control is hidden due to capability flags, its column space MUST be preserved (use `visibility: hidden` or an empty placeholder) so that visible controls in adjacent columns do not shift.
*   **Flicker-Free Updates:** When agent configuration is updated (via user interaction or auto-refresh), the Agents section MUST update without visible flicker. The implementation MUST diff incoming state against current DOM values and only update controls whose values have changed. Full section re-renders on every refresh cycle are prohibited.
*   **Pending-Write Lock:** When a user changes a control value, that control is considered "pending" from the moment of user interaction until a `POST /config/agents` response confirms the change. While a control is pending, ALL incoming state updates -- both auto-refresh AND POST responses -- MUST NOT overwrite its value. Each pending lock is associated with the POST request that carries its change. When a POST response arrives, only pending locks that were included in that specific request are released; controls changed after that POST was sent remain pending. This ensures that rapid sequential edits are not reverted by a stale response from an earlier save.
*   **Styling:** All controls follow existing dashboard patterns:
    *   `<select>`: `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size.
    *   Checkbox: Native with `accent-color: var(--purlin-accent)`.
    *   On focus: `border-color: var(--purlin-accent)`.

### 2.2 Dashboard API Endpoints

*   **`POST /config/agents`:** Accepts a JSON body with the full `agents` object (all four roles: `architect`, `builder`, `qa`, `pm` MUST be present). Validates that model IDs exist in the `models` array and effort values are one of `low`/`medium`/`high`. Writes atomically to `config.local.json` (temp file + rename). Returns updated config on success, 400 on validation failure. The `config.json` (shared/committed) is never modified by this endpoint.
    *   **Completeness check:** The backend MUST reject any request that is missing one or more of the four expected roles (`architect`, `builder`, `qa`, `pm`) with a 400 error: `"agents payload must include all roles: architect, builder, qa, pm"`. Partial saves that silently drop roles are not permitted.
    *   **Merge semantics:** The backend MUST merge incoming role configs into the existing `agents` object in `config.local.json` key-by-key, not replace the entire `agents` object wholesale. Any role present in the existing config but absent from the request MUST be preserved. This prevents a frontend rendering gap (a role's DOM element not being present) from silently erasing that role's saved configuration.
    *   **Frontend contract:** The frontend `saveAgentConfig()` function MUST always include all four roles in the payload before POSTing. If a role's DOM elements are not yet rendered, the save MUST be deferred until all elements are present -- it MUST NOT send a partial payload.
*   **`GET /config.json`:** Serves the resolved config (reads `config.local.json` if present, falls back to `config.json`) via the config resolver. This is transparent to the dashboard frontend.

### 2.3 Web-Verify Fixture Tags

The following fixture tags provide deterministic project states for web-verify testing:

| Tag | State Description |
|-----|-------------------|
| `main/cdd_agent_configuration/mixed-models` | Different models per agent for verifying model badges and capability-gated controls |


## 3. Scenarios

### Automated Scenarios

#### Scenario: Agents Section Displays Four Agent Rows in Spec Order
    Given a valid resolved config with four agents (architect, builder, qa, pm)
    And each agent has a configured model, effort, and bypass_permissions value
    When the dashboard HTML is generated
    Then the Agents section contains four agent rows
    And the rows appear in spec order: PM, Architect, Builder, QA (top to bottom)
    And the architect row displays the configured model in its dropdown
    And the builder row displays the configured effort value
    And the qa row displays the configured bypass_permissions checkbox state

#### Scenario: Capability-Gated Controls Hidden in HTML When Capabilities Are False
    Given the builder agent is configured with a model that has capabilities.effort false and capabilities.permissions false
    When the dashboard HTML is generated
    Then the builder row's effort dropdown is hidden (visibility hidden or absent)
    And the builder row's bypass_permissions checkbox is hidden (visibility hidden or absent)
    And the column space for hidden controls is preserved in the grid layout

#### Scenario: POST /config/agents Persists to config.local.json
    Given a valid resolved config exists
    When a POST request is sent to /config/agents with body {"architect": {"model": "claude-opus-4-6", "effort": "high", "bypass_permissions": true}, "builder": {"model": "claude-opus-4-6", "effort": "high", "bypass_permissions": true}, "qa": {"model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": false}, "pm": {"model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": true}}
    Then config.local.json contains the updated agents values
    And config.json (shared) is unchanged
    And the response contains the updated config

#### Scenario: Collapsed Badge Shows Uniform Model Summary in HTML
    Given all four agents are configured with the same model "claude-sonnet-4-6" (label "Sonnet 4.6")
    When the dashboard HTML is generated
    Then the Agents section collapsed badge contains "4x Sonnet 4.6"

#### Scenario: Collapsed Badge Shows Grouped Model Summary in HTML
    Given the architect uses "claude-opus-4-6" (label "Opus 4.6") and builder, qa, and pm use "claude-sonnet-4-6" (label "Sonnet 4.6")
    When the dashboard HTML is generated
    Then the Agents section collapsed badge contains "3x Sonnet 4.6 | 1x Opus 4.6"

#### Scenario: Agents Section Has Visual Separator in HTML
    Given a valid resolved config exists
    When the dashboard HTML is generated
    Then the Agents section heading element has a separator distinct from the Workspace section above it
    And the Agents section container is a separate DOM element from the Workspace section container

#### Scenario: Agents Section State Persists Across Reloads
    Given the user expands the Agents section
    When the page is reloaded
    Then the Agents section is still expanded
    And the expanded/collapsed state is read from localStorage

### Manual Scenarios (Human Verification Required)

#### Scenario: Pending Change is Not Overwritten by Concurrent State Updates
    Given the user changes the architect threshold to 50
    And a POST /config/agents request is in-flight for that change
    And the user then changes the builder threshold to 30 before the POST response arrives
    When the first POST response arrives with stale builder config
    Then the architect threshold lock is released and shows the confirmed value
    And the builder threshold remains 30 (still pending, not overwritten)
    And the 5-second auto-refresh also does not overwrite the pending builder value


## Visual Specification

### Screen: CDD Dashboard -- Agent Config Section
- **Reference:** N/A
- [ ] Agents section heading ("Agent Config") has a visible underline separator matching Active/Complete/Workspace headings
- [ ] A visible vertical gap of at least 16px (matching the gap between Active/Complete sections and the Workspace box) separates the bottom of the Workspace box from the top of the Agents section
- [ ] Agents section has a chevron indicator (right=collapsed, down=expanded)
- [ ] Collapsed state shows grouped model badge (e.g., "3x Sonnet 4.6" or "1x Opus 4.6 | 2x Sonnet 4.6")
- [ ] A column header row appears above the agent data rows with a label cell for each control column
- [ ] "YOLO" column header is displayed in a fixed-width cell with text centered; no inline label appears beside the checkbox in agent rows
- [ ] Agent data rows contain no inline labels for any checkbox controls; identification is solely via the column header row
- [ ] Agent name labels are Inter 500, 12px, uppercase, using `var(--purlin-primary)` color
- [ ] Column header row is visually aligned with the control columns in the agent data rows below it
- [ ] Model dropdowns are left-edge aligned across all four agent rows
- [ ] Effort dropdowns are left-edge aligned across all four agent rows
- [ ] All dropdowns in the same column have identical widths across rows
- [ ] When a control is hidden (capability-gated), its column space is preserved so adjacent controls do not shift
- [ ] YOLO checkboxes are center-aligned under the "YOLO" column header
- [ ] Dropdown styling matches existing dashboard selects: `var(--purlin-bg)` bg, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px
- [ ] Checkbox uses `accent-color: var(--purlin-accent)`
- [ ] On 5-second auto-refresh, the Agents section does not flicker or visibly re-render
- [ ] Changing a control value does not cause it to visibly revert and re-apply while the config write is in-flight
- [ ] Changing a dropdown value does not cause other rows or columns to shift or resize
- [ ] Section collapse/expand state persists across page reloads via localStorage


## Regression Guidance
- Pending-write lock: rapid sequential edits not reverted by stale POST response
- Capability-gated controls: hidden controls preserve column space (no layout shift)
- Flicker-free updates: only changed controls re-rendered on auto-refresh
- Section collapse state persists in localStorage alongside other sections
- Config writes go to config.local.json (gitignored), not config.json
