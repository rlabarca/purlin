#!/bin/bash
# test_init_preflight.sh — Tests for init_preflight_checks feature.
# Covers all 9 automated scenarios from features/init_preflight_checks.md.
# Produces tests/init_preflight_checks/tests.json.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$SUBMODULE_SRC/tests"
PASS=0
FAIL=0
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

cleanup_sandbox() {
    if [ -n "${SANDBOX:-}" ] && [ -d "$SANDBOX" ]; then
        rm -rf "$SANDBOX"
    fi
}

# Build a sandbox simulating a consumer project with Purlin as a submodule.
setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT

    PROJECT="$SANDBOX/my-project"
    mkdir -p "$PROJECT"

    # Initialize consumer project as a git repo
    git -C "$PROJECT" init -q
    git -C "$PROJECT" commit --allow-empty -q -m "initial commit"

    # Clone current repo into the consumer project as a "submodule"
    git clone -q "$SUBMODULE_SRC" "$PROJECT/purlin"

    # Overlay uncommitted scripts so tests exercise latest code
    cp "$SUBMODULE_SRC/tools/init.sh" "$PROJECT/purlin/tools/init.sh"
    cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$PROJECT/purlin/tools/resolve_python.sh"
    # Copy CDD scripts for symlink targets
    cp "$SUBMODULE_SRC/tools/cdd/start.sh" "$PROJECT/purlin/tools/cdd/start.sh"
    cp "$SUBMODULE_SRC/tools/cdd/stop.sh" "$PROJECT/purlin/tools/cdd/stop.sh"

    INIT_SH="$PROJECT/purlin/tools/init.sh"
}

# Build a restricted PATH that excludes specific commands.
# Usage: build_restricted_path "git" "claude" "node"
build_restricted_path() {
    local excludes=("$@")
    local restricted=""
    IFS=: read -ra DIRS <<< "$PATH"
    for dir in "${DIRS[@]}"; do
        local skip=false
        for excl in "${excludes[@]}"; do
            if [ -x "$dir/$excl" ]; then
                # Only skip this dir if it ONLY has the excluded tool
                # Actually, we need to be more precise — remove the tool, not the dir
                skip=false
                break
            fi
        done
        if [ -z "$restricted" ]; then
            restricted="$dir"
        else
            restricted="$restricted:$dir"
        fi
    done
    echo "$restricted"
}

