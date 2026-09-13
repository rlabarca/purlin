#!/usr/bin/env bash
# Purlin pre-push hook, Layer 1 enforcement.
#
# Modes (set in .purlin/config.json, "pre_push"):
#   "warn"   (default) block on FAILING, report partial coverage
#   "strict" block on anything not VERIFIED, PASSING included
#   "off"    do nothing
#
# This half resolves paths and runs the test runners. It does NOT decide the
# verdict: scripts/hooks/pre_push_gate.py reads the structured status payload
# and decides, and this script propagates its exit code. Nothing here parses
# the rendered summary table, so no column order or glyph can change what a
# push is allowed to do.
set -euo pipefail

# --- Locate the project root ---
ROOT="$(git rev-parse --show-toplevel)"
if [[ ! -d "$ROOT/.purlin" ]]; then
  exit 0  # Not a Purlin project
fi

# --- The Purlin plugin root ---
# The shim at .purlin/hooks/pre-push resolved it and exec'd this script out of
# it (`skill_init` RULE-77), so this script is inside the plugin by
# construction and its own directory is the answer. Nothing here searches: a
# second resolution order is a second answer the day one of them is edited,
# and the shim is the one that runs before this script exists to be run. The
# case where no plugin can be found is the shim's too, since a hook that
# cannot reach the plugin cannot reach this file either.
PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATE="$PLUGIN_ROOT/scripts/hooks/pre_push_gate.py"

# --- The interpreter ---
# One resolver, shared with the MCP launcher and the pre-commit hook, so a
# host whose Python answers to `python` or `py` is one answer to fix rather
# than four. It leaves the command in $PURLIN_PY and has already named on
# stderr every name it tried when it finds none.
. "$PLUGIN_ROOT/scripts/purlin_python.sh"
if [[ -z "${PURLIN_PY:-}" ]]; then
  echo "purlin: no Python 3 interpreter, so the proof coverage check did not run."
  # warn and off would have let this push through anyway; strict would not,
  # and a check that could not run is not a pass. The gate owns config
  # reading and the gate needs the interpreter that is missing, so the one
  # mode that blocks is read here from the text, and nothing else is.
  if [[ -f "$ROOT/.purlin/config.json" ]] \
     && grep -q '"pre_push"[[:space:]]*:[[:space:]]*"strict"' "$ROOT/.purlin/config.json"; then
    echo "purlin: pre-push mode is \"strict\", which cannot be enforced without an"
    echo "        interpreter. Blocking the push rather than passing it unchecked."
    exit 1
  fi
  exit 0
fi

# --- Read the mode ---
# The gate owns config reading; this script asks it rather than parsing the
# config a second way.
CONFIG_RC=0
CONFIG_OUT="$("$PURLIN_PY" "$GATE" config --project-root "$ROOT")" || CONFIG_RC=$?
if [[ $CONFIG_RC -ne 0 ]]; then
  echo "purlin: the pre-push gate could not read this project's configuration"
  echo "        (exit $CONFIG_RC, reason above). Blocking the push."
  exit 1
fi
MODE="$(printf '%s\n' "$CONFIG_OUT" | sed -n 's/^mode=//p')"
FRAMEWORKS="$(printf '%s\n' "$CONFIG_OUT" | sed -n 's/^frameworks=//p')"

if [[ "$MODE" == "off" ]]; then
  echo "purlin: pre-push mode is \"off\"; skipping the proof coverage check."
  exit 0
fi

# --- Find the specs ---
# Recursive: specs nest by category, and a depth limit silently stopped
# checking anything filed deeper than two levels.
SPEC_DIR="$ROOT/specs"
if [[ ! -d "$SPEC_DIR" ]]; then
  exit 0  # No specs yet
fi
if [[ -z "$(find "$SPEC_DIR" -name '*.md')" ]]; then
  exit 0  # No specs yet
fi

# --- Run the unit-tier tests ---
# No `|| true` on any arm. A runner that crashes proved nothing, and a hook
# that shrugs at a crashed runner is reading stale proof files.
IFS=',' read -r -a FRAMEWORK_LIST <<< "$FRAMEWORKS"
for FRAMEWORK in "${FRAMEWORK_LIST[@]}"; do
  RUNNER_RC=0
  case "$FRAMEWORK" in
    pytest)
      echo "purlin: running unit-tier tests ($FRAMEWORK)..."
      # The tier a proof marker names is also a pytest marker on the test
      # (proof_plugins_pytest RULE-5), so this expression actually deselects
      # something: without it the "unit-tier" arm ran every tier there is.
      (cd "$ROOT" && "$PURLIN_PY" -m pytest -m "not integration and not e2e" -q) || RUNNER_RC=$?
      # pytest exits 5 when it collected nothing. No tests is not a failure
      # here; the gate is about to report the coverage that fact produces.
      if [[ $RUNNER_RC -eq 5 ]]; then
        RUNNER_RC=0
      fi
      ;;
    jest)
      echo "purlin: running unit-tier tests ($FRAMEWORK)..."
      (cd "$ROOT" && npx jest --testPathPattern=unit --passWithNoTests) || RUNNER_RC=$?
      ;;
    vitest)
      echo "purlin: running unit-tier tests ($FRAMEWORK)..."
      (cd "$ROOT" && npx vitest run --passWithNoTests) || RUNNER_RC=$?
      ;;
    shell)
      echo "purlin: running unit-tier tests ($FRAMEWORK)..."
      for t in "$ROOT"/*.test.sh; do
        if [[ -f "$t" ]]; then
          bash "$t" || RUNNER_RC=$?
          if [[ $RUNNER_RC -ne 0 ]]; then
            break
          fi
        fi
      done
      ;;
    *)
      echo "purlin: no pre-push runner arm for \"$FRAMEWORK\"; its tests were not run."
      ;;
  esac
  if [[ $RUNNER_RC -ne 0 ]]; then
    echo ""
    echo "PUSH BLOCKED: the $FRAMEWORK runner exited $RUNNER_RC"
    echo ""
    echo "RECOVERY STEPS"
    echo ""
    echo "The tests did not finish, so the proof files on disk describe an"
    echo "earlier run. Fix the runner, then push again."
    echo ""
    echo "1. Reproduce it: run the $FRAMEWORK suite by hand and read the error."
    echo "2. Re-run the proofs once it is green:"
    echo "     purlin:test"
    exit 1
  fi
done

# --- The verdict ---
GATE_RC=0
"$PURLIN_PY" "$GATE" check --project-root "$ROOT" --mode "$MODE" || GATE_RC=$?
if [[ $GATE_RC -ne 0 ]]; then
  # Exit 2 means the gate could not read the evidence and has already said so.
  exit 1
fi

exit 0
