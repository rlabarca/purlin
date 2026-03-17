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

if echo "$OUTPUT" | grep -q "Purlin initialized"; then
    log_pass "Output contains 'Purlin initialized'"
else
    log_fail "Output missing 'Purlin initialized'"
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

# Create existing settings.json with a custom PreToolUse hook BEFORE init
mkdir -p "$PROJECT/.claude"
cat > "$PROJECT/.claude/settings.json" << 'HOOK_EOF'
{
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "custom_tool",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo custom pre-tool hook"
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

# Check that the PreToolUse hook is preserved
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
pre_hooks = s.get('hooks', {}).get('PreToolUse', [])
found = any(e.get('matcher') == 'custom_tool' for e in pre_hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    log_pass "Pre-existing PreToolUse hook preserved"
else
    log_fail "Pre-existing PreToolUse hook was lost"
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

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
