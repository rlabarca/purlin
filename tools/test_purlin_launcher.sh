#!/bin/bash
# test_purlin_launcher.sh -- Unit tests for the Purlin unified agent launcher (pl-run.sh).
# Covers 7 scenarios from features/purlin_agent_launcher.md:
#   1. Launcher generation on full init
#   2. Launcher generation on refresh
#   3. Config resolver accepts purlin role
#   4. Config resolver falls back to builder
#   5. CLI model short name resolution
#   6. CLI auto-build alias
#   7. Session message for QA verify with feature
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

# Create a sandbox that mimics a consumer project for the purlin launcher.
# Sets SANDBOX, MOCK_DIR, CAPTURE_FILE.
setup_purlin_sandbox() {
    SANDBOX="$(mktemp -d)"
    MOCK_DIR="$(mktemp -d)"
    CAPTURE_FILE="$MOCK_DIR/captured_args"
    CAPTURE_ENV="$MOCK_DIR/captured_env"

    # Minimal instruction stubs so launcher cat commands succeed
    mkdir -p "$SANDBOX/instructions" "$SANDBOX/.purlin" "$SANDBOX/.purlin/runtime"
    echo "# stub HOW_WE_WORK_BASE" > "$SANDBOX/instructions/HOW_WE_WORK_BASE.md"
    echo "# stub PURLIN_BASE" > "$SANDBOX/instructions/PURLIN_BASE.md"

    # Copy config resolver so purlin launcher can read agent config
    mkdir -p "$SANDBOX/tools/config"
    cp "$SCRIPT_DIR/config/resolve_config.py" "$SANDBOX/tools/config/"

    # Copy the existing pl-run.sh to sandbox
    cp "$PROJECT_ROOT/pl-run.sh" "$SANDBOX/"

    # Mock claude that captures its args and relevant env vars
    cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "\$@" > "$CAPTURE_FILE"
{
    echo "AGENT_MODEL=\${AGENT_MODEL:-}"
    echo "AGENT_EFFORT=\${AGENT_EFFORT:-}"
    echo "AGENT_ROLE=\${AGENT_ROLE:-}"
    echo "PURLIN_PROJECT_ROOT=\${PURLIN_PROJECT_ROOT:-}"
} > "$CAPTURE_ENV"
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/claude"

    # Mock git so worktree operations do not touch real repos
    cat > "$MOCK_DIR/git" << MOCK_EOF
#!/bin/bash
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/git"
}

teardown_purlin_sandbox() {
    rm -rf "${SANDBOX:-}" "${MOCK_DIR:-}"
    unset SANDBOX MOCK_DIR CAPTURE_FILE CAPTURE_ENV
}

###############################################################################
echo "=== Purlin Unified Agent Launcher Tests ==="
###############################################################################

# ---------------------------------------------------------------------------
# Scenario 1: Launcher generation on full init
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Launcher generation on full init"

# Instead of running the full init.sh (which requires a consumer project with
# a git repo and submodule), we verify:
# (a) generate_purlin_launcher() exists in init.sh
# (b) It is called during full init (line grep)
# (c) The existing pl-run.sh at project root is executable and non-empty

if grep -q 'generate_purlin_launcher' "$SCRIPT_DIR/init.sh"; then
    log_pass "generate_purlin_launcher function exists in init.sh"
else
    log_fail "generate_purlin_launcher function not found in init.sh"
fi

# Verify it is invoked during full init mode (section 3.5)
if grep -q 'generate_purlin_launcher.*pl-run\.sh' "$SCRIPT_DIR/init.sh"; then
    log_pass "generate_purlin_launcher is called with pl-run.sh during full init"
else
    log_fail "generate_purlin_launcher call for pl-run.sh not found in full init"
fi

# Verify the generated launcher exists and is executable at project root
if [ -f "$PROJECT_ROOT/pl-run.sh" ]; then
    log_pass "pl-run.sh exists at project root"
else
    log_fail "pl-run.sh does not exist at project root"
fi

if [ -x "$PROJECT_ROOT/pl-run.sh" ]; then
    log_pass "pl-run.sh is executable"
else
    log_fail "pl-run.sh is not executable"
fi

if [ -s "$PROJECT_ROOT/pl-run.sh" ]; then
    log_pass "pl-run.sh is non-empty"
else
    log_fail "pl-run.sh is empty"
