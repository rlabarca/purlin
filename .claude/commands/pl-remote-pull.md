Pull: pull remote collab branch into local main.

**Owner: All roles — from main checkout only**

## Steps

### 0. Main Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result is not `main`, abort immediately:

```
This command is only valid from the main checkout.
Current branch: <branch>. Run /pl-remote-pull from the project root (branch: main).
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

If any non-`.purlin/` output remains, abort: "Commit or stash changes before pulling."

### 4. Fetch

```
git fetch <remote> collab/<session>
```

If the fetch fails (remote branch does not exist), abort: "Remote branch collab/<session> not found on <remote>. Verify the session exists."

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

### 6. Merge or No-op

**SAME:** Print "Local main is already in sync with remote." Exit.

**AHEAD:** Print "Local main is AHEAD by N commits. Nothing to pull — run /pl-remote-push when ready." Exit.

**BEHIND:** Fast-forward merge:
```
git merge --ff-only origin/collab/<session>
```
On success: Print "Fast-forwarded local main by M commits from <remote>/collab/<session>."
On failure (race condition where ff is not possible): Print "Fast-forward failed — re-run /pl-remote-pull." Exit with failure.

**DIVERGED:** Print pre-merge context:
```
Diverged state detected.
Remote has M commit(s) not in local main:
  <git log main..origin/collab/<session> --stat --oneline>
Merging origin/collab/<session> into local main...
```

Run:
```
git merge origin/collab/<session>
```

On clean merge: Print "Local main updated: merged <remote>'s M commits into main."

On conflict: For each conflicting file, print:
```
CONFLICT: <filepath>

  Remote commits that touched this file:
    <git log main..origin/collab/<session> --oneline -- <filepath>>

  Local commits that touched this file:
    <git log origin/collab/<session>..main --oneline -- <filepath>>
```

Then print:
```
Resolve each conflict, then run `git add <file>` and `git merge --continue`.
To abandon: `git merge --abort` (restores main to its pre-merge state).
```
Exit with failure.

**No cascade.** After `/pl-remote-pull` updates main, any active isolations that are BEHIND will show BEHIND in the ISOLATED TEAMS section and sync themselves via `/pl-local-pull` when ready. Each isolation controls its own branch.

## Notes

- Uses `git merge` (not rebase) on main — main is a shared branch; rebase would rewrite history that other contributors depend on.
- Does NOT cascade to isolated team worktrees. Each isolation syncs itself via `/pl-local-pull`.
- Run from the project root (branch: main) only.
