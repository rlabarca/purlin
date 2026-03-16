# Feature: CDD Lifecycle Management

> Label: "CDD: Lifecycle"
> Category: "CDD Dashboard"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/config_layering.md
> AFT Web: http://localhost:9086
> AFT Start: /pl-cdd

[TODO]

## 1. Overview

Stateless, self-managing process lifecycle for the CDD Dashboard server. The server auto-selects a port, detects its own running state via the OS process list (no PID files), prints a clickable URL on start, and refuses to launch duplicate instances. This replaces the previous PID-file-based lifecycle and `cdd_port` config key with a simpler, more robust model.

---

## 2. Requirements

### 2.1 Stateless Process Detection

- `serve.py` accepts a `--project-root <path>` CLI argument (in addition to the existing `PURLIN_PROJECT_ROOT` env var). When provided, the argument sets `PURLIN_PROJECT_ROOT` internally. This makes the project root visible in `ps` output for per-project process detection.
- Detection command pattern: `ps aux | grep "[s]erve.py" | grep -- "--project-root $PROJECT_ROOT"`
- No PID file is written or read. The file `.purlin/runtime/cdd.pid` is eliminated entirely from `start.sh`, `stop.sh`, and any other script that references it.
- Process liveness is always determined by `ps` output, never by file existence.

### 2.2 Auto Port Selection

Port is determined by a priority chain:

1. **Already running:** If a CDD process for this project is found in `ps`, reuse the port read from `.purlin/runtime/cdd.port`. Do not start a new instance.
2. **`-p` flag:** If the user passes `-p <port>` to `start.sh`, use that port exactly.
3. **OS-assigned free port:** When neither (1) nor (2) applies, `serve.py` binds to port 0 via `socket.bind(('', 0))` and lets the OS assign a free port.

The `cdd_port` config key is **removed entirely** from `.purlin/config.json`, `purlin-config-sample/config.json`, and all config resolution logic in `start.sh` and `serve.py`. Port is now either auto-selected or explicitly set via the `-p` flag.

### 2.3 Port File

- `serve.py` writes the bound port number to `.purlin/runtime/cdd.port` as a single integer on one line, immediately after binding and before entering `serve_forever()`.
- This file is a **cache for the URL** -- it is NOT a state file. Process liveness is always checked via `ps` (Section 2.1).
- If the port file exists but no matching process is found in `ps`, the file is stale. `start.sh` deletes the stale file and proceeds with a fresh start.

### 2.4 Start Script (`start.sh`) Changes

The start script follows this sequence:

1. **Check for existing instance:** Query `ps` for a running `serve.py` with `--project-root "$PROJECT_ROOT"`. If found, read the port from `.purlin/runtime/cdd.port`, print the URL, and exit 0 (idempotent start).
2. **Clean stale port file:** If `.purlin/runtime/cdd.port` exists but no matching process is running, delete the stale file.
3. **Launch:** Start `serve.py` via `nohup` with `--project-root "$PROJECT_ROOT"`. If the user passed `-p <port>`, also pass `--port <port>` to `serve.py`.
4. **Wait and verify:** Wait briefly (up to 2 seconds), then verify the process is running via `ps` and read the port from `.purlin/runtime/cdd.port`.
5. **Print URL:** Output the full clickable URL: `http://localhost:<port>`
6. **Remove all PID file writes.** No `cdd.pid` is created.
7. **Remove all `cdd_port` config resolution logic.** The config resolver call for `cdd_port` is deleted.

### 2.5 Stop Script (`stop.sh`) Changes

1. **Detect process:** Query `ps` for a running `serve.py` with `--project-root "$PROJECT_ROOT"`. Extract the PID from the `ps` output.
2. **Kill:** Send SIGTERM to the extracted PID. If the process does not exit within 2 seconds, send SIGKILL.
3. **Clean up:** Remove `.purlin/runtime/cdd.port` if it exists.
4. **No PID file read.** The script does not reference `cdd.pid`.
5. **Idempotent stop:** If no matching process is found, print a "not running" message and exit 0.

### 2.6 `serve.py` CLI Argument Changes

- **Add `--project-root <path>`:** When provided, sets `PURLIN_PROJECT_ROOT` internally (equivalent to the env var). This argument's primary purpose is to make the project root visible in `ps aux` output for process detection.
- **Add `--port <port>`:** When provided, bind to this exact port. Only passed when the user provides `-p` to `start.sh`.
- **Auto port when `--port` is omitted:** Use `socket.bind(('', 0))` to let the OS assign a free port. Retrieve the assigned port via `socket.getsockname()[1]`.
- **Remove `cdd_port` config resolution:** The `resolve_port()` function (or equivalent) no longer reads `cdd_port` from config. Port comes exclusively from `--port` or auto-selection.
- **Write port file:** After binding, write the chosen port number to `.purlin/runtime/cdd.port` (single integer, one line) before entering `serve_forever()`.

