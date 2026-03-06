Push: push local collaboration branch to remote.

**Owner: All roles — from collaboration branch only**

## Steps

### 0. Branch Guard

Read `.purlin/runtime/active_branch`. If the file is absent or empty, abort:

```
No active collaboration branch. Use the CDD dashboard to create or join a branch.
```

Extract the branch name from the file contents (single line, trimmed).

### 1. Collaboration Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result does not match the value from Step 0, abort immediately:

```
This command must be run from the collaboration branch (<branch>).
Current branch: <current>. Switch to <branch> before running /pl-remote-push.
```

Do NOT proceed to Step 2.

### 2. Load Config

Read `branch_collab.remote` from `.purlin/config.json`. Default to `"origin"` if the key is absent or the file does not exist. Fallback: if `branch_collab` is absent, read `remote_collab.remote`.

### 3. Dirty Check

```
git status --porcelain
```

Filter out any lines where the file path starts with `.purlin/` — these are excluded from dirty state per the collaboration policy.

If any non-`.purlin/` output remains, abort: "Commit or stash changes before pushing."

### 4. Fetch

```
git fetch <remote>
```

If the remote branch does not exist yet (fetch returns non-zero because the refspec is not found), this is fine — it means we are creating the branch for the first time. Proceed to Step 5 treating the remote as having zero commits (AHEAD state).

### 5. Sync State

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

If the remote tracking ref does not exist (first push), treat as AHEAD with ahead = all commits on <branch>.

### 6. Push or Block

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
On success: Print "Pushed N commits to <remote>/<branch>."
On failure: Print the git error message. Exit with failure.

## Notes

- Does NOT merge anything. Use `/pl-remote-pull` first if behind or diverged.
- Branches are created via the CDD dashboard, not this command.
- Run from the collaboration branch only.
- If the remote branch does not exist, `git push` creates it automatically.
