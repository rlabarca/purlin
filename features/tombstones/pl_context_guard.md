# TOMBSTONE: pl_context_guard

**Retired:** 2026-03-08
**Reason:** The `/pl-context-guard` skill toggled the Context Guard feature, which is being retired entirely. With the guard removed, the toggle skill has no purpose.

## Files to Delete

- `.claude/commands/pl-context-guard.md` -- entire file (slash command definition)
- `tools/hooks/test_pl_context_guard.sh` -- entire file (skill test script)
- `tests/pl_context_guard/tests.json` -- entire file (test definitions)

## Dependencies to Check

- `features/cdd_agent_configuration.md` -- referenced context guard checkbox (already cleaned by Architect).
- `features/config_layering.md` -- referenced `tools/cdd/context_guard.sh` in config consumers (already cleaned by Architect).

## Context

The `/pl-context-guard` skill provided `status` and `on`/`off` subcommands to view and toggle the per-agent `context_guard` boolean in `config.local.json`. It followed the same config-write protocol as `/pl-agent-config` (copy-on-first-access, atomic write, gitignored local config). With the Context Guard feature retired, this skill is no longer needed. The `context_guard` key is also being removed from all config files.
