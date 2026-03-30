#!/usr/bin/env bash
# Test: Help output flag references in the purlin:resume skill.
# Verifies the resume skill file contains --yolo, --no-yolo, and --no-save.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"

skill_file="$PROJECT_ROOT/skills/resume/SKILL.md"

if [[ ! -f "$skill_file" ]]; then
    echo "FAIL: resume skill file not found"
    exit 0
fi

# Check 1: --yolo flag present
if grep -q -- '--yolo' "$skill_file"; then
    echo "resume skill contains --yolo"
else
    echo "FAIL: resume skill missing --yolo flag"
fi

# Check 2: --no-yolo flag present
if grep -q -- '--no-yolo' "$skill_file"; then
    echo "resume skill contains --no-yolo"
else
    echo "FAIL: resume skill missing --no-yolo flag"
fi

# Check 3: --no-save flag present
if grep -q -- '--no-save' "$skill_file"; then
    echo "resume skill contains --no-save"
else
    echo "FAIL: resume skill missing --no-save flag"
fi

# Always exit 0 — harness evaluates assertions against output
exit 0
