#!/usr/bin/env bash
# tests/purlin_worktree/test_worktree_management.sh
#
# Regression tests for worktree management: manage.sh subcommands,
# session-end-merge.sh hook, session locks, and concurrent access protection.
#
# Creates a real git repo with worktrees in a temp directory.
# Does NOT touch the project repo.
#
# Usage:
#   bash tests/purlin_worktree/test_worktree_management.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANAGE_SH="$PROJECT_ROOT/scripts/worktree/manage.sh"
MERGE_HOOK="$PROJECT_ROOT/hooks/scripts/session-end-merge.sh"

PASSED=0
FAILED=0
TOTAL=0
TEST_ROOT=""

# --- Test helpers ---

cleanup() {
    if [[ -n "$TEST_ROOT" && -d "$TEST_ROOT" ]]; then
        # Remove worktrees before deleting the repo
        git -C "$TEST_ROOT/repo" worktree list --porcelain 2>/dev/null | \
            grep '^worktree ' | sed 's/worktree //' | while read -r wt; do
                [[ "$wt" == "$TEST_ROOT/repo" ]] && continue
                git -C "$TEST_ROOT/repo" worktree remove "$wt" --force 2>/dev/null || true
            done
        rm -rf "$TEST_ROOT"
    fi
}
trap cleanup EXIT

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if [[ "$expected" == "$actual" ]]; then
        echo "  PASS  $label"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $label"
        echo "        expected: $expected"
        echo "        got:      $actual"
        FAILED=$((FAILED + 1))
    fi
}

assert_contains() {
    local label="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$actual" | grep -q "$expected"; then
        echo "  PASS  $label"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $label (expected to contain: $expected)"
        echo "        got: $actual"
        FAILED=$((FAILED + 1))
    fi
}

assert_not_contains() {
    local label="$1" unexpected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if ! echo "$actual" | grep -q "$unexpected"; then
        echo "  PASS  $label"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $label (should NOT contain: $unexpected)"
        FAILED=$((FAILED + 1))
    fi
}

assert_file_exists() {
    local label="$1" filepath="$2"
    TOTAL=$((TOTAL + 1))
    if [[ -f "$filepath" ]]; then
        echo "  PASS  $label"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $label (file not found: $filepath)"
        FAILED=$((FAILED + 1))
    fi
}

assert_file_not_exists() {
    local label="$1" filepath="$2"
    TOTAL=$((TOTAL + 1))
    if [[ ! -f "$filepath" ]]; then
        echo "  PASS  $label"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $label (file should not exist: $filepath)"
        FAILED=$((FAILED + 1))
    fi
}

assert_dir_not_exists() {
    local label="$1" dirpath="$2"
    TOTAL=$((TOTAL + 1))
    if [[ ! -d "$dirpath" ]]; then
        echo "  PASS  $label"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $label (directory should not exist: $dirpath)"
        FAILED=$((FAILED + 1))
    fi
}

# Extract a JSON string value (simple single-line JSON)
json_val() {
    local json="$1" key="$2"
    echo "$json" | sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p"
}

json_num() {
    local json="$1" key="$2"
    echo "$json" | sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p"
}

json_bool() {
    local json="$1" key="$2"
    echo "$json" | sed -nE "s/.*\"$key\": *(true|false).*/\1/p"
}

# --- Fixture setup ---

setup_test_repo() {
    # Resolve real path to avoid /var vs /private/var symlink mismatch on macOS
    TEST_ROOT="$(cd "$(mktemp -d -t purlin-wt-test-XXXXXX)" && pwd -P)"
    local repo="$TEST_ROOT/repo"

    # Create a bare-minimum git repo with .purlin structure
    git init -q "$repo"
    mkdir -p "$repo/.purlin/worktrees" "$repo/.purlin/cache"
    echo "initial" > "$repo/README.md"

    cat > "$repo/.gitignore" <<'EOF'
.purlin/worktrees/
.purlin_worktree_label
.purlin_session.lock
.purlin/cache/merge.lock
EOF

    git -C "$repo" add -A
    git -C "$repo" commit -q -m "initial commit"

    echo "$repo"
}

