#!/bin/bash
# test_purlin_migration.sh -- Unit tests for tools/migration/migrate.py
# Covers the 9 unit test scenarios from features/purlin_migration.md Section 3.
#
# Produces tests/purlin_migration/tests.json
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
SCENARIOS=()
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); SCENARIOS+=("$1"); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); SCENARIOS+=("$1"); ERRORS="$ERRORS\n  FAIL: $1 — $2"; echo "  FAIL: $1 — $2"; }

cleanup_fixture() {
    if [ -n "${FIXTURE_DIR:-}" ] && [ -d "$FIXTURE_DIR" ]; then
        rm -rf "$FIXTURE_DIR"
    fi
}

# Run migrate.py against a fixture project root.
# Usage: run_migrate <fixture_root> [extra_args...]
# Sets MIGRATE_OUTPUT and MIGRATE_EXIT.
run_migrate() {
    local fixture_root="$1"
    shift
    local migrate_py="$PROJECT_ROOT/tools/migration/migrate.py"
    MIGRATE_OUTPUT=$(PURLIN_PROJECT_ROOT="$fixture_root" python3 "$migrate_py" --auto-approve "$@" 2>&1) || true
    MIGRATE_EXIT=$?
}

# Run migrate.py --detect-only against a fixture.
# Sets DETECT_OUTPUT and DETECT_EXIT.
run_detect() {
    local fixture_root="$1"
    shift
    local migrate_py="$PROJECT_ROOT/tools/migration/migrate.py"
    DETECT_OUTPUT=$(PURLIN_PROJECT_ROOT="$fixture_root" python3 "$migrate_py" --detect-only "$@" 2>&1)
    DETECT_EXIT=$?
}

# Read a JSON value from a file. Usage: json_from_file <file> <expr>
json_from_file() {
    python3 -c "
import sys, json
with open('$1') as f:
    d = json.load(f)
val = eval('d' + '''$2''')
if val is None:
    print('null')
elif isinstance(val, bool):
    print('true' if val else 'false')
elif isinstance(val, (list, dict)):
    print(json.dumps(val))
else:
    print(val)
" 2>/dev/null
}

###############################################################################
# Build a minimal fixture project with old 4-role config
###############################################################################
setup_fixture_old_config() {
    FIXTURE_DIR="$(mktemp -d)"
    mkdir -p "$FIXTURE_DIR/.purlin"
    mkdir -p "$FIXTURE_DIR/features"

    # Create old-style config.json with builder/architect but no purlin
    cat > "$FIXTURE_DIR/.purlin/config.json" << 'CONFIGEOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true
        },
        "pm": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true
        }
    }
}
CONFIGEOF
}

setup_fixture_migrated() {
    FIXTURE_DIR="$(mktemp -d)"
    mkdir -p "$FIXTURE_DIR/.purlin"
    mkdir -p "$FIXTURE_DIR/features"

    cat > "$FIXTURE_DIR/.purlin/config.json" << 'CONFIGEOF'
{
    "tools_root": "tools",
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false,
            "default_mode": null
        }
    }
}
CONFIGEOF
}

setup_fixture_fresh() {
    FIXTURE_DIR="$(mktemp -d)"
    mkdir -p "$FIXTURE_DIR/.purlin"

    cat > "$FIXTURE_DIR/.purlin/config.json" << 'CONFIGEOF'
{
    "tools_root": "tools"
}
CONFIGEOF
}

echo "=== Purlin Migration Tests ==="
echo ""

###############################################################################
# Scenario 1: Migration detected when old config present
###############################################################################
echo "--- Scenario 1: Migration detected when old config present ---"
setup_fixture_old_config

run_detect "$FIXTURE_DIR"
if [ "$DETECT_OUTPUT" = "needed" ] && [ "$DETECT_EXIT" -eq 0 ]; then
    log_pass "Migration detected when old config present"
else
    log_fail "Migration detected when old config present" "got output='$DETECT_OUTPUT' exit=$DETECT_EXIT"
fi
cleanup_fixture

###############################################################################
# Scenario 2: Migration skipped when already migrated
###############################################################################
echo "--- Scenario 2: Migration skipped when already migrated ---"
setup_fixture_migrated

run_detect "$FIXTURE_DIR"
if [ "$DETECT_OUTPUT" = "complete" ] && [ "$DETECT_EXIT" -eq 1 ]; then
    log_pass "Migration skipped when already migrated"
else
    log_fail "Migration skipped when already migrated" "got output='$DETECT_OUTPUT' exit=$DETECT_EXIT"
