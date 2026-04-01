# Developing Purlin

This repo IS the Purlin plugin framework — and it uses Purlin to develop itself. The full Purlin protocol (`agents/purlin.md`) applies here: spec-driven development, sync tracking, skill workflows, commit conventions, all of it. This CLAUDE.md provides **project-specific overrides and extensions** for developing the framework. It does NOT replace or suppress the Purlin protocol.

## Hook Authoring Rules

**Critical: PreToolUse hooks that block via exit code 2 MUST write error messages to stderr (`>&2`), not stdout.** Claude Code ignores stdout for exit-code-2 hooks — if stderr is empty, the tool call proceeds despite the non-zero exit code. Every `echo ... ; exit 2` pair in a guard script must use `echo "..." >&2`. Omitting this silently disables the guard.

**Error messages must tell the agent EXACTLY what to do.** Agents cannot infer what action to take — they will try wrong approaches unless the error message spells out the fix. Every `echo ... ; exit 2` pair in a guard script must include the exact resolution:
- Invariant file → `"Use purlin:invariant sync to update from the external source"`
- Unknown file → `"Add a rule to CLAUDE.md under '## Purlin File Classifications': \`path/\` → CODE (or SPEC)"`

When adding or modifying error paths in `write-guard.sh`, always include the specific corrective action.

## Purlin File Classifications
- `docs/` → SPEC
- `references/` → CODE
- `RELEASE_NOTES.md` → CODE
- `PLAN-` → CODE
- `PURLIN_REVAMP.md` → CODE

## Tool Folder Separation

*   **`scripts/`** — Consumer-facing framework tooling. Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use.

