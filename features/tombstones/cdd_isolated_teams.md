# TOMBSTONE: cdd_isolated_teams

**Retired:** 2026-03-08
**Reason:** CDD Dashboard isolated teams section removed along with the isolated teams feature.

## Files to Delete

- `tools/cdd/test_cdd_isolated_teams.py` -- entire file
- `tools/cdd/serve.py:get_isolation_worktrees()` -- function and all helper functions: `_detect_worktrees()`, `_name_from_path()`, `_read_delivery_phase()`, `_worktree_state()`, `_compute_sync_state()` (isolation-specific), `_is_isolation_digest_stale()`, `_staleness_banner_html()`, `_isolation_section_html()`, `_collapsed_isolation_label()`
- `tools/cdd/serve.py` -- `/isolate/create`, `/isolate/kill`, `/isolate/<name>/whats-different/generate`, `/isolate/<name>/whats-different/read` API endpoints
- `tools/cdd/serve.py` -- ISOLATED TEAMS HTML section in `generate_html()`, kill modal HTML/JS, per-isolation What's Different modal
- `tools/cdd/serve.py` -- `isolations_active` and `worktrees` fields from `/status.json` generation
- `tools/cdd/serve.py` -- worktree propagation logic in `_handle_config_agents()`
- `tools/collab/generate_whats_different.sh` -- if only serves isolated teams (per-isolation digest)
- `tools/collab/generate_whats_different_deep.sh` -- if only serves isolated teams
- `tools/collab/extract_whats_different.py` -- if only serves isolated teams

## Dependencies to Check

- `tools/cdd/serve.py` -- dashboard section ordering must change from [BRANCH COLLABORATION, ISOLATED TEAMS, LOCAL BRANCH] to [BRANCH COLLABORATION, LOCAL BRANCH]
- `features/cdd_branch_collab.md` -- prerequisite link removed (covered in Phase 2)
- Test fixture tags `main/cdd_isolated_teams/*` -- may have fixture data to clean up

## Context

This feature rendered the ISOLATED TEAMS section in the CDD Dashboard, including worktree detection, sync state display, creation/kill UI, and per-isolation What's Different digests. All of this is obsolete with the removal of isolated teams.
