#!/usr/bin/env bash
# Test: Help output flag references in the purlin:resume skill.
# Verifies the resume skill file contains --yolo, --no-yolo, and --no-save.
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

passed=0
failed=0

skill_file="$PROJECT_ROOT/skills/resume/SKILL.md"

if [[ ! -f "$skill_file" ]]; then
    echo "FAIL: resume skill file not found at $skill_file"
    exit 1
fi

# Check 1: --yolo flag present
if grep -q -- '--yolo' "$skill_file"; then
    echo "resume skill contains --yolo"
    ((passed++))
else
    echo "FAIL: resume skill missing --yolo flag"
    ((failed++))
fi

# Check 2: --no-yolo flag present
if grep -q -- '--no-yolo' "$skill_file"; then
    echo "resume skill contains --no-yolo"
    ((passed++))
else
    echo "FAIL: resume skill missing --no-yolo flag"
    ((failed++))
fi

# Check 3: --no-save flag present
if grep -q -- '--no-save' "$skill_file"; then
    echo "resume skill contains --no-save"
    ((passed++))
else
    echo "FAIL: resume skill missing --no-save flag"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
