"""Cross-language cheating detection matrix.

5 cheat patterns x 5 languages = 25 test cases. Every test compiles or
interprets real code in the target language, runs it through the proof
plugin, and verifies the proof JSON. Each test documents whether the cheat
is caught by Pass 1 (deterministic) or requires Pass 2 (LLM).

Cheat patterns:
  1. Tautological — assertion always true regardless of code behavior
  2. Fixture-only — asserts test setup data, never calls code under test
  3. Happy-path-only — rule says "rejects X" but test only sends valid input
  4. Name/value drift — test name claims one thing, assertion checks the opposite
  5. No real assertion — lots of setup but no actual check on the result

Languages: C (gcc), PHP (php), SQL (sqlite3), TypeScript (tsc+node), Python

Run with: python3 -m pytest dev/test_cheat_matrix.py -v
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

PROOF_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))
from static_checks import check_python


# ---------------------------------------------------------------------------
# Language runners — each takes source code, compiles/runs it, returns proof JSON
# ---------------------------------------------------------------------------

def _run_c(tmp_path, c_source, feature):
    """Compile C source with gcc, run binary, return proof JSON dict."""
    shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))
    c_file = tmp_path / 'test.c'
    c_file.write_text(c_source)
    binary = tmp_path / 'test_bin'
    r = subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"gcc failed:\n{r.stderr}"
    r = subprocess.run([str(binary)], capture_output=True, text=True)
    assert r.returncode == 0, f"binary failed:\n{r.stderr}"
    return json.loads(r.stdout)


def _run_php(tmp_path, php_source, feature):
    """Run PHP source through phpunit_purlin, return proof JSON dict."""
    php_file = tmp_path / 'test.php'
    php_file.write_text(php_source)
    r = subprocess.run(
        ['php', os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php'), str(php_file)],
        capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, f"php failed:\n{r.stderr}\n{r.stdout}"
    return json.loads(r.stdout)


def _run_sql(tmp_path, sql_source, feature, setup_sql=None):
    """Run SQL source against sqlite3 via sql_purlin.sh, return proof JSON dict."""
    db = tmp_path / 'test.db'
    if setup_sql:
        subprocess.run(['sqlite3', str(db)], input=setup_sql,
                       capture_output=True, text=True, check=True)
    sql_file = tmp_path / 'test.sql'
    sql_file.write_text(sql_source)
    r = subprocess.run(
        ['bash', os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh'), str(sql_file), str(db)],
        capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, f"sql_purlin failed:\n{r.stderr}\n{r.stdout}"
    return json.loads(r.stdout)


def _run_typescript(tmp_path, ts_source, feature):
    """Compile TypeScript with tsc, run with node, return proof JSON dict."""
    ts_file = tmp_path / 'test.ts'
    ts_file.write_text(ts_source)
    tsconfig = tmp_path / 'tsconfig.json'
    tsconfig.write_text(json.dumps({
        "compilerOptions": {"target": "ES2020", "module": "commonjs",
                            "strict": True, "outDir": str(tmp_path / "dist")},
        "include": ["*.ts"],
    }))
    r = subprocess.run(['tsc', '--project', str(tsconfig)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, f"tsc failed:\n{r.stderr}"
    r = subprocess.run(['node', str(tmp_path / 'dist' / 'test.js')],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"node failed:\n{r.stderr}"
    return json.loads(r.stdout)


def _run_python(tmp_path, py_source, feature):
    """Run Python test with pytest + proof plugin, return proof JSON dict from file."""
    spec_dir = tmp_path / 'specs' / 'test'
    spec_dir.mkdir(parents=True)
    (spec_dir / f'{feature}.md').write_text(
        f'# Feature: {feature}\n\n## Rules\n- RULE-1: test\n\n'
        f'## Proof\n- PROOF-1 (RULE-1): test\n')
    test_file = tmp_path / 'test_it.py'
    test_file.write_text(py_source)
    conftest = tmp_path / 'conftest.py'
    with open(os.path.join(PROOF_SCRIPTS, 'pytest_purlin.py')) as f:
        conftest.write_text(f.read())
    r = subprocess.run(
        [sys.executable, '-m', 'pytest', str(test_file), '-v', '--tb=short'],
        capture_output=True, text=True, cwd=str(tmp_path))
    # Read proof file
    proof_path = spec_dir / f'{feature}.proofs-unit.json'
    if proof_path.exists():
        with open(str(proof_path)) as f:
            return json.load(f)
    # If no proof file, build minimal JSON from pytest output
    return {"tier": "unit", "proofs": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_spec(tmp_path, feature, rule_desc):
    """Create a spec dir so proof plugins can resolve it."""
    spec_dir = tmp_path / 'specs' / 'test'
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / f'{feature}.md').write_text(
        f'# Feature: {feature}\n\n## Rules\n- RULE-1: {rule_desc}\n\n'
        f'## Proof\n- PROOF-1 (RULE-1): test\n')


def _assert_proof_passes(data, msg=""):
    """Assert proof JSON has exactly 1 proof with status=pass."""
    proofs = data.get('proofs', [])
    assert len(proofs) >= 1, f"No proofs emitted. {msg}"
    assert proofs[0]['status'] == 'pass', f"Expected pass, got {proofs[0]['status']}. {msg}"


# ===========================================================================
# CHEAT 1: Tautological — assertion always true
# ===========================================================================

class TestTautological:
    """Assertion is always true regardless of what the code does."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-22", "RULE-22")
    def test_c_tautological(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Validates input')
        data = _run_c(tmp_path, r'''
#include "c_purlin.h"
int validate(int x) { return x > 0 ? 0 : -1; }
int main(void) {
    int r = validate(-1);
    /* CHEAT: 1 == 1 is always true, ignores r */
    purlin_proof("feat", "PROOF-1", "RULE-1",
                 1 == 1, "test_validates_input", "test.c", "unit");
    purlin_proof_finish();
    return 0;
}
''', 'feat')
        _assert_proof_passes(data, "C tautological cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    @pytest.mark.proof("proof_plugins", "PROOF-25", "RULE-24")
    def test_php_tautological(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Validates input')
        data = _run_php(tmp_path, r'''<?php
function validate(int $x): bool { return $x > 0; }
/** @purlin feat PROOF-1 RULE-1 unit */
function test_validates_input() {
    $r = validate(-1);
    // CHEAT: always true, doesn't check $r
    if (true !== true) { throw new Exception("impossible"); }
}
''', 'feat')
        _assert_proof_passes(data, "PHP tautological cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins", "PROOF-27", "RULE-26")
    def test_sql_tautological(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Validates input')
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: validates input
SELECT CASE WHEN 1 = 1 THEN 'PASS' ELSE 'FAIL' END;
''', 'feat', setup_sql='CREATE TABLE t (id INTEGER);')
        _assert_proof_passes(data, "SQL tautological cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28")
    def test_typescript_tautological(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Validates input')
        data = _run_typescript(tmp_path, '''\
function validate(x: number): boolean { return x > 0; }
const r = validate(-1);
// CHEAT: ignores r, asserts literal true
const proofs = [{
    feature: "feat", id: "PROOF-1", rule: "RULE-1",
    test_file: "test.ts", test_name: "test_validates_input",
    status: (true === true ? "pass" : "fail") as "pass" | "fail",
    tier: "unit",
}];
console.log(JSON.stringify({ proofs }, null, 2));
''', 'feat')
        _assert_proof_passes(data, "TS tautological cheat passes — needs LLM")

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
    def test_python_tautological(self, tmp_path):
        """Python `assert result or True` — caught by Pass 1 static checks."""
        test_file = tmp_path / 'test_cheat.py'
        test_file.write_text('''\
import pytest
def validate(x): return x > 0
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_validates_input():
    r = validate(-1)
    assert r or True
''')
        results = check_python(str(test_file), 'feat')
        assert results[0]['status'] == 'fail', "Python `or True` caught by Pass 1"
        assert results[0]['check'] == 'assert_true'


# ===========================================================================
# CHEAT 2: Fixture-only — asserts test data, never calls code under test
# ===========================================================================

class TestFixtureOnly:
    """Test asserts properties of its own constants, never invokes the real code."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-22", "RULE-22")
    def test_c_fixture_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Returns sorted list')
        data = _run_c(tmp_path, r'''
#include "c_purlin.h"
#include <string.h>
int main(void) {
    /* CHEAT: never calls sort(), asserts hardcoded fixture */
    const char *expected[] = {"a", "b", "c"};
    purlin_proof("feat", "PROOF-1", "RULE-1",
                 strcmp(expected[0], "a") == 0 && strcmp(expected[2], "c") == 0,
                 "test_returns_sorted", "test.c", "unit");
    purlin_proof_finish();
    return 0;
}
''', 'feat')
        _assert_proof_passes(data, "C fixture-only cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    @pytest.mark.proof("proof_plugins", "PROOF-25", "RULE-24")
    def test_php_fixture_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Returns sorted list')
        data = _run_php(tmp_path, r'''<?php
function sort_items(array $items): array { sort($items); return $items; }
/** @purlin feat PROOF-1 RULE-1 unit */
function test_returns_sorted() {
    // CHEAT: never calls sort_items(), checks fixture
    $expected = ["a", "b", "c"];
    if (count($expected) !== 3) throw new Exception("wrong count");
}
''', 'feat')
        _assert_proof_passes(data, "PHP fixture-only cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins", "PROOF-27", "RULE-26")
    def test_sql_fixture_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Unique constraint enforced')
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: unique constraint enforced
SELECT CASE WHEN 'alice' = 'alice' THEN 'PASS' ELSE 'FAIL' END;
''', 'feat', setup_sql='CREATE TABLE users (email TEXT UNIQUE);')
        _assert_proof_passes(data, "SQL fixture-only cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28")
    def test_typescript_fixture_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Returns sorted list')
        data = _run_typescript(tmp_path, '''\
function sortItems(items: string[]): string[] { return [...items].sort(); }
// CHEAT: never calls sortItems, just checks fixture
const expected = ["a", "b", "c"];
const passed = expected.length === 3 && expected[0] === "a";
const proofs = [{
    feature: "feat", id: "PROOF-1", rule: "RULE-1",
    test_file: "test.ts", test_name: "test_returns_sorted",
    status: (passed ? "pass" : "fail") as "pass" | "fail", tier: "unit",
}];
console.log(JSON.stringify({ proofs }, null, 2));
''', 'feat')
        _assert_proof_passes(data, "TS fixture-only cheat passes — needs LLM")

    @pytest.mark.proof("static_checks", "PROOF-6", "RULE-6")
    def test_python_fixture_only(self, tmp_path):
        """Python fixture-only — Pass 1 passes (has assertions), needs LLM."""
        test_file = tmp_path / 'test_cheat.py'
        test_file.write_text('''\
import pytest
EXPECTED = ["a", "b", "c"]
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_returns_sorted():
    # CHEAT: never calls the real sort function
    assert len(EXPECTED) == 3
    assert EXPECTED[0] == "a"
''')
        results = check_python(str(test_file), 'feat')
        assert results[0]['status'] == 'pass', "Pass 1 passes — fixture cheat needs LLM"


# ===========================================================================
# CHEAT 3: Happy-path-only — rule says "rejects X" but test sends valid input
# ===========================================================================

class TestHappyPathOnly:
    """Rule describes rejection behavior, but test only validates the happy path."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-24", "RULE-6")
    def test_c_happy_path_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects negative quantities')
        data = _run_c(tmp_path, r'''
#include "c_purlin.h"
int validate_qty(int qty) { return qty >= 0 ? 0 : -1; }
int main(void) {
    /* CHEAT: rule says "rejects negative" but we test positive */
    purlin_proof("feat", "PROOF-1", "RULE-1",
                 validate_qty(5) == 0,
                 "test_rejects_negative", "test.c", "unit");
    purlin_proof_finish();
    return 0;
}
''', 'feat')
        _assert_proof_passes(data, "C happy-path cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    @pytest.mark.proof("proof_plugins", "PROOF-26", "RULE-25")
    def test_php_happy_path_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects empty email')
        data = _run_php(tmp_path, r'''<?php
function validate_email(string $e): bool { return strpos($e, '@') !== false; }
/** @purlin feat PROOF-1 RULE-1 unit */
function test_rejects_empty_email() {
    // CHEAT: rule says "rejects empty" but we test a valid email
    $r = validate_email("user@example.com");
    if (!$r) throw new Exception("should accept valid email");
}
''', 'feat')
        _assert_proof_passes(data, "PHP happy-path cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins", "PROOF-28", "RULE-27")
    def test_sql_happy_path_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects duplicate emails')
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: rejects duplicate emails
INSERT INTO users (email) VALUES ('unique@test.com');
SELECT CASE WHEN (SELECT count(*) FROM users) = 1 THEN 'PASS' ELSE 'FAIL' END;
''', 'feat', setup_sql='CREATE TABLE users (email TEXT UNIQUE);')
        # CHEAT: only inserts one unique row — never tests the duplicate rejection
        _assert_proof_passes(data, "SQL happy-path cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28")
    def test_typescript_happy_path_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects passwords under 8 characters')
        data = _run_typescript(tmp_path, '''\
function validatePassword(pw: string): boolean { return pw.length >= 8; }
// CHEAT: rule says "rejects under 8 chars" but test sends a valid password
const result = validatePassword("longpassword123");
const proofs = [{
    feature: "feat", id: "PROOF-1", rule: "RULE-1",
    test_file: "test.ts", test_name: "test_rejects_short_password",
    status: (result === true ? "pass" : "fail") as "pass" | "fail", tier: "unit",
}];
console.log(JSON.stringify({ proofs }, null, 2));
''', 'feat')
        _assert_proof_passes(data, "TS happy-path cheat passes — needs LLM")

    @pytest.mark.proof("static_checks", "PROOF-6", "RULE-6")
    def test_python_happy_path_only(self, tmp_path):
        """Python happy-path — Pass 1 passes, needs LLM to catch missing negative test."""
        test_file = tmp_path / 'test_cheat.py'
        test_file.write_text('''\
import pytest
def reject_negative(x):
    if x < 0: raise ValueError("negative")
    return x
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_rejects_negative():
    # CHEAT: only tests the happy path
    assert reject_negative(5) == 5
''')
        results = check_python(str(test_file), 'feat')
        assert results[0]['status'] == 'pass', "Pass 1 passes — happy-path cheat needs LLM"


# ===========================================================================
# CHEAT 4: Name/value drift — name claims X, assertion checks opposite
# ===========================================================================

class TestNameValueDrift:
    """Test function name describes one behavior, but assertion validates the opposite."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-22", "RULE-22")
    def test_c_name_drift(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects invalid tokens')
        data = _run_c(tmp_path, r'''
#include "c_purlin.h"
/* Bug: accepts everything */
int validate_token(const char *t) { return 0; }
int main(void) {
    /* Name says "rejects" but asserts return == 0 (accepts) */
    purlin_proof("feat", "PROOF-1", "RULE-1",
                 validate_token("INVALID") == 0,
                 "test_rejects_invalid_token", "test.c", "unit");
    purlin_proof_finish();
    return 0;
}
''', 'feat')
        _assert_proof_passes(data, "C name-drift cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    @pytest.mark.proof("proof_plugins", "PROOF-25", "RULE-24")
    def test_php_name_drift(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects invalid tokens')
        data = _run_php(tmp_path, r'''<?php
/* Bug: accepts everything */
function validate_token(string $t): bool { return true; }
/** @purlin feat PROOF-1 RULE-1 unit */
function test_rejects_invalid_token() {
    // Name says "rejects" but asserts it returns true (accepts)
    $r = validate_token("INVALID");
    if ($r !== true) throw new Exception("Expected true");
}
''', 'feat')
        _assert_proof_passes(data, "PHP name-drift cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins", "PROOF-27", "RULE-26")
    def test_sql_name_drift(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Blocks unauthorized access')
        # CHEAT: test name says "blocks" but it verifies INSERT succeeds
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: blocks unauthorized access
INSERT INTO access_log (user_id, action) VALUES (999, 'admin_delete');
SELECT CASE WHEN (SELECT count(*) FROM access_log WHERE user_id = 999) = 1
       THEN 'PASS' ELSE 'FAIL' END;
''', 'feat',
            setup_sql='CREATE TABLE access_log (user_id INTEGER, action TEXT);')
        _assert_proof_passes(data, "SQL name-drift cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28")
    def test_typescript_name_drift(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects expired sessions')
        data = _run_typescript(tmp_path, '''\
// Bug: accepts everything
function isSessionValid(token: string): boolean { return true; }
const result = isSessionValid("expired-token-xyz");
// Name says "rejects expired" but asserts result is true (accepted!)
const proofs = [{
    feature: "feat", id: "PROOF-1", rule: "RULE-1",
    test_file: "test.ts", test_name: "test_rejects_expired_session",
    status: (result === true ? "pass" : "fail") as "pass" | "fail", tier: "unit",
}];
console.log(JSON.stringify({ proofs }, null, 2));
''', 'feat')
        _assert_proof_passes(data, "TS name-drift cheat passes — needs LLM")

    @pytest.mark.proof("static_checks", "PROOF-6", "RULE-6")
    def test_python_name_drift(self, tmp_path):
        """Python name-drift — Pass 1 passes, needs LLM."""
        test_file = tmp_path / 'test_cheat.py'
        test_file.write_text('''\
import pytest
def validate_token(t): return True  # Bug: accepts everything
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_rejects_invalid_token():
    # Name says "rejects" but asserts True (accepted)
    assert validate_token("INVALID") is True
''')
        results = check_python(str(test_file), 'feat')
        assert results[0]['status'] == 'pass', "Pass 1 passes — name-drift cheat needs LLM"


# ===========================================================================
# CHEAT 5: No real assertion — lots of setup, zero actual verification
# ===========================================================================

class TestNoRealAssertion:
    """Test runs code but never checks the output. Setup looks thorough."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-24", "RULE-6")
    def test_c_no_assertion(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Computes correct hash')
        data = _run_c(tmp_path, r'''
#include "c_purlin.h"
unsigned int hash(const char *s) {
    unsigned int h = 0;
    while (*s) h = h * 31 + (unsigned char)(*s++);
    return h;
}
int main(void) {
    unsigned int h = hash("hello");
    /* CHEAT: computes hash but hardcodes pass — never checks h */
    purlin_proof("feat", "PROOF-1", "RULE-1",
                 1, "test_computes_hash", "test.c", "unit");
    purlin_proof_finish();
    return 0;
}
''', 'feat')
        _assert_proof_passes(data, "C no-assertion cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('php'), reason='php not available')
    @pytest.mark.proof("proof_plugins", "PROOF-26", "RULE-25")
    def test_php_no_assertion(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Sends notification email')
        data = _run_php(tmp_path, r'''<?php
function send_email(string $to, string $body): bool { return true; }
/** @purlin feat PROOF-1 RULE-1 unit */
function test_sends_notification() {
    // CHEAT: calls function but never checks the return value
    $result = send_email("user@test.com", "Hello");
    // No throw = pass. But $result is never inspected.
}
''', 'feat')
        _assert_proof_passes(data, "PHP no-assertion cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins", "PROOF-28", "RULE-27")
    def test_sql_no_assertion(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Cascade delete removes children')
        # CHEAT: does the delete but never checks if children were removed
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: cascade delete removes children
DELETE FROM parents WHERE id = 1;
SELECT 'PASS';
''', 'feat',
            setup_sql='CREATE TABLE parents (id INTEGER PRIMARY KEY);\n'
                      'CREATE TABLE children (id INTEGER, parent_id INTEGER);\n'
                      'INSERT INTO parents VALUES (1);\n'
                      'INSERT INTO children VALUES (1, 1);')
        _assert_proof_passes(data, "SQL no-assertion cheat passes — needs LLM")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28")
    def test_typescript_no_assertion(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Reverses payload before sending')
        data = _run_typescript(tmp_path, '''\
function reversePayload(data: string): string {
    return data.split("").reverse().join("");
}
// CHEAT: calls reversePayload but never checks the output
const reversed = reversePayload("secret data");
// reversed is never compared to anything
const proofs = [{
    feature: "feat", id: "PROOF-1", rule: "RULE-1",
    test_file: "test.ts", test_name: "test_reverses_payload",
    status: "pass" as "pass" | "fail", tier: "unit",
}];
console.log(JSON.stringify({ proofs }, null, 2));
''', 'feat')
        _assert_proof_passes(data, "TS no-assertion cheat passes — needs LLM")

    @pytest.mark.proof("static_checks", "PROOF-2", "RULE-2")
    def test_python_no_assertion(self, tmp_path):
        """Python no-assertion — caught by Pass 1 (no_assertions check)."""
        test_file = tmp_path / 'test_cheat.py'
        test_file.write_text('''\
import pytest
import json
def encrypt(data): return data[::-1]
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_encrypts_payload():
    payload = {"secret": "value"}
    encrypted = encrypt(json.dumps(payload))
    decoded = json.loads(encrypted[::-1])
    token = decoded.get("secret")
    # CHEAT: lots of setup, zero assertions
''')
        results = check_python(str(test_file), 'feat')
        assert results[0]['status'] == 'fail', "Python no-assertion caught by Pass 1"
        assert results[0]['check'] == 'no_assertions'
