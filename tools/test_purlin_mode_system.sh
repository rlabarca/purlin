#!/bin/bash
# test_purlin_mode_system.sh -- Unit tests for the Purlin Mode System feature.
# Covers all 13 unit test scenarios from features/purlin_mode_system.md plus
# additional structural checks (dual headers on all skills, no new-only headers).
# Produces tests/purlin_mode_system/tests.json at project root.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
COMMANDS_DIR="$PROJECT_ROOT/.claude/commands"
PURLIN_BASE="$PROJECT_ROOT/instructions/PURLIN_BASE.md"
PASS=0
FAIL=0
ERRORS=""
DETAILS=""

###############################################################################
# Helpers
###############################################################################
log_pass() {
    PASS=$((PASS + 1))
    echo "  PASS: $1"
    DETAILS="$DETAILS{\"test\": \"$1\", \"status\": \"PASS\"}, "
}
log_fail() {
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n  FAIL: $1"
    echo "  FAIL: $1"
    DETAILS="$DETAILS{\"test\": \"$1\", \"status\": \"FAIL\"}, "
}

###############################################################################
echo "=== Purlin Mode System Tests ==="
###############################################################################

# --- Scenario 1: Skill activates correct mode ---
echo ""
echo "[Scenario] Skill activates correct mode"

BUILD_FILE="$COMMANDS_DIR/pl-build.md"
if [ -f "$BUILD_FILE" ]; then
    LINE2=$(sed -n '2p' "$BUILD_FILE")
    if echo "$LINE2" | grep -q "Purlin mode: Engineer"; then
        log_pass "pl-build.md line 2 declares Purlin mode: Engineer"
    else
        log_fail "pl-build.md line 2 does not declare Purlin mode: Engineer (got: $LINE2)"
    fi
else
    log_fail "pl-build.md does not exist"
fi

# Also verify PURLIN_BASE.md lists /pl-build in Engineer mode activation
if [ -f "$PURLIN_BASE" ]; then
    if grep -q '3\.1 Engineer Mode' "$PURLIN_BASE" && grep -q '/pl-build' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md section 3.1 lists /pl-build under Engineer mode activation"
    else
        log_fail "PURLIN_BASE.md does not list /pl-build under Engineer mode activation"
    fi
else
    log_fail "PURLIN_BASE.md does not exist"
fi

# --- Scenario 2: Mode guard blocks write in wrong mode ---
echo ""
echo "[Scenario] Mode guard blocks write in wrong mode"

if [ -f "$PURLIN_BASE" ]; then
    if grep -q 'Mode Guard' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md contains Mode Guard section"
    else
        log_fail "PURLIN_BASE.md missing Mode Guard section"
    fi

    if grep -q "wrong mode" "$PURLIN_BASE" || grep -q "other mode.*-owned" "$PURLIN_BASE"; then
        log_pass "Mode guard describes blocking writes and suggesting correct mode"
    else
        log_fail "Mode guard does not describe blocking wrong-mode writes"
    fi

    if grep -q "write-access list" "$PURLIN_BASE"; then
        log_pass "Mode guard references write-access list verification"
    else
        log_fail "Mode guard does not reference write-access list"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for mode guard)"
    log_fail "Cannot check mode guard detail (PURLIN_BASE.md missing)"
    log_fail "Cannot check write-access list (PURLIN_BASE.md missing)"
fi

# --- Scenario 3: Cross-mode QA runs tests without switching ---
echo ""
echo "[Scenario] Cross-mode QA runs tests without switching"

if [ -f "$PURLIN_BASE" ]; then
    if grep -q 'Cross-mode test execution' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md describes cross-mode test execution"
    else
        log_fail "PURLIN_BASE.md missing cross-mode test execution description"
    fi

    if grep -q 'QA CAN invoke' "$PURLIN_BASE" || grep -q 'QA.*invoke.*test' "$PURLIN_BASE"; then
        log_pass "Cross-mode allows QA to invoke test tools"
    else
        log_fail "Cross-mode does not specify QA can invoke test tools"
    fi

    if grep -q 'without switching' "$PURLIN_BASE" || grep -q 'does NOT modify app code' "$PURLIN_BASE"; then
        log_pass "Cross-mode QA does not switch to Engineer or modify code"
    else
        log_fail "Cross-mode does not state QA stays in QA mode"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for cross-mode tests)"
    log_fail "Cannot check cross-mode QA invocation (PURLIN_BASE.md missing)"
    log_fail "Cannot check cross-mode QA no-switch (PURLIN_BASE.md missing)"
