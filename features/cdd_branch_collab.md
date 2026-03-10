# Feature: CDD Branch Collaboration

> Label: "CDD Branch Collaboration"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_branch_collab.md
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/test_fixture_repo.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd

[TODO] <!-- reset: Builder must implement HEAD-based sync, operation modals, --prune -->

## 1. Overview

The CDD dashboard provides a BRANCH COLLABORATION section that enables multi-machine collaboration via branches on the hosted remote. The section is always visible in the dashboard and serves as the entry point for creating, joining, and leaving collaboration branches. It renders above LOCAL BRANCH in the section order.

---

## 2. Requirements

### 2.1 Section Positioning and Visibility

The BRANCH COLLABORATION section is always rendered in the dashboard, regardless of configuration or active branch state. It appears in this order:

1. **BRANCH COLLABORATION** (always rendered)
2. **LOCAL BRANCH** (existing, renamed from MAIN WORKSPACE)

The section is always visible because it IS the entry point for branch collaboration. Hiding it behind config creates a chicken-and-egg problem (user cannot discover the feature without editing config).

The expanded heading text is always `"BRANCH COLLABORATION"` (plain, no parenthetical). The **collapsed badge** always includes the shortened remote URL when a remote is configured: `"BRANCH COLLABORATION (<shortened-url>)"`, regardless of whether a branch is actively joined. The remote URL is always relevant since the Refresh Branches button and all branch operations target that remote. The shortened URL format: remote URL with protocol stripped (`https://`, `git@`, `ssh://`), trailing `.git` removed, and `git@host:path` converted to `host/path`. Example: `https://github.com/rlabarca/purlin.git` becomes `github.com/rlabarca/purlin`. The shortened URL is computed server-side from `git remote get-url <remote>` (where `<remote>` comes from `branch_collab.remote` config, default `"origin"`; falls back to `remote_collab.remote` if `branch_collab` absent). When no remote is configured, the collapsed badge shows plain `"BRANCH COLLABORATION"`.

Exception: if `git remote` returns empty (no remote configured at all), the section body shows "No git remote configured. Add a remote to enable branch collaboration."

### 2.2 State A: No Active Branch (Setup Mode)

When `.purlin/runtime/active_branch` is absent or empty:

**Collapsed badge:** `"BRANCH COLLABORATION (<shortened-url>)"` when a remote is configured (see Section 2.1 for URL format). Plain `"BRANCH COLLABORATION"` when no remote is configured.

**Expanded content (in order):**

1. **Creation row** (always first):
   - Label: "Create Branch"
   - Text input: any valid git branch name, 20-char visible field width, unlimited entry length
   - Create button: disabled until valid name. On click -> `POST /branch-collab/create`.
   - Input uses standard dashboard input CSS tokens.

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

Five POST endpoints:

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

**`POST /branch-collab/join`** -- `{ "branch": "<name>" }` (Phase 1: Assessment)

Join uses a two-phase flow: **assessment** (fetch + compute state) then **confirmation** (act on user choice). This endpoint performs Phase 1 only — it returns state information without switching branches.

1. **Best-effort current-branch sync:** Before switching branches, synchronize the current branch with its remote counterpart. The sync is bidirectional and advisory — failures do not block the join.
   - **Local AHEAD of remote:** `git push <remote> <current-branch>`. Ensures the remote has the user's latest work.
   - **Remote AHEAD of local:** `git pull --ff-only` on the current branch. Brings in remote commits before switching away.
   - **DIVERGED:** No git operation. Returns `push_result: "diverged"` with a `push_guidance` field recommending `/pl-remote-pull origin/<current-branch>`.
   - **SAME or no upstream:** Skipped. Returns `push_result: "skipped"`.
   - On any failure (e.g., remote rejects, no network): log server-side and continue. Returns `push_result: "failed"`.