# Create a purlin worktree in the test repo
# Usage: create_worktree <repo> <branch_name>
create_worktree() {
    local repo="$1" branch="$2"
    local wt_dir="$repo/.purlin/worktrees/$branch"
    git -C "$repo" worktree add -q "$wt_dir" -b "$branch" 2>/dev/null
    # Return the real path (resolves /var → /private/var on macOS)
    echo "$(cd "$wt_dir" && pwd -P)"
}

# Write a session lock file
# Usage: write_lock <wt_path> <pid> <mode> <label>
write_lock() {
    local wt_path="$1" pid="$2" mode="$3" label="$4"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cat > "$wt_path/.purlin_session.lock" <<EOF
{
  "pid": $pid,
  "started": "$ts",
  "mode": "$mode",
  "label": "$label"
}
EOF
}

write_label() {
    echo "$2" > "$1/.purlin_worktree_label"
}

###############################################################################
echo ""
echo "=== manage.sh list ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- list: empty (no worktrees) ---"
result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" list)
assert_contains "returns empty array" '"worktrees": \[\]' "$result"

echo "--- list: active worktree (live PID) ---"
WT1=$(create_worktree "$REPO" "purlin-engineer-20260325-140000")
write_lock "$WT1" "$$" "engineer" "W1"
write_label "$WT1" "W1"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" list)
assert_contains "has W1 label" '"label": "W1"' "$result"
assert_contains "status is active" '"status": "active"' "$result"
assert_contains "mode is engineer" '"mode": "engineer"' "$result"

echo "--- list: stale worktree (dead PID) ---"
WT2=$(create_worktree "$REPO" "purlin-pm-20260325-150000")
write_lock "$WT2" "99999" "pm" "W2"
write_label "$WT2" "W2"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" list)
assert_contains "has stale entry" '"status": "stale"' "$result"
assert_contains "has W2 label" '"label": "W2"' "$result"

echo "--- list: orphaned worktree (no lock) ---"
WT3=$(create_worktree "$REPO" "purlin-qa-20260325-160000")
write_label "$WT3" "W3"
# No lock file

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" list)
assert_contains "has orphaned entry" '"status": "orphaned"' "$result"

# Clean up this repo
cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== manage.sh check-lock ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- check-lock: no lock file (orphaned) ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260325-170000")
result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" check-lock "$WT")
assert_eq "safe is true" "true" "$(json_bool "$result" "safe")"
assert_eq "status is orphaned" "orphaned" "$(json_val "$result" "status")"

echo "--- check-lock: dead PID (stale) ---"
write_lock "$WT" "99999" "engineer" "W1"
result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" check-lock "$WT")
assert_eq "safe is true" "true" "$(json_bool "$result" "safe")"
assert_eq "status is stale" "stale" "$(json_val "$result" "status")"
assert_eq "pid is 99999" "99999" "$(json_num "$result" "pid")"

echo "--- check-lock: live PID (active) ---"
write_lock "$WT" "$$" "engineer" "W1"
result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" check-lock "$WT")
assert_eq "safe is false" "false" "$(json_bool "$result" "safe")"
assert_eq "status is active" "active" "$(json_val "$result" "status")"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== manage.sh claim ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- claim: stale worktree succeeds ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260325-180000")
write_lock "$WT" "99999" "engineer" "W1"
write_label "$WT" "W1"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" claim "$WT" --mode qa)
assert_eq "claimed is true" "true" "$(json_bool "$result" "claimed")"
assert_eq "label preserved" "W1" "$(json_val "$result" "label")"
assert_eq "mode updated to qa" "qa" "$(json_val "$result" "mode")"

# Verify lock file was actually updated
lock_content=$(cat "$WT/.purlin_session.lock")
assert_eq "lock mode is qa" "qa" "$(json_val "$lock_content" "mode")"

echo "--- claim: orphaned worktree succeeds ---"
WT2=$(create_worktree "$REPO" "purlin-pm-20260325-190000")
write_label "$WT2" "W2"
# No lock at all

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" claim "$WT2" --mode pm)
assert_eq "claimed is true" "true" "$(json_bool "$result" "claimed")"
assert_file_exists "lock file created" "$WT2/.purlin_session.lock"

