#!/bin/bash
# run.sh — Run the Critic Quality Gate tool.
# Usage:
#   tools/critic/run.sh              # Analyze all features
#   tools/critic/run.sh features/X.md  # Analyze a single feature
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/critic.py" "$@"
