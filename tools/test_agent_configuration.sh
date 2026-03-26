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
    mkdir -p "$SANDBOX/instructions" "$SANDBOX/.purlin" "$SANDBOX/.purlin/runtime"
    echo "# stub" > "$SANDBOX/instructions/PURLIN_BASE.md"

    # Copy config resolver so launchers can read agent config
    mkdir -p "$SANDBOX/tools/config"
    cp "$SCRIPT_DIR/config/resolve_config.py" "$SANDBOX/tools/config/"

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

CONFIG_FILE="$PROJECT_ROOT/.purlin/config.json"
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

# --- Scenario: Config Schema Validates All Agent Roles ---
echo ""
echo "[Scenario] Config Schema Validates All Agent Roles"

if [ -f "$CONFIG_FILE" ]; then
    if python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
agents = c.get('agents', {})
models = {m['id'] for m in c.get('models', [])}
for role in ['architect', 'builder', 'qa']:
    a = agents[role]
    assert isinstance(a.get('model'), str), f'{role} model must be string'
    assert isinstance(a.get('effort'), str), f'{role} effort must be string'
    assert isinstance(a.get('bypass_permissions'), bool), f'{role} bypass_permissions must be bool'
    assert a['model'] in models, f'{role} model {a[\"model\"]} not in models array'
# PM is optional - if present, validate same fields
if 'pm' in agents:
    a = agents['pm']
    assert isinstance(a.get('model'), str), 'pm model must be string'
    assert isinstance(a.get('effort'), str), 'pm effort must be string'
    assert isinstance(a.get('bypass_permissions'), bool), 'pm bypass_permissions must be bool'
    assert a['model'] in models, f'pm model {a[\"model\"]} not in models array'
" 2>/dev/null; then
        log_pass "All agent roles (architect, builder, qa, optional pm) validate correctly"
    else
        log_fail "Agent role validation failed"
    fi
else
    log_fail "config.json does not exist"
fi

# --- Scenario: PM Agent Entry is Optional ---
echo ""
echo "[Scenario] PM Agent Entry is Optional"

# Test 1: resolve_config.py accepts 'pm' role
if python3 -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR/config')
os.environ['PURLIN_PROJECT_ROOT'] = '$PROJECT_ROOT'
from resolve_config import resolve_config, _cli_role
# Should not raise when called with 'pm'
_cli_role('$PROJECT_ROOT', 'pm')
" > /dev/null 2>&1; then
    log_pass "resolve_config.py accepts 'pm' as a valid role"
else
    log_fail "resolve_config.py does not accept 'pm' role"
fi

# Test 2: PM falls back to defaults when absent from config
PM_SANDBOX="$(mktemp -d)"
mkdir -p "$PM_SANDBOX/.purlin"
cat > "$PM_SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": { "model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": false },
        "builder": { "model": "claude-opus-4-6", "effort": "high", "bypass_permissions": true },
        "qa": { "model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": false }
    }
}
EOF

PM_OUTPUT=$(PURLIN_PROJECT_ROOT="$PM_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" pm 2>/dev/null)
if echo "$PM_OUTPUT" | grep -q 'AGENT_MODEL=""'; then
    log_pass "PM falls back to empty model when absent from config"
else
    log_fail "PM did not fall back correctly (output: $PM_OUTPUT)"
fi
rm -rf "$PM_SANDBOX"

# --- Scenario: Sample Config Matches Schema ---
echo ""
echo "[Scenario] Sample Config Matches Schema"

SAMPLE_FILE="$PROJECT_ROOT/purlin-config-sample/config.json"
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
        log_pass "purlin-config-sample/config.json matches new schema"
    else
        log_fail "Sample config does not match new schema"
    fi
else
    log_fail "purlin-config-sample/config.json does not exist"
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

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
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

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>&1
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
    log_pass "Launcher passed --allowedTools for PM role (bypass=false)"
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

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"
# No config.json written — .purlin/ is empty

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -qv -- '--model'; then
    log_pass "Launcher omits --model when config is missing (default behavior)"
else
    # --model could appear if config read silently picked up something unexpected
    log_fail "Launcher passed --model unexpectedly (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    log_pass "PM role restrictions applied when falling back to defaults"
else
    log_fail "PM role restrictions not applied on fallback (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Engineer Launcher Has No AllowedTools ---
