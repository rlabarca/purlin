#!/usr/bin/env bash
# Test: Bash command guard enforcement
# Verifies that bash-guard.sh blocks destructive commands in default mode
# and allows everything when a mode is active.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
BASH_GUARD="$PLUGIN_ROOT/hooks/scripts/bash-guard.sh"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
TEST_SESSION="test-bash-$$"
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export PURLIN_SESSION_ID="$TEST_SESSION"

mkdir -p "$TEST_DIR/.purlin/runtime"

set_mode() {
    echo "$1" > "$TEST_DIR/.purlin/runtime/current_mode_$TEST_SESSION"
}

clear_mode() {
    echo "" > "$TEST_DIR/.purlin/runtime/current_mode_$TEST_SESSION"
}

run_bash_guard() {
    local cmd="$1"
    echo "{\"tool_input\": {\"command\": \"$cmd\"}}" | bash "$BASH_GUARD" >/dev/null 2>&1
    return $?
}

assert_allowed() {
    local desc="$1" cmd="$2"
    ((total++))
    if run_bash_guard "$cmd"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (expected allow, got block)"
        ((failed++))
    fi
}

assert_blocked() {
    local desc="$1" cmd="$2"
    ((total++))
    if run_bash_guard "$cmd"; then
        echo "FAIL: $desc (expected block, got allow)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

# === DEFAULT MODE — blocks destructive patterns ===
clear_mode

assert_blocked "default blocks rm" "rm -rf build/"
assert_blocked "default blocks mv" "mv old.py new.py"
assert_blocked "default blocks cp" "cp src/a.py src/b.py"
assert_blocked "default blocks mkdir" "mkdir -p new_dir"
assert_blocked "default blocks touch" "touch new_file.txt"
assert_blocked "default blocks chmod" "chmod +x script.sh"
assert_blocked "default blocks git add" "git add ."
assert_blocked "default blocks git commit" "git commit -m test"
assert_blocked "default blocks git push" "git push origin main"
assert_blocked "default blocks redirect" "echo hello > output.txt"
assert_blocked "default blocks append redirect" "echo hello >> output.txt"
assert_blocked "default blocks sed -i" "sed -i 's/old/new/' file.py"
assert_blocked "default blocks tee" "tee output.log"

# Read-only commands should be allowed in default mode
assert_allowed "default allows ls" "ls -la"
assert_allowed "default allows cat" "cat README.md"
assert_allowed "default allows grep" "grep -r pattern src/"
assert_allowed "default allows git status" "git status"
assert_allowed "default allows git log" "git log --oneline -5"
assert_allowed "default allows git diff" "git diff HEAD"
assert_allowed "default allows python read" "python3 -c 'print(1+1)'"

# === ENGINEER MODE — allows everything ===
set_mode "engineer"

assert_allowed "engineer allows rm" "rm -rf build/"
assert_allowed "engineer allows git add" "git add ."
assert_allowed "engineer allows git commit" "git commit -m test"
assert_allowed "engineer allows mkdir" "mkdir -p new_dir"
assert_allowed "engineer allows redirect" "echo hello > output.txt"
assert_allowed "engineer allows sed -i" "sed -i 's/old/new/' file.py"

# === PM MODE — allows everything (bash guard defers to file guard) ===
set_mode "pm"

assert_allowed "pm allows git commit" "git commit -m 'spec update'"
assert_allowed "pm allows mkdir" "mkdir -p features/new"

# === QA MODE — allows everything ===
set_mode "qa"

assert_allowed "qa allows git commit" "git commit -m 'qa report'"
assert_allowed "qa allows rm" "rm -rf tests/tmp/"

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
