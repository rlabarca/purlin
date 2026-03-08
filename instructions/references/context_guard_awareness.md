# Context Guard Awareness

> **Reference file.** Loaded on demand when context guard behavior needs clarification.
> Stub location: each role's base file (ARCHITECT_BASE Section 5.4, BUILDER_BASE Section 5.4, QA_BASE Section 5.4).

The Context Guard is a `PreCompact` hook that intercepts Claude Code's auto-compaction. It is invisible during normal operation -- no per-turn output, no counters, no status lines. It only activates when Claude Code is about to auto-compact context.

**How it works:**

- When Claude Code triggers **auto-compaction**, the hook blocks it (exit code 2) and sends an evacuation message via stderr.
- When Claude Code triggers **manual compaction** (user-initiated), the hook allows it (exit code 0).
- When the guard is **disabled** for the current agent (`context_guard: false`), the hook allows all compaction (exit code 0).

**Evacuation message (stderr):**

```
CONTEXT GUARD: Auto-compaction blocked. Run /pl-resume save, then /clear, then /pl-resume to continue.
```

When you see this message, stop current work immediately. Run `/pl-resume save`, then `/clear`, then `/pl-resume` to continue in a fresh context.

**Prerequisites:** Auto-compact must be enabled in Claude Code for the PreCompact hook to fire. If auto-compact is disabled, the guard has no effect.
