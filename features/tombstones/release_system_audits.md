# TOMBSTONE: release_system_audits

**Retired:** 2026-03-26
**Reason:** Replaced by the Agentic Toolbox system (features/toolbox_core.md, features/pl_toolbox.md).

## Retired Features

- release_audit_automation.md
- release_audit_automation.impl.md
- release_audit_automation.discoveries.md
- release_verify_zero_queue.md
- release_verify_zero_queue.impl.md
- release_verify_dependency_integrity.md
- release_verify_dependency_integrity.impl.md
- release_verify_dependency_integrity.discoveries.md
- release_submodule_safety_audit.md
- release_submodule_safety_audit.impl.md
- release_doc_consistency_check.md
- release_doc_consistency_check.impl.md
- release_critic_consistency_check.md
- release_critic_consistency_check.impl.md
- release_critic_consistency_check.discoveries.md
- release_framework_doc_consistency.md
- release_framework_doc_consistency.impl.md
- release_framework_doc_consistency.discoveries.md

## Files to Delete

- `tools/release/test_release_audit.py` -- old audit test suite

NOTE: The audit scripts themselves (verify_zero_queue.py, verify_dependency_integrity.py, etc.) are PRESERVED -- they have been copied to `tools/toolbox/`. Only the test file listed above should be deleted.

## Dependencies to Check

- References to `tools/release/verify_*.py` scripts updated to `tools/toolbox/` paths
- Audit step references in release checklist configs updated to toolbox action references
- Test imports referencing `tools/release/` audit modules updated

## Context

This group contained the release audit automation framework and its individual audit checks: zero-queue verification (all features must reach Engineer DONE and QA CLEAN/N/A), dependency integrity validation (cycle/orphan detection via graph.py), submodule safety audits, documentation consistency checks, critic consistency checks, and framework documentation consistency checks. These deterministic audit scripts extracted manual release verification into automated checks producing structured JSON output. The scripts themselves have been preserved in `tools/toolbox/` as reusable actions; only the release-system-specific test harness and feature specs are retired.