echo ""
echo "[Scenario] Engineer Launcher Has No AllowedTools"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-builder.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
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

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-builder.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -qv -- '--allowedTools'; then
    log_pass "Engineer launcher does not pass --allowedTools (default permissions)"
else
    log_fail "Engineer launcher should not pass --allowedTools (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--model claude-opus-4-6'; then
    log_pass "Engineer launcher passed --model"
else
    log_fail "Engineer launcher did not pass --model (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: QA Launcher Has Correct AllowedTools ---
echo ""
echo "[Scenario] QA Launcher Has Correct AllowedTools"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-qa.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
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

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-qa.sh" > /dev/null 2>&1
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

cp "$PROJECT_ROOT/pl-run-qa.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
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

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-qa.sh" > /dev/null 2>&1
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

# --- Scenario: Launcher Exports PURLIN_PROJECT_ROOT ---
echo ""
echo "[Scenario] Launcher Exports PURLIN_PROJECT_ROOT"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
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

# Mock claude that captures PURLIN_PROJECT_ROOT from its env
cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "PURLIN_PROJECT_ROOT=\$PURLIN_PROJECT_ROOT" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q "PURLIN_PROJECT_ROOT=$SANDBOX"; then
    log_pass "PURLIN_PROJECT_ROOT exported as project root"
else
    log_fail "PURLIN_PROJECT_ROOT not set correctly (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Exports AGENT_ROLE ---
echo ""
echo "[Scenario] Launcher Exports AGENT_ROLE"
setup_launcher_sandbox

# Test each launcher exports its correct AGENT_ROLE
for ROLE_INFO in "architect:pl-run-architect.sh" "builder:pl-run-builder.sh" "qa:pl-run-qa.sh"; do
    ROLE="${ROLE_INFO%%:*}"
    LAUNCHER="${ROLE_INFO#*:}"

    cp "$PROJECT_ROOT/$LAUNCHER" "$SANDBOX/"

    cat > "$SANDBOX/.purlin/config.json" << EOF
{
    "agents": {
        "$ROLE": {
            "model": "claude-sonnet-4-6",
            "effort": "",
            "bypass_permissions": true
        }
    }
}
EOF

    # Mock claude that captures AGENT_ROLE from its env
    cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "AGENT_ROLE=\$AGENT_ROLE" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/claude"

    PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/$LAUNCHER" > /dev/null 2>&1
    CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

    if echo "$CAPTURED" | grep -q "AGENT_ROLE=$ROLE"; then
        log_pass "$LAUNCHER exports AGENT_ROLE=$ROLE"
    else
        log_fail "$LAUNCHER AGENT_ROLE not set correctly (captured: $CAPTURED)"
    fi
done

teardown_launcher_sandbox

# --- Scenario: Launcher Reads Resolved Config ---
echo ""
echo "[Scenario] Launcher Reads Resolved Config"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
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

# Verify launcher script calls resolve_config.py (not inline Python json import)
if grep -q 'resolve_config.py' "$SANDBOX/pl-run-architect.sh"; then
    log_pass "Launcher references resolve_config.py"
else
    log_fail "Launcher does not reference resolve_config.py"
fi

if ! grep -q 'python3 -c.*import json' "$SANDBOX/pl-run-architect.sh"; then
    log_pass "Launcher does not use inline Python to read config.json directly"
else
    log_fail "Launcher uses inline Python pattern (should use resolve_config.py)"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Falls Back When Config is Absent ---
echo ""
echo "[Scenario] Launcher Falls Back When Config is Absent (resolve_config.py unavailable)"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"
# Remove resolve_config.py from sandbox to simulate unavailability
rm -f "$SANDBOX/tools/config/resolve_config.py"
# No config.json written

# Mock claude that captures its env vars
cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "MODEL=\${AGENT_MODEL:-} EFFORT=\${AGENT_EFFORT:-} BYPASS=\${AGENT_BYPASS:-}" > "$CAPTURE_FILE"
echo "\$@" >> "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

# With resolver absent, defaults should apply: empty model, empty effort, bypass false
# Check CLI args: no --model (empty default), --allowedTools present (bypass=false default)
if echo "$CAPTURED" | grep -qv -- '--model'; then
    log_pass "Fallback defaults: no --model passed (empty default)"
else
    log_fail "Fallback: --model unexpectedly present (captured: $CAPTURED)"
fi

