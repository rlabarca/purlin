#!/usr/bin/env bash
# Test: Sync ledger update logic
# Verifies that sync-ledger-update.sh correctly maps staged files to features,
# computes sync status, and supports SHA backfill.
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

# Initial commit
echo "init" > README.md
git add README.md .purlin/ 2>/dev/null
git commit -q -m "init"

LEDGER="$TEST_DIR/.purlin/sync_ledger.json"

# === Test 1: Code-only commit -> code_ahead ===
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

# === Test 2: Spec-only commit -> spec_ahead ===
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

# === Test 3: Code+spec commit -> synced ===
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

# === Test 4: Code+impl commit -> synced ===
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

# === Test 6: Impl-only commit resolves code_ahead -> synced ===
# First, create a code_ahead state
rm -f "$LEDGER"
echo "code4" > tests/my_feature/test_four.sh
git add tests/my_feature/test_four.sh
bash "$LEDGER_SCRIPT" 2>/dev/null
git commit -q -m "code only for impl test" --allow-empty 2>/dev/null || true

# Verify we're in code_ahead
if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
sys.exit(0 if entry.get('sync_status') == 'code_ahead' else 1)
" 2>/dev/null; then
    : # precondition met
else
    assert_fail "impl-only resolves code_ahead (precondition: code_ahead not set)"
fi

# Now commit impl-only
echo "impl update" > features/skills_engineer/my_feature.impl.md
git add features/skills_engineer/my_feature.impl.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('my_feature', {})
status = entry.get('sync_status')
has_impl = entry.get('last_impl_commit') == 'pending'
sys.exit(0 if status == 'synced' and has_impl else 1)
" 2>/dev/null; then
    assert_pass "impl-only commit resolves code_ahead to synced"
else
    assert_fail "impl-only commit resolves code_ahead to synced"
fi
git commit -q -m "impl only" --allow-empty 2>/dev/null || true

# === Test 7: Impl-only commit with unknown status does NOT change status ===
rm -f "$LEDGER"
# Create a fresh feature with unknown status, then add impl only
echo "spec first" > features/skills_engineer/other_feature.md
git add features/skills_engineer/other_feature.md
bash "$LEDGER_SCRIPT" 2>/dev/null
git commit -q -m "spec for other" --allow-empty 2>/dev/null || true

# Now impl-only -- status is spec_ahead, impl alone should NOT change it
echo "impl" > features/skills_engineer/other_feature.impl.md
git add features/skills_engineer/other_feature.impl.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('other_feature', {})
sys.exit(0 if entry.get('sync_status') == 'spec_ahead' else 1)
" 2>/dev/null; then
    assert_pass "impl-only keeps spec_ahead (no false resolution)"
else
    assert_fail "impl-only keeps spec_ahead (no false resolution)"
fi
git commit -q -m "impl for other" --allow-empty 2>/dev/null || true

# === Test 8: Discoveries file skipped by ledger (no stem mapping) ===
rm -f "$LEDGER"
echo "discovery" > features/skills_engineer/disc_feature.discoveries.md
git add features/skills_engineer/disc_feature.discoveries.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if [ ! -f "$LEDGER" ] || python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
# discoveries.md doesn't match impl or spec stem patterns in ledger
sys.exit(0 if 'disc_feature' not in data else 1)
" 2>/dev/null; then
    assert_pass "discoveries file skipped by ledger (no stem mapping)"
else
    assert_fail "discoveries file skipped by ledger (no stem mapping)"
fi
git commit -q -m "disc" --allow-empty 2>/dev/null || true

# === Test 9: Regression JSON staged maps to feature via tests/ path ===
rm -f "$LEDGER"
mkdir -p tests/reg_feature
echo '{"status":"PASS"}' > tests/reg_feature/regression.json
git add tests/reg_feature/regression.json
bash "$LEDGER_SCRIPT" 2>/dev/null

if python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('reg_feature', {})
# regression.json is in tests/reg_feature/ -> stem=reg_feature, type=code
sys.exit(0 if entry.get('sync_status') in ('code_ahead', 'synced') else 1)
" 2>/dev/null; then
    assert_pass "regression.json maps to feature and tracked as code change"
else
    assert_fail "regression.json maps to feature and tracked as code change"
fi
git commit -q -m "regression" --allow-empty 2>/dev/null || true

# === Test 10: skills/<name>/ maps to purlin_<name> feature ===
rm -f "$LEDGER"
# Create a feature spec so the skill mapping has a known stem to match
echo "spec" > features/skills_engineer/purlin_build.md
git add features/skills_engineer/purlin_build.md
bash "$LEDGER_SCRIPT" 2>/dev/null
git commit -q -m "add spec" --allow-empty 2>/dev/null || true
rm -f "$LEDGER"

mkdir -p skills/build
echo "skill content" > skills/build/SKILL.md
git add skills/build/SKILL.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if [ -f "$LEDGER" ] && python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('purlin_build', {})
sys.exit(0 if entry.get('sync_status') in ('code_ahead', 'spec_ahead', 'synced') else 1)
" 2>/dev/null; then
    assert_pass "skills/build/ maps to purlin_build feature"
else
    assert_fail "skills/build/ maps to purlin_build feature"
fi
git commit -q -m "skill" --allow-empty 2>/dev/null || true

# === Test 11: skills/<name>/ with no matching feature stays unmapped ===
rm -f "$LEDGER"
mkdir -p skills/nonexistent
echo "orphan skill" > skills/nonexistent/SKILL.md
git add skills/nonexistent/SKILL.md
bash "$LEDGER_SCRIPT" 2>/dev/null

if [ ! -f "$LEDGER" ] || python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
sys.exit(0 if 'purlin_nonexistent' not in data else 1)
" 2>/dev/null; then
    assert_pass "skills/nonexistent/ stays unmapped (no matching feature)"
else
    assert_fail "skills/nonexistent/ stays unmapped (no matching feature)"
fi
git commit -q -m "nonexistent skill" --allow-empty 2>/dev/null || true

# === Test 12: Commit scope parsing maps unmapped code files ===
rm -f "$LEDGER"
echo "engine code" > scripts/mcp/some_engine.py
git add scripts/mcp/some_engine.py
PURLIN_COMMIT_MSG="feat(purlin_build): add engine" bash "$LEDGER_SCRIPT" 2>/dev/null

if [ -f "$LEDGER" ] && python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
entry = data.get('purlin_build', {})
sys.exit(0 if entry.get('sync_status') in ('code_ahead', 'synced') else 1)
" 2>/dev/null; then
    assert_pass "commit scope maps unmapped scripts/ to feature"
else
    assert_fail "commit scope maps unmapped scripts/ to feature"
fi
git commit -q -m "engine" --allow-empty 2>/dev/null || true

# === Test 13: Unmapped code file without commit scope stays unmapped ===
rm -f "$LEDGER"
echo "random code" > scripts/mcp/random_util.py
git add scripts/mcp/random_util.py
bash "$LEDGER_SCRIPT" 2>/dev/null

if [ ! -f "$LEDGER" ] || python3 -c "
import json, sys
with open('$LEDGER') as f:
    data = json.load(f)
sys.exit(0 if len(data) == 0 else 1)
" 2>/dev/null; then
    assert_pass "unmapped code file without commit scope stays unmapped"
else
    assert_fail "unmapped code file without commit scope stays unmapped"
fi
git commit -q -m "random util" --allow-empty 2>/dev/null || true

# Cleanup
cd /
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
