#!/bin/bash
# test_python_env.sh — Tests for the Python environment isolation feature.
# Produces tests/python_environment/tests.json.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$SUBMODULE_SRC/tests"
PASS=0
FAIL=0
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

cleanup_sandbox() {
    if [ -n "${SANDBOX:-}" ] && [ -d "$SANDBOX" ]; then
        rm -rf "$SANDBOX"
    fi
}

# Build a sandbox with resolve_python.sh and a mock venv for testing.
setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT

    PROJECT="$SANDBOX/my-project"
    mkdir -p "$PROJECT/tools/critic"
    mkdir -p "$PROJECT/tools/cdd"

    # Copy resolve_python.sh into the sandbox
    cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$PROJECT/tools/resolve_python.sh"

    # Create a test sourcing script at tools/critic/ depth
    cat > "$PROJECT/tools/critic/test_source.sh" << 'SRCEOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../resolve_python.sh"
echo "$PYTHON_EXE"
SRCEOF
    chmod +x "$PROJECT/tools/critic/test_source.sh"
}

# Create a .venv with a python3 symlink at the given root
create_venv() {
    local root="$1"
    mkdir -p "$root/.venv/bin"
    ln -s "$(command -v python3)" "$root/.venv/bin/python3"
}

###############################################################################
echo "=== Python Environment Isolation Tests ==="
###############################################################################

# --- Scenario: resolve_python Uses AGENTIC_PYTHON Override ---
echo ""
echo "[Scenario] resolve_python Uses AGENTIC_PYTHON Override"
setup_sandbox
create_venv "$PROJECT"

SYSTEM_PYTHON="$(command -v python3)"
RESULT=$(AGENTIC_PYTHON="$SYSTEM_PYTHON" PURLIN_PROJECT_ROOT="$PROJECT" bash "$PROJECT/tools/critic/test_source.sh" 2>/dev/null)
if [ "$RESULT" = "$SYSTEM_PYTHON" ]; then
    log_pass "AGENTIC_PYTHON takes priority over .venv"
else
    log_fail "AGENTIC_PYTHON not used (got: $RESULT, expected: $SYSTEM_PYTHON)"
fi

cleanup_sandbox

# --- Scenario: resolve_python Finds Project Root Venv via PURLIN_PROJECT_ROOT ---
echo ""
echo "[Scenario] resolve_python Finds Project Root Venv via PURLIN_PROJECT_ROOT"
setup_sandbox
create_venv "$PROJECT"

RESULT=$(unset AGENTIC_PYTHON; PURLIN_PROJECT_ROOT="$PROJECT" bash "$PROJECT/tools/critic/test_source.sh" 2>/dev/null)
EXPECTED="$PROJECT/.venv/bin/python3"
if [ "$RESULT" = "$EXPECTED" ]; then
    log_pass "Project root venv found via PURLIN_PROJECT_ROOT"
else
    log_fail "Wrong venv (got: $RESULT, expected: $EXPECTED)"
fi

cleanup_sandbox

# --- Scenario: resolve_python Climbing Detection (Standalone Layout) ---
echo ""
echo "[Scenario] resolve_python Climbing Detection (Standalone Layout)"
setup_sandbox
create_venv "$PROJECT"

# Unset both env vars to force climbing from tools/critic/
RESULT=$(unset AGENTIC_PYTHON; unset PURLIN_PROJECT_ROOT; bash "$PROJECT/tools/critic/test_source.sh" 2>/dev/null)
EXPECTED="$PROJECT/.venv/bin/python3"
if [ "$RESULT" = "$EXPECTED" ]; then
    log_pass "Climbing detection finds standalone venv"
else
    log_fail "Climbing failed (got: $RESULT, expected: $EXPECTED)"
fi

cleanup_sandbox

# --- Scenario: resolve_python Climbing Detection (Submodule Layout) ---
echo ""
echo "[Scenario] resolve_python Climbing Detection (Submodule Layout)"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
PROJECT="$SANDBOX/my-project"
mkdir -p "$PROJECT/agentic-dev/tools/critic"

cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"
cat > "$PROJECT/agentic-dev/tools/critic/test_source.sh" << 'SRCEOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../resolve_python.sh"
echo "$PYTHON_EXE"
SRCEOF
chmod +x "$PROJECT/agentic-dev/tools/critic/test_source.sh"
create_venv "$PROJECT"

RESULT=$(unset AGENTIC_PYTHON; unset PURLIN_PROJECT_ROOT; bash "$PROJECT/agentic-dev/tools/critic/test_source.sh" 2>/dev/null)
EXPECTED="$PROJECT/.venv/bin/python3"
if [ "$RESULT" = "$EXPECTED" ]; then
    log_pass "Climbing detection finds submodule venv"
else
    log_fail "Submodule climbing failed (got: $RESULT, expected: $EXPECTED)"
fi

cleanup_sandbox

