#!/usr/bin/env bash
# tests/qa/test_pl_update_purlin_regression.sh
# QA-owned regression harness for features/pl_update_purlin.md
# Tests: standalone mode guard, pl-update-purlin command file exists,
#        fast path behavior (non-submodule consumer detection)
#
# Usage: bash tests/qa/test_pl_update_purlin_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: pl_update_purlin ==="
echo ""

# PU1: pl-update-purlin.md command file exists
CMD_FILE="$PURLIN_ROOT/.claude/commands/pl-update-purlin.md"
if [ -f "$CMD_FILE" ]; then
    log_pass "PU1: .claude/commands/pl-update-purlin.md exists"
else
    log_fail "PU1: pl-update-purlin.md command file not found"
fi

# PU2: Command file contains key behavioral elements
if [ -f "$CMD_FILE" ]; then
    if grep -q "standalone\|submodule\|guard" "$CMD_FILE" 2>/dev/null; then
        log_pass "PU2: command file references standalone/submodule guard behavior"
    else
        log_fail "PU2: command file missing standalone guard references"
    fi
fi

# PU3: Standalone guard — init.sh correctly detects standalone (non-consumer) mode
# The purlin repo itself IS standalone mode. init.sh should reject running in this context.
INIT_SH="$PURLIN_ROOT/tools/init.sh"
if [ -f "$INIT_SH" ]; then
    # Run init.sh from the purlin repo root — should trigger standalone guard
    INIT_OUT=$(cd "$PURLIN_ROOT" && bash "$INIT_SH" 2>&1 || true)
    if echo "$INIT_OUT" | grep -qi "standalone\|consumer\|submodule\|not.*consumer"; then
        log_pass "PU3: init.sh standalone guard fires when run from framework repo"
    else
        log_fail "PU3: init.sh standalone guard did not produce expected output (got: $(echo "$INIT_OUT" | head -3))"
    fi
else
    log_fail "PU3: tools/init.sh not found"
fi

# PU4: Feature spec exists and has regression testing section
FEATURE_SPEC="$PURLIN_ROOT/features/pl_update_purlin.md"
if [ -f "$FEATURE_SPEC" ]; then
    if grep -q "Regression Testing\|Regression Guidance" "$FEATURE_SPEC" 2>/dev/null; then
        log_pass "PU4: pl_update_purlin.md has regression section"
    else
        log_fail "PU4: pl_update_purlin.md missing regression section"
    fi
else
    log_fail "PU4: features/pl_update_purlin.md not found"
fi

# PU5: init.sh contains fast-path guard (already-current detection)
if grep -q "already\|current\|fast.path\|up.to.date\|no.op\|SAME" "$INIT_SH" 2>/dev/null; then
    log_pass "PU5: init.sh contains fast-path/already-current logic"
else
    log_fail "PU5: init.sh missing fast-path logic"
fi

echo ""
echo "────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL tests passed"
if [ $FAIL -gt 0 ]; then
    printf "\nFailed tests:%s\n" "$ERRORS"
    exit 1
fi
exit 0
