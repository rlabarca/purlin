"""Integration tests for proof plugins across 5 languages.

Each test compiles/interprets REAL executable code in the target language,
runs it through the corresponding Purlin proof plugin, and verifies the
emitted proof JSON matches the contract.

Languages tested: C (gcc), PHP (php), SQL (sqlite3), TypeScript (tsc+node), Python (pytest).

Run with: python3 -m pytest dev/test_multilang_proof_plugins.py -v
"""

import json
import os
import re
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

    @pytest.mark.proof("proof_plugins_c", "PROOF-1", "RULE-1", tier="integration")
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

    @pytest.mark.proof("proof_plugins_c", "PROOF-3", "RULE-1", tier="integration")
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

    @pytest.mark.proof("proof_plugins_c", "PROOF-2", "RULE-2", tier="integration")
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

    @pytest.mark.proof("proof_plugins_php", "PROOF-1", "RULE-1", tier="integration")
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

    @pytest.mark.proof("proof_plugins_php", "PROOF-2", "RULE-2", tier="integration")
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
# PHP plugin source checks - no php binary required
# ---------------------------------------------------------------------------

class TestPHPProofPluginSource:
    """proof_plugins_php RULE-3: an argv array, never a shell string."""

    @pytest.mark.proof("proof_plugins_php", "PROOF-3", "RULE-3", tier="integration")
    def test_php_plugin_launches_through_proc_open_with_an_argv_array(self):
        plugin_path = os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php')
        with open(plugin_path) as f:
            source = f.read()

        launches = [m for m in re.finditer(r'\bproc_open\s*\(', source)]
        assert launches, "no proc_open( launch site found in the PHP plugin"
        for m in launches:
            after = source[m.end():m.end() + 40].lstrip()
            assert after.startswith('['), (
                f"proc_open first argument is not an array literal: {after[:40]!r}")

        forbidden = 'ex' + 'ec('
        assert forbidden not in source, (
            f"{forbidden} is still present in the PHP plugin; a shell string "
            "can be assembled")

# ---------------------------------------------------------------------------
# SQL tests — run with sqlite3
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
class TestSQLProofPlugin:

    @pytest.mark.proof("proof_plugins_sql", "PROOF-1", "RULE-1", tier="integration")
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

    @pytest.mark.proof("proof_plugins_sql", "PROOF-2", "RULE-2", tier="integration")
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
# TypeScript / Vitest reporter — drive the REAL reporter's onFinished(files)
# with a synthetic Vitest 2.x+ task tree. Loaded via tsc (compile) or Node's
# native TypeScript type-stripping (Node >= 22.6). This actually exercises the
# reporter, unlike the old proof which only ran hand-built JSON through node.
# ---------------------------------------------------------------------------

_REPORTER_SRC = os.path.join(PROOF_SCRIPTS, 'vitest_purlin.ts')

# Minimal `glob` stand-in so the compiled/stripped reporter's require("glob")
# resolves without an npm install. It performs the real filesystem walk the
# reporter expects (globSync("specs/**/*.md")) — only the dependency is
# substituted; the reporter's collection and write logic run for real.
_GLOB_SHIM = '''\
const fs = require('fs');
const path = require('path');
function walk(dir, out) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walk(full, out);
    else if (e.name.endsWith('.md')) out.push(full);
  }
}
function globSync(pattern) { const base = pattern.split('/**/')[0]; const out = []; walk(base, out); return out; }
module.exports = { globSync };
'''


def _node_can_run_ts():
    """True if `node` is present and can load .ts — via tsc, or native type-stripping (>=22.6)."""
    if not shutil.which('node'):
        return False
    if shutil.which('tsc'):
        return True
    try:
        out = subprocess.run(['node', '--version'], capture_output=True, text=True)
        major, minor = (int(x) for x in out.stdout.strip().lstrip('v').split('.')[:2])
        return major > 22 or (major == 22 and minor >= 6)
    except Exception:
        return False


