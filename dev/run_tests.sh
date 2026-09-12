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
# On exit the sweep writes TWO files under .purlin/runtime/ (gitignored).
#
# 1. test_run.json, the shared marker, with the commit, the suites and test
#    files it invoked, and the counts, so a receipt issuer can tell which run
#    its evidence came from. The write is a merge under proof_common RULE-19:
#    the proof plugins write the same marker as each run finishes, so their
#    `runs` entries and any field they added are kept, and the sweep replaces
#    only the summary it owns (its own counts, ok and test_files).
#
# 2. last_sweep.json, this script's own record of the same run: at, commit,
#    passed, failed, skipped, ok and suites, written whole and never merged
#    with anything. It exists because the shared marker cannot be trusted to
#    still describe the sweep: the plugins rewrite test_run.json as each run
#    finishes, the shell suites run before the pytest pool, so mid-sweep the
#    marker on disk is a plugin's with only that plugin's share of the counts.
#    Anything that needs the sweep's own counts (purlin_version RULE-9 checks
#    the RELEASE_NOTES Unreleased counts line against them) reads this file,
#    where no plugin writes, instead of guessing from a field on the shared one.
#
# `--fast` is the inner-loop run: it holds out the 15 shell suites and the
# browser suite (test_purlin_report.py), which together are nearly all of the
# wall clock, and writes NEITHER marker. Both files are read as the claim that
# every suite ran (proof_common RULE-19, purlin_version RULE-9 against
# last_sweep.json), and a partial run has no right to make that claim, so
# --fast leaves whatever the last whole sweep recorded in place rather than
# overwriting it with a subset. The held-out invocations stay in this file
# behind `if [[ $FAST -eq 0 ]]` rather than being deleted, because
# dev/test_sweep_completeness.py (proof_common PROOF-18) reads this file as
# text for `$SCRIPT_DIR/test_*` paths and a deleted line reads to it as a suite
# dropped from the sweep.
set -euo pipefail

FAST=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    *) echo "usage: $0 [--fast]" >&2; exit 2 ;;
  esac
done

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
LAST_SWEEP="$ROOT/.purlin/runtime/last_sweep.json"
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
# the sweep reached its end with no failed suite. Writes both the shared
# marker ($MARKER, merged with the plugin runs) and the sweep's own record
# ($LAST_SWEEP, written whole, never merged).
write_marker() {
  if [[ $FAST -eq 1 ]]; then
    rm -f "$PYTEST_LOG"
    echo "fast mode: no run marker written"
    return 0
  fi
  mkdir -p "$(dirname "$MARKER")" "$(dirname "$LAST_SWEEP")"
  PURLIN_RUN_SUITES="$SUITES" \
  PURLIN_RUN_TEST_FILES="$TEST_FILES" \
  PURLIN_RUN_SHELL_PASSED="$PASS" \
  PURLIN_RUN_SHELL_FAILED="$FAIL" \
  PURLIN_RUN_PYTEST_PASSED="$PYTEST_PASSED" \
  PURLIN_RUN_PYTEST_FAILED="$PYTEST_FAILED" \
  PURLIN_RUN_PYTEST_SKIPPED="$PYTEST_SKIPPED" \
  PURLIN_RUN_COMPLETE="$SWEEP_COMPLETE" \
  python3 - "$MARKER" "$LAST_SWEEP" <<'PY'
import datetime, json, os, subprocess, sys, time

marker = sys.argv[1]
last_sweep = sys.argv[2]
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

# The proof plugins write the same marker as they finish (proof_common
# RULE-19), so this write is a merge through that rule: an existing marker at
# this commit keeps its `runs` list and every field this sweep does not own,
# including fields a newer plugin added. What the sweep does own is the
# summary: it watched every suite, so its counts, its `ok` and its own
# `test_files` list replace whatever the plugin runs inside it recorded.
run = {}
for _attempt in range(3):
    try:
        with open(marker) as f:
            existing = json.load(f)
        if isinstance(existing, dict) and existing.get('commit') == commit:
            run = existing
        break
    except FileNotFoundError:
        break
    except (ValueError, OSError):
        # A plugin is mid-replace: read again before giving up.
        time.sleep(0.05)

at = datetime.datetime.now(datetime.timezone.utc).isoformat()
passed = py_passed + max(shell_passed, 0)
failed = py_failed + max(shell_failed, 0)
ok = (env['PURLIN_RUN_COMPLETE'] == '1'
      and int(env['PURLIN_RUN_SHELL_FAILED']) == 0)


def write_atomic(path, payload):
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'w') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    os.replace(tmp, path)