fi

# --- Scenario 4: Pre-switch commit prompt ---
echo ""
echo "[Scenario] Pre-switch commit prompt"

if [ -f "$PURLIN_BASE" ]; then
    if grep -q 'Pre-Switch Check' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md contains Pre-Switch Check section"
    else
        log_fail "PURLIN_BASE.md missing Pre-Switch Check section"
    fi

    if grep -q 'uncommitted work' "$PURLIN_BASE"; then
        log_pass "Pre-switch check mentions uncommitted work"
    else
        log_fail "Pre-switch check does not mention uncommitted work"
    fi

    if grep -qi 'commit first\|prompt to commit\|commit.*mode prefix' "$PURLIN_BASE"; then
        log_pass "Pre-switch prompts user to commit before switching"
    else
        log_fail "Pre-switch does not prompt to commit"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for pre-switch check)"
    log_fail "Cannot check uncommitted work detection (PURLIN_BASE.md missing)"
    log_fail "Cannot check commit prompt (PURLIN_BASE.md missing)"
fi

# --- Scenario 5: Dual skill header for legacy compatibility ---
echo ""
echo "[Scenario] Dual skill header for legacy compatibility"

if [ -f "$BUILD_FILE" ]; then
    LINE1=$(sed -n '1p' "$BUILD_FILE")
    if echo "$LINE1" | grep -q "Purlin command owner: Builder"; then
        log_pass "pl-build.md line 1 has legacy header: Purlin command owner: Builder"
    else
        log_fail "pl-build.md line 1 missing legacy header (got: $LINE1)"
    fi
else
    log_fail "pl-build.md does not exist (needed for dual header check)"
fi

# --- Scenario 6: Purlin-only skill blocked by legacy agents ---
echo ""
echo "[Scenario] Purlin-only skill blocked by legacy agents"

MODE_FILE="$COMMANDS_DIR/pl-mode.md"
if [ -f "$MODE_FILE" ]; then
    LINE1=$(sed -n '1p' "$MODE_FILE")
    if echo "$LINE1" | grep -q "Purlin command: Purlin agent only"; then
        log_pass "pl-mode.md line 1 has: Purlin command: Purlin agent only"
    else
        log_fail "pl-mode.md line 1 missing Purlin-only marker (got: $LINE1)"
    fi
else
    log_fail "pl-mode.md does not exist"
fi

# --- Scenario 7: Consolidated release skill subcommands ---
echo ""
echo "[Scenario] Consolidated release skill subcommands"

# Check consolidated files exist
CONSOLIDATED_PASS=true
for SKILL in pl-release.md pl-regression.md pl-remote.md; do
    if [ -f "$COMMANDS_DIR/$SKILL" ]; then
        log_pass "Consolidated skill $SKILL exists"
    else
        log_fail "Consolidated skill $SKILL does not exist"
        CONSOLIDATED_PASS=false
    fi
done

# Check old files are deleted
for OLD_SKILL in pl-release-check.md pl-release-run.md pl-release-step.md \
                 pl-regression-run.md pl-regression-author.md pl-regression-evaluate.md \
                 pl-remote-push.md pl-remote-pull.md pl-remote-add.md pl-edit-base.md; do
    if [ ! -f "$COMMANDS_DIR/$OLD_SKILL" ]; then
        log_pass "Old skill $OLD_SKILL correctly deleted"
    else
        log_fail "Old skill $OLD_SKILL still exists (should be deleted)"
    fi
done

# --- Scenario 8: pl-anchor dual-mode activation ---
echo ""
echo "[Scenario] pl-anchor dual-mode activation"

