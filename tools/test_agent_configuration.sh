#!/bin/bash
# test_agent_configuration.sh — Automated tests for agent configuration.
# Tests launcher behavior, provider probes, and detect-providers aggregator.
# Produces tests/agent_configuration/tests.json and tests/agent_launchers_common/tests.json at project root.
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

# Create a sandbox with minimal instructions and a mock claude binary.
# Sets SANDBOX, MOCK_DIR, CAPTURE_FILE, MOCK_CLAUDE.
setup_launcher_sandbox() {
    SANDBOX="$(mktemp -d)"
    MOCK_DIR="$(mktemp -d)"
    CAPTURE_FILE="$MOCK_DIR/captured_args"

    # Minimal instruction stubs so launcher cat commands don't fail
    mkdir -p "$SANDBOX/instructions" "$SANDBOX/.agentic_devops"
    echo "# stub" > "$SANDBOX/instructions/HOW_WE_WORK_BASE.md"
    echo "# stub" > "$SANDBOX/instructions/BUILDER_BASE.md"
    echo "# stub" > "$SANDBOX/instructions/ARCHITECT_BASE.md"
    echo "# stub" > "$SANDBOX/instructions/QA_BASE.md"

    # Mock claude that captures its args and exits 0
    cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "\$@" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/claude"
}

teardown_launcher_sandbox() {
    rm -rf "${SANDBOX:-}" "${MOCK_DIR:-}"
    unset SANDBOX MOCK_DIR CAPTURE_FILE
}

###############################################################################
echo "=== Agent Configuration Tests ==="
###############################################################################

# --- Scenario: Launcher Reads Agent Config from Config JSON ---
echo ""
echo "[Scenario] Launcher Reads Agent Config from Config JSON"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "architect": {
            "provider": "claude",
            "model": "claude-sonnet-4-6",
            "effort": "high",
            "bypass_permissions": false
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-sonnet-4-6'; then
    log_pass "Launcher passed --model claude-sonnet-4-6"
else
    log_fail "Launcher did not pass --model (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--effort high'; then
    log_pass "Launcher passed --effort high"
else
    log_fail "Launcher did not pass --effort high (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    log_pass "Launcher passed --allowedTools for Architect role (bypass=false)"
else
    log_fail "Launcher did not pass --allowedTools (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Falls Back When Config is Missing ---
echo ""
echo "[Scenario] Launcher Falls Back When Config is Missing"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_architect.sh" "$SANDBOX/"
# No config.json written — .agentic_devops/ is empty

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -qv -- '--model'; then
    log_pass "Launcher omits --model when config is missing (default behavior)"
else
    # --model could appear if config read silently picked up something unexpected
    log_fail "Launcher passed --model unexpectedly (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    log_pass "Architect role restrictions applied when falling back to defaults"
else
    log_fail "Architect role restrictions not applied on fallback (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Handles Unsupported Provider ---
echo ""
echo "[Scenario] Launcher Handles Unsupported Provider"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_builder.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "builder": {
            "provider": "openai",
            "model": "gpt-4o",
            "effort": "medium",
            "bypass_permissions": false
        }
    }
}
EOF

OUTPUT=$(PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_builder.sh" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    log_pass "Launcher exits non-zero for unsupported provider"
else
    log_fail "Launcher should exit non-zero for unsupported provider (got 0)"
fi

if echo "$OUTPUT" | grep -qi "not.*supported\|unsupported\|ERROR.*Provider"; then
    log_pass "Launcher prints error message for unsupported provider"
else
    log_fail "Launcher missing error message for unsupported provider: '$OUTPUT'"
fi

if echo "$OUTPUT" | grep -qi "claude"; then
    log_pass "Launcher lists supported providers (claude) in error output"
else
    log_fail "Launcher does not list supported providers in error: '$OUTPUT'"
fi

teardown_launcher_sandbox

# --- Scenario: Gemini Launcher Sets GEMINI_SYSTEM_MD ---
echo ""
echo "[Scenario] Gemini Launcher Sets GEMINI_SYSTEM_MD"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_qa.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "qa": {
            "provider": "gemini",
            "model": "gemini-3.0-pro",
            "effort": "",
            "bypass_permissions": true
        }
    }
}
EOF

# Mock gemini that captures its args and env
cat > "$MOCK_DIR/gemini" << MOCK_EOF
#!/bin/bash
echo "GEMINI_SYSTEM_MD=\$GEMINI_SYSTEM_MD" > "$CAPTURE_FILE"
echo "ARGS=\$@" >> "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/gemini"

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_qa.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q 'GEMINI_SYSTEM_MD=.*tmp'; then
    log_pass "GEMINI_SYSTEM_MD is set to a temporary prompt file path"
