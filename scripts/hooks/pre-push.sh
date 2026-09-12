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

# --- Locate the Purlin plugin root ---
# In order: the directory this script actually lives in (resolved through a
# symlink, which is how a plugin install wires .git/hooks/pre-push), then the
# two environment variables, then the project root for a dev checkout of the
# framework itself. The first candidate carrying the gate script wins.
SELF="${BASH_SOURCE[0]}"
if [[ -L "$SELF" ]]; then
  LINK="$(readlink "$SELF")"
  if [[ "$LINK" != /* ]]; then
    LINK="$(dirname "$SELF")/$LINK"
  fi
  SELF="$LINK"
fi
SELF_DIR="$(cd "$(dirname "$SELF")" && pwd)"

CANDIDATES=("$(cd "$SELF_DIR/../.." && pwd)")
if [[ -n "${PURLIN_PLUGIN_ROOT:-}" ]]; then
  CANDIDATES+=("$PURLIN_PLUGIN_ROOT")
fi
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  CANDIDATES+=("$CLAUDE_PLUGIN_ROOT")
fi
CANDIDATES+=("$ROOT")

GATE=""
for candidate in "${CANDIDATES[@]}"; do
  if [[ -z "$GATE" && -f "$candidate/scripts/hooks/pre_push_gate.py" ]]; then
    GATE="$candidate/scripts/hooks/pre_push_gate.py"
  fi
done

# --- Read the mode ---
# The gate owns config reading, so the inline python below exists only for the
# one case where there is no gate to ask.
MODE=""
FRAMEWORKS=""
if [[ -n "$GATE" ]]; then
  CONFIG_RC=0
  CONFIG_OUT="$(python3 "$GATE" config --project-root "$ROOT")" || CONFIG_RC=$?
  if [[ $CONFIG_RC -ne 0 ]]; then
    echo "purlin: the pre-push gate could not read this project's configuration"
    echo "        (exit $CONFIG_RC, reason above). Blocking the push."
    exit 1
  fi
  MODE="$(printf '%s\n' "$CONFIG_OUT" | sed -n 's/^mode=//p')"
  FRAMEWORKS="$(printf '%s\n' "$CONFIG_OUT" | sed -n 's/^frameworks=//p')"
else
  # $ROOT is an argument, never text spliced into the program: a path
  # containing a quote would otherwise rewrite the script that reads it.
  MODE="$(python3 -c '
import json, os, sys
path = os.path.join(sys.argv[1], ".purlin", "config.json")
if not os.path.isfile(path):
    print("warn")
    sys.exit(0)
try:
    with open(path) as handle:
        print(json.load(handle).get("pre_push", "warn"))
except Exception:
    print("unreadable")
' "$ROOT")"
fi

if [[ "$MODE" == "off" ]]; then
  echo "purlin: pre-push mode is \"off\"; skipping the proof coverage check."
  exit 0
fi

# --- The plugin has to be present to check anything ---
if [[ -z "$GATE" ]]; then
  echo "purlin: WARNING: the Purlin plugin was not found, so proof coverage"
  echo "        was NOT checked. Searched for scripts/hooks/pre_push_gate.py under:"
  for candidate in "${CANDIDATES[@]}"; do
    echo "          $candidate"
  done
  echo "        Set PURLIN_PLUGIN_ROOT to the plugin directory to fix this."
  if [[ "$MODE" == "warn" ]]; then
    exit 0
  fi
  echo "purlin: mode is \"$MODE\", which cannot be enforced without the plugin."
  echo "        Blocking the push rather than passing it unchecked."
  exit 1
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
      (cd "$ROOT" && python3 -m pytest -m "not integration" -q) || RUNNER_RC=$?
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
    echo "     /purlin:test"
    exit 1
  fi
done

# --- The verdict ---
GATE_RC=0
python3 "$GATE" check --project-root "$ROOT" --mode "$MODE" || GATE_RC=$?
if [[ $GATE_RC -ne 0 ]]; then
  # Exit 2 means the gate could not read the evidence and has already said so.
  exit 1
fi

exit 0
