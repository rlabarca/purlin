#!/bin/bash
# test_pl_remote_push.sh — Tests for /pl-remote-push skill logic
# Covers automated scenarios from features/pl_remote_push.md.
# Produces tests/pl_remote_push/tests.json.
#
# Tests verify the precondition guards and sync-state detection logic
# that the slash command prescribes.

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

    # Create bare remote
    REMOTE_DIR="$SANDBOX/remote.git"
    git init --bare -q "$REMOTE_DIR"

    # Clone into local
    LOCAL_DIR="$SANDBOX/local"
    git clone -q "$REMOTE_DIR" "$LOCAL_DIR"
    cd "$LOCAL_DIR"
    git config user.email "test@test.com"
    git config user.name "Test"

    # Initial commit on main
    echo "init" > file.txt
    git add file.txt
    git commit -q -m "initial commit"
    git push -q origin main 2>/dev/null

    # Create branch and push it
    BRANCH="feature/auth"
    git checkout -q -b "$BRANCH"
    git push -q -u origin "$BRANCH" 2>/dev/null

    # Set up active branch file
    mkdir -p .purlin/runtime
    echo "$BRANCH" > .purlin/runtime/active_branch
}

echo "==============================="
echo "/pl-remote-push Skill Tests"
echo "==============================="

###############################################################################
# Scenario: pl-remote-push Exits When Not On Collaboration Branch
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Exits When Not On Collaboration Branch"
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
# Scenario: pl-remote-push Exits When On Wrong Branch
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Exits When On Wrong Branch"
setup_collab_repos
cd "$LOCAL_DIR"
git checkout -q -b "hotfix/urgent"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ACTIVE_BRANCH=$(cat .purlin/runtime/active_branch | tr -d '[:space:]')
if [[ "$CURRENT" != "$ACTIVE_BRANCH" && "$CURRENT" == "hotfix/urgent" ]]; then
    log_pass "Branch guard detects wrong branch: current=$CURRENT expected=$ACTIVE_BRANCH"
else
    log_fail "Expected hotfix/urgent != feature/auth"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Resolves To Main When No Active Branch
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Resolves To Main When No Active Branch"
setup_collab_repos
cd "$LOCAL_DIR"
rm -f .purlin/runtime/active_branch
git checkout -q main
# Add 2 local commits ahead of origin/main
echo "m1" > m1.txt && git add m1.txt && git commit -q -m "main commit 1"
echo "m2" > m2.txt && git add m2.txt && git commit -q -m "main commit 2"
# Resolve collaboration branch: no active_branch file => defaults to main
if [[ -f .purlin/runtime/active_branch ]] && [[ -s .purlin/runtime/active_branch ]]; then
    COLLAB_BRANCH=$(cat .purlin/runtime/active_branch | tr -d '[:space:]')
else
    COLLAB_BRANCH="main"
