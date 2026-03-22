**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-verify instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Scope

If an argument was provided, scope verification to `features/<arg>.md` only.
If no argument was provided, run `${TOOLS_ROOT}/cdd/status.sh --role qa` and batch ALL TESTING features into a single verification pass. Phase A executes @auto scenarios; Phase B presents remaining manual items.

Phase A and Phase B both respect this scope. In scoped mode, all steps target only the scoped feature.

---

## Phase A -- Automated Execution

Execute these steps IN ORDER before assembling the manual checklist. Do NOT skip Phase A or defer automated items to after Phase B. This phase applies in both batch mode (all TESTING features) and scoped mode (single feature). In scoped mode, all steps target only the scoped feature.

> **Canonical source:** QA_BASE Section 3.3 defines the Auto-First Protocol. This phase implements it. If they diverge, QA_BASE Section 3.3 is authoritative.

> **Auto-start behavior:** When `auto_start` is `true` for the QA role,
> execute ALL Phase A steps without user prompts. Do not present
> approval gates or "shall I proceed?" questions — just execute.
> Steps 1-3 and 5 run silently and report results in the Phase A
> Summary. Step 4 auto-classifies without per-scenario proposals:
> automation-feasible scenarios become `@auto` (author regression JSON
> + run immediately), infeasible become `@manual`.

### Step 0 -- Scoped Verification Modes

Before any execution, check each in-scope feature's regression scope from `tests/<feature_name>/critic.json`:

*   **`full`** (or missing/default) -- Verify all scenarios and all visual checklist items.
*   **`targeted:Scenario A,Scenario B`** -- Verify ONLY the named scenarios. Skip all other scenarios and visual items unless explicitly named.
*   **`cosmetic`** -- Skip the feature entirely. Output: "Feature X: QA skip (cosmetic change). No scenarios queued."
*   **`dependency-only`** -- Verify only scenarios listed in `regression_scope.scenarios`. If the list is empty, skip: "Feature X: QA skip (dependency-only, no scenarios in scope)."

If the Critic emitted a cross-validation WARNING (e.g., `cosmetic` scope but modified files touch scenarios), present the warning and ask whether to proceed with declared scope or escalate to `full`.

### Step 1 -- Auto-pass builder-verified features

Credit features where Builder status is DONE and zero QA scenarios exist (TestOnly or Skip in Critic). These require no QA action.

*   When `find_work` is `true`: execute acknowledgments silently.
*   When `find_work` is `false`: present the list and wait for user confirmation.
*   Output per feature: `"Auto-pass: <feature> (builder-verified, zero QA scenarios)."`

### Step 2 -- Smoke gate

**Conditional:** Only runs if a `## Test Priority Tiers` table exists in `QA_OVERRIDES.md`. If no table exists, skip this step.

1.  Identify smoke-tier features in scope that have QA work (TODO or AUTO status). In scoped mode: only applies if the scoped feature is classified as smoke.
2.  For each smoke-tier feature, run ALL its scenarios:
    *   `@auto` scenarios: invoke the harness runner (see Step 3 for invocation syntax).
    *   `@manual` and untagged scenarios: present to the user for manual verification.
3.  **Halt-on-fail:** If ANY smoke-tier scenario fails (automated or manual):
    ```
    Smoke failure: <feature> — <scenario>.
    Fix before continuing full verification? [yes to stop / no to continue]
    ```
    *   "yes": Abort the batch. Record the failure as a `[BUG]` discovery. Report which smoke features failed and route to Builder.
    *   "no": Continue to Step 3. The failure is still recorded as a discovery.

### Step 3 -- Run @auto scenarios

For each `@auto`-tagged QA scenario (classified in a prior session) that was NOT already run in Step 2 (smoke gate):

1.  **Check for regression JSON:** Look for `tests/qa/scenarios/<feature_name>.json`.
    *   If found: proceed to invocation.
    *   If missing: invoke `/pl-regression` (author mode) to create the regression JSON for this feature. Then proceed to invocation.

2.  **Start servers if needed:** If the scenario requires a running server (e.g., feature has `> Web Test:` metadata or regression JSON has `setup_commands`):
    *   Check target port is not in use.
    *   Start the server process.
    *   Track the PID for cleanup.

