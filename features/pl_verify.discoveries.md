# User Testing Discoveries: PL Verify

### [BUG] Hardcoded tools/test_support/harness_runner.py paths (Discovered: 2026-03-23)
- **Observed Behavior:** Hardcoded tools/test_support/harness_runner.py paths at pl-verify.md lines 206-207.
- **Expected Behavior:** Should use ${TOOLS_ROOT}/test_support/harness_runner.py.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_verify.impl.md for context.
