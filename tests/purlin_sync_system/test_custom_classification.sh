#!/usr/bin/env bash
# Test: Custom file classification via CLAUDE.md
# Verifies that classify_file() reads project-specific overrides from CLAUDE.md
# and that UNKNOWN files are correctly identified when no rule matches.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"

passed=0
failed=0
total=0

# Create a temp directory for isolated test projects
TEST_ROOT=""
cleanup() {
    if [[ -n "$TEST_ROOT" && -d "$TEST_ROOT" ]]; then
        rm -rf "$TEST_ROOT"
    fi
}
trap cleanup EXIT

setup_test_project() {
    TEST_ROOT="$(cd "$(mktemp -d -t purlin-classify-XXXXXX)" && pwd -P)"
    local project="$TEST_ROOT/project"
    mkdir -p "$project/.purlin"
    echo "$project"
}

# classify with a specific project root (to pick up its CLAUDE.md)
classify() {
    local project_root="$1" filepath="$2"
    PURLIN_PROJECT_ROOT="$project_root" PURLIN_PLUGIN_ROOT="$PLUGIN_ROOT" PURLIN_CLASSIFY_PATH="$filepath" python3 -c "
import sys, os, importlib
os.environ['PURLIN_PROJECT_ROOT'] = os.environ['PURLIN_PROJECT_ROOT']
sys.path.insert(0, os.path.join(os.environ['PURLIN_PLUGIN_ROOT'], 'scripts', 'mcp'))
# Force reimport to clear cached classifications
if 'config_engine' in sys.modules:
    mod = sys.modules['config_engine']
    if hasattr(mod._read_claude_md_classifications, '_cache'):
        del mod._read_claude_md_classifications._cache
    importlib.reload(mod)
from config_engine import classify_file
print(classify_file(os.environ['PURLIN_CLASSIFY_PATH']))
" 2>/dev/null
}

assert_class() {
    local desc="$1" expected="$2" project_root="$3" filepath="$4"
    ((total++))
    local actual
    actual=$(classify "$project_root" "$filepath")
    if [ "$expected" = "$actual" ]; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (expected '$expected', got '$actual')"
        ((failed++))
    fi
}

###############################################################################
echo "=== UNKNOWN files (no custom rules) ==="
###############################################################################

PROJECT=$(setup_test_project)

# docs/ is not in the built-in rules — should be UNKNOWN
assert_class "docs/ file is UNKNOWN without custom rules" \
    "UNKNOWN" "$PROJECT" "docs/guide.md"

assert_class "random unclassified file is UNKNOWN" \
    "UNKNOWN" "$PROJECT" "misc/notes.txt"

# Built-in rules still work
assert_class "skills/ still classified as CODE" \
    "CODE" "$PROJECT" "skills/build/SKILL.md"

assert_class "features/ still classified as SPEC" \
    "SPEC" "$PROJECT" "features/my_feature.md"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== Custom CLAUDE.md classifications ==="
###############################################################################

PROJECT=$(setup_test_project)

cat > "$PROJECT/CLAUDE.md" <<'EOF'
# My Project

Some instructions here.

## Purlin File Classifications
- `docs/` → SPEC
- `config/` → CODE
- `static/` → QA

## Other Section

More stuff.
EOF

assert_class "docs/ classified as SPEC via CLAUDE.md" \
    "SPEC" "$PROJECT" "docs/guide.md"

assert_class "docs/ nested path classified as SPEC" \
    "SPEC" "$PROJECT" "docs/api/reference.md"

assert_class "config/ classified as CODE via CLAUDE.md" \
    "CODE" "$PROJECT" "config/settings.yaml"

assert_class "static/ classified as QA via CLAUDE.md" \
    "QA" "$PROJECT" "static/test-data.json"

# Built-in rules still work alongside custom rules
assert_class "skills/ still CODE with custom rules present" \
    "CODE" "$PROJECT" "skills/build/SKILL.md"

