#!/usr/bin/env bash
# tests/qa/test_purlin_worktree_identity_regression.sh
# QA-owned regression harness for features/purlin_worktree_identity.md
# Tests: worktree label assignment, badge format, identity updates
#
# Usage: bash tests/qa/test_purlin_worktree_identity_regression.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

PL_RUN="$PURLIN_ROOT/pl-run.sh"

echo "=== QA Regression: purlin_worktree_identity ==="
echo ""

# ──────────────────────────────────────────────
# WTI1: Badge format uses mode name without "Purlin:" prefix
# Verify ROLE_DISPLAY values in pl-run.sh never start with "Purlin:"
# ──────────────────────────────────────────────
if [ -f "$PL_RUN" ]; then
    # Check for MODE_NAME assignment (the new format)
    if grep -q 'MODE_NAME=' "$PL_RUN" 2>/dev/null; then
        # Verify no "Purlin:" prefix patterns in the mode display
        if grep -q '"Purlin:' "$PL_RUN" 2>/dev/null; then
            log_fail "WTI1: found 'Purlin:' prefix in pl-run.sh badge values"
        else
            log_pass "WTI1: badge format never uses 'Purlin:' prefix"
        fi
    else
        log_fail "WTI1: MODE_NAME variable not found in pl-run.sh"
    fi
else
    log_fail "WTI1: pl-run.sh not found"
fi

# ──────────────────────────────────────────────
# WTI2: pl-run.sh writes .purlin_worktree_label file in worktree
# ──────────────────────────────────────────────
if [ -f "$PL_RUN" ] && grep -q '.purlin_worktree_label' "$PL_RUN" 2>/dev/null; then
    log_pass "WTI2: pl-run.sh writes .purlin_worktree_label file in worktree"
else
    log_fail "WTI2: .purlin_worktree_label handling not found in pl-run.sh"
fi

# ──────────────────────────────────────────────
# WTI3: Worktree label gap-filling logic exists in pl-run.sh
# The launcher should find the lowest unused positive integer
# ──────────────────────────────────────────────
if [ -f "$PL_RUN" ] && grep -q '_used_nums\|_next' "$PL_RUN" 2>/dev/null; then
    log_pass "WTI3: gap-filling label assignment logic exists in pl-run.sh"
else
    log_fail "WTI3: gap-filling label logic not found in pl-run.sh"
fi

# ──────────────────────────────────────────────
# WTI4: Identity is computed AFTER worktree creation
# pl-run.sh must set ROLE_DISPLAY after the worktree block
# ──────────────────────────────────────────────
if [ -f "$PL_RUN" ]; then
    # The worktree block sets WORKTREE_LABEL, then ROLE_DISPLAY references it
    WORKTREE_LINE=$(grep -n 'git worktree add' "$PL_RUN" 2>/dev/null | head -1 | cut -d: -f1)
    ROLE_LINE=$(grep -n 'ROLE_DISPLAY=' "$PL_RUN" 2>/dev/null | tail -1 | cut -d: -f1)
    if [ -n "$WORKTREE_LINE" ] && [ -n "$ROLE_LINE" ] && [ "$ROLE_LINE" -gt "$WORKTREE_LINE" ]; then
        log_pass "WTI4: identity computed after worktree creation (line $ROLE_LINE > $WORKTREE_LINE)"
    else
        log_fail "WTI4: ROLE_DISPLAY set before worktree creation — label won't be available"
    fi
else
    log_fail "WTI4: pl-run.sh not found"
fi

# ──────────────────────────────────────────────
# WTI5: Badge includes worktree label when label file exists
# Verify the pattern: ROLE_DISPLAY="$MODE_NAME ($WORKTREE_LABEL)"
# ──────────────────────────────────────────────
if [ -f "$PL_RUN" ] && grep -q 'WORKTREE_LABEL' "$PL_RUN" 2>/dev/null; then
    # Check that the label is appended to ROLE_DISPLAY
    if grep -q 'MODE_NAME.*WORKTREE_LABEL\|ROLE_DISPLAY.*WORKTREE_LABEL' "$PL_RUN" 2>/dev/null; then
        log_pass "WTI5: badge appends worktree label when present"
    else
        log_fail "WTI5: WORKTREE_LABEL not incorporated into ROLE_DISPLAY"
    fi
else
    log_fail "WTI5: WORKTREE_LABEL not referenced in pl-run.sh"
fi

# ──────────────────────────────────────────────
# WTI6: --name CLI arg uses the same string as badge (ROLE_DISPLAY)
# ──────────────────────────────────────────────
if [ -f "$PL_RUN" ] && grep -q '\-\-name.*ROLE_DISPLAY' "$PL_RUN" 2>/dev/null; then
    log_pass "WTI6: --name CLI arg uses ROLE_DISPLAY value"
else
    log_fail "WTI6: --name CLI arg does not reference ROLE_DISPLAY"
fi

# ──────────────────────────────────────────────
# WTI7: Functional test — label file content matches W<N> pattern
# Creates a temp repo, simulates the label assignment from pl-run.sh,
# and verifies the content.
# ──────────────────────────────────────────────
TEMP_REPO=$(mktemp -d)
WTI7_RESULT=1

