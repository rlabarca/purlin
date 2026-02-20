#!/bin/bash
# start.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_EXE="python3"

# Check if we are in a virtualenv
if [ -d "$DIR/../../.venv" ]; then
    PYTHON_EXE="$DIR/../../.venv/bin/python3"
elif [ -d "$DIR/../../../.venv" ]; then
     PYTHON_EXE="$DIR/../../../.venv/bin/python3"
fi

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
echo "Software Map Viewer started on port $PORT (PID: $(cat "$RUNTIME_DIR/software_map.pid"))"
