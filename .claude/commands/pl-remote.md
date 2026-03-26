**Purlin command: Purlin agent only (replaces /pl-remote-push, /pl-remote-pull, /pl-remote-add)**
**Purlin mode: shared**

Legacy agents: Use /pl-remote-push, /pl-remote-pull, or /pl-remote-add instead.
Purlin agent: Branch collaboration — remote config, branch lifecycle, push/pull sync.

---

## Usage

```
/pl-remote push                                — Push collaboration branch to remote
/pl-remote pull [<branch>]                     — Pull remote branch into local
/pl-remote add [<url>] [--name <remote-name>]  — Configure a git remote
/pl-remote branch create <name>                — Create and switch to a collaboration branch
/pl-remote branch join <name>                  — Switch to an existing collaboration branch
/pl-remote branch leave                        — Return to main and clear active branch
/pl-remote branch list                         — List available collaboration branches
```

No subcommand or invalid subcommand: print usage and exit.

## Shared Protocol

### Config Reading

Read remote name from `.purlin/config.json`:
1. `branch_collab.remote`
2. Fallback: `remote_collab.remote`
3. Default: `"origin"`

### Collaboration Branch Resolution

1. Read `.purlin/runtime/active_branch`.
2. If present and non-empty: collaboration branch = that value.
3. If absent or empty: collaboration branch = `main`.

### Branch Guard (push and pull no-argument mode)

`git rev-parse --abbrev-ref HEAD` — must match the resolved collaboration branch.
- Active branch exists but wrong branch: `"This command must be run from the collaboration branch (<branch>). Current branch: <current>."`
- No active branch, not on main: `"No active collaboration branch. On main, /pl-remote <push|pull> operates on main directly. Current branch: <current>. Switch to main or create a collaboration branch with /pl-remote branch create <name>."`

### Remote Guard (push, pull, branch create, branch join, branch list)

`git remote -v` — if empty: `"No git remote configured. Run /pl-remote add to set up a remote first."` Exit 1.

### Working Tree Check (push, pull, branch create, branch join, branch leave)

`git status --porcelain` — if staged/unstaged modifications to tracked files outside `.purlin/`: abort. Untracked files ignored. `.purlin/` changes exempt.

## Subcommands

### push

Push the local collaboration branch to the remote.

**Preconditions:** Branch Resolution → Branch Guard → Remote Guard → Working Tree Check → Config Reading.

**First-push safety:** If `git rev-parse --verify <remote>/<branch>` fails (no tracking ref), show confirmation:
```
First push to this remote. Please confirm:
  Remote:  <name> (<url>)
  Branch:  <branch>
  Commits: <N> commit(s) will be pushed
Proceed? [Y/n]
```

**Sync state** (after `git fetch <remote>`):
- **SAME:** `"Already in sync. Nothing to push."` Exit 0.
- **BEHIND:** `"Local <branch> is BEHIND by M commits. Run /pl-remote pull before pushing."` Exit 1.
- **DIVERGED:** Print incoming commits. Instruct `/pl-remote pull`. Exit 1.
- **AHEAD:** `git push <remote> <branch>`. Report count. On failure: print error, exit 1.

**FORBIDDEN:** No `--force`. No pushing to non-collaboration branch. Validate input against injection.

### pull

Pull remote collaboration branch into local via merge.

**Two modes:**
- **No-argument:** Resolve branch → Branch Guard → Remote Guard → Working Tree Check → Config.
- **Explicit-branch** (`/pl-remote pull RC0.8.0`): Use argument directly. Skip resolution and guard. Remote Guard → Working Tree Check → Config.

**First-pull safety:** If `git merge-base <branch> <remote>/<branch>` fails, show confirmation (same pattern as push).

