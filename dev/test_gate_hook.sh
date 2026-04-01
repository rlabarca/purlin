#!/usr/bin/env bash
# Tests for gate_hook — 8 rules.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GATE_SCRIPT="$REAL_PROJECT_ROOT/scripts/gate.sh"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

# Setup temp project
TMPDIR_ROOT=$(mktemp -d)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT
export PROJECT_ROOT="$TMPDIR_ROOT"
mkdir -p "$TMPDIR_ROOT/.purlin/runtime"
mkdir -p "$TMPDIR_ROOT/specs/_invariants"

echo "=== gate_hook tests ==="

# PROOF-1 (RULE-1): hooks.json registers Write|Edit|NotebookEdit pointing to gate.sh
HOOKS_JSON="$REAL_PROJECT_ROOT/hooks/hooks.json"
if python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
hooks = data['hooks']['PreToolUse']
found = any(
    h['matcher'] == 'Write|Edit|NotebookEdit'
    and any('gate.sh' in cmd.get('command', '') for cmd in h['hooks'])
    for h in hooks
)
sys.exit(0 if found else 1)
" "$HOOKS_JSON"; then
    echo "  PASS: hooks.json matcher"
    purlin_proof "gate_hook" "PROOF-1" "RULE-1" pass "hooks.json registers correct matcher"
else
    echo "  FAIL: hooks.json matcher"
    purlin_proof "gate_hook" "PROOF-1" "RULE-1" fail "hooks.json registers correct matcher"
fi

# PROOF-2 (RULE-2): Non-invariant files pass through (exit 0)
export TOOL_INPUT_FILE_PATH="src/app.js"
if bash "$GATE_SCRIPT" 2>/dev/null; then
    echo "  PASS: non-invariant passes"
    purlin_proof "gate_hook" "PROOF-2" "RULE-2" pass "non-invariant file exits 0"
else
    echo "  FAIL: non-invariant passes"
    purlin_proof "gate_hook" "PROOF-2" "RULE-2" fail "non-invariant file exits 0"
fi

# PROOF-3 (RULE-3): No bypass lock → blocked exit 2
export TOOL_INPUT_FILE_PATH="specs/_invariants/i_test.md"
rm -f "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
ec=0; bash "$GATE_SCRIPT" 2>/dev/null || ec=$?
if [[ $ec -eq 2 ]]; then
    echo "  PASS: no lock → exit 2"
    purlin_proof "gate_hook" "PROOF-3" "RULE-3" pass "no bypass lock blocks with exit 2"
else
    echo "  FAIL: no lock → exit 2 (got $ec)"
    purlin_proof "gate_hook" "PROOF-3" "RULE-3" fail "no bypass lock blocks with exit 2"
fi

# PROOF-4 (RULE-4): Bypass lock with matching target → exit 0
export TOOL_INPUT_FILE_PATH="specs/_invariants/i_test.md"
echo '{"target": "i_test.md"}' > "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
if bash "$GATE_SCRIPT" 2>/dev/null; then
    echo "  PASS: matching lock → exit 0"
    purlin_proof "gate_hook" "PROOF-4" "RULE-4" pass "matching bypass lock allows write"
else
    echo "  FAIL: matching lock → exit 0"
    purlin_proof "gate_hook" "PROOF-4" "RULE-4" fail "matching bypass lock allows write"
fi
rm -f "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"

# PROOF-5 (RULE-5): Bypass lock with wrong target → blocked exit 2
export TOOL_INPUT_FILE_PATH="specs/_invariants/i_test.md"
echo '{"target": "i_other.md"}' > "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
ec=0; bash "$GATE_SCRIPT" 2>/dev/null || ec=$?
rm -f "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
if [[ $ec -eq 2 ]]; then
    echo "  PASS: wrong target → exit 2"
    purlin_proof "gate_hook" "PROOF-5" "RULE-5" pass "wrong target blocks with exit 2"
else
    echo "  FAIL: wrong target → exit 2 (got $ec)"
    purlin_proof "gate_hook" "PROOF-5" "RULE-5" fail "wrong target blocks with exit 2"
fi

# PROOF-6 (RULE-6): Block message on stderr includes corrective action
export TOOL_INPUT_FILE_PATH="specs/_invariants/i_test.md"
rm -f "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
stderr_out=$(bash "$GATE_SCRIPT" 2>&1 1>/dev/null) || true
if [[ "$stderr_out" == *"purlin:invariant sync"* ]]; then
    echo "  PASS: stderr corrective action"
    purlin_proof "gate_hook" "PROOF-6" "RULE-6" pass "block message includes purlin:invariant sync on stderr"
else
    echo "  FAIL: stderr corrective action"
    purlin_proof "gate_hook" "PROOF-6" "RULE-6" fail "block message includes purlin:invariant sync on stderr"
fi

# PROOF-7 (RULE-7): Handles both absolute and relative paths
rm -f "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
export TOOL_INPUT_FILE_PATH="/Users/test/project/specs/_invariants/i_test.md"
ec_abs=0; bash "$GATE_SCRIPT" 2>/dev/null || ec_abs=$?
export TOOL_INPUT_FILE_PATH="specs/_invariants/i_test.md"
ec_rel=0; bash "$GATE_SCRIPT" 2>/dev/null || ec_rel=$?
if [[ $ec_abs -eq 2 ]] && [[ $ec_rel -eq 2 ]]; then
    echo "  PASS: absolute + relative paths"
    purlin_proof "gate_hook" "PROOF-7" "RULE-7" pass "blocks both absolute and relative invariant paths"
else
    echo "  FAIL: absolute + relative paths (abs=$ec_abs rel=$ec_rel)"
    purlin_proof "gate_hook" "PROOF-7" "RULE-7" fail "blocks both absolute and relative invariant paths"
fi

# PROOF-8 (RULE-8): Empty FILE_PATH → exit 0
unset TOOL_INPUT_FILE_PATH 2>/dev/null || true
unset TOOL_INPUT_file_path 2>/dev/null || true
export TOOL_INPUT_FILE_PATH=""
if bash "$GATE_SCRIPT" 2>/dev/null; then
    echo "  PASS: empty path → exit 0"
    purlin_proof "gate_hook" "PROOF-8" "RULE-8" pass "empty FILE_PATH exits 0"
else
    echo "  FAIL: empty path → exit 0"
    purlin_proof "gate_hook" "PROOF-8" "RULE-8" fail "empty FILE_PATH exits 0"
fi

# Emit proof files from real project root
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "gate_hook: 8/8 proofs recorded"
