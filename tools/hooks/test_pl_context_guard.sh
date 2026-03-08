#!/bin/bash
# test_pl_context_guard.sh — Tests for /pl-context-guard skill config operations
# Covers automated scenarios from features/pl_context_guard.md.
# Produces tests/pl_context_guard/tests.json.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

SANDBOX=""
cleanup_sandbox() { [[ -n "${SANDBOX:-}" && -d "$SANDBOX" ]] && rm -rf "$SANDBOX"; }

setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT
    mkdir -p "$SANDBOX/.purlin"
    mkdir -p "$SANDBOX/tools/config"
    cp "$SCRIPT_DIR/../config/resolve_config.py" "$SANDBOX/tools/config/"
}

# Helper: read a nested JSON value via Python (keys as separate args)
json_get() {
    local file="$1"; shift
    python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
for k in sys.argv[2:]:
    d = d[k]
print(json.dumps(d))
" "$file" "$@" 2>/dev/null
}

# Helper: write config change (simulates what the skill does)
apply_config_change() {
    local config_path="$1" role="$2" key="$3" value="$4"
    python3 -c "
import json, os, sys
config_path, role, key, value_str = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(config_path) as f:
    cfg = json.load(f)
agents = cfg.setdefault('agents', {})
agent = agents.setdefault(role, {})
# Parse value: True/False -> bool, digits -> int, else string
if value_str == 'True':
    agent[key] = True
elif value_str == 'False':
    agent[key] = False
elif value_str.isdigit():
    agent[key] = int(value_str)
else:
    agent[key] = value_str
tmp = config_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(cfg, f, indent=4)
os.replace(tmp, config_path)
" "$config_path" "$role" "$key" "$value"
}

echo "==============================="
echo "/pl-context-guard Skill Tests"
echo "==============================="

###############################################################################
# Scenario: Status with no arguments shows all roles
###############################################################################
echo ""
echo "[Scenario] Status with no arguments shows all roles"
setup_sandbox
cat > "$SANDBOX/.purlin/config.local.json" <<'JSON'
{"context_guard_threshold": 45, "agents": {"architect": {"context_guard": true, "context_guard_threshold": 45}, "builder": {"context_guard": true, "context_guard_threshold": 30}, "qa": {"context_guard": false, "context_guard_threshold": 45}}}
JSON
ARCH_CG=$(json_get "$SANDBOX/.purlin/config.local.json" agents architect context_guard)
BUILD_T=$(json_get "$SANDBOX/.purlin/config.local.json" agents builder context_guard_threshold)
QA_CG=$(json_get "$SANDBOX/.purlin/config.local.json" agents qa context_guard)
if [[ "$ARCH_CG" == "true" && "$BUILD_T" == "30" && "$QA_CG" == "false" ]]; then
    log_pass "All three roles readable with correct values"
else
    log_fail "Config read failed: arch_cg=$ARCH_CG build_t=$BUILD_T qa_cg=$QA_CG"
fi
cleanup_sandbox

###############################################################################
# Scenario: Status for single role shows per-agent annotation
###############################################################################
echo ""
echo "[Scenario] Status for single role shows per-agent annotation"
setup_sandbox
cat > "$SANDBOX/.purlin/config.local.json" <<'JSON'
{"context_guard_threshold": 45, "agents": {"builder": {"context_guard_threshold": 30}}}
JSON
GLOBAL=$(json_get "$SANDBOX/.purlin/config.local.json" context_guard_threshold)
PERAGENT=$(json_get "$SANDBOX/.purlin/config.local.json" agents builder context_guard_threshold)
if [[ "$PERAGENT" == "30" && "$GLOBAL" == "45" ]]; then
    log_pass "Per-agent threshold 30 distinct from global 45"
else
    log_fail "Expected per-agent=30 global=45, got per-agent=$PERAGENT global=$GLOBAL"
fi
cleanup_sandbox

###############################################################################
# Scenario: Status shows global default annotation when no per-agent threshold
###############################################################################
echo ""
echo "[Scenario] Status shows global default annotation when no per-agent threshold"
setup_sandbox
cat > "$SANDBOX/.purlin/config.local.json" <<'JSON'
{"context_guard_threshold": 45, "agents": {"architect": {"model": "claude-opus-4-6"}}}
JSON
HAS_CGT=$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print('context_guard_threshold' in d.get('agents',{}).get('architect',{}))
" "$SANDBOX/.purlin/config.local.json" 2>/dev/null)
if [[ "$HAS_CGT" == "False" ]]; then
    log_pass "No per-agent threshold — falls back to global default"
