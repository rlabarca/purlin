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

[TODO] <!-- reset: Builder must implement HEAD-based sync, operation modals, --prune -->

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

The expanded heading text is always `"BRANCH COLLABORATION"` (plain, no parenthetical). The **collapsed badge** always includes the shortened remote URL when a remote is configured: `"BRANCH COLLABORATION (<shortened-url>)"`, regardless of whether a branch is actively joined. The remote URL is always relevant since the Refresh Branches button and all branch operations target that remote. The shortened URL format: remote URL with protocol stripped (`https://`, `git@`, `ssh://`), trailing `.git` removed, and `git@host:path` converted to `host/path`. Example: `https://github.com/rlabarca/purlin.git` becomes `github.com/rlabarca/purlin`. The shortened URL is computed server-side from `git remote get-url <remote>` (where `<remote>` comes from `branch_collab.remote` config, default `"origin"`; falls back to `remote_collab.remote` if `branch_collab` absent). When no remote is configured, the collapsed badge shows plain `"BRANCH COLLABORATION"`.

Exception: if `git remote` returns empty (no remote configured at all), the section body shows "No git remote configured. Add a remote to enable branch collaboration."

### 2.2 State A: No Active Branch (Setup Mode)

When `.purlin/runtime/active_branch` is absent or empty:

**Collapsed badge:** `"BRANCH COLLABORATION (<shortened-url>)"` when a remote is configured (see Section 2.1 for URL format). Plain `"BRANCH COLLABORATION"` when no remote is configured.

**Expanded content (in order):**

1. **Creation row** (always first, same pattern as ISOLATED TEAMS creation row):
   - Label: "Create Branch"
   - Text input: any valid git branch name, 20-char visible field width, unlimited entry length
   - Create button: disabled until valid name. On click -> `POST /branch-collab/create`.
   - Input uses same color scheme as ISOLATED TEAMS name input (same CSS tokens).

2. **Branches table** (below creation row):
   - Populated from `git branch -r` filtered to exclude `HEAD`, `main`/`master`.
   - Columns: Branch | State | Action
   - The **State** column shows the per-branch sync state badge using the same styling as the active-branch sync badge: EMPTY=normal text (`--purlin-fg`, no badge), SAME=green, AHEAD/BEHIND=yellow, DIVERGED=orange. State is computed from the `branch_collab_branches` data (Section 2.7).
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
   - **Sync state row:** badge with remote-perspective sync annotation + "Last check: N min ago" (or "Never") + "Check Remote" button (right-aligned): `POST /branch-collab/fetch`. Annotation format: EMPTY (no annotation), SAME (no annotation), AHEAD -> `"AHEAD (Remote is N behind local)"`, BEHIND -> `"BEHIND (Remote is N ahead of local)"`, DIVERGED -> `"DIVERGED (Remote is N ahead, M behind local)"`. Color: EMPTY -> normal text (`--purlin-fg`, no badge background), SAME -> green (`--purlin-status-good`), AHEAD/BEHIND -> yellow (`--purlin-status-todo`), DIVERGED -> orange (`--purlin-status-warning`).
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

Join MUST reconcile local and remote state before completing the checkout. A join is not just a `git checkout` — it is a fetch + reconcile + checkout sequence. The reconciliation strategy depends on the sync state between the local and remote versions of the target branch.

1. Abort if the working tree is dirty (uncommitted changes outside `.purlin/`).
2. Fetch the target branch from remote: `git fetch <remote> <name>`. If `origin/<name>` does not exist after fetch, return error.
3. Check if a local branch `<name>` already exists.
4. **If no local branch exists:** Create it tracking the remote: `git checkout -b <name> origin/<name>`. No reconciliation needed — skip to step 8.
5. **If local branch exists:** Compute sync state between local `<name>` and `origin/<name>`:
   - **SAME:** No reconciliation needed. Checkout: `git checkout <name>`.
   - **BEHIND (remote is ahead of local):** Fast-forward local to remote. Checkout then fast-forward: `git checkout <name> && git merge --ff-only origin/<name>`. This is always safe because the local branch is a strict ancestor of the remote. Include `"reconciled": "fast-forward"` in the response.
   - **AHEAD (local is ahead of remote):** Checkout: `git checkout <name>`. Include `"action_required": "push"` and `"warning": "Local branch has N unpushed commits — run /pl-remote-push to sync remote"` in the response. The modal should display this prominently so the user knows to push.
   - **DIVERGED (both have unique commits):** Checkout: `git checkout <name>`. Do NOT attempt an inline merge — diverged state requires proper conflict resolution. Include `"action_required": "pull"` and `"warning": "Branch is diverged — run /pl-remote-pull to reconcile"` in the response. The modal should display this as a required next step.
