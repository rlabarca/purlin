#!/bin/bash
# Tests for subagent_parallel_builder feature.
# Verifies sub-agent definitions, instruction consolidation, server lifecycle skill,
# continuous mode deprecation, and BUILDER_BASE.md structure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

###############################################################################
echo "=== Sub-Agent Definition Tests ==="
###############################################################################

# --- Scenario: builder-worker.md exists with correct frontmatter ---
echo ""
echo "[Scenario] builder-worker.md exists with correct frontmatter"

BW_FILE="$PROJECT_ROOT/.claude/agents/builder-worker.md"
if [ -f "$BW_FILE" ]; then
    log_pass "builder-worker.md exists"
else
    log_fail "builder-worker.md not found at $BW_FILE"
fi

if grep -q '^name: builder-worker' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker has correct name"
else
    log_fail "builder-worker missing 'name: builder-worker'"
fi

if grep -q 'isolation: worktree' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker has isolation: worktree"
else
    log_fail "builder-worker missing 'isolation: worktree'"
fi

if grep -q 'skills:.*pl-build' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker preloads pl-build skill"
else
    log_fail "builder-worker missing pl-build in skills"
fi

if grep -q 'maxTurns: 200' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker has maxTurns: 200"
else
    log_fail "builder-worker missing maxTurns: 200"
fi

if grep -q 'model: inherit' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker uses model: inherit"
else
    log_fail "builder-worker missing model: inherit"
fi

# --- builder-worker constraints ---
echo ""
echo "[Scenario] builder-worker enforces single-feature and Steps 0-2 only"

if grep -qi 'single.feature' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker enforces single-feature focus"
else
    log_fail "builder-worker missing single-feature constraint"
fi

if grep -qi 'Steps 0-2 only' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker limits to Steps 0-2"
else
    log_fail "builder-worker missing Steps 0-2 limit"
fi

if grep -qi 'delivery_plan' "$BW_FILE" 2>/dev/null && grep -qi 'MUST NOT modify' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker prohibits delivery plan modification"
else
    log_fail "builder-worker missing delivery plan modification prohibition"
fi

# Check builder-worker cannot spawn nested sub-agents (no Agent tool)
if grep -qi 'no Agent' "$BW_FILE" 2>/dev/null || grep -qi 'MUST NOT spawn' "$BW_FILE" 2>/dev/null; then
    log_pass "builder-worker cannot spawn nested sub-agents"
else
    log_fail "builder-worker missing nested sub-agent prohibition"
fi

# --- Scenario: verification-runner.md exists with correct frontmatter ---
echo ""
echo "[Scenario] verification-runner.md exists with correct frontmatter"

VR_FILE="$PROJECT_ROOT/.claude/agents/verification-runner.md"
if [ -f "$VR_FILE" ]; then
    log_pass "verification-runner.md exists"
else
    log_fail "verification-runner.md not found at $VR_FILE"
fi

if grep -q '^name: verification-runner' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner has correct name"
else
    log_fail "verification-runner missing 'name: verification-runner'"
fi

if grep -q 'skills:.*pl-unit-test' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner preloads pl-unit-test skill"
else
    log_fail "verification-runner missing pl-unit-test in skills"
fi

if grep -q 'model: haiku' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner uses model: haiku"
else
    log_fail "verification-runner missing model: haiku"
fi

if grep -q 'background: true' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner has background: true"
else
    log_fail "verification-runner missing background: true"
fi

if grep -q 'maxTurns: 50' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner has maxTurns: 50"
else
    log_fail "verification-runner missing maxTurns: 50"
fi

if grep -q 'disallowedTools:.*Edit.*Agent\|disallowedTools:.*Agent.*Edit' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner disallows Edit and Agent"
else
    log_fail "verification-runner missing disallowedTools: Edit, Agent"
fi

# --- verification-runner constraints ---
echo ""
echo "[Scenario] verification-runner cannot edit files"

if grep -qi 'MUST NOT fix code' "$VR_FILE" 2>/dev/null; then
    log_pass "verification-runner prohibits code fixes"
else
    log_fail "verification-runner missing code fix prohibition"
fi

###############################################################################
echo ""
echo "=== Instruction Consolidation Tests ==="
###############################################################################

# --- Scenario: BUILDER_BASE.md Section 5 contains only skill invocation pointer ---
echo ""
echo "[Scenario] BUILDER_BASE.md Section 5 contains only skill invocation pointer"