3.  **Invoke harness runner:**
    ```bash
    python3 ${TOOLS_ROOT}/test_support/harness_runner.py tests/qa/scenarios/<feature_name>.json
    ```
    The harness runner handles: fixture checkout (if `fixture_tag` specified), execution based on `harness_type` (agent_behavior, web_test, custom_script), assertion evaluation, fixture cleanup, and writing enriched `tests/<feature_name>/tests.json`.

4.  **Process results:**
    *   Exit 0 (all passed): record pass. Feature's @auto scenarios are complete.
    *   Non-zero (failures): record each failed assertion as a `[BUG]` discovery in `features/<feature_name>.discoveries.md`. Failed @auto scenarios do NOT enter the Phase B manual checklist -- they are already recorded as discoveries.

5.  **Cleanup:** Stop any servers started in substep 2.

6.  **Report after all @auto scenarios complete:**
    ```
    @auto results: N scenarios executed across M features.
    Passed: X | Failed: Y
    [List any failures with feature + scenario name]
    ```

### Step 4 -- Classify untagged scenarios

For each QA scenario in scope with NO tag (neither `@auto` nor `@manual`) that was NOT already handled in Step 2 (smoke gate):

> **Auto-start override:** When `auto_start` is `true`, skip the
> per-scenario user proposal (substeps 2-5 below). Instead: auto-classify
> each scenario — if automation-feasible, author via `/pl-regression`, run
> via harness, and tag `@auto`; if not feasible, tag `@manual`. Batch-commit
> all tag changes. Report all classifications in the Phase A Summary.

1.  **Evaluate automation feasibility:** Can the scenario be automated? Criteria: deterministic assertions (no subjective judgment), no physical hardware required, no interactive multi-step human workflow.

2.  **Propose to user:**
    ```
    Classify: "<Scenario Title>" in <feature>
    Automatable via <harness_type> — <one-line rationale>.
    Automate now? [yes / no / skip classification]
    ```

3.  **If user approves ("yes"):**
    *   Invoke `/pl-regression` (author mode) to create or append to the regression JSON.
    *   Run the new scenario via the harness runner (same process as Step 3).
    *   Add `@auto` tag to the scenario heading in the feature file.
    *   Commit the tag change and regression JSON.

4.  **If user declines ("no") or scenario is not feasible:**
    *   Add `@manual` tag to the scenario heading in the feature file.
    *   Commit the tag change.
    *   Scenario enters Phase B manual checklist.

5.  **If user says "skip classification":**
    *   Leave the scenario untagged for this session.
    *   Scenario enters Phase B manual checklist as-is.

6.  **Invariant:** After this step, every scenario has been classified (tagged @auto or @manual) OR explicitly skipped by the user. No scenario silently remains untagged.

### Step 5 -- Visual smoke

For features in scope that have visual specification sections:

*   **Web Test features** (have `> Web Test:` metadata): invoke `/pl-web-test` to take a Playwright screenshot and check the Visual Specification checklist against the running app. Record pass/fail per visual item.
*   **Non-web features:** Request a screenshot from the human: `"Please provide a screenshot of <screen name> for visual smoke check."` Read the screenshot and evaluate visual checklist items that are screenshot-verifiable.

This is a smoke check -- it clears visual items that can be verified now, reducing the Phase B manual list. Items that cannot be verified from a screenshot remain in the Phase B checklist.

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