@pytest.mark.skipif(
    not _node_can_run_ts(),
    reason='node with a TS loader (tsc or type-stripping) not available'
)
class TestTypeScriptProofPlugin:

    def _drive_reporter(self, tmp_path, files_js, env=None):
        """Load vitest_purlin.ts and call onFinished(files) with the given JS
        task-tree literal, with cwd=tmp_path so it writes proofs under specs/.
        `env` replaces the subprocess environment when given."""
        glob_dir = tmp_path / 'node_modules' / 'glob'
        glob_dir.mkdir(parents=True)
        (glob_dir / 'package.json').write_text('{"name":"glob","version":"0.0.0","main":"index.js"}')
        (glob_dir / 'index.js').write_text(_GLOB_SHIM)

        shutil.copy(_REPORTER_SRC, str(tmp_path / 'vitest_purlin.ts'))

        if shutil.which('tsc'):
            (tmp_path / 'tsconfig.json').write_text(json.dumps({
                "compilerOptions": {
                    "target": "ES2020", "module": "commonjs",
                    "esModuleInterop": True, "skipLibCheck": True,
                    "noEmitOnError": False, "types": [],
                    "outDir": str(tmp_path / "dist"),
                },
                "include": ["vitest_purlin.ts"],
            }))
            # type errors (missing @types/node) are tolerated — we only need the JS
            subprocess.run(['tsc', '--project', str(tmp_path / 'tsconfig.json')],
                           capture_output=True, text=True, cwd=str(tmp_path))
            compiled = tmp_path / 'dist' / 'vitest_purlin.js'
            assert compiled.exists(), "tsc did not emit dist/vitest_purlin.js"
            harness = tmp_path / 'harness.cjs'
            harness.write_text(
                'const Reporter = require("./dist/vitest_purlin.js").default;\n'
                f'const files = {files_js};\n'
                'new Reporter().onFinished(files);\n'
            )
            cmd = ['node', str(harness)]
        else:
            harness = tmp_path / 'harness.mjs'
            harness.write_text(
                'import Reporter from "./vitest_purlin.ts";\n'
                f'const files = {files_js};\n'
                'new Reporter().onFinished(files);\n'
            )
            cmd = ['node', '--experimental-strip-types', str(harness)]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), env=env)
        assert result.returncode == 0, (
            f"reporter harness failed:\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}"
        )

    @pytest.mark.proof("proof_plugins_vitest", "PROOF-2", "RULE-2", tier="integration")
    def test_vitest_reporter_onfinished_walk(self, tmp_path):
        """Vitest 2.x+ onFinished(files) tree walk: pass/fail mapping, skipped
        tasks excluded, test_file resolved from the file task's filepath."""
        spec_dir = tmp_path / 'specs' / 'string'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'string_utils.md').write_text(
            '# Feature: string_utils\n\n## Rules\n'
            '- RULE-1: capitalize returns first letter uppercase\n'
            '- RULE-2: reverse returns string reversed\n\n'
            '## Proof\n- PROOF-1 (RULE-1): test\n- PROOF-2 (RULE-2): test\n'
        )

        # Synthetic Vitest 2.x+ task tree: a file suite task with nested test
        # tasks carrying result.state. A `skip` task must NOT be recorded.
        files_js = '''[{
  type: "suite",
  filepath: process.cwd() + "/test_strings.test.ts",
  tasks: [
    { type: "test", name: "capitalize works [proof:string_utils:PROOF-1:RULE-1:unit]", result: { state: "pass" } },
    { type: "test", name: "reverse works [proof:string_utils:PROOF-2:RULE-2:unit]", result: { state: "fail" } },
    { type: "test", name: "todo case [proof:string_utils:PROOF-9:RULE-9:unit]", result: { state: "skip" } },
  ],
}]'''
        self._drive_reporter(tmp_path, files_js)

        proof_file = spec_dir / 'string_utils.proofs-unit.json'
        # Exactly 2 entries — the skipped task is excluded (len check inside helper).
        _assert_proof_json(str(proof_file), [
            {'feature': 'string_utils', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'unit'},
            {'feature': 'string_utils', 'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'fail', 'tier': 'unit'},
        ])
        with open(proof_file) as f:
            entries = json.load(f)['proofs']
        # test_file is resolved from the file task's filepath (relative to cwd).
        assert all(e['test_file'] == 'test_strings.test.ts' for e in entries), entries

    @pytest.mark.proof("proof_plugins_vitest", "PROOF-1", "RULE-1", tier="integration")
    def test_vitest_reporter_marker_parsing(self, tmp_path):
        """Marker in a test name parses into feature/id/rule/tier identically to Jest."""
        spec_dir = tmp_path / 'specs' / 'svc'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'feat.md').write_text(
            '# Feature: feat\n\n## Rules\n- RULE-1: x\n\n## Proof\n- PROOF-1 (RULE-1): test\n'
        )

        files_js = '''[{
  type: "suite",
  filepath: process.cwd() + "/feat.test.ts",
  tasks: [
    { type: "test", name: "does the thing [proof:feat:PROOF-1:RULE-1:integration]", result: { state: "pass" } },
  ],
}]'''
        self._drive_reporter(tmp_path, files_js)

        proof_file = spec_dir / 'feat.proofs-integration.json'
        _assert_proof_json(str(proof_file), [
            {'feature': 'feat', 'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass', 'tier': 'integration'},
        ])
        # Directly prove RULE-1: the `[proof:feat:PROOF-1:RULE-1:integration]` marker
        # parses into the four fields (feature, id, rule, tier) — identically to Jest.
        with open(proof_file) as f:
            entry = json.load(f)['proofs'][0]
        assert (entry['feature'], entry['id'], entry['rule'], entry['tier']) == \
            ('feat', 'PROOF-1', 'RULE-1', 'integration'), entry


# ---------------------------------------------------------------------------
# Python tests — run with pytest + pytest_purlin plugin
# ---------------------------------------------------------------------------

class TestPythonProofPlugin:

    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
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
    """Verify that a re-run of one test file purges that file's stale entries."""

    @pytest.mark.proof("proof_common", "PROOF-13", "RULE-10", tier="integration")
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
# Write-scoped overwrite: the (feature, tier, test_file) merge key
# ---------------------------------------------------------------------------

