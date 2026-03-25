# Implementation Notes: Git Timestamp Resilience

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


*   **Section 2.1 (Boundary-Inclusive Lifecycle Comparisons):** Changed `>` to `>=` in both `_has_testing_phase_commit()` (critic.py line 2252) and `_has_verified_complete_commit()` (critic.py line 2310). Updated comments from "strictly after" to "at or after". These functions are used by `compute_role_status()` for QA verification integrity checks.
*   **Section 2.2 (Deterministic Scope Assignment):** Added hash-based tiebreaker to `build_status_commit_cache()` in serve.py. When two status commits share the same Unix timestamp, the commit with the lexicographically greater commit hash wins. Added `_best_hash` internal tracking field (cleaned up before return, same pattern as existing `_best_ts`).
*   **Section 2.3 (Conservative Fast-Path):** Changed `<=` to `<` in `get_feature_status()` (serve.py) for both the complete_ts and testing_ts fast-path comparisons. When `file_mod_ts == complete_ts` (same second), the function now falls through to `spec_content_unchanged()` instead of taking the fast path. Applied consistently to both complete and testing branches for safety, even though the spec only explicitly mentions complete_ts.
*   **[CLARIFICATION]** Applied the same `<` fast-path change to the testing_ts branch (line 312) for consistency, even though the spec's Section 2.3 only mentions complete_ts explicitly. The same-second race condition applies equally to both lifecycle states. (Severity: INFO)