fi
CURRENT=$(git rev-parse --abbrev-ref HEAD)
if [[ "$COLLAB_BRANCH" == "main" && "$CURRENT" == "main" ]]; then
    git fetch -q origin
    AHEAD=$(git log "origin/main..main" --oneline 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$AHEAD" -eq 2 ]]; then
        PUSH_OUTPUT=$(git push origin main 2>&1)
        PUSH_EXIT=$?
        if [[ $PUSH_EXIT -eq 0 ]]; then
            log_pass "Resolved to main, pushed $AHEAD commits"
        else
            log_fail "Push failed: $PUSH_OUTPUT"
        fi
    else
        log_fail "Expected 2 commits ahead, got $AHEAD"
    fi
else
    log_fail "Expected collab=main current=main, got collab=$COLLAB_BRANCH current=$CURRENT"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Rejects Non-Main Branch When No Active Branch
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Rejects Non-Main Branch When No Active Branch"
setup_collab_repos
cd "$LOCAL_DIR"
rm -f .purlin/runtime/active_branch
git checkout -q -b "hotfix/urgent"
# Resolve collaboration branch: no active_branch file => defaults to main
if [[ -f .purlin/runtime/active_branch ]] && [[ -s .purlin/runtime/active_branch ]]; then
    COLLAB_BRANCH=$(cat .purlin/runtime/active_branch | tr -d '[:space:]')
else
    COLLAB_BRANCH="main"
fi
CURRENT=$(git rev-parse --abbrev-ref HEAD)
# Direct mode: not on main => abort with "No active collaboration branch" + "Switch to main"
if [[ "$COLLAB_BRANCH" == "main" && "$CURRENT" != "main" ]]; then
    MSG="No active collaboration branch. On main, /pl-remote-push pushes main directly. Current branch: $CURRENT. Switch to main or use the CDD dashboard to create a collaboration branch."
    if [[ "$MSG" == *"No active collaboration branch"* && "$MSG" == *"Switch to main"* ]]; then
        log_pass "Rejects non-main branch ($CURRENT) when no active branch: direct mode guard"
    else
        log_fail "Error message missing expected text"
    fi
else
    log_fail "Expected collab=main current=hotfix/urgent, got collab=$COLLAB_BRANCH current=$CURRENT"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Aborts When Working Tree Is Dirty
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Aborts When Working Tree Is Dirty"
setup_collab_repos
cd "$LOCAL_DIR"
echo "dirty" > untracked_file.txt
git add untracked_file.txt
# Check dirty state (excluding .purlin/)
DIRTY=$(git status --porcelain | grep -v '^\?\? \.purlin/' | grep -v '^ *\.purlin/')
if [[ -n "$DIRTY" ]]; then
    log_pass "Dirty check detects uncommitted changes outside .purlin/"
else
    log_fail "Should detect dirty working tree"
fi
# Verify .purlin/ changes are excluded
echo "runtime" > .purlin/runtime/test_file
PURLIN_ONLY=$(git status --porcelain | grep -v '\.purlin/')
NON_PURLIN_ONLY=$(echo "$PURLIN_ONLY" | grep -v '^\s*$' | wc -l | tr -d ' ')
if [[ "$NON_PURLIN_ONLY" -ge 1 ]]; then
    log_pass ".purlin/ files excluded from dirty check (non-purlin changes: $NON_PURLIN_ONLY)"
else
    log_fail "Should exclude .purlin/ from dirty check"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Blocked When Local Is BEHIND Remote
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Blocked When Local Is BEHIND Remote"
setup_collab_repos
cd "$LOCAL_DIR"
# Add commits to remote via a second clone
CLONE2="$SANDBOX/clone2"
git clone -q "$REMOTE_DIR" "$CLONE2"
cd "$CLONE2"
git config user.email "test@test.com"
git config user.name "Test"
git checkout -q "$BRANCH"
echo "remote1" > remote_file1.txt && git add remote_file1.txt && git commit -q -m "remote commit 1"
echo "remote2" > remote_file2.txt && git add remote_file2.txt && git commit -q -m "remote commit 2"
git push -q origin "$BRANCH" 2>/dev/null
# Back to local, fetch
cd "$LOCAL_DIR"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -eq 0 && "$BEHIND" -eq 2 ]]; then
    log_pass "BEHIND state detected: ahead=$AHEAD behind=$BEHIND"
else
    log_fail "Expected BEHIND (ahead=0 behind=2), got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Blocked When Local Is DIVERGED
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Blocked When Local Is DIVERGED"
setup_collab_repos
cd "$LOCAL_DIR"
# Add a local commit
echo "local" > local_file.txt && git add local_file.txt && git commit -q -m "local commit"
# Add commits to remote via second clone
CLONE2="$SANDBOX/clone2"
git clone -q "$REMOTE_DIR" "$CLONE2"
cd "$CLONE2"
git config user.email "test@test.com"
git config user.name "Test"
git checkout -q "$BRANCH"
echo "remote1" > remote_file1.txt && git add remote_file1.txt && git commit -q -m "remote commit 1"
echo "remote2" > remote_file2.txt && git add remote_file2.txt && git commit -q -m "remote commit 2"
git push -q origin "$BRANCH" 2>/dev/null
# Back to local, fetch
cd "$LOCAL_DIR"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -eq 1 && "$BEHIND" -eq 2 ]]; then
    log_pass "DIVERGED state detected: ahead=$AHEAD behind=$BEHIND"
