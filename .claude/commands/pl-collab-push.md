Push: push local collaboration branch to remote.

**Owner: All roles — from collaboration branch only**

## Steps

### 0. Session Guard

Read `.purlin/runtime/active_remote_session`. If the file is absent or empty, abort:

```
No active remote session. Use the CDD dashboard to start or join a remote collab session.
```

Extract the session name from the file contents (single line, trimmed).

### 1. Collaboration Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result is not `collab/<session>` (where `<session>` is the value from Step 0), abort immediately:

```
This command must be run from the collaboration branch (collab/<session>).
Current branch: <branch>. Switch to collab/<session> before running /pl-collab-push.
```

Do NOT proceed to Step 2.

### 2. Load Config

Read `remote_collab.remote` from `.purlin/config.json`. Default to `"origin"` if the key is absent or the file does not exist.

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
git log origin/collab/<session>..collab/<session> --oneline
git log collab/<session>..origin/collab/<session> --oneline
```

Count ahead = lines from query 1, behind = lines from query 2.

Determine state:
- ahead=0, behind=0 -> SAME
- ahead>0, behind=0 -> AHEAD
- ahead=0, behind>0 -> BEHIND
- ahead>0, behind>0 -> DIVERGED

If the remote tracking ref does not exist (first push), treat as AHEAD with ahead = all commits on collab/<session>.

### 6. Push or Block

**SAME:** Print "Already in sync. Nothing to push." Exit.

**BEHIND:** Print:
```
Local collab/<session> is BEHIND <remote>/collab/<session> by M commits. Run /pl-collab-pull before pushing.
```
Exit with failure.

**DIVERGED:** Print the incoming commits:
```
Local collab/<session> is DIVERGED from <remote>/collab/<session>.
Remote has M commit(s) not in local collab/<session>:
  <git log collab/<session>..origin/collab/<session> --oneline>
Run /pl-collab-pull to merge remote changes before pushing.
```
Exit with failure.

**AHEAD:** Push:
```
git push <remote> collab/<session>
```
On success: Print "Pushed N commits to <remote>/collab/<session>."
On failure: Print the git error message. Exit with failure.

## Notes

- Does NOT merge anything. Use `/pl-collab-pull` first if behind or diverged.
- Sessions are created via the CDD dashboard, not this command.
- Run from the collaboration branch (collab/<session>) only.
- If the remote branch does not exist, `git push` creates it automatically.
