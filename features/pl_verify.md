# Feature: Verification

> Label: "/pl-verify Verification"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The primary QA skill that executes interactive feature verification. Operates in two phases: Phase A runs automated scenarios (@auto classification, harness execution, visual smoke checks) without human intervention; Phase B assembles and presents a condensed manual verification checklist for remaining items. Supports batch mode (all TESTING features) and scoped mode (single named feature), with scope filtering (full, targeted, cosmetic, dependency-only), tier-based prioritization, and structured failure processing with discovery recording.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Scope Selection

- If an argument is provided, scope verification to that single feature.
- If no argument is provided, batch the union of: (1) ALL TESTING features from `testing_features`, and (2) features from QA action items with `visual_verification` or `regression_run` categories (these are AUTO features that may not be in the TESTING lifecycle but still need automated re-verification). Do NOT limit to `testing_features` alone.
- Scoped verification modes: `full` (default), `targeted:Scenario A,Scenario B`, `cosmetic` (skip), `dependency-only`.

### 2.3 Phase A -- Automated Execution

- **Step 1 (Auto-pass):** Credit builder-verified features (TestOnly, Skip) with zero QA scenarios. AUTO features (`qa_status: AUTO`) are NOT auto-passed — they have automated QA work (web tests, @auto scenarios) that MUST execute in Steps 2–5.
- **Step 2 (Smoke gate):** If test priority tiers exist, run smoke-tier scenarios first with halt-on-fail behavior.
- **Step 3 (Run @auto):** Execute @auto-tagged scenarios via the harness runner. Create BUG discoveries for failures.
- **Step 4 (Classify untagged):** Propose automation for untagged scenarios. Tag as @auto (author + run regression JSON) or @manual based on feasibility and user approval.
- **Step 5 (Visual smoke):** For features with visual specs, run web test or request screenshot for verification. For AUTO features where all items are automated/web-test, this step completes their verification.
- **Step 5a (Phase A Checkpoint, MANDATORY HARD GATE):** Fires at two points: (A) after Steps 1-5, and (B) after in-session regression suites pass — BEFORE the external agent_behavior test gate. At each checkpoint, IN ORDER: (1) commit regression artifacts, (2) commit `[Complete] [Verified]` status tags — ONE `--allow-empty` COMMIT PER FEATURE (this is what changes lifecycle, not the artifact commits), (3) run `{tools_root}/cdd/status.sh` as a hard gate — do NOT proceed to Phase B until it completes, (4) verify finalized features no longer show AUTO/TODO in Critic output — if they do, a status tag was missed. The external test gate does NOT block finalization. If zero manual items remain, skip to Session Conclusion.
- Print Phase A Summary bridging to Phase B.
- **Regression result validity:** A `regression.json` with `status: "PASS"` where source files are NOT modified since the result mtime is a valid pass. Do NOT re-run, do NOT flag as "prior run; re-run needed." Only STALE, FAIL, and NOT_RUN require action.

### 2.4 Phase B -- Manual Verification Checklist

- **Step 6 (Assembly):** Collect remaining testable items into a flat-numbered list across features. Exclude @auto scenarios. Apply web-test visual dedup.
- **Step 7 (Presentation):** Sort by tier priority (smoke first). Use condensed two-line format: Do/Verify. Default-to-PASS semantics.
- **Step 8 (Response Processing):** Parse flexible responses: "all pass", failure numbers ("F3, F7"), "help N", "detail N", "DISPUTE N", "stop".
- **Step 9 (Failure Processing):** Classify failures as BUG/DISCOVERY/INTENT_DRIFT/SPEC_DISPUTE. Record in discovery sidecar files.
- **Step 10 (Exploratory):** Ask if anything unexpected was noticed beyond the checklist.
- **Step 11 (Batch Completion):** Mark eligible features complete with `[Verified]` tag. Run Critic once for all completions.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-verify
    Then the command responds with a redirect message

#### Scenario: Scoped mode targets single feature

    Given feature_a is in TESTING state
    When /pl-verify is invoked with argument "feature_a"
    Then only feature_a scenarios are verified

#### Scenario: Batch mode includes all TESTING features

    Given feature_a and feature_b are both in TESTING state
    When /pl-verify is invoked without arguments
    Then both features are included in the verification pass

#### Scenario: Cosmetic scope skips feature entirely

    Given feature_a has cosmetic verification scope
    When /pl-verify processes feature_a
    Then feature_a is skipped with "QA skip (cosmetic change)" message

#### Scenario: Auto-pass credits builder-verified features

    Given feature_a has builder status DONE and zero QA scenarios
    When Phase A Step 1 runs
    Then feature_a is auto-passed with acknowledgment message

#### Scenario: Completion commits include Verified tag

    Given all scenarios for feature_a passed verification
    When the completion commit is created
    Then the commit message includes "[Verified]"

#### Scenario: Failures create discovery entries

    Given item 3 fails during manual verification
    When the failure is processed
    Then a discovery entry is recorded in the feature's discovery sidecar file
    And the discovery includes observed behavior and classification

### QA Scenarios

None.
