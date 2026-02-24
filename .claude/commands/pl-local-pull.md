Pull: merge latest commits from main into the current isolation branch.

**Owner: All roles** (no role inference — generic pull)

## Steps

### 0. Isolation Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result does NOT start with `isolated/`, abort immediately:

```
This command is only valid inside an isolated session.
Current branch: <branch>. Run /pl-local-pull from a worktree
on an isolated/* branch.
```

Do NOT proceed to Step 1.

### 1. Resolve PROJECT_ROOT

Use `PURLIN_PROJECT_ROOT` env var if set. Otherwise, parse `git worktree list --porcelain` and identify the main checkout: the entry whose `branch` field is `refs/heads/main`, or the first worktree entry. Extract its absolute path.

### 2. Check Dirty State

```
git status --porcelain
```
If any output is returned, abort: "Commit or stash changes before pulling."

### 3. Report Sync State

Gather both counts before taking any action:

```
# Commits on main that this branch is missing:
git log HEAD..main --oneline

# Commits on this branch not yet on main:
git log main..HEAD --oneline
```

Let N = number of commits behind, M = number of commits ahead.

Print: "You are N commit(s) behind / M commit(s) ahead of main."

Determine and print the state label:
- N=0, M=0 → `State: SAME`
- N=0, M>0 → `State: AHEAD`
- N>0, M=0 → `State: BEHIND`
- N>0, M>0 → `State: DIVERGED`

### 4. State Dispatch

**SAME (N=0, M=0):**
Print: "Already up to date — nothing to pull or push." Stop.

**AHEAD (N=0, M>0):**
Print: "M commits ahead, nothing to pull. Run /pl-local-push when ready." Stop.

**BEHIND (N>0, M=0):**
Run:
```
git rebase main
```
This is a fast-forward rebase — no local commits to replay, no conflict risk.
On success, print: "Rebased onto main (fast-forward). N new commits incorporated."

**DIVERGED (N>0, M>0):**

1. Print DIVERGED context before rebasing. Show all commits coming in from main and which files each touched:
   ```
   git log HEAD..main --stat --oneline
   ```
   Label this output: `Incoming from main (N commits):` — one commit per line with its stat block.

2. Run:
   ```
   git rebase main
   ```

3. On clean success, print: "Rebased M commits onto main. Branch is now AHEAD by M commits. Ready to push."

### 5. Conflict Handling

When `git rebase main` halts with conflicts, for **each conflicting file** print:

```
CONFLICT: <filepath>

  What main changed in this file:
    <git log HEAD..main --oneline -- <filepath>>

  What your branch changed in this file:
    <git log main..ORIG_HEAD --oneline -- <filepath>>

  Resolution hint: <path-scoped guidance>
```

Path-scoped guidance (derived from file path prefix):
- `features/` → "Architect priority: accept spec changes, incorporate non-conflicting additions from main."
- `tests/` → "Preserve all passing test cases. Review both sides."
- Everything else → "Review both sides carefully. If unsure, run `git rebase --abort` and ask for help."

After printing all per-file conflict blocks, print:
```
Resolve each conflict, then run `git add <file>` and `git rebase --continue`.
To abandon: `git rebase --abort` (restores your branch to its pre-rebase state).
```

### 6. Post-Rebase Command Re-Sync

**Only runs after a successful rebase (BEHIND or DIVERGED states). Skipped for SAME and AHEAD.**

After rebase, the git checkout may restore command files that were intentionally removed from this worktree. Re-apply the isolation command file setup:

a. List all files in `.claude/commands/`. For each file that is NOT `pl-local-push.md` and NOT `pl-local-pull.md`:
   - Delete the file from disk: `rm .claude/commands/<file>`
   - Mark the deletion as intentional: `git update-index --skip-worktree .claude/commands/<file>`

b. Ensure `pl-local-push.md` and `pl-local-pull.md` are present in `.claude/commands/`. If missing, copy from the project root's `.claude/commands/`.

c. After re-sync, verify `git status --porcelain` reports no file changes in `.claude/commands/`.

## Notes

- This command pulls from the local `main` ref only — it does not fetch from remote. Run `git fetch origin main` first if you need remote changes.
- Use this when another agent has merged their branch to `main` and you want those changes before continuing your work.
- `/pl-local-push` auto-rebases if the branch is BEHIND main (safe, no conflicts). If the branch is DIVERGED, `/pl-local-push` blocks and instructs you to run `/pl-local-pull` manually.
