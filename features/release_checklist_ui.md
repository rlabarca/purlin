# Feature: Release Checklist — Dashboard Section

> Label: "CDD Release Checklist"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/release_checklist_core.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd

## 1. Overview

This feature defines the "RELEASE CHECKLIST" section in the CDD Dashboard. It surfaces the fully resolved, ordered release step list to human users as a collapsible section with drag-to-reorder, enable/disable toggles, and a step detail modal. Changes to ordering and enabled state are persisted back to `.purlin/release/config.json` via a POST API.

## 2. Requirements

### 2.1 Section Placement

The Release Checklist section is the last section in the CDD Dashboard Status view, positioned below WORKSPACE. It uses the same collapsible section pattern as ACTIVE, COMPLETE, and WORKSPACE: a clickable header row that toggles between collapsed and expanded states.

### 2.2 Collapsed State

*   **Heading:** "RELEASE CHECKLIST" using the standard section heading typography (Inter Bold 14px uppercase, letter-spacing 0.1em, `--purlin-text`).
*   **Chevron:** Right-pointing when collapsed; down-pointing when expanded. Consistent with other collapsible sections.
*   **Inline badge:** A single badge showing two counts: `N enabled · M disabled`. The enabled count is rendered using `--purlin-status-good`; the separator (` · `) and disabled count use `--purlin-dim`.
*   **Section separator:** A 1px `--purlin-border` line above the section, consistent with other section dividers.

### 2.3 Expanded State

When expanded, the section renders an ordered list of steps. Each row contains the following columns, in order from left to right:

*   **Drag handle** (leftmost, fixed width): The character `⠿` (Unicode U+28FF, Braille Pattern Dots 1-8). Color: `--purlin-dim`. Cursor changes to `grab` on hover. The drag handle is the only interactive element that initiates drag-to-reorder.
*   **Step number** (fixed width, right-aligned): The 1-based position of the step among enabled steps. Enabled steps are numbered contiguously (1, 2, 3, ...). Disabled steps display an em dash (`—`) instead of a number. Rendered in monospace font, `--purlin-muted` color for enabled steps; `--purlin-dim` color for the em dash on disabled steps.
*   **Global/Local badge** (narrow, optional): A tag showing `GLOBAL` or `LOCAL`. Uses `--purlin-tag-fill` as background color and `--purlin-tag-outline` as border, Inter Bold 10px uppercase. Only shown when the step's `source` field is present.
*   **Friendly name** (flex-grow): The step's `friendly_name`. Clickable. Underline appears on hover; color changes to `--purlin-accent` on hover. Clicking opens the Step Detail Modal (Section 2.6). When the step is disabled, the friendly name is dimmed to `--purlin-dim`.
*   **Enable/disable checkbox** (rightmost, fixed width): A checkbox representing the step's `enabled` state. When unchecked, the entire row (handle, number, badge, name) is dimmed to `--purlin-dim`.

### 2.4 Drag-to-Reorder

Drag-and-drop reordering is supported using the HTML5 Drag and Drop API or a lightweight JS library consistent with the dashboard's existing implementation stack.

Behavior when a user drops a step at a new position:
1.  The UI optimistically updates the displayed order immediately.
2.  A `POST /release-checklist/config` request is sent with the full new ordered list (all step IDs with their current enabled states).
3.  On a successful response, the in-memory config is updated to match the new order.
4.  On a failure response (non-2xx or network error), the UI reverts to the previous order and displays a brief inline error indicator adjacent to the drag handle.

The drag handle element MUST have `draggable="true"` set on the row or a dedicated drag-source element.

### 2.5 Enable/Disable Toggle

Behavior when a checkbox is toggled:
1.  The UI optimistically updates the row appearance (checked = normal appearance; unchecked = dimmed to `--purlin-dim`).
2.  A `POST /release-checklist/config` request is sent with the updated enabled state for that step (full config payload, not a partial diff).
3.  On success, the collapsed-state badge recalculates and updates the enabled/disabled count.
4.  On failure, the checkbox reverts to its previous state and a brief inline error indicator is shown.
5.  Step numbers for all rows are recalculated: enabled steps are renumbered contiguously; the toggled row (if now disabled) shows `—` instead of its former number.

### 2.6 Step Detail Modal

Triggered by clicking a step's friendly name. Uses the same modal overlay and container pattern as the Feature Detail Modal used elsewhere in the CDD Dashboard.

**Dismissal:** The modal is dismissed by clicking the close button (X), clicking outside the modal container, or pressing Escape.

