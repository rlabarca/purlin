# Implementation Notes: QA Verification Effort Classification

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


*   **[CLARIFICATION]** `verification_effort` was a top-level key in the former critic output (sibling to `role_status`). The critic system has been removed; verification effort classification is now handled by the scan and `/pl-status` workflow. (Severity: INFO)
*   **[CLARIFICATION]** Hardware keyword detection uses a simple regex matching `hardware|serial|GPIO|USB|device|physical` against scenario body text. This is a coarse heuristic that may produce false positives (e.g., "the device settings panel"). If this proves too aggressive, it can be refined with negation patterns or a more targeted keyword list. (Severity: INFO)
*   **[CLARIFICATION]** The "mixed feature splits" scenario (INCONCLUSIVE handling from prior `/pl-aft-web` runs) is deferred. The current implementation does not read prior web-verify results to determine INCONCLUSIVE scenarios. All manual scenarios on AFT-web features are classified as `aft_web`. INCONCLUSIVE re-routing would require a persistent web-verify result store, which does not yet exist. (Severity: INFO)
*   **[CLARIFICATION]** The output schema includes both the spec-required simplified keys (`auto`, `manual`) and the pre-existing granular subcategories (`web_test`, `manual_interactive`, `manual_visual`, `manual_hardware`, `total_auto`, `total_manual`). The `auto` key counts @auto-tagged QA scenarios only; `manual` key equals `total_manual` (sum of all manual subcategories). (Severity: INFO)
*   **[CLARIFICATION]** The summary format excludes visual-auto items (web-test visual checklist items) from the "auto" count in the summary text. This reconciles the spec's example JSON (`auto: 5, manual: 6, summary: "6 manual"`) with scenario 4 (`auto: 2, manual: 1, summary: "2 auto, 1 manual"`). Visual items on web-test features are Engineer-verified via `/pl-web-test` and do not generate QA action items, so they appear in the `total_auto` field but not in the summary. Only @auto-tagged QA scenarios contribute to the summary's auto count. (Severity: INFO)
*   **[CLARIFICATION]** The `dependency-only` scope now filters scenarios to only those listed in `regression_scope.scenarios`, rather than treating all scenarios as in-scope. When the scenarios list is empty (no computed regression set), all manual scenarios are included as a safe fallback. (Severity: INFO)

## INCONCLUSIVE AFT-Web Results (Deferred)
INCONCLUSIVE AFT-web results are intentionally deferred. When AFT-web returns INCONCLUSIVE for a checklist item, the item falls back to manual verification classification. A dedicated INCONCLUSIVE handling scenario will be added when the persistent web-verify result store is implemented.
