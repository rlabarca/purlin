# Developing Purlin

This repo IS the Purlin plugin framework — and it uses Purlin to develop itself. The agent definition (`agents/purlin.md`) applies here: spec-driven development, rule-proof coverage, all of it. This CLAUDE.md provides **project-specific overrides and extensions** for developing the framework.

## Hook Authoring Rules

**Critical: PreToolUse hooks that block via exit code 2 MUST write error messages to stderr (`>&2`), not stdout.** Claude Code ignores stdout for exit-code-2 hooks — if stderr is empty, the tool call proceeds despite the non-zero exit code. Every `echo ... ; exit 2` pair in a guard script must use `echo "..." >&2`. Omitting this silently disables the guard.

**Error messages must tell the agent EXACTLY what to do.** Agents cannot infer what action to take — they will try wrong approaches unless the error message spells out the fix. Every `echo ... ; exit 2` pair in a guard script must include the exact resolution:
- Invariant file → `"Use purlin:invariant sync to update from the external source"`

When adding or modifying error paths in `gate.sh`, always include the specific corrective action.

## Format Reference Versioning

The files in `references/formats/` are **versioned contracts**. External tools, invariant authors, and consumer projects depend on them. Each format file has a `> Format-Version: N` line at the top.

**When to bump the version:**
- Adding or removing a REQUIRED field → bump
- Changing the structure (new sections, renamed sections) → bump
- Adding an OPTIONAL field → bump (consumers may need to handle it)
- Clarifying documentation, adding examples, fixing typos → do NOT bump

**Procedure when changing spec/proof/invariant parsing or emission:**
1. Make the code change (in `scripts/mcp/purlin_server.py`, `scripts/proof/`, or skill definitions)
2. Update the corresponding format file in `references/formats/` to match
3. If the change is structural (new field, removed field, changed structure): bump `> Format-Version:` by 1
4. Update `references/spec_quality_guide.md` if the change affects quality guidance
5. Grep for references to the changed format in `docs/`, `skills/`, and `agents/purlin.md` — update any that are now stale
6. Commit the format change in the SAME commit as the code change — never let them drift

**Format files and what they govern:**
- `spec_format.md` — parsed by `sync_status` (rule extraction, metadata)
- `anchor_format.md` — same parser, different naming convention
- `invariant_format.md` (v3) — parsed by `sync_status` + `purlin:invariant sync`. v2 added `> Global: true` metadata field. v3 added `> Visual-Reference:` metadata field.
- `proofs_format.md` — emitted by proof plugins, read by `sync_status`

## Tool Folder Separation

*   **`scripts/`** — Consumer-facing framework tooling. Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use.
