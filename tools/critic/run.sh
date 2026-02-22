#!/bin/bash
# run.sh — Run the Critic Quality Gate tool.
# Usage:
#   tools/critic/run.sh              # Analyze all features
#   tools/critic/run.sh features/X.md  # Analyze a single feature
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

# Set CRITIC_RUNNING to prevent recursion: status.sh auto-runs this script,
# so when we call status.sh below, the guard prevents an infinite loop.
export CRITIC_RUNNING=1

# Refresh CDD feature_status.json so lifecycle state is current
CDD_STATUS_SCRIPT="$SCRIPT_DIR/../cdd/status.sh"
if [ -f "$CDD_STATUS_SCRIPT" ]; then
    "$CDD_STATUS_SCRIPT" > /dev/null 2>&1 || true
fi

exec "$PYTHON_EXE" "$SCRIPT_DIR/critic.py" "$@"