echo "--- claim: active worktree rejected ---"
WT3=$(create_worktree "$REPO" "purlin-qa-20260325-200000")
write_lock "$WT3" "$$" "qa" "W3"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" claim "$WT3" --mode engineer 2>&1 || true)
assert_contains "rejected with error" "active session" "$result"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== manage.sh cleanup-stale ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- cleanup-stale: skips active, removes stale with no changes ---"
WT_ACTIVE=$(create_worktree "$REPO" "purlin-engineer-20260325-210000")
write_lock "$WT_ACTIVE" "$$" "engineer" "W1"
write_label "$WT_ACTIVE" "W1"

WT_STALE=$(create_worktree "$REPO" "purlin-pm-20260325-220000")
write_lock "$WT_STALE" "99999" "pm" "W2"
write_label "$WT_STALE" "W2"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" cleanup-stale 2>/dev/null)
assert_contains "cleaned W2" '"W2"' "$result"
assert_contains "skipped W1" '"skipped_active"' "$result"

echo "--- cleanup-stale: reports uncommitted changes ---"
WT_DIRTY=$(create_worktree "$REPO" "purlin-qa-20260325-230000")
write_lock "$WT_DIRTY" "99998" "qa" "W3"
write_label "$WT_DIRTY" "W3"
echo "dirty" > "$WT_DIRTY/new_file.txt"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" cleanup-stale 2>/dev/null)
assert_contains "reports uncommitted" '"has_uncommitted"' "$result"
assert_contains "W3 has uncommitted" '"W3"' "$result"

echo "--- cleanup-stale: dry-run does not remove ---"
WT_DRY=$(create_worktree "$REPO" "purlin-engineer-20260325-233000")
write_lock "$WT_DRY" "99997" "engineer" "W4"
write_label "$WT_DRY" "W4"

result=$(PURLIN_PROJECT_ROOT="$REPO" bash "$MANAGE_SH" cleanup-stale --dry-run 2>/dev/null)
assert_contains "dry-run reports W4" '"W4"' "$result"
# Worktree should still exist
TOTAL=$((TOTAL + 1))
if git -C "$REPO" worktree list --porcelain | grep -q "purlin-engineer-20260325-233000"; then
    echo "  PASS  dry-run did not remove worktree"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  dry-run removed the worktree"
    FAILED=$((FAILED + 1))
fi

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: auto-commit + merge ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: auto-commits tracked changes and merges ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260326-100000")

# Make a tracked change in the worktree
echo "modified" > "$WT/README.md"

# Run the hook (simulating session end from main repo)
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null

# Verify branch was merged and cleaned up
TOTAL=$((TOTAL + 1))
if ! git -C "$REPO" branch --list 'purlin-engineer-20260326-100000' | grep -q .; then
    echo "  PASS  branch deleted after merge"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  branch still exists"
    FAILED=$((FAILED + 1))
fi

# Verify the change landed on the source branch
actual_content=$(cat "$REPO/README.md")
assert_eq "change merged to source" "modified" "$actual_content"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: auto-commit untracked files ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: auto-commits untracked files and merges ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260326-110000")

# Create a new file in the worktree
echo "new feature code" > "$WT/feature.py"

PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null

# Verify the new file landed on source branch
assert_file_exists "untracked file merged to source" "$REPO/feature.py"
actual=$(cat "$REPO/feature.py")
assert_eq "file content correct" "new feature code" "$actual"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: merge conflict → breadcrumb ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: writes breadcrumb on merge conflict ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260326-120000")

# Create divergent changes on both sides
echo "worktree version" > "$WT/README.md"
git -C "$WT" add -A && git -C "$WT" commit -q -m "worktree change"

echo "main version conflict" > "$REPO/README.md"
git -C "$REPO" add -A && git -C "$REPO" commit -q -m "main change"

# Run the hook — should fail to merge and write breadcrumb
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null

# Verify breadcrumb was written
BREADCRUMB="$REPO/.purlin/cache/merge_pending/purlin-engineer-20260326-120000.json"
assert_file_exists "breadcrumb written" "$BREADCRUMB"

