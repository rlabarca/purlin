# Feature: Plan Mode Exit Guard

> Label: "Tool: Plan Mode Exit Guard"
> Category: "Framework Core"
> Status: RETIRED
> Retired-by: purlin_sync_system.md
> Prerequisite: purlin_sync_system.md

## Retirement Notice

This feature was retired as part of the mode-to-sync migration (v0.8.6). The mode system has been replaced by the sync tracking system (`purlin_sync_system.md`). Without modes, there is no mode state to clear on plan exit.

**What was removed:**
- `hooks/scripts/plan-exit-mode-clear.sh` — PostToolUse hook on ExitPlanMode
- `.purlin/runtime/current_mode` state file
- Mode guard enforcement (replaced by classification-based write guard)

**What replaced it:**
- The write guard (`write-guard.sh`) now enforces file classification (INVARIANT/UNKNOWN blocking) without mode state
- No ExitPlanMode hook is needed — agents can write any classified file type at any time
- Sync tracking (`sync_state.json` + `sync_ledger.json`) observes spec-code drift without blocking
