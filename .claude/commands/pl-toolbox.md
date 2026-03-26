**Purlin command: Purlin agent only**
**Purlin mode: shared**

Purlin agent: This skill is shared across all modes. List and run are available in any mode. Write operations (create, edit, copy, delete, add, pull, push) activate Engineer mode.

---

## Usage

```
/pl-toolbox                     — Guided interactive menu
/pl-toolbox list [--tag <tag>]  — Show all tools grouped by category
/pl-toolbox run <tool> [...]    — Execute one or more tools
/pl-toolbox create              — Create a new project tool
/pl-toolbox edit <tool>         — Edit a project or community tool
/pl-toolbox copy <purlin-tool>  — Copy a purlin tool to project
/pl-toolbox add <git-url>       — Download a community tool
/pl-toolbox pull [tool]         — Update community tool(s)
/pl-toolbox push <tool> [url]   — Push tool to source repo
/pl-toolbox delete <tool>       — Delete a project or community tool
```

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

## Tool Resolution

All subcommands that accept a tool name support fuzzy matching against both IDs and friendly names. Exact ID match always wins. If multiple matches, show candidates and ask the user to pick.

Registry paths:
- Purlin tools: `${TOOLS_ROOT}/toolbox/purlin_tools.json`
- Project tools: `.purlin/toolbox/project_tools.json`
- Community index: `.purlin/toolbox/community_tools.json`
- Community content: `.purlin/toolbox/community/<tool_id>/tool.json`

Use `${TOOLS_ROOT}/toolbox/resolve.py` functions for three-source resolution and fuzzy matching.

## Subcommands

### (none) — Guided Menu

Display:

```
Agentic Toolbox
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What would you like to do?

  1. List all tools           /pl-toolbox list
  2. Run tool(s)              /pl-toolbox run <name> [name2 ...]
  3. Create a new tool        /pl-toolbox create
  4. Add a community tool     /pl-toolbox add <git-url>
  5. Manage tools             /pl-toolbox edit|copy|delete
  6. Share a tool             /pl-toolbox push <tool> [git-url]

Enter a number or command:
```

Wait for user input, then execute the corresponding subcommand.

### list

Show all tools grouped by category (Purlin, Project, Community). Each tool shows id, friendly_name, and tags. Community tools show author and repo on indented lines. Omit categories with zero tools.

With `--tag <tag>`: filter to tools whose `tags` array contains the tag (case-insensitive). Header shows: `Agentic Toolbox — <N> tools matching tag "<tag>"`.

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
4. Prompt for tags (comma-separated, optional)
5. Ask for `code` (shell command, optional)
6. Ask for `agent_instructions` (natural language, optional)
7. Write to `project_tools.json` via `${TOOLS_ROOT}/toolbox/manage.py`
8. Confirm: `"Created tool '<id>' in project_tools.json."`

### edit

Resolve tool name via fuzzy matching.
- **Purlin tool:** `"Purlin tools are read-only. Use '/pl-toolbox copy <tool>' to create an editable project copy."`
- **Project tool:** Read definition, present fields for editing, write changes back.
- **Community tool:** Warn about upstream divergence, present fields for editing, write changes.

### copy

Copy a purlin tool to project for customization (Engineer mode required).
- Suggest new ID by stripping `purlin.` prefix (e.g., `purlin.verify_zero_queue` → `verify_zero_queue`)
- Copy all fields, set `metadata.last_updated` to today
- Write to `project_tools.json`
- Confirm with next-step hint: `"You can now edit it with '/pl-toolbox edit <new_id>'."`

### delete

Resolve tool name via fuzzy matching (Engineer mode required).
- **Purlin tool:** `"Purlin tools cannot be deleted. They are distributed with the framework."`
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
