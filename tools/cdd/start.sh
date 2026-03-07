#!/bin/bash
# start.sh — Stateless CDD Dashboard lifecycle (cdd_lifecycle)
# Resolve symlinks so DIR points to tools/cdd/ even when invoked via root symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    _dir="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$_dir/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
# Project root discovery (Section 2.11)
if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
    PROJECT_ROOT="$PURLIN_PROJECT_ROOT"
else
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    PROJECT_ROOT="$(cd "$DIR/../../.." 2>/dev/null && pwd)"
    if [ ! -d "$PROJECT_ROOT/.purlin" ]; then
        PROJECT_ROOT="$(cd "$DIR/../.." 2>/dev/null && pwd)"
    fi
fi

# Source shared Python resolver (python_environment.md §2.2)
source "$DIR/../resolve_python.sh"

# Runtime port override: -p <port> flag
OVERRIDE_PORT=""
while getopts "p:" opt; do
    case $opt in
        p) OVERRIDE_PORT="$OPTARG" ;;
        *) echo "Usage: start.sh [-p <port>]" >&2; exit 1 ;;
    esac
done

# Validate -p value if provided
if [ -n "$OVERRIDE_PORT" ]; then
    if ! [[ "$OVERRIDE_PORT" =~ ^[0-9]+$ ]] || [ "$OVERRIDE_PORT" -lt 1 ] || [ "$OVERRIDE_PORT" -gt 65535 ]; then
        echo "ERROR: Invalid port '$OVERRIDE_PORT'. Must be an integer between 1 and 65535." >&2
        exit 1
    fi
fi

RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"
mkdir -p "$RUNTIME_DIR"
PORT_FILE="$RUNTIME_DIR/cdd.port"

# Helper: find CDD process for this project via ps (handles paths with spaces)
find_cdd_pid() {
    ps aux | grep "[s]erve.py" | grep -F -- "--project-root" | grep -F "$PROJECT_ROOT" | awk '{print $2}' | head -1
}

# Stateless process detection (cdd_lifecycle §2.1): ps-based, no PID file
EXISTING_PID=$(find_cdd_pid)

if [ -n "$EXISTING_PID" ]; then
    # Restart-on-rerun (§2.9): stop existing, start fresh on same port
    PREVIOUS_PORT=""
    if [ -f "$PORT_FILE" ]; then
        PREVIOUS_PORT=$(cat "$PORT_FILE")
    fi

    # Stop existing process (same logic as stop.sh §2.5)
    kill "$EXISTING_PID" 2>/dev/null
    for i in $(seq 1 20); do
        if ! kill -0 "$EXISTING_PID" 2>/dev/null; then
            break
        fi
        sleep 0.1
    done
    if kill -0 "$EXISTING_PID" 2>/dev/null; then
        kill -9 "$EXISTING_PID" 2>/dev/null
    fi
    rm -f "$PORT_FILE"

    # Prefer previous port unless user specified -p
    if [ -z "$OVERRIDE_PORT" ] && [ -n "$PREVIOUS_PORT" ]; then
        OVERRIDE_PORT="$PREVIOUS_PORT"
    fi
    RESTARTING=true
else
    RESTARTING=false
fi

# Clean stale port file if no process is running (§2.4 step 2)
rm -f "$PORT_FILE"

# Launch serve.py (§2.4 step 3) — array handles paths with spaces
nohup "$PYTHON_EXE" "$DIR/serve.py" --project-root "$PROJECT_ROOT" \
    ${OVERRIDE_PORT:+--port "$OVERRIDE_PORT"} \
    > "$RUNTIME_DIR/cdd.log" 2>&1 &

# Wait for port file to appear (up to 2 seconds, §2.4 step 4)
for i in $(seq 1 20); do
    if [ -f "$PORT_FILE" ]; then
        break
    fi
    sleep 0.1
done

# Verify server started
VERIFY_PID=$(find_cdd_pid)

if [ -n "$VERIFY_PID" ] && [ -f "$PORT_FILE" ]; then
    PORT=$(cat "$PORT_FILE")
    if [ "$RESTARTING" = true ]; then
        echo "Restarted CDD server on port $PORT"
    fi
    echo "http://localhost:$PORT"
else
    echo "ERROR: CDD Monitor failed to start. Check $RUNTIME_DIR/cdd.log" >&2
    exit 1
fi
