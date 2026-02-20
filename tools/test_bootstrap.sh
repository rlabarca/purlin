#!/bin/bash
# test_bootstrap.sh — Automated tests for bootstrap.sh and sync_upstream.sh
# Produces test_status.json in the same directory.
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

# Build a sandbox that simulates a consumer project with agentic-dev-core as a submodule.
# The submodule is a real git clone of the current repo so that `git rev-parse HEAD` works.
setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT

    PROJECT="$SANDBOX/my-project"
    mkdir -p "$PROJECT"

    # Initialize consumer project as a git repo (needed for submodule simulation)
    git -C "$PROJECT" init -q

    # Clone current repo into the consumer project as a "submodule"
    git clone -q "$SUBMODULE_SRC" "$PROJECT/agentic-dev"

    # Overlay uncommitted scripts into the clone so tests use the latest versions
    cp "$SUBMODULE_SRC/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/bootstrap.sh"
    cp "$SUBMODULE_SRC/tools/sync_upstream.sh" "$PROJECT/agentic-dev/tools/sync_upstream.sh"
    cp "$SUBMODULE_SRC/tools/cdd/start.sh" "$PROJECT/agentic-dev/tools/cdd/start.sh"
    cp "$SUBMODULE_SRC/tools/cdd/serve.py" "$PROJECT/agentic-dev/tools/cdd/serve.py"
    cp "$SUBMODULE_SRC/tools/software_map/start.sh" "$PROJECT/agentic-dev/tools/software_map/start.sh"
    cp "$SUBMODULE_SRC/tools/software_map/serve.py" "$PROJECT/agentic-dev/tools/software_map/serve.py"
    cp "$SUBMODULE_SRC/tools/software_map/generate_tree.py" "$PROJECT/agentic-dev/tools/software_map/generate_tree.py"
    cp "$SUBMODULE_SRC/tools/critic/critic.py" "$PROJECT/agentic-dev/tools/critic/critic.py"
    cp "$SUBMODULE_SRC/tools/critic/run.sh" "$PROJECT/agentic-dev/tools/critic/run.sh"
    chmod +x "$PROJECT/agentic-dev/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/sync_upstream.sh"

    BOOTSTRAP="$PROJECT/agentic-dev/tools/bootstrap.sh"
    SYNC="$PROJECT/agentic-dev/tools/sync_upstream.sh"
}

###############################################################################
echo "=== Bootstrap Tests ==="
###############################################################################

# --- Scenario: Fresh bootstrap ---
echo ""
echo "[Scenario] Bootstrap a Fresh Consumer Project"
setup_sandbox

OUTPUT=$("$BOOTSTRAP" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "Exit code 0"; else log_fail "Exit code was $EXIT_CODE (expected 0)"; fi

if [ -d "$PROJECT/.agentic_devops" ]; then log_pass ".agentic_devops/ created"; else log_fail ".agentic_devops/ not created"; fi

if [ -f "$PROJECT/.agentic_devops/config.json" ]; then
    if grep -q '"tools_root": "agentic-dev/tools"' "$PROJECT/.agentic_devops/config.json"; then
        log_pass "config.json tools_root patched correctly"
    else
        log_fail "config.json tools_root incorrect: $(cat "$PROJECT/.agentic_devops/config.json")"
    fi
else
    log_fail "config.json not created"
fi

if [ -f "$PROJECT/.agentic_devops/.upstream_sha" ]; then
    SHA_LEN=$(wc -c < "$PROJECT/.agentic_devops/.upstream_sha" | tr -d ' ')
    if [ "$SHA_LEN" -ge 40 ]; then
        log_pass ".upstream_sha recorded (${SHA_LEN} chars)"
    else
        log_fail ".upstream_sha too short ($SHA_LEN chars)"
    fi
else
    log_fail ".upstream_sha not created"
fi

if [ -f "$PROJECT/.agentic_devops/ARCHITECT_OVERRIDES.md" ]; then log_pass "ARCHITECT_OVERRIDES.md copied"; else log_fail "ARCHITECT_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.agentic_devops/BUILDER_OVERRIDES.md" ]; then log_pass "BUILDER_OVERRIDES.md copied"; else log_fail "BUILDER_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" ]; then log_pass "HOW_WE_WORK_OVERRIDES.md copied"; else log_fail "HOW_WE_WORK_OVERRIDES.md missing"; fi

