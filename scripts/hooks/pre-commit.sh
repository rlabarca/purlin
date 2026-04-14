#!/usr/bin/env bash
# Purlin pre-commit hook — project digest auto-generation.
#
# Modes (set in .purlin/config.json → "digest"):
#   "auto"  — regenerate digest before every commit (default)
#   "warn"  — warn if digest is stale, don't regenerate
#   "off"   — disable hook
#
# IMPORTANT: This hook runs sync_status (coverage) and drift ONLY.
# It NEVER triggers a new audit. Cached audit data is included.
# Run purlin:audit separately when you want fresh audit scores.
set -euo pipefail

# Skip if explicitly disabled via environment
if [[ "${PURLIN_SKIP_DIGEST:-}" == "1" ]]; then
  exit 0
fi

# --- Locate project root ---
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ ! -d "$ROOT/.purlin" ]]; then
  exit 0  # Not a Purlin project
fi

# --- Read mode from config ---
MODE="auto"
if [[ -f "$ROOT/.purlin/config.json" ]]; then
  MODE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('digest','auto'))" "$ROOT/.purlin/config.json" 2>/dev/null || echo "auto")
fi
if [[ "$MODE" == "off" ]]; then
  exit 0
fi

# --- Locate purlin_server.py ---
SERVER="$ROOT/scripts/mcp/purlin_server.py"
if [[ ! -f "$SERVER" ]]; then
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -f "$CLAUDE_PLUGIN_ROOT/scripts/mcp/purlin_server.py" ]]; then
    SERVER="$CLAUDE_PLUGIN_ROOT/scripts/mcp/purlin_server.py"
  else
    exit 0  # Can't find server, skip silently
  fi
fi
SERVER_DIR="$(dirname "$SERVER")"

if [[ "$MODE" == "auto" ]]; then
  echo "purlin: generating project digest (coverage + drift)..."
  echo "purlin: NOTE — does NOT trigger audit (cached data only)"

  RESULT=$(python3 -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
from purlin_server import generate_digest
path = generate_digest('$ROOT')
print(path or '')
" 2>/dev/null) || { echo "purlin: digest generation failed, continuing"; exit 0; }

  if [[ -n "$RESULT" && -f "$RESULT" ]]; then
    git add "$RESULT"
    echo "purlin: digest updated and staged: .purlin/report-data.js"
  fi

elif [[ "$MODE" == "warn" ]]; then
  DIGEST_FILE="$ROOT/.purlin/report-data.js"
  if [[ ! -f "$DIGEST_FILE" ]]; then
    echo "purlin: WARNING — project digest not found. Run purlin:status to generate."
  else
    STALE=$(python3 -c "
import json, datetime, sys
try:
    with open(sys.argv[1]) as f:
        content = f.read()
    json_str = content.replace('const PURLIN_DATA = ', '', 1).rstrip().rstrip(';')
    data = json.loads(json_str)
    ts = data.get('timestamp', '')
    if not ts:
        print('stale')
        sys.exit(0)
    then = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
    age = (datetime.datetime.now(datetime.timezone.utc) - then).total_seconds()
    print('stale' if age > 3600 else 'fresh')
except Exception:
    print('stale')
" "$DIGEST_FILE" 2>/dev/null)
    if [[ "$STALE" == "stale" ]]; then
      echo "purlin: WARNING — project digest is stale (>1 hour). Run purlin:status or set digest=auto."
    fi
  fi
fi

exit 0
