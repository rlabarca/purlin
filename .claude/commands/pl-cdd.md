Start, stop, or restart the CDD Dashboard server. Prints the full clickable URL on start. The server persists after the agent session exits.

**Owner: All roles** (shared skill)

## Usage

```
/pl-cdd              # Start (or restart if already running)
/pl-cdd stop         # Stop the server
/pl-cdd restart      # Stop then start
```

**Examples:**
```
/pl-cdd
/pl-cdd stop
/pl-cdd restart
```

---

## Steps

### 1. Resolve Paths

Read `.purlin/config.json` and extract `tools_root` (default: `tools`).

Resolve the project root:
- Use `PURLIN_PROJECT_ROOT` env var if set and `.purlin/` exists there.
- Otherwise, detect from the current working directory by climbing until `.purlin/` is found.

Set:
- `TOOLS_ROOT` = `<project_root>/<tools_root>`
- `START_SCRIPT` = `<TOOLS_ROOT>/cdd/start.sh`
- `STOP_SCRIPT` = `<TOOLS_ROOT>/cdd/stop.sh`

### 2. Parse Argument

Parse the argument from `$ARGUMENTS`:
- **No argument or empty:** Action is `start`.
- **`stop`:** Action is `stop`.
- **`restart`:** Action is `restart`.
- **Anything else:** Abort with: `Error: Unknown argument '<arg>'. Valid: stop, restart`

### 3. Detect Running Instance

Run:
```bash
ps aux | grep "[s]erve.py" | grep -- "--project-root"
```

Check if the output contains a line matching the current project root. If it does, a CDD server is already running for this project.

### 4. Execute Action

#### 4a. Start

If already running:
- Read the current port from `.purlin/runtime/cdd.port` and save it as `PREFERRED_PORT`.
- Stop the existing instance: Run via Bash: `PURLIN_PROJECT_ROOT="<project_root>" bash "<STOP_SCRIPT>"`
- Start a new instance with port preference: Run via Bash: `PURLIN_PROJECT_ROOT="<project_root>" bash "<START_SCRIPT>" -p <PREFERRED_PORT>`
- If the start fails (non-zero exit, e.g., preferred port still held by OS), retry without `-p` to let the OS assign a new port.
- Print the URL from the start output.

If not running:
- Run via Bash: `PURLIN_PROJECT_ROOT="<project_root>" bash "<START_SCRIPT>"`
- The script prints the URL on success. Relay the output.
- If the script exits non-zero, print the error and suggest checking `.purlin/runtime/cdd.log`.

#### 4b. Stop

- Run via Bash: `PURLIN_PROJECT_ROOT="<project_root>" bash "<STOP_SCRIPT>"`
- Relay the output (either confirmation or "not running" message).

#### 4c. Restart

- Execute Stop (4b), then Start (4a) sequentially.
- Print the new URL from the start output.

---

## Notes

- The server runs in the background via `nohup` and persists after the agent session exits.
- Process detection uses `ps` -- no PID files are involved.
- When restarting an already-running server, the skill reads the current port from `cdd.port` and passes it via `-p` to preserve the URL across restarts.
- If the preferred port is unavailable after stop (OS still holding it), the skill retries without `-p` for an OS-assigned port.
- To use a specific port manually, invoke `start.sh` directly with `-p`: `bash tools/cdd/start.sh -p 9090`
