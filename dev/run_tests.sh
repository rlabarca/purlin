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

run_suite "Config Engine" pytest "$SCRIPT_DIR/test_config_engine.py" -v
run_suite "MCP Server" pytest "$SCRIPT_DIR/test_mcp_server.py" -v
run_suite "Purlin References" pytest "$SCRIPT_DIR/test_purlin_references.py" -v
run_suite "Purlin Agent" pytest "$SCRIPT_DIR/test_purlin_agent.py" -v
run_suite "Purlin Skills" pytest "$SCRIPT_DIR/test_purlin_skills.py" -v
run_suite "Schema Spec Format" pytest "$SCRIPT_DIR/test_schema_spec_format.py" -v
run_suite "Schema Proof Format" pytest "$SCRIPT_DIR/test_schema_proof_format.py" -v
run_suite "Security Patterns" pytest "$SCRIPT_DIR/test_security.py" -v
run_suite "Gate Hook" bash "$SCRIPT_DIR/test_gate_hook.sh"
run_suite "Proof Plugins" bash "$SCRIPT_DIR/test_proof_plugins.sh"
run_suite "Session Start" bash "$SCRIPT_DIR/test_session_start.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suites: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
[[ $FAIL -eq 0 ]]
