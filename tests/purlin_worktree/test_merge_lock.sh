#!/usr/bin/env bash
# tests/purlin_worktree/test_merge_lock.sh
#
# Tests for merge lock acquisition/release, stale PID detection, lock
# contention, merge conflict handling, successful merge cleanup, and
# auto-commit before merge — all exercising functions in
# hooks/scripts/session-end-merge.sh.
#
# Creates real git repos with worktrees in a temp directory.
# Does NOT touch the project repo.
#
# Usage:
#   bash tests/purlin_worktree/test_merge_lock.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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

# --- Fixture setup ---

setup_test_repo() {
    TEST_ROOT="$(cd "$(mktemp -d -t purlin-merge-lock-XXXXXX)" && pwd -P)"
    local repo="$TEST_ROOT/repo"

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

create_worktree() {
    local repo="$1" branch="$2"
    local wt_dir="$repo/.purlin/worktrees/$branch"
    git -C "$repo" worktree add -q "$wt_dir" -b "$branch" 2>/dev/null
    echo "$(cd "$wt_dir" && pwd -P)"
}

# Define the functions under test directly, mirroring session-end-merge.sh.
# We inline them here rather than sourcing the hook (which has top-level code
# that calls merge_worktrees and exits). These must stay in sync with the hook.

acquire_lock() {
    local lockfile="$1"
    local max_retries=3
    local attempt=0
    mkdir -p "$(dirname "$lockfile")"

    while true; do
        if [ -f "$lockfile" ]; then
            local lock_pid
            lock_pid=$(cat "$lockfile" 2>/dev/null)
            if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                rm -f "$lockfile"
            fi
        fi

        if (set -o noclobber; echo $$ > "$lockfile") 2>/dev/null; then
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $attempt -ge $max_retries ]; then
            echo "Warning: Could not acquire merge lock after $max_retries retries" >&2
            return 1
        fi
        sleep 0  # no real delay in tests (original uses sleep 2)
    done
}

release_lock() {
    rm -f "$1"
}

# Set PROJECT_ROOT for write_breadcrumb (used by tests 5-7 via the hook)
init_test_project_root() {
    PROJECT_ROOT="$1"
}

###############################################################################
echo ""
echo "=== 1. Merge lock acquisition ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- acquire_lock creates lockfile with current PID ---"
LOCKFILE="$REPO/.purlin/cache/merge.lock"

acquire_lock "$LOCKFILE"
lock_result=$?
assert_eq "acquire_lock returns 0" "0" "$lock_result"
assert_file_exists "lockfile created" "$LOCKFILE"

lock_pid=$(cat "$LOCKFILE")
assert_eq "lockfile contains current PID" "$$" "$lock_pid"

# Clean up for next test
release_lock "$LOCKFILE"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== 2. Merge lock stale PID detection ==="
###############################################################################

REPO="$(setup_test_repo)"
init_test_project_root "$REPO"

echo "--- acquire_lock cleans stale lock (dead PID) and acquires ---"
LOCKFILE="$REPO/.purlin/cache/merge.lock"
mkdir -p "$(dirname "$LOCKFILE")"

# Plant a lock with a dead PID
echo "99999" > "$LOCKFILE"

acquire_lock "$LOCKFILE"
lock_result=$?
assert_eq "acquire_lock succeeds after stale cleanup" "0" "$lock_result"

lock_pid=$(cat "$LOCKFILE")
assert_eq "lockfile now has current PID" "$$" "$lock_pid"

release_lock "$LOCKFILE"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== 3. Merge lock contention (live PID) ==="
###############################################################################

REPO="$(setup_test_repo)"
init_test_project_root "$REPO"

echo "--- acquire_lock fails when lockfile holds a live PID ---"
LOCKFILE="$REPO/.purlin/cache/merge.lock"
mkdir -p "$(dirname "$LOCKFILE")"

# Plant a lock with our own PID (which is alive) — but we need a
# different process to try acquiring. We already hold no lock, so
# first create the lockfile manually with a live PID ($$).
echo "$$" > "$LOCKFILE"

# Now try to acquire — should fail because $$ is alive and the file exists.
# Override sleep to avoid waiting in tests.
acquire_lock_contention_test() {
    local lockfile="$1"
    local max_retries=3
    local attempt=0
    mkdir -p "$(dirname "$lockfile")"

    while true; do
        if [ -f "$lockfile" ]; then
            local lock_pid
            lock_pid=$(cat "$lockfile" 2>/dev/null)
            if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                rm -f "$lockfile"
            fi
        fi

        if (set -o noclobber; echo "99990" > "$lockfile") 2>/dev/null; then
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $attempt -ge $max_retries ]; then
            return 1
        fi
        # No sleep in test — just retry immediately
    done
}

contention_result=0
acquire_lock_contention_test "$LOCKFILE" 2>/dev/null || contention_result=$?
assert_eq "acquire_lock fails on contention" "1" "$contention_result"

# Verify original lock is untouched
lock_pid=$(cat "$LOCKFILE")
assert_eq "original lock PID preserved" "$$" "$lock_pid"

rm -f "$LOCKFILE"
cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== 4. Merge lock release ==="
###############################################################################

REPO="$(setup_test_repo)"
init_test_project_root "$REPO"

echo "--- release_lock removes the lockfile ---"
LOCKFILE="$REPO/.purlin/cache/merge.lock"
mkdir -p "$(dirname "$LOCKFILE")"

# Create and then release
acquire_lock "$LOCKFILE"
assert_file_exists "lockfile exists before release" "$LOCKFILE"

release_lock "$LOCKFILE"
assert_file_not_exists "lockfile removed after release" "$LOCKFILE"

