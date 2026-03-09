# TOMBSTONE: policy_collaboration

**Retired:** 2026-03-08
**Reason:** Policy anchor for isolated agent collaboration retired. Entire content (worktree naming, merge-before-proceed, PURLIN_PROJECT_ROOT in worktrees, ff-only merge, three-layer sync stack) is specific to the isolated teams model being removed.

## Files to Delete

No implementation code to delete -- this is a policy anchor. Its constraints were implemented by tools now being retired (create_isolation.sh, kill_isolation.sh, /pl-isolated-push, /pl-isolated-pull).

## Dependencies to Check

- `features/config_layering.md` -- remove `> Prerequisite: features/policy_collaboration.md` (covered in Phase 2)
- `features/pl_agent_config.md` -- remove `> Prerequisite: features/policy_collaboration.md` (covered in Phase 2)
- `features/policy_branch_collab.md` -- remove `> Prerequisite: features/policy_collaboration.md` (covered in Phase 2)

## Context

This policy defined invariants for the isolated agent collaboration model: isolation naming conventions, worktree location, ff-only merge, PURLIN_PROJECT_ROOT requirements, ACTIVE_EDITS.md multi-architect protocol, and the three-layer sync stack. With isolated teams removed, branch collaboration (policy_branch_collab.md) stands independently.
