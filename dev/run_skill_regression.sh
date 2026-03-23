#!/usr/bin/env bash
# Run skill behavior regression tests.
#
# Purlin-dev convenience wrapper. Resolves the fixture repo,
# runs setup if needed, and invokes the harness runner.
#
# Usage:
#   ./dev/run_skill_regression.sh
#
# See features/skill_behavior_regression.md for full specification.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SCENARIO_FILE="$PROJECT_ROOT/tests/qa/scenarios/skill_behavior_regression.json"
HARNESS_RUNNER="$PROJECT_ROOT/tools/test_support/harness_runner.py"
SETUP_SCRIPT="$PROJECT_ROOT/dev/setup_fixture_repo.sh"

# Verify scenario file exists
if [ ! -f "$SCENARIO_FILE" ]; then
    echo "Error: scenario file not found: $SCENARIO_FILE" >&2
    exit 1
fi

# Verify harness runner exists
if [ ! -f "$HARNESS_RUNNER" ]; then
    echo "Error: harness runner not found: $HARNESS_RUNNER" >&2
    exit 1
fi

# Resolve fixture repo via three-tier lookup
FIXTURE_REPO=""

# Tier 1: per-feature metadata (embedded in scenario JSON via fixture_tag)
# Tier 2: config fixture_repo_url
if [ -f "$PROJECT_ROOT/.purlin/config.json" ]; then
    FIXTURE_REPO=$(python3 -c "
import json, sys
try:
    with open('$PROJECT_ROOT/.purlin/config.json') as f:
        print(json.load(f).get('fixture_repo_url', ''))
except: pass
" 2>/dev/null)
fi

# Tier 3: convention path
if [ -z "$FIXTURE_REPO" ]; then
    FIXTURE_REPO="$PROJECT_ROOT/.purlin/runtime/fixture-repo"
fi

# Run setup if fixture repo is missing
if [ ! -d "$FIXTURE_REPO" ] && [ -f "$SETUP_SCRIPT" ]; then
    echo "Fixture repo not found. Running setup script..."
    bash "$SETUP_SCRIPT"
fi

# Invoke harness runner
echo "Running skill behavior regression tests..."
echo ""

PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 "$HARNESS_RUNNER" "$SCENARIO_FILE" --project-root "$PROJECT_ROOT"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "All skill behavior tests passed."
else
    echo ""
    echo "Some skill behavior tests failed. See tests/skill_behavior_regression/tests.json"
fi

exit $EXIT_CODE
