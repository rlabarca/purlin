#!/bin/bash
# test_init.sh — Unit tests for tools/init.sh (Project Init)
# Covers the fast, structural assertions listed under ### Unit Tests in
# features/project_init.md Section 3. Behavioral integration tests
# (refresh mode, idempotency, MCP, etc.) are QA-owned regression tests.
#
# Produces tests/project_init/tests.json and tests/context_recovery_hook/tests.json.
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
crh_pass() { CRH_PASS=$((CRH_PASS + 1)); echo "  PASS: [CRH] $1"; }
crh_fail() { CRH_FAIL=$((CRH_FAIL + 1)); echo "  FAIL: [CRH] $1"; }

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
        mkdir -p "$PROJECT/purlin/purlin-config-sample"
        cp "$SUBMODULE_SRC/purlin-config-sample/CLAUDE.md.purlin" "$PROJECT/purlin/purlin-config-sample/CLAUDE.md.purlin"
    fi
    # Copy gitignore template
    if [ -f "$SUBMODULE_SRC/purlin-config-sample/gitignore.purlin" ]; then
        mkdir -p "$PROJECT/purlin/purlin-config-sample"
        cp "$SUBMODULE_SRC/purlin-config-sample/gitignore.purlin" "$PROJECT/purlin/purlin-config-sample/gitignore.purlin"
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
echo "=== Unit Tests: project_init ==="
echo ""
echo "Setting up single sandbox for all init assertions..."
###############################################################################

setup_sandbox

# Pre-create an untracked file for the staging test (Scenario 5)
echo "print('hello')" > "$PROJECT/src_app.py"

# Remove claude from PATH so MCP installation doesn't run
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

# Run init ONCE (all assertions check the result)
OUTPUT=$(PATH="$RESTRICTED_PATH" "$INIT_SH" 2>&1)
INIT_EXIT=$?

###############################################################################
echo ""
echo "[Scenario] Full Init Creates All Artifacts"
###############################################################################

if [ $INIT_EXIT -eq 0 ]; then log_pass "Exit code 0"; else log_fail "Exit code was $INIT_EXIT (expected 0)"; fi

# .purlin/ with config, overrides, .upstream_sha
if [ -d "$PROJECT/.purlin" ]; then log_pass ".purlin/ created"; else log_fail ".purlin/ not created"; fi
if [ -f "$PROJECT/.purlin/config.json" ]; then log_pass "config.json exists"; else log_fail "config.json missing"; fi
if [ -f "$PROJECT/.purlin/ARCHITECT_OVERRIDES.md" ]; then log_pass "ARCHITECT_OVERRIDES.md exists"; else log_fail "ARCHITECT_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/BUILDER_OVERRIDES.md" ]; then log_pass "BUILDER_OVERRIDES.md exists"; else log_fail "BUILDER_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/QA_OVERRIDES.md" ]; then log_pass "QA_OVERRIDES.md exists"; else log_fail "QA_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then log_pass "HOW_WE_WORK_OVERRIDES.md exists"; else log_fail "HOW_WE_WORK_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/.upstream_sha" ]; then log_pass ".upstream_sha exists"; else log_fail ".upstream_sha missing"; fi

# Config JSON validity and correct tools_root
if python3 -c "import json; json.load(open('$PROJECT/.purlin/config.json'))" 2>/dev/null; then
    log_pass "config.json is valid JSON"
else
    log_fail "config.json is NOT valid JSON"
fi
if grep -q '"tools_root": "purlin/tools"' "$PROJECT/.purlin/config.json"; then
    log_pass "tools_root set to purlin/tools"
else
    log_fail "tools_root incorrect: $(grep tools_root "$PROJECT/.purlin/config.json")"
fi

# Launcher scripts exist and are executable
for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if [ -x "$PROJECT/$launcher" ]; then
        log_pass "$launcher exists and is executable"
    else
        log_fail "$launcher missing or not executable"
    fi
done

# Launcher scripts export PURLIN_PROJECT_ROOT
for launcher in pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh; do
    if grep -q 'export PURLIN_PROJECT_ROOT=' "$PROJECT/$launcher"; then
        log_pass "$launcher exports PURLIN_PROJECT_ROOT"
    else
        log_fail "$launcher does NOT export PURLIN_PROJECT_ROOT"
    fi
done

# Command files copied (excluding pl-edit-base.md)
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

# pl-edit-base.md excluded
mkdir -p "$PROJECT/purlin/.claude/commands"
echo "# MUST NOT be distributed" > "$PROJECT/purlin/.claude/commands/pl-edit-base.md"
# We already ran init, but check the exclusion from the first run
if [ -f "$PROJECT/.claude/commands/pl-edit-base.md" ]; then
    log_fail "pl-edit-base.md was copied (MUST NOT be)"