2. Fetch the target branch from remote: `git fetch <remote> <name>`. If `origin/<name>` does not exist after fetch, return error.
3. Check if a local branch `<name>` already exists.
4. **If no local branch exists:** Check if working tree is dirty. If dirty, return error with `"dirty": true` and `"dirty_files": [...]`. If clean, create tracking branch: `git checkout -b <name> origin/<name>`, record base branch, write active_branch, and return `{ "status": "ok", "branch": "<name>", "completed": true }`. No Phase 2 needed.
5. **If local branch exists:** Compute two sync states:
   - **HEAD-relative** (primary): compare `origin/<name>` vs `HEAD` using the same computation as the branches table (Section 2.5). This tells the user how the branch relates to their current position.
   - **Local-vs-remote** (reconciliation): compare local `<name>` vs `origin/<name>`. This determines what action is needed to sync the local copy before joining.
   Check if working tree is dirty (uncommitted changes outside `.purlin/`).
   **Auto-complete:** If HEAD-relative is SAME or EMPTY AND local-vs-remote is SAME AND working tree is clean, auto-complete with checkout (same behavior as step 4: record base branch, checkout, write active_branch, return `{ "completed": true }`). No Phase 2 modal needed.
6. Return assessment: `{ "status": "ok", "sync_state": "<STATE>", "commits_ahead": N, "commits_behind": M, "local_sync": "<STATE>", "local_ahead": N, "local_behind": M, "dirty": bool, "dirty_files": [...], "push_result": "<pushed|pulled|diverged|skipped|failed>" }`. `sync_state`/`commits_ahead`/`commits_behind` are HEAD-relative (same perspective as the branches table). `local_sync`/`local_ahead`/`local_behind` are local-vs-remote. `push_result` reports the outcome of the step-1 bidirectional sync: `"pushed"` (local was ahead, pushed to remote), `"pulled"` (remote was ahead, fast-forward pulled), `"diverged"` (both sides have unique commits, no action taken — response also includes `push_guidance` field), `"skipped"` (already in sync or no upstream), `"failed"` (sync attempted but failed). The UI determines the Phase 2 action from the combined state (see Section 2.8).

**`POST /branch-collab/join-confirm`** -- `{ "branch": "<name>", "action": "<action>" }` (Phase 2: Confirm)

Executes the user-chosen action from the assessment modal.

