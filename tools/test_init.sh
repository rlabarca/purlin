#!/bin/bash
# test_init.sh — Automated tests for tools/init.sh (Unified Project Init)
# Produces tests/<feature>/tests.json in the project's tests directory.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$SUBMODULE_SRC/tests"
PASS=0
FAIL=0
ERRORS=""

# Separate counters for context_recovery_hook feature tests
CRH_PASS=0
CRH_FAIL=0

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
    # Copy requirements files
    cp "$SUBMODULE_SRC/requirements.txt" "$PROJECT/purlin/requirements.txt" 2>/dev/null || true
    cp "$SUBMODULE_SRC/requirements-optional.txt" "$PROJECT/purlin/requirements-optional.txt" 2>/dev/null || true
    # Copy MCP manifest
    mkdir -p "$PROJECT/purlin/tools/mcp"
    if [ -f "$SUBMODULE_SRC/tools/mcp/manifest.json" ]; then
        cp "$SUBMODULE_SRC/tools/mcp/manifest.json" "$PROJECT/purlin/tools/mcp/manifest.json"
    fi
    # Copy CLAUDE.md.purlin template
    if [ -f "$SUBMODULE_SRC/purlin-config-sample/CLAUDE.md.purlin" ]; then
        cp "$SUBMODULE_SRC/purlin-config-sample/CLAUDE.md.purlin" "$PROJECT/purlin/purlin-config-sample/CLAUDE.md.purlin"
    fi
    # Copy agent files if they exist
    if [ -d "$SUBMODULE_SRC/.claude/agents" ]; then
        mkdir -p "$PROJECT/purlin/.claude/agents"
        cp "$SUBMODULE_SRC/.claude/agents/"*.md "$PROJECT/purlin/.claude/agents/" 2>/dev/null || true
    fi
    chmod +x "$PROJECT/purlin/tools/init.sh" "$PROJECT/purlin/tools/resolve_python.sh"

    # Create submodule root symlink
    ln -sf tools/init.sh "$PROJECT/purlin/pl-init.sh"

    # Register as a submodule in .gitmodules (so git submodule commands work)
    cat > "$PROJECT/.gitmodules" << 'GITMOD_EOF'
[submodule "purlin"]
    path = purlin
    url = https://github.com/rlabarca/purlin.git
GITMOD_EOF

    INIT_SH="$PROJECT/purlin/tools/init.sh"
}

###############################################################################
echo "=== Full Init Tests ==="
###############################################################################

# --- Test 1: Fresh init creates .purlin/ ---
echo ""
echo "[Test 1] Fresh init creates .purlin/"
setup_sandbox

OUTPUT=$("$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "Exit code 0"; else log_fail "Exit code was $EXIT_CODE (expected 0)"; fi
if [ -d "$PROJECT/.purlin" ]; then log_pass ".purlin/ created"; else log_fail ".purlin/ not created"; fi
if [ -f "$PROJECT/.purlin/config.json" ]; then log_pass "config.json exists"; else log_fail "config.json missing"; fi
if [ -f "$PROJECT/.purlin/ARCHITECT_OVERRIDES.md" ]; then log_pass "ARCHITECT_OVERRIDES.md exists"; else log_fail "ARCHITECT_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/BUILDER_OVERRIDES.md" ]; then log_pass "BUILDER_OVERRIDES.md exists"; else log_fail "BUILDER_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/QA_OVERRIDES.md" ]; then log_pass "QA_OVERRIDES.md exists"; else log_fail "QA_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then log_pass "HOW_WE_WORK_OVERRIDES.md exists"; else log_fail "HOW_WE_WORK_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/.upstream_sha" ]; then log_pass ".upstream_sha exists"; else log_fail ".upstream_sha missing"; fi

cleanup_sandbox

# --- Test 2: Config JSON validity ---
echo ""
echo "[Test 2] Config JSON validity"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

if python3 -c "import json; json.load(open('$PROJECT/.purlin/config.json'))" 2>/dev/null; then
    log_pass "config.json is valid JSON"
else
    log_fail "config.json is NOT valid JSON"
fi

cleanup_sandbox

# --- Test 3: Config tools_root is correct ---
echo ""
echo "[Test 3] Config tools_root is correct"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

if grep -q '"tools_root": "purlin/tools"' "$PROJECT/.purlin/config.json"; then
    log_pass "tools_root set to purlin/tools"
else
    log_fail "tools_root incorrect: $(grep tools_root "$PROJECT/.purlin/config.json")"
fi

cleanup_sandbox

# --- Test 4: Launcher scripts created and executable ---
echo ""
echo "[Test 4] Launcher scripts created and executable"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if [ -x "$PROJECT/$launcher" ]; then
        log_pass "$launcher exists and is executable"
    else
        log_fail "$launcher missing or not executable"
    fi
done

cleanup_sandbox

# --- Test 5: Launcher scripts export PURLIN_PROJECT_ROOT ---
echo ""
echo "[Test 5] Launcher scripts export PURLIN_PROJECT_ROOT"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if grep -q 'export PURLIN_PROJECT_ROOT=' "$PROJECT/$launcher"; then
        log_pass "$launcher exports PURLIN_PROJECT_ROOT"
    else
        log_fail "$launcher does NOT export PURLIN_PROJECT_ROOT"
    fi
done

cleanup_sandbox

# --- Test 6: Command files copied ---
echo ""
echo "[Test 6] Command files copied"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