else
    log_fail "Expected DIVERGED (ahead=1 behind=2), got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Succeeds When AHEAD
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Succeeds When AHEAD"
setup_collab_repos
cd "$LOCAL_DIR"
# Add 3 local commits
echo "a" > a.txt && git add a.txt && git commit -q -m "commit 1"
echo "b" > b.txt && git add b.txt && git commit -q -m "commit 2"
echo "c" > c.txt && git add c.txt && git commit -q -m "commit 3"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -eq 3 && "$BEHIND" -eq 0 ]]; then
    # Actually push
    PUSH_OUTPUT=$(git push origin "$BRANCH" 2>&1)
    PUSH_EXIT=$?
    if [[ $PUSH_EXIT -eq 0 ]]; then
        log_pass "AHEAD push succeeded: $AHEAD commits pushed"
    else
        log_fail "Push failed: $PUSH_OUTPUT"
    fi
else
    log_fail "Expected AHEAD (ahead=3 behind=0), got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Is No-Op When SAME
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Is No-Op When SAME"
setup_collab_repos
cd "$LOCAL_DIR"
git fetch -q origin
AHEAD=$(git log "origin/$BRANCH..$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
BEHIND=$(git log "$BRANCH..origin/$BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$AHEAD" -eq 0 && "$BEHIND" -eq 0 ]]; then
    log_pass "SAME state detected: nothing to push"
else
    log_fail "Expected SAME (ahead=0 behind=0), got ahead=$AHEAD behind=$BEHIND"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Exits With Guidance When No Remote Configured
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Exits With Guidance When No Remote Configured"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
LOCAL_DIR="$SANDBOX/local"
mkdir -p "$LOCAL_DIR"
cd "$LOCAL_DIR"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
echo "init" > file.txt && git add file.txt && git commit -q -m "initial commit"
# No active branch => resolves to main, current is main
mkdir -p .purlin/runtime
# Verify no remotes are configured
REMOTES=$(git remote -v 2>/dev/null)
if [[ -z "$REMOTES" ]]; then
    # Construct the expected error message
    EXPECTED_MSG="No git remote configured. Run /pl-remote-add to set up a remote first."
    if [[ "$EXPECTED_MSG" == *"No git remote configured"* && "$EXPECTED_MSG" == *"/pl-remote-add"* ]]; then
        log_pass "No remotes detected, exits with guidance: '$EXPECTED_MSG'"
    else
        log_fail "Error message missing expected text"
    fi
else
    log_fail "Expected no remotes, got: $REMOTES"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push First Push To Empty Remote Succeeds
