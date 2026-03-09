# TOMBSTONE: workflow_checklist_system

**Retired:** 2026-03-08
**Reason:** Handoff checklist system retired. Only consumer was /pl-isolated-push, which is also being retired.

## Files to Delete

- `tools/handoff/` -- entire directory (global_steps.json, run.sh)
- `tools/release/resolve.py` -- remove `checklist_type="handoff"` routing (keep `"release"` routing intact)

## Dependencies to Check

- `.purlin/handoff/` -- may exist in consumer projects (not present in Purlin core)

## Context

The handoff checklist system was architecturally parallel to the release checklist, reusing the same step schema and resolver. It ran pre-merge checks (clean worktree, current Critic report) before /pl-isolated-push could merge an isolation branch. With isolated teams removed, this entire system is unused.
