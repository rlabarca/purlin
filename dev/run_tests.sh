#!/usr/bin/env bash
# Run all Purlin dev tests and print summary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0
FAIL=0

run_suite() {
  local name="$1"
  shift
  echo ""
  echo "━━━ $name ━━━"
  if "$@"; then
    echo ">>> $name: PASSED"
    PASS=$((PASS + 1))
  else
    echo ">>> $name: FAILED"
    FAIL=$((FAIL + 1))
  fi
}

run_suite "MCP Server Tests" python3 "$SCRIPT_DIR/test_mcp_server.py" -v
run_suite "Gate Hook Tests" bash "$SCRIPT_DIR/test_gate_hook.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suites: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
[[ $FAIL -eq 0 ]]
