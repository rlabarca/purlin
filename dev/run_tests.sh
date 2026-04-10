#!/usr/bin/env bash
# Run all Purlin dev tests and print summary.
#
# Shell tests run first. Then ALL pytest tests run in a single session so the
# proof plugin accumulates every proof before writing — no feature-scoped
# overwrite collisions between test files.
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

# ── Shell tests first (proof files written per feature) ──────────────
run_suite "Proof Plugins (Shell)" bash "$SCRIPT_DIR/test_proof_plugins.sh"
run_suite "E2E Teammate Audit Loop" bash "$SCRIPT_DIR/test_e2e_teammate_audit_loop.sh"
run_suite "E2E Build Changeset" bash "$SCRIPT_DIR/test_e2e_build_changeset.sh"

# ── All pytest tests in a single session ─────────────────────────────
# Running in one session ensures the proof plugin collects ALL markers
# before writing proof files, avoiding feature-scoped overwrite between
# separate pytest invocations.
run_suite "All Pytest Tests" pytest \
  "$SCRIPT_DIR/test_config_engine.py" \
  "$SCRIPT_DIR/test_mcp_server.py" \
  "$SCRIPT_DIR/test_purlin_references.py" \
  "$SCRIPT_DIR/test_purlin_agent.py" \
  "$SCRIPT_DIR/test_purlin_skills.py" \
  "$SCRIPT_DIR/test_skill_specs.py" \
  "$SCRIPT_DIR/test_schema_spec_format.py" \
  "$SCRIPT_DIR/test_schema_proof_format.py" \
  "$SCRIPT_DIR/test_security.py" \
  "$SCRIPT_DIR/test_static_checks.py" \
  "$SCRIPT_DIR/test_e2e_audit_cache_pipeline.py" \
  "$SCRIPT_DIR/test_multilang_proof_plugins.py" \
  "$SCRIPT_DIR/test_purlin_teammate_definitions.py" \
  -v

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suites: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
[[ $FAIL -eq 0 ]]