class TestWriteScopedMergeKey:
    """proof_common RULE-4/11/12: two test files covering one (feature, tier) coexist.

    Every test here drives the real scripts/proof/pytest_purlin.py in a subprocess with
    cwd set to a temp repo root, which is what the plugin's spec glob and its test-file
    existence check both assume.
    """

    FEATURE = 'ledger'

    def _repo(self, tmp_path):
        """A temp repo root with a 2-rule spec and the real plugin wired into conftest."""
        spec_dir = tmp_path / 'specs' / 'money'
        spec_dir.mkdir(parents=True)
        (spec_dir / f'{self.FEATURE}.md').write_text(
            f'# Feature: {self.FEATURE}\n\n## Rules\n'
            '- RULE-1: debits are recorded\n'
            '- RULE-2: credits are recorded\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): test\n'
            '- PROOF-2 (RULE-2): test\n'
        )
        plugin = os.path.abspath(os.path.join(PROOF_SCRIPTS, 'pytest_purlin.py'))
        (tmp_path / 'conftest.py').write_text(
            'import sys\n'
            f'sys.path.insert(0, r{os.path.dirname(plugin)!r})\n'
            'from pytest_purlin import pytest_configure  # noqa: F401\n'
        )
        return spec_dir / f'{self.FEATURE}.proofs-unit.json'

    def _write_test(self, tmp_path, name, proof_id, rule_id):
        (tmp_path / name).write_text(
            'import pytest\n'
            f'@pytest.mark.proof({self.FEATURE!r}, {proof_id!r}, {rule_id!r})\n'
            f'def test_{proof_id.lower().replace("-", "_")}(): assert True\n'
        )

    def _run(self, tmp_path, name):
        """Run ONE test file, from the repo root, as its own pytest process."""
        r = subprocess.run(
            [sys.executable, '-m', 'pytest', name, '-q', '--no-header'],
            cwd=str(tmp_path), capture_output=True, text=True,
        )
        assert r.returncode == 0, f'{name} failed:\n{r.stdout}\n{r.stderr}'
        return r

    @staticmethod
    def _entries(proof_file):
        return {
            (e['id'], e['test_file']): e
            for e in json.loads(proof_file.read_text())['proofs']
        }

    @pytest.mark.proof("proof_common", "PROOF-14", "RULE-4", tier="integration")
    def test_two_test_files_one_feature_and_tier_coexist_in_either_order(self, tmp_path):
        """Two files writing one (feature, tier) keep both entries, whichever runs last."""
        proof_file = self._repo(tmp_path)
        self._write_test(tmp_path, 'test_debit.py', 'PROOF-1', 'RULE-1')
        self._write_test(tmp_path, 'test_credit.py', 'PROOF-2', 'RULE-2')

        # Order A→B
        self._run(tmp_path, 'test_debit.py')
        self._run(tmp_path, 'test_credit.py')
        assert set(self._entries(proof_file)) == {
            ('PROOF-1', 'test_debit.py'),
            ('PROOF-2', 'test_credit.py'),
        }, 'B must not clobber A'

        # Order B→A, from a clean proof file
        proof_file.unlink()
        self._run(tmp_path, 'test_credit.py')
        self._run(tmp_path, 'test_debit.py')
        assert set(self._entries(proof_file)) == {
            ('PROOF-1', 'test_debit.py'),
            ('PROOF-2', 'test_credit.py'),
        }, 'A must not clobber B'

    @pytest.mark.proof("proof_common", "PROOF-15", "RULE-11", tier="integration")
    def test_deleted_test_file_entry_is_reaped(self, tmp_path):
        """An entry whose test file no longer exists is dropped on the next write.

        Three files, so the assertion separates reaping from a blanket feature purge: the
        deleted file's entry must go while the surviving file that this run also did not
        execute must stay. A purge-everything merge satisfies the first half and fails the
        second.
        """
        proof_file = self._repo(tmp_path)
        self._write_test(tmp_path, 'test_debit.py', 'PROOF-1', 'RULE-1')
        self._write_test(tmp_path, 'test_credit.py', 'PROOF-2', 'RULE-2')
        self._write_test(tmp_path, 'test_balance.py', 'PROOF-1', 'RULE-1')

        self._run(tmp_path, 'test_debit.py')
        self._run(tmp_path, 'test_credit.py')
        assert ('PROOF-1', 'test_debit.py') in self._entries(proof_file)

        (tmp_path / 'test_debit.py').unlink()
        self._run(tmp_path, 'test_balance.py')

        entries = self._entries(proof_file)
        assert ('PROOF-1', 'test_debit.py') not in entries, (
            f'deleted test file should be reaped, got {sorted(entries)}'
        )
        assert ('PROOF-2', 'test_credit.py') in entries, (
            'a still-present file that this run did not execute must survive the reap; '
            f'got {sorted(entries)}'
        )
        assert ('PROOF-1', 'test_balance.py') in entries

    @pytest.mark.proof("proof_common", "PROOF-16", "RULE-12", tier="integration")
    def test_marker_removed_from_a_file_that_is_not_rerun_survives(self, tmp_path):
        """The bounded cost of per-file scoping, asserted so it cannot change silently.

        Dropping a marker from test_debit.py while running only test_credit.py leaves the
        stale entry: the write key is (feature, tier, test_file) and this run never
        executed test_debit.py. The file still exists, so RULE-11's reap does not apply.
        """
        proof_file = self._repo(tmp_path)
        self._write_test(tmp_path, 'test_debit.py', 'PROOF-1', 'RULE-1')
        self._write_test(tmp_path, 'test_credit.py', 'PROOF-2', 'RULE-2')
        self._run(tmp_path, 'test_debit.py')
        self._run(tmp_path, 'test_credit.py')

        # Marker removed, file kept, file NOT re-run.
        (tmp_path / 'test_debit.py').write_text('def test_debit_no_longer_a_proof(): assert True\n')
        self._run(tmp_path, 'test_credit.py')

        entries = self._entries(proof_file)
        assert ('PROOF-1', 'test_debit.py') in entries, (
            'an unexecuted file\'s entry must survive until that file runs again; '
            f'got {sorted(entries)}'
        )
        assert ('PROOF-2', 'test_credit.py') in entries


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


# ---------------------------------------------------------------------------
# xUnit / .NET — drive the REAL custom `dotnet test` logger end to end.
# Builds the logger (scripts/proof/xunit_purlin.cs) plus an xUnit test project,
# runs `dotnet test --logger purlin`, and asserts on the emitted proof JSON.
# One build+run (class-scoped fixture is the "act"); each proof checks one rule.
# ---------------------------------------------------------------------------

_XUNIT_LOGGER_SRC = os.path.join(PROOF_SCRIPTS, 'xunit_purlin.cs')