echo "--- release_lock is safe on non-existent file ---"
release_lock "$LOCKFILE"
TOTAL=$((TOTAL + 1))
echo "  PASS  release_lock on missing file does not error"
PASSED=$((PASSED + 1))

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== 5. Merge conflict handling ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- merge conflict aborts merge, writes breadcrumb, preserves worktree ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260327-100000")

# Create divergent changes to force a conflict
echo "worktree side" > "$WT/README.md"
git -C "$WT" add -A && git -C "$WT" commit -q -m "worktree change"

echo "main side conflict" > "$REPO/README.md"
git -C "$REPO" add -A && git -C "$REPO" commit -q -m "main change"

# Run the hook
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" >/dev/null 2>&1

# 5a: Merge was aborted (repo is not in a merge state)
TOTAL=$((TOTAL + 1))
if ! git -C "$REPO" status 2>/dev/null | grep -q "You have unmerged paths"; then
    echo "  PASS  merge was aborted (no unmerged paths)"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  repo left in merge state"
    FAILED=$((FAILED + 1))
fi

# 5b: Breadcrumb was written
BREADCRUMB="$REPO/.purlin/cache/merge_pending/purlin-engineer-20260327-100000.json"
assert_file_exists "breadcrumb written on conflict" "$BREADCRUMB"

if [[ -f "$BREADCRUMB" ]]; then
    bc_content=$(cat "$BREADCRUMB")
    assert_contains "breadcrumb has branch name" "purlin-engineer-20260327-100000" "$bc_content"
    assert_contains "breadcrumb has reason conflict" '"reason": "conflict"' "$bc_content"
    assert_contains "breadcrumb has worktree_path" '"worktree_path"' "$bc_content"
    assert_contains "breadcrumb has source_branch" '"source_branch"' "$bc_content"
    assert_contains "breadcrumb has failed_at timestamp" '"failed_at"' "$bc_content"
fi

# 5c: Worktree (branch) was preserved
TOTAL=$((TOTAL + 1))
if git -C "$REPO" branch --list 'purlin-engineer-20260327-100000' | grep -q .; then
    echo "  PASS  branch preserved after conflict"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  branch deleted despite conflict"
    FAILED=$((FAILED + 1))
fi

# 5d: Merge lock was released
assert_file_not_exists "merge lock released after conflict" "$REPO/.purlin/cache/merge.lock"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== 6. Successful merge cleanup ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- successful merge removes worktree, deletes branch, cleans breadcrumb ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260327-110000")

# Make a non-conflicting change
echo "new feature" > "$WT/feature.py"
git -C "$WT" add -A && git -C "$WT" commit -q -m "add feature"

# Plant a stale breadcrumb from a prior failed attempt
mkdir -p "$REPO/.purlin/cache/merge_pending"
echo '{"branch":"purlin-engineer-20260327-110000","reason":"conflict"}' \
    > "$REPO/.purlin/cache/merge_pending/purlin-engineer-20260327-110000.json"

# Run the hook
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" >/dev/null 2>&1

# 6a: Worktree directory was removed
assert_dir_not_exists "worktree directory removed" "$WT"

# 6b: Branch was deleted
TOTAL=$((TOTAL + 1))
if ! git -C "$REPO" branch --list 'purlin-engineer-20260327-110000' | grep -q .; then
    echo "  PASS  branch deleted after successful merge"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  branch still exists after merge"
    FAILED=$((FAILED + 1))
fi

# 6c: Stale breadcrumb was cleaned up
assert_file_not_exists "stale breadcrumb removed" \
    "$REPO/.purlin/cache/merge_pending/purlin-engineer-20260327-110000.json"

# 6d: Change actually landed on source branch
assert_file_exists "merged file on source branch" "$REPO/feature.py"
actual=$(cat "$REPO/feature.py")
assert_eq "merged content correct" "new feature" "$actual"

# 6e: Merge lock was released
assert_file_not_exists "merge lock released after success" "$REPO/.purlin/cache/merge.lock"

cleanup
TEST_ROOT=""

###############################################################################
echo ""
echo "=== 7. Auto-commit before merge ==="
###############################################################################

REPO="$(setup_test_repo)"

echo "--- uncommitted tracked changes are auto-committed before merge ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260327-120000")

# Modify a tracked file but do NOT commit
echo "auto-committed content" > "$WT/README.md"

# Run the hook — should auto-commit then merge
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" >/dev/null 2>&1

# Branch should be merged and deleted
TOTAL=$((TOTAL + 1))
if ! git -C "$REPO" branch --list 'purlin-engineer-20260327-120000' | grep -q .; then
    echo "  PASS  branch merged and deleted (tracked changes auto-committed)"
    PASSED=$((PASSED + 1))
else
    echo "  FAIL  branch still exists (auto-commit may have failed)"
    FAILED=$((FAILED + 1))
fi

actual=$(cat "$REPO/README.md")
assert_eq "auto-committed tracked change merged" "auto-committed content" "$actual"

cleanup
TEST_ROOT=""

REPO="$(setup_test_repo)"

echo "--- uncommitted untracked files are auto-committed before merge ---"
WT=$(create_worktree "$REPO" "purlin-engineer-20260327-130000")

# Create new untracked file but do NOT commit
echo "brand new file" > "$WT/newfile.txt"

# Run the hook
PURLIN_PROJECT_ROOT="$REPO" CLAUDE_PLUGIN_ROOT="$PROJECT_ROOT" bash "$MERGE_HOOK" >/dev/null 2>&1

# Verify file landed on source branch
assert_file_exists "untracked file auto-committed and merged" "$REPO/newfile.txt"
actual=$(cat "$REPO/newfile.txt")
assert_eq "untracked file content correct" "brand new file" "$actual"

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
