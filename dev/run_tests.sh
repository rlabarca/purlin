#!/usr/bin/env bash
# Run the Purlin dev tests and print a summary. The shell suites run first,
# then one pytest session over the rest; pooling the pytest files is a speed
# choice, not a correctness one, because the proof merge key is (feature,
# tier, test_file). Running a subset of the tests inside one file still
# replaces that file's entries for the features it touches, so run whole files.
#
# On exit the sweep writes two gitignored files under .purlin/runtime/.
# test_run.json is the shared marker the proof plugins also write, so the
# sweep merges: their `runs` entries and any field they added survive, and
# only the summary the sweep owns is replaced. last_sweep.json is the sweep's
# own copy of those counts, written whole, because partway through a run the
# shared marker is a plugin's and carries only that plugin's share;
# dev/test_purlin_version.py reads it to check the RELEASE_NOTES counts line.
#
# `--fast` holds out the shell suites and the browser suite
# (dev/test_purlin_report.py), nearly all of the wall clock, and writes neither
# file: both are read as the claim that every suite ran, and a partial run has
# no right to make it.
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
# The shell suites and the hooks they drive call python3 by name; put the
# repository venv first so that name carries pytest and the proof plugin.
if [[ -x "$ROOT/.venv/bin/python3" ]]; then export PATH="$ROOT/.venv/bin:$PATH"; fi
cd "$ROOT"

PASS=0; FAIL=0
# Newline-separated accumulators rather than arrays: /bin/bash on macOS is 3.2,
# where expanding an empty array under `set -u` is an error.
SUITES=""; TEST_FILES=""
PYTEST_PASSED=0; PYTEST_FAILED=0; PYTEST_SKIPPED=0
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
  printf '\n━━━ %s ━━━\n' "$name"
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
  local status=0 summary
  pytest "$@" 2>&1 | tee "$PYTEST_LOG" || status=$?
  summary="$(grep -E '^=+ .*[0-9]+ (passed|failed|skipped|error).* in [0-9.]+s' "$PYTEST_LOG" | tail -1 || true)"
  count() { echo "$summary" | grep -oE "[0-9]+ $1" | awk '{print $1}'; }
  PYTEST_PASSED="$(count passed)"; PYTEST_PASSED="${PYTEST_PASSED:-0}"
  PYTEST_FAILED="$(count failed)"; PYTEST_FAILED="${PYTEST_FAILED:-0}"
  PYTEST_SKIPPED="$(count skipped)"; PYTEST_SKIPPED="${PYTEST_SKIPPED:-0}"
  return "$status"
}

# Written on every exit, including an abort partway: `ok` is true only when
# the sweep reached its end with no failed suite.
write_marker() {
  if [[ $FAST -eq 1 ]]; then
    rm -f "$PYTEST_LOG"
    echo "--fast: no run marker written"
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
marker, last_sweep = sys.argv[1], sys.argv[2]
env = os.environ
lines = lambda key: [l for l in env.get(key, '').split('\n') if l]
num = lambda key: int(env[key])
suites = lines('PURLIN_RUN_SUITES')
shell_passed, shell_failed = num('PURLIN_RUN_SHELL_PASSED'), num('PURLIN_RUN_SHELL_FAILED')
py_passed, py_failed = num('PURLIN_RUN_PYTEST_PASSED'), num('PURLIN_RUN_PYTEST_FAILED')
py_skipped = num('PURLIN_RUN_PYTEST_SKIPPED')
# The pool counts as one suite in PASS/FAIL and its tests are counted
# individually, so drop the pool from the suite tally.
if 'All Pytest Tests' in suites:
    if py_failed:
        shell_failed -= 1
    else:
        shell_passed -= 1
commit = subprocess.run(['git', 'rev-parse', 'HEAD'],
                        capture_output=True, text=True).stdout.strip() or None

# The proof plugins write this marker too, so an existing marker at this
# commit keeps its `runs` list and every field the sweep does not own.
run = {}
for _attempt in range(3):
    try:
        with open(marker, encoding='utf-8') as f:
            existing = json.load(f)
        if isinstance(existing, dict) and existing.get('commit') == commit:
            run = existing
        break
    except FileNotFoundError:
        break
    except (ValueError, OSError):
        time.sleep(0.05)  # a plugin is partway through a replace

def write_atomic(path, payload):
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    os.replace(tmp, path)

# Nothing below may be a line of just `}`: dev/test_purlin_version.py cuts this function out with sed up to /^}$/.
summary = dict(
    at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    commit=commit,
    passed=py_passed + max(shell_passed, 0),
    failed=py_failed + max(shell_failed, 0),
    skipped=py_skipped,
    ok=num('PURLIN_RUN_COMPLETE') == 1 and num('PURLIN_RUN_SHELL_FAILED') == 0,
    suites=suites,
)
run.update(summary)
run.update({'sweep': 'dev/run_tests.sh', 'test_files': lines('PURLIN_RUN_TEST_FILES')})
run.setdefault('runs', [])
write_atomic(marker, run)
write_atomic(last_sweep, summary)
print('run marker: %s (ok=%s, %d plugin run(s) merged)' % (marker, str(summary['ok']).lower(), len(run['runs'])))
print('sweep record: %s (%d passed, %d failed, %d skipped)' % (last_sweep, summary['passed'], summary['failed'], py_skipped))
PY
  rm -f "$PYTEST_LOG"
}
trap write_marker EXIT

