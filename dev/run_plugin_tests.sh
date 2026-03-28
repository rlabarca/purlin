#!/usr/bin/env bash
# dev/run_plugin_tests.sh
#
# Top-level runner for all Purlin plugin test suites.
# Provisions the fixture if needed, runs each test script,
# and prints an aggregated summary.
#
# Usage:
#   ./dev/run_plugin_tests.sh [--help]
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'HELP'
Usage: run_plugin_tests.sh [--help]

Runs all Purlin plugin test suites:

  1. setup_plugin_test_fixture.sh  (provision fixture if needed)
  2. test_plugin_hooks.sh          (hook script integration tests)
  3. test_plugin_mcp.sh            (MCP server JSON-RPC tests)
  4. test_plugin_classify.py       (file classification unit tests)
  5. test_plugin_config.py         (config resolution unit tests)
  6. test_plugin_scan.py           (scan engine integration tests)

Aggregates PASS/FAIL from all suites and prints a summary.
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

echo "============================================="
echo "  Purlin Plugin Test Runner"
echo "============================================="
echo ""
echo "Plugin root: $PLUGIN_ROOT"
echo "Fixture dir: $FIXTURE_DIR"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Provision fixture if needed
# ---------------------------------------------------------------------------
echo "--- Step 1: Fixture Setup ---"

SETUP_SCRIPT="$PLUGIN_ROOT/dev/setup_plugin_test_fixture.sh"

if [[ ! -d "$FIXTURE_DIR/.purlin" ]]; then
    if [[ -f "$SETUP_SCRIPT" ]]; then
        echo "Fixture not found. Running setup..."
        bash "$SETUP_SCRIPT"
        echo ""
    else
        echo "ERROR: Fixture not found and setup script missing: $SETUP_SCRIPT"
        exit 1
    fi
else
    echo "Fixture already exists at $FIXTURE_DIR"
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 2: Run test suites
# ---------------------------------------------------------------------------
SUITES_PASS=0
SUITES_FAIL=0
SUITES_SKIP=0
SUITES_TOTAL=0
RESULTS=()

run_suite() {
    local name="$1"
    local command="$2"
    ((SUITES_TOTAL++))

    echo "--- $name ---"

    local ec=0
    eval "$command" || ec=$?

    if [[ "$ec" -eq 0 ]]; then
        ((SUITES_PASS++))
        RESULTS+=("PASS  $name")
    else
        ((SUITES_FAIL++))
        RESULTS+=("FAIL  $name (exit $ec)")
    fi
    echo ""
}

# Suite 1: Hook tests (bash)
HOOKS_SCRIPT="$PLUGIN_ROOT/dev/test_plugin_hooks.sh"
if [[ -f "$HOOKS_SCRIPT" ]]; then
    run_suite "test_plugin_hooks.sh" "bash '$HOOKS_SCRIPT'"
else
    echo "--- test_plugin_hooks.sh --- SKIP (not found)"
    ((SUITES_SKIP++))
    ((SUITES_TOTAL++))
    RESULTS+=("SKIP  test_plugin_hooks.sh (not found)")
    echo ""
fi

# Suite 2: MCP tests (bash)
MCP_SCRIPT="$PLUGIN_ROOT/dev/test_plugin_mcp.sh"
if [[ -f "$MCP_SCRIPT" ]]; then
    run_suite "test_plugin_mcp.sh" "bash '$MCP_SCRIPT'"
else
    echo "--- test_plugin_mcp.sh --- SKIP (not found)"
    ((SUITES_SKIP++))
    ((SUITES_TOTAL++))
    RESULTS+=("SKIP  test_plugin_mcp.sh (not found)")
    echo ""
fi

# Suite 3: Classify tests (python)
CLASSIFY_SCRIPT="$PLUGIN_ROOT/dev/test_plugin_classify.py"
if [[ -f "$CLASSIFY_SCRIPT" ]]; then
    run_suite "test_plugin_classify.py" "python3 -m pytest '$CLASSIFY_SCRIPT' -v 2>&1 || python3 '$CLASSIFY_SCRIPT' 2>&1"
else
    echo "--- test_plugin_classify.py --- SKIP (not found)"
    ((SUITES_SKIP++))
    ((SUITES_TOTAL++))
    RESULTS+=("SKIP  test_plugin_classify.py (not found)")
    echo ""
fi

# Suite 4: Config tests (python)
CONFIG_SCRIPT="$PLUGIN_ROOT/dev/test_plugin_config.py"
if [[ -f "$CONFIG_SCRIPT" ]]; then
    run_suite "test_plugin_config.py" "python3 -m pytest '$CONFIG_SCRIPT' -v 2>&1 || python3 '$CONFIG_SCRIPT' 2>&1"
else
    echo "--- test_plugin_config.py --- SKIP (not found)"
    ((SUITES_SKIP++))
    ((SUITES_TOTAL++))
    RESULTS+=("SKIP  test_plugin_config.py (not found)")
    echo ""
fi

# Suite 5: Scan tests (python)
SCAN_SCRIPT="$PLUGIN_ROOT/dev/test_plugin_scan.py"
if [[ -f "$SCAN_SCRIPT" ]]; then
    run_suite "test_plugin_scan.py" "python3 -m pytest '$SCAN_SCRIPT' -v 2>&1 || python3 '$SCAN_SCRIPT' 2>&1"
else
    echo "--- test_plugin_scan.py --- SKIP (not found)"
    ((SUITES_SKIP++))
    ((SUITES_TOTAL++))
    RESULTS+=("SKIP  test_plugin_scan.py (not found)")
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 3: Aggregated Summary
# ---------------------------------------------------------------------------
echo "============================================="
echo "  Plugin Test Results"
echo "============================================="
echo ""
for r in "${RESULTS[@]}"; do
    echo "  $r"
done
echo ""
echo "Suites: $SUITES_TOTAL total, $SUITES_PASS passed, $SUITES_FAIL failed, $SUITES_SKIP skipped"
echo ""

if [[ "$SUITES_FAIL" -gt 0 ]]; then
    echo "OVERALL: FAIL"
    exit 1
else
    echo "OVERALL: PASS"
    exit 0
fi
