#!/usr/bin/env bash
# dev/test_plugin_hooks.sh
#
# Integration tests for all Purlin plugin hook scripts.
# Tests mode-guard enforcement, session lifecycle hooks,
# pre-compact checkpoint creation, and permission management.
#
# Usage:
#   ./dev/test_plugin_hooks.sh [--help]
#
# Requires:
#   - The plugin fixture at /tmp/purlin-plugin-fixture
#     (run dev/setup_plugin_test_fixture.sh to create it)
#   - python3 on PATH
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'HELP'
Usage: test_plugin_hooks.sh [--help]

Integration tests for all Purlin plugin hook scripts.

Tests:
  - mode-guard.sh: 16+ mode/file-class combinations (allow/block)
  - session-start.sh: context reminder output
  - pre-compact-checkpoint.sh: checkpoint file creation
  - session-end-merge.sh: exits 0 (no-op)
  - permission-manager.sh: bypass_permissions auto-approve
  - companion-debt-tracker.sh: exits 0 for non-feature files

Requires the fixture at /tmp/purlin-plugin-fixture.
Run dev/setup_plugin_test_fixture.sh first.
HELP
    exit 0
fi

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve PLUGIN_ROOT: support both main repo and worktree layouts.
# Walk up from SCRIPT_DIR looking for hooks/scripts/mode-guard.sh.
_resolve_plugin_root() {
    local candidate="$SCRIPT_DIR/.."
    candidate="$(cd "$candidate" && pwd)"
    for _ in $(seq 1 10); do
        if [[ -f "$candidate/hooks/scripts/mode-guard.sh" ]]; then
            echo "$candidate"
            return
        fi
        candidate="$(cd "$candidate/.." && pwd)"
    done
    # Worktree fallback: read .git file to find main repo
    local git_file="$SCRIPT_DIR/../.git"
    if [[ -f "$git_file" ]]; then
        local gitdir
        gitdir="$(sed 's/^gitdir: //' "$git_file")"
        gitdir="$(cd "$(dirname "$git_file")" && cd "$(dirname "$gitdir")" && pwd)/$(basename "$gitdir")"
        # /main-repo/.git/worktrees/<name> -> up 3 -> /main-repo
        local main_repo
        main_repo="$(cd "$gitdir/../../.." && pwd)"
        if [[ -f "$main_repo/hooks/scripts/mode-guard.sh" ]]; then
            echo "$main_repo"
            return
        fi
    fi
    echo "$(cd "$SCRIPT_DIR/.." && pwd)"
}

PLUGIN_ROOT="$(_resolve_plugin_root)"
FIXTURE_DIR="/tmp/purlin-plugin-fixture"

if [[ ! -d "$FIXTURE_DIR/.purlin" ]]; then
    echo "ERROR: Fixture not found at $FIXTURE_DIR"
    echo "Run: dev/setup_plugin_test_fixture.sh"
    exit 1
fi

if [[ ! -f "$PLUGIN_ROOT/hooks/scripts/mode-guard.sh" ]]; then
    echo "ERROR: Hook scripts not found at $PLUGIN_ROOT/hooks/scripts/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
PASS=0
FAIL=0
TOTAL=0

pass() {
    ((PASS++))
    ((TOTAL++))
    echo "  PASS: $1"
}