# Should still launch claude (with --allowedTools since bypass defaults to false)
if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    log_pass "Fallback: launcher dispatches with role restrictions (bypass=false default)"
else
    log_fail "Fallback: launcher did not dispatch correctly (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Launchers Have No Provider Dispatch ---
echo ""
echo "[Scenario] Launchers Have No Provider Dispatch"

HAS_CASE=0
for LAUNCHER in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh; do
    if grep -q 'case.*AGENT_PROVIDER\|gemini\|AGENT_PROVIDER' "$PROJECT_ROOT/$LAUNCHER"; then
        log_fail "$LAUNCHER still contains provider dispatch or Gemini references"
        HAS_CASE=1
    fi
done
if [ $HAS_CASE -eq 0 ]; then
    log_pass "No launcher scripts contain provider dispatch or Gemini references"
fi

for LAUNCHER in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh; do
    if grep -q 'provider' "$PROJECT_ROOT/$LAUNCHER"; then
        log_fail "$LAUNCHER still references 'provider'"
        HAS_CASE=1
    fi
done
if [ $HAS_CASE -eq 0 ]; then
    log_pass "No launcher scripts reference 'provider'"
fi

# --- Scenario: Model With Warning Field Triggers Display at Configuration Surfaces ---
echo ""
echo "[Scenario] Model With Warning Field Triggers Display at Configuration Surfaces"

# Test that resolve_config.py outputs AGENT_MODEL_WARNING for a model with a warning
WARNING_SANDBOX="$(mktemp -d)"
mkdir -p "$WARNING_SANDBOX/.purlin"
cat > "$WARNING_SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}},
        {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]", "capabilities": {"effort": true, "permissions": true}, "warning": "Extended context costs extra.", "warning_dismissible": true}
    ],
    "agents": {
        "architect": {"model": "claude-opus-4-6[1m]", "effort": "high", "bypass_permissions": true}
    }
}
EOF

WARN_OUTPUT=$(PURLIN_PROJECT_ROOT="$WARNING_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" architect 2>/dev/null)

if echo "$WARN_OUTPUT" | grep -q 'AGENT_MODEL_WARNING="Extended context costs extra."'; then
    log_pass "resolve_config.py outputs AGENT_MODEL_WARNING for model with warning"
else
    log_fail "AGENT_MODEL_WARNING not set correctly (output: $WARN_OUTPUT)"
fi

if echo "$WARN_OUTPUT" | grep -q 'AGENT_MODEL_WARNING_DISMISSED="false"'; then
    log_pass "AGENT_MODEL_WARNING_DISMISSED is false when not acknowledged"
else
    log_fail "AGENT_MODEL_WARNING_DISMISSED not set correctly (output: $WARN_OUTPUT)"
fi

# Test that a model without a warning outputs empty AGENT_MODEL_WARNING
# Remove local config created by copy-on-first-access from previous sub-test
rm -f "$WARNING_SANDBOX/.purlin/config.local.json"
cat > "$WARNING_SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}}
    ],
    "agents": {
        "architect": {"model": "claude-opus-4-6", "effort": "high", "bypass_permissions": true}
    }
}
EOF

NOWARN_OUTPUT=$(PURLIN_PROJECT_ROOT="$WARNING_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" architect 2>/dev/null)

if echo "$NOWARN_OUTPUT" | grep -q 'AGENT_MODEL_WARNING=""'; then
    log_pass "resolve_config.py outputs empty AGENT_MODEL_WARNING for model without warning"
else
    log_fail "AGENT_MODEL_WARNING should be empty for model without warning (output: $NOWARN_OUTPUT)"
fi

rm -rf "$WARNING_SANDBOX"

# --- Scenario: Acknowledged Warning is Suppressed on Subsequent Access ---
echo ""
echo "[Scenario] Acknowledged Warning is Suppressed on Subsequent Access"

ACK_SANDBOX="$(mktemp -d)"
mkdir -p "$ACK_SANDBOX/.purlin"
cat > "$ACK_SANDBOX/.purlin/config.local.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]", "capabilities": {"effort": true, "permissions": true}, "warning": "Extended context costs extra.", "warning_dismissible": true}
    ],
    "agents": {
        "architect": {"model": "claude-opus-4-6[1m]", "effort": "high", "bypass_permissions": true}
    },
    "acknowledged_warnings": ["claude-opus-4-6[1m]"]
}
EOF

