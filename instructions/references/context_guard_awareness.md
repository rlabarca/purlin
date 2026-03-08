# Context Guard Awareness

> **Reference file.** Loaded on demand when the context budget message format needs clarification.
> Stub location: each role's base file (ARCHITECT_BASE Section 5.4, BUILDER_BASE Section 5.4, QA_BASE Section 5.4).

The `PostToolUse` hook displays a context budget message after every tool call:

- **Normal:** `CONTEXT GUARD: X / Y used` -- X is turns consumed, Y is the configured threshold. Higher X means closer to the limit.
- **Exceeded:** `CONTEXT GUARD: X / Y used -- Run /pl-resume save, then /clear, then /pl-resume to continue.` -- X has reached or passed Y. Save your work immediately.

When you see the exceeded message, stop current work, run `/pl-resume save`, then `/clear`, then `/pl-resume` to continue in a fresh context.
