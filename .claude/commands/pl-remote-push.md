Push: push local collaboration branch to remote.

**Owner: All roles**

The command operates in three modes:
- **Mode 1 — No remote configured:** Guides the user through adding a git remote, then pushes.
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

If no remotes exist, guide the user through setup:

1. Scan for hosting hints:
   - Check `~/.ssh/config` for configured hosts (e.g., `github.com`, `gitlab.com`, `bitbucket.org`).
   - Check git credential helpers: `git config --global --get-regexp credential`.
   - Check for hosting CLIs: `gh` (GitHub), `glab` (GitLab).
2. Present the user with a prompt:
   ```
   No remote configured. Enter a git remote URL
   (SSH or HTTPS — any git-compatible host):
   ```
   If hosting hints were found in step 1, list them as informational suggestions below the prompt (e.g., "Detected: github.com (SSH key)"). Do not auto-select any host.
3. Accept any valid git URL format: `git@host:user/repo.git`, `https://host/user/repo.git`, `ssh://...`, or local paths.
4. Ask for the remote name (default `"origin"`).
5. Execute `git remote add <name> <url>`.
6. Verify connectivity: `git ls-remote <name>`. If it fails, report the error and let the user correct the URL.
7. Proceed to push.

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

## Notes

- Does NOT merge anything. Use `/pl-remote-pull` first if behind or diverged.
- Branches are created via the CDD dashboard, not this command.
- **Mode 1 (no remote):** Detected after the branch guard passes. Scans for hosting hints (SSH keys, credential helpers, CLIs) and prompts for any git-compatible remote URL.
- **Mode 2 (direct mode):** No active branch file → resolves to `main`. Pushes main directly.
- **Mode 3 (collaboration mode):** Active branch file present → pushes that branch.
- If the remote branch does not exist, `git push` creates it automatically. The first-push safety confirmation applies.
