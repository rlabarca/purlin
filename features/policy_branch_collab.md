# Policy: Branch Collaboration

> Label: "Policy: Branch Collaboration"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_release.md

## Purpose

Branch collaboration extends Purlin's local isolation model to multi-machine workflows via named branches managed through the CDD dashboard. Any valid git branch name can be used as a collaboration branch. One branch is active at a time per machine. Remote `main` is untouched during active collaboration -- all sync flows through the active branch.

## 2. Invariants

### 2.1 Branch-Based Collaboration

- The branch name IS the identifier. No prefix is prepended, no session abstraction exists.
- Branches are created and managed exclusively through the CDD dashboard UI.
- Multiple collaboration branches may exist on the remote; exactly one is active per machine at a time.
- Branch discovery: `git branch -r` filtered to exclude `HEAD`, `main`, and `master`.

### 2.2 Active Branch State (Per-Machine, Gitignored)

- The active branch is stored in `.purlin/runtime/active_branch` (a single-line plaintext file containing the full branch name).
- This file is gitignored (`.purlin/runtime/` is already in `.gitignore`).
- Each collaborator independently chooses which branch to join.
- `/pl-remote-push` and `/pl-remote-pull` read this file to determine the target branch.
- When the file is absent or empty, no branch is active and both commands abort with a message directing the user to the CDD dashboard.

### 2.3 Config Is Optional

- `.purlin/config.json` MAY contain a `branch_collab` block for non-default settings.
- Backward compatibility: if `branch_collab` is absent, read `remote_collab` as a fallback.
- When absent, defaults are used: remote = "origin", auto_fetch_interval = 300 seconds.
- The config block does NOT store the active branch -- that is runtime state (2.2).
- No manual config editing is required to use branch collaboration.

### 2.4 Collaboration Branch

The **collaboration branch** is a contextual reference that replaces all hardcoded `main` references in the collaboration toolchain:

- **No active branch:** collaboration branch = `main` (no behavioral change from pre-collab workflows).
- **Active branch:** collaboration branch = the value read from `.purlin/runtime/active_branch`.

Detection: read `.purlin/runtime/active_branch`. If present and non-empty, that value is the collaboration branch. Otherwise, `main`.

All collaboration commands (`/pl-remote-push`, `/pl-remote-pull`) use the collaboration branch as their integration target. During an active branch, the local machine checks out that branch, making push and pull symmetric same-branch operations.

### 2.5 Collaboration Branch Restriction (Critical)

- `/pl-remote-push` and `/pl-remote-pull` MUST be run from the active collaboration branch.
- Enforcement: Step 0 branch check in each command file verifies the current branch matches the collaboration branch.

### 2.6 Integration Sequence

Local collaboration branch -> remote (via `/pl-remote-push`). During an active branch, the collaboration branch is the value from `.purlin/runtime/active_branch`.

### 2.7 Fetch-Before-Push

Always `git fetch` before pushing. If the local collaboration branch is BEHIND or DIVERGED relative to the remote, block and require `/pl-remote-pull` first.

### 2.8 Merge-Not-Rebase for Collaboration Branch

`/pl-remote-pull` uses `git merge` (not rebase) on the local collaboration branch. The collaboration branch is a shared integration branch -- rebasing rewrites commits other contributors depend on.

### 2.9 Contributor Identity

Attribution via git author metadata (`git log --format="%ae|%an|%cr|%s"`). No manifest file required.

### 2.10 Branch Lifecycle

All branch transitions abort if the working tree is dirty (uncommitted changes outside `.purlin/`).

- **Create:** Dashboard creates the branch from HEAD and pushes to remote. The local machine checks out the new branch. The branch becomes immediately discoverable by other collaborators via `git fetch`.
- **Join:** Dashboard fetches the remote branch, checks out the branch locally, and sets it as active.
- **Leave:** Dashboard checks out the stored base branch (or `main` if absent) and clears the active branch. Does NOT delete any branches. The branch remains joinable.

### 2.11 Release Integration (Known Follow-Up)

During active collaboration, remote main is untouched. Release protocol changes (merging the collaboration branch to remote main at release time) are deferred to a separate spec increment.

## 3. Config Schema (Optional Override)

```json
{
  "branch_collab": {
    "remote": "origin",
    "auto_fetch_interval": 300
  }
}
```

Fields: `remote` (default `"origin"`), `auto_fetch_interval` (seconds; 0 = disable, default 300). Entire block is optional -- defaults work without any config. Active branch is NOT stored here -- see 2.2. Backward compatibility: if `branch_collab` is absent, read `remote_collab` with same schema.

## 4. FORBIDDEN Patterns

- `git push origin main` -- direct push to remote main during active collaboration
- `git push --force origin <branch>` -- force push to collaboration branch
- Running `/pl-remote-push` or `/pl-remote-pull` from a branch that does not match the active branch
- `git checkout main` while a branch is active -- use Leave to return to main
- Manual editing of `.purlin/config.json` to set up branch collaboration (use the dashboard)

## Scenarios

No automated or manual scenarios. This is a policy anchor node -- its "scenarios" are
process invariants enforced via command file guards, dashboard endpoints, and runtime state file.
