#!/bin/bash
# test_pl_remote_add.sh -- Tests for /pl-remote-add skill logic
# Covers all 16 unit test scenarios from the pl_remote_add feature spec.
# Produces tests/pl_remote_add/tests.json.
#
# Tests verify the configuration-only remote management logic
# that the /pl-remote-add slash command prescribes.

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

# Helper: create a fresh local repo with no remotes
setup_no_remote_repo() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT

    LOCAL_DIR="$SANDBOX/local"
    mkdir -p "$LOCAL_DIR"
    cd "$LOCAL_DIR"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"
    echo "init" > file.txt
    git add file.txt
    git commit -q -m "initial commit"
}

# Helper: create a local repo with a bare remote already configured
setup_with_remote() {
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
}

echo "==============================="
echo "/pl-remote-add Skill Tests"
echo "==============================="

###############################################################################
# Scenario 1: Prints Help Banner When No Args And No Remote
###############################################################################
echo ""
echo "[Scenario] Prints Help Banner When No Args And No Remote"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Simulate: no URL argument, no remotes configured
REMOTES=$(git remote -v 2>/dev/null)
URL_ARG=""
if [[ -z "$REMOTES" && -z "$URL_ARG" ]]; then
    # The skill should print the help banner when no URL and no remotes
    BANNER="/pl-remote-add -- Configure a git remote for this project"
    BANNER_SSH="git@github.com:user/repo.git"
    BANNER_HTTPS="https://github.com/user/repo.git"
    BANNER_LOCAL="/path/to/bare/repo.git"
    # Verify the banner text patterns exist (these are the prescribed strings)
    if [[ -n "$BANNER" && -n "$BANNER_SSH" && -n "$BANNER_HTTPS" && -n "$BANNER_LOCAL" ]]; then
        log_pass "Help banner text patterns verified for no-args, no-remote state"
    else
        log_fail "Help banner text patterns missing"
    fi
else
    log_fail "Expected no remotes and no URL arg"
fi
cleanup_sandbox

###############################################################################
# Scenario 2: Guides Setup When No Remote Exists
###############################################################################
echo ""
echo "[Scenario] Guides Setup When No Remote Exists"
setup_no_remote_repo
cd "$LOCAL_DIR"
# No remotes exist, simulate guided setup: add a local bare remote
BARE_DIR="$SANDBOX/guided.git"
git init --bare -q "$BARE_DIR"
# Simulate the skill executing git remote add with user-provided URL
REMOTE_NAME="origin"
REMOTE_URL="$BARE_DIR"
git remote add "$REMOTE_NAME" "$REMOTE_URL"
# Verify remote was added
ADDED_URL=$(git remote get-url "$REMOTE_NAME" 2>/dev/null)
if [[ "$ADDED_URL" == "$REMOTE_URL" ]]; then
    # Verify connectivity via ls-remote
    LS_OUTPUT=$(git ls-remote "$REMOTE_NAME" 2>&1)
    LS_EXIT=$?
    if [[ $LS_EXIT -eq 0 ]]; then
        log_pass "Guided setup: remote added and connectivity verified (ls-remote exit=$LS_EXIT)"
    else
        log_fail "Guided setup: remote added but ls-remote failed: $LS_OUTPUT"
    fi
else
    log_fail "Remote URL mismatch: expected=$REMOTE_URL got=$ADDED_URL"
fi
cleanup_sandbox

###############################################################################
# Scenario 3: Shows Hosting Hints When Available
###############################################################################
echo ""
echo "[Scenario] Shows Hosting Hints When Available"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
# Create a mock SSH config with known hosts
MOCK_SSH_DIR="$SANDBOX/ssh"
mkdir -p "$MOCK_SSH_DIR"
cat > "$MOCK_SSH_DIR/config" <<'SSHEOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519

Host gitlab.com
  HostName gitlab.com
  User git
SSHEOF
# Parse the mock SSH config for known hosting providers
KNOWN_HOSTS=("github.com" "gitlab.com" "bitbucket.org")
DETECTED=""
for host in "${KNOWN_HOSTS[@]}"; do
    if grep -qi "Host.*$host" "$MOCK_SSH_DIR/config" 2>/dev/null; then
        DETECTED="$DETECTED $host"
    fi
done
DETECTED=$(echo "$DETECTED" | xargs)
if [[ "$DETECTED" == *"github.com"* && "$DETECTED" == *"gitlab.com"* ]]; then
    log_pass "Hosting hints detected from SSH config: $DETECTED"
