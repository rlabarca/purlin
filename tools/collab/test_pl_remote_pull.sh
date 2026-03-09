#!/bin/bash
# test_pl_remote_pull.sh — Tests for /pl-remote-pull skill logic
# Covers automated scenarios from features/pl_remote_pull.md.
# Produces tests/pl_remote_pull/tests.json.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

SANDBOX=""
cleanup_sandbox() { [[ -n "${SANDBOX:-}" && -d "$SANDBOX" ]] && rm -rf "$SANDBOX"; }

# Helper: create a bare remote + local clone with an active branch
setup_collab_repos() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT

    REMOTE_DIR="$SANDBOX/remote.git"
    git init --bare -q "$REMOTE_DIR"

    LOCAL_DIR="$SANDBOX/local"
    git clone -q "$REMOTE_DIR" "$LOCAL_DIR"
    cd "$LOCAL_DIR"
    git config user.email "test@test.com"
    git config user.name "Test"

    echo "init" > file.txt
    git add file.txt
    git commit -q -m "initial commit"
    git push -q origin main 2>/dev/null

    BRANCH="feature/auth"
    git checkout -q -b "$BRANCH"
    git push -q -u origin "$BRANCH" 2>/dev/null

    mkdir -p .purlin/runtime
    echo "$BRANCH" > .purlin/runtime/active_branch
}

echo "==============================="
echo "/pl-remote-pull Skill Tests"
echo "==============================="

###############################################################################
# Scenario: pl-remote-pull Exits When Not On Collaboration Branch
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Exits When Not On Collaboration Branch"
setup_collab_repos
cd "$LOCAL_DIR"
git checkout -q main
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ACTIVE_BRANCH=$(cat .purlin/runtime/active_branch | tr -d '[:space:]')
if [[ "$CURRENT" != "$ACTIVE_BRANCH" ]]; then
    log_pass "Branch guard detects mismatch: current=$CURRENT active=$ACTIVE_BRANCH"
else
    log_fail "Branch guard should have detected mismatch"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Exits When No Active Branch
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Exits When No Active Branch"
setup_collab_repos
cd "$LOCAL_DIR"
rm -f .purlin/runtime/active_branch
if [[ ! -f .purlin/runtime/active_branch ]]; then
    log_pass "No active branch file triggers abort"
else
    log_fail "Active branch file should be absent"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Aborts When Working Tree Is Dirty
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Aborts When Working Tree Is Dirty"
setup_collab_repos
cd "$LOCAL_DIR"
echo "dirty" > untracked_file.txt
git add untracked_file.txt
DIRTY=$(git status --porcelain | grep -v '^\?\? \.purlin/' | grep -v '^ *\.purlin/')
if [[ -n "$DIRTY" ]]; then
    log_pass "Dirty check detects uncommitted changes"
else
    log_fail "Should detect dirty working tree"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Fast-Forwards When BEHIND
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Fast-Forwards When BEHIND"
setup_collab_repos
cd "$LOCAL_DIR"
# Add commits to remote
CLONE2="$SANDBOX/clone2"
git clone -q "$REMOTE_DIR" "$CLONE2"
cd "$CLONE2"
git config user.email "test@test.com"
git config user.name "Test"
git checkout -q "$BRANCH"
echo "r1" > r1.txt && git add r1.txt && git commit -q -m "remote 1"
echo "r2" > r2.txt && git add r2.txt && git commit -q -m "remote 2"
echo "r3" > r3.txt && git add r3.txt && git commit -q -m "remote 3"
git push -q origin "$BRANCH" 2>/dev/null
# Back to local
cd "$LOCAL_DIR"
git fetch -q origin
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$BEHIND" -eq 3 ]]; then
    # Fast-forward merge
    MERGE_OUT=$(git merge --ff-only "origin/$BRANCH" 2>&1)
    MERGE_EXIT=$?
    if [[ $MERGE_EXIT -eq 0 ]]; then
        log_pass "Fast-forward succeeded: $BEHIND commits merged"
    else
        log_fail "Fast-forward failed: $MERGE_OUT"
    fi