else
    log_pass "pl-edit-base.md correctly excluded"
fi

# features/ directory
if [ -d "$PROJECT/features" ]; then
    log_pass "features/ directory exists"
else
    log_fail "features/ directory missing"
fi

# pl-init.sh shim exists and is executable
if [ -x "$PROJECT/pl-init.sh" ]; then
    log_pass "pl-init.sh exists and is executable"
else
    log_fail "pl-init.sh missing or not executable"
fi

###############################################################################
echo ""
echo "[Scenario] Full Init Creates CDD Convenience Symlinks"
###############################################################################

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

# Symlinks use relative paths
START_TARGET="$(readlink "$PROJECT/pl-cdd-start.sh" 2>/dev/null || true)"
STOP_TARGET="$(readlink "$PROJECT/pl-cdd-stop.sh" 2>/dev/null || true)"

if [ -n "$START_TARGET" ] && [[ "$START_TARGET" != /* ]]; then
    log_pass "pl-cdd-start.sh uses relative path: $START_TARGET"
else
    log_fail "pl-cdd-start.sh uses absolute path or missing: $START_TARGET"
fi
if [ -n "$STOP_TARGET" ] && [[ "$STOP_TARGET" != /* ]]; then
    log_pass "pl-cdd-stop.sh uses relative path: $STOP_TARGET"
else
    log_fail "pl-cdd-stop.sh uses absolute path or missing: $STOP_TARGET"
fi

###############################################################################
echo ""
echo "[Scenario] Shim Contains Repo URL, SHA, and Version"
###############################################################################

SHIM_CONTENT="$(cat "$PROJECT/pl-init.sh")"
EXPECTED_SHA="$(git -C "$PROJECT/purlin" rev-parse HEAD)"

if echo "$SHIM_CONTENT" | grep -q "Repo:"; then
    log_pass "Shim contains Repo field"
else
    log_fail "Shim missing Repo field"
fi
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

###############################################################################
echo ""
echo "[Scenario] Full Init Copies Agent Files"
###############################################################################

if [ -d "$PROJECT/.claude/agents" ]; then
    log_pass ".claude/agents/ directory exists"
else
    log_fail ".claude/agents/ directory missing"
fi

# Check for specific agent files from the submodule
AGENT_FILES_FOUND=0
for af in "$PROJECT/.claude/agents/"*.md; do
    if [ -f "$af" ]; then
        AGENT_FILES_FOUND=$((AGENT_FILES_FOUND + 1))
    fi
done
if [ "$AGENT_FILES_FOUND" -gt 0 ]; then
    log_pass "$AGENT_FILES_FOUND agent .md files copied"
else
    log_fail "No agent .md files found in .claude/agents/"
fi

###############################################################################
echo ""
echo "[Scenario] Full Init Stages Only Created Files"
###############################################################################

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
if echo "$OUTPUT" | grep -q "git add -A"; then
    log_fail "Summary suggests 'git add -A' (MUST NOT)"
else
    log_pass "Summary does NOT suggest 'git add -A'"
fi

###############################################################################
echo ""
echo "[Scenario] Full Init Installs Complete Gitignore Patterns"
###############################################################################

GITIGNORE="$PROJECT/.gitignore"
TEMPLATE="$PROJECT/purlin/purlin-config-sample/gitignore.purlin"

if [ -f "$TEMPLATE" ]; then
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
else
    log_fail "gitignore.purlin template not found"
fi

###############################################################################
echo ""
echo "[Scenario] Full Init Installs Session Recovery Hook"
###############################################################################

SETTINGS_FILE="$PROJECT/.claude/settings.json"

if [ -f "$SETTINGS_FILE" ]; then
    log_pass ".claude/settings.json exists"
else
    log_fail ".claude/settings.json missing"
fi

if python3 -c "import json; json.load(open('$SETTINGS_FILE'))" 2>/dev/null; then
    log_pass ".claude/settings.json is valid JSON"
else
    log_fail ".claude/settings.json is NOT valid JSON"
fi

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

if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
for entry in hooks:
    if isinstance(entry, dict) and entry.get('matcher') == 'clear':
        for h in entry.get('hooks', []):
            cmd = h.get('command', '')
            if 'pl-resume' in cmd:
                sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    log_pass "Clear hook echoes pl-resume recovery instruction"
else
    log_fail "Clear hook does NOT echo pl-resume instruction"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "[Scenario] Standalone Mode Guard Prevents Init in Purlin Repo"
###############################################################################

# Run init.sh from within the Purlin repo itself (standalone mode)
STANDALONE_EXIT=0
STANDALONE_OUTPUT=$("$SUBMODULE_SRC/tools/init.sh" 2>&1) || STANDALONE_EXIT=$?

if [ $STANDALONE_EXIT -ne 0 ]; then
    log_pass "Standalone guard exits with non-zero status ($STANDALONE_EXIT)"
else
    log_fail "Standalone guard did NOT exit with non-zero status"
fi

if echo "$STANDALONE_OUTPUT" | grep -qi "consumer"; then
    log_pass "Error message mentions consumer projects"
else
    log_fail "Error message does NOT mention consumer projects"
fi

###############################################################################
echo ""
echo "[Scenario] Ergonomic Symlink at Submodule Root"
###############################################################################

# Check the symlink in the actual Purlin repo
if [ -L "$SUBMODULE_SRC/pl-init.sh" ]; then
    log_pass "purlin/pl-init.sh is a symlink"
else
    log_fail "purlin/pl-init.sh is NOT a symlink"
fi

SYMLINK_TARGET="$(readlink "$SUBMODULE_SRC/pl-init.sh" 2>/dev/null || true)"
if [ "$SYMLINK_TARGET" = "tools/init.sh" ]; then
    log_pass "pl-init.sh points to tools/init.sh"
else
    log_fail "pl-init.sh target is '$SYMLINK_TARGET' (expected 'tools/init.sh')"
fi

###############################################################################
echo ""
echo "=== Context Recovery Hook Tests ==="
###############################################################################

# CRH basic test: compact hook installed by init (reuse state from above)
echo ""
echo "[CRH Scenario] Consumer Full Init Installs Compact Hook"
setup_sandbox

# Remove claude from PATH so MCP doesn't run
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

SETTINGS_FILE="$PROJECT/.claude/settings.json"

if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
found = any(e.get('matcher') == 'compact' for e in hooks if isinstance(e, dict))
sys.exit(0 if found else 1)
" 2>/dev/null; then
    crh_pass "SessionStart hook with matcher 'compact' present"
else
    crh_fail "SessionStart hook with matcher 'compact' NOT found"
fi

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
    crh_pass "Compact hook echoes role guard rails and /pl-resume directive"
else
    crh_fail "Compact hook does NOT echo role guard rails and /pl-resume"
fi

# Both clear and compact exist
if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
has_clear = any(e.get('matcher') == 'clear' for e in hooks if isinstance(e, dict))
has_compact = any(e.get('matcher') == 'compact' for e in hooks if isinstance(e, dict))
sys.exit(0 if has_clear and has_compact else 1)
" 2>/dev/null; then
    crh_pass "Both 'clear' and 'compact' hooks present after full init"
else
    crh_fail "Missing either 'clear' or 'compact' hook after full init"
fi

cleanup_sandbox

# CRH merge test: hook merges with existing settings
echo ""
echo "[CRH Scenario] Compact Hook Merges with Existing Hooks"
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

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

# Check all three hooks present
if python3 -c "
import json, sys
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
matchers = set(e.get('matcher') for e in hooks if isinstance(e, dict))
sys.exit(0 if {'custom', 'clear', 'compact'}.issubset(matchers) else 1)
" 2>/dev/null; then
    crh_pass "All three hooks present: custom, clear, and compact"
else
    crh_fail "Missing one or more hooks (expected custom, clear, compact)"
fi

# Custom hook unchanged
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
    crh_pass "Existing custom hook is unchanged"
else
    crh_fail "Existing custom hook was modified"
fi

cleanup_sandbox

# CRH idempotent test: compact hook not duplicated on refresh
echo ""
echo "[CRH Scenario] Compact Hook Idempotent on Refresh"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

# Run again (refresh mode)
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

COMPACT_COUNT=$(python3 -c "
import json
with open('$PROJECT/.claude/settings.json') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('SessionStart', [])
print(sum(1 for e in hooks if isinstance(e, dict) and e.get('matcher') == 'compact'))
" 2>/dev/null)

if [ "$COMPACT_COUNT" = "1" ]; then
    crh_pass "Exactly one compact hook entry after refresh (not duplicated)"
else
    crh_fail "Expected 1 compact hook, found $COMPACT_COUNT (duplicated)"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== CLAUDE.md Installation Tests ==="
###############################################################################

# CRH CLAUDE.md test 1: Fresh init creates CLAUDE.md via template
echo ""
echo "[CRH Scenario] Full Init Creates CLAUDE.md via Template"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

CLAUDE_MD="$PROJECT/CLAUDE.md"

if [ -f "$CLAUDE_MD" ]; then
    crh_pass "CLAUDE.md exists after full init"
else
    crh_fail "CLAUDE.md missing after full init"
fi

if grep -q '<!-- purlin:start -->' "$CLAUDE_MD" && grep -q '<!-- purlin:end -->' "$CLAUDE_MD"; then
    crh_pass "CLAUDE.md contains purlin start/end markers"
else
    crh_fail "CLAUDE.md missing purlin markers"
fi

# Check content between markers matches template
TEMPLATE="$PROJECT/purlin/purlin-config-sample/CLAUDE.md.purlin"
if [ -f "$TEMPLATE" ]; then
    TEMPLATE_CONTENT="$(cat "$TEMPLATE")"
    if grep -qF "Role Boundaries" "$CLAUDE_MD"; then
        crh_pass "CLAUDE.md contains role boundary text"
    else
        crh_fail "CLAUDE.md missing role boundary text"
    fi
    if grep -qF "Architect" "$CLAUDE_MD" && grep -qF "Builder" "$CLAUDE_MD" && grep -qF "QA" "$CLAUDE_MD" && grep -qF "PM" "$CLAUDE_MD"; then
        crh_pass "CLAUDE.md contains text for all four roles"
    else
        crh_fail "CLAUDE.md missing text for one or more roles"
    fi
else
    crh_fail "CLAUDE.md.purlin template missing"
fi

cleanup_sandbox

# CRH CLAUDE.md test 2: Replaces marked block when markers exist
echo ""
echo "[CRH Scenario] CLAUDE.md Replaces Marked Block on Refresh"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

CLAUDE_MD="$PROJECT/CLAUDE.md"

# Add user content before and after markers, and modify content between markers
python3 -c "
with open('$CLAUDE_MD', 'r') as f:
    content = f.read()
# Add user content outside markers and replace inner content with outdated text
new_content = '# My Custom Header\n\n' + content.replace('Role Boundaries', 'OUTDATED CONTENT') + '\n\n# My Custom Footer\n'
with open('$CLAUDE_MD', 'w') as f:
    f.write(new_content)
" 2>/dev/null

# Run refresh
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

# Check that markers still exist and content between them is current
if grep -qF "Role Boundaries" "$CLAUDE_MD"; then
    crh_pass "Marked block replaced with current template content"
else
    crh_fail "Marked block NOT replaced (still has outdated content)"
fi

# Check user content outside markers is preserved
if grep -qF "My Custom Header" "$CLAUDE_MD" && grep -qF "My Custom Footer" "$CLAUDE_MD"; then
    crh_pass "User content outside markers preserved"
else
    crh_fail "User content outside markers lost"
fi

cleanup_sandbox

# CRH CLAUDE.md test 3: Appends marked block when no markers exist
echo ""
echo "[CRH Scenario] CLAUDE.md Appends Block When No Markers Exist"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

CLAUDE_MD="$PROJECT/CLAUDE.md"

# Replace CLAUDE.md with user-only content (no markers)
echo "# My Project" > "$CLAUDE_MD"
echo "" >> "$CLAUDE_MD"
echo "This is my custom CLAUDE.md with no purlin markers." >> "$CLAUDE_MD"

# Run refresh
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

# Check original content preserved
if grep -qF "My Project" "$CLAUDE_MD"; then
    crh_pass "Original user content preserved when appending"
else
    crh_fail "Original user content lost when appending"
fi

# Check purlin block appended
if grep -q '<!-- purlin:start -->' "$CLAUDE_MD" && grep -q '<!-- purlin:end -->' "$CLAUDE_MD"; then
    crh_pass "Purlin marked block appended to existing CLAUDE.md"
else
    crh_fail "Purlin marked block NOT appended"
fi

# Check role text present
if grep -qF "Role Boundaries" "$CLAUDE_MD"; then
    crh_pass "Appended block contains role boundary text"
else
    crh_fail "Appended block missing role boundary text"
fi

cleanup_sandbox

# CRH CLAUDE.md test 4: Preserves user content outside markers
echo ""
echo "[CRH Scenario] CLAUDE.md Preserves User Content Outside Markers"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

CLAUDE_MD="$PROJECT/CLAUDE.md"

# Add user content before and after markers
python3 -c "
with open('$CLAUDE_MD', 'r') as f:
    content = f.read()
new_content = '# User Preamble\n\nCustom instructions here.\n\n' + content + '\n\n# User Epilogue\n\nMore custom content.\n'
with open('$CLAUDE_MD', 'w') as f:
    f.write(new_content)
" 2>/dev/null

# Run refresh
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

if grep -qF "User Preamble" "$CLAUDE_MD" && grep -qF "Custom instructions here." "$CLAUDE_MD"; then
    crh_pass "User preamble preserved after refresh"
else
    crh_fail "User preamble lost after refresh"
fi

if grep -qF "User Epilogue" "$CLAUDE_MD" && grep -qF "More custom content." "$CLAUDE_MD"; then
    crh_pass "User epilogue preserved after refresh"
else
    crh_fail "User epilogue lost after refresh"
fi

if grep -q '<!-- purlin:start -->' "$CLAUDE_MD" && grep -q '<!-- purlin:end -->' "$CLAUDE_MD"; then
    crh_pass "Purlin markers still present after refresh with user content"
else
    crh_fail "Purlin markers lost after refresh with user content"
fi

cleanup_sandbox

# CRH CLAUDE.md test 5: Idempotent on refresh
echo ""
echo "[CRH Scenario] CLAUDE.md Installation Is Idempotent"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

CLAUDE_MD="$PROJECT/CLAUDE.md"

# Record content after first run
FIRST_CONTENT="$(cat "$CLAUDE_MD")"

# Run refresh (second run)
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

SECOND_CONTENT="$(cat "$CLAUDE_MD")"

if [ "$FIRST_CONTENT" = "$SECOND_CONTENT" ]; then
    crh_pass "CLAUDE.md unchanged after second run (idempotent)"
else
    crh_fail "CLAUDE.md changed after second run (not idempotent)"
fi

# Check no duplicate markers
MARKER_COUNT=$(grep -c '<!-- purlin:start -->' "$CLAUDE_MD")
if [ "$MARKER_COUNT" = "1" ]; then
    crh_pass "Exactly one purlin:start marker (no duplicates)"
else
    crh_fail "Expected 1 purlin:start marker, found $MARKER_COUNT"
fi

cleanup_sandbox

# CRH CLAUDE.md test 6: Staged in post-init git add
echo ""
echo "[CRH Scenario] CLAUDE.md Is Staged in Post-Init Git Add"
setup_sandbox

PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

STAGED_FILES="$(git -C "$PROJECT" diff --cached --name-only 2>/dev/null)"

if echo "$STAGED_FILES" | grep -q "CLAUDE.md"; then
    crh_pass "CLAUDE.md is staged after full init"
else
    crh_fail "CLAUDE.md is NOT staged after full init"
fi

cleanup_sandbox

# CRH CLAUDE.md test 7: CLAUDE.md staged after refresh path
echo ""
echo "[CRH Scenario] CLAUDE.md Staged After Refresh"
setup_sandbox

# Full init first
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

# Commit everything so refresh has a clean slate
git -C "$PROJECT" add -A > /dev/null 2>&1
git -C "$PROJECT" commit -q -m "after init" 2>/dev/null

# Modify the template to force a change during refresh
echo "# Updated Template" >> "$PROJECT/purlin/purlin-config-sample/CLAUDE.md.purlin"

# Run refresh
PATH="$RESTRICTED_PATH" "$INIT_SH" > /dev/null 2>&1

STAGED_FILES="$(git -C "$PROJECT" diff --cached --name-only 2>/dev/null)"

if echo "$STAGED_FILES" | grep -q "CLAUDE.md"; then
    crh_pass "CLAUDE.md is staged after refresh (M48 fix verified)"
else
    crh_fail "CLAUDE.md is NOT staged after refresh (M48 regression)"
fi

cleanup_sandbox

###############################################################################
# Results
###############################################################################
echo ""
echo "==============================="
TOTAL=$((PASS + FAIL))
echo "  project_init: $PASS/$TOTAL passed"
CRH_TOTAL=$((CRH_PASS + CRH_FAIL))
echo "  context_recovery_hook: $CRH_PASS/$CRH_TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

# Write tests/project_init/tests.json
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_init.sh\"}"
OUTDIR="$TESTS_DIR/project_init"
mkdir -p "$OUTDIR"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

# Write tests/context_recovery_hook/tests.json
CRH_RESULT_JSON="{\"status\": \"$([ $CRH_FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $CRH_PASS, \"failed\": $CRH_FAIL, \"total\": $CRH_TOTAL, \"test_file\": \"tools/test_init.sh\"}"
CRH_OUTDIR="$TESTS_DIR/context_recovery_hook"
mkdir -p "$CRH_OUTDIR"
echo "$CRH_RESULT_JSON" > "$CRH_OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ] && [ $CRH_FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
