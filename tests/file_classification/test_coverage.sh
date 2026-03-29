#!/usr/bin/env bash
# Test: All standard file types are classified in file_classification.md
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
FC="$PROJECT_ROOT/references/file_classification.md"

passed=0
failed=0

if [[ ! -f "$FC" ]]; then
    echo "FAIL: file_classification.md not found"
    exit 1
fi

content=$(cat "$FC")

# Check CODE section has source, scripts, tests
code_ok=true
for pattern in "Source code" "Scripts" "Tests" "Hooks"; do
    if ! echo "$content" | grep -q "$pattern"; then
        code_ok=false
    fi
done
if $code_ok; then
    echo "CODE section covers source and scripts"
    ((passed++))
else
    echo "FAIL: CODE section missing expected patterns"
    ((failed++))
fi

# Check SPEC section has features and anchors
spec_ok=true
for pattern in "Feature specs" "Design anchors" "Policy anchors"; do
    if ! echo "$content" | grep -q "$pattern"; then
        spec_ok=false
    fi
done
if $spec_ok; then
    echo "SPEC section covers features and anchors"
    ((passed++))
else
    echo "FAIL: SPEC section missing expected patterns"
    ((failed++))
fi

# Check QA-OWNED section has discoveries and regression
qa_ok=true
for pattern in "Discovery sidecars" "Regression" "regression"; do
    if ! echo "$content" | grep -qi "$pattern"; then
        qa_ok=false
    fi
done
if $qa_ok; then
    echo "QA-OWNED section covers discoveries and regression"
    ((passed++))
else
    echo "FAIL: QA-OWNED section missing expected patterns"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
