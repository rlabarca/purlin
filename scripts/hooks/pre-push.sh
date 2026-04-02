#!/usr/bin/env bash
# Purlin pre-push hook — Layer 1 enforcement for good-actor developers.
# Blocks push if any feature has FAILING proofs.
# Warns (but allows) if features have partial coverage (NO PROOF rules).
# Allows silently if all proofs pass or no specs exist.
set -euo pipefail

# --- Locate project root (walk up from repo root looking for .purlin/) ---
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ ! -d "$ROOT/.purlin" ]]; then
  exit 0  # Not a Purlin project — allow push
fi

SPEC_DIR="$ROOT/specs"
if [[ ! -d "$SPEC_DIR" ]] || [[ -z "$(find "$SPEC_DIR" -maxdepth 2 -name '*.md' 2>/dev/null | head -1)" ]]; then
  exit 0  # No specs yet — allow push
fi

# --- Run default-tier tests ---
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

echo "purlin: running default-tier tests ($FRAMEWORK)..."
case "$FRAMEWORK" in
  pytest) (cd "$ROOT" && python3 -m pytest -m "not slow" -q 2>&1) || true ;;
  jest)   (cd "$ROOT" && npx jest --testPathPattern=default 2>&1) || true ;;
  shell)  for t in "$ROOT"/*.test.sh; do [[ -f "$t" ]] && bash "$t" 2>&1; done || true ;;
esac

# --- Check sync_status for FAIL entries ---
SERVER="$ROOT/scripts/mcp/purlin_server.py"
if [[ ! -f "$SERVER" ]]; then
  # Purlin scripts not available (consumer project without bundled scripts)
  # Try CLAUDE_PLUGIN_ROOT
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
while IFS= read -r line; do
  if [[ "$line" =~ ^[a-zA-Z_] ]] && [[ ! "$line" =~ ^[[:space:]] ]]; then
    CURRENT_FEATURE="$line"
  fi
  if [[ "$line" == *": FAIL "* ]]; then
    RULE=$(echo "$line" | sed 's/^[[:space:]]*//')
    FAILS="${FAILS}  ${CURRENT_FEATURE%%:*} → ${RULE}\n"
  fi
  if [[ "$line" == *": NO PROOF "* ]]; then
    RULE=$(echo "$line" | sed 's/^[[:space:]]*//')
    WARNINGS="${WARNINGS}  ${CURRENT_FEATURE%%:*} → ${RULE}\n"
  fi
  if [[ "$line" =~ READY ]]; then
    PASSES="${PASSES}  ${line%%:*}\n"
  fi
done <<< "$STATUS"

# --- Report and decide ---
if [[ -n "$PASSES" ]]; then
  echo "purlin: passing features:"
  echo -e "$PASSES"
fi

if [[ -n "$WARNINGS" ]]; then
  echo "purlin: partial coverage (allowed, but consider adding proofs):"
  echo -e "$WARNINGS"
fi

if [[ -n "$FAILS" ]]; then
  echo ""
  echo "purlin: PUSH BLOCKED — failing proofs detected:"
  echo -e "$FAILS"
  echo "Directives:"
  echo "  1. Run 'purlin:unit-test' to see full failure details"
  echo "  2. Fix the failing tests or update the spec rules"
  echo "  3. Run 'purlin:status' to confirm all proofs pass"
  exit 1
fi

exit 0
