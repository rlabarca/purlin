# Implementation Notes: Context Guard

**[DECISION]** Complete rewrite from PostToolUse turn-counting to PreCompact auto-compaction interception. The previous implementation (~280-line hook script, 36 scenarios, counter files, session tracking, threshold math, color zones) solved the wrong problem: Claude Code already knows when context is running out and triggers auto-compaction. The new approach registers a single PreCompact hook. When auto-compaction fires, the hook blocks it (exit 2), sends an evacuation message, and the agent saves a checkpoint then prompts the user to `/clear` and `/pl-resume`. No counting, no thresholds, no per-turn display. Prior implementation artifacts (`turn_count_*`, `session_meta_*`, file locking, PID detection, color zones) are all obsolete.

**Hook registration gotcha: absolute paths required.** The hook command in `.claude/settings.json` MUST use `$CLAUDE_PROJECT_DIR` to construct an absolute path (e.g., `"$CLAUDE_PROJECT_DIR"/tools/hooks/context_guard.sh`). Relative paths fail silently when Claude Code's CWD drifts from the project root. The command quoting pattern must match the official Claude Code docs: quote just the variable (`"$CLAUDE_PROJECT_DIR"/path`), not the entire path, and omit the `bash` prefix since the script has a shebang and is executable.

**[DISCOVERY] [SPEC_PROPOSAL] PreCompact hooks cannot block compaction — spec redesign required.**

The current spec (Section 2.1) assumes exit code 2 blocks auto-compaction. This is incorrect. Per the official Claude Code hooks documentation (https://code.claude.com/docs/en/hooks.md), PreCompact is a "side effects only" event with NO decision control. Exit code 2 shows stderr to the user but compaction proceeds regardless. This is the same category as SessionEnd and Notification — logging/cleanup only. See also: https://github.com/anthropics/claude-code/issues/31845 (feature request to add decision control to PreCompact, currently open/unresolved).

**Proposed redesign** (three-layer approach from the GitHub issue's workaround pattern):

1. **PreCompact hook (mechanical save):** Instead of blocking, the hook should mechanically save a session checkpoint to `.purlin/cache/session_checkpoint_<role>.md` — the shell equivalent of what `/pl-resume save` does. This runs as a side effect before compaction proceeds. The hook should also attempt a git commit of any staged work. No agent involvement (the agent doesn't see PreCompact stderr).

2. **Post-compaction recovery:** After compaction, the agent's compacted context should include instructions to check for and restore from the checkpoint. This could use a `SessionStart` hook with matcher `compact` (if available) or rely on the agent's base instructions to detect and recover from a compacted state.

3. **Proactive clearing (soft enforcement):** Agent instructions should emphasize calling `/pl-resume save` + `/clear` + `/pl-resume` proactively before context fills up. This is the "optimal path" — the PreCompact hook is a safety net for when the agent doesn't clear proactively.

**Spec sections that need changes:**
- Section 2.1 (Hook Behavior): Remove exit code 2 blocking. Redefine as mechanical checkpoint save.
- Section 2.3 (Evacuation Message): Remove or repurpose — stderr goes to user only, not the agent.
- Section 2.4 (Hook Registration): Update matcher to empty string (match all events; script handles auto/manual internally).
- Section 3 (Scenarios): Rewrite all scenarios around the new three-layer model.
- New section needed: Post-compaction recovery mechanism (SessionStart hook or instruction-based).
