#!/bin/bash
# status.sh — CLI agent interface for CDD feature status and dependency graph.
# Usage: tools/cdd/status.sh           — outputs /status.json to stdout
#        tools/cdd/status.sh --graph    — outputs dependency_graph.json to stdout
# Side effect: regenerates .agentic_devops/cache/ artifacts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root detection (Section 2.11)
if [ -z "${AGENTIC_PROJECT_ROOT:-}" ]; then
    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    if [ -d "$SCRIPT_DIR/../../../.agentic_devops" ]; then
        export AGENTIC_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    elif [ -d "$SCRIPT_DIR/../../.agentic_devops" ]; then
        export AGENTIC_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    fi
fi

# Source shared Python resolver (python_environment.md §2.2)
source "$SCRIPT_DIR/../resolve_python.sh"

if [ "${1:-}" = "--graph" ]; then
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-graph
else
    exec "$PYTHON_EXE" "$SCRIPT_DIR/serve.py" --cli-status
fi
