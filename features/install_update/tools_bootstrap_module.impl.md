# Implementation Notes: Bootstrap Module

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


## Design Decisions

**[CLARIFICATION]** The spec says "try the further path (3 levels up from script_dir) before the nearer path (2 levels up)." The implementation uses hardcoded relative depths (`../../../` and `../../`) matching the existing inline patterns exactly. A general walk-up approach was considered but rejected because it could find `.purlin/` directories from unrelated projects higher in the filesystem tree (e.g., Claude Code's `~/.claude/projects/*/memory/` creates `.purlin/` in the user's home directory). (Severity: INFO)

**[CLARIFICATION]** For scripts at non-standard depths (`scripts/cleanup_orphaned_features.py` and `scripts/test_pl_design_*.py` at `scripts/` root level), the migration passes `os.path.join(SCRIPT_DIR, 'config')` as `script_dir` to align with the standard 2-level depth expectation. This is functionally equivalent to their original custom climbing depths. (Severity: INFO)

**[CLARIFICATION]** `audit_common.py`'s `detect_project_root` was replaced with a re-export from bootstrap, preserving the import interface for downstream consumers (`verify_zero_queue.py`, `test_release_audit.py`). Legacy scripts (`verify_dependency_integrity.py`, `instruction_audit.py`, `doc_consistency_check.py`) were removed in 2026-03-26 — their functionality is now in toolbox agent_instructions. (Severity: INFO)

## Migration Summary

12 files migrated to import from `scripts/mcp/bootstrap.py`:
- **Application files (4):** graph.py, manage_step.py, resolve.py, extract_whats_different.py
- **Shared utility (1):** audit_common.py (re-export)
- **Test files (5):** test_manage_step.py, test_release.py, test_fixture.py, test_continuous_phase_builder.py, test_pl_design_ingest.py, test_pl_design_audit.py

Files NOT migrated (by design):
- `scripts/mcp/config_engine.py`: Keeps its own `_find_project_root` for CLI entry point (avoids circular dependency with bootstrap's `load_config`)


