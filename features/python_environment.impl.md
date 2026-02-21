# Implementation Notes: Python Environment

*   **`cdd/stop.sh` exclusion:** `stop.sh` does not invoke Python -- it only reads a PID file and sends a signal. No migration needed.
*   **`BASH_SOURCE[1]` for climbing:** When `resolve_python.sh` is sourced, `${BASH_SOURCE[0]}` is the helper itself and `${BASH_SOURCE[1]}` is the sourcing script. Climbing paths must be relative to the sourcing script's directory, not the helper's. This ensures correct venv detection regardless of where the helper lives.
*   **No `set -e` in helper:** The helper is sourced into scripts that may or may not use `set -e`. Using `set -e` in the helper would impose error behavior on the caller. Use explicit `if/elif` instead of relying on exit codes.
*   **MSYS/MinGW detection:** Check `$OSTYPE` for patterns `msys*`, `mingw*`, or `cygwin*`. These indicate Git Bash or similar Windows shell environments where the venv binary path is `.venv/Scripts/python.exe` instead of `.venv/bin/python3`.
*   **Why not `$VIRTUAL_ENV`?** The `$VIRTUAL_ENV` environment variable is set when a venv is activated, but our tools are not launched from within an activated venv. They are launched from launcher scripts or directly by agents. The resolution helper must detect the venv by directory presence, not by activation state.
