Pull: merge latest commits from main into the current worktree branch.

**Owner: All roles** (architect, builder, qa)

## Steps

1. Check that the working tree is clean:
   `git status --porcelain`
   If any output is returned, abort with: "Commit or stash changes before pulling."

2. Run `git merge main` from within the worktree.

3. Report:
   - Number of new commits pulled (from git output)
   - List of new or changed feature files (filter: `features/*.md` in the merge diff)

## Notes

- This command pulls from `main` only — it does not fetch from remote.
- Use this when another role has merged their branch to `main` and you want those changes before continuing your work.
- Example: After Architect merges `spec/collab` to `main`, Builder runs `/pl-work-pull` to get the new specs before implementing.
