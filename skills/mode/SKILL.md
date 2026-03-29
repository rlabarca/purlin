---
name: mode
description: This skill switches the Purlin agent's operating mode, or shows current mode status when invoked with no arguments
---

## Usage

```
purlin:mode [pm|engineer|qa]
```

## No-Argument: Status Display

When invoked with no arguments, display current mode status. No mode change, no terminal update.

1. Print the current mode: `"Current mode: <Engineer|PM|QA>"` or `"No mode active"` if in open mode.
2. Print the available skills for the current mode from `${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`:
   - If a mode is active, print that mode's skill section.
   - If no mode is active, print the Mode Quick Reference table below.
3. Print: `"Switch with purlin:mode <pm|engineer|qa>"`

## With Argument: Mode Switch

1. **Check for uncommitted work.** If the current mode has uncommitted file changes:
   - List the uncommitted files.
   - Ask: "Uncommitted [current mode] changes. Commit first?"
   - If yes, commit with mode-appropriate prefix, then switch.
   - If no, warn that changes will carry into the new mode.

2. **Companion file gate (Engineer mode exit only).** When switching OUT of Engineer mode:
   - Check: were code commits made for any feature during this session without a corresponding companion file update?
   - If companion debt exists: **BLOCK the switch.** List the features with debt. There is no "skip" option.
   - The engineer MUST write at least `[IMPL]` entries for each feature with debt before the switch proceeds.
   - This is a mechanical check (did the companion file get new entries?), not a judgment call about deviation.

3. **Activate the new mode.**
   - Print the mode's command subset from `${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`.
   - Update terminal identity: `source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<mode>" "<project>"`. This sets the unified format `<short_mode>(<branch>) | <project>` — e.g., `Eng(main) | purlin`, `PM(feature-xyz) | purlin`. Worktree label replaces branch when present (e.g., `Eng(W1) | purlin`). Branch context is never dropped.

4. **Announce:** "Switched to [Mode] mode."

## Mode Quick Reference

| Mode | Activates | Write Access |
|---|---|---|
| engineer | Build, test, release, arch anchors | Code, tests, scripts, arch_*, companions, instructions |
| pm | Spec authoring, design anchors | Feature specs, design_*, policy_* |
| qa | Verification, discovery, regression | Discovery sidecars, QA tags, regression JSON |

## Internal Mode Switches

`purlin:verify` Phase A.5 (auto-fix iteration loop) performs internal write-boundary toggles between QA and Engineer without invoking `purlin:mode`. These internal switches preserve mode guard enforcement but skip terminal badge updates and user-facing prompts. See the `purlin:verify` skill for the full protocol.
