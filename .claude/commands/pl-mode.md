**Purlin command: Purlin agent only**
**Purlin mode: shared**

Purlin agent: This skill switches the Purlin agent's operating mode, or shows current mode status when invoked with no arguments.

---

## Usage

```
/pl-mode [pm|engineer|qa]
```

## No-Argument: Status Display

When invoked with no arguments, display current mode status. No mode change, no terminal update.

1. Print the current mode: `"Current mode: <Engineer|PM|QA>"` or `"No mode active"` if in open mode.
2. Print the available skills for the current mode from `instructions/references/purlin_commands.md`:
   - If a mode is active, print that mode's skill section.
   - If no mode is active, print the Mode Quick Reference table below.
3. Print: `"Switch with /pl-mode <pm|engineer|qa>"`

## With Argument: Mode Switch

1. **Check for uncommitted work.** If the current mode has uncommitted file changes:
   - List the uncommitted files.
   - Ask: "Uncommitted [current mode] changes. Commit first?"
   - If yes, commit with mode-appropriate prefix, then switch.
   - If no, warn that changes will carry into the new mode.

2. **Activate the new mode.**
   - Print the mode's command subset from `instructions/references/purlin_commands.md`.
   - Update terminal identity per PURLIN_BASE.md section 4.1.1: badge is `<mode> (<branch>)` — e.g., `Engineer (main)`, `PM (feature-xyz)`. If `.purlin_worktree_label` exists, the worktree label replaces the branch (e.g., `Engineer (W1)`). The branch context is never dropped on mode switch.

3. **Announce:** "Switched to [Mode] mode."

## Mode Quick Reference

| Mode | Activates | Write Access |
|---|---|---|
| engineer | Build, test, release, arch anchors | Code, tests, scripts, arch_*, companions, instructions |
| pm | Spec authoring, design anchors | Feature specs, design_*, policy_* |
| qa | Verification, discovery, regression | Discovery sidecars, QA tags, regression JSON |
