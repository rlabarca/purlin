#!/bin/bash
# test_agent_configuration.sh — Automated tests for model configuration and agent launchers.
# Tests launcher behavior with the flat models config schema (Claude-only).
# Produces tests/models_configuration/tests.json and tests/agent_launchers_common/tests.json at project root.
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

    # Mock git so pre-launch git add doesn't touch real repos
    cat > "$MOCK_DIR/git" << MOCK_EOF
#!/bin/bash
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/git"
}

teardown_launcher_sandbox() {
    rm -rf "${SANDBOX:-}" "${MOCK_DIR:-}"
    unset SANDBOX MOCK_DIR CAPTURE_FILE
}

###############################################################################
echo "=== Model Configuration & Launcher Tests ==="
###############################################################################

# --- Scenario: Config Schema Has Flat Models Array ---
echo ""
echo "[Scenario] Config Schema Has Flat Models Array"

CONFIG_FILE="$PROJECT_ROOT/.agentic_devops/config.json"
if [ -f "$CONFIG_FILE" ]; then
    if python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
assert isinstance(c.get('models'), list), 'top-level models must be a list'
assert len(c['models']) > 0, 'models must be non-empty'
for m in c['models']:
    assert 'id' in m and 'label' in m and 'capabilities' in m, f'model missing fields: {m}'
    assert 'effort' in m['capabilities'] and 'permissions' in m['capabilities'], f'caps missing: {m}'
assert 'llm_providers' not in c, 'llm_providers must not exist in new schema'
" 2>/dev/null; then
        log_pass "config.json has flat top-level models array with no llm_providers"
    else
        log_fail "config.json schema validation failed"
    fi

    if python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
agents = c.get('agents', {})
for role in ['architect', 'builder', 'qa']:
    a = agents.get(role, {})
    assert 'provider' not in a, f'{role} must not have provider field'
    assert 'model' in a, f'{role} missing model field'
    assert 'effort' in a, f'{role} missing effort field'
    assert 'bypass_permissions' in a, f'{role} missing bypass_permissions field'
" 2>/dev/null; then
        log_pass "agents entries have no provider field and include model/effort/bypass_permissions"
    else
        log_fail "agents entries have wrong fields"
    fi
else
    log_fail "config.json does not exist"
fi

# --- Scenario: Sample Config Matches Schema ---
echo ""
echo "[Scenario] Sample Config Matches Schema"

SAMPLE_FILE="$PROJECT_ROOT/agentic_devops.sample/config.json"
if [ -f "$SAMPLE_FILE" ]; then
    if python3 -c "
import json
c = json.load(open('$SAMPLE_FILE'))
assert isinstance(c.get('models'), list), 'sample must have top-level models array'
assert 'llm_providers' not in c, 'sample must not have llm_providers'
agents = c.get('agents', {})
for role in ['architect', 'builder', 'qa']:
    a = agents.get(role, {})
    assert 'provider' not in a, f'sample {role} must not have provider field'
" 2>/dev/null; then
        log_pass "agentic_devops.sample/config.json matches new schema"
    else
        log_fail "Sample config does not match new schema"
    fi
else
    log_fail "agentic_devops.sample/config.json does not exist"
fi

# --- Scenario: Provider Probe Infrastructure Removed ---
echo ""
echo "[Scenario] Provider Probe Infrastructure Removed"

if [ ! -d "$SCRIPT_DIR/providers" ]; then
    log_pass "tools/providers/ directory does not exist"
else
    log_fail "tools/providers/ directory still exists (should be deleted)"
fi

if [ ! -f "$SCRIPT_DIR/detect-providers.sh" ]; then
    log_pass "tools/detect-providers.sh does not exist"
else
    log_fail "tools/detect-providers.sh still exists (should be deleted)"
fi

# --- Scenario: Launcher Reads Agent Config from Config JSON ---
echo ""
echo "[Scenario] Claude Launcher Dispatches with Model and Effort"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "architect": {
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

if echo "$CAPTURED" | grep -q -- '--append-system-prompt-file'; then
    log_pass "Launcher passed --append-system-prompt-file"
else
    log_fail "Launcher did not pass --append-system-prompt-file (captured: $CAPTURED)"
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

# --- Scenario: Builder Launcher Has No AllowedTools ---
echo ""
echo "[Scenario] Builder Launcher Has No AllowedTools"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_builder.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": false
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_builder.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -qv -- '--allowedTools'; then
    log_pass "Builder launcher does not pass --allowedTools (default permissions)"
else
    log_fail "Builder launcher should not pass --allowedTools (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--model claude-opus-4-6'; then
    log_pass "Builder launcher passed --model"
else
    log_fail "Builder launcher did not pass --model (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: QA Launcher Has Correct AllowedTools ---
echo ""
echo "[Scenario] QA Launcher Has Correct AllowedTools"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_qa.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": false
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_qa.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    log_pass "QA launcher passed --allowedTools"
else
    log_fail "QA launcher did not pass --allowedTools (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- 'Write'; then
    log_pass "QA allowedTools includes Write"
else
    log_fail "QA allowedTools missing Write (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- 'Edit'; then
    log_pass "QA allowedTools includes Edit"
else
    log_fail "QA allowedTools missing Edit (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Bypass Permissions Passes Dangerously Skip ---
echo ""
echo "[Scenario] Bypass Permissions Passes Dangerously Skip"
setup_launcher_sandbox

cp "$PROJECT_ROOT/run_qa.sh" "$SANDBOX/"

cat > "$SANDBOX/.agentic_devops/config.json" << 'EOF'
{
    "agents": {
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/run_qa.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    log_pass "Launcher passes --dangerously-skip-permissions when bypass=true"
else
    log_fail "Launcher did not pass --dangerously-skip-permissions (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -qv -- '--allowedTools'; then
    log_pass "Launcher omits --allowedTools when bypass=true"
else
    log_fail "Launcher should not pass --allowedTools when bypass=true (captured: $CAPTURED)"
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

# --- Scenario: Launchers Have No Provider Dispatch ---
echo ""
echo "[Scenario] Launchers Have No Provider Dispatch"

HAS_CASE=0
for LAUNCHER in run_architect.sh run_builder.sh run_qa.sh; do
    if grep -q 'case.*AGENT_PROVIDER\|gemini\|AGENT_PROVIDER' "$PROJECT_ROOT/$LAUNCHER"; then
        log_fail "$LAUNCHER still contains provider dispatch or Gemini references"
        HAS_CASE=1
    fi
done
if [ $HAS_CASE -eq 0 ]; then
    log_pass "No launcher scripts contain provider dispatch or Gemini references"
fi

for LAUNCHER in run_architect.sh run_builder.sh run_qa.sh; do
    if grep -q 'provider' "$PROJECT_ROOT/$LAUNCHER"; then
        log_fail "$LAUNCHER still references 'provider'"
        HAS_CASE=1
    fi
done
if [ $HAS_CASE -eq 0 ]; then
    log_pass "No launcher scripts reference 'provider'"
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

# Write test results for both features
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}"
for FEAT in models_configuration agent_launchers_common; do
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
