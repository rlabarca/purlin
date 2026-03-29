#!/usr/bin/env bash
# Test: Mode shortening is case-insensitive and handles all documented inputs
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
identity_sh="$PROJECT_ROOT/scripts/terminal/identity.sh"

passed=0
failed=0

if [[ ! -f "$identity_sh" ]]; then
    echo "FAIL: identity.sh not found"
    exit 1
fi

source "$identity_sh" 2>/dev/null

# Test case-insensitive mode shortening
all_ok=true

# Standard cases (already tested in test_badge_format.sh but we test case variants)
for input_mode in "Engineer" "engineer"; do
    result=$(_purlin_short_mode "$input_mode")
    if [[ "$result" != "Eng" ]]; then
        echo "FAIL: _purlin_short_mode '$input_mode' = '$result', expected 'Eng'"
        all_ok=false
    fi
done

for input_mode in "PM" "pm" "Pm"; do
    result=$(_purlin_short_mode "$input_mode")
    if [[ "$result" != "PM" ]]; then
        echo "FAIL: _purlin_short_mode '$input_mode' = '$result', expected 'PM'"
        all_ok=false
    fi
done

for input_mode in "QA" "qa" "Qa"; do
    result=$(_purlin_short_mode "$input_mode")
    if [[ "$result" != "QA" ]]; then
        echo "FAIL: _purlin_short_mode '$input_mode' = '$result', expected 'QA'"
        all_ok=false
    fi
done

if $all_ok; then
    echo "case-insensitive mode shortening works"
    ((passed++))
else
    ((failed++))
fi

# Test empty and "none" inputs both produce "Purlin"
empty_ok=true
for input_mode in "" "none"; do
    result=$(_purlin_short_mode "$input_mode")
    if [[ "$result" != "Purlin" ]]; then
        echo "FAIL: _purlin_short_mode '$input_mode' = '$result', expected 'Purlin'"
        empty_ok=false
    fi
done
if $empty_ok; then
    echo "empty and none modes produce Purlin"
    ((passed++))
else
    ((failed++))
fi

# Test unknown mode passes through unchanged
result=$(_purlin_short_mode "Custom")
if [[ "$result" == "Custom" ]]; then
    echo "custom mode passes through unchanged"
    ((passed++))
else
    echo "FAIL: _purlin_short_mode 'Custom' = '$result', expected 'Custom'"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
