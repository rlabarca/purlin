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
- **Expected Behavior:** AUTO features MUST NOT be auto-passed. Their automated tests must execute in Steps 2-5, then Step 5a (Phase A Checkpoint) must commit completions, clean workspace, and update CDD status before any manual work begins. The skill file (`pl-verify.md`) must sync with the updated QA_BASE Section 3.3: add the AUTO feature mandate callout, update Step 1 to exclude AUTO features, add Step 5a (Phase A Checkpoint) between Step 5 and Phase A Summary, and update the Critic-run guidance to "once per phase."
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added AUTO exclusion language and regression guidance exclusion to Step 1; added AUTO feature completion path to Step 5; added Step 5a (Phase A Checkpoint) for AUTO finalization, CDD update, and zero-manual-items fast path; clarified Step 11 excludes Step 5a completions.

### [BUG] Step 5a fires before in-session regression suites — clean features not finalized (Discovered: 2026-03-24)
- **Scenario:** Phase A Checkpoint timing
- **Observed Behavior:** QA agent runs in-session regression suites (critic_tool, project_init both PASS), but does not commit [Complete] status tags or update CDD. Features remain as TODO/AUTO in the dashboard. The agent waits for external agent_behavior tests before finalizing anything.
- **Expected Behavior:** Step 5a must fire at two points: (A) after Steps 1-5 for web-test/visual/auto-verified features, and (B) after in-session regression suites pass — BEFORE the external agent_behavior gate. Features that passed in-session must be finalized immediately. The external test gate must NOT block completion of already-clean features. Applies to both AUTO and TODO features whose automated work is satisfied.
- **Action Required:** Builder
- **Status:** OPEN
