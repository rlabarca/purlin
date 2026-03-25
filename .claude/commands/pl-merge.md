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

1. **Acquire merge lock.** Write PID + timestamp to `.purlin/cache/merge.lock` in the main working directory. If the lock exists and the PID is alive (another worktree is merging), print: "Merge blocked: another worktree is merging to main (PID <pid>). Retrying..." Retry after 2s, up to 3 times. If still blocked, abort: "Merge lock timeout. Try again later."

   If the lock exists but the PID is dead, remove the stale lock and proceed.

2. **Detect worktree state.**
   ```bash
   git rev-parse --git-common-dir
   ```
   If the common dir differs from the git dir, we're in a worktree.

3. **Commit any pending work** in the current worktree with appropriate mode prefix.

4. **Identify the source branch.** The worktree was created from a base branch (usually `main`). Detect it:
   ```bash
   git merge-base --fork-point main HEAD 2>/dev/null || git merge-base main HEAD
   ```

5. **Switch to the main working directory** and source branch:
   ```bash
   cd "$PURLIN_PROJECT_ROOT"  # Original project root, not worktree
   git checkout main
   ```

6. **Merge the worktree branch** using the robust merge protocol:
   ```bash
   git merge <worktree-branch> --no-edit
   ```

   **On conflict:**
   - Auto-resolve safe files: `.purlin/delivery_plan.md`, `.purlin/cache/*` (keep main's version)
   - For other conflicts: present the diff to the user and ask for resolution direction
   - Do NOT force-resolve code or spec conflicts automatically
   - On unresolvable conflict: release merge lock, write breadcrumb per `purlin_worktree_concurrency.md` Section 2.8

7. **Clean up:**
   - Delete `.purlin_session.lock` from the worktree
   - Remove the worktree: `git worktree remove <worktree-path>`
   - Delete the branch: `git branch -d <worktree-branch>`

8. **Release merge lock.** Delete `.purlin/cache/merge.lock`.

9. **Report:** "Merged [branch] into [source]. Worktree cleaned up. [N files changed]."
