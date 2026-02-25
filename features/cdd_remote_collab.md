# Feature: CDD Remote Collaboration

> Label: "Tool: CDD Remote Collaboration"
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
   - Each row has a **Join** button -> `POST /remote-collab/switch`.
   - Empty state: "No remote collab sessions found."

### 2.3 State B: Active Session (Operational Mode)

When `.purlin/runtime/active_remote_session` contains a session name:

**Collapsed badge:** `"<session-name> <STATE>"` where STATE is the sync state. Color: SAME -> green (`--purlin-status-good`), AHEAD/BEHIND -> yellow (`--purlin-status-todo`), DIVERGED -> orange (`--purlin-status-warning`). Same tokens as ISOLATED TEAMS.

**Expanded content (in order):**

1. **Active session panel** (replaces creation row):
   - Session name + branch displayed prominently.
   - Sync state row: SAME/AHEAD/BEHIND/DIVERGED badge + "Last check: N min ago" (or "Never").
   - "Check Remote" button (right-aligned): `POST /remote-collab/fetch`.
   - "Switch Session" dropdown: `<select>` populated with all known sessions from remote. Changing selection -> `POST /remote-collab/switch`.
   - "Disconnect" button: clears active session -> `POST /remote-collab/disconnect`. Does NOT delete any branches. Session remains joinable.

2. **CONTRIBUTORS table:**
   - Name | Commits | Last Active | Last Commit Subject -- sorted most-recent-first, max 10.
   - Derived from `git log origin/collab/<session> --format="%ae|%an|%cr|%s"`.
   - Empty state: "(no commits on this session yet)"

3. **IN FLIGHT table:**
   - Branch | Commits Ahead | Last Commit -- remote `isolated/*` branches not yet merged to the collab branch. Derived from `git branch -r --no-merged origin/collab/<session>` filtered to `isolated/` prefix.
   - No Role column -- isolation names have no role assignment.
   - Empty state: "(none)"

### 2.4 Server Endpoints

Four new POST endpoints, following the existing `/isolate/*` pattern:

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
    ],
    "in_flight_branches": [
      { "branch": "isolated/feat1", "commits_ahead": 3, "last_commit": "abc1234 add sort scenarios (45 min ago)" }
    ]
  },
  "remote_collab_sessions": [
    { "name": "v0.5-sprint", "branch": "collab/v0.5-sprint", "active": true },
    { "name": "hotfix-auth", "branch": "collab/hotfix-auth", "active": false }
  ]
}
```

`remote_collab`: present only when an active session exists. Absent otherwise.

`remote_collab_sessions`: always present (may be empty array). Lists all sessions discovered from remote tracking refs.

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

#### Scenario: In-Flight Branches Show Only Remote Isolated Branches

    Given an active session "v0.5-sprint" is set
    And remote has branch isolated/feat1 not merged into origin/collab/v0.5-sprint
    And remote has branch feature/other not merged into origin/collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab.in_flight_branches contains an entry for isolated/feat1
    And remote_collab.in_flight_branches does not contain an entry for feature/other

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
    Then the session name and branch are displayed
    And a sync state badge is visible
    And a "Check Remote" button is present
    And a "Switch Session" dropdown is present
    And a "Disconnect" button is present

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

---

## 4. Visual Specification

### Screen: CDD Dashboard -- Remote Collaboration Section

- **Reference:** N/A
- [ ] REMOTE COLLABORATION section position: above ISOLATED TEAMS, above MAIN WORKSPACE
- [ ] Section always visible (collapsible, same indent as peers)
- [ ] No-active-session: creation row "Start Remote Session [input] [Create]" + known sessions table
- [ ] Active-session: session name + branch, sync badge, Check Remote button, Switch dropdown, Disconnect
- [ ] "Checking..." guard state while fetch in flight
- [ ] Four sync state badge colors (matching ISOLATED TEAMS color scheme: SAME=green, AHEAD/BEHIND=yellow, DIVERGED=orange)
- [ ] Last check "Never" on server start; "N min ago" after manual check
- [ ] CONTRIBUTORS table columns: Name, Commits, Last Active, Last Commit Subject (no Role)
- [ ] IN FLIGHT table columns: Branch, Commits Ahead, Last Commit (no Role)
- [ ] Empty state messages for both tables
- [ ] "Last remote sync: N min ago" annotation in MAIN WORKSPACE body (not heading), only when active

## User Testing Discoveries

### [BUG] IN FLIGHT section renders without label and column headers when empty (Discovered: 2026-02-25)
- **Scenario:** Active-Session State Shows Sync Badge and Controls
- **Observed Behavior:** In the active session view, the IN FLIGHT empty state `(none)` appears directly below the CONTRIBUTORS table row with no "IN FLIGHT" section label and no column headers (Branch, Commits Ahead, Last Commit). It looks like a stray element with no context.
- **Expected Behavior:** The IN FLIGHT section should always render its label and column headers. The `(none)` empty state should appear within the labeled table, not as a bare floating text element.
- **Action Required:** Builder
- **Status:** OPEN

### [INTENT_DRIFT] Sync state annotation is ambiguous about perspective (Discovered: 2026-02-25)
- **Scenario:** Active-Session State Shows Sync Badge and Controls
- **Observed Behavior:** The sync state row shows `AHEAD (1 ahead)` when local main has 1 commit not yet pushed to the remote collab branch. The annotation "(1 ahead)" is ambiguous — ahead of what?
- **Expected Behavior:** The annotation should explicitly frame the relationship from the remote's perspective relative to local main. Examples: `AHEAD (Remote is 1 behind local main)`, `BEHIND (Remote is 2 ahead of local main)`, `DIVERGED (Remote is diverged from local main)`. This makes the directionality unambiguous at a glance.
- **Action Required:** Architect
- **Status:** OPEN

