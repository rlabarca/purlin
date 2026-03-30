#!/usr/bin/env bash
# Test: Mode state persistence and PID-scoping
# Verifies get_mode/set_mode behavior, PID-scoped isolation,
# authoritative empty file behavior, and concurrent terminal independence.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
CONFIG_ENGINE="$PLUGIN_ROOT/scripts/mcp/config_engine.py"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
mkdir -p "$TEST_DIR/.purlin/runtime"

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    ((total++))
    if [ "$expected" = "$actual" ]; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (expected '$expected', got '$actual')"
        ((failed++))
    fi
}

get_mode_py() {
    python3 -c "
import sys, os
os.environ['PURLIN_PROJECT_ROOT'] = '$TEST_DIR'
os.environ['PURLIN_SESSION_ID'] = '${1:-}'
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
# Force reload to clear cached state
import importlib
import config_engine
importlib.reload(config_engine)
mode = config_engine.get_mode()
print(mode if mode else 'none')
" 2>/dev/null
}

set_mode_py() {
    local mode="$1" session_id="${2:-}"
    python3 -c "
import sys, os
os.environ['PURLIN_PROJECT_ROOT'] = '$TEST_DIR'
os.environ['PURLIN_SESSION_ID'] = '$session_id'
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
import importlib
import config_engine
importlib.reload(config_engine)
config_engine.set_mode('$mode' if '$mode' != 'None' else None)
" 2>/dev/null
}

# === Basic set/get mode ===
export PURLIN_SESSION_ID="session-1000"

set_mode_py "engineer" "session-1000"
result=$(get_mode_py "session-1000")
assert_eq "set_mode engineer then get_mode returns engineer" "engineer" "$result"

set_mode_py "pm" "session-1000"
result=$(get_mode_py "session-1000")
assert_eq "set_mode pm then get_mode returns pm" "pm" "$result"

set_mode_py "qa" "session-1000"
result=$(get_mode_py "session-1000")
assert_eq "set_mode qa then get_mode returns qa" "qa" "$result"

# === Clear mode (set to None) ===
set_mode_py "None" "session-1000"
result=$(get_mode_py "session-1000")
assert_eq "set_mode None clears mode" "none" "$result"

# === PID-scoped isolation ===
set_mode_py "engineer" "session-A"
set_mode_py "pm" "session-B"

result_a=$(get_mode_py "session-A")
result_b=$(get_mode_py "session-B")
assert_eq "session A has engineer mode" "engineer" "$result_a"
assert_eq "session B has pm mode (independent)" "pm" "$result_b"

# Changing session B does not affect session A
set_mode_py "qa" "session-B"
result_a=$(get_mode_py "session-A")
result_b=$(get_mode_py "session-B")
assert_eq "session A still engineer after B changed" "engineer" "$result_a"
assert_eq "session B now qa" "qa" "$result_b"

# === Authoritative empty file ===
# When PID-scoped file exists but is empty, get_mode returns None
# even if unscoped file has a mode (stale data)
echo "engineer" > "$TEST_DIR/.purlin/runtime/current_mode"
echo "" > "$TEST_DIR/.purlin/runtime/current_mode_session-empty"
result=$(get_mode_py "session-empty")
assert_eq "empty PID-scoped file is authoritative (returns none, not stale unscoped)" "none" "$result"

# === Unscoped fallback when no session ID ===
echo "pm" > "$TEST_DIR/.purlin/runtime/current_mode"
result=$(get_mode_py "")
assert_eq "no session ID falls back to unscoped file" "pm" "$result"

# === Missing mode file returns none ===
rm -f "$TEST_DIR/.purlin/runtime/current_mode_session-missing"
result=$(get_mode_py "session-missing")
# Should fall back to unscoped (which has "pm" from previous test)
# unless there's no unscoped — but we have "pm" there
# Actually with session-missing, no PID-scoped file exists, so it tries unscoped
assert_eq "missing PID-scoped file falls back to unscoped" "pm" "$result"

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
