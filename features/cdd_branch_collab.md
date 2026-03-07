# Feature: CDD Branch Collaboration

> Label: "CDD Branch Collaboration"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_branch_collab.md
> Prerequisite: features/cdd_isolated_teams.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/test_fixture_repo.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd

[TODO]

## 1. Overview

The CDD dashboard provides a BRANCH COLLABORATION section that enables multi-machine collaboration via branches on the hosted remote. The section is always visible in the dashboard (same pattern as ISOLATED TEAMS) and serves as the entry point for creating, joining, and leaving collaboration branches. It renders above ISOLATED TEAMS and LOCAL BRANCH in the section order.

---

## 2. Requirements

### 2.1 Section Positioning and Visibility

The BRANCH COLLABORATION section is always rendered in the dashboard, regardless of configuration or active branch state. It appears in this order:

1. **BRANCH COLLABORATION** (always rendered)
2. **ISOLATED TEAMS** (existing)
3. **LOCAL BRANCH** (existing, renamed from MAIN WORKSPACE)

The section is always visible because it IS the entry point for branch collaboration. Hiding it behind config creates a chicken-and-egg problem (user cannot discover the feature without editing config).

The expanded heading text is always `"BRANCH COLLABORATION"` (plain, no parenthetical). The shortened remote URL appears only on the **collapsed badge** when a branch is actively joined (see Section 2.3). The shortened URL format: remote URL with protocol stripped (`https://`, `git@`, `ssh://`), trailing `.git` removed, and `git@host:path` converted to `host/path`. Example: `https://github.com/rlabarca/purlin.git` becomes `github.com/rlabarca/purlin`. The shortened URL is computed server-side from `git remote get-url <remote>` (where `<remote>` comes from `branch_collab.remote` config, default `"origin"`; falls back to `remote_collab.remote` if `branch_collab` absent).

Exception: if `git remote` returns empty (no remote configured at all), the section body shows "No git remote configured. Add a remote to enable branch collaboration."

### 2.2 State A: No Active Branch (Setup Mode)

When `.purlin/runtime/active_branch` is absent or empty:

**Collapsed badge:** "BRANCH COLLABORATION" (no annotation, no branch count).

**Expanded content (in order):**

1. **Creation row** (always first, same pattern as ISOLATED TEAMS creation row):
   - Label: "Create Branch"
   - Text input: any valid git branch name, 20-char visible field width, unlimited entry length
   - Create button: disabled until valid name. On click -> `POST /branch-collab/create`.
   - Input uses same color scheme as ISOLATED TEAMS name input (same CSS tokens).

2. **Branches table** (below creation row):
   - Populated from `git branch -r` filtered to exclude `HEAD`, `main`/`master`.
   - Columns: Branch | Action
   - Each row has a **Join** button in the Action column.
   - Empty state: "No remote branches found."

3. **Refresh Branches button** (inline with the branches table heading):
   - A **"Refresh Branches"** button positioned to the right of the branches table heading.
   - On click: `POST /branch-collab/fetch-all`.
   - While in-flight: button text changes to "Refreshing..." and is disabled (same guard pattern as "Check Remote").
   - After success: the branches table re-renders with updated branches from refreshed refs.

### 2.3 State B: Active Branch (Operational Mode)

When `.purlin/runtime/active_branch` contains a branch name:

**Collapsed badge:** `"BRANCH COLLABORATION (<shortened-url>)"` where `<shortened-url>` is the remote URL with protocol stripped, trailing `.git` removed, and `git@host:path` converted to `host/path` (same computation as the expanded heading in Section 2.1).

**Expanded content (in order):**

1. **Active branch panel** (replaces creation row):
   - **Branch row (single line):** `[branch-dropdown ▾] [Leave]`. The branch dropdown is a `<select>` populated with all known branches from remote (current branch pre-selected). Changing selection -> `POST /branch-collab/join`. The "Leave" button is right-aligned on the same row -> `POST /branch-collab/leave`. Does NOT delete any branches. Branch remains joinable.
   - **Sync state row:** badge with remote-perspective sync annotation + "Last check: N min ago" (or "Never") + "Check Remote" button (right-aligned): `POST /branch-collab/fetch`. Annotation format: SAME (no annotation), AHEAD -> `"AHEAD (Remote is N behind local)"`, BEHIND -> `"BEHIND (Remote is N ahead of local)"`, DIVERGED -> `"DIVERGED (Remote is N ahead, M behind local)"`. Color: SAME -> green (`--purlin-status-good`), AHEAD/BEHIND -> yellow (`--purlin-status-todo`), DIVERGED -> orange (`--purlin-status-warning`).
   - **Panel alignment:** The branch row and sync state row MUST share a consistent left edge. The dropdown's left edge on Row 1 and the sync badge's left edge on Row 2 MUST be horizontally aligned, giving the active branch panel a coherent vertical alignment.

