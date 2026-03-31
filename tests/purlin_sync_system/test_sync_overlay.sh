#!/usr/bin/env bash
# Test: Scan engine sync overlay (scan_sync_ledger)
# Verifies that scan_engine.scan_sync_ledger() correctly merges the persistent
# sync_ledger.json with the session-scoped sync_state.json, producing accurate
# per-feature sync status with session_pending overlays.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"

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

# Create isolated test environment
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

mkdir -p "$TEST_DIR/.purlin/runtime"

LEDGER="$TEST_DIR/.purlin/sync_ledger.json"
SESSION="$TEST_DIR/.purlin/runtime/sync_state.json"

# Helper: run scan_sync_ledger and return JSON
run_overlay() {
    PURLIN_PROJECT_ROOT="$TEST_DIR" python3 -c "
import sys, os, json
os.environ['PURLIN_PROJECT_ROOT'] = '$TEST_DIR'
sys.path.insert(0, os.path.join('$PLUGIN_ROOT', 'scripts', 'mcp'))
from scan_engine import scan_sync_ledger
result = scan_sync_ledger()
json.dump(result, sys.stdout, indent=2)
" 2>/dev/null
}

# === Test 1: Ledger entry appears in scan output ===
cat > "$LEDGER" <<'EOF'
{
  "webhook_delivery": {
    "sync_status": "code_ahead",
    "last_code_commit": "abc123",
    "last_code_date": "2026-03-30T10:00:00Z",
    "last_spec_commit": null,
    "last_spec_date": null,
    "last_impl_commit": null,
    "last_impl_date": null
  }
}
EOF
rm -f "$SESSION"

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
entry = data.get('webhook_delivery', {})
sys.exit(0 if entry.get('sync_status') == 'code_ahead' and entry.get('last_code_commit') == 'abc123' else 1)
" 2>/dev/null; then
    assert_pass "ledger entry appears in scan output"
else
    assert_fail "ledger entry appears in scan output"
fi

# === Test 2: Session overlay adds session_pending ===
cat > "$SESSION" <<'EOF'
{
  "features": {
    "webhook_delivery": {
      "code_files": ["scripts/webhook.py"],
      "test_files": [],
      "spec_changed": true,
      "impl_changed": false
    }
  },
  "unclassified_writes": []
}
EOF

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
entry = data.get('webhook_delivery', {})
# Session has code+spec -> session_pending=synced
sys.exit(0 if entry.get('session_pending') == 'synced' else 1)
" 2>/dev/null; then
    assert_pass "session overlay adds session_pending"
else
    assert_fail "session overlay adds session_pending"
fi

# === Test 3: Unclassified writes surfaced ===
echo '{}' > "$LEDGER"
cat > "$SESSION" <<'EOF'
{
  "features": {},
  "unclassified_writes": ["utils/helpers.py", "lib/common.py"]
}
EOF

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
uc = data.get('_unclassified', {})
files = uc.get('files', [])
sys.exit(0 if 'utils/helpers.py' in files and len(files) == 2 else 1)
" 2>/dev/null; then
    assert_pass "unclassified writes surfaced"
else
    assert_fail "unclassified writes surfaced"
fi

# === Test 4: Empty ledger and state returns empty ===
echo '{}' > "$LEDGER"
rm -f "$SESSION"

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
sys.exit(0 if len(data) == 0 else 1)
" 2>/dev/null; then
    assert_pass "empty ledger and state returns empty"
else
    assert_fail "empty ledger and state returns empty"
fi

# === Test 5: Session-only feature appears without ledger entry ===
echo '{}' > "$LEDGER"
cat > "$SESSION" <<'EOF'
{
  "features": {
    "new_feature": {
      "code_files": ["src/new.py"],
      "test_files": [],
      "spec_changed": false,
      "impl_changed": false
    }
  },
  "unclassified_writes": []
}
EOF

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
entry = data.get('new_feature', {})
sys.exit(0 if entry.get('session_pending') == 'code_ahead' else 1)
" 2>/dev/null; then
    assert_pass "session-only feature appears without ledger entry"
else
    assert_fail "session-only feature appears without ledger entry"
fi

# === Test 6: Synced ledger + session code-only -> pending drift ===
cat > "$LEDGER" <<'EOF'
{
  "auth_middleware": {
    "sync_status": "synced",
    "last_code_commit": "def456",
    "last_code_date": "2026-03-29T10:00:00Z",
    "last_spec_commit": "def456",
    "last_spec_date": "2026-03-29T10:00:00Z"
  }
}
EOF
cat > "$SESSION" <<'EOF'
{
  "features": {
    "auth_middleware": {
      "code_files": ["scripts/auth.py"],
      "test_files": [],
      "spec_changed": false,
      "impl_changed": false
    }
  },
  "unclassified_writes": []
}
EOF

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
entry = data.get('auth_middleware', {})
sys.exit(0 if entry.get('sync_status') == 'synced' and entry.get('session_pending') == 'code_ahead' else 1)
" 2>/dev/null; then
    assert_pass "synced ledger + session code-only detects pending drift"
else
    assert_fail "synced ledger + session code-only detects pending drift"
fi

# === Test 7: Code+impl session resolves to synced pending ===
cat > "$SESSION" <<'EOF'
{
  "features": {
    "auth_middleware": {
      "code_files": ["scripts/auth.py"],
      "test_files": [],
      "spec_changed": false,
      "impl_changed": true
    }
  },
  "unclassified_writes": []
}
EOF

if run_overlay | python3 -c "
import json, sys
data = json.load(sys.stdin)
entry = data.get('auth_middleware', {})
sys.exit(0 if entry.get('session_pending') == 'synced' else 1)
" 2>/dev/null; then
    assert_pass "code+impl session pending resolves to synced"
else
    assert_fail "code+impl session pending resolves to synced"
fi

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