6. Record the base branch (current branch before checkout) in `.purlin/runtime/branch_collab_base_branch` if not already set.
7. Write branch name to `.purlin/runtime/active_branch`.
8. Return `{ "status": "ok", "branch": "<name>" }` (plus optional `"action_required"` and `"warning"` fields per step 5).

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
2. Run `git fetch --prune <remote>` (no branch argument -- fetches all refs for the configured remote). The `--prune` flag removes local tracking refs for branches that no longer exist on the remote, ensuring deleted branches disappear from the branches table after refresh.
3. Return `{ "status": "ok", "fetched_at": "<ISO timestamp>" }`.
4. Uses the same `_branch_collab_fetch_lock` to prevent concurrent fetches with the active-branch fetch.
5. On failure: return `{ "error": "..." }`.

### 2.5 Sync State Computation

- Uses locally cached remote tracking refs -- never triggers a network fetch during the 5-second poll.
- `git log origin/<branch>..<branch> --oneline` -> commits local branch is ahead.
- `git log <branch>..origin/<branch> --oneline` -> commits remote is ahead.
- EMPTY/SAME/AHEAD/BEHIND/DIVERGED five-state logic. For branches in the branches table (setup mode, no local checkout), sync state is computed by comparing `origin/<branch>` against the current HEAD:
  - `git log HEAD..origin/<branch> --oneline` -> commits the branch has that HEAD does not.
  - `git log origin/<branch>..HEAD --oneline` -> commits HEAD has that the branch does not.
  - **EMPTY:** Both directions return zero lines AND `origin/<branch>` and HEAD point to the same commit. The branch was just created and has no work. Shows `"EMPTY"` in normal text color (`--purlin-fg`) without a badge background.
  - **SAME:** Both directions return zero lines (identical to EMPTY detection -- in practice, EMPTY and SAME are equivalent for remote-only branches; use EMPTY as the label since it better communicates the branch state to the user).
  - **AHEAD:** Branch has unique commits HEAD does not, but HEAD has none the branch lacks. Shows yellow badge.
  - **BEHIND:** HEAD has commits the branch lacks, but the branch has none HEAD lacks. This is a stale branch. Shows yellow badge.
  - **DIVERGED:** Both have unique commits. Shows orange badge.
- For the active branch panel (operational mode), sync state compares local vs remote of the same branch (existing logic): `git log origin/<branch>..<branch>` and `git log <branch>..origin/<branch>`. SAME/AHEAD/BEHIND/DIVERGED four-state. EMPTY applies when the branch has zero unique commits relative to main (`git log main..<branch>` returns zero lines AND `git log <branch>..main` returns zero lines -- both directions must be zero, meaning branch tip equals main tip).
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

`branch_collab`: present only when an active branch exists. Absent otherwise. `sync_state` may be `"EMPTY"`, `"SAME"`, `"AHEAD"`, `"BEHIND"`, or `"DIVERGED"`. EMPTY indicates the branch has zero commits relative to the base branch.

`branch_collab_branches`: always present (may be empty array). Lists all branches discovered from remote tracking refs (filtered to exclude `HEAD`, `main`/`master`). Each entry includes per-branch sync state computed from locally cached refs (same rules as Section 2.5, applied per branch). The `sync_state` field may include `"EMPTY"` for branches with no commits relative to main.

### 2.8 Operation Modals (Joining / Leaving / Creating)

Branch operations (join, leave, create, switch) involve git checkouts, fetches, and pushes that can take several seconds. During this time the user sees no feedback. Operation modals provide a blocking progress indicator with inline error reporting.

**Modal HTML:** A single shared modal element (`id="bc-op-modal-overlay"`) is reused for all branch operations. It follows the Kill Isolation modal pattern (inline styles, lightweight, no tabs).

**Structure:**

```
+---------------------------------------+
|  <title>                          [X]  |
|---------------------------------------|
|                                       |
|  <spinner>  <status message>          |
|                                       |
|  <error block — hidden by default>    |
|                                       |
|                         [Close]       |
+---------------------------------------+
```