BB_FILE="$PROJECT_ROOT/instructions/BUILDER_BASE.md"

# Extract Section 5 (between ## 5 and ## 6)
SEC5=$(sed -n '/^## 5\./,/^## 6\./{ /^## 6\./d; p; }' "$BB_FILE")

if echo "$SEC5" | grep -qi 'Invoke.*\/pl-build'; then
    log_pass "Section 5 contains 'Invoke /pl-build'"
else
    log_fail "Section 5 missing 'Invoke /pl-build'"
fi

if echo "$SEC5" | grep -qi '\/pl-unit-test'; then
    log_pass "Section 5 references /pl-unit-test"
else
    log_fail "Section 5 missing /pl-unit-test reference"
fi

if echo "$SEC5" | grep -qi '\/pl-server'; then
    log_pass "Section 5 references /pl-server"
else
    log_fail "Section 5 missing /pl-server reference"
fi

# Section 5 should be fewer than 10 lines
SEC5_LINES=$(echo "$SEC5" | grep -c '.' || true)
if [ "$SEC5_LINES" -lt 10 ]; then
    log_pass "Section 5 is concise ($SEC5_LINES non-blank lines)"
else
    log_fail "Section 5 is too long ($SEC5_LINES lines, expected <10)"
fi

# Section 5 should NOT contain web test verification rules directly
if echo "$SEC5" | grep -qi 'web test.*verification.*rule\|browser_navigate\|browser_snapshot'; then
    log_fail "Section 5 contains web test rules (should be in /pl-build)"
else
    log_pass "Section 5 does not contain web test rules"
fi

# Section 5 should NOT contain phase halt rules directly
if echo "$SEC5" | grep -qi 'phase.*halt.*rule\|STOP the session'; then
    log_fail "Section 5 contains phase halt rules (should be in /pl-build)"
else
    log_pass "Section 5 does not contain phase halt rules"
fi

# --- Scenario: Old Section 7 (Agentic Team Orchestration) is deleted ---
echo ""
echo "[Scenario] Old Section 7 (Agentic Team Orchestration) is deleted"

if grep -qi 'Agentic Team Orchestration' "$BB_FILE" 2>/dev/null; then
    log_fail "BUILDER_BASE.md still contains 'Agentic Team Orchestration'"
else
    log_pass "Agentic Team Orchestration section is removed"
fi

###############################################################################
echo ""
echo "=== Server Lifecycle Skill Tests ==="
###############################################################################

# --- Scenario: pl-server.md exists with required content ---
echo ""
echo "[Scenario] pl-server.md exists with required content"

PS_FILE="$PROJECT_ROOT/.claude/commands/pl-server.md"
if [ -f "$PS_FILE" ]; then
    log_pass "pl-server.md exists"
else
    log_fail "pl-server.md not found"
fi

if grep -qi 'port.*management\|port.*availab\|alternate port' "$PS_FILE" 2>/dev/null; then
    log_pass "pl-server.md covers port management"
else
    log_fail "pl-server.md missing port management"
fi

if grep -qi 'dev_server.json' "$PS_FILE" 2>/dev/null; then
    log_pass "pl-server.md references dev_server.json state file"
else
    log_fail "pl-server.md missing dev_server.json reference"
fi

if grep -qi 'cleanup\|session.*end\|stopped' "$PS_FILE" 2>/dev/null; then
    log_pass "pl-server.md covers cleanup guarantee"
else
    log_fail "pl-server.md missing cleanup guarantee"
fi

if grep -qi 'NEVER.*production\|NEVER.*persistent' "$PS_FILE" 2>/dev/null; then
    log_pass "pl-server.md prohibits production server management"
else
    log_fail "pl-server.md missing production server prohibition"
fi

###############################################################################
echo ""
echo "=== Continuous Mode Deprecation Tests ==="
###############################################################################

# --- Scenario: --continuous flag prints deprecation warning and exits ---
echo ""
echo "[Scenario] --continuous flag prints deprecation warning and exits"

BUILDER_LAUNCHER="$PROJECT_ROOT/pl-run-builder.sh"
DEPRECATION_OUTPUT=$(bash "$BUILDER_LAUNCHER" --continuous 2>&1) && DEPRECATION_EXIT=0 || DEPRECATION_EXIT=$?

if echo "$DEPRECATION_OUTPUT" | grep -qi 'deprecated'; then
    log_pass "--continuous prints deprecation warning"
else
    log_fail "--continuous did not print deprecation warning"
