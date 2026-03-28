---
name: help
description: Available to all agents and modes
---

**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

Display the Purlin unified command table and list available CLI launcher scripts. Invoke this when the user asks "how do I run...", "what commands are available", or needs help with any Purlin command.

No side effects. Output only.

## Steps

### 1. Print Command Table

Read `${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md` and print the Default Variant verbatim.

No role detection is needed — the Purlin agent uses one unified command table showing all modes (Engineer, PM, QA) and common commands.

### 2. List CLI Scripts

1. Determine project root: use `$PURLIN_PROJECT_ROOT` if set, else `git rev-parse --show-toplevel`.
2. Glob `pl-*.sh` in the project root.
3. After the slash command table, print:

```
---

## CLI Scripts (run from terminal)
```

4. List each discovered script by filename (e.g., `pl-run.sh`). Do NOT attempt to run the scripts or fetch `--help` output.
5. If no `pl-*.sh` scripts were found in the project root, print: `(no CLI scripts found in project root)`
