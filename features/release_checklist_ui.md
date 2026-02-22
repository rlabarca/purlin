# Feature: Release Checklist — Dashboard Section

> Label: "Release Checklist: Dashboard Section"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the "RELEASE CHECKLIST" section in the CDD Dashboard. It surfaces the fully resolved, ordered release step list to human users as a collapsible section with drag-to-reorder, enable/disable toggles, and a step detail modal. Changes to ordering and enabled state are persisted back to `.agentic_devops/release/config.json` via a POST API.

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
*   **Step number** (fixed width, right-aligned): The 1-based position of the step in the current ordered list. Rendered in monospace font, `--purlin-muted` color.
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

The RELEASE CHECKLIST section participates in the dashboard's existing 5-second incremental refresh cycle (per `cdd_status_monitor.md` Section 2.10). When a backing config file changes — `.agentic_devops/release/config.json`, `tools/release/global_steps.json`, or `.agentic_devops/release/local_steps.json` — the section MUST update to reflect the new state without any visible disruption.

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

The `source` field is `"global"` for steps defined in `global_steps.json` and `"local"` for steps from `local_steps.json`. The `order` field is the 1-based position in the resolved list.

#### `POST /release-checklist/config`

Accepts the updated config as a JSON body and writes it to `.agentic_devops/release/config.json`.

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
None. All scenarios for this feature require the running CDD Dashboard server and human interaction to verify.

### Manual Scenarios

#### Scenario: Collapsed State Displays Correct Counts
Given the release checklist has 7 enabled steps and 2 disabled steps,
When the RELEASE CHECKLIST section is collapsed,
Then the inline badge shows "7 enabled · 2 disabled",
And the enabled count is styled with `--purlin-status-good`,
And the disabled count is styled with `--purlin-dim`.

#### Scenario: Drag Handle Reorders Steps in Display
Given the release checklist is expanded showing at least 3 steps in their current order,
And the step currently at position 3 has a known friendly name (e.g. "Push to Remote"),
When the user grabs that step by its drag handle (`⠿`) and drops it at position 1,
Then the step formerly at position 3 is now displayed at position 1 in the list,
And the steps formerly at positions 1 and 2 are now displayed at positions 2 and 3,
And the step number labels on all rows update to reflect their new positions,
And no page reload is required for these changes to appear.

#### Scenario: Drag Reorder Persists to Config File
Given the release checklist is expanded showing at least 3 steps in their current order,
And the step currently at position 3 has a known step ID (e.g. "purlin.push_to_remote"),
When the user grabs that step by its drag handle and drops it at position 1,
Then the `steps` array in `.agentic_devops/release/config.json` lists that step's ID as the first entry,
And the IDs of all other steps appear in the file in the same relative order they now occupy in the displayed list.

#### Scenario: Toggle Disables Step
Given the release checklist is expanded,
When the user unchecks the checkbox for `purlin.push_to_remote`,
Then the `purlin.push_to_remote` row is dimmed,
And the disabled count in the collapsed badge increments by 1,
And refreshing the dashboard shows `purlin.push_to_remote` still disabled.

#### Scenario: Modal Displays Step Details
Given the release checklist is expanded,
When the user clicks the friendly name of a step that has all three fields populated (description, code, and agent_instructions),
Then a modal opens showing the DESCRIPTION, CODE, and AGENT INSTRUCTIONS sections in order.

#### Scenario: Modal Omits Empty Sections
Given the release checklist is expanded,
When the user clicks the friendly name of a step where `code` is null,
Then the modal opens showing DESCRIPTION and AGENT INSTRUCTIONS sections,
And no CODE section is rendered.

#### Scenario: Local Step Identified
Given the project has a local step defined in `.agentic_devops/release/local_steps.json`,
When the release checklist is expanded,
Then that step's row displays a "LOCAL" badge,
And when the user opens the step's detail modal, the modal header displays the "LOCAL" source badge.

#### Scenario: Config File Change Refreshes Without Visual Disruption
Given the CDD Dashboard is open in a browser with the RELEASE CHECKLIST section expanded,
And the user has scrolled down so that the release checklist is visible,
When `.agentic_devops/release/config.json` is edited externally to change the enabled state of one step or its order,
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
- [ ] Step number is right-aligned, rendered in monospace font, `--purlin-muted` color
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

