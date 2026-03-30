Push: push local collaboration branch to remote.

**Owner: All roles**

The command operates in three modes:
- **Mode 1 — No remote configured:** Exits with guidance to run `/pl-remote-add`.
- **Mode 2 — Direct mode (no active branch):** Collaboration branch resolves to `main`. Pushes `main` to the remote.
- **Mode 3 — Collaboration mode (active branch):** Pushes the active collaboration branch to the same-named remote branch.

## Steps

### 0. Collaboration Branch Resolution

Read `.purlin/runtime/active_branch`:

1. If present and non-empty: collaboration branch = that value (trimmed).
2. If absent or empty: collaboration branch = `main`.

### 1. Collaboration Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result does not match the resolved collaboration branch, abort with a mode-appropriate message:

- **Active branch exists** (file was present and non-empty): abort with:
  ```
  This command must be run from the collaboration branch (<branch>).
  Current branch: <current>. Switch to <branch> before running /pl-remote-push.
  ```

- **No active branch (direct mode)** (file was absent or empty, resolved to `main`): abort with:
  ```
  No active collaboration branch. On `main`, /pl-remote-push pushes main directly.
  Current branch: <current>. Switch to main or use the CDD dashboard to create a collaboration branch.
  ```

Do NOT proceed to Step 2.

### 2. Remote Guard

Check for configured remotes:

```
git remote -v
```

If no remotes exist, print: "No git remote configured. Run `/pl-remote-add` to set up a remote first." and exit with code 1.

### 3. Load Config

Read `branch_collab.remote` from `.purlin/config.json`. Default to `"origin"` if the key is absent or the file does not exist. Fallback: if `branch_collab` is absent, read `remote_collab.remote`.

### 4. Dirty Check

```
git status --porcelain
```

Filter out any lines where the file path starts with `.purlin/` — these are excluded from dirty state per the collaboration policy.

If any non-`.purlin/` output remains, abort: "Commit or stash changes before pushing."

### 5. Fetch

```
git fetch <remote>
```

If the remote branch does not exist yet (fetch returns non-zero because the refspec is not found), this is fine — it means we are creating the branch for the first time. Proceed to Step 6 treating the remote as having zero commits (AHEAD state).

### 6. Sync State

Run two range queries:

```
git log <remote>/<branch>..<branch> --oneline
git log <branch>..<remote>/<branch> --oneline
```

Count ahead = lines from query 1, behind = lines from query 2.

Determine state:
- ahead=0, behind=0 -> SAME
- ahead>0, behind=0 -> AHEAD
- ahead=0, behind>0 -> BEHIND
- ahead>0, behind>0 -> DIVERGED

If the remote tracking ref does not exist (first push), treat as AHEAD with ahead = all commits on `<branch>`.

### 7. First-Push Safety Confirmation

On the first push to a remote+branch pair, detected by `git rev-parse --verify <remote>/<branch>` failing (no remote tracking ref exists), display a confirmation prompt:

```
First push to this remote. Please confirm:
  Remote:  <name> (<url>)
  Branch:  <branch>
  Commits: <N> commit(s) will be pushed

Proceed? [Y/n]
```

If the user declines, abort without pushing. Subsequent pushes to the same remote+branch (where the remote tracking ref exists) skip this confirmation.

### 8. Push or Block

**SAME:** Print "Already in sync. Nothing to push." Exit.

**BEHIND:** Print:
```
Local <branch> is BEHIND <remote>/<branch> by M commits. Run /pl-remote-pull before pushing.
```
Exit with failure.

**DIVERGED:** Print the incoming commits:
```
Local <branch> is DIVERGED from <remote>/<branch>.
Remote has M commit(s) not in local <branch>:
  <git log <branch>..<remote>/<branch> --oneline>
Run /pl-remote-pull to merge remote changes before pushing.
```
Exit with failure.

**AHEAD:** Push:
```
git push <remote> <branch>
```
On success: Print "Pushed N commits to `<remote>/<branch>`."
On failure: Print the git error message. Exit with failure.

## FORBIDDEN

- **MUST NOT** execute `git push --force` (or `--force-with-lease`) to any branch. If push fails due to non-fast-forward, report the error and instruct the user to run `/pl-remote-pull`.
- **MUST NOT** push to a branch that does not match the resolved collaboration branch. The Collaboration Branch Guard (Step 1) enforces this — do not bypass it.
- **MUST NOT** pass unchecked user input directly to git commands. Branch names are resolved from `.purlin/runtime/active_branch` or defaulted to `main` — never from raw user input. Remote names come from `.purlin/config.json` with a default of `"origin"`.

## Notes

- Does NOT merge anything. Use `/pl-remote-pull` first if behind or diverged.
- Branches are created via the CDD dashboard, not this command.
- **Mode 1 (no remote):** Detected after the branch guard passes. Prints guidance to run `/pl-remote-add` and exits.
- **Mode 2 (direct mode):** No active branch file → resolves to `main`. Pushes main directly.
- **Mode 3 (collaboration mode):** Active branch file present → pushes that branch.
- If the remote branch does not exist, `git push` creates it automatically. The first-push safety confirmation applies.
