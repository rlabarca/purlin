#!/bin/bash
# stop.sh
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Project root discovery (must match start.sh for PID path consistency)
if [ -n "${AGENTIC_PROJECT_ROOT:-}" ] && [ -d "$AGENTIC_PROJECT_ROOT/.agentic_devops" ]; then
    PROJECT_ROOT="$AGENTIC_PROJECT_ROOT"
else
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    PROJECT_ROOT="$(cd "$DIR/../../.." 2>/dev/null && pwd)"
    if [ ! -d "$PROJECT_ROOT/.agentic_devops" ]; then
        PROJECT_ROOT="$(cd "$DIR/../.." 2>/dev/null && pwd)"
    fi
fi

RUNTIME_DIR="$PROJECT_ROOT/.agentic_devops/runtime"
PID_FILE="$RUNTIME_DIR/cdd.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    kill "$PID" 2>/dev/null
    rm "$PID_FILE"
    echo "CDD Monitor stopped (PID: $PID)"
else
    echo "CDD Monitor is not running (no cdd.pid found at $PID_FILE)"
fi
