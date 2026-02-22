# Implementation Notes: Model Configuration

## Architecture Decisions

### Claude-Only Design
Purlin targets the Claude CLI exclusively. The config schema uses a flat `models` array at the top level of `config.json` (no `llm_providers` wrapper). Each `agents.*` entry has `model`, `effort`, and `bypass_permissions` — no `provider` field.

### Launcher Config Reading
Launchers use inline Python to parse nested JSON from config.json. This avoids adding `jq` as a dependency while handling nested object access reliably. The Python block is wrapped in `eval "$(python3 -c '...')"` to set shell variables.

Reading the model for the architect role:
```python
import json,sys
c=json.load(open('.purlin/config.json'))
a=c.get('agents',{}).get('architect',{})
print(f"AGENT_MODEL={a.get('model','')}")
print(f"AGENT_EFFORT={a.get('effort','')}")
print(f"AGENT_BYPASS={str(a.get('bypass_permissions',False)).lower()}")
```

### Fallback Behavior
All launcher scripts initialize variables with sensible defaults before attempting config reads. If config.json is missing or malformed, the defaults produce the same behavior as the pre-config-driven scripts.

### Role-Specific Tool Restrictions
When `bypass_permissions` is false, each role gets a curated `--allowedTools` list:
- Architect: Read-only + git + scripting (no Write/Edit)
- Builder: No restrictions (default Claude behavior, user confirms)
- QA: Read/Write + git + scripting (can edit files for status commits)

### Bootstrap Launcher Generation
The bootstrap script generates launchers with the same config-reading logic. The generated launchers differ from the standalone ones only in the `CORE_DIR` path (uses `$SCRIPT_DIR/<submodule_name>` instead of detecting local vs submodule).

## Migration from llm_providers Schema

### Files to Delete
The provider probe infrastructure is retired. The Builder MUST delete:
- `tools/providers/claude.sh`
- `tools/providers/gemini.sh`
- `tools/providers/` directory (once all probe scripts are removed)
- `tools/detect-providers.sh`

### Config Files to Update
Both `config.json` and `purlin-config-sample/config.json` MUST be updated:
- Remove the `llm_providers` object
- Add a top-level `models` array (see Section 2.1 canonical schema)
- Remove `provider` field from each `agents.*` entry

### Test Directory to Rename
`tests/agent_configuration/` MUST be renamed to `tests/models_configuration/` to match the new feature name. The `tests.json` file inside should be preserved.
