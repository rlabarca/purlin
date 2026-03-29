# Agentic Toolbox Guide

How to use, create, and share project tools.

---

## What the Toolbox Is

The Agentic Toolbox is a collection of independent, reusable tools that the agent can run on demand. Each tool is a JSON definition with shell commands, natural-language instructions for the agent, or both. Tools replace the old release checklist — instead of a fixed sequence of steps, you have a library of tools you can run in any order.

```
purlin:toolbox                          # Interactive menu
purlin:toolbox list                     # See all tools
purlin:toolbox run <tool>               # Run a tool by name or ID
```

---

## Three Categories

| Category | Location | Who Manages |
|----------|----------|-------------|
| **Purlin** | Inside the Purlin plugin | Framework maintainers (read-only in consumer projects) |
| **Project** | `.purlin/toolbox/project_tools.json` | You and your team |
| **Community** | `.purlin/toolbox/community/` | Downloaded from git repos, locally editable |

When you run a tool by name, the agent searches all three registries. Project tools can shadow Purlin tools with the same ID — your version wins.

---

## Running Tools

```
purlin:toolbox run spec check           # Run by friendly name (fuzzy matched)
purlin:toolbox run purlin.spec_check    # Run by exact ID
purlin:toolbox run tool1 tool2          # Run multiple sequentially
```

The agent resolves the name against all registries. If multiple tools match, it shows candidates and asks you to pick. Exact ID match always wins over fuzzy name matching.

Each tool executes based on what it defines:

- **Agent instructions only** — the agent follows the natural-language instructions.
- **Shell code only** — the agent runs the command.
- **Both** — the agent follows the instructions, which may reference the code.

---

## Listing Tools

```
purlin:toolbox list
```

Shows all tools grouped by category with their ID and friendly name. Community tools also show author and source repo. Categories with no tools are omitted.

---

## Creating Project Tools

```
purlin:toolbox create
```

Walks you through an interactive flow (requires Engineer mode):

1. **Tool ID** — a unique identifier (no `purlin.` or `community.` prefix).
2. **Friendly name** — what shows up in `list`.
3. **Description** — one-line summary.
4. **Shell code** (optional) — a command the agent can execute.
5. **Agent instructions** (optional) — natural-language steps for the agent.

At least one of code or instructions must be provided. The tool is written to `.purlin/toolbox/project_tools.json`.

### What Makes a Good Tool

- **Self-contained.** A tool should work without setup steps that live outside it.
- **Idempotent when possible.** Running it twice shouldn't break anything.
- **Clear instructions.** If using agent instructions, write them as if for a new agent with no prior context.

---

## Customizing Purlin Tools

In consumer projects, Purlin tools are read-only (they're distributed with the plugin). To customize one:

```
purlin:toolbox copy spec_check
```

This copies the Purlin tool to your project registry with a new ID (stripping the `purlin.` prefix). You can then edit it:

```
purlin:toolbox edit spec_check
```

Your project copy shadows the original — when you run `spec_check`, your version executes.

In the Purlin framework repo itself, Purlin tools can be edited directly.

---

## Community Tools

Community tools are shared via git repos. Each repo contains a `tool.json` at its root with the standard tool fields.

### Installing

```
purlin:toolbox add https://github.com/someone/my-cool-tool.git
```

The agent clones the repo, validates `tool.json`, assigns a `community.` prefixed ID, and registers it locally.

### Updating

```
purlin:toolbox pull                     # Update all community tools
purlin:toolbox pull my-cool-tool        # Update one tool
```

If you haven't edited the tool locally, it auto-updates from upstream. If you have local edits, you're offered three options: accept upstream, keep yours, or view the diff.

### Sharing

```
purlin:toolbox push my-tool https://github.com/me/my-tool.git
```

Pushes a project tool to a git repo, converting it into a community tool others can `add`. If the tool already has a stored `source_repo`, the URL argument is optional.

---

## Deleting Tools

```
purlin:toolbox delete my-tool
```

Shows a dry-run preview before deleting. Purlin tools can't be deleted in consumer projects. Project and community tools can be deleted after confirmation.

---

## Tool Schema

Each tool definition has these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier. Prefixed `purlin.` or `community.` by category. |
| `friendly_name` | Yes | Human-readable name for display and fuzzy matching. |
| `description` | Yes | One-line summary. |
| `code` | No | Shell command to execute. |
| `agent_instructions` | No | Natural-language instructions for the agent. |
| `metadata.last_updated` | No | ISO date of last modification. |

At least one of `code` or `agent_instructions` must be non-null.

---

## Quick Reference

| You want to... | Command |
|----------------|---------|
| See all available tools | `purlin:toolbox list` |
| Run a tool | `purlin:toolbox run <name>` |
| Create a new tool | `purlin:toolbox create` |
| Customize a Purlin tool | `purlin:toolbox copy <name>` then `purlin:toolbox edit <name>` |
| Install a shared tool | `purlin:toolbox add <git-url>` |
| Update shared tools | `purlin:toolbox pull` |
| Share your tool | `purlin:toolbox push <name> <git-url>` |
| Delete a tool | `purlin:toolbox delete <name>` |