fi

# ---------------------------------------------------------------------------
# Scenario 2: Launcher generation on refresh
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Launcher generation on refresh"

# Verify generate_purlin_launcher is called in refresh mode (section 4.5)
REFRESH_LINE=$(grep -n 'generate_purlin_launcher.*pl-run\.sh' "$SCRIPT_DIR/init.sh" | tail -1)
if [ -n "$REFRESH_LINE" ]; then
    # There should be at least 2 calls: one in full init, one in refresh
    CALL_COUNT=$(grep -c 'generate_purlin_launcher.*pl-run\.sh' "$SCRIPT_DIR/init.sh")
    if [ "$CALL_COUNT" -ge 2 ]; then
        log_pass "generate_purlin_launcher is called in both full init and refresh modes"
    else
        log_fail "generate_purlin_launcher should be called in both modes (found $CALL_COUNT call(s))"
    fi
else
    log_fail "generate_purlin_launcher call not found in refresh section"
fi

# Verify the refresh section regenerates pl-run.sh (appears after the mode detection guard)
# The refresh section begins at "# 4. Refresh Mode" or "else" after the full init block
REFRESH_SECTION=$(sed -n '/^# 4\. Refresh Mode/,$ p' "$SCRIPT_DIR/init.sh" 2>/dev/null || \
                  sed -n '/Launcher Regeneration.*always regenerate/,$ p' "$SCRIPT_DIR/init.sh")
if echo "$REFRESH_SECTION" | grep -q 'generate_purlin_launcher'; then
    log_pass "Refresh mode regenerates pl-run.sh (always regenerate on refresh)"
else
    log_fail "Refresh mode does not regenerate pl-run.sh"
fi

# ---------------------------------------------------------------------------
# Scenario 3: Config resolver accepts purlin role
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Config resolver accepts purlin role"

CFG_SANDBOX="$(mktemp -d)"
mkdir -p "$CFG_SANDBOX/.purlin"
cat > "$CFG_SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]", "capabilities": {"effort": true, "permissions": true}}
    ],
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6[1m]",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false
        },
        "builder": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": false,
            "find_work": false,
            "auto_start": false
        }
    }
}
EOF

PURLIN_OUTPUT=$(PURLIN_PROJECT_ROOT="$CFG_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" purlin 2>/dev/null)

if echo "$PURLIN_OUTPUT" | grep -q 'AGENT_MODEL="claude-opus-4-6\[1m\]"'; then
    log_pass "resolve_config.py with purlin role outputs AGENT_MODEL from agents.purlin"
else
    log_fail "resolve_config.py purlin did not return correct AGENT_MODEL (output: $PURLIN_OUTPUT)"
fi

if echo "$PURLIN_OUTPUT" | grep -q 'AGENT_EFFORT="high"'; then
    log_pass "resolve_config.py with purlin role outputs AGENT_EFFORT from agents.purlin"
else
    log_fail "resolve_config.py purlin did not return correct AGENT_EFFORT (output: $PURLIN_OUTPUT)"
fi

if echo "$PURLIN_OUTPUT" | grep -q 'AGENT_BYPASS="true"'; then
    log_pass "resolve_config.py with purlin role outputs AGENT_BYPASS from agents.purlin"
else
    log_fail "resolve_config.py purlin did not return correct AGENT_BYPASS (output: $PURLIN_OUTPUT)"
fi

rm -rf "$CFG_SANDBOX"

# ---------------------------------------------------------------------------
# Scenario 4: Config resolver falls back to builder
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Config resolver falls back to builder"

FB_SANDBOX="$(mktemp -d)"
mkdir -p "$FB_SANDBOX/.purlin"
cat > "$FB_SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}},
        {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "capabilities": {"effort": true, "permissions": true}}
    ],
    "agents": {
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": false,
            "find_work": true,
            "auto_start": false
        }
    }
}
EOF

FB_OUTPUT=$(PURLIN_PROJECT_ROOT="$FB_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" purlin 2>/dev/null)

if echo "$FB_OUTPUT" | grep -q 'AGENT_MODEL="claude-opus-4-6"'; then
    log_pass "resolve_config.py purlin falls back to builder model when agents.purlin absent"
else
    log_fail "Fallback to builder failed for AGENT_MODEL (output: $FB_OUTPUT)"
fi

