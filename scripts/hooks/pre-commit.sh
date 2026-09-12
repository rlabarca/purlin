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

# --- Locate the Purlin plugin root ---
# The same order scripts/hooks/pre-push.sh uses: the directory this script
# actually lives in (resolved through a symlink, which is how a plugin install
# wires .git/hooks/pre-commit), then the two environment variables, then the
# project root for a dev checkout of the framework itself. The first candidate
# carrying the server wins, and a candidate that does not carry it is stepped
# over rather than ending the search.
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

SERVER=""
for candidate in "${CANDIDATES[@]}"; do
  if [[ -z "$SERVER" && -f "$candidate/scripts/mcp/purlin_server.py" ]]; then
    SERVER="$candidate/scripts/mcp/purlin_server.py"
  fi
done

# --- Read the mode ---
# $CONFIG is an argument, never text spliced into the program: a path
# containing a quote would otherwise rewrite the script that reads it.
CONFIG="$ROOT/.purlin/config.json"
MODE="auto"
if [[ -f "$CONFIG" ]]; then
  MODE="$(python3 -c '
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
  # --- The plugin has to be present to generate anything ---
  if [[ -z "$SERVER" ]]; then
    echo "purlin: WARNING: the Purlin plugin was not found, so the project"
    echo "        digest was NOT refreshed. Searched for"
    echo "        scripts/mcp/purlin_server.py under:"
    for candidate in "${CANDIDATES[@]}"; do
      echo "          $candidate"
    done
    echo "        Set PURLIN_PLUGIN_ROOT to the plugin directory to fix this."
    exit 0
  fi
  SERVER_DIR="$(dirname "$SERVER")"

  echo "purlin: generating the project digest (coverage and drift)..."
  echo "purlin: NOTE: this does not trigger an audit, cached data only."

  # $SERVER_DIR and $ROOT are arguments, never text spliced into the program,
  # for the same reason as above. Only stdout is captured: whatever
  # generate_digest raises goes straight to the developer's terminal.
  GENERATE_RC=0
  RESULT="$(python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
from purlin_server import generate_digest
path = generate_digest(sys.argv[2])
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
    STALE="$(python3 -c '
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
