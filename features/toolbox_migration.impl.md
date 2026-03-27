## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Core migration script at tools/migration/migrate_release_to_toolbox.py: detects old release steps, transforms to toolbox format, writes project_tools.json, writes migration marker with checksum. Unit tests in tools/migration/test_migrate_release_to_toolbox.py. Edge cases handled: empty steps, corrupt JSON, partial re-run.

**[GAP]** Integration hooks missing: not wired into pl-update-purlin step 7c, init.sh doesn't copy toolbox sample for new projects, no stale artifact cleanup prompting for old .purlin/release/ directory. Estimated: ~75% complete.
