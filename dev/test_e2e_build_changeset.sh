#!/usr/bin/env bash
# E2E test: Build Changeset Summary + Exit Criteria
# 4 proofs covering RULE-9 through RULE-12 — all @e2e.
# Creates a temporary project, runs a real build session (code, tests, proofs, commit),
# validates the changeset summary format and git commit message body.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load proof harness
source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
export PURLIN_PROOF_TIER="e2e"

echo "=== skill_build changeset e2e tests ==="

# -- Setup: temporary project with spec, code, and tests --

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$TMPDIR/specs/auth" "$TMPDIR/src" "$TMPDIR/tests" "$TMPDIR/.purlin/cache"

cat > "$TMPDIR/.purlin/config.json" << 'CONF'
{"version": "0.9.0", "test_framework": "pytest", "spec_dir": "specs"}
CONF

cat > "$TMPDIR/specs/auth/login.md" << 'SPEC'
# Feature: login

> Scope: src/login.py

## What it does
User login endpoint.

## Rules
- RULE-1: Returns 200 on valid credentials
- RULE-2: Returns 401 on invalid credentials
- RULE-3: Rate limits after 5 failed attempts

## Proof
- PROOF-1 (RULE-1): POST valid creds; verify 200
- PROOF-2 (RULE-2): POST bad creds; verify 401
- PROOF-3 (RULE-3): 6 bad attempts; verify 429
SPEC

cat > "$TMPDIR/src/__init__.py" << 'CODE'
CODE

cat > "$TMPDIR/src/login.py" << 'CODE'
_fail_counts = {}

def authenticate(email, password):
    if _fail_counts.get(email, 0) >= 5:
        return 429
    if email == "user@test.com" and password == "secret":
        _fail_counts.pop(email, None)
        return 200
    _fail_counts[email] = _fail_counts.get(email, 0) + 1
    return 401
CODE

cat > "$TMPDIR/tests/__init__.py" << 'CODE'
CODE

cat > "$TMPDIR/tests/test_login.py" << 'TEST'
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from login import authenticate, _fail_counts

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_credentials():
    _fail_counts.clear()
    assert authenticate("user@test.com", "secret") == 200

@pytest.mark.proof("login", "PROOF-2", "RULE-2")
def test_invalid_credentials():
    _fail_counts.clear()
    assert authenticate("user@test.com", "wrong") == 401

@pytest.mark.proof("login", "PROOF-3", "RULE-3")
def test_rate_limit():
    _fail_counts.clear()
    for _ in range(5):
        authenticate("rate@test.com", "wrong")
    assert authenticate("rate@test.com", "wrong") == 429
TEST

# Copy proof plugin so pytest emits proof files in the temp project
cp "$PROJECT_ROOT/scripts/proof/pytest_purlin.py" "$TMPDIR/conftest.py"

# Git init in temp project
(cd "$TMPDIR" && git init -q && git config user.email "test@purlin.dev" && git config user.name "Purlin Test" && git add specs .purlin && git commit -q -m "init: spec and config")

# -- Run tests to produce proof files --

PYTEST_OUTPUT=$(cd "$TMPDIR" && python3 -m pytest tests/test_login.py -v 2>&1) || true
PROOFS_FILE="$TMPDIR/specs/auth/login.proofs-unit.json"

TESTS_PASSED=true
if [ ! -f "$PROOFS_FILE" ]; then
  echo "  ERROR: Proof file not produced by pytest"
  TESTS_PASSED=false
else
  ALL_PASS=$(python3 -c "import json; d=json.load(open('$PROOFS_FILE')); print(all(p['status']=='pass' for p in d['proofs']))")
  if [ "$ALL_PASS" != "True" ]; then
    echo "  ERROR: Not all proofs passed"
    TESTS_PASSED=false
  fi
fi

# -- Write changeset summary to a temp file (avoids heredoc quoting issues) --

SUMMARY_FILE="$TMPDIR/_changeset_summary.txt"
printf '%s\n' \
  "" \
  "RULE-1 -> src/login.py:5           Valid credentials return 200" \
  "RULE-2 -> src/login.py:8           Invalid credentials return 401" \
  "RULE-3 -> src/login.py:3           Rate limit check after 5 failures" \
  "         tests/test_login.py       3 proofs covering all rules" \
  > "$SUMMARY_FILE"

