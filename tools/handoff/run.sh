#!/usr/bin/env bash
# Handoff checklist CLI entry point.
# Usage: tools/handoff/run.sh
# All steps apply to all agents — no role filtering.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root detection (Section 2.11 of submodule_bootstrap.md)
if [[ -n "${PURLIN_PROJECT_ROOT:-}" ]] && [[ -d "$PURLIN_PROJECT_ROOT" ]]; then
    PROJECT_ROOT="$PURLIN_PROJECT_ROOT"
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# Detect Python
PYTHON="${AGENTIC_PYTHON:-python3}"

exec "$PYTHON" "$SCRIPT_DIR/run.py" --project-root "$PROJECT_ROOT" "$@"
