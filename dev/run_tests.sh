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
#
# Completeness (proof_common RULE-14): every test file named by a committed
# proof entry is either invoked here or listed in that rule's exception list.
# dev/test_sweep_completeness.py parses this file for `$SCRIPT_DIR/test_*`
# references, so a suite added below is counted and a suite removed below fails
# the sweep. Suites that need a runner this machine lacks (Windows, Figma MCP,
# gemini CLI, a paid claude session) are the exceptions and stay out.
#
# On exit the sweep writes .purlin/runtime/test_run.json (gitignored) with the
# commit, the suites and test files it invoked, and the counts, so a receipt
# issuer can tell which run its evidence came from.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
# Newline-separated accumulators rather than arrays: /bin/bash on macOS is 3.2,
# where expanding an empty array under `set -u` is an error.
SUITES=""
TEST_FILES=""
PYTEST_PASSED=0
PYTEST_FAILED=0
PYTEST_SKIPPED=0
SWEEP_COMPLETE=0
MARKER="$ROOT/.purlin/runtime/test_run.json"
PYTEST_LOG="$(mktemp -t purlin-pytest.XXXXXX)"

# Record each dev/test_* path an invocation names, project-relative.
record_test_files() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      "$SCRIPT_DIR"/test_*) TEST_FILES="${TEST_FILES}dev/$(basename "$arg")"$'\n' ;;
    esac
  done
}

run_suite() {
  local name="$1"
  shift
  echo ""
  echo "━━━ $name ━━━"
  SUITES="${SUITES}${name}"$'\n'
  record_test_files "$@"
  if "$@"; then
    echo ">>> $name: PASSED"
    PASS=$((PASS + 1))
  else
    echo ">>> $name: FAILED"
    FAIL=$((FAIL + 1))
  fi
}

# Runs pytest and reads the counts off its final summary line
# ("=== N passed, M skipped in 1.2s ==="); the exit status is pytest's own.
run_pytest() {
  local status=0
  pytest "$@" 2>&1 | tee "$PYTEST_LOG" || status=$?
  local summary
  summary="$(grep -E '^=+ .*[0-9]+ (passed|failed|skipped|error).* in [0-9.]+s' "$PYTEST_LOG" | tail -1 || true)"
  PYTEST_PASSED="$(echo "$summary" | grep -oE '[0-9]+ passed' | awk '{print $1}')"
  PYTEST_FAILED="$(echo "$summary" | grep -oE '[0-9]+ failed' | awk '{print $1}')"
  PYTEST_SKIPPED="$(echo "$summary" | grep -oE '[0-9]+ skipped' | awk '{print $1}')"
  PYTEST_PASSED="${PYTEST_PASSED:-0}"
  PYTEST_FAILED="${PYTEST_FAILED:-0}"
  PYTEST_SKIPPED="${PYTEST_SKIPPED:-0}"
  return "$status"
}

