## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| §2.3: Re-run overwrites existing toolbox files | Merges migrated tools into existing project_tools.json, deduplicating by ID. Existing tools take precedence. | [DEVIATION] | ACKNOWLEDGED |
| §2.6: Next purlin:update prompts for stale .purlin/release/ deletion | Step 8 checks for .purlin/release/ when .migrated_from_release marker exists and prompts for deletion. | [DEVIATION] | ACKNOWLEDGED |

### [DEVIATION] Migration merges with existing project_tools.json instead of overwriting
- **Spec says (§2.3):** "If `.purlin/toolbox/` exists but no marker, the migration re-runs and overwrites existing toolbox files."
- **Implementation does:** Merges migrated tools into any existing `project_tools.json`, deduplicating by ID. Existing tools take precedence.
- **Reason:** The overwrite behavior destroys manually-added project tools when migration runs on a project that started using the toolbox before formal migration. The spec's regression guidance itself flags this as the most fragile edge case.
- **Impact:** Partial migration recovery no longer wipes user data. The only behavioral change: existing tools are preserved rather than replaced.

### [DEVIATION] pl-update-purlin step 8 includes .purlin/release/ stale cleanup
- **Spec says (§2.6):** "The next `purlin:update` run (after the migration release) can prompt for deletion as a stale artifact."
- **Implementation does:** Step 8 now checks for `.purlin/release/` when `.migrated_from_release` marker exists and prompts for deletion.
- **Reason:** The spec described this behavior but the command file hadn't been updated to implement it.

### [DISCOVERY] Purlin repo local_steps.json deleted — 3 project tools are the canonical set
- The old `local_steps.json` had 5 tools that were superseded by the 3 manually-curated tools already in `project_tools.json`.
- `config.json` retains 2 orphaned stub entries (`sync_docs_to_confluence`, `sync_docs_to_github_wiki`) with no full definitions anywhere. These are harmless but stale.

**[IMPL]** Core migration script at scripts/migration/migrate_release_to_toolbox.py: detects old release steps, transforms to toolbox format, writes project_tools.json, writes migration marker with checksum. Unit tests in scripts/migration/test_migrate_release_to_toolbox.py. Edge cases handled: empty steps, corrupt JSON, partial re-run.

**[IMPL]** Integration hooks verified complete: (1) pl-update-purlin step 7c documents toolbox migration detection and script invocation. (2) init.sh full mode copies templates/ (which includes toolbox/ with project_tools.json and community_tools.json) to .purlin/; refresh mode creates .purlin/toolbox/community/ directory without overwriting project-owned files. (3) pl-update-purlin step 8 handles stale artifact cleanup — checks for .purlin/release/ after migration marker exists, prompts user for deletion.