fi
cleanup_fixture

###############################################################################
# Scenario 3: Config migration creates purlin section
###############################################################################
echo "--- Scenario 3: Config migration creates purlin section ---"
setup_fixture_old_config

run_migrate "$FIXTURE_DIR"

config_file="$FIXTURE_DIR/.purlin/config.json"
purlin_model=$(json_from_file "$config_file" "['agents']['purlin']['model']")
purlin_default_mode=$(json_from_file "$config_file" "['agents']['purlin']['default_mode']")
builder_deprecated=$(json_from_file "$config_file" "['agents']['builder']['_deprecated']")

if [ "$purlin_model" = "claude-opus-4-6" ] && \
   [ "$purlin_default_mode" = "null" ] && \
   [ "$builder_deprecated" = "true" ]; then
    log_pass "Config migration creates purlin section"
else
    log_fail "Config migration creates purlin section" \
        "model=$purlin_model default_mode=$purlin_default_mode deprecated=$builder_deprecated"
fi
cleanup_fixture

###############################################################################
# Scenario 4: Override files consolidated
###############################################################################
echo "--- Scenario 4: Override files consolidated ---"
setup_fixture_old_config

# Create old override files
echo "use pytest" > "$FIXTURE_DIR/.purlin/BUILDER_OVERRIDES.md"
echo "smoke tier table" > "$FIXTURE_DIR/.purlin/QA_OVERRIDES.md"

run_migrate "$FIXTURE_DIR"

overrides_file="$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md"
if [ -f "$overrides_file" ]; then
    has_engineer=$(grep -c "## Engineer Mode" "$overrides_file" 2>/dev/null || true)
    has_pytest=$(grep -c "use pytest" "$overrides_file" 2>/dev/null || true)
    has_qa=$(grep -c "## QA Mode" "$overrides_file" 2>/dev/null || true)
    has_smoke=$(grep -c "smoke tier table" "$overrides_file" 2>/dev/null || true)

    if [ "$has_engineer" -ge 1 ] && [ "$has_pytest" -ge 1 ] && \
       [ "$has_qa" -ge 1 ] && [ "$has_smoke" -ge 1 ]; then
        log_pass "Override files consolidated"
    else
        log_fail "Override files consolidated" \
            "engineer=$has_engineer pytest=$has_pytest qa=$has_qa smoke=$has_smoke"
    fi
else
    log_fail "Override files consolidated" "PURLIN_OVERRIDES.md not created"
fi
cleanup_fixture

###############################################################################
# Scenario 5: Spec role renames use Migration tag
###############################################################################
echo "--- Scenario 5: Spec role renames use Migration tag ---"
setup_fixture_old_config

# Create a feature spec with old role references
cat > "$FIXTURE_DIR/features/auth_flow.md" << 'SPECEOF'
# Feature: Auth Flow

## Requirements

The Builder implements the login flow.
The Architect reviews the specification.
SPECEOF

run_migrate "$FIXTURE_DIR"

spec_file="$FIXTURE_DIR/features/auth_flow.md"
has_engineer=$(grep -c "Engineer mode implements" "$spec_file" 2>/dev/null || true)
# "The Architect" -> "PM mode"
has_pm_mode=$(grep -c "PM mode reviews" "$spec_file" 2>/dev/null || true)

if [ "$has_engineer" -ge 1 ] && [ "$has_pm_mode" -ge 1 ]; then
    log_pass "Spec role renames use Migration tag"
else
    content=$(cat "$spec_file")
    log_fail "Spec role renames use Migration tag" \
        "engineer=$has_engineer pm_mode=$has_pm_mode content: $content"
fi
cleanup_fixture

###############################################################################
# Scenario 6: Migration tag preserves lifecycle
# Sets up a git repo with a COMPLETE feature, runs migration to rename roles,
# commits with [Migration] tag, then verifies scan.py reports
# spec_modified_after_completion as false.
###############################################################################
echo "--- Scenario 6: Migration tag preserves lifecycle ---"

FIXTURE_DIR="$(mktemp -d)"
(
    cd "$FIXTURE_DIR"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"

    mkdir -p .purlin/cache features

    # Create old-style config
    cat > .purlin/config.json << 'CFGEOF'
{
    "tools_root": "tools",
    "agents": {
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true
        }
    }
}
CFGEOF

    # Create feature spec with old role references
    cat > features/auth_flow.md << 'SPECEOF'
# Feature: Auth Flow

