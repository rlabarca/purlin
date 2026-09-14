#!/usr/bin/env bash
# Walk the consumer fixture's workflow locally, step by step.
#
# `dev/fixtures/consumer-ci/` is a complete minimal consumer project: specs,
# `.purlin/`, a test file, and no Purlin `scripts/`, exactly as a project that
# installed Purlin from the marketplace looks. Its
# `.github/workflows/purlin.yml` is what a runner executes. This script reads
# that file, walks the steps it names against a copy of the fixture, and says
# PASS or FAIL for each one.
#
# Nothing here contacts a git host. There is no repository to create, no run to
# dispatch and no account to authenticate: the point is that a person can read
# what the workflow does before a runner ever does it.
#
# The record step needs `scripts/run/purlin_run.py`. When that file is not in
# this checkout yet the step is skipped with a message rather than failed, so
# the script is useful while the run script is still being written.
#
# USAGE
#   bash dev/consumer_ci_dryrun.sh            # walk the steps
#   bash dev/consumer_ci_dryrun.sh --keep     # keep the working copy and say where

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE="$REPO_ROOT/dev/fixtures/consumer-ci"
WORKFLOW_REL=".github/workflows/purlin.yml"
RUN_SCRIPT="$REPO_ROOT/scripts/run/purlin_run.py"

KEEP=0
FAILURES=0
SKIPPED=0

usage() {
  sed -n '2,21p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep)    KEEP=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "consumer_ci_dryrun: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '\n=== %s\n' "$*"; }
cmd()  { printf '+ %s\n' "$*"; }
pass() { printf 'PASS  %s\n' "$*"; }
skip() { printf 'SKIP  %s\n' "$*"; SKIPPED=$((SKIPPED + 1)); }
fail() { printf 'FAIL  %s\n' "$*"; FAILURES=$((FAILURES + 1)); }

WORK=""
cleanup() {
  if [[ $KEEP -eq 0 && -n "$WORK" && -d "$WORK" ]]; then
    rm -rf "$WORK"
  fi
  return 0
}
trap cleanup EXIT

# ── 1. the fixture, copied and committed ──────────────────────────────
say "Copy the fixture to a temporary directory and commit it"
WORK="$(mktemp -d -t purlin-consumer-ci)"
cmd "cp -R $FIXTURE/. $WORK/"
cp -R "$FIXTURE/." "$WORK/"
cd "$WORK"
cmd "git init -b main && git add -A && git commit"
git init -q -b main
git add -A
git -c user.name="purlin dry run" -c user.email="dryrun@example.com" \
    -c commit.gpgsign=false commit -q -m "Purlin consumer CI fixture"
pass "committed $(git ls-files | wc -l | tr -d ' ') files from the fixture"

# ── 2. the workflow the runner would read ─────────────────────────────
say "Read the steps the workflow names"
if [[ ! -f "$WORK/$WORKFLOW_REL" ]]; then
  fail "the fixture has no $WORKFLOW_REL"
  exit 1
fi
STEPS="$(grep -E '^      - (name|uses): ' "$WORK/$WORKFLOW_REL" \
         | sed -E 's/^ *- (name|uses): //')"
printf '%s\n' "$STEPS" | sed 's/^/  step: /'
pass "$(printf '%s\n' "$STEPS" | wc -l | tr -d ' ') steps"

# ── 3. Locate Purlin ──────────────────────────────────────────────────
# On a consumer's runner this clones the pinned release. Here the checkout the
# script lives in IS Purlin, so the step resolves to it and nothing is cloned.
say "Locate Purlin"
PURLIN_ROOT="$REPO_ROOT"
cmd "PURLIN_ROOT=$PURLIN_ROOT"
if [[ -d "$PURLIN_ROOT/scripts/mcp/purlin" ]]; then
  pass "Purlin is this checkout"
else
  fail "no Purlin package at $PURLIN_ROOT/scripts/mcp/purlin"
fi

# ── 4. Set up the test framework ──────────────────────────────────────
# The workflow installs what the project's manifests call for. Installing into
# the developer's environment is not this script's business, so the step is
# reported rather than executed, and the framework is checked instead.
say "Set up the test framework"
if python3 -c 'import pytest' >/dev/null 2>&1; then
  pass "pytest is importable, which is what the fixture's conftest.py needs"
else
  fail "pytest is not importable; the workflow's install step would provide it"
fi

# ── 5. Run the tests the way the runner does ──────────────────────────
say "Run the fixture's tests"
cmd "python3 -m pytest tests -q"
if python3 -m pytest tests -q -p no:cacheprovider >/dev/null 2>&1; then
  pass "the fixture's tests pass"
else
  # PROOF-2 is a claim about a Linux host. On a Mac it fails honestly.
  if [[ "$(uname -s)" == "Linux" ]]; then
    fail "the fixture's tests failed on a Linux host"
  else
    skip "PROOF-2 is tagged @env(linux) and this host is $(uname -s)"
  fi
fi

# ── 6. Run verify and write the record ────────────────────────────────
say "Run verify and write the record"
if [[ -f "$RUN_SCRIPT" ]]; then
  cmd "python3 $RUN_SCRIPT --all --record"
  if python3 "$RUN_SCRIPT" --all --record; then
    pass "the run script finished"
  else
    fail "the run script exited non-zero"
  fi
  if compgen -G "$WORK/.purlin/records/greeting/*.json" >/dev/null; then
    pass "a record was written to .purlin/records/greeting/"
  else
    fail "no record was written"
  fi
else
  skip "scripts/run/purlin_run.py is not in this checkout yet"
fi

# ── 7. The dashboard artifact ─────────────────────────────────────────
say "Publish the dashboard the workflow uploads"
cmd "publish_dashboard($WORK, $WORK/artifact)"
if python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/scripts/run')
import ci
ci.publish_dashboard('$WORK', '$WORK/artifact')
" >/dev/null 2>&1; then
  pass "the artifact directory was written"
else
  fail "the dashboard could not be published"
fi

# ── 8. Result ─────────────────────────────────────────────────────────
say "Result"
if [[ $KEEP -eq 1 ]]; then
  printf 'KEPT  %s\n' "$WORK"
fi
printf '%s step(s) skipped.\n' "$SKIPPED"
if [[ $FAILURES -eq 0 ]]; then
  printf 'Every step that ran passed.\n'
  exit 0
fi
printf '%s step(s) failed.\n' "$FAILURES"
exit 1
