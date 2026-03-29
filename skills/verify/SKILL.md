---
name: verify
description: This skill activates QA mode. If another mode is active, confirm switch first
---

**Purlin mode: QA**

> **Hard gates (lifecycle diagnostic, regression readiness, auto-start silence, scoped verification modes, etc.) are defined in the agent definition §14. They apply regardless of whether this skill was invoked.** This skill provides orchestration: Phase A/B execution, auto-fix iteration loop, checklist assembly, and strategy dispatch.

---

> **Phased delivery:** See `${CLAUDE_PLUGIN_ROOT}/references/phased_delivery.md`.
> **Test infrastructure:** See `${CLAUDE_PLUGIN_ROOT}/references/test_infrastructure.md` for result schemas, harness types, status interpretation, and smoke tier rules.
> **Testing lifecycle:** See `${CLAUDE_PLUGIN_ROOT}/references/testing_lifecycle.md` for the complete lifecycle across all modes (define, implement, verify, complete).

## Session Identity

You MUST update the terminal identity before starting verification work. Derive a short task label (3-4 words max) from the feature being verified or the batch scope. Do NOT leave the label as the project name — always derive a work-specific label.

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "QA" "<task label>"
```

Examples: `QA(main) | verify auth flow`, `QA(dev/0.8.6) | batch verify`.

---

## Argument Parsing

Parse `$ARGUMENTS` for three orthogonal filters:

- **Feature scope:** A bare word (no `--` prefix) scopes to the feature file matching `<arg>` (resolve via `features/**/<arg>.md`). If absent, batch all TESTING features + AUTO re-verification candidates.
- **Execution mode:** `--mode <auto|smoke|regression|manual>`. If absent, run the full pipeline.
- **Auto-fix:** `--auto-verify`. Enables the Phase A.5 auto-fix iteration loop. Implies full pipeline (Phase A + Phase A.5 + Phase B). Mutually exclusive with `--mode`. Also activated when `auto_start: true` in session config.

Examples: `purlin:verify` (full batch), `purlin:verify notifications` (full, one feature), `purlin:verify --mode smoke` (smoke batch), `purlin:verify notifications --mode auto` (auto, one feature), `purlin:verify --auto-verify` (full batch with auto-fix loop).

## Execution Mode Dispatch

| Mode | Runs | Skips |
|------|------|-------|
| (none/full) | Phase A + Phase B | Nothing |
| `auto` | Phase A Steps 2-5 (@auto scenarios, visual smoke) | Step 1 auto-pass, Step 4 classification, Phase B |
| `smoke` | Phase A Step 2 only (smoke-tier scenarios) | Everything else |
| `regression` | Phase A Step 0b + regression checkpoint (Step 5a-B) | All other steps, Phase B |
| `manual` | Phase B only (assemble + present manual checklist) | Entire Phase A |

Execution modes do NOT change what gets committed — a mode that skips steps simply doesn't execute them. Features that would have been finalized in a skipped step remain in their current state.

---

## Scope

Run the MCP `purlin_scan` tool (with `only: "features"`) and read the JSON result.

If a feature argument was provided, extract that feature's entry from the scan results.
  - If the feature is not found in scan output, error: `"Feature <arg> not found in features/."`
  - Use the scan entry's `lifecycle`, `test_status`, `regression_status`, and other fields as the authoritative source for all subsequent steps.

If no feature argument was provided, batch the union of: (1) ALL features in TESTING lifecycle, and (2) features with QA scenarios that need automated re-verification (visual_verification or regression_run categories). Phase A executes @auto scenarios; Phase B presents remaining manual items.

Phase A and Phase B both respect this scope. In scoped mode, all steps target only the scoped feature.

---

## Lifecycle Diagnostic

After the scan, check for lifecycle mismatches that indicate cross-session branch divergence. This diagnostic detects when Engineer committed status tags on a different branch than the one QA is on.

**`--auto-verify` / `auto_start: true` compatibility:** This diagnostic MUST NOT block automation. When it fires in an automated mode (`--auto-verify` flag active OR `auto_start: true`), log the diagnostic message and proceed directly to Session Conclusion (exit cleanly with zero items verified). Do NOT wait for user input. Do NOT enter Phase A/B with stale data. The diagnostic output is still printed so it appears in logs — it just doesn't block.

**Scoped mode (feature argument provided):**
If the scoped feature's lifecycle from scan is TODO:
1. Run: `git log --all --oneline --grep='status(' | grep '<feature_stem>'`
2. If matches found on other branches:
   ```
   ━━━ Branch Mismatch ━━━
   <feature> is [TODO] on current branch (<current_branch>).
   Status commits found on other branches:
     <commit_hash> <branch_decoration> <message>

   Merge or switch branches before verifying.
   ━━━━━━━━━━━━━━━━━━━━━━━
   ```
   - **Interactive mode:** STOP — do not proceed with verification.
   - **`auto_start` / `--auto-verify`:** Log the above, then exit to Session Conclusion.
3. If no matches anywhere: the feature is genuinely TODO. Print:
   `"<feature> is in TODO lifecycle — not yet marked for verification."`
   Same stop/exit behavior per mode.

**Batch mode (no feature argument):**
If zero TESTING features found in scan:
1. Run: `git log --all --oneline --grep='Ready for Verification' | head -10`
2. Filter to commits not reachable from HEAD.
3. If matches found:
   ```
   ━━━ Nothing to Verify ━━━
   No TESTING features on current branch (<current_branch>).
   Status commits found on other branches:
     <list>
   Merge or switch branches to access these features.
   ━━━━━━━━━━━━━━━━━━━━━━━━━
   ```
4. If no matches: `"No features in TESTING lifecycle anywhere. Nothing to verify."`
5. Same stop/exit behavior per mode as scoped.

**When TESTING features ARE found:** This diagnostic is a no-op. Normal Phase A/B flow proceeds unmodified. The scan invocation is the only change — it provides data, not gates.

---

## Phase A -- Automated Execution

**Update terminal identity (MANDATORY):** Before any verification work, derive a short task label (3-4 words max) from the feature being verified or the batch scope. Call: `source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "qa" "<task label>"`. Examples: `QA(main) | verify auth flow`, `QA(dev/0.8.6) | batch verify`. The label MUST describe the current work, not the project name.

**Mode gate:** Skip this entire phase if `--mode manual`. If `--mode smoke`, execute only Step 2. If `--mode regression`, execute only Step 0b + regression checkpoint (Step 5a-B). If `--mode auto`, execute Steps 2-5 (skip Step 1 auto-pass and Step 4 classification). If no mode flag (full), execute all steps.

Execute the applicable steps IN ORDER before assembling the manual checklist. This phase applies in both batch mode (all TESTING features) and scoped mode (single feature). In scoped mode, all steps target only the scoped feature.

> **Auto-start behavior:** When `auto_start` is `true` for the QA role,
> execute ALL Phase A steps without user prompts. Do not present
> approval gates or "shall I proceed?" questions — just execute.
> Steps 1-3 and 5 run silently and report results in the Phase A
> Summary. Step 4 auto-classifies without per-scenario proposals:
> automation-feasible scenarios become `@auto` (author regression JSON
> + run immediately), infeasible become `@manual`.

### Step 0 -- Scoped Verification Modes

Before any execution, check each in-scope feature's regression scope by reading the feature spec directly (`features/<feature_name>.md`):

*   **`full`** (or missing/default) -- Verify all scenarios and all visual checklist items.
*   **`targeted:Scenario A,Scenario B`** -- Verify ONLY the named scenarios. Skip all other scenarios and visual items unless explicitly named.
*   **`cosmetic`** -- Skip the feature entirely. Output: "Feature X: QA skip (cosmetic change). No scenarios queued."
*   **`dependency-only`** -- Verify only scenarios explicitly listed in the feature spec's scope metadata. If none are listed, skip: "Feature X: QA skip (dependency-only, no scenarios in scope)."

If a cross-validation concern is detected (e.g., `cosmetic` scope but modified files touch scenarios), present the warning and ask whether to proceed with declared scope or escalate to `full`.

### Step 0c -- Regression Readiness Check

Before any tests run, ensure all in-scope @auto scenarios have regression JSON. This prevents the smoke gate (Step 2) from running with incomplete coverage and ensures the auto-fix loop (Phase A.5) has tests to iterate on.

1.  Scan all in-scope features for @auto scenarios that lack `tests/qa/scenarios/<feature>.json`.
2.  Check smoke-tier features for missing `_smoke.json` files.
3.  **If `--auto-verify` or `auto_start: true`:**
    *   Use an internal mode switch to Engineer (see Phase A.5 Internal Mode Switch Protocol).
    *   Author ALL missing regression JSON and smoke JSON upfront using `purlin:regression` logic.
    *   Commit authored files: `engineer(<scope>): author regression scenarios`
    *   Switch back to QA.
    *   Output: `"Readiness: authored N regression files, M smoke files."`
4.  **If interactive (`auto_start: false`, no `--auto-verify`):**
    *   Count gaps. Do NOT author them now — surface them in the strategy menu (Phase A Summary).
    *   Output: `"Readiness: N features need regression JSON (surfaced in strategy menu)."`
5.  If all in-scope features already have regression JSON, this step is a no-op.

### Step 0b -- Early regression launch (background)

Before any other Phase A work, scan for slow regression suites that can run in background while Steps 1-5 execute:

1. Scan `tests/qa/scenarios/*.json` for scenario files with `harness_type: "agent_behavior"` and 2+ scenarios (estimated >30s).
2. Check their `tests/<feature>/regression.json` status. Only launch suites that are STALE, FAIL, or NOT_RUN.
3. **Skip smoke-tier suites** — these run synchronously in Step 2 (smoke gate must block).
4. Launch eligible suites via `run_in_background`. QA is notified on completion.
5. Track which suites were launched (to avoid re-running in the regression step later).

This step is silent — no output, no user prompt. The goal is to overlap slow test execution with Phase A classification/visual work so results are ready by the regression checkpoint.

Under `auto_start: false`, still launch background suites — they're non-destructive and save time regardless.

### Step 1 -- Auto-pass builder-verified features

Credit features where Engineer status is DONE and zero QA scenarios exist. These require no QA action.

**AUTO features are NOT auto-passed.** Features with `qa_status: AUTO` have automated QA work (web tests, @auto scenarios) that MUST execute in Steps 2–5. Do NOT credit, skip, or auto-complete them here — they require test execution even though they need zero human time. **Regression guidance exclusion:** Features where scan results show `qa_reason` = `"regression harness authoring pending"` MUST be excluded from auto-pass. Do NOT mark them `[Complete]`, do NOT commit status tags for them, do NOT edit their lifecycle tags. Acknowledge them silently in the Phase A summary and route them to Step 3 for regression authoring.

*   When `find_work` is `true`: execute acknowledgments silently.
*   When `find_work` is `false`: present the list and wait for user confirmation.
*   Output per feature: `"Auto-pass: <feature> (builder-verified, zero QA scenarios)."`

### Step 2 -- Smoke gate

**Always runs.** Read the `## Test Priority Tiers` table from `PURLIN_OVERRIDES.md` or `QA_OVERRIDES.md` (check both; purlin agent uses the former, legacy agents the latter). Also detect smoke regression suites: any `tests/qa/scenarios/<feature>_smoke.json` file with `"tier": "smoke"`.

1.  Identify smoke-tier features. A feature is smoke-tier if:
    *   It appears in the tier table with `smoke`, OR
    *   A `<feature>_smoke.json` regression file exists with `"tier": "smoke"`
2.  **Run smoke regressions FIRST.** For each smoke-tier feature with a `_smoke.json` file, run the smoke regression via the harness runner. These are designed to be fast (< 30s).
3.  **Then run smoke QA scenarios.** For each smoke-tier feature in scope with QA work:
    *   `@auto` scenarios: invoke the harness runner.
    *   `@manual` and untagged scenarios: present to the user.
4.  **Halt-on-fail:** If ANY smoke test fails (regression or scenario):
    ```
    ━━━ SMOKE FAILURE ━━━
    <feature> — <test name>
    Smoke tests verify critical functionality. This failure blocks all further verification.
    Fix before continuing? [yes to stop / no to continue anyway]
    ━━━━━━━━━━━━━━━━━━━━━
    ```
    *   "yes": Abort the batch. Record the failure as a `[BUG]` discovery. Route to Engineer mode.
    *   "no": Continue to Step 3. The failure is still recorded as a discovery.
5.  **Suggest smoke promotion.** After running smoke, if any non-smoke feature in scope is a prerequisite for 3+ other features and has no smoke classification, suggest: "Consider promoting `<feature>` to smoke tier with `purlin:smoke <feature>`." Do this once per session, not per feature.

### Step 3 -- Run @auto scenarios

For each `@auto`-tagged QA scenario (classified in a prior session) that was NOT already run in Step 2 (smoke gate):

1.  **Check for regression JSON:** Look for `tests/qa/scenarios/<feature_name>.json`.
    *   If found: proceed to invocation.
    *   If missing: invoke `purlin:regression` to create the regression JSON for this feature. Then proceed to invocation.

2.  **Start servers if needed:** If the scenario requires a running server (e.g., feature has `> Web Test:` metadata or regression JSON has `setup_commands`):
    *   Check target port is not in use.
    *   Start the server process.
    *   Track the PID for cleanup.

3.  **Invoke harness runner:**
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/test_support/harness_runner.py tests/qa/scenarios/<feature_name>.json
    ```
    The harness runner handles: fixture checkout (if `fixture_tag` specified), execution based on `harness_type` (agent_behavior, web_test, custom_script), assertion evaluation, fixture cleanup, and writing enriched `tests/<feature_name>/regression.json`.

4.  **Process results:**
    *   Exit 0 (all passed): record pass. Feature's @auto scenarios are complete.
    *   Non-zero (failures): record each failed assertion as a `[BUG]` discovery in `features/<feature_name>.discoveries.md`. Failed @auto scenarios do NOT enter the Phase B manual checklist -- they are already recorded as discoveries. These failures feed into Phase A.5 (auto-fix loop) when `--auto-verify` is active, rather than being deferred to a future session.

5.  **Cleanup:** Stop any servers started in substep 2.

6.  **Report after all @auto scenarios complete:**
    ```
    @auto results: N scenarios executed across M features.
    Passed: X | Failed: Y
    [List any failures with feature + scenario name]
    ```

### Step 4 -- Classify untagged scenarios

For each QA scenario in scope with NO tag (neither `@auto` nor `@manual`) that was NOT already handled in Step 2 (smoke gate):

1.  **Evaluate automation feasibility for ALL untagged scenarios first** (do NOT prompt one at a time). Criteria: deterministic assertions (no subjective judgment), no physical hardware required, no interactive multi-step human workflow.

2.  **Batch-classify obvious cases silently.** If QA determines a scenario is clearly not automatable (requires human judgment, requires physical hardware, requires interactive multi-step human workflow), tag it `@manual` immediately without asking the user. Do NOT prompt for confirmation on obvious classifications. Note: `agent_behavior` tests ARE automatable — they run in-session via background execution.

3.  **Present a single summary** of all classifications made and any that need user input:

    ```
    Classified 4 scenarios:

    Tagged @manual (not automatable in-session):
      purlin_migration: "Complete transition removes old artifacts" — agent_behavior
      purlin_migration: "End-to-end migration preserves completeness" — agent_behavior
      purlin_smoke_testing: "Smoke regression targets fast execution" — agent_behavior
      purlin_smoke_testing: "End-to-end smoke promotion" — agent_behavior

    Need your input:
      (none this batch)
    ```

4.  **Only prompt the user for genuinely ambiguous cases** — scenarios where QA is unsure whether automation is feasible. Present these as a batch, not one at a time:

    ```
    These could go either way — automate or manual?
      feature_x: "Scenario A" — could be custom_script but setup is complex
      feature_y: "Scenario B" — deterministic but needs server running

    Tag all as @manual? Or specify which to automate: "A=auto, B=manual"
    ```

5.  **Commit all tag changes in one batch commit** with `[QA-Tags]` exemption tag.

6.  **Invariant:** After this step, every scenario is tagged `@auto` or `@manual`. No scenario silently remains untagged.

### Step 5 -- Visual smoke

For features in scope that have visual specification sections:

*   **Web Test features** (have `> Web Test:` metadata): invoke `purlin:web-test` to take a Playwright screenshot and check the Visual Specification checklist against the running app. Record pass/fail per visual item.
*   **Non-web features:** Request a screenshot from the human: `"Please provide a screenshot of <screen name> for visual smoke check."` Read the screenshot and evaluate visual checklist items that are screenshot-verifiable.

This is a smoke check -- it clears visual items that can be verified now, reducing the Phase B manual list. Items that cannot be verified from a screenshot remain in the Phase B checklist.

**Feature completion via Step 5a:** For features (both AUTO and TODO) where all automated work passed (unit tests, regression, @auto scenarios) AND zero @manual scenarios remain, this step completes their verification — they are eligible for finalization at the next Step 5a checkpoint. No Phase B items are generated for these features. Features with passing automated work but pending @manual scenarios get their artifacts committed but proceed to Phase B for manual verification before finalization.

### Step 5a -- Phase A Checkpoint (MANDATORY HARD GATE)

This checkpoint fires at **three** points during Phase A:

**Checkpoint (A) — after Steps 1–5:** Finalize features verified by web tests, @auto scenarios, and visual smoke. This fires immediately after Step 5 completes.

**Checkpoint (B) — after all regression suites complete:** Finalize features whose regression suites passed (all harness types, including `agent_behavior`). This fires after evaluation of all suite results.

**Checkpoint (C) — after Phase A.5 auto-fix loop completes:** Finalize features whose tests were fixed and now pass after the auto-fix iteration loop. This fires only when Phase A.5 was activated.

At each checkpoint, execute this sequence IN ORDER for all newly-clean features (both AUTO and TODO):

> **CRITICAL: Committing regression artifacts is NOT finalization.** The lifecycle tracks status via commit messages containing `[Complete]`. Committing regression JSON files, scenario tags, or test results does NOT change lifecycle status. You MUST commit the explicit `[Complete] [Verified]` status tag commits (step 2 below) or the features remain in TODO/AUTO state.

1.  **Commit regression artifacts:** Commit all regression JSON files and scenario tag changes produced since the last checkpoint.
2.  **Commit status tags:** For each feature where all automated work passed (unit tests in `tests.json`, regression suites, @auto scenarios) AND zero @manual scenarios remain unverified, commit ONE `--allow-empty` commit per feature: `git commit --allow-empty -m "status(<scope>): [Complete features/<FILENAME>.md] [Verified]"`. These are QA completions, so `[Verified]` is required. ONE COMMIT PER FEATURE — do not batch multiple features into a single status commit. Features with passing automated work but pending @manual scenarios are NOT finalized here — they proceed to Phase B.
3.  **Update scan (HARD GATE):** Run the MCP `purlin_scan` tool once to refresh project state. Do NOT proceed to Phase B until this completes.
4.  **Verify finalization:** Check scan results — finalized features MUST no longer show AUTO/TODO in their QA column. If they do, a status tag commit was missed. Fix before continuing.
5.  **Verify clean workspace:** Confirm no uncommitted changes remain.
6.  **Zero manual items check:** If zero manual items remain AND no external tests are pending, skip Phase B entirely and proceed to Session Conclusion.

### Phase A Summary

After all steps complete, print a bridging summary before proceeding to Phase B:

```
━━━ Phase A Complete ━━━
Auto-passed:     N features (builder-verified)
Smoke gate:      [ran M smoke scenarios / skipped (no tier table)]
@auto executed:  X scenarios — Y passed, Z failed
Classified:      A scenarios (B → @auto, C → @manual, D skipped)
Visual smoke:    E items checked
Regression:      R authored this session, S pre-existing
Unit tests:      P features PASS, Q features FAIL

Remaining for manual verification: F items across G features.
Proceeding to Phase B.
━━━━━━━━━━━━━━━━━━━━━━━
```

**Regression suite status table** (print after the summary block):

1. Scan `tests/qa/scenarios/*.json` for all existing scenario files.
2. For each, check the corresponding `tests/<feature>/regression.json`:
   - `status: "PASS"` and source NOT modified since mtime → **PASS**
   - `status: "PASS"` but source modified since mtime → **STALE**
   - `status: "FAIL"` → **FAIL**
   - Missing or `total: 0` → **NOT_RUN**
   PASS results are valid — do NOT flag as "prior run; re-run needed" or request fresh execution. Only STALE, FAIL, and NOT_RUN require action.
3. Read `QA_OVERRIDES.md` `## Test Priority Tiers` table (if it exists) to determine each feature's test priority tier (smoke, standard, full-only).
4. Read each scenario file's `frequency` field (`per-feature` default, or `pre-release`).
5. **Harness type detection:** Read each scenario file's `harness_type`. Note `agent_behavior` suites (these invoke `claude --print` as a non-interactive subprocess and may take longer).
6. Group suites by frequency (`per-feature` vs `pre-release`). Within each group, sort by tier (smoke first, then standard, then full-only). Mark smoke-tier features with a `[smoke]` indicator. Annotate `agent_behavior` suites so the user knows which are slow.
7. Print the table:

```
Regression suites:
  per-feature:
    [STALE]   config_layering (3/3, source modified) [smoke]
    [PASS]    instruction_audit (5/5, 2h ago)
    [NOT_RUN] terminal_identity
    [NOT_RUN] release_record_version_notes (agent_behavior, 3 scenarios)

  pre-release:
    [NOT_RUN] skill_behavior_regression (agent_behavior, 9 scenarios)
```

8. **`auto_start` gate (BEFORE prompting — do NOT print a prompt or wait for input when `auto_start: true`).**
   - **When `auto_start: true`:** Print `"auto_start: running N per-feature suites (smoke first). Skipped M pre-release suites (run manually before release)."` Proceed directly to step 9 with all STALE and NOT_RUN per-feature suites selected. Do NOT print a prompt. Do NOT wait for user input.
   - **When `auto_start: false`:** Print `"Run regression suites? [all / per-feature / skip]"` and wait for user selection. If the user says "skip": skip regression execution, proceed to Phase B, and record skipped suites in the QA report. Also prompt for pre-release suites: `"Run pre-release regression suites? [yes / skip]"`.

9. **Execute selected suites in-session.** Skip suites already launched in Step 0b (background). All harness types — including `agent_behavior` — run directly. The `claude --print` invocations within `agent_behavior` suites are stateless, non-interactive subprocesses that do not conflict with the active session.
   - **Fast suites** (`web_test`, `custom_script`, single-scenario `agent_behavior`): run synchronously for immediate feedback.
   - **Already-launched suites** (from Step 0b): check if background results have arrived. If yes, evaluate immediately. If not, note "waiting for N background suites" and proceed — they'll be evaluated at the regression checkpoint.

10. **Auto-evaluate on completion.** When each suite finishes (foreground or background notification), immediately read `regression.json` and evaluate:
   - PASS: record pass, no action needed.
   - FAIL: create `[BUG]` discovery in companion file with `scenario_ref`, `expected`, and `actual_excerpt`.
   - Report a summary after all suites complete.

11. **Step 5a(B) — Regression checkpoint:** After all regression suites complete and are evaluated, execute Step 5a checkpoint (B). Finalize features whose regression suites passed — commit `[Complete] [Verified]` status tags, commit regression artifacts, run the MCP `purlin_scan` tool. Then proceed to Phase B.

If no scenario files exist in `tests/qa/scenarios/`, skip the regression suite status table entirely.

**Regression gap table** (print only if features have regression guidance but
no harness JSON and the gap was NOT resolved during Step 0c or Phase A):

```
Regression gaps: T features without harness JSON
| Feature | Harness Type | Blocker |
|---------|-------------|---------|
| <name>  | <type>      | <why>   |
```

### Strategy Dispatch

After the Phase A Summary, regression table, and gap table, dispatch based on flags.

**"Automated failures" definition:** The union of (1) regression suite failures (`regression.json` with `status: "FAIL"` or `"STALE"`), (2) @auto scenario failures from Phase A Step 3, AND (3) unit test failures (`tests.json` with `status: "FAIL"` for any in-scope feature). All three sources MUST be checked — if any single source has failures, the dispatch enters Phase A.5.

**When `--auto-verify` or `auto_start: true`:**
*   If any automated failures exist (per definition above): proceed to Phase A.5 auto-fix loop.
*   If zero failures across all three sources and zero gaps: skip to Phase B (or skip Phase B if zero manual items).

**When interactive (`auto_start: false`, no `--auto-verify`):**
*   If Phase A had zero failures (across all three sources) AND zero gaps: skip to Phase B directly (or skip Phase B if zero manual items).
*   If failures or gaps exist, present the strategy menu:

```
━━━ Verification Strategy ━━━
N features in scope | M @auto passed | K failed | G gaps

  [1] Auto-fix    — build missing regressions, fix failures, iterate until green (up to 5 rounds), then manual
  [2] Automated   — current results stand, proceed to manual checklist
  [3] Smoke only  — re-run smoke tier tests only
  [4] Manual only — skip to Phase B manual checklist
  [5] Exit        — save checkpoint, return later

Choose [1-5]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

| Choice | Behavior |
|--------|----------|
| 1 | Enter Phase A.5 auto-fix loop (same as `--auto-verify`) |
| 2 | Accept current Phase A results, proceed to Phase B |
| 3 | Re-run Step 2 smoke gate only, then return to this menu |
| 4 | Skip directly to Phase B |
| 5 | Run `purlin:resume save` and end session |

---

## Phase A.5 -- Auto-Fix Iteration Loop

**Activation:** `--auto-verify` flag, `auto_start: true`, or user selected [1] from strategy menu.

**Purpose:** Automatically resolve all automated test failures before presenting any manual verification. The agent iterates between Engineer mode (fixing code/tests) and QA mode (re-running failed tests) until all automated tests pass or the maximum iteration count is reached.

### Internal Mode Switch Protocol

Phase A.5 crosses the QA/Engineer write boundary. This uses a lightweight internal protocol that preserves safety while avoiding the full `purlin:mode` ceremony:

**Invariants:**
*   Write-boundary enforcement (mode guard) remains active. Engineer cannot write QA files; QA cannot write code files.
*   Terminal badge stays in QA format (`QA(<branch>) | <label>`) throughout. The user is in a QA verification session; rapid mode flips are invisible.
*   Pending work is committed before each switch.

**QA → Engineer:**
1.  Commit any pending QA artifacts (regression JSON, scenario tags).
2.  Activate Engineer write permissions.
3.  Log internally: `"Auto-fix: Engineer mode (iteration N)."`

**Engineer → QA:**
1.  Run companion file gate: verify `[CLARIFICATION]` entries exist for all fixes made.
2.  Commit any pending Engineer changes with `fix(scope):` prefix.
3.  Activate QA write permissions.
4.  Log internally: `"Auto-fix: QA mode (iteration N)."`

### Failure Tracker

Maintain a session-local tracker (in conversation context, not a file) for each failing test:

*   **Status:** PASS / FAIL / ESCALATED
*   **Failure signature:** `hash(expected + actual_excerpt[:200])` — used to detect repeated identical failures
*   **Attempt count:** number of fix attempts for this specific test
*   **Escalation reason:** null, `same_failure`, `spec_change_needed`, `external_dependency`, `max_attempts`

### Per-Iteration Protocol

```
━━━ Auto-Fix Iteration N of 5 ━━━
```

1.  **Collect failures.** Read all `regression.json` AND `tests.json` for in-scope features. Gather `[BUG]` discoveries from Phase A. Skip tests with status PASS or ESCALATED in the tracker. Skip scenario files where ALL scenarios passed (do not re-run passed tests). Unit test failures (`tests.json` with `status: "FAIL"`) are included because the internal mode switch to Engineer (step 4) provides write access to fix Engineer-owned test code.

2.  **If zero failures remain:** exit the loop (success).

3.  **Group failures by feature.** Print:
    ```
    Failures to fix:
      feature_a: 2 scenarios (scenario_x assertion Y, scenario_z assertion W)
      feature_b: 1 scenario (scenario_m assertion N)
    ```

4.  **Engineer fix phase.** Internal switch to Engineer.
    For each feature with failures:
    a.  For regression failures: read `regression.json` details (`expected`, `actual_excerpt`, `scenario_ref`). Read the source code referenced by `scenario_ref`. Read the test scenario assertions from `tests/qa/scenarios/<feature>.json`.
    b.  For unit test failures (`tests.json` FAIL): re-run the feature's unit test suite to capture detailed failure output, then read the failing test source code and application code under test.
    c.  **Diagnose:**
        *   **Code bug** (actual behavior diverges from spec intent): fix the source code. Commit: `fix(<scope>): resolve regression failure in <scenario_name>`.
        *   **Stale test** (assertion pattern is wrong/brittle): do NOT modify QA-owned scenario JSON. Flag for QA fix by recording `[BUG] test-scenario: <assertion context>` with `Action Required: QA` in the discovery sidecar.
        *   **Spec issue** (intent mismatch between spec and scenario): ESCALATE. Record `[SPEC_DISPUTE]` or `[INTENT_DRIFT]` discovery routed to PM. Mark test as ESCALATED in tracker.
        *   **External dependency** (fix requires system outside project): ESCALATE with reason `external_dependency`.
    d.  Update companion file with `[CLARIFICATION]` auto-fix entry: `"Auto-fix iteration N: fixed <what> to resolve <failure description>."`
    e.  **Scope is minimal:** Fix ONLY the specific failure. No refactoring, no feature additions, no extras.

5.  **QA fix phase.** Internal switch to QA.
    *   Fix any test scenarios flagged as stale by Engineer in step 4c: update assertion patterns, remove brittle Tier-1 checks, adjust expected output. Commit: `qa(<scope>): fix stale regression assertion`.
    *   If no stale tests were flagged, this phase is a no-op.

6.  **Re-run failed tests only.** For each scenario file that had at least one failure (and was not escalated):
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/test_support/harness_runner.py tests/qa/scenarios/<feature>.json
    ```
    For features with unit test failures, re-run the unit test suite via `purlin:unit-test` and read the updated `tests.json`.
    Read the updated `regression.json`. Update the failure tracker:
    *   New PASS → mark as resolved.
    *   Same failure (signature matches previous iteration) → increment attempt count. If this is the 2nd identical failure, mark ESCALATED with reason `same_failure`.
    *   Different failure → reset signature, continue iterating.

7.  **Print iteration summary:**
    ```
    ━━━ Iteration N Summary ━━━
    Fixed:     F tests now passing
    Remaining: R tests still failing
    Escalated: E tests
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ```

8.  **Check exit conditions:**
    *   All tests pass (zero remaining) → exit loop.
    *   Iteration count reached 5 → exit loop.
    *   Zero tests fixed this iteration (no progress) → exit loop early to conserve context.
    *   All remaining tests are ESCALATED → exit loop.

### Post-Loop Summary

```
━━━ Auto-Fix Complete ━━━
Iterations:  N of 5
Fixed:       F tests (now passing)
Escalated:   E tests
  - feature_a/scenario_x: same failure after 2 attempts
  - feature_b/scenario_m: requires spec change (PM)
Remaining:   R tests (max iterations reached)
━━━━━━━━━━━━━━━━━━━━━━━━━
```

After the summary:
1.  Execute Step 5a Checkpoint (C) to finalize any newly-passing features.
2.  If zero manual items remain, skip to Step 11 (Batch Completion).
3.  Otherwise proceed to Phase B.

---

## Phase B -- Manual Verification Checklist

**Mode gate:** Skip this entire phase if `--mode auto`, `--mode smoke`, or `--mode regression`. Only execute for full (no flag) or `--mode manual`.

### Step 6 -- Checklist Assembly

Collect remaining testable items (those NOT handled in Phase A) across in-scope TESTING features into a single flat-numbered list:

1.  Apply scope rules from Step 0. Skip cosmetic features. For targeted/dependency-only, include only in-scope scenarios.
2.  Exclude `@auto`-tagged scenarios -- already executed in Phase A Steps 2-4.
3.  Exclude visual items already verified in Phase A Step 5.
4.  Auto-skip builder-verified features (zero manual scenarios, zero visual items).
5.  Assign flat sequential numbers (1, 2, ... N) across all features. Do not restart numbering per feature.
6.  Visual items from `## Visual Specification` sections are interleaved under their feature, tagged with `[V]` prefix, sharing the numbering sequence.
7.  **Web-test visual dedup:** For features with `> Web Test:` metadata, exclude visual `[V]` items from the QA checklist. These were verified by Engineer mode via `purlin:web-test` during implementation and by Phase A Step 5. Include only manual scenarios that require human interaction. If a web-test feature has zero manual scenarios remaining after this exclusion, auto-skip it: `"Feature X: visual items verified via purlin:web-test. Auto-pass."`
8.  **Tier labels:** If tier classification exists in `QA_OVERRIDES.md`, prefix each feature group with its tier: `[SMOKE]`, `[STD]`, or `[FULL]`.
9.  **Condensing rule:** For each functional scenario, produce a two-line entry: line 1 = **what to do** (setup + action, imperative voice), line 2 = **what to verify** (expected outcome). Strip Gherkin boilerplate but keep essential setup context. Visual items use `[V]` prefix with verbatim checklist text (single line).
10. Cross-validation warnings: insert an advisory line before affected feature's items.
11. Fixture awareness: if scan results indicate `fixture_repo_unavailable` for a feature, append `[fixture N/A]` to affected scenarios.
12. Large visual batches (50+ visual items for one feature): offer grouped sub-prompt by screen.

### Step 7 -- Checklist Presentation

*   **Ordering:** Sort features: smoke first, then standard, then full-only. Within each tier group, sort ascending by estimated verification time (shortest first).

Output the checklist as a numbered list grouped by feature:

```
**Verification Checklist** -- N items across M features (~X min estimated)
Tiers: S smoke, T standard, F full-only
Default: PASS. Reply "all pass", or list failures: "F3, F7"
"help N" = I'll walk you through testing it | purlin:discovery = issues outside this list

**Feature Label** [PRIORITY]
1. **Do:** <setup + action to perform>
   **Verify:** <what the tester should observe>
2. **Do:** <setup + action to perform>
   **Verify:** <what the tester should observe>
3. [V] <visual checklist item text>

**Feature Label** [PRIORITY]
4. **Do:** <setup + action to perform>
   **Verify:** <what the tester should observe>

Reply "all pass", list failures ("F3, F7"), or "help N" for testing assistance.
```

**Format rules:** Feature headers are bold with priority tag. One blank line between groups. Functional items: `N. **Do:** ...` / `   **Verify:** ...`. Visual items: `N. [V] ...`. Imperative voice. End with response prompt + help offer. If no tier classification exists in `QA_OVERRIDES.md`, omit the Tiers line from the header.

**Zero testable items:** If all items were handled in Phase A or all TESTING features are builder-verified/cosmetic-scoped, skip the checklist. Output: "All scenarios passed automated verification or are builder-verified. No manual verification needed." Proceed to Step 11.

### Step 8 -- Response Processing

Parse the user's response (case-insensitive, flexible separators):

*   **`all pass`** / **`pass`** -- All items pass. Proceed to Step 10.
*   **`F3, F7`** / **`3, 7`** / **`f3 f7`** -- Items 3 and 7 failed; everything else passes. Proceed to Step 9.
*   **`help 5`** / **`help 5, 8`** -- Walk the user through testing the item(s) step by step: setup, actions, what to look for. Use the full Gherkin scenario as source but present conversationally. For `[V]` items, explain what to inspect and where. Re-prompt for overall response.
*   **`detail 5`** / **`d5`** / **`detail 5, 8`** -- Show raw Gherkin steps (or full visual checklist with design references). Re-prompt.
*   **`DISPUTE 4`** / **`dispute 4`** -- Triggers SPEC_DISPUTE flow for item 4. Ask why they disagree. Record a `[SPEC_DISPUTE]` discovery. Scenario is suspended. Re-prompt for remaining items.
*   **Stop / partial** -- Complete passing features verified so far, leave the rest in TESTING, proceed to Step 11 with partial summary.

### Step 9 -- Failure Processing

For each failed item:

1.  **Batch observations:** Ask the user to describe failures. When multiple failures belong to the same feature, collect together: "Items 3 and 4 are both in Feature X. What did you observe for each?"
2.  **Classify** each via the discovery protocol. Types:
    *   **[BUG]** -- Behavior contradicts an existing scenario.
    *   **[DISCOVERY]** -- Behavior exists but no scenario covers it.
    *   **[INTENT_DRIFT]** -- Behavior matches spec literally but misses actual intent.
    *   **[SPEC_DISPUTE]** -- User disagrees with scenario's expected behavior.
    Confirm classification with the user.
3.  **Record** entries to discovery sidecar files (`features/<name>.discoveries.md`). Format:
    ```
    ### [TYPE] <title> (Discovered: YYYY-MM-DD)
    - **Scenario:** <which scenario, or NONE>
    - **Observed Behavior:** <what the user described>
    - **Expected Behavior:** <from the scenario, or "not specified">
    - **Action Required:** <PM or Engineer>
    - **Status:** OPEN
    ```
4.  **Commit** all discovery entries: `git commit -m "qa(scope): [TYPE] - <brief>"`.

### Step 9.5 -- Visual Verification Integration

Visual items appear as numbered `[V]` entries in the main checklist. Judged by number like functional items.

*   **Detail expansion:** When `detail` requested for a `[V]` item, present full visual context: design anchor references, Token Map entries, design asset reference.
*   **Screenshot-assisted analysis:** Offer screenshot input when: user requests `detail` for visual items, feature has many visual items (10+), or user explicitly asks. When screenshots are provided:
    1.  Read each screenshot via the Read tool.
    2.  Classify checklist items as screenshot-verifiable (static visible properties) vs. not (interactions, state persistence, temporal behaviors).
    3.  For verifiable items: PASS, FAIL, or UNCERTAIN with observation notes.
    4.  Present results in two groups: auto-verified + manual confirmation required.
*   **Figma-Triangulated Verification:** When Figma MCP is available and a visual spec screen has a Figma reference, perform three-source comparison (Figma design, spec Token Map + checklists, running app). Verdicts: PASS, BUG (app wrong -> Engineer), STALE (Figma updated -> PM), SPEC_DRIFT (app matches Figma, not spec -> PM).
*   **Web test alternative:** For features with `> Web Test:` metadata, `purlin:web-test` provides fully automated visual verification via Playwright MCP.

### Step 10 -- Exploratory Testing

After all checklist items are resolved, present:

> "Did you notice anything unexpected across all the features tested -- any behavior not covered by the checklist?"

If yes, record each as a `[DISCOVERY]` in the appropriate sidecar file. If no, proceed to Step 11.

### Step 11 -- Batch Completion

1.  **Present Phase A results:** `"Automated (Phase A): N @auto scenarios executed, M passed, K failed."`
2.  **Identify passing features:** All items (Phase A + Phase B) passed and zero discoveries recorded. Exclude features already completed in Step 5a checkpoints.
3.  **Delivery plan gating:** Check `.purlin/delivery_plan.md`. If a feature appears in any PENDING phase, do NOT mark complete: "Feature X passed but has more work coming in Phase N. Deferring [Complete]."
4.  **Mark eligible features complete:** `git commit --allow-empty -m "status(scope): [Complete features/FILENAME.md] [Verified]"`. The `[Verified]` tag is mandatory for QA completions.
5.  **Features with discoveries:** Do NOT mark complete. They remain in TESTING.
6.  **Run scan once:** Run the MCP `purlin_scan` tool after all status commits to refresh project state. Do NOT run per-feature.
7.  **Present batch summary:**
    *   Automated: N @auto executed, M passed, K failed.
    *   Manual: N passed, M failed, K disputed.
    *   Features completed (list).
    *   Features remaining in TESTING with discovery counts (list).
    *   Features deferred by delivery plan (list).
    *   Discovery routing: which items need PM vs. Engineer.
