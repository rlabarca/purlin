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

### 3. Execute Action

#### 3a. Start

Run via Bash: `PURLIN_PROJECT_ROOT="<project_root>" bash "<START_SCRIPT>"`

The script handles all restart logic internally (see `cdd_lifecycle.md` Section 2.9): if a server is already running, it stops the existing instance and starts fresh on the same port. Print the output from the script (restart notice if applicable, followed by URL).

If the script exits non-zero, print the error and suggest checking `.purlin/runtime/cdd.log`.

#### 3b. Stop

- Run via Bash: `PURLIN_PROJECT_ROOT="<project_root>" bash "<STOP_SCRIPT>"`
- Relay the output (either confirmation or "not running" message).

#### 3c. Restart

- Execute Stop (3b), then Start (3a) sequentially.
- Print the new URL from the start output.

---

## Notes

- The server runs in the background via `nohup` and persists after the agent session exits.
- Process detection uses `ps` -- no PID files are involved.
- `start.sh` handles restart-on-rerun internally: it detects existing instances, stops them, and restarts on the same port.
- To use a specific port manually, invoke `start.sh` directly with `-p`: `bash tools/cdd/start.sh -p 9090`