ACK_OUTPUT=$(PURLIN_PROJECT_ROOT="$ACK_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" architect 2>/dev/null)

if echo "$ACK_OUTPUT" | grep -q 'AGENT_MODEL_WARNING_DISMISSED="true"'; then
    log_pass "AGENT_MODEL_WARNING_DISMISSED is true when model ID is in acknowledged_warnings"
else
    log_fail "AGENT_MODEL_WARNING_DISMISSED should be true (output: $ACK_OUTPUT)"
fi

# Verify the warning text is still populated (dismissed just suppresses display)
if echo "$ACK_OUTPUT" | grep -q 'AGENT_MODEL_WARNING="Extended context costs extra."'; then
    log_pass "AGENT_MODEL_WARNING still contains the warning text even when dismissed"
else
    log_fail "AGENT_MODEL_WARNING should still be set (output: $ACK_OUTPUT)"
fi

rm -rf "$ACK_SANDBOX"

# --- Scenario: Non-Dismissible Warning Always Displays ---
echo ""
echo "[Scenario] Non-Dismissible Warning Always Displays"

ND_SANDBOX="$(mktemp -d)"
mkdir -p "$ND_SANDBOX/.purlin"
cat > "$ND_SANDBOX/.purlin/config.local.json" << 'EOF'
{
    "models": [
        {"id": "claude-special", "label": "Special", "capabilities": {"effort": true, "permissions": true}, "warning": "This model is experimental.", "warning_dismissible": false}
    ],
    "agents": {
        "builder": {"model": "claude-special", "effort": "high", "bypass_permissions": true}
    },
    "acknowledged_warnings": ["claude-special"]
}
EOF

ND_OUTPUT=$(PURLIN_PROJECT_ROOT="$ND_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" builder 2>/dev/null)

if echo "$ND_OUTPUT" | grep -q 'AGENT_MODEL_WARNING="This model is experimental."'; then
    log_pass "Non-dismissible warning text is output"
else
    log_fail "Non-dismissible warning text not found (output: $ND_OUTPUT)"
fi

if echo "$ND_OUTPUT" | grep -q 'AGENT_MODEL_WARNING_DISMISSED="false"'; then
    log_pass "AGENT_MODEL_WARNING_DISMISSED remains false for non-dismissible warning"
else
    log_fail "Non-dismissible warning should not be marked dismissed (output: $ND_OUTPUT)"
fi

rm -rf "$ND_SANDBOX"

# --- Scenario: Launcher Prints Warning and Auto-Acknowledges on First Run ---
echo ""
echo "[Scenario] Launcher Prints Warning and Auto-Acknowledges on First Run"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]", "capabilities": {"effort": true, "permissions": true}, "warning": "Extended context costs extra.", "warning_dismissible": true}
    ],
    "agents": {
        "architect": {"model": "claude-opus-4-6[1m]", "effort": "high", "bypass_permissions": true}
    }
}
EOF

STDERR_FILE="$MOCK_DIR/stderr_capture"
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>"$STDERR_FILE"
STDERR_CAPTURED=$(cat "$STDERR_FILE" 2>/dev/null || echo "")

if echo "$STDERR_CAPTURED" | grep -q "WARNING: Extended context costs extra."; then
    log_pass "Launcher prints warning to stderr on first run"
else
    log_fail "Launcher did not print warning to stderr (stderr: $STDERR_CAPTURED)"
fi

if echo "$STDERR_CAPTURED" | grep -q "By continuing, you are acknowledging this warning."; then
    log_pass "Launcher prints acknowledgment message"
else
    log_fail "Launcher did not print acknowledgment message (stderr: $STDERR_CAPTURED)"
fi

# Verify auto-acknowledge wrote to config.local.json
if [ -f "$SANDBOX/.purlin/config.local.json" ]; then
    if python3 -c "
import json
c = json.load(open('$SANDBOX/.purlin/config.local.json'))
assert 'claude-opus-4-6[1m]' in c.get('acknowledged_warnings', [])
" 2>/dev/null; then
        log_pass "Auto-acknowledge added model ID to acknowledged_warnings in config.local.json"
    else
        log_fail "acknowledged_warnings not updated in config.local.json"
    fi
else
    log_fail "config.local.json was not created by auto-acknowledge"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Suppresses Warning on Subsequent Runs ---
