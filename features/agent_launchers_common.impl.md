# Implementation Notes: Agent Launchers

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


### Launcher Config Reading
Launchers call `resolve_config.py <role>` via `eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"` to read agent settings from the resolved config. The resolver handles config.local.json / config.json resolution and outputs shell variable assignments. No `provider` field is read — Claude is implicit.

### These scripts are the standalone versions.
Submodule equivalents are produced by `tools/init.sh` (which superseded the retired `bootstrap.sh`) and follow the same structure with a submodule-specific `CORE_DIR` path.

### AGENT_ROLE Export
Each launcher exports `AGENT_ROLE` as an env var for use by config resolution and other tools.

### Model Warning Display and Auto-Acknowledge
All launchers initialize `AGENT_MODEL_WARNING=""` and `AGENT_MODEL_WARNING_DISMISSED="false"` alongside the other default variables. After the `eval` of `resolve_config.py`, a common warning block checks: if `AGENT_MODEL_WARNING` is non-empty AND `AGENT_MODEL_WARNING_DISMISSED` is not `"true"`, the warning is printed to stderr in a bordered block and then auto-acknowledged by calling `resolve_config.py acknowledge_warning <model_id>`. This ensures the warning is shown once per model, per user.