- **Title:** Operation-specific. "Joining Branch", "Leaving Branch", or "Creating Branch".
- **Spinner:** A CSS-only animated spinner (small, inline with status message). Hidden when the operation completes (success or error).
- **Status message:** Operation-specific progress text, updated as the operation progresses through steps:
  - Join/Switch: Initial `"Fetching <branch>..."`, then `"Reconciling with remote..."` (only shown when local branch exists and is BEHIND or DIVERGED), then `"Switching to <branch>..."`. Uses "Switching" for both join and switch since the git operation is identical.
  - Leave: `"Returning to <base-branch>..."`
  - Create: `"Creating <branch>..."`
- **Error block:** Hidden by default. On error, the spinner is replaced with an error icon (red text), the status message updates to the error text from the server response (`d.error`), and the block becomes visible. The error text uses `color: var(--purlin-status-error)`.
- **Close button:** Always visible in the footer. During progress, clicking Close is a no-op (button disabled). On completion (success or error), the button is enabled.
- **Auto-close on success:** When the operation succeeds with no `action_required` field, the modal closes automatically after a brief delay (400ms) and `refreshStatus()` is called. The user sees the spinner resolve to a success state momentarily before the modal dismisses.
- **Hold on action_required:** When the response includes an `action_required` field (e.g., join on DIVERGED or AHEAD branch), the modal does NOT auto-close. Instead, it displays the warning message prominently (styled distinctly from errors — informational, not red). The Close button is enabled and the user must explicitly dismiss the modal. `refreshStatus()` is called on dismissal.
- **No close on overlay click during progress:** While the operation is in flight, clicking the overlay background does NOT close the modal. After completion (success or error), overlay click closes normally.
- **Escape key:** Same behavior as overlay click -- blocked during progress, allowed after completion.

**JavaScript integration:**

The existing `joinBranch()`, `leaveBranch()`, `switchBranch()`, and `createBranch()` functions are updated to:

1. Open the modal with the appropriate title and status message BEFORE sending the fetch request.
2. On success: briefly show a success state, then auto-close and call `refreshStatus()`.
3. On error: update the modal to show the error message, enable Close button.
4. On network failure (fetch `.catch`): show "Request failed -- check your connection" as the error message.

The `bcRemotePending` guard is preserved -- the modal is the visual manifestation of that guard state.

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

#### Scenario: Join Branch Fetches Then Checks Out and Updates Runtime File

    Given feature/auth exists as a remote tracking branch
    And no local branch feature/auth exists
    And no active branch is set
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth before checkout
    And a local branch feature/auth is created tracking origin/feature/auth
    And .purlin/runtime/active_branch contains "feature/auth"
    And GET /status.json shows branch_collab.active_branch as "feature/auth"

#### Scenario: Join Branch Fast-Forwards When Local Is Behind Remote

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth
    And local feature/auth is checked out
    And local feature/auth is fast-forwarded to origin/feature/auth
    And the response contains "reconciled": "fast-forward"
    And .purlin/runtime/active_branch contains "feature/auth"

#### Scenario: Join Branch Routes Diverged to pl-remote-pull

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has 1 commit not in origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth
    And local feature/auth is checked out (no inline merge attempted)
    And the response contains "action_required": "pull"
    And the response contains a warning to run /pl-remote-pull
    And .purlin/runtime/active_branch contains "feature/auth"

#### Scenario: Join Branch Warns When Local Is Ahead and Suggests Push

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And local feature/auth has 3 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth
    And local feature/auth is checked out
    And the response contains "action_required": "push"
    And the response contains a warning to run /pl-remote-push
    And .purlin/runtime/active_branch contains "feature/auth"

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

#### Scenario: Switch Branch via Join Fetches Reconciles and Updates Active Branch

    Given an active branch "feature/auth" is set
    And hotfix/urgent exists as a remote tracking branch
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "hotfix/urgent"}
    Then git fetch is called for hotfix/urgent before checkout
    And hotfix/urgent is checked out with reconciliation if needed
    And .purlin/runtime/active_branch contains "hotfix/urgent"
    And GET /status.json shows branch_collab.active_branch as "hotfix/urgent"

