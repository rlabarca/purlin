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
WORKFLOWS=("purlin-${PLATFORM_ID}-proofs.yml" "verify-gate.yml")

DRY_RUN=0
KEEP=1
FAILURES=0

usage() {
  sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

# ── 3. dispatch both workflows and wait ───────────────────────────────
say "Dispatch both workflows on main and wait for them"
for workflow in "${WORKFLOWS[@]}"; do
  gh_run gh workflow run "$workflow" --ref main
done
if [[ $DRY_RUN -eq 0 ]]; then
  # The dispatch is asynchronous: the run does not exist the instant the API
  # call returns, and `gh run list` would report the previous one.
  sleep 10
fi
for workflow in "${WORKFLOWS[@]}"; do
  gh_capture RUN_ID '<run-id>' gh run list --workflow "$workflow" \
    --branch main --limit 1 --json databaseId --jq '.[0].databaseId'
  gh_run gh run watch "$RUN_ID" --exit-status
done

# ── 4. pull the commit-back ───────────────────────────────────────────
say "Pull what the runner committed back"
if [[ $DRY_RUN -eq 1 ]]; then
  cmd "git pull --ff-only"
else
  git pull --ff-only || { sleep 5; git pull --ff-only; }
fi

# ── 5. the four assertions ────────────────────────────────────────────
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

# ── 6. the scratch repository, deleted or kept ────────────────────────
say "Scratch repository"
if [[ $KEEP -eq 1 ]]; then
  printf 'KEPT  %s (re-run with --delete to remove it)\n' "$REPO_SLUG"
else
  gh_run gh repo delete "$REPO_SLUG" --yes
  printf 'DELETED  %s\n' "$REPO_SLUG"
fi

say "Result"
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
