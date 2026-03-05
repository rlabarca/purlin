# Policy: Remote Multi-Machine Collaboration

> Label: "Policy: Remote Multi-Machine Collaboration"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/policy_release.md

## Purpose

Remote collaboration extends Purlin's local isolation model to multi-machine workflows via collab sessions managed through the CDD dashboard. Each session maps to a `collab/<name>` branch on the hosted remote. One session is active at a time per machine. Remote `main` is untouched during active collaboration — all sync flows through the collab branch.

## 2. Invariants

### 2.1 Session-Based Collab Branches

- Each session maps to a branch: session "v0.5-sprint" -> branch `collab/v0.5-sprint`.
- Sessions are created and managed exclusively through the CDD dashboard UI.
- Multiple sessions may exist on the remote; exactly one is active per machine at a time.
- Session discovery: `git branch -r --list '<remote>/collab/*'`.

### 2.2 Active Session State (Per-Machine, Gitignored)

- The active session is stored in `.purlin/runtime/active_remote_session` (a single-line plaintext file).
- This file is gitignored (`.purlin/runtime/` is already in `.gitignore`).
- Each collaborator independently chooses which session to connect to.
- `/pl-collab-push` and `/pl-collab-pull` read this file to determine the target branch.
- When the file is absent or empty, no session is active and both commands abort with a message directing the user to the CDD dashboard.

### 2.3 Config Is Optional

- `.purlin/config.json` MAY contain a `remote_collab` block for non-default settings.
- When absent, defaults are used: remote = "origin", auto_fetch_interval = 300 seconds.
- The config block does NOT store the active session — that is runtime state (2.2).
- No manual config editing is required to use remote collaboration.

### 2.4 Collaboration Branch

The **collaboration branch** is a contextual reference that replaces all hardcoded `main` references in the collaboration toolchain:

- **No active session:** collaboration branch = `main` (no behavioral change from pre-collab workflows).
- **Active session:** collaboration branch = `collab/<session>` (read from `.purlin/runtime/active_remote_session`).

Detection: read `.purlin/runtime/active_remote_session`. If present and non-empty, collaboration branch = `collab/<value>`. Otherwise, `main`.

All collaboration commands (`/pl-collab-push`, `/pl-collab-pull`, `/pl-local-push`, `/pl-local-pull`) use the collaboration branch as their integration target. During an active session, the local machine checks out the `collab/<session>` branch, making push and pull symmetric same-branch operations.

### 2.5 Collaboration Branch Restriction (Critical)

- `/pl-collab-push` and `/pl-collab-pull` MUST be run from the collaboration branch. During an active session, that is `collab/<session>` (not `main`).
- They are FORBIDDEN inside isolated worktrees.
- Enforcement: Step 0 branch check in each command file verifies the current branch matches the collaboration branch.
- Physical placement: both files exist in the project root `.claude/commands/`. They are NOT present in isolated worktree `.claude/commands/` directories (`create_isolation.sh` places only `pl-local-push.md` and `pl-local-pull.md` in worktree `.claude/commands/`).

### 2.6 Integration Sequence

Always: isolation branch -> local collaboration branch (via `/pl-local-push`) -> remote collab (via `/pl-collab-push`). During an active session, the collaboration branch is `collab/<session>`. Isolation branches (`isolated/*`) remain local and are never pushed directly to remote.

### 2.7 Fetch-Before-Push

Always `git fetch` before pushing. If the local collaboration branch is BEHIND or DIVERGED relative to the remote, block and require `/pl-collab-pull` first.

### 2.8 Merge-Not-Rebase for Collaboration Branch

`/pl-collab-pull` uses `git merge` (not rebase) on the local collaboration branch. The collaboration branch is a shared integration branch — rebasing rewrites commits other contributors depend on. This differs from `/pl-local-pull` (isolation branches are personal -> rebase; the collaboration branch is shared -> merge).

### 2.9 Contributor Identity

Attribution via git author metadata (`git log --format="%ae|%an|%cr|%s"`). No manifest file required.

### 2.10 Session Lifecycle

All session transitions abort if the working tree is dirty (uncommitted changes outside `.purlin/`).

- **Create:** Dashboard creates the branch from main's HEAD and pushes to remote. The local machine checks out `collab/<name>`. The session becomes immediately discoverable by other collaborators via `git fetch`.
- **Join:** Dashboard fetches the remote branch, checks out `collab/<name>` locally, and sets it as active.
- **Switch:** Dashboard checks out the new `collab/<target>` branch locally, changing the active session.
- **Disconnect:** Dashboard checks out `main` and clears the active session. Does NOT delete any branches. The session remains joinable.

### 2.11 Release Integration (Known Follow-Up)

During active collab, remote main is untouched. Release protocol changes (merging collab branch to remote main at release time) are deferred to a separate spec increment.

## 3. Config Schema (Optional Override)

```json
{
  "remote_collab": {
    "remote": "origin",
    "auto_fetch_interval": 300
  }
}
```

Fields: `remote` (default `"origin"`), `auto_fetch_interval` (seconds; 0 = disable, default 300). Entire block is optional — defaults work without any config. Active session is NOT stored here — see 2.2.

## 4. FORBIDDEN Patterns

- `git push origin main` — direct push to remote main during active collaboration
- `git push --force origin <collab-branch>` — force push to collab branch
- Running `/pl-collab-push` or `/pl-collab-pull` from inside an isolated worktree
- Running `/pl-collab-push` or `/pl-collab-pull` from `main` when a session is active (must be on `collab/<session>`)
- `git checkout main` while a session is active — use Disconnect to return to main
- Manual editing of `.purlin/config.json` to set up remote collab (use the dashboard)

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are
process invariants enforced via command file guards, dashboard endpoints, and runtime state file.