**Sync state** (after `git fetch <remote>`):
- **SAME:** `"Already in sync with remote."` Exit 0.
- **AHEAD:** `"AHEAD by N commits. Nothing to pull."` Exit 0.
- **BEHIND:** `git merge --ff-only <remote>/<branch>`. Report count.
- **DIVERGED:** Show `git log <branch>..<remote>/<branch> --stat --oneline`. Run `git merge <remote>/<branch>`. On conflict: print per-file context, resolution instructions, exit 1.

**Post-merge digest:** After successful merge, run `bash ${TOOLS_ROOT}/collab/generate_whats_different.sh <branch>`. Display digest inline. Non-blocking — warn and continue on failure.

**FORBIDDEN:** No rebase. No push. No auto-resolve conflicts. Must be on collaboration branch (no-argument mode).

### add

Configure a git remote. No branch guard, no dirty check — configuration only.

**No remotes (guided setup):**
1. Print help banner with supported URL formats.
2. Scan hosting hints (`~/.ssh/config`, credential helpers, `gh`/`glab` CLIs).
3. Prompt for URL (or use argument). Normalize browser URLs to SSH.
4. Prompt for remote name (or use `--name`). Default: `"origin"`.
5. `git remote add <name> <url>`.
6. Verify connectivity via `git ls-remote`.
7. On SSH auth failure: auto-setup SSH key (check existing → generate if needed → keyscan host → display pubkey with hosting-provider URL → wait for user → re-verify).
8. On failure + decline: rollback (`git remote remove` if new, restore old URL if set-url).
9. Print success. Suggest next step: `/pl-remote branch create <name>` for collaboration.

**Remotes exist:** Show current remotes. Offer change URL or add additional. Same verification and rollback.

**Config sync:** If non-origin name is the only remote, prompt to set `branch_collab.remote`.

**FORBIDDEN:** No push/pull. No remote deletion except rollback of failed new add.

### branch

Manage the collaboration branch lifecycle.

#### branch create \<name\>

**Preconditions:** Remote Guard → Working Tree Check → must be on `main` → name must not exist locally or on remote.

1. `git checkout -b <name>`
2. `git push -u <remote> <name>`
3. Write `<name>` to `.purlin/runtime/active_branch`.
4. Store `main` in `.purlin/runtime/branch_collab_base`.

```
Created collaboration branch: <name>
  Pushed to: <remote>/<name>
  Active branch set. Use /pl-remote push and /pl-remote pull to sync.
  Use /pl-remote branch leave to return to main.
```

#### branch join \<name\>

**Preconditions:** Remote Guard → Working Tree Check → `git fetch <remote>` → branch must exist on remote.

1. Local branch exists: `git checkout <name>` + `git merge --ff-only <remote>/<name>`.
2. No local branch: `git checkout -b <name> <remote>/<name>`.
3. Write `<name>` to `.purlin/runtime/active_branch`.
4. Store current branch in `.purlin/runtime/branch_collab_base`.

```
Joined collaboration branch: <name>
  Tracking: <remote>/<name>
  Use /pl-remote push and /pl-remote pull to sync.
```

#### branch leave

**Preconditions:** Working Tree Check → active branch must exist.

1. Read base from `.purlin/runtime/branch_collab_base` (default: `main`).
2. `git checkout <base>`.
3. Clear `.purlin/runtime/active_branch`.
4. Delete `.purlin/runtime/branch_collab_base`.

Does NOT delete the branch. It remains joinable.

```
Left collaboration branch: <name>
  Returned to: <base>
  Use /pl-remote branch join <name> to rejoin.
```

#### branch list

1. `git fetch <remote>`.
2. `git branch -r` — filter out `HEAD`, `main`, `master`.
3. Mark active branch from `.purlin/runtime/active_branch`.

```
Collaboration branches on <remote>:
  * feature/collab  (active)
    feature/auth
```

No branches: `"No collaboration branches on <remote>. Use /pl-remote branch create <name> to start one."`

**FORBIDDEN:** `branch create` only from main. `branch leave` never deletes. `branch join` never force-checkouts dirty tree. Validate branch names.

ARGUMENTS: $ARGUMENTS