fi

if echo "$DEPRECATION_OUTPUT" | grep -qi 'auto_start.*true'; then
    log_pass "--continuous mentions auto_start: true alternative"
else
    log_fail "--continuous missing auto_start: true guidance"
fi

if [ "$DEPRECATION_EXIT" -ne 0 ]; then
    log_pass "--continuous exits with non-zero status"
else
    log_fail "--continuous did not exit with non-zero status"
fi

###############################################################################
echo ""
echo "=== /pl-build Skill Content Tests ==="
###############################################################################

# --- Scenario: /pl-build contains robust merge protocol ---
echo ""
echo "[Scenario] /pl-build skill contains required protocols"

PB_FILE="$PROJECT_ROOT/.claude/commands/pl-build.md"

if grep -qi 'Robust Merge Protocol' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build contains Robust Merge Protocol"
else
    log_fail "/pl-build missing Robust Merge Protocol"
fi

if grep -qi 'builder-worker' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build references builder-worker sub-agent"
else
    log_fail "/pl-build missing builder-worker reference"
fi

if grep -qi 'safe.*file\|CRITIC_REPORT\|delivery_plan' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build defines safe file list for merge conflict resolution"
else
    log_fail "/pl-build missing safe file list"
fi

if grep -qi 'Bright-Line Rules' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build contains Bright-Line Rules section"
else
    log_fail "/pl-build missing Bright-Line Rules section"
fi

if grep -qi 'Server Lifecycle' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build contains Server Lifecycle section"
else
    log_fail "/pl-build missing Server Lifecycle section"
fi

if grep -qi 'auto_start.*true.*auto-advance\|auto_start.*true.*next.*PENDING\|auto-advance' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build contains auto-progression logic"
else
    log_fail "/pl-build missing auto-progression logic"
fi

###############################################################################
echo ""
echo "=== Execution Group Dispatch Bright-Line Rule Tests ==="
###############################################################################

# --- Scenario: Execution group dispatch bright-line rule exists in /pl-build ---
echo ""
echo "[Scenario] Execution group dispatch bright-line rule exists in /pl-build"

PB_FILE="$PROJECT_ROOT/.claude/commands/pl-build.md"

# Rule about execution group dispatch being mandatory must exist in Bright-Line Rules section
if grep -q 'Execution group dispatch is mandatory for multi-feature groups' "$PB_FILE" 2>/dev/null; then
    log_pass "/pl-build contains execution group dispatch bright-line rule"
else
    log_fail "/pl-build missing execution group dispatch bright-line rule"
fi

# Rule must require reading dependency_graph.json before Step 0
if grep -q 'dependency_graph.json' "$PB_FILE" 2>/dev/null && grep -q 'BEFORE beginning Step 0' "$PB_FILE" 2>/dev/null; then
    log_pass "Rule requires reading dependency_graph.json before Step 0"
else
    log_fail "Rule missing requirement to read dependency_graph.json before Step 0"
fi

# Rule must label sequential processing of independent features as protocol violation
if grep -q 'protocol violation' "$PB_FILE" 2>/dev/null; then
    log_pass "Rule labels sequential processing as protocol violation"
else
    log_fail "Rule missing protocol violation label"
fi

###############################################################################
echo ""
echo "=== Resume Protocol Tests ==="
###############################################################################

# --- Scenario: Resume checkpoint format includes Parallel B1 State ---
echo ""
echo "[Scenario] Resume checkpoint includes Parallel B1 State field"

RESUME_FILE="$PROJECT_ROOT/.claude/commands/pl-resume.md"

if grep -q 'Parallel B1 State' "$RESUME_FILE" 2>/dev/null; then
    log_pass "pl-resume checkpoint includes Parallel B1 State field"
else
    log_fail "pl-resume checkpoint missing Parallel B1 State field"
fi

# --- Scenario: Resume includes orphaned worktree branch recovery ---
echo ""
echo "[Scenario] Resume includes orphaned sub-agent branch recovery"

if grep -qi 'worktree-\*\|orphaned.*worktree\|Orphaned Sub-Agent' "$RESUME_FILE" 2>/dev/null; then
    log_pass "pl-resume includes orphaned worktree branch recovery"
else
    log_fail "pl-resume missing orphaned worktree branch recovery"
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
TESTS_DIR="$PROJECT_ROOT/tests"
OUTDIR="$TESTS_DIR/subagent_parallel_builder"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_subagent_parallel_builder.sh\"}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