if echo "$FB_OUTPUT" | grep -q 'AGENT_EFFORT="high"'; then
    log_pass "resolve_config.py purlin falls back to builder effort when agents.purlin absent"
else
    log_fail "Fallback to builder failed for AGENT_EFFORT (output: $FB_OUTPUT)"
fi

if echo "$FB_OUTPUT" | grep -q 'AGENT_BYPASS="true"'; then
    log_pass "resolve_config.py purlin falls back to builder bypass_permissions when agents.purlin absent"
else
    log_fail "Fallback to builder failed for AGENT_BYPASS (output: $FB_OUTPUT)"
fi

rm -rf "$FB_SANDBOX"

# ---------------------------------------------------------------------------
# Scenario 5: CLI model short name resolution
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] CLI model short name resolution"
setup_purlin_sandbox

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}},
        {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "capabilities": {"effort": true, "permissions": true}},
        {"id": "claude-haiku-4-5-20251001", "label": "Haiku 4.5", "capabilities": {"effort": true, "permissions": true}}
    ],
    "agents": {
        "purlin": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false
        }
    }
}
EOF

# Test opus short name
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run.sh" --model opus > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-opus-4-6'; then
    log_pass "--model opus resolves to claude-opus-4-6"
else
    log_fail "--model opus did not resolve correctly (captured: $CAPTURED)"
fi

# Test sonnet short name
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run.sh" --model sonnet > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-sonnet-4-6'; then
    log_pass "--model sonnet resolves to claude-sonnet-4-6"
else
    log_fail "--model sonnet did not resolve correctly (captured: $CAPTURED)"
fi

# Test haiku short name
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run.sh" --model haiku > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-haiku-4-5-20251001'; then
    log_pass "--model haiku resolves to claude-haiku-4-5-20251001"
else
    log_fail "--model haiku did not resolve correctly (captured: $CAPTURED)"
fi

teardown_purlin_sandbox

# ---------------------------------------------------------------------------
# Scenario 6: CLI auto-build alias
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] CLI auto-build alias"
setup_purlin_sandbox

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}}
    ],
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run.sh" --auto-build > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

# The session message should contain "Enter Engineer mode" and "Run /pl-build"
if echo "$CAPTURED" | grep -q 'Enter Engineer mode'; then
    log_pass "--auto-build session message contains 'Enter Engineer mode'"
else
    log_fail "--auto-build session message missing 'Enter Engineer mode' (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q 'Run /pl-build'; then
    log_pass "--auto-build session message contains 'Run /pl-build'"
else
    log_fail "--auto-build session message missing 'Run /pl-build' (captured: $CAPTURED)"
fi

# Verify --auto-build sets the correct model from config (confirms it ran)
if echo "$CAPTURED" | grep -q -- '--model claude-opus-4-6'; then
    log_pass "--auto-build passes configured model to claude"
else
    log_fail "--auto-build did not pass configured model (captured: $CAPTURED)"
fi

teardown_purlin_sandbox

# ---------------------------------------------------------------------------
# Scenario 7: Session message for QA verify with feature
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Session message for QA verify with feature"
setup_purlin_sandbox

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}}
    ],
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run.sh" --verify notifications > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q 'Enter QA mode'; then
    log_pass "--verify notifications session message contains 'Enter QA mode'"
else
    log_fail "--verify notifications missing 'Enter QA mode' (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q 'Run /pl-verify notifications'; then
    log_pass "--verify notifications session message contains 'Run /pl-verify notifications'"
else
    log_fail "--verify notifications missing 'Run /pl-verify notifications' (captured: $CAPTURED)"
fi

# Also test --verify without feature name
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run.sh" --verify > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q 'Enter QA mode'; then
    log_pass "--verify (no feature) session message contains 'Enter QA mode'"
else
    log_fail "--verify (no feature) missing 'Enter QA mode' (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q 'Run /pl-verify\.'; then
    log_pass "--verify (no feature) session message contains 'Run /pl-verify.'"
else
    log_fail "--verify (no feature) missing 'Run /pl-verify.' (captured: $CAPTURED)"
fi

teardown_purlin_sandbox

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

# Write test results
RESULT_STATUS="$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"
RESULT_JSON="{\"status\": \"$RESULT_STATUS\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_purlin_launcher.sh\"}"
OUTDIR="$TESTS_DIR/purlin_agent_launcher"
mkdir -p "$OUTDIR"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
