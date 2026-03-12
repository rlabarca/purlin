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
    echo "# stub" > "$SANDBOX/instructions/HOW_WE_WORK_BASE.md"
    echo "# stub" > "$SANDBOX/instructions/BUILDER_BASE.md"
    echo "# stub" > "$SANDBOX/instructions/ARCHITECT_BASE.md"
    echo "# stub" > "$SANDBOX/instructions/QA_BASE.md"

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
    log_pass "Architect role restrictions applied when falling back to defaults"
else
    log_fail "Architect role restrictions not applied on fallback (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Builder Launcher Has No AllowedTools ---
echo ""
echo "[Scenario] Builder Launcher Has No AllowedTools"
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
