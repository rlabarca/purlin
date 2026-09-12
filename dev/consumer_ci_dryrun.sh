#!/usr/bin/env bash
# The live dry run of Purlin's remote verification loop, from a consumer's side.
#
# `dev/fixtures/consumer-ci/` is a complete minimal consumer project: it holds
# specs, proofs, `.purlin/` and no Purlin `scripts/`, exactly as a real consumer
# checkout does. This script pushes it to a scratch GitHub repository, dispatches
# both of its workflows, and asserts what came back:
#
#   1. the commit-back carries BOTH provenance trailers, readable through
#      `git log -1 --format='%(trailers:key=...,valueonly)'` (they share one
#      `-m`; two `-m` flags would read correctly in `git log` and be invisible
#      here, which is the whole point of asserting it this way),
#   2. the scoped proof file `*.proofs-unit@ubuntu-24.json` came back and its
#      payload names `"platform": "ubuntu-24"` (an unscoped run would have
#      written the agnostic file and satisfied nothing),
#   3. `scripts/ci/verify_gate.py --check` exits 0 against the pulled checkout,
#   4. the scratch repository is deleted, unless it is kept.
#
# Two waits make it deterministic. `gh repo create --push` returns before
# GitHub has indexed the workflow files, so a dispatch fired straight after it
# 404s with `workflow not found on the default branch`; the script polls
# `gh workflow list` until both workflows are `active` first. And `--push`
# fires both workflows on `push` as well as the dispatch, so the script waits
# for the push runs, then dispatches, then watches the `workflow_dispatch`
# runs by id: every run it asserts on is one it named.
#
# It is `specs/ci/consumer_ci.md` RULE-3, and the proof of that rule is a
# `@manual` stamp: this script creates and destroys a real repository under a
# real account, so nothing about it is something a test suite may do by itself.
#
# USAGE
#   bash dev/consumer_ci_dryrun.sh --dry-run   # print every command, run no gh
#   bash dev/consumer_ci_dryrun.sh             # live, and KEEP the scratch repo
#   bash dev/consumer_ci_dryrun.sh --delete    # live, and delete it at the end
#
# The scratch repository is KEPT by default. The first live run is the one most
# likely to fail, and a deleted repository takes its workflow logs with it.
# `--delete` is the deliberate second run; `--keep` is the default said out loud.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE="$REPO_ROOT/dev/fixtures/consumer-ci"
GATE="$REPO_ROOT/scripts/ci/verify_gate.py"

SCRATCH_NAME="purlin-consumer-ci-scratch"
PLATFORM_ID="ubuntu-24"
RUNS_ON="ubuntu-24.04"
PROOF_GLOB="*.proofs-unit@${PLATFORM_ID}.json"
# The two the fixture ships: the file `gh workflow run` dispatches, and the
# `name:` the workflow declares, which is what `gh workflow list` reports.
WORKFLOW_FILES=("purlin-${PLATFORM_ID}-proofs.yml" "verify-gate.yml")
WORKFLOW_NAMES=("purlin-${PLATFORM_ID}-proofs" "verify-gate")

# How long to wait for GitHub to index the pushed workflow files, and how
# often to ask. 180s is a long way past what it has ever taken; the point is
# that the script never dispatches into the window where it 404s.
REGISTER_TIMEOUT=180
REGISTER_INTERVAL=5
# How long to wait for a run to appear after the event that should create it.
RUN_APPEAR_TIMEOUT=120

DRY_RUN=0
KEEP=1
FAILURES=0
PUSH_RUNS=""
DISPATCH_RUNS=""

usage() {
  sed -n '2,38p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --keep)    KEEP=1 ;;
    --delete)  KEEP=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "consumer_ci_dryrun: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\n=== %s\n' "$*"; }
cmd() { printf '+ %s\n' "$*"; }

# Every `gh` call goes through here, so `--dry-run` cannot touch an account by
# accident: the dry-run branch returns before the command is ever built.
gh_run() {
  cmd "$*"
  if [[ $DRY_RUN -eq 1 ]]; then
    return 0
  fi
  "$@"
}

# Captures a `gh` call's stdout into the named variable. In a dry run the
# variable gets a readable placeholder instead, so the printed plan still shows
# what the later commands would be shaped like.
gh_capture() {
  local var="$1" placeholder="$2"; shift 2
  cmd "$*"
  if [[ $DRY_RUN -eq 1 ]]; then
    printf -v "$var" '%s' "$placeholder"
    return 0
  fi
  local out
  out="$("$@")"
  printf -v "$var" '%s' "$out"
}

check() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    printf 'PASS  %s: %s\n' "$label" "$actual"
  else
    printf 'FAIL  %s: expected %s, got %s\n' "$label" "$expected" "$actual"
    FAILURES=$((FAILURES + 1))
  fi
}

# An assertion that a dry run can only describe: it reads state that exists
# solely because a runner produced it.
would() { printf 'WOULD ASSERT  %s\n' "$*"; }