2. **CONTRIBUTORS table:**
   - Name | Commits | Last Active | Last Commit Subject -- sorted most-recent-first, max 10.
   - Derived from `git log origin/<branch> --format="%ae|%an|%cr|%s"`.
   - Empty state: "(no commits on this branch yet)"

### 2.4 Server Endpoints

Five POST endpoints, following the existing `/isolate/*` pattern:

**`POST /branch-collab/create`** -- `{ "branch": "<name>" }`

1. Validate branch name is a valid git branch name.
2. Abort if the working tree is dirty (uncommitted changes outside `.purlin/`).
3. Read remote from config (`branch_collab.remote`, default `"origin"`; fallback to `remote_collab.remote`).
4. Record the current branch as the base branch (stored in `.purlin/runtime/branch_collab_base_branch`). Create branch `<name>` from HEAD: `git branch <name> HEAD`.
5. Push to remote: `git push <remote> <name>`.
6. Checkout the new branch: `git checkout <name>`.
7. Write branch name to `.purlin/runtime/active_branch`.
8. Return `{ "status": "ok", "branch": "<name>" }`.
9. On push failure: return `{ "error": "..." }`, do NOT write runtime file or checkout.

**`POST /branch-collab/join`** -- `{ "branch": "<name>" }`

1. Abort if the working tree is dirty (uncommitted changes outside `.purlin/`).
2. Verify `origin/<name>` exists in remote tracking refs. If not: `git fetch <remote> <name>`.
3. Checkout the target branch: `git checkout <name>`. If the local branch does not exist, create it tracking the remote: `git checkout -b <name> origin/<name>`.
4. Write branch name to `.purlin/runtime/active_branch`.
5. Return `{ "status": "ok", "branch": "<name>" }`.

**`POST /branch-collab/leave`** -- `{}`

1. Abort if the working tree is dirty (uncommitted changes outside `.purlin/`).
2. Read the stored base branch from `.purlin/runtime/branch_collab_base_branch` (default `main` if absent). Checkout that branch: `git checkout <base-branch>`.
3. Remove/truncate `.purlin/runtime/active_branch` and `.purlin/runtime/branch_collab_base_branch`.
4. Do NOT delete any branches or remote refs.
5. Return `{ "status": "ok" }`.

**`POST /branch-collab/fetch`** -- `{}` (uses active branch)

1. Read active branch from runtime file. Abort if none.
2. `git fetch <remote> <branch>`.
3. Return `{ "status": "ok", "fetched_at": "<ISO timestamp>" }`.
4. "Checking..." label + disabled guard while in flight (same guard pattern as `rcPendingSave`).
5. Auto-fetch: background thread fires after first interval (NOT on startup); boolean lock prevents concurrent fetches; failures logged server-side only.
6. `last_fetch`: in-memory only; resets to null on server restart.

**`POST /branch-collab/fetch-all`** -- `{}`

1. Read remote from config (`branch_collab.remote`, default `"origin"`; fallback to `remote_collab.remote`).
2. Run `git fetch <remote>` (no branch argument -- fetches all refs for the configured remote).
3. Return `{ "status": "ok", "fetched_at": "<ISO timestamp>" }`.
4. Uses the same `_branch_collab_fetch_lock` to prevent concurrent fetches with the active-branch fetch.
5. On failure: return `{ "error": "..." }`.

### 2.5 Sync State Computation

- Uses locally cached remote tracking refs -- never triggers a network fetch during the 5-second poll.
- `git log origin/<branch>..<branch> --oneline` -> commits local branch is ahead.
- `git log <branch>..origin/<branch> --oneline` -> commits remote is ahead.
- SAME/AHEAD/BEHIND/DIVERGED four-state logic (same as ISOLATED TEAMS section). Same-branch comparison is simpler than the previous cross-branch model.
- When remote tracking ref `origin/<branch>` does not exist yet (pre-first-fetch): show inline note "Run Check Remote to see sync state" instead of a badge.

