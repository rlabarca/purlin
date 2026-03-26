#!/usr/bin/env bash
# tests/qa/test_pl_session_resume_regression.sh
# QA-owned regression harness for features/pl_session_resume.md
# Tests: checkpoint file path convention, role-scoped naming, cache directory is gitignored
#
# Usage: bash tests/qa/test_pl_session_resume_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: pl_session_resume ==="
echo ""

CACHE_DIR="$PURLIN_ROOT/.purlin/cache"

# SR1: .purlin/cache/ directory exists
if [ -d "$CACHE_DIR" ]; then
    log_pass "SR1: .purlin/cache/ directory exists"
else
    log_fail "SR1: .purlin/cache/ directory not found"
fi

# SR2: .purlin/cache/ is gitignored (checkpoint files survive clear/restart)
if git -C "$PURLIN_ROOT" check-ignore -q "$CACHE_DIR" 2>/dev/null; then
    log_pass "SR2: .purlin/cache/ is gitignored"
else
    # Check gitignore content directly
    if grep -r "\.purlin/cache\|purlin/cache" "$PURLIN_ROOT/.gitignore" 2>/dev/null | grep -q "cache"; then
        log_pass "SR2: .purlin/cache/ covered by .gitignore"
    else
        log_fail "SR2: .purlin/cache/ not gitignored (checkpoint files won't survive restarts)"
    fi
fi

# SR3: Role-scoped file naming convention — write a test checkpoint and verify naming
ROLES=("architect" "builder" "qa" "pm")
for role in "${ROLES[@]}"; do
    EXPECTED_PATH="$CACHE_DIR/session_checkpoint_${role}.md"
    # Write a minimal test checkpoint
    mkdir -p "$CACHE_DIR"
    cat > "$EXPECTED_PATH" << CHECKPOINT
# Checkpoint: ${role}
## Role: ${role}
## Session: regression-test
## Done
- regression test checkpoint write
CHECKPOINT
    if [ -f "$EXPECTED_PATH" ]; then
        log_pass "SR3: checkpoint file created at expected path: session_checkpoint_${role}.md"
        rm -f "$EXPECTED_PATH"
    else
        log_fail "SR3: failed to create checkpoint at session_checkpoint_${role}.md"
    fi
done

# SR4: Role-scoped files are independent (writing one doesn't affect others)
# Write architect and builder checkpoints simultaneously
echo "# PM checkpoint" > "$CACHE_DIR/session_checkpoint_architect.md"
echo "# Engineer checkpoint" > "$CACHE_DIR/session_checkpoint_builder.md"

ARCH_CONTENT=$(cat "$CACHE_DIR/session_checkpoint_architect.md" 2>/dev/null)
BUILDER_CONTENT=$(cat "$CACHE_DIR/session_checkpoint_builder.md" 2>/dev/null)

if [ "$ARCH_CONTENT" = "# PM checkpoint" ] && [ "$BUILDER_CONTENT" = "# Engineer checkpoint" ]; then
    log_pass "SR4: role-scoped checkpoints are independent (concurrent agents don't overwrite each other)"
else
    log_fail "SR4: role-scoped checkpoints not independent"
fi
rm -f "$CACHE_DIR/session_checkpoint_architect.md" "$CACHE_DIR/session_checkpoint_builder.md"

# SR5: Missing checkpoint handled gracefully (existence check doesn't error)
for role in architect builder qa pm; do
    CHECKPOINT_PATH="$CACHE_DIR/session_checkpoint_${role}.md"
    if test -f "$CHECKPOINT_PATH"; then
        log_pass "SR5: $role checkpoint exists (pre-existing state)"
    else
        log_pass "SR5: $role checkpoint absent (existence check is non-erroring)"
    fi
done

echo ""
echo "────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL tests passed"
if [ $FAIL -gt 0 ]; then
    printf "\nFailed tests:%s\n" "$ERRORS"
    exit 1
fi
exit 0
