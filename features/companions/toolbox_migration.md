# Companion: toolbox_migration

## Deviations

### [DEVIATION] Migration merges with existing project_tools.json instead of overwriting
- **Spec says (§2.3):** "If `.purlin/toolbox/` exists but no marker, the migration re-runs and overwrites existing toolbox files."
- **Implementation does:** Merges migrated tools into any existing `project_tools.json`, deduplicating by ID. Existing tools take precedence.
- **Reason:** The overwrite behavior destroys manually-added project tools when migration runs on a project that started using the toolbox before formal migration. The spec's regression guidance itself flags this as the most fragile edge case.
- **Impact:** Partial migration recovery no longer wipes user data. The only behavioral change: existing tools are preserved rather than replaced.

### [DEVIATION] pl-update-purlin step 8 includes .purlin/release/ stale cleanup
- **Spec says (§2.6):** "The next `/pl-update-purlin` run (after the migration release) can prompt for deletion as a stale artifact."
- **Implementation does:** Step 8 now checks for `.purlin/release/` when `.migrated_from_release` marker exists and prompts for deletion.
- **Reason:** The spec described this behavior but the command file hadn't been updated to implement it.

## Discoveries

### [DISCOVERY] Purlin repo local_steps.json deleted — 3 project tools are the canonical set
- The old `local_steps.json` had 5 tools that were superseded by the 3 manually-curated tools already in `project_tools.json`.
- `config.json` retains 2 orphaned stub entries (`sync_docs_to_confluence`, `sync_docs_to_github_wiki`) with no full definitions anywhere. These are harmless but stale.
