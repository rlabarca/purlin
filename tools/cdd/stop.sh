#!/bin/bash
# stop.sh — Stateless CDD Dashboard stop (cdd_lifecycle)
# Resolve symlinks so DIR points to tools/cdd/ even when invoked via root symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    _dir="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$_dir/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Project root discovery (must match start.sh)
if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
    PROJECT_ROOT="$PURLIN_PROJECT_ROOT"
else
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    PROJECT_ROOT="$(cd "$DIR/../../.." 2>/dev/null && pwd)"
    if [ ! -d "$PROJECT_ROOT/.purlin" ]; then
        PROJECT_ROOT="$(cd "$DIR/../.." 2>/dev/null && pwd)"
    fi
fi

RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"
PORT_FILE="$RUNTIME_DIR/cdd.port"

# Stateless process detection (cdd_lifecycle §2.5): ps-based, no PID file
PID=$(ps aux | grep "[s]erve.py" | grep -F -- "--project-root" | grep -F "$PROJECT_ROOT" | awk '{print $2}' | head -1)

if [ -z "$PID" ]; then
    echo "CDD Monitor is not running"
    rm -f "$PORT_FILE"
    exit 0
fi

# Kill with SIGTERM, escalate to SIGKILL after 2 seconds (§2.5 step 2)
kill "$PID" 2>/dev/null
for i in $(seq 1 20); do
    if ! kill -0 "$PID" 2>/dev/null; then
        break
    fi
    sleep 0.1
done
if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" 2>/dev/null
fi

# Clean up port file (§2.5 step 3)
rm -f "$PORT_FILE"
echo "CDD Monitor stopped (PID: $PID)"