# Build a mock directory with wrapper scripts that shadow real tools.
# Usage: setup_mock_path "git" "node"  — creates mock dir where git/node are absent
# Returns: MOCK_RESTRICTED_PATH with those tools removed
setup_restricted_env() {
    local excludes=("$@")
    MOCK_BIN_DIR="$(mktemp -d)"
    MOCK_RESTRICTED_PATH="$MOCK_BIN_DIR"

    # Add all PATH dirs, but for each excluded tool, create a wrapper dir
    # that doesn't have it
    IFS=: read -ra DIRS <<< "$PATH"
    for dir in "${DIRS[@]}"; do
        local has_excluded=false
        for excl in "${excludes[@]}"; do
            if [ -x "$dir/$excl" ]; then
                has_excluded=true
                break
            fi
        done

        if [ "$has_excluded" = true ]; then
            # Create a shadow dir with everything EXCEPT the excluded tools
            local shadow="$(mktemp -d)"
            for file in "$dir"/*; do
                [ -f "$file" ] || continue
                local bname
                bname="$(basename "$file")"
                local is_excluded=false
                for excl in "${excludes[@]}"; do
                    if [ "$bname" = "$excl" ]; then
                        is_excluded=true
                        break
                    fi
                done
                if [ "$is_excluded" = false ]; then
                    ln -s "$file" "$shadow/$bname" 2>/dev/null || true
                fi
            done
            MOCK_RESTRICTED_PATH="$MOCK_RESTRICTED_PATH:$shadow"
        else
            MOCK_RESTRICTED_PATH="$MOCK_RESTRICTED_PATH:$dir"
        fi
    done
}

###############################################################################
# Scenario: All prerequisites present
###############################################################################
echo ""
echo "[Scenario] All prerequisites present"
setup_sandbox

OUTPUT=$("$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Init completes successfully with all prerequisites"
else
    log_fail "Init failed with all prerequisites present (exit $EXIT_CODE)"
fi

# Should NOT contain NOT FOUND warnings
if echo "$OUTPUT" | grep -qi "NOT FOUND"; then
    log_fail "Preflight printed warnings when all tools are present"
else
    log_pass "No preflight warnings when all tools present"
fi

# Should proceed to mode detection (init completes)
if [ -d "$PROJECT/.purlin" ]; then
    log_pass "Initialization proceeded to completion"
else
    log_fail "Initialization did not complete (.purlin/ not created)"
fi

cleanup_sandbox

###############################################################################
# Scenario: Git missing blocks init
###############################################################################
echo ""
echo "[Scenario] Git missing blocks init"
setup_sandbox

# We need to run init.sh without git on PATH.
# Since setup_sandbox already created the sandbox using git, we can now
# remove git from PATH for the actual init run.
setup_restricted_env "git"
OUTPUT=$(PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" 2>&1) || true
EXIT_CODE=${PIPESTATUS[0]:-$?}

# Capture exit code properly
PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" > /tmp/preflight_test_stdout.txt 2>/tmp/preflight_test_stderr.txt
EXIT_CODE=$?

COMBINED_OUTPUT="$(cat /tmp/preflight_test_stdout.txt /tmp/preflight_test_stderr.txt)"

if [ $EXIT_CODE -ne 0 ]; then
    log_pass "Script exits with non-zero code when git is missing"
else
    log_fail "Script should exit non-zero when git is missing (got $EXIT_CODE)"
fi

if echo "$COMBINED_OUTPUT" | grep -qi "git"; then
    if echo "$COMBINED_OUTPUT" | grep -qi "not found"; then
        log_pass "Output includes git not found message"
    else
        log_fail "Output mentions git but not 'not found'"
    fi
else
    log_fail "Output does not mention git"
fi

if echo "$COMBINED_OUTPUT" | grep -qi "brew install git\|apt-get install git"; then
    log_pass "Output includes platform-appropriate install command for git"
else
    log_fail "Output missing install command for git"
fi

# .purlin/ should NOT have been created (no init steps executed)
# Note: .purlin/ doesn't exist in a fresh sandbox, so check it stayed absent
if [ ! -d "$PROJECT/.purlin" ]; then
    log_pass "No initialization steps executed (no .purlin/ created)"
else
    log_fail ".purlin/ was created despite git being missing"
fi

rm -f /tmp/preflight_test_stdout.txt /tmp/preflight_test_stderr.txt
cleanup_sandbox

###############################################################################
# Scenario: Claude CLI missing warns and continues
###############################################################################
echo ""
echo "[Scenario] Claude CLI missing warns and continues"
setup_sandbox

setup_restricted_env "claude"
OUTPUT=$(PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Init completes successfully without claude CLI"
else
    log_fail "Init failed without claude CLI (exit $EXIT_CODE)"
fi

if echo "$OUTPUT" | grep -qi "claude.*NOT FOUND"; then
    log_pass "Warning about claude not found is printed"
else
    log_fail "No warning about claude being missing"
fi

if echo "$OUTPUT" | grep -q "npm install -g @anthropic-ai/claude-code"; then
    log_pass "Claude install command is shown"
else
    log_fail "Claude install command not shown"
fi

if echo "$OUTPUT" | grep -qi "MCP servers will not be installed"; then
    log_pass "MCP servers note is shown"
else
    log_fail "MCP servers note not shown"
fi

cleanup_sandbox

###############################################################################
# Scenario: Node missing warns and continues
###############################################################################
echo ""
echo "[Scenario] Node missing warns and continues"
setup_sandbox

setup_restricted_env "node"
OUTPUT=$(PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Init completes successfully without node"
else
    log_fail "Init failed without node (exit $EXIT_CODE)"
fi

if echo "$OUTPUT" | grep -qi "node.*NOT FOUND"; then
    log_pass "Warning about node not found is printed"
else
    log_fail "No warning about node being missing"
fi

if echo "$OUTPUT" | grep -qi "Playwright web testing will be unavailable"; then
    log_pass "Playwright unavailability note is shown"
else
    log_fail "Playwright unavailability note not shown"
fi

cleanup_sandbox

###############################################################################
# Scenario: Multiple tools missing reports all before exit
###############################################################################
echo ""
echo "[Scenario] Multiple tools missing reports all before exit"
setup_sandbox

# Remove both git and node
setup_restricted_env "git" "node"
PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" > /tmp/preflight_multi_stdout.txt 2>/tmp/preflight_multi_stderr.txt
EXIT_CODE=$?
COMBINED_OUTPUT="$(cat /tmp/preflight_multi_stdout.txt /tmp/preflight_multi_stderr.txt)"

if [ $EXIT_CODE -ne 0 ]; then
    log_pass "Script exits non-zero when required tool (git) is missing"
else
    log_fail "Script should exit non-zero with git missing"
fi

if echo "$COMBINED_OUTPUT" | grep -qi "git.*NOT FOUND"; then
    log_pass "Git missing is reported"
else
    log_fail "Git missing not reported"
fi

if echo "$COMBINED_OUTPUT" | grep -qi "node.*NOT FOUND"; then
    log_pass "Node missing is reported alongside git"
else
    log_fail "Node missing not reported (should report ALL missing tools before exit)"
fi

rm -f /tmp/preflight_multi_stdout.txt /tmp/preflight_multi_stderr.txt
cleanup_sandbox

###############################################################################
# Scenario: Platform detection for install commands
###############################################################################
echo ""
echo "[Scenario] Platform detection for install commands"
setup_sandbox

# On macOS (which is our test platform), git install should suggest brew
setup_restricted_env "git"
PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" > /tmp/preflight_platform_stdout.txt 2>/tmp/preflight_platform_stderr.txt || true
COMBINED_OUTPUT="$(cat /tmp/preflight_platform_stdout.txt /tmp/preflight_platform_stderr.txt)"

CURRENT_PLATFORM="$(uname -s)"
if [ "$CURRENT_PLATFORM" = "Darwin" ]; then
    if echo "$COMBINED_OUTPUT" | grep -q "brew install git"; then
        log_pass "macOS platform detected: brew install git suggested"
    else
        log_fail "macOS platform not detected (expected 'brew install git')"
    fi
else
    if echo "$COMBINED_OUTPUT" | grep -q "apt-get install git"; then
        log_pass "Linux platform detected: apt-get install git suggested"
    else
        log_fail "Linux platform not detected (expected 'apt-get install git')"
    fi
fi

rm -f /tmp/preflight_platform_stdout.txt /tmp/preflight_platform_stderr.txt
cleanup_sandbox

###############################################################################
# Scenario: Post-init narrative on full init
###############################################################################
echo ""
echo "[Scenario] Post-init narrative on full init"
setup_sandbox

OUTPUT=$("$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Full init completes"
else
    log_fail "Full init failed (exit $EXIT_CODE)"
fi

if echo "$OUTPUT" | grep -q "What's Next"; then
    log_pass "Post-init narrative includes What's Next heading"
else
    log_fail "Post-init narrative missing What's Next heading"
fi

if echo "$OUTPUT" | grep -q "git commit"; then
    log_pass "Step 1 mentions git commit"
else
    log_fail "Step 1 missing git commit mention"
fi

if echo "$OUTPUT" | grep -q "pl-run-pm.sh"; then
    log_pass "Step 2 mentions ./pl-run-pm.sh (designs context)"
else
    log_fail "Step 2 missing ./pl-run-pm.sh"
fi

if echo "$OUTPUT" | grep -qi "design"; then
    log_pass "Step 2 includes designs context"
else
    log_fail "Step 2 missing designs context"
fi

if echo "$OUTPUT" | grep -q "pl-run-architect.sh"; then
    log_pass "Step 2 mentions ./pl-run-architect.sh (requirements context)"
else
    log_fail "Step 2 missing ./pl-run-architect.sh"
fi

if echo "$OUTPUT" | grep -qi "requirement"; then
    log_pass "Step 2 includes requirements context"
else
    log_fail "Step 2 missing requirements context"
fi

if echo "$OUTPUT" | grep -q "pl-cdd-start.sh"; then
    log_pass "Narrative mentions ./pl-cdd-start.sh for dashboard"
else
    log_fail "Narrative missing ./pl-cdd-start.sh mention"
fi

cleanup_sandbox

###############################################################################
# Scenario: Post-init narrative on refresh
###############################################################################
echo ""
echo "[Scenario] Post-init narrative on refresh"
setup_sandbox

# First run: full init
"$INIT_SH" > /dev/null 2>&1

# Second run: refresh
OUTPUT=$("$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Refresh completes"
else
    log_fail "Refresh failed (exit $EXIT_CODE)"
fi

if echo "$OUTPUT" | grep -q "Purlin refreshed"; then
    log_pass "Refresh shows abbreviated summary"
else
    log_fail "Refresh missing abbreviated summary"
fi

# Should NOT include the full numbered narrative
if echo "$OUTPUT" | grep -q "What's Next"; then
    log_fail "Refresh should not include full narrative"
else
    log_pass "Refresh does not include full narrative"
fi

# Should still mention CDD dashboard
if echo "$OUTPUT" | grep -q "pl-cdd-start.sh"; then
    log_pass "Refresh summary includes CDD dashboard reminder"
else
    log_fail "Refresh summary missing CDD dashboard reminder"
fi

cleanup_sandbox

###############################################################################
# Scenario: Quiet mode suppresses preflight output
###############################################################################
echo ""
echo "[Scenario] Quiet mode suppresses preflight output"
setup_sandbox

setup_restricted_env "claude"
STDOUT_OUTPUT=$(PATH="$MOCK_RESTRICTED_PATH" "$INIT_SH" --quiet 2>/dev/null)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Quiet mode init completes"
else
    log_fail "Quiet mode init failed (exit $EXIT_CODE)"
fi

# stdout should have no preflight warnings in quiet mode
if [ -z "$STDOUT_OUTPUT" ]; then
    log_pass "Quiet mode suppresses all stdout output including preflight warnings"
else
    if echo "$STDOUT_OUTPUT" | grep -qi "NOT FOUND"; then
        log_fail "Quiet mode should suppress preflight warnings on stdout"
    else
        log_pass "No preflight warnings on stdout in quiet mode"
    fi
fi

cleanup_sandbox

###############################################################################
# Summary
###############################################################################
echo ""
echo "============================================"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS passed, $FAIL failed, $TOTAL total"
if [ $FAIL -gt 0 ]; then
    echo -e "\nFailures:$ERRORS"
fi
echo "============================================"

# Write tests.json
OUT_DIR="$TESTS_DIR/init_preflight_checks"
mkdir -p "$OUT_DIR"
if [ $FAIL -eq 0 ]; then
    STATUS="PASS"
else
    STATUS="FAIL"
fi
cat > "$OUT_DIR/tests.json" << EOF
{"status": "$STATUS", "passed": $PASS, "failed": $FAIL, "total": $TOTAL, "test_file": "tools/test_init_preflight.sh"}
EOF

echo "Wrote $OUT_DIR/tests.json"

exit $FAIL