ANCHOR_FILE="$COMMANDS_DIR/pl-anchor.md"
if [ -f "$ANCHOR_FILE" ]; then
    if grep -q 'arch_\*' "$ANCHOR_FILE" && grep -q 'Engineer' "$ANCHOR_FILE"; then
        log_pass "pl-anchor.md references arch_* activating Engineer mode"
    else
        log_fail "pl-anchor.md does not reference arch_* -> Engineer activation"
    fi

    LINE2=$(sed -n '2p' "$ANCHOR_FILE")
    if echo "$LINE2" | grep -q "Purlin mode:"; then
        log_pass "pl-anchor.md line 2 has Purlin mode header"
    else
        log_fail "pl-anchor.md line 2 missing Purlin mode header (got: $LINE2)"
    fi
else
    log_fail "pl-anchor.md does not exist"
    log_fail "Cannot check pl-anchor mode header (file missing)"
fi

# --- Scenario 9: pl-anchor activates PM for design anchors ---
echo ""
echo "[Scenario] pl-anchor activates PM for design anchors"

if [ -f "$ANCHOR_FILE" ]; then
    if grep -q 'design_\*' "$ANCHOR_FILE" || grep -q 'design_.*PM' "$ANCHOR_FILE"; then
        log_pass "pl-anchor.md references design_* targets"
    else
        log_fail "pl-anchor.md does not reference design_* targets"
    fi

    if grep -q 'PM mode' "$ANCHOR_FILE" || grep -q 'activates PM' "$ANCHOR_FILE" || echo "$LINE2" | grep -q 'PM'; then
        log_pass "pl-anchor.md activates PM mode for design anchors"
    else
        log_fail "pl-anchor.md does not activate PM mode for design anchors"
    fi
else
    log_fail "pl-anchor.md does not exist (needed for PM activation check)"
    log_fail "Cannot check PM activation (file missing)"
fi

# --- Scenario 10: Commit attribution with mode trailer ---
echo ""
echo "[Scenario] Commit attribution with mode trailer"

if [ -f "$PURLIN_BASE" ]; then
    # Check for commit prefix conventions
    if grep -q 'feat(scope)' "$PURLIN_BASE" || grep -q 'feat(' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md defines Engineer commit prefix feat()"
    else
        log_fail "PURLIN_BASE.md missing Engineer commit prefix convention"
    fi

    if grep -q 'spec(scope)' "$PURLIN_BASE" || grep -q 'spec(' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md defines PM commit prefix spec()"
    else
        log_fail "PURLIN_BASE.md missing PM commit prefix convention"
    fi

    if grep -q 'qa(scope)' "$PURLIN_BASE" || grep -q 'qa(' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md defines QA commit prefix qa()"
    else
        log_fail "PURLIN_BASE.md missing QA commit prefix convention"
    fi

    if grep -q 'Purlin-Mode:' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md defines Purlin-Mode trailer"
    else
        log_fail "PURLIN_BASE.md missing Purlin-Mode trailer definition"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for commit attribution)"
    log_fail "Cannot check PM prefix (PURLIN_BASE.md missing)"
    log_fail "Cannot check QA prefix (PURLIN_BASE.md missing)"
    log_fail "Cannot check Purlin-Mode trailer (PURLIN_BASE.md missing)"
fi

# --- Scenario 11: iTerm badge set on mode activation ---
echo ""
echo "[Scenario] iTerm badge set on mode activation"

if [ -f "$PURLIN_BASE" ]; then
    if grep -q 'set_iterm_badge' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md references set_iterm_badge for mode activation"
    else
        log_fail "PURLIN_BASE.md missing set_iterm_badge reference"
    fi

    if grep -q 'set_term_title' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md references set_term_title for mode activation"
    else
        log_fail "PURLIN_BASE.md missing set_term_title reference"
    fi

    if grep -q '<project> - <mode>' "$PURLIN_BASE" || grep -q '<project>.*<mode>' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md specifies title format <project> - <mode>"
    else
        log_fail "PURLIN_BASE.md missing title format <project> - <mode>"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for iTerm badge check)"
    log_fail "Cannot check set_term_title (PURLIN_BASE.md missing)"
    log_fail "Cannot check title format (PURLIN_BASE.md missing)"
