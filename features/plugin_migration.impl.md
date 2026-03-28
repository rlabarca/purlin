# Companion: Plugin Architecture Migration

## Active Deviations

| Tag | Section | Description | PM Status |
|-----|---------|-------------|-----------|
| — | — | No deviations | — |

## Implementation Log

### Phase 0: Plugin Scaffold
- [IMPL] Created `.claude-plugin/plugin.json` with name, version (0.9.0), description, author, and userConfig (figma_access_token, default_model).
- [IMPL] Created `settings.json` at repo root with `{ "agent": "purlin" }`.
- [IMPL] Created `agents/purlin.md` with full PURLIN_BASE.md content transformed for plugin model: all `/pl-*` refs → `purlin:*`, all `{tools_root}/` → `${CLAUDE_PLUGIN_ROOT}/scripts/`, all `instructions/references/` → `${CLAUDE_PLUGIN_ROOT}/references/`, removed submodule-specific sections (submodule immutability mandate, launcher pre-session references).

### Phase 1: Skill Migration
- [IMPL] Migrated all 36 `.claude/commands/pl-*.md` files to `skills/*/SKILL.md` format using `dev/migrate_skills.py`.
- [IMPL] Applied 4 mechanical transforms to every skill: YAML frontmatter addition, `/pl-*` → `purlin:*` cross-references, `${TOOLS_ROOT}/` → `${CLAUDE_PLUGIN_ROOT}/scripts/` paths, `instructions/references/` → `${CLAUDE_PLUGIN_ROOT}/references/` paths. Also replaced legacy Path Resolution preamble.
- [IMPL] Created `skills/start/SKILL.md` — session entry point replacing pl-run.sh, with checkpoint recovery, mode activation, worktree entry, YOLO support, and hook integration table.
- [IMPL] Created `skills/init/SKILL.md` — project initialization replacing init.sh, with 7-step flow (pre-flight, directory creation, config, CLAUDE.md, gitignore, features/, confirmation).
- [IMPL] Created `skills/upgrade/SKILL.md` — submodule-to-plugin migration with 11-step flow including dry-run support, pre-upgrade safety commit, and step-by-step verification.
- [IMPL] Deleted all 36 old `.claude/commands/pl-*.md` files. `.claude/commands/` directory is now empty.
- [IMPL] Special case: `pl-update-purlin.md` → `skills/update/SKILL.md` (dropped `-purlin` suffix since plugin namespace provides context).

### Phase 2: MCP Server + Script Migration
- [IMPL] Created `scripts/mcp/purlin_server.py` — MCP stdio server (JSON-RPC 2.0) with 6 tools: purlin_scan, purlin_status, purlin_graph, purlin_classify, purlin_mode, purlin_config. Stdlib only, lazy module loading, in-memory scan cache.
- [IMPL] Refactored `scan.py` → `scripts/mcp/scan_engine.py`: updated imports from `tools.bootstrap`/`tools.cdd.invariant`/`tools.smoke.smoke` to same-directory imports. `run_scan()` function already existed and is importable.
- [IMPL] Refactored `graph.py` → `scripts/mcp/graph_engine.py`: updated imports.
- [IMPL] Copied `invariant.py` → `scripts/mcp/invariant_engine.py`: no import changes needed (stdlib only).
- [IMPL] Refactored `resolve_config.py` → `scripts/mcp/config_engine.py`: simplified `_find_project_root()` to use cwd climbing instead of submodule nearer/further logic. Added `classify_file()`, `get_mode()`, `set_mode()` for mode guard support.
- [IMPL] Refactored `bootstrap.py` → `scripts/mcp/bootstrap.py`: simplified `detect_project_root()` to use cwd climbing. Inlined `load_config()` (no longer delegates to resolve_config.py import).
- [IMPL] Moved supporting scripts: `terminal/identity.sh`, `toolbox/*.py`, `worktree/manage.sh`, `test_support/*`, `smoke/` to `scripts/`.
- [IMPL] Updated `.mcp.json` with purlin MCP server entry pointing to `scripts/mcp/purlin_server.py`.
- [IMPL] Deleted old `tools/` files: scan.py, graph.py, invariant.py, scan.sh, resolve_config.py, bootstrap.py, resolve_python.sh, init.sh, toolbox scripts, terminal/identity.sh, worktree/manage.sh, smoke/smoke.py.

### Phase 3: Hook Implementation
- [IMPL] Created `hooks/hooks.json` declaring 6 hook events: SessionStart (clear + compact matchers), SessionEnd, PreToolUse (Write|Edit|NotebookEdit matcher), PermissionRequest, PreCompact, FileChanged.
- [IMPL] Created 6 hook scripts: session-start.sh (context reminder), session-end-merge.sh (worktree merge adapted from old merge-worktrees.sh), mode-guard.sh (mechanical PreToolUse enforcement with MCP + JSON fallback), permission-manager.sh (YOLO auto-approve from config), pre-compact-checkpoint.sh (auto-save checkpoint), companion-debt-tracker.sh (FileChanged tracking).
- [IMPL] Created `references/file_classification.json` — machine-readable pattern-to-classification rules for mode guard fallback.
- [IMPL] Deleted `tools/hooks/merge-worktrees.sh` (moved to hooks/scripts/).
- [IMPL] Cleared old SessionStart/SessionEnd hooks from `.claude/settings.json`.

### Phase 4: References, Templates, Agent Defs, Cleanup
- [IMPL] Moved 16 reference docs from `instructions/references/` to `references/`.
- [IMPL] Deleted `instructions/PURLIN_BASE.md` and entire `instructions/` directory.
- [IMPL] Moved `purlin-config-sample/` to `templates/` (CLAUDE.md.purlin → CLAUDE.md). Deleted `purlin-config-sample/`.
- [IMPL] Moved `engineer-worker.md` and `verification-runner.md` from `.claude/agents/` to `agents/`. Deleted `.claude/commands/`.
- [IMPL] Deleted `pl-run.sh` (replaced by purlin:start).
- [IMPL] Moved `feature_templates/`, `collab/`, `release/`, `mcp/manifest.json` from `tools/` to `scripts/`.
- [IMPL] Deleted entire `tools/` directory (including all remaining test scripts — these tested old paths and need rewriting for Phase 5).
- [IMPL] Created `output-styles/purlin-status.md`.
- [IMPL] Updated CLAUDE.md for plugin model (purlin:start, purlin:help).
- [IMPL] Updated `.gitignore`: un-ignored `.mcp.json`, added `.claude-plugin-data/` pattern.
