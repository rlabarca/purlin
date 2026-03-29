#!/usr/bin/env bash
# Test: Instruction stack assembly for Purlin unified agent.
# Verifies PURLIN_BASE.md and PURLIN_OVERRIDES.md exist and
# the harness runner's construct_system_prompt handles the PURLIN role.
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

passed=0
failed=0

# Check 1: PURLIN_BASE.md exists in instructions/
if [[ -f "$PROJECT_ROOT/instructions/PURLIN_BASE.md" ]]; then
    echo "PURLIN_BASE.md found in instructions"
    ((passed++))
else
    echo "FAIL: PURLIN_BASE.md not found in instructions/"
    ((failed++))
fi

# Check 2: PURLIN_OVERRIDES.md exists in .purlin/
if [[ -f "$PROJECT_ROOT/.purlin/PURLIN_OVERRIDES.md" ]]; then
    echo "PURLIN_OVERRIDES.md found in .purlin"
    ((passed++))
else
    echo "FAIL: PURLIN_OVERRIDES.md not found in .purlin/"
    ((failed++))
fi

# Check 3: construct_system_prompt in harness_runner.py handles PURLIN role
harness="$PROJECT_ROOT/scripts/test_support/harness_runner.py"
if [[ -f "$harness" ]]; then
    if grep -q "if role == 'PURLIN'" "$harness"; then
        # Verify it loads the correct two-layer stack (PURLIN_BASE + PURLIN_OVERRIDES)
        if grep -q "PURLIN_BASE.md" "$harness" && grep -q "PURLIN_OVERRIDES.md" "$harness"; then
            echo "construct_system_prompt handles PURLIN role"
            ((passed++))
        else
            echo "FAIL: construct_system_prompt missing PURLIN layer file references"
            ((failed++))
        fi
    else
        echo "FAIL: construct_system_prompt does not handle PURLIN role"
        ((failed++))
    fi
else
    echo "FAIL: harness_runner.py not found"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
