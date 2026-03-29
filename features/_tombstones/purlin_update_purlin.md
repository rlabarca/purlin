# TOMBSTONE: purlin_update_purlin

**Retired:** 2026-03-28
**Reason:** Replaced by `features/purlin_update.md` which unifies the old submodule-only update and one-time upgrade into a single version-aware command.

## Files to Delete

- `skills/upgrade/SKILL.md` -- old one-time submodule-to-plugin migration skill (merged into `purlin:update` step 2)
- `dev/setup_upgrade_fixture.sh` -- old single-era fixture script (replaced by `dev/setup_version_fixtures.sh`)

## Dependencies to Check

- `features/plugin_migration.md` -- references `skills/upgrade/SKILL.md` and `purlin:upgrade`
- `features/plugin_migration.impl.md` -- references `dev/setup_upgrade_fixture.sh`

## Context

The old `purlin_update_purlin` spec described a submodule-only update flow (fetch tags, advance submodule, sync config). The old `purlin:upgrade` skill handled the one-time submodule-to-plugin migration. Both are now unified into `purlin:update` via a three-layer architecture: version detector, migration registry (3 steps), and skill orchestration. The new `features/purlin_update.md` spec covers the full version-aware flow.