fail() {
    ((FAIL++))
    ((TOTAL++))
    echo "  FAIL: $1"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
run_hook() {
    local script="$1"
    local input="$2"
    echo "$input" | PURLIN_PROJECT_ROOT="$FIXTURE_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" bash "$PLUGIN_ROOT/hooks/scripts/$script" 2>/dev/null
}

run_hook_exit_code() {
    local script="$1"
    local input="$2"
    local ec=0
    echo "$input" | PURLIN_PROJECT_ROOT="$FIXTURE_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" bash "$PLUGIN_ROOT/hooks/scripts/$script" >/dev/null 2>/dev/null || ec=$?
    echo "$ec"
}

set_mode() {
    local mode="$1"
    mkdir -p "$FIXTURE_DIR/.purlin/runtime"
    echo "$mode" > "$FIXTURE_DIR/.purlin/runtime/current_mode"
}

clear_mode() {
    mkdir -p "$FIXTURE_DIR/.purlin/runtime"
    echo "" > "$FIXTURE_DIR/.purlin/runtime/current_mode"
}

make_input() {
    local filepath="$1"
    echo '{"tool_name":"Write","tool_input":{"file_path":"'"$filepath"'"}}'
}

# ---------------------------------------------------------------------------
# Test: mode-guard.sh
# ---------------------------------------------------------------------------
echo ""
echo "=== Mode Guard Tests ==="

# --- Engineer mode ---
echo ""
echo "-- Engineer mode --"

set_mode "engineer"

# 1. engineer + CODE -> allow (exit 0)
INPUT="$(make_input "$FIXTURE_DIR/src/app.py")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "engineer + CODE (src/app.py) -> exit 0"
else
    fail "engineer + CODE (src/app.py) -> expected exit 0, got $EC"
fi

# 2. engineer + SPEC -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/core/user_auth.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "engineer + SPEC (features/user_auth.md) -> exit 2"
else
    fail "engineer + SPEC (features/user_auth.md) -> expected exit 2, got $EC"
fi

# 3. engineer + QA -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/core/api_endpoints.discoveries.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "engineer + QA (api_endpoints.discoveries.md) -> exit 2"
else
    fail "engineer + QA (api_endpoints.discoveries.md) -> expected exit 2, got $EC"
fi

# 4. engineer + INVARIANT -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/_invariants/i_arch_security.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "engineer + INVARIANT (i_arch_security.md) -> exit 2"
else
    fail "engineer + INVARIANT (i_arch_security.md) -> expected exit 2, got $EC"
fi

# 5. engineer + companion (CODE) -> allow (exit 0)
INPUT="$(make_input "$FIXTURE_DIR/features/core/api_endpoints.impl.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "engineer + CODE companion (api_endpoints.impl.md) -> exit 0"
else
    fail "engineer + CODE companion (api_endpoints.impl.md) -> expected exit 0, got $EC"
fi

# --- PM mode ---
echo ""
echo "-- PM mode --"

set_mode "pm"

# 6. pm + SPEC -> allow (exit 0)
INPUT="$(make_input "$FIXTURE_DIR/features/core/user_auth.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "pm + SPEC (features/user_auth.md) -> exit 0"
else
    fail "pm + SPEC (features/user_auth.md) -> expected exit 0, got $EC"
fi

# 7. pm + CODE -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/src/app.py")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "pm + CODE (src/app.py) -> exit 2"
else
    fail "pm + CODE (src/app.py) -> expected exit 2, got $EC"
fi

# 8. pm + QA -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/core/api_endpoints.discoveries.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "pm + QA (api_endpoints.discoveries.md) -> exit 2"
else
    fail "pm + QA (api_endpoints.discoveries.md) -> expected exit 2, got $EC"
fi

# 9. pm + INVARIANT -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/_invariants/i_arch_security.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "pm + INVARIANT (i_arch_security.md) -> exit 2"
else
    fail "pm + INVARIANT (i_arch_security.md) -> expected exit 2, got $EC"
fi

# --- QA mode ---
echo ""
echo "-- QA mode --"

set_mode "qa"

# 10. qa + QA -> allow (exit 0)
INPUT="$(make_input "$FIXTURE_DIR/features/core/api_endpoints.discoveries.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "qa + QA (api_endpoints.discoveries.md) -> exit 0"
else
    fail "qa + QA (api_endpoints.discoveries.md) -> expected exit 0, got $EC"
fi

# 11. qa + CODE -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/src/app.py")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "qa + CODE (src/app.py) -> exit 2"
else
    fail "qa + CODE (src/app.py) -> expected exit 2, got $EC"
fi

# 12. qa + SPEC -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/core/user_auth.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "qa + SPEC (features/user_auth.md) -> exit 2"
else
    fail "qa + SPEC (features/user_auth.md) -> expected exit 2, got $EC"
fi

# 13. qa + INVARIANT -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/_invariants/i_arch_security.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "qa + INVARIANT (i_arch_security.md) -> exit 2"
else
    fail "qa + INVARIANT (i_arch_security.md) -> expected exit 2, got $EC"
fi

# --- No mode (empty) ---
echo ""
echo "-- No mode (empty) --"

clear_mode

# 14. no mode + CODE -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/src/app.py")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "no mode + CODE (src/app.py) -> exit 2"
else
    fail "no mode + CODE (src/app.py) -> expected exit 2, got $EC"
fi

# 15. no mode + SPEC -> block (exit 2)
INPUT="$(make_input "$FIXTURE_DIR/features/core/user_auth.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "no mode + SPEC (features/user_auth.md) -> exit 2"
else
    fail "no mode + SPEC (features/user_auth.md) -> expected exit 2, got $EC"
fi

# --- Extra invariant tests ---
echo ""
echo "-- Invariant blocked in all modes --"

# 16. engineer + second invariant -> block
set_mode "engineer"
INPUT="$(make_input "$FIXTURE_DIR/features/_invariants/i_policy_data_retention.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "engineer + INVARIANT (i_policy_data_retention.md) -> exit 2"
else
    fail "engineer + INVARIANT (i_policy_data_retention.md) -> expected exit 2, got $EC"
fi

# 17. pm + second invariant -> block
set_mode "pm"
INPUT="$(make_input "$FIXTURE_DIR/features/_invariants/i_policy_data_retention.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "pm + INVARIANT (i_policy_data_retention.md) -> exit 2"
else
    fail "pm + INVARIANT (i_policy_data_retention.md) -> expected exit 2, got $EC"
fi

# 18. qa + second invariant -> block
set_mode "qa"
INPUT="$(make_input "$FIXTURE_DIR/features/_invariants/i_policy_data_retention.md")"
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 2 ]]; then
    pass "qa + INVARIANT (i_policy_data_retention.md) -> exit 2"
