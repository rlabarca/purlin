Pull: merge latest commits from main into the current worktree branch.

**Owner: All roles** (architect, builder, qa)

## Steps

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
git -C <PROJECT_ROOT> log HEAD..main --oneline

# Commits on this branch not yet on main:
git -C <PROJECT_ROOT> log main..HEAD --oneline
```

Let N = number of commits behind, M = number of commits ahead.

Print: "You are N commit(s) behind / M commit(s) ahead of main."

### 4. If Already Up To Date (N == 0)

Print: "Already up to date. M commits ready to push."

Stop — do not run any merge.

### 5. If Behind Main (N > 0)

Run:
```
git merge main
```

On success, report:
- Number of new commits pulled (N)
- List of new or changed feature files from the merge diff:
  ```
  git diff HEAD~N..HEAD -- features/*.md --name-only
  ```
  Print each path, one per line. If none, print "No feature file changes in this pull."

On conflict: print the conflicting files and instruct: "Resolve conflicts manually, then run `git merge --continue`."

## Notes

- This command pulls from the local `main` ref only — it does not fetch from remote. Run `git fetch origin main` first if you need remote changes.
- Use this when another role has merged their branch to `main` and you want those changes before continuing your work.
- Example: After Architect merges `spec/collab` to `main`, Builder runs `/pl-work-pull` to get the new specs before implementing.
- `/pl-work-push` calls this logic automatically (auto-pull) if the branch is behind main at push time.
