# Implementation Notes: Config Layering

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | CLI role mode shell variable outputs use stale names — Acknowledged | DISCOVERY | PENDING |

## Consumer Inventory

### Python Consumers (import `resolve_config`)

| File | Current Pattern | Migration |
|------|----------------|-----------|
| `scripts/collab/extract_whats_different.py` | `json.load()` on config path | Replace with `resolve_config()` import |

All Python consumers follow the Section 2.13 safe-read pattern (`try/except` with fallback defaults). The resolver centralizes this -- individual consumers no longer need their own error handling for config reads.

### Shell Consumers (call `resolve_config.py` CLI)

| File | Current Pattern | Migration |
|------|----------------|-----------|
| `purlin:resume` | MCP `purlin_config` tool call | Config resolved via `config_engine.py` at session entry |
| `purlin:mode` | MCP `purlin_config` tool call | Config resolved via `config_engine.py` on mode switch |
| `purlin_scan` MCP tool | Config resolved via `config_engine.py` internally | No migration needed (handled by MCP server) |

### Writers

| Component | Current Target | New Target | Notes |
|-----------|---------------|------------|-------|
| `purlin:agent-config` skill | `config.json` + git commit | `config.local.json`, no commit | Commit step removed (gitignored file) |
| `bootstrap.sh` | Creates `config.json` | Creates `config.json` only (unchanged) | Adds `config.local.json` to gitignore |

## Phased Implementation Order

### Phase 1: Foundation
1. Create `scripts/mcp/config_engine.py` with `resolve_config()`, `sync_config()`, and CLI modes.
2. Wire into MCP server (`scripts/mcp/purlin_server.py`) as `purlin_config` tool.
3. Write unit tests for the resolver (`tests/config_layering/`).

### Phase 2: Reader Migration
4. Update Python consumers (5 files) to import and use `resolve_config()`.
5. Update shell consumers (4-5 files) to call `resolve_config.py` CLI.
6. Verify all readers produce identical behavior to before (same config values returned).

### Phase 3: Writer Updates
7. Update `purlin:agent-config` command file to target `config.local.json` and remove commit step.

### Phase 4: Bootstrap and Gitignore
11. Update `bootstrap.sh` to add `.purlin/config.local.json` to consumer `.gitignore`.
12. Add `.purlin/config.local.json` to this repo's `.gitignore`.

### Phase 5: Worktree Propagation
13. Update `create_isolation.sh` to copy `config.local.json` alongside `config.json`.

## Pattern Replacement Template

### Python (before)
```python
config_path = os.path.join(project_root, ".purlin", "config.json")
try:
    with open(config_path) as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}
```

### Python (after)
```python
from scripts.mcp.config_engine import resolve_config
config = resolve_config(project_root)
```

### MCP Tool
Config resolution is now handled by the `purlin_config` MCP tool, which wraps `scripts/mcp/config_engine.py`. Shell consumers call the MCP tool directly instead of eval-ing Python output.

## Test Update Inventory

Existing tests that reference `config.json` directly may need updates:

- `scripts/test_bootstrap.sh` -- Verify it checks `config.json` creation (shared template) but NOT `config.local.json` creation.
- `tests/pl_agent_config/` -- Tests must verify writes to `config.local.json` and absence of git commits.

New test directory: `tests/config_layering/` for resolver unit tests covering all 24 scenarios.

## Resolver Project Root Detection

The resolver in `scripts/mcp/config_engine.py` uses the project root from the MCP server's working directory. No path climbing or `PURLIN_PROJECT_ROOT` needed — the MCP server runs from the project root.

### Audit Finding -- 2026-03-19

[DISCOVERY] CLI role mode shell variable outputs use stale names — Acknowledged

**Source:** purlin:spec-code-audit --deep (item #8)
**Severity:** HIGH
**Details:** The spec (Section 2.6) defines CLI role mode outputs as `AGENT_FIND_WORK` and `AGENT_AUTO_START`, but the shell consumer template in this companion file (line 95) still references `AGENT_STARTUP` and `AGENT_RECOMMEND`. The resolver implementation must output the correct variable names matching the spec. Additionally, the spec's CLI role mode section should explicitly enumerate all output variables including the new `find_work` and `auto_start` fields.
**Suggested fix:** (1) Update the shell consumer template in this companion file to use `AGENT_FIND_WORK` and `AGENT_AUTO_START`. (2) Verify the resolver implementation (`scripts/mcp/config_engine.py`) outputs these variable names when invoked in CLI role mode.