| Action | Condition | Behavior | Clean Tree Required |
|--------|-----------|----------|-------------------|
| `"checkout"` | local-vs-remote SAME, HEAD-relative SAME or AHEAD (not BEHIND, not DIVERGED) | `git checkout <name>`. | Yes |
| `"fast-forward"` | local-vs-remote BEHIND (and HEAD-relative not DIVERGED) | `git checkout <name> && git merge --ff-only origin/<name>`. | Yes |
| `"push"` | local-vs-remote AHEAD (and HEAD-relative not DIVERGED) | `git checkout <name> && git push <remote> <name>`. On push failure: branch IS checked out (active_branch written) but response returns error. | Yes |
| `"update-to-head"` | local-vs-remote SAME, HEAD-relative BEHIND | `git push origin HEAD:<name>` (replaces remote branch with current HEAD), then `git fetch origin <name>` (refreshes local tracking ref), then `git checkout -B <name> origin/<name>` (resets the local branch to match the updated remote ref and switches to it; handles stale local branches that can't fast-forward). Response includes `"reconciled": "update-to-head"`. | Yes |
| `"guide-pull"` | HEAD-relative DIVERGED (any local state), OR local-vs-remote DIVERGED | No checkout. Return copyable `/pl-remote-pull origin/<branch>` command. | No |

For `checkout`, `fast-forward`, `push`, and `update-to-head`: abort with error if working tree is dirty. Record base branch in `.purlin/runtime/branch_collab_base_branch` if not already set. Write branch name to `.purlin/runtime/active_branch`. Return `{ "status": "ok", "branch": "<name>" }` (plus `"reconciled": "fast-forward"` for fast-forward, `"reconciled": "push"` for push, or `"reconciled": "update-to-head"` for update-to-head). On push failure: branch IS checked out and active_branch written, but response returns `{ "status": "error", "error": "...", "branch_checked_out": true }`.

For `guide-pull`: return `{ "status": "ok", "action_required": "pull", "command": "/pl-remote-pull origin/<branch>", "warning": "Branch is diverged — run /pl-remote-pull in an agent to reconcile" }`. No git operations performed. No runtime files written.

**Builder Guidance — Git State Validation:** Tests MUST use temporary local branches and temporary remote refs that do not interfere with real project branches. Use fixture repos with pre-built branch topologies. If testing against a real remote, use namespaced throwaway branch names (e.g., `test-fixture/behind-2-<timestamp>`) and clean up in teardown. Tests MUST NOT create, modify, or delete branches that other agents might use.

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
  - **EMPTY:** Both directions return zero lines AND `origin/<branch>` and HEAD point to the same commit AND the branch has literally zero total commits (`git rev-list --count origin/<branch>` returns 0). This means the branch is an orphan or degenerate ref with no history at all. Shows `"EMPTY"` in normal text color (`--purlin-fg`) without a badge background.
  - **SAME:** Both directions return zero lines AND `origin/<branch>` and HEAD point to the same commit AND the branch has at least one total commit (`git rev-list --count origin/<branch>` returns > 0). This covers both new branches created from main (zero unique commits vs main, but sharing main's commit history) and established branches whose work has been merged. Shows green badge (`--purlin-status-good`).
  - **AHEAD:** Branch has unique commits HEAD does not, but HEAD has none the branch lacks. Shows yellow badge.
  - **BEHIND:** HEAD has commits the branch lacks, but the branch has none HEAD lacks. This is a stale branch. Shows yellow badge.
  - **DIVERGED:** Both have unique commits. Shows orange badge.
- For the active branch panel (operational mode), sync state compares local vs remote of the same branch (existing logic): `git log origin/<branch>..<branch>` and `git log <branch>..origin/<branch>`. SAME/AHEAD/BEHIND/DIVERGED four-state. EMPTY applies when the branch has literally zero total commits (`git rev-list --count <branch>` returns 0). A branch created from main that happens to match HEAD shows SAME, not EMPTY -- even if it has zero unique commits vs main -- because it shares main's commit history.
- When remote tracking ref `origin/<branch>` does not exist yet (pre-first-fetch): show inline note "Run Check Remote to see sync state" instead of a badge.

### 2.6 Cross-Section Annotation in LOCAL BRANCH

When an active branch exists, the LOCAL BRANCH section body shows a "Last remote sync: N min ago" line (or "Never synced") below the clean/dirty state line. Absent when no active branch.

NOT appended to the section heading text.

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

`branch_collab`: present only when an active branch exists. Absent otherwise. `sync_state` may be `"EMPTY"`, `"SAME"`, `"AHEAD"`, `"BEHIND"`, or `"DIVERGED"`. EMPTY indicates the branch has literally zero total commits (`git rev-list --count` returns 0).

`branch_collab_branches`: always present (may be empty array). Lists all branches discovered from remote tracking refs (filtered to exclude `HEAD`, `main`/`master`). Each entry includes per-branch sync state computed from locally cached refs (same rules as Section 2.5, applied per branch). The `sync_state` field may include `"EMPTY"` for branches with literally zero total commits.

### 2.8 Operation Modals (Joining / Leaving / Creating)

Branch operations (join, leave, create, switch) involve git checkouts, fetches, and pushes that can take several seconds. During this time the user sees no feedback. Operation modals provide a blocking progress indicator with inline error reporting.

**Modal HTML:** A single shared modal element (`id="bc-op-modal-overlay"`) is reused for all branch operations. It uses a lightweight modal pattern (inline styles, no tabs).

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
  - Join/Switch Phase 1: `"Fetching and checking sync state..."` while the assessment request is in flight.
  - Leave: `"Returning to <base-branch>..."`
  - Create: `"Creating <branch>..."`
- **Error block:** Hidden by default. On error, the spinner is replaced with an error icon (red text), the status message updates to the error text from the server response (`d.error`), and the block becomes visible. The error text uses `color: var(--purlin-status-error)`.
- **Close button:** Always visible in the footer. During progress, clicking Close is a no-op (button disabled). On completion (success or error), the button is enabled.
- **Auto-close on success:** For leave/create: auto-close after 400ms on success, call `refreshStatus()`. For join Phase 1: if `completed: true` (new branch created), auto-close. Otherwise transition to Phase 2 content. For join Phase 2 confirm: auto-close on success.
- **No close on overlay click during progress:** While the operation is in flight, clicking the overlay background does NOT close the modal. After completion (success or error), overlay click closes normally.
- **Escape key:** Same behavior as overlay click -- blocked during progress, allowed after completion.

**JavaScript integration:**

The existing `joinBranch()`, `leaveBranch()`, `switchBranch()`, and `createBranch()` functions are updated to:

1. Open the modal with the appropriate title and status message BEFORE sending the fetch request.
2. On success: briefly show a success state, then auto-close and call `refreshStatus()`.
3. On error: update the modal to show the error message, enable Close button.
4. On network failure (fetch `.catch`): show "Request failed -- check your connection" as the error message.

The `bcRemotePending` guard is preserved -- the modal is the visual manifestation of that guard state.

**Join Modal Two-Phase Content:**

Phase 1 (automatic): spinner + "Fetching and checking sync state..." while the assessment request is in flight. On completion, transition to Phase 2.

**Dirty gate:** If the assessment response has `dirty: true`, Phase 2 shows ONLY the dirty file block -- no sync state information is displayed. The dirty file block has a heading `"Uncommitted changes:"` followed by the file list in monospace font, then `"Commit or stash uncommitted changes before joining."` and a [Close] button. No action buttons are shown. The dirty gate renders identically regardless of the underlying sync state.

Phase 2 (interactive, clean tree only): the modal body replaces the spinner with content determined by the combined HEAD-relative and local-vs-remote state from the Phase 1 response.

The modal always shows a **primary line** with the HEAD-relative context (matching the branches table state), then optionally a **secondary line** with local-vs-remote reconciliation info, then the appropriate action.

**If HEAD-relative is DIVERGED** (regardless of local-vs-remote state):
- Primary: `"Branch has diverged from HEAD (N ahead, M behind)."`
- Instruction: `"Run the following command in an agent to reconcile:"`
- Copyable command block: `/pl-remote-pull origin/<branch>`
- [Close] button only (no join action).

**If HEAD-relative is NOT DIVERGED** and local-vs-remote is DIVERGED:
- Primary: `"Branch is N commits [ahead of / behind] HEAD."` (uses HEAD-relative counts; omit if HEAD-relative is SAME)
- Secondary: `"Local and remote copies have diverged."`
- Instruction + copyable command block: `/pl-remote-pull origin/<branch>`
- [Close] button only (no join action).

**If HEAD-relative is NOT DIVERGED** and local-vs-remote is BEHIND:
- Primary: `"Branch is N commits [ahead of / behind] HEAD."` (omit if HEAD-relative is SAME)
- Secondary: `"Local branch is M commits behind remote."`
- [Fast-Forward Local & Join] button.

**If HEAD-relative is NOT DIVERGED** and local-vs-remote is AHEAD:
- Primary: `"Branch is N commits [ahead of / behind] HEAD."` (omit if HEAD-relative is SAME)
- Secondary: `"Local branch is M commits ahead of remote."`
- [Push to Remote & Join] button.

**If HEAD-relative is BEHIND** and local-vs-remote is SAME:
- Primary: `"Branch is N commits behind HEAD."`
- Secondary: `"Will push current HEAD to remote <branch>, then switch to it."`
- [Update Remote & Join] button. Sends join-confirm with action `"update-to-head"`.

**If HEAD-relative is AHEAD** and local-vs-remote is SAME:
- Primary: `"Branch is N commits ahead of HEAD."`
- [Join] button (checkout only).

Note: HEAD-relative SAME/EMPTY + local-vs-remote SAME is auto-completed in Phase 1 (no Phase 2 modal shown).

Phase 2 action buttons ([Join], [Fast-Forward Local & Join], [Push to Remote & Join]) call `POST /branch-collab/join-confirm` with the appropriate action. While the confirm request is in flight, the button is replaced with a spinner. On success, auto-close. On error, show error in modal.

The DIVERGED copyable command block uses monospace font with subtle background, matching existing dashboard code styling. Includes a copy-to-clipboard button.

### 2.9 Integration Test Fixture Tags

The following fixture tags provide real git branch topology for integration-level tests, replacing mocked subprocess output with actual git state:

| Tag | State Description |
|-----|-------------------|
| `main/cdd_branch_collab/ahead-3` | Branch 3 commits ahead of collaboration branch |
| `main/cdd_branch_collab/behind-2` | Branch 2 commits behind collaboration branch |
| `main/cdd_branch_collab/diverged` | Both branch and collaboration branch have unique commits |
| `main/cdd_branch_collab/same` | Branch at same position as collaboration branch |
| `main/cdd_branch_collab/behind-dirty` | Branch behind remote, working tree has uncommitted changes |

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

#### Scenario: Join Branch Pushes Current Branch Before Fetch

    Given the current branch is main
    And main is 3 commits ahead of origin/main
    And feature/auth exists as a remote tracking branch
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the current branch is synced with the remote before git fetch
    And the response contains "push_result": "pushed"

#### Scenario: Join Branch Continues When Pre-Join Push Fails

    Given the current branch is main
    And the remote rejects the push
    And feature/auth exists as a remote tracking branch
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the push failure is logged server-side
    And git fetch is called for feature/auth
    And the response contains "push_result": "failed"
    And the join assessment proceeds normally

#### Scenario: Join Branch Assessment Creates Tracking Branch When No Local Exists

    Given feature/auth exists as a remote tracking branch
    And no local branch feature/auth exists
    And no active branch is set
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth
    And a local branch feature/auth is created tracking origin/feature/auth
    And the response contains "completed": true
    And .purlin/runtime/active_branch contains "feature/auth"
    And GET /status.json shows branch_collab.active_branch as "feature/auth"

#### Scenario: Join Branch Assessment Returns HEAD-Relative BEHIND With Local AHEAD

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And HEAD (main) has 10 commits not in origin/feature/auth (HEAD-relative: BEHIND)
    And local feature/auth has 1 commit not in origin/feature/auth (local-vs-remote: AHEAD)
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "sync_state": "BEHIND"
    And the response contains "commits_behind": 10
    And the response contains "local_sync": "AHEAD"
    And the response contains "local_ahead": 1
    And the response contains "dirty": false
    And no branch checkout has occurred (current branch unchanged)

#### Scenario: Join Branch Assessment Returns HEAD-Relative DIVERGED With Local SAME

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And origin/feature/auth has 1 commit not in HEAD (HEAD-relative AHEAD component)
    And HEAD has 5 commits not in origin/feature/auth (HEAD-relative BEHIND component)
    And local feature/auth is at SAME as origin/feature/auth (local-vs-remote: SAME)
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "sync_state": "DIVERGED"
    And the response contains "commits_ahead": 1
    And the response contains "commits_behind": 5
    And the response contains "local_sync": "SAME"
    And the response contains "local_ahead": 0
    And the response contains "local_behind": 0
    And no branch checkout has occurred (current branch unchanged)

#### Scenario: Join Branch Assessment Returns HEAD-Relative BEHIND With Local SAME

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And HEAD (main) has 20 commits not in origin/feature/auth (HEAD-relative: BEHIND)
    And origin/feature/auth has 0 commits not in HEAD
    And local feature/auth is at SAME as origin/feature/auth (local-vs-remote: SAME)
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "sync_state": "BEHIND"
    And the response contains "commits_behind": 20
    And the response contains "local_sync": "SAME"
    And no branch checkout has occurred (current branch unchanged)

#### Scenario: Join Branch Assessment Auto-Completes When SAME and Local SAME

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And origin/feature/auth and HEAD point to the same commit (HEAD-relative: SAME)
    And local feature/auth is at SAME as origin/feature/auth (local-vs-remote: SAME)
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then local feature/auth is checked out
    And the response contains "completed": true
    And .purlin/runtime/active_branch contains "feature/auth"

#### Scenario: Join Branch Assessment Returns Sync State With Dirty File List

    Given the branch "feature/auth" exists as a remote tracking branch
    And a local branch feature/auth exists
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "dirty": true
    And the response contains "dirty_files" as a non-empty array
    And the response contains a "sync_state" field
    And the response contains a "local_sync" field
    And no branch checkout has occurred (current branch unchanged)

#### Scenario: Join Branch With Nonexistent Remote Branch Returns Error

    Given no branch "nonexistent" exists as a remote tracking branch
    When a POST request is sent to /branch-collab/join with body {"branch": "nonexistent"}
    Then the response contains an error message
    And no branch checkout occurs

#### Scenario: Join Confirm Fast-Forward Checks Out and Merges

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is BEHIND origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "fast-forward"}
    Then local feature/auth is checked out
    And local feature/auth is fast-forwarded to origin/feature/auth
    And the response contains "reconciled": "fast-forward"
    And .purlin/runtime/active_branch contains "feature/auth"

#### Scenario: Join Confirm Fast-Forward Requires Clean Tree

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is BEHIND origin/feature/auth
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "fast-forward"}
    Then the response contains an error message about dirty working tree
    And the current branch is unchanged

