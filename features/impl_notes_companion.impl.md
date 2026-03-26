## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


### Companion File Resolution
Companion files are resolved by stripping the `.md` extension from the feature filename and appending `.impl.md`. For example, `features/project_init.md` resolves to `features/project_init.impl.md`.

### Orphan Detection
`cleanup_orphaned_features.py` detects orphaned companions by checking whether a corresponding `features/<name>.md` exists.

### Re-Verification (2026-03-24)

**[CLARIFICATION]** Sections 2.2-2.10 were re-verified against the existing implementation. All requirements are satisfied by existing code. No code changes were needed. (Severity: INFO)

Verified sections:
- **2.2 Companion File Resolution**: Resolved by naming convention without feature file references.
- **2.3 Companion File Structure**: Companion files have no metadata headers; begin with heading and content directly.
- **2.4 Exclusion Rules**: graph.py and cleanup_orphaned_features.py exclude `.impl.md` and `.discoveries.md` from feature scanning.
- **2.5 Status Reset Exemption**: Scan excludes `.impl.md` from feature file scanning, so companion edits do not trigger lifecycle resets.
- **2.7 Orphan Detection**: `get_referenced_features()` in cleanup_orphaned_features.py detects orphaned companions.
- **2.9 Integration Test Fixture Tags**: Fixture tag `companion-with-decisions` defined in spec and referenced in `dev/setup_fixture_repo.sh`.