### 2.6 Cross-Section Annotation in LOCAL BRANCH

When an active branch exists, the LOCAL BRANCH section body shows a "Last remote sync: N min ago" line (or "Never synced") below the clean/dirty state line. Absent when no active branch.

NOT appended to the section heading text (per `cdd_isolated_teams.md` Section 2.3 "no annotations on heading").

### 2.7 /status.json Extension

When an active branch exists, the `/status.json` response includes:

```json
{
  "branch_collab": {
    "active_branch": "feature/auth",
    "remote": "origin",
    "sync_state": "AHEAD",
    "commits_ahead": 2,
    "commits_behind": 0,
    "last_fetch": "2026-02-23T14:30:00Z",
    "contributors": [
      { "email": "bob@example.com", "name": "Bob Ramos", "commits": 5, "last_active": "2h ago", "last_subject": "implement task CRUD handlers" }
    ]
  },
  "branch_collab_branches": [
    { "branch": "feature/auth", "active": true, "sync_state": "AHEAD", "commits_ahead": 2, "commits_behind": 0 },
    { "branch": "hotfix/urgent", "active": false, "sync_state": "BEHIND", "commits_ahead": 0, "commits_behind": 3 }
  ]
}
```

`branch_collab`: present only when an active branch exists. Absent otherwise. Sync state computation is unchanged -- it compares local vs `origin/<branch>` regardless of naming convention.

`branch_collab_branches`: always present (may be empty array). Lists all branches discovered from remote tracking refs (filtered to exclude `HEAD`, `main`/`master`). Each entry includes per-branch sync state computed from locally cached refs (same rules as Section 2.5, applied per branch).

### 2.9 Integration Test Fixture Tags

The following fixture tags provide real git branch topology for integration-level tests, replacing mocked subprocess output with actual git state:

| Tag | State Description |
|-----|-------------------|
| `main/cdd_branch_collab/ahead-3` | Branch 3 commits ahead of collaboration branch |
| `main/cdd_branch_collab/behind-2` | Branch 2 commits behind collaboration branch |
| `main/cdd_branch_collab/diverged` | Both branch and collaboration branch have unique commits |
| `main/cdd_branch_collab/same` | Branch at same position as collaboration branch |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: BRANCH Section Always Rendered in Dashboard HTML

    Given the CDD server is running
    And no branch_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section is present in the HTML output

#### Scenario: branch_collab Absent From status.json When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When an agent calls GET /status.json
    Then the response does not contain a branch_collab field

#### Scenario: branch_collab_branches Present In status.json Even When Empty

    Given no collaboration branches exist on the remote
    When an agent calls GET /status.json
    Then the response contains branch_collab_branches as an empty array

#### Scenario: Create Branch Pushes Checks Out and Writes Runtime File

    Given no feature/auth branch exists on the remote
    And the CDD server is running
    And the working tree is clean
    When a POST request is sent to /branch-collab/create with body {"branch": "feature/auth"}
    Then the server creates branch feature/auth from HEAD
    And pushes feature/auth to origin
    And checks out feature/auth locally
    And writes "feature/auth" to .purlin/runtime/active_branch
    And the response contains { "status": "ok", "branch": "feature/auth" }
    And GET /status.json shows branch_collab.sync_state as "SAME"

#### Scenario: Create Branch Blocked When Working Tree Is Dirty

    Given the CDD server is running
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/create with body {"branch": "feature/auth"}
    Then the response contains an error message about dirty working tree
    And no branch is created
    And the current branch is unchanged

#### Scenario: Join Branch Checks Out and Updates Runtime File

    Given feature/auth exists as a remote tracking branch
    And no active branch is set
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the local branch feature/auth is checked out
    And .purlin/runtime/active_branch contains "feature/auth"
    And GET /status.json shows branch_collab.active_branch as "feature/auth"

#### Scenario: Join Branch With Dirty Working Tree Returns Error

    Given the branch "feature/auth" exists as a remote tracking branch
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains an error message about dirty working tree
    And the current branch is unchanged

#### Scenario: Join Branch With Nonexistent Remote Branch Returns Error

    Given no branch "nonexistent" exists as a remote tracking branch
    When a POST request is sent to /branch-collab/join with body {"branch": "nonexistent"}
    Then the response contains an error message
    And no branch checkout occurs