else
    log_fail "GEMINI_SYSTEM_MD not set (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '-m gemini-3.0-pro'; then
    log_pass "Gemini launcher passes -m gemini-3.0-pro"
else
    log_fail "Gemini launcher did not pass -m flag (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--yolo'; then
    log_pass "Gemini launcher passes --yolo for bypass_permissions=true"
else
    log_fail "Gemini launcher did not pass --yolo (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--no-gitignore'; then
    log_fail "Gemini launcher must not pass --no-gitignore (unsupported flag; captured: $CAPTURED)"
else
    log_pass "Gemini launcher does not pass --no-gitignore (unsupported in Gemini CLI v0.29+)"
fi

if echo "$CAPTURED" | grep -qE '(^| )-p '; then
    log_fail "Gemini launcher must not pass -p flag (captured: $CAPTURED)"
else
    log_pass "Gemini launcher does not pass -p flag (non-interactive mode prohibited)"
fi

teardown_launcher_sandbox

# --- Scenario: Gemini Launcher Skips Effort Flag ---
echo ""
echo "[Scenario] Gemini Launcher Skips Effort Flag"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_builder.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "builder": {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "effort": "high",
            "bypass_permissions": false
        }
    }
}
EOF

# Mock gemini that captures its args
cat > "$MOCK_DIR/gemini" << MOCK_EOF
#!/bin/bash
echo "ARGS=\$@" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/gemini"

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_builder.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--effort\|effort'; then
    log_fail "Gemini launcher must not pass effort-related argument (captured: $CAPTURED)"
else
    log_pass "Gemini launcher skips effort flag"
fi

if echo "$CAPTURED" | grep -qv -- '--yolo'; then
    log_pass "Gemini launcher omits --yolo when bypass_permissions=false"
else
    log_fail "Gemini launcher should not pass --yolo when bypass=false (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Exports AGENTIC_PROJECT_ROOT ---
echo ""
echo "[Scenario] Launcher Exports AGENTIC_PROJECT_ROOT"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "architect": {
            "provider": "claude",
            "model": "claude-sonnet-4-6",
            "effort": "",
            "bypass_permissions": true
        }
    }
}
EOF

# Mock claude that captures AGENTIC_PROJECT_ROOT from its env
cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "AGENTIC_PROJECT_ROOT=\$AGENTIC_PROJECT_ROOT" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q "AGENTIC_PROJECT_ROOT=$SANDBOX"; then
    log_pass "AGENTIC_PROJECT_ROOT exported as project root"
else
    log_fail "AGENTIC_PROJECT_ROOT not set correctly (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Claude Probe Detects Installed CLI ---
echo ""
echo "[Scenario] Claude Probe Detects Installed CLI"

PROBE_OUT=$(mktemp)
bash "$SCRIPT_DIR/providers/claude.sh" > "$PROBE_OUT" 2>/dev/null
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "claude.sh exits 0"
else
    log_fail "claude.sh must always exit 0 (got $EXIT_CODE)"
fi

if python3 -c "
import json, sys
data = json.load(open('$PROBE_OUT'))
assert 'provider' in data and data['provider'] == 'claude', 'provider must be claude'
assert isinstance(data.get('available'), bool), 'available must be bool'
assert isinstance(data.get('models'), list) and len(data['models']) > 0, 'models must be non-empty list'
for m in data['models']:
    assert 'id' in m and 'label' in m and 'capabilities' in m, 'model missing required fields'
    assert 'effort' in m['capabilities'] and 'permissions' in m['capabilities'], 'capabilities missing fields'
" 2>/dev/null; then
    log_pass "claude.sh outputs valid JSON with provider, available, and models with capabilities"
else
    log_fail "claude.sh output missing required fields: $(cat "$PROBE_OUT")"
fi

# When claude CLI is installed, available must be true
if command -v claude >/dev/null 2>&1; then
    if python3 -c "import json; d=json.load(open('$PROBE_OUT')); assert d['available'] is True" 2>/dev/null; then
        log_pass "claude.sh reports available=true when claude CLI is installed"
    else
        log_fail "claude.sh reports available=false but claude CLI is installed"
    fi
fi

rm -f "$PROBE_OUT"

# --- Scenario: Gemini Probe Detects API Key ---
echo ""
echo "[Scenario] Gemini Probe Detects API Key"

