#!/bin/bash
# test_bootstrap.sh — Automated tests for submodule_bootstrap.md
# Tests the bootstrap.sh deprecation shim and submodule-safety requirements
# (Sections 2.11-2.13). Init-specific tests are in test_init.sh.
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
    git clone -q "$SUBMODULE_SRC" "$PROJECT/agentic-dev"

    # Overlay uncommitted scripts so tests use the latest versions
    cp "$SUBMODULE_SRC/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/bootstrap.sh"
    cp "$SUBMODULE_SRC/tools/init.sh" "$PROJECT/agentic-dev/tools/init.sh"
    cp "$SUBMODULE_SRC/tools/cdd/start.sh" "$PROJECT/agentic-dev/tools/cdd/start.sh"
    cp "$SUBMODULE_SRC/tools/cdd/stop.sh" "$PROJECT/agentic-dev/tools/cdd/stop.sh"
    cp "$SUBMODULE_SRC/tools/cdd/serve.py" "$PROJECT/agentic-dev/tools/cdd/serve.py"
    cp "$SUBMODULE_SRC/tools/cdd/graph.py" "$PROJECT/agentic-dev/tools/cdd/graph.py"
    cp "$SUBMODULE_SRC/tools/critic/critic.py" "$PROJECT/agentic-dev/tools/critic/critic.py"
    cp "$SUBMODULE_SRC/tools/critic/run.sh" "$PROJECT/agentic-dev/tools/critic/run.sh"
    cp "$SUBMODULE_SRC/tools/resolve_python.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"
    cp "$SUBMODULE_SRC/requirements.txt" "$PROJECT/agentic-dev/requirements.txt" 2>/dev/null || true
    cp "$SUBMODULE_SRC/requirements-optional.txt" "$PROJECT/agentic-dev/requirements-optional.txt" 2>/dev/null || true
    chmod +x "$PROJECT/agentic-dev/tools/bootstrap.sh" "$PROJECT/agentic-dev/tools/init.sh" "$PROJECT/agentic-dev/tools/resolve_python.sh"

    BOOTSTRAP="$PROJECT/agentic-dev/tools/bootstrap.sh"
}

###############################################################################
echo "=== Bootstrap Deprecation Shim Tests ==="
###############################################################################

# --- Scenario: Bootstrap delegates to init.sh ---
echo ""
echo "[Scenario] Bootstrap Delegates to init.sh (Fresh Project)"
setup_sandbox