_LOGGER_CSPROJ = (
    '<Project Sdk="Microsoft.NET.Sdk">\n'
    '  <PropertyGroup><TargetFramework>net8.0</TargetFramework>'
    '<AssemblyName>Purlin.TestLogger</AssemblyName><Nullable>enable</Nullable>'
    '<ImplicitUsings>disable</ImplicitUsings></PropertyGroup>\n'
    '  <ItemGroup><PackageReference Include="Microsoft.TestPlatform.ObjectModel" Version="17.11.1" /></ItemGroup>\n'
    '</Project>\n'
)

_TEST_CSPROJ = (
    '<Project Sdk="Microsoft.NET.Sdk">\n'
    '  <PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>enable</Nullable><IsPackable>false</IsPackable></PropertyGroup>\n'
    '  <ItemGroup>\n'
    '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />\n'
    '    <PackageReference Include="xunit" Version="2.9.2" />\n'
    '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />\n'
    '  </ItemGroup>\n'
    '  <ItemGroup><ProjectReference Include="../logger/logger.csproj" /></ItemGroup>\n'
    '</Project>\n'
)

_TEST_CS = (
    'using Xunit;\n'
    'namespace Svc.Tests {\n'
    '  public class FeatTests {\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-1:RULE-1:unit")]\n'
    '    public void Passes() { Assert.Equal(4, 2+2); }\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-2:RULE-2:unit")]\n'
    '    public void Fails() { Assert.True(false); }\n'
    '    [Fact(Skip="nyi")][Trait("PurlinProof","feat:PROOF-9:RULE-9:unit")]\n'
    '    public void SkippedTagged() { Assert.True(false); }\n'
    '    [Fact]\n'
    '    public void Untagged() { Assert.True(true); }\n'
    '  }\n'
    '}\n'
)


@pytest.mark.skipif(not shutil.which('dotnet'), reason='dotnet SDK not available')
class TestXUnitProofPlugin:

    @pytest.fixture(scope="class")
    def run(self, tmp_path_factory):
        root = tmp_path_factory.mktemp("xunit_proj")
        specs = root / "specs" / "svc"
        specs.mkdir(parents=True)
        (specs / "feat.md").write_text(
            "# Feature: feat\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n\n"
            "## Proof\n- PROOF-1 (RULE-1): t\n- PROOF-2 (RULE-2): t\n"
        )
        # Pre-seed with a DIFFERENT feature — must survive (feature-scoped overwrite).
        (specs / "feat.proofs-unit.json").write_text(json.dumps({
            "tier": "unit",
            "proofs": [{"feature": "otherfeat", "id": "PROOF-1", "rule": "RULE-1",
                        "test_file": "tests/Other.cs", "test_name": "Other.Keep",
                        "status": "pass", "tier": "unit"}],
        }))

        logger = root / "logger"
        logger.mkdir()
        shutil.copy(_XUNIT_LOGGER_SRC, str(logger / "PurlinProofLogger.cs"))
        (logger / "logger.csproj").write_text(_LOGGER_CSPROJ)

        tests = root / "tests"
        tests.mkdir()
        (tests / "tests.csproj").write_text(_TEST_CSPROJ)
        (tests / "Tests.cs").write_text(_TEST_CS)

        env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
        # RULE-2: --logger purlin (custom in-process logger).
        # CollectSourceInformation populates CodeFilePath for RULE-5 (test_file).
        cmd = ["dotnet", "test", "tests/tests.csproj", "--logger", "purlin",
               "--", "RunConfiguration.CollectSourceInformation=true"]
        proc = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True, env=env,
        )
        proof_file = specs / "feat.proofs-unit.json"
        data = json.loads(proof_file.read_text())
        # The logger must have run and recorded the "feat" entries.
        assert any(p["feature"] == "feat" for p in data["proofs"]), (
            f"logger did not record proofs:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
        )
        return {"root": root, "proc": proc, "cmd": cmd, "data": data, "proof_file": proof_file,
                "by_id": {p["id"]: p for p in data["proofs"] if p["feature"] == "feat"}}

    @pytest.mark.proof("proof_plugins_xunit", "PROOF-1", "RULE-1", tier="integration")
    def test_trait_marker_parses(self, run):
        e = run["by_id"]["PROOF-1"]
        assert (e["feature"], e["id"], e["rule"], e["tier"]) == ("feat", "PROOF-1", "RULE-1", "unit"), e

    @pytest.mark.proof("proof_plugins_xunit", "PROOF-2", "RULE-2", tier="integration")
    def test_logger_runs_in_process(self, run):
        # RULE-2: the logger collects in-process, not by post-parsing a .trx file.
        # It emits a completion line to stderr from inside TestRunComplete, which
        # fires within the test-platform process during the run — the line's
        # presence proves in-process collection, not a separate parse step.
        out = run["proc"].stderr + run["proc"].stdout
        assert "[PurlinProofLogger] collected" in out, (
            f"no in-process logger signal in dotnet output:\n{out}"
        )
        # Driven by --logger purlin alone; no trx logger was requested or produced.
        assert "trx" not in run["cmd"], run["cmd"]
        assert not list(run["root"].rglob("*.trx")), "no .trx should be produced"
        assert "PROOF-1" in run["by_id"]

    @pytest.mark.proof("proof_plugins_xunit", "PROOF-3", "RULE-3", tier="integration")
    def test_untagged_ignored(self, run):
        names = [p["test_name"] for p in run["data"]["proofs"]]
        assert not any("Untagged" in n for n in names), names

    @pytest.mark.proof("proof_plugins_xunit", "PROOF-4", "RULE-4", tier="integration")
    def test_status_mapping_and_skip_excluded(self, run):
        by = run["by_id"]
        assert by["PROOF-1"]["status"] == "pass", by["PROOF-1"]
        assert by["PROOF-2"]["status"] == "fail", by["PROOF-2"]
        # the [Fact(Skip=...)] tagged test (PROOF-9/RULE-9) must not be recorded
        assert "PROOF-9" not in by, run["data"]["proofs"]

    @pytest.mark.proof("proof_plugins_xunit", "PROOF-5", "RULE-5", tier="integration")
    def test_relative_file_and_fq_name(self, run):
        e = run["by_id"]["PROOF-1"]
        assert e["test_file"] and not e["test_file"].startswith("/"), e["test_file"]
        assert e["test_file"].endswith(".cs"), e["test_file"]
        assert e["test_name"] == "Svc.Tests.FeatTests.Passes", e["test_name"]

    @pytest.mark.proof("proof_plugins_xunit", "PROOF-6", "RULE-6", tier="integration")
    def test_feature_scoped_overwrite(self, run):
        feats = {p["feature"] for p in run["data"]["proofs"]}
        assert "otherfeat" in feats, "pre-seeded other feature must be preserved"
        assert "feat" in feats
        other = [p for p in run["data"]["proofs"] if p["feature"] == "otherfeat"]
        assert len(other) == 1 and other[0]["test_name"] == "Other.Keep", other


