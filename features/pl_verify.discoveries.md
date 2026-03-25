# User Testing Discoveries: PL Verify

### [BUG] Hardcoded tools/test_support/harness_runner.py paths (Discovered: 2026-03-23)
- **Observed Behavior:** Hardcoded tools/test_support/harness_runner.py paths at pl-verify.md lines 206-207.
- **Expected Behavior:** Should use ${TOOLS_ROOT}/test_support/harness_runner.py.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_verify.impl.md for context.

### [BUG] Skill file does not enforce AUTO feature mandate from QA_BASE (Discovered: 2026-03-24)
- **Scenario:** Phase A Step 1 auto-pass
- **Observed Behavior:** QA agent auto-passes or skips AUTO features (`qa_status: AUTO`) during Phase A, requiring explicit user intervention to run their automated tests (web tests, @auto scenarios). The skill file lacks the AUTO exclusion language added to QA_BASE Section 3.3.
- **Expected Behavior:** AUTO features MUST NOT be auto-passed. Their automated tests must execute in Steps 2-5, then Step 5a (Phase A Checkpoint) must commit completions, clean workspace, and update CDD status before any manual work begins. The skill file (`pl-verify.md`) must sync with the updated QA_BASE Section 3.3: add the AUTO feature mandate callout, update Step 1 to exclude AUTO features, add Step 5a (Phase A Checkpoint) between Step 5 and Phase A Summary, and update the Critic-run guidance to "once per phase."
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Added AUTO exclusion language and regression guidance exclusion to Step 1; added AUTO feature completion path to Step 5; added Step 5a (Phase A Checkpoint) for AUTO finalization, CDD update, and zero-manual-items fast path; clarified Step 11 excludes Step 5a completions.

### [BUG] Step 5a fires before in-session regression suites — clean features not finalized (Discovered: 2026-03-24)
- **Scenario:** Phase A Checkpoint timing
- **Observed Behavior:** QA agent runs in-session regression suites (critic_tool, project_init both PASS), but does not commit [Complete] status tags or update CDD. Features remain as TODO/AUTO in the dashboard. The agent waits for external agent_behavior tests before finalizing anything.
- **Expected Behavior:** Step 5a must fire at two points: (A) after Steps 1-5 for web-test/visual/auto-verified features, and (B) after in-session regression suites pass — BEFORE the external agent_behavior gate. Features that passed in-session must be finalized immediately. The external test gate must NOT block completion of already-clean features. Applies to both AUTO and TODO features whose automated work is satisfied.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Restructured Step 5a to fire at two checkpoints (A and B). Reordered regression suite section: in-session suites run first (step 8), Step 5a(B) checkpoint fires (step 9), then agent_behavior gate (step 10). Updated Step 5a to cover both AUTO and TODO features. Updated Step 5 and Step 11 to reference both feature types.

### [BUG] QA agent re-runs passing regression suites unnecessarily (Discovered: 2026-03-24)
- **Scenario:** Phase A regression suite status table
- **Observed Behavior:** QA agent flags `release_record_version_notes` regression.json as `[PASS] ← prior run; re-run needed` despite the result being PASS with source files unmodified (not STALE). The agent repeatedly requests re-validation of already-passing suites, creating unnecessary work.
- **Expected Behavior:** The staleness check is the sole arbiter: PASS + source not modified = valid pass, no re-run. The skill file must add an explicit note after the staleness classification (step 2 of the regression suite status table) prohibiting re-run requests for valid PASS results. Text: "PASS results are valid — do NOT flag as 'prior run; re-run needed' or request fresh execution. Only STALE, FAIL, and NOT_RUN require action."
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Added explicit note after staleness classification in step 2 of the regression suite status table: "PASS results are valid — do NOT flag as 'prior run; re-run needed' or request fresh execution. Only STALE, FAIL, and NOT_RUN require action."

### [BUG] AUTO features from action items excluded from verification batch (Discovered: 2026-03-24)
- **Scenario:** Scope selection (batch mode)
- **Observed Behavior:** QA agent only processes `testing_features` from the startup briefing. Features with `qa_status: AUTO` that appear in QA action items (category `visual_verification`) but NOT in `testing_features` are excluded from Phase A. The QA agent sees them as action items but does not include them in the verification workflow, requiring explicit user intervention.
- **Expected Behavior:** The skill file's Scope section must batch the UNION of: (1) `testing_features` and (2) features from QA action items with `visual_verification` or `regression_run` categories. Change line 16 from "batch ALL TESTING features" to include both sources. This ensures AUTO features are processed during Phase A regardless of lifecycle state.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Updated Scope section to batch the union of testing_features and QA action items with visual_verification/regression_run categories, with explicit "Do NOT limit to testing_features alone" guard.

### [BUG] QA agent commits regression artifacts but skips status tag commits in Step 5a (Discovered: 2026-03-24)
- **Scenario:** Phase A Checkpoint — Step 5a
- **Observed Behavior:** QA agent runs 5 AUTO web tests (all PASS), commits regression artifacts and scenario JSON files, then moves to the manual checklist. It does NOT commit `[Complete] [Verified]` status tags and does NOT run `status.sh`. Features remain AUTO in the dashboard because the Critic tracks lifecycle via status commit messages, not file changes.
- **Expected Behavior:** Step 5a in the skill file must enforce the full sequence: (1) commit artifacts, (2) commit one `--allow-empty` status tag per feature, (3) run `status.sh` as a HARD GATE before Phase B, (4) verify features cleared from AUTO/TODO in Critic output. Add the "CRITICAL: Committing regression artifacts is NOT finalization" callout from QA_BASE. The CDD update is a hard gate — do NOT present the manual checklist until it completes.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Restructured Step 5a: reordered to artifacts-first then status tags, added CRITICAL callout about artifacts not being finalization, added --allow-empty with ONE COMMIT PER FEATURE mandate, made CDD update a HARD GATE, added verify-finalization step checking AUTO/TODO clearing.
