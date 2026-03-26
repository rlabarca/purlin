# Feature: Verification

> Label: "Agent Skills: QA: /pl-verify Verification"
> Category: "Agent Skills: QA"

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
- Per-feature scoped verification modes: `full` (default), `targeted:Scenario A,Scenario B`, `cosmetic` (skip), `dependency-only`.

### 2.2.1 Execution Modes

The `--mode` flag controls which *type* of verification work runs. This is orthogonal to feature scope — you can combine `--mode auto` with a single feature argument.

| Flag | What runs | What's skipped |
|------|-----------|----------------|
| (no flag) | Full pipeline: Phase A + Phase B | Nothing |
| `--mode auto` | Phase A Steps 2-5 only (@auto scenarios, visual smoke) | Auto-pass (Step 1), classification (Step 4), Phase B manual checklist |
| `--mode smoke` | Phase A Step 2 only (smoke-tier scenarios) | Everything else |
| `--mode regression` | Phase A regression suites only (Step 0b + Step 5a regression checkpoint) | All other steps, Phase B |
| `--mode manual` | Phase B only (assemble + present manual checklist) | Entire Phase A |

Execution modes MUST NOT change what gets committed — a mode that skips steps simply doesn't execute them. Features that would have been finalized in a skipped step remain in their current state.

When `--mode` is combined with a feature argument, both filters apply: e.g., `/pl-verify notifications --mode smoke` runs only smoke-tier scenarios for the notifications feature.

### 2.3 Phase A -- Automated Execution

- **Step 1 (Auto-pass):** Credit builder-verified features (TestOnly, Skip) with zero QA scenarios. AUTO features (`qa_status: AUTO`) are NOT auto-passed — they have automated QA work (web tests, @auto scenarios) that MUST execute in Steps 2–5.
- **Step 2 (Smoke gate):** If test priority tiers exist, run smoke-tier scenarios first with halt-on-fail behavior.
- **Step 3 (Run @auto):** Execute @auto-tagged scenarios via the harness runner. Create BUG discoveries for failures.
- **Step 4 (Classify untagged):** Propose automation for untagged scenarios. Tag as @auto (author + run regression JSON) or @manual based on feasibility and user approval.
- **Step 5 (Visual smoke):** For features with visual specs, run web test or request screenshot for verification. For AUTO features where all items are automated/web-test, this step completes their verification.
- **Step 5a (Phase A Checkpoint, MANDATORY HARD GATE):** Fires at two points: (A) after Steps 1-5, and (B) after in-session regression suites pass — BEFORE the external agent_behavior test gate. At each checkpoint, IN ORDER: (1) commit regression artifacts, (2) commit `[Complete] [Verified]` status tags — ONE `--allow-empty` COMMIT PER FEATURE (this is what changes lifecycle, not the artifact commits), (3) run `{tools_root}/cdd/scan.sh` as a hard gate — do NOT proceed to Phase B until it completes, (4) verify finalized features no longer show AUTO/TODO in scan output — if they do, a status tag was missed. The external test gate does NOT block finalization. If zero manual items remain, skip to Session Conclusion.
- Print Phase A Summary bridging to Phase B.
- **Regression result validity:** A `regression.json` with `status: "PASS"` where source files are NOT modified since the result mtime is a valid pass. Do NOT re-run, do NOT flag as "prior run; re-run needed." Only STALE, FAIL, and NOT_RUN require action.

### 2.4 Phase B -- Manual Verification Checklist

- **Step 6 (Assembly):** Collect remaining testable items into a flat-numbered list across features. Exclude @auto scenarios. Apply web-test visual dedup.
- **Step 7 (Presentation):** Sort by tier priority (smoke first). Use condensed two-line format: Do/Verify. Default-to-PASS semantics.
- **Step 8 (Response Processing):** Parse flexible responses: "all pass", failure numbers ("F3, F7"), "help N", "detail N", "DISPUTE N", "stop".
- **Step 9 (Failure Processing):** Classify failures as BUG/DISCOVERY/INTENT_DRIFT/SPEC_DISPUTE. Record in discovery sidecar files.
- **Step 10 (Exploratory):** Ask if anything unexpected was noticed beyond the checklist.
- **Step 11 (Batch Completion):** Mark eligible features complete with `[Verified]` tag. Run `scan.sh` to confirm status transitions.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given an Engineer agent session
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

#### Scenario: Auto mode runs only automated scenarios

    Given features are in TESTING state with @auto scenarios
    When /pl-verify is invoked with --mode auto
    Then Phase A Steps 2-5 execute (@auto scenarios, visual smoke)
    And Phase B manual checklist is skipped entirely

#### Scenario: Smoke mode runs only smoke-tier scenarios

    Given smoke-tier scenarios exist for a feature
    When /pl-verify is invoked with --mode smoke
    Then only smoke-tier scenarios execute
    And all other steps and Phase B are skipped

#### Scenario: Regression mode runs only regression suites

    Given regression suites exist for TESTING features
    When /pl-verify is invoked with --mode regression
    Then only regression suites execute and are evaluated
    And Phase A steps 1-5 and Phase B are skipped

#### Scenario: Manual mode skips Phase A entirely

    Given features have both @auto and @manual scenarios
    When /pl-verify is invoked with --mode manual
    Then Phase A is skipped
    And Phase B manual checklist is assembled and presented

#### Scenario: Execution mode combines with feature scope

    Given feature_a has smoke-tier and standard scenarios
    When /pl-verify is invoked with "feature_a --mode smoke"
    Then only smoke-tier scenarios for feature_a execute

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