# ---------------------------------------------------------------------------
# Platform-scoped proof files (proof_common RULE-5/15/16/17; proofs_format.md v5)
#
# One test per plugin per behaviour, each driving the real plugin:
#   scoped:  PURLIN_PLATFORM=p1, one marker declaring on(p1) and one unmarked ->
#            the declared entry lands in <feature>.proofs-unit@p1.json with
#            platform "p1" at the top level and on the entry (8 fields); the
#            unmarked entry lands only in <feature>.proofs-unit.json (7 fields).
#   slash:   a backslash-bearing path reaches the plugin through whatever its
#            API allows; no "\" appears in any written test_file.
#   family:  PURLIN_PLATFORM unset -> the scoped file is named after the OS
#            family, computed here from platform.system() independently.
# jest lives here rather than in dev/test_proof_jest.sh because that script is
# not in dev/run_tests.sh, and a proof only that script regenerated would fail
# proof_common RULE-14. The shell harness is covered in dev/test_proof_plugins.sh.
# ---------------------------------------------------------------------------

import platform as _platform_mod
import re as _re

_SEVEN = {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}
_PLUGIN_COPIES = os.path.join(os.path.dirname(__file__), '..', '.purlin', 'plugins')


def _expected_family():
    system = _platform_mod.system()
    return {'Windows': 'windows', 'Darwin': 'macos', 'Linux': 'linux'}.get(system, system.lower())


def _env(platform_id):
    """The subprocess environment: PURLIN_PLATFORM set to `platform_id`, or absent when None."""
    env = {k: v for k, v in os.environ.items() if k != 'PURLIN_PLATFORM'}
    if platform_id is not None:
        env['PURLIN_PLATFORM'] = platform_id
    return env


def _assert_scoped_split(scoped_path, agnostic_path, platform_id, scoped_ids, agnostic_ids):
    """The declared marker went to the scoped file with 8 fields; the unmarked
    one went only to the agnostic file with exactly 7; no backslash anywhere."""
    assert os.path.isfile(scoped_path), f"scoped file not written: {scoped_path}"
    data = json.load(open(scoped_path))
    assert data.get('tier') == 'unit', data
    assert data.get('platform') == platform_id, (
        f"top-level platform must equal the filename id {platform_id!r}: {data}")
    assert {e['id'] for e in data['proofs']} == set(scoped_ids), data['proofs']
    for e in data['proofs']:
        assert e.get('platform') == platform_id, e
        assert set(e) == _SEVEN | {'platform'}, f"scoped entry must carry exactly 8 fields: {sorted(e)}"
        assert '\\' not in e['test_file'], e['test_file']

    assert os.path.isfile(agnostic_path), f"agnostic file not written: {agnostic_path}"
    adata = json.load(open(agnostic_path))
    assert 'platform' not in adata, f"an agnostic file carries no platform: {adata}"
    assert {e['id'] for e in adata['proofs']} == set(agnostic_ids), adata['proofs']
    for e in adata['proofs']:
        assert set(e) == _SEVEN, f"agnostic entry must carry exactly the 7 fields: {sorted(e)}"
        assert '\\' not in e['test_file'], e['test_file']
    scoped_in_agnostic = {e['id'] for e in adata['proofs']} & set(scoped_ids)
    assert not scoped_in_agnostic, (
        f"a declared marker must not also land in the agnostic file: {scoped_in_agnostic}")


def _spec(tmp_path, feature, sub='a'):
    spec_dir = tmp_path / 'specs' / sub
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / f'{feature}.md').write_text(
        f'# Feature: {feature}\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n\n'
        '## Proof\n- PROOF-1 (RULE-1): t\n- PROOF-2 (RULE-2): t\n')
    return spec_dir


# ----- pytest --------------------------------------------------------------

