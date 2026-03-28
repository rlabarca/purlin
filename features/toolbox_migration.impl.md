## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Core migration script at scripts/migration/migrate_release_to_toolbox.py: detects old release steps, transforms to toolbox format, writes project_tools.json, writes migration marker with checksum. Unit tests in scripts/migration/test_migrate_release_to_toolbox.py. Edge cases handled: empty steps, corrupt JSON, partial re-run.

**[IMPL]** Integration hooks verified complete: (1) pl-update-purlin step 7c documents toolbox migration detection and script invocation. (2) init.sh full mode copies templates/ (which includes toolbox/ with project_tools.json and community_tools.json) to .purlin/; refresh mode creates .purlin/toolbox/community/ directory without overwriting project-owned files. (3) pl-update-purlin step 8 handles stale artifact cleanup — checks for .purlin/release/ after migration marker exists, prompts user for deletion.