echo ""
echo "[Scenario] Launcher Suppresses Warning on Subsequent Runs"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.local.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]", "capabilities": {"effort": true, "permissions": true}, "warning": "Extended context costs extra.", "warning_dismissible": true}
    ],
    "agents": {
        "architect": {"model": "claude-opus-4-6[1m]", "effort": "high", "bypass_permissions": true}
    },
    "acknowledged_warnings": ["claude-opus-4-6[1m]"]
}
EOF

STDERR_FILE="$MOCK_DIR/stderr_capture"
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>"$STDERR_FILE"
STDERR_CAPTURED=$(cat "$STDERR_FILE" 2>/dev/null || echo "")

if echo "$STDERR_CAPTURED" | grep -qv "WARNING:"; then
    log_pass "Launcher does not print warning when already acknowledged"
else
    log_fail "Launcher should not print warning on subsequent run (stderr: $STDERR_CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: acknowledge_warning CLI subcommand ---
echo ""
echo "[Scenario] acknowledge_warning CLI subcommand"

ACK_CLI_SANDBOX="$(mktemp -d)"
mkdir -p "$ACK_CLI_SANDBOX/.purlin"
cat > "$ACK_CLI_SANDBOX/.purlin/config.local.json" << 'EOF'
{
    "models": [
        {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]", "capabilities": {"effort": true, "permissions": true}, "warning": "Test warning", "warning_dismissible": true}
    ],
    "agents": {}
}
EOF

PURLIN_PROJECT_ROOT="$ACK_CLI_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" acknowledge_warning "claude-opus-4-6[1m]" 2>/dev/null

if python3 -c "
import json
c = json.load(open('$ACK_CLI_SANDBOX/.purlin/config.local.json'))
assert 'claude-opus-4-6[1m]' in c.get('acknowledged_warnings', [])
" 2>/dev/null; then
    log_pass "acknowledge_warning adds model ID to acknowledged_warnings"
else
    log_fail "acknowledge_warning did not update config.local.json"
fi

# Test idempotency (duplicate calls don't create duplicates)
PURLIN_PROJECT_ROOT="$ACK_CLI_SANDBOX" python3 "$SCRIPT_DIR/config/resolve_config.py" acknowledge_warning "claude-opus-4-6[1m]" 2>/dev/null

ACK_COUNT=$(python3 -c "
import json
c = json.load(open('$ACK_CLI_SANDBOX/.purlin/config.local.json'))
print(c.get('acknowledged_warnings', []).count('claude-opus-4-6[1m]'))
" 2>/dev/null)

if [ "$ACK_COUNT" = "1" ]; then
    log_pass "acknowledge_warning is idempotent (no duplicates)"
else
    log_fail "acknowledge_warning created duplicate entries (count: $ACK_COUNT)"
fi

rm -rf "$ACK_CLI_SANDBOX"

# --- Scenario: Launcher Updates Claude CLI When Out of Date ---
echo ""
echo "[Scenario] Launcher Updates Claude CLI When Out of Date"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": {"model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true}
    }
}
EOF

# Mock claude: update --check returns 1 (update available), update returns 0, session captures args
cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
if [ "\$1" = "update" ]; then
    if [ "\${2:-}" = "--check" ]; then
        exit 1
    fi
    exit 0
fi
echo "\$@" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

STDERR_FILE="$MOCK_DIR/stderr_capture"
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>"$STDERR_FILE"
STDERR_CAPTURED=$(cat "$STDERR_FILE" 2>/dev/null || echo "")

if echo "$STDERR_CAPTURED" | grep -q "Checking for Claude Code updates..."; then
    log_pass "Launcher prints update check message to stderr"
else
    log_fail "Launcher did not print update check message (stderr: $STDERR_CAPTURED)"
fi

if echo "$STDERR_CAPTURED" | grep -q "Claude Code updated successfully."; then
    log_pass "Launcher prints update success message after update"
else
    log_fail "Launcher did not print update success message (stderr: $STDERR_CAPTURED)"
fi

# Verify session claude was still invoked after the update
if [ -f "$CAPTURE_FILE" ]; then
    log_pass "Launcher still invoked claude session command after update"
else
    log_fail "Launcher did not invoke claude session command after update"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Skips Update When Already Current ---
echo ""
echo "[Scenario] Launcher Skips Update When Already Current"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": {"model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true}
    }
}
EOF