# ── Shell suites first (proof files written per feature) ─────────────
# Held out by `--fast`: these invocations are most of the sweep's wall clock.
if [[ $FAST -eq 0 ]]; then
run_suite "Proof Plugins (Shell)" bash "$SCRIPT_DIR/test_proof_plugins.sh"
# test_proof_plugins.sh covers the behaviour the three plugins share; these
# three cover one plugin each, and it does not invoke them.
run_suite "Proof Plugin (pytest)" bash "$SCRIPT_DIR/test_proof_pytest.sh"
run_suite "Proof Plugin (jest)" bash "$SCRIPT_DIR/test_proof_jest.sh"
run_suite "Proof Plugin (shell)" bash "$SCRIPT_DIR/test_proof_shell.sh"
run_suite "E2E Build Changeset" bash "$SCRIPT_DIR/test_e2e_build_changeset.sh"
run_suite "E2E Init" bash "$SCRIPT_DIR/test_init_e2e.sh"
run_suite "E2E Write-Scoped Overwrite" bash "$SCRIPT_DIR/test_e2e_feature_scoped_overwrite.sh"
# The dog-food external reference repo; idempotent, creates it once.
bash "$SCRIPT_DIR/setup-external-refs.sh"
run_suite "E2E External Refs" bash "$SCRIPT_DIR/test_e2e_external_refs.sh"
run_suite "E2E Required Rules" bash "$SCRIPT_DIR/test_e2e_required_rules.sh"
run_suite "E2E Anchor Authority" bash "$SCRIPT_DIR/test_e2e_anchor_authority.sh"
else
  echo "--fast: skipping the shell suites"
fi

# ── All pytest tests in a single session ─────────────────────────────
# One session for speed. Correctness does not depend on it: the merge key
# includes test_file, so these files can coexist in one proof file.
PYTEST_FILES=(
  "$SCRIPT_DIR/test_config_engine.py" "$SCRIPT_DIR/test_mcp_server.py" \
  "$SCRIPT_DIR/test_plugin_contract.py" "$SCRIPT_DIR/test_schema_spec_format.py" \
  "$SCRIPT_DIR/test_schema_proof_format.py" "$SCRIPT_DIR/test_security.py" \
  "$SCRIPT_DIR/test_static_checks.py" "$SCRIPT_DIR/test_multilang_proof_plugins.py" \
  "$SCRIPT_DIR/test_proof_plugins_missing.py" "$SCRIPT_DIR/test_proof_stress.py" \
  "$SCRIPT_DIR/test_purlin_version.py" "$SCRIPT_DIR/test_init_update.py" \
  "$SCRIPT_DIR/test_init_scaffold.py" "$SCRIPT_DIR/test_verify_gate.py" \
  "$SCRIPT_DIR/test_consumer_ci.py" "$SCRIPT_DIR/test_drift.py" \
  "$SCRIPT_DIR/test_refresh_digest_hook.py" "$SCRIPT_DIR/test_pre_push_hook.py" \
  "$SCRIPT_DIR/test_vocabulary.py" "$SCRIPT_DIR/test_mutation_adapters.py" \
  "$SCRIPT_DIR/test_records.py" "$SCRIPT_DIR/test_run_script.py" \
  "$SCRIPT_DIR/test_scan.py" "$SCRIPT_DIR/test_upstream.py"
)
# test_purlin_report.py drives a headless browser and adds roughly 80s. It is
# in the default run; only --fast holds it out, and then no marker is written.
if [[ $FAST -eq 0 ]]; then
  PYTEST_FILES+=("$SCRIPT_DIR/test_purlin_report.py")
else
  echo "--fast: skipping the browser suite (dev/test_purlin_report.py)"
fi
run_suite "All Pytest Tests" run_pytest "${PYTEST_FILES[@]}" -v

printf '\n━━━━━━━━━━━━━━━━━━━━━━━━━\nSuites: %d passed, %d failed\n━━━━━━━━━━━━━━━━━━━━━━━━━\n' "$PASS" "$FAIL"
SWEEP_COMPLETE=1
[[ $FAIL -eq 0 ]]
