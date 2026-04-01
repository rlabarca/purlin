---
name: worktree
description: Worktree management (list, cleanup)
---

Manage git worktrees for parallel development sessions.

## Usage

```
purlin:worktree list                    List active worktrees
purlin:worktree cleanup [--dry-run]     Remove stale worktrees
```

## list

Show all git worktrees:

```bash
git worktree list
```

Display results:

```
Worktrees:
  /path/to/main           abc1234 [main]
  /path/to/feature-branch def5678 [feature/auth]
```

If no extra worktrees exist: "No additional worktrees."

## cleanup

Remove worktrees that are no longer needed.

1. List all worktrees via `git worktree list`.
2. For each non-main worktree:
   - Check for uncommitted changes: `git -C <path> status --porcelain`
   - If uncommitted changes: warn and skip (unless user confirms discard).
   - If clean: `git worktree remove <path>`.
3. Prune stale worktree references: `git worktree prune`.

With `--dry-run`: show what would be removed without removing.

```
Cleaned up N worktrees.
```
