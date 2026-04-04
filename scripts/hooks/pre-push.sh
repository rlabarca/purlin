#!/usr/bin/env bash
# Purlin pre-push hook — Layer 1 enforcement.
#
# Modes (set in .purlin/config.json → "pre_push"):
#   "warn"   — block on FAIL, allow passing+partial (default)
#   "strict" — block on anything not READY (requires verification receipt)
#   "off"    — disable hook
set -euo pipefail

# --- Locate project root ---
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ ! -d "$ROOT/.purlin" ]]; then
  exit 0  # Not a Purlin project
fi

# --- Read mode from config ---
MODE="warn"
if [[ -f "$ROOT/.purlin/config.json" ]]; then
  MODE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('pre_push','warn'))" "$ROOT/.purlin/config.json" 2>/dev/null || echo "warn")
fi
if [[ "$MODE" == "off" ]]; then
  exit 0
fi

SPEC_DIR="$ROOT/specs"
if [[ ! -d "$SPEC_DIR" ]] || [[ -z "$(find "$SPEC_DIR" -maxdepth 2 -name '*.md' 2>/dev/null | head -1)" ]]; then
  exit 0  # No specs yet
fi

# --- Run unit-tier tests ---
FRAMEWORK="auto"
if [[ -f "$ROOT/.purlin/config.json" ]]; then
  FRAMEWORK=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('test_framework','auto'))" "$ROOT/.purlin/config.json" 2>/dev/null || echo "auto")
fi
if [[ "$FRAMEWORK" == "auto" ]]; then
  if [[ -f "$ROOT/conftest.py" ]] || grep -q '\[tool\.pytest\]' "$ROOT/pyproject.toml" 2>/dev/null; then
    FRAMEWORK="pytest"
  elif [[ -f "$ROOT/package.json" ]] && grep -q jest "$ROOT/package.json" 2>/dev/null; then
    FRAMEWORK="jest"
  else
    FRAMEWORK="shell"
  fi
fi

echo "purlin: running unit-tier tests ($FRAMEWORK)..."
case "$FRAMEWORK" in
  pytest) (cd "$ROOT" && python3 -m pytest -m "not integration" -q 2>&1) || true ;;
  jest)   (cd "$ROOT" && npx jest --testPathPattern=unit 2>&1) || true ;;
  shell)  for t in "$ROOT"/*.test.sh; do [[ -f "$t" ]] && bash "$t" 2>&1; done || true ;;
esac

# --- Check sync_status ---
SERVER="$ROOT/scripts/mcp/purlin_server.py"
if [[ ! -f "$SERVER" ]]; then
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -f "$CLAUDE_PLUGIN_ROOT/scripts/mcp/purlin_server.py" ]]; then
    SERVER="$CLAUDE_PLUGIN_ROOT/scripts/mcp/purlin_server.py"
  else
    echo "purlin: sync_status not available, skipping coverage check"
    exit 0
  fi
fi

SERVER_DIR="$(dirname "$SERVER")"
STATUS=$(python3 -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
from purlin_server import sync_status
print(sync_status('$ROOT'))
" 2>/dev/null) || { echo "purlin: could not run sync_status, allowing push"; exit 0; }

# --- Parse results ---
FAILS=""
WARNINGS=""
PASSES=""
NON_READY=""
while IFS= read -r line; do
  if [[ "$line" =~ ^[a-zA-Z_] ]] && [[ ! "$line" =~ ^[[:space:]] ]]; then
    CURRENT_FEATURE="$line"
  fi
  if [[ "$line" == *": FAIL "* ]]; then
    RULE=$(echo "$line" | sed 's/^[[:space:]]*//')
    FAILS="${FAILS}  ${CURRENT_FEATURE%%:*} → ${RULE}\n"
  fi
  if [[ "$line" == *": NO PROOF "* ]] || [[ "$line" == *"MANUAL PROOF NEEDED"* ]] || [[ "$line" == *"MANUAL PROOF STALE"* ]]; then
    RULE=$(echo "$line" | sed 's/^[[:space:]]*//')
    WARNINGS="${WARNINGS}  ${CURRENT_FEATURE%%:*} → ${RULE}\n"
  fi
  if [[ "$line" =~ ": READY" ]]; then
    PASSES="${PASSES}  ${line%%:*}\n"
  fi
  if [[ "$line" =~ ": passing" ]]; then
    PASSES="${PASSES}  ${line%%:*}\n"
    # passing = all proofs pass but no receipt — blocked in strict mode
    NON_READY="${NON_READY}  ${line} (needs purlin:verify)\n"
  fi
  if [[ "$line" =~ "rules proved" ]] && [[ ! "$line" =~ READY ]] && [[ ! "$line" =~ passing ]] && [[ ! "$line" =~ ^[[:space:]] ]]; then
    NON_READY="${NON_READY}  ${line}\n"
  fi
done <<< "$STATUS"

# --- Report and decide ---
if [[ -n "$PASSES" ]]; then
  echo "purlin: passing features:"
  echo -e "$PASSES"
fi

if [[ -n "$WARNINGS" ]]; then
  echo "purlin: partial coverage:"
  echo -e "$WARNINGS"
fi

# Always block on FAIL (both modes)
if [[ -n "$FAILS" ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚠ PUSH BLOCKED — failing proofs detected"
  echo ""
  echo -e "$FAILS"
  echo "Fix failing proofs, then push again:"
  echo "  → Run: test <feature>"
  echo "  → Run: purlin:status"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi

# In strict mode, also block on non-READY
if [[ "$MODE" == "strict" ]] && [[ -n "$NON_READY" ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚠ PUSH BLOCKED (strict mode) — features not verified"
  echo ""
  echo -e "$NON_READY"
  echo ""
  echo "All features must be READY (passing + verified) before push in strict mode."
  echo "  → Run: test <feature> for partial features"
  echo "  → Run: purlin:verify for passing features"
  echo ""
  echo "To switch to warn mode: set \"pre_push\": \"warn\" in .purlin/config.json"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi

exit 0
