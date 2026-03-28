## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


### Companion File Resolution
Companion files are resolved by stripping the `.md` extension from the feature filename and appending `.impl.md`. For example, `features/project_init.md` resolves to `features/project_init.impl.md`.

### Orphan Detection
Orphan detection is handled by the scan engine (`scripts/mcp/graph_engine.py`), which reports orphaned features in `.purlin/cache/dependency_graph.json` under the `orphans` key. The standalone `cleanup_orphaned_features.py` was removed (2026-03-26) as redundant.

### Re-Verification (2026-03-24)

**[CLARIFICATION]** Sections 2.2-2.10 were re-verified against the existing implementation. All requirements are satisfied by existing code. No code changes were needed. (Severity: INFO)

Verified sections:
- **2.2 Companion File Resolution**: Resolved by naming convention without feature file references.
- **2.3 Companion File Structure**: Companion files have no metadata headers; begin with heading and content directly.
- **2.4 Exclusion Rules**: graph.py excludes `.impl.md` and `.discoveries.md` from feature scanning.
- **2.5 Status Reset Exemption**: Scan excludes `.impl.md` from feature file scanning, so companion edits do not trigger lifecycle resets.
- **2.7 Orphan Detection**: Handled by scan engine (`graph_engine.py`). Standalone script removed.
- **2.9 Integration Test Fixture Tags**: Fixture tag `companion-with-decisions` defined in spec and referenced in `dev/setup_fixture_repo.sh`.