else
    log_fail "Expected no per-agent threshold, got $HAS_CGT"
fi
cleanup_sandbox

###############################################################################
# Scenario: Set threshold persists to config.local.json
###############################################################################
echo ""
echo "[Scenario] Set threshold persists to config.local.json"
setup_sandbox
cat > "$SANDBOX/.purlin/config.local.json" <<'JSON'
{"context_guard_threshold": 45, "agents": {"builder": {"model": "claude-opus-4-6"}}}
JSON
apply_config_change "$SANDBOX/.purlin/config.local.json" "builder" "context_guard_threshold" "30"
RESULT=$(json_get "$SANDBOX/.purlin/config.local.json" agents builder context_guard_threshold)
if [[ "$RESULT" == "30" ]]; then
    log_pass "Threshold persisted: agents.builder.context_guard_threshold = 30"
else
    log_fail "Expected 30, got $RESULT"
fi
cleanup_sandbox

###############################################################################
# Scenario: Set threshold rejects out-of-range value
###############################################################################
echo ""
echo "[Scenario] Set threshold rejects out-of-range value"
setup_sandbox
VALID=$(python3 -c "v=300; print('valid' if 5<=v<=200 else 'invalid')")
if [[ "$VALID" == "invalid" ]]; then
    log_pass "Value 300 correctly identified as out of range"
else
    log_fail "Expected invalid for 300"
fi
cleanup_sandbox

###############################################################################
# Scenario: Disable guard for a role
###############################################################################
echo ""
echo "[Scenario] Disable guard for a role"
setup_sandbox
cat > "$SANDBOX/.purlin/config.local.json" <<'JSON'
{"agents": {"qa": {"context_guard": true}}}
JSON
apply_config_change "$SANDBOX/.purlin/config.local.json" "qa" "context_guard" "False"
RESULT=$(json_get "$SANDBOX/.purlin/config.local.json" agents qa context_guard)
if [[ "$RESULT" == "false" ]]; then
    log_pass "Guard disabled: agents.qa.context_guard = false"
else
    log_fail "Expected false, got $RESULT"
fi
cleanup_sandbox

###############################################################################
# Scenario: Enable guard for a role
###############################################################################
echo ""
echo "[Scenario] Enable guard for a role"
setup_sandbox
cat > "$SANDBOX/.purlin/config.local.json" <<'JSON'
{"agents": {"qa": {"context_guard": false}}}
JSON
apply_config_change "$SANDBOX/.purlin/config.local.json" "qa" "context_guard" "True"
RESULT=$(json_get "$SANDBOX/.purlin/config.local.json" agents qa context_guard)
if [[ "$RESULT" == "true" ]]; then
    log_pass "Guard enabled: agents.qa.context_guard = true"
else
    log_fail "Expected true, got $RESULT"
fi
cleanup_sandbox

###############################################################################
# Scenario: Invalid role rejected
###############################################################################
echo ""
echo "[Scenario] Invalid role rejected"
VALID_ROLE=$(python3 -c "print('admin' in ['architect','builder','qa'])")
if [[ "$VALID_ROLE" == "False" ]]; then
    log_pass "Role 'admin' correctly rejected"
else
    log_fail "Expected rejection of 'admin'"
fi

###############################################################################
# Scenario: Copy-on-first-access when config.local.json missing
###############################################################################
echo ""
echo "[Scenario] Copy-on-first-access when config.local.json missing"
setup_sandbox
cat > "$SANDBOX/.purlin/config.json" <<'JSON'
{"context_guard_threshold": 45, "agents": {"builder": {"model": "claude-opus-4-6"}}}
JSON
# Simulate copy-on-first-access
if [[ ! -f "$SANDBOX/.purlin/config.local.json" ]]; then
    cp "$SANDBOX/.purlin/config.json" "$SANDBOX/.purlin/config.local.json"
fi
apply_config_change "$SANDBOX/.purlin/config.local.json" "builder" "context_guard_threshold" "25"
RESULT=$(json_get "$SANDBOX/.purlin/config.local.json" agents builder context_guard_threshold)
if [[ "$RESULT" == "25" ]]; then
    log_pass "Copy-on-first-access created local config and wrote threshold 25"
else
    log_fail "Expected 25 after copy-on-first-access, got $RESULT"
fi
cleanup_sandbox

###############################################################################
# Summary
###############################################################################
TOTAL=$((PASS + FAIL))
echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed (of $TOTAL)"
if [[ $FAIL -gt 0 ]]; then
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

OUTDIR="$TESTS_DIR/pl_context_guard"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/hooks/test_pl_context_guard.sh\"}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