else
    fail "qa + INVARIANT (i_policy_data_retention.md) -> expected exit 2, got $EC"
fi

# 19. mode-guard with empty file_path -> allow (fail open)
set_mode "engineer"
INPUT='{"tool_name":"Write","tool_input":{"file_path":""}}'
EC="$(run_hook_exit_code mode-guard.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "engineer + empty file_path -> exit 0 (fail open)"
else
    fail "engineer + empty file_path -> expected exit 0, got $EC"
fi

# ---------------------------------------------------------------------------
# Test: session-start.sh
# ---------------------------------------------------------------------------
echo ""
echo "=== Session Start Tests ==="

# 20. session-start.sh outputs purlin reminder
OUTPUT="$(run_hook session-start.sh "")"
if echo "$OUTPUT" | grep -qi "purlin"; then
    pass "session-start.sh output contains 'purlin'"
else
    fail "session-start.sh output does not contain 'purlin': $OUTPUT"
fi

# 21. session-start.sh exits 0
EC="$(run_hook_exit_code session-start.sh "")"
if [[ "$EC" -eq 0 ]]; then
    pass "session-start.sh exits 0"
else
    fail "session-start.sh expected exit 0, got $EC"
fi

# ---------------------------------------------------------------------------
# Test: pre-compact-checkpoint.sh
# ---------------------------------------------------------------------------
echo ""
echo "=== Pre-Compact Checkpoint Tests ==="

# Clean up any previous checkpoint
rm -f "$FIXTURE_DIR/.purlin/cache/session_checkpoint_purlin.md"

# 22. pre-compact-checkpoint.sh creates checkpoint file
run_hook pre-compact-checkpoint.sh "" >/dev/null
if [[ -f "$FIXTURE_DIR/.purlin/cache/session_checkpoint_purlin.md" ]]; then
    pass "pre-compact-checkpoint.sh creates session_checkpoint_purlin.md"
else
    fail "pre-compact-checkpoint.sh did not create session_checkpoint_purlin.md"
fi