# Written on every exit, including an abort partway: `ok` is true only when
# the sweep reached its end with no failed suite.
write_marker() {
  mkdir -p "$(dirname "$MARKER")"
  PURLIN_RUN_SUITES="$SUITES" \
  PURLIN_RUN_TEST_FILES="$TEST_FILES" \
  PURLIN_RUN_SHELL_PASSED="$PASS" \
  PURLIN_RUN_SHELL_FAILED="$FAIL" \
  PURLIN_RUN_PYTEST_PASSED="$PYTEST_PASSED" \
  PURLIN_RUN_PYTEST_FAILED="$PYTEST_FAILED" \
  PURLIN_RUN_PYTEST_SKIPPED="$PYTEST_SKIPPED" \
  PURLIN_RUN_COMPLETE="$SWEEP_COMPLETE" \
  python3 - "$MARKER" <<'PY'
import datetime, json, os, subprocess, sys

marker = sys.argv[1]
env = os.environ
lines = lambda key: [l for l in env.get(key, '').split('\n') if l]
suites = lines('PURLIN_RUN_SUITES')
# The pytest pool counts as one suite in PASS/FAIL; its tests are counted
# individually below, so subtract the pool from the suite tally.
shell_passed = int(env['PURLIN_RUN_SHELL_PASSED'])
shell_failed = int(env['PURLIN_RUN_SHELL_FAILED'])
py_passed = int(env['PURLIN_RUN_PYTEST_PASSED'])
py_failed = int(env['PURLIN_RUN_PYTEST_FAILED'])
py_skipped = int(env['PURLIN_RUN_PYTEST_SKIPPED'])
pool_ran = 'All Pytest Tests' in suites
if pool_ran:
    if py_failed:
        shell_failed -= 1
    else:
        shell_passed -= 1
commit = subprocess.run(['git', 'rev-parse', 'HEAD'],
                        capture_output=True, text=True).stdout.strip() or None
run = {
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'commit': commit,
    'sweep': 'dev/run_tests.sh',
    'suites': suites,
    'test_files': lines('PURLIN_RUN_TEST_FILES'),
    'passed': py_passed + max(shell_passed, 0),
    'failed': py_failed + max(shell_failed, 0),
    'skipped': py_skipped,
    'ok': env['PURLIN_RUN_COMPLETE'] == '1'
          and int(env['PURLIN_RUN_SHELL_FAILED']) == 0,
}
with open(marker, 'w') as f:
    json.dump(run, f, indent=2)
    f.write('\n')
print(f'run marker: {marker} (ok={str(run["ok"]).lower()})')
PY
  rm -f "$PYTEST_LOG"
}
trap write_marker EXIT

# ── Shell tests first (proof files written per feature) ──────────────
run_suite "Proof Plugins (Shell)" bash "$SCRIPT_DIR/test_proof_plugins.sh"
run_suite "E2E Teammate Audit Loop" bash "$SCRIPT_DIR/test_e2e_teammate_audit_loop.sh"
run_suite "E2E Build Changeset" bash "$SCRIPT_DIR/test_e2e_build_changeset.sh"
run_suite "E2E Init" bash "$SCRIPT_DIR/test_init_e2e.sh"
run_suite "E2E Write-Scoped Overwrite" bash "$SCRIPT_DIR/test_e2e_feature_scoped_overwrite.sh"
# The dog-food external reference repo; idempotent, creates it once.
bash "$SCRIPT_DIR/setup-external-refs.sh"
run_suite "E2E External Refs" bash "$SCRIPT_DIR/test_e2e_external_refs.sh"
run_suite "E2E Strict Required" bash "$SCRIPT_DIR/test_e2e_strict_required.sh"
run_suite "E2E Manual Staleness" bash "$SCRIPT_DIR/test_e2e_manual_staleness.sh"
run_suite "E2E Required Rules" bash "$SCRIPT_DIR/test_e2e_required_rules.sh"
run_suite "E2E Verify Audit" bash "$SCRIPT_DIR/test_e2e_verify_audit.sh"
run_suite "E2E Anchor Authority" bash "$SCRIPT_DIR/test_e2e_anchor_authority.sh"
run_suite "E2E Hybrid Audit" bash "$SCRIPT_DIR/test_e2e_hybrid_audit.sh"
run_suite "E2E Additional Criteria" bash "$SCRIPT_DIR/test_e2e_additional_criteria.sh"

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
# test_sweep_completeness.py checks this file against the committed proofs.
run_suite "All Pytest Tests" run_pytest \
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
  "$SCRIPT_DIR/test_receipts.py" \
  "$SCRIPT_DIR/test_init_update.py" \
  "$SCRIPT_DIR/test_verify_gate.py" \
  "$SCRIPT_DIR/test_drift.py" \
  "$SCRIPT_DIR/test_pre_push_hook.py" \
  "$SCRIPT_DIR/test_e2e_spec_from_input.py" \
  "$SCRIPT_DIR/test_e2e_spec_migration.py" \
  "$SCRIPT_DIR/test_e2e_ui_extraction.py" \
  "$SCRIPT_DIR/test_sweep_completeness.py" \
  "$SCRIPT_DIR/test_purlin_report.py" \
  -v

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suites: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
SWEEP_COMPLETE=1
[[ $FAIL -eq 0 ]]
