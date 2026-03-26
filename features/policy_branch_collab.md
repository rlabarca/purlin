# Policy: Branch Collaboration

> Label: "Policy: Branch Collaboration"
> Category: "Policy"

## Purpose

Branch collaboration extends Purlin's local isolation model to multi-machine workflows via named branches managed through `/pl-remote`. Any valid git branch name can be used as a collaboration branch. One branch is active at a time per machine. Remote `main` is untouched during active collaboration -- all sync flows through the active branch.

## 2. Invariants

### 2.1 Branch-Based Collaboration

- The branch name IS the identifier. No prefix is prepended, no session abstraction exists.
- Branches are created and managed via `/pl-remote branch` (create, join, leave, list).
- Multiple collaboration branches may exist on the remote; exactly one is active per machine at a time.
- Branch discovery: `git branch -r` filtered to exclude `HEAD`, `main`, and `master`.

### 2.2 Active Branch State (Per-Machine, Gitignored)

- The active branch is stored in `.purlin/runtime/active_branch` (a single-line plaintext file containing the full branch name).
- This file is gitignored (`.purlin/runtime/` is already in `.gitignore`).
- Each collaborator independently chooses which branch to join.
- `/pl-remote push` and `/pl-remote pull` read this file to determine the target branch.
- When the file is absent or empty, no branch is active. The collaboration branch defaults to `main` (per Section 2.4).

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

All collaboration commands (`/pl-remote push`, `/pl-remote pull`) use the collaboration branch as their integration target. During an active branch, the local machine checks out that branch, making push and pull symmetric same-branch operations.

Throughout this policy, **collaboration branch** is the canonical term for the branch that push/pull operations target. **Active branch** refers specifically to the value stored in `.purlin/runtime/active_branch`. When no active branch exists, the collaboration branch defaults to `main`.

### 2.5 Collaboration Branch Resolution

- `/pl-remote push` and `/pl-remote pull` resolve the collaboration branch per Section 2.4: if `.purlin/runtime/active_branch` is present and non-empty, the collaboration branch is that value; otherwise it is `main`.
- When the collaboration branch resolves to `main` (direct mode), push/pull operate on `main` directly -- no active branch file is required.
- Enforcement: the precondition sequence in each subcommand resolves the collaboration branch, then verifies the current checked-out branch matches it.

### 2.6 Integration Sequence

Local collaboration branch -> remote (via `/pl-remote push`). During an active branch, the collaboration branch is the value from `.purlin/runtime/active_branch`.

### 2.7 Fetch-Before-Push

Always `git fetch` before pushing. If the local collaboration branch is BEHIND or DIVERGED relative to the remote, block and require `/pl-remote pull` first.

### 2.8 Merge-Not-Rebase for Collaboration Branch

`/pl-remote pull` uses `git merge` (not rebase) on the local collaboration branch. The collaboration branch is a shared integration branch -- rebasing rewrites commits other contributors depend on.

If `git merge` encounters conflicts during `/pl-remote pull`, the command halts with file-level conflict context (which files conflict, the merge state). Conflict resolution is a human responsibility -- the agent does not auto-resolve. After manual resolution, the user runs `/pl-remote pull` again to verify clean state.

### 2.9 Contributor Identity

Attribution via git author metadata (`git log --format="%ae|%an|%cr|%s"`). No manifest file required.

### 2.10 Branch Lifecycle

All branch transitions abort if the working tree is dirty. A dirty working tree is defined as: `git status --porcelain` returns any staged or unstaged modifications to tracked files outside `.purlin/`. Untracked files are ignored. Changes inside `.purlin/` (runtime state, caches) are exempt.

- **Create** (`/pl-remote branch create <name>`): Creates the branch from HEAD and pushes to remote. The local machine checks out the new branch. The branch becomes immediately discoverable by other collaborators via `git fetch`.
- **Join** (`/pl-remote branch join <name>`): Fetches the remote branch, checks out the branch locally, and sets it as active.
- **Leave** (`/pl-remote branch leave`): Checks out the stored base branch (or `main` if absent) and clears the active branch. Does NOT delete any branches. The branch remains joinable.

### 2.11 Release Integration

During active collaboration, remote main is untouched. The release process operates independently of the collaboration branch lifecycle. Specifically:

- **Pre-release:** All features must reach a satisfied state before release. This work happens on the collaboration branch.
- **Merge to main:** When the release is ready, the collaboration branch is merged to `main` via a standard `git merge` (not rebase, consistent with Section 2.8). This merge is performed by the human or PM as part of the release checklist, not by `/pl-remote push`.
- **Post-merge push:** After merging to `main`, the `purlin.push_to_remote` release step pushes `main` to the remote. The active branch file should be cleared (`/pl-remote branch leave`) before this step.
- **FORBIDDEN pattern exemption:** The `git push origin main` FORBIDDEN pattern (Section 4) does not apply during the release merge-to-main step, as the collaboration branch has been merged and the active branch cleared.

### 2.12 No Remote Configured

When no git remote exists (`git remote -v` returns empty):

- `/pl-remote add` is the standalone subcommand for configuring a remote: scans for hosting hints (SSH keys, credential helpers, hosting CLIs), prompts for a git remote URL, executes `git remote add` or `git remote set-url`, and verifies connectivity via `git ls-remote`. It does not push or pull.
- `/pl-remote push` prints: "No git remote configured. Run `/pl-remote add` to set up a remote first." and exits with code 1.
- `/pl-remote pull` prints: "No git remote configured. Run `/pl-remote add` to set up a remote first." and exits with code 1.

### 2.13 First-Push Safety Confirmation

On the first push to any remote+branch pair (detected by absence of remote tracking ref via `git rev-parse --verify <remote>/<branch>`), the command MUST display the target remote name, URL, branch, and commit count, and require explicit user confirmation before pushing. Subsequent pushes to the same remote+branch skip this confirmation. This prevents accidental pushes to wrong remotes or branches during initial setup.

The same confirmation pattern applies to `/pl-remote pull` on first pull from a remote+branch pair. First pull is detected by checking whether a merge-base exists between the local branch and the remote tracking branch. The confirmation displays remote details and incoming commit count.

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
- Running `/pl-remote push` or `/pl-remote pull` from a branch that does not match the resolved collaboration branch
- `git checkout main` while a branch is active -- use `/pl-remote branch leave` to return to main
- Manual editing of `.purlin/config.json` to set up branch collaboration (use `/pl-remote add` for remote config)

## Scenarios

No automated or manual scenarios. This is a policy anchor node -- its "scenarios" are
process invariants enforced via `/pl-remote` subcommand guards and runtime state files.