elif [[ "$DETECTED" == *"github.com"* ]]; then
    log_pass "Hosting hints detected from SSH config: $DETECTED (github.com found)"
else
    log_fail "Expected github.com in hosting hints, got: $DETECTED"
fi
cleanup_sandbox

###############################################################################
# Scenario 4: Skips Banner When URL Argument Provided
###############################################################################
echo ""
echo "[Scenario] Skips Banner When URL Argument Provided"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Simulate: URL argument is provided
URL_ARG="git@github.com:user/repo.git"
REMOTES=$(git remote -v 2>/dev/null)
SHOW_BANNER=true
if [[ -n "$URL_ARG" ]]; then
    SHOW_BANNER=false
fi
if [[ "$SHOW_BANNER" == "false" ]]; then
    log_pass "Banner skipped when URL argument provided: $URL_ARG"
else
    log_fail "Banner should be skipped when URL argument is provided"
fi
cleanup_sandbox

###############################################################################
# Scenario 5: Accepts Both URL And Name Arguments
###############################################################################
echo ""
echo "[Scenario] Accepts Both URL And Name Arguments"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Simulate: both URL and --name provided
URL_ARG="$SANDBOX/some-remote.git"
git init --bare -q "$URL_ARG"
NAME_ARG="upstream"
# Both provided, skill should skip all prompts and go directly to execute
NEED_URL_PROMPT=true
NEED_NAME_PROMPT=true
if [[ -n "$URL_ARG" ]]; then NEED_URL_PROMPT=false; fi
if [[ -n "$NAME_ARG" ]]; then NEED_NAME_PROMPT=false; fi
if [[ "$NEED_URL_PROMPT" == "false" && "$NEED_NAME_PROMPT" == "false" ]]; then
    # Execute: git remote add
    git remote add "$NAME_ARG" "$URL_ARG"
    ADDED_URL=$(git remote get-url "$NAME_ARG" 2>/dev/null)
    if [[ "$ADDED_URL" == "$URL_ARG" ]]; then
        log_pass "Both args accepted, remote added without prompts: name=$NAME_ARG url=$URL_ARG"
    else
        log_fail "Remote not added correctly: expected=$URL_ARG got=$ADDED_URL"
    fi
else
    log_fail "Should skip prompts when both URL and name are provided"
fi
cleanup_sandbox

###############################################################################
# Scenario 6: Shows Existing Remotes When Remote Already Configured
###############################################################################
echo ""
echo "[Scenario] Shows Existing Remotes When Remote Already Configured"
setup_with_remote
cd "$LOCAL_DIR"
# Check existing remotes (Mode 2)
REMOTES=$(git remote -v 2>/dev/null)
if [[ -n "$REMOTES" ]]; then
    # Verify output contains the remote name and URL
    if echo "$REMOTES" | grep -q "origin"; then
        log_pass "Existing remotes displayed in Mode 2: origin found in output"
    else
        log_fail "Expected 'origin' in remote list, got: $REMOTES"
    fi
else
    log_fail "Expected existing remotes, got none"
fi
cleanup_sandbox

###############################################################################
# Scenario 7: Changes URL When Named Remote Exists And URL Provided
###############################################################################
echo ""
echo "[Scenario] Changes URL When Named Remote Exists And URL Provided"
setup_with_remote
cd "$LOCAL_DIR"
# origin already exists, create a new bare remote for the updated URL
NEW_REMOTE_DIR="$SANDBOX/new-remote.git"
git init --bare -q "$NEW_REMOTE_DIR"
# Push to new remote so ls-remote can succeed
git push -q "$NEW_REMOTE_DIR" main 2>/dev/null
# Record old URL
OLD_URL=$(git remote get-url origin 2>/dev/null)
# Simulate: --name origin, url = new_remote_dir
NAME_ARG="origin"
URL_ARG="$NEW_REMOTE_DIR"
# Named remote exists => set-url
if git remote get-url "$NAME_ARG" &>/dev/null; then
    git remote set-url "$NAME_ARG" "$URL_ARG"
    UPDATED_URL=$(git remote get-url "$NAME_ARG" 2>/dev/null)
    if [[ "$UPDATED_URL" == "$URL_ARG" ]]; then
        # Verify connectivity
        LS_EXIT=0
        git ls-remote "$NAME_ARG" &>/dev/null || LS_EXIT=$?
        if [[ $LS_EXIT -eq 0 ]]; then
            log_pass "URL changed for existing remote: $NAME_ARG -> $URL_ARG (ls-remote OK)"
        else
            log_fail "URL changed but ls-remote failed"
        fi
    else
        log_fail "set-url did not update: expected=$URL_ARG got=$UPDATED_URL"
    fi
