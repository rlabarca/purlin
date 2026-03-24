# Delivery Plan

**Created:** 2026-03-23
**Total Phases:** 5

## Summary
25 TODO features require re-verification and bug fixes following a bulk discovery sidecar audit. Phasing splits work by dependency layer (foundations first, CDD dashboard last) with parallel execution groups to enable concurrent Builder sessions. 2 features deferred pending Architect spec resolution.

## Phase 1 -- Foundations [IN_PROGRESS]
**Features:** test_fixture_repo.md, regression_testing.md, context_recovery_hook.md, pm_agent_launcher.md, pl_help.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Parallel Build:** test_fixture_repo, regression_testing independent foundations; context_recovery_hook, pm_agent_launcher, pl_help fully independent
**Execution Group:** A (parallel with Phase 2)

## Phase 2 -- Independent Skills [PENDING]
**Features:** pl_remote_push.md, pl_release_step.md, pl_web_test.md, pl_design_audit.md, release_verify_dependency_integrity.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Parallel Build:** All 5 features fully independent (no mutual dependencies)
**Execution Group:** A (parallel with Phase 1)

## Phase 3 -- Skills & Release Batch 2 [PENDING]
**Features:** pl_spec_code_audit.md, pl_update_purlin.md, release_critic_consistency_check.md, release_audit_automation.md, cdd_qa_effort_display.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Parallel Build:** All 5 independent at phase start (shared deps resolved in Phase 1)
**Execution Group:** B (parallel with Phase 4; depends on Phase 1)

## Phase 4 -- Critic Chain [PENDING]
**Features:** critic_tool.md, skill_behavior_regression.md, critic_role_status.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --
**Parallel Build:** critic_tool + skill_behavior_regression parallel; critic_role_status sequential after critic_tool
**Execution Group:** B (parallel with Phase 3; depends on Phase 1)

## Phase 5 -- CDD Dashboard [PENDING]
**Features:** cdd_status_monitor.md, cdd_spec_map.md, cdd_branch_collab.md, cdd_agent_configuration.md, release_checklist_ui.md
**Completion Commit:** --
**Deferred:** git_operation_cache.md (architect TODO), release_framework_doc_consistency.md (architect TODO)
**QA Bugs Addressed:** --
**Parallel Build:** cdd_status_monitor first; then cdd_spec_map, cdd_branch_collab, cdd_agent_configuration, release_checklist_ui parallel
**Execution Group:** C (depends on Phase 4)

## Plan Amendments
_None._
