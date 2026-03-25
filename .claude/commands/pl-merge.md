**Purlin command: Purlin agent only**
**Purlin mode: shared**

Legacy agents: This command is for the Purlin unified agent. It is not available in role-specific agent sessions.
Purlin agent: Merge the current worktree branch back to the source branch and clean up.

---

## Usage

```
/pl-merge
```

## Prerequisites

This command only works when the agent is running in a worktree (launched with `--worktree`). If not in a worktree, respond: "Not in a worktree. Nothing to merge."

## Protocol

1. **Detect worktree state.**
   ```bash
   # Check if we're in a worktree
   git rev-parse --git-common-dir
   ```
   If the common dir differs from the git dir, we're in a worktree.

2. **Commit any pending work** in the current worktree with appropriate mode prefix.

3. **Identify the source branch.** The worktree was created from a base branch (usually `main`). Detect it:
   ```bash
   # The branch we forked from
   git merge-base --fork-point main HEAD 2>/dev/null || git merge-base main HEAD
   ```

4. **Switch to the main working directory** and source branch:
   ```bash
   cd "$PURLIN_PROJECT_ROOT"  # Original project root, not worktree
   git checkout main  # Or whatever the source branch is
   ```

5. **Merge the worktree branch** using the robust merge protocol:
   ```bash
   git merge <worktree-branch> --no-edit
   ```

   **On conflict:**
   - Auto-resolve safe files: `.purlin/delivery_plan.md`, `.purlin/cache/*` (keep main's version)
   - For other conflicts: present the diff to the user and ask for resolution direction
   - Do NOT force-resolve code or spec conflicts automatically

6. **Clean up the worktree:**
   ```bash
   git worktree remove <worktree-path>
   git branch -d <worktree-branch>
   ```

7. **Report:** "Merged [branch] into [source]. Worktree cleaned up. [N files changed]."
