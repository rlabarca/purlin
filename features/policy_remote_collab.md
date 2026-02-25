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
- `/pl-remote-push` and `/pl-remote-pull` read this file to determine the target branch.
- When the file is absent or empty, no session is active and both commands abort with a message directing the user to the CDD dashboard.

### 2.3 Config Is Optional

- `.purlin/config.json` MAY contain a `remote_collab` block for non-default settings.
- When absent, defaults are used: remote = "origin", auto_fetch_interval = 300 seconds.
- The config block does NOT store the active session — that is runtime state (2.2).
- No manual config editing is required to use remote collaboration.

### 2.4 Main-Only Restriction (Critical)

- `/pl-remote-push` and `/pl-remote-pull` MUST be run from the main checkout (branch: `main`).
- They are FORBIDDEN inside isolated worktrees.
- Enforcement: Step 0 branch check in each command file.
- Physical placement: both files exist in the project root `.claude/commands/`. They are NOT present in isolated worktree `.claude/commands/` directories (`create_isolation.sh` places only `pl-local-push.md` and `pl-local-pull.md` in worktree `.claude/commands/`).

### 2.5 Integration Sequence

Always: isolation branch -> local main (via `/pl-local-push`) -> remote collab (via `/pl-remote-push`). Isolation branches (`isolated/*`) remain local and are never pushed directly to remote.

### 2.6 Fetch-Before-Push

Always `git fetch` before pushing. If local main is BEHIND or DIVERGED relative to remote, block and require `/pl-remote-pull` first.

### 2.7 Merge-Not-Rebase for Local Main

`/pl-remote-pull` uses `git merge` (not rebase) on local main. Main is a shared integration branch — rebasing rewrites commits other contributors depend on. This differs from `/pl-local-pull` (isolation branches are personal -> rebase; main is shared -> merge).

### 2.8 Contributor Identity

Attribution via git author metadata (`git log --format="%ae|%an|%cr|%s"`). No manifest file required.

### 2.9 Session Lifecycle

- **Create:** Dashboard creates the branch from main's HEAD and pushes to remote. The session becomes immediately discoverable by other collaborators via `git fetch`.
- **Join:** Dashboard fetches the remote branch and sets it as active locally.
- **Switch:** Dashboard changes the active session to a different existing session.
- **Disconnect:** Dashboard clears the active session. Does NOT delete any branches. The session remains joinable.

### 2.10 Release Integration (Known Follow-Up)

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
- Running `/pl-remote-push` or `/pl-remote-pull` from inside an isolated worktree
- Manual editing of `.purlin/config.json` to set up remote collab (use the dashboard)

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are
process invariants enforced via command file guards, dashboard endpoints, and runtime state file.
