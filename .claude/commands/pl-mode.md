**Purlin command: Purlin agent only**
**Purlin mode: shared**

Legacy agents: This command is for the Purlin unified agent. It is not available in role-specific agent sessions.
Purlin agent: This skill switches the Purlin agent's operating mode.

---

## Usage

```
/pl-mode <pm|engineer|qa>
```

## Protocol

1. **Check for uncommitted work.** If the current mode has uncommitted file changes:
   - List the uncommitted files.
   - Ask: "Uncommitted [current mode] changes. Commit first?"
   - If yes, commit with mode-appropriate prefix, then switch.
   - If no, warn that changes will carry into the new mode.

2. **Activate the new mode.**
   - Print the mode's command subset from `instructions/references/purlin_commands.md`.
   - Update terminal identity per PURLIN_BASE.md section 4.1.1: badge is the mode name (`Engineer`, `PM`, `QA`) with worktree label appended if `.purlin_worktree_label` exists (e.g., `Engineer (W1)`).
   - Rename the session: run `/rename <ProjectName> | <Badge>` where `ProjectName` is from config `project_name` (fallback: directory basename) and `Badge` is the iTerm badge value just set.

3. **Announce:** "Switched to [Mode] mode."

## Mode Quick Reference

| Mode | Activates | Write Access |
|---|---|---|
| engineer | Build, test, release, arch anchors | Code, tests, scripts, arch_*, companions, instructions |
| pm | Spec authoring, design anchors | Feature specs, design_*, policy_* |
| qa | Verification, discovery, regression | Discovery sidecars, QA tags, regression JSON |
