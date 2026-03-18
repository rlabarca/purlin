#!/bin/bash
# run.sh — Run the Critic Quality Gate tool.
# Usage:
#   tools/critic/run.sh              # Analyze all features
#   tools/critic/run.sh features/X.md  # Analyze a single feature
#   tools/critic/run.sh --verbose ...  # Show diagnostic stderr on terminal
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

# --- Diagnostic logging (tools_diagnostic_logging) ---
_PURLIN_VERBOSE=0
_pl_args=()
for _pl_a in "$@"; do
    [ "$_pl_a" = "--verbose" ] && _PURLIN_VERBOSE=1 || _pl_args+=("$_pl_a")
done
set -- "${_pl_args[@]+"${_pl_args[@]}"}"

_PURLIN_LOG_DIR="${PURLIN_PROJECT_ROOT:-.}/.purlin/runtime"
mkdir -p "$_PURLIN_LOG_DIR"
_PURLIN_LOG="$_PURLIN_LOG_DIR/purlin.log"

_log_stderr() {
    local _label="$1" _errfile="$2"
    [ ! -s "$_errfile" ] && return 0
    local _ts
    _ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    while IFS= read -r _line; do
        printf '[%s %s] %s\n' "$_ts" "$_label" "$_line"
    done < "$_errfile" >> "$_PURLIN_LOG"
    [ "$_PURLIN_VERBOSE" = "1" ] && cat "$_errfile" >&2
    return 0
}

# Source shared Python resolver (python_environment.md §2.2)
source "$SCRIPT_DIR/../resolve_python.sh"

# Set CRITIC_RUNNING to prevent recursion: status.sh auto-runs this script,
# so when we call status.sh below, the guard prevents an infinite loop.
export CRITIC_RUNNING=1

# Refresh CDD feature_status.json so lifecycle state is current
CDD_STATUS_SCRIPT="$SCRIPT_DIR/../cdd/status.sh"
if [ -f "$CDD_STATUS_SCRIPT" ]; then
    _status_err=$(mktemp)
    "$CDD_STATUS_SCRIPT" > /dev/null 2>"$_status_err" || true
    _log_stderr "run.sh" "$_status_err"
    rm -f "$_status_err"
fi

exec "$PYTHON_EXE" "$SCRIPT_DIR/critic.py" "$@"
