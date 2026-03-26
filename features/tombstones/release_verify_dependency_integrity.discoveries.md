# Discovery Sidecar: release_verify_dependency_integrity

## [BUG] H10: Stale cache regeneration absent -- RESOLVED

**Source:** /pl-spec-code-audit --deep
**Severity:** HIGH
**Status:** RESOLVED
**Details:** Code called `parse_features()` directly without checking staleness of `dependency_graph.json`. Spec requires staleness check on `dependency_graph.json` before use; if stale, regenerate cache.
**Resolution:** Added `ensure_cache_fresh()` function to `tools/release/verify_dependency_integrity.py` that checks if `.purlin/cache/dependency_graph.json` is absent or older than the most recently modified feature file. If stale, calls `run_full_generation()` from `tools/cdd/graph.py` to regenerate before proceeding. Three tests added to cover absent, stale, and fresh cache scenarios.