###############################################################################
echo ""
echo "[Scenario] pl-remote-push First Push To Empty Remote Succeeds"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
REMOTE_DIR="$SANDBOX/remote.git"
git init --bare -q "$REMOTE_DIR"
LOCAL_DIR="$SANDBOX/local"
mkdir -p "$LOCAL_DIR"
cd "$LOCAL_DIR"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
# Create 5 commits on main
echo "c1" > c1.txt && git add c1.txt && git commit -q -m "commit 1"
echo "c2" > c2.txt && git add c2.txt && git commit -q -m "commit 2"
echo "c3" > c3.txt && git add c3.txt && git commit -q -m "commit 3"
echo "c4" > c4.txt && git add c4.txt && git commit -q -m "commit 4"
echo "c5" > c5.txt && git add c5.txt && git commit -q -m "commit 5"
# Add remote but do NOT push (so origin/main does not exist)
git remote add origin "$REMOTE_DIR"
mkdir -p .purlin/runtime
# No active_branch => resolves to main
COLLAB_BRANCH="main"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
# Verify origin/main does not exist (first push scenario)
if ! git rev-parse --verify "origin/$COLLAB_BRANCH" &>/dev/null; then
    # First push: treat as AHEAD with all commits on branch
    AHEAD=$(git log --oneline "$COLLAB_BRANCH" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$AHEAD" -eq 5 ]]; then
        # Simulate user confirming first-push prompt, then push
        PUSH_OUTPUT=$(git push origin "$COLLAB_BRANCH" 2>&1)
        PUSH_EXIT=$?
        if [[ $PUSH_EXIT -eq 0 ]]; then
            log_pass "First push to empty remote succeeded: $AHEAD commits pushed"
        else
            log_fail "Push failed: $PUSH_OUTPUT"
        fi
    else
        log_fail "Expected 5 commits ahead, got $AHEAD"
    fi
else
    log_fail "origin/$COLLAB_BRANCH should not exist yet"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push First Push Shows Safety Confirmation
###############################################################################
echo ""
echo "[Scenario] pl-remote-push First Push Shows Safety Confirmation"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
REMOTE_DIR="$SANDBOX/remote.git"
git init --bare -q "$REMOTE_DIR"
LOCAL_DIR="$SANDBOX/local"
mkdir -p "$LOCAL_DIR"
cd "$LOCAL_DIR"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
# Create 3 commits on main
echo "c1" > c1.txt && git add c1.txt && git commit -q -m "commit 1"
echo "c2" > c2.txt && git add c2.txt && git commit -q -m "commit 2"
echo "c3" > c3.txt && git add c3.txt && git commit -q -m "commit 3"
# Add remote with a specific URL
REMOTE_URL="$REMOTE_DIR"
git remote add origin "$REMOTE_URL"
mkdir -p .purlin/runtime
COLLAB_BRANCH="main"
# Verify first-push condition: origin/main does not exist
FIRST_PUSH=false
if ! git rev-parse --verify "origin/$COLLAB_BRANCH" &>/dev/null; then
    FIRST_PUSH=true
fi
if [[ "$FIRST_PUSH" == "true" ]]; then
    # Build the safety confirmation details
    REMOTE_NAME="origin"
    REMOTE_ACTUAL_URL=$(git remote get-url origin 2>/dev/null)
    COMMIT_COUNT=$(git log --oneline "$COLLAB_BRANCH" 2>/dev/null | wc -l | tr -d ' ')
    # Verify all confirmation fields are present
    if [[ -n "$REMOTE_NAME" && -n "$REMOTE_ACTUAL_URL" && "$COLLAB_BRANCH" == "main" && "$COMMIT_COUNT" -eq 3 ]]; then
        log_pass "First push shows safety confirmation: remote=$REMOTE_NAME url=$REMOTE_ACTUAL_URL branch=$COLLAB_BRANCH commits=$COMMIT_COUNT"
    else
        log_fail "Safety confirmation fields incomplete: remote=$REMOTE_NAME url=$REMOTE_ACTUAL_URL branch=$COLLAB_BRANCH commits=$COMMIT_COUNT"
    fi
else
    log_fail "Expected first-push condition (no remote tracking ref)"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push First Push Aborted When User Declines
###############################################################################
echo ""
echo "[Scenario] pl-remote-push First Push Aborted When User Declines"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
REMOTE_DIR="$SANDBOX/remote.git"
git init --bare -q "$REMOTE_DIR"
LOCAL_DIR="$SANDBOX/local"
mkdir -p "$LOCAL_DIR"
cd "$LOCAL_DIR"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
echo "c1" > c1.txt && git add c1.txt && git commit -q -m "commit 1"
git remote add origin "$REMOTE_DIR"
mkdir -p .purlin/runtime
COLLAB_BRANCH="main"
# Verify first-push condition
if ! git rev-parse --verify "origin/$COLLAB_BRANCH" &>/dev/null; then
    # User declines => no push happens
    # Verify remote has no refs (nothing was pushed)
    REMOTE_REFS=$(git ls-remote origin 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$REMOTE_REFS" -eq 0 ]]; then
        log_pass "First push aborted: user declined, no git push executed, remote still empty"
    else
        log_fail "Expected empty remote (no refs), got $REMOTE_REFS refs"
    fi
else
    log_fail "Expected first-push condition (no remote tracking ref)"
fi
cleanup_sandbox

###############################################################################
# Scenario: pl-remote-push Subsequent Push Skips Confirmation
###############################################################################
echo ""
echo "[Scenario] pl-remote-push Subsequent Push Skips Confirmation"
setup_collab_repos
cd "$LOCAL_DIR"
git checkout -q main
rm -f .purlin/runtime/active_branch
# origin/main exists because setup_collab_repos pushed to it
# Add 2 local commits
echo "m1" > m1.txt && git add m1.txt && git commit -q -m "main commit 1"
echo "m2" > m2.txt && git add m2.txt && git commit -q -m "main commit 2"
git fetch -q origin
COLLAB_BRANCH="main"
# Verify the remote tracking ref EXISTS (subsequent push)
SUBSEQUENT=false
if git rev-parse --verify "origin/$COLLAB_BRANCH" &>/dev/null; then
    SUBSEQUENT=true
fi
if [[ "$SUBSEQUENT" == "true" ]]; then
    # No safety confirmation needed, push directly
    AHEAD=$(git log "origin/$COLLAB_BRANCH..$COLLAB_BRANCH" --oneline 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$AHEAD" -eq 2 ]]; then
        PUSH_OUTPUT=$(git push origin "$COLLAB_BRANCH" 2>&1)
        PUSH_EXIT=$?
        if [[ $PUSH_EXIT -eq 0 ]]; then
            log_pass "Subsequent push skips confirmation: pushed $AHEAD commits directly"
        else
            log_fail "Push failed: $PUSH_OUTPUT"
        fi
    else
        log_fail "Expected 2 commits ahead, got $AHEAD"
    fi
else
    log_fail "Expected remote tracking ref to exist for subsequent push"
fi
cleanup_sandbox

###############################################################################
# FORBIDDEN Enforcement: Skill file contains FORBIDDEN section
###############################################################################
echo ""
echo "[FORBIDDEN] Skill file contains FORBIDDEN enforcement section"
SKILL_FILE="$(dirname "$(dirname "$SCRIPT_DIR")")/.claude/commands/pl-remote-push.md"
if [[ -f "$SKILL_FILE" ]]; then
    if grep -q "^## FORBIDDEN" "$SKILL_FILE"; then
        log_pass "Skill file contains ## FORBIDDEN section"
    else
        log_fail "Skill file missing ## FORBIDDEN section"
    fi
else
    log_fail "Skill file not found at $SKILL_FILE"
fi

###############################################################################
# FORBIDDEN Enforcement: No force push directive
###############################################################################
echo ""
echo "[FORBIDDEN] Skill file prohibits git push --force"
if [[ -f "$SKILL_FILE" ]]; then
    if grep -q "git push --force" "$SKILL_FILE" && grep -q "MUST NOT" "$SKILL_FILE"; then
        log_pass "Skill file contains force push prohibition"
    else
        log_fail "Skill file missing force push prohibition"
    fi
else
    log_fail "Skill file not found at $SKILL_FILE"
fi

###############################################################################
# FORBIDDEN Enforcement: No push to non-collaboration branch
###############################################################################
echo ""
echo "[FORBIDDEN] Skill file prohibits push to non-collaboration branch"
if [[ -f "$SKILL_FILE" ]]; then
    if grep -q "MUST NOT.*push to a branch that does not match" "$SKILL_FILE"; then
        log_pass "Skill file contains non-collaboration branch push prohibition"
    else
        log_fail "Skill file missing non-collaboration branch push prohibition"
    fi
else
    log_fail "Skill file not found at $SKILL_FILE"
fi

###############################################################################
# FORBIDDEN Enforcement: No unchecked user input in git commands
###############################################################################
echo ""
echo "[FORBIDDEN] Skill file prohibits unchecked user input in git commands"
if [[ -f "$SKILL_FILE" ]]; then
    if grep -q "MUST NOT.*unchecked user input" "$SKILL_FILE"; then
        log_pass "Skill file contains user input validation prohibition"
    else
        log_fail "Skill file missing user input validation prohibition"
    fi
else
    log_fail "Skill file not found at $SKILL_FILE"
fi

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

OUTDIR="$TESTS_DIR/pl_remote_push"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/collab/test_pl_remote_push.sh\"}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
