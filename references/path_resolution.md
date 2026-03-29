# Path Resolution Protocol

All skills and scripts that need to locate project or plugin resources MUST use this protocol.

## Two Roots

| Root | Variable | Points to | Example |
|---|---|---|---|
| **Project root** | `PURLIN_PROJECT_ROOT` | Consumer project directory (contains `.purlin/`) | `/Users/dev/myapp` |
| **Plugin root** | `CLAUDE_PLUGIN_ROOT` | Purlin plugin installation directory | `~/.claude/plugins/purlin` |

## Resolving Project Root

1. Use `PURLIN_PROJECT_ROOT` env var if set (MCP server and hooks set this automatically).
2. Otherwise, climb from CWD until a directory containing `.purlin/` is found.

## Resolving Plugin Resources

Plugin scripts, references, and templates are at `${CLAUDE_PLUGIN_ROOT}/`:

- Scripts: `${CLAUDE_PLUGIN_ROOT}/scripts/`
- References: `${CLAUDE_PLUGIN_ROOT}/references/`
- Templates: `${CLAUDE_PLUGIN_ROOT}/templates/`
- MCP tools: Call `purlin_scan`, `purlin_config`, etc. directly (no script paths needed)

## Usage in Skills

Reference this file instead of repeating the protocol:

```
> **Path resolution:** See `references/path_resolution.md`.
```