**Modal structure:**
*   **Header row:** Step friendly name (Montserrat or Inter Bold, section-header scale). A `GLOBAL` or `LOCAL` source badge is displayed adjacent to the name.
*   **Body sections** (each section is only rendered when the corresponding field is non-null/non-empty):
    *   **DESCRIPTION:** Label "DESCRIPTION" (caption style: Inter Bold 10px uppercase, `--purlin-muted`). Body: prose text.
    *   **CODE:** Label "CODE". Body: monospace code block with `--purlin-surface` background. Only rendered when `code` is non-null.
    *   **AGENT INSTRUCTIONS:** Label "AGENT INSTRUCTIONS". Body: prose text. Only rendered when `agent_instructions` is non-null.
*   **Footer:** A "Close" button (standard button style).

If a step has neither a `code` field nor an `agent_instructions` field, only the DESCRIPTION section is rendered.

### 2.7 Section State Persistence

The expanded/collapsed state of the RELEASE CHECKLIST section is persisted in `localStorage` under the existing `purlin-section-states` key, using the same mechanism as other collapsible sections. The default state is collapsed.

### 2.8 Refresh Stability

The RELEASE CHECKLIST section participates in the dashboard's existing 5-second incremental refresh cycle (per `cdd_status_monitor.md` Section 2.10). When a backing config file changes — `.purlin/release/config.json`, `tools/release/global_steps.json`, or `.purlin/release/local_steps.json` — the section MUST update to reflect the new state without any visible disruption.

**What updates on each refresh cycle (incremental DOM mutation only):**
*   Step order and step content in the expanded list.
*   The enabled/disabled counts in the collapsed-state badge.
*   The enabled state and dimming of individual rows.

**What MUST NOT happen on a refresh:**
*   The section MUST NOT flash, blink, or momentarily disappear and reappear.
*   The section MUST NOT collapse if it was expanded, or expand if it was collapsed.
*   The surrounding page layout (header, other sections, scroll position) MUST NOT shift.
*   Individual rows that did not change SHOULD NOT be re-rendered.

The implementation MUST use incremental DOM diffing or targeted element updates — the same constraint that applies to feature table rows in `cdd_status_monitor.md` Section 2.10. Replacing the entire section's innerHTML on every poll is not acceptable.

### 2.9 API Endpoints

#### `GET /release-checklist`

Returns the fully resolved, ordered list of release steps by applying the algorithm from `release_checklist_core.md` Section 2.5.

**Response format:**
```json
{
  "steps": [
    {
      "id": "purlin.record_version_notes",
      "friendly_name": "Record Version & Release Notes",
      "description": "...",
      "code": null,
      "agent_instructions": "...",
      "source": "global",
      "enabled": true,
      "order": 1
    }
  ]
}
```

The `source` field is `"global"` for steps defined in `global_steps.json` and `"local"` for steps from `local_steps.json`. The `order` field is the 1-based position among enabled steps. Disabled steps have `order: null`.

#### `POST /release-checklist/config`

Accepts the updated config as a JSON body and writes it to `.purlin/release/config.json`.

**Request body:**
```json
{
  "steps": [
    {"id": "purlin.record_version_notes", "enabled": true},
    {"id": "purlin.push_to_remote", "enabled": false}
  ]
}
```

**Success response:** `{"ok": true}`

**Error response:** HTTP 400 with `{"ok": false, "error": "<message>"}` for validation failures (e.g., duplicate IDs, unknown fields). HTTP 500 for file write failures.

The server MUST validate that:
*   Each `id` in the request body corresponds to a known step (present in global or local steps). Unknown IDs are accepted but logged as warnings, consistent with the auto-discovery orphan behavior.
*   No `id` appears more than once in the request.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Collapsed Badge Shows Enabled and Disabled Counts
    Given the release checklist has 7 enabled steps and 2 disabled steps
    When the dashboard HTML is generated
    Then the RELEASE CHECKLIST collapsed badge contains "7 enabled"
    And the badge contains "2 disabled"
    And the enabled count element uses the --purlin-status-good color class
    And the disabled count element uses the --purlin-dim color class

#### Scenario: POST /release-checklist/config Persists New Step Order
    Given the release checklist config has steps in order [A, B, C]
    When a POST request is sent to /release-checklist/config with body {"steps": [{"id": "C", "enabled": true}, {"id": "A", "enabled": true}, {"id": "B", "enabled": true}]}
    Then .purlin/release/config.json lists step "C" as the first entry
    And step "A" as the second entry
    And step "B" as the third entry
    And the response contains {"ok": true}