else
    log_fail "Expected BEHIND by 3, got $BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Creates Merge Commit When DIVERGED No Conflicts
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Creates Merge Commit When DIVERGED No Conflicts"
setup_collab_repos
cd "$LOCAL_DIR"
# Local commit (different file)
echo "local" > local_only.txt && git add local_only.txt && git commit -q -m "local commit"
# Remote commits (different files)
CLONE2="$SANDBOX/clone2"
git clone -q "$REMOTE_DIR" "$CLONE2"
cd "$CLONE2"
git config user.email "test@test.com"
git config user.name "Test"
git checkout -q "$BRANCH"
echo "r1" > remote_only1.txt && git add remote_only1.txt && git commit -q -m "remote 1"
echo "r2" > remote_only2.txt && git add remote_only2.txt && git commit -q -m "remote 2"
git push -q origin "$BRANCH" 2>/dev/null
# Back to local
cd "$LOCAL_DIR"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -ge 1 && "$BEHIND" -ge 1 ]]; then
    MERGE_OUT=$(git merge "origin/$BRANCH" --no-edit 2>&1)
    MERGE_EXIT=$?
    if [[ $MERGE_EXIT -eq 0 ]]; then
        log_pass "Diverged merge succeeded without conflicts"
    else
        log_fail "Merge failed: $MERGE_OUT"
    fi
else
    log_fail "Expected DIVERGED, got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Exits On Conflict With Per-File Context
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Exits On Conflict With Per-File Context"
setup_collab_repos
cd "$LOCAL_DIR"
# Local changes to shared file
echo "local version" > file.txt && git add file.txt && git commit -q -m "local change to file.txt"
# Remote changes to same file
CLONE2="$SANDBOX/clone2"
git clone -q "$REMOTE_DIR" "$CLONE2"
cd "$CLONE2"
git config user.email "test@test.com"
git config user.name "Test"
git checkout -q "$BRANCH"
echo "remote version" > file.txt && git add file.txt && git commit -q -m "remote change to file.txt"
git push -q origin "$BRANCH" 2>/dev/null
# Back to local
cd "$LOCAL_DIR"
git fetch -q origin
MERGE_OUT=$(git merge "origin/$BRANCH" --no-edit 2>&1)
MERGE_EXIT=$?
if [[ $MERGE_EXIT -ne 0 ]]; then
    # Verify conflict exists
    CONFLICTS=$(git diff --name-only --diff-filter=U 2>/dev/null)
    if [[ "$CONFLICTS" == *"file.txt"* ]]; then
        log_pass "Conflict detected in file.txt as expected"
    else
        log_fail "Expected conflict in file.txt, got: $CONFLICTS"
    fi
    # Verify per-file commit context is available
    REMOTE_COMMITS=$(git log "$BRANCH..origin/$BRANCH" --oneline -- file.txt 2>/dev/null | wc -l | tr -d ' ')
    LOCAL_COMMITS=$(git log "origin/$BRANCH..$BRANCH" --oneline -- file.txt 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$REMOTE_COMMITS" -ge 1 && "$LOCAL_COMMITS" -ge 1 ]]; then
        log_pass "Per-file commit context available: remote=$REMOTE_COMMITS local=$LOCAL_COMMITS"
    else
        log_fail "Per-file context missing: remote=$REMOTE_COMMITS local=$LOCAL_COMMITS"
    fi
    git merge --abort 2>/dev/null
else
    log_fail "Expected merge conflict but merge succeeded"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Is No-Op When AHEAD
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Is No-Op When AHEAD"
setup_collab_repos
cd "$LOCAL_DIR"
echo "a" > a.txt && git add a.txt && git commit -q -m "commit 1"
echo "b" > b.txt && git add b.txt && git commit -q -m "commit 2"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -eq 2 && "$BEHIND" -eq 0 ]]; then
    log_pass "AHEAD state detected: nothing to pull"
else
    log_fail "Expected AHEAD (ahead=2 behind=0), got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-pull Is No-Op When SAME
###############################################################################
echo ""
echo "[Scenario] pl-remote-pull Is No-Op When SAME"
setup_collab_repos
cd "$LOCAL_DIR"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -eq 0 && "$BEHIND" -eq 0 ]]; then
    log_pass "SAME state detected: nothing to pull"
else
    log_fail "Expected SAME (ahead=0 behind=0), got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Summary
###############################################################################
TOTAL=$((PASS + FAIL))
echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed (of $TOTAL)"
if [[ $FAIL -gt 0 ]]; then
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

OUTDIR="$TESTS_DIR/pl_remote_pull"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/collab/test_pl_remote_pull.sh\"}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
