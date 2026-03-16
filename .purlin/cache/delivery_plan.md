# Delivery Plan

**Created:** 2026-03-16
**Total Phases:** 8

## Summary
Remediation of 16 features reset to TODO by the Architect's deep spec-code audit. All items are low-complexity (review+retag, verify compliance, or small code fixes ~20 lines total). Phased for incremental QA checkpoints. Plan restructured to respect dependency graph ordering.

## Phase 1 -- Config & Script Fixes [COMPLETE]
**Features:** pm_agent_launcher.md, continuous_phase_builder.md
**Completion Commit:** 73e9e88
**QA Bugs Addressed:** --

## Phase 2 -- Design Anchors (Foundation) [PENDING]
**Features:** design_modal_standards.md, design_visual_standards.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 3 -- Design & AFT Anchors [PENDING]
**Features:** design_artifact_pipeline.md, arch_automated_feedback_tests.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 4 -- Policy Anchors (Critic & Release) [PENDING]
**Features:** policy_critic.md, policy_release.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 5 -- Command & Companion [PENDING]
**Features:** impl_notes_companion.md, pl_session_resume.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 6 -- Policy & CDD Core [PENDING]
**Features:** policy_branch_collab.md, cdd_status_monitor.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 7 -- CDD Consumers [PENDING]
**Features:** release_checklist_ui.md, cdd_branch_collab.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 8 -- Config & Behavior Tests [PENDING]
**Features:** cdd_agent_configuration.md, agent_behavior_tests.md
**Completion Commit:** --
**QA Bugs Addressed:** --

## Plan Amendments
Restructured Phases 2-8 to resolve dependency cycles detected by phase analyzer. Anchor nodes moved to early phases; consumer features ordered after their transitive prerequisites (agent_behavior_tests depends transitively on cdd_agent_configuration via cdd_startup_controls).
