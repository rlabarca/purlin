Push: push local main branch to the remote collab branch.

**Owner: All roles — from main checkout only**

## Steps

### 0. Main Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result is not `main`, abort immediately:

```
This command is only valid from the main checkout.
Current branch: <branch>. Run /pl-remote-push from the project root (branch: main).
```

Do NOT proceed to Step 1.

### 1. Session Guard

Read `.purlin/runtime/active_remote_session`. If the file is absent or empty, abort:

```
No active remote session. Use the CDD dashboard to start or join a remote collab session.
```

Extract the session name from the file contents (single line, trimmed).

### 2. Load Config

Read `remote_collab.remote` from `.purlin/config.json`. Default to `"origin"` if the key is absent or the file does not exist.

Construct the target branch: `collab/<session>`.

### 3. Dirty Check

```
git status --porcelain
```

Filter out any lines where the file path starts with `.purlin/` — these are excluded from dirty state per the collaboration policy.

If any non-`.purlin/` output remains, abort: "Commit or stash changes before pushing."

### 4. Fetch

```
git fetch <remote> collab/<session>
```

If the remote branch does not exist yet (fetch returns non-zero because the refspec is not found), this is fine — it means we are creating the branch for the first time. Proceed to Step 5 treating the remote as having zero commits (AHEAD state).

### 5. Sync State

Run two range queries:

```
git log origin/collab/<session>..main --oneline
git log main..origin/collab/<session> --oneline
```

Count ahead = lines from query 1, behind = lines from query 2.

Determine state:
- ahead=0, behind=0 -> SAME
- ahead>0, behind=0 -> AHEAD
- ahead=0, behind>0 -> BEHIND
- ahead>0, behind>0 -> DIVERGED

If the remote tracking ref does not exist (first push), treat as AHEAD with ahead = all commits on main since the branch point.

### 6. Push or Block

**SAME:** Print "Already in sync. Nothing to push." Exit.

**BEHIND:** Print:
```
Local main is BEHIND <remote>/collab/<session> by M commits. Run /pl-remote-pull before pushing.
```
Exit with failure.

**DIVERGED:** Print the incoming commits:
```
Local main is DIVERGED from <remote>/collab/<session>.
Remote has M commit(s) not in local main:
  <git log main..origin/collab/<session> --oneline>
Run /pl-remote-pull to merge remote changes before pushing.
```
Exit with failure.

**AHEAD:** Push:
```
git push <remote> main:collab/<session>
```
On success: Print "Pushed N commits to <remote>/collab/<session>."
On failure: Print the git error message. Exit with failure.

## Notes

- Does NOT merge anything. Use `/pl-remote-pull` first if behind or diverged.
- Sessions are created via the CDD dashboard, not this command.
- Run from the project root (branch: main) only.
- If the remote branch does not exist, `git push` creates it automatically.
