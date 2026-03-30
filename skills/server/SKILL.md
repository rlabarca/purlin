---
name: server
description: Dev server lifecycle management for web test verification
---

**Writes:** .purlin/runtime/dev_server.json

## Server Lifecycle Management

Manages dev server processes during web test verification. Handles port selection, state tracking, cleanup, and user visibility.

### Starting a Dev Server

1. **Check port availability:** Before starting, check if the default port is in use:
   ```bash
   lsof -i :<port> -t 2>/dev/null
   ```
2. **Select alternate port** if occupied: default + 100 (e.g., 3000 -> 3100).
3. **Start the server** using the feature's `> Web Start:` command if available.
4. **Announce to user:** `"Dev server running: http://localhost:XXXX (PID YYYY)"`

### State Tracking

Write server PID and port to `.purlin/runtime/dev_server.json`:
```json
{"pid": N, "port": N, "command": "...", "started_at": "ISO-8601"}
```

This file is gitignored (runtime artifact). Makes server state discoverable by other tools.

### Cleanup Guarantee

- **On verification complete:** Stop the server and remove `dev_server.json`.
- **On session end:** Check `.purlin/runtime/dev_server.json`, kill tracked PID if still running.
- **On session start:** Check for stale `dev_server.json`. If the tracked PID is still running from a previous session, warn: `"Stale dev server detected from previous session (port XXXX, PID YYYY)"` and ask the user whether to kill it.

### Stopping a Dev Server

1. Read `.purlin/runtime/dev_server.json`.
2. Kill the tracked PID: `kill <pid>`.
3. Remove `dev_server.json`.
4. Print: `"Dev server stopped (port XXXX)"`

### Rules

- NEVER manage persistent or production servers.
- NEVER use `kill`/`pkill` on processes not tracked in `dev_server.json`.
- Use the `> Web Start:` command from the feature spec when available.
- If the server fails to start, print a clear error with port and command.
