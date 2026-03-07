# Feature: CDD Agent Configuration

> Label: "CDD Agent Configuration"
> Category: "CDD Dashboard"
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/models_configuration.md
> Prerequisite: features/config_layering.md
> Prerequisite: features/context_guard.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
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
*   **Section Header Row:** A non-data row at the top of the section body containing column labels for the control columns. Labels for narrow checkbox columns display on two lines to conserve horizontal space (e.g., "YOLO" centered; "Startup" / "Sequence" on two lines). The header row MUST span all control columns and remain visually aligned with the agent data rows below. The `cdd_startup_controls.md` feature appends two additional column headers to this row: **Startup** / **Sequence** and **Suggest** / **Next** (each on two lines). This feature adds a **Context** / **Guard** column header (two lines, matching the two-line pattern).
*   **Section Body:** Three rows, one per agent (Architect, Builder, QA). Each row contains:
    1.  **Agent Name:** Inter 500, 12px, uppercase, `var(--purlin-primary)` color.
    2.  **Model Dropdown:** Lists models from the `models` array in config. Active selection matches config value.
    3.  **Effort Dropdown:** Options: `low`, `medium`, `high`. Visible only when the selected model has `capabilities.effort: true`.
    4.  **YOLO Checkbox:** No inline label (identified solely by the column header). Checked = `bypass_permissions: true` (agent skips permission prompts). Unchecked = `bypass_permissions: false` (agent asks before using tools). Visible only when the selected model has `capabilities.permissions: true`.
    5.  **Context Guard (compound cell):** A checkbox and number input arranged horizontally (`display: flex`, `gap: 4px`).
        *   **Checkbox:** Toggles `context_guard` on/off for the agent. No inline label (column header identifies it). Defaults to checked.
        *   **Number input:** `type="number"`, `min="5"`, `max="200"`, ~40px wide, with stepper arrows for up/down. Represents `context_guard_threshold` for the agent. Defaults to the global `context_guard_threshold` value, then 45.
        *   **Disabled state:** When the checkbox is unchecked, the number input is `disabled` with `opacity: 0.4`. The threshold value remains visible but is not editable.
        *   **Styling:** Matches dashboard conventions — `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size. Checkbox uses `accent-color: var(--purlin-accent)`. Focus state: `border-color: var(--purlin-accent)`. **Stepper arrows:** The number input's up/down spinner buttons MUST use `color: var(--purlin-muted)` via `::-webkit-inner-spin-button` styling (and equivalent for other engines) so arrows are visible against dark backgrounds.
        *   **Live Counter Display:** To the right of the threshold number input, a `<span>` displays the current turn counts of all running agents of that role.
            *   **Zero agents running:** Empty (no text shown).
            *   **One agent running:** Plain count (e.g., `12`).
            *   **Multiple agents running:** Counts joined by `|` with no spaces (e.g., `3|22|35`), sorted ascending.
            *   Includes agents running in isolated team worktrees, grouped by role regardless of origin.
            *   **Styling:** `font-family: monospace`, `var(--purlin-muted)` color, 10px font size, ~6px left margin from the threshold input.
            *   **Refresh:** Updated on each 5-second auto-refresh cycle via `GET /context-guard/counters`. The counter span is read-only — no pending-write locks apply.
*   **Column Alignment:** All agent rows MUST use a consistent grid layout so that the left edges and widths of each control column (Model, Effort, YOLO) are identical across all three rows and aligned with the column header row above. Use CSS Grid or fixed-width columns -- not auto-sized flexbox -- to guarantee alignment. When a control is hidden due to capability flags, its column space MUST be preserved (use `visibility: hidden` or an empty placeholder) so that visible controls in adjacent columns do not shift.
*   **Flicker-Free Updates:** When agent configuration is updated (via user interaction or auto-refresh), the Agents section MUST update without visible flicker. The implementation MUST diff incoming state against current DOM values and only update controls whose values have changed. Full section re-renders on every refresh cycle are prohibited.
*   **Pending-Write Lock:** When a user changes a control value, that control is considered "pending" from the moment of user interaction until a `POST /config/agents` response confirms the change. While a control is pending, ALL incoming state updates -- both auto-refresh AND POST responses -- MUST NOT overwrite its value. Each pending lock is associated with the POST request that carries its change. When a POST response arrives, only pending locks that were included in that specific request are released; controls changed after that POST was sent remain pending. This ensures that rapid sequential edits are not reverted by a stale response from an earlier save.
*   **Styling:** All controls follow existing dashboard patterns:
    *   `<select>`: `var(--purlin-bg)` background, `var(--purlin-border)` border, `var(--purlin-muted)` text, 11px font size.
    *   Checkbox: Native with `accent-color: var(--purlin-accent)`.
    *   On focus: `border-color: var(--purlin-accent)`.

### 2.2 Dashboard API Endpoints

*   **`POST /config/agents`:** Accepts a JSON body with the full `agents` object (all three roles: `architect`, `builder`, `qa` MUST be present). Validates that model IDs exist in the `models` array, effort values are one of `low`/`medium`/`high`, `context_guard` is boolean if present, and `context_guard_threshold` is an integer in the range 5-200 if present. Both `context_guard` and `context_guard_threshold` are optional — when absent, the existing value is preserved via merge semantics. Writes atomically to `config.local.json` (temp file + rename). Returns updated config on success, 400 on validation failure. The `config.json` (shared/committed) is never modified by this endpoint.
    *   **Completeness check:** The backend MUST reject any request that is missing one or more of the three expected roles (`architect`, `builder`, `qa`) with a 400 error: `"agents payload must include all three roles: architect, builder, qa"`. Partial saves that silently drop roles are not permitted.
    *   **Merge semantics:** The backend MUST merge incoming role configs into the existing `agents` object in `config.local.json` key-by-key, not replace the entire `agents` object wholesale. Any role present in the existing config but absent from the request MUST be preserved. This prevents a frontend rendering gap (a role's DOM element not being present) from silently erasing that role's saved configuration.
    *   **Worktree propagation:** When active worktrees exist, the endpoint MUST also propagate agent changes to `config.local.json` in each worktree's `.purlin/` directory.
    *   **Frontend contract:** The frontend `saveAgentConfig()` function MUST always include all three roles in the payload before POSTing. If a role's DOM elements are not yet rendered, the save MUST be deferred until all elements are present -- it MUST NOT send a partial payload.
*   **`GET /config.json`:** Serves the resolved config (reads `config.local.json` if present, falls back to `config.json`) via the config resolver. This is transparent to the dashboard frontend.

### 2.3 Live Counter Endpoint

*   **`GET /context-guard/counters`:** Returns a JSON object mapping each role to an array of active turn counts for currently running agents.
*   **Scan Locations:**
    1.  `<PROJECT_ROOT>/.purlin/runtime/` — main project directory.
    2.  `<PROJECT_ROOT>/.worktrees/<name>/.purlin/runtime/` — each active worktree directory (detected via `get_isolation_worktrees()`).
*   **File Matching:** Counter files use the per-session format `turn_count_<PID>_<SESSION_HASH>` (see `context_guard.md` Section 2.3). For each file, extract the PID from the middle segment (between `turn_count_` and the second underscore). Read the corresponding `session_meta_<PID>` to determine the role (second line of the three-line format defined in `context_guard.md` Section 2.8). If no `session_meta` file exists for a given PID, that counter is excluded. When multiple counter files exist for the same PID (multiple sessions), report the **highest count** among them (the active session has the highest count; old sessions have stale lower counts).
*   **Liveness Check:** Only include counters whose PID suffix corresponds to a currently running process (Python `os.kill(pid, 0)` succeeds). Dead-process files are excluded from the response but NOT deleted by the server — cleanup is the hook's responsibility per `context_guard.md` Section 2.8.
*   **Response Format:**
    ```json
    {
      "architect": [5, 12],
      "builder": [3, 22, 35],
      "qa": []
    }
    ```
    Arrays are sorted ascending. Empty arrays indicate no running agents for that role.


### 2.4 Collapsed Context Guard Summary

*   **Visibility:** When the Agent Config section is **collapsed**, an inline context guard summary is displayed between the "Agent Config" heading text and the existing model-count badge (right side).
*   **Position:** The summary is a **separate element**, left-justified immediately after the heading text, before the model badge. The existing model-count badge (e.g., "2x Opus 4.6 | 1x Sonnet 4.6") remains unchanged in position, content, and styling on the right side.
*   **Format:** `(<role>: <counts>, <role>: <counts>, ...)` where counts use the same `value|value` pipe-separated format as the expanded live counter display (Section 2.1).
*   **Role Filtering:** Only include roles that have at least one active agent process (from `GET /context-guard/counters`). If no agents are running across any role, show nothing (empty — no parentheses).
*   **Role Order:** Architect, Builder, QA (fixed order when present).
*   **Text Styling:** Agent role names use `var(--purlin-primary)` color. Count values are individually colored using the threshold zones defined in Section 2.5. Counts use `font-family: monospace`, 10px font size, matching the expanded counter styling.
*   **Show/Hide:** The summary is visible only when the section is collapsed. When expanded, the summary is hidden (same show/hide behavior as the existing model badge).
*   **Refresh:** Updated on the same 5-second auto-refresh cycle as the expanded counters via `GET /context-guard/counters`.

### 2.5 Counter Color Thresholds

Individual count values in **both** the collapsed summary (Section 2.4) and the expanded per-agent counter span (Section 2.1) are colored based on proximity to the agent's configured threshold:

| Zone | Condition | Color Token |
|------|-----------|-------------|
| Normal | count < 80% of threshold | `--purlin-muted` (existing default) |
| Warning | count >= 80% of threshold | `--purlin-status-warning` |
| Critical | count >= 92% of threshold | `--purlin-status-error` |

*   **Per-value coloring:** Each individual count value is colored independently based on its agent's configured threshold. In a pipe-separated display (e.g., `3|22|35`), each number may have a different color.
*   **Threshold source:** The threshold for each agent is sourced from the already-loaded `agentsConfig` — per-agent `context_guard_threshold`, falling back to global `context_guard_threshold`, then hardcoded `45`.
*   **Disabled guard:** When `context_guard` is `false` for an agent, counts still display but always use `--purlin-muted` color (no threshold coloring applies).
*   **Boundary math:** Warning triggers at `count >= threshold * 0.80`. Critical triggers at `count >= threshold * 0.92`. Matches the shell hook zones defined in `context_guard.md` Section 2.4.1.

### 2.5 Web-Verify Fixture Tags

The following fixture tags provide deterministic project states for web-verify testing:

| Tag | State Description |
|-----|-------------------|
| `main/cdd_agent_configuration/mixed-models` | Different models per agent for verifying model badges and capability-gated controls |


## 3. Scenarios

### Automated Scenarios

#### Scenario: Agents Section Displays Three Agent Rows in HTML
    Given a valid resolved config with three agents (architect, builder, qa)
    And each agent has a configured model, effort, and bypass_permissions value
    When the dashboard HTML is generated
    Then the Agents section contains three agent rows
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
    When a POST request is sent to /config/agents with body {"architect": {"model": "claude-opus-4-6", "effort": "high", "bypass_permissions": true}, "builder": {"model": "claude-opus-4-6", "effort": "high", "bypass_permissions": true}, "qa": {"model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": false}}
    Then config.local.json contains the updated agents values
    And config.json (shared) is unchanged
    And the response contains the updated config

#### Scenario: Collapsed Badge Shows Uniform Model Summary in HTML
    Given all three agents are configured with the same model "claude-sonnet-4-6" (label "Sonnet 4.6")
    When the dashboard HTML is generated
    Then the Agents section collapsed badge contains "3x Sonnet 4.6"

#### Scenario: Collapsed Badge Shows Grouped Model Summary in HTML
    Given the architect uses "claude-opus-4-6" (label "Opus 4.6") and builder and qa use "claude-sonnet-4-6" (label "Sonnet 4.6")
    When the dashboard HTML is generated
    Then the Agents section collapsed badge contains "2x Sonnet 4.6 | 1x Opus 4.6"

#### Scenario: Agents Section Has Visual Separator in HTML
    Given a valid resolved config exists
    When the dashboard HTML is generated
    Then the Agents section heading element has a separator distinct from the Workspace section above it
    And the Agents section container is a separate DOM element from the Workspace section container

#### Scenario: Context Guard Controls Render with Correct State
    Given the architect agent has context_guard true and context_guard_threshold 60 in config
    When the dashboard HTML is generated
    Then the architect row's Context Guard checkbox is checked
    And the architect row's Context Guard threshold input shows "60"
    And the threshold input is enabled

#### Scenario: Threshold Input Disabled When Guard Unchecked
    Given the builder agent has context_guard false and context_guard_threshold 30 in config
    When the dashboard HTML is generated
    Then the builder row's Context Guard checkbox is unchecked
    And the builder row's Context Guard threshold input shows "30"
    And the threshold input is disabled with opacity 0.4

#### Scenario: POST Validates Context Guard Threshold Range
    Given a valid resolved config exists
    When a POST request is sent to /config/agents with builder context_guard_threshold set to 300
    Then the response status is 400
    And the response contains a validation error for threshold range

#### Scenario: POST Accepts Valid Context Guard Settings
    Given a valid resolved config exists
    When a POST request is sent to /config/agents with architect context_guard true and context_guard_threshold 30
    Then config.local.json contains agents.architect.context_guard as true
    And config.local.json contains agents.architect.context_guard_threshold as 30

#### Scenario: GET /context-guard/counters returns per-role arrays
    Given turn_count_100_abc123 exists in .purlin/runtime/ with value "5"
    And session_meta_100 exists with role "architect" on line 2
    And turn_count_200_def456 exists in .purlin/runtime/ with value "12"
    And session_meta_200 exists with role "builder" on line 2
    And turn_count_300_ghi789 exists in .purlin/runtime/ with value "3"
    And session_meta_300 exists with role "builder" on line 2
    And processes 100, 200, and 300 are alive
    When a GET request is sent to /context-guard/counters
    Then the response contains {"architect": [5], "builder": [3, 12], "qa": []}

#### Scenario: Multiple session files for same PID reports highest count
    Given turn_count_100_abc123 exists in .purlin/runtime/ with value "30"
    And turn_count_100_def456 exists in .purlin/runtime/ with value "5"
    And session_meta_100 exists with role "architect" on line 2
    And process 100 is alive
    When a GET request is sent to /context-guard/counters
    Then the architect array contains [30] (highest of the two session files)

#### Scenario: Dead process counters excluded from response
    Given turn_count_999_abc123 exists in .purlin/runtime/ with value "42"
    And session_meta_999 exists with role "builder" on line 2
    And process 999 is not running
    When a GET request is sent to /context-guard/counters
    Then the builder array does not contain 42

#### Scenario: Worktree agent counters included in response
    Given turn_count_400_abc123 exists in .worktrees/feat1/.purlin/runtime/ with value "7"
    And session_meta_400 exists in the same directory with role "builder" on line 2
    And turn_count_500_def456 exists in .purlin/runtime/ with value "20"
    And session_meta_500 exists with role "builder" on line 2
    And processes 400 and 500 are alive
    When a GET request is sent to /context-guard/counters
    Then the builder array contains [7, 20]

#### Scenario: Counter without session_meta is excluded
    Given turn_count_600_abc123 exists in .purlin/runtime/ with value "10"
    And no session_meta_600 file exists
    And process 600 is alive
    When a GET request is sent to /context-guard/counters
    Then no role array contains 10

#### Scenario: Collapsed Summary Shows Active Agent Counts with Role Labels
    Given turn_count_100 exists with value "5" and session_meta_100 has role "architect"
    And turn_count_200 exists with value "12" and session_meta_200 has role "builder"
    And processes 100 and 200 are alive
    And the Agent Config section is collapsed
    When the dashboard renders the collapsed heading
    Then the heading displays an inline summary "(Architect: 5, Builder: 12)" between the heading text and the model badge

#### Scenario: Collapsed Summary Omits Roles with No Active Processes
    Given turn_count_100 exists with value "5" and session_meta_100 has role "architect"
    And no builder or qa agents are running
    And the Agent Config section is collapsed
    When the dashboard renders the collapsed heading
    Then the heading displays "(Architect: 5)" with no Builder or QA entries

#### Scenario: Collapsed Summary Hidden When Section Expanded
    Given agents are running and context guard counters are available
    When the user expands the Agent Config section
    Then the inline context guard summary is not visible
    And the model badge is not visible

#### Scenario: Counter Values Colored Warning at >= 80% Threshold
    Given the architect agent has context_guard_threshold 50
    And a running architect agent has turn count 40 (80% of 50)
    When the counter value is rendered (collapsed summary or expanded counter)
    Then the count "40" is styled with var(--purlin-status-warning) color

#### Scenario: Counter Values Colored Critical at >= 92% Threshold
    Given the builder agent has context_guard_threshold 50
    And a running builder agent has turn count 46 (92% of 50)
    When the counter value is rendered (collapsed summary or expanded counter)
    Then the count "46" is styled with var(--purlin-status-error) color

#### Scenario: Counter Values Use Muted Color When Guard Disabled
    Given the qa agent has context_guard false and context_guard_threshold 50
    And a running qa agent has turn count 48
    When the counter value is rendered
    Then the count "48" is styled with var(--purlin-muted) color regardless of threshold proximity

#### Scenario: Collapsed Summary Pipe-Separates Multiple Agents of Same Role
    Given turn_count_100 exists with value "3" and session_meta_100 has role "builder"
    And turn_count_200 exists with value "22" and session_meta_200 has role "builder"
    And processes 100 and 200 are alive
    And the Agent Config section is collapsed
    When the dashboard renders the collapsed heading
    Then the heading displays "(Builder: 3|22)" with counts sorted ascending

#### Scenario: Agents Section State Persists Across Reloads
    Given the user expands the Agents section
    When the page is reloaded
    Then the Agents section is still expanded
    And the expanded/collapsed state is read from localStorage

#### Scenario: Context Guard Checkbox Toggle Disables Threshold Input
    Given the Agents section is expanded
    And the architect Context Guard checkbox is checked
    When the user unchecks the architect Context Guard checkbox
    Then the architect threshold input becomes disabled with opacity 0.4
    And the threshold value remains visible

#### Scenario: Context Guard Threshold Stepper Persists Value
    Given the Agents section is expanded
    And the builder Context Guard checkbox is checked
    When the user clicks the threshold stepper up arrow to increase the value
    Then the new threshold value is sent via POST /config/agents
    And on page reload the new value is displayed

#### Scenario: Collapsed Summary Updates on 5-Second Refresh Cycle
    Given one or more Claude Code agents are running
    And the Agent Config section is collapsed
    When the dashboard auto-refreshes on the 5-second cycle
    Then the inline context guard summary updates with current counter values
    And counter colors update to reflect current threshold proximity

#### Scenario: Live Counter Displays Running Agent Counts
    Given one or more Claude Code agents are running (visible as turn_count_<PID> files in .purlin/runtime/)
    And the Agents section is expanded
    When the dashboard auto-refreshes
    Then each agent row shows the current turn counts to the right of the threshold input
    And multiple agents of the same role are shown pipe-separated (e.g., "3|22|35")
    And agents from isolated team worktrees appear alongside main-directory agents

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
- [ ] "Context" / "Guard" column header displays on two lines, aligned with adjacent two-line headers (Startup/Sequence, Suggest/Next)
- [ ] Context Guard column is wide enough to accommodate checkbox, threshold stepper, and live counter text without overflow
- [ ] Context Guard compound cell shows checkbox and number stepper arranged horizontally with 4px gap
- [ ] When Context Guard checkbox is unchecked, the threshold input is visually dimmed (opacity 0.4) and non-interactive
- [ ] Number stepper arrows are visible and functional within the 40px-wide input
- [ ] Stepper arrows use `var(--purlin-muted)` color, visible against dark blueprint theme background
- [ ] Toggling the Context Guard checkbox does not cause adjacent columns to shift or resize
- [ ] Live counter text appears to the right of the threshold input with ~6px gap
- [ ] Counter text uses monospace font, 10px, `var(--purlin-muted)` color
- [ ] Multiple counters are pipe-separated (e.g., "3|22|35") with no spaces around pipes
- [ ] Counter display updates on 5-second refresh without flickering
- [ ] When no agents are running for a role, no counter text appears (span is empty)
- [ ] Collapsed heading shows inline context guard summary "(Role: counts, ...)" between heading text and model badge
- [ ] Collapsed summary role names use `var(--purlin-primary)` color
- [ ] Collapsed summary count values use monospace font, 10px, matching expanded counter styling
- [ ] Collapsed summary disappears when section is expanded; reappears when collapsed
- [ ] Counter values below 80% threshold use `var(--purlin-muted)` color in both collapsed summary and expanded display
- [ ] Counter values at or above 80% threshold use `var(--purlin-status-warning)` color (orange)
- [ ] Counter values at or above 92% threshold use `var(--purlin-status-error)` color (red)
- [ ] Counter colors update on 5-second refresh cycle as counts change
- [ ] When guard is disabled for an agent, counter values always use `var(--purlin-muted)` regardless of count

