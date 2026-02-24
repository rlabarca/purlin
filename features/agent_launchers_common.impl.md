# Implementation Notes: Agent Launchers

### Launcher Config Reading
Launchers use inline Python to parse nested JSON from config.json. The Python block is wrapped in `eval "$(python3 -c '...')"` to set shell variables. No `provider` field is read — Claude is implicit.

### These scripts are the standalone versions.
Bootstrap-generated equivalents (Section 2.3 of `submodule_bootstrap.md`) are produced by `tools/bootstrap.sh` and follow the same structure with a submodule-specific `CORE_DIR` path.
