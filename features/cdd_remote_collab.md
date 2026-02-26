# Feature: CDD Remote Collaboration

> Label: "CDD Remote Collaboration"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_remote_collab.md
> Prerequisite: features/cdd_isolated_teams.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md

[TODO]

## 1. Overview

The CDD dashboard provides a REMOTE COLLABORATION section that enables multi-machine collaboration via session-based collab branches on the hosted remote. The section is always visible in the dashboard (same pattern as ISOLATED TEAMS) and serves as the entry point for creating, joining, switching, and disconnecting from remote collab sessions. It renders between MAIN WORKSPACE and ISOLATED TEAMS in the section order.

---

## 2. Requirements

### 2.1 Section Positioning and Visibility

The REMOTE COLLABORATION section is always rendered in the dashboard, regardless of configuration or active session state. It appears between the existing sections in this order:

1. **REMOTE COLLABORATION** (new; always rendered)
2. **ISOLATED TEAMS** (existing)
3. **MAIN WORKSPACE** (existing, renamed from WORKSPACE)

The section is always visible because it IS the entry point for remote collab. Hiding it behind config creates a chicken-and-egg problem (user cannot discover the feature without editing config).

Exception: if `git remote` returns empty (no remote configured at all), the section body shows "No git remote configured. Add a remote to enable remote collaboration."

### 2.2 State A: No Active Session (Setup Mode)

When `.purlin/runtime/active_remote_session` is absent or empty:

**Collapsed badge:** "REMOTE COLLABORATION" (no annotation) or "N Remote Sessions" (if known sessions exist on remote, `--purlin-muted` color).

**Expanded content (in order):**

1. **Creation row** (always first, same pattern as ISOLATED TEAMS creation row):
   - Label: "Start Remote Session"
   - Text input: session name, validated `[a-zA-Z0-9_.-]+`, max 30 chars (dots allowed for version numbers like `v0.5-sprint`; longer than isolation names because these are branch names, not directories)
   - Create button: disabled until valid name. On click -> `POST /remote-collab/create`.
   - Input uses same color scheme as ISOLATED TEAMS name input (same CSS tokens).

2. **Known sessions table** (below creation row):
   - Populated from `git branch -r --list '<remote>/collab/*'` (uses locally cached refs, no network fetch).
   - Columns: Session | Branch | Action
   - Each row has a **Delete** button and a **Join** button in the Action column, in that order (Delete left, Join right). Delete -> opens the Delete Confirmation Modal (Section 2.8). Join -> `POST /remote-collab/switch`.
   - Empty state: "No remote collab sessions found."

### 2.3 State B: Active Session (Operational Mode)

When `.purlin/runtime/active_remote_session` contains a session name:

**Collapsed badge:** `"<session-name> <STATE annotation>"` where STATE is the sync state, framed from the remote's perspective. Annotation format: SAME (no annotation), AHEAD -> `"AHEAD (Remote is N behind local main)"`, BEHIND -> `"BEHIND (Remote is N ahead of local main)"`, DIVERGED -> `"DIVERGED (Remote is N ahead, M behind local main)"`. Color: SAME -> green (`--purlin-status-good`), AHEAD/BEHIND -> yellow (`--purlin-status-todo`), DIVERGED -> orange (`--purlin-status-warning`). Same tokens as ISOLATED TEAMS.

**Expanded content (in order):**

1. **Active session panel** (replaces creation row):
   - **Session row (single line):** `[session-name ▾] collab/<name>  [Disconnect]`. The session name is a `<select>` dropdown populated with all known sessions from remote (current session pre-selected). Changing selection -> `POST /remote-collab/switch`. The branch ref `collab/<name>` is displayed as muted text beside the dropdown. The "Disconnect" button is right-aligned on the same row -> `POST /remote-collab/disconnect`. Does NOT delete any branches. Session remains joinable.
   - **Sync state row:** badge with remote-perspective annotation (same format as collapsed badge) + "Last check: N min ago" (or "Never") + "Check Remote" button (right-aligned): `POST /remote-collab/fetch`.