# 23. checkpoint contains expected content
if [[ -f "$FIXTURE_DIR/.purlin/cache/session_checkpoint_purlin.md" ]]; then
    CHECKPOINT_CONTENT="$(cat "$FIXTURE_DIR/.purlin/cache/session_checkpoint_purlin.md")"
    if echo "$CHECKPOINT_CONTENT" | grep -q "Session Checkpoint"; then
        pass "checkpoint contains 'Session Checkpoint' header"
    else
        fail "checkpoint missing 'Session Checkpoint' header"
    fi
else
    fail "checkpoint file not available for content check"
fi

# 24. checkpoint contains branch info
if [[ -f "$FIXTURE_DIR/.purlin/cache/session_checkpoint_purlin.md" ]]; then
    if echo "$CHECKPOINT_CONTENT" | grep -q "Branch:"; then
        pass "checkpoint contains branch info"
    else
        fail "checkpoint missing branch info"
    fi
else
    fail "checkpoint file not available for branch check"
fi

# 25. pre-compact-checkpoint.sh exits 0
EC="$(run_hook_exit_code pre-compact-checkpoint.sh "")"
if [[ "$EC" -eq 0 ]]; then
    pass "pre-compact-checkpoint.sh exits 0"
else
    fail "pre-compact-checkpoint.sh expected exit 0, got $EC"
fi

# ---------------------------------------------------------------------------
# Test: session-end-merge.sh
# ---------------------------------------------------------------------------
echo ""
echo "=== Session End Merge Tests ==="

# 26. session-end-merge.sh exits 0
EC="$(run_hook_exit_code session-end-merge.sh "")"
if [[ "$EC" -eq 0 ]]; then
    pass "session-end-merge.sh exits 0 (no-op)"
else
    fail "session-end-merge.sh expected exit 0, got $EC"
fi

# ---------------------------------------------------------------------------
# Test: permission-manager.sh
# ---------------------------------------------------------------------------
echo ""
echo "=== Permission Manager Tests ==="

# 27. bypass_permissions=true -> outputs allow decision
# The fixture has bypass_permissions: true in config.local.json
INPUT='{"tool_name":"Bash","tool_input":{"command":"ls"}}'
OUTPUT="$(run_hook permission-manager.sh "$INPUT")"
if echo "$OUTPUT" | grep -q '"allow"'; then
    pass "permission-manager.sh with bypass_permissions=true -> allow"
else
    fail "permission-manager.sh with bypass_permissions=true -> expected 'allow' in output, got: $OUTPUT"
fi

# 28. permission-manager.sh exits 0
EC="$(run_hook_exit_code permission-manager.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "permission-manager.sh exits 0"
else
    fail "permission-manager.sh expected exit 0, got $EC"
fi

# ---------------------------------------------------------------------------
# Test: companion-debt-tracker.sh
# ---------------------------------------------------------------------------
echo ""
echo "=== Companion Debt Tracker Tests ==="

# 29. companion-debt-tracker.sh exits 0 for code file
INPUT='{"file_path":"src/app.py"}'
EC="$(run_hook_exit_code companion-debt-tracker.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "companion-debt-tracker.sh exits 0 for code file"
else
    fail "companion-debt-tracker.sh expected exit 0, got $EC"
fi

# 30. companion-debt-tracker.sh exits 0 for feature file (skipped)
INPUT='{"file_path":"features/core/user_auth.md"}'
EC="$(run_hook_exit_code companion-debt-tracker.sh "$INPUT")"
if [[ "$EC" -eq 0 ]]; then
    pass "companion-debt-tracker.sh exits 0 for feature file (skipped)"
else
    fail "companion-debt-tracker.sh expected exit 0, got $EC"
fi

# ---------------------------------------------------------------------------
# Restore fixture state
# ---------------------------------------------------------------------------
set_mode "engineer"
rm -f "$FIXTURE_DIR/.purlin/cache/session_checkpoint_purlin.md"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Hook Tests Summary ==="
echo "Total: $TOTAL  Passed: $PASS  Failed: $FAIL"

if [[ "$FAIL" -gt 0 ]]; then
    echo "RESULT: FAIL"
    exit 1
else
    echo "RESULT: PASS"
    exit 0
fi