WORK=""
cleanup() {
  if [[ -n "$WORK" && -d "$WORK" ]]; then
    rm -rf "$WORK"
  fi
  return 0
}
trap cleanup EXIT

# ── 1. the fixture, copied and committed ──────────────────────────────
say "Copy the fixture to a temp directory and commit it"
WORK="$(mktemp -d -t purlin-consumer-ci)"
cmd "cp -R $FIXTURE/. $WORK/"
cp -R "$FIXTURE/." "$WORK/"
cd "$WORK"
cmd "git init -b main && git add -A && git commit -m 'Purlin consumer CI scratch'"
git init -q -b main
git add -A
git -c user.name="purlin dry run" -c user.email="dryrun@example.com" \
    commit -q -m "Purlin consumer CI scratch"
printf 'committed %s files from the fixture\n' "$(git ls-files | wc -l | tr -d ' ')"

# ── 2. the scratch repository ─────────────────────────────────────────
say "Create the private scratch repository and push"
gh_capture GH_USER '<user>' gh api user --jq .login
REPO_SLUG="$GH_USER/$SCRATCH_NAME"
gh_run gh repo create "$REPO_SLUG" --private --source . --push

# ── 3. wait for GitHub to register both workflows ────────────
# `gh repo create --push` returns before GitHub has indexed the workflow files
# on the default branch. A dispatch inside that window fails with
# `HTTP 404: workflow not found on the default branch`, while `gh workflow
# list` shows both workflows `active` seconds later. So poll the list, and
# dispatch nothing until both names are there and active.
say "Wait for GitHub to register both workflows"

registered() {
  python3 - "$1" "${WORKFLOW_NAMES[@]}" <<'PY'
import json
import sys
try:
    listing = json.loads(sys.argv[1] or '[]')
except ValueError:
    listing = []
active = set()
for entry in listing:
    if isinstance(entry, dict) and entry.get('state') == 'active':
        active.add(entry.get('name'))
sys.exit(0 if all(name in active for name in sys.argv[2:]) else 1)
PY
}

cmd "gh workflow list --repo $REPO_SLUG --json name,state  # every ${REGISTER_INTERVAL}s, up to ${REGISTER_TIMEOUT}s"
if [[ $DRY_RUN -eq 1 ]]; then
  would "both of '${WORKFLOW_NAMES[*]}' are listed active before anything is dispatched"
else
  WAITED=0
  LISTING='[]'
  while true; do
    LISTING="$(gh workflow list --repo "$REPO_SLUG" --json name,state 2>/dev/null || printf '[]')"
    if registered "$LISTING"; then
      printf 'both workflows active after %ss: %s\n' "$WAITED" "$LISTING"
      break
    fi
    if [[ $WAITED -ge $REGISTER_TIMEOUT ]]; then
      printf 'FAIL  GitHub had not registered both workflows after %ss.\n' \
             "$REGISTER_TIMEOUT" >&2
      printf 'gh workflow list --repo %s --json name,state showed:\n%s\n' \
             "$REPO_SLUG" "$LISTING" >&2
      exit 1
    fi
    sleep "$REGISTER_INTERVAL"
    WAITED=$((WAITED + REGISTER_INTERVAL))
  done
fi

# The newest run of one workflow for one event, or nothing when there is none.
latest_run() {
  gh run list --repo "$REPO_SLUG" --workflow "$1" --event "$2" --branch main \
    --limit 1 --json databaseId --jq '.[0].databaseId // empty'
}

# ── 4. the push-triggered runs, before any dispatch ───────────
# `--push` fires both workflows on `push` as well as the dispatch below. The
# proofs workflow commits its scoped file back, so two live runs of it would
# race for one branch and hand the three-attempt rebase loop a conflict it
# cannot resolve. Let the push runs finish first: the dispatch then starts
# from a branch that already carries the commit-back, and every run this
# script watches is named by id, never "the latest one".
say "Wait for the push-triggered runs to finish"
for workflow in "${WORKFLOW_FILES[@]}"; do
  cmd "gh run list --repo $REPO_SLUG --workflow $workflow --event push --branch main --limit 1"
  if [[ $DRY_RUN -eq 1 ]]; then
    would "the push-triggered run of $workflow finishes before anything is dispatched"
    continue
  fi
  waited=0
  run_id=""
  while true; do
    run_id="$(latest_run "$workflow" push || true)"
    if [[ -n "$run_id" ]]; then
      break
    fi
    if [[ $waited -ge $RUN_APPEAR_TIMEOUT ]]; then
      break
    fi
    sleep 5
    waited=$((waited + 5))
  done
  if [[ -z "$run_id" ]]; then
    printf 'no push-triggered run of %s within %ss; nothing to serialise against\n' \
           "$workflow" "$RUN_APPEAR_TIMEOUT"
    continue
  fi
  printf 'push run of %s: %s\n' "$workflow" "$run_id"
  PUSH_RUNS="$PUSH_RUNS $workflow=$run_id"
  gh_run gh run watch "$run_id" --repo "$REPO_SLUG" --exit-status
