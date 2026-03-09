# TOMBSTONE: isolated_teams

**Retired:** 2026-03-08
**Reason:** Isolated teams (git worktree management) feature removed from Purlin.

## Files to Delete

- `tools/collab/create_isolation.sh` -- entire file
- `tools/collab/kill_isolation.sh` -- entire file
- `tools/collab/test_isolation.py` -- entire file

## Dependencies to Check

- `.gitignore` -- remove patterns for `pl-run-*-architect.sh`, `pl-run-*-builder.sh`, `pl-run-*-qa.sh`, `.worktrees/`
- `tools/cdd/serve.py` -- calls `create_isolation.sh` and `kill_isolation.sh` via `/isolate/create` and `/isolate/kill` endpoints (covered by cdd_isolated_teams tombstone)

## Context

This feature provided `create_isolation.sh` and `kill_isolation.sh` for creating/destroying named git worktrees with generated launcher scripts. Retired because the isolated teams collaboration model is being removed in favor of branch-only collaboration.