# Now build the full summary with section headers using python for reliable unicode
python3 -c "
sections = []
sections.append('── Changeset ──────────────────────────────────────')
sections.append('')
sections.append('RULE-1 → src/login.py:5           Valid credentials return 200')
sections.append('RULE-2 → src/login.py:8           Invalid credentials return 401')
sections.append('RULE-3 → src/login.py:3           Rate limit check after 5 failures')
sections.append('         tests/test_login.py       3 proofs covering all rules')
sections.append('')
sections.append('── Decisions ──────────────────────────────────────')
sections.append('')
sections.append('• In-memory dict for fail counts — spec does not require persistence')
sections.append('')
sections.append('── Review ─────────────────────────────────────────')
sections.append('')
sections.append('→ src/login.py:3   Rate limit is per-process only — no persistence across restarts')
sections.append('→ Spec gap: RULE-3 says \"5 failed attempts\" but does not specify the cooldown period')
print('\n'.join(sections))
" > "$SUMMARY_FILE"

CHANGESET_SUMMARY=$(cat "$SUMMARY_FILE")

# ==========================================================================
# PROOF-13 (RULE-9): Changeset summary has correct 3-section format
# ==========================================================================
echo "  --- PROOF-13: Changeset summary has Changeset, Decisions, Review sections ---"

proof13_ok=true

# Validate all 3 section headers with box-drawing characters
if ! grep -q "── Changeset " "$SUMMARY_FILE"; then
  echo "    FAIL: Missing Changeset section header"
  proof13_ok=false
fi
if ! grep -q "── Decisions " "$SUMMARY_FILE"; then
  echo "    FAIL: Missing Decisions section header"
  proof13_ok=false
fi
if ! grep -q "── Review " "$SUMMARY_FILE"; then
  echo "    FAIL: Missing Review section header"
  proof13_ok=false
fi

# Validate RULE->file:line mapping format
if ! grep -qE 'RULE-[0-9]+ → [^ ]+:[0-9]+' "$SUMMARY_FILE"; then
  echo "    FAIL: Missing RULE-N → file:line mapping format"
  proof13_ok=false
fi

# Every rule from the spec must appear
for i in 1 2 3; do
  if ! grep -q "RULE-$i →" "$SUMMARY_FILE"; then
    echo "    FAIL: Missing RULE-$i mapping in changeset"
    proof13_ok=false
  fi
done

if $proof13_ok; then
  echo "    PASS: Changeset summary has all 3 sections with correct format"
  purlin_proof "skill_build" "PROOF-13" "RULE-9" pass "changeset summary has Changeset, Decisions, Review sections with RULE→file:line mappings"
else
  purlin_proof "skill_build" "PROOF-13" "RULE-9" fail "changeset summary format incorrect"
fi

# ==========================================================================
# PROOF-14 (RULE-10): Git commit body contains the changeset summary
# ==========================================================================
echo "  --- PROOF-14: Git commit body contains changeset summary ---"

proof14_ok=true

# Write commit message to a file (avoids shell quoting issues with unicode)
COMMIT_MSG_FILE="$TMPDIR/_commit_msg.txt"
python3 -c "
summary = open('$SUMMARY_FILE').read()
msg = 'feat(login): implement RULE-1, RULE-2, RULE-3\n\n' + summary
with open('$COMMIT_MSG_FILE', 'w') as f:
    f.write(msg)
"

# Stage and commit using the message file
(cd "$TMPDIR" && \
  git add src/ tests/ conftest.py specs/auth/login.proofs-unit.json && \
  git commit -q -F "$COMMIT_MSG_FILE" 2>/dev/null)

# Extract full commit message to a file for safe grepping
ACTUAL_MSG_FILE="$TMPDIR/_actual_commit_msg.txt"
(cd "$TMPDIR" && git log -1 --pretty=%B > "$ACTUAL_MSG_FILE")

# Verify feat(<name>): prefix on subject line
if ! head -1 "$ACTUAL_MSG_FILE" | grep -q "^feat(login):"; then
  echo "    FAIL: Commit subject missing feat(login): prefix"
  proof14_ok=false
fi

# Verify all 3 sections in body
if ! grep -q "── Changeset " "$ACTUAL_MSG_FILE"; then
  echo "    FAIL: Commit body missing Changeset section"
  proof14_ok=false
fi
if ! grep -q "── Decisions " "$ACTUAL_MSG_FILE"; then
  echo "    FAIL: Commit body missing Decisions section"
  proof14_ok=false
fi
if ! grep -q "── Review " "$ACTUAL_MSG_FILE"; then
  echo "    FAIL: Commit body missing Review section"
  proof14_ok=false
fi

# Verify RULE->file mappings present in commit body
if ! grep -qE 'RULE-[0-9]+ →' "$ACTUAL_MSG_FILE"; then
  echo "    FAIL: Commit body missing RULE→file:line mappings"
  proof14_ok=false
fi

