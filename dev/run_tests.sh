#!/usr/bin/env bash
# Run the Purlin dev tests and print a summary. The shell suites run first,
# then one pytest session over every dev/test_*.py; pooling the pytest files
# is a speed choice, not a correctness one. This is the maintainer's sweep; the
# evidence path is `purlin_run.py`, which runs the suites `.purlin/config.json`
# names.
#
# `--fast` holds out the shell suites and the browser suites
# (dev/test_purlin_report*.py), nearly all of the wall clock.
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
# The shell suites call python3 by name; put the repository venv first so
# that name carries pytest.
if [[ -x "$ROOT/.venv/bin/python3" ]]; then export PATH="$ROOT/.venv/bin:$PATH"; fi
cd "$ROOT"

PASS=0; FAIL=0

run_suite() {
  local name="$1"
  shift
  printf '\n━━━ %s ━━━\n' "$name"
  if "$@"; then
    echo ">>> $name: PASSED"
    PASS=$((PASS + 1))
  else
    echo ">>> $name: FAILED"
    FAIL=$((FAIL + 1))
  fi
}

# ── Shell suites first ───────────────────────────────────────────────
# Held out by `--fast`: these invocations are most of the sweep's wall clock.
if [[ $FAST -eq 0 ]]; then
run_suite "E2E Build Changeset" bash "$SCRIPT_DIR/test_e2e_build_changeset.sh"
run_suite "E2E Init (gates)" bash "$SCRIPT_DIR/test_init_e2e_gates.sh"
run_suite "E2E Init (wiring)" bash "$SCRIPT_DIR/test_init_e2e_wiring.sh"
# The dog-food external reference repo; idempotent, creates it once.
bash "$SCRIPT_DIR/setup-external-refs.sh"
run_suite "E2E External Refs" bash "$SCRIPT_DIR/test_e2e_external_refs.sh"
run_suite "E2E Required Rules" bash "$SCRIPT_DIR/test_e2e_required_rules.sh"
run_suite "E2E Anchor Authority" bash "$SCRIPT_DIR/test_e2e_anchor_authority.sh"
else
  echo "--fast: skipping the shell suites"
fi

# ── All pytest tests in a single session ─────────────────────────────
# One session for speed. Correctness does not depend on it.
# Every dev/test_*.py, found rather than listed: a hand-kept list left new test
# files out of the sweep. The browser suites (test_purlin_report*.py) join below.
PYTEST_FILES=()
for test_file in "$SCRIPT_DIR"/test_*.py; do
  case "$(basename "$test_file")" in
    test_purlin_report*.py) ;;
    *) PYTEST_FILES+=("$test_file") ;;
  esac
done
# test_purlin_report.py drives a headless browser and adds roughly 80s. It is
# in the default run; only --fast holds it out.
if [[ $FAST -eq 0 ]]; then
  for test_file in "$SCRIPT_DIR"/test_purlin_report*.py; do
    PYTEST_FILES+=("$test_file")
  done
else
  echo "--fast: skipping the browser suites (dev/test_purlin_report*.py)"
fi
run_suite "All Pytest Tests" pytest "${PYTEST_FILES[@]}" -v

printf '\n━━━━━━━━━━━━━━━━━━━━━━━━━\nSuites: %d passed, %d failed\n━━━━━━━━━━━━━━━━━━━━━━━━━\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
