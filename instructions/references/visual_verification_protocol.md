# Visual Verification Protocol

> This file is loaded on-demand by `/pl-verify` when a feature has a `## Visual Specification` section.

## 5.4.1 Present Checklist and Offer Screenshot Input
1.  **Present the visual spec overview:** List the screens defined in the visual specification section with their design asset references. For each screen, also present the `- **Processed:**` date. If the processed date is older than the artifact's modification time (or the Critic has flagged it as STALE), note the staleness to the user: "Warning: design artifact for Screen X was updated after the description was last processed. The description may not reflect the latest design."
2.  **Present the full checklist** for the screen (all visual acceptance criteria).
3.  **Offer screenshot input:** After presenting the checklist, prompt the user: "Would you like to provide one or more screenshots of this screen? I can analyze them to auto-verify many of the checklist items, reducing the number of items you need to confirm manually."
4.  If the user declines or provides no screenshots, fall back to manual verification (Section 5.4.4).

## 5.4.2 Screenshot Analysis
When screenshot(s) are provided:

1.  **Read each screenshot** via the Read tool.
2.  **Validate the screenshot** appears to show the expected screen. If it does not match or is clearly cropped/low-quality, inform the user and ask for a corrected one, or proceed with what is visible.
3.  **Design artifact comparison (optional):** If the screen has a local design artifact reference (`features/design/<stem>/<file>`), QA MAY read the artifact alongside the screenshot to compare the implementation against the original design intent. This enables detection of visual drift between the design artifact and the live implementation.
4.  **Classify each checklist item** into one of two categories:
    *   **Screenshot-verifiable:** Static visible properties -- element presence, layout/positioning, typography, color, spacing, alignment, text content.
    *   **Not screenshot-verifiable:** Interaction behaviors (clicks, toggles, hovers), state persistence (survives refresh/reload), temporal behaviors (animations, auto-refresh stability, flicker), implementation details (CSS variables, localStorage), absence of negative behaviors ("does not re-load").
5.  **For screenshot-verifiable items:** Examine the screenshot and determine PASS, FAIL, or UNCERTAIN.
    *   **PASS:** Auto-checked with a brief observation note (e.g., "Heading text 'ACTIVE' visible in bold, left-aligned").
    *   **FAIL:** Flagged with expected vs. observed. Present to the user for confirmation before recording -- the agent may misjudge due to image compression, scaling, or rendering differences.
    *   **UNCERTAIN:** Moved to the manual confirmation list with a reason (e.g., "Cannot determine exact font family from screenshot").
6.  **For non-verifiable items:** Added to the manual confirmation list without analysis.
7.  **Multi-screenshot support:** If checklist items reference multiple states (e.g., dark and light theme), ask the user for additional screenshots as needed, or defer cross-state items to the manual list.

## 5.4.3 Consolidated Results
Present results in two groups:

1.  **Auto-verified items:** List each item with PASS/FAIL and a brief observation note. Any auto-FAILs require user confirmation before being recorded as failures.
2.  **Manual confirmation required:** A consolidated list of items the agent could not verify from screenshots. Present these together with a single prompt for the user to confirm PASS or FAIL (preserving the existing "single checklist, single prompt" pattern for the manual subset).

## 5.4.4 Manual Fallback
If the user declines screenshots: present the full checklist and ask for a single PASS/FAIL for all visual items (current behavior, preserved as-is).

## 5.4.5 Recording Failures
Record failures using the standard discovery protocol (Section 4.2). Record `[BUG]` or `[DISCOVERY]` entries (depending on whether a scenario covers the behavior) with a "visual" context note in the discovery entry. For auto-detected failures confirmed by the user, include the screenshot observation in the discovery's Observed Behavior field.

## 5.4.6 Batching Optimization
When multiple features have visual specs in the same session, you MAY offer to batch all visual checks together with screenshot-assisted verification:
*   Collect screenshots for all screens across features before analysis.
*   Present auto-verified results grouped by feature.
*   Present the consolidated manual confirmation list across all features.
*   Example prompt: "3 functional scenarios across 2 features completed. Ready for visual verification: 12 checklist items across 3 screens. Would you like to provide screenshots for batch analysis, or verify feature-by-feature?"