# Mock claude: update --check returns 0 (up to date), track if update was called
UPDATE_CALLED_FILE="$MOCK_DIR/update_called"
cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
if [ "\$1" = "update" ]; then
    if [ "\${2:-}" = "--check" ]; then
        exit 0
    fi
    echo "called" > "$UPDATE_CALLED_FILE"
    exit 0
fi
echo "\$@" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

STDERR_FILE="$MOCK_DIR/stderr_capture"
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>"$STDERR_FILE"
STDERR_CAPTURED=$(cat "$STDERR_FILE" 2>/dev/null || echo "")

if echo "$STDERR_CAPTURED" | grep -q "Checking for Claude Code updates..."; then
    log_pass "Launcher prints check message even when up to date"
else
    log_fail "Launcher did not print check message (stderr: $STDERR_CAPTURED)"
fi

if [ ! -f "$UPDATE_CALLED_FILE" ]; then
    log_pass "Launcher did not run claude update when already current"
else
    log_fail "Launcher ran claude update unnecessarily"
fi

if echo "$STDERR_CAPTURED" | grep -qv "Claude Code updated successfully."; then
    log_pass "Launcher does not print update success message when already current"
else
    log_fail "Launcher printed update success message unexpectedly (stderr: $STDERR_CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Continues When Update Fails ---
echo ""
echo "[Scenario] Launcher Continues When Update Fails"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": {"model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true}
    }
}
EOF

# Mock claude: update --check returns 1 (update available), update returns 1 (failure)
cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
if [ "\$1" = "update" ]; then
    if [ "\${2:-}" = "--check" ]; then
        exit 1
    fi
    exit 1
fi
echo "\$@" > "$CAPTURE_FILE"
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

STDERR_FILE="$MOCK_DIR/stderr_capture"
PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>"$STDERR_FILE"
STDERR_CAPTURED=$(cat "$STDERR_FILE" 2>/dev/null || echo "")

if echo "$STDERR_CAPTURED" | grep -q "WARNING: Claude Code update failed. Continuing with current version."; then
    log_pass "Launcher prints update failure warning"
else
    log_fail "Launcher did not print update failure warning (stderr: $STDERR_CAPTURED)"
fi

# Verify session claude was still invoked despite update failure
if [ -f "$CAPTURE_FILE" ]; then
    log_pass "Launcher still invoked claude session command after update failure"
else
    log_fail "Launcher did not invoke claude session command after update failure"
fi

teardown_launcher_sandbox

# --- Scenario: Launcher Skips Update Check When Claude Not on PATH ---
echo ""
echo "[Scenario] Launcher Skips Update Check When Claude Not on PATH"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": {"model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true}
    }
}
EOF

# Use an empty directory as PATH so claude is not found
EMPTY_PATH_DIR="$(mktemp -d)"
# But we need python3 and basic utils — create a wrapper that fails for claude only
cat > "$EMPTY_PATH_DIR/claude" << 'MOCK_EOF'
#!/bin/bash
exit 127
MOCK_EOF
# Don't make it executable — command -v should not find it
# Instead, remove the mock dir's claude entirely and use a PATH without claude
rm -f "$EMPTY_PATH_DIR/claude"

# We need bash, python3, cat, etc. but NOT claude
# Create symlinks for needed tools
for tool in bash python3 cat printf mktemp rm chmod mkdir grep echo sed; do
    tool_path="$(command -v "$tool" 2>/dev/null)"
    if [ -n "$tool_path" ]; then
        ln -sf "$tool_path" "$EMPTY_PATH_DIR/$tool"
    fi
done

STDERR_FILE="$MOCK_DIR/stderr_capture"
PATH="$EMPTY_PATH_DIR" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>"$STDERR_FILE"
LAUNCHER_EXIT=$?
STDERR_CAPTURED=$(cat "$STDERR_FILE" 2>/dev/null || echo "")

# Update check should be skipped entirely (no "Checking" message)
if echo "$STDERR_CAPTURED" | grep -qv "Checking for Claude Code updates..."; then
    log_pass "Launcher skips update check when claude not on PATH"
else
    log_fail "Launcher attempted update check without claude on PATH (stderr: $STDERR_CAPTURED)"
fi

rm -rf "$EMPTY_PATH_DIR"
teardown_launcher_sandbox

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
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_agent_configuration.sh\"}"
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