#### Scenario: Join Confirm Checkout Requires Clean Tree

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists at SAME as origin/feature/auth (local-vs-remote)
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "checkout"}
    Then the response contains an error message about dirty working tree
    And the current branch is unchanged

#### Scenario: Join Confirm Checkout Switches Branch for Local SAME State

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists at SAME as origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is BEHIND (branch is behind main)
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "checkout"}
    Then local feature/auth is checked out
    And .purlin/runtime/active_branch contains "feature/auth"

#### Scenario: Join Confirm Push Checks Out and Pushes to Remote

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is AHEAD of origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "push"}
    Then local feature/auth is checked out
    And git push is called for feature/auth to the configured remote
    And the response contains "reconciled": "push"
    And .purlin/runtime/active_branch contains "feature/auth"

#### Scenario: Join Confirm Guide-Pull Returns Command Without Checkout (HEAD-Relative DIVERGED)

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists at SAME as origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is DIVERGED
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "guide-pull"}
    Then the response contains "action_required": "pull"
    And the response contains a "command" field with "/pl-remote-pull"
    And no branch checkout has occurred (current branch unchanged)
    And .purlin/runtime/active_branch is unchanged

#### Scenario: Join Confirm Guide-Pull Returns Command Without Checkout (Local DIVERGED)

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is DIVERGED from origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is BEHIND
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "guide-pull"}
    Then the response contains "action_required": "pull"
    And the response contains a "command" field with "/pl-remote-pull"
    And no branch checkout has occurred (current branch unchanged)
    And .purlin/runtime/active_branch is unchanged