2. **CONTRIBUTORS table:**
   - Name | Commits | Last Active | Last Commit Subject -- sorted most-recent-first, max 10.
   - Derived from `git log origin/collab/<session> --format="%ae|%an|%cr|%s"`.
   - Empty state: "(no commits on this session yet)"

### 2.4 Server Endpoints

Five POST endpoints, following the existing `/isolate/*` pattern:

**`POST /remote-collab/create`** -- `{ "name": "<session-name>" }`

1. Validate session name (`[a-zA-Z0-9_.-]+`, 1-30 chars, no leading/trailing dots/hyphens, no `..`).
2. Read remote from config (`remote_collab.remote`, default `"origin"`).
3. Create branch `collab/<name>` from current `main` HEAD: `git branch collab/<name> main`.
4. Push to remote: `git push <remote> collab/<name>`.
5. Write session name to `.purlin/runtime/active_remote_session`.
6. Return `{ "status": "ok", "session": "<name>", "branch": "collab/<name>" }`.
7. On push failure: return `{ "error": "..." }`, do NOT write runtime file.

**`POST /remote-collab/switch`** -- `{ "name": "<session-name>" }`

1. Verify `origin/collab/<name>` exists in remote tracking refs. If not: `git fetch <remote> collab/<name>`.
2. Write session name to `.purlin/runtime/active_remote_session`.
3. Return `{ "status": "ok", "session": "<name>" }`.

**`POST /remote-collab/disconnect`** -- `{}`

1. Remove/truncate `.purlin/runtime/active_remote_session`.
2. Do NOT delete any branches or remote refs.
3. Return `{ "status": "ok" }`.

**`POST /remote-collab/fetch`** -- `{}` (uses active session)

1. Read active session from runtime file. Abort if none.
2. `git fetch <remote> collab/<session>`.
3. Return `{ "status": "ok", "fetched_at": "<ISO timestamp>" }`.
4. "Checking..." label + disabled guard while in flight (same pattern as `rcPendingSave`).
5. Auto-fetch: background thread fires after first interval (NOT on startup); boolean lock prevents concurrent fetches; failures logged server-side only.
6. `last_fetch`: in-memory only; resets to null on server restart.

**`POST /remote-collab/delete`** -- `{ "name": "<session-name>" }`

