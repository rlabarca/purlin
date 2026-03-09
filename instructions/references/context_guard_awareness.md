# Context Guard Awareness

> **Reference file.** Loaded on demand when context guard behavior needs clarification.
> Stub location: each role's base file (ARCHITECT_BASE Section 5.4, BUILDER_BASE Section 5.4, QA_BASE Section 5.4).

The Context Guard is a `PreCompact` hook that acts as a safety net when Claude Code auto-compacts context. It is invisible during normal operation -- no per-turn output, no counters, no status lines. It only activates when auto-compaction fires.

**How it works:**

The guard operates in three layers:

1. **PreCompact hook (mechanical save):** When auto-compaction fires, the hook saves a minimal checkpoint to `.purlin/cache/session_checkpoint_<role>.md` and attempts to commit any staged git changes. The hook cannot block compaction -- it runs as a side effect only.

2. **Instruction-based recovery:** After compaction, your compacted context retains these instructions. Check for a checkpoint file and restore using `/pl-resume`.

3. **Proactive clearing (recommended):** The best outcome is to clear context before auto-compaction triggers. Run `/pl-resume save`, then `/clear`, then `/pl-resume` proactively when you notice context growing large.

**When auto-compaction occurs:**

The hook saves what it can (role, branch, git status), but it has no access to your session state. For a clean recovery:
- Run `/pl-resume` to detect and restore from the checkpoint
- Resume work from where the checkpoint indicates

**When the guard is disabled** (`context_guard: false` in agent config), the hook takes no action during compaction.

**Proactive clearing workflow:**

```
/pl-resume save   →   /clear   →   /pl-resume
```

This is the optimal path. The PreCompact hook is the fallback for when you do not clear proactively.

**Prerequisites:** Auto-compact must be enabled in Claude Code for the PreCompact hook to fire. If auto-compact is disabled, the guard has no effect.
