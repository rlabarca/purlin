#!/bin/bash
# status.sh — CLI agent interface for CDD feature status and dependency graph.
# Usage: tools/cdd/status.sh                    — outputs /status.json to stdout
#        tools/cdd/status.sh --startup <role>    — startup briefing for agent role
#        tools/cdd/status.sh --graph             — outputs dependency_graph.json to stdout
#        tools/cdd/status.sh --incomplete        — lists features not fully complete
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
# Suppress resolve_python diagnostics so agents piping stdout to a JSON
# parser (even with accidental 2>&1) get clean output.
source "$SCRIPT_DIR/../resolve_python.sh" 2>/dev/null

# Helper: run Critic before status to ensure critic.json files are fresh.
run_critic_if_needed() {
    if [ -z "${CRITIC_RUNNING:-}" ]; then
        export CRITIC_RUNNING=1
        CRITIC_SCRIPT="$SCRIPT_DIR/../critic/run.sh"
        if [ -f "$CRITIC_SCRIPT" ]; then
            "$CRITIC_SCRIPT" >/dev/null 2>&1 || true
        fi
    fi
}

# Suppress Python SyntaxWarnings from serve.py (e.g., invalid escape sequences)
# so they don't pollute JSON output when callers pipe stdout to a parser.
export PYTHONWARNINGS=ignore

if [ "${1:-}" = "--startup" ]; then
    # Startup briefing (cdd_status_monitor.md Section 2.15)
    # --startup takes precedence over all other flags (mutual exclusivity)
    if [ -z "${2:-}" ]; then
        echo "Error: --startup requires a role argument (architect|builder|qa|pm)" >&2
        exit 1
    fi
    run_critic_if_needed
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-startup "$2"
elif [ "${1:-}" = "--graph" ]; then
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-graph
elif [ "${1:-}" = "--role" ]; then
    # Role-filtered output (cdd_status_monitor.md Section 2.7, --role flag)
    if [ -z "${2:-}" ]; then
        echo "Error: --role requires a role argument (architect|builder|qa|pm)" >&2
        exit 1
    fi
    run_critic_if_needed
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-role-status "$2"
elif [ "${1:-}" = "--incomplete" ]; then
    # List features where any role column is not in its "done" state.
    # This avoids agents needing inline Python with != (which bash
    # history expansion corrupts: != becomes \!=).
    run_critic_if_needed
    "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-status | "$PYTHON_EXE" "$SCRIPT_DIR/check_incomplete.py"
else
    # Auto-Critic integration (cdd_status_monitor.md Section 2.6):
    # Run Critic before status output so critic.json files are fresh.
    # Recursion guard: skip if CRITIC_RUNNING is already set (the Critic's
    # run.sh calls status.sh to refresh feature_status.json; the guard
    # prevents that inner call from triggering a second Critic run).
    run_critic_if_needed
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-status
fi
