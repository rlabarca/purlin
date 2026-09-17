#!/usr/bin/env bash
# Text check: the commit body purlin:build writes.
#
# The build skill tells the agent to commit with a `feat(<name>):` subject and a body of
# three named sections: Changeset (a RULE-N -> file:line line for every rule addressed),
# Decisions (omitted when every rule had one obvious implementation) and Review (omitted
# when nothing needs a second look). `references/commit_conventions.md` carries the exact
# rendering.
#
# This runs no model. It writes a fixture commit whose message follows the contract, reads
# the message back out of git, and checks it. Three further fixtures each break the
# contract in exactly one way and must be rejected, so every check is shown to
# discriminate rather than to restate a fixture it wrote itself.
#
# Exit 0 when every check holds, 1 otherwise.
#
# This suite is the evidence for skill_build PROOF-5 (RULE-5). It carries no
# purlin_proof call of its own: the shell runner arm of scripts/run/purlin_run.py
# executes `*.test.sh` in the project root and nothing else, so a marker in this
# directory could never produce a proof entry and every run would report the
# evidence as missing. dev/test_skills.py runs this script from the repository
# root under that proof marker instead, and asserts both the exit status and the
# `ok:` line below.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_SKILL="$PROJECT_ROOT/skills/build/SKILL.md"
CONVENTIONS="$PROJECT_ROOT/references/commit_conventions.md"

TMPDIR_RUN=$(mktemp -d)
trap 'rm -rf "$TMPDIR_RUN"' EXIT

failures=0
checks=0

fail() {
    echo "  FAIL: $1"
    failures=$((failures + 1))
}

counted() {
    checks=$((checks + 1))
}

# --- the contract, as one function -----------------------------------------------------
#
# A body satisfies the contract when the subject carries the feat(<name>): prefix, the
# Changeset section is present, every rule named in the subject has a file:line mapping,
# and the sections that are present are the named ones. Decisions and Review are optional
# by the contract, so their absence is never a failure here.

section_present() {
    # Matches "Changeset", "Changeset:" and a decorated "-- Changeset -----".
    grep -qE "^([^A-Za-z]* )?$2[^A-Za-z]*\$" "$1"
}

body_ok() {
    local file="$1"
    head -1 "$file" | grep -qE '^feat\([a-z0-9_]+\): ' || return 1
    section_present "$file" "Changeset" || return 1
    grep -qE 'RULE-[0-9]+ (->|→) [^ ]+:[0-9]+' "$file" || return 1
    local rule
    for rule in $(head -1 "$file" | grep -oE 'RULE-[0-9]+'); do
        grep -qE "^$rule (->|→) " "$file" || return 1
    done
    return 0
}

# --- the fixture commit -----------------------------------------------------------------

GOOD_MSG="$TMPDIR_RUN/good.txt"
cat > "$GOOD_MSG" <<'MSG'
feat(login): implement RULE-1, RULE-2, RULE-3

Changeset

RULE-1 → src/login.py:12   Valid credentials return 200 and a session cookie
RULE-2 → src/login.py:18   Wrong password returns 401 and sets no cookie
RULE-3 → src/login.py:4    Lockout counter, 5 failures, 15 minutes
         tests/test_login.py:1   3 tests, one per proof

Decisions

  - In-memory counter for failures: the spec says nothing about surviving a restart

Review

  - src/login.py:4   The lockout is per process only, so a restart clears it
MSG

REPO="$TMPDIR_RUN/repo"
mkdir -p "$REPO/src"
git -C "$REPO" -c init.defaultBranch=main init -q
git -C "$REPO" config user.email "check@purlin.test"
git -C "$REPO" config user.name "Purlin Check"
echo "def authenticate(): return 200" > "$REPO/src/login.py"
git -C "$REPO" add src/login.py
git -C "$REPO" commit -q -F "$GOOD_MSG"

ACTUAL="$TMPDIR_RUN/actual.txt"
git -C "$REPO" log -1 --pretty=%B > "$ACTUAL"

echo "=== purlin:build commit body ==="

# 1. Git keeps the body intact and the body satisfies the contract.
counted
if ! body_ok "$ACTUAL"; then
    fail "the fixture commit body read back from git does not satisfy the contract"
fi

# 2. The optional sections survive the round trip when they are written.
counted
if ! section_present "$ACTUAL" "Decisions"; then
    fail "the Decisions section did not survive the commit"
fi
counted
if ! section_present "$ACTUAL" "Review"; then
    fail "the Review section did not survive the commit"
fi

# 3. A body with no Changeset section is rejected.
NO_CHANGESET="$TMPDIR_RUN/no_changeset.txt"
cat > "$NO_CHANGESET" <<'MSG'
feat(login): implement RULE-1

RULE-1 → src/login.py:12   Valid credentials return 200
MSG
counted
if body_ok "$NO_CHANGESET"; then
    fail "a body with no Changeset section was accepted"
fi

# 4. A body whose subject names a rule the Changeset never maps is rejected.
MISSING_RULE="$TMPDIR_RUN/missing_rule.txt"
cat > "$MISSING_RULE" <<'MSG'
feat(login): implement RULE-1, RULE-2

Changeset

RULE-1 → src/login.py:12   Valid credentials return 200
MSG
counted
if body_ok "$MISSING_RULE"; then
    fail "a body that skipped RULE-2 in the Changeset was accepted"
fi

# 5. A body with no feat(<name>): prefix is rejected.
NO_PREFIX="$TMPDIR_RUN/no_prefix.txt"
cat > "$NO_PREFIX" <<'MSG'
implement the login rules

Changeset

RULE-1 → src/login.py:12   Valid credentials return 200
MSG
counted
if body_ok "$NO_PREFIX"; then
    fail "a body with no feat(<name>): subject prefix was accepted"
fi

# --- the skill and the conventions still describe this contract --------------------------

for word in Changeset Decisions Review; do
    counted
    grep -q "$word" "$BUILD_SKILL" || fail "skills/build/SKILL.md no longer names $word"
    counted
    grep -q "$word" "$CONVENTIONS" || fail "references/commit_conventions.md no longer names $word"
done

counted
grep -qE 'RULE-N (->|→) file:line' "$BUILD_SKILL" \
    || fail "skills/build/SKILL.md no longer states the RULE-N -> file:line mapping"
counted
grep -q 'feat(<name>):' "$BUILD_SKILL" \
    || fail "skills/build/SKILL.md no longer states the feat(<name>): subject prefix"
counted
grep -q 'commit_conventions.md' "$BUILD_SKILL" \
    || fail "skills/build/SKILL.md no longer points at references/commit_conventions.md"

if [ "$failures" -eq 0 ]; then
    echo "  ok: $checks checks"
    exit 0
fi

echo "  $failures of $checks checks failed"
exit 1