#### Scenario: Join Confirm Update-to-Head Pushes HEAD and Joins BEHIND Branch

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists at SAME as origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is BEHIND (HEAD has 5 commits not in origin/feature/auth)
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "update-to-head"}
    Then git push origin HEAD:feature/auth is executed (remote branch updated to HEAD)
    And git fetch origin feature/auth is executed (local tracking ref refreshed)
    And git checkout -B feature/auth origin/feature/auth is executed (local branch reset to updated remote)
    And the response contains "reconciled": "update-to-head"
    And .purlin/runtime/active_branch contains "feature/auth"

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

#### Scenario: Sync State EMPTY When Branch Has Zero Total Commits

    Given an active branch "feature/empty" is set
    And feature/empty has literally zero total commits (git rev-list --count returns 0)
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "EMPTY"
    And branch_collab.commits_ahead is 0
    And branch_collab.commits_behind is 0

#### Scenario: EMPTY Badge Rendered Without Badge Background

    Given an active branch "feature/empty" is set
    And feature/empty has literally zero total commits
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

#### Scenario: No-Active-Branch Shows Creation Row and Branches Table

    Given no file exists at .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section contains a creation row with "Create Branch" label
    And the creation row contains a text input and a Create button
    And a branches table element is present below the creation row

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

