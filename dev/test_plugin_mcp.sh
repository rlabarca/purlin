#!/usr/bin/env bash
# dev/test_plugin_mcp.sh
#
# Integration tests for the Purlin MCP server (scripts/mcp/purlin_server.py).
# Tests all 6 tools via JSON-RPC 2.0 stdio protocol.
#
# Usage:
#   ./dev/test_plugin_mcp.sh [--help]
#
# Requires:
#   - The plugin fixture at /tmp/purlin-plugin-fixture
#     (run dev/setup_plugin_test_fixture.sh to create it)
#   - python3 on PATH
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'HELP'
Usage: test_plugin_mcp.sh [--help]

Integration tests for the Purlin MCP server JSON-RPC protocol.

Tests all 6 MCP tools:
  - purlin_scan: full scan, only filter, tombstones
  - purlin_classify: CODE, SPEC, QA, INVARIANT classifications
  - purlin_sync: per-feature sync status
  - purlin_config: read config values
  - purlin_graph: regenerate dependency graph
  - purlin_status: scan-based status

Also tests protocol-level behavior:
  - initialize handshake
  - tools/list enumeration
  - unknown tool error handling

Requires the fixture at /tmp/purlin-plugin-fixture.
Run dev/setup_plugin_test_fixture.sh first.
HELP
    exit 0
fi

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve PLUGIN_ROOT: support both main repo and worktree layouts.
_resolve_plugin_root() {
    local candidate="$SCRIPT_DIR/.."
    candidate="$(cd "$candidate" && pwd)"
    for _ in $(seq 1 10); do
        if [[ -f "$candidate/scripts/mcp/purlin_server.py" ]]; then
            echo "$candidate"
            return
        fi
        candidate="$(cd "$candidate/.." && pwd)"
    done
    # Worktree fallback
    local git_file="$SCRIPT_DIR/../.git"
    if [[ -f "$git_file" ]]; then
        local gitdir
        gitdir="$(sed 's/^gitdir: //' "$git_file")"
        gitdir="$(cd "$(dirname "$git_file")" && cd "$(dirname "$gitdir")" && pwd)/$(basename "$gitdir")"
        local main_repo
        main_repo="$(cd "$gitdir/../../.." && pwd)"
        if [[ -f "$main_repo/scripts/mcp/purlin_server.py" ]]; then
            echo "$main_repo"
            return
        fi
    fi
    echo "$(cd "$SCRIPT_DIR/.." && pwd)"
}

PLUGIN_ROOT="$(_resolve_plugin_root)"
FIXTURE_DIR="/tmp/purlin-plugin-fixture"
MCP_SERVER="$PLUGIN_ROOT/scripts/mcp/purlin_server.py"

if [[ ! -d "$FIXTURE_DIR/.purlin" ]]; then
    echo "ERROR: Fixture not found at $FIXTURE_DIR"
    echo "Run: dev/setup_plugin_test_fixture.sh"
    exit 1
fi

if [[ ! -f "$MCP_SERVER" ]]; then
    echo "ERROR: MCP server not found at $MCP_SERVER"
    exit 1
fi

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
PASS=0
FAIL=0
TOTAL=0

pass() {
    ((PASS++))
    ((TOTAL++))
    echo "  PASS: $1"
}

