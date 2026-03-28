# Path Resolution Protocol

All skills that need the project root or tools directory MUST use this protocol.

## Steps

1. **Resolve config:** Read `.purlin/config.local.json` if it exists, otherwise `.purlin/config.json` (local file wins, no merging). Extract `tools_root` (default: `"tools"`).
2. **Resolve project root:** Use `PURLIN_PROJECT_ROOT` env var if set. Otherwise, climb from CWD until a directory containing `.purlin/` is found.
3. **Set TOOLS_ROOT:** `TOOLS_ROOT = <project_root>/<tools_root>`.

## Usage in Skills

Reference this file instead of repeating the protocol:

```
> **Path resolution:** See `instructions/references/path_resolution.md`.
```