#### Scenario: Leave Checks Out Base Branch and Clears Active Branch

    Given an active branch "feature/auth" is set in .purlin/runtime/active_branch
    And the working tree is clean
    When a POST request is sent to /branch-collab/leave
    Then the stored base branch is checked out
    And .purlin/runtime/active_branch is empty or absent
    And GET /status.json does not contain a branch_collab field
    And feature/auth still exists on the remote

#### Scenario: Leave Blocked When Working Tree Is Dirty

    Given an active branch "feature/auth" is set
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/leave
    Then the response contains an error message about dirty working tree
    And the current branch remains feature/auth
    And .purlin/runtime/active_branch still contains "feature/auth"

#### Scenario: Switch Branch via Join Updates Active Branch

    Given an active branch "feature/auth" is set
    And hotfix/urgent exists as a remote tracking branch
    When a POST request is sent to /branch-collab/join with body {"branch": "hotfix/urgent"}
    Then .purlin/runtime/active_branch contains "hotfix/urgent"
    And GET /status.json shows branch_collab.active_branch as "hotfix/urgent"

#### Scenario: Sync State SAME When Local and Remote Are Identical

    Given an active branch "feature/auth" is set
    And local feature/auth and origin/feature/auth point to the same commit
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "SAME"
    And branch_collab.commits_ahead is 0
    And branch_collab.commits_behind is 0

#### Scenario: Sync State AHEAD When Local Has Unpushed Commits

    Given an active branch "feature/auth" is set
    And local feature/auth has 3 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "AHEAD"
    And branch_collab.commits_ahead is 3

#### Scenario: Sync State BEHIND When Remote Has New Commits

    Given an active branch "feature/auth" is set
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "BEHIND"
    And branch_collab.commits_behind is 2

#### Scenario: Sync State DIVERGED When Both Sides Have Commits

    Given an active branch "feature/auth" is set
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "DIVERGED"
    And branch_collab.commits_ahead is 1
    And branch_collab.commits_behind is 2

#### Scenario: Contributors Derived From Git Log Sorted Most-Recent-First

    Given an active branch "feature/auth" is set
    And origin/feature/auth has commits from two different authors
    When an agent calls GET /status.json
    Then branch_collab.contributors has entries sorted by most-recent-first
    And each entry has email, name, commits, last_active, and last_subject fields
    And the contributors list has at most 10 entries

#### Scenario: Manual Check Updates last_fetch Timestamp

    Given an active branch "feature/auth" is set
    And branch_collab.last_fetch is null (server just started)
    When a POST request is sent to /branch-collab/fetch
    Then the response contains fetched_at with an ISO timestamp
    And subsequent GET /status.json shows branch_collab.last_fetch as a non-null value

#### Scenario: 5-Second Status Poll Triggers Zero Git Fetch Calls

    Given an active branch "feature/auth" is set
    And auto_fetch_interval is 0 in the test config
    When the dashboard polls GET /status.json 3 times at 5-second intervals
    Then no git fetch commands are executed during those polls

#### Scenario: Per-Branch Sync State in branch_collab_branches

    Given feature/auth exists as a remote tracking branch
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When an agent calls GET /status.json
    Then branch_collab_branches contains an entry for "feature/auth"
    And that entry has sync_state "BEHIND" and commits_behind 2

#### Scenario: BRANCH COLLABORATION Section Always Visible in Dashboard HTML

    Given the CDD server is running
    And no branch_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section heading is present in the HTML output
    And the section is rendered above the ISOLATED TEAMS section in the DOM

#### Scenario: No-Active-Branch Shows Creation Row and Branches Table

    Given no file exists at .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section contains a creation row with "Create Branch" label
    And the creation row contains a text input and a Create button
    And a branches table element is present below the creation row

#### Scenario: BRANCH COLLABORATION Renders Above ISOLATED TEAMS in DOM Order

    Given the CDD server is running
    And both BRANCH COLLABORATION and ISOLATED TEAMS sections exist in the HTML
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section appears before the ISOLATED TEAMS section in the HTML output

#### Scenario: Last Remote Sync Annotation Present in LOCAL BRANCH Body

    Given an active branch "feature/auth" is set in .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the LOCAL BRANCH section body contains a "Last remote sync" annotation element
    And the annotation appears below the clean/dirty state line

#### Scenario: status.json Reflects Active Branch

    Given the branch "feature/auth" has been joined via /branch-collab/join
    When an agent calls GET /status.json
    Then branch_collab.active_branch is "feature/auth"