fi

# --- Scenario 12: iTerm badge reset to Purlin in open mode ---
echo ""
echo "[Scenario] iTerm badge reset to Purlin in open mode"

if [ -f "$PURLIN_BASE" ]; then
    if grep -q 'badge.*=.*Purlin' "$PURLIN_BASE" || grep -q 'badge = `Purlin`' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md specifies open mode badge = Purlin"
    else
        log_fail "PURLIN_BASE.md missing open mode badge = Purlin"
    fi

    if grep -q 'title.*=.*<project> - Purlin' "$PURLIN_BASE" || grep -q '<project> - Purlin' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md specifies open mode title = <project> - Purlin"
    else
        log_fail "PURLIN_BASE.md missing open mode title = <project> - Purlin"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for open mode badge check)"
    log_fail "Cannot check open mode title (PURLIN_BASE.md missing)"
fi

# --- Scenario 13: iTerm badge updates on mode switch ---
echo ""
echo "[Scenario] iTerm badge updates on mode switch"

if [ -f "$PURLIN_BASE" ]; then
    if grep -q 'mode switch.*update' "$PURLIN_BASE" || grep -q 'update both badge and title.*new mode' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md specifies badge+title update on mode switch"
    else
        log_fail "PURLIN_BASE.md missing badge+title update on mode switch"
    fi

    # Verify identity.sh helper is referenced for agent use
    if grep -q 'terminal/identity.sh' "$PURLIN_BASE"; then
        log_pass "PURLIN_BASE.md references terminal/identity.sh helper"
    else
        log_fail "PURLIN_BASE.md missing terminal/identity.sh reference"
    fi
else
    log_fail "PURLIN_BASE.md does not exist (needed for mode switch badge check)"
    log_fail "Cannot check identity.sh reference (PURLIN_BASE.md missing)"
fi

# --- Additional: All skill files have dual headers ---
echo ""
echo "[Additional] All skill files have both legacy and new headers"

SKILL_COUNT=0
DUAL_HEADER_COUNT=0
NEW_ONLY_COUNT=0
MISSING_LEGACY=()
MISSING_NEW=()

for SKILL_FILE in "$COMMANDS_DIR"/pl-*.md; do
    SKILL_NAME=$(basename "$SKILL_FILE")
    SKILL_COUNT=$((SKILL_COUNT + 1))
    LINE1=$(sed -n '1p' "$SKILL_FILE")
    LINE2=$(sed -n '2p' "$SKILL_FILE")

    HAS_LEGACY=false
    HAS_NEW=false

    # Legacy header: starts with **Purlin command (owner:|:)
    if echo "$LINE1" | grep -q '^\*\*Purlin command'; then
        HAS_LEGACY=true
    fi

    # New header: line 2 starts with **Purlin mode:
    if echo "$LINE2" | grep -q '^\*\*Purlin mode:'; then
        HAS_NEW=true
    fi

    if $HAS_LEGACY && $HAS_NEW; then
        DUAL_HEADER_COUNT=$((DUAL_HEADER_COUNT + 1))
    fi

    if ! $HAS_LEGACY; then
        MISSING_LEGACY+=("$SKILL_NAME")
    fi

    if ! $HAS_NEW; then
        MISSING_NEW+=("$SKILL_NAME")
    fi

    # Check for new-only (has Purlin mode but no legacy header) -- breaks legacy agents
    if $HAS_NEW && ! $HAS_LEGACY; then
        NEW_ONLY_COUNT=$((NEW_ONLY_COUNT + 1))
    fi
done

if [ "$SKILL_COUNT" -ge 33 ]; then
    log_pass "Found $SKILL_COUNT skill files (expected >= 33)"
else
    log_fail "Only found $SKILL_COUNT skill files (expected >= 33)"
fi