### [BUG] LOCAL badge narrower than GLOBAL badge (Discovered: 2026-02-22)
- **Scenario:** Visual Specification — Release Checklist Row Layout
- **Observed Behavior:** The `LOCAL` scope badge renders narrower than the `GLOBAL` badge because no minimum width is set. In a list where both badge types appear, the column is visually uneven — `LOCAL` is approximately one character-width narrower and the label is not centered relative to the GLOBAL badge width.
- **Expected Behavior:** Both `GLOBAL` and `LOCAL` badges should occupy the same fixed width with the label centered within the box, maintaining consistent column alignment across all rows.
- **Action Required:** Builder — apply a consistent `min-width` (or fixed width) to both badge variants so they render at the same size with centered text.
- **Status:** RESOLVED

### [BUG] Disabled row is not visually dimmed (Discovered: 2026-02-22)
- **Scenario:** Toggle Disables Step
- **Observed Behavior:** Unchecking a step's checkbox leaves the row at full color — the row text (handle, number, badge, name) is not dimmed. The checkbox is empty and the disabled count increments correctly, but no visual dimming is applied.
- **Expected Behavior:** Disabled rows should have all text dimmed to `--purlin-dim`, as specified in the scenario and the visual spec.
- **Action Required:** Builder — apply `--purlin-dim` styling to the row when its checkbox is unchecked.
- **Status:** RESOLVED

### [BUG] Drag handle does not reorder steps (Discovered: 2026-02-22)
- **Scenario:** Drag Handle Reorders Steps in Display
- **Observed Behavior:** The drag handle (`⠿`) is visible but dragging it does not reorder the steps in the list.
- **Expected Behavior:** Grabbing a step by its drag handle and dropping it at a new position should reorder the steps in the displayed list immediately, without a page reload.
- **Action Required:** Builder — implement drag-and-drop reorder functionality for release checklist rows.
- **Status:** RESOLVED

### [BUG] Drag reorder snaps back before updating; unreliable persistence (Discovered: 2026-02-22)
- **Scenario:** Drag Handle Reorders Steps in Display
- **Observed Behavior:** After dropping a step at a new position, the item snaps back to its original position briefly before (sometimes) settling into the new order. Occasionally the reorder does not persist at all, requiring multiple drag attempts to achieve the desired ordering.
- **Expected Behavior:** The UI should optimistically update the displayed order immediately on drop (no snap-back). The POST /release-checklist/config request persists the change in the background. The displayed order should remain stable throughout. The operation should be fully deterministic on the first drag attempt.
- **Action Required:** Builder — investigate the snap-back. Likely cause: the 5-second auto-refresh is overwriting the optimistic DOM update before the POST completes, because the `rcPendingSave` flag is not being set at the start of a drag operation. Ensure the in-flight guard is set before the POST and cleared only after the response is received and the cache is updated.
- **Status:** RESOLVED

## Implementation Notes

*   The drag-to-reorder implementation MUST be consistent with any drag/drop library or pattern already used in the CDD Dashboard. If none exists, the HTML5 Drag and Drop API is the default. Do not introduce a new dependency without confirming with the Architect.
*   The `POST /release-checklist/config` endpoint writes directly to `.agentic_devops/release/config.json`. The server MUST handle concurrent writes gracefully (e.g., the user rapidly toggling checkboxes); debouncing on the frontend is preferred over server-side locking for this use case.
*   The `purlin-section-states` localStorage key already exists (per `cdd_status_monitor.md`). The RELEASE CHECKLIST section's key within that object SHOULD be `release-checklist`.
*   The Step Detail Modal pattern references the Feature Detail Modal. If the Feature Detail Modal does not yet exist as an independent component, the Builder should implement the modal as a reusable component and refactor the Feature Detail Modal to use it.
*   **Refresh Stability:** Uses `refreshReleaseChecklist()` called from `refreshStatus()` after innerHTML replacement. Fetches `/release-checklist`, compares against `rcStepsCache`, and only updates changed rows (reorder via DOM reappend, enabled state via checkbox+dimming diff). A `rcPendingSave` flag prevents refresh overwrites during in-flight `POST /release-checklist/config` requests — same pattern as the agents section's `pendingWrites` mechanism. Badge updates use shared `rcUpdateBadge()` function.
*   **Drag Snap-Back Fix (2026-02-22):** BUG resolved — root cause was `refreshStatus()` replacing `status-view` innerHTML (including release checklist rows) from server-rendered HTML. When `rcPendingSave` was true, `refreshReleaseChecklist()` returned early, leaving the old server-rendered order in the DOM. Two-part fix: (1) `refreshStatus()` now saves and restores `rc-tbody` innerHTML when `rcPendingSave` is true, so the optimistic DOM survives the full-page refresh. (2) `rcPersistConfig()` optimistically updates `rcStepsCache` from the current DOM before sending the POST, so subsequent refreshes see the cache matching the server's new order and skip redundant DOM updates.
