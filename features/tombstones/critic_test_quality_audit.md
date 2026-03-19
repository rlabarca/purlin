# Tombstone: Critic Test Quality Audit Trail

> **Retired:** 2026-03-18
> **Reason:** The subagent test quality evaluation mandate (`policy_test_quality.md` Section 2.6) and its Critic backstop (`policy_critic.md` Section 2.17) have been eliminated. The Builder no longer spawns Haiku subagents for test quality evaluation, and the Critic no longer checks for `### Test Quality Audit` sections in companion files. Test quality is governed by guidelines in `policy_test_quality.md` (AP-1 through AP-4) without machine enforcement.

## Files to Delete

- `features/critic_test_quality_audit.md` -- the feature spec itself
- Any test files in `tests/critic_test_quality_audit/` (if present)

## Dependencies to Check

- `tools/critic/run.sh` or equivalent Critic implementation -- remove the `missing_test_quality_audit` category check
- Any companion files (`features/*.impl.md`) with `### Test Quality Audit` sections -- these are now inert (no action needed, they are historical records)

## Context

This feature existed solely to implement the backstop defined in `policy_critic.md` Section 2.17. That section has been replaced by Section 2.17 (Regression Guidance Detection), which serves a different purpose. The original 2.17 was deleted because:

1. The subagent quality audit it backstopped (`policy_test_quality.md` Section 2.6) was eliminated
2. Without the subagent audit, there is no `### Test Quality Audit` section to check for
3. QA regression testing provides independent behavioral verification, making Builder-side traceability enforcement redundant
