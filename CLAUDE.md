# Developing Purlin

This repo IS the Purlin plugin framework. Rules here apply to developing Purlin itself — not to projects that install Purlin as a plugin. Anything we want Purlin to do for other projects using it should ONLY be in `agents/purlin.md`.

## Hook Authoring Rules

**Critical: PreToolUse hooks that block via exit code 2 MUST write error messages to stderr (`>&2`), not stdout.** Claude Code ignores stdout for exit-code-2 hooks — if stderr is empty, the tool call proceeds despite the non-zero exit code. Every `echo ... ; exit 2` pair in a guard script must use `echo "..." >&2`. Omitting this silently disables the guard.

**Error messages must tell the agent EXACTLY what to do.** Agents cannot infer that "activate a mode" means calling an MCP tool — they will try sourcing shell scripts, setting env vars, or other wrong approaches. Every guard error message must include the exact fix:
- Wrong mode → `"Switch by calling the MCP tool: purlin_mode(mode: \"<correct_mode>\")"`
- No mode active → `"Activate a mode by calling the MCP tool: purlin_mode(mode: \"engineer\")"`
- Invariant file → `"Invariants are immutable — use purlin:invariant sync to update from the external source"`
- Shell write bypass → `"Use Write/Edit tools instead, or call the MCP tool: purlin_mode(mode: \"engineer\")"`

When adding or modifying error paths in `mode-guard.sh` or `bash-guard.sh`, always include the specific MCP tool call with the correct mode parameter for the file type being blocked.

## Tool Folder Separation

*   **`scripts/`** — Consumer-facing framework tooling. Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use.

