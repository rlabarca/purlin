#!/bin/bash
# start.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Project root and config discovery (Section 2.11)
if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
    PROJECT_ROOT="$PURLIN_PROJECT_ROOT"
    CONFIG_FILE="$PURLIN_PROJECT_ROOT/.purlin/config.json"
else
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    CONFIG_FILE="$DIR/../../../.purlin/config.json"
    PROJECT_ROOT="$(cd "$DIR/../../.." 2>/dev/null && pwd)"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="$DIR/../../.purlin/config.json"
        PROJECT_ROOT="$(cd "$DIR/../.." 2>/dev/null && pwd)"
    fi
fi

# Source shared Python resolver (python_environment.md §2.2)
source "$DIR/../resolve_python.sh"

# Runtime port override (Section 2.12): -p <port> flag
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

PORT=8086

if [ -f "$CONFIG_FILE" ]; then
    # Simple grep/sed extraction for "cdd_port": 1234
    PORT_FROM_CONFIG=$(grep '"cdd_port"' "$CONFIG_FILE" | sed -E 's/.*"cdd_port": *([0-9]+).*/\1/')
    if [ ! -z "$PORT_FROM_CONFIG" ]; then
        PORT=$PORT_FROM_CONFIG
    fi
fi

# -p flag overrides config (Section 2.12 priority: -p > config > 8086 default)
if [ -n "$OVERRIDE_PORT" ]; then
    PORT="$OVERRIDE_PORT"
fi

# Artifact isolation (Section 2.12): logs/pids to .purlin/runtime/
RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"
mkdir -p "$RUNTIME_DIR"

# Export CDD_PORT when -p is provided (Section 2.12)
if [ -n "$OVERRIDE_PORT" ]; then
    PURLIN_PROJECT_ROOT="$PROJECT_ROOT" CDD_PORT="$OVERRIDE_PORT" nohup $PYTHON_EXE "$DIR/serve.py" > "$RUNTIME_DIR/cdd.log" 2>&1 &
else
    PURLIN_PROJECT_ROOT="$PROJECT_ROOT" nohup $PYTHON_EXE "$DIR/serve.py" > "$RUNTIME_DIR/cdd.log" 2>&1 &
fi
echo $! > "$RUNTIME_DIR/cdd.pid"
SERVER_PID=$(cat "$RUNTIME_DIR/cdd.pid")

# Verify server actually started (detect bind failures)
sleep 0.5
if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "CDD Monitor started on port $PORT (PID: $SERVER_PID)"
else
    echo "ERROR: CDD Monitor failed to start (PID $SERVER_PID exited). Check $RUNTIME_DIR/cdd.log" >&2
    rm -f "$RUNTIME_DIR/cdd.pid"
    exit 1
fi