#### Scenario: Disabled Step Shows Em Dash and Affects Badge Count
    Given the release checklist config has step "purlin.push_to_remote" set to enabled false
    When the dashboard HTML is generated
    Then the row for "purlin.push_to_remote" displays an em dash in the step number column
    And the row for "purlin.push_to_remote" has dimmed styling
    And the collapsed badge disabled count reflects the disabled step
    And enabled steps have contiguous 1-based step numbers

#### Scenario: Step Detail Modal Contains All Populated Sections
    Given the release checklist contains a step with description, code, and agent_instructions all populated
    When the dashboard HTML is generated for the step detail modal of that step
    Then the modal contains a DESCRIPTION section with the step's description text
    And the modal contains a CODE section with a monospace code block
    And the modal contains an AGENT INSTRUCTIONS section

#### Scenario: Step Detail Modal Omits CODE Section When Code Is Null
    Given the release checklist contains a step where code is null and description and agent_instructions are populated
    When the dashboard HTML is generated for the step detail modal of that step
    Then the modal contains a DESCRIPTION section
    And the modal contains an AGENT INSTRUCTIONS section
    And the modal does not contain a CODE section

#### Scenario: Local Step Displays LOCAL Badge in Row and Modal
    Given the release checklist contains a step with source "local"
    When the dashboard HTML is generated
    Then that step's row contains a "LOCAL" badge element
    And the step detail modal header for that step contains a "LOCAL" source badge

### Manual Scenarios

#### Scenario: Drag Handle Reorders Steps in Display
Given the release checklist is expanded showing at least 3 steps in their current order,
And the step currently at position 3 has a known friendly name (e.g. "Push to Remote"),
When the user grabs that step by its drag handle (`⠿`) and drops it at position 1,
Then the step formerly at position 3 is now displayed at position 1 in the list,
And the steps formerly at positions 1 and 2 are now displayed at positions 2 and 3,
And the step number labels on all rows update to reflect their new positions,
And no page reload is required for these changes to appear.

#### Scenario: Config File Change Refreshes Without Visual Disruption
Given the CDD Dashboard is open in a browser with the RELEASE CHECKLIST section expanded,
And the user has scrolled down so that the release checklist is visible,
When `.purlin/release/config.json` is edited externally to change the enabled state of one step or its order,
Then within one 5-second refresh cycle the release checklist section updates to reflect the new state,
And the section remains expanded (it does not collapse and re-expand),
And no row flickers or disappears and reappears during the update,
And the scroll position of the page does not change,
And rows whose content did not change appear visually undisturbed.

## Visual Specification

### Screen: Release Checklist Section (Collapsed)
- **Reference:** N/A
- [ ] Section heading "RELEASE CHECKLIST" uses Inter Bold 14px uppercase with letter-spacing 0.1em
- [ ] Chevron points right (collapsed) and transitions to pointing down (expanded)
- [ ] Enabled count text uses `--purlin-status-good` color
- [ ] Separator (` · `) and disabled count text use `--purlin-dim` color
- [ ] A 1px `--purlin-border` horizontal line separates this section from WORKSPACE above

### Screen: Release Checklist Section (Expanded)
- **Reference:** N/A
- [ ] Drag handle character (`⠿`) appears at the left edge of each row
- [ ] Drag handle color is `--purlin-dim`; cursor changes to `grab` on hover
- [ ] Step number is right-aligned, rendered in monospace font, `--purlin-muted` color for enabled steps; disabled steps show `—` in `--purlin-dim` color instead of a number
- [ ] GLOBAL/LOCAL badge uses `--purlin-tag-fill` background and `--purlin-tag-outline` border, Inter Bold 10px uppercase
- [ ] Friendly name is clickable; underline and `--purlin-accent` color appear on hover
- [ ] Disabled rows have all text (handle, number, badge, name) dimmed to `--purlin-dim`
- [ ] Checkbox is right-aligned in a fixed-width rightmost column

### Screen: Step Detail Modal
- **Reference:** N/A
- [ ] Modal uses the same overlay dimming and container border-radius as the Feature Detail Modal
- [ ] Section labels (DESCRIPTION, CODE, AGENT INSTRUCTIONS) use Inter Bold 10px uppercase, `--purlin-muted` color
- [ ] CODE section body is rendered in a monospace code block with `--purlin-surface` background
- [ ] Modal is scrollable when content exceeds viewport height
- [ ] GLOBAL/LOCAL source badge is visible adjacent to the step's friendly name in the modal header

## User Testing Discoveries