# --- Scenario: resolve_python Falls Back to System Python ---
echo ""
echo "[Scenario] resolve_python Falls Back to System Python"
setup_sandbox
# No .venv created — should fall back to system python3

RESULT=$(unset AGENTIC_PYTHON; unset PURLIN_PROJECT_ROOT; bash "$PROJECT/tools/critic/test_source.sh" 2>/dev/null)
SYSTEM_PYTHON="$(command -v python3)"
if [ "$RESULT" = "$SYSTEM_PYTHON" ]; then
    log_pass "Falls back to system python3"
else
    log_fail "System fallback wrong (got: $RESULT, expected: $SYSTEM_PYTHON)"
fi

# Verify no stderr output for system fallback
STDERR=$(unset AGENTIC_PYTHON; unset PURLIN_PROJECT_ROOT; bash "$PROJECT/tools/critic/test_source.sh" 2>&1 1>/dev/null)
if [ -z "$STDERR" ]; then
    log_pass "No diagnostic output for system python fallback"
else
    log_fail "Unexpected stderr for system fallback: $STDERR"
fi

cleanup_sandbox

# --- Scenario: resolve_python Diagnostic Output to Stderr Only ---
echo ""
echo "[Scenario] resolve_python Diagnostic Output to Stderr Only"
setup_sandbox
create_venv "$PROJECT"

STDOUT=$(PURLIN_PROJECT_ROOT="$PROJECT" bash "$PROJECT/tools/critic/test_source.sh" 2>/dev/null)
STDERR=$(PURLIN_PROJECT_ROOT="$PROJECT" bash "$PROJECT/tools/critic/test_source.sh" 2>&1 1>/dev/null)

if echo "$STDERR" | grep -q '\[resolve_python\]'; then
    log_pass "Diagnostic message printed to stderr with [resolve_python] tag"
else
    log_fail "Missing [resolve_python] diagnostic on stderr"
fi

# stdout should only contain the python path, no diagnostic
if echo "$STDOUT" | grep -q '\[resolve_python\]'; then
    log_fail "Diagnostic leaked to stdout"
else
    log_pass "No diagnostic pollution on stdout"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Shell Script Migration Tests (Code Inspection) ==="
###############################################################################

# --- Scenario: Critic run.sh Uses Resolved Python ---
echo ""
echo "[Scenario] Critic run.sh Uses Resolved Python"
CRITIC_RUN="$SCRIPT_DIR/critic/run.sh"
if grep -q 'source.*resolve_python\.sh' "$CRITIC_RUN"; then
    log_pass "critic/run.sh sources resolve_python.sh"
else
    log_fail "critic/run.sh does not source resolve_python.sh"
fi
if grep -q 'PYTHON_EXE.*critic\.py' "$CRITIC_RUN"; then
    log_pass "critic/run.sh uses \$PYTHON_EXE"
else
    log_fail "critic/run.sh does not use \$PYTHON_EXE"
fi

# --- Scenario: CDD status.sh Uses Resolved Python ---
echo ""
echo "[Scenario] CDD status.sh Uses Resolved Python"
CDD_STATUS="$SCRIPT_DIR/cdd/status.sh"
if grep -q 'source.*resolve_python\.sh' "$CDD_STATUS"; then
    log_pass "cdd/status.sh sources resolve_python.sh"
else
    log_fail "cdd/status.sh does not source resolve_python.sh"
fi
if grep -q 'PYTHON_EXE.*serve\.py' "$CDD_STATUS"; then
    log_pass "cdd/status.sh uses \$PYTHON_EXE"
else
    log_fail "cdd/status.sh does not use \$PYTHON_EXE"
fi

# --- Scenario: CDD start.sh Replaced Ad-Hoc Detection ---
echo ""
echo "[Scenario] CDD start.sh Replaced Ad-Hoc Detection"
CDD_START="$SCRIPT_DIR/cdd/start.sh"
if grep -q 'if \[ -d "\$DIR/../../\.venv" \]' "$CDD_START"; then
    log_fail "cdd/start.sh still contains ad-hoc venv detection"
else
    log_pass "cdd/start.sh ad-hoc venv detection removed"
fi
if grep -q 'source.*resolve_python\.sh' "$CDD_START"; then
    log_pass "cdd/start.sh sources resolve_python.sh"
else
    log_fail "cdd/start.sh does not source resolve_python.sh"
fi

# --- Scenario: Bootstrap Uses Resolved Python for JSON Validation ---
echo ""
echo "[Scenario] Bootstrap Uses Resolved Python for JSON Validation"
BOOTSTRAP="$SCRIPT_DIR/bootstrap.sh"
if grep -q 'source.*resolve_python\.sh' "$BOOTSTRAP"; then
    log_pass "bootstrap.sh sources resolve_python.sh"
else
    log_fail "bootstrap.sh does not source resolve_python.sh"