#### Scenario: Join Branch Shows Two-Phase Operation Modal

    Given the CDD server is running
    And an active branch is not set
    And feature/auth exists as a remote tracking branch
    When the user clicks the Join button for feature/auth
    Then an operation modal appears with title "Joining Branch"
    And the modal initially shows a spinner with text "Fetching and checking sync state..."
    And the Close button is disabled while the assessment is in flight
    And clicking the overlay background does not close the modal
    And on assessment completion the modal transitions to Phase 2 content

#### Scenario: Join Branch Modal Shows HEAD Context and Fast-Forward for Local Behind

    Given the CDD server is running
    And a local branch feature/auth exists that is BEHIND origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is BEHIND (branch 10 commits behind HEAD)
    And the working tree is clean
    When the user clicks the Join button for feature/auth
    Then the modal shows "Branch is 10 commits behind HEAD." as primary text
    And the modal shows "Local branch is 2 commits behind remote." as secondary text
    And a [Fast-Forward Local & Join] button is visible
    And clicking the button sends a join-confirm request with action "fast-forward"

#### Scenario: Join Branch Modal Shows Diverged Guide-Pull for HEAD-Relative Diverged

    Given the CDD server is running
    And a local branch feature/auth exists at SAME as origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is DIVERGED (1 ahead, 5 behind)
    When the user clicks the Join button for feature/auth
    Then the modal shows "Branch has diverged from HEAD (1 ahead, 5 behind)." as primary text
    And instruction text reads "Run the following command in an agent to reconcile:"
    And a copyable command block with "/pl-remote-pull origin/feature/auth" is displayed
    And the command block uses monospace font with subtle background
    And no Join action button is present (only Close)
    And the branch is NOT checked out

