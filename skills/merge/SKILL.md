---
name: merge
description: Merge the current worktree branch back to the source branch and clean up
---

## Usage

```
purlin:merge
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

4. **Save paths and identify source branch.** Capture these values BEFORE any directory changes:
   ```bash
   WORKTREE_PATH="$(pwd)"
   MAIN_ROOT="$(git rev-parse --git-common-dir | sed 's|/\.git$||')"
   WORKTREE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
   SOURCE_BRANCH="main"
   ```

5. **Merge from the main working directory.** Run the checkout and merge via `cd "$MAIN_ROOT"` in each Bash call:
   ```bash
   cd "$MAIN_ROOT" && git checkout "$SOURCE_BRANCH"
   ```
   ```bash
   cd "$MAIN_ROOT" && git merge "$WORKTREE_BRANCH" --no-edit
   ```

   **On conflict:**
   - Auto-resolve safe files: `.purlin/delivery_plan.md`, `.purlin/cache/*` (keep main's version)
   - For other conflicts: present the diff to the user and ask for resolution direction
   - Do NOT force-resolve code or spec conflicts automatically
   - On unresolvable conflict: release merge lock, write breadcrumb per `purlin_worktree_concurrency.md` Section 2.8

6. **Clean up in a SINGLE Bash call.** This is CRITICAL — the worktree removal deletes the agent's CWD, and the Bash tool validates CWD existence before executing any command. If cleanup is split across multiple Bash calls, all calls after the worktree removal will fail with "Path does not exist." Run everything as one chained command:
   ```bash
   cd "$MAIN_ROOT" && rm -f "$WORKTREE_PATH/.purlin_session.lock" && git worktree remove "$WORKTREE_PATH" --force && git worktree prune && git branch -d "$WORKTREE_BRANCH" && rm -f .purlin/cache/merge.lock && echo "Cleanup complete"
   ```
   If any cleanup step fails, the remaining steps still execute (use `;` instead of `&&` for non-critical steps like lock removal). The `cd "$MAIN_ROOT"` MUST be first — it is what keeps the shell alive after the worktree directory is gone.

7. **Update terminal identity.** The agent is no longer in a worktree. Update all terminal environments to reflect the source branch:
   ```bash
   source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<project>"
   ```
   Replace `<project>` with the project name. Produces format: `(<branch>) <project>`.

8. **Report:** "Merged [branch] into [source]. Worktree cleaned up. [N files changed]."