(
    set -e
    cd "$TEMP_REPO"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > file.txt
    git add file.txt
    git commit -m "initial" --quiet

    mkdir -p .purlin/worktrees
    BRANCH="purlin-open-20260101-120000"
    WORKTREE_DIR="$TEMP_REPO/.purlin/worktrees/$BRANCH"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    # Simulate label assignment (same logic as pl-run.sh)
    _used_nums=()
    for _lf in "$TEMP_REPO/.purlin/worktrees"/*/.purlin_worktree_label; do
        [ -f "$_lf" ] || continue
        _n=$(tr -cd '0-9' < "$_lf")
        [ -n "$_n" ] && _used_nums+=("$_n")
    done
    _next=1
    while [ ${#_used_nums[@]} -gt 0 ] && printf '%s\n' "${_used_nums[@]}" | grep -qx "$_next"; do
        _next=$((_next + 1))
    done
    LABEL="W${_next}"
    echo "$LABEL" > "$WORKTREE_DIR/.purlin_worktree_label"

    # Verify label format
    CONTENT=$(cat "$WORKTREE_DIR/.purlin_worktree_label")
    if [[ "$CONTENT" =~ ^W[0-9]+$ ]]; then
        echo "LABEL_OK"
    else
        echo "LABEL_BAD: $CONTENT"
        exit 1
    fi

    # Verify first label is W1
    if [ "$CONTENT" = "W1" ]; then
        echo "FIRST_W1_OK"
    else
        echo "FIRST_NOT_W1: $CONTENT"
        exit 1
    fi

    # Cleanup
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
    git branch -D "$BRANCH" 2>/dev/null || true
)
WTI7_RESULT=$?

if [ $WTI7_RESULT -eq 0 ]; then
    log_pass "WTI7: label file content matches W<N> pattern and first worktree gets W1"
else
    log_fail "WTI7: label file content test failed"
fi

rm -rf "$TEMP_REPO"

# ──────────────────────────────────────────────
# WTI8: Functional test — gap-filling assigns lowest unused number
# ──────────────────────────────────────────────
TEMP_REPO2=$(mktemp -d)
WTI8_RESULT=1

(
    set -e
    cd "$TEMP_REPO2"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > file.txt
    git add file.txt
    git commit -m "initial" --quiet

    mkdir -p .purlin/worktrees

    # Create worktrees W1 and W3 (skip W2)
    for IDX in 1 3; do
        BRANCH="purlin-open-2026010${IDX}-120000"
        WDIR="$TEMP_REPO2/.purlin/worktrees/$BRANCH"
        git worktree add "$WDIR" -b "$BRANCH" --quiet 2>/dev/null
        echo "W${IDX}" > "$WDIR/.purlin_worktree_label"
    done

    # Now compute next label using the same logic as pl-run.sh
    _used_nums=()
    for _lf in "$TEMP_REPO2/.purlin/worktrees"/*/.purlin_worktree_label; do
        [ -f "$_lf" ] || continue
        _n=$(tr -cd '0-9' < "$_lf")
        [ -n "$_n" ] && _used_nums+=("$_n")
    done
    _next=1
    while printf '%s\n' "${_used_nums[@]}" 2>/dev/null | grep -qx "$_next"; do
        _next=$((_next + 1))
    done
    LABEL="W${_next}"

    if [ "$LABEL" = "W2" ]; then
        echo "GAP_FILL_OK"
    else
        echo "GAP_FILL_FAILED: expected W2 got $LABEL"
        exit 1
    fi

    # Cleanup
    for BRANCH in purlin-open-20260101-120000 purlin-open-20260103-120000; do
        WDIR="$TEMP_REPO2/.purlin/worktrees/$BRANCH"
        git worktree remove "$WDIR" --force 2>/dev/null || true
        git branch -D "$BRANCH" 2>/dev/null || true
    done
)
WTI8_RESULT=$?

if [ $WTI8_RESULT -eq 0 ]; then
    log_pass "WTI8: gap-filling correctly assigns W2 when W1 and W3 exist"
else
    log_fail "WTI8: gap-filling label assignment failed"
fi

rm -rf "$TEMP_REPO2"

# ──────────────────────────────────────────────
# WTI9: PURLIN_BASE.md references worktree label detection
# The agent's mode switch protocol should check for .purlin_worktree_label
# ──────────────────────────────────────────────
BASE_MD="$PURLIN_ROOT/instructions/PURLIN_BASE.md"
if [ -f "$BASE_MD" ] && grep -q '.purlin_worktree_label' "$BASE_MD" 2>/dev/null; then
    log_pass "WTI9: PURLIN_BASE.md references .purlin_worktree_label for mode switch"
else
    log_fail "WTI9: PURLIN_BASE.md does not reference .purlin_worktree_label"
fi

# ──────────────────────────────────────────────
# WTI10: No .purlin_worktree_label file in the main repo root
# ──────────────────────────────────────────────
if [ ! -f "$PURLIN_ROOT/.purlin_worktree_label" ]; then
    log_pass "WTI10: no .purlin_worktree_label in main repo root (non-worktree session)"
else
    log_fail "WTI10: .purlin_worktree_label exists in main repo root — should only be in worktrees"
fi

# ──────────────────────────────────────────────
echo ""
echo "────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL tests passed"
if [ $FAIL -gt 0 ]; then
    printf "\nFailed tests:%s\n" "$ERRORS"
    exit 1
fi
exit 0