class TestPytestPlatformScoping:

    def _run(self, tmp_path, test_rel, platform_id):
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'pytest_purlin.py'), str(tmp_path / 'conftest.py'))
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', test_rel, '-q', '--no-header', '-p', 'no:cacheprovider'],
            capture_output=True, text=True, cwd=str(tmp_path), env=_env(platform_id))
        assert result.returncode == 0, f"pytest failed:\n{result.stdout}\n{result.stderr}"

    _SRC = (
        'import pytest\n'
        '@pytest.mark.proof("feat", "PROOF-1", "RULE-1", platforms=("p1",))\n'
        'def test_declared(): assert True\n'
        '@pytest.mark.proof("feat", "PROOF-2", "RULE-2")\n'
        'def test_unmarked(): assert True\n'
    )

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_pytest_declared_marker_scopes_and_unmarked_stays_agnostic(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        (tmp_path / 'test_feat.py').write_text(self._SRC)
        self._run(tmp_path, 'test_feat.py', 'p1')
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_pytest_test_file_has_forward_slashes(self, tmp_path):
        # A file literally named with a backslash is collectable on POSIX, and
        # item.fspath.relto(rootdir) hands the plugin that backslash.
        spec_dir = _spec(tmp_path, 'feat')
        (tmp_path / 'tests\\test_feat.py').write_text(self._SRC)
        self._run(tmp_path, 'tests\\test_feat.py', 'p1')
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert e['test_file'] == 'tests/test_feat.py', e['test_file']

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_pytest_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        (tmp_path / 'test_feat.py').write_text(self._SRC)
        self._run(tmp_path, 'test_feat.py', None)
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), os.listdir(spec_dir)
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam
        assert not [n for n in os.listdir(spec_dir) if '@' in n and n != f'feat.proofs-unit@{fam}.json']


# ----- jest ----------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('node'), reason='node not available')
class TestJestPlatformScoping:

    def _run(self, tmp_path, test_file_path, platform_id):
        """Drive the real reporter's onTestResult/onRunComplete in node with a
        fake testFilePath under rootDir=tmp_path."""
        glob_dir = tmp_path / 'node_modules' / 'glob'
        glob_dir.mkdir(parents=True, exist_ok=True)
        (glob_dir / 'package.json').write_text('{"name":"glob","version":"0.0.0","main":"index.js"}')
        (glob_dir / 'index.js').write_text(_GLOB_SHIM)
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'jest_purlin.js'), str(tmp_path / 'jest_purlin.js'))
        harness = tmp_path / 'harness.cjs'
        harness.write_text(
            'const Reporter = require("./jest_purlin.js");\n'
            f'const r = new Reporter({{ rootDir: {json.dumps(str(tmp_path))} }}, {{}});\n'
            f'r.onTestResult(null, {{ testFilePath: {json.dumps(test_file_path)}, testResults: [\n'
            '  { title: "declared [proof:feat:PROOF-1:RULE-1:on(p1)]", status: "passed" },\n'
            '  { title: "unmarked [proof:feat:PROOF-2:RULE-2]", status: "passed" },\n'
            ']});\n'
            'r.onRunComplete();\n')
        result = subprocess.run(['node', str(harness)], capture_output=True, text=True,
                                cwd=str(tmp_path), env=_env(platform_id))
        assert result.returncode == 0, f"jest reporter harness failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_jest_declared_marker_scopes_and_unmarked_stays_agnostic(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, str(tmp_path / 'tests' / 'feat.test.js'), 'p1')
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_jest_test_file_has_forward_slashes(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, str(tmp_path) + '/tests\\sub\\feat.test.js', 'p1')
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert e['test_file'] == 'tests/sub/feat.test.js', e['test_file']

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_jest_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, str(tmp_path / 'tests' / 'feat.test.js'), None)
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), os.listdir(spec_dir)
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam


# ----- vitest --------------------------------------------------------------