if [ -x "$PROJECT/run_claude_architect.sh" ]; then log_pass "run_claude_architect.sh executable"; else log_fail "run_claude_architect.sh not executable"; fi
if [ -x "$PROJECT/run_claude_builder.sh" ]; then log_pass "run_claude_builder.sh executable"; else log_fail "run_claude_builder.sh not executable"; fi

if [ -d "$PROJECT/features" ]; then log_pass "features/ created"; else log_fail "features/ missing"; fi
if [ -f "$PROJECT/PROCESS_HISTORY.md" ]; then log_pass "PROCESS_HISTORY.md created"; else log_fail "PROCESS_HISTORY.md missing"; fi

cleanup_sandbox

# --- Scenario: Double init guard ---
echo ""
echo "[Scenario] Prevent Double Initialization"
setup_sandbox

"$BOOTSTRAP" > /dev/null 2>&1
OUTPUT=$("$BOOTSTRAP" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then log_pass "Second run exits non-zero ($EXIT_CODE)"; else log_fail "Second run should exit non-zero"; fi
if echo "$OUTPUT" | grep -qi "already exists"; then log_pass "Error message mentions 'already exists'"; else log_fail "Error message doesn't mention 'already exists'"; fi

cleanup_sandbox

# --- Scenario: Launcher concatenation order ---
echo ""
echo "[Scenario] Launcher Script Concatenation Order"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

# Check that architect launcher references the correct files in order
ARCHITECT_CONTENT=$(cat "$PROJECT/run_claude_architect.sh")
if echo "$ARCHITECT_CONTENT" | grep -q 'HOW_WE_WORK_BASE.md.*>.*PROMPT_FILE'; then
    log_pass "Architect: HOW_WE_WORK_BASE.md written first"
else
    log_fail "Architect: HOW_WE_WORK_BASE.md not first"
fi
if echo "$ARCHITECT_CONTENT" | grep -q 'ARCHITECT_BASE.md.*>>.*PROMPT_FILE'; then
    log_pass "Architect: ARCHITECT_BASE.md appended second"
else
    log_fail "Architect: ARCHITECT_BASE.md not appended"
fi
if echo "$ARCHITECT_CONTENT" | grep -q 'HOW_WE_WORK_OVERRIDES.md'; then
    log_pass "Architect: HOW_WE_WORK_OVERRIDES.md referenced"
else
    log_fail "Architect: HOW_WE_WORK_OVERRIDES.md not referenced"
fi
if echo "$ARCHITECT_CONTENT" | grep -q 'ARCHITECT_OVERRIDES.md'; then
    log_pass "Architect: ARCHITECT_OVERRIDES.md referenced"
else
    log_fail "Architect: ARCHITECT_OVERRIDES.md not referenced"
fi

# Check builder launcher
BUILDER_CONTENT=$(cat "$PROJECT/run_claude_builder.sh")
if echo "$BUILDER_CONTENT" | grep -q 'dangerously-skip-permissions'; then
    log_pass "Builder: --dangerously-skip-permissions flag present"
else
    log_fail "Builder: --dangerously-skip-permissions flag missing"
fi

cleanup_sandbox

# --- Scenario: QA Launcher Script Concatenation Order ---
echo ""
echo "[Scenario] QA Launcher Script Concatenation Order"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

QA_CONTENT=$(cat "$PROJECT/run_claude_qa.sh")
if echo "$QA_CONTENT" | grep -q 'HOW_WE_WORK_BASE.md.*>.*PROMPT_FILE'; then
    log_pass "QA: HOW_WE_WORK_BASE.md written first"
else
    log_fail "QA: HOW_WE_WORK_BASE.md not first"
fi
if echo "$QA_CONTENT" | grep -q 'QA_BASE.md.*>>.*PROMPT_FILE'; then
    log_pass "QA: QA_BASE.md appended second"
else
    log_fail "QA: QA_BASE.md not appended"
fi
if echo "$QA_CONTENT" | grep -q 'HOW_WE_WORK_OVERRIDES.md'; then
    log_pass "QA: HOW_WE_WORK_OVERRIDES.md referenced"
else
    log_fail "QA: HOW_WE_WORK_OVERRIDES.md not referenced"
fi
if echo "$QA_CONTENT" | grep -q 'QA_OVERRIDES.md'; then
    log_pass "QA: QA_OVERRIDES.md referenced"
else
    log_fail "QA: QA_OVERRIDES.md not referenced"
fi

cleanup_sandbox

# --- Scenario: Gitignore warning ---
echo ""
echo "[Scenario] Gitignore Warning"
setup_sandbox
echo ".agentic_devops" > "$PROJECT/.gitignore"

OUTPUT=$("$BOOTSTRAP" 2>&1)
if echo "$OUTPUT" | grep -qi "WARNING.*\.agentic_devops"; then
    log_pass "Gitignore warning printed"
else
    log_fail "Gitignore warning not printed"
fi

cleanup_sandbox

# --- Scenario: Gitignore creation ---
echo ""
echo "[Scenario] Gitignore Creation (no existing .gitignore)"
setup_sandbox
rm -f "$PROJECT/.gitignore"

"$BOOTSTRAP" > /dev/null 2>&1
if [ -f "$PROJECT/.gitignore" ]; then
    if grep -q '.DS_Store' "$PROJECT/.gitignore"; then
        log_pass ".gitignore created with recommended ignores"
    else
        log_fail ".gitignore missing recommended ignores"
    fi
    # Check that .agentic_devops itself is not ignored (subdirs like runtime/cache are OK)
    if grep -qE '^\\.agentic_devops/?$' "$PROJECT/.gitignore"; then
        log_fail ".gitignore ignores .agentic_devops directory (MUST NOT)"
    else
        log_pass ".gitignore does not ignore .agentic_devops directory"
    fi
else
    log_fail ".gitignore not created"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Sync Upstream Tests ==="
###############################################################################

# --- Scenario: Already up to date ---
echo ""
echo "[Scenario] Already Up to Date"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

OUTPUT=$("$SYNC" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "Exit code 0"; else log_fail "Exit code was $EXIT_CODE (expected 0)"; fi
if echo "$OUTPUT" | grep -qi "already up to date"; then log_pass "Prints 'Already up to date'"; else log_fail "Missing 'already up to date' message"; fi

cleanup_sandbox

# --- Scenario: Missing .upstream_sha ---
echo ""
echo "[Scenario] Missing Upstream SHA File"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1
rm "$PROJECT/.agentic_devops/.upstream_sha"

OUTPUT=$("$SYNC" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then log_pass "Exit code non-zero ($EXIT_CODE)"; else log_fail "Should exit non-zero when .upstream_sha missing"; fi
if echo "$OUTPUT" | grep -qi "not found\|missing"; then log_pass "Error mentions missing file"; else log_fail "Error doesn't mention missing file"; fi

cleanup_sandbox

# --- Scenario: Detect upstream changes ---
echo ""
echo "[Scenario] Detect Upstream Changes"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

# Simulate upstream change: record an old (fake) SHA and verify the diff runs
REAL_SHA="$(git -C "$PROJECT/agentic-dev" rev-parse HEAD)"
# Get a parent commit to use as "old" SHA
PARENT_SHA="$(git -C "$PROJECT/agentic-dev" rev-parse HEAD~1 2>/dev/null || echo "")"

if [ -n "$PARENT_SHA" ]; then
    echo "$PARENT_SHA" > "$PROJECT/.agentic_devops/.upstream_sha"

    OUTPUT=$("$SYNC" 2>&1)
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then log_pass "Sync completed successfully"; else log_fail "Sync exit code $EXIT_CODE"; fi
    if echo "$OUTPUT" | grep -qi "instruction changes\|tool changes"; then
        log_pass "Changelog sections displayed"
    else
        log_fail "Changelog sections not displayed"
    fi

    # Verify SHA was updated
    UPDATED_SHA="$(cat "$PROJECT/.agentic_devops/.upstream_sha" | tr -d '[:space:]')"
    if [ "$UPDATED_SHA" = "$REAL_SHA" ]; then
        log_pass ".upstream_sha updated to current HEAD"
    else
        log_fail ".upstream_sha not updated (got: ${UPDATED_SHA:0:12}, expected: ${REAL_SHA:0:12})"
    fi
else
    echo "  SKIP: Only one commit in history — cannot test diff scenario"
fi

cleanup_sandbox

# --- Scenario: Contextual notes ---
echo ""
echo "[Scenario] Contextual Notes for Changes"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

# Find an ancestor commit that predates instruction/tool changes
# so the diff actually contains changes in those directories.
ANCESTOR_SHA=""
for N in 1 2 3 4 5; do
    CANDIDATE="$(git -C "$PROJECT/agentic-dev" rev-parse "HEAD~$N" 2>/dev/null || echo "")"
    if [ -z "$CANDIDATE" ]; then break; fi
    DIFF_CHECK="$(git -C "$PROJECT/agentic-dev" diff --stat "$CANDIDATE"..HEAD -- instructions/ tools/ 2>/dev/null || true)"
    if [ -n "$DIFF_CHECK" ]; then
        ANCESTOR_SHA="$CANDIDATE"
        break
    fi
done

if [ -n "$ANCESTOR_SHA" ]; then
    echo "$ANCESTOR_SHA" > "$PROJECT/.agentic_devops/.upstream_sha"
    OUTPUT=$("$SYNC" 2>&1)

    if echo "$OUTPUT" | grep -qi "automatic"; then
        log_pass "Contextual notes mention 'automatic'"
    else
        log_fail "Contextual notes missing"
    fi
else
    echo "  SKIP: Only one commit in history"
fi

cleanup_sandbox

###############################################################################
# Section 2.10: Config JSON Validity After Bootstrap
###############################################################################
echo ""
echo "[Scenario] Config JSON Validity After Bootstrap"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

if python3 -c "import json; json.load(open('$PROJECT/.agentic_devops/config.json'))" 2>/dev/null; then
    log_pass "config.json is valid JSON after bootstrap"
else
    log_fail "config.json is NOT valid JSON after bootstrap"
fi

# Verify original keys preserved
if python3 -c "
import json
c = json.load(open('$PROJECT/.agentic_devops/config.json'))
assert 'tools_root' in c, 'missing tools_root'
assert 'cdd_port' in c, 'missing cdd_port'
" 2>/dev/null; then
    log_pass "config.json preserves original keys"
else
    log_fail "config.json missing original keys"
fi

cleanup_sandbox

###############################################################################
# Section 2.11: Launcher Scripts Export AGENTIC_PROJECT_ROOT
###############################################################################
echo ""
echo "[Scenario] Launcher Scripts Export AGENTIC_PROJECT_ROOT"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

for LAUNCHER in run_claude_architect.sh run_claude_builder.sh run_claude_qa.sh; do
    if grep -q 'export AGENTIC_PROJECT_ROOT=' "$PROJECT/$LAUNCHER"; then
        log_pass "$LAUNCHER exports AGENTIC_PROJECT_ROOT"
    else
        log_fail "$LAUNCHER does NOT export AGENTIC_PROJECT_ROOT"
    fi
done

cleanup_sandbox

###############################################################################
# Section 2.11: Python Tool Uses AGENTIC_PROJECT_ROOT
###############################################################################
echo ""
echo "[Scenario] Python Tool Uses AGENTIC_PROJECT_ROOT"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

# Create a features dir and minimal feature file so critic can run
mkdir -p "$PROJECT/features"
cat > "$PROJECT/features/test_feature.md" << 'FEAT_EOF'
# Feature: Test Feature
> Label: "Test"
> Category: "Test"

## 1. Overview
Test.

## 2. Requirements
Test.

## 3. Scenarios
### Automated Scenarios
#### Scenario: Test
    Given test
    When test
    Then test

## 4. Implementation Notes
None.
FEAT_EOF

# Set AGENTIC_PROJECT_ROOT to the consumer project and invoke critic
mkdir -p "$PROJECT/tests"
AGENTIC_PROJECT_ROOT="$PROJECT" python3 "$PROJECT/agentic-dev/tools/critic/critic.py" "$PROJECT/features/test_feature.md" > /dev/null 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "critic.py runs with AGENTIC_PROJECT_ROOT set"
else
    log_fail "critic.py failed with AGENTIC_PROJECT_ROOT set (exit $EXIT_CODE)"
fi

# Verify it used the consumer project root (critic.json written to consumer's tests/)
if [ -f "$PROJECT/tests/test_feature/critic.json" ]; then
    log_pass "critic.json written to consumer project tests/"
else
    log_fail "critic.json NOT written to consumer project tests/"
fi

cleanup_sandbox

###############################################################################
# Section 2.13: Python Tool Survives Malformed Config
###############################################################################
echo ""
echo "[Scenario] Python Tool Survives Malformed Config"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

# Corrupt the config.json
echo "{ this is not valid json" > "$PROJECT/.agentic_devops/config.json"

mkdir -p "$PROJECT/features"
mkdir -p "$PROJECT/tests"

# Attempt to run critic with malformed config — should not crash
AGENTIC_PROJECT_ROOT="$PROJECT" python3 "$PROJECT/agentic-dev/tools/critic/critic.py" 2>/dev/null
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "critic.py survives malformed config.json"
else
    log_fail "critic.py crashed with malformed config.json (exit $EXIT_CODE)"
fi

# Verify warning is printed to stderr
STDERR_OUTPUT=$(AGENTIC_PROJECT_ROOT="$PROJECT" python3 "$PROJECT/agentic-dev/tools/critic/critic.py" 2>&1 1>/dev/null || true)
if echo "$STDERR_OUTPUT" | grep -qi "warning"; then
    log_pass "Warning printed to stderr for malformed config"
else
    log_fail "No warning printed to stderr for malformed config"
fi

cleanup_sandbox

###############################################################################
# Section 2.12: Generated Artifacts Written Outside Submodule
###############################################################################
echo ""
echo "[Scenario] Generated Artifacts Written Outside Submodule"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

mkdir -p "$PROJECT/features"
cat > "$PROJECT/features/test_feature.md" << 'FEAT_EOF'
# Feature: Test Feature
> Label: "Test"
> Category: "Test"

## 1. Overview
Test.

## 2. Requirements
Test.

## 3. Scenarios
### Automated Scenarios
#### Scenario: Test
    Given test
    When test
    Then test

## 4. Implementation Notes
None.
FEAT_EOF

# Run generate_tree.py (produces .mmd and dependency_graph.json)
AGENTIC_PROJECT_ROOT="$PROJECT" python3 "$PROJECT/agentic-dev/tools/software_map/generate_tree.py" > /dev/null 2>&1

if [ -f "$PROJECT/.agentic_devops/cache/dependency_graph.json" ]; then
    log_pass "dependency_graph.json written to .agentic_devops/cache/"
else
    log_fail "dependency_graph.json NOT in .agentic_devops/cache/"
fi

if [ -f "$PROJECT/.agentic_devops/cache/feature_graph.mmd" ]; then
    log_pass "feature_graph.mmd written to .agentic_devops/cache/"
else
    log_fail "feature_graph.mmd NOT in .agentic_devops/cache/"
fi

# Verify NO artifacts in the submodule's tools/ directory
if [ -f "$PROJECT/agentic-dev/tools/software_map/dependency_graph.json" ]; then
    log_fail "dependency_graph.json found inside submodule tools/ (should not be)"
else
    log_pass "No dependency_graph.json inside submodule tools/"
fi

cleanup_sandbox

###############################################################################
# Tool Start Script Config Discovery Tests
###############################################################################
echo ""
echo "=== Start Script Config Discovery Tests ==="

# --- Scenario: Submodule layout config discovery ---
echo ""
echo "[Scenario] CDD start.sh discovers submodule config"
CDD_START="$SCRIPT_DIR/cdd/start.sh"
SMAP_START="$SCRIPT_DIR/software_map/start.sh"

# Check that both start scripts have the submodule fallback path
if grep -q 'DIR/../../../.agentic_devops/config.json' "$CDD_START"; then
    log_pass "cdd/start.sh has submodule config fallback"
else
    log_fail "cdd/start.sh missing submodule config fallback"
fi

if grep -q 'DIR/../../../.agentic_devops/config.json' "$SMAP_START"; then
    log_pass "software_map/start.sh has submodule config fallback"
else
    log_fail "software_map/start.sh missing submodule config fallback"
fi

# Verify standalone path is tried first
if grep -q 'DIR/../../.agentic_devops/config.json' "$CDD_START"; then
    log_pass "cdd/start.sh tries standalone path first"
else
    log_fail "cdd/start.sh missing standalone config path"
fi

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

# Write tests/<feature>/tests.json for both covered features
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}"

for FEATURE in submodule_bootstrap submodule_sync; do
    OUTDIR="$TESTS_DIR/$FEATURE"
    mkdir -p "$OUTDIR"
    echo "$RESULT_JSON" > "$OUTDIR/tests.json"
done

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