#### Scenario: Join Branch Modal Shows HEAD Context and Push for Local Ahead

    Given the CDD server is running
    And a local branch feature/auth exists that is AHEAD of origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is BEHIND (branch 20 commits behind HEAD)
    And the working tree is clean
    When the user clicks the Join button for feature/auth
    Then the modal shows "Branch is 20 commits behind HEAD." as primary text
    And the modal shows "Local branch is 3 commits ahead of remote." as secondary text
    And a [Push to Remote & Join] button is visible
    And clicking the button sends a join-confirm request with action "push"

#### Scenario: Join Branch Modal Shows Update Remote and Join for Local SAME With HEAD Behind

    Given the CDD server is running
    And a local branch feature/auth exists at SAME as origin/feature/auth (local-vs-remote)
    And HEAD-relative sync state is BEHIND (branch 15 commits behind HEAD)
    And the working tree is clean
    When the user clicks the Join button for feature/auth
    Then the modal shows "Branch is 15 commits behind HEAD." as primary text
    And the modal shows "Will push current HEAD to remote feature/auth, then switch to it." as secondary text
    And an [Update Remote & Join] button is visible
    And clicking the button sends a join-confirm request with action "update-to-head"

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

#### Scenario: Join Confirm Push Fails After Checkout

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is AHEAD of origin/feature/auth
    And the working tree is clean
    And the git push will be rejected by the remote
    When a POST request is sent to /branch-collab/join-confirm with body {"branch": "feature/auth", "action": "push"}
    Then local feature/auth is checked out (branch IS switched)
    And .purlin/runtime/active_branch contains "feature/auth"
    And the response contains "status": "error"
    And the response contains "branch_checked_out": true
    And the response contains an error message about the push failure

#### Scenario: Join Branch Modal Shows Error When Push to Remote Fails

    Given the operation modal is showing a join-confirm response for an AHEAD branch
    When the server returns { "status": "error", "error": "push rejected", "branch_checked_out": true }
    Then the modal shows the error message in error color
    And the Close button is enabled
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

