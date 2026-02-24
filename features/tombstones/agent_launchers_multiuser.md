# TOMBSTONE: agent_launchers_multiuser

**Retired:** 2026-02-23
**Reason:** Replaced by `isolated_agents.md`. The three-role fixed worktree model (Architect/Builder/QA each with a dedicated session) is superseded by the flexible named isolation system, where any agent can create a named worktree via `create_isolation.sh <name>`.

## Files to Delete

- `tools/collab/setup_worktrees.sh` — entire file; replaced by `tools/collab/create_isolation.sh`
- `tools/collab/teardown_worktrees.sh` — entire file; replaced by `tools/collab/kill_isolation.sh`

## Dependencies to Check

- `features/cdd_collab_mode.md` — references `/start-collab` (calls `setup_worktrees.sh`) and `/end-collab` (calls `teardown_worktrees.sh`). These endpoints are replaced by `/isolate/create` and `/isolate/kill`. Feature is being updated concurrently.
- `features/workflow_checklist_system.md` — post-rebase command cleanup referenced `setup_worktrees.sh` behavior. Feature is being updated concurrently to use the new `create_isolation.sh` approach.
- `.claude/commands/pl-work-push.md` — rename to `pl-local-push.md`; update content to remove role inference and role-specific checklist steps.
- `.claude/commands/pl-work-pull.md` — rename to `pl-local-pull.md`; update content references from "pl-work-push" to "pl-local-push".

## Context

The old system used `setup_worktrees.sh` to create exactly three worktrees at once (`.worktrees/architect-session/`, `.worktrees/build-session/`, `.worktrees/qa-session/`) on branches `spec/collab`, `build/collab`, `qa/collab`. This enforced a linear three-role collaboration model. The `teardown_worktrees.sh` script removed all three simultaneously.

The new system (`isolated_agents.md`) creates one named worktree per call. No role is assumed. Multiple isolations can coexist. Users pick meaningful names (≤8 chars). This matches the natural use case: a Builder working on a feature in isolation while main continues to evolve, or two Builder sessions on parallel features.

The `.claude/commands/` handling is also inverted: instead of deleting all commands from the worktree, the new approach copies ONLY `pl-local-push.md` and `pl-local-pull.md` into the worktree's `.claude/commands/`, then deletes all other files. Tree climbing handles discovery of all other commands.
