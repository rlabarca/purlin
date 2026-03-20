# Implementation Notes: Model Configuration

## Architecture Decisions

### Claude-Only Design
Purlin targets the Claude CLI exclusively. The config schema uses a flat `models` array at the top level of `config.json` (no `llm_providers` wrapper). Each `agents.*` entry has `model`, `effort`, and `bypass_permissions` — no `provider` field.

### Launcher Config Reading
Launchers call `resolve_config.py <role>` via `eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"` to read agent settings from the resolved config. The resolver handles config.local.json / config.json resolution and outputs shell variable assignments (`AGENT_MODEL`, `AGENT_EFFORT`, `AGENT_BYPASS`, `AGENT_FIND_WORK`, `AGENT_AUTO_START`). No `provider` field is read — Claude is implicit. Inline `python3 -c "import json; ..."` patterns for config reading are prohibited by the spec.

### Fallback Behavior
All launcher scripts initialize variables with sensible defaults before attempting config reads. If config.json is missing or malformed, the defaults produce the same behavior as the pre-config-driven scripts.

### Role-Specific Tool Restrictions
When `bypass_permissions` is false, each role gets a curated `--allowedTools` list:
- Architect: Read-only + git + scripting (no Write/Edit)
- Builder: No restrictions (default Claude behavior, user confirms)
- QA: Read/Write + git + scripting (can edit files for status commits)

### Bootstrap Launcher Generation
The bootstrap script generates launchers with the same config-reading logic. The generated launchers differ from the standalone ones only in the `CORE_DIR` path (uses `$SCRIPT_DIR/<submodule_name>` instead of detecting local vs submodule).

## Model Warning Support

### Warning Output in resolve_config.py
The `_cli_role()` function outputs two additional shell variables: `AGENT_MODEL_WARNING` (the warning text from the model's `warning` field, empty if absent) and `AGENT_MODEL_WARNING_DISMISSED` (`"true"` only when the model ID is in `acknowledged_warnings` AND `warning_dismissible` is `true`; `"false"` otherwise). Non-dismissible warnings (`warning_dismissible: false`) always report `AGENT_MODEL_WARNING_DISMISSED="false"` regardless of `acknowledged_warnings`.

### acknowledge_warning Subcommand
`resolve_config.py acknowledge_warning <model_id>` adds a model ID to the `acknowledged_warnings` array in `config.local.json` (creating the array if absent). The operation is idempotent (duplicate calls do not create duplicate entries). The write is atomic (temp file + `os.replace`).

## Migration from llm_providers Schema (COMPLETED)

All migration work is done: `llm_providers` wrapper removed, provider probe scripts deleted (`tools/providers/`, `tools/detect-providers.sh`), config files updated to flat `models` array, `provider` fields removed from agent entries, and test directory renamed to `tests/models_configuration/`.
