#!/usr/bin/env bash
# Run all Purlin dev tests and print summary.
#
# Shell tests run first, then the pytest tests. Since the proof merge key became
# (feature, tier, test_file), two test files covering one feature at one tier no
# longer clobber each other, so suites no longer have to be pooled into one
# process to survive. Pooling the pytest files is kept because it is faster, not
# because it is required.
#
# Still true at the FILE level: running a subset of the tests inside one file
# replaces that file's entries for the features it touches, so the proofs from
# the tests you skipped go away. Run whole files.
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
run_suite "E2E Init" bash "$SCRIPT_DIR/test_init_e2e.sh"
run_suite "E2E Write-Scoped Overwrite" bash "$SCRIPT_DIR/test_e2e_feature_scoped_overwrite.sh"

# ── All pytest tests in a single session ─────────────────────────────
# One session for speed. Correctness no longer depends on it: the merge key
# includes test_file, so these files can coexist in one proof file.
#
# test_proof_plugins_missing.py, test_proof_stress.py and test_cheat_matrix.py
# were held out of the sweep because they collided with test_proof_plugins.sh
# and each other over proof_common@unit, static_checks@unit and
# sync_status@unit. Running them used to delete roughly a thousand lines of
# another file's proofs, which is why proof_common PROOF-10/11/12 were specced
# but absent from every committed proof file. With the merge key fixed they
# belong in the sweep.
#
# test_purlin_report.py drives a real browser and adds roughly 80s.
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
  "$SCRIPT_DIR/test_proof_plugins_missing.py" \
  "$SCRIPT_DIR/test_proof_stress.py" \
  "$SCRIPT_DIR/test_cheat_matrix.py" \
  "$SCRIPT_DIR/test_purlin_teammate_definitions.py" \
  "$SCRIPT_DIR/test_purlin_report_markup.py" \
  "$SCRIPT_DIR/test_purlin_version.py" \
  "$SCRIPT_DIR/test_report_data.py" \
  "$SCRIPT_DIR/test_purlin_report.py" \
  -v

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suites: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
[[ $FAIL -eq 0 ]]
