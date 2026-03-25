#!/usr/bin/env bash
# tests/qa/test_purlin_migration_regression.sh
# QA-owned regression harness for features/purlin_migration.md
# Tests: complete-transition preconditions, migration-preserves-completeness preconditions
#
# Usage: bash tests/qa/test_purlin_migration_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
FIXTURE_TOOL="$PURLIN_ROOT/tools/test_support/fixture.sh"
FIXTURE_REPO="$PURLIN_ROOT/.purlin/runtime/fixture-repo"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: purlin_migration ==="
echo ""

# --- Scenario 1: Complete transition removes old artifacts ---
echo "--- Scenario 1: post-migration-with-old-artifacts fixture ---"

CHECKOUT1=""
CHECKOUT1=$("$FIXTURE_TOOL" checkout "$FIXTURE_REPO" "main/purlin_migration/post-migration-with-old-artifacts" 2>/dev/null) || {
    log_fail "M1: Could not check out post-migration fixture"
}

if [ -n "$CHECKOUT1" ] && [ -d "$CHECKOUT1" ]; then
    # M1: Config has agents.purlin
    if python3 -c "import json; d=json.load(open('$CHECKOUT1/.purlin/config.json')); assert 'purlin' in d['agents']" 2>/dev/null; then
        log_pass "M1: Config has agents.purlin (migration ran)"
    else
        log_fail "M1: Config missing agents.purlin"
    fi

    # M2: Config has deprecated old entries
    if python3 -c "
import json
d = json.load(open('$CHECKOUT1/.purlin/config.json'))
assert d['agents'].get('architect', {}).get('_deprecated') == True
assert d['agents'].get('builder', {}).get('_deprecated') == True
" 2>/dev/null; then
        log_pass "M2: Old agent entries marked _deprecated"
    else
        log_fail "M2: Old agent entries not properly deprecated"
    fi

    # M3: Old launchers exist
    OLD_LAUNCHERS_FOUND=0
    for role in architect builder qa pm; do
        [ -f "$CHECKOUT1/pl-run-${role}.sh" ] && OLD_LAUNCHERS_FOUND=$((OLD_LAUNCHERS_FOUND+1))
    done
    if [ "$OLD_LAUNCHERS_FOUND" -eq 4 ]; then
        log_pass "M3: All 4 old launchers present (pre-transition)"
    else
        log_fail "M3: Expected 4 old launchers, found $OLD_LAUNCHERS_FOUND"
    fi

    # M4: Old override files exist
    OLD_OVERRIDES_FOUND=0
    for f in ARCHITECT_OVERRIDES.md BUILDER_OVERRIDES.md QA_OVERRIDES.md PM_OVERRIDES.md; do
        [ -f "$CHECKOUT1/.purlin/$f" ] && OLD_OVERRIDES_FOUND=$((OLD_OVERRIDES_FOUND+1))
    done
    if [ "$OLD_OVERRIDES_FOUND" -ge 2 ]; then
        log_pass "M4: Old override files present ($OLD_OVERRIDES_FOUND found)"
    else
        log_fail "M4: Expected old override files, found $OLD_OVERRIDES_FOUND"
    fi

    # M5: Consolidated PURLIN_OVERRIDES.md exists
    if [ -f "$CHECKOUT1/.purlin/PURLIN_OVERRIDES.md" ]; then
        log_pass "M5: PURLIN_OVERRIDES.md exists (migration consolidated)"
    else
        log_fail "M5: PURLIN_OVERRIDES.md not found"
    fi

    "$FIXTURE_TOOL" cleanup "$CHECKOUT1" 2>/dev/null
fi

echo ""
echo "--- Scenario 2: old-4role-20-complete fixture ---"

CHECKOUT2=""
CHECKOUT2=$("$FIXTURE_TOOL" checkout "$FIXTURE_REPO" "main/purlin_migration/old-4role-20-complete" 2>/dev/null) || {
    log_fail "M6: Could not check out old-4role fixture"
}

if [ -n "$CHECKOUT2" ] && [ -d "$CHECKOUT2" ]; then
    # M6: Config has old 4-role agents but NO agents.purlin
    if python3 -c "
import json
d = json.load(open('$CHECKOUT2/.purlin/config.json'))
assert 'purlin' not in d['agents'], 'agents.purlin should not exist'
assert 'architect' in d['agents'], 'agents.architect should exist'
assert 'builder' in d['agents'], 'agents.builder should exist'
" 2>/dev/null; then
        log_pass "M6: Old 4-role config present, no agents.purlin"
    else
        log_fail "M6: Config does not have expected old 4-role structure"
    fi

    # M7: 20 feature files exist
    FEAT_COUNT=$(find "$CHECKOUT2/features" -maxdepth 1 -name "feature_*.md" ! -name "*.impl.md" | wc -l | tr -d ' ')
    if [ "$FEAT_COUNT" -eq 20 ]; then
        log_pass "M7: 20 feature files found"
    else
        log_fail "M7: Expected 20 feature files, found $FEAT_COUNT"
    fi

    # M8: All features have [Complete] tag
    COMPLETE_COUNT=0
    for f in "$CHECKOUT2/features"/feature_*.md; do
        [ -f "$f" ] || continue
        [[ "$f" == *.impl.md ]] && continue
        grep -q '\[Complete\]' "$f" && COMPLETE_COUNT=$((COMPLETE_COUNT+1))
    done
    if [ "$COMPLETE_COUNT" -eq 20 ]; then
        log_pass "M8: All 20 features marked [Complete]"
    else
        log_fail "M8: Expected 20 [Complete] features, found $COMPLETE_COUNT"
    fi

    # M9: Features contain old-style role references
    OLD_REF_COUNT=0
    for f in "$CHECKOUT2/features"/feature_*.md; do
        [ -f "$f" ] || continue
        [[ "$f" == *.impl.md ]] && continue
        if grep -q "the Architect\|the Builder" "$f" 2>/dev/null; then
            OLD_REF_COUNT=$((OLD_REF_COUNT+1))
        fi
    done
    if [ "$OLD_REF_COUNT" -ge 10 ]; then
        log_pass "M9: Features contain old-style role references ($OLD_REF_COUNT files)"
    else
        log_fail "M9: Expected old-style role references, found in $OLD_REF_COUNT files"
    fi

    # M10: Companion files exist for features
    IMPL_COUNT=$(find "$CHECKOUT2/features" -maxdepth 1 -name "feature_*.impl.md" | wc -l | tr -d ' ')
    if [ "$IMPL_COUNT" -eq 20 ]; then
        log_pass "M10: 20 companion files found"
    else
        log_fail "M10: Expected 20 companion files, found $IMPL_COUNT"
    fi

    # M11: scan.py recognizes [Migration] as exemption tag
    if python3 -c "
import sys
sys.path.insert(0, '$PURLIN_ROOT/tools/cdd')
# Check scan.py source for Migration exemption tag recognition
with open('$PURLIN_ROOT/tools/cdd/scan.py') as f:
    src = f.read()
assert 'Migration' in src, 'scan.py must recognize Migration tag'
" 2>/dev/null; then
        log_pass "M11: scan.py source references Migration exemption tag"
    else
        log_fail "M11: scan.py does not reference Migration exemption tag"
    fi

    "$FIXTURE_TOOL" cleanup "$CHECKOUT2" 2>/dev/null
fi

# Summary
echo ""
echo "Results: $((PASS+FAIL))/$((PASS+FAIL)) tests ran, ${PASS} passed, ${FAIL} failed"
if [ $FAIL -gt 0 ]; then
    echo -e "\nFailures:$ERRORS"
    exit 1
fi
exit 0
