# Implementation Notes: CDD Lifecycle

### Port Auto-Selection Race Condition
`resolve_port(cli_port=None)` uses `socket.bind(('', 0))` then closes the socket. The OS may reassign the port before `TCPServer` binds to it. In practice this is extremely rare on a single-user dev machine. The alternative (passing the pre-bound socket to TCPServer) would require a larger refactor of the socketserver setup.

### Pre-parse for Module-Level Globals
`--project-root` and `--port` are pre-parsed with simple argv scanning before full argparse, because `PROJECT_ROOT` and `PORT` are needed at module level (import time) for config loading and path setup. Full argparse happens in `__main__` but the values are already resolved.

### ps-based Detection Pattern
The grep pattern `grep "[s]erve.py" | grep -F "--project-root" | grep -F "$PROJECT_ROOT"` uses the bracket trick to exclude the grep process itself, and `grep -F` for fixed-string matching to handle project roots with spaces or special characters. The `--project-root` match ensures per-project isolation on multi-project machines.

### Symlink Resolution in start.sh / stop.sh
Both scripts use a `while [ -L "$SOURCE" ]` loop to resolve symlinks before computing `DIR`. This is critical because:
- Purlin standalone: `cdd_start.sh -> tools/cdd/start.sh` (one level)
- Consumer submodule: `pl-cdd-start.sh -> purlin/tools/cdd/start.sh` (one level)
Without resolution, `DIR` would be the invoking directory (project root), not `tools/cdd/`, and relative paths like `$DIR/../resolve_python.sh` would fail. macOS `readlink` does not support `-f`, so the loop is required.