fail() {
    ((FAIL++))
    ((TOTAL++))
    echo "  FAIL: $1"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# call_mcp_raw: pipe a raw JSON-RPC request string to the MCP server.
# Returns the first line of JSON output.
call_mcp_raw() {
    local request="$1"
    echo "$request" | PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 "$MCP_SERVER" 2>/dev/null | head -1
}

# call_mcp: build and send a JSON-RPC request.
# Uses python3 to construct the JSON to avoid bash brace/quoting issues.
call_mcp() {
    local method="$1"
    local params="$2"
    local id="$3"
    local request
    request="$(python3 -c "
import json, sys
print(json.dumps({
    'jsonrpc': '2.0',
    'id': $id,
    'method': '$method',
    'params': json.loads('$params')
}))
" 2>/dev/null)"
    call_mcp_raw "$request"
}

# call_mcp_tool: send a tools/call request for the named tool.
call_mcp_tool() {
    local tool_name="$1"
    local arguments="$2"
    local id="$3"
    local request
    request="$(python3 -c "
import json, sys
print(json.dumps({
    'jsonrpc': '2.0',
    'id': $id,
    'method': 'tools/call',
    'params': {
        'name': '$tool_name',
        'arguments': json.loads('$arguments')
    }
}))
" 2>/dev/null)"
    call_mcp_raw "$request"
}

# extract_text: pull the text content from a tools/call response via stdin.
# Usage: TEXT="$(echo "$RESP" | extract_text)"
extract_text() {
    python3 -c "
import json, sys
resp = json.load(sys.stdin)
content = resp.get('result', {}).get('content', [])
if content and 'text' in content[0]:
    print(content[0]['text'])
else:
    print('')
" 2>/dev/null
}

# json_field: extract a field from JSON via stdin.
# Usage: VALUE="$(echo "$JSON" | json_field "d.get('key')")"
json_field() {
    local expr="$1"
    python3 -c "
import json, sys
d = json.load(sys.stdin)
val = $expr
if val is None:
    print('null')
elif isinstance(val, bool):
    print('true' if val else 'false')
else:
    print(val)
" 2>/dev/null
}

# json_check: validate a boolean condition on JSON via stdin. Returns 0/1.
# Usage: echo "$JSON" | json_check "expr"
json_check() {
    local expr="$1"
    python3 -c "
import json, sys
d = json.load(sys.stdin)
result = bool($expr)
sys.exit(0 if result else 1)
" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Clean state before tests
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Protocol Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== MCP Protocol Tests ==="

# 1. initialize returns serverInfo
RESP="$(call_mcp "initialize" '{}' 1)"
SERVER_NAME="$(echo "$RESP" | python3 -c "
import json, sys
r = json.load(sys.stdin)
print(r.get('result', {}).get('serverInfo', {}).get('name', ''))
" 2>/dev/null)"
if [[ "$SERVER_NAME" == "purlin" ]]; then
    pass "initialize returns serverInfo.name='purlin'"
else
    fail "initialize response missing serverInfo.name='purlin': $RESP"
fi

# 2. tools/list returns 6 tools
RESP="$(call_mcp "tools/list" '{}' 2)"
TOOL_COUNT="$(echo "$RESP" | python3 -c "
import json, sys
r = json.load(sys.stdin)
print(len(r.get('result', {}).get('tools', [])))
" 2>/dev/null)"
if [[ "$TOOL_COUNT" -eq 6 ]]; then
    pass "tools/list returns 6 tools"
else
    fail "tools/list returned $TOOL_COUNT tools, expected 6"
fi

# 3. unknown tool returns error
RESP="$(call_mcp_tool "nonexistent_tool" '{}' 3)"
HAS_ERROR="$(echo "$RESP" | python3 -c "
import json, sys
r = json.load(sys.stdin)
print('true' if 'error' in r else 'false')
" 2>/dev/null)"
if [[ "$HAS_ERROR" == "true" ]]; then
    pass "unknown tool returns error"
else
    fail "unknown tool did not return error: $RESP"
fi

# ---------------------------------------------------------------------------
# purlin_scan Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== purlin_scan Tests ==="

# 4. full scan has features key
RESP="$(call_mcp_tool "purlin_scan" '{}' 4)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "'features' in d"; then
    pass "purlin_scan: full scan has 'features' key"
else
    fail "purlin_scan: full scan missing 'features' key"
fi

# 5. only=features filters output
RESP="$(call_mcp_tool "purlin_scan" '{"only":"features"}' 5)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "'features' in d and 'git_state' not in d"; then
    pass "purlin_scan: only=features filters output correctly"
else
    fail "purlin_scan: only=features did not filter correctly"
fi

# 6. tombstones=true includes tombstones
RESP="$(call_mcp_tool "purlin_scan" '{"tombstones":true}' 6)"
TEXT="$(echo "$RESP" | extract_text)"
TOMB_COUNT="$(echo "$TEXT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(len([f for f in d.get('features', []) if f.get('tombstone')]))
" 2>/dev/null)"
if [[ "$TOMB_COUNT" -ge 1 ]]; then
    pass "purlin_scan: tombstones=true includes $TOMB_COUNT tombstone(s)"
else
    fail "purlin_scan: tombstones=true found 0 tombstones"
fi

# 7. default scan excludes tombstones
RESP="$(call_mcp_tool "purlin_scan" '{"tombstones":false}' 7)"
TEXT="$(echo "$RESP" | extract_text)"
TOMB_COUNT="$(echo "$TEXT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(len([f for f in d.get('features', []) if f.get('tombstone')]))
" 2>/dev/null)"
if [[ "$TOMB_COUNT" -eq 0 ]]; then
    pass "purlin_scan: tombstones=false excludes tombstones"
else
    fail "purlin_scan: tombstones=false still has $TOMB_COUNT tombstone(s)"
fi

# ---------------------------------------------------------------------------
# purlin_classify Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== purlin_classify Tests ==="

# Helper: test classification
test_classify() {
    local filepath="$1"
    local expected="$2"
    local label="$3"
    local id="$4"
    local resp
    resp="$(call_mcp_tool "purlin_classify" "{\"filepath\":\"$filepath\"}" "$id")"
    local text
    text="$(echo "$resp" | extract_text)"
    local actual
    actual="$(echo "$text" | json_field "d.get('classification', '')")"
    if [[ "$actual" == "$expected" ]]; then
        pass "purlin_classify: $label -> $expected"
    else
        fail "purlin_classify: $label -> expected $expected, got $actual"
    fi
}

# 8. src/app.py -> CODE
test_classify "src/app.py" "CODE" "src/app.py" 8

# 9. features/user_auth.md -> SPEC
test_classify "features/core/user_auth.md" "SPEC" "features/core/user_auth.md" 9

# 10. features/i_arch_security.md -> INVARIANT
test_classify "features/_invariants/i_arch_security.md" "INVARIANT" "features/_invariants/i_arch_security.md" 10

# 11. features/api_endpoints.discoveries.md -> QA
test_classify "features/core/api_endpoints.discoveries.md" "QA" "features/core/api_endpoints.discoveries.md" 11

# 12. features/api_endpoints.impl.md -> CODE (companion)
test_classify "features/core/api_endpoints.impl.md" "CODE" "features/core/api_endpoints.impl.md" 12

# 13. README.md -> CODE (default)
test_classify "README.md" "CODE" "README.md" 13

# ---------------------------------------------------------------------------
# purlin_sync Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== purlin_sync Tests ==="

# 14. sync returns features dict
RESP="$(call_mcp_tool "purlin_sync" '{}' 14)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "'features' in d"; then
    pass "purlin_sync: returns features dict"
else
    fail "purlin_sync: missing features key"
fi

# 15. sync with feature filter returns dict
RESP="$(call_mcp_tool "purlin_sync" '{"feature":"nonexistent"}' 15)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "isinstance(d, dict)"; then
    pass "purlin_sync: feature filter returns dict"
else
    fail "purlin_sync: feature filter failed"
fi

# ---------------------------------------------------------------------------
# purlin_config Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== purlin_config Tests ==="

# 18. read returns config with agents.purlin
RESP="$(call_mcp_tool "purlin_config" '{"action":"read"}' 18)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "'agents' in d and 'purlin' in d.get('agents', {})"; then
    pass "purlin_config: read returns agents.purlin"
else
    fail "purlin_config: read missing agents.purlin"
fi

# 19. read returns local override (opus model from config.local.json)
MODEL="$(echo "$TEXT" | json_field "d.get('agents', {}).get('purlin', {}).get('model', '')")"
if echo "$MODEL" | grep -q "opus"; then
    pass "purlin_config: read returns opus model from local override"
else
    fail "purlin_config: expected opus model, got: $MODEL"
fi

# 20. config has bypass_permissions=true
BP="$(echo "$TEXT" | json_field "d.get('agents', {}).get('purlin', {}).get('bypass_permissions')")"
if [[ "$BP" == "true" ]]; then
    pass "purlin_config: bypass_permissions is true"
else
    fail "purlin_config: bypass_permissions is '$BP', expected 'true'"
fi

# ---------------------------------------------------------------------------
# purlin_graph Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== purlin_graph Tests ==="

# 21. regenerate returns graph data
RESP="$(call_mcp_tool "purlin_graph" '{"regenerate":true}' 21)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "'features' in d or 'total' in d"; then
    pass "purlin_graph: regenerate returns graph data"
else
    fail "purlin_graph: regenerate missing expected keys"
fi

# 22. graph has features list with entries
GRAPH_FEAT_COUNT="$(echo "$TEXT" | json_field "len(d.get('features', []))")"
if [[ "$GRAPH_FEAT_COUNT" -ge 1 ]]; then
    pass "purlin_graph: has $GRAPH_FEAT_COUNT features in graph"
else
    fail "purlin_graph: no features in graph"
fi

# ---------------------------------------------------------------------------
# purlin_status Tests
# ---------------------------------------------------------------------------
echo ""
echo "=== purlin_status Tests ==="

# 23. engineer mode status returns scan data
RESP="$(call_mcp_tool "purlin_status" '{"mode":"engineer"}' 23)"
TEXT="$(echo "$RESP" | extract_text)"
if echo "$TEXT" | json_check "'scan' in d and 'mode' in d"; then
    pass "purlin_status: engineer mode returns scan and mode"
else
    fail "purlin_status: engineer mode missing expected keys"
fi

# 24. status scan contains features
if echo "$TEXT" | json_check "'features' in d.get('scan', {})"; then
    pass "purlin_status: scan contains features"
else
    fail "purlin_status: scan missing features"
fi

# ---------------------------------------------------------------------------
# Clean up
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== MCP Tests Summary ==="
echo "Total: $TOTAL  Passed: $PASS  Failed: $FAIL"

if [[ "$FAIL" -gt 0 ]]; then
    echo "RESULT: FAIL"
    exit 1
else
    echo "RESULT: PASS"
    exit 0
fi
