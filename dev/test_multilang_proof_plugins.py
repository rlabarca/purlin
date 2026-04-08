"""Integration tests for proof plugins across 5 languages.

Each test compiles/interprets REAL executable code in the target language,
runs it through the corresponding Purlin proof plugin, and verifies the
emitted proof JSON matches the contract.

Languages tested: C (gcc), PHP (php), SQL (sqlite3), TypeScript (tsc+node), Python (pytest).

Run with: python3 -m pytest dev/test_multilang_proof_plugins.py -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

PROOF_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof')


def _assert_proof_json(proof_json_path, expected_proofs):
    """Validate a proof JSON file matches expected entries."""
    assert os.path.isfile(proof_json_path), f"Proof file not created: {proof_json_path}"
    with open(proof_json_path) as f:
        data = json.load(f)
    assert 'tier' in data, "Missing 'tier' field"
    assert 'proofs' in data, "Missing 'proofs' field"
    proofs = data['proofs']
    assert len(proofs) == len(expected_proofs), (
        f"Expected {len(expected_proofs)} proofs, got {len(proofs)}: {proofs}"
    )
    for expected in expected_proofs:
        matching = [p for p in proofs if p['id'] == expected['id']]
        assert len(matching) == 1, f"Expected exactly 1 proof with id={expected['id']}, got {len(matching)}"
        proof = matching[0]
        for field in ('feature', 'id', 'rule', 'status', 'tier'):
            assert proof[field] == expected[field], (
                f"Proof {expected['id']}: expected {field}={expected[field]!r}, got {proof[field]!r}"
            )
        assert 'test_file' in proof, f"Proof {expected['id']}: missing test_file"
        assert 'test_name' in proof, f"Proof {expected['id']}: missing test_name"


# ---------------------------------------------------------------------------
# C tests — compile with gcc, run binary, pipe to emitter
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
class TestCProofPlugin:

    @pytest.mark.proof("proof_plugins", "PROOF-22", "RULE-22", tier="integration")
    def test_c_proof_plugin_real_compilation(self, tmp_path):
        """Compile and run a real C test, verify proof JSON emission."""
        # Create a minimal spec so the emitter can resolve the directory
        spec_dir = tmp_path / 'specs' / 'math'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'math_ops.md').write_text(
            '# Feature: math_ops\n\n## Rules\n'
            '- RULE-1: Addition returns correct sum\n'
            '- RULE-2: Division by zero returns error code\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )

        # Copy the C header to tmp
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))

        # Write a real C test file
        c_file = tmp_path / 'test_math.c'
        c_file.write_text(r'''
#include "c_purlin.h"

int add(int a, int b) { return a + b; }
int safe_div(int a, int b) { return b == 0 ? -1 : a / b; }

int main(void) {
    /* Test 1: addition */
    int sum = add(2, 3);
    purlin_proof("math_ops", "PROOF-1", "RULE-1",
                 sum == 5, "test_addition", "test_math.c", "unit");

    /* Test 2: division by zero */
    int result = safe_div(10, 0);
    purlin_proof("math_ops", "PROOF-2", "RULE-2",
                 result == -1, "test_div_by_zero", "test_math.c", "unit");

    purlin_proof_finish();
    return 0;
}
''')

        # Compile
        binary = tmp_path / 'test_math'
        result = subprocess.run(
            ['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"C compilation failed:\n{result.stderr}"

        # Run and pipe to emitter
        run_result = subprocess.run(
            [str(binary)], capture_output=True, text=True
        )
        assert run_result.returncode == 0, f"C test runner failed:\n{run_result.stderr}"

        # Parse the JSON output directly
        proof_data = json.loads(run_result.stdout)
        assert len(proof_data['proofs']) == 2

        # Pipe to emitter to test file writing
        emit_result = subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=run_result.stdout, capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert emit_result.returncode == 0, f"Emitter failed:\n{emit_result.stderr}"

        # Verify proof file
        proof_file = spec_dir / 'math_ops.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'math_ops', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
            {'feature': 'math_ops', 'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass', 'tier': 'unit'},
        ])

    @pytest.mark.proof("proof_plugins", "PROOF-24", "RULE-6", tier="integration")
    def test_c_proof_plugin_failing_test(self, tmp_path):
        """C test that fails — verify status='fail' in proof JSON."""
        spec_dir = tmp_path / 'specs' / 'math'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'math_ops.md').write_text(
            '# Feature: math_ops\n\n## Rules\n- RULE-1: test\n\n## Proof\n- PROOF-1 (RULE-1): test\n'
        )
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))

        c_file = tmp_path / 'test_fail.c'
        c_file.write_text(r'''
#include "c_purlin.h"
int main(void) {
    int wrong = 2 + 2;
    purlin_proof("math_ops", "PROOF-1", "RULE-1",
                 wrong == 5, "test_bad_math", "test_fail.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')

        binary = tmp_path / 'test_fail'
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        run_result = subprocess.run([str(binary)], capture_output=True, text=True)

        emit_result = subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=run_result.stdout, capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert emit_result.returncode == 0

        proof_file = spec_dir / 'math_ops.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'math_ops', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'fail', 'tier': 'unit'},
        ])

    @pytest.mark.proof("proof_plugins", "PROOF-23", "RULE-23", tier="integration")
    def test_c_emit_pipeline_writes_to_spec_dir(self, tmp_path):
        """purlin_proof_finish() prints JSON to stdout; c_purlin_emit.py reads and writes proof file."""
        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'login.md').write_text(
            '# Feature: login\n\n## Rules\n- RULE-1: test\n\n## Proof\n- PROOF-1 (RULE-1): test\n'
        )
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))

        c_file = tmp_path / 'test_emit.c'
        c_file.write_text(r'''
#include "c_purlin.h"
int main(void) {
    purlin_proof("login", "PROOF-1", "RULE-1",
                 1, "test_login", "test_emit.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')

        binary = tmp_path / 'test_emit'
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        run_result = subprocess.run([str(binary)], capture_output=True, text=True)
        assert run_result.returncode == 0

        # Verify purlin_proof_finish() output is valid JSON on stdout
        proof_json = json.loads(run_result.stdout)
        assert 'proofs' in proof_json, "purlin_proof_finish() must output JSON with 'proofs' key"

        # Pipe to c_purlin_emit.py and verify it writes the proof file
        emit_result = subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=run_result.stdout, capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert emit_result.returncode == 0, f"c_purlin_emit.py failed:\n{emit_result.stderr}"

        proof_file = spec_dir / 'login.proofs-unit.json'
        assert proof_file.exists(), "c_purlin_emit.py did not write proof file to spec directory"
        _assert_proof_json(str(proof_file), [
            {'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
        ])


# ---------------------------------------------------------------------------
# PHP tests — run with php interpreter
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('php'), reason='php not available')
class TestPHPProofPlugin:

    @pytest.mark.proof("proof_plugins", "PROOF-25", "RULE-24", tier="integration")
    def test_php_proof_plugin_real_execution(self, tmp_path):
        """Execute real PHP test code and verify proof JSON emission."""
        spec_dir = tmp_path / 'specs' / 'cart'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'cart_ops.md').write_text(
            '# Feature: cart_ops\n\n## Rules\n'
            '- RULE-1: Adding item increases total\n'
            '- RULE-2: Empty cart has zero total\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )

        # Write a real PHP test file
        php_file = tmp_path / 'test_cart.php'
        php_file.write_text(r'''<?php
function add_to_cart(array $cart, string $item, float $price): array {
    $cart[$item] = $price;
    return $cart;
}

function cart_total(array $cart): float {
    return array_sum($cart);
}

/** @purlin cart_ops PROOF-1 RULE-1 unit */
function test_add_item_increases_total() {
    $cart = [];
    $cart = add_to_cart($cart, "widget", 9.99);
    $total = cart_total($cart);
    if (abs($total - 9.99) > 0.001) {
        throw new Exception("Expected total 9.99, got {$total}");
    }
}

/** @purlin cart_ops PROOF-2 RULE-2 unit */
function test_empty_cart_zero_total() {
    $total = cart_total([]);
    if ($total !== 0.0) {
        throw new Exception("Expected 0, got {$total}");
    }
}
''')

        # Run the PHP proof plugin
        plugin_path = os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php')
        result = subprocess.run(
            ['php', plugin_path, str(php_file)],
            capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert result.returncode == 0, f"PHP plugin failed:\n{result.stderr}\n{result.stdout}"

        # Parse stdout JSON
        proof_data = json.loads(result.stdout)
        assert len(proof_data['proofs']) == 2

        # Verify proof file
        proof_file = spec_dir / 'cart_ops.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'cart_ops', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
            {'feature': 'cart_ops', 'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass', 'tier': 'unit'},
        ])

    @pytest.mark.proof("proof_plugins", "PROOF-26", "RULE-25", tier="integration")
    def test_php_proof_plugin_failing_test(self, tmp_path):
        """PHP test that throws — verify status='fail' in proof JSON."""
        spec_dir = tmp_path / 'specs' / 'cart'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'cart_ops.md').write_text(
            '# Feature: cart_ops\n\n## Rules\n- RULE-1: test\n\n## Proof\n- PROOF-1 (RULE-1): test\n'
        )

        php_file = tmp_path / 'test_fail.php'
        php_file.write_text(r'''<?php
/** @purlin cart_ops PROOF-1 RULE-1 unit */
function test_deliberate_failure() {
    throw new Exception("This test deliberately fails");
}
''')

        plugin_path = os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php')
        result = subprocess.run(
            ['php', plugin_path, str(php_file)],
            capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert result.returncode == 0

        proof_file = spec_dir / 'cart_ops.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'cart_ops', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'fail', 'tier': 'unit'},
        ])


# ---------------------------------------------------------------------------
# SQL tests — run with sqlite3
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
class TestSQLProofPlugin:

    @pytest.mark.proof("proof_plugins", "PROOF-27", "RULE-26", tier="integration")
    def test_sql_proof_plugin_real_execution(self, tmp_path):
        """Execute real SQL against sqlite3 and verify proof JSON emission."""
        spec_dir = tmp_path / 'specs' / 'db'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'data_integrity.md').write_text(
            '# Feature: data_integrity\n\n## Rules\n'
            '- RULE-1: Unique constraint enforced on email\n'
            '- RULE-2: NOT NULL constraint enforced on name\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )

        # Create a real database with schema
        db_file = tmp_path / 'test.db'
        subprocess.run(
            ['sqlite3', str(db_file)],
            input='CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE);',
            capture_output=True, text=True, check=True
        )

        # Write a real SQL test file
        sql_file = tmp_path / 'test_constraints.sql'
        sql_file.write_text(f'''\
-- @purlin data_integrity PROOF-1 RULE-1 unit
-- Test: unique constraint on email rejects duplicates
INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com');
INSERT OR IGNORE INTO users (name, email) VALUES ('Bob', 'alice@test.com');
SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='alice@test.com') = 1
       THEN 'PASS' ELSE 'FAIL' END;

-- @purlin data_integrity PROOF-2 RULE-2 unit
-- Test: NOT NULL constraint on name prevents empty inserts
INSERT OR IGNORE INTO users (name, email) VALUES (NULL, 'null@test.com');
SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='null@test.com') = 0
       THEN 'PASS' ELSE 'FAIL' END;
''')

        # Run the SQL proof plugin
        plugin_path = os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh')
        result = subprocess.run(
            ['bash', plugin_path, str(sql_file), str(db_file)],
            capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert result.returncode == 0, f"SQL plugin failed:\n{result.stderr}\n{result.stdout}"

        # Parse stdout JSON
        proof_data = json.loads(result.stdout)
        assert len(proof_data['proofs']) == 2

        # Verify proof file
        proof_file = spec_dir / 'data_integrity.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'data_integrity', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
            {'feature': 'data_integrity', 'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass', 'tier': 'unit'},
        ])

    @pytest.mark.proof("proof_plugins", "PROOF-28", "RULE-27", tier="integration")
    def test_sql_proof_plugin_failing_test(self, tmp_path):
        """SQL test that produces FAIL result."""
        spec_dir = tmp_path / 'specs' / 'db'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'data_integrity.md').write_text(
            '# Feature: data_integrity\n\n## Rules\n- RULE-1: test\n\n## Proof\n- PROOF-1 (RULE-1): test\n'
        )

        db_file = tmp_path / 'test.db'
        subprocess.run(
            ['sqlite3', str(db_file)],
            input='CREATE TABLE items (id INTEGER PRIMARY KEY, qty INTEGER);',
            capture_output=True, text=True, check=True
        )

        sql_file = tmp_path / 'test_fail.sql'
        sql_file.write_text('''\
-- @purlin data_integrity PROOF-1 RULE-1 unit
-- Test: deliberately failing — expect 99 rows but there are 0
SELECT CASE WHEN (SELECT count(*) FROM items) = 99
       THEN 'PASS' ELSE 'FAIL' END;
''')

        plugin_path = os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh')
        result = subprocess.run(
            ['bash', plugin_path, str(sql_file), str(db_file)],
            capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert result.returncode == 0

        proof_file = spec_dir / 'data_integrity.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'data_integrity', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'fail', 'tier': 'unit'},
        ])


# ---------------------------------------------------------------------------
# TypeScript tests — compile with tsc, run with node
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not shutil.which('tsc') or not shutil.which('node'),
    reason='tsc or node not available'
)
class TestTypeScriptProofPlugin:

    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28", tier="integration")
    def test_typescript_proof_plugin_real_compilation(self, tmp_path):
        """Compile real TypeScript, run with Node, verify proof JSON."""
        spec_dir = tmp_path / 'specs' / 'string'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'string_utils.md').write_text(
            '# Feature: string_utils\n\n## Rules\n'
            '- RULE-1: capitalize returns first letter uppercase\n'
            '- RULE-2: reverse returns string reversed\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )

        # Write real TypeScript source + test
        ts_file = tmp_path / 'test_strings.ts'
        ts_file.write_text('''\
function capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function reverse(s: string): string {
    return s.split("").reverse().join("");
}

interface ProofEntry {
    feature: string; id: string; rule: string;
    test_file: string; test_name: string;
    status: "pass" | "fail"; tier: string;
}

const proofs: ProofEntry[] = [];

function proof(feature: string, id: string, rule: string,
               passed: boolean, testName: string, tier: string = "unit") {
    proofs.push({
        feature, id, rule,
        test_file: "test_strings.ts",
        test_name: testName,
        status: passed ? "pass" : "fail",
        tier,
    });
}

// Test 1: capitalize
const cap = capitalize("hello");
proof("string_utils", "PROOF-1", "RULE-1",
      cap === "Hello", "test_capitalize");

// Test 2: reverse
const rev = reverse("abcd");
proof("string_utils", "PROOF-2", "RULE-2",
      rev === "dcba", "test_reverse");

// Emit JSON
console.log(JSON.stringify({ proofs }, null, 2));
''')

        # Write tsconfig
        tsconfig = tmp_path / 'tsconfig.json'
        tsconfig.write_text(json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "strict": True,
                "outDir": str(tmp_path / "dist"),
            },
            "include": ["*.ts"],
        }))

        # Compile TypeScript
        tsc_result = subprocess.run(
            ['tsc', '--project', str(tsconfig)],
            capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert tsc_result.returncode == 0, f"TypeScript compilation failed:\n{tsc_result.stderr}"

        # Run compiled JavaScript
        js_file = tmp_path / 'dist' / 'test_strings.js'
        assert js_file.exists(), f"Compiled JS not found at {js_file}"

        run_result = subprocess.run(
            ['node', str(js_file)],
            capture_output=True, text=True
        )
        assert run_result.returncode == 0, f"Node execution failed:\n{run_result.stderr}"

        # Parse JSON and pipe to C emitter (reuse — it's generic JSON)
        proof_data = json.loads(run_result.stdout)
        assert len(proof_data['proofs']) == 2

        emit_result = subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=run_result.stdout, capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert emit_result.returncode == 0

        proof_file = spec_dir / 'string_utils.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'string_utils', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
            {'feature': 'string_utils', 'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass', 'tier': 'unit'},
        ])

    @pytest.mark.proof("proof_plugins", "PROOF-29", "RULE-28", tier="integration")
    def test_typescript_proof_plugin_failing_test(self, tmp_path):
        """TypeScript test that fails — verify status='fail'."""
        spec_dir = tmp_path / 'specs' / 'string'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'string_utils.md').write_text(
            '# Feature: string_utils\n\n## Rules\n- RULE-1: test\n\n## Proof\n- PROOF-1 (RULE-1): test\n'
        )

        ts_file = tmp_path / 'test_fail.ts'
        ts_file.write_text('''\
const proofs: Array<{feature: string; id: string; rule: string;
    test_file: string; test_name: string; status: "pass"|"fail"; tier: string}> = [];

const result: string = "hello";
proofs.push({
    feature: "string_utils", id: "PROOF-1", rule: "RULE-1",
    test_file: "test_fail.ts", test_name: "test_wrong_value",
    status: result === "WRONG" ? "pass" : "fail",
    tier: "unit",
});

console.log(JSON.stringify({ proofs }, null, 2));
''')

        tsconfig = tmp_path / 'tsconfig.json'
        tsconfig.write_text(json.dumps({
            "compilerOptions": {"target": "ES2020", "module": "commonjs",
                                "strict": True, "outDir": str(tmp_path / "dist")},
            "include": ["*.ts"],
        }))

        subprocess.run(['tsc', '--project', str(tsconfig)],
                       capture_output=True, text=True, check=True, cwd=str(tmp_path))
        run_result = subprocess.run(
            ['node', str(tmp_path / 'dist' / 'test_fail.js')],
            capture_output=True, text=True
        )

        emit_result = subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=run_result.stdout, capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert emit_result.returncode == 0

        proof_file = spec_dir / 'string_utils.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'string_utils', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'fail', 'tier': 'unit'},
        ])


# ---------------------------------------------------------------------------
# Python tests — run with pytest + pytest_purlin plugin
# ---------------------------------------------------------------------------

class TestPythonProofPlugin:

    @pytest.mark.proof("proof_plugins", "PROOF-5", "RULE-5", tier="integration")
    def test_python_proof_plugin_real_execution(self, tmp_path):
        """Run real pytest tests with proof markers and verify JSON emission."""
        spec_dir = tmp_path / 'specs' / 'calc'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'calculator.md').write_text(
            '# Feature: calculator\n\n## Rules\n'
            '- RULE-1: add returns sum\n'
            '- RULE-2: multiply returns product\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )

        # Write a real Python test file
        test_file = tmp_path / 'test_calc.py'
        test_file.write_text('''\
import pytest

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

@pytest.mark.proof("calculator", "PROOF-1", "RULE-1")
def test_add():
    assert add(2, 3) == 5

@pytest.mark.proof("calculator", "PROOF-2", "RULE-2")
def test_multiply():
    assert multiply(4, 5) == 20
''')

        # Copy the pytest plugin
        conftest = tmp_path / 'conftest.py'
        plugin_src = os.path.join(PROOF_SCRIPTS, 'pytest_purlin.py')
        with open(plugin_src) as f:
            plugin_code = f.read()
        conftest.write_text(plugin_code)

        # Run pytest
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_file), '-v'],
            capture_output=True, text=True,
            cwd=str(tmp_path)
        )
        assert result.returncode == 0, f"pytest failed:\n{result.stdout}\n{result.stderr}"

        # Verify proof file
        proof_file = spec_dir / 'calculator.proofs-unit.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'calculator', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
            {'feature': 'calculator', 'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass', 'tier': 'unit'},
        ])


# ---------------------------------------------------------------------------
# Proof purging: removed tests must not carry over
# ---------------------------------------------------------------------------

class TestProofPurging:
    """Verify that feature-scoped overwrite purges stale entries on re-run."""

    @pytest.mark.proof("proof_plugins", "PROOF-32", "RULE-29", tier="integration")
    def test_removed_test_purged_on_rerun(self, tmp_path):
        """Run with 2 proofs, then re-run with only 1 — verify the old entry is purged."""
        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'login.md').write_text(
            '# Feature: login\n\n## Rules\n'
            '- RULE-1: Validates password\n'
            '- RULE-2: Returns token\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )

        plugins_dir = tmp_path / '.purlin' / 'plugins'
        plugins_dir.mkdir(parents=True)
        src = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof', 'pytest_purlin.py')
        shutil.copy(src, str(plugins_dir / 'pytest_purlin.py'))

        conftest = tmp_path / 'conftest.py'
        conftest.write_text(
            "import sys\n"
            f"sys.path.insert(0, r'{str(plugins_dir)}')\n"
            "from pytest_purlin import pytest_configure\n"
        )

        # Run 1: two proofs
        test_file = tmp_path / 'test_login.py'
        test_file.write_text(
            "import pytest\n"
            "@pytest.mark.proof('login', 'PROOF-1', 'RULE-1')\n"
            "def test_password():\n    assert True\n"
            "@pytest.mark.proof('login', 'PROOF-2', 'RULE-2')\n"
            "def test_token():\n    assert True\n"
        )
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_file), '-v', '--tb=short'],
            cwd=str(tmp_path), capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Run 1 failed:\n{result.stdout}\n{result.stderr}"

        proof_file = spec_dir / 'login.proofs-unit.json'
        with open(str(proof_file)) as f:
            data = json.load(f)
        assert len(data['proofs']) == 2, "Run 1 should produce 2 proofs"

        # Run 2: remove the second test (only PROOF-1 remains)
        test_file.write_text(
            "import pytest\n"
            "@pytest.mark.proof('login', 'PROOF-1', 'RULE-1')\n"
            "def test_password():\n    assert True\n"
        )
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_file), '-v', '--tb=short'],
            cwd=str(tmp_path), capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Run 2 failed:\n{result.stdout}\n{result.stderr}"

        with open(str(proof_file)) as f:
            data = json.load(f)
        assert len(data['proofs']) == 1, \
            f"Run 2 should purge removed test, got {len(data['proofs'])} proofs"
        assert data['proofs'][0]['id'] == 'PROOF-1', \
            "Only PROOF-1 should remain after removing PROOF-2's test"


# ---------------------------------------------------------------------------
# Cross-language: proof-file checks work on output from ANY plugin
# ---------------------------------------------------------------------------

class TestCrossLanguageProofFileChecks:
    """Verify that check_proof_file detects collisions/orphans in JSON
    produced by real language-specific plugins."""

    @pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15", tier="integration")
    def test_collision_detected_in_c_output(self, tmp_path):
        """C test emits duplicate PROOF-1 for different rules — check_proof_file catches it."""
        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'auth_login.md').write_text(
            '# Feature: auth_login\n\n## Rules\n'
            '- RULE-1: Validates password\n- RULE-2: Returns token\n\n'
            '## Proof\n- PROOF-1 (RULE-1): test\n- PROOF-2 (RULE-2): test\n'
        )
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))

        c_file = tmp_path / 'test_collision.c'
        c_file.write_text(r'''
#include "c_purlin.h"
int main(void) {
    purlin_proof("auth_login", "PROOF-1", "RULE-1", 1, "test_a", "test.c", "unit");
    purlin_proof("auth_login", "PROOF-1", "RULE-2", 1, "test_b", "test.c", "unit");
    purlin_proof_finish();
    return 0;
}
''')

        binary = tmp_path / 'test_collision'
        subprocess.run(['gcc', '-o', str(binary), str(c_file), '-I', str(tmp_path)],
                       capture_output=True, text=True, check=True)
        run_result = subprocess.run([str(binary)], capture_output=True, text=True)
        subprocess.run(
            [sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
            input=run_result.stdout, capture_output=True, text=True,
            cwd=str(tmp_path)
        )

        # Now run check_proof_file on the result
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))
        from static_checks import check_proof_file

        proof_file = spec_dir / 'auth_login.proofs-unit.json'
        findings = check_proof_file(str(proof_file), spec_path=str(spec_dir / 'auth_login.md'))
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 1
        assert collisions[0]['proof_id'] == 'PROOF-1'
        assert set(collisions[0]['rules']) == {'RULE-1', 'RULE-2'}