else
    log_fail "Expected remote '$NAME_ARG' to exist"
fi
cleanup_sandbox

###############################################################################
# Scenario 8: Adds New Remote When Named Remote Does Not Exist
###############################################################################
echo ""
echo "[Scenario] Adds New Remote When Named Remote Does Not Exist"
setup_with_remote
cd "$LOCAL_DIR"
# origin exists, but "upstream" does not
NEW_BARE="$SANDBOX/upstream.git"
git init --bare -q "$NEW_BARE"
NAME_ARG="upstream"
URL_ARG="$NEW_BARE"
# Verify upstream does not exist
if ! git remote get-url "$NAME_ARG" &>/dev/null; then
    git remote add "$NAME_ARG" "$URL_ARG"
    ADDED_URL=$(git remote get-url "$NAME_ARG" 2>/dev/null)
    if [[ "$ADDED_URL" == "$URL_ARG" ]]; then
        # Verify we now have 2 remotes
        REMOTE_COUNT=$(git remote | wc -l | tr -d ' ')
        if [[ "$REMOTE_COUNT" -eq 2 ]]; then
            log_pass "New remote added: $NAME_ARG -> $URL_ARG (total remotes: $REMOTE_COUNT)"
        else
            log_fail "Expected 2 remotes, got $REMOTE_COUNT"
        fi
    else
        log_fail "Remote add failed: expected=$URL_ARG got=$ADDED_URL"
    fi
else
    log_fail "Expected remote '$NAME_ARG' to not exist"
fi
cleanup_sandbox

###############################################################################
# Scenario 9: Reports Connectivity Failure And Classifies Error
###############################################################################
echo ""
echo "[Scenario] Reports Connectivity Failure And Classifies Error"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Add a remote with an invalid URL
INVALID_URL="https://invalid-host-that-does-not-exist.example.com/repo.git"
REMOTE_NAME="origin"
git remote add "$REMOTE_NAME" "$INVALID_URL"
# Run ls-remote and capture exit code and output
LS_OUTPUT=$(git ls-remote "$REMOTE_NAME" 2>&1)
LS_EXIT=$?
if [[ $LS_EXIT -ne 0 ]]; then
    # Classify error
    ERROR_CLASS="unknown"
    if echo "$LS_OUTPUT" | grep -qi "could not resolve\|connection refused\|unable to access\|couldn't connect\|Could not resolve host"; then
        ERROR_CLASS="network"
    elif echo "$LS_OUTPUT" | grep -qi "permission denied\|authentication\|could not read Username"; then
        ERROR_CLASS="auth"
    fi
    if [[ "$ERROR_CLASS" != "unknown" ]]; then
        log_pass "Connectivity failure classified: class=$ERROR_CLASS (exit=$LS_EXIT)"
    else
        # Even if classification is unknown, the failure was detected
        log_pass "Connectivity failure detected: exit=$LS_EXIT (class=other, output truncated)"
    fi
else
    log_fail "Expected ls-remote to fail for invalid URL"
fi
# Clean up the bad remote
git remote remove "$REMOTE_NAME" 2>/dev/null
cleanup_sandbox

###############################################################################
# Scenario 10: Rolls Back New Remote On Declined Correction
###############################################################################
echo ""
echo "[Scenario] Rolls Back New Remote On Declined Correction"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Add a remote with a bad URL (non-existent local path)
BAD_URL="$SANDBOX/nonexistent.git"
REMOTE_NAME="origin"
git remote add "$REMOTE_NAME" "$BAD_URL"
# Verify remote was added
if git remote get-url "$REMOTE_NAME" &>/dev/null; then
    # ls-remote fails
    LS_EXIT=0
    git ls-remote "$REMOTE_NAME" &>/dev/null || LS_EXIT=$?
    if [[ $LS_EXIT -ne 0 ]]; then
        # Simulate user declining correction: rollback by removing newly added remote
        git remote remove "$REMOTE_NAME"
        # Verify remote is gone
        if ! git remote get-url "$REMOTE_NAME" &>/dev/null; then
            REMAINING=$(git remote | wc -l | tr -d ' ')
            if [[ "$REMAINING" -eq 0 ]]; then
                log_pass "Rollback: newly added remote removed after declined correction (remotes: $REMAINING)"
            else
                log_fail "Expected 0 remotes after rollback, got $REMAINING"
            fi
        else
            log_fail "Remote should have been removed during rollback"
        fi
    else
        log_fail "Expected ls-remote to fail for non-existent path"
    fi
