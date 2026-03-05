Pull: pull remote collaboration branch into local collaboration branch.

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
Current branch: <branch>. Switch to collab/<session> before running /pl-collab-pull.
```

Do NOT proceed to Step 2.

### 2. Load Config

Read `remote_collab.remote` from `.purlin/config.json`. Default to `"origin"` if the key is absent or the file does not exist.

### 3. Dirty Check

```
git status --porcelain
```

Filter out any lines where the file path starts with `.purlin/` — these are excluded from dirty state per the collaboration policy.

If any non-`.purlin/` output remains, abort: "Commit or stash changes before pulling."

### 4. Fetch

```
git fetch <remote>
```

If the fetch fails (remote branch does not exist), abort: "Remote branch collab/<session> not found on <remote>. Verify the session exists."

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

### 6. Merge or No-op

**SAME:** Print "Local collab/<session> is already in sync with remote." Exit.

**AHEAD:** Print "Local collab/<session> is AHEAD by N commits. Nothing to pull — run /pl-collab-push when ready." Exit.

**BEHIND:** Fast-forward merge:
```
git merge --ff-only origin/collab/<session>
```
On success: Print "Fast-forwarded local collab/<session> by M commits from <remote>/collab/<session>."
On failure (race condition where ff is not possible): Print "Fast-forward failed — re-run /pl-collab-pull." Exit with failure.

**DIVERGED:** Print pre-merge context:
```
Diverged state detected.
Remote has M commit(s) not in local collab/<session>:
  <git log collab/<session>..origin/collab/<session> --stat --oneline>
Merging origin/collab/<session> into local collab/<session>...
```

Run:
```
git merge origin/collab/<session>
```

On clean merge: Print "Local collab/<session> updated: merged <remote>'s M commits."

On conflict: For each conflicting file, print:
```
CONFLICT: <filepath>

  Remote commits that touched this file:
    <git log collab/<session>..origin/collab/<session> --oneline -- <filepath>>

  Local commits that touched this file:
    <git log origin/collab/<session>..collab/<session> --oneline -- <filepath>>
```

Then print:
```
Resolve each conflict, then run `git add <file>` and `git merge --continue`.
To abandon: `git merge --abort` (restores collab/<session> to its pre-merge state).
```
Exit with failure.

**No cascade.** After `/pl-collab-pull` updates the collaboration branch, any active isolations that are BEHIND will show BEHIND in the ISOLATED TEAMS section and sync themselves via `/pl-local-pull` when ready. Each isolation controls its own branch.

### 7. Post-Merge Digest Generation

After a successful merge (BEHIND fast-forward or DIVERGED clean merge), auto-generate the "What's Different?" digest. This step is informational and does not block or fail the pull.

1. Run the generation script:
```
bash <tools_root>/collab/generate_whats_different.sh <session>
```
where `<tools_root>` is from `.purlin/config.json` (default `tools`).

2. Read the generated file at `features/digests/whats-different.md` and display its content inline.

3. If the script fails or the file is not written, print a warning and continue — do not fail the pull.

**Skip this step** when the merge result is SAME, AHEAD, or DIVERGED-with-conflicts (no successful merge occurred).

## Notes

- Uses `git merge` (not rebase) on the collaboration branch — it is a shared branch; rebase would rewrite history that other contributors depend on.
- Does NOT cascade to isolated team worktrees. Each isolation syncs itself via `/pl-local-pull`.
- Run from the collaboration branch (collab/<session>) only.
