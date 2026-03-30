# Developing Purlin

This repo IS the Purlin plugin framework. Rules here apply to developing Purlin itself — not to projects that install Purlin as a plugin. Anything we want Purlin to do for other projects using it should ONLY be in `agents/purlin.md`.

## Hook Authoring Rules

**Critical: PreToolUse hooks that block via exit code 2 MUST write error messages to stderr (`>&2`), not stdout.** Claude Code ignores stdout for exit-code-2 hooks — if stderr is empty, the tool call proceeds despite the non-zero exit code. Every `echo ... ; exit 2` pair in a guard script must use `echo "..." >&2`. Omitting this silently disables the guard.

## Tool Folder Separation

*   **`scripts/`** — Consumer-facing framework tooling. Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use.

