# Feature: Verification

> Label: "Agent Skills: QA: purlin:verify Verification"
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

- Both scoped mode (feature argument) and batch mode (no argument) MUST run `scan.sh --only features` and use the scan results as the authoritative source for lifecycle, test status, regression status, and delivery plan data. The agent MUST NOT determine lifecycle by reading inline file tags alone — lifecycle is git-commit-based (status commits).
- If an argument is provided, extract that feature's entry from the scan results. If the feature is not found in scan output, error: "Feature <arg> not found in features/."
- If no argument is provided, batch the union of: (1) ALL TESTING features from `testing_features`, and (2) features from QA action items with `visual_verification` or `regression_run` categories (these are AUTO features that may not be in the TESTING lifecycle but still need automated re-verification). Do NOT limit to `testing_features` alone.
- Per-feature scoped verification modes: `full` (default), `targeted:Scenario A,Scenario B`, `cosmetic` (skip), `dependency-only`.

### 2.2.0 Lifecycle Diagnostic

When the scan resolves a feature's lifecycle to TODO (scoped mode) or finds zero TESTING features (batch mode), `purlin:verify` MUST check for status commits on other local branches before concluding the feature is not ready. This detects cross-session branch divergence where Engineer committed status tags on a different branch than the one QA is on.

- **Scoped mode:** When the scoped feature's lifecycle from scan is TODO, run `git log --all --oneline --grep='status(' | grep '<feature>'` to check for status commits on other branches. If found, print a branch mismatch diagnostic naming the other branch(es) and do not proceed with verification against stale state.
- **Batch mode:** When zero TESTING features are found in the scan, run the same cross-branch check for any `Ready for Verification` commits. If found, report them with merge/checkout suggestions.
- **Genuinely TODO:** If no cross-branch status commits are found, the feature is genuinely TODO. Print that the feature is not yet marked for verification. Do not proceed.
- **`--auto-verify` / `auto_start: true` compatibility:** The diagnostic MUST NOT block automated workflows. In automated modes, log the diagnostic message and exit to Session Conclusion (zero items verified). Do NOT wait for user input or enter Phase A/B with stale data.
- **No-op when features found:** When TESTING features ARE found (scoped or batch), this diagnostic does not fire. Normal Phase A/B flow proceeds unmodified.

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

When `--mode` is combined with a feature argument, both filters apply: e.g., `purlin:verify notifications --mode smoke` runs only smoke-tier scenarios for the notifications feature.

### 2.2.2 Auto-Verify Flag

`--auto-verify` enables the Phase A.5 auto-fix iteration loop (Section 2.3.2). When present:

- The full pipeline runs (Phase A + Phase A.5 + Phase B).
- After Phase A completes, if any automated tests failed, the agent automatically iterates: switching to Engineer mode to fix failures, switching back to QA to re-run, up to 5 rounds.
- Only after ALL automated tests pass (or max iterations exhausted) does the agent proceed to Phase B manual verification.
- Passed tests are never re-run — only scenarios with FAIL status are re-executed.

`--auto-verify` is mutually exclusive with `--mode`. It is also activated when `auto_start: true` is set in the agent's session config.

### 2.2.3 Interactive Strategy Menu

When `--auto-verify` is NOT active and `auto_start` is `false`, the agent MUST present a strategy menu after Phase A completes (before Phase B). This gives the user control over how to proceed based on Phase A results.

The menu is presented when Phase A has failures, regression gaps, or remaining manual items. Options:

| Choice | Behavior |
|--------|----------|
| Auto-fix | Enter Phase A.5 loop (same as `--auto-verify`) |
| Run automated only | Current Phase A behavior, then proceed to Phase B |
| Smoke only | Re-run Step 2 smoke gate only |
| Skip to manual | Proceed directly to Phase B |
| Exit | Save checkpoint via `purlin:resume save`, end session |

If Phase A had zero failures (across all three sources defined in Section 2.3.1) and zero gaps, the menu is skipped — proceed directly to Phase B (or skip Phase B if zero manual items).

### 2.3 Phase A -- Automated Execution

- **Step 0c (Regression Readiness Check):** Before any tests run, scan all in-scope features for @auto scenarios that lack regression JSON (`tests/qa/scenarios/<feature>.json`). Also check smoke-tier features that lack `_smoke.json`. If `--auto-verify` or `auto_start`: use an internal mode switch to Engineer (Section 2.3.2) to author ALL missing regression and smoke JSON upfront, then switch back to QA. If interactive: count gaps and surface them in the strategy menu (Section 2.2.3). This ensures all tests exist before any tests run, giving the smoke gate (Step 2) full coverage.
- **Step 1 (Auto-pass):** Credit builder-verified features (TestOnly, Skip) with zero QA scenarios. AUTO features (`qa_status: AUTO`) are NOT auto-passed — they have automated QA work (web tests, @auto scenarios) that MUST execute in Steps 2–5.
- **Step 2 (Smoke gate):** If test priority tiers exist, run smoke-tier scenarios first with halt-on-fail behavior.
- **Step 3 (Run @auto):** Execute @auto-tagged scenarios via the harness runner. Create BUG discoveries for failures. These failures feed into Phase A.5 (not just deferred to a future session).
- **Step 4 (Classify untagged):** Propose automation for untagged scenarios. Tag as @auto (author + run regression JSON) or @manual based on feasibility and user approval.
- **Step 5 (Visual smoke):** For features with visual specs, run web test or request screenshot for verification. For AUTO features where all items are automated/web-test, this step completes their verification.
- **Step 5a (Phase A Checkpoint, MANDATORY HARD GATE):** Fires at three points: (A) after Steps 1-5, (B) after in-session regression suites pass, and (C) after Phase A.5 auto-fix loop completes. At each checkpoint, IN ORDER: (1) commit regression artifacts, (2) commit `[Complete] [Verified]` status tags — ONE `--allow-empty` COMMIT PER FEATURE — for features where all automated work passed (unit tests in `tests.json`, regression suites, @auto scenarios) AND zero @manual scenarios remain unverified. Features with passing automated work but pending @manual scenarios are NOT finalized here — they proceed to Phase B. (3) run the MCP `purlin_scan` tool as a hard gate — do NOT proceed to Phase B until it completes, (4) verify finalized features no longer show AUTO/TODO in scan output — if they do, a status tag was missed. The external test gate does NOT block finalization. If zero manual items remain, skip to Session Conclusion.
- Print Phase A Summary bridging to Phase A.5 or Phase B.
- **Regression result validity:** A `regression.json` with `status: "PASS"` where source files are NOT modified since the result mtime is a valid pass. Do NOT re-run, do NOT flag as "prior run; re-run needed." Only STALE, FAIL, and NOT_RUN require action.

### 2.3.1 Phase A Summary and Strategy Dispatch

After Phase A Steps 0c–5a complete, print a summary of automated results (auto-passed, smoke gate, @auto results, classifications, visual checks, regression suite status, unit test status from `tests.json`).

**Dispatch logic:**

"Automated failures" means the union of: (1) regression suite failures (`regression.json` with `status: "FAIL"` or `"STALE"`) across ALL suites that were run — not just in-scope TESTING features, (2) @auto scenario failures from Phase A Step 3, AND (3) unit test failures (`tests.json` with `status: "FAIL"` for any in-scope feature). All three sources MUST be checked — if any single source has failures, the dispatch enters Phase A.5. **Regression failures are never scoped:** `--auto-verify` runs all regression suites and any failure in any suite triggers the auto-fix loop regardless of that feature's lifecycle status.

- If `--auto-verify` or `auto_start: true`: MUST proceed to Phase A.5 if any automated failures exist (per definition above). This is mandatory — the agent MUST NOT skip failures, defer them, or proceed to Phase B while failures exist. The auto-fix loop uses internal mode switches (QA → Engineer → QA) to fix and re-run. Skip to Phase B only when zero failures across all three sources.
- If interactive (`auto_start: false`, no `--auto-verify`): present the strategy menu (Section 2.2.3) if failures or gaps exist. If zero failures and zero gaps, skip directly to Phase B.

### 2.3.2 Phase A.5 -- Auto-Fix Iteration Loop

Activates when: `--auto-verify` flag is present, OR `auto_start: true`, OR user selects "Auto-fix" from the interactive strategy menu.

**Purpose:** Automatically resolve ALL automated test failures before presenting any manual verification. The agent MUST iterate between Engineer mode (fixing code/tests) and QA mode (re-running failed tests) until all automated tests pass or the maximum iteration count is reached. The internal mode switches are mandatory — the agent MUST NOT skip them, present failures without attempting fixes, or defer to a later session.

#### Iteration Protocol (max 5 iterations)

Each iteration consists of two fix phases and a re-run:

1. **Collect failures.** Read all `regression.json` AND `tests.json` files for in-scope features. Gather `[BUG]` discoveries recorded during Phase A. Skip tests with status PASS or ESCALATED. Unit test failures (`tests.json` with `status: "FAIL"`) are included because the internal mode switch to Engineer (step 4) provides the write access needed to fix Engineer-owned test code.
2. **If zero failures remain**, exit the loop.
3. **Group failures by feature** with scenario details (expected, actual_excerpt, scenario_ref).
4. **Engineer fix phase.** Internal mode switch to Engineer (Section 2.3.3). For each feature with failures:
   - For regression failures: read regression.json details and source code referenced by scenario_ref. Read the test scenario assertions.
   - For unit test failures (`tests.json` FAIL): re-run the feature's unit test suite to capture detailed failure output, then read the failing test source code.
   - Diagnose: code bug vs stale test assertion vs spec-level issue.
   - **Code bug** → fix source code, commit with `fix(scope):` prefix.
   - **Stale test** → flag for QA fix in step 5 (record `[BUG] test-scenario:` with `Action Required: QA`). Do NOT modify QA-owned scenario JSON.
   - **Spec issue** → ESCALATE. Record `[SPEC_DISPUTE]` or `[INTENT_DRIFT]` discovery routed to PM. Do not attempt fix.
   - Update companion file with `[CLARIFICATION]` auto-fix entry.
   - Engineer scope is minimal: fix ONLY the specific failure. No refactoring, no extras.
5. **QA fix phase.** Internal mode switch to QA. Fix any test scenarios flagged as stale by Engineer (update assertion patterns, remove brittle checks). Commit scenario fixes.
6. **Re-run failed tests only.** Run harness on scenario files that had at least one failure. For features with unit test failures, re-run the unit test suite via `purlin:unit-test`. Do NOT re-run scenario files or test suites that were all-PASS. Update the failure tracker.
7. **Check escalation conditions.** For each re-run result:
   - New PASS → mark test as resolved.
   - Same failure (identical signature: `hash(expected + actual_excerpt[:200])`) → if this is the second identical failure, ESCALATE that test. Do not attempt a third fix on the same failure.
   - Different failure → reset signature, continue iterating.
8. **Print iteration summary:** fixed count, remaining failures, escalated tests.

#### Exit Conditions

| Condition | Trigger | Action |
|-----------|---------|--------|
| All pass | Zero failures remain after re-run | Exit loop, proceed to Step 5a(C) checkpoint |
| Max iterations | 5 iterations completed | Exit loop, report remaining failures |
| Same failure twice | Identical failure signature after fix attempt | Escalate that specific test, continue fixing others |
| Spec change needed | Engineer diagnoses intent mismatch | Escalate to PM, continue fixing others |
| No progress | Zero tests fixed in an iteration | Early exit to conserve context |

#### Post-Loop

After the loop exits (success, max iterations, or all escalated):
- Print an auto-fix summary: iterations used, tests fixed, tests escalated with reasons, tests remaining.
- Execute Step 5a Checkpoint (C) to finalize any newly-passing features.
- Proceed to Phase B for manual items, or skip Phase B if zero manual items remain.

### 2.3.3 Internal Mode Switch Protocol (Auto-Fix Only)

Phase A.5 requires crossing the QA/Engineer write boundary within a single verification session. The agent MUST use the `purlin_mode` MCP tool (or `set_mode()` in config_engine) to toggle between QA and Engineer modes. These mode switches are mandatory — the agent cannot fix code without switching to Engineer, and cannot re-run tests without switching back to QA. This is a lightweight "internal mode switch" that preserves safety while avoiding the full ceremony of `purlin:mode`.

**Invariants:**
- Write-boundary enforcement (mode guard) remains active. Engineer cannot write QA files; QA cannot write code files.
- Terminal identity stays in QA format (`QA(<branch>) | <label>`) throughout. The user is in a QA verification session; rapid mode flips should be invisible.
- Pending work is committed before each switch.

**QA → Engineer:**
1. Commit any pending QA artifacts (regression JSON, scenario tags).
2. Activate Engineer write permissions.
3. Log internally: "Auto-fix: Engineer mode (iteration N)."

**Engineer → QA:**
1. Run companion file gate: verify `[CLARIFICATION]` entries exist for all fixes made.
2. Commit any pending Engineer changes with `fix(scope):` prefix.
3. Activate QA write permissions.
4. Log internally: "Auto-fix: QA mode (iteration N)."

This protocol is defined within `purlin:verify` only. It does NOT modify `purlin:mode` behavior.

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
    When the agent invokes purlin:verify
    Then the command responds with a redirect message

#### Scenario: Scoped mode targets single feature

    Given feature_a is in TESTING state
    When purlin:verify is invoked with argument "feature_a"
    Then only feature_a scenarios are verified

#### Scenario: Batch mode includes all TESTING features

    Given feature_a and feature_b are both in TESTING state
    When purlin:verify is invoked without arguments
    Then both features are included in the verification pass

#### Scenario: Auto mode runs only automated scenarios

    Given features are in TESTING state with @auto scenarios
    When purlin:verify is invoked with --mode auto
    Then Phase A Steps 2-5 execute (@auto scenarios, visual smoke)
    And Phase B manual checklist is skipped entirely

#### Scenario: Smoke mode runs only smoke-tier scenarios

    Given smoke-tier scenarios exist for a feature
    When purlin:verify is invoked with --mode smoke
    Then only smoke-tier scenarios execute
    And all other steps and Phase B are skipped

#### Scenario: Regression mode runs only regression suites

    Given regression suites exist for TESTING features
    When purlin:verify is invoked with --mode regression
    Then only regression suites execute and are evaluated
    And Phase A steps 1-5 and Phase B are skipped

#### Scenario: Manual mode skips Phase A entirely

    Given features have both @auto and @manual scenarios
    When purlin:verify is invoked with --mode manual
    Then Phase A is skipped
    And Phase B manual checklist is assembled and presented

#### Scenario: Execution mode combines with feature scope

    Given feature_a has smoke-tier and standard scenarios
    When purlin:verify is invoked with "feature_a --mode smoke"
    Then only smoke-tier scenarios for feature_a execute

#### Scenario: Cosmetic scope skips feature entirely

    Given feature_a has cosmetic verification scope
    When purlin:verify processes feature_a
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

#### Scenario: Regression readiness check authors missing JSON before tests run

    Given feature_a has @auto scenarios but no regression JSON file
    And purlin:verify is invoked with --auto-verify
    When Step 0c runs
    Then the agent switches to Engineer mode internally
    And authors regression JSON for feature_a
    And switches back to QA mode
    And the smoke gate (Step 2) runs with the newly-authored JSON available

#### Scenario: Auto-fix loop resolves a code bug

    Given feature_a has a failing @auto scenario due to a code bug
    And purlin:verify is invoked with --auto-verify
    When Phase A.5 begins
    Then the agent switches to Engineer mode
    And diagnoses the failure from regression.json details
    And fixes the source code
    And commits with a fix() prefix
    And switches back to QA mode
    And re-runs only the failed scenario
    And the scenario now passes

#### Scenario: Auto-fix loop resolves a unit test failure

    Given feature_a has tests.json with status FAIL
    And purlin:verify is invoked with --auto-verify
    When Phase A.5 collects failures
    Then the tests.json FAIL status is included in the failure set
    When the Engineer fix phase runs
    Then the agent re-runs the unit tests to capture failure details
    And diagnoses and fixes the failing test or source code
    And commits with a fix() prefix
    When the re-run phase executes
    Then the unit tests are re-run via purlin:unit-test
    And tests.json now shows PASS

#### Scenario: Auto-fix loop handles stale test assertion

    Given feature_a has a failing @auto scenario due to a stale test assertion
    And purlin:verify is invoked with --auto-verify
    When Phase A.5 iteration 1 runs the Engineer fix phase
    Then the agent flags the test as stale with Action Required: QA
    When the QA fix phase runs
    Then the agent updates the scenario JSON assertion
    And re-runs the test
    And the scenario now passes

#### Scenario: Auto-fix escalates after same failure twice

    Given feature_a has a failing scenario
    And the agent fixes code in iteration 1 but the same failure recurs
    When iteration 2 produces an identical failure signature
    Then the test is marked ESCALATED
    And the agent stops attempting to fix that specific test
    And continues fixing other failing tests

#### Scenario: Auto-fix exits after max iterations

    Given 3 features have failing scenarios that cannot be resolved
    When the agent reaches iteration 5
    Then the loop exits
    And remaining failures are reported with iteration count
    And the agent proceeds to Phase B

#### Scenario: Auto-fix exits early on no progress

    Given all remaining failures persist unchanged after an iteration
    And zero tests were fixed in that iteration
    Then the loop exits early to conserve context
    And the agent reports the no-progress condition

#### Scenario: Passed tests are not re-run

    Given feature_a has 5 scenarios with 4 passing and 1 failing
    When the auto-fix loop re-runs after fixing the failure
    Then only the 1 previously-failing scenario is re-executed
    And the 4 passing scenarios are not re-run

#### Scenario: Scoped mode uses scan for lifecycle resolution

    Given feature_a has a [Ready for Verification] status commit on the current branch
    And the feature file has no inline lifecycle tag
    When purlin:verify is invoked with argument "feature_a"
    Then scan.sh --only features is executed
    And feature_a's lifecycle is resolved as TESTING from the git status commit
    And Phase A proceeds normally

#### Scenario: Scoped mode detects cross-branch status mismatch

    Given feature_a has a [Ready for Verification] status commit on branch "feature/a"
    And the current branch is "main" which lacks that commit
    When purlin:verify is invoked with argument "feature_a"
    Then a branch mismatch diagnostic is printed naming branch "feature/a"
    And verification does NOT proceed to Phase A

#### Scenario: Batch mode diagnoses empty TESTING set with cross-branch hints

    Given no features are in TESTING state on the current branch
    And feature_a has a [Ready for Verification] status commit on branch "feature/a"
    When purlin:verify is invoked without arguments
    Then the diagnostic reports status commits found on branch "feature/a"
    And suggests merging or switching branches
    And verification does NOT proceed to Phase A

#### Scenario: Auto-verify exits cleanly on branch mismatch

    Given feature_a has a [Ready for Verification] status commit on branch "feature/a"
    And the current branch is "main" which lacks that commit
    When purlin:verify is invoked with argument "feature_a" and --auto-verify
    Then the branch mismatch diagnostic is printed
    And verification exits to Session Conclusion without entering Phase A
    And no user prompt is displayed

#### Scenario: Auto-start batch exits cleanly with zero TESTING features

    Given auto_start is true
    And no features are in TESTING state on the current branch
    When purlin:verify is invoked without arguments
    Then the diagnostic is logged
    And the session exits to Session Conclusion without blocking

#### Scenario: Interactive strategy menu presented when failures exist

    Given Phase A completed with 3 test failures
    And auto_start is false and --auto-verify is not set
    When the Phase A Summary displays
    Then the strategy menu is presented with options
    And the user can choose "Auto-fix" to enter Phase A.5
    Or "Skip to manual" to proceed to Phase B

#### Scenario: Strategy menu skipped when no failures

    Given Phase A completed with zero failures and zero gaps
    And auto_start is false
    When the Phase A Summary displays
    Then the strategy menu is NOT presented
    And the agent proceeds directly to Phase B

### QA Scenarios

None.
