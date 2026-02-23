Push: run handoff checklist and merge current branch to main.

**Owner: All roles** (architect, builder, qa)

## Steps

1. Infer role from current branch name:
   - `spec/*` → architect
   - `build/*` → builder
   - `qa/*` → qa
   - Other → ask user to specify role

2. Run `tools/handoff/run.sh --role <role> --project-root <PURLIN_PROJECT_ROOT>`.

3. If all steps PASS (exit code 0):
   a. Verify the main checkout is on branch `main`:
      `git -C <PROJECT_ROOT> rev-parse --abbrev-ref HEAD`
      If not `main`, abort with: "Safety check failed: main checkout is not on 'main' branch."
   b. Merge current branch into main using fast-forward only:
      `git -C <PROJECT_ROOT> merge --ff-only <current-branch>`
   c. Report: "Merged <current-branch> into main (N commits)."

4. If any steps FAIL or PENDING (exit code 1):
   - Print: "Handoff checks failed — merge blocked."
   - List each failing item from the checklist output.
   - Do NOT merge.

## Notes

- Does NOT push to remote. Use `git push origin main` separately.
- `PROJECT_ROOT` is determined from `PURLIN_PROJECT_ROOT` env var if set, otherwise from `git worktree list --porcelain` to find the main checkout path.
- `--ff-only` ensures no accidental merge commits. If the branch cannot be fast-forwarded, instruct the user to rebase first.
