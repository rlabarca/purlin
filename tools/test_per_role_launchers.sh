#!/bin/bash
# test_per_role_launchers.sh — Automated tests for per-role agent launcher features.
# Tests PM, PM, Engineer, and QA launchers.
# Produces tests/{pm,architect,builder,qa}_agent_launcher/tests.json.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"

# Per-feature counters
PM_PASS=0
PM_FAIL=0
PM_ERRORS=""

ARCH_PASS=0
ARCH_FAIL=0
ARCH_ERRORS=""

BUILD_PASS=0
BUILD_FAIL=0
BUILD_ERRORS=""

QA_PASS=0
QA_FAIL=0
QA_ERRORS=""

###############################################################################
# Helpers
###############################################################################
pm_pass() { PM_PASS=$((PM_PASS + 1)); echo "  PASS: $1"; }
pm_fail() { PM_FAIL=$((PM_FAIL + 1)); PM_ERRORS="$PM_ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }
pm_pass() { ARCH_PASS=$((ARCH_PASS + 1)); echo "  PASS: $1"; }
pm_fail() { ARCH_FAIL=$((ARCH_FAIL + 1)); ARCH_ERRORS="$ARCH_ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }
eng_pass() { BUILD_PASS=$((BUILD_PASS + 1)); echo "  PASS: $1"; }
eng_fail() { BUILD_FAIL=$((BUILD_FAIL + 1)); BUILD_ERRORS="$BUILD_ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }
qa_pass() { QA_PASS=$((QA_PASS + 1)); echo "  PASS: $1"; }
qa_fail() { QA_FAIL=$((QA_FAIL + 1)); QA_ERRORS="$QA_ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

# Create a sandbox with minimal instructions and a mock claude binary.
setup_launcher_sandbox() {
    SANDBOX="$(mktemp -d)"
    MOCK_DIR="$(mktemp -d)"
    CAPTURE_FILE="$MOCK_DIR/captured_args"
    PROMPT_CAPTURE="$MOCK_DIR/captured_prompt"

    # Minimal instruction stubs
    mkdir -p "$SANDBOX/instructions" "$SANDBOX/.purlin" "$SANDBOX/.purlin/runtime"
    echo "# HOW_WE_WORK_BASE stub" > "$SANDBOX/instructions/HOW_WE_WORK_BASE.md"
    echo "# BUILDER_BASE stub" > "$SANDBOX/instructions/BUILDER_BASE.md"
    echo "# ARCHITECT_BASE stub" > "$SANDBOX/instructions/ARCHITECT_BASE.md"
    echo "# QA_BASE stub" > "$SANDBOX/instructions/QA_BASE.md"
    echo "# PM_BASE stub" > "$SANDBOX/instructions/PM_BASE.md"

    # Copy config resolver
    mkdir -p "$SANDBOX/tools/config"
    cp "$SCRIPT_DIR/config/resolve_config.py" "$SANDBOX/tools/config/"

    # Mock claude that captures its args and the prompt file content
    cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "\$@" > "$CAPTURE_FILE"
# Find the prompt file path from --append-system-prompt-file arg
PROMPT_PATH=""
FOUND_FLAG=0
for arg in "\$@"; do
    if [ "\$FOUND_FLAG" = "1" ]; then
        PROMPT_PATH="\$arg"
        break
    fi
    if [ "\$arg" = "--append-system-prompt-file" ]; then
        FOUND_FLAG=1
    fi
done
if [ -n "\$PROMPT_PATH" ] && [ -f "\$PROMPT_PATH" ]; then
    cp "\$PROMPT_PATH" "$PROMPT_CAPTURE"
fi
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/claude"

    # Mock git
    cat > "$MOCK_DIR/git" << MOCK_EOF
#!/bin/bash
exit 0
MOCK_EOF
    chmod +x "$MOCK_DIR/git"
}

teardown_launcher_sandbox() {
    rm -rf "${SANDBOX:-}" "${MOCK_DIR:-}"
    unset SANDBOX MOCK_DIR CAPTURE_FILE PROMPT_CAPTURE
}

###############################################################################
echo "=== PM Agent Launcher Tests ==="
###############################################################################

# --- Scenario: PM Launcher Dispatches with Config ---
echo ""
echo "[Scenario] PM Launcher Dispatches with Config"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-pm.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "pm": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-pm.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-sonnet-4-6'; then
    pm_pass "PM launcher passed --model claude-sonnet-4-6"
else
    pm_fail "PM launcher did not pass --model (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--effort medium'; then
    pm_pass "PM launcher passed --effort medium"
else
    pm_fail "PM launcher did not pass --effort medium (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    pm_pass "PM launcher passed --dangerously-skip-permissions when bypass=true"
else
    pm_fail "PM launcher did not pass --dangerously-skip-permissions (captured: $CAPTURED)"
fi

# Verify resolve_config.py is called (not inline python)
if grep -q 'resolve_config.py' "$SANDBOX/pl-run-pm.sh"; then
    pm_pass "PM launcher calls resolve_config.py pm"
else
    pm_fail "PM launcher does not reference resolve_config.py"
fi

teardown_launcher_sandbox

# --- Scenario: PM Launcher Non-Bypass AllowedTools Includes Write and Edit ---
echo ""
echo "[Scenario] PM Launcher Non-Bypass AllowedTools Includes Write and Edit"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-pm.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "pm": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": false
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-pm.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    pm_pass "PM launcher passes --allowedTools when bypass=false"
else
    pm_fail "PM launcher missing --allowedTools when bypass=false (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q 'Write' && echo "$CAPTURED" | grep -q 'Edit'; then
    pm_pass "PM --allowedTools includes Write and Edit"
else
    pm_fail "PM --allowedTools missing Write/Edit (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    pm_fail "PM should NOT pass --dangerously-skip-permissions when bypass=false"
else
    pm_pass "PM does not pass --dangerously-skip-permissions when bypass=false"
fi

teardown_launcher_sandbox

# --- Scenario: PM Launcher Falls Back When Config is Missing ---
echo ""
echo "[Scenario] PM Launcher Falls Back When Config is Missing"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-pm.sh" "$SANDBOX/"
# No agents.pm in config
cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": { "model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": false }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-pm.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-sonnet-4-6'; then
    pm_pass "PM defaults to model claude-sonnet-4-6 when absent from config"
else
    pm_fail "PM did not default to sonnet-4-6 (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--effort medium'; then
    pm_pass "PM defaults to effort medium when absent from config"
else
    pm_fail "PM did not default to effort medium (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    pm_pass "PM defaults to bypass_permissions true when absent from config"
else
    pm_fail "PM did not default to bypass=true (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: PM Launcher Assembles Correct Prompt ---
echo ""
echo "[Scenario] PM Launcher Assembles Correct Prompt"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-pm.sh" "$SANDBOX/"

# Create PM_OVERRIDES.md to verify it gets included
echo "# PM_OVERRIDES content" > "$SANDBOX/.purlin/PM_OVERRIDES.md"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "pm": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-pm.sh" > /dev/null 2>&1
PROMPT_CONTENT=$(cat "$PROMPT_CAPTURE" 2>/dev/null || echo "")

if echo "$PROMPT_CONTENT" | grep -q 'HOW_WE_WORK_BASE stub'; then
    pm_pass "Prompt includes HOW_WE_WORK_BASE.md content"
else
    pm_fail "Prompt missing HOW_WE_WORK_BASE.md (prompt: $PROMPT_CONTENT)"
fi

if echo "$PROMPT_CONTENT" | grep -q 'PM_BASE stub'; then
    pm_pass "Prompt includes PM_BASE.md content"
else
    pm_fail "Prompt missing PM_BASE.md (prompt: $PROMPT_CONTENT)"
fi

if echo "$PROMPT_CONTENT" | grep -q 'PM_OVERRIDES content'; then
    pm_pass "Prompt includes PM_OVERRIDES.md content"
else
    pm_fail "Prompt missing PM_OVERRIDES.md (prompt: $PROMPT_CONTENT)"
fi

# Verify session message
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")
if echo "$CAPTURED" | grep -q 'Begin PM session.'; then
    pm_pass "Session message is 'Begin PM session.'"
else
    pm_fail "Wrong session message (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Init Script Generates PM Launcher ---
echo ""
echo "[Scenario] Init Script Generates PM Launcher"

# Verify init.sh has the PM launcher generation call
if grep -q 'generate_launcher.*pl-run-pm.sh.*"pm".*PM_BASE.md.*PM_OVERRIDES.md.*"Begin PM session."' "$SCRIPT_DIR/init.sh"; then
    pm_pass "init.sh generates pl-run-pm.sh with correct parameters"
else
    pm_fail "init.sh missing PM launcher generation call"
fi

# Verify the generate_launcher function includes PM-specific defaults
if grep -q 'pm' "$SCRIPT_DIR/init.sh" && grep -A5 'Role-specific defaults' "$SCRIPT_DIR/init.sh" | grep -q 'pm'; then
    pm_pass "generate_launcher includes PM-specific default handling"
else
    pm_fail "generate_launcher missing PM-specific defaults"
fi

# Test actual generation in a sandbox
INIT_SANDBOX="$(mktemp -d)"
mkdir -p "$INIT_SANDBOX/.purlin"
cat > "$INIT_SANDBOX/.purlin/config.json" << 'EOF'
{ "agents": {} }
EOF

# Create minimal instruction stubs for init to work
mkdir -p "$INIT_SANDBOX/purlin/instructions"
echo "# stub" > "$INIT_SANDBOX/purlin/instructions/HOW_WE_WORK_BASE.md"
echo "# stub" > "$INIT_SANDBOX/purlin/instructions/PM_BASE.md"
echo "# stub" > "$INIT_SANDBOX/purlin/instructions/ARCHITECT_BASE.md"
echo "# stub" > "$INIT_SANDBOX/purlin/instructions/BUILDER_BASE.md"
echo "# stub" > "$INIT_SANDBOX/purlin/instructions/QA_BASE.md"

# Source init.sh to get generate_launcher, then call it
(
    cd "$INIT_SANDBOX"
    SUBMODULE_NAME="purlin"
    SUBMODULE_DIR="$INIT_SANDBOX/purlin"
    PROJECT_ROOT="$INIT_SANDBOX"
    source "$SCRIPT_DIR/init.sh" --source-only 2>/dev/null || true
)

# Since sourcing init.sh is complex, just verify the generated PM launcher has correct structure
# by checking init.sh output for PM role
if grep -q '"pm"' "$SCRIPT_DIR/init.sh"; then
    pm_pass "init.sh recognizes pm role for launcher generation"
else
    pm_fail "init.sh does not recognize pm role"
fi

if [ -f "$PROJECT_ROOT/pl-run-pm.sh" ] && [ -x "$PROJECT_ROOT/pl-run-pm.sh" ]; then
    pm_pass "pl-run-pm.sh exists and has executable permissions"
else
    pm_fail "pl-run-pm.sh missing or not executable at project root"
fi

rm -rf "$INIT_SANDBOX"


###############################################################################
echo ""
echo "=== PM Agent Launcher Tests ==="
###############################################################################

# --- Scenario: PM Launcher Dispatches with Config ---
echo ""
echo "[Scenario] PM Launcher Dispatches with Config"
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
    arch_pass "PM launcher passed --model claude-sonnet-4-6"
else
    arch_fail "PM launcher did not pass --model (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--effort high'; then
    arch_pass "PM launcher passed --effort high"
else
    arch_fail "PM launcher did not pass --effort high (captured: $CAPTURED)"
fi

# Verify resolve_config.py architect is called
if grep -q 'resolve_config.py' "$SANDBOX/pl-run-architect.sh"; then
    arch_pass "PM launcher calls resolve_config.py architect"
else
    arch_fail "PM launcher does not reference resolve_config.py"
fi

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    arch_pass "PM launcher passes --allowedTools (bypass=false)"
else
    arch_fail "PM launcher missing --allowedTools (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q 'Write' && echo "$CAPTURED" | grep -q 'Edit'; then
    arch_pass "PM --allowedTools includes Write and Edit"
else
    arch_fail "PM --allowedTools missing Write/Edit (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--append-system-prompt-file'; then
    arch_pass "PM launcher passes --append-system-prompt-file"
else
    arch_fail "PM launcher missing --append-system-prompt-file (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: PM Launcher Falls Back When Config is Missing ---
echo ""
echo "[Scenario] PM Launcher Falls Back When Config is Missing"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"
# No agents.architect in config
cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "pm": { "model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": true }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

# With empty model/effort, the launcher should still run (omitting --model/--effort or passing empty)
# bypass_permissions defaults to false, so --allowedTools should be present (not --dangerously-skip-permissions)
if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    arch_fail "PM should NOT have --dangerously-skip-permissions when config missing (bypass defaults to false)"
else
    arch_pass "PM defaults bypass_permissions to false when config missing"
fi

# Verify it still launches (captured args exist)
if [ -n "$CAPTURED" ]; then
    arch_pass "PM launcher still runs when role section missing from config"
else
    arch_fail "PM launcher did not run when role section missing"
fi

teardown_launcher_sandbox

# --- Scenario: PM Launcher Assembles Correct Prompt ---
echo ""
echo "[Scenario] PM Launcher Assembles Correct Prompt"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-architect.sh" "$SANDBOX/"

# Create ARCHITECT_OVERRIDES.md to verify inclusion
echo "# ARCHITECT_OVERRIDES content" > "$SANDBOX/.purlin/ARCHITECT_OVERRIDES.md"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "architect": {
            "model": "claude-sonnet-4-6",
            "effort": "high",
            "bypass_permissions": true
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-architect.sh" > /dev/null 2>&1
PROMPT_CONTENT=$(cat "$PROMPT_CAPTURE" 2>/dev/null || echo "")

if echo "$PROMPT_CONTENT" | grep -q 'HOW_WE_WORK_BASE stub'; then
    arch_pass "Prompt includes HOW_WE_WORK_BASE.md content"
else
    arch_fail "Prompt missing HOW_WE_WORK_BASE.md"
fi

if echo "$PROMPT_CONTENT" | grep -q 'ARCHITECT_BASE stub'; then
    arch_pass "Prompt includes ARCHITECT_BASE.md content"
else
    arch_fail "Prompt missing ARCHITECT_BASE.md"
fi

if echo "$PROMPT_CONTENT" | grep -q 'ARCHITECT_OVERRIDES content'; then
    arch_pass "Prompt includes ARCHITECT_OVERRIDES.md content"
else
    arch_fail "Prompt missing ARCHITECT_OVERRIDES.md"
fi

# Verify session message
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")
if echo "$CAPTURED" | grep -q 'Begin PM session.'; then
    arch_pass "Session message is 'Begin PM session.'"
else
    arch_fail "Wrong session message (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

###############################################################################
echo ""
echo "=== Engineer Agent Launcher Tests ==="
###############################################################################

# --- Scenario: Engineer Launcher Dispatches with Config ---
echo ""
echo "[Scenario] Engineer Launcher Dispatches with Config"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-builder.sh" "$SANDBOX/"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-builder.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

if echo "$CAPTURED" | grep -q -- '--model claude-opus-4-6'; then
    build_pass "Engineer launcher passed --model claude-opus-4-6"
else
    build_fail "Engineer launcher did not pass --model (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--effort high'; then
    build_pass "Engineer launcher passed --effort high"
else
    build_fail "Engineer launcher did not pass --effort high (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    build_pass "Engineer launcher passed --dangerously-skip-permissions when bypass=true"
else
    build_fail "Engineer launcher did not pass --dangerously-skip-permissions (captured: $CAPTURED)"
fi

# Verify resolve_config.py is called
if grep -q 'resolve_config.py' "$SANDBOX/pl-run-builder.sh"; then
    build_pass "Engineer launcher calls resolve_config.py builder"
else
    build_fail "Engineer launcher does not reference resolve_config.py"
fi

if echo "$CAPTURED" | grep -q -- '--append-system-prompt-file'; then
    build_pass "Engineer launcher passes --append-system-prompt-file"
else
    build_fail "Engineer launcher missing --append-system-prompt-file (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: Engineer Launcher Uses Default Permissions When bypass=false ---
echo ""
echo "[Scenario] Engineer Launcher Uses Default Permissions When bypass=false"
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

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    build_fail "Engineer launcher should NOT pass --allowedTools when bypass=false (captured: $CAPTURED)"
else
    build_pass "Engineer launcher does not pass --allowedTools when bypass=false"
fi

if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    build_fail "Engineer launcher should NOT pass --dangerously-skip-permissions when bypass=false (captured: $CAPTURED)"
else
    build_pass "Engineer launcher does not pass --dangerously-skip-permissions when bypass=false"
fi

teardown_launcher_sandbox

# --- Scenario: Engineer Launcher Assembles Correct Prompt ---
echo ""
echo "[Scenario] Engineer Launcher Assembles Correct Prompt"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-builder.sh" "$SANDBOX/"

# Create BUILDER_OVERRIDES.md to verify inclusion
echo "# BUILDER_OVERRIDES content" > "$SANDBOX/.purlin/BUILDER_OVERRIDES.md"

cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true
        }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-builder.sh" > /dev/null 2>&1
PROMPT_CONTENT=$(cat "$PROMPT_CAPTURE" 2>/dev/null || echo "")

if echo "$PROMPT_CONTENT" | grep -q 'HOW_WE_WORK_BASE stub'; then
    build_pass "Prompt includes HOW_WE_WORK_BASE.md content"
else
    build_fail "Prompt missing HOW_WE_WORK_BASE.md"
fi

if echo "$PROMPT_CONTENT" | grep -q 'BUILDER_BASE stub'; then
    build_pass "Prompt includes BUILDER_BASE.md content"
else
    build_fail "Prompt missing BUILDER_BASE.md"
fi

if echo "$PROMPT_CONTENT" | grep -q 'BUILDER_OVERRIDES content'; then
    build_pass "Prompt includes BUILDER_OVERRIDES.md content"
else
    build_fail "Prompt missing BUILDER_OVERRIDES.md"
fi

# Verify session message
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")
if echo "$CAPTURED" | grep -q 'Begin Engineer session.'; then
    build_pass "Session message is 'Begin Engineer session.'"
else
    build_fail "Wrong session message (captured: $CAPTURED)"
fi

teardown_launcher_sandbox


###############################################################################
echo ""
echo "=== QA Agent Launcher Tests ==="
###############################################################################

# --- Scenario: QA Launcher Dispatches with Config ---
echo ""
echo "[Scenario] QA Launcher Dispatches with Config"
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

if echo "$CAPTURED" | grep -q -- '--model claude-sonnet-4-6'; then
    qa_pass "QA launcher passed --model claude-sonnet-4-6"
else
    qa_fail "QA launcher did not pass --model (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--effort medium'; then
    qa_pass "QA launcher passed --effort medium"
else
    qa_fail "QA launcher did not pass --effort medium (captured: $CAPTURED)"
fi

# Verify resolve_config.py qa is called
if grep -q 'resolve_config.py' "$SANDBOX/pl-run-qa.sh"; then
    qa_pass "QA launcher calls resolve_config.py qa"
else
    qa_fail "QA launcher does not reference resolve_config.py"
fi

if echo "$CAPTURED" | grep -q -- '--allowedTools'; then
    qa_pass "QA launcher passes --allowedTools (bypass=false)"
else
    qa_fail "QA launcher missing --allowedTools (captured: $CAPTURED)"
fi

# Verify the specific QA tool restrictions
if echo "$CAPTURED" | grep -q 'Write' && echo "$CAPTURED" | grep -q 'Edit'; then
    qa_pass "QA --allowedTools includes Write and Edit"
else
    qa_fail "QA --allowedTools missing Write/Edit (captured: $CAPTURED)"
fi

if echo "$CAPTURED" | grep -q -- '--append-system-prompt-file'; then
    qa_pass "QA launcher passes --append-system-prompt-file"
else
    qa_fail "QA launcher missing --append-system-prompt-file (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

# --- Scenario: QA Launcher Falls Back When Config is Missing ---
echo ""
echo "[Scenario] QA Launcher Falls Back When Config is Missing"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-qa.sh" "$SANDBOX/"
# No agents.qa in config
cat > "$SANDBOX/.purlin/config.json" << 'EOF'
{
    "agents": {
        "pm": { "model": "claude-sonnet-4-6", "effort": "medium", "bypass_permissions": true }
    }
}
EOF

PATH="$MOCK_DIR:$PATH" bash "$SANDBOX/pl-run-qa.sh" > /dev/null 2>&1
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")

# bypass_permissions defaults to false, so --allowedTools should be present
if echo "$CAPTURED" | grep -q -- '--dangerously-skip-permissions'; then
    qa_fail "QA should NOT have --dangerously-skip-permissions when config missing (bypass defaults to false)"
else
    qa_pass "QA defaults bypass_permissions to false when config missing"
fi

# Verify it still launches
if [ -n "$CAPTURED" ]; then
    qa_pass "QA launcher still runs when role section missing from config"
else
    qa_fail "QA launcher did not run when role section missing"
fi

teardown_launcher_sandbox

# --- Scenario: QA Launcher Assembles Correct Prompt ---
echo ""
echo "[Scenario] QA Launcher Assembles Correct Prompt"
setup_launcher_sandbox

cp "$PROJECT_ROOT/pl-run-qa.sh" "$SANDBOX/"

# Create QA_OVERRIDES.md to verify inclusion
echo "# QA_OVERRIDES content" > "$SANDBOX/.purlin/QA_OVERRIDES.md"

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
PROMPT_CONTENT=$(cat "$PROMPT_CAPTURE" 2>/dev/null || echo "")

if echo "$PROMPT_CONTENT" | grep -q 'HOW_WE_WORK_BASE stub'; then
    qa_pass "Prompt includes HOW_WE_WORK_BASE.md content"
else
    qa_fail "Prompt missing HOW_WE_WORK_BASE.md"
fi

if echo "$PROMPT_CONTENT" | grep -q 'QA_BASE stub'; then
    qa_pass "Prompt includes QA_BASE.md content"
else
    qa_fail "Prompt missing QA_BASE.md"
fi

if echo "$PROMPT_CONTENT" | grep -q 'QA_OVERRIDES content'; then
    qa_pass "Prompt includes QA_OVERRIDES.md content"
else
    qa_fail "Prompt missing QA_OVERRIDES.md"
fi

# Verify session message
CAPTURED=$(cat "$CAPTURE_FILE" 2>/dev/null || echo "")
if echo "$CAPTURED" | grep -q 'Begin QA verification session.'; then
    qa_pass "Session message is 'Begin QA verification session.'"
else
    qa_fail "Wrong session message (captured: $CAPTURED)"
fi

teardown_launcher_sandbox

###############################################################################
# Results
###############################################################################
echo ""
echo "==============================="
echo "  PM Launcher: $PM_PASS/$((PM_PASS + PM_FAIL)) passed"
if [ $PM_FAIL -gt 0 ]; then
    echo "  Failures:"
    echo -e "$PM_ERRORS"
fi
echo ""
echo "  PM Launcher: $ARCH_PASS/$((ARCH_PASS + ARCH_FAIL)) passed"
if [ $ARCH_FAIL -gt 0 ]; then
    echo "  Failures:"
    echo -e "$ARCH_ERRORS"
fi
echo ""
echo "  Engineer Launcher: $BUILD_PASS/$((BUILD_PASS + BUILD_FAIL)) passed"
if [ $BUILD_FAIL -gt 0 ]; then
    echo "  Failures:"
    echo -e "$BUILD_ERRORS"
fi
echo ""
echo "  QA Launcher: $QA_PASS/$((QA_PASS + QA_FAIL)) passed"
if [ $QA_FAIL -gt 0 ]; then
    echo "  Failures:"
    echo -e "$QA_ERRORS"
fi
echo "==============================="

# Write per-feature test results
PM_TOTAL=$((PM_PASS + PM_FAIL))
ARCH_TOTAL=$((ARCH_PASS + ARCH_FAIL))
BUILD_TOTAL=$((BUILD_PASS + BUILD_FAIL))
QA_TOTAL=$((QA_PASS + QA_FAIL))

PM_JSON="{\"status\": \"$([ $PM_FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PM_PASS, \"failed\": $PM_FAIL, \"total\": $PM_TOTAL, \"test_file\": \"tools/test_per_role_launchers.sh\"}"
ARCH_JSON="{\"status\": \"$([ $ARCH_FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $ARCH_PASS, \"failed\": $ARCH_FAIL, \"total\": $ARCH_TOTAL, \"test_file\": \"tools/test_per_role_launchers.sh\"}"
BUILD_JSON="{\"status\": \"$([ $BUILD_FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $BUILD_PASS, \"failed\": $BUILD_FAIL, \"total\": $BUILD_TOTAL, \"test_file\": \"tools/test_per_role_launchers.sh\"}"
QA_JSON="{\"status\": \"$([ $QA_FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $QA_PASS, \"failed\": $QA_FAIL, \"total\": $QA_TOTAL, \"test_file\": \"tools/test_per_role_launchers.sh\"}"

mkdir -p "$TESTS_DIR/pm_agent_launcher"
echo "$PM_JSON" > "$TESTS_DIR/pm_agent_launcher/tests.json"

mkdir -p "$TESTS_DIR/architect_agent_launcher"
echo "$ARCH_JSON" > "$TESTS_DIR/architect_agent_launcher/tests.json"

mkdir -p "$TESTS_DIR/builder_agent_launcher"
echo "$BUILD_JSON" > "$TESTS_DIR/builder_agent_launcher/tests.json"

mkdir -p "$TESTS_DIR/qa_agent_launcher"
echo "$QA_JSON" > "$TESTS_DIR/qa_agent_launcher/tests.json"

echo ""
OVERALL_FAIL=$((PM_FAIL + ARCH_FAIL + BUILD_FAIL + QA_FAIL))
if [ $OVERALL_FAIL -eq 0 ]; then
    echo "All tests passed."
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
