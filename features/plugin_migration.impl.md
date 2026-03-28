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