## Requirements
The Builder implements the login flow.
SPECEOF

    git add -A && git commit -q -m "feat(auth): initial spec"

    # Mark feature as COMPLETE via status commit
    git commit -q --allow-empty -m "status(auth): [Complete features/auth_flow.md] [Scope: full]"

    # Now run migration to rename roles
    PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 "$PROJECT_ROOT/tools/migration/migrate.py" \
        --auto-approve --skip-overrides --skip-companions 2>/dev/null

    # Commit with [Migration] tag
    git add -A && git commit -q -m "chore(migration): rename role references [Migration]"

    # Run scan.py and check the result
    SCAN_JSON=$(PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 "$PROJECT_ROOT/tools/cdd/scan.py" 2>/dev/null)

    spec_modified=$(echo "$SCAN_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d.get('features', []):
    if f['name'] == 'auth_flow':
        print('true' if f.get('spec_modified_after_completion') else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

) >/dev/null 2>&1
scan_result=$(cd "$FIXTURE_DIR" && PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 "$PROJECT_ROOT/tools/cdd/scan.py" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d.get('features', []):
    if f['name'] == 'auth_flow':
        print('true' if f.get('spec_modified_after_completion') else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$scan_result" = "false" ]; then
    log_pass "Migration tag preserves lifecycle"
else
    log_fail "Migration tag preserves lifecycle" "spec_modified_after_completion=$scan_result (expected false)"
fi
rm -rf "$FIXTURE_DIR"

###############################################################################
# Scenario 7: Companion file gets Active Deviations table
###############################################################################
echo "--- Scenario 7: Companion file gets Active Deviations table ---"
setup_fixture_old_config

# Create a companion file with a DEVIATION tag but no table
cat > "$FIXTURE_DIR/features/auth_flow.impl.md" << 'IMPLEOF'
# Implementation Notes: Auth Flow

## Notes

**[DEVIATION]** Used JWT instead of session cookies (Severity: HIGH)

Some other prose content here.
IMPLEOF

run_migrate "$FIXTURE_DIR"

impl_file="$FIXTURE_DIR/features/auth_flow.impl.md"
has_table=$(grep -c "## Active Deviations" "$impl_file" 2>/dev/null || true)
has_row=$(grep -c "DEVIATION" "$impl_file" 2>/dev/null || true)
has_prose=$(grep -c "Some other prose content" "$impl_file" 2>/dev/null || true)

# Table should exist, tag should appear in a table row, and prose preserved
if [ "$has_table" -ge 1 ] && [ "$has_row" -ge 1 ] && [ "$has_prose" -ge 1 ]; then
    log_pass "Companion file gets Active Deviations table"
else
    log_fail "Companion file gets Active Deviations table" \
        "table=$has_table row=$has_row prose=$has_prose"
fi
cleanup_fixture

###############################################################################
# Scenario 8: Dry run shows changes without modifying
###############################################################################
echo "--- Scenario 8: Dry run shows changes without modifying ---"
setup_fixture_old_config

# Record original content
orig_config=$(cat "$FIXTURE_DIR/.purlin/config.json")

run_migrate "$FIXTURE_DIR" --dry-run

# Verify output mentions dry run
has_dry_run=$(echo "$MIGRATE_OUTPUT" | grep -ci "dry run" || true)

# Verify files unchanged
new_config=$(cat "$FIXTURE_DIR/.purlin/config.json")
no_purlin_overrides=true
[ -f "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" ] && no_purlin_overrides=false

if [ "$has_dry_run" -ge 1 ] && [ "$orig_config" = "$new_config" ] && $no_purlin_overrides; then
    log_pass "Dry run shows changes without modifying"
else
    log_fail "Dry run shows changes without modifying" \
        "dry_run_msg=$has_dry_run config_same=$([ "$orig_config" = "$new_config" ] && echo true || echo false) no_overrides=$no_purlin_overrides"
fi
cleanup_fixture

###############################################################################
# Scenario 9: Skip flags exclude steps
###############################################################################
echo "--- Scenario 9: Skip flags exclude steps ---"
setup_fixture_old_config

# Create override and companion files
echo "use pytest" > "$FIXTURE_DIR/.purlin/BUILDER_OVERRIDES.md"
cat > "$FIXTURE_DIR/features/auth_flow.md" << 'SPECEOF'
# Feature: Auth Flow
The Builder implements the login flow.
SPECEOF
cat > "$FIXTURE_DIR/features/auth_flow.impl.md" << 'IMPLEOF'
# Implementation Notes: Auth Flow
**[DEVIATION]** Used JWT (Severity: HIGH)
IMPLEOF

run_migrate "$FIXTURE_DIR" --skip-specs --skip-companions

# Config should be migrated
config_file="$FIXTURE_DIR/.purlin/config.json"
has_purlin=$(json_from_file "$config_file" "['agents']['purlin']['model']")

# Overrides should be consolidated (not skipped)
has_overrides_file=false
[ -f "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" ] && has_overrides_file=true

# Spec should NOT be modified (--skip-specs)
spec_still_builder=$(grep -c "The Builder" "$FIXTURE_DIR/features/auth_flow.md" 2>/dev/null || true)

# Companion should NOT have table (--skip-companions)
impl_no_table=$(grep -c "## Active Deviations" "$FIXTURE_DIR/features/auth_flow.impl.md" 2>/dev/null || true)

if [ "$has_purlin" = "claude-opus-4-6" ] && \
   $has_overrides_file && \
   [ "$spec_still_builder" -ge 1 ] && \
   [ "$impl_no_table" -eq 0 ]; then
    log_pass "Skip flags exclude steps"
else
    log_fail "Skip flags exclude steps" \
        "purlin=$has_purlin overrides=$has_overrides_file builder_ref=$spec_still_builder table=$impl_no_table"
fi
cleanup_fixture

###############################################################################
# Scenario 10: Idempotent re-run
###############################################################################
echo "--- Scenario 10: Idempotent re-run ---"
setup_fixture_old_config

echo "use pytest" > "$FIXTURE_DIR/.purlin/BUILDER_OVERRIDES.md"
cat > "$FIXTURE_DIR/features/auth_flow.impl.md" << 'IMPLEOF'
# Implementation Notes: Auth Flow
**[DEVIATION]** Used JWT (Severity: HIGH)
IMPLEOF

# First run
run_migrate "$FIXTURE_DIR"

# Record state after first run
config_after_first=$(cat "$FIXTURE_DIR/.purlin/config.json")
overrides_after_first=$(cat "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md")
impl_after_first=$(cat "$FIXTURE_DIR/features/auth_flow.impl.md")

# Second run
run_migrate "$FIXTURE_DIR"

# Record state after second run
config_after_second=$(cat "$FIXTURE_DIR/.purlin/config.json")
overrides_after_second=$(cat "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" 2>/dev/null || echo "MISSING")
impl_after_second=$(cat "$FIXTURE_DIR/features/auth_flow.impl.md")

# Count Active Deviations tables (should be exactly 1)
table_count=$(grep -c "## Active Deviations" "$FIXTURE_DIR/features/auth_flow.impl.md" 2>/dev/null || true)

if [ "$config_after_first" = "$config_after_second" ] && \
   [ "$overrides_after_first" = "$overrides_after_second" ] && \
   [ "$impl_after_first" = "$impl_after_second" ] && \
   [ "$table_count" -eq 1 ]; then
    log_pass "Idempotent re-run"
else
    log_fail "Idempotent re-run" \
        "config_same=$([ "$config_after_first" = "$config_after_second" ] && echo true || echo false) overrides_same=$([ "$overrides_after_first" = "$overrides_after_second" ] && echo true || echo false) impl_same=$([ "$impl_after_first" = "$impl_after_second" ] && echo true || echo false) tables=$table_count"
fi
cleanup_fixture

###############################################################################
# Results
###############################################################################
echo ""
echo "=== Results ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "  Total: $((PASS + FAIL))"

if [ -n "$ERRORS" ]; then
    echo ""
    echo "Failures:"
    echo -e "$ERRORS"
fi

# Write tests.json
FEATURE_NAME="purlin_migration"
RESULT_DIR="$TESTS_DIR/$FEATURE_NAME"
mkdir -p "$RESULT_DIR"

STATUS="PASS"
[ "$FAIL" -gt 0 ] && STATUS="FAIL"

# Build scenarios JSON array
SCENARIO_JSON="["
for i in "${!SCENARIOS[@]}"; do
    [ "$i" -gt 0 ] && SCENARIO_JSON+=","
    SCENARIO_JSON+="\"${SCENARIOS[$i]}\""
done
SCENARIO_JSON+="]"

cat > "$RESULT_DIR/tests.json" << JSONEOF
{
  "feature": "$FEATURE_NAME",
  "status": "$STATUS",
  "passed": $PASS,
  "failed": $FAIL,
  "total": $((PASS + FAIL)),
  "test_file": "tools/test_purlin_migration.sh",
  "scenarios": $SCENARIO_JSON,
  "ran_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSONEOF

echo ""
echo "Results written to tests/$FEATURE_NAME/tests.json"

exit $FAIL
