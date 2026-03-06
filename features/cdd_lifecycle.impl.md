# Implementation Notes: CDD Lifecycle

### Port Auto-Selection Race Condition
`resolve_port(cli_port=None)` uses `socket.bind(('', 0))` then closes the socket. The OS may reassign the port before `TCPServer` binds to it. In practice this is extremely rare on a single-user dev machine. The alternative (passing the pre-bound socket to TCPServer) would require a larger refactor of the socketserver setup.

### Pre-parse for Module-Level Globals
`--project-root` and `--port` are pre-parsed with simple argv scanning before full argparse, because `PROJECT_ROOT` and `PORT` are needed at module level (import time) for config loading and path setup. Full argparse happens in `__main__` but the values are already resolved.

### ps-based Detection Pattern
The grep pattern `grep "[s]erve.py" | grep -- "--project-root $PROJECT_ROOT"` uses the bracket trick to exclude the grep process itself. The `--project-root` match ensures per-project isolation on multi-project machines.
