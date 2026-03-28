---
name: toolbox
description: This skill is shared across all modes. List and run are available in any mode. Write operations (create, edit, copy, ...
---

**Purlin command: Purlin agent only**
**Purlin mode: shared**

Purlin agent: This skill is shared across all modes. List and run are available in any mode. Write operations (create, edit, copy, delete, add, pull, push) activate Engineer mode.

---

## Usage

```
purlin:toolbox                     — Guided interactive menu
purlin:toolbox list                — Show all tools grouped by category
purlin:toolbox run <tool> [...]    — Execute one or more tools
purlin:toolbox create              — Create a new project tool
purlin:toolbox edit <tool>         — Edit a project or community tool
purlin:toolbox copy <purlin-tool>  — Copy a purlin tool to project
purlin:toolbox add <git-url>       — Download a community tool
purlin:toolbox pull [tool]         — Update community tool(s)
purlin:toolbox push <tool> [url]   — Push tool to source repo
purlin:toolbox delete <tool>       — Delete a project or community tool
```

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.

## Tool Resolution

All subcommands that accept a tool name support fuzzy matching against both IDs and friendly names. Exact ID match always wins. If multiple matches, show candidates and ask the user to pick.

Registry paths:
- Purlin tools: `${CLAUDE_PLUGIN_ROOT}/scripts/toolbox/purlin_tools.json`
- Project tools: `.purlin/toolbox/project_tools.json`
- Community index: `.purlin/toolbox/community_tools.json`
- Community content: `.purlin/toolbox/community/<tool_id>/tool.json`

Use `${CLAUDE_PLUGIN_ROOT}/scripts/toolbox/resolve.py` functions for three-source resolution and fuzzy matching.

## Subcommands

### (none) — Guided Menu

Display:

```
Agentic Toolbox
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What would you like to do?

  1. List all tools           purlin:toolbox list
  2. Run tool(s)              purlin:toolbox run <name> [name2 ...]
  3. Create a new tool        purlin:toolbox create
  4. Add a community tool     purlin:toolbox add <git-url>
  5. Manage tools             purlin:toolbox edit|copy|delete
  6. Share a tool             purlin:toolbox push <tool> [git-url]

Enter a number or command:
```

Wait for user input, then execute the corresponding subcommand.

### list

Show all tools grouped by category (Purlin, Project, Community). Each tool shows id and friendly_name. Community tools show author and repo on indented lines. Omit categories with zero tools.

### run

Execute one or more tools by name. Multiple tools run sequentially.

Execution logic per tool:
- `agent_instructions` non-null → follow those instructions
- `code` non-null and `agent_instructions` null → execute the shell command
- Both non-null → follow `agent_instructions` (may reference `code`)
- Both null → error: `"Tool '<id>' has no instructions or code to execute."`

### create

Interactive flow (Engineer mode required):
1. Prompt for tool ID (validate: non-empty, no `purlin.` or `community.` prefix, no collision)
2. Prompt for friendly name
3. Prompt for description
4. Ask for `code` (shell command, optional)
5. Ask for `agent_instructions` (natural language, optional)
7. Write to `project_tools.json` via `${CLAUDE_PLUGIN_ROOT}/scripts/toolbox/manage.py`
8. Confirm: `"Created tool '<id>' in project_tools.json."`

### edit

Resolve tool name via fuzzy matching.
- **Purlin tool (submodule context):** `"Purlin tools are read-only in consumer projects. Use 'purlin:toolbox copy <tool>' to create an editable project copy."` Detect submodule context: run `git -C "${CLAUDE_PLUGIN_ROOT}/scripts" rev-parse --show-superproject-working-tree 2>/dev/null` — if non-empty, tools are inside a submodule.
- **Purlin tool (framework repo):** Allow editing. Read definition from `purlin_tools.json`, present fields for editing, write changes back.
- **Project tool:** Read definition, present fields for editing, write changes back.
- **Community tool:** Warn about upstream divergence, present fields for editing, write changes.

### copy

Copy a purlin tool to project for customization (Engineer mode required).
- Suggest new ID by stripping `purlin.` prefix (e.g., `purlin.verify_zero_queue` → `verify_zero_queue`)
- Copy all fields, set `metadata.last_updated` to today
- Write to `project_tools.json`
- Confirm with next-step hint: `"You can now edit it with 'purlin:toolbox edit <new_id>'."`

### delete

Resolve tool name via fuzzy matching (Engineer mode required).
- **Purlin tool (submodule context):** `"Purlin tools cannot be deleted in consumer projects. They are distributed with the framework."` (Same submodule detection as edit — `git rev-parse --show-superproject-working-tree`.)
- **Purlin tool (framework repo):** Allow deletion. Show dry-run preview, confirm, then remove from `purlin_tools.json`.
- **Project tool:** Show dry-run preview, confirm, then remove from `project_tools.json`.
- **Community tool:** Show preview (registry entry + directory), confirm, then remove.

### add, pull, push

See `features/toolbox_community.md` for the full community tool lifecycle. Key behaviors:
- **add**: Clone repo, validate `tool.json`, register in `community_tools.json`, copy to `.purlin/toolbox/community/<tool_id>/`
- **pull**: Check upstream for changes, auto-update if no local edits, offer three options if local edits exist
- **push**: Use stored `source_repo` if available. If no repo stored (project tool), `git-url` arg is required. Shows dry-run preview before executing.

## Error Handling

All error messages suggest a recovery path:
- Edit purlin tool → suggests `copy`
- Delete purlin tool → explains why
- Reserved prefix → names the prefix
- Network failure → confirms no state modified
- Missing tool.json in repo → explains requirement
- Ambiguous match → shows candidates
- Tool not found → suggests `list`
- Push without repo → shows required syntax
- No instructions or code → explains tool is empty
