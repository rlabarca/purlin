#!/usr/bin/env bash
# Purlin pre-push hook: run the tagged tests once before a push, and say what
# they did.
#
# The hook runs `scripts/run/purlin_run.py --all --quick`, which is the same
# thing `purlin:test` runs: the tagged tests, into `.purlin/runtime/proofs/`,
# in seconds. It prints one line either way.
#
# It blocks a push only when both of these are true: `pre_push` in
# `.purlin/config.json` is `on`, and a test failed. Every other outcome exits
# 0, including a missing interpreter, a project with no specs and a failing
# test in a project that left `pre_push` at its default. What a change must
# clear before it merges is the gate, and the gate is the git host's to
# enforce; this hook is a local convenience in front of it.
#
# `.purlin/hooks/pre-push` is the shim that finds the installed plugin and
# execs this file out of it, so by the time this runs the plugin root is this
# script's own grandparent directory and nothing here searches for it.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$ROOT" ] || exit 0
[ -d "$ROOT/.purlin" ] || exit 0
# No spec is nothing to run, and the folder alone is not a spec: purlin:init
# creates specs/ before anything has been written into it.
[ -n "$(find "$ROOT/specs" -name '*.md' -print 2>/dev/null | head -1)" ] || exit 0

PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# One interpreter resolver, shared with the MCP launcher and the shim.
# shellcheck source=../purlin_python.sh
. "$PLUGIN_ROOT/scripts/purlin_python.sh"
if [ -z "${PURLIN_PY:-}" ]; then
  echo "purlin: no Python 3 interpreter, so the tagged tests did not run before this push."
  exit 0
fi

# The one setting this hook reads. An unreadable file is `off`: a hook that
# cannot read the project's answer has not been told to block anything.
SETTING="$("$PURLIN_PY" - "$ROOT" <<'PY'
import json
import os
import sys
try:
    path = os.path.join(sys.argv[1], '.purlin', 'config.json')
    with open(path, encoding='utf-8') as handle:
        print(json.load(handle).get('pre_push', 'off'))
except Exception:
    print('off')
PY
)"

RUN_RC=0
"$PURLIN_PY" "$PLUGIN_ROOT/scripts/run/purlin_run.py" \
  --all --quick --project-root "$ROOT" || RUN_RC=$?

if [ "$RUN_RC" -eq 0 ]; then
  echo "purlin: the tagged tests passed, so this push goes ahead."
  exit 0
fi

if [ "$SETTING" = "on" ] || [ "$SETTING" = "True" ] || [ "$SETTING" = "true" ]; then
  echo "purlin: a tagged test failed and pre_push is \"on\", so this push is blocked."
  echo "        Run purlin:test, fix the failure, then push again."
  exit 1
fi

echo "purlin: a tagged test failed. pre_push is \"$SETTING\", so this push is not blocked."
echo "        Run purlin:test to see it."
exit 0