#### Scenario: Branches Table Populated in HTML

    Given no file exists at .purlin/runtime/active_branch
    And remote tracking branches "origin/feature/auth" and "origin/hotfix/urgent" exist
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section contains a branches table with "feature/auth" and "hotfix/urgent" rows

#### Scenario: Active-Branch HTML Shows Branch Dropdown and Sync Badge

    Given an active branch "feature/auth" is set in .purlin/runtime/active_branch
    And feature/auth exists as a remote tracking branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section contains a branch-name select dropdown
    And "feature/auth" is an option in the branch dropdown
    And a "Leave" button element is present in the active branch panel
    And a sync state badge element is present
    And a "Check Remote" button element is present

#### Scenario: No-Active-Branch HTML Differs From Active-Branch HTML

    Given no file exists at .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section contains a creation row with "Create Branch" label
    And the section does not contain a branch-name select dropdown
    And the section does not contain a "Leave" button
    And the section does not contain a sync state badge

#### Scenario: Refresh Branches Button Fetches All Remote Refs

    Given the CDD server is running with no active branch
    And the branches table shows 1 branch
    When a new branch is pushed to the remote from another machine
    And a POST request is sent to /branch-collab/fetch-all
    Then the response contains { "status": "ok" } with a fetched_at timestamp
    And the branches table re-renders with the newly discovered branch

#### Scenario: Collapsed Badge Shows URL When Branch Active

    Given the CDD server is running
    And an active branch is set in .purlin/runtime/active_branch
    And the git remote "origin" is configured with URL "https://github.com/rlabarca/purlin.git"
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION (github.com/rlabarca/purlin)"

#### Scenario: Collapsed Badge Shows Plain Title When No Branch Active

    Given the CDD server is running
    And no file exists at .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION"

#### Scenario: Collapsed Badge Shows Plain Title When No Remote Configured

    Given the CDD server is running
    And an active branch is set in .purlin/runtime/active_branch
    And no git remote is configured
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION"

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Visual Specification

### Screen: CDD Dashboard -- Branch Collaboration Section

- **Reference:** N/A
- [ ] BRANCH COLLABORATION section position: above ISOLATED TEAMS, above LOCAL BRANCH
- [ ] Section always visible (collapsible, same indent as peers)
- [ ] No-active-branch: creation row "Create Branch [input] [Create]" + branches table
- [ ] Active-branch row 1: branch-name dropdown + Leave button (right-aligned), all on one line
- [ ] Active-branch row 2: sync badge + annotation + last-check timestamp + Check Remote button (right-aligned)
- [ ] Active-branch panel: Row 1 dropdown left edge and Row 2 sync badge left edge are horizontally aligned
- [ ] "Checking..." guard state while fetch in flight
- [ ] Four sync state badge colors (matching ISOLATED TEAMS color scheme: SAME=green, AHEAD/BEHIND=yellow, DIVERGED=orange)
- [ ] Last check "Never" on server start; "N min ago" after manual check
- [ ] CONTRIBUTORS table columns: Name, Commits, Last Active, Last Commit Subject (no Role)
- [ ] CONTRIBUTORS empty state: "(no commits on this branch yet)"
- [ ] "Last remote sync: N min ago" annotation in LOCAL BRANCH body (not heading), only when active
- [ ] Sync badge colors: SAME=green (`--purlin-status-good`), AHEAD/BEHIND=yellow (`--purlin-status-todo`), DIVERGED=orange (`--purlin-status-warning`) -- matching ISOLATED TEAMS color scheme
- [ ] Create Branch click transitions section from setup mode (creation row + branches table) to active mode (branch dropdown + sync badge)
- [ ] Leave click transitions section from active mode back to setup mode (creation row + branches table visible)
- [ ] "Refresh Branches" button positioned to the right of the branches table heading in setup mode
- [ ] "Refresh Branches" button shows "Refreshing..." text and is disabled while fetch-all is in flight
- [ ] Collapsed badge shows "BRANCH COLLABORATION (github.com/rlabarca/purlin)" when a branch is active and remote is configured
- [ ] Collapsed badge shows plain "BRANCH COLLABORATION" when no branch is active
- [ ] Collapsed badge shows plain "BRANCH COLLABORATION" when branch is active but no remote is configured

## User Testing Discoveries



