## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Core data model and resolution algorithm in tools/toolbox/resolve.py: three-source resolution (purlin, project, community), fuzzy matching (exact ID + substring), reserved prefix validation, schema version handling, backward compatibility with old release-step format. Project tools registry in .purlin/toolbox/project_tools.json. Unit tests in tools/toolbox/test_toolbox.py.

**[GAP]** Project-community collision handling: spec says "error," code skips tool but continues (soft error vs hard error). Community tool write operations (add/pull/push) not in resolve.py — belongs to toolbox_community feature. Unrecognized fields: preserved with warning, warning path not tested. Estimated: ~60% complete.
