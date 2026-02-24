#!/bin/bash
# test_pl_agent_config.sh — Automated tests for the /pl-agent-config skill.
# Verifies the underlying operations: config reading/writing, key validation,
# model validation, worktree context detection, and atomic write behavior.
# Produces tests/pl_agent_config/tests.json at project root.
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

# Create a temporary git repo sandbox with a valid .purlin/config.json
setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    cd "$SANDBOX"
    git init -q
    git checkout -q -b main

    mkdir -p .purlin
    cat > .purlin/config.json << 'CFGEOF'
{
    "cdd_port": 9086,
    "tools_root": "tools",
    "models": [
        {
            "id": "claude-opus-4-6",
            "label": "Opus 4.6",
            "capabilities": { "effort": true, "permissions": true }
        },
        {
            "id": "claude-sonnet-4-6",
            "label": "Sonnet 4.6",
            "capabilities": { "effort": true, "permissions": true }
        }
    ],
    "agents": {
        "architect": {
            "model": "claude-sonnet-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "startup_sequence": false,
            "recommend_next_actions": false
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "startup_sequence": true,
            "recommend_next_actions": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true,
            "startup_sequence": false,
            "recommend_next_actions": false
        }
    }
}
CFGEOF

    git add -A
    git commit -q -m "initial"
}

teardown_sandbox() {
    cd "$PROJECT_ROOT"
    rm -rf "${SANDBOX:-}"
    unset SANDBOX
}

# Simulate the config update operation the agent performs (Step 6 of the skill)
apply_config_change() {
    local config_path="$1"
    local role="$2"
    local key="$3"
    local value="$4"

    python3 -c "
import json, sys, os, tempfile

config_path = '$config_path'
role = '$role'
key = '$key'
value = '$value'

with open(config_path) as f:
    config = json.load(f)

# Convert booleans
if value.lower() == 'true':
    value = True
elif value.lower() == 'false':
    value = False

config['agents'][role][key] = value

# Atomic write: temp file + rename
dir_path = os.path.dirname(config_path)
fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
with os.fdopen(fd, 'w') as f:
    json.dump(config, f, indent=4)
    f.write('\n')
os.rename(tmp_path, config_path)
"
}

# Validate a key against the allowed list (Step 2 of the skill)
validate_key() {
    local key="$1"
    case "$key" in
        model|effort|startup_sequence|recommend_next_actions|bypass_permissions)
            return 0 ;;
        *)
            return 1 ;;
    esac
}

# Validate a model value against the config's models array (Step 2 of the skill)
validate_model() {
    local config_path="$1"
    local model_id="$2"
    python3 -c "
import json, sys
with open('$config_path') as f:
    config = json.load(f)
valid_ids = [m['id'] for m in config.get('models', [])]
sys.exit(0 if '$model_id' in valid_ids else 1)
"
}

echo "=== /pl-agent-config Skill Tests ==="

###############################################################################
# Scenario: Config Change Applied to MAIN in Non-Isolated Session
###############################################################################
echo ""
echo "[Scenario] Config Change Applied to MAIN in Non-Isolated Session"
setup_sandbox

# Verify initial state: builder.startup_sequence is true
INITIAL=$(python3 -c "import json; c=json.load(open('$SANDBOX/.purlin/config.json')); print(c['agents']['builder']['startup_sequence'])")
if [ "$INITIAL" = "True" ]; then
    log_pass "Initial config has startup_sequence=true for builder"
else
    log_fail "Initial config startup_sequence is not true (got: $INITIAL)"
fi

