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

# Extract port from config.json if it exists, otherwise default to 8087
# Standalone: ../../.agentic_devops  |  Submodule: ../../../.agentic_devops
CONFIG_FILE="$DIR/../../.agentic_devops/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="$DIR/../../../.agentic_devops/config.json"
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

nohup $PYTHON_EXE "$DIR/serve.py" > "$DIR/software_map.log" 2>&1 &
echo $! > "$DIR/software_map.pid"
echo "Software Map Viewer started on port $PORT (PID: $(cat "$DIR/software_map.pid"))"
