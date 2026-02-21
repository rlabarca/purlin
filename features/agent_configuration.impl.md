# Implementation Notes: Agent Configuration

## Architecture Decisions

### Provider-Agnostic Design
The config schema separates provider/model definitions (`llm_providers`) from agent assignments (`agents`). This allows adding new providers without touching agent config structure.

### Probe Script Contract
Each provider probe script at `tools/providers/<provider>.sh` outputs JSON to stdout and always exits 0. This simplifies the aggregator -- it only needs to check for valid JSON output, not exit codes.

### Launcher Config Reading
Launchers use inline Python to parse nested JSON from config.json. This avoids adding `jq` as a dependency while handling nested object access reliably. The Python block is wrapped in `eval "$(python3 -c '...')"` to set shell variables.

### Fallback Behavior
All launcher scripts initialize variables with sensible defaults before attempting config reads. If config.json is missing or malformed, the defaults produce the same behavior as the pre-config-driven scripts.

### Role-Specific Tool Restrictions
When `bypass_permissions` is false, each role gets a curated `--allowedTools` list:
- Architect: Read-only + git + scripting (no Write/Edit)
- Builder: No restrictions (default Claude behavior, user confirms)
- QA: Read/Write + git + scripting (can edit files for status commits)

### Bootstrap Launcher Generation
The bootstrap script generates launchers with the same config-reading logic. The generated launchers differ from the standalone ones only in the `CORE_DIR` path (uses `$SCRIPT_DIR/<submodule_name>` instead of detecting local vs submodule).
