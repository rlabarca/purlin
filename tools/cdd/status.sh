#!/bin/bash
# status.sh — CLI agent interface for CDD feature status and dependency graph.
# Usage: tools/cdd/status.sh           — outputs /status.json to stdout
#        tools/cdd/status.sh --graph    — outputs dependency_graph.json to stdout
# Side effect: regenerates .purlin/cache/ artifacts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root detection (Section 2.11)
if [ -z "${PURLIN_PROJECT_ROOT:-}" ]; then
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    if [ -d "$SCRIPT_DIR/../../../.purlin" ]; then
        export PURLIN_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    elif [ -d "$SCRIPT_DIR/../../.purlin" ]; then
        export PURLIN_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    fi
fi

# Source shared Python resolver (python_environment.md §2.2)
source "$SCRIPT_DIR/../resolve_python.sh"

if [ "${1:-}" = "--graph" ]; then
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-graph
else
    # Auto-Critic integration (cdd_status_monitor.md Section 2.6):
    # Run Critic before status output so critic.json files are fresh.
    # Recursion guard: skip if CRITIC_RUNNING is already set (the Critic's
    # run.sh calls status.sh to refresh feature_status.json; the guard
    # prevents that inner call from triggering a second Critic run).
    if [ -z "${CRITIC_RUNNING:-}" ]; then
        export CRITIC_RUNNING=1
        CRITIC_SCRIPT="$SCRIPT_DIR/../critic/run.sh"
        if [ -f "$CRITIC_SCRIPT" ]; then
            "$CRITIC_SCRIPT" >/dev/null 2>&1 || true
        fi
    fi
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-status
fi
