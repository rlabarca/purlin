# TOMBSTONE: submodule_sync

**Retired:** 2026-03-05
**Reason:** Replaced by `/pl-update-purlin` agent skill (features/pl_update_purlin.md), which provides intelligent merge strategies, migration plans, and user customization preservation.

## Files to Delete

- `tests/submodule_sync/` -- entire directory (tests.json, critic.json for retired feature)
- `features/submodule_sync.impl.md` -- companion file for retired feature

## Dependencies to Check

- `tools/test_bootstrap.sh` -- contains stale `sync_upstream.sh` references throughout (header comment, cp/chmod lines, test setup). Remove all sync_upstream.sh references from this test file.
- `RELEASE_NOTES.md` -- references sync_upstream.sh in historical context (no action needed, historical record)
- `features/pl_update_purlin.md` -- references sync_upstream.sh as the predecessor it replaced (no action needed, contextual)

## Context

This feature specified `tools/sync_upstream.sh`, a shell script that fetched upstream Purlin commits, displayed changelogs, and synced command files to consumer projects. The script itself was already deleted by the Builder in a previous session. The `/pl-update-purlin` agent skill (features/pl_update_purlin.md) is the full replacement, providing all original functionality plus intelligent conflict resolution and customization preservation. This tombstone exists to trigger cleanup of residual test artifacts and stale references in `tools/test_bootstrap.sh`.
