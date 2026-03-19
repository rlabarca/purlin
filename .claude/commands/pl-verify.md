**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-verify instead." and stop.

---

## Scope

If an argument was provided, scope verification to `features/<arg>.md` only.
If no argument was provided, run `tools/cdd/status.sh --role qa` and batch ALL TESTING features with manual scenarios into a single verification checklist.

---

## Batched Verification Workflow

### Step 1 -- Scoped Verification Modes

Before assembling the checklist, check each feature's regression scope from `tests/<feature_name>/critic.json`:

*   **`full`** (or missing/default) -- Verify all manual scenarios and all visual checklist items.
*   **`targeted:Scenario A,Scenario B`** -- Verify ONLY the named scenarios. Skip all other manual scenarios and visual items unless explicitly named.
*   **`cosmetic`** -- Skip the feature entirely. Output: "Feature X: QA skip (cosmetic change). No scenarios queued."
*   **`dependency-only`** -- Verify only scenarios listed in `regression_scope.scenarios`. If the list is empty, skip: "Feature X: QA skip (dependency-only, no scenarios in scope)."

If the Critic emitted a cross-validation WARNING (e.g., `cosmetic` scope but modified files touch manual scenarios), present the warning and ask whether to proceed with declared scope or escalate to `full`.

### Step 2 -- Checklist Assembly

Collect all testable items across TESTING features into a single flat-numbered list:

1.  Apply scope rules from Step 1. Skip cosmetic features. For targeted/dependency-only, include only in-scope scenarios.
2.  Auto-skip builder-verified features (zero manual scenarios, zero visual items).
3.  Assign flat sequential numbers (1, 2, ... N) across all features. Do not restart numbering per feature.
4.  Visual items from `## Visual Specification` sections are interleaved under their feature, tagged with `[V]` prefix, sharing the numbering sequence.
5.  **Condensing rule:** For each functional scenario, produce a two-line entry: line 1 = **what to do** (setup + action, imperative voice), line 2 = **what to verify** (expected outcome). Strip Gherkin boilerplate but keep essential setup context. Visual items use `[V]` prefix with verbatim checklist text (single line).
6.  Cross-validation warnings: insert an advisory line before affected feature's items.
7.  Fixture awareness: if Critic report includes `fixture_repo_unavailable` for a feature, append `[fixture N/A]` to affected scenarios.
8.  Large visual batches (50+ visual items for one feature): offer grouped sub-prompt by screen.

### Step 3 -- Checklist Presentation

Output the checklist as a numbered list grouped by feature:

```
**Verification Checklist** -- N items across M features
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

**Format rules:** Feature headers are bold with priority tag. One blank line between groups. Functional items: `N. **Do:** ...` / `   **Verify:** ...`. Visual items: `N. [V] ...`. Imperative voice. End with response prompt + help offer.

**Zero testable items:** If all TESTING features are builder-verified or cosmetic-scoped, skip the checklist. Output: "All TESTING features are builder-verified. No manual verification needed." Proceed to Step 7.

### Step 4 -- Response Processing

Parse the user's response (case-insensitive, flexible separators):

*   **`all pass`** / **`pass`** -- All items pass. Proceed to Step 6.
*   **`F3, F7`** / **`3, 7`** / **`f3 f7`** -- Items 3 and 7 failed; everything else passes. Proceed to Step 5.
*   **`help 5`** / **`help 5, 8`** -- Walk the user through testing the item(s) step by step: setup, actions, what to look for. Use the full Gherkin scenario as source but present conversationally. For `[V]` items, explain what to inspect and where. Re-prompt for overall response.
*   **`detail 5`** / **`d5`** / **`detail 5, 8`** -- Show raw Gherkin steps (or full visual checklist with design references). Re-prompt.
*   **`DISPUTE 4`** / **`dispute 4`** -- Triggers SPEC_DISPUTE flow for item 4. Ask why they disagree. Record a `[SPEC_DISPUTE]` discovery. Scenario is suspended. Re-prompt for remaining items.
*   **Stop / partial** -- Complete passing features verified so far, leave the rest in TESTING, proceed to Step 7 with partial summary.

### Step 5 -- Failure Processing

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

### Step 5.5 -- Visual Verification Integration

Visual items appear as numbered `[V]` entries in the main checklist. Judged by number like functional items.

*   **Detail expansion:** When `detail` requested for a `[V]` item, present full visual context: design anchor references, Token Map entries, design asset reference.
*   **Screenshot-assisted analysis:** Offer screenshot input when: user requests `detail` for visual items, feature has many visual items (10+), or user explicitly asks. When screenshots are provided:
    1.  Read each screenshot via the Read tool.
    2.  Classify checklist items as screenshot-verifiable (static visible properties) vs. not (interactions, state persistence, temporal behaviors).
    3.  For verifiable items: PASS, FAIL, or UNCERTAIN with observation notes.
    4.  Present results in two groups: auto-verified + manual confirmation required.
*   **Figma-Triangulated Verification:** When Figma MCP is available and a visual spec screen has a Figma reference, perform three-source comparison (Figma design, spec Token Map + checklists, running app). Verdicts: PASS, BUG (app wrong -> Builder), STALE (Figma updated -> PM), SPEC_DRIFT (app matches Figma, not spec -> PM).
*   **Web test alternative:** For features with `> Web Test:` metadata, `/pl-web-test` provides fully automated visual verification via Playwright MCP.

### Step 6 -- Exploratory Testing

After all checklist items are resolved, present:

> "Did you notice anything unexpected across all the features tested -- any behavior not covered by the checklist?"

If yes, record each as a `[DISCOVERY]` in the appropriate sidecar file. If no, proceed to Step 7.

### Step 7 -- Batch Completion

1.  **Identify passing features:** All items passed and zero discoveries recorded.
2.  **Delivery plan gating:** Check `.purlin/delivery_plan.md`. If a feature appears in any PENDING phase, do NOT mark complete: "Feature X passed but has more work coming in Phase N. Deferring [Complete]."
3.  **Mark eligible features complete:** `git commit --allow-empty -m "status(scope): [Complete features/FILENAME.md] [Verified]"`. The `[Verified]` tag is mandatory for QA completions.
4.  **Features with discoveries:** Do NOT mark complete. They remain in TESTING.
5.  **Run Critic once:** `tools/cdd/status.sh` after all status commits. Do NOT run per-feature.
6.  **Present batch summary:**
    *   Total items: N passed, M failed, K disputed.
    *   Features completed (list).
    *   Features remaining in TESTING with discovery counts (list).
    *   Features deferred by delivery plan (list).
    *   Discovery routing: which items need Architect vs. Builder.
