# Implementation Notes: Agent Launchers

### Launcher Config Reading
Launchers call `resolve_config.py <role>` via `eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"` to read agent settings from the resolved config. The resolver handles config.local.json / config.json resolution and outputs shell variable assignments. No `provider` field is read — Claude is implicit.

### These scripts are the standalone versions.
Submodule equivalents are produced by `tools/init.sh` (which superseded the retired `bootstrap.sh`) and follow the same structure with a submodule-specific `CORE_DIR` path.

### AGENT_ROLE Export
Each launcher exports `AGENT_ROLE` as an env var AND writes it to `.purlin/runtime/agent_role` so that PostToolUse hooks (which don't inherit env vars from Claude Code) can read it.