done

# ── 5. dispatch both workflows and watch the dispatched runs ────
# `--event workflow_dispatch` cannot return a push run, so the id captured
# here is the dispatched run and nothing else. That is the run the assertions
# below describe.
say "Dispatch both workflows on main and wait for the dispatched runs"
for workflow in "${WORKFLOW_FILES[@]}"; do
  gh_run gh workflow run "$workflow" --repo "$REPO_SLUG" --ref main
done
for workflow in "${WORKFLOW_FILES[@]}"; do
  cmd "gh run list --repo $REPO_SLUG --workflow $workflow --event workflow_dispatch --branch main --limit 1"
  if [[ $DRY_RUN -eq 1 ]]; then
    would "the workflow_dispatch run of $workflow finishes 'completed success'"
    continue
  fi
  waited=0
  run_id=""
  while true; do
    run_id="$(latest_run "$workflow" workflow_dispatch || true)"
    if [[ -n "$run_id" ]]; then
      break
    fi
    if [[ $waited -ge $RUN_APPEAR_TIMEOUT ]]; then
      printf 'FAIL  no workflow_dispatch run of %s appeared within %ss\n' \
             "$workflow" "$RUN_APPEAR_TIMEOUT" >&2
      exit 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
  printf 'dispatched run of %s: %s\n' "$workflow" "$run_id"
  DISPATCH_RUNS="$DISPATCH_RUNS $workflow=$run_id"
  gh_run gh run watch "$run_id" --repo "$REPO_SLUG" --exit-status
done

# ── 6. pull the commit-back ───────────────────────────────────────────
say "Pull what the runner committed back"
if [[ $DRY_RUN -eq 1 ]]; then
  cmd "git pull --ff-only"
else
  git pull --ff-only || { sleep 5; git pull --ff-only; }
fi

# ── 7. the four assertions ────────────────────────────────────────────
say "Assertions"
SCOPED="$(find specs -name "$PROOF_GLOB" -print -quit 2>/dev/null || true)"

if [[ $DRY_RUN -eq 1 ]]; then
  would "git log -1 --format='%(trailers:key=Purlin-Runner,valueonly)' -- $PROOF_GLOB is 'github-actions/$RUNS_ON'"
  would "git log -1 --format='%(trailers:key=Purlin-Platform,valueonly)' -- $PROOF_GLOB is '$PLATFORM_ID'"
  would "specs/**/$PROOF_GLOB exists and its payload's platform is '$PLATFORM_ID'"
  cmd "python3 $GATE --check --project-root $WORK"
  would "the gate exits 0"
else
  RUNNER_TRAILER="$(git log -1 --format='%(trailers:key=Purlin-Runner,valueonly)' \
                    -- "$SCOPED" | tr -d '\n')"
  PLATFORM_TRAILER="$(git log -1 --format='%(trailers:key=Purlin-Platform,valueonly)' \
                      -- "$SCOPED" | tr -d '\n')"
  check "Purlin-Runner trailer" "github-actions/$RUNS_ON" "$RUNNER_TRAILER"
  check "Purlin-Platform trailer" "$PLATFORM_ID" "$PLATFORM_TRAILER"

  if [[ -n "$SCOPED" && -f "$SCOPED" ]]; then
    check "scoped proof file" "found" "found"
    SCOPED_PLATFORM="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("platform",""))' "$SCOPED")"
    check "scoped proof platform" "$PLATFORM_ID" "$SCOPED_PLATFORM"
  else
    check "scoped proof file" "found" "missing ($PROOF_GLOB)"
  fi

  GATE_STATUS=0
  cmd "python3 $GATE --check --project-root $WORK"
  python3 "$GATE" --check --project-root "$WORK" || GATE_STATUS=$?
  check "verify_gate.py --check exit code" "0" "$GATE_STATUS"
fi

# ── 8. the scratch repository, deleted or kept ────────────────────────
say "Scratch repository"
if [[ $KEEP -eq 1 ]]; then
  printf 'KEPT  %s (re-run with --delete to remove it)\n' "$REPO_SLUG"
else
  gh_run gh repo delete "$REPO_SLUG" --yes
  printf 'DELETED  %s\n' "$REPO_SLUG"
fi

say "Result"
if [[ -n "$PUSH_RUNS$DISPATCH_RUNS" ]]; then
  printf 'push runs:      %s\n' "${PUSH_RUNS# }"
  printf 'dispatch runs:  %s\n' "${DISPATCH_RUNS# }"
fi
if [[ $DRY_RUN -eq 1 ]]; then
  printf 'DRY RUN: every command above was printed; no gh call was made.\n'
  exit 0
fi
if [[ $FAILURES -eq 0 ]]; then
  printf 'All assertions passed. Stamp specs/ci/consumer_ci.md PROOF-3 with\n'
  printf '@manual(<email>, <date>, %s)\n' "$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
  exit 0
fi
printf '%s assertion(s) failed.\n' "$FAILURES"
exit 1
