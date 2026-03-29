## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Skill file (skills/worktree/SKILL.md) defines `list` and `cleanup-stale` subcommands. Worktree infrastructure exists (scripts/hooks/merge-worktrees.sh, .purlin_worktree_label convention, .purlin_session.lock format). Integration tests in tests/qa/.

**[IMPL]** Worktree management helper at scripts/worktree/manage.sh implements both subcommands. `list`: parses `git worktree list --porcelain`, filters for .purlin/worktrees/, reads session lock and label files, classifies status via `kill -0 $PID` liveness check, computes age, outputs JSON. `cleanup-stale`: same discovery, checks for uncommitted work via `git status --porcelain`, removes clean stale/orphaned worktrees (directory + branch), supports `--dry-run`, outputs structured JSON. Uses PURLIN_PROJECT_ROOT with climbing fallback, BSD/GNU date compatibility, --help flag per CLI convention.
