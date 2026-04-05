#!/usr/bin/env bash
# Purlin pre-push hook — Layer 1 enforcement.
#
# Modes (set in .purlin/config.json → "pre_push"):
#   "warn"   — block on FAILING, allow VERIFIED+PARTIAL (default)
#   "strict" — block on anything not VERIFIED (requires verification receipt)
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

# --- Parse summary table ---
# The summary table uses │-delimited rows: │ name │ N/M │ STATUS │
# Parsing the table avoids false positives from rule descriptions that
# contain status keywords (e.g. "RULE-8: FAIL status badge...").
FAILS=""
FAIL_FEATURES=""
PASSES=""
NON_READY=""
while IFS= read -r line; do
  # Match summary table rows: │ feature_name │ N/M │ STATUS │
  if [[ "$line" == *"│"* ]]; then
    # Extract fields by splitting on │
    FEAT=$(echo "$line" | awk -F'│' '{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
    STAT=$(echo "$line" | awk -F'│' '{gsub(/^[ \t]+|[ \t]+$/, "", $4); print $4}')
    COVERAGE=$(echo "$line" | awk -F'│' '{gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')
    # Skip header/border rows
    [[ -z "$FEAT" || "$FEAT" == "Feature" || "$FEAT" == *"─"* ]] && continue
    # Strip "(anchor)" suffix for feature name
    FEAT_NAME=$(echo "$FEAT" | sed 's/ *(anchor)$//')
    case "$STAT" in
      FAILING)
        FAILS="${FAILS}  ${FEAT_NAME} (${COVERAGE})\n"
        if [[ "$FAIL_FEATURES" != *"$FEAT_NAME"* ]]; then
          FAIL_FEATURES="${FAIL_FEATURES} ${FEAT_NAME}"
        fi
        ;;
      VERIFIED)
        PASSES="${PASSES}  ${FEAT_NAME}\n"
        ;;
      PASSING)
        PASSES="${PASSES}  ${FEAT_NAME}\n"
        ;;
      PARTIAL)
        PASSES="${PASSES}  ${FEAT_NAME}\n"
        NON_READY="${NON_READY}  ${FEAT_NAME} (${COVERAGE}, needs purlin:verify)\n"
        ;;
      UNTESTED)
        NON_READY="${NON_READY}  ${FEAT_NAME} (${COVERAGE}, untested)\n"
        ;;
    esac
  fi
done <<< "$STATUS"

# --- Report and decide ---
if [[ -n "$PASSES" ]]; then
  echo "purlin: passing features:"
  echo -e "$PASSES"
fi

if [[ -n "$NON_READY" ]] && [[ "$MODE" != "strict" ]]; then
  echo "purlin: partial coverage (not blocking in warn mode):"
  echo -e "$NON_READY"
fi

# Always block on FAIL (both modes)
if [[ -n "$FAILS" ]]; then
  FAIL_FEATURES="$(echo "$FAIL_FEATURES" | xargs)"  # trim whitespace
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "PUSH BLOCKED — failing proofs detected"
  echo ""
  echo "Failing rules:"
  echo -e "$FAILS"
  echo "RECOVERY STEPS"
  echo ""
  echo "Proofs may be stale (tests pass but proof files still record a"
  echo "prior failure). Re-emitting proofs will fix this. If the tests"
  echo "themselves are broken, fix the code first."
  echo ""
  echo "1. Re-run tests to re-emit proofs for each failing feature:"
  for feat in $FAIL_FEATURES; do
    echo "     /purlin:unit-test ${feat}"
  done
  echo ""
  echo "2. Confirm all rules pass:"
  echo "     /purlin:status"
  echo ""
  echo "3. If any rules still show FAIL, the test is genuinely broken."
  echo "   Fix with /purlin:build <feature>, then repeat from step 1."
  echo ""
  echo "4. Once status shows PASSING (no FAILs), retry the push."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi

# In strict mode, also block on non-VERIFIED
if [[ "$MODE" == "strict" ]] && [[ -n "$NON_READY" ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "PUSH BLOCKED (strict mode) — features not verified"
  echo ""
  echo -e "$NON_READY"
  echo ""
  echo "RECOVERY STEPS"
  echo ""
  echo "Strict mode requires all features to be VERIFIED (all rules"
  echo "proved with a current verification receipt)."
  echo ""
  echo "1. Run tests for features showing PARTIAL coverage:"
  echo "     /purlin:unit-test <feature>"
  echo ""
  echo "2. Check status to confirm all rules pass:"
  echo "     /purlin:status"
  echo ""
  echo "3. If any rules show FAIL, fix with /purlin:build <feature>,"
  echo "   then re-run /purlin:unit-test <feature>."
  echo ""
  echo "4. Once all features show PASSING, issue verification receipts:"
  echo "     /purlin:verify"
  echo ""
  echo "5. Retry the push."
  echo ""
  echo "To switch to warn mode (allows PARTIAL/UNTESTED):"
  echo "  Set \"pre_push\": \"warn\" in .purlin/config.json"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi

exit 0
