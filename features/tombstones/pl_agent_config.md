# Tombstone: pl_agent_config

> **Retired:** 2026-03-22
> **Reason:** The `/pl-agent-config` command is retired. The `qa_mode` config key (its primary remaining use case) is replaced by the `-qa` launcher flag on `pl-run-builder.sh`. Other config keys (`model`, `effort`, `find_work`, `auto_start`, `bypass_permissions`) are set directly in `.purlin/config.local.json` by the user -- no agent command needed.

## Files to Delete

- `.claude/commands/pl-agent-config.md` (the slash command definition)

## Dependencies to Check

- `instructions/QA_BASE.md` -- remove `/pl-agent-config` from authorized commands list
- `instructions/BUILDER_BASE.md` -- remove `/pl-agent-config` from authorized commands list
- `instructions/ARCHITECT_BASE.md` -- remove `/pl-agent-config` from authorized commands list
- `features/cdd_agent_configuration.md` -- no longer has `pl_agent_config` as dependent; no change needed
- `features/config_layering.md` -- no longer has `pl_agent_config` as dependent; no change needed

## Context

The `qa_mode` key was the only config value that agents toggled at runtime via `/pl-agent-config`. With `qa_mode` replaced by the `-qa` launcher flag, the command has no remaining high-value use case. The remaining config keys are stable enough to be edited manually in JSON when needed.

Consumer projects that have `pl-agent-config.md` will have it auto-removed during `pl-update-purlin` (the update process removes command files that no longer exist in the framework).