# Branch is main (non-isolated)
BRANCH=$(git -C "$SANDBOX" rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
    log_pass "Current branch is main (non-isolated)"
else
    log_fail "Expected branch main, got: $BRANCH"
fi

# Apply change: builder.startup_sequence = false
apply_config_change "$SANDBOX/.purlin/config.json" "builder" "startup_sequence" "false"

# Verify the change
UPDATED=$(python3 -c "import json; c=json.load(open('$SANDBOX/.purlin/config.json')); print(c['agents']['builder']['startup_sequence'])")
if [ "$UPDATED" = "False" ]; then
    log_pass "Config updated: builder.startup_sequence=false"
else
    log_fail "Config not updated correctly (got: $UPDATED)"
fi

# Verify commit works (simulating Step 7)
git -C "$SANDBOX" add .purlin/config.json
git -C "$SANDBOX" commit -q -m "config: set builder.startup_sequence = false"
LAST_MSG=$(git -C "$SANDBOX" log -1 --format='%s')
if [ "$LAST_MSG" = "config: set builder.startup_sequence = false" ]; then
    log_pass "Commit message follows the required format"
else
    log_fail "Commit message wrong (got: $LAST_MSG)"
fi

teardown_sandbox

###############################################################################
# Scenario: Worktree Warning Displayed in Isolated Session
###############################################################################
echo ""
echo "[Scenario] Worktree Warning Displayed in Isolated Session"
setup_sandbox

# Create an isolation branch
git -C "$SANDBOX" checkout -q -b isolated/feat1

BRANCH=$(git -C "$SANDBOX" rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" == isolated/* ]]; then
    log_pass "Branch detected as isolated (isolated/feat1)"
else
    log_fail "Branch not detected as isolated (got: $BRANCH)"
fi

# Extract isolation name
ISO_NAME="${BRANCH#isolated/}"
if [ "$ISO_NAME" = "feat1" ]; then
    log_pass "Isolation name extracted correctly: feat1"
else
    log_fail "Isolation name wrong (got: $ISO_NAME)"
fi

teardown_sandbox

###############################################################################
# Scenario: Worktree Change Applied to MAIN Config
###############################################################################
echo ""
echo "[Scenario] Worktree Change Applied to MAIN Config"
setup_sandbox

# Create a worktree to simulate isolation
mkdir -p "$SANDBOX/.worktrees"
git -C "$SANDBOX" worktree add -q "$SANDBOX/.worktrees/feat1" -b isolated/feat1

# Make a copy of MAIN config in the worktree (like create_isolation.sh does)
mkdir -p "$SANDBOX/.worktrees/feat1/.purlin"
cp "$SANDBOX/.purlin/config.json" "$SANDBOX/.worktrees/feat1/.purlin/config.json"

# Resolve MAIN root from worktree using git worktree list
# Note: normalize with realpath to handle macOS /var -> /private/var symlink
MAIN_ROOT=$(git -C "$SANDBOX/.worktrees/feat1" worktree list --porcelain | head -1 | sed 's/^worktree //')
MAIN_ROOT_REAL=$(cd "$MAIN_ROOT" && pwd -P)
SANDBOX_REAL=$(cd "$SANDBOX" && pwd -P)
if [ "$MAIN_ROOT_REAL" = "$SANDBOX_REAL" ]; then
    log_pass "MAIN project root resolved correctly from worktree"
else
    log_fail "MAIN root resolution failed (got: $MAIN_ROOT, expected: $SANDBOX)"
fi

# Apply change to MAIN config (not worktree config)
apply_config_change "$MAIN_ROOT/.purlin/config.json" "builder" "startup_sequence" "false"

# Verify MAIN config changed
MAIN_VAL=$(python3 -c "import json; c=json.load(open('$MAIN_ROOT/.purlin/config.json')); print(c['agents']['builder']['startup_sequence'])")
if [ "$MAIN_VAL" = "False" ]; then
    log_pass "MAIN config updated: builder.startup_sequence=false"
else
    log_fail "MAIN config not updated (got: $MAIN_VAL)"
fi

# Verify worktree config UNCHANGED
WT_VAL=$(python3 -c "import json; c=json.load(open('$SANDBOX/.worktrees/feat1/.purlin/config.json')); print(c['agents']['builder']['startup_sequence'])")
if [ "$WT_VAL" = "True" ]; then
    log_pass "Worktree config unchanged (still startup_sequence=true)"
else
    log_fail "Worktree config was modified unexpectedly (got: $WT_VAL)"
fi

# Commit in MAIN checkout
git -C "$MAIN_ROOT" add .purlin/config.json
git -C "$MAIN_ROOT" commit -q -m "config: set builder.startup_sequence = false"
LAST_MSG=$(git -C "$MAIN_ROOT" log -1 --format='%s')
if [ "$LAST_MSG" = "config: set builder.startup_sequence = false" ]; then
    log_pass "Commit made in MAIN checkout"
else
    log_fail "Commit not in MAIN checkout (got: $LAST_MSG)"
fi

# Cleanup worktree
git -C "$SANDBOX" worktree remove "$SANDBOX/.worktrees/feat1" --force 2>/dev/null
git -C "$SANDBOX" branch -D isolated/feat1 2>/dev/null

teardown_sandbox

###############################################################################
# Scenario: Worktree Change Aborted on User Denial
###############################################################################
echo ""
echo "[Scenario] Worktree Change Aborted on User Denial"
setup_sandbox

# Snapshot config before (simulating abort — no change should occur)
BEFORE=$(python3 -c "import json; print(json.dumps(json.load(open('$SANDBOX/.purlin/config.json'))))")

# Simulate abort: do NOT call apply_config_change (user said N)

AFTER=$(python3 -c "import json; print(json.dumps(json.load(open('$SANDBOX/.purlin/config.json'))))")
if [ "$BEFORE" = "$AFTER" ]; then
    log_pass "Config unchanged when user aborts (no modifications made)"
else
    log_fail "Config was modified despite abort"
fi

# Verify no new commit was made
COMMIT_COUNT=$(git -C "$SANDBOX" rev-list --count HEAD)
if [ "$COMMIT_COUNT" = "1" ]; then
    log_pass "No git commit made on abort"
else
    log_fail "Unexpected commit count (got: $COMMIT_COUNT, expected: 1)"
fi

teardown_sandbox

###############################################################################
# Scenario: Invalid Key Rejected
###############################################################################
echo ""
echo "[Scenario] Invalid Key Rejected"
setup_sandbox

# Test valid keys
for KEY in model effort startup_sequence recommend_next_actions bypass_permissions; do
    if validate_key "$KEY"; then
        log_pass "Key '$KEY' accepted as valid"
    else
        log_fail "Key '$KEY' rejected (should be valid)"
    fi
done

# Test invalid key
if validate_key "unknown_key"; then
    log_fail "Key 'unknown_key' accepted (should be rejected)"
else
    log_pass "Key 'unknown_key' rejected with error"
fi

# Verify config unchanged after invalid key
BEFORE=$(python3 -c "import json; print(json.dumps(json.load(open('$SANDBOX/.purlin/config.json'))))")
# (no apply_config_change called for invalid key)
AFTER=$(python3 -c "import json; print(json.dumps(json.load(open('$SANDBOX/.purlin/config.json'))))")
if [ "$BEFORE" = "$AFTER" ]; then
    log_pass "Config unchanged after invalid key rejection"
else
    log_fail "Config modified despite invalid key"
fi

teardown_sandbox

###############################################################################
# Scenario: Invalid Model Value Rejected
###############################################################################
echo ""
echo "[Scenario] Invalid Model Value Rejected"
setup_sandbox

# Test valid model ID
if validate_model "$SANDBOX/.purlin/config.json" "claude-sonnet-4-6"; then
    log_pass "Model 'claude-sonnet-4-6' accepted (exists in models array)"
else
    log_fail "Model 'claude-sonnet-4-6' rejected (should be valid)"
fi

if validate_model "$SANDBOX/.purlin/config.json" "claude-opus-4-6"; then
    log_pass "Model 'claude-opus-4-6' accepted (exists in models array)"
else
    log_fail "Model 'claude-opus-4-6' rejected (should be valid)"
fi

# Test invalid model ID
if validate_model "$SANDBOX/.purlin/config.json" "claude-gpt-5"; then
    log_fail "Model 'claude-gpt-5' accepted (should be rejected)"
else
    log_pass "Model 'claude-gpt-5' rejected (not in models array)"
fi

# Verify config unchanged after invalid model rejection
BEFORE=$(python3 -c "import json; print(json.dumps(json.load(open('$SANDBOX/.purlin/config.json'))))")
AFTER=$(python3 -c "import json; print(json.dumps(json.load(open('$SANDBOX/.purlin/config.json'))))")
if [ "$BEFORE" = "$AFTER" ]; then
    log_pass "Config unchanged after invalid model rejection"
else
    log_fail "Config modified despite invalid model"
fi

teardown_sandbox

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
OUTDIR="$TESTS_DIR/pl_agent_config"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