#### Scenario: Sync State EMPTY When Branch Tip Equals Main Tip

    Given an active branch "feature/empty" is set
    And feature/empty tip equals main tip (both directions of git log return zero lines)
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "EMPTY"
    And branch_collab.commits_ahead is 0
    And branch_collab.commits_behind is 0

#### Scenario: EMPTY Badge Rendered Without Badge Background

    Given an active branch "feature/empty" is set
    And feature/empty tip equals main tip
    When the dashboard HTML is generated
    Then the sync state position shows "EMPTY" in normal text color (--purlin-fg)
    And the text does not use a badge class (no st-good, st-todo, st-disputed)

#### Scenario: Branches Table Shows BEHIND For Stale Remote Branch

    Given no active branch is set
    And origin/RC0.8.0 exists as a remote tracking branch
    And origin/RC0.8.0 is a strict ancestor of HEAD (HEAD has commits RC0.8.0 does not)
    And origin/RC0.8.0 has no unique commits beyond HEAD
    When the dashboard HTML is generated
    Then the branches table shows "BEHIND" badge for RC0.8.0
    And the badge uses yellow color (--purlin-status-todo)

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

#### Scenario: Collapsed Badge Always Shows URL When Remote Configured

    Given the CDD server is running
    And the git remote "origin" is configured with URL "https://github.com/rlabarca/purlin.git"
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION (github.com/rlabarca/purlin)"
    And this applies regardless of whether an active branch is set

#### Scenario: Collapsed Badge Shows Plain Title When No Remote Configured

    Given the CDD server is running
    And no git remote is configured
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION"

#### Scenario: Join Branch Shows Operation Modal With Multi-Step Progress

    Given the CDD server is running
    And an active branch is not set
    And feature/auth exists as a remote tracking branch
    When the user clicks the Join button for feature/auth
    Then an operation modal appears with title "Joining Branch"
    And the modal initially shows a spinner with text "Fetching feature/auth..."
    And the status message updates to "Switching to feature/auth..." during checkout
    And the Close button is disabled while the operation is in flight
    And clicking the overlay background does not close the modal

#### Scenario: Join Branch Modal Shows Reconciliation Step for Behind

    Given the CDD server is running
    And a local branch feature/auth exists that is BEHIND origin/feature/auth
    When the user clicks the Join button for feature/auth
    Then the modal status message progresses through "Fetching feature/auth..." then "Reconciling with remote..." then "Switching to feature/auth..."

#### Scenario: Join Branch Modal Shows Action Required for Diverged

    Given the CDD server is running
    And a local branch feature/auth exists that is DIVERGED from origin/feature/auth
    When the user clicks the Join button for feature/auth
    Then the modal completes successfully (branch is joined)
    And the modal displays a prominent message: "Branch is diverged — run /pl-remote-pull to reconcile"
    And the message persists until the user dismisses the modal

#### Scenario: Join Branch Modal Shows Action Required for Ahead

    Given the CDD server is running
    And a local branch feature/auth exists that is AHEAD of origin/feature/auth
    When the user clicks the Join button for feature/auth
    Then the modal completes successfully (branch is joined)
    And the modal displays a message: "Local branch has N unpushed commits — run /pl-remote-push to sync remote"

#### Scenario: Join Branch Modal Auto-Closes on Success

    Given the operation modal is showing for a join operation
    When the server returns { "status": "ok" }
    Then the modal auto-closes after a brief delay
    And refreshStatus() is called to update the dashboard

#### Scenario: Join Branch Modal Shows Error on Failure

    Given the operation modal is showing for a join operation
    When the server returns { "status": "error", "error": "Working tree has uncommitted changes" }
    Then the spinner is hidden
    And the status message shows "Working tree has uncommitted changes" in error color
    And the Close button is enabled
    And clicking Close dismisses the modal

#### Scenario: Join Branch Modal Auto-Close Delayed When Action Required

    Given the operation modal is showing for a join on a DIVERGED branch
    When the server returns { "status": "ok", "action_required": "pull" }
    Then the modal does NOT auto-close (unlike a clean success)
    And the user must click Close or acknowledge the action required message
    And after dismissal refreshStatus() is called to update the dashboard

#### Scenario: Leave Branch Shows Operation Modal During Request

    Given the CDD server is running
    And an active branch "feature/auth" is set
    When the user clicks the Leave button
    Then an operation modal appears with title "Leaving Branch"
    And the modal shows a spinner with text "Returning to main..."

