# Delivery Plan

**Created:** 2026-03-23
**Total Phases:** 4

## Summary
15 features reset to TODO after spec updates. Work spans Critic core (policy + tool), CDD Dashboard display, Init/Regression infrastructure, and agent skills. Phasing groups features by dependency order and logical cohesion, with two execution groups enabling parallel session execution.

## Execution Groups
- **Group 1:** Phase 1, Phase 2 (no cross-dependencies — can execute in parallel)
- **Group 2:** Phase 3, Phase 4 (both depend on Phase 1 only — can execute in parallel after Group 1)

## Phase 1 -- Critic Foundation [IN_PROGRESS]
**Features:** policy_critic.md, critic_tool.md, policy_release.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --

## Phase 2 -- Init, Regression & Pull [PENDING]
**Features:** project_init.md, init_preflight_checks.md, regression_testing.md, skill_behavior_regression.md, pl_remote_pull.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --

## Phase 3 -- Critic Status & CDD Dashboard [PENDING]
**Features:** qa_verification_effort.md, critic_role_status.md, cdd_status_monitor.md, cdd_qa_effort_display.md, cdd_branch_collab.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --

## Phase 4 -- Audit & Resume Skills [PENDING]
**Features:** pl_spec_code_audit.md, pl_session_resume.md
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --

## Plan Amendments
_None._