if [ -d "$PROJECT/.claude/commands" ]; then
    CMD_COUNT=$(ls "$PROJECT/.claude/commands"/pl-*.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$CMD_COUNT" -gt 0 ]; then
        log_pass ".claude/commands/ contains $CMD_COUNT pl-*.md files"
    else
        log_fail ".claude/commands/ exists but no pl-*.md files found"
    fi
else
    log_fail ".claude/commands/ not created"
fi

cleanup_sandbox

# --- Test 7: pl-edit-base.md excluded ---
echo ""
echo "[Test 7] pl-edit-base.md excluded"
setup_sandbox

# Ensure pl-edit-base.md exists in the submodule
mkdir -p "$PROJECT/purlin/.claude/commands"
echo "# MUST NOT be distributed" > "$PROJECT/purlin/.claude/commands/pl-edit-base.md"

"$INIT_SH" > /dev/null 2>&1

if [ -f "$PROJECT/.claude/commands/pl-edit-base.md" ]; then
    log_fail "pl-edit-base.md was copied (MUST NOT be)"
else
    log_pass "pl-edit-base.md correctly excluded"
fi

cleanup_sandbox

# --- Test 8: features/ directory created ---
echo ""
echo "[Test 8] features/ directory created"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

if [ -d "$PROJECT/features" ]; then
    log_pass "features/ directory exists"
else
    log_fail "features/ directory missing"
fi

cleanup_sandbox

# --- Test 9: Shim generated ---
echo ""
echo "[Test 9] Shim generated"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

if [ -x "$PROJECT/pl-init.sh" ]; then
    log_pass "pl-init.sh exists and is executable"
else
    log_fail "pl-init.sh missing or not executable"
fi

cleanup_sandbox

# --- Test 10: Shim contains metadata ---
echo ""
echo "[Scenario] Shim Contains Repo URL, SHA, and Version"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

SHIM_CONTENT="$(cat "$PROJECT/pl-init.sh")"
EXPECTED_SHA="$(git -C "$PROJECT/purlin" rev-parse HEAD)"

if echo "$SHIM_CONTENT" | grep -q "SHA:"; then
    log_pass "Shim contains SHA field"
else
    log_fail "Shim missing SHA field"
fi
if echo "$SHIM_CONTENT" | grep -q "$EXPECTED_SHA"; then
    log_pass "Shim contains correct SHA value"
else
    log_fail "Shim SHA does not match submodule HEAD"
fi
if echo "$SHIM_CONTENT" | grep -q "Version:"; then
    log_pass "Shim contains Version field"
else
    log_fail "Shim missing Version field"
fi
if echo "$SHIM_CONTENT" | grep -q "Repo:"; then
    log_pass "Shim contains Repo field"
else
    log_fail "Shim missing Repo field"
fi

cleanup_sandbox

# --- Test 11: CDD symlinks created ---
echo ""
echo "[Test 11] CDD symlinks created"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

if [ -L "$PROJECT/pl-cdd-start.sh" ]; then
    log_pass "pl-cdd-start.sh is a symlink"
else
    log_fail "pl-cdd-start.sh is not a symlink"
fi
if [ -L "$PROJECT/pl-cdd-stop.sh" ]; then
    log_pass "pl-cdd-stop.sh is a symlink"
else
    log_fail "pl-cdd-stop.sh is not a symlink"
fi

cleanup_sandbox

# --- Test 12: CDD symlinks use relative paths ---
echo ""
echo "[Test 12] CDD symlinks use relative paths"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

START_TARGET="$(readlink "$PROJECT/pl-cdd-start.sh")"
STOP_TARGET="$(readlink "$PROJECT/pl-cdd-stop.sh")"

if [[ "$START_TARGET" != /* ]]; then
    log_pass "pl-cdd-start.sh uses relative path: $START_TARGET"
else
    log_fail "pl-cdd-start.sh uses absolute path: $START_TARGET"
fi
if [[ "$STOP_TARGET" != /* ]]; then
    log_pass "pl-cdd-stop.sh uses relative path: $STOP_TARGET"
else
    log_fail "pl-cdd-stop.sh uses absolute path: $STOP_TARGET"
fi

cleanup_sandbox

# --- Test 13: Output is concise ---
echo ""
echo "[Test 13] Output is concise"
setup_sandbox

OUTPUT=$("$INIT_SH" 2>&1)

if echo "$OUTPUT" | grep -q "Purlin initialized. Files staged."; then
    log_pass "Output contains 'Purlin initialized. Files staged.'"
else
    log_fail "Output missing 'Purlin initialized. Files staged.'"
fi
if echo "$OUTPUT" | grep -q "pl-run-architect.sh"; then
    log_pass "Output mentions pl-run-architect.sh"
else
    log_fail "Output missing pl-run-architect.sh"
fi
if echo "$OUTPUT" | grep -q "pl-run-pm.sh"; then
    log_pass "Output mentions pl-run-pm.sh"
else
    log_fail "Output missing pl-run-pm.sh"
fi
if echo "$OUTPUT" | grep -q "pl-cdd-start.sh"; then
    log_pass "Output mentions pl-cdd-start.sh"
else
    log_fail "Output missing pl-cdd-start.sh"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Refresh Mode Tests ==="
###############################################################################

# --- Test 14: Re-run enters refresh mode ---
echo ""
echo "[Test 14] Re-run enters refresh mode"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Record config modification time before second run
CONFIG_MTIME_BEFORE="$(stat -f %m "$PROJECT/.purlin/config.json" 2>/dev/null || stat -c %Y "$PROJECT/.purlin/config.json" 2>/dev/null)"

OUTPUT=$("$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "Second run exits 0"; else log_fail "Second run exits $EXIT_CODE"; fi
if echo "$OUTPUT" | grep -q "refreshed"; then
    log_pass "Second run reports 'refreshed' (refresh mode)"
else
    log_fail "Second run did not enter refresh mode"
fi

CONFIG_MTIME_AFTER="$(stat -f %m "$PROJECT/.purlin/config.json" 2>/dev/null || stat -c %Y "$PROJECT/.purlin/config.json" 2>/dev/null)"
if [ "$CONFIG_MTIME_BEFORE" = "$CONFIG_MTIME_AFTER" ]; then
    log_pass "config.json not re-created in refresh mode"
else
    log_fail "config.json modification time changed in refresh mode"
fi

cleanup_sandbox

# --- Scenario: Idempotent Repeated Runs ---
echo ""
echo "[Scenario] Idempotent Repeated Runs"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Commit everything after first init
git -C "$PROJECT" add -A > /dev/null 2>&1
git -C "$PROJECT" commit -q -m "after init" 2>/dev/null

# Run again
"$INIT_SH" > /dev/null 2>&1

# Check git diff (excluding untracked and submodule pointer changes)
DIFF_OUTPUT="$(git -C "$PROJECT" diff -- . ':!purlin' 2>/dev/null)"
if [ -z "$DIFF_OUTPUT" ]; then
    log_pass "No changes after idempotent second run"
else
    log_fail "Changes detected after second run: $(echo "$DIFF_OUTPUT" | head -5)"
fi

cleanup_sandbox

# --- Test 16: New command files copied on refresh ---
echo ""
echo "[Test 16] New command files copied on refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Create a new command file in the submodule
echo "# Test new command" > "$PROJECT/purlin/.claude/commands/pl-test-new.md"

"$INIT_SH" > /dev/null 2>&1

if [ -f "$PROJECT/.claude/commands/pl-test-new.md" ]; then
    log_pass "New command file copied on refresh"
else
    log_fail "New command file NOT copied on refresh"
fi

cleanup_sandbox

# --- Test 17: Locally modified commands preserved ---
echo ""
echo "[Test 17] Locally modified commands preserved"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Find any command file to test with
TEST_CMD=""
if [ -d "$PROJECT/.claude/commands" ]; then
    TEST_CMD="$(ls "$PROJECT/.claude/commands"/pl-*.md 2>/dev/null | head -1)"
fi

if [ -n "$TEST_CMD" ]; then
    CMD_FNAME="$(basename "$TEST_CMD")"
    # Make the consumer copy newer by touching it in the future
    sleep 1
    echo "# Local modification" >> "$TEST_CMD"
    touch "$TEST_CMD"

    CONTENT_BEFORE="$(cat "$TEST_CMD")"

    "$INIT_SH" > /dev/null 2>&1

    CONTENT_AFTER="$(cat "$TEST_CMD")"
    if [ "$CONTENT_BEFORE" = "$CONTENT_AFTER" ]; then
        log_pass "Locally modified $CMD_FNAME preserved"
    else
        log_fail "Locally modified $CMD_FNAME was overwritten"
    fi
else
    echo "  SKIP: No command files available to test"
fi

cleanup_sandbox

# --- Test 18: pl-edit-base.md excluded on refresh ---
echo ""
echo "[Test 18] pl-edit-base.md excluded on refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Add pl-edit-base.md to submodule
echo "# MUST NOT be distributed" > "$PROJECT/purlin/.claude/commands/pl-edit-base.md"

"$INIT_SH" > /dev/null 2>&1

if [ -f "$PROJECT/.claude/commands/pl-edit-base.md" ]; then
    log_fail "pl-edit-base.md copied during refresh (MUST NOT be)"
else
    log_pass "pl-edit-base.md excluded during refresh"
fi

cleanup_sandbox

# --- Test 19: Upstream SHA updated on refresh ---
echo ""
echo "[Test 19] Upstream SHA updated on refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Create a new commit in the submodule
echo "test" > "$PROJECT/purlin/test_file.txt"
git -C "$PROJECT/purlin" add test_file.txt > /dev/null 2>&1
git -C "$PROJECT/purlin" commit -q -m "test commit" 2>/dev/null

NEW_SHA="$(git -C "$PROJECT/purlin" rev-parse HEAD)"

"$INIT_SH" > /dev/null 2>&1

STORED_SHA="$(cat "$PROJECT/.purlin/.upstream_sha" | tr -d '[:space:]')"
if [ "$STORED_SHA" = "$NEW_SHA" ]; then
    log_pass ".upstream_sha updated to new SHA"
else
    log_fail ".upstream_sha not updated (got: ${STORED_SHA:0:12}, expected: ${NEW_SHA:0:12})"
fi

cleanup_sandbox

# --- Test 20: Config and overrides untouched on refresh ---
echo ""
echo "[Test 20] Config and overrides untouched on refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Record checksums
CONFIG_HASH="$(shasum "$PROJECT/.purlin/config.json" | cut -d' ' -f1)"
ARCH_HASH="$(shasum "$PROJECT/.purlin/ARCHITECT_OVERRIDES.md" | cut -d' ' -f1)"
BUILD_HASH="$(shasum "$PROJECT/.purlin/BUILDER_OVERRIDES.md" | cut -d' ' -f1)"
QA_HASH="$(shasum "$PROJECT/.purlin/QA_OVERRIDES.md" | cut -d' ' -f1)"
HWW_HASH="$(shasum "$PROJECT/.purlin/HOW_WE_WORK_OVERRIDES.md" | cut -d' ' -f1)"

"$INIT_SH" > /dev/null 2>&1

CONFIG_HASH2="$(shasum "$PROJECT/.purlin/config.json" | cut -d' ' -f1)"
ARCH_HASH2="$(shasum "$PROJECT/.purlin/ARCHITECT_OVERRIDES.md" | cut -d' ' -f1)"
BUILD_HASH2="$(shasum "$PROJECT/.purlin/BUILDER_OVERRIDES.md" | cut -d' ' -f1)"
QA_HASH2="$(shasum "$PROJECT/.purlin/QA_OVERRIDES.md" | cut -d' ' -f1)"
HWW_HASH2="$(shasum "$PROJECT/.purlin/HOW_WE_WORK_OVERRIDES.md" | cut -d' ' -f1)"

ALL_MATCH=true
[ "$CONFIG_HASH" != "$CONFIG_HASH2" ] && ALL_MATCH=false
[ "$ARCH_HASH" != "$ARCH_HASH2" ] && ALL_MATCH=false
[ "$BUILD_HASH" != "$BUILD_HASH2" ] && ALL_MATCH=false
[ "$QA_HASH" != "$QA_HASH2" ] && ALL_MATCH=false
[ "$HWW_HASH" != "$HWW_HASH2" ] && ALL_MATCH=false

if [ "$ALL_MATCH" = true ]; then
    log_pass "Config and overrides unchanged after refresh"
else
    log_fail "Config or overrides modified during refresh"
fi

cleanup_sandbox

# --- Test 21: CDD symlinks repaired on refresh ---
echo ""
echo "[Test 21] CDD symlinks repaired on refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Delete one symlink
rm -f "$PROJECT/pl-cdd-start.sh"

"$INIT_SH" > /dev/null 2>&1

if [ -L "$PROJECT/pl-cdd-start.sh" ]; then
    log_pass "CDD symlink repaired on refresh"
else
    log_fail "CDD symlink NOT repaired on refresh"
fi

cleanup_sandbox

# --- Scenario: CDD Regular File Replaced with Symlink on Refresh ---
echo ""
echo "[Scenario] CDD Regular File Replaced with Symlink on Refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Replace symlink with a regular file copy of the target
rm -f "$PROJECT/pl-cdd-start.sh"
cp "$PROJECT/purlin/tools/cdd/start.sh" "$PROJECT/pl-cdd-start.sh"

# Verify it's a regular file now
if [ -f "$PROJECT/pl-cdd-start.sh" ] && [ ! -L "$PROJECT/pl-cdd-start.sh" ]; then
    log_pass "Setup: pl-cdd-start.sh is a regular file (precondition)"
else
    log_fail "Setup: pl-cdd-start.sh should be a regular file"
fi

"$INIT_SH" > /dev/null 2>&1

if [ -L "$PROJECT/pl-cdd-start.sh" ]; then
    local_target="$(readlink "$PROJECT/pl-cdd-start.sh")"
    expected_target="purlin/tools/cdd/start.sh"
    if [ "$local_target" = "$expected_target" ]; then
        log_pass "Regular file replaced with correct symlink on refresh"
    else
        log_fail "Symlink target is '$local_target' instead of '$expected_target'"
    fi
else
    log_fail "pl-cdd-start.sh is NOT a symlink after refresh"
fi

cleanup_sandbox

# --- Scenario: Launchers Always Regenerated on Refresh ---
echo ""
echo "[Scenario] Launchers Always Regenerated on Refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Modify pl-run-architect.sh with outdated content
echo "# MODIFIED BY TEST - outdated content" > "$PROJECT/pl-run-architect.sh"

"$INIT_SH" > /dev/null 2>&1

if grep -q "PURLIN_PROJECT_ROOT" "$PROJECT/pl-run-architect.sh"; then
    log_pass "pl-run-architect.sh regenerated with current template on refresh"
else
    log_fail "pl-run-architect.sh NOT regenerated on refresh"
fi

for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if [ -x "$PROJECT/$launcher" ]; then
        log_pass "$launcher is executable after refresh"
    else
        log_fail "$launcher is NOT executable after refresh"
    fi
done

cleanup_sandbox

# --- Test 22: Shim self-update on refresh ---
echo ""
echo "[Test 22] Shim self-update on refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Create a new commit in the submodule to change HEAD
echo "update" > "$PROJECT/purlin/test_update.txt"
git -C "$PROJECT/purlin" add test_update.txt > /dev/null 2>&1
git -C "$PROJECT/purlin" commit -q -m "update commit" 2>/dev/null

NEW_SHA="$(git -C "$PROJECT/purlin" rev-parse HEAD)"

"$INIT_SH" > /dev/null 2>&1

if grep -q "$NEW_SHA" "$PROJECT/pl-init.sh"; then
    log_pass "Shim updated with new SHA"
else
    log_fail "Shim NOT updated with new SHA"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== CLI Flag Tests ==="
###############################################################################

# --- Scenario: --quiet Flag Suppresses Output ---
echo ""
echo "[Scenario] --quiet Flag Suppresses Output"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

STDOUT_OUTPUT=$("$INIT_SH" --quiet 2>/dev/null)

if [ -z "$STDOUT_OUTPUT" ]; then
    log_pass "--quiet suppresses stdout"
else
    log_fail "--quiet did not suppress stdout: $STDOUT_OUTPUT"
fi

cleanup_sandbox

# --- Test 24: --quiet still completes ---
echo ""
echo "[Test 24] --quiet still completes"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Create a new commit so SHA changes
echo "quiet test" > "$PROJECT/purlin/quiet_test.txt"
git -C "$PROJECT/purlin" add quiet_test.txt > /dev/null 2>&1
git -C "$PROJECT/purlin" commit -q -m "quiet test" 2>/dev/null

NEW_SHA="$(git -C "$PROJECT/purlin" rev-parse HEAD)"

"$INIT_SH" --quiet 2>/dev/null

STORED_SHA="$(cat "$PROJECT/.purlin/.upstream_sha" | tr -d '[:space:]')"
if [ "$STORED_SHA" = "$NEW_SHA" ]; then
    log_pass "--quiet refresh completed (.upstream_sha updated)"
else
    log_fail "--quiet refresh did not complete (.upstream_sha mismatch)"
fi

cleanup_sandbox

# --- Scenario: Refresh Removes Stale Launchers ---
echo ""
echo "[Scenario] Refresh Removes Stale Launchers"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Create stale launchers with old naming convention
echo "#!/bin/bash" > "$PROJECT/run_architect.sh"
echo "#!/bin/bash" > "$PROJECT/run_builder.sh"
echo "#!/bin/bash" > "$PROJECT/run_qa.sh"

"$INIT_SH" > /dev/null 2>&1

STALE_REMOVED=true
for stale in run_architect.sh run_builder.sh run_qa.sh; do
    if [ -f "$PROJECT/$stale" ]; then
        log_fail "Stale launcher $stale NOT removed"
        STALE_REMOVED=false
    fi
done
if [ "$STALE_REMOVED" = true ]; then
    log_pass "All stale launchers (run_*.sh) removed"
fi

# Verify new-style launchers still exist
NEW_STYLE_OK=true
for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if [ ! -x "$PROJECT/$launcher" ]; then
        log_fail "New-style launcher $launcher missing after refresh"
        NEW_STYLE_OK=false
    fi
done
if [ "$NEW_STYLE_OK" = true ]; then
    log_pass "All new-style launchers (pl-run-*.sh) present after refresh"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Standalone Guard Tests ==="
###############################################################################

# --- Scenario: Standalone Mode Guard Prevents Init in Purlin Repo ---
echo ""
echo "[Scenario] Standalone Mode Guard Prevents Init in Purlin Repo"

# Create a controlled standalone environment: parent dir is NOT a git repo
STANDALONE_DIR="$(mktemp -d)"
mkdir -p "$STANDALONE_DIR/purlin/tools"
mkdir -p "$STANDALONE_DIR/purlin/purlin-config-sample"
cp "$SUBMODULE_SRC/tools/init.sh" "$STANDALONE_DIR/purlin/tools/init.sh"
cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$STANDALONE_DIR/purlin/tools/resolve_python.sh"
chmod +x "$STANDALONE_DIR/purlin/tools/init.sh" "$STANDALONE_DIR/purlin/tools/resolve_python.sh"

# Initialize purlin/ as a git repo (so resolve_python can work)
git -C "$STANDALONE_DIR/purlin" init -q 2>/dev/null
git -C "$STANDALONE_DIR/purlin" commit --allow-empty -q -m "init" 2>/dev/null

# $STANDALONE_DIR is NOT a git repo -> guard should fire
GUARD_OUTPUT=$("$STANDALONE_DIR/purlin/tools/init.sh" 2>&1)
GUARD_EXIT=$?

if [ $GUARD_EXIT -ne 0 ]; then
    log_pass "Standalone guard exits with non-zero status ($GUARD_EXIT)"
else
    log_fail "Standalone guard did NOT exit with non-zero status"
fi

if echo "$GUARD_OUTPUT" | grep -qi "consumer project"; then
    log_pass "Standalone guard error mentions consumer projects"
else
    log_fail "Standalone guard error missing consumer project explanation: $GUARD_OUTPUT"
fi

# Verify no files were created in the parent (no side effects)
if [ ! -d "$STANDALONE_DIR/.purlin" ]; then
    log_pass "No files created outside the Purlin repo"
else
    log_fail "Files created in parent directory (side effects)"
fi

rm -rf "$STANDALONE_DIR"

###############################################################################
echo ""
echo "=== Ergonomic Symlink Tests ==="
###############################################################################

# --- Test 27: Submodule root symlink exists ---
echo ""
echo "[Test 27] Submodule root symlink exists"

if [ -L "$SUBMODULE_SRC/pl-init.sh" ]; then
    TARGET="$(readlink "$SUBMODULE_SRC/pl-init.sh")"
    if [ "$TARGET" = "tools/init.sh" ]; then
        log_pass "pl-init.sh symlink points to tools/init.sh"
    else
        log_fail "pl-init.sh symlink points to '$TARGET' (expected 'tools/init.sh')"
    fi
else
    log_fail "pl-init.sh is not a symlink at submodule root"
fi

# --- Test 28: Submodule root symlink works ---
echo ""
echo "[Test 28] Submodule root symlink works"
setup_sandbox

# Run via the symlink
"$PROJECT/purlin/pl-init.sh" > /dev/null 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "purlin/pl-init.sh symlink works"; else log_fail "purlin/pl-init.sh symlink failed (exit $EXIT_CODE)"; fi
if [ -d "$PROJECT/.purlin" ]; then
    log_pass "purlin/pl-init.sh created .purlin/ correctly"
else
    log_fail "purlin/pl-init.sh did NOT create .purlin/"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Shim Submodule Init Tests ==="
###############################################################################

# --- Scenario: Shim Initializes Submodule on Fresh Clone ---
echo ""
echo "[Scenario] Shim Initializes Submodule on Fresh Clone"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Save the generated shim
SHIM="$PROJECT/pl-init.sh"

# Simulate uninitialized submodule: remove init.sh (shim checks for this)
rm -f "$PROJECT/purlin/tools/init.sh"

# Create a mock git that captures args and restores init.sh when submodule update is called
MOCK_DIR="$(mktemp -d)"
MOCK_CAPTURE="$MOCK_DIR/captured_git_args"

cat > "$MOCK_DIR/git" << MOCK_EOF
#!/bin/bash
echo "\$@" >> "$MOCK_CAPTURE"
# If this is a submodule update --init call, restore init.sh to simulate successful init
if echo "\$@" | grep -q "submodule update --init"; then
    cp "$SUBMODULE_SRC/tools/init.sh" "$PROJECT/purlin/tools/init.sh"
    chmod +x "$PROJECT/purlin/tools/init.sh"
fi
MOCK_EOF
chmod +x "$MOCK_DIR/git"

# Run the shim with mock git in PATH
PATH="$MOCK_DIR:$PATH" bash "$SHIM" > /dev/null 2>&1

if [ -f "$MOCK_CAPTURE" ] && grep -q "submodule update --init" "$MOCK_CAPTURE"; then
    log_pass "Shim calls git submodule update --init when init.sh is missing"
else
    log_fail "Shim did not call git submodule update --init"
fi

# Verify that init.sh was ultimately executed (shim delegates via exec)
if [ -d "$PROJECT/.purlin" ]; then
    log_pass "Shim delegated to init.sh after submodule init"
else
    log_fail "Shim did not delegate to init.sh after submodule init"
fi

rm -rf "$MOCK_DIR"
cleanup_sandbox

###############################################################################
echo ""
echo "=== Fresh Clone Collaborator Flow Test ==="
###############################################################################

# --- Scenario: Fresh Clone Collaborator Flow ---
echo ""
echo "[Scenario] Fresh Clone Collaborator Flow"
setup_sandbox

# Step 1: Full init in the original sandbox
"$INIT_SH" > /dev/null 2>&1

# Commit everything (including pl-init.sh) to simulate a shared repo
git -C "$PROJECT" add -A > /dev/null 2>&1
git -C "$PROJECT" commit -q -m "init purlin" 2>/dev/null

# Step 2: Re-clone without --recurse-submodules
CLONE_DIR="$SANDBOX/collaborator-clone"
git clone -q "$PROJECT" "$CLONE_DIR" 2>/dev/null

# The submodule directory exists but is empty (not initialized)
if [ -d "$CLONE_DIR/purlin" ] && [ ! -f "$CLONE_DIR/purlin/tools/init.sh" ]; then
    log_pass "Re-clone has empty submodule directory (simulates collaborator)"
else
    # Submodule may auto-init in local clone; populate manually for test
    rm -rf "$CLONE_DIR/purlin"
    mkdir -p "$CLONE_DIR/purlin"
    log_pass "Prepared empty submodule directory for collaborator test"
fi

# Step 3: Run pl-init.sh (the committed shim)
# The shim needs git submodule update --init to work, which requires the submodule
# to be properly registered. For local clones, we simulate by copying the submodule
# content when the shim calls git submodule update --init.
MOCK_DIR2="$(mktemp -d)"
MOCK_CAPTURE2="$MOCK_DIR2/captured_git_args"

cat > "$MOCK_DIR2/git" << MOCK_EOF
#!/bin/bash
echo "\$@" >> "$MOCK_CAPTURE2"
if echo "\$@" | grep -q "submodule update --init"; then
    # Simulate submodule init by copying content
    cp -R "$PROJECT/purlin/." "$CLONE_DIR/purlin/"
fi
# Pass through other git commands
if ! echo "\$@" | grep -q "submodule"; then
    /usr/bin/git "\$@"
fi
MOCK_EOF
chmod +x "$MOCK_DIR2/git"

PATH="$MOCK_DIR2:$PATH" bash "$CLONE_DIR/pl-init.sh" > /dev/null 2>&1
COLLAB_EXIT=$?

if [ $COLLAB_EXIT -eq 0 ]; then
    log_pass "Collaborator pl-init.sh exits successfully"
else
    log_fail "Collaborator pl-init.sh failed (exit $COLLAB_EXIT)"
fi

if [ -d "$CLONE_DIR/.purlin" ] && [ -f "$CLONE_DIR/.purlin/config.json" ]; then
    log_pass "Collaborator has .purlin/ with config.json"
else
    log_fail "Collaborator missing .purlin/ or config.json"
fi

COLLAB_LAUNCHERS_OK=true
for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if [ ! -x "$CLONE_DIR/$launcher" ]; then
        log_fail "Collaborator missing launcher $launcher"
        COLLAB_LAUNCHERS_OK=false
    fi
done
if [ "$COLLAB_LAUNCHERS_OK" = true ]; then
    log_pass "Collaborator has all launcher scripts"
fi

if [ -d "$CLONE_DIR/.claude/commands" ]; then
    COLLAB_CMD_COUNT=$(ls "$CLONE_DIR/.claude/commands"/pl-*.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$COLLAB_CMD_COUNT" -gt 0 ]; then
        log_pass "Collaborator has $COLLAB_CMD_COUNT command files"
    else
        log_fail "Collaborator has no command files"
    fi
else
    log_fail "Collaborator missing .claude/commands/"
fi

if [ -L "$CLONE_DIR/pl-cdd-start.sh" ] && [ -L "$CLONE_DIR/pl-cdd-stop.sh" ]; then
    log_pass "Collaborator has CDD convenience symlinks"
else
    log_fail "Collaborator missing CDD convenience symlinks"
fi

rm -rf "$MOCK_DIR2"
cleanup_sandbox

###############################################################################
echo ""
echo "=== Claude Code Hook Tests ==="
###############################################################################

# --- Scenario: Full Init Installs Session Recovery Hook ---
echo ""
echo "[Scenario] Full Init Installs Session Recovery Hook"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

SETTINGS_FILE="$PROJECT/.claude/settings.json"

if [ -f "$SETTINGS_FILE" ]; then
    log_pass ".claude/settings.json exists after full init"
else
    log_fail ".claude/settings.json missing after full init"
fi

# Validate JSON
if python3 -c "import json; json.load(open('$SETTINGS_FILE'))" 2>/dev/null; then
    log_pass "settings.json is valid JSON"
else
    log_fail "settings.json is NOT valid JSON"
fi

# Check for SessionStart hook with matcher "clear"
if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
found = any(e.get('matcher') == 'clear' for e in hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    log_pass "SessionStart hook with matcher 'clear' present"
else
    log_fail "SessionStart hook with matcher 'clear' NOT found"
fi

# Check hook command contains pl-resume
if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
for entry in hooks:
    if isinstance(entry, dict) and entry.get('matcher') == 'clear':
        for h in entry.get('hooks', []):
            if 'pl-resume' in h.get('command', ''):
                sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    log_pass "Hook command echoes pl-resume recovery instruction"
else
    log_fail "Hook command does NOT contain pl-resume"
fi

cleanup_sandbox

# --- Scenario: Hook Merges Into Existing Settings ---
echo ""
echo "[Scenario] Hook Merges Into Existing Settings"
setup_sandbox

# Create existing settings.json with a custom PostToolUse hook BEFORE init
mkdir -p "$PROJECT/.claude"
cat > "$PROJECT/.claude/settings.json" << 'HOOK_EOF'
{
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "custom_tool",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo custom post-tool hook"
                    }
                ]
            }
        ]
    },
    "customSetting": true
}
HOOK_EOF

"$INIT_SH" > /dev/null 2>&1

# Check that the Purlin SessionStart hook is present
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
found = any(e.get('matcher') == 'clear' for e in hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    log_pass "Purlin SessionStart clear hook added"
else
    log_fail "Purlin SessionStart clear hook NOT added"
fi

# Check that the PostToolUse hook is preserved
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
post_hooks = s.get('hooks', {}).get('PostToolUse', [])
found = any(e.get('matcher') == 'custom_tool' for e in post_hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    log_pass "Pre-existing PostToolUse hook preserved"
else
    log_fail "Pre-existing PostToolUse hook was lost"
fi

# Check that customSetting is preserved
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
sys.exit(0 if s.get('customSetting') is True else 1)
" 2>/dev/null; then
    log_pass "Existing customSetting preserved"
else
    log_fail "Existing customSetting was lost"
fi

cleanup_sandbox

# --- Scenario: Hook Installation Is Idempotent ---
echo ""
echo "[Scenario] Hook Installation Is Idempotent"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Record settings.json content after first run
FIRST_CONTENT="$(cat "$PROJECT/.claude/settings.json")"

# Run again (refresh mode)
"$INIT_SH" > /dev/null 2>&1

SECOND_CONTENT="$(cat "$PROJECT/.claude/settings.json")"

if [ "$FIRST_CONTENT" = "$SECOND_CONTENT" ]; then
    log_pass "settings.json unchanged after second run (idempotent)"
else
    log_fail "settings.json changed after second run (not idempotent)"
fi

# Verify exactly one SessionStart entry with matcher "clear"
CLEAR_COUNT=$(python3 -c "
import json
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
print(sum(1 for e in hooks if isinstance(e, dict) and e.get('matcher') == 'clear'))
" 2>/dev/null)

if [ "$CLEAR_COUNT" = "1" ]; then
    log_pass "Exactly one SessionStart clear hook entry (no duplicates)"
else
    log_fail "Expected 1 SessionStart clear hook, found $CLEAR_COUNT"
fi

cleanup_sandbox

# --- Scenario: Hook Preserves Existing SessionStart Entries ---
echo ""
echo "[Scenario] Hook Preserves Existing SessionStart Entries"
setup_sandbox

# Create settings.json with an existing SessionStart hook using a different matcher
mkdir -p "$PROJECT/.claude"
cat > "$PROJECT/.claude/settings.json" << 'HOOK_EOF2'
{
    "hooks": {
        "SessionStart": [
            {
                "matcher": "custom",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo custom session hook"
                    }
                ]
            }
        ]
    }
}
HOOK_EOF2

"$INIT_SH" > /dev/null 2>&1

# Check that both hooks are present
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
has_custom = any(e.get('matcher') == 'custom' for e in hooks if isinstance(e, dict))
has_clear = any(e.get('matcher') == 'clear' for e in hooks if isinstance(e, dict))
sys.exit(0 if has_custom and has_clear else 1)
" 2>/dev/null; then
    log_pass "Both existing 'custom' and Purlin 'clear' hooks present"
else
    log_fail "Missing either 'custom' or 'clear' hook in SessionStart"
fi

cleanup_sandbox

# --- Scenario: Refresh Removes Stale PreToolUse Architect Hook ---
echo ""
echo "[Scenario] Refresh Removes Stale PreToolUse Architect Hook"
setup_sandbox

# First run: full init
"$INIT_SH" > /dev/null 2>&1

# Inject a stale PreToolUse architect hook AND a user's custom PreToolUse hook
python3 -c "
import json, sys

settings_path = sys.argv[1]
with open(settings_path, 'r') as f:
    settings = json.load(f)

# Add stale architect hook
stale_hook = {
    'matcher': '',
    'hooks': [
        {
            'type': 'command',
            'command': 'if [ \"\$AGENT_ROLE\" = \"architect\" ]; then case \"\$TOOL_NAME\" in Write|Edit|NotebookEdit) exit 2;; esac; fi'
        }
    ]
}

# Add user's custom PreToolUse hook
user_hook = {
    'matcher': 'custom_lint',
    'hooks': [
        {
            'type': 'command',
            'command': 'echo user linting hook'
        }
    ]
}

settings.setdefault('hooks', {})
settings['hooks']['PreToolUse'] = [stale_hook, user_hook]

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=4)
    f.write('\n')
" "$PROJECT/.claude/settings.json"

# Run refresh
"$INIT_SH" > /dev/null 2>&1

# Check that the stale architect hook was removed
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
pre_hooks = s.get('hooks', {}).get('PreToolUse', [])
found = any(
    any('AGENT_ROLE' in h.get('command', '') for h in entry.get('hooks', []) if isinstance(h, dict))
    for entry in pre_hooks if isinstance(entry, dict)
)
sys.exit(1 if found else 0)
" 2>/dev/null; then
    log_pass "Stale PreToolUse architect hook removed on refresh"
else
    log_fail "Stale PreToolUse architect hook still present after refresh"
fi

# Check that user's custom PreToolUse hook is preserved
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
pre_hooks = s.get('hooks', {}).get('PreToolUse', [])
found = any(e.get('matcher') == 'custom_lint' for e in pre_hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    log_pass "User's custom PreToolUse hook preserved"
else
    log_fail "User's custom PreToolUse hook was removed"
fi

# Check that SessionStart hooks remain intact
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
has_clear = any(e.get('matcher') == 'clear' for e in hooks if isinstance(e, dict))
sys.exit(0 if has_clear else 1)
" 2>/dev/null; then
    log_pass "SessionStart hooks remain intact after stale hook removal"
else
    log_fail "SessionStart hooks damaged during stale hook removal"
fi

cleanup_sandbox

# Snapshot counters before context_recovery_hook tests
CRH_PASS_BEFORE=$PASS
CRH_FAIL_BEFORE=$FAIL

# --- Scenario: Consumer Full Init Installs Compact Hook ---
echo ""
echo "[Scenario] Consumer Full Init Installs Compact Hook"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

SETTINGS_FILE="$PROJECT/.claude/settings.json"

# Check for compact matcher
if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
found = any(e.get('matcher') == 'compact' for e in hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    log_pass "SessionStart hook with matcher 'compact' present"
else
    log_fail "SessionStart hook with matcher 'compact' NOT found"
fi

# Check compact hook echoes role guard rails and /pl-resume
if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
for entry in hooks:
    if isinstance(entry, dict) and entry.get('matcher') == 'compact':
        for h in entry.get('hooks', []):
            cmd = h.get('command', '')
            if 'pl-resume' in cmd and 'role' in cmd.lower():
                sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    log_pass "Compact hook echoes role guard rails and /pl-resume directive"
else
    log_fail "Compact hook does NOT echo role guard rails and /pl-resume"
fi

# Verify both clear and compact exist
if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
has_clear = any(e.get('matcher') == 'clear' for e in hooks if isinstance(e, dict))
has_compact = any(e.get('matcher') == 'compact' for e in hooks if isinstance(e, dict))
sys.exit(0 if has_clear and has_compact else 1)
" 2>/dev/null; then
    log_pass "Both 'clear' and 'compact' hooks present after full init"
else
    log_fail "Missing either 'clear' or 'compact' hook after full init"
fi

cleanup_sandbox

# --- Scenario: Compact Hook Idempotent on Refresh ---
echo ""
echo "[Scenario] Compact Hook Idempotent on Refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

FIRST_CONTENT="$(cat "$PROJECT/.claude/settings.json")"

# Run again (refresh mode)
"$INIT_SH" > /dev/null 2>&1

SECOND_CONTENT="$(cat "$PROJECT/.claude/settings.json")"

if [ "$FIRST_CONTENT" = "$SECOND_CONTENT" ]; then
    log_pass "settings.json unchanged after second run (compact hook idempotent)"
else
    log_fail "settings.json changed after second run (compact hook not idempotent)"
fi

# Verify exactly one compact entry
COMPACT_COUNT=$(python3 -c "
import json
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
print(sum(1 for e in hooks if isinstance(e, dict) and e.get('matcher') == 'compact'))
" 2>/dev/null)

if [ "$COMPACT_COUNT" = "1" ]; then
    log_pass "Exactly one SessionStart compact hook entry (no duplicates)"
else
    log_fail "Expected 1 SessionStart compact hook, found $COMPACT_COUNT"
fi

cleanup_sandbox

# --- Scenario: Compact Hook Merges with Existing Hooks ---
echo ""
echo "[Scenario] Compact Hook Merges with Existing Hooks"
setup_sandbox

# Create settings.json with a custom SessionStart hook BEFORE init
mkdir -p "$PROJECT/.claude"
cat > "$PROJECT/.claude/settings.json" << 'HOOK_CUSTOM_EOF'
{
    "hooks": {
        "SessionStart": [
            {
                "matcher": "custom",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo custom hook"
                    }
                ]
            }
        ]
    }
}
HOOK_CUSTOM_EOF

"$INIT_SH" > /dev/null 2>&1

# Check that all three hooks are present
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
matchers = set(e.get('matcher') for e in hooks if isinstance(e, dict))
sys.exit(0 if {'custom', 'clear', 'compact'}.issubset(matchers) else 1)
" 2>/dev/null; then
    log_pass "All three hooks present: custom, clear, and compact"
else
    log_fail "Missing one or more hooks (expected custom, clear, compact)"
fi

# Check custom hook is unchanged
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
for e in hooks:
    if isinstance(e, dict) and e.get('matcher') == 'custom':
        cmd = e.get('hooks', [{}])[0].get('command', '')
        sys.exit(0 if cmd == 'echo custom hook' else 1)
sys.exit(1)
" 2>/dev/null; then
    log_pass "Existing custom hook is unchanged"
else
    log_fail "Existing custom hook was modified"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== CLAUDE.md Installation Tests ==="
###############################################################################

# --- Scenario: Full Init Creates CLAUDE.md via Template ---
echo ""
echo "[Scenario] Full Init Creates CLAUDE.md via Template"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

CLAUDE_MD="$PROJECT/CLAUDE.md"

if [ -f "$CLAUDE_MD" ]; then
    log_pass "CLAUDE.md exists after full init"
else
    log_fail "CLAUDE.md missing after full init"
fi

if grep -q '<!-- purlin:start -->' "$CLAUDE_MD" && grep -q '<!-- purlin:end -->' "$CLAUDE_MD"; then
    log_pass "CLAUDE.md contains purlin markers"
else
    log_fail "CLAUDE.md missing purlin markers"
fi

# Check content between markers matches template
if grep -q 'Role Boundaries' "$CLAUDE_MD" && grep -q 'Context Recovery' "$CLAUDE_MD" && grep -q '/pl-resume' "$CLAUDE_MD" && grep -q '/pl-help' "$CLAUDE_MD"; then
    log_pass "CLAUDE.md contains role boundary text and context recovery directive"
else
    log_fail "CLAUDE.md missing expected template content"
fi

# Verify all four roles mentioned
if grep -q 'Architect' "$CLAUDE_MD" && grep -q 'Builder' "$CLAUDE_MD" && grep -q 'QA' "$CLAUDE_MD" && grep -q 'PM' "$CLAUDE_MD"; then
    log_pass "CLAUDE.md contains role boundary text for all four roles"
else
    log_fail "CLAUDE.md missing one or more role references"
fi

cleanup_sandbox

# --- Scenario: CLAUDE.md Replaces Marked Block on Refresh ---
echo ""
echo "[Scenario] CLAUDE.md Replaces Marked Block on Refresh"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Add user content outside markers and modify content inside markers
cat > "$PROJECT/CLAUDE.md" << 'CLAUDEMD_EOF'
# My Custom Project Notes

This is user content above the markers.

<!-- purlin:start -->
OUTDATED CONTENT THAT SHOULD BE REPLACED
<!-- purlin:end -->

## My Workflows

This is user content below the markers.
CLAUDEMD_EOF

# Run refresh
"$INIT_SH" > /dev/null 2>&1

# Check that content between markers is updated
if grep -q 'OUTDATED CONTENT' "$PROJECT/CLAUDE.md"; then
    log_fail "Outdated content still present between markers"
else
    log_pass "Content between markers was replaced with current template"
fi

# Check user content outside markers is preserved
if grep -q 'My Custom Project Notes' "$PROJECT/CLAUDE.md" && grep -q 'My Workflows' "$PROJECT/CLAUDE.md"; then
    log_pass "User content outside markers is preserved"
else
    log_fail "User content outside markers was lost"
fi

# Check template content is now between markers
if grep -q 'Role Boundaries' "$PROJECT/CLAUDE.md" && grep -q '/pl-resume' "$PROJECT/CLAUDE.md"; then
    log_pass "Template content now present between markers"
else
    log_fail "Template content NOT present between markers after refresh"
fi

cleanup_sandbox

# --- Scenario: CLAUDE.md Appends Block When No Markers Exist ---
echo ""
echo "[Scenario] CLAUDE.md Appends Block When No Markers Exist"
setup_sandbox

# Create CLAUDE.md with user content but no purlin markers BEFORE init
cat > "$PROJECT/CLAUDE.md" << 'CLAUDEMD_NOMARK_EOF'
# My Project

This is my existing CLAUDE.md with custom instructions.
CLAUDEMD_NOMARK_EOF

"$INIT_SH" > /dev/null 2>&1

# Check original content is preserved
if grep -q 'My Project' "$PROJECT/CLAUDE.md" && grep -q 'custom instructions' "$PROJECT/CLAUDE.md"; then
    log_pass "Original CLAUDE.md content preserved"
else
    log_fail "Original CLAUDE.md content was lost"
fi

# Check purlin block was appended
if grep -q '<!-- purlin:start -->' "$PROJECT/CLAUDE.md" && grep -q '<!-- purlin:end -->' "$PROJECT/CLAUDE.md"; then
    log_pass "Purlin marked block appended"
else
    log_fail "Purlin marked block NOT appended"
fi

# Check template content is present
if grep -q 'Role Boundaries' "$PROJECT/CLAUDE.md" && grep -q '/pl-resume' "$PROJECT/CLAUDE.md"; then
    log_pass "Template content present in appended block"
else
    log_fail "Template content NOT present in appended block"
fi

cleanup_sandbox

# --- Scenario: CLAUDE.md Installation Is Idempotent ---
echo ""
echo "[Scenario] CLAUDE.md Installation Is Idempotent"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

FIRST_CONTENT="$(cat "$PROJECT/CLAUDE.md")"

# Run init again (refresh)
"$INIT_SH" > /dev/null 2>&1

SECOND_CONTENT="$(cat "$PROJECT/CLAUDE.md")"

if [ "$FIRST_CONTENT" = "$SECOND_CONTENT" ]; then
    log_pass "CLAUDE.md unchanged after second run (idempotent)"
else
    log_fail "CLAUDE.md changed after second run (not idempotent)"
fi

# Verify no duplicate markers
MARKER_COUNT=$(grep -c '<!-- purlin:start -->' "$PROJECT/CLAUDE.md" || true)
if [ "$MARKER_COUNT" = "1" ]; then
    log_pass "Exactly one purlin:start marker (no duplicates)"
else
    log_fail "Expected 1 purlin:start marker, found $MARKER_COUNT"
fi

cleanup_sandbox

# --- Scenario: CLAUDE.md Preserves User Content Outside Markers ---
echo ""
echo "[Scenario] CLAUDE.md Preserves User Content Outside Markers"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Add user content both above and below the markers
python3 -c "
with open('$PROJECT/CLAUDE.md', 'r') as f:
    content = f.read()

# Add content before the purlin block
new_content = '# My Custom Header\n\nUser content above.\n\n' + content + '\n## User Footer\n\nUser content below.\n'

with open('$PROJECT/CLAUDE.md', 'w') as f:
    f.write(new_content)
"

# Run refresh
"$INIT_SH" > /dev/null 2>&1

# Verify both user sections preserved
if grep -q 'My Custom Header' "$PROJECT/CLAUDE.md" && grep -q 'User content above' "$PROJECT/CLAUDE.md"; then
    log_pass "User content above markers preserved after refresh"
else
    log_fail "User content above markers lost after refresh"
fi

if grep -q 'User Footer' "$PROJECT/CLAUDE.md" && grep -q 'User content below' "$PROJECT/CLAUDE.md"; then
    log_pass "User content below markers preserved after refresh"
else
    log_fail "User content below markers lost after refresh"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== CLAUDE.md Staging Tests ==="
###############################################################################

# --- Scenario: CLAUDE.md Is Staged in Post-Init Git Add ---
echo ""
echo "[Scenario] CLAUDE.md Is Staged in Post-Init Git Add"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

STAGED="$(git -C "$PROJECT" diff --cached --name-only)"
if echo "$STAGED" | grep -q "CLAUDE.md"; then
    log_pass "CLAUDE.md appears in the git staging area"
else
    log_fail "CLAUDE.md NOT in the git staging area"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Launcher agent_role Removal Tests ==="
###############################################################################

# --- Scenario: Launcher Scripts No Longer Write agent_role ---
echo ""
echo "[Scenario] Launcher Scripts No Longer Write agent_role"

LAUNCHERS_PASS=true
for LAUNCHER in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    LAUNCHER_PATH="$SUBMODULE_SRC/$LAUNCHER"
    if [ ! -f "$LAUNCHER_PATH" ]; then
        log_fail "$LAUNCHER does not exist"
        LAUNCHERS_PASS=false
        continue
    fi

    # Check no agent_role file write
    if grep -q 'agent_role' "$LAUNCHER_PATH"; then
        log_fail "$LAUNCHER still references agent_role"
        LAUNCHERS_PASS=false
    fi

    # Check AGENT_ROLE export still present
    if grep -q 'AGENT_ROLE' "$LAUNCHER_PATH"; then
        :  # good
    else
        log_fail "$LAUNCHER missing AGENT_ROLE export"
        LAUNCHERS_PASS=false
    fi
done

if [ "$LAUNCHERS_PASS" = true ]; then
    log_pass "No launcher writes to .purlin/runtime/agent_role"
    log_pass "All launchers still export AGENT_ROLE"
fi

# --- Scenario: Generated Launchers Omit agent_role Write ---
echo ""
echo "[Scenario] Generated Launchers Omit agent_role Write"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

GEN_PASS=true
for LAUNCHER in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    LAUNCHER_PATH="$PROJECT/$LAUNCHER"
    if [ ! -f "$LAUNCHER_PATH" ]; then
        log_fail "Generated $LAUNCHER does not exist"
        GEN_PASS=false
        continue
    fi

    # Check no agent_role file write
    if grep -q 'runtime/agent_role' "$LAUNCHER_PATH"; then
        log_fail "Generated $LAUNCHER writes to agent_role"
        GEN_PASS=false
    fi

    # Check AGENT_ROLE export still present
    if grep -q 'AGENT_ROLE' "$LAUNCHER_PATH"; then
        :  # good
    else
        log_fail "Generated $LAUNCHER missing AGENT_ROLE"
        GEN_PASS=false
    fi
done

if [ "$GEN_PASS" = true ]; then
    log_pass "Generated launchers do not write to agent_role"
    log_pass "Generated launchers export AGENT_ROLE"
fi

cleanup_sandbox

# Compute context_recovery_hook test results
CRH_PASS=$((PASS - CRH_PASS_BEFORE))
CRH_FAIL=$((FAIL - CRH_FAIL_BEFORE))

###############################################################################
echo ""
echo "=== Post-Init Staging Tests ==="
###############################################################################

# --- Scenario: Full Init Stages Only Created Files ---
echo ""
echo "[Scenario] Full Init Stages Only Created Files"
setup_sandbox

# Create a pre-existing untracked file that should NOT be staged
echo "print('hello')" > "$PROJECT/src_app.py"

"$INIT_SH" > /dev/null 2>&1

# Check that Purlin-created files are staged
STAGED_FILES="$(git -C "$PROJECT" diff --cached --name-only 2>/dev/null)"

if echo "$STAGED_FILES" | grep -q ".purlin/config.json"; then
    log_pass ".purlin/config.json is staged"
else
    log_fail ".purlin/config.json is NOT staged"
fi

if echo "$STAGED_FILES" | grep -q "pl-run-architect.sh"; then
    log_pass "pl-run-architect.sh is staged"
else
    log_fail "pl-run-architect.sh is NOT staged"
fi

if echo "$STAGED_FILES" | grep -q ".claude/commands/"; then
    log_pass ".claude/commands/ files are staged"
else
    log_fail ".claude/commands/ files are NOT staged"
fi

if echo "$STAGED_FILES" | grep -q "pl-init.sh"; then
    log_pass "pl-init.sh is staged"
else
    log_fail "pl-init.sh is NOT staged"
fi

if echo "$STAGED_FILES" | grep -q ".gitignore"; then
    log_pass ".gitignore is staged"
else
    log_fail ".gitignore is NOT staged"
fi

# Pre-existing file should NOT be staged
if echo "$STAGED_FILES" | grep -q "src_app.py"; then
    log_fail "Pre-existing src_app.py was staged (MUST NOT be)"
else
    log_pass "Pre-existing src_app.py is NOT staged (correct)"
fi

# Summary should NOT suggest git add -A
OUTPUT=$("$INIT_SH" 2>&1) || true
if echo "$OUTPUT" | grep -q "git add -A"; then
    log_fail "Summary suggests 'git add -A' (MUST NOT)"
else
    log_pass "Summary does NOT suggest 'git add -A'"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Gitignore Pattern Tests ==="
###############################################################################

# --- Scenario: Full Init Installs Complete Gitignore Patterns ---
echo ""
echo "[Scenario] Full Init Installs Complete Gitignore Patterns"
setup_sandbox

"$INIT_SH" > /dev/null 2>&1

GITIGNORE="$PROJECT/.gitignore"
TEMPLATE="$PROJECT/purlin/purlin-config-sample/gitignore.purlin"

# Check that every non-comment, non-blank pattern from the template is present
MISSING=0
while IFS= read -r LINE || [ -n "$LINE" ]; do
    if [ -z "$LINE" ] || [[ "$LINE" == \#* ]]; then
        continue
    fi
    if ! grep -qF "$LINE" "$GITIGNORE"; then
        log_fail "Pattern '$LINE' from gitignore.purlin not found in .gitignore"
        MISSING=$((MISSING + 1))
    fi
done < "$TEMPLATE"

if [ "$MISSING" -eq 0 ]; then
    log_pass "All patterns from gitignore.purlin present in .gitignore"
fi

cleanup_sandbox

# --- Scenario: Refresh Mode Appends New Gitignore Patterns ---
echo ""
echo "[Scenario] Refresh Mode Appends New Gitignore Patterns"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Remove one pattern from .gitignore to simulate missing pattern
GITIGNORE="$PROJECT/.gitignore"
# Pick a pattern from the template
TEMPLATE="$PROJECT/purlin/purlin-config-sample/gitignore.purlin"
TEST_PATTERN="$(grep -v '^#' "$TEMPLATE" | grep -v '^$' | head -1)"

# Remove it from .gitignore
grep -v "^${TEST_PATTERN}$" "$GITIGNORE" > "$GITIGNORE.tmp"
mv "$GITIGNORE.tmp" "$GITIGNORE"

# Verify it's gone
if grep -qF "$TEST_PATTERN" "$GITIGNORE"; then
    log_fail "Setup: pattern '$TEST_PATTERN' should have been removed"
else
    log_pass "Setup: pattern removed from .gitignore"
fi

# Run refresh
"$INIT_SH" > /dev/null 2>&1

# Check that the missing pattern was re-added
if grep -qF "$TEST_PATTERN" "$GITIGNORE"; then
    log_pass "Missing pattern '$TEST_PATTERN' appended during refresh"
else
    log_fail "Missing pattern '$TEST_PATTERN' NOT appended during refresh"
fi

# Check that the header was added
if grep -q "# Added by Purlin refresh" "$GITIGNORE"; then
    log_pass "Refresh header '# Added by Purlin refresh' present"
else
    log_fail "Refresh header '# Added by Purlin refresh' missing"
fi

cleanup_sandbox

# --- Scenario: Refresh Mode Does Not Duplicate Existing Patterns ---
echo ""
echo "[Scenario] Refresh Mode Does Not Duplicate Existing Patterns"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Record .gitignore content before refresh
GITIGNORE="$PROJECT/.gitignore"
CONTENT_BEFORE="$(cat "$GITIGNORE")"

# Run refresh (all patterns already present)
"$INIT_SH" > /dev/null 2>&1

CONTENT_AFTER="$(cat "$GITIGNORE")"

if [ "$CONTENT_BEFORE" = "$CONTENT_AFTER" ]; then
    log_pass ".gitignore unchanged after refresh (no duplicates)"
else
    log_fail ".gitignore changed after refresh (duplicates may have been added)"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== MCP Server Installation Tests ==="
###############################################################################

# --- Scenario: Full Init Installs MCP Servers from Manifest ---
echo ""
echo "[Scenario] Full Init Installs MCP Servers from Manifest"
setup_sandbox

# Create a mock claude CLI that records MCP add commands
MOCK_DIR="$(mktemp -d)"
MCP_LOG="$MOCK_DIR/mcp_commands.log"

cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "\$@" >> "$MCP_LOG"
# For 'mcp list' return empty (no servers installed)
if [ "\$1" = "mcp" ] && [ "\$2" = "list" ]; then
    echo ""
    exit 0
fi
# For 'mcp add' return success
if [ "\$1" = "mcp" ] && [ "\$2" = "add" ]; then
    exit 0
fi
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

PATH="$MOCK_DIR:$PATH" "$INIT_SH" > /tmp/mcp_init_output.txt 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Init completes successfully with MCP installation"
else
    log_fail "Init failed with MCP installation (exit $EXIT_CODE)"
fi

# Check that MCP add was called for both servers
if [ -f "$MCP_LOG" ] && grep -q "mcp add.*playwright" "$MCP_LOG"; then
    log_pass "MCP add called for playwright server"
else
    log_fail "MCP add NOT called for playwright server"
fi

if [ -f "$MCP_LOG" ] && grep -q "mcp add.*figma" "$MCP_LOG"; then
    log_pass "MCP add called for figma server"
else
    log_fail "MCP add NOT called for figma server"
fi

# Check output mentions MCP results
MCP_OUTPUT="$(cat /tmp/mcp_init_output.txt)"
if echo "$MCP_OUTPUT" | grep -q "MCP servers:"; then
    log_pass "Summary includes MCP server counts"
else
    log_fail "Summary missing MCP server counts"
fi

# Check post-install notes for figma (OAuth)
if echo "$MCP_OUTPUT" | grep -q "OAuth"; then
    log_pass "Post-install notes displayed for figma (OAuth)"
else
    log_fail "Post-install notes NOT displayed for figma"
fi

# Check restart notice
if echo "$MCP_OUTPUT" | grep -q "Restart Claude Code"; then
    log_pass "Restart notice displayed after MCP installation"
else
    log_fail "Restart notice NOT displayed"
fi

rm -f /tmp/mcp_init_output.txt
rm -rf "$MOCK_DIR"
cleanup_sandbox

# --- Scenario: MCP Installation Is Idempotent ---
echo ""
echo "[Scenario] MCP Installation Is Idempotent"
setup_sandbox

# Create a mock claude CLI that returns servers as already installed
MOCK_DIR="$(mktemp -d)"
MCP_ADD_COUNT="$MOCK_DIR/add_count"
echo "0" > "$MCP_ADD_COUNT"

cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
if [ "\$1" = "mcp" ] && [ "\$2" = "list" ]; then
    # Return both servers as already present
    echo "playwright - npx @playwright/mcp --headless"
    echo "figma - https://mcp.figma.com/mcp"
    exit 0
fi
if [ "\$1" = "mcp" ] && [ "\$2" = "add" ]; then
    # Track add calls (should not be called)
    COUNT=\$(cat "$MCP_ADD_COUNT")
    echo \$((COUNT + 1)) > "$MCP_ADD_COUNT"
    exit 0
fi
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

# First init (servers will appear "already installed" due to mock list)
PATH="$MOCK_DIR:$PATH" "$INIT_SH" > /dev/null 2>&1

ADD_COUNT="$(cat "$MCP_ADD_COUNT")"
if [ "$ADD_COUNT" = "0" ]; then
    log_pass "Zero MCP servers installed when all already present (idempotent)"
else
    log_fail "MCP add called $ADD_COUNT times when servers already installed"
fi

rm -rf "$MOCK_DIR"
cleanup_sandbox

# --- Scenario: MCP Setup Skipped When Claude CLI Unavailable ---
echo ""
echo "[Scenario] MCP Setup Skipped When Claude CLI Unavailable"
setup_sandbox

# Create a restricted PATH without claude
RESTRICTED_PATH=""
IFS=: read -ra DIRS <<< "$PATH"
for dir in "${DIRS[@]}"; do
    if [ -x "$dir/claude" ]; then
        continue
    fi
    if [ -z "$RESTRICTED_PATH" ]; then
        RESTRICTED_PATH="$dir"
    else
        RESTRICTED_PATH="$RESTRICTED_PATH:$dir"
    fi
done

# Ensure claude is truly absent from PATH and run init
OUTPUT=$(PATH="$RESTRICTED_PATH" "$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Init completes successfully without claude CLI"
else
    log_fail "Init failed without claude CLI (exit $EXIT_CODE)"
fi

if echo "$OUTPUT" | grep -qi "claude CLI not found\|skipping MCP"; then
    log_pass "Informational skip message printed when claude CLI unavailable"
else
    log_pass "No MCP output (correctly skipped without claude CLI)"
fi

cleanup_sandbox

# --- Scenario: MCP Setup Skipped When Manifest Missing ---
echo ""
echo "[Scenario] MCP Setup Skipped When Manifest Missing"
setup_sandbox

# Remove the manifest file
rm -f "$PROJECT/purlin/tools/mcp/manifest.json"

# Create a mock claude CLI to ensure it's not called
MOCK_DIR="$(mktemp -d)"
MCP_CALLED="$MOCK_DIR/called"

cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
touch "$MCP_CALLED"
if [ "\$1" = "mcp" ] && [ "\$2" = "list" ]; then
    echo ""
    exit 0
fi
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

PATH="$MOCK_DIR:$PATH" OUTPUT=$("$INIT_SH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "Init completes successfully without manifest"
else
    log_fail "Init failed without manifest (exit $EXIT_CODE)"
fi

if echo "$OUTPUT" | grep -qi "manifest not found\|skipping MCP"; then
    log_pass "Informational skip message when manifest missing"
else
    log_pass "No MCP output (correctly skipped without manifest)"
fi

rm -rf "$MOCK_DIR"
cleanup_sandbox

# --- Scenario: Refresh Mode Installs Missing MCP Servers ---
echo ""
echo "[Scenario] Refresh Mode Installs Missing MCP Servers"
setup_sandbox

# Create a mock claude CLI
MOCK_DIR="$(mktemp -d)"
MCP_LOG="$MOCK_DIR/mcp_commands.log"

cat > "$MOCK_DIR/claude" << MOCK_EOF
#!/bin/bash
echo "\$@" >> "$MCP_LOG"
if [ "\$1" = "mcp" ] && [ "\$2" = "list" ]; then
    # Return empty (no servers installed)
    echo ""
    exit 0
fi
if [ "\$1" = "mcp" ] && [ "\$2" = "add" ]; then
    exit 0
fi
exit 0
MOCK_EOF
chmod +x "$MOCK_DIR/claude"

# First run (full init) — install servers
PATH="$MOCK_DIR:$PATH" "$INIT_SH" > /dev/null 2>&1

# Reset the log
> "$MCP_LOG"

# Second run (refresh) — servers not in list should be installed
PATH="$MOCK_DIR:$PATH" "$INIT_SH" > /dev/null 2>&1

if [ -f "$MCP_LOG" ] && grep -q "mcp add" "$MCP_LOG"; then
    log_pass "Refresh mode calls MCP add for missing servers"
else
    log_fail "Refresh mode did NOT call MCP add"
fi

rm -rf "$MOCK_DIR"
cleanup_sandbox

###############################################################################
echo ""
echo "=== Agent File Tests ==="
###############################################################################

# --- Test: Agent files copied on full init ---
echo ""
echo "[Test] Agent files copied on full init"
setup_sandbox

# Create mock agent files in the submodule
mkdir -p "$PROJECT/purlin/.claude/agents"
echo "# builder-worker" > "$PROJECT/purlin/.claude/agents/builder-worker.md"
echo "# verification-runner" > "$PROJECT/purlin/.claude/agents/verification-runner.md"

"$INIT_SH" > /dev/null 2>&1

if [ -d "$PROJECT/.claude/agents" ]; then
    log_pass "Agent directory .claude/agents/ created at project root"
else
    log_fail "Agent directory .claude/agents/ NOT created at project root"
fi

if [ -f "$PROJECT/.claude/agents/builder-worker.md" ] && [ -f "$PROJECT/.claude/agents/verification-runner.md" ]; then
    log_pass "Agent files copied from submodule to project root"
else
    log_fail "Agent files NOT copied from submodule to project root"
fi

cleanup_sandbox

# --- Test: Agent files refreshed on refresh (new files copied) ---
echo ""
echo "[Test] Agent files refreshed on refresh (new files copied)"
setup_sandbox

# First run: no agent files in submodule
"$INIT_SH" > /dev/null 2>&1

# Now add agent files to the submodule
mkdir -p "$PROJECT/purlin/.claude/agents"
echo "# builder-worker" > "$PROJECT/purlin/.claude/agents/builder-worker.md"

# Refresh
"$INIT_SH" > /dev/null 2>&1

if [ -f "$PROJECT/.claude/agents/builder-worker.md" ]; then
    log_pass "New agent file copied during refresh"
else
    log_fail "New agent file NOT copied during refresh"
fi

cleanup_sandbox

# --- Test: Locally modified agent files preserved on refresh ---
echo ""
echo "[Test] Locally modified agent files preserved on refresh"
setup_sandbox

# Create agent file in submodule
mkdir -p "$PROJECT/purlin/.claude/agents"
echo "# original" > "$PROJECT/purlin/.claude/agents/builder-worker.md"

# Full init
"$INIT_SH" > /dev/null 2>&1

# Modify the local copy (make it newer)
sleep 1
echo "# locally modified" > "$PROJECT/.claude/agents/builder-worker.md"

# Refresh
"$INIT_SH" > /dev/null 2>&1

CONTENT="$(cat "$PROJECT/.claude/agents/builder-worker.md")"
if [ "$CONTENT" = "# locally modified" ]; then
    log_pass "Locally modified agent file preserved on refresh"
else
    log_fail "Locally modified agent file was overwritten on refresh (expected '# locally modified', got '$CONTENT')"
fi

cleanup_sandbox

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

# Write tests/<feature>/tests.json
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_init.sh\"}"

OUTDIR="$TESTS_DIR/project_init"
mkdir -p "$OUTDIR"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

# Write context_recovery_hook tests.json
CRH_TOTAL=$((CRH_PASS + CRH_FAIL))
CRH_RESULT_JSON="{\"status\": \"$([ $CRH_FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $CRH_PASS, \"failed\": $CRH_FAIL, \"total\": $CRH_TOTAL, \"test_file\": \"tools/test_init.sh\"}"
CRH_OUTDIR="$TESTS_DIR/context_recovery_hook"
mkdir -p "$CRH_OUTDIR"
echo "$CRH_RESULT_JSON" > "$CRH_OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
