# Implementation Notes: Config Layering

## Consumer Inventory

### Python Consumers (import `resolve_config`)

| File | Current Pattern | Migration |
|------|----------------|-----------|
| `tools/cdd/serve.py` | `json.load(open(...config.json...))` | `from tools.config.resolve_config import resolve_config; config = resolve_config(project_root)` |
| `tools/critic/critic.py` | `json.load()` with try/except fallback | Replace with `resolve_config()` import |
| `tools/critic/resolve.py` | `json.load()` with try/except fallback | Replace with `resolve_config()` import |
| `tools/release/manage_step.py` | `json.load()` on config path | Replace with `resolve_config()` import |
| `tools/collab/extract_whats_different.py` | `json.load()` on config path | Replace with `resolve_config()` import |

All Python consumers follow the Section 2.13 safe-read pattern (`try/except` with fallback defaults). The resolver centralizes this -- individual consumers no longer need their own error handling for config reads.

### Shell Consumers (call `resolve_config.py` CLI)

| File | Current Pattern | Migration |
|------|----------------|-----------|
| `run_architect.sh` | `python3 -c "import json; ..."` inline | `eval $(python3 tools/config/resolve_config.py architect)` |
| `run_builder.sh` | `python3 -c "import json; ..."` inline | `eval $(python3 tools/config/resolve_config.py builder)` |
| `run_qa.sh` | `python3 -c "import json; ..."` inline | `eval $(python3 tools/config/resolve_config.py qa)` |
| `tools/cdd/start.sh` | `python3 -c "import json; ..."` for port | `CDD_PORT=$(python3 tools/config/resolve_config.py --key cdd_port)` |
| `tools/cdd/context_guard.sh` | `python3 -c "import json; ..."` | Replace with `resolve_config.py --key` calls |

### Writers

| Component | Current Target | New Target | Notes |
|-----------|---------------|------------|-------|
| `/pl-agent-config` skill | `config.json` + git commit | `config.local.json`, no commit | Commit step removed (gitignored file) |
| `POST /config/agents` (serve.py) | `config.json` | `config.local.json` | Propagation targets local in worktrees too |
| `GET /config.json` (serve.py) | Reads `config.json` | Reads via resolver (local priority) | Transparent to dashboard frontend |
| `bootstrap.sh` | Creates `config.json` | Creates `config.json` only (unchanged) | Adds `config.local.json` to gitignore |

## Phased Implementation Order

### Phase 1: Foundation
1. Create `tools/config/resolve_config.py` with `resolve_config()`, `sync_config()`, and CLI modes.
2. Create `tools/config/__init__.py` (empty, for Python imports).
3. Write unit tests for the resolver (`tests/config_layering/`).

### Phase 2: Reader Migration
4. Update Python consumers (5 files) to import and use `resolve_config()`.
5. Update shell consumers (4-5 files) to call `resolve_config.py` CLI.
6. Verify all readers produce identical behavior to before (same config values returned).

### Phase 3: Writer Updates
7. Update `serve.py` `POST /config/agents` to write to `config.local.json`.
8. Update `serve.py` `GET /config.json` to serve via resolver.
9. Update `/pl-agent-config` command file to target `config.local.json` and remove commit step.
10. Update worktree propagation in `serve.py` to target `config.local.json`.

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
from tools.config.resolve_config import resolve_config
config = resolve_config(project_root)
```

### Shell (before)
```bash
AGENT_MODEL=$(python3 -c "
import json, sys
try:
    cfg = json.load(open('$CONFIG_PATH'))
    print(cfg.get('agents', {}).get('$ROLE', {}).get('model', 'claude-sonnet-4-6'))
except: print('claude-sonnet-4-6')
")
```

### Shell (after)
```bash
eval $(python3 "$TOOLS_ROOT/config/resolve_config.py" "$ROLE")
# Now AGENT_MODEL, AGENT_EFFORT, AGENT_BYPASS, AGENT_STARTUP, AGENT_RECOMMEND are set
```

## Test Update Inventory

Existing tests that reference `config.json` directly may need updates:

- `tools/test_bootstrap.sh` -- Verify it checks `config.json` creation (shared template) but NOT `config.local.json` creation.
- `tests/cdd_agent_configuration/` -- Tests that verify config writes must target `config.local.json`.
- `tests/pl_agent_config/` -- Tests must verify writes to `config.local.json` and absence of git commits.

New test directory: `tests/config_layering/` for resolver unit tests covering all 24 scenarios.

## Resolver Project Root Detection

The resolver uses `PURLIN_PROJECT_ROOT` as the primary detection mechanism. When not set, it climbs from its own `__file__` location:
- Standalone: `tools/config/resolve_config.py` -> climb 2 levels -> project root
- Submodule: `<submodule>/tools/config/resolve_config.py` -> climb 3 levels -> project root (detected by presence of `.purlin/` directory)

This follows the same submodule-aware climbing pattern established in Section 2.11 of `submodule_bootstrap.md`.
