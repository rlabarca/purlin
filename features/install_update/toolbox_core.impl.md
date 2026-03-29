## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Core data model and resolution algorithm in scripts/toolbox/resolve.py: three-source resolution (purlin, project, community), fuzzy matching (exact ID + substring), reserved prefix validation, schema version handling, backward compatibility with old release-step format. Project tools registry in .purlin/toolbox/project_tools.json. Unit tests in scripts/toolbox/test_toolbox.py.

**[IMPL]** Project-community collision handling: scripts/toolbox/resolve.py reports exact-ID collision between project and community as an error (appended to errors list) and skips the conflicting community tool. This matches the spec's "error" semantics — the error is surfaced to the caller, and resolution continues for non-conflicting tools. Community tool write operations (add/pull/push) implemented in scripts/toolbox/community.py per the toolbox_community feature.

**[IMPL]** Unrecognized field warnings: Added `warnings` parameter to `_make_resolved_entry()` so it appends a warning message per unrecognized field. Format: `"Tool '<id>' has unrecognized field '<key>' (preserved)"`. All callers in `resolve_toolbox()` now pass the shared `warnings` list. This closes the spec 2.1 gap -- fields are preserved AND a warning is emitted.

**[IMPL]** Fixed broken `test_case_insensitive`: test searched for "ZERO" but no tool in the fixture contained "zero". Changed query to "DEPENDENCY" which uniquely matches `purlin.verify_dependency_integrity`.

**[IMPL]** Updated `test_unrecognized_fields_preserved` to also assert that warnings are returned when unrecognized fields exist. Added new `test_unrecognized_fields_warning` to verify warning message content (tool ID and field name appear in each warning, one warning per unrecognized field).
