# Implementation Notes: Context Guard

**[DECISION] v1 rewrite: turn-counting to PreCompact interception.** The original implementation (~280-line hook script, 36 scenarios, counter files, session tracking, threshold math, color zones) solved the wrong problem: Claude Code already knows when context is running out and triggers auto-compaction. Prior implementation artifacts (`turn_count_*`, `session_meta_*`, file locking, PID detection, color zones) are all obsolete.

**[DECISION] v2 rewrite: blocking model to mechanical-save model.** The v1 PreCompact spec assumed exit code 2 could block auto-compaction. This is incorrect. PreCompact is a "side effects only" event -- same category as SessionEnd and Notification. Exit code 2 shows stderr to the user but compaction proceeds regardless. The v2 spec redesigns around a three-layer model: mechanical save, instruction-based recovery, proactive clearing.

**[DISCOVERY] PreCompact cannot block compaction.** Per the official Claude Code hooks docs, PreCompact has NO decision control. Only PreToolUse and PermissionRequest support blocking via exit code 2. See: https://github.com/anthropics/claude-code/issues/31845 (open feature request for PreCompact decision control).

**[DISCOVERY] SessionStart "compact" matcher is unreliable.** There is a known bug (GitHub issue #15174) where SessionStart hook output is not injected into Claude's context after compaction. Post-compaction recovery cannot rely on hooks -- it must be instruction-based. The agent's compacted context retains base instructions which direct checkpoint recovery via `/pl-resume`.

**[DISCOVERY] PreCompact stderr is not preserved.** Stderr from PreCompact hooks is briefly visible to the user in the terminal but is NOT included in the compacted context. The agent never sees it. This means the evacuation message pattern (stderr -> agent reads -> agent acts) is fundamentally broken. The v2 design eliminates this dependency.

**Hook registration: absolute paths required.** The hook command in `.claude/settings.json` MUST use `$CLAUDE_PROJECT_DIR` to construct an absolute path (e.g., `"$CLAUDE_PROJECT_DIR"/tools/hooks/context_guard.sh`). Relative paths fail silently when Claude Code's CWD drifts from the project root. Quote just the variable (`"$CLAUDE_PROJECT_DIR"/path`), not the entire path, and omit the `bash` prefix since the script has a shebang and is executable.

**Checkpoint is intentionally minimal.** The hook-written checkpoint only contains role, timestamp, branch, and git status. It cannot capture work-in-progress details because the hook has no access to the agent's session state. The agent's own `/pl-resume save` produces the rich checkpoint. The hook checkpoint serves as a signal that compaction occurred plus basic git context for recovery.

**[DISCOVERY] Checkpoint filenames must be unique per agent instance.** Multiple agents of the same role can run concurrently (e.g., two Builder sessions in different worktrees). The checkpoint filename uses `session_checkpoint_<role>_<ppid>.md` where PPID is the parent process ID (the Claude Code session). This ensures concurrent agents don't overwrite each other's checkpoints. The `/pl-resume` command should glob for `session_checkpoint_<role>_*.md` and use the most recent match by modification time.
