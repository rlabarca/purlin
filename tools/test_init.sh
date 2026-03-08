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

for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh; do
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

for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh; do
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
echo "[Test 10] Shim contains metadata"
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

# --- Scenario: Missing Launchers Created on Refresh Without Flag ---
echo ""
echo "[Scenario] Missing Launchers Created on Refresh Without Flag"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Record builder launcher checksum before deletion
BUILDER_HASH_BEFORE="$(shasum "$PROJECT/pl-run-builder.sh" | cut -d' ' -f1)"

# Delete one launcher to simulate upgrade/rename
rm -f "$PROJECT/pl-run-architect.sh"

"$INIT_SH" > /dev/null 2>&1

if [ -x "$PROJECT/pl-run-architect.sh" ]; then
    log_pass "Missing pl-run-architect.sh recreated on refresh"
else
    log_fail "Missing pl-run-architect.sh NOT recreated on refresh"
fi

BUILDER_HASH_AFTER="$(shasum "$PROJECT/pl-run-builder.sh" | cut -d' ' -f1)"
if [ "$BUILDER_HASH_BEFORE" = "$BUILDER_HASH_AFTER" ]; then
    log_pass "Existing pl-run-builder.sh NOT modified"
else
    log_fail "Existing pl-run-builder.sh was modified during launcher repair"
fi

# Verify the recreated launcher is functional (exports PURLIN_PROJECT_ROOT)
if grep -q 'export PURLIN_PROJECT_ROOT=' "$PROJECT/pl-run-architect.sh"; then
    log_pass "Recreated launcher exports PURLIN_PROJECT_ROOT"
else
    log_fail "Recreated launcher missing PURLIN_PROJECT_ROOT export"
fi

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

# --- Scenario: --regenerate-launchers Flag ---
echo ""
echo "[Scenario] --regenerate-launchers Flag"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Modify pl-run-architect.sh
echo "# MODIFIED BY TEST" > "$PROJECT/pl-run-architect.sh"

"$INIT_SH" --regenerate-launchers > /dev/null 2>&1

if grep -q "PURLIN_PROJECT_ROOT" "$PROJECT/pl-run-architect.sh"; then
    log_pass "--regenerate-launchers overwrote pl-run-architect.sh"
else
    log_fail "--regenerate-launchers did NOT overwrite pl-run-architect.sh"
fi

cleanup_sandbox

# --- Scenario: --regenerate-launchers Removes Stale Launchers ---
echo ""
echo "[Scenario] --regenerate-launchers Removes Stale Launchers"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Create stale launchers with old naming convention
echo "#!/bin/bash" > "$PROJECT/run_architect.sh"
echo "#!/bin/bash" > "$PROJECT/run_builder.sh"
echo "#!/bin/bash" > "$PROJECT/run_qa.sh"

"$INIT_SH" --regenerate-launchers > /dev/null 2>&1

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
for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh; do
    if [ ! -x "$PROJECT/$launcher" ]; then
        log_fail "New-style launcher $launcher missing after --regenerate-launchers"
        NEW_STYLE_OK=false
    fi
done
if [ "$NEW_STYLE_OK" = true ]; then
    log_pass "All new-style launchers (pl-run-*.sh) present"
fi

cleanup_sandbox

# --- Test 26: Refresh without --regenerate-launchers preserves launchers ---
echo ""
echo "[Test 26] Refresh without --regenerate-launchers preserves launchers"
setup_sandbox
"$INIT_SH" > /dev/null 2>&1

# Modify pl-run-architect.sh
echo "# MODIFIED BY TEST" > "$PROJECT/pl-run-architect.sh"

"$INIT_SH" > /dev/null 2>&1

if grep -q "MODIFIED BY TEST" "$PROJECT/pl-run-architect.sh"; then
    log_pass "Launcher preserved without --regenerate-launchers"
else
    log_fail "Launcher overwritten without --regenerate-launchers flag"
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