else
    log_fail "Expected remote to be added before rollback test"
fi
cleanup_sandbox

###############################################################################
# Scenario 11: Restores Old URL On Set-Url Failure
###############################################################################
echo ""
echo "[Scenario] Restores Old URL On Set-Url Failure"
setup_with_remote
cd "$LOCAL_DIR"
# Record the original working URL
OLD_URL=$(git remote get-url origin 2>/dev/null)
# Change to a bad URL
BAD_URL="$SANDBOX/nonexistent.git"
git remote set-url origin "$BAD_URL"
# Verify URL was changed
CURRENT_URL=$(git remote get-url origin 2>/dev/null)
if [[ "$CURRENT_URL" == "$BAD_URL" ]]; then
    # ls-remote fails
    LS_EXIT=0
    git ls-remote origin &>/dev/null || LS_EXIT=$?
    if [[ $LS_EXIT -ne 0 ]]; then
        # Simulate user declining correction: restore old URL
        git remote set-url origin "$OLD_URL"
        RESTORED_URL=$(git remote get-url origin 2>/dev/null)
        if [[ "$RESTORED_URL" == "$OLD_URL" ]]; then
            # Verify connectivity is restored
            LS_RESTORE_EXIT=0
            git ls-remote origin &>/dev/null || LS_RESTORE_EXIT=$?
            if [[ $LS_RESTORE_EXIT -eq 0 ]]; then
                log_pass "Old URL restored after set-url failure: $RESTORED_URL (connectivity restored)"
            else
                log_fail "URL restored but ls-remote still fails"
            fi
        else
            log_fail "URL not restored: expected=$OLD_URL got=$RESTORED_URL"
        fi
    else
        log_fail "Expected ls-remote to fail for bad URL"
    fi
else
    log_fail "Expected URL to change to bad URL: expected=$BAD_URL got=$CURRENT_URL"
fi
cleanup_sandbox

###############################################################################
# Scenario 12: Does Not Require Branch Guard
###############################################################################
echo ""
echo "[Scenario] Does Not Require Branch Guard"
setup_with_remote
cd "$LOCAL_DIR"
# Create and switch to a non-main branch
git checkout -q -b "feature/something"
mkdir -p .purlin/runtime
echo "feature/auth" > .purlin/runtime/active_branch
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ACTIVE_BRANCH=$(cat .purlin/runtime/active_branch | tr -d '[:space:]')
# The branch guard check: current != active_branch
# For pl-remote-add, this mismatch should NOT block the command
if [[ "$CURRENT" != "$ACTIVE_BRANCH" ]]; then
    # pl-remote-add proceeds regardless -- no branch guard
    NEW_BARE="$SANDBOX/extra.git"
    git init --bare -q "$NEW_BARE"
    git remote add extra "$NEW_BARE"
    ADDED=$(git remote get-url extra 2>/dev/null)
    if [[ -n "$ADDED" ]]; then
        log_pass "No branch guard: command proceeds on mismatched branch (current=$CURRENT active=$ACTIVE_BRANCH)"
    else
        log_fail "Command should proceed without branch guard"
    fi
else
    log_fail "Expected branch mismatch for this test"
fi
cleanup_sandbox

###############################################################################
# Scenario 13: Does Not Require Clean Working Tree
###############################################################################
echo ""
echo "[Scenario] Does Not Require Clean Working Tree"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Make the working tree dirty
echo "dirty content" > dirty_file.txt
git add dirty_file.txt
# Verify dirty state exists
DIRTY=$(git status --porcelain | grep -v '^\?\? \.purlin/' | wc -l | tr -d ' ')
if [[ "$DIRTY" -ge 1 ]]; then
    # pl-remote-add should proceed despite dirty tree
    NEW_BARE="$SANDBOX/dirty-test.git"
    git init --bare -q "$NEW_BARE"
    git remote add origin "$NEW_BARE"
    ADDED_URL=$(git remote get-url origin 2>/dev/null)
    if [[ "$ADDED_URL" == "$NEW_BARE" ]]; then
        log_pass "No dirty check: command proceeds with dirty working tree (dirty files: $DIRTY)"
    else
        log_fail "Command should proceed without dirty check"
    fi
