#!/usr/bin/env bash
# Test: Sync ledger update logic
# Verifies that sync-ledger-update.sh correctly classifies staged files,
# maps them to features, computes sync status, and supports SHA backfill.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
LEDGER_SCRIPT="$PLUGIN_ROOT/hooks/scripts/sync-ledger-update.sh"

passed=0
failed=0
total=0

assert_pass() {
    local desc="$1"
    ((total++))
    echo "PASS: $desc"
    ((passed++))
}

assert_fail() {
    local desc="$1"
    ((total++))
    echo "FAIL: $desc"
    ((failed++))
}

# Create isolated git repo for testing
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

cd "$TEST_DIR"
git init -q
git config user.email "test@test.com"
git config user.name "Test"

mkdir -p .purlin/runtime
mkdir -p features/skills_engineer
mkdir -p tests/my_feature
mkdir -p scripts/mcp

# Copy file_classification.json for fallback
if [ -f "$PLUGIN_ROOT/references/file_classification.json" ]; then
    mkdir -p references
    cp "$PLUGIN_ROOT/references/file_classification.json" references/
fi

# Initial commit
echo "init" > README.md
git add README.md .purlin/ 2>/dev/null
git commit -q -m "init"

LEDGER="$TEST_DIR/.purlin/sync_ledger.json"

# === Test 1: Code-only commit → code_ahead ===
echo "code" > tests/my_feature/test_one.sh
git add tests/my_feature/test_one.sh
bash "$LEDGER_SCRIPT" 2>/dev/null

if [ -f "$LEDGER" ] && python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
sys.exit(0 if entry.get('sync_status') == 'code_ahead' else 1)
" 2>/dev/null; then
    assert_pass "code-only commit sets code_ahead"
else
    assert_fail "code-only commit sets code_ahead"
fi
git commit -q -m "code only" --allow-empty 2>/dev/null || true

# === Test 2: Spec-only commit → spec_ahead ===
rm -f "$LEDGER"
echo "spec" > features/skills_engineer/my_feature.md
git add features/skills_engineer/my_feature.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
sys.exit(0 if entry.get('sync_status') == 'spec_ahead' else 1)
" 2>/dev/null; then
    assert_pass "spec-only commit sets spec_ahead"
else
    assert_fail "spec-only commit sets spec_ahead"
fi
git commit -q -m "spec only" --allow-empty 2>/dev/null || true

# === Test 3: Code+spec commit → synced ===
rm -f "$LEDGER"
echo "code2" > tests/my_feature/test_two.sh
echo "spec2" > features/skills_engineer/my_feature.md
git add tests/my_feature/test_two.sh features/skills_engineer/my_feature.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
sys.exit(0 if entry.get('sync_status') == 'synced' else 1)
" 2>/dev/null; then
    assert_pass "code+spec commit sets synced"
else
    assert_fail "code+spec commit sets synced"
fi
git commit -q -m "both" --allow-empty 2>/dev/null || true

# === Test 4: Code+impl commit → synced ===
rm -f "$LEDGER"
echo "code3" > tests/my_feature/test_three.sh
echo "impl" > features/skills_engineer/my_feature.impl.md
git add tests/my_feature/test_three.sh features/skills_engineer/my_feature.impl.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
sys.exit(0 if entry.get('sync_status') == 'synced' else 1)
" 2>/dev/null; then
    assert_pass "code+impl commit sets synced"
else
    assert_fail "code+impl commit sets synced"
fi
git commit -q -m "code+impl" --allow-empty 2>/dev/null || true

# === Test 5: SHA backfill ===
# Set up a ledger with 'pending' SHAs
cat > "$LEDGER" <<'ENDJSON'
{
  "my_feature": {
    "last_code_commit": "pending",
    "last_code_date": "2026-03-30T12:00:00Z",
    "last_spec_commit": "pending",
    "last_spec_date": "2026-03-30T12:00:00Z",
    "last_impl_commit": null,
    "last_impl_date": null,
    "sync_status": "synced"
  }
}
ENDJSON

FAKE_SHA="abc123def456"
PURLIN_LEDGER_FILE="$LEDGER" bash "$LEDGER_SCRIPT" --sha "$FAKE_SHA" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
code_sha = entry.get('last_code_commit', '')
spec_sha = entry.get('last_spec_commit', '')
impl_sha = entry.get('last_impl_commit')
sys.exit(0 if code_sha == '$FAKE_SHA' and spec_sha == '$FAKE_SHA' and impl_sha is None else 1)
" 2>/dev/null; then
    assert_pass "sha backfill replaces pending"
else
    assert_fail "sha backfill replaces pending"
fi

# Cleanup
cd /
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
