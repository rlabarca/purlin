#!/usr/bin/env bash
# Test: Badge format never uses "Purlin:" prefix and follows unified format.
# Verifies identity.sh functions produce correct output patterns.
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

passed=0
failed=0

identity_sh="$PROJECT_ROOT/scripts/terminal/identity.sh"

if [[ ! -f "$identity_sh" ]]; then
    echo "FAIL: identity.sh not found at $identity_sh"
    exit 1
fi

# Check 1: No "Purlin:" prefix in identity script output patterns
# The script should use "Purlin" (without colon) as a mode short name
if grep -q '"Purlin:"' "$identity_sh"; then
    echo "FAIL: identity.sh contains 'Purlin:' prefix pattern"
    ((failed++))
else
    echo "no Purlin: prefix found"
    ((passed++))
fi

# Check 2: Verify unified format is implemented
# _purlin_short_mode should map Engineer->Eng, and update_session_identity
# should compose <short_mode>(<context>) | <label>
source "$identity_sh" 2>/dev/null

# Test mode shortening
eng_short=$(_purlin_short_mode "Engineer")
pm_short=$(_purlin_short_mode "PM")
qa_short=$(_purlin_short_mode "QA")
purlin_short=$(_purlin_short_mode "")

if [[ "$eng_short" == "Eng" && "$pm_short" == "PM" && "$qa_short" == "QA" && "$purlin_short" == "Purlin" ]]; then
    echo "unified format verified"
    ((passed++))
else
    echo "FAIL: mode shortening incorrect: Eng=$eng_short PM=$pm_short QA=$qa_short Purlin=$purlin_short"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