OUTPUT=$("$BOOTSTRAP" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "Exit code 0"; else log_fail "Exit code was $EXIT_CODE (expected 0)"; fi
if [ -d "$PROJECT/.purlin" ]; then log_pass ".purlin/ created via delegation"; else log_fail ".purlin/ not created"; fi

if [ -f "$PROJECT/.purlin/config.json" ]; then
    if grep -q '"tools_root": "agentic-dev/tools"' "$PROJECT/.purlin/config.json"; then
        log_pass "config.json tools_root patched correctly"
    else
        log_fail "config.json tools_root incorrect"
    fi
else
    log_fail "config.json not created"
fi

if [ -f "$PROJECT/.purlin/.upstream_sha" ]; then
    SHA_LEN=$(wc -c < "$PROJECT/.purlin/.upstream_sha" | tr -d ' ')
    if [ "$SHA_LEN" -ge 40 ]; then
        log_pass ".upstream_sha recorded (${SHA_LEN} chars)"
    else
        log_fail ".upstream_sha too short ($SHA_LEN chars)"
    fi
else
    log_fail ".upstream_sha not created"
fi

if [ -f "$PROJECT/.purlin/ARCHITECT_OVERRIDES.md" ]; then log_pass "ARCHITECT_OVERRIDES.md copied"; else log_fail "ARCHITECT_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/BUILDER_OVERRIDES.md" ]; then log_pass "BUILDER_OVERRIDES.md copied"; else log_fail "BUILDER_OVERRIDES.md missing"; fi
if [ -f "$PROJECT/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then log_pass "HOW_WE_WORK_OVERRIDES.md copied"; else log_fail "HOW_WE_WORK_OVERRIDES.md missing"; fi

if [ -x "$PROJECT/run_architect.sh" ]; then log_pass "run_architect.sh executable"; else log_fail "run_architect.sh not executable"; fi
if [ -x "$PROJECT/run_builder.sh" ]; then log_pass "run_builder.sh executable"; else log_fail "run_builder.sh not executable"; fi

if [ -d "$PROJECT/features" ]; then log_pass "features/ created"; else log_fail "features/ missing"; fi

# Deprecation notice
if echo "$OUTPUT" | grep -qi "deprecated"; then
    log_pass "Deprecation notice printed"
else
    log_fail "Deprecation notice NOT printed"
fi

cleanup_sandbox

# --- Scenario: Bootstrap second run enters refresh mode ---
echo ""
echo "[Scenario] Bootstrap Second Run Enters Refresh Mode"
setup_sandbox

"$BOOTSTRAP" > /dev/null 2>&1
OUTPUT=$("$BOOTSTRAP" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then log_pass "Second run exits 0 (refresh mode)"; else log_fail "Second run exits $EXIT_CODE (expected 0)"; fi
if echo "$OUTPUT" | grep -q "refreshed"; then
    log_pass "Second run enters refresh mode"
else
    log_fail "Second run did not enter refresh mode"
fi

cleanup_sandbox

# --- Scenario: Launcher concatenation order ---
echo ""
echo "[Scenario] Launcher Script Concatenation Order"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

ARCHITECT_CONTENT=$(cat "$PROJECT/run_architect.sh")
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

BUILDER_CONTENT=$(cat "$PROJECT/run_builder.sh")
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

QA_CONTENT=$(cat "$PROJECT/run_qa.sh")
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
echo ".purlin" > "$PROJECT/.gitignore"

OUTPUT=$("$BOOTSTRAP" 2>&1)
if echo "$OUTPUT" | grep -qi "WARNING.*\.purlin"; then
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
    if grep -qE '^\.purlin/?$' "$PROJECT/.gitignore"; then
        log_fail ".gitignore ignores .purlin directory (MUST NOT)"
    else
        log_pass ".gitignore does not ignore .purlin directory"
    fi
else
    log_fail ".gitignore not created"
fi

cleanup_sandbox

# --- Scenario: Bootstrap Excludes pl-edit-base.md ---
echo ""
echo "[Scenario] Bootstrap Excludes pl-edit-base.md from Consumer Projects"
setup_sandbox

mkdir -p "$PROJECT/agentic-dev/.claude/commands"
echo "# pl-edit-base — MUST NOT be distributed" > "$PROJECT/agentic-dev/.claude/commands/pl-edit-base.md"
echo "# pl-status — shared command" > "$PROJECT/agentic-dev/.claude/commands/pl-status.md"

"$BOOTSTRAP" > /dev/null 2>&1

if [ -f "$PROJECT/.claude/commands/pl-edit-base.md" ]; then
    log_fail "pl-edit-base.md was copied (MUST NOT be)"
else
    log_pass "pl-edit-base.md correctly excluded"
fi

if [ -f "$PROJECT/.claude/commands/pl-status.md" ]; then
    log_pass "Other command files still copied normally"
else
    log_fail "Other command files not copied"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Config JSON Validity ==="
###############################################################################
echo ""
echo "[Scenario] Config JSON Validity After Bootstrap"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

if python3 -c "import json; json.load(open('$PROJECT/.purlin/config.json'))" 2>/dev/null; then
    log_pass "config.json is valid JSON"
else
    log_fail "config.json is NOT valid JSON"
fi

if python3 -c "
import json
c = json.load(open('$PROJECT/.purlin/config.json'))
assert 'tools_root' in c, 'missing tools_root'
assert 'cdd_port' in c, 'missing cdd_port'
" 2>/dev/null; then
    log_pass "config.json preserves original keys"
else
    log_fail "config.json missing original keys"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Submodule Safety Tests (Sections 2.11-2.13) ==="
###############################################################################

# --- Scenario: Launcher Scripts Export PURLIN_PROJECT_ROOT ---
echo ""
echo "[Scenario] Launcher Scripts Export PURLIN_PROJECT_ROOT"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

for LAUNCHER in run_architect.sh run_builder.sh run_qa.sh; do
    if grep -q 'export PURLIN_PROJECT_ROOT=' "$PROJECT/$LAUNCHER"; then
        log_pass "$LAUNCHER exports PURLIN_PROJECT_ROOT"
    else
        log_fail "$LAUNCHER does NOT export PURLIN_PROJECT_ROOT"
    fi
done

cleanup_sandbox

# --- Scenario: Python Tool Uses PURLIN_PROJECT_ROOT ---
echo ""
echo "[Scenario] Python Tool Uses PURLIN_PROJECT_ROOT"
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
FEAT_EOF

mkdir -p "$PROJECT/tests"
PURLIN_PROJECT_ROOT="$PROJECT" python3 "$PROJECT/agentic-dev/tools/critic/critic.py" "$PROJECT/features/test_feature.md" > /dev/null 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "critic.py runs with PURLIN_PROJECT_ROOT set"
else
    log_fail "critic.py failed with PURLIN_PROJECT_ROOT set (exit $EXIT_CODE)"
fi

if [ -f "$PROJECT/tests/test_feature/critic.json" ]; then
    log_pass "critic.json written to consumer project tests/"
else
    log_fail "critic.json NOT written to consumer project tests/"
fi

cleanup_sandbox

# --- Scenario: Python Tool Survives Malformed Config ---
echo ""
echo "[Scenario] Python Tool Survives Malformed Config"
setup_sandbox
"$BOOTSTRAP" > /dev/null 2>&1

echo "{ this is not valid json" > "$PROJECT/.purlin/config.json"

mkdir -p "$PROJECT/features"
mkdir -p "$PROJECT/tests"

PURLIN_PROJECT_ROOT="$PROJECT" python3 "$PROJECT/agentic-dev/tools/critic/critic.py" 2>/dev/null
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_pass "critic.py survives malformed config.json"
else
    log_fail "critic.py crashed with malformed config.json (exit $EXIT_CODE)"
fi

cleanup_sandbox

# --- Scenario: Generated Artifacts Written Outside Submodule ---
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
FEAT_EOF

PURLIN_PROJECT_ROOT="$PROJECT" bash "$PROJECT/agentic-dev/tools/cdd/status.sh" --graph > /dev/null 2>&1

if [ -f "$PROJECT/.purlin/cache/dependency_graph.json" ]; then
    log_pass "dependency_graph.json written to .purlin/cache/"
else
    log_fail "dependency_graph.json NOT in .purlin/cache/"
fi

if [ -f "$PROJECT/.purlin/cache/feature_graph.mmd" ]; then
    log_pass "feature_graph.mmd written to .purlin/cache/"
else
    log_fail "feature_graph.mmd NOT in .purlin/cache/"
fi

if [ -f "$PROJECT/agentic-dev/tools/cdd/dependency_graph.json" ]; then
    log_fail "dependency_graph.json found inside submodule tools/"
else
    log_pass "No dependency_graph.json inside submodule tools/"
fi

cleanup_sandbox

###############################################################################
echo ""
echo "=== Venv Suggestion Tests ==="
###############################################################################

echo ""
echo "[Scenario] Bootstrap Prints Venv Suggestion When No Venv Exists"
setup_sandbox

OUTPUT=$("$BOOTSTRAP" 2>&1)
if echo "$OUTPUT" | grep -q "requirements-optional.txt"; then
    log_pass "Venv suggestion includes requirements-optional.txt path"
else
    log_fail "Venv suggestion missing"
fi
if echo "$OUTPUT" | grep -qi "optional"; then
    log_pass "Venv suggestion marked as optional"
else
    log_fail "Venv suggestion not marked as optional"
fi

cleanup_sandbox

echo ""
echo "[Scenario] Bootstrap Omits Venv Suggestion When Venv Exists"
setup_sandbox
mkdir -p "$PROJECT/.venv"

OUTPUT=$("$BOOTSTRAP" 2>&1)
if echo "$OUTPUT" | grep -q "requirements-optional.txt"; then
    log_fail "Venv suggestion printed when .venv already exists"
else
    log_pass "Venv suggestion correctly omitted when .venv exists"
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

# Write tests/<feature>/tests.json for submodule_bootstrap only
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}"

OUTDIR="$TESTS_DIR/submodule_bootstrap"
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