#### Scenario: Switch Branch Shows Two-Phase Operation Modal

    Given the CDD server is running
    And an active branch "feature/auth" is set
    When the user selects "hotfix/urgent" from the branch dropdown
    Then an operation modal appears with title "Joining Branch"
    And the modal initially shows a spinner with text "Fetching and checking sync state..."
    And on assessment completion the modal transitions to Phase 2 content

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

#### Scenario: Join BEHIND Branch Shows HEAD Context in Modal

    Given the CDD server is running against fixture tag main/cdd_branch_collab/behind-2
    When the user navigates to the dashboard
    And clicks Join on the BEHIND branch
    Then the modal shows HEAD-relative context as primary text
    And the appropriate local-vs-remote action is shown
    When the user clicks the action button
    Then the branch is joined successfully
    And the modal auto-closes

#### Scenario: Join AHEAD Branch Shows HEAD Context and Push in Modal

    Given the CDD server is running against fixture tag main/cdd_branch_collab/ahead-3
    When the user navigates to the dashboard
    And clicks Join on the AHEAD branch
    Then the modal shows HEAD-relative context as primary text
    And local-vs-remote state determines the action button

#### Scenario: Join DIVERGED Branch Shows Diverged Message and Pull Command

    Given the CDD server is running against fixture tag main/cdd_branch_collab/diverged
    When the user navigates to the dashboard
    And clicks Join on the DIVERGED branch
    Then the modal shows "Branch has diverged from HEAD" with commit counts as primary text
    And a copyable command block with "/pl-remote-pull" is displayed
    And the command block has monospace font with subtle background
    And no Join action button is present (only Close)

#### Scenario: Join Branch With Dirty Tree Shows Dirty Gate Only

    Given the CDD server is running against fixture tag main/cdd_branch_collab/behind-dirty
    When the user navigates to the dashboard
    And clicks Join on the branch
    Then the modal shows "Uncommitted changes:" heading
    And a dirty file list is displayed in monospace font below the heading
    And the modal shows "Commit or stash uncommitted changes before joining."
    And no sync state information is displayed
    And action buttons (Join, Fast-Forward, Push) are absent
    And only the Close button is available

#### Scenario: Sync Badge Colors Match Design Spec

    Given the CDD server is running against fixture tags with branches in various sync states
    When the user navigates to the dashboard
    Then SAME branches show a green badge (--purlin-status-good)
    And AHEAD/BEHIND branches show a yellow badge (--purlin-status-todo)
    And DIVERGED branches show an orange badge (--purlin-status-warning)
    And EMPTY branches show normal text (--purlin-fg) without badge background

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Visual Specification

### Screen: CDD Dashboard -- Branch Collaboration Section

- **Reference:** N/A
- [ ] BRANCH COLLABORATION section position: above LOCAL BRANCH
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
- [ ] Operation modal: centered overlay with semi-transparent background, matching lightweight modal styling
- [ ] Operation modal: CSS spinner (small, inline) visible during in-flight state
- [ ] Operation modal: join/switch Phase 1 shows "Fetching and checking sync state..." then transitions to Phase 2 interactive content
- [ ] Operation modal: join dirty gate shows "Uncommitted changes:" heading + file list in monospace + instruction text, no sync state info
- [ ] Operation modal: join Phase 2 shows HEAD-relative context as primary line, local-vs-remote reconciliation as secondary line, with action: DIVERGED (HEAD-relative or local)=copyable command + [Close], local BEHIND=[Fast-Forward Local & Join], local AHEAD=[Push to Remote & Join], local SAME + HEAD BEHIND=[Update Remote & Join], local SAME + HEAD AHEAD=[Join]
- [ ] Operation modal: DIVERGED state shows copyable command block with monospace font and copy button
- [ ] Operation modal: spinner hidden and replaced with error text (red) on failure
- [ ] Operation modal: Close button disabled (greyed) during in-flight, enabled on completion/error
- [ ] Operation modal: auto-closes on success with brief visible transition (~400ms)
- [ ] Refresh Branches: stale branches (deleted from remote) are removed from the table after fetch-all

## User Testing Discoveries



