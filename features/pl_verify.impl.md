# Implementation Notes: pl_verify

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | [ACKNOWLEDGED] The QA agent was not automatically executing automated tests for features with `qa_status: AUTO` during Phase A. Root cause: PURLIN_BASE Section 3.3 and the skill file did not explicitly distinguish AUTO features from builder-verified. The QA agent conflated "zero manual work" with "no QA action needed." Fix applied to PURLIN_BASE (authoritative source): added AUTO feature mandate callout, excluded AUTO from Step 1 auto-pass, clarified Step 5 completes AUTO feature verification. Skill file update routed to Engineer via discovery sidecar. Spec §2.3 Step 1 now has explicit AUTO exclusion. (2026-03-24, resolved 2026-03-26) | DISCOVERY | RESOLVED |

## Implementation Summary

The `/pl-verify` skill file (`skills/verify/SKILL.md`) is a QA agent instruction file implementing the interactive feature verification workflow described in `features/pl_verify.md`.

## Bug Fixes

**[CLARIFICATION]** Fixed hardcoded `scripts/test_support/harness_runner.py` paths at lines 206-207 of the skill file. These were the only two occurrences not using the `${TOOLS_ROOT}` variable established in the Path Resolution section. All other references (e.g., line 86 for Step 3 harness invocation, line 364 for scan.sh) already used `${TOOLS_ROOT}` correctly. (Severity: INFO)

## Spec-Implementation Alignment

Verified all spec requirements (Sections 2.1-2.4) are covered in the skill file:
- 2.1 Role Gating: QA ownership declaration at line 1, redirect at line 3.
- 2.2 Scope Selection: scan.sh runs for both batch and scoped modes (Scope section), argument-based filtering from scan results, scope modes in Step 0.
- 2.2.0 Lifecycle Diagnostic: cross-branch status commit detection, auto-verify/auto_start non-blocking exit.
- 2.3 Phase A: Steps 1-5a + Summary all present and ordered correctly. AUTO exclusion in Step 1, AUTO completion in Step 5, Phase A Checkpoint in Step 5a.
- 2.4 Phase B: Steps 6-11 all present with correct content.

No additional gaps found between spec and implementation.

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 40 total, 40 passed
- AP scan: clean
- Date: 2026-03-24

## AUTO Feature Handling Gap

**[DISCOVERY] [ACKNOWLEDGED]** The QA agent was not automatically executing automated tests for features with `qa_status: AUTO` during Phase A. Root cause: PURLIN_BASE Section 3.3 and the skill file did not explicitly distinguish AUTO features from builder-verified. The QA agent conflated "zero manual work" with "no QA action needed." Fix applied to PURLIN_BASE (authoritative source): added AUTO feature mandate callout, excluded AUTO from Step 1 auto-pass, clarified Step 5 completes AUTO feature verification. Skill file update routed to Engineer via discovery sidecar. (2026-03-24)

## Scoped Mode Scan and Cross-Branch Diagnostic

### [CLARIFICATION] Scoped mode now runs scan.sh for lifecycle resolution

**Spec ref:** Section 2.2 (Scope Selection), Section 2.2.0 (Lifecycle Diagnostic)

Scoped mode (`/pl-verify <feature>`) previously did not run `scan.sh`, causing the agent to read inline file tags for lifecycle determination. Since lifecycle is git-commit-based (status commits), this defaulted to TODO for features that had no inline tag — even when a `[Ready for Verification]` status commit existed on the current branch. This was reported by a user running Engineer and QA in separate terminal sessions.

**Fix:** The Scope section now runs `scan.sh --only features` for both batch and scoped modes, ensuring authoritative git-based lifecycle resolution. The scoped feature's entry is extracted from the scan JSON output.

**Cross-branch diagnostic:** Additionally, when lifecycle is TODO (scoped) or zero TESTING features exist (batch), a new Lifecycle Diagnostic section runs `git log --all` to check for status commits on other branches. This is diagnostic only — it does not change lifecycle resolution (which remains current-branch-only per `purlin_scan_engine.md` Section 2.1). The agent prints a branch mismatch message and stops (interactive) or exits cleanly (auto-verify/auto_start). (2026-03-28)