fi
if grep -q '\$PYTHON_EXE.*-c.*import json' "$BOOTSTRAP" || grep -q '"$PYTHON_EXE" -c.*import json' "$BOOTSTRAP"; then
    log_pass "bootstrap.sh uses \$PYTHON_EXE for JSON validation"
else
    log_fail "bootstrap.sh still uses bare python3 for JSON validation"
fi

# --- Scenario: test_lifecycle.sh Uses Resolved Python ---
echo ""
echo "[Scenario] test_lifecycle.sh Uses Resolved Python"
TEST_LIFECYCLE="$SCRIPT_DIR/cdd/test_lifecycle.sh"
if grep -q 'source.*resolve_python\.sh' "$TEST_LIFECYCLE"; then
    log_pass "test_lifecycle.sh sources resolve_python.sh"
else
    log_fail "test_lifecycle.sh does not source resolve_python.sh"
fi
if grep -q 'PYTHON_EXE.*-c' "$TEST_LIFECYCLE"; then
    log_pass "test_lifecycle.sh uses \$PYTHON_EXE in helpers"
else
    log_fail "test_lifecycle.sh still uses bare python3 in helpers"
fi

###############################################################################
echo ""
echo "=== Dependency Manifest Tests ==="
###############################################################################

# --- Scenario: requirements.txt Exists with No Packages ---
echo ""
echo "[Scenario] requirements.txt Exists with No Packages"
REQ_FILE="$SUBMODULE_SRC/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    # Check that every non-empty line is a comment
    NON_COMMENT=$(grep -v '^#' "$REQ_FILE" | grep -v '^[[:space:]]*$' || true)
    if [ -z "$NON_COMMENT" ]; then
        log_pass "requirements.txt contains only comments (no packages)"
    else
        log_fail "requirements.txt contains non-comment lines: $NON_COMMENT"
    fi
else
    log_fail "requirements.txt does not exist"
fi

# --- Scenario: requirements-optional.txt Lists anthropic ---
echo ""
echo "[Scenario] requirements-optional.txt Lists anthropic"
REQ_OPT="$SUBMODULE_SRC/requirements-optional.txt"
if [ -f "$REQ_OPT" ]; then
    if grep -q 'anthropic>=0.18.0' "$REQ_OPT"; then
        log_pass "requirements-optional.txt lists anthropic>=0.18.0"
    else
        log_fail "requirements-optional.txt missing anthropic>=0.18.0"
    fi
else
    log_fail "requirements-optional.txt does not exist"
fi

###############################################################################
echo ""
echo "=== Bootstrap Venv Suggestion Tests ==="
###############################################################################

# --- Scenario: Bootstrap Prints Venv Suggestion When No Venv Exists ---
echo ""
echo "[Scenario] Bootstrap Prints Venv Suggestion When No Venv Exists"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
PROJECT="$SANDBOX/my-project"
mkdir -p "$PROJECT"
git -C "$PROJECT" init -q
git clone -q "$SUBMODULE_SRC" "$PROJECT/agentic-dev"
# Overlay latest scripts
cp "$SUBMODULE_SRC/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/bootstrap.sh"
cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"
cp "$SUBMODULE_SRC/requirements-optional.txt" "$PROJECT/agentic-dev/requirements-optional.txt" 2>/dev/null || true
chmod +x "$PROJECT/agentic-dev/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"

OUTPUT=$("$PROJECT/agentic-dev/tools/bootstrap.sh" 2>&1)
if echo "$OUTPUT" | grep -q "requirements-optional.txt"; then
    log_pass "Venv suggestion printed when no .venv exists"
else
    log_fail "Venv suggestion missing when no .venv exists"
fi

cleanup_sandbox

# --- Scenario: Bootstrap Omits Venv Suggestion When Venv Exists ---
echo ""
echo "[Scenario] Bootstrap Omits Venv Suggestion When Venv Exists"
SANDBOX="$(mktemp -d)"
trap cleanup_sandbox EXIT
PROJECT="$SANDBOX/my-project"
mkdir -p "$PROJECT"
git -C "$PROJECT" init -q
git clone -q "$SUBMODULE_SRC" "$PROJECT/agentic-dev"
cp "$SUBMODULE_SRC/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/bootstrap.sh"
cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"
cp "$SUBMODULE_SRC/requirements-optional.txt" "$PROJECT/agentic-dev/requirements-optional.txt" 2>/dev/null || true
chmod +x "$PROJECT/agentic-dev/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"
mkdir -p "$PROJECT/.venv"

OUTPUT=$("$PROJECT/agentic-dev/tools/bootstrap.sh" 2>&1)
if echo "$OUTPUT" | grep -q "requirements-optional.txt"; then
    log_fail "Venv suggestion printed when .venv already exists"
else
    log_pass "Venv suggestion omitted when .venv exists"
fi

cleanup_sandbox

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

# Write tests/python_environment/tests.json
OUTDIR="$TESTS_DIR/python_environment"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
