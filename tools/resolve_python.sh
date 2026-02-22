#!/bin/bash
# resolve_python.sh — Shared Python interpreter resolution helper.
# Designed to be SOURCED (not executed directly). Sets $PYTHON_EXE.
# Must NOT contain set -e, set -u, exit, or constructs that terminate the caller.

# Capture the sourcing script's path at file scope.
# Inside a function, BASH_SOURCE[1] would refer to the function's caller (this file),
# not the script that sourced this file. So we capture it here at top level.
_RESOLVE_PYTHON_CALLER="${BASH_SOURCE[1]:-}"

_resolve_python() {
    PYTHON_EXE=""

    # Detect platform-appropriate venv binary path
    local venv_bin="bin/python3"
    case "${OSTYPE:-}" in
        msys*|mingw*|cygwin*) venv_bin="Scripts/python.exe" ;;
    esac

    # Priority 1: AGENTIC_PYTHON environment variable
    if [ -n "${AGENTIC_PYTHON:-}" ] && [ -x "$AGENTIC_PYTHON" ]; then
        PYTHON_EXE="$AGENTIC_PYTHON"
        echo "[resolve_python] Using AGENTIC_PYTHON at $PYTHON_EXE" >&2
        return
    fi

    # Priority 2: PURLIN_PROJECT_ROOT/.venv/
    if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -x "$PURLIN_PROJECT_ROOT/.venv/$venv_bin" ]; then
        PYTHON_EXE="$PURLIN_PROJECT_ROOT/.venv/$venv_bin"
        echo "[resolve_python] Using project root venv at $PYTHON_EXE" >&2
        return
    fi

    # Priority 3: Climbing detection from the sourcing script's directory
    local caller_dir
    if [ -n "${_RESOLVE_PYTHON_CALLER:-}" ]; then
        caller_dir="$(cd "$(dirname "$_RESOLVE_PYTHON_CALLER")" 2>/dev/null && pwd)"
    fi
    if [ -n "${caller_dir:-}" ]; then
        # Standalone layout: ../../.venv from tools/<subtool>/
        if [ -x "$caller_dir/../../.venv/$venv_bin" ]; then
            PYTHON_EXE="$(cd "$caller_dir/../.." && pwd)/.venv/$venv_bin"
            echo "[resolve_python] Using standalone venv at $PYTHON_EXE" >&2
            return
        fi
        # Submodule layout: ../../../.venv from <submodule>/tools/<subtool>/
        if [ -x "$caller_dir/../../../.venv/$venv_bin" ]; then
            PYTHON_EXE="$(cd "$caller_dir/../../.." && pwd)/.venv/$venv_bin"
            echo "[resolve_python] Using submodule venv at $PYTHON_EXE" >&2
            return
        fi
    fi

    # Priority 4: System python3
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_EXE="$(command -v python3)"
        return
    fi

    # Priority 5: System python
    if command -v python >/dev/null 2>&1; then
        PYTHON_EXE="$(command -v python)"
        return
    fi
}

# Auto-resolve on source
_resolve_python
