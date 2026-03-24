# User Testing Discoveries: PL Verify

### [BUG] Hardcoded tools/test_support/harness_runner.py paths (Discovered: 2026-03-23)
- **Observed Behavior:** Hardcoded tools/test_support/harness_runner.py paths at pl-verify.md lines 206-207.
- **Expected Behavior:** Should use ${TOOLS_ROOT}/test_support/harness_runner.py.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_verify.impl.md for context.

### [BUG] Skill file does not enforce AUTO feature mandate from QA_BASE (Discovered: 2026-03-24)
- **Scenario:** Phase A Step 1 auto-pass
- **Observed Behavior:** QA agent auto-passes or skips AUTO features (`qa_status: AUTO`) during Phase A, requiring explicit user intervention to run their automated tests (web tests, @auto scenarios). The skill file lacks the AUTO exclusion language added to QA_BASE Section 3.3.
- **Expected Behavior:** AUTO features MUST NOT be auto-passed. Their automated tests must execute in Steps 2-5. The skill file (`pl-verify.md`) must sync with the updated QA_BASE Section 3.3: add the AUTO feature mandate callout, update Step 1 to exclude AUTO features, and update Step 5 to note that AUTO features complete their verification there.
- **Action Required:** Builder
- **Status:** OPEN
