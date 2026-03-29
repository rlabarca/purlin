---
name: worktree
description: Worktree management. Available in any mode without switching
---

## Usage

```
purlin:worktree list
purlin:worktree cleanup-stale [--dry-run]
```

## Subcommands

### `list`

Show all worktrees with their status. Informational — shows currently active and any preserved worktrees.

1. Run `${CLAUDE_PLUGIN_ROOT}/scripts/worktree/manage.sh list`.
2. Display results:
   ```
   Worktrees:
     W1  Engineer  PID 12345  active    2h ago   purlin-engineer-20260325-1430
     W2  PM        (dead)     stale     5h ago   purlin-pm-20260325-1130
     W3  QA        (no lock)  orphaned  1d ago   purlin-qa-20260324-0900
   ```
3. If no worktrees exist: "No worktrees."

### `cleanup-stale`

Remove stale and orphaned worktrees that are no longer needed. Safety valve for edge cases.

1. Run `${CLAUDE_PLUGIN_ROOT}/scripts/worktree/manage.sh cleanup-stale [--dry-run]`.
2. Skip active worktrees entirely.
3. For each stale/orphaned worktree:
   - Check for uncommitted work: `git -C <path> status --porcelain`
   - If uncommitted work exists: prompt — "Worktree <label> has uncommitted changes. Merge back, or discard?"
     - **Merge:** commit changes, merge to source branch (using merge lock from `purlin:merge`), clean up
     - **Discard:** remove worktree and delete branch without merging
   - If no uncommitted work: auto-remove worktree directory and delete branch
4. Report: "Cleaned up N worktrees."

---

## Notes

- Worktree creation and resume are handled by `purlin:resume` (`--worktree`, `--resume <label>`), not this skill.
- Worktrees are ephemeral by default — session exit always attempts auto-commit + merge. Preserved worktrees exist only when merges fail or sessions end unexpectedly.
- See `features/purlin_worktree_concurrency.md` for the full lifecycle model.
