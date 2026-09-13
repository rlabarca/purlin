#!/usr/bin/env bash
# Purlin pre-commit hook, project digest refresh.
#
# Modes (set in .purlin/config.json, "digest"):
#   "auto"  (default) regenerate the digest and stage it before every commit
#   "warn"  never regenerate, warn when the digest is missing or stale
#   "off"   do nothing
#
# This hook never blocks a commit: every path exits 0. Because of that, every
# path that gives up says so on stdout. A silent skip is indistinguishable from
# a hook that worked, and the developer would go on believing the digest in the
# commit is current when nothing refreshed it.
#
# IMPORTANT: this hook runs sync_status (coverage) and drift ONLY. It never
# triggers a new audit; cached audit data is carried through as it stands.
# Run purlin:audit separately when you want fresh audit scores.
set -euo pipefail

# --- The explicit opt out, before anything else is read ---
if [[ "${PURLIN_SKIP_DIGEST:-}" == "1" ]]; then
  echo "purlin: PURLIN_SKIP_DIGEST=1, skipping the project digest."
  exit 0
fi

# --- Locate the project root ---
ROOT="$(git rev-parse --show-toplevel)"
if [[ ! -d "$ROOT/.purlin" ]]; then
  exit 0  # Not a Purlin project, and not this hook's business to say so
fi

# --- The Purlin plugin root ---
# The shim at .purlin/hooks/pre-commit resolved it and exec'd this script out
# of it (`skill_init` RULE-77), so this script is inside the plugin by
# construction and its own directory is the answer. Nothing here searches: a
# second resolution order is a second answer the day one of them is edited,
# and the shim is the one that runs before this script exists to be run.
PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SERVER="$PLUGIN_ROOT/scripts/mcp/purlin_server.py"

# --- The interpreter ---
# One resolver, shared with the MCP launcher and the pre-push hook, so a host
# whose Python answers to `python` or `py` is one answer to fix rather than
# four. It leaves the command in $PURLIN_PY and has already named on stderr
# every name it tried when it finds none.
. "$PLUGIN_ROOT/scripts/purlin_python.sh"
if [[ -z "${PURLIN_PY:-}" ]]; then
  echo "purlin: no Python 3 interpreter, so the project digest was not refreshed."
  echo "        Committing anyway, with .purlin/report-data.js left as it was."
  exit 0
fi

# --- Read the mode ---
# $CONFIG is an argument, never text spliced into the program: a path
# containing a quote would otherwise rewrite the script that reads it.
CONFIG="$ROOT/.purlin/config.json"
MODE="auto"
if [[ -f "$CONFIG" ]]; then
  MODE="$("$PURLIN_PY" -c '
import json, sys
try:
    with open(sys.argv[1]) as handle:
        print(json.load(handle).get("digest", "auto"))
except Exception:
    print("unreadable")
' "$CONFIG")"
fi

case "$MODE" in
  auto|warn|off) ;;
  *)
    echo "purlin: could not read a usable \"digest\" mode from $CONFIG"
    echo "        (got \"$MODE\"); assuming \"auto\"."
    MODE="auto"
    ;;
esac

if [[ "$MODE" == "off" ]]; then
  echo "purlin: digest mode is \"off\"; skipping the project digest."
  exit 0
fi

if [[ "$MODE" == "auto" ]]; then
  SERVER_DIR="$(dirname "$SERVER")"

  echo "purlin: generating the project digest (coverage and drift)..."
  echo "purlin: NOTE: this does not trigger an audit, cached data only."

  # $SERVER_DIR and $ROOT are arguments, never text spliced into the program,
  # for the same reason as above. Only stdout is captured: whatever
  # generate_digest raises goes straight to the developer's terminal.
  GENERATE_RC=0
  RESULT="$("$PURLIN_PY" -c '
import sys
sys.path.insert(0, sys.argv[1])
from purlin_server import generate_digest
path = generate_digest(sys.argv[2], generated_by="pre-commit")
print(path or "")
' "$SERVER_DIR" "$ROOT")" || GENERATE_RC=$?

  if [[ $GENERATE_RC -ne 0 ]]; then
    echo "purlin: digest generation failed (python exit $GENERATE_RC, error above)."
    echo "        Committing anyway, with .purlin/report-data.js left as it was."
    exit 0
  fi

  if [[ -n "$RESULT" && -f "$RESULT" ]]; then
    if git add "$RESULT"; then
      echo "purlin: digest updated and staged: .purlin/report-data.js"
    else
      echo "purlin: digest updated but git add refused it (reason above);"
      echo "        committing anyway without it."
    fi
  else
    echo "purlin: digest generation wrote no file;"
    echo "        committing anyway, with .purlin/report-data.js left as it was."
  fi

elif [[ "$MODE" == "warn" ]]; then
  # warn never regenerates and never stages: it only reports.
  DIGEST_FILE="$ROOT/.purlin/report-data.js"
  if [[ ! -f "$DIGEST_FILE" ]]; then
    echo "purlin: WARNING: the project digest was not found at .purlin/report-data.js."
    echo "        Run purlin:status to generate it."
  else
    STALE="$("$PURLIN_PY" -c '
import json, datetime, sys
try:
    with open(sys.argv[1]) as handle:
        content = handle.read()
    json_str = content.replace("const PURLIN_DATA = ", "", 1).rstrip().rstrip(";")
    data = json.loads(json_str)
    ts = data.get("timestamp", "")
    if not ts:
        print("stale")
        sys.exit(0)
    then = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    age = (datetime.datetime.now(datetime.timezone.utc) - then).total_seconds()
    print("stale" if age > 3600 else "fresh")
except Exception:
    print("stale")
' "$DIGEST_FILE")"
    if [[ "$STALE" == "stale" ]]; then
      echo "purlin: WARNING: the project digest is stale (older than 3600 seconds)."
      echo "        Run purlin:status, or set digest=auto in .purlin/config.json."
    fi
  fi
fi

exit 0
