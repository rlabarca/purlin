#!/bin/sh
# Purlin interpreter resolver: which Python runs a Purlin script.
#
#   sh "$PLUGIN_ROOT/scripts/purlin_python.sh" <script> [args...]
#
# execs the resolved interpreter on <script>. This is the form a JSON launcher
# takes, where "command" is one program and no shell runs.
#
# The order, the first that runs winning:
#   1. $PURLIN_PYTHON, for a host whose interpreter carries none of the names
#      below, or where the first name found is not the right one
#   2. python3
#   3. python, and only when it reports major version 3. A Python 2 under that
#      name is not a fallback, it is a different language
#   4. py -3, the Windows launcher, which is what a python.org install puts on
#      PATH when nothing else is added to it. It resolves to the interpreter's
#      own path, so $PURLIN_PY is always a single word
#
# When none of them runs, this writes one line to stderr naming all four and
# exits 1, so a skill that starts a script through it fails loudly. With
# PURLIN_PYTHON_SOFT set to 1 it exits 0 after the same line: the plugin
# manifest sets it for the MCP server, whose stderr the client shows, so the
# client decides what a missing interpreter means there. The usage line, for
# a call that names no script, exits 0 either way.
#
# POSIX sh only. This file runs before anything has established that bash is
# present, on the operating system least likely to have it.

purlin_python() {
    PURLIN_PY=""

    if [ -n "${PURLIN_PYTHON:-}" ]; then
        if "$PURLIN_PYTHON" -c 'import sys' >/dev/null 2>&1; then
            PURLIN_PY="$PURLIN_PYTHON"
            return 0
        fi
    fi

    if command -v python3 >/dev/null 2>&1; then
        PURLIN_PY="python3"
        return 0
    fi

    if command -v python >/dev/null 2>&1; then
        if python -c 'import sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then
            PURLIN_PY="python"
            return 0
        fi
    fi

    if command -v py >/dev/null 2>&1; then
        purlin_py_exe="$(py -3 -c 'import sys; sys.stdout.write(sys.executable)' 2>/dev/null)"
        if [ -n "$purlin_py_exe" ] && [ -x "$purlin_py_exe" ]; then
            PURLIN_PY="$purlin_py_exe"
            return 0
        fi
    fi

    echo "purlin: no Python 3 interpreter found; tried \$PURLIN_PYTHON, python3, python and py -3. Set PURLIN_PYTHON to the one to use." >&2
    return 1
}

if [ "$#" -eq 0 ]; then
    echo "purlin: usage: sh purlin_python.sh <script> [args...]" >&2
    exit 0
fi
if ! purlin_python; then
    [ "${PURLIN_PYTHON_SOFT:-}" = "1" ] && exit 0
    exit 1
fi
exec "$PURLIN_PY" "$@"
