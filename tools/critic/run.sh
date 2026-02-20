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

exec python3 "$SCRIPT_DIR/critic.py" "$@"
