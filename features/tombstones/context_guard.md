# TOMBSTONE: context_guard

**Retired:** 2026-03-08
**Reason:** Context Guard provides no effective protection -- the PreCompact hook cannot block compaction, the agent never sees the evacuation message, and proactive clearing has no trigger mechanism. Claude Code's built-in auto-compaction with context summarization is more effective than the minimal checkpoint the hook saves.

## Files to Delete

- `tools/hooks/context_guard.sh` -- entire file (PreCompact hook script)
- `tools/hooks/test_context_guard.sh` -- entire file (hook test script)
- `tests/context_guard/tests.json` -- entire file (test definitions)
- `.claude/commands/pl-context-guard.md` -- entire file (slash command; also listed in pl_context_guard tombstone)

## Files to Modify

- `.claude/settings.json` -- remove entire PreCompact hook registration (the `hooks.PreCompact` entry referencing `context_guard.sh`). If no other hooks remain, the file becomes `{}` or is deleted.
- `tools/cdd/serve.py` -- remove context_guard checkbox rendering, JavaScript event handlers for context guard toggle, and any validation logic specific to `context_guard`.
- `tools/cdd/test_cdd_model_configuration.py` -- remove test references to `context_guard` (assertions, fixtures, expected values).
- `tools/config/resolve_config.py` -- remove any `context_guard`-specific logic if present (check before modifying).

## Dependencies to Check

- `features/cdd_agent_configuration.md` -- had `context_guard.md` as a prerequisite and context guard scenarios (already cleaned by Architect in this removal).
- `features/config_layering.md` -- referenced `tools/cdd/context_guard.sh` in config consumers list (already cleaned by Architect).

## Context

The Context Guard was a three-layer safety net for auto-compaction: (1) a PreCompact hook that saved a minimal checkpoint, (2) instruction-based recovery directing agents to restore from the checkpoint, and (3) proactive clearing as the recommended path. In practice, none of these layers worked effectively: the hook cannot prevent compaction (exit code 2 just shows stderr), agents never see the evacuation message after compaction, and proactive clearing had no trigger mechanism. Claude Code's built-in auto-compaction with context summarization provides better protection than the minimal checkpoint (role, timestamp, branch, git status) the hook saved. The feature is being replaced with a preventive approach: enhancing phased delivery to help the Builder plan work that fits within context limits.
