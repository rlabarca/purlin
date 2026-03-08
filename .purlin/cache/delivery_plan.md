# Delivery Plan

**Created:** 2026-03-07
**Total Phases:** 2

## Summary

All 49 TODO features fail `structural_completeness` in the Critic's Implementation Gate. No test quality issues -- the code and tests pass. The failures are test *reporting* format issues introduced by the new Section 2.15 rules (required fields, test file discoverability, anti-stub validation). Phase 1 fixes all ~33 features with real test runners (format/discoverability fixes across ~25 shared runners). Phase 2 addresses ~16 features with bare stubs (delete) or zero-test counts (write real tests).

## Phase 1 -- Test Infrastructure Compliance [IN_PROGRESS]

**Features:** agent_behavior_tests.md, agent_launchers_common.md, cdd_agent_configuration.md, cdd_isolated_teams.md, cdd_lifecycle.md, cdd_qa_effort_display.md, cdd_spec_map.md, cdd_startup_controls.md, cdd_status_monitor.md, collab_whats_different.md, config_layering.md, context_guard.md, impl_notes_companion.md, isolated_teams.md, models_configuration.md, pl_cdd.md, pl_context_guard.md, pl_design_audit.md, pl_design_ingest.md, pl_session_resume.md, pl_spec_code_audit.md, pl_whats_different.md, project_init.md, python_environment.md, qa_verification_effort.md, release_audit_automation.md, release_checklist_core.md, release_checklist_ui.md, release_push_to_remote.md, release_step_management.md, spec_code_audit_role_clarity.md, spec_from_code.md, test_fixture_repo.md

**Work:** Fix ~25 shared test runners to output compliant `tests.json` (add `passed`/`failed`/`total` fields, add `test_file` for colocated tests in `tools/`). Re-run each runner to regenerate. Status-tag all affected features.

**Completion Commit:** --
**QA Bugs Addressed:** --

## Phase 2 -- Stub Deletion & Real Test Writing [PENDING]

**Features:** cdd_branch_collab.md, instruction_audit.md, pl_help.md, pl_isolated_pull.md, pl_isolated_push.md, pl_remote_pull.md, pl_remote_push.md, pl_update_purlin.md, release_critic_consistency_check.md, release_doc_consistency_check.md, release_framework_doc_consistency.md, release_record_version_notes.md, release_submodule_safety_audit.md, release_verify_dependency_integrity.md, release_verify_zero_queue.md, workflow_checklist_system.md

**Work:**
- **Delete 7 bare stubs** (no test code exists): workflow_checklist_system, cdd_branch_collab, pl_isolated_push, pl_isolated_pull, pl_remote_push, pl_remote_pull, pl_update_purlin. Deletion correctly shows QA: N/A.
- **Write real tests** for 8 features with `total: 0`: instruction_audit, release_record_version_notes, release_submodule_safety_audit, release_verify_dependency_integrity, release_verify_zero_queue, release_critic_consistency_check, release_doc_consistency_check, release_framework_doc_consistency.
- **Investigate** pl_help (manual-only spec vs. automated scenario classification mismatch).

**Completion Commit:** --
**QA Bugs Addressed:** --

## Plan Amendments

_None._