Remaining for manual verification: F items across G features.
Proceeding to Phase B.
━━━━━━━━━━━━━━━━━━━━━━━
```

**Regression gap table** (print only if features have regression guidance but
no harness JSON and the gap was NOT resolved during Phase A):

```
Regression gaps requiring Builder: T features
| Feature | Harness Type | Blocker |
|---------|-------------|---------|
| <name>  | <type>      | <why>   |
```

**Decision point** (only when BOTH regression gaps needing Builder AND manual
items remain):
```
T features need Builder work for regression infrastructure.
M manual items remain for human verification.
→ [exit] Return to Builder for regression work
→ [continue] Proceed to Phase B manual verification
→ [both] Author what's possible now, then manual
```
When `auto_start` is `true`, default to `[both]` without prompting.
When `auto_start` is `false`, wait for user choice.

If zero manual items remain after Phase A:
```
All scenarios passed automated verification. No manual checklist needed.
```
Skip directly to Step 11 (Batch Completion).

---

## Phase B -- Manual Verification Checklist

### Step 6 -- Checklist Assembly

Collect remaining testable items (those NOT handled in Phase A) across in-scope TESTING features into a single flat-numbered list:

1.  Apply scope rules from Step 0. Skip cosmetic features. For targeted/dependency-only, include only in-scope scenarios.
2.  Exclude `@auto`-tagged scenarios -- already executed in Phase A Steps 2-4.
3.  Exclude visual items already verified in Phase A Step 5.
4.  Auto-skip builder-verified features (zero manual scenarios, zero visual items).
5.  Assign flat sequential numbers (1, 2, ... N) across all features. Do not restart numbering per feature.
6.  Visual items from `## Visual Specification` sections are interleaved under their feature, tagged with `[V]` prefix, sharing the numbering sequence.
7.  **Web-test visual dedup:** For features with `> Web Test:` metadata, exclude visual `[V]` items from the QA checklist. These were verified by the Builder via `/pl-web-test` during implementation and by Phase A Step 5. Include only manual scenarios that require human interaction. If a web-test feature has zero manual scenarios remaining after this exclusion, auto-skip it: `"Feature X: visual items verified via /pl-web-test. Auto-pass."`
8.  **Tier labels:** If tier classification exists in `QA_OVERRIDES.md`, prefix each feature group with its tier: `[SMOKE]`, `[STD]`, or `[FULL]`.
9.  **Condensing rule:** For each functional scenario, produce a two-line entry: line 1 = **what to do** (setup + action, imperative voice), line 2 = **what to verify** (expected outcome). Strip Gherkin boilerplate but keep essential setup context. Visual items use `[V]` prefix with verbatim checklist text (single line).
10. Cross-validation warnings: insert an advisory line before affected feature's items.
11. Fixture awareness: if Critic report includes `fixture_repo_unavailable` for a feature, append `[fixture N/A]` to affected scenarios.
12. Large visual batches (50+ visual items for one feature): offer grouped sub-prompt by screen.

### Step 7 -- Checklist Presentation

*   **Ordering:** Sort features: smoke first, then standard, then full-only. Within each tier group, sort ascending by estimated verification time (shortest first).

Output the checklist as a numbered list grouped by feature:

```
**Verification Checklist** -- N items across M features (~X min estimated)
Tiers: S smoke, T standard, F full-only
Default: PASS. Reply "all pass", or list failures: "F3, F7"
"help N" = I'll walk you through testing it | /pl-discovery = issues outside this list

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
    - **Action Required:** <Architect or Builder>
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
*   **Figma-Triangulated Verification:** When Figma MCP is available and a visual spec screen has a Figma reference, perform three-source comparison (Figma design, spec Token Map + checklists, running app). Verdicts: PASS, BUG (app wrong -> Builder), STALE (Figma updated -> PM), SPEC_DRIFT (app matches Figma, not spec -> PM).
*   **Web test alternative:** For features with `> Web Test:` metadata, `/pl-web-test` provides fully automated visual verification via Playwright MCP.

### Step 10 -- Exploratory Testing

After all checklist items are resolved, present:

> "Did you notice anything unexpected across all the features tested -- any behavior not covered by the checklist?"

If yes, record each as a `[DISCOVERY]` in the appropriate sidecar file. If no, proceed to Step 11.

### Step 11 -- Batch Completion

1.  **Present Phase A results:** `"Automated (Phase A): N @auto scenarios executed, M passed, K failed."`
2.  **Identify passing features:** All items (Phase A + Phase B) passed and zero discoveries recorded.
3.  **Delivery plan gating:** Check `.purlin/delivery_plan.md`. If a feature appears in any PENDING phase, do NOT mark complete: "Feature X passed but has more work coming in Phase N. Deferring [Complete]."
4.  **Mark eligible features complete:** `git commit --allow-empty -m "status(scope): [Complete features/FILENAME.md] [Verified]"`. The `[Verified]` tag is mandatory for QA completions.
5.  **Features with discoveries:** Do NOT mark complete. They remain in TESTING.
6.  **Run Critic once:** `${TOOLS_ROOT}/cdd/status.sh` after all status commits. Do NOT run per-feature.
7.  **Present batch summary:**
    *   Automated: N @auto executed, M passed, K failed.
    *   Manual: N passed, M failed, K disputed.
    *   Features completed (list).
    *   Features remaining in TESTING with discovery counts (list).
    *   Features deferred by delivery plan (list).
    *   Discovery routing: which items need Architect vs. Builder.
