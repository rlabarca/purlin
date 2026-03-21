# Tombstone: continuous_phase_builder

> Retired: 2026-03-20
> Reason: Replaced by interactive multi-phase auto-progression with sub-agent parallel building (see features/subagent_parallel_builder.md)

## Context

The `--continuous` mode in `pl-run-builder.sh` provided automated multi-phase delivery via a bash orchestration loop with LLM evaluator, parallel worktree execution, canvas rendering, plan amendment support, remediation logic, and bootstrap mode. This functionality is now replaced by:

- **Multi-phase auto-progression:** The interactive Builder auto-advances phases when `auto_start: true` (Section 2.8 of `subagent_parallel_builder.md`).
- **Parallel building:** `builder-worker` sub-agents with `isolation: worktree` replace bash worktree orchestration.
- **Test execution:** `verification-runner` sub-agent replaces inline test runs.
- **Merge protocol:** Robust rebase-before-merge replaces the continuous mode's merge handling.

## Files to Delete

- `pl-run-builder.sh`: Remove `--continuous` flag handling and all continuous-mode-specific code (~1700 lines). Includes:
  - Phase orchestration loop
  - LLM evaluator integration (Haiku classifier)
  - Canvas rendering engine (terminal UI)
  - Deferred status tracking
  - Plan amendment processing for parallel workers
  - Remediation logic (dynamic phase insertion)
  - Bootstrap mode (delivery plan creation)
  - `try_auto_resolve_conflicts()` function (ported to `/pl-build` merge protocol -- do NOT delete, move to skill)

## Dependencies to Check

- `instructions/references/phased_delivery.md` Section 10.11 (Continuous Phase Mode): Update to reference deprecation. Remove continuous mode exception from Section 10.3.
- `.purlin/config.json`: Deprecated keys to remove: `continuous_evaluator_model`, `inter_phase_critic`, `max_remediation_attempts`.
- `.purlin/runtime/`: Continuous-mode artifacts to stop generating: `continuous_build_phase_*.log`, phase status JSON, evaluator state files.
- `features/phase_analyzer.md`: Still needed (used by interactive parallel B1). No deletion.
- `tools/delivery/phase_analyzer.py`: Still needed. No deletion.

## What Stays

- `pl-run-builder.sh` as the launcher (minus `--continuous`).
- `tools/delivery/phase_analyzer.py` (still used for feature independence analysis).
- Delivery plan format (unchanged).
- `try_auto_resolve_conflicts()` logic -- ported into the `/pl-build` robust merge protocol.