PROBE_OUT=$(mktemp)
GOOGLE_API_KEY="test-key-for-probe-test" bash "$SCRIPT_DIR/providers/gemini.sh" > "$PROBE_OUT" 2>/dev/null
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "gemini.sh exits 0"
else
    log_fail "gemini.sh must always exit 0 (got $EXIT_CODE)"
fi

if python3 -c "
import json
data = json.load(open('$PROBE_OUT'))
assert data.get('provider') == 'gemini', f'provider must be gemini, got: {data.get(\"provider\")}'
assert data.get('available') is True, f'available must be True when GOOGLE_API_KEY set, got: {data.get(\"available\")}'
assert isinstance(data.get('models'), list) and len(data['models']) > 0, 'models must be non-empty list'
" 2>/dev/null; then
    log_pass "gemini.sh reports available=true and returns models when GOOGLE_API_KEY is set"
else
    log_fail "gemini.sh failed required checks with GOOGLE_API_KEY set: $(cat "$PROBE_OUT")"
fi

rm -f "$PROBE_OUT"

# --- Scenario: Probe Handles Missing Provider Gracefully ---
echo ""
echo "[Scenario] Probe Handles Missing Provider Gracefully"

# Build a PATH that excludes the directory containing the claude CLI binary.
# System binaries (cat, head, etc.) must remain available so the probe script runs.
# If claude is not installed at all, the current PATH already satisfies the condition.
CLAUDE_BIN=$(command -v claude 2>/dev/null || echo "")
if [ -n "$CLAUDE_BIN" ]; then
    CLAUDE_BIN_DIR=$(dirname "$CLAUDE_BIN")
    RESTRICTED_PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "^${CLAUDE_BIN_DIR}$" | tr '\n' ':' | sed 's/:$//')
else
    RESTRICTED_PATH="$PATH"
fi

PROBE_OUT=$(mktemp)

PATH="$RESTRICTED_PATH" bash "$SCRIPT_DIR/providers/claude.sh" > "$PROBE_OUT" 2>/dev/null
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "claude.sh exits 0 when CLI not on PATH"
else
    log_fail "claude.sh must exit 0 even when CLI is not on PATH (got $EXIT_CODE)"
fi

if python3 -c "
import json
data = json.load(open('$PROBE_OUT'))
assert data.get('available') is False, f'available must be False when CLI absent, got: {data.get(\"available\")}'
assert data.get('provider') == 'claude', 'provider field must still be claude'
" 2>/dev/null; then
    log_pass "claude.sh reports available=false gracefully when CLI not on PATH"
else
    log_fail "claude.sh did not report available=false when CLI absent: $(cat "$PROBE_OUT")"
fi

rm -f "$PROBE_OUT"

# --- Scenario: Aggregator Collects All Providers ---
echo ""
echo "[Scenario] Aggregator Collects All Providers"

PROBE_COUNT=$(ls "$SCRIPT_DIR/providers/"*.sh 2>/dev/null | wc -l | tr -d ' ')
AGG_OUT=$(mktemp)

bash "$SCRIPT_DIR/detect-providers.sh" > "$AGG_OUT" 2>/dev/null
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "detect-providers.sh exits 0"
else
    log_fail "detect-providers.sh must exit 0 (got $EXIT_CODE)"
fi

if python3 -c "
import json
data = json.load(open('$AGG_OUT'))
assert isinstance(data, list), f'output must be a JSON array, got: {type(data)}'
assert len(data) == $PROBE_COUNT, f'expected $PROBE_COUNT entries (one per probe script), got {len(data)}'
for entry in data:
    assert 'provider' in entry, f'entry missing provider field: {entry}'
    assert 'available' in entry, f'entry missing available field: {entry}'
    assert 'models' in entry, f'entry missing models field: {entry}'
" 2>/dev/null; then
    log_pass "detect-providers.sh outputs JSON array with one entry per probe, each with provider/available/models"
else
    log_fail "detect-providers.sh output has wrong structure (expected $PROBE_COUNT entries): $(cat "$AGG_OUT")"
fi

rm -f "$AGG_OUT"

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

# Write tests/agent_configuration/tests.json and tests/agent_launchers_common/tests.json
# Both features share the same test suite (launchers depend on config).
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}"
for FEAT in agent_configuration agent_launchers_common; do
    OUTDIR="$TESTS_DIR/$FEAT"
    mkdir -p "$OUTDIR"
    echo "$RESULT_JSON" > "$OUTDIR/tests.json"
done

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
