---
name: help
description: Available to all agents and modes
---

Display the Purlin unified command table. Invoke this when the user asks "how do I run...", "what commands are available", or needs help with any Purlin command.

No side effects. Output only.

## Steps

### 1. Print Command Table

Read `${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md` and print the Default Variant verbatim.

No role detection is needed — the Purlin agent uses one unified command table showing all modes (Engineer, PM, QA) and common commands.

### 2. Done

No additional output after the command table. The plugin model has no CLI launcher scripts.
