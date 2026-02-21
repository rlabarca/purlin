#!/bin/bash
# start.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Project root and config discovery (Section 2.11)
if [ -n "${AGENTIC_PROJECT_ROOT:-}" ] && [ -d "$AGENTIC_PROJECT_ROOT/.agentic_devops" ]; then
    PROJECT_ROOT="$AGENTIC_PROJECT_ROOT"
    CONFIG_FILE="$AGENTIC_PROJECT_ROOT/.agentic_devops/config.json"
else
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    CONFIG_FILE="$DIR/../../../.agentic_devops/config.json"
    PROJECT_ROOT="$(cd "$DIR/../../.." 2>/dev/null && pwd)"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="$DIR/../../.agentic_devops/config.json"
        PROJECT_ROOT="$(cd "$DIR/../.." 2>/dev/null && pwd)"
    fi
fi

# Source shared Python resolver (python_environment.md §2.2)
source "$DIR/../resolve_python.sh"

PORT=8087

if [ -f "$CONFIG_FILE" ]; then
    PORT_FROM_CONFIG=$(grep '"map_port"' "$CONFIG_FILE" | sed -E 's/.*"map_port": *([0-9]+).*/\1/')
    if [ ! -z "$PORT_FROM_CONFIG" ]; then
        PORT=$PORT_FROM_CONFIG
    fi
fi

# Generate outputs before starting (serve.py also regenerates on startup)
$PYTHON_EXE "$DIR/generate_tree.py"

# Artifact isolation (Section 2.12): logs/pids to .agentic_devops/runtime/
RUNTIME_DIR="$PROJECT_ROOT/.agentic_devops/runtime"
mkdir -p "$RUNTIME_DIR"

nohup $PYTHON_EXE "$DIR/serve.py" > "$RUNTIME_DIR/software_map.log" 2>&1 &
echo $! > "$RUNTIME_DIR/software_map.pid"
SERVER_PID=$(cat "$RUNTIME_DIR/software_map.pid")

# Verify server actually started (detect bind failures)
sleep 0.5
if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Software Map Viewer started on port $PORT (PID: $SERVER_PID)"
else
    echo "ERROR: Software Map failed to start (PID $SERVER_PID exited). Check $RUNTIME_DIR/software_map.log" >&2
    rm -f "$RUNTIME_DIR/software_map.pid"
    exit 1
fi
