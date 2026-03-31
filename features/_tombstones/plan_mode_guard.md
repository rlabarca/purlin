# TOMBSTONE: plan_mode_guard

**Retired:** 2026-03-31
**Reason:** Mode system removed in mode→sync migration (v0.8.6). Write guard now enforces file classification without mode state.

## Files to Delete

None — all implementation code was already removed during the mode→sync migration:
- `hooks/scripts/plan-exit-mode-clear.sh` (deleted)
- `.purlin/runtime/current_mode` state file (deleted)

## Dependencies to Check

None. No features reference plan_mode_guard.

## Context

This feature provided a PostToolUse hook on ExitPlanMode that cleared the `.purlin/runtime/current_mode` state file when leaving Plan mode. The entire mode system was replaced by sync tracking (`purlin_sync_system.md`) in v0.8.6. The write guard (`write-guard.sh`) now enforces file classification (INVARIANT/UNKNOWN blocking) without any mode state. No ExitPlanMode hook is needed.