1. Validate session name (same rules as create).
2. Read remote from config (`remote_collab.remote`, default `"origin"`).
3. Delete the remote branch: `git push <remote> --delete collab/<name>`.
4. Delete the local tracking branch if it exists: `git branch -D collab/<name>`.
5. If the deleted session was the active session, clear `.purlin/runtime/active_remote_session`.
6. Return `{ "status": "ok", "session": "<name>", "deleted_branch": "collab/<name>" }`.
7. On failure (branch doesn't exist on remote, permission denied): return `{ "error": "..." }`.

### 2.5 Sync State Computation

- Uses locally cached remote tracking refs -- never triggers a network fetch during the 5-second poll.
- `git log origin/collab/<session>..main --oneline` -> commits local main is ahead.
- `git log main..origin/collab/<session> --oneline` -> commits remote is ahead.
- SAME/AHEAD/BEHIND/DIVERGED four-state logic (same as ISOLATED TEAMS section).
- When remote tracking ref `origin/collab/<session>` does not exist yet (pre-first-fetch): show inline note "Run Check Remote to see sync state" instead of a badge.

### 2.6 Cross-Section Annotation in MAIN WORKSPACE

When an active session exists, the MAIN WORKSPACE section body shows a "Last remote sync: N min ago" line (or "Never synced") below the clean/dirty state line. Absent when no active session.

NOT appended to the section heading text (per `cdd_isolated_teams.md` Section 2.3 "no annotations on heading").

### 2.7 /status.json Extension

When an active session exists, the `/status.json` response includes:

```json
{
  "remote_collab": {
    "active_session": "v0.5-sprint",
    "branch": "collab/v0.5-sprint",
    "remote": "origin",
    "sync_state": "AHEAD",
    "commits_ahead": 2,
    "commits_behind": 0,
    "last_fetch": "2026-02-23T14:30:00Z",
    "contributors": [
      { "email": "bob@example.com", "name": "Bob Ramos", "commits": 5, "last_active": "2h ago", "last_subject": "implement task CRUD handlers" }
    ]
  },
  "remote_collab_sessions": [
    { "name": "v0.5-sprint", "branch": "collab/v0.5-sprint", "active": true, "sync_state": "AHEAD", "commits_ahead": 2, "commits_behind": 0 },
    { "name": "hotfix-auth", "branch": "collab/hotfix-auth", "active": false, "sync_state": "BEHIND", "commits_ahead": 0, "commits_behind": 3 }
  ]
}
```

`remote_collab`: present only when an active session exists. Absent otherwise.

`remote_collab_sessions`: always present (may be empty array). Lists all sessions discovered from remote tracking refs. Each entry includes per-session sync state computed from locally cached refs (same rules as Section 2.5, applied per session). This data is used by the Delete Confirmation Modal (Section 2.8) to determine whether a data loss warning is needed.

### 2.8 Delete Session Confirmation Modal

Triggered by clicking a session's **Delete** button in the known sessions table (Section 2.2). Uses the same modal overlay and container pattern as other CDD Dashboard modals (Feature Detail Modal, Kill modal).

**Dismissal:** X button, clicking outside the modal, or pressing Escape. Same as all CDD modals.

**Sync state source:** The modal reads the session's sync state from the `remote_collab_sessions` array in the most recent `/status.json` poll. No additional server request is needed to render the modal.

**Modal content (two variants):**

1. **Standard confirmation (sync state is SAME or BEHIND):**
   - Title: "Delete Session"
   - Body: "Are you sure you want to delete session '<name>'? This will delete the remote branch collab/<name>. This action cannot be undone."
   - Buttons: [Cancel] [Delete] -- Cancel has default focus. Delete button uses `--purlin-status-error` as background color with contrasting text.

2. **Data loss warning (sync state is AHEAD or DIVERGED):**
   - Title: "Delete Session"
   - Body: same as standard confirmation.
   - **Warning block (below body, above buttons):** Red text using `--purlin-status-error` on a subtle red-tinted background (`--purlin-status-error` at reduced opacity). Text varies by state:
     - AHEAD: "WARNING: The remote branch has N commit(s) not in your local main. Deleting this session will permanently discard those commits."
     - DIVERGED: "WARNING: The remote branch has diverged from your local main (N commit(s) ahead, M behind). Deleting this session will permanently discard the N remote-only commit(s)."
   - Buttons: [Cancel] [Delete] -- same styling as standard variant.

**On confirm:** Dashboard sends `POST /remote-collab/delete` with body `{ "name": "<name>" }`. On success, the known sessions table re-renders without the deleted session. On failure, an inline error is shown within the modal.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: REMOTE Section Always Rendered in Dashboard HTML

    Given the CDD server is running
    And no remote_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section is present in the HTML output

#### Scenario: remote_collab Absent From status.json When No Active Session

    Given no file exists at .purlin/runtime/active_remote_session
    When an agent calls GET /status.json
    Then the response does not contain a remote_collab field

#### Scenario: remote_collab_sessions Present In status.json Even When Empty

    Given no collab/* branches exist on the remote
    When an agent calls GET /status.json
    Then the response contains remote_collab_sessions as an empty array

#### Scenario: Create Session Pushes Branch and Writes Runtime File

    Given no collab/v0.5-sprint branch exists on the remote
    And the CDD server is running
    When a POST request is sent to /remote-collab/create with body {"name": "v0.5-sprint"}
    Then the server creates branch collab/v0.5-sprint from main HEAD
    And pushes collab/v0.5-sprint to origin
    And writes "v0.5-sprint" to .purlin/runtime/active_remote_session
    And the response contains { "status": "ok", "session": "v0.5-sprint" }
    And GET /status.json shows remote_collab.sync_state as "SAME"

#### Scenario: Create Session With Invalid Name Returns Error

    Given the CDD server is running
    When a POST request is sent to /remote-collab/create with body {"name": "bad..name"}
    Then the response contains an error message
    And no branch is created on the remote
    And .purlin/runtime/active_remote_session is not written

#### Scenario: Join Existing Session Updates Runtime File

    Given collab/v0.5-sprint exists as a remote tracking branch
    And no active session is set
    When a POST request is sent to /remote-collab/switch with body {"name": "v0.5-sprint"}
    Then .purlin/runtime/active_remote_session contains "v0.5-sprint"
    And GET /status.json shows remote_collab.active_session as "v0.5-sprint"

#### Scenario: Disconnect Clears Active Session

    Given an active session "v0.5-sprint" is set in .purlin/runtime/active_remote_session
    When a POST request is sent to /remote-collab/disconnect
    Then .purlin/runtime/active_remote_session is empty or absent
    And GET /status.json does not contain a remote_collab field
    And collab/v0.5-sprint still exists on the remote

#### Scenario: Switch Session Updates Active Session

    Given an active session "v0.5-sprint" is set
    And collab/hotfix-auth exists as a remote tracking branch
    When a POST request is sent to /remote-collab/switch with body {"name": "hotfix-auth"}
    Then .purlin/runtime/active_remote_session contains "hotfix-auth"
    And GET /status.json shows remote_collab.active_session as "hotfix-auth"

#### Scenario: Sync State SAME When Local and Remote Are Identical

    Given an active session "v0.5-sprint" is set
    And local main and origin/collab/v0.5-sprint point to the same commit
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "SAME"
    And remote_collab.commits_ahead is 0
    And remote_collab.commits_behind is 0

#### Scenario: Sync State AHEAD When Local Has Unpushed Commits

    Given an active session "v0.5-sprint" is set
    And local main has 3 commits not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has no commits not in local main
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "AHEAD"
    And remote_collab.commits_ahead is 3

#### Scenario: Sync State BEHIND When Remote Has New Commits

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    And local main has no commits not in origin/collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "BEHIND"
    And remote_collab.commits_behind is 2

#### Scenario: Sync State DIVERGED When Both Sides Have Commits

    Given an active session "v0.5-sprint" is set
    And local main has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "DIVERGED"
    And remote_collab.commits_ahead is 1
    And remote_collab.commits_behind is 2

#### Scenario: Contributors Derived From Git Log Sorted Most-Recent-First

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has commits from two different authors
    When an agent calls GET /status.json
    Then remote_collab.contributors has entries sorted by most-recent-first
    And each entry has email, name, commits, last_active, and last_subject fields
    And the contributors list has at most 10 entries

#### Scenario: Manual Check Updates last_fetch Timestamp

    Given an active session "v0.5-sprint" is set
    And remote_collab.last_fetch is null (server just started)
    When a POST request is sent to /remote-collab/fetch
    Then the response contains fetched_at with an ISO timestamp
    And subsequent GET /status.json shows remote_collab.last_fetch as a non-null value

#### Scenario: 5-Second Status Poll Triggers Zero Git Fetch Calls

    Given an active session "v0.5-sprint" is set
    And auto_fetch_interval is 0 in the test config
    When the dashboard polls GET /status.json 3 times at 5-second intervals
    Then no git fetch commands are executed during those polls

#### Scenario: Delete Session Removes Remote Branch and Returns Success

    Given collab/v0.5-sprint exists as a remote tracking branch
    And the CDD server is running
    When a POST request is sent to /remote-collab/delete with body {"name": "v0.5-sprint"}
    Then the server deletes collab/v0.5-sprint from the remote
    And the local tracking branch collab/v0.5-sprint is removed if it existed
    And the response contains { "status": "ok", "session": "v0.5-sprint" }

#### Scenario: Delete Active Session Also Clears Runtime File

    Given an active session "v0.5-sprint" is set in .purlin/runtime/active_remote_session
    And collab/v0.5-sprint exists as a remote tracking branch
    When a POST request is sent to /remote-collab/delete with body {"name": "v0.5-sprint"}
    Then the server deletes collab/v0.5-sprint from the remote
    And .purlin/runtime/active_remote_session is empty or absent
    And GET /status.json does not contain a remote_collab field

#### Scenario: Delete Nonexistent Session Returns Error

    Given no collab/nonexistent branch exists on the remote
    When a POST request is sent to /remote-collab/delete with body {"name": "nonexistent"}
    Then the response contains an error message

#### Scenario: Per-Session Sync State in remote_collab_sessions

    Given collab/v0.5-sprint exists as a remote tracking branch
    And origin/collab/v0.5-sprint has 2 commits not in local main
    And local main has no commits not in origin/collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab_sessions contains an entry for "v0.5-sprint"
    And that entry has sync_state "BEHIND" and commits_behind 2

### Manual Scenarios (Human Verification Required)

#### Scenario: REMOTE COLLABORATION Section Always Visible

    Given the CDD dashboard is open in a browser
    And no remote_collab config exists in .purlin/config.json
    When the User views the dashboard
    Then the REMOTE COLLABORATION section is visible
    And it appears above the ISOLATED TEAMS section

#### Scenario: No-Active-Session State Shows Creation Row and Known Sessions

    Given the CDD dashboard is open
    And no active remote session exists
    When the User views the REMOTE COLLABORATION section
    Then a creation row "Start Remote Session [input] [Create]" is visible
    And a known sessions table is shown below the creation row

#### Scenario: Active-Session State Shows Sync Badge and Controls

    Given the CDD dashboard is open
    And an active remote session "v0.5-sprint" exists
    When the User views the REMOTE COLLABORATION section
    Then a session-name dropdown is displayed with "v0.5-sprint" selected
    And the branch ref "collab/v0.5-sprint" is shown as muted text beside the dropdown
    And a "Disconnect" button is right-aligned on the same row as the dropdown
    And a sync state badge with annotation is visible on the next row
    And a "Check Remote" button is right-aligned on the sync state row

#### Scenario: Badge Colors Match ISOLATED TEAMS Section

    Given the CDD dashboard is open
    And an active remote session exists with DIVERGED sync state
    When the User views the collapsed REMOTE COLLABORATION heading
    Then the DIVERGED badge uses orange (--purlin-status-warning)
    And SAME would use green (--purlin-status-good)
    And AHEAD/BEHIND would use yellow (--purlin-status-todo)

#### Scenario: REMOTE COLLABORATION Renders Above ISOLATED TEAMS

    Given the CDD dashboard is open
    And both REMOTE COLLABORATION and ISOLATED TEAMS sections are visible
    When the User scrolls through the dashboard
    Then REMOTE COLLABORATION appears above ISOLATED TEAMS in the DOM order

#### Scenario: Last Remote Sync Annotation In MAIN WORKSPACE Body

    Given the CDD dashboard is open
    And an active remote session exists
    When the User views the MAIN WORKSPACE section body
    Then a "Last remote sync: N min ago" line is visible below the clean/dirty state line

#### Scenario: Create Session Transitions From Setup to Active Mode

    Given the CDD dashboard is open in setup mode (no active session)
    When the User types "v0.5-sprint" and clicks Create
    Then the REMOTE COLLABORATION section transitions to active mode
    And the session name and sync state badge are shown

#### Scenario: Disconnect Transitions From Active to Setup Mode

    Given the CDD dashboard is open in active mode with session "v0.5-sprint"
    When the User clicks the Disconnect button
    Then the REMOTE COLLABORATION section transitions back to setup mode
    And the creation row and known sessions table are shown

#### Scenario: Delete Button Visible in Known Sessions Table

    Given the CDD dashboard is open
    And no active remote session exists
    And at least one collab session exists on the remote
    When the User views the known sessions table
    Then each session row has a "Delete" button to the left of the "Join" button

#### Scenario: Delete Confirmation Modal With Standard Warning

    Given the CDD dashboard is open
    And session "v0.5-sprint" has sync state SAME relative to local main
    When the User clicks the Delete button for "v0.5-sprint"
    Then a confirmation modal appears with title "Delete Session"
    And the modal body warns that deleting will remove the remote branch
    And Cancel and Delete buttons are visible
    And the Delete button uses red (--purlin-status-error) background

#### Scenario: Delete Confirmation Modal Shows Data Loss Warning for AHEAD Session

    Given the CDD dashboard is open
    And session "hotfix-auth" has sync state AHEAD with 3 commits ahead of local main
    When the User clicks the Delete button for "hotfix-auth"
    Then a confirmation modal appears with title "Delete Session"
    And a red warning block is visible below the body text
    And the warning states that 3 commits will be permanently discarded
    And Cancel and Delete buttons are visible

---

## 4. Visual Specification

### Screen: CDD Dashboard -- Remote Collaboration Section

- **Reference:** N/A
- [ ] REMOTE COLLABORATION section position: above ISOLATED TEAMS, above MAIN WORKSPACE
- [ ] Section always visible (collapsible, same indent as peers)
- [ ] No-active-session: creation row "Start Remote Session [input] [Create]" + known sessions table
- [ ] Active-session row 1: session-name dropdown + `collab/<name>` branch ref (muted) + Disconnect button (right-aligned), all on one line
- [ ] Active-session row 2: sync badge + annotation + last-check timestamp + Check Remote button (right-aligned)
- [ ] "Checking..." guard state while fetch in flight
- [ ] Four sync state badge colors (matching ISOLATED TEAMS color scheme: SAME=green, AHEAD/BEHIND=yellow, DIVERGED=orange)
- [ ] Last check "Never" on server start; "N min ago" after manual check
- [ ] CONTRIBUTORS table columns: Name, Commits, Last Active, Last Commit Subject (no Role)
- [ ] CONTRIBUTORS empty state: "(no commits on this session yet)"
- [ ] "Last remote sync: N min ago" annotation in MAIN WORKSPACE body (not heading), only when active
- [ ] Known sessions table: Delete button to the left of Join button in each row's Action column
- [ ] Delete Confirmation Modal: same overlay/container pattern as Feature Detail Modal and Kill modal
- [ ] Delete Confirmation Modal: Cancel and Delete buttons; Delete button uses `--purlin-status-error` background with contrasting text
- [ ] Delete Confirmation Modal (AHEAD/DIVERGED): red warning block with `--purlin-status-error` text on subtle red-tinted background, positioned between body text and buttons

## User Testing Discoveries

### [BUG] IN FLIGHT section renders without label and column headers when empty (Discovered: 2026-02-25)
- **Scenario:** Active-Session State Shows Sync Badge and Controls
- **Observed Behavior:** In the active session view, the IN FLIGHT empty state `(none)` appears directly below the CONTRIBUTORS table row with no "IN FLIGHT" section label and no column headers (Branch, Commits Ahead, Last Commit). It looks like a stray element with no context.
- **Expected Behavior:** The IN FLIGHT section should always render its label and column headers. The `(none)` empty state should appear within the labeled table, not as a bare floating text element.
- **Action Required:** Builder
- **Status:** RESOLVED

### [SPEC_DISPUTE] IN FLIGHT table should be removed from Remote Collaboration section (Discovered: 2026-02-25)
- **Scenario:** In-Flight Branches Show Only Remote Isolated Branches
- **Observed Behavior:** The IN FLIGHT table shows remote `isolated/*` branches not yet merged into the collab branch.
- **Expected Behavior:** The IN FLIGHT table serves no useful purpose in this view. Each collaborator's work-in-progress lives in their own `main` branch and is reflected in the CONTRIBUTORS table. Remote isolated branches are private to each collaborator — there is no need to expose them in the shared Remote Collaboration section. The only meaningful comparison is local `main` vs. the remote collab branch head, which is already surfaced by the sync badge.
- **Action Required:** Architect
- **Status:** RESOLVED
- **Resolution:** Accepted. IN FLIGHT table removed from spec (Section 2.3, /status.json schema, automated scenario, visual spec). Policy invariant 2.5 explicitly states isolation branches remain local and are never pushed to remote, making the table perpetually empty under normal workflow. CONTRIBUTORS + sync badge already provide the meaningful collaboration signals.

### [BUG] Sync badge never appears when local main branch does not exist (Discovered: 2026-02-25)
- **Scenario:** Active-Session State Shows Sync Badge and Controls
- **Observed Behavior:** A collaborator cloned the repo directly from the collab branch (`collab/test1`) and started the CDD server. After clicking "Check Remote", the dashboard shows "Run Check Remote to see sync state" with "Last check: just now" — no sync badge is ever displayed. The check ran, but the badge never appeared.
- **Root Cause:** `compute_remote_sync_state()` runs `git log origin/collab/<session>..main --oneline`. When checked out from the collab branch, local `main` does not exist, so the git command fails. The exception is silently caught and `sync_state: None` is returned, causing the dashboard to remain in the pre-check state indefinitely with no error message.
- **Expected Behavior:** When local `main` does not exist, the server should detect this condition and return a meaningful error or guidance (e.g., "local main branch not found — check out main to enable sync tracking") rather than silently returning `sync_state: None` and leaving the user with no actionable feedback.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** `compute_remote_sync_state()` now verifies local `main` ref exists before running log comparisons. Returns `sync_state: "NO_MAIN"` when absent, and the dashboard displays "Local main branch not found (check out main to enable sync tracking)" instead of silently showing no badge.

### [BUG] Active session layout splits controls across multiple rows instead of single line (Discovered: 2026-02-26)
- **Scenario:** Active-Session State Shows Sync Badge and Controls
- **Observed Behavior:** The active session view renders the session name and branch ref on one row, the sync state badge on a second row, and the session dropdown with Disconnect button on a third row. The layout spreads across three lines instead of two.
- **Expected Behavior:** Per Section 2.3, the session row should be a single line: `[session-name ▾] collab/<name> [Disconnect]` -- the dropdown, branch ref, and Disconnect button all on one row. The sync state row (badge + annotation + last-check + Check Remote) should be the second row. Two rows total, not three.
- **Action Required:** Builder
- **Status:** OPEN

### [INTENT_DRIFT] Sync state annotation is ambiguous about perspective (Discovered: 2026-02-25)
- **Scenario:** Active-Session State Shows Sync Badge and Controls
- **Observed Behavior:** The sync state row shows `AHEAD (1 ahead)` when local main has 1 commit not yet pushed to the remote collab branch. The annotation "(1 ahead)" is ambiguous — ahead of what?
- **Expected Behavior:** The annotation should explicitly frame the relationship from the remote's perspective relative to local main. Examples: `AHEAD (Remote is 1 behind local main)`, `BEHIND (Remote is 2 ahead of local main)`, `DIVERGED (Remote is diverged from local main)`. This makes the directionality unambiguous at a glance.
- **Action Required:** Architect
- **Status:** RESOLVED
- **Resolution:** Code already updated in commit 65d5f19 to use remote-perspective framing. Annotation now shows "Remote is N behind/ahead of local main" matching the spec update.

