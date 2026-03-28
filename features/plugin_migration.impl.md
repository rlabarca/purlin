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
