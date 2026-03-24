# User Testing Discoveries: Release Verify Dependency Integrity

### [BUG] H10: Stale cache regeneration absent (Discovered: 2026-03-23)
- **Observed Behavior:** Code calls `parse_features()` directly without checking staleness of `dependency_graph.json`.
- **Expected Behavior:** Spec requires a staleness check on `dependency_graph.json` before use; if stale, the cache should be regenerated before proceeding.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See release_verify_dependency_integrity.impl.md for full context.