if [[ -f "$BREADCRUMB" ]]; then
    bc_content=$(cat "$BREADCRUMB")
    assert_contains "breadcrumb has branch" "purlin-engineer-20260326-120000" "$bc_content"
    assert_contains "breadcrumb has reason" '"reason": "conflict"' "$bc_content"
    assert_contains "breadcrumb has source_branch" '"source_branch"' "$bc_content"
    assert_contains "breadcrumb has failed_at" '"failed_at"' "$bc_content"
fi

# Verify worktree was preserved (not removed)
TOTAL=$((TOTAL + 1))
if git -C "$REPO" branch --list 'purlin-engineer-20260326-120000' | grep -q .; then
    echo "  PASS  branch preserved after conflict"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  branch was deleted despite conflict"
    FAILED=$((FAILED + 1))
fi

# Verify main is not in a broken merge state
TOTAL=$((TOTAL + 1))
if ! git -C "$REPO" status | grep -q "You have unmerged paths"; then
    echo "  PASS  main repo not in merge state"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  main repo left in merge state"
    FAILED=$((FAILED + 1))
fi

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: successful merge deletes stale breadcrumb ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: removes breadcrumb from prior failed merge ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260326-130000")
echo "clean change" > "$WT/feature2.py"

# Plant a stale breadcrumb as if a prior attempt failed
mkdir -p "$REPO/.purlin/cache/merge_pending"
echo '{"branch":"purlin-engineer-20260326-130000","reason":"conflict"}' \
    > "$REPO/.purlin/cache/merge_pending/purlin-engineer-20260326-130000.json"

PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null

assert_file_not_exists "stale breadcrumb deleted" \
    "$REPO/.purlin/cache/merge_pending/purlin-engineer-20260326-130000.json"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: skips non-purlin branches ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: ignores non-purlin branches ---"
# Create a worktree on a non-purlin branch
git -C "$REPO" worktree add -q "$REPO/.purlin/worktrees/feature-login" -b "feature/login" 2>/dev/null
echo "login code" > "$REPO/.purlin/worktrees/feature-login/login.py"

PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null

# Branch should still exist (not merged)
TOTAL=$((TOTAL + 1))
if git -C "$REPO" branch --list 'feature/login' | grep -q .; then
    echo "  PASS  non-purlin branch not touched"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  non-purlin branch was merged/deleted"
    FAILED=$((FAILED + 1))
fi

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: no-op when no purlin branches ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: exits cleanly with no worktrees ---"
exit_code=0
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null || exit_code=$?
assert_eq "exits 0 with no worktrees" "0" "$exit_code"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: merge lock stale PID detection ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: cleans stale merge lock before acquiring ---"
mkdir -p "$REPO/.purlin/cache"
# Plant a stale merge lock with a dead PID
echo "99999" > "$REPO/.purlin/cache/merge.lock"

WT=$(create_worktree "$REPO" "purlin-engineer-20260326-150000")
echo "some work" > "$WT/work.py"

PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null

# If it merged successfully, the stale lock was handled
assert_file_exists "work merged despite stale lock" "$REPO/work.py"
assert_file_not_exists "merge lock cleaned up" "$REPO/.purlin/cache/merge.lock"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== session-end-merge.sh: always exits 0 ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- hook: exits 0 even on error conditions ---"
# Make .purlin/cache unwritable to cause errors
mkdir -p "$REPO/.purlin/cache"
# Create a branch that will have merge issues but the hook should still exit 0
WT=$(create_worktree "$REPO" "purlin-engineer-20260326-160000")
echo "conflict" > "$WT/README.md"
git -C "$WT" add -A && git -C "$WT" commit -q -m "wt change"
echo "other conflict" > "$REPO/README.md"
git -C "$REPO" add -A && git -C "$REPO" commit -q -m "main change"

exit_code=0
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" 2>/dev/null || exit_code=$?
assert_eq "exits 0 even on conflict" "0" "$exit_code"

cleanup
TEST_ROOT=""

###############################################################################
# Summary
###############################################################################

echo ""
echo "==============================="
echo "Results: $PASSED/$TOTAL passed, $FAILED failed"
echo "==============================="

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
exit 0