@pytest.mark.skipif(not _node_can_run_ts(), reason='node with a TS loader (tsc or type-stripping) not available')
class TestVitestPlatformScoping(TestTypeScriptProofPlugin):

    def _files(self, filepath):
        return (
            '[{ type: "suite", filepath: ' + json.dumps(filepath) + ', tasks: [\n'
            '  { type: "test", name: "declared [proof:feat:PROOF-1:RULE-1:unit:on(p1)]", result: { state: "pass" } },\n'
            '  { type: "test", name: "unmarked [proof:feat:PROOF-2:RULE-2]", result: { state: "pass" } },\n'
            ']}]')

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_vitest_declared_marker_scopes_and_unmarked_stays_agnostic(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._drive_reporter(tmp_path, self._files(str(tmp_path / 'tests' / 'feat.test.ts')), env=_env('p1'))
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_vitest_test_file_has_forward_slashes(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._drive_reporter(tmp_path, self._files(str(tmp_path) + '/tests\\sub\\feat.test.ts'), env=_env('p1'))
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert e['test_file'] == 'tests/sub/feat.test.ts', e['test_file']

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_vitest_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._drive_reporter(tmp_path, self._files(str(tmp_path / 'tests' / 'feat.test.ts')), env=_env(None))
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), os.listdir(spec_dir)
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam

    # The inherited parsing/walk tests are already recorded under the parent
    # class; re-running them here would only duplicate their entries.
    test_vitest_reporter_onfinished_walk = None
    test_vitest_reporter_marker_parsing = None


# ----- C -------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('gcc'), reason='gcc not available')
class TestCPlatformScoping:

    def _run(self, tmp_path, test_file_literal, platform_id):
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'c_purlin.h'), str(tmp_path))
        src = tmp_path / 't.c'
        src.write_text(
            '#include "c_purlin.h"\n'
            'int main(void) {\n'
            f'  purlin_proof_on("feat", "PROOF-1", "RULE-1", 1, "declared", "{test_file_literal}", "unit", "p1");\n'
            f'  purlin_proof("feat", "PROOF-2", "RULE-2", 1, "unmarked", "{test_file_literal}", "unit");\n'
            '  purlin_proof_finish();\n  return 0;\n}\n')
        binary = tmp_path / 't'
        cc = subprocess.run(['gcc', '-o', str(binary), str(src), '-I', str(tmp_path)],
                            capture_output=True, text=True)
        assert cc.returncode == 0, cc.stderr
        run = subprocess.run([str(binary)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        emit = subprocess.run([sys.executable, os.path.join(PROOF_SCRIPTS, 'c_purlin_emit.py')],
                              input=run.stdout, capture_output=True, text=True,
                              cwd=str(tmp_path), env=_env(platform_id))
        assert emit.returncode == 0, emit.stderr
        return run.stdout

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_c_declared_marker_scopes_and_unmarked_stays_agnostic(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        stdout = self._run(tmp_path, 'tests/t.c', 'p1')
        # The header records what was declared; the emitter decides the file.
        by_id = {e['id']: e for e in json.loads(stdout)['proofs']}
        assert by_id['PROOF-1']['platforms'] == 'p1' and by_id['PROOF-2']['platforms'] == '', by_id
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_c_test_file_has_forward_slashes(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        stdout = self._run(tmp_path, 'tests\\\\sub\\\\t.c', 'p1')
        assert '\\\\' in stdout, "the header must hand the emitter the backslashes as given"
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert e['test_file'] == 'tests/sub/t.c', e['test_file']

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_c_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests/t.c', None)
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), os.listdir(spec_dir)
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam


# ----- SQL -----------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
class TestSQLPlatformScoping:

    _SQL = (
        '-- @purlin feat PROOF-1 RULE-1 on(p1)\n-- Test: declared\nSELECT \'PASS\';\n'
        '-- @purlin feat PROOF-2 RULE-2\n-- Test: unmarked\nSELECT \'PASS\';\n'
    )

    def _run(self, tmp_path, rel, platform_id):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(self._SQL)
        result = subprocess.run(['bash', os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh'), rel],
                                capture_output=True, text=True, cwd=str(tmp_path), env=_env(platform_id))
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_sql_declared_marker_scopes_and_unmarked_stays_agnostic(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests/feat.sql', 'p1')
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_sql_test_file_has_forward_slashes(self, tmp_path):
        # The argv path is a file literally named with a backslash on POSIX.
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests\\feat.sql', 'p1')
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert e['test_file'] == 'tests/feat.sql', e['test_file']

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_sql_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests/feat.sql', None)
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), os.listdir(spec_dir)
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam


# ----- PHP -----------------------------------------------------------------

@pytest.mark.skipif(not shutil.which('php'), reason='php not available')
class TestPHPPlatformScoping:

    _PHP = (
        '<?php\n'
        '/** @purlin feat PROOF-1 RULE-1 unit on(p1) */\n'
        'function test_declared() { }\n'
        '/** @purlin feat PROOF-2 RULE-2 unit */\n'
        'function test_unmarked() { }\n'
    )

    def _run(self, tmp_path, rel, platform_id):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(self._PHP)
        result = subprocess.run(['php', os.path.join(PROOF_SCRIPTS, 'phpunit_purlin.php'), rel],
                                capture_output=True, text=True, cwd=str(tmp_path), env=_env(platform_id))
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_php_declared_marker_scopes_and_unmarked_stays_agnostic(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests/FeatTest.php', 'p1')
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_php_test_file_has_forward_slashes(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests\\FeatTest.php', 'p1')
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert e['test_file'] == 'tests/FeatTest.php', e['test_file']

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_php_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat')
        self._run(tmp_path, 'tests/FeatTest.php', None)
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), os.listdir(spec_dir)
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam


# ----- xUnit ---------------------------------------------------------------

_PLATFORM_TEST_CS = (
    'using Xunit;\n'
    'namespace Svc.Tests {\n'
    '  public class PlatTests {\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-1:RULE-1:unit:on(p1)")]\n'
    '    public void Declared() { Assert.True(true); }\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-2:RULE-2")]\n'
    '    public void Unmarked() { Assert.True(true); }\n'
    '  }\n'
    '}\n'
)


@pytest.mark.skipif(not shutil.which('dotnet'), reason='dotnet SDK not available')
class TestXUnitPlatformScoping:

    def _build_and_run(self, root, platform_id):
        (root / 'logger').mkdir()
        shutil.copy(_XUNIT_LOGGER_SRC, str(root / 'logger' / 'PurlinProofLogger.cs'))
        (root / 'logger' / 'logger.csproj').write_text(_LOGGER_CSPROJ)
        (root / 'tests').mkdir()
        (root / 'tests' / 'tests.csproj').write_text(_TEST_CSPROJ)
        (root / 'tests' / 'Tests.cs').write_text(_PLATFORM_TEST_CS)
        env = _env(platform_id)
        env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1')
        proc = subprocess.run(
            ['dotnet', 'test', 'tests/tests.csproj', '--logger', 'purlin',
             '--', 'RunConfiguration.CollectSourceInformation=true'],
            cwd=str(root), capture_output=True, text=True, env=env)
        return proc

    @pytest.fixture(scope='class')
    def scoped_run(self, tmp_path_factory):
        root = tmp_path_factory.mktemp('xunit_plat')
        spec_dir = _spec(root, 'feat', 'svc')
        proc = self._build_and_run(root, 'p1')
        return {'root': root, 'spec_dir': spec_dir, 'proc': proc}

    @pytest.mark.proof("proof_common", "PROOF-21", "RULE-17", tier="integration")
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5", tier="integration")
    def test_xunit_declared_marker_scopes_and_unmarked_stays_agnostic(self, scoped_run):
        spec_dir = scoped_run['spec_dir']
        assert (spec_dir / 'feat.proofs-unit@p1.json').is_file(), (
            f"{os.listdir(spec_dir)}\n{scoped_run['proc'].stdout}\n{scoped_run['proc'].stderr}")
        _assert_scoped_split(spec_dir / 'feat.proofs-unit@p1.json', spec_dir / 'feat.proofs-unit.json',
                             'p1', ['PROOF-1'], ['PROOF-2'])

    @pytest.mark.proof("proof_common", "PROOF-19", "RULE-15", tier="integration")
    def test_xunit_test_file_has_forward_slashes(self, scoped_run):
        # CodeFilePath comes from the compiler's own view of the source path, so a
        # backslash can only reach the logger on Windows; there MakeRelative's
        # Replace turns it into "/". On a POSIX host this asserts the recorded
        # path of the real run and that the replacement is what MakeRelative does.
        spec_dir = scoped_run['spec_dir']
        for name in ('feat.proofs-unit@p1.json', 'feat.proofs-unit.json'):
            for e in json.load(open(spec_dir / name))['proofs']:
                assert '\\' not in e['test_file'] and e['test_file'].endswith('Tests.cs'), e['test_file']
        src = open(_XUNIT_LOGGER_SRC).read()
        body = src[src.index('private static string MakeRelative'):]
        body = body[:body.index('\n        }\n')]
        assert body.count(".Replace('\\\\', '/')") == 2, body

    @pytest.mark.proof("proof_common", "PROOF-22", "RULE-17", tier="integration")
    def test_xunit_unset_env_names_the_family(self, tmp_path):
        spec_dir = _spec(tmp_path, 'feat', 'svc')
        proc = self._build_and_run(tmp_path, None)
        fam = _expected_family()
        assert (spec_dir / f'feat.proofs-unit@{fam}.json').is_file(), (
            f"{os.listdir(spec_dir)}\n{proc.stdout}\n{proc.stderr}")
        assert json.load(open(spec_dir / f'feat.proofs-unit@{fam}.json'))['platform'] == fam


# ----- one plugin per framework, everywhere (RULE-16) -----------------------

class TestOnePluginEverywhere:

    _HOST_TOKENS = _re.compile(
        r'sys\.platform|platform\.system|process\.platform|os\.platform|PHP_OS|RuntimeInformation|\buname\b')
    # Function-definition lines across Python, shell, JS/TS, PHP, C and C#.
    _DEF_RE = _re.compile(
        r'^\s*(?:'
        r'def\s+(?P<py>\w+)\s*\('                                    # Python (also inside shell heredocs)
        r'|(?:export\s+)?(?:async\s+)?function\s+(?P<js>\w+)\s*\('   # JS/TS/PHP
        r'|(?P<sh>\w+)\s*\(\)\s*\{'                                  # shell
        r'|(?:(?:public|private|protected|internal|static|override|async)\s+)*[\w<>\[\]?,. ]+?\s+(?P<cs>\w+)\s*\([^;]*\)\s*(?:\{|$)'  # C/C#
        r'|(?:private|public|protected)?\s*(?P<ts>\w+)\s*\([^)]*\)\s*(?::\s*[\w<>\[\]| ]+)?\s*\{\s*$'  # TS/JS methods
        r')')

    _KEYWORDS = {'if', 'else', 'elseif', 'for', 'foreach', 'while', 'switch', 'catch', 'return', 'try'}

    @staticmethod
    def _enclosing_function(lines, idx):
        """Name of the nearest function definition at or above line idx, or None."""
        for i in range(idx, -1, -1):
            m = TestOnePluginEverywhere._DEF_RE.match(lines[i])
            if m:
                name = next(v for v in m.groupdict().values() if v)
                if name not in TestOnePluginEverywhere._KEYWORDS:
                    return name
        return None

    @pytest.mark.proof("proof_common", "PROOF-20", "RULE-16", tier="integration")
    def test_host_detection_lives_only_in_the_host_platform_helper(self):
        dirs = [os.path.abspath(PROOF_SCRIPTS), os.path.abspath(_PLUGIN_COPIES)]
        checked = 0
        hits = 0
        offenders = []
        for d in dirs:
            for name in sorted(os.listdir(d)):
                path = os.path.join(d, name)
                if not os.path.isfile(path) or name.startswith('.'):
                    continue
                checked += 1
                lines = open(path, encoding='utf-8').read().splitlines()
                for i, line in enumerate(lines):
                    if not self._HOST_TOKENS.search(line):
                        continue
                    hits += 1
                    fn = self._enclosing_function(lines, i)
                    if not fn or 'hostplatform' not in fn.lower().replace('_', ''):
                        offenders.append(f"{os.path.relpath(path)}:{i + 1} in {fn!r}: {line.strip()}")
        assert checked >= 12, f"expected the 8 plugins plus the 4 copies, saw {checked}"
        assert hits >= 7, f"every host-detecting plugin should show its helper; saw {hits} hits"
        assert not offenders, "host detection outside a host_platform helper:\n" + "\n".join(offenders)

    @pytest.mark.proof("proof_common", "PROOF-20", "RULE-16", tier="integration")
    def test_plugin_copies_are_byte_identical_to_the_originals(self):
        pairs = {
            'pytest_purlin.py': 'pytest_purlin.py',
            'jest_purlin.js': 'jest_purlin.js',
            'vitest_purlin.ts': 'vitest_purlin.ts',
            'shell_purlin.sh': 'purlin-proof.sh',
        }
        for src, copy in pairs.items():
            a = open(os.path.join(PROOF_SCRIPTS, src), 'rb').read()
            b = open(os.path.join(_PLUGIN_COPIES, copy), 'rb').read()
            assert a == b, f".purlin/plugins/{copy} differs from scripts/proof/{src}"