#### Scenario: Leave Branch Modal Shows Error on Dirty Working Tree

    Given the operation modal is showing for a leave operation
    When the server returns an error about dirty working tree
    Then the spinner is hidden
    And the error message is displayed in the modal
    And the Close button is enabled

#### Scenario: Create Branch Shows Operation Modal During Request

    Given the CDD server is running
    And a valid branch name is entered in the creation input
    When the user clicks the Create button
    Then an operation modal appears with title "Creating Branch"
    And the modal shows a spinner with text "Creating feature/new..."

#### Scenario: Switch Branch Shows Operation Modal During Request

    Given the CDD server is running
    And an active branch "feature/auth" is set
    When the user selects "hotfix/urgent" from the branch dropdown
    Then an operation modal appears with title "Joining Branch"
    And the modal initially shows a spinner with text "Fetching hotfix/urgent..."
    And the status message updates through reconciliation and checkout steps

#### Scenario: Operation Modal Blocks Escape Key During Progress

    Given the operation modal is showing with a spinner (in-flight)
    When the user presses the Escape key
    Then the modal remains open
    And the operation continues

#### Scenario: Network Failure Shows Connection Error in Modal

    Given the operation modal is showing for any branch operation
    When the fetch request fails due to a network error
    Then the modal shows "Request failed -- check your connection" in error color
    And the Close button is enabled

#### Scenario: Refresh Branches Reflects Deleted Remote Branches

    Given the CDD server is running with no active branch
    And the branches table shows branches "feature/auth" and "hotfix/urgent"
    And "hotfix/urgent" has been deleted from the remote
    When a POST request is sent to /branch-collab/fetch-all
    And the branches table re-renders
    Then "hotfix/urgent" is no longer shown in the branches table
    And "feature/auth" is still shown in the branches table

#### Scenario: Refresh Branches Reflects Newly Added Remote Branches

    Given the CDD server is running with no active branch
    And the branches table shows only "feature/auth"
    And "feature/new" has been pushed to the remote from another machine
    When a POST request is sent to /branch-collab/fetch-all
    And the branches table re-renders
    Then "feature/new" is shown in the branches table
    And "feature/auth" is still shown in the branches table

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
- [ ] Five sync states: EMPTY=normal text (no badge background), SAME=green, AHEAD/BEHIND=yellow, DIVERGED=orange
- [ ] Last check "Never" on server start; "N min ago" after manual check
- [ ] CONTRIBUTORS table columns: Name, Commits, Last Active, Last Commit Subject (no Role)
- [ ] CONTRIBUTORS empty state: "(no commits on this branch yet)"
- [ ] "Last remote sync: N min ago" annotation in LOCAL BRANCH body (not heading), only when active
- [ ] Sync badge colors: EMPTY=normal text (`--purlin-fg`, no badge), SAME=green (`--purlin-status-good`), AHEAD/BEHIND=yellow (`--purlin-status-todo`), DIVERGED=orange (`--purlin-status-warning`)
- [ ] Create Branch click transitions section from setup mode (creation row + branches table) to active mode (branch dropdown + sync badge)
- [ ] Leave click transitions section from active mode back to setup mode (creation row + branches table visible)
- [ ] "Refresh Branches" button positioned to the right of the branches table heading in setup mode
- [ ] "Refresh Branches" button shows "Refreshing..." text and is disabled while fetch-all is in flight
- [ ] Collapsed badge always shows "BRANCH COLLABORATION (github.com/rlabarca/purlin)" when remote is configured (regardless of active branch state)
- [ ] Collapsed badge shows plain "BRANCH COLLABORATION" only when no remote is configured
- [ ] Operation modal: centered overlay with semi-transparent background, matching Kill Isolation modal styling
- [ ] Operation modal: CSS spinner (small, inline) visible during in-flight state
- [ ] Operation modal: join/switch status message updates through steps: "Fetching..." -> "Reconciling..." (if needed) -> "Switching..."
- [ ] Operation modal: spinner hidden and replaced with error text (red) on failure
- [ ] Operation modal: Close button disabled (greyed) during in-flight, enabled on completion/error
- [ ] Operation modal: auto-closes on success with brief visible transition (~400ms)
- [ ] Refresh Branches: stale branches (deleted from remote) are removed from the table after fetch-all

## User Testing Discoveries