### 2.7 URL Output

- `start.sh` prints the full clickable URL on successful start: `http://localhost:<port>`
- The output line is clean and copy-paste friendly -- no surrounding decoration that would break URL selection in a terminal.
- On idempotent start (already running), the same URL is printed.

### 2.8 Framework Root Symlinks

- Create `pl-cdd-start.sh` as a symlink to `tools/cdd/start.sh` at the repository root.
- Create `pl-cdd-stop.sh` as a symlink to `tools/cdd/stop.sh` at the repository root.
- Both symlinks are committed to git and follow the `pl-` naming convention shared with consumer projects.
- Consumer projects continue using their own `pl-cdd-start.sh` / `pl-cdd-stop.sh` (generated by bootstrap, unchanged by this feature).

### 2.9 Restart-on-Rerun

- If a CDD process for this project is already running (detected via `ps`), `start.sh` stops the existing instance, then starts a fresh one on the same port.
- **Restart sequence:** Read current port from `.purlin/runtime/cdd.port`, stop the running process (same logic as `stop.sh`), start a new instance with the previous port as preferred (`-p <port>`). If the preferred port is unavailable (e.g., not yet released by the OS), fall back to OS-assigned port selection.
- **Restart notice:** Before printing the URL, `start.sh` prints `Restarted CDD server on port <port>` to stdout. This line appears before the URL line.
- Running `start.sh` multiple times always results in exactly one server running the latest code, and always prints a usable URL.

### 2.10 Config Key Removal

- The `"cdd_port"` key is removed from `.purlin/config.json` and `purlin-config-sample/config.json`.
- All code that reads or resolves `cdd_port` from config is removed from `start.sh` and `serve.py`.
- The `resolve_config.py` resolver does not need changes -- it dynamically resolves whatever keys exist. Removing the key from the config file is sufficient.

### 2.11 Web-Verify Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/cdd_lifecycle/mixed-statuses` | Project with features in TODO, TESTING, and COMPLETE lifecycle states |
| `main/cdd_lifecycle/all-complete` | Project where every feature is at COMPLETE lifecycle state |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Start prints clickable URL with auto-selected port

    Given no CDD server is running for this project
    And no -p flag is provided
    When start.sh is executed
    Then serve.py binds to an OS-assigned free port
    And .purlin/runtime/cdd.port contains the assigned port number
    And start.sh prints "http://localhost:<port>" to stdout
    And no cdd.pid file is created

#### Scenario: Start with explicit port via -p flag

    Given no CDD server is running for this project
    When start.sh is executed with -p 9090
    Then serve.py binds to port 9090
    And .purlin/runtime/cdd.port contains 9090
    And start.sh prints "http://localhost:9090"

#### Scenario: Restart on rerun preserves port

    Given a CDD server is running for this project on port 9090
    When start.sh is executed again
    Then the existing server process is stopped
    And a new server process is started on port 9090
    And start.sh prints "Restarted CDD server on port 9090"
    And start.sh prints "http://localhost:9090"

#### Scenario: Restart falls back to new port when previous port unavailable

    Given a CDD server was running on port 9090 but the port is still held by the OS after stop
    When start.sh is executed
    Then the server starts on an OS-assigned port
    And start.sh prints the new URL

#### Scenario: Stale port file is cleaned up

    Given .purlin/runtime/cdd.port contains 9090
    And no CDD process is running for this project
    When start.sh is executed
    Then the stale port file is deleted
    And a new CDD server is started with a fresh port
    And the new port is written to .purlin/runtime/cdd.port

#### Scenario: Stop uses ps-based detection

    Given a CDD server is running for this project
    When stop.sh is executed
    Then the process is found via ps (not via cdd.pid)
    And the process is terminated
    And .purlin/runtime/cdd.port is removed
    And no cdd.pid file is referenced

#### Scenario: Idempotent stop when not running

    Given no CDD server is running for this project
    When stop.sh is executed
    Then a "not running" message is printed
    And stop.sh exits with code 0

#### Scenario: Multiple projects on same machine

    Given a CDD server is running for project A on port 8080
    When start.sh is executed for project B
    Then a separate CDD server starts for project B on a different port
    And ps shows two serve.py processes with different --project-root values

#### Scenario: serve.py --project-root is visible in ps

    Given serve.py is started with --project-root /path/to/project
    When ps aux is queried
    Then the output contains "serve.py" and "--project-root /path/to/project"

#### Scenario: Port file written before serve_forever

    Given serve.py is started
    When the server binds to a port
    Then .purlin/runtime/cdd.port is written with the port number
    And this write happens before serve_forever() is called

#### Scenario: cdd_port config key is not read

    Given .purlin/config.json does not contain a cdd_port key
    When start.sh is executed
    Then the server starts successfully with an auto-selected port
    And no error about missing cdd_port is raised

### Manual Scenarios (Human Verification Required)

None.
