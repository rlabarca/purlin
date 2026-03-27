## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Core data model and resolution algorithm in tools/toolbox/resolve.py: three-source resolution (purlin, project, community), fuzzy matching (exact ID + substring), reserved prefix validation, schema version handling, backward compatibility with old release-step format. Project tools registry in .purlin/toolbox/project_tools.json. Unit tests in tools/toolbox/test_toolbox.py.

**[GAP]** Project-community collision handling: spec says "error," code skips tool but continues (soft error vs hard error). Community tool write operations (add/pull/push) not in resolve.py -- belongs to toolbox_community feature. Estimated: ~70% complete.

**[IMPL]** Unrecognized field warnings: Added `warnings` parameter to `_make_resolved_entry()` so it appends a warning message per unrecognized field. Format: `"Tool '<id>' has unrecognized field '<key>' (preserved)"`. All callers in `resolve_toolbox()` now pass the shared `warnings` list. This closes the spec 2.1 gap -- fields are preserved AND a warning is emitted.

**[IMPL]** Fixed broken `test_case_insensitive`: test searched for "ZERO" but no tool in the fixture contained "zero". Changed query to "DEPENDENCY" which uniquely matches `purlin.verify_dependency_integrity`.

**[IMPL]** Updated `test_unrecognized_fields_preserved` to also assert that warnings are returned when unrecognized fields exist. Added new `test_unrecognized_fields_warning` to verify warning message content (tool ID and field name appear in each warning, one warning per unrecognized field).
