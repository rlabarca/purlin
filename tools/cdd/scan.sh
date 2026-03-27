#!/bin/bash
# scan.sh -- Lightweight status scanner for the Purlin agent.
# Gathers project facts and outputs structured JSON to stdout.
# Usage: tools/cdd/scan.sh            -- full scan
#        tools/cdd/scan.sh --cached    -- return cached result if < 60s old
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root detection
if [ -z "${PURLIN_PROJECT_ROOT:-}" ]; then
    if [ -d "$SCRIPT_DIR/../../../.purlin" ]; then
        export PURLIN_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    elif [ -d "$SCRIPT_DIR/../../.purlin" ]; then
        export PURLIN_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    fi
fi

# Resolve Python interpreter (shared helper)
_resolve_err=$(mktemp)
source "$SCRIPT_DIR/../resolve_python.sh" 2>"$_resolve_err" || true
rm -f "$_resolve_err"

# Suppress Python SyntaxWarnings so they don't pollute JSON output.
export PYTHONWARNINGS=ignore

exec "$PYTHON_EXE" "$SCRIPT_DIR/scan.py" "$@"
