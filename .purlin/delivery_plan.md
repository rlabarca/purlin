# Delivery Plan

**Created:** 2026-03-22
**Total Phases:** 7

## Summary
11 features reset to TODO by recent spec heading migrations and targeted spec changes. 5 are re-verification only (heading renames), 3 are targeted (specific scenario changes), and 3 are full implementations. Phasing ensures dependency ordering is respected and HIGH-complexity features get dedicated phases.

## Execution Groups
- **Group 1:** Phase 1, Phase 3 (no cross-dependencies, can execute in parallel)
- **Group 2:** Phase 2 (depends on Phase 1 from Group 1)
- **Group 3:** Phase 4, Phase 5, Phase 6 (depend on Group 2 but not each other, can execute in parallel)
- **Group 4:** Phase 7 (depends on Phase 5 from Group 3)

## Phase 1 -- Foundation Roots [COMPLETE]
**Features:** project_init.md, critic_tool.md
**Completion Commit:** fc23a65
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** Both are dependency roots that unblock later phases. project_init is targeted (2 scenarios); critic_tool is re-verification only. Parallel build opportunity (independent features).

## Phase 2 -- Core Infrastructure [PENDING]
**Features:** config_layering.md, cdd_status_monitor.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** config_layering depends on project_init (Phase 1); cdd_status_monitor has all deps COMPLETE. config_layering is re-verification; cdd_status_monitor is targeted (Single-Line Status Cells). Parallel build opportunity (independent features).

## Phase 3 -- Independent Skills [COMPLETE]
**Features:** pl_spec_code_audit.md, pl_web_test.md
**Completion Commit:** 0b695e1
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** Both re-verification only. All dependencies are COMPLETE features. No deps on any TODO feature -- can execute in parallel with Phase 1 (Group 1). Parallel build opportunity (independent features).

## Phase 4 -- Dependent Skills [PENDING]
**Features:** pl_update_purlin.md, cdd_spec_map.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** pl_update_purlin depends on config_layering (Phase 2) + project_init (Phase 1); cdd_spec_map depends on cdd_status_monitor (Phase 2). pl_update_purlin is targeted (5 scenarios); cdd_spec_map is re-verification. Parallel build opportunity (independent features).

## Phase 5 -- Branch Collaboration [PENDING]
**Features:** cdd_branch_collab.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** Full implementation, HIGH complexity (67 scenarios). Depends on cdd_status_monitor (Phase 2). Solo phase per sizing cap.

## Phase 6 -- Git Operation Cache [PENDING]
**Features:** git_operation_cache.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** Full implementation, HIGH complexity (26 scenarios). Depends on cdd_status_monitor (Phase 2) + critic_tool (Phase 1). Solo phase per sizing cap. Can execute in parallel with Phase 4 and Phase 5 (Group 3).

## Phase 7 -- What's Different [PENDING]
**Features:** collab_whats_different.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Notes:** Full implementation, HIGH complexity (35 scenarios). Depends on cdd_branch_collab (Phase 5). Solo phase per sizing cap. Must follow Phase 5.

## Plan Amendments
_None._
