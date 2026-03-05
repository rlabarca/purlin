Push: run handoff checks and merge current isolation branch to the collaboration branch.

**Owner: All roles** (no role inference — generic handoff)

## Steps

### 0. Isolation Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result does NOT start with `isolated/`, abort immediately:

```
This command is only valid inside an isolated session.
Current branch: <branch>. Run /pl-local-push from a worktree
on an isolated/* branch.
```

Do NOT proceed to Step 1.

### 1. Resolve PROJECT_ROOT

Use `PURLIN_PROJECT_ROOT` env var if set. Otherwise, parse `git worktree list --porcelain` and identify the main checkout: the entry whose `branch` field does NOT start with `refs/heads/isolated/`, or the first worktree entry. Extract its absolute path.

### 2. Detect Collaboration Branch

Read `.purlin/runtime/active_remote_session` from PROJECT_ROOT (the main checkout, not the worktree). If the file exists and is non-empty, the collaboration branch is `collab/<value>` (trimmed). Otherwise, the collaboration branch is `main`.

Print: `Collaboration branch: <collaboration-branch>`

### 3. Pre-Flight Sync Check

**a. Dirty check:**
```
git status --porcelain
```

Filter out any lines where the file path starts with `.purlin/` — these are environment-specific
config files excluded from dirty state per the collaboration policy.

If any non-.purlin/ output remains, abort: "Commit or stash changes before pushing."

**b. Behind-collaboration-branch check:**
```
git log HEAD..<collaboration-branch> --oneline
git log <collaboration-branch>..HEAD --oneline
```
Count N = commits behind the collaboration branch, M = commits ahead of the collaboration branch.

If N > 0 AND M == 0 (BEHIND):
- Print: "Branch is N commit(s) behind <collaboration-branch> — auto-rebasing before merge check."
- Run: `git rebase <collaboration-branch>` (fast-forward — no local commits to replay, no conflict risk)
- If rebase fails, abort: "Auto-rebase failed — resolve conflicts manually, then retry."
- After rebase, re-run dirty check (step 3a) to confirm clean state.

If N > 0 AND M > 0 (DIVERGED):
- Block immediately. Print:
  ```
  Branch is DIVERGED from <collaboration-branch> — cannot auto-resolve.
  <collaboration-branch> has N commit(s) this branch is missing:
    <git log HEAD..<collaboration-branch> --oneline>
  Run /pl-local-pull to rebase and resolve before retrying /pl-local-push.
  ```
- Stop here. Do NOT proceed to handoff checklist.

### 4. Safety Check

Verify the main checkout (`PROJECT_ROOT`) is on the collaboration branch:
```
git -C <PROJECT_ROOT> rev-parse --abbrev-ref HEAD
```
If the result does not match the collaboration branch, abort: "Main checkout is not on branch <collaboration-branch> — cannot merge."

### 5. Run Handoff Checklist

Run `tools/handoff/run.sh` from within the worktree.

### 6. Decision

**If any item is FAIL or PENDING:**
- Print: "Handoff checks failed — merge blocked."
- List each failing item with its reason.
- Do NOT merge. Stop here.

**If all items PASS:**
- Run from PROJECT_ROOT: `git -C <PROJECT_ROOT> merge --ff-only <current-branch>`
- If `--ff-only` fails: print "Branches diverged — run /pl-local-pull to rebase, then retry."

### 7. Report

On successful merge:
```
Merged <branch> into <collaboration-branch> (N commits).
```

## Notes

- Does NOT push to remote. Use `/pl-collab-push` separately if needed.
- The collaboration branch is `collab/<session>` when a remote session is active, or `main` when no session is active.
- Auto-rebase in BEHIND state uses `git rebase <collaboration-branch>` to preserve linear history required by `--ff-only` merge.
- No role inference or role-specific checklist items — the handoff checklist is generic.
