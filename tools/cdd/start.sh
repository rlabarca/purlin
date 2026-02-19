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

# Extract port from config.json if it exists, otherwise default to 8086
# Path is ../../ because we are in tools/cdd and config is in root/.agentic_devops
CONFIG_FILE="$DIR/../../.agentic_devops/config.json"
PORT=8086

if [ -f "$CONFIG_FILE" ]; then
    # Simple grep/sed extraction for "cdd_port": 1234
    PORT_FROM_CONFIG=$(grep '"cdd_port"' "$CONFIG_FILE" | sed -E 's/.*"cdd_port": *([0-9]+).*/\1/')
    if [ ! -z "$PORT_FROM_CONFIG" ]; then
        PORT=$PORT_FROM_CONFIG
    fi
fi

nohup $PYTHON_EXE $DIR/serve.py > $DIR/cdd.log 2>&1 &
echo $! > $DIR/cdd.pid
echo "CDD Monitor started on port $PORT (PID: $(cat $DIR/cdd.pid))"