run.update({
    'at': at,
    'commit': commit,
    'sweep': 'dev/run_tests.sh',
    'suites': suites,
    'test_files': lines('PURLIN_RUN_TEST_FILES'),
    'passed': passed,
    'failed': failed,
    'skipped': py_skipped,
    'ok': ok,
})
run.setdefault('runs', [])
write_atomic(marker, run)

# The sweep's own record, written whole and never merged: no plugin writes
# this path, so the counts here are always the whole sweep's. purlin_version
# RULE-9 checks the RELEASE_NOTES Unreleased counts line against it.
write_atomic(last_sweep, {
    'at': at,
    'commit': commit,
    'passed': passed,
    'failed': failed,
    'skipped': py_skipped,
    'ok': ok,
    'suites': suites,
})

print(f'run marker: {marker} (ok={str(ok).lower()}, '
      f'{len(run["runs"])} plugin run(s) merged)')
print(f'sweep record: {last_sweep} '
      f'({passed} passed, {failed} failed, {py_skipped} skipped)')
PY
  rm -f "$PYTEST_LOG"
}
trap write_marker EXIT

# ── Shell tests first (proof files written per feature) ──────────────
# Held out by --fast: these 15 invocations are most of the sweep's wall clock.
if [[ $FAST -eq 0 ]]; then
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
run_suite "E2E Fake Audit LLM" bash "$SCRIPT_DIR/test_e2e_fake_audit_llm.sh"
else
  echo "fast mode: skipping the 15 shell suites"
fi

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
# test_purlin_report.py drives a real browser and adds roughly 80s. It is in
# the default run; only --fast holds it out, and then no marker is written.
# test_sweep_completeness.py checks this file against the committed proofs.
PYTEST_FILES=(
  "$SCRIPT_DIR/test_config_engine.py" \
  "$SCRIPT_DIR/test_mcp_server.py" \
  "$SCRIPT_DIR/test_purlin_docs.py" \
  "$SCRIPT_DIR/test_purlin_references.py" \
  "$SCRIPT_DIR/test_plugin_contract.py" \
  "$SCRIPT_DIR/test_tools_qa.py" \
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
  "$SCRIPT_DIR/test_init_scaffold.py" \
  "$SCRIPT_DIR/test_verify_gate.py" \
  "$SCRIPT_DIR/test_consumer_ci.py" \
  "$SCRIPT_DIR/test_drift.py" \
  "$SCRIPT_DIR/test_pre_commit_hook.py" \
  "$SCRIPT_DIR/test_refresh_digest_hook.py" \
  "$SCRIPT_DIR/test_pre_push_hook.py" \
  "$SCRIPT_DIR/test_e2e_spec_from_input.py" \
  "$SCRIPT_DIR/test_e2e_spec_migration.py" \
  "$SCRIPT_DIR/test_e2e_ui_extraction.py" \
  "$SCRIPT_DIR/test_claude_cli_helper.py" \
  "$SCRIPT_DIR/test_sweep_completeness.py"
)
if [[ $FAST -eq 0 ]]; then
  PYTEST_FILES+=("$SCRIPT_DIR/test_purlin_report.py")
else
  echo "fast mode: skipping the browser suite (dev/test_purlin_report.py)"
fi
run_suite "All Pytest Tests" run_pytest "${PYTEST_FILES[@]}" -v

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suites: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
SWEEP_COMPLETE=1
[[ $FAIL -eq 0 ]]