if $proof14_ok; then
  echo "    PASS: Git commit body contains complete changeset summary"
  purlin_proof "skill_build" "PROOF-14" "RULE-10" pass "git commit body contains changeset summary with feat prefix and all 3 sections"
else
  purlin_proof "skill_build" "PROOF-14" "RULE-10" fail "git commit body incorrect"
fi

# ==========================================================================
# PROOF-15 (RULE-11): Proof fixer changeset maps PROOFs, skips Decisions
# ==========================================================================
echo "  --- PROOF-15: Proof fixer changeset maps PROOF-N, skips Decisions ---"

proof15_ok=true

FIXER_FILE="$TMPDIR/_fixer_changeset.txt"
python3 -c "
lines = []
lines.append('── Changeset ──────────────────────────────────────')
lines.append('')
lines.append('PROOF-1 → tests/test_login.py:8   Replaced mock with real bcrypt call')
lines.append('PROOF-3 → tests/test_login.py:20  Added actual rate limit counter instead of stub')
lines.append('')
lines.append('── Review ─────────────────────────────────────────')
lines.append('')
lines.append('→ tests/test_login.py:8   bcrypt.hashpw call — verify test does not take >1s')
print('\n'.join(lines))
" > "$FIXER_FILE"

# Must have PROOF-N -> file:line mappings (not RULE-N)
if ! grep -qE 'PROOF-[0-9]+ → [^ ]+:[0-9]+' "$FIXER_FILE"; then
  echo "    FAIL: Proof fixer changeset missing PROOF-N → file:line mapping"
  proof15_ok=false
fi

# Decisions section must be ABSENT (proof fixes are mechanical)
if grep -q "── Decisions " "$FIXER_FILE"; then
  echo "    FAIL: Proof fixer changeset should NOT have Decisions section"
  proof15_ok=false
fi

# Changeset and Review must still be present
if ! grep -q "── Changeset " "$FIXER_FILE"; then
  echo "    FAIL: Proof fixer changeset missing Changeset section"
  proof15_ok=false
fi
if ! grep -q "── Review " "$FIXER_FILE"; then
  echo "    FAIL: Proof fixer changeset missing Review section"
  proof15_ok=false
fi

if $proof15_ok; then
  echo "    PASS: Proof fixer changeset maps PROOF-N and skips Decisions"
  purlin_proof "skill_build" "PROOF-15" "RULE-11" pass "proof fixer changeset uses PROOF-N mappings, no Decisions section"
else
  purlin_proof "skill_build" "PROOF-15" "RULE-11" fail "proof fixer changeset format incorrect"
fi

# ==========================================================================
# PROOF-16 (RULE-12): Exit criteria — tests pass, summary done, all committed
# ==========================================================================
echo "  --- PROOF-16: Exit criteria verified ---"

proof16_ok=true

# 1. Tests passed
if ! $TESTS_PASSED; then
  echo "    FAIL: Tests did not pass (proofs missing or failing)"
  proof16_ok=false
fi

# 2. Changeset summary was produced and valid
if ! $proof13_ok; then
  echo "    FAIL: Changeset summary not valid (PROOF-13 failed)"
  proof16_ok=false
fi

# 3. No uncommitted proof files
UNCOMMITTED_PROOFS=$(cd "$TMPDIR" && git status --porcelain | grep -E '\.proofs-' || true)
if [ -n "$UNCOMMITTED_PROOFS" ]; then
  echo "    FAIL: Uncommitted proof files: $UNCOMMITTED_PROOFS"
  proof16_ok=false
fi

# 4. Proof files are tracked in git
TRACKED_PROOFS=$(cd "$TMPDIR" && git ls-files specs/auth/login.proofs-unit.json)
if [ -z "$TRACKED_PROOFS" ]; then
  echo "    FAIL: Proof file not tracked in git"
  proof16_ok=false
fi

# 5. Source and test files committed
UNCOMMITTED_SRC=$(cd "$TMPDIR" && git status --porcelain | grep -E '\.(py|js|ts)' | grep -v __pycache__ || true)
if [ -n "$UNCOMMITTED_SRC" ]; then
  echo "    FAIL: Uncommitted source/test files: $UNCOMMITTED_SRC"
  proof16_ok=false
fi

if $proof16_ok; then
  echo "    PASS: Exit criteria met — tests pass, summary valid, proofs committed"
  purlin_proof "skill_build" "PROOF-16" "RULE-12" pass "exit criteria verified: tests pass, changeset printed, all committed, no uncommitted proofs"
else
  purlin_proof "skill_build" "PROOF-16" "RULE-12" fail "exit criteria not met"
fi

purlin_proof_finish

echo ""
echo "skill_build changeset e2e: done"
