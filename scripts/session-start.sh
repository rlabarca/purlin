#!/usr/bin/env bash
# Session start: clear stale runtime files
set -euo pipefail

RUNTIME_DIR="${PROJECT_ROOT:-.}/.purlin/runtime"
[[ -d "$RUNTIME_DIR" ]] && rm -f "$RUNTIME_DIR/invariant_write_lock"
exit 0
