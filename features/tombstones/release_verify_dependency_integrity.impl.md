# Implementation Notes: Verify Dependency Integrity

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | [ACKNOWLEDGED]** Stale cache regeneration not implemented | DISCOVERY | PENDING |
| (see prose) | Reverse reference classification not implemented as tiered severity — **ACKNOWLEDGED** | DISCOVERY | PENDING |

This step is a structural read-only check. PM mode does not modify feature files as part of this step. Regenerating the dependency cache via `tools/cdd/scan.sh --graph` is permissible and does not count as a spec modification.

The dependency graph is computed and cached by `tools/cdd/scan.sh --graph`. Manual graph file edits are not supported; the cache is always regenerated from source feature files.

### Audit Finding -- 2026-03-23

**[DISCOVERY] [ACKNOWLEDGED]** Stale cache regeneration not implemented
**Source:** /pl-spec-code-audit --deep (H10)
**Severity:** HIGH
**Details:** Spec §2.1 requires reading `.purlin/cache/dependency_graph.json` and checking its modification time, then running `tools/cdd/scan.sh --graph` to regenerate if stale or absent. `verify_dependency_integrity.py:83-107` calls `parse_features()` from `graph.py` directly, bypassing the cache file and staleness check entirely. The cache-regeneration path is never invoked.
**Suggested fix:** Add cache file mtime check and `scan.sh --graph` invocation before `parse_features()`.

### Audit Finding -- 2026-03-16

[DISCOVERY] Reverse reference classification not implemented as tiered severity — **ACKNOWLEDGED**

**Source:** /pl-spec-code-audit --deep
**Severity:** MEDIUM
**Details:** The spec describes tiered severity for reverse references (based on distance, type), but the implementation flags all reverse references at the same severity level.
**Suggested fix:** Implement tiered severity per spec: direct reverse refs = HIGH, transitive = MEDIUM, informational = LOW.

**PM Acknowledgment (2026-03-19):** Re-confirmed during deep audit. The flat severity classification is a known simplification. The spec's tiered model (direct=HIGH, transitive=MEDIUM, informational=LOW) remains the target state. Priority: LOW -- the current behavior is conservative (over-flags rather than under-flags), which is safe for release validation.