if [ "$DUAL_HEADER_COUNT" -eq "$SKILL_COUNT" ]; then
    log_pass "All $SKILL_COUNT skill files have both legacy and new headers"
else
    MISSING_MSG=""
    if [ ${#MISSING_LEGACY[@]} -gt 0 ]; then
        MISSING_MSG="Missing legacy: ${MISSING_LEGACY[*]}. "
    fi
    if [ ${#MISSING_NEW[@]} -gt 0 ]; then
        MISSING_MSG="${MISSING_MSG}Missing new: ${MISSING_NEW[*]}."
    fi
    log_fail "Only $DUAL_HEADER_COUNT/$SKILL_COUNT files have dual headers. $MISSING_MSG"
fi

if [ "$NEW_ONLY_COUNT" -eq 0 ]; then
    log_pass "No skill file has ONLY the new header format (legacy compatibility preserved)"
else
    log_fail "$NEW_ONLY_COUNT skill files have ONLY new header (breaks legacy agents)"
fi

# --- Scenario: Pre-switch companion file gate ---
echo ""
echo "[Scenario] Pre-switch companion file gate"

if [ -f "$PURLIN_BASE" ]; then
    if grep -qi 'companion file gate\|companion.*before switching\|companion.*entry.*before' "$PURLIN_BASE" 2>/dev/null; then
        log_pass "PURLIN_BASE.md describes companion file gate before mode switch"
    else
        log_fail "PURLIN_BASE.md missing companion file gate before mode switch"
    fi

    if grep -qi 'skip\|user.*says.*skip\|explicitly.*skip' "$PURLIN_BASE" 2>/dev/null; then
        log_pass "Companion file gate allows user to skip"
    else
        log_fail "Companion file gate missing skip option"
    fi
else
    log_fail "PURLIN_BASE.md missing (needed for companion file gate check)"
    log_fail "Cannot check skip option"
fi

# --- Scenario: Build status tag blocked by missing companion entry ---
echo ""
echo "[Scenario] Build status tag blocked by missing companion entry"

PL_BUILD="$COMMANDS_DIR/pl-build.md"
if [ -f "$PL_BUILD" ]; then
    if grep -qi 'companion.*gate\|companion.*block\|companion.*entry.*first\|BLOCK.*status.*tag.*companion' "$PL_BUILD" 2>/dev/null; then
        log_pass "pl-build.md blocks status tag on missing companion entry"
    else
        log_fail "pl-build.md missing companion file gate at status tag"
    fi
else
    log_fail "pl-build.md not found"
fi

# --- Scenario: Regression evaluate documents failure in companion file ---
echo ""
echo "[Scenario] Regression evaluate documents failure in companion file"

PL_REGRESSION="$COMMANDS_DIR/pl-regression.md"
if [ -f "$PL_REGRESSION" ]; then
    if grep -qi 'companion.*DISCOVERY\|impl\.md.*DISCOVERY\|\[DISCOVERY\].*companion' "$PL_REGRESSION" 2>/dev/null; then
        log_pass "pl-regression.md writes DISCOVERY to companion file on failure"
    else
        log_fail "pl-regression.md missing companion file DISCOVERY on regression failure"
    fi
else
    log_fail "pl-regression.md not found"
fi

###############################################################################
# Results
###############################################################################
echo ""
echo "==============================="
TOTAL=$((PASS + FAIL))
echo "  Results: $PASS/$TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

# Write tests.json
OUTDIR="$TESTS_DIR/purlin_mode_system"
mkdir -p "$OUTDIR"

# Build details array (trim trailing comma-space)
DETAILS_TRIMMED=$(echo "$DETAILS" | sed 's/, $//')
STATUS=$([ $FAIL -eq 0 ] && echo "PASS" || echo "FAIL")

cat > "$OUTDIR/tests.json" << EOF
{
  "status": "$STATUS",
  "passed": $PASS,
  "failed": $FAIL,
  "total": $TOTAL,
  "test_file": "tools/test_purlin_mode_system.sh",
  "details": [$DETAILS_TRIMMED]
}
EOF

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