assert_class "features/ still SPEC with custom rules present" \
    "SPEC" "$PROJECT" "features/my_feature.md"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== Custom rules override built-in rules (non-protected paths) ==="
###############################################################################

PROJECT=$(setup_test_project)

cat > "$PROJECT/CLAUDE.md" <<'EOF'
## Purlin File Classifications
- `src/` → SPEC
EOF

# src/ is CODE by default, but custom rule says SPEC — and src/ is not a protected prefix
assert_class "custom rule overrides built-in for non-protected path" \
    "SPEC" "$PROJECT" "src/app.py"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== INVARIANT cannot be assigned via CLAUDE.md ==="
###############################################################################

PROJECT=$(setup_test_project)

cat > "$PROJECT/CLAUDE.md" <<'EOF'
## Purlin File Classifications
- `secrets/` → INVARIANT
- `docs/` → SPEC
EOF

# INVARIANT assignment should be ignored
assert_class "INVARIANT assignment ignored — stays UNKNOWN" \
    "UNKNOWN" "$PROJECT" "secrets/keys.json"

# Non-INVARIANT rules in same file still work
assert_class "SPEC assignment works alongside ignored INVARIANT" \
    "SPEC" "$PROJECT" "docs/guide.md"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== Consumer projects CAN reclassify their own directories ==="
###############################################################################

PROJECT=$(setup_test_project)

cat > "$PROJECT/CLAUDE.md" <<'EOF'
## Purlin File Classifications
- `scripts/` → SPEC
- `docs/` → SPEC
EOF

# Consumer's own scripts/ directory can be reclassified
assert_class "consumer can reclassify their own scripts/ as SPEC" \
    "SPEC" "$PROJECT" "scripts/deploy.sh"

assert_class "consumer can reclassify their own docs/ as SPEC" \
    "SPEC" "$PROJECT" "docs/guide.md"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== Custom rules only match project-relative paths ==="
###############################################################################

PROJECT=$(setup_test_project)

cat > "$PROJECT/CLAUDE.md" <<'EOF'
## Purlin File Classifications
- `skills/` → SPEC
EOF

# Relative path (project file) — custom rule applies
assert_class "relative path matches custom rule" \
    "SPEC" "$PROJECT" "skills/my-skill/SKILL.md"

# Absolute path (simulating plugin file outside project) — custom rule does NOT apply
assert_class "absolute path immune to custom rules" \
    "CODE" "$PROJECT" "/Users/someone/.claude/plugins/purlin/skills/build/SKILL.md"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== No CLAUDE.md file ==="
###############################################################################

PROJECT=$(setup_test_project)
# No CLAUDE.md at all — should fall through to built-in rules

assert_class "no CLAUDE.md: built-in CODE still works" \
    "CODE" "$PROJECT" "scripts/foo.sh"

assert_class "no CLAUDE.md: unclassified file is UNKNOWN" \
    "UNKNOWN" "$PROJECT" "docs/guide.md"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== Malformed CLAUDE.md ==="
###############################################################################

PROJECT=$(setup_test_project)

cat > "$PROJECT/CLAUDE.md" <<'EOF'
## Purlin File Classifications
- `docs/` → SPEC
- this line is malformed and should be ignored
- `config/` → INVALID_CLASS
- `valid/` → CODE
EOF

assert_class "valid rule still works in malformed file" \
    "SPEC" "$PROJECT" "docs/guide.md"

assert_class "invalid classification ignored" \
    "UNKNOWN" "$PROJECT" "config/settings.yaml"

assert_class "valid rule after invalid still works" \
    "CODE" "$PROJECT" "valid/file.py"

cleanup
TEST_ROOT=""

###############################################################################
# Summary
###############################################################################

echo ""
echo "==============================="
echo "Results: $passed/$total passed, $failed failed"
echo "==============================="

if [[ $failed -gt 0 ]]; then
    exit 1
fi
exit 0