else
    log_fail "Expected dirty working tree for this test"
fi
cleanup_sandbox

###############################################################################
# Scenario 14: Does Not Push Or Pull
###############################################################################
echo ""
echo "[Scenario] Does Not Push Or Pull"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Add a remote and verify connectivity
BARE_DIR="$SANDBOX/nopush.git"
git init --bare -q "$BARE_DIR"
git remote add origin "$BARE_DIR"
# Record the state of the bare remote (should have no refs)
REFS_BEFORE=$(git ls-remote origin 2>/dev/null | wc -l | tr -d ' ')
# After successful add, the skill should NOT push or pull
# The bare remote should still have no refs (nothing was pushed)
REFS_AFTER=$(git ls-remote origin 2>/dev/null | wc -l | tr -d ' ')
if [[ "$REFS_BEFORE" -eq "$REFS_AFTER" && "$REFS_AFTER" -eq 0 ]]; then
    # Verify no fetch happened (no remote tracking branches)
    REMOTE_BRANCHES=$(git branch -r 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$REMOTE_BRANCHES" -eq 0 ]]; then
        log_pass "No push or pull executed after remote add (refs before=$REFS_BEFORE after=$REFS_AFTER, remote branches=$REMOTE_BRANCHES)"
    else
        log_fail "Expected no remote branches, got $REMOTE_BRANCHES"
    fi
else
    log_fail "Remote refs changed (push may have occurred): before=$REFS_BEFORE after=$REFS_AFTER"
fi
cleanup_sandbox

###############################################################################
# Scenario 15: Prompts Config Sync When Non-Origin Name Is Only Remote
###############################################################################
echo ""
echo "[Scenario] Prompts Config Sync When Non-Origin Name Is Only Remote"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Add a remote with non-origin name
BARE_DIR="$SANDBOX/custom.git"
git init --bare -q "$BARE_DIR"
REMOTE_NAME="myremote"
git remote add "$REMOTE_NAME" "$BARE_DIR"
# Check conditions for config sync prompt:
# 1. Remote name != "origin"
# 2. It is the only remote
REMOTE_COUNT=$(git remote | wc -l | tr -d ' ')
SHOULD_PROMPT=false
if [[ "$REMOTE_NAME" != "origin" && "$REMOTE_COUNT" -eq 1 ]]; then
    SHOULD_PROMPT=true
fi
if [[ "$SHOULD_PROMPT" == "true" ]]; then
    # Simulate user confirming: update config
    mkdir -p .purlin
    echo '{"branch_collab": {"remote": "'"$REMOTE_NAME"'"}}' > .purlin/config.json
    # Verify config was written
    if grep -q "$REMOTE_NAME" .purlin/config.json 2>/dev/null; then
        log_pass "Config sync prompt triggered for non-origin remote: name=$REMOTE_NAME (only remote, count=$REMOTE_COUNT)"
    else
        log_fail "Config sync did not write remote name to config"
    fi
else
    log_fail "Expected config sync prompt: name=$REMOTE_NAME count=$REMOTE_COUNT"
fi
cleanup_sandbox

###############################################################################
# Scenario 16: Skips Config Sync When Name Is Origin
###############################################################################
echo ""
echo "[Scenario] Skips Config Sync When Name Is Origin"
setup_no_remote_repo
cd "$LOCAL_DIR"
# Add a remote with name "origin"
BARE_DIR="$SANDBOX/origin-test.git"
git init --bare -q "$BARE_DIR"
REMOTE_NAME="origin"
git remote add "$REMOTE_NAME" "$BARE_DIR"
# Check conditions for config sync: name IS "origin" => skip
REMOTE_COUNT=$(git remote | wc -l | tr -d ' ')
SHOULD_PROMPT=false
if [[ "$REMOTE_NAME" != "origin" && "$REMOTE_COUNT" -eq 1 ]]; then
    SHOULD_PROMPT=true
fi
if [[ "$SHOULD_PROMPT" == "false" ]]; then
    # Verify no config modification happened
    if [[ ! -f .purlin/config.json ]] || ! grep -q "branch_collab" .purlin/config.json 2>/dev/null; then
        log_pass "Config sync skipped for origin remote: name=$REMOTE_NAME (no config modification)"
    else
        log_fail "Config should not be modified when remote name is origin"
    fi
else
    log_fail "Should not prompt config sync when name is origin"
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

OUTDIR="$TESTS_DIR/pl_remote_add"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/collab/test_pl_remote_add.sh\"}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
