"""Tests for static_checks.py.

Covers the five Python checks (assert_true_literal, tautology, no_assertion,
bare_except, logic_mirroring, mock_of_target), the JS, C#, shell and SQL body
checks, the CLI, the whole-project sweep, the run scope, the file lock, and the
language-agnostic proof-record checks (proof_id_collision, proof_rule_orphan).
"""

import ast
import builtins
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'review'))
import static_checks
from static_checks import (
    analyze_test_file,
    check_csharp,
    check_js,
    check_proof_file,
    check_python,
    check_shell,
    check_spec_coverage,
    check_sql,
    deterministic_sweep,
    resolve_test_file_from_name,
    _read_rule_descriptions,
)

STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'review', 'static_checks.py'
)
_STATIC_CHECKS_PY = STATIC_CHECKS_PY


def _write_tmp(content, suffix='.py'):
    f = tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name

def _scaffold_proof(root, feature='login', proof_id='PROOF-1', rule_id='RULE-1',
                    test_file='tests/test_login.py', test_name='test_login',
                    rule_text=None, description=None, tier='unit',
                    test_body='    assert 1 + 1 == 2', write_test=True):
    """Write the spec, proof record and test function behind <feature>/<proof_id>.

    The record lands in `.purlin/runtime/proofs/<feature>.<tier>.json`, where the
    sweep reads it, and the spec in `specs/app/<feature>.md`.

    Repeated calls accumulate: a second proof for the same feature is added to the
    same spec, proof file and test file rather than replacing the first. Calling
    again for the SAME proof_id replaces just that proof's test function, which is
    how a test simulates an edit to the graded code.

    With `write_test` False only the spec and the proof record are written and
    the test file is left to the caller, which is how a test scaffolds one source
    file carrying several proofs in a language this helper does not generate.

    Returns the path of the test file (written or merely named).
    """
    spec_dir = os.path.join(root, 'specs', 'app')
    os.makedirs(spec_dir, exist_ok=True)
    spec_path = os.path.join(spec_dir, f'{feature}.md')
    rule_text = rule_text or f'{feature} enforces {rule_id} on every request'
    description = description or (
        f'Call {feature}() and verify the {rule_id} branch returns 200')

    # --- spec: merge this rule/proof into any spec already scaffolded ---
    rules, proofs = [], []
    if os.path.isfile(spec_path):
        for line in open(spec_path, encoding='utf-8').read().splitlines():
            if re.match(r'^- RULE-\d+:', line):
                rules.append(line)
            elif re.match(r'^- PROOF-\d+ ', line):
                proofs.append(line)
    rules = [r for r in rules if not r.startswith(f'- {rule_id}:')]
    rules.append(f'- {rule_id}: {rule_text}')
    proofs = [p for p in proofs if not p.startswith(f'- {proof_id} ')]
    proofs.append(f'- {proof_id} ({rule_id}): {description} @{tier}')
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(
            f'# Feature: {feature}\n\n'
            f'> Scope: {test_file}\n\n'
            '## Rules\n\n' + '\n'.join(sorted(rules)) + '\n\n'
            '## Proof\n\n' + '\n'.join(sorted(proofs)) + '\n'
        )

    # --- proof record: the only record of which test function backs the proof ---
    runtime_dir = os.path.join(root, '.purlin', 'runtime', 'proofs')
    os.makedirs(runtime_dir, exist_ok=True)
    proof_path = os.path.join(runtime_dir, f'{feature}.{tier}.json')
    records = []
    if os.path.isfile(proof_path):
        try:
            records = json.load(open(proof_path, encoding='utf-8')).get('proofs', [])
        except (json.JSONDecodeError, OSError):
            records = []
    records = [r for r in records if r.get('id') != proof_id]
    records.append({
        'feature': feature, 'id': proof_id, 'rule': rule_id,
        'test_file': test_file, 'test_name': test_name,
        'status': 'pass', 'tier': tier,
    })
    with open(proof_path, 'w', encoding='utf-8') as f:
        json.dump({'tier': tier, 'proofs': records}, f, indent=2)

    # --- the test itself ---
    test_path = os.path.join(root, *test_file.split('/'))
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    if not write_test:
        return test_path
    if test_file.endswith('.py'):
        block = (f'@pytest.mark.proof("{feature}", "{proof_id}", "{rule_id}")\n'
                 f'def {test_name}():\n{test_body}')
        blocks = ['import pytest']
        if os.path.isfile(test_path):
            existing = open(test_path, encoding='utf-8').read().rstrip('\n')
            blocks = existing.split('\n\n\n') or blocks
            blocks = [blocks[0]] + [
                b for b in blocks[1:]
                if f'"{proof_id}"' not in b and f'def {test_name}(' not in b
            ]
        blocks.append(block)
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write('\n\n\n'.join(blocks) + '\n')
    else:
        # A language with no extractor here (shell): the proof still resolves,
        # but no test code enters the key.
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env bash\n'
                    f'purlin_proof "{feature}" "{proof_id}" "{rule_id}" pass\n')
    return test_path

def _write_spec(rules):
    content = "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
    for rid, desc in rules.items():
        content += f"- {rid}: {desc}\n"
    content += "\n## Proof\n"
    for rid in rules:
        pid = rid.replace("RULE", "PROOF")
        content += f"- {pid} ({rid}): test\n"
    return _write_tmp(content, suffix='.md')

class TestAssertTrue:

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1", tier="integration")
    def test_detects_assert_true(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true_literal'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-2", "RULE-2", tier="integration")
    def test_detects_assert_is_not_none(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    result = do_something()
    assert result is not None
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'tautology'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-3", "RULE-2", tier="integration")
    def test_detects_assert_len_gte_zero(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    items = get_items()
    assert len(items) >= 0
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'tautology'
        finally:
            os.unlink(path)


class TestNoAssertions:

    @pytest.mark.proof("static_checks", "PROOF-4", "RULE-3", tier="integration")
    def test_detects_no_assertions(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    result = do_something()
    print(result)
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertion'
        finally:
            os.unlink(path)


class TestBareExcept:

    @pytest.mark.proof("static_checks", "PROOF-5", "RULE-4", tier="integration")
    def test_detects_bare_except_pass(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    try:
        result = do_something()
    except Exception:
        pass
    assert result == "ok"
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'bare_except'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-6", "RULE-4", tier="integration")
    def test_detects_bare_except_no_type(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    try:
        result = do_something()
    except:
        pass
    assert result == "ok"
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'bare_except'
        finally:
            os.unlink(path)


class TestLogicMirroring:

    @pytest.mark.proof("static_checks", "PROOF-7", "RULE-5", tier="integration")
    def test_detects_logic_mirroring(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    expected = hash_func(input_val)
    result = hash_func(input_val)
    assert result == expected
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'logic_mirroring'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-7", tier="integration")
    def test_no_mirroring_with_literal(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_good():
    result = hash_func("secret")
    assert result == "5e884898da28047151d0e56f8dc6292773603d0d"
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'pass'
        finally:
            os.unlink(path)


class TestMockTargetMatch:

    @pytest.mark.proof("static_checks", "PROOF-9", "RULE-6", tier="integration")
    def test_detects_mock_matching_rule(self):
        path = _write_tmp('''
import pytest
from unittest.mock import patch

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
@patch("auth.bcrypt.checkpw")
def test_bad(mock_checkpw):
    mock_checkpw.return_value = True
    assert login("alice") == 200
''')
        spec_path = _write_spec({"RULE-1": "Passwords hashed with bcrypt"})
        try:
            results = check_python(path, "testfeat", _read_rule_descriptions(spec_path))
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'mock_of_target'
        finally:
            os.unlink(path)
            os.unlink(spec_path)

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-7", tier="integration")
    def test_no_match_when_mock_unrelated(self):
        path = _write_tmp('''
import pytest
from unittest.mock import patch

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
@patch("email.send_notification")
def test_ok(mock_email):
    mock_email.return_value = True
    assert login("alice") == 200
''')
        spec_path = _write_spec({"RULE-1": "Passwords hashed with bcrypt"})
        try:
            results = check_python(path, "testfeat", _read_rule_descriptions(spec_path))
            assert len(results) == 1
            assert results[0]['status'] == 'pass'
        finally:
            os.unlink(path)
            os.unlink(spec_path)


class TestJsonOutput:

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-16", tier="integration")
    def test_json_has_required_fields(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_good():
    assert 1 == 1

@pytest.mark.proof("testfeat", "PROOF-2", "RULE-2")
def test_bad():
    assert True
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat", "--json"],
                capture_output=True, text=True
            )
            data = json.loads(result.stdout)
            assert 'proofs' in data
            assert isinstance(data['proofs'], list)
            assert len(data['proofs']) == 2
            for proof in data['proofs']:
                assert 'proof_id' in proof
                assert 'rule_id' in proof
                assert 'test_name' in proof
                assert 'status' in proof
                assert 'reason' in proof
        finally:
            os.unlink(path)


class TestExitCodes:

    @pytest.mark.proof("static_checks", "PROOF-12", "RULE-17", tier="integration")
    def test_exit_0_when_all_pass(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_good():
    result = do_something()
    assert result == "expected"
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat"],
                capture_output=True, text=True
            )
            assert result.returncode == 0
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-17", tier="integration")
    def test_exit_0_with_fail_status_when_defects_found(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat", "--json"],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert any(p['status'] == 'fail' for p in data['proofs'])
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-14", "RULE-17", tier="integration")
    def test_exit_2_is_reserved_for_a_real_error(self):
        """RULE-7's other half: exit 2 is reserved for real errors. A test file
        that does not exist is one, and it must not be confused with the exit 0
        a completed analysis returns however weak the test it graded."""
        missing = os.path.join(tempfile.gettempdir(),
                               'purlin_no_such_test_file_9184.py')
        assert not os.path.exists(missing), missing
        result = subprocess.run(
            [sys.executable, STATIC_CHECKS_PY, missing, "testfeat"],
            capture_output=True, text=True
        )
        assert result.returncode == 2, (
            "a missing input file is a real error and must exit 2, got "
            f"{result.returncode}\nstdout={result.stdout!r}\n"
            f"stderr={result.stderr!r}")
        data = json.loads(result.stdout)
        assert data['error'] == f'File not found: {missing}', (
            f"exit 2 did not name the missing file: {data!r}")
        assert 'proofs' not in data, (
            f"a real error must not report an analysis: {data!r}")


class TestSpecCoverage:

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-18", tier="integration")
    def test_spec_coverage_counts(self):
        """check_spec_coverage returns rule_count and proof_count."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
            "- RULE-1: Verify agent.md contains ## Core Loop section\n"
            "- RULE-2: Returns 200 on valid credentials\n"
            "- RULE-3: Grep skill files for ## Usage heading\n"
            "\n## Proof\n"
            "- PROOF-1 (RULE-1): test\n"
            "- PROOF-2 (RULE-2): test\n"
            "- PROOF-3 (RULE-3): test\n",
            suffix='.md'
        )
        try:
            result = check_spec_coverage(path)
            assert result['rule_count'] == 3
            assert result['proof_count'] == 3
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-18", tier="integration")
    def test_spec_coverage_ignores_a_proof_tag(self):
        """A trailing `@e2e` is metadata, so the proof still counts once."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
            "- RULE-1: Verify file exists in specs directory\n"
            "- RULE-2: Returns error when missing\n"
            "\n## Proof\n"
            "- PROOF-1 (RULE-1): test @e2e\n"
            "- PROOF-2 (RULE-2): test @manual(qa@example.com, 2026-01-01, abc1234)\n",
            suffix='.md'
        )
        try:
            result = check_spec_coverage(path)
            assert result['rule_count'] == 2
            assert result['proof_count'] == 2
            descriptions = static_checks._read_proof_descriptions(path)
            assert [d['description'] for d in descriptions] == ['test', 'test']
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-17", "RULE-18", tier="integration")
    def test_spec_coverage_empty(self):
        """Spec with no rules returns zero counts."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n",
            suffix='.md'
        )
        try:
            result = check_spec_coverage(path)
            assert result['rule_count'] == 0
            assert result['proof_count'] == 0
        finally:
            os.unlink(path)

class TestShellIfElsePair:

    @pytest.mark.proof("static_checks", "PROOF-18", "RULE-8", tier="integration")
    def test_if_else_pair_not_flagged(self):
        """if/else proof pair with grep condition should pass, not be flagged."""
        path = _write_tmp('''#!/usr/bin/env bash
source shell_purlin.sh
output=$(some_command)
if echo "$output" | grep -q "VERIFIED"; then
  purlin_proof "testfeat" "PROOF-1" "RULE-1" pass "checks VERIFIED"
else
  purlin_proof "testfeat" "PROOF-1" "RULE-1" fail "checks VERIFIED"
fi
''', suffix='.sh')
        try:
            results = check_shell(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'pass'
            assert results[0]['proof_id'] == 'PROOF-1'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-19", "RULE-8", tier="integration")
    def test_hardcoded_pass_still_caught(self):
        """A bare purlin_proof pass with no test logic should still be flagged."""
        path = _write_tmp('''#!/usr/bin/env bash
source shell_purlin.sh
purlin_proof "testfeat" "PROOF-1" "RULE-1" pass "no test here"
''', suffix='.sh')
        try:
            results = check_shell(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'tautology'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-20", "RULE-8", tier="integration")
    def test_if_else_pair_no_condition_flagged(self):
        """if/else pair with no real test logic in condition should still fail."""
        path = _write_tmp('''#!/usr/bin/env bash
source shell_purlin.sh
if true; then
  purlin_proof "testfeat" "PROOF-1" "RULE-1" pass "no real check"
else
  purlin_proof "testfeat" "PROOF-1" "RULE-1" fail "no real check"
fi
''', suffix='.sh')
        try:
            results = check_shell(path, "testfeat")
            assert len(results) == 1
            # The `if` keyword IS in the segment, so has_logic is true
            # This is acceptable — `if true` has test logic (the if keyword)
            # The deeper semantic issue would be caught by LLM Pass 2
        finally:
            os.unlink(path)


class TestAssertTrueLiteral:
    """RULE-14: the literal shapes and the heuristic ones get different names."""

    @pytest.mark.proof("static_checks", "PROOF-21", "RULE-1", tier="integration")
    def test_a_literal_assert_true_is_named_assert_true_literal(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true_literal', results[0]
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-22", "RULE-2", tier="integration")
    def test_a_heuristic_always_true_assert_is_named_tautology(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    result = do_something()
    assert result is not None
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'tautology', results[0]
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Proof-file structural checks (Pass 0.5 — language-agnostic)
#
# These tests verify that check_proof_file works regardless of which language
# produced the proof record. Each test creates records as if emitted by
# different test runners (Python/pytest, JavaScript/Jest, Shell, SQL, Vitest).
# ---------------------------------------------------------------------------

def _write_proof_json(tmp_path, feature, tier, proofs):
    """Write a proof JSON file and return its path."""
    path = tmp_path / f"{feature}.proofs-{tier}.json"
    path.write_text(json.dumps({"tier": tier, "proofs": proofs}, indent=2))
    return str(path)


def _write_spec_file(tmp_path, feature, rules):
    """Write a minimal spec file and return its path."""
    content = f"# Feature: {feature}\n\n## Rules\n"
    for rid, desc in rules.items():
        content += f"- {rid}: {desc}\n"
    content += "\n## Proof\n"
    for rid in rules:
        pid = rid.replace("RULE", "PROOF")
        content += f"- {pid} ({rid}): test\n"
    path = tmp_path / f"{feature}.md"
    path.write_text(content)
    return str(path)


# Language-specific proof entry factories — each simulates the output
# of a real test framework's proof plugin.

def _python_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_login.py",
        "test_name": "test_validates_credentials",
        "status": status, "tier": "unit",
    }


def _jest_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "src/__tests__/login.test.ts",
        "test_name": "validates credentials [proof:login:PROOF-1:RULE-1:unit]",
        "status": status, "tier": "unit",
    }


def _shell_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_login.sh",
        "test_name": "purlin_proof login PROOF-1 RULE-1 pass",
        "status": status, "tier": "e2e",
    }

def _sql_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_constraints.sql",
        "test_name": "check_foreign_key_enforced",
        "status": status, "tier": "integration",
    }


def _typescript_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "src/__tests__/auth.spec.ts",
        "test_name": "should validate credentials",
        "status": status, "tier": "unit",
    }


# Map language name to factory for parametrized tests
_LANGUAGE_FACTORIES = {
    "python": _python_proof,
    "javascript": _jest_proof,
    "shell": _shell_proof,
    "sql": _sql_proof,
    "typescript": _typescript_proof,
}


class TestProofIdCollision:
    """Proof ID collision detection across all supported language contexts."""

    @pytest.mark.parametrize("lang,factory", list(_LANGUAGE_FACTORIES.items()))
    @pytest.mark.proof("static_checks", "PROOF-23", "RULE-19", tier="integration")
    def test_detects_collision_per_language(self, tmp_path, lang, factory):
        """Same PROOF-1 targeting RULE-1 and RULE-2 — detected regardless of source language."""
        proofs = [
            factory("login", "PROOF-1", "RULE-1"),
            factory("login", "PROOF-1", "RULE-2"),
            factory("login", "PROOF-2", "RULE-3"),  # no collision
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 1, f"Expected 1 collision for {lang}, got {len(collisions)}"
        assert collisions[0]['proof_id'] == 'PROOF-1'
        assert set(collisions[0]['rules']) == {'RULE-1', 'RULE-2'}

    @pytest.mark.proof("static_checks", "PROOF-24", "RULE-19", tier="integration")
    def test_no_collision_when_ids_unique(self, tmp_path):
        """Distinct PROOF-IDs should produce zero findings."""
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            _python_proof("login", "PROOF-2", "RULE-2"),
            _jest_proof("login", "PROOF-3", "RULE-3"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)
        assert len(findings) == 0, f"Expected no findings, got {findings}"

    @pytest.mark.proof("static_checks", "PROOF-25", "RULE-19", tier="integration")
    def test_collision_with_mixed_languages(self, tmp_path):
        """Collision across language boundaries — Python and TypeScript both claim PROOF-1."""
        proofs = [
            _python_proof("auth", "PROOF-1", "RULE-1"),
            _typescript_proof("auth", "PROOF-1", "RULE-3"),
            _shell_proof("auth", "PROOF-2", "RULE-2"),
        ]
        proof_path = _write_proof_json(tmp_path, "auth", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 1
        assert set(collisions[0]['rules']) == {'RULE-1', 'RULE-3'}

    @pytest.mark.proof("static_checks", "PROOF-26", "RULE-19", tier="integration")
    def test_multiple_collisions_detected(self, tmp_path):
        """Two separate collisions in one file — both detected."""
        proofs = [
            _jest_proof("cart", "PROOF-1", "RULE-1"),
            _jest_proof("cart", "PROOF-1", "RULE-2"),
            _sql_proof("cart", "PROOF-3", "RULE-3"),
            _sql_proof("cart", "PROOF-3", "RULE-4"),
        ]
        proof_path = _write_proof_json(tmp_path, "cart", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 2
        collision_ids = {c['proof_id'] for c in collisions}
        assert collision_ids == {'PROOF-1', 'PROOF-3'}


class TestProofRuleOrphan:
    """Orphan rule detection across all supported language contexts."""

    @pytest.mark.parametrize("lang,factory", list(_LANGUAGE_FACTORIES.items()))
    @pytest.mark.proof("static_checks", "PROOF-27", "RULE-20", tier="integration")
    def test_detects_orphan_per_language(self, tmp_path, lang, factory):
        """Proof targeting RULE-99 which doesn't exist — detected regardless of language."""
        spec_path = _write_spec_file(tmp_path, "login", {
            "RULE-1": "Validates credentials",
            "RULE-2": "Returns JWT on success",
            "RULE-3": "Rejects expired tokens",
        })
        proofs = [
            factory("login", "PROOF-1", "RULE-1"),
            factory("login", "PROOF-99", "RULE-99"),  # orphan
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 1, f"Expected 1 orphan for {lang}, got {len(orphans)}"
        assert orphans[0]['rule'] == 'RULE-99'

    @pytest.mark.proof("static_checks", "PROOF-28", "RULE-20", tier="integration")
    def test_no_orphan_when_all_rules_exist(self, tmp_path):
        """All proofs target existing rules — zero orphans."""
        spec_path = _write_spec_file(tmp_path, "login", {
            "RULE-1": "Validates credentials",
            "RULE-2": "Returns JWT on success",
        })
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            _shell_proof("login", "PROOF-2", "RULE-2"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, f"Expected no orphans, got {orphans}"

    @pytest.mark.proof("static_checks", "PROOF-29", "RULE-20", tier="integration")
    def test_required_anchor_rules_not_flagged(self, tmp_path):
        """Rules with '/' (from required anchors) should NOT be flagged as orphans."""
        spec_path = _write_spec_file(tmp_path, "login", {
            "RULE-1": "Validates credentials",
        })
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            # This targets an anchor rule — should not be flagged
            {
                "feature": "login", "id": "PROOF-10", "rule": "security_policy/RULE-1",
                "test_file": "tests/test_security.py",
                "test_name": "test_no_eval",
                "status": "pass", "tier": "unit",
            },
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, f"Anchor rules should not be flagged as orphans: {orphans}"

    @pytest.mark.proof("static_checks", "PROOF-30", "RULE-20", tier="integration")
    def test_no_orphan_check_without_spec(self, tmp_path):
        """Without spec_path, orphan check is skipped — only collision check runs."""
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            _python_proof("login", "PROOF-99", "RULE-99"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)  # no spec_path
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, "Should not check orphans without spec_path"


class TestFileLocking:
    """The one check this repository keeps for Windows as well as POSIX."""

    @pytest.mark.proof("static_checks", "PROOF-31", "RULE-34", tier="integration")
    def test_lock_is_held_until_it_is_released(self, tmp_path):
        """lock_exclusive creates the file and takes the lock; unlock frees it.

        The non-blocking probe runs in a second process, because a POSIX flock is
        held per open file description and a second lock inside this process
        would succeed whether or not the first one is held.
        """
        lock_path = tmp_path / 'records.lock'
        probe = (
            'import sys\n'
            'sys.path.insert(0, %r)\n'
            'import fcntl\n'
            'f = open(%r, "a+", encoding="utf-8")\n'
            'try:\n'
            '    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
            '    print("free")\n'
            'except OSError:\n'
            '    print("held")\n'
        ) % (os.path.dirname(STATIC_CHECKS_PY), str(lock_path))

        handle = static_checks.lock_exclusive(str(lock_path))
        try:
            assert lock_path.exists(), "lock_exclusive did not create the lock file"
            busy = subprocess.run([sys.executable, '-c', probe],
                                  capture_output=True, text=True)
            assert busy.stdout.strip() == 'held', (
                f"another process took the lock while it was held: {busy.stdout!r}")
        finally:
            static_checks.unlock(handle)

        free = subprocess.run([sys.executable, '-c', probe],
                              capture_output=True, text=True)
        assert free.stdout.strip() == 'free', (
            f"unlock did not release the lock: {free.stdout!r}")
        assert handle.closed, "unlock left the handle open"

    @pytest.mark.proof("static_checks", "PROOF-32", "RULE-35")
    def test_the_windows_branch_is_reachable(self):
        """fcntl is imported under try/except, and both branches set _HAS_FCNTL.

        A machine with no fcntl must still import this module, so the flag is
        assigned in the try and in the except, and every lock helper reads it.
        """
        with open(STATIC_CHECKS_PY, encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in tree.body:
            if isinstance(node, ast.Import):
                assert 'fcntl' not in [a.name for a in node.names], \
                    "fcntl is imported unconditionally at module level"
        in_try = in_except = False
        for node in tree.body:
            if not isinstance(node, ast.Try):
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.Import) and any(
                        a.name == 'fcntl' for a in stmt.names):
                    in_try = any(
                        isinstance(s, ast.Assign) and any(
                            getattr(t, 'id', None) == '_HAS_FCNTL' for t in s.targets)
                        for s in node.body)
            catches_import_error = any(
                isinstance(h.type, ast.Name) and h.type.id == 'ImportError'
                for h in node.handlers)
            for h in node.handlers:
                if any(isinstance(s, ast.Assign) and any(
                        getattr(t, 'id', None) == '_HAS_FCNTL' for t in s.targets)
                        for s in h.body):
                    in_except = catches_import_error
        assert in_try and in_except, \
            "_HAS_FCNTL must be set in both the try and the except ImportError branch"
        assert hasattr(static_checks, '_HAS_FCNTL'), "no _HAS_FCNTL flag"
        source = open(STATIC_CHECKS_PY, encoding='utf-8').read()
        assert 'msvcrt' in source, "the Windows lock branch is gone"

    @pytest.mark.skipif(sys.platform != 'win32',
                        reason='the native lock is msvcrt, which Windows has '
                               'and no other operating system does')
    @pytest.mark.proof("static_checks", "PROOF-33", "RULE-37", tier="integration")
    def test_the_windows_lock_is_held_until_it_is_released(self, tmp_path):
        """The msvcrt branch for real: one byte locked, and a second process
        cannot take it until unlock releases it.

        The probe runs in a second process because a lock is held per open
        file, and a second lock inside this one would succeed either way.
        """
        lock_path = tmp_path / 'records.lock'
        probe = (
            'import msvcrt\n'
            'f = open(%r, "a+", encoding="utf-8")\n'
            'f.write("\\0")\n'
            'f.flush()\n'
            'f.seek(0)\n'
            'try:\n'
            '    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)\n'
            '    print("free")\n'
            'except OSError:\n'
            '    print("held")\n'
        ) % str(lock_path)

        assert not static_checks._HAS_FCNTL, \
            "fcntl exists here, so this is not the Windows lock branch"
        handle = static_checks.lock_exclusive(str(lock_path))
        try:
            busy = subprocess.run([sys.executable, '-c', probe],
                                  capture_output=True, text=True)
            assert busy.stdout.strip() == 'held', (
                f"another process took the lock while it was held: "
                f"{busy.stdout!r}")
        finally:
            static_checks.unlock(handle)

        free = subprocess.run([sys.executable, '-c', probe],
                              capture_output=True, text=True)
        assert free.stdout.strip() == 'free', (
            f"unlock did not release the lock: {free.stdout!r}")
        assert handle.closed, "unlock left the handle open"


class TestCheckJs:
    """check_js JS/TS structural checks, exercised through the real CLI."""

    @staticmethod
    def _run(ts_source, feature):
        path = _write_tmp(ts_source, suffix='.ts')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, feature, '--json'],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"static_checks exited non-zero: {result.stderr}"
            return {p['proof_id']: p for p in json.loads(result.stdout)['proofs']}
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-34", "RULE-9", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-16", tier="integration")
    def test_check_js_assertion_detection(self):
        """tautology and no_assertion are detected in JS/TS bodies; clean tests pass."""
        proofs = self._run('''
import { it, expect } from "vitest";

it("tautological [proof:jsfeat:PROOF-1:RULE-1]", () => {
  expect(true).toBe(true);
});

it("empty body [proof:jsfeat:PROOF-2:RULE-2]", () => {
  const x = 5;
});

it("real assertion [proof:jsfeat:PROOF-3:RULE-3]", () => {
  expect(2 + 2).toBe(4);
});
''', "jsfeat")

        assert proofs["PROOF-1"]["status"] == "fail"
        assert proofs["PROOF-1"]["check"] == "tautology"
        assert proofs["PROOF-2"]["status"] == "fail"
        assert proofs["PROOF-2"]["check"] == "no_assertion"
        assert proofs["PROOF-3"]["status"] == "pass"

        # RULE-27: check_js returns the same JSON shape as check_python —
        # every proof dict carries proof_id, rule_id, test_name, status, reason.
        for pid in ("PROOF-1", "PROOF-2", "PROOF-3"):
            entry = proofs[pid]
            for field in ("proof_id", "rule_id", "test_name", "status", "reason"):
                assert field in entry, f"{pid} missing '{field}' (shape must match check_python): {entry}"
        assert proofs["PROOF-1"]["rule_id"] == "RULE-1"
        assert proofs["PROOF-3"]["test_name"].startswith("real assertion")

    @pytest.mark.proof("static_checks", "PROOF-36", "RULE-10", tier="integration")
    def test_check_js_tokenizer_handles_braces_and_apostrophes(self):
        """Issue #2 repro: nested-brace bodies are not truncated and apostrophe
        titles are not dropped."""
        proofs = self._run('''
import { describe, it, expect } from "vitest";
import { execSync } from "node:child_process";

describe("repro", () => {
  it("execSync options trigger early-truncation [proof:demo:PROOF-1:RULE-1]", () => {
    const out = execSync("ls", { cwd: ".", encoding: "utf8" });
    expect(out).toMatch(/./);
  });

  it("cd's into a sibling [proof:demo:PROOF-2:RULE-2]", () => {
    expect(1).toBe(1);
  });
});
''', "demo")

        # Bug #2: apostrophe in a double-quoted title must not drop the test.
        assert "PROOF-1" in proofs, "the options-object test vanished from the output"
        assert "PROOF-2" in proofs, "the apostrophe-title test vanished from the output"
        # Bug #1: the options-object body must be captured fully, so the expect()
        # after it is seen and the test is NOT falsely flagged no_assertions.
        assert proofs["PROOF-1"]["status"] == "pass", proofs["PROOF-1"]
        assert proofs["PROOF-1"].get("check") != "no_assertion"
        assert proofs["PROOF-2"]["status"] == "pass"


class TestRunsOnWindowsToo:
    """RULE-29/30: static_checks.py imports and runs on Windows as well as POSIX."""

    def _source(self):
        with open(STATIC_CHECKS_PY, encoding='utf-8') as f:
            return f.read()

    @pytest.mark.proof("static_checks", "PROOF-37", "RULE-35")
    def test_no_unconditional_fcntl_import(self):
        """fcntl is imported under try/except ImportError, never unconditionally,
        and _HAS_FCNTL is assigned in both branches."""
        tree = ast.parse(self._source())

        # No top-level `import fcntl` in the module body.
        for node in tree.body:
            if isinstance(node, ast.Import):
                assert 'fcntl' not in [a.name for a in node.names], \
                    "fcntl is imported unconditionally at module level"

        fcntl_in_try = False
        flag_in_try = False
        flag_in_except = False
        for node in tree.body:
            if not isinstance(node, ast.Try):
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.Import) and any(a.name == 'fcntl' for a in stmt.names):
                    fcntl_in_try = True
                if isinstance(stmt, ast.Assign) and any(
                        getattr(t, 'id', None) == '_HAS_FCNTL' for t in stmt.targets):
                    flag_in_try = True
            # The except must catch ImportError and set the flag.
            catches_import_error = any(
                h.type is not None and isinstance(h.type, ast.Name) and h.type.id == 'ImportError'
                for h in node.handlers)
            for h in node.handlers:
                if any(isinstance(s, ast.Assign) and any(
                        getattr(t, 'id', None) == '_HAS_FCNTL' for t in s.targets) for s in h.body):
                    flag_in_except = catches_import_error

        assert fcntl_in_try, "fcntl is not imported inside a try block"
        assert flag_in_try and flag_in_except, \
            "_HAS_FCNTL must be set in both the try and except ImportError branches"
        assert hasattr(static_checks, '_HAS_FCNTL'), "module exposes no _HAS_FCNTL flag"

    @pytest.mark.proof("static_checks", "PROOF-38", "RULE-36")
    def test_all_text_open_calls_specify_utf8(self):
        """Every text open() in static_checks.py passes encoding='utf-8'."""
        tree = ast.parse(self._source())
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'open'):
                continue
            # Any string argument other than the encoding says how to open it.
            flags = [a.value for a in node.args[1:] if isinstance(a, ast.Constant)]
            flags += [kw.value.value for kw in node.keywords
                      if kw.arg != 'encoding' and isinstance(kw.value, ast.Constant)]
            if any(isinstance(f, str) and 'b' in f for f in flags):
                continue  # bytes, which take no encoding
            enc = next((kw.value.value for kw in node.keywords
                        if kw.arg == 'encoding'
                        and isinstance(kw.value, ast.Constant)), None)
            if enc != 'utf-8':
                offenders.append(getattr(node, 'lineno', '?'))
        assert not offenders, \
            f"a text open() without encoding='utf-8' at lines: {offenders}"

class TestCheckCsharp:
    """RULE-31: deterministic Pass-1 checks for C#/.NET (xUnit/NUnit/MSTest) tests."""

    def _cs(self, body, proof_id="PROOF-1", rule_id="RULE-1"):
        return _write_tmp(f'''
using Xunit;
using FluentAssertions;
namespace Demo {{
  public class Tests {{
    [Fact]
    [Trait("PurlinProof", "csfeat:{proof_id}:{rule_id}:unit")]
    public void TheTest() {{ {body} }}
  }}
}}
''', suffix='.cs')

    @pytest.mark.proof("static_checks", "PROOF-39", "RULE-11", tier="integration")
    def test_detects_assert_true(self):
        path = self._cs("Assert.True(true);")
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'tautology'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-40", "RULE-11", tier="integration")
    def test_detects_no_assertions(self):
        path = self._cs("var x = Compute(); var y = x + 1;")
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertion'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-41", "RULE-11", tier="integration")
    def test_recognizes_all_assertion_frameworks(self):
        """xUnit Assert.Equal, NUnit Assert.That, MSTest Assert.IsTrue, and
        FluentAssertions .Should() each count as a real assertion (status=pass)."""
        cases = {
            "xunit": "Assert.Equal(3, 1 + 2);",
            "nunit": "Assert.That(2 + 2, Is.EqualTo(4));",
            "mstest": "Assert.IsTrue(1 < 2);",
            "fluent": 'var s = "hi { nested }"; s.Should().Contain("hi");',
        }
        for name, body in cases.items():
            path = self._cs(body)
            try:
                results = check_csharp(path, "csfeat")
                assert len(results) == 1, f"{name}: expected 1 proof"
                assert results[0]['status'] == 'pass', \
                    f"{name}: assertion not recognized — {results[0]}"
            finally:
                os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-42", "RULE-21", tier="integration")
    def test_dispatch_routes_cs_to_check_csharp(self):
        """analyze_test_file routes a .cs file to check_csharp (not the empty fallback)."""
        path = self._cs("Assert.True(true);", proof_id="PROOF-7", rule_id="RULE-9")
        try:
            results = analyze_test_file(path, "csfeat")
            assert results, ".cs file produced no proofs — dispatch fell through to []"
            assert results[0]['proof_id'] == 'PROOF-7'
            assert results[0]['check'] == 'tautology'
            # A genuinely unknown extension still yields the empty fallback.
            other = _write_tmp("nothing here", suffix='.txt')
            try:
                assert analyze_test_file(other, "csfeat") == []
            finally:
                os.unlink(other)
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-43", "RULE-11", tier="integration")
    def test_recognizes_playwright_fluent_assertions(self):
        """A C# test asserting only via Playwright's Expect(...).To*Async() is recognized
        as an assertion (status=pass), but a bare Expect(x) with no matcher is still flagged."""
        # Mirrors the PR #4 repro: Nav_ShowsUser_AndSignOut asserts only through Playwright.
        playwright = (
            'await Assertions.Expect(page.Locator("text=" + user)).ToBeVisibleAsync();\n'
            'await Assertions.Expect(page.Locator("a[href=\'logout\']")).ToBeVisibleAsync();'
        )
        path = self._cs(playwright)
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'pass', \
                f"Playwright assertion not recognized — {results[0]}"
        finally:
            os.unlink(path)

        # Bare Expect(x) with no To*Async() matcher chain is NOT an assertion.
        bare = self._cs("Expect(result);")
        try:
            results = check_csharp(bare, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertion', \
                f"bare Expect(x) should be no_assertions — {results[0]}"
        finally:
            os.unlink(bare)

    @pytest.mark.proof("static_checks", "PROOF-44", "RULE-12", tier="integration")
    def test_resolve_test_file_from_name(self):
        """When a proof's test_file is empty (C#/xUnit under dotnet test), the
        source file is resolved from the fully-qualified test_name by locating the
        declaring class — preferring the authored file over a bin/ build copy."""
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'tests'))
            os.makedirs(os.path.join(root, 'bin'))
            authored = os.path.join(root, 'tests', 'AuthLogicTests.cs')
            with open(authored, 'w', encoding='utf-8') as f:
                f.write('namespace Demo.Tests {\n  public class AuthLogicTests {\n'
                        '    [Fact] public void Evaluate_NullRow() { }\n  }\n}\n')
            # A build-output copy that must be skipped.
            with open(os.path.join(root, 'bin', 'AuthLogicTests.cs'), 'w', encoding='utf-8') as f:
                f.write('public class AuthLogicTests { }\n')

            got = resolve_test_file_from_name(
                'Demo.Tests.AuthLogicTests.Evaluate_NullRow', root)
            assert got == 'tests/AuthLogicTests.cs', f"resolved to {got!r}"

            # A test_name whose class is not declared anywhere resolves to ''.
            assert resolve_test_file_from_name('Demo.Tests.MissingClass.X', root) == ''

            # A file the walk must skip cannot win by sorting first.
            assert resolve_test_file_from_name(
                'Demo.Tests.AuthLogicTests.Evaluate_NullRow', root,
                ext='.java') == '', "the extension filter let a .cs file through"

class TestCheckSql:
    """RULE-46: deterministic Pass-1 checks for SQL (sqlite3) proof blocks."""

    def _sql(self, block, proof_id="PROOF-1", rule_id="RULE-1"):
        return _write_tmp(f'-- @purlin sqlfeat {proof_id} {rule_id} unit\n'
                          f'-- Test: the thing\n{block}\n', suffix='.sql')

    @pytest.mark.proof("static_checks", "PROOF-45", "RULE-13", tier="integration")
    def test_detects_unconditional_pass(self):
        """A PASS that nothing decides is assert_true, bare or inside a CASE."""
        cases = {
            'bare': "DELETE FROM parents WHERE id = 1;\nSELECT 'PASS';",
            'constant case': "SELECT CASE WHEN 1 = 1 THEN 'PASS' ELSE 'FAIL' END;",
            'fixture case': "SELECT CASE WHEN 'alice' = 'alice' THEN 'PASS' ELSE 'FAIL' END;",
        }
        for name, block in cases.items():
            path = self._sql(block)
            try:
                results = check_sql(path, "sqlfeat")
                assert len(results) == 1, f"{name}: expected 1 proof, got {results}"
                assert results[0]['status'] == 'fail', f"{name}: not flagged — {results[0]}"
                assert results[0]['check'] == 'tautology', f"{name}: {results[0]}"
                assert results[0]['test_name'] == 'the thing', results[0]
            finally:
                os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-46", "RULE-14", tier="integration")
    def test_detects_block_with_no_select(self):
        """A block that never SELECTs observes nothing, and the proof id stands in
        for a missing `-- Test:` name exactly as the shipped plugin does."""
        path = _write_tmp("-- @purlin sqlfeat PROOF-3 RULE-3 unit\n"
                          "INSERT INTO users (email) VALUES ('a@b.c');\n", suffix='.sql')
        try:
            results = check_sql(path, "sqlfeat")
            assert len(results) == 1, results
            assert results[0]['status'] == 'fail', results[0]
            assert results[0]['check'] == 'no_assertion', results[0]
            assert results[0]['test_name'] == 'PROOF-3', results[0]
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-47", "RULE-13", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-48", "RULE-15", tier="integration")
    def test_predicates_that_read_the_database_pass(self):
        """A predicate naming a column, a function or a subquery decides something;
        a block ends at the next marker rather than running on into it; and a
        trailing `--` comment is not read as SQL the block runs."""
        path = _write_tmp("""-- @purlin sqlfeat PROOF-1 RULE-1 unit
-- Test: subquery
SELECT CASE WHEN (SELECT count(*) FROM users) = 1 THEN 'PASS' ELSE 'FAIL' END;

-- @purlin sqlfeat PROOF-2 RULE-2 unit
-- Test: function
SELECT CASE WHEN changes() = 1 THEN 'PASS' ELSE 'FAIL' END;

-- @purlin sqlfeat PROOF-3 RULE-3 unit
-- Test: column
SELECT CASE WHEN email IS NOT NULL THEN 'PASS' ELSE 'FAIL' END FROM users; -- not SELECT 'PASS'

-- @purlin otherfeat PROOF-9 RULE-9 unit
-- Test: not this feature
SELECT 'PASS';
""", suffix='.sql')
        try:
            results = check_sql(path, "sqlfeat")
            assert [r['proof_id'] for r in results] == ['PROOF-1', 'PROOF-2', 'PROOF-3'], \
                f"another feature's block leaked in — {results}"
            for r in results:
                assert r['status'] == 'pass', f"a real predicate was flagged — {r}"
        finally:
            os.unlink(path)

class TestDispatchAllExtensions:
    """RULE-44: one extension table, and no fallback for anything outside it."""

    _FIXTURES = {
        '.mjs': 'it("t [proof:dfeat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });',
        '.cjs': 'it("t [proof:dfeat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });',
        '.sql': "-- @purlin dfeat PROOF-1 RULE-1 unit\nSELECT 'PASS';\n",
        '.cs': ('using Xunit;\nnamespace D {\n  public class T {\n    [Fact]\n'
                '    [Trait("PurlinProof", "dfeat:PROOF-1:RULE-1:unit")]\n'
                '    public void A() { Assert.True(true); }\n  }\n}\n'),
    }

    @pytest.mark.proof("static_checks", "PROOF-49", "RULE-21", tier="integration")
    def test_every_shipped_extension_dispatches_and_nothing_else_does(self):
        """Each extension a shipped plugin emits reaches a checker that flags the
        always-true fixture; an extension no checker reads yields [] and no
        extracted body, rather than being handed to whichever checker an if-chain
        ended on."""
        for ext, content in self._FIXTURES.items():
            path = _write_tmp(content, suffix=ext)
            try:
                results = analyze_test_file(path, 'dfeat')
                assert len(results) == 1, f"{ext}: dispatch produced {results}"
                assert results[0]['check'] == 'tautology', f"{ext}: {results[0]}"
            finally:
                os.unlink(path)

        # An unknown extension: no checker, and no extractor either. The `.rb` file
        # carries a Jest-shaped marker, which the old silent fallback would read.
        ruby = _write_tmp(
            'it("t [proof:dfeat:PROOF-1:RULE-1]", () => { expect(1).toBe(1); });',
            suffix='.rb')
        try:
            assert analyze_test_file(ruby, 'dfeat') == [], \
                ".rb reached a checker — the dispatch has a fallback"
            assert static_checks._test_bodies(ruby, '.rb', 'dfeat') is None, \
                ".rb produced a body — _test_bodies still falls back to the JS extractor"
        finally:
            os.unlink(ruby)

        # One table: the extractor set is derived from it rather than listed again,
        # and shell is the single checked language deliberately left out of it.
        assert static_checks._CHECKER_EXTENSIONS == frozenset(
            {'.py', '.sh', '.cs', '.sql'} | static_checks._JS_EXTENSIONS)
        assert static_checks._TEST_CODE_EXTENSIONS == \
            static_checks._CHECKER_EXTENSIONS - {'.sh'}
        assert {'.mjs', '.cjs'} <= static_checks._JS_EXTENSIONS

def _tree_snapshot(root):
    """{relative path: sha256} for every file under `root`.

    A sweep that opened anything for writing — a cache, a lock, a runtime file,
    a rewritten proof JSON — changes this mapping, which is the whole assertion.
    """
    snapshot = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, '/')
            with open(path, 'rb') as f:
                snapshot[rel] = hashlib.sha256(f.read()).hexdigest()
    return snapshot


class TestDeterministicSweep:
    """RULE-49 and RULE-50 — the free checks over a whole project."""

    _MJS = 'it("t [proof:jsfeat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });\n'
    _CS = """using Xunit;
namespace Demo {
  public class CsharpTests {
    [Fact]
    [Trait("PurlinProof", "csfeat:PROOF-1:RULE-1:unit")]
    public void AlwaysTrue() { Assert.True(true); }
  }
}
"""
    _SQL = "-- @purlin sqlfeat PROOF-1 RULE-1 unit\n-- Test: always\nSELECT 'PASS';\n"
    _RB = 'it("t [proof:rbfeat:PROOF-1:RULE-1]", () => { expect(1).toBe(1); });\n'

    # Every Python test file the project below actually has on disk. The sweep
    # must parse each exactly once inside its one run scope, however many
    # features or proofs point at it.
    _PY_FILES = ('tests/test_shared.py', 'tests/test_marker.py',
                 'tests/test_multi_ok.py', 'tests/test_multi_bad.py',
                 'tests/test_mixed_ok.py', 'tests/test_worst_bad.py')

    def _write(self, root, rel, source):
        path = os.path.join(root, *rel.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(source)
        return path

    def _project(self, root):
        """A project holding one test file per checked language plus every way a
        backing can go unmeasurable, and two features sharing one Python file."""
        # alpha and beta share tests/test_shared.py.
        _scaffold_proof(root, 'alpha', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_shared.py',
                        test_name='test_alpha_always', test_body='    assert True')
        _scaffold_proof(root, 'alpha', 'PROOF-2', 'RULE-2',
                        test_file='tests/test_shared.py',
                        test_name='test_alpha_ok', test_body='    assert 1 + 1 == 2')
        _scaffold_proof(root, 'beta', 'PROOF-3', 'RULE-3',
                        test_file='tests/test_shared.py',
                        test_name='test_beta_ok', test_body='    assert 2 + 2 == 4')

        # A stamped manual proof: declared, and backed by nothing.
        with open(os.path.join(root, 'specs', 'app', 'alpha.md'),
                  'a', encoding='utf-8') as f:
            f.write('- PROOF-9 (RULE-1): Open the dashboard in Chrome and verify the '
                    'header reads "Purlin" @manual(dev@example.com, 2026-03-31, a1b2c3d)\n')

        # Shell: the helper writes a bare `purlin_proof ... pass`, which is the
        # hardcoded-pass defect.
        _scaffold_proof(root, 'shfeat', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_sh.sh', test_name='test_sh')

        for feature, rel, source, test_name in (
                ('jsfeat', 'tests/test_mod.mjs', self._MJS, 't'),
                ('sqlfeat', 'tests/test_sql.sql', self._SQL, 'always'),
                ('rbfeat', 'tests/test_rb.rb', self._RB, 't')):
            _scaffold_proof(root, feature, 'PROOF-1', 'RULE-1', test_file=rel,
                            test_name=test_name, write_test=False)
            self._write(root, rel, source)

        # C#: the xUnit logger records an empty test_file when no source info is
        # available, so the path has to come back from the fully-qualified name.
        _scaffold_proof(root, 'csfeat', 'PROOF-1', 'RULE-1',
                        test_file='tests/CsharpTests.cs',
                        test_name='Demo.CsharpTests.AlwaysTrue', write_test=False)
        self._write(root, 'tests/CsharpTests.cs', self._CS)
        record = os.path.join(root, '.purlin', 'runtime', 'proofs', 'csfeat.unit.json')
        with open(record, encoding='utf-8') as f:
            data = json.load(f)
        data['proofs'][0]['test_file'] = ''
        with open(record, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # A record naming a file nobody wrote.
        _scaffold_proof(root, 'gonefeat', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_gone.py', test_name='test_gone',
                        write_test=False)

        # A file the checker reads but that carries no marker for PROOF-2.
        _scaffold_proof(root, 'markerfeat', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_marker.py', test_name='test_marker',
                        test_body='    assert 7 % 2 == 1')
        _scaffold_proof(root, 'markerfeat', 'PROOF-2', 'RULE-2',
                        test_file='tests/test_marker.py', test_name='test_absent',
                        write_test=False)

        # Two backings, one clean and one always true: fail wins.
        _scaffold_proof(root, 'multi', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_multi_ok.py', test_name='test_ok',
                        test_body='    assert 3 + 3 == 6', tier='unit')
        _scaffold_proof(root, 'multi', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_multi_bad.py', test_name='test_bad',
                        test_body='    assert True', tier='integration')

        # Two backings, one clean and one in a language no checker reads:
        # unmeasurable wins over pass.
        _scaffold_proof(root, 'mixed', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_mixed_ok.py', test_name='test_ok',
                        test_body='    assert 5 * 2 == 10', tier='unit')
        _scaffold_proof(root, 'mixed', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_mixed.rb', test_name='t',
                        write_test=False, tier='integration')
        self._write(root, 'tests/test_mixed.rb', self._RB)

        # Two backings, one failing and one in a language no checker reads: the
        # failure wins, because a defect outranks a measurement gap. The `.rb`
        # file sorts first, so the ranking has to override a verdict already in
        # hand rather than merely keep the first one it met.
        _scaffold_proof(root, 'worst', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_worst_bad.py', test_name='test_bad',
                        test_body='    assert True', tier='unit')
        _scaffold_proof(root, 'worst', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_worst.rb', test_name='t',
                        write_test=False, tier='integration')
        self._write(root, 'tests/test_worst.rb', self._RB)

    _EXPECTED = {
        ('alpha', 'PROOF-1'): ('fail', 'assert_true_literal'),
        ('alpha', 'PROOF-2'): ('pass', 'none'),
        ('beta', 'PROOF-3'): ('pass', 'none'),
        ('csfeat', 'PROOF-1'): ('fail', 'tautology'),
        ('gonefeat', 'PROOF-1'): ('unmeasurable', 'missing_file'),
        ('jsfeat', 'PROOF-1'): ('fail', 'tautology'),
        ('markerfeat', 'PROOF-1'): ('pass', 'none'),
        ('markerfeat', 'PROOF-2'): ('unmeasurable', 'marker_not_found'),
        ('mixed', 'PROOF-1'): ('unmeasurable', 'no_checker'),
        ('multi', 'PROOF-1'): ('fail', 'assert_true_literal'),
        ('rbfeat', 'PROOF-1'): ('unmeasurable', 'no_checker'),
        ('shfeat', 'PROOF-1'): ('fail', 'tautology'),
        ('sqlfeat', 'PROOF-1'): ('fail', 'tautology'),
        ('worst', 'PROOF-1'): ('fail', 'assert_true_literal'),
    }

    @pytest.mark.proof("static_checks", "PROOF-50", "RULE-23", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-51", "RULE-24", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-52", "RULE-25", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-53", "RULE-26", tier="integration")
    def test_sweep_grades_every_backing_and_writes_nothing(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._project(tmpdir)
            before = _tree_snapshot(tmpdir)

            parses = []
            real_parse = static_checks.ast.parse
            monkeypatch.setattr(
                static_checks.ast, 'parse',
                lambda *a, **k: (parses.append(1), real_parse(*a, **k))[1])
            result = deterministic_sweep(tmpdir)

            assert result['project_root'] == tmpdir
            specs = glob.glob(os.path.join(tmpdir, 'specs', '**', '*.md'),
                              recursive=True)
            assert result['counts']['features'] == len(specs) == 12, result['counts']

            got = {(feat, pid): (entry['status'], entry['check'])
                   for feat, data in result['features'].items()
                   for pid, entry in data['proofs'].items()}
            assert got == self._EXPECTED

            # A .rb backing is a measurement gap, never a defect.
            assert ('rbfeat', 'PROOF-1') not in {(r['feature'], r['proof_id'])
                                                 for r in result['failing']}

            # An empty test_file resolved from the fully-qualified test name.
            csharp = result['features']['csfeat']['proofs']['PROOF-1']
            assert csharp['test_file'] == 'tests/CsharpTests.cs', csharp
            assert csharp['test_name'] == 'AlwaysTrue', csharp

            # Precedence across several backings.
            multi = result['features']['multi']['proofs']['PROOF-1']
            assert (multi['backings'], multi['test_file']) == (2, 'tests/test_multi_bad.py')
            mixed = result['features']['mixed']['proofs']['PROOF-1']
            assert (mixed['backings'], mixed['test_file']) == (2, 'tests/test_mixed.rb')
            worst = result['features']['worst']['proofs']['PROOF-1']
            assert (worst['backings'], worst['test_file']) == (2, 'tests/test_worst_bad.py'), \
                "an unmeasurable backing outranked a failing one"

            # A manual stamp has no test backing, so it is neither failing nor
            # unmeasurable: it is simply not a proof a machine checked.
            assert 'PROOF-9' not in result['features']['alpha']['proofs']
            assert ('alpha', 'PROOF-9') not in {
                (r['feature'], r['proof_id'])
                for r in result['unmeasurable'] + result['failing']}

            for name in ('failing', 'unmeasurable'):
                rows = result[name]
                assert rows == sorted(
                    rows, key=lambda r: (r['feature'], r['proof_id'],
                                         r.get('test_file', ''))), \
                    f"{name} is not sorted by (feature, proof_id, test_file)"
            assert result['counts']['failing'] == len(result['failing']) == 7
            assert result['counts']['unmeasurable'] == len(result['unmeasurable']) == 4
            assert result['counts']['backings'] == 17, result['counts']

            assert len(parses) == len(self._PY_FILES), (
                f"{len(self._PY_FILES)} Python test files must mean "
                f"{len(self._PY_FILES)} parses, not {len(parses)}")

            assert _tree_snapshot(tmpdir) == before, \
                "the sweep wrote to the project it was only supposed to read"

    @staticmethod
    def _repo_state(root):
        """(git porcelain status, every file under .purlin with its size).

        `.purlin/runtime/` is gitignored, so a sweep that wrote a runtime file
        would leave `git status` clean and has to be caught by the listing.
        """
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=root,
                                capture_output=True, text=True).stdout
        runtime = sorted(
            (os.path.relpath(os.path.join(d, n), root).replace(os.sep, '/'),
             os.path.getsize(os.path.join(d, n)))
            for d, _sub, files in os.walk(os.path.join(root, '.purlin'))
            for n in files)
        return status, runtime

    @pytest.mark.proof("static_checks", "PROOF-54", "RULE-27", tier="integration")
    def test_cli_sweeps_this_repository_without_touching_it(self):
        """The real CLI over this repository: every spec swept, every backing in
        a language a shipped checker reads, and the checkout byte-identical
        afterwards."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        before_status, before_runtime = self._repo_state(root)

        proc = subprocess.run(
            [sys.executable, _STATIC_CHECKS_PY, '--sweep', '--json',
             '--project-root', root],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout)

        specs = glob.glob(os.path.join(root, 'specs', '**', '*.md'), recursive=True)
        assert result['counts']['features'] == len(specs) > 0, \
            f"{len(specs)} specs on disk, {result['counts']['features']} swept"
        assert set(result['features']) == {
            os.path.splitext(os.path.basename(p))[0] for p in specs}

        no_checker = [(r['feature'], r['proof_id'], r['test_file'])
                      for r in result['unmeasurable'] if r['check'] == 'no_checker']
        assert no_checker == [], (
            "every language this repository's proofs are written in has a checker, "
            f"so no backing may be unmeasurable for want of one: {no_checker}")

        after_status, after_runtime = self._repo_state(root)
        assert after_status == before_status, \
            "the sweep changed a tracked file in the checkout it was only reading"
        assert after_runtime == before_runtime, \
            "the sweep wrote under .purlin/"

        bare = subprocess.run([sys.executable, _STATIC_CHECKS_PY],
                              capture_output=True, text=True)
        assert bare.returncode == 2
        assert '--sweep [--project-root <path>] [--json]' in bare.stderr, \
            "the sweep is missing from the usage text"


class TestCliSelfDocumentation:
    """RULE-34 — the help text cannot drift from the dispatch chain.

    The usage text once went stale and omitted five real flags, and the module
    docstring claimed "exit 1 = at least one failed" while main() always exits 0
    for a completed analysis, contradicting RULE-7.
    """

    @pytest.mark.proof("static_checks", "PROOF-55", "RULE-32")
    def test_usage_matches_dispatch_chain(self):
        src = open(_STATIC_CHECKS_PY, encoding='utf-8').read()
        tree = ast.parse(src)

        main_fn = next(
            (n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name == 'main'), None)
        assert main_fn is not None, "static_checks.py has no main()"

        # Every string literal tested against sys.argv is a dispatch flag.
        dispatched = set()
        for node in ast.walk(main_fn):
            if isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.In):
                left, right = node.left, node.comparators[0]
                is_argv = (
                    isinstance(right, ast.Attribute) and right.attr == 'argv'
                ) or (
                    isinstance(right, ast.Name) and right.id == 'argv'
                )
                if is_argv and isinstance(left, ast.Constant) \
                        and isinstance(left.value, str) and left.value.startswith('--'):
                    dispatched.add(left.value)
        assert dispatched, "found no --flag dispatches in main(); detector is broken"

        usage_text = ' '.join(static_checks._USAGE)
        undocumented = sorted(f for f in dispatched if f not in usage_text)
        assert not undocumented, \
            f"main() dispatches on flags absent from _USAGE: {undocumented}"

        # And _USAGE must not advertise a flag that does not exist.
        advertised = set(re.findall(r'--[a-z][a-z-]+', usage_text))
        # Sub-options are documented on the line of the form they belong to.
        sub_options = {'--project-root'}
        phantom = sorted(f for f in advertised - sub_options if f not in dispatched)
        assert not phantom, f"_USAGE advertises flags main() never dispatches on: {phantom}"

        # RULE-7: the docstring must not promise a non-zero exit for a found defect.
        docstring = ast.get_docstring(tree) or ''
        assert 'Exit code 0 = all proofs passed, 1 = at least one failed' not in docstring, \
            "module docstring still contradicts RULE-7's exit convention"
        assert 'RULE-7' in docstring, \
            "module docstring should cite the exit convention it follows"

    @pytest.mark.proof("static_checks", "PROOF-56", "RULE-33", tier="integration")
    def test_bad_invocation_prints_every_usage_line(self):
        r = subprocess.run([sys.executable, _STATIC_CHECKS_PY],
                           capture_output=True, text=True)
        assert r.returncode == 2, f"expected exit 2 for a bad invocation, got {r.returncode}"
        for line in static_checks._USAGE:
            assert line in r.stderr, f"usage line not printed: {line!r}"

    @pytest.mark.proof("static_checks", "PROOF-57", "RULE-33", tier="integration")
    def test_help_prints_the_usage_and_the_exit_codes(self):
        """--help exits 0 and documents both exit codes, which RULE-7 fixes."""
        r = subprocess.run([sys.executable, _STATIC_CHECKS_PY, '--help'],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        for line in static_checks._USAGE:
            assert line in r.stdout, f"usage line not printed: {line!r}"
        assert 'Exit codes:' in r.stdout, r.stdout
        assert '0 for a completed analysis' in r.stdout, r.stdout
        assert '2 for a real error' in r.stdout, r.stdout

class TestRunScope:
    """RULE-42: inside one run scope every file is read or parsed once."""

    @pytest.mark.proof("static_checks", "PROOF-58", "RULE-28", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-59", "RULE-29", tier="integration")
    @pytest.mark.proof("static_checks", "PROOF-60", "RULE-31", tier="integration")
    def test_one_parse_per_file_and_identical_results(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            pairs = []
            for feature in ('alpha', 'beta'):
                for n in (1, 2, 3):
                    _scaffold_proof(
                        tmpdir, feature, f'PROOF-{n}', f'RULE-{n}',
                        test_file=f'tests/test_{feature}.py',
                        test_name=f'test_{feature}_{n}',
                        test_body=f'    value = {n} + 0\n    assert value == {n}')
                    pairs.append((feature, f'PROOF-{n}', f'tests/test_{feature}.py'))
            _scaffold_proof(tmpdir, 'gamma', 'PROOF-1', 'RULE-1',
                            test_file='tests/test_gamma.sh', test_name='test_gamma')
            pairs.append(('gamma', 'PROOF-1', 'tests/test_gamma.sh'))

            def _bodies():
                return {(f, p): static_checks._extract_test_code(tmpdir, f, p, t)
                        for f, p, t in pairs}

            outside = _bodies()
            assert len(outside) == 7
            assert outside[('alpha', 'PROOF-1')] is not None, \
                "the Python body did not come back"
            assert outside[('gamma', 'PROOF-1')] is None, \
                "shell has no extractor, so it has no body"

            parses, segments = [], []
            real_parse = static_checks.ast.parse
            monkeypatch.setattr(static_checks.ast, 'parse',
                                lambda *a, **k: (parses.append(1), real_parse(*a, **k))[1])
            monkeypatch.setattr(static_checks.ast, 'get_source_segment',
                                lambda *a, **k: (segments.append(1), None)[1])
            with static_checks.run_scope():
                inside = _bodies()
                again = _bodies()
            assert len(parses) == 2, (
                f"two Python test files must mean two parses, not {len(parses)}")
            assert segments == [], \
                "function source must come from the one line split, never get_source_segment"
            assert inside == outside, "a scoped body differs from the unscoped one"
            assert again == outside

            # Outside a scope nothing is memoized: an edit is seen at once.
            test_path = os.path.join(tmpdir, 'tests', 'test_alpha.py')
            with open(test_path, encoding='utf-8') as f:
                source = f.read()
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(source.replace('value == 1', 'value == 10'))
            assert static_checks._extract_test_code(
                tmpdir, 'alpha', 'PROOF-1', 'tests/test_alpha.py') \
                != outside[('alpha', 'PROOF-1')], \
                "the scope leaked past its block: an edited test kept its old body"
            assert static_checks._RUN_CACHE is None

    @pytest.mark.proof("static_checks", "PROOF-61", "RULE-28", tier="integration")
    def test_the_checks_and_the_extractor_share_the_one_parse(self, monkeypatch):
        """The checks and the body extractor go through the same memo, so a file
        carrying two features is parsed once inside a scope however many of them
        ask for it, and no check reaches for ast.get_source_segment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feature, pid, rid in (('alpha', 'PROOF-1', 'RULE-1'),
                                      ('beta', 'PROOF-2', 'RULE-2')):
                _scaffold_proof(tmpdir, feature, pid, rid,
                                test_file='tests/test_both.py',
                                test_name=f'test_{feature}',
                                test_body='    value = 1 + 1\n    assert value == 2')
            path = os.path.join(tmpdir, 'tests', 'test_both.py')
            unscoped = analyze_test_file(path, 'alpha')

            parses, segments = [], []
            real_parse = static_checks.ast.parse
            monkeypatch.setattr(static_checks.ast, 'parse',
                                lambda *a, **k: (parses.append(1), real_parse(*a, **k))[1])
            monkeypatch.setattr(static_checks.ast, 'get_source_segment',
                                lambda *a, **k: (segments.append(1), None)[1])
            with static_checks.run_scope():
                scoped = analyze_test_file(path, 'alpha')
                other = analyze_test_file(path, 'beta')
                body = static_checks._extract_test_code(
                    tmpdir, 'alpha', 'PROOF-1', 'tests/test_both.py')
            assert len(parses) == 1, (
                "one file carrying two features and one extracted body must mean "
                f"one ast.parse, not {len(parses)}")
            assert segments == [], \
                "a check reached for get_source_segment instead of the one line split"
            assert scoped == unscoped, "a scoped result differs from the unscoped one"
            assert [r['proof_id'] for r in other] == ['PROOF-2'], other
            assert body and 'def test_alpha' in body, body

            # The mock-target check reads the decorator from that same split.
            mocked = _write_tmp('''import pytest
from unittest.mock import patch

@patch("auth.bcrypt.checkpw")
@pytest.mark.proof("alpha", "PROOF-3", "RULE-3")
def test_hashes(mock_checkpw):
    mock_checkpw.return_value = True
    assert login("a", "b") == 200
''')
            try:
                with static_checks.run_scope():
                    results = check_python(mocked, 'alpha',
                                           {'RULE-3': 'Passwords are hashed with bcrypt'})
                assert results[0]['check'] == 'mock_of_target', results
                assert segments == [], \
                    "mock_of_target still calls get_source_segment"
            finally:
                os.unlink(mocked)

    @pytest.mark.proof("static_checks", "PROOF-62", "RULE-30")
    def test_segment_matches_the_stdlib_byte_for_byte(self):
        source = (
            "import pytest\r\n"
            "\x0c\n"
            "@pytest.mark.proof(\n"
            "    'feat', 'PROOF-1',\n"
            "    'RULE-1')\r"
            "def test_a():\n"
            "    value = 'é'  # \x0c form feed and 'ü' on a def line\r\n"
            "    assert value == 'é'\n"
            "@pytest.mark.proof('feat', 'PROOF-2', 'RULE-2')\n"
            "def test_b(): assert 'ü' == 'ü'\n"
            "def helper(): return 'ñ'"
        )
        tree = ast.parse(source)
        lines = static_checks._split_source_lines(source)
        assert lines == ast._splitlines_no_ff(source), \
            "the line split must match the stdlib's, or every offset is off"
        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for target in [node] + list(node.decorator_list):
                expected = ast.get_source_segment(source, target)
                assert static_checks._segment(lines, target) == expected, \
                    f"segment for {type(target).__name__} at line {target.lineno} differs"
                checked += 1
        assert checked == 5
        entries, _ = static_checks._python_proof_functions(source)
        assert [(f, p) for f, p, *_ in entries] == [('feat', 'PROOF-1'), ('feat', 'PROOF-2')]


class TestSingleReadPerFile:
    """RULE-51 - one open per file inside one run scope."""

    _SH = (
        '#!/usr/bin/env bash\n'
        'if [ "$(echo hi)" = "hi" ]; then\n'
        '  purlin_proof "shfeat" "PROOF-1" "RULE-1" pass\n'
        'else\n'
        '  purlin_proof "shfeat" "PROOF-1" "RULE-1" fail\n'
        'fi\n'
    )

    @staticmethod
    def _project(root):
        """Four specs: three features share one Python test file, one is shell."""
        _scaffold_proof(root, 'alpha', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_shared.py',
                        test_name='test_alpha', test_body='    assert 1 + 1 == 2')
        _scaffold_proof(root, 'beta', 'PROOF-2', 'RULE-2',
                        test_file='tests/test_shared.py',
                        test_name='test_beta', test_body='    assert True')
        _scaffold_proof(root, 'gamma', 'PROOF-3', 'RULE-3',
                        test_file='tests/test_shared.py',
                        test_name='test_gamma', test_body='    assert 2 + 2 == 4')
        _scaffold_proof(root, 'shfeat', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_sh.sh', test_name='test_sh',
                        write_test=False)
        path = os.path.join(root, 'tests', 'test_sh.sh')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(TestSingleReadPerFile._SH)

    @staticmethod
    def _verdicts(result):
        return {(feat, pid): (entry['status'], entry['check'])
                for feat, data in result['features'].items()
                for pid, entry in data['proofs'].items()}

    @pytest.mark.proof("static_checks", "PROOF-63", "RULE-28", tier="integration")
    def test_sweep_opens_every_spec_and_test_file_exactly_once(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._project(tmpdir)
            plain = deterministic_sweep(tmpdir)

            opens = {}
            real_open = builtins.open

            def spy(file, *args, **kwargs):
                try:
                    key = os.path.abspath(os.fspath(file))
                except TypeError:          # an fd, not a path
                    key = repr(file)
                opens[key] = opens.get(key, 0) + 1
                return real_open(file, *args, **kwargs)

            monkeypatch.setattr(builtins, 'open', spy)
            spied = deterministic_sweep(tmpdir)
            monkeypatch.setattr(builtins, 'open', real_open)

            for feature in ('alpha', 'beta', 'gamma', 'shfeat'):
                spec = os.path.abspath(
                    os.path.join(tmpdir, 'specs', 'app', f'{feature}.md'))
                assert opens.get(spec) == 1, \
                    f"{feature}.md was opened {opens.get(spec)} times, not once"
            for rel in ('tests/test_shared.py', 'tests/test_sh.sh'):
                test_path = os.path.abspath(os.path.join(tmpdir, *rel.split('/')))
                assert opens.get(test_path) == 1, \
                    f"{rel} was opened {opens.get(test_path)} times, not once"
            repeated = {k: v for k, v in opens.items() if v > 1}
            assert repeated == {}, f"paths opened more than once: {repeated}"

            assert spied['counts'] == plain['counts']
            assert self._verdicts(spied) == self._verdicts(plain)
            assert self._verdicts(plain) == {
                ('alpha', 'PROOF-1'): ('pass', 'none'),
                ('beta', 'PROOF-2'): ('fail', 'assert_true_literal'),
                ('gamma', 'PROOF-3'): ('pass', 'none'),
                ('shfeat', 'PROOF-1'): ('pass', 'none'),
            }


class TestOneBodyCheckDriver:
    """RULE-52 - the three brace-body checkers are wrappers over one driver."""

    _WRAPPERS = ('check_js', 'check_csharp', 'check_sql')

    # (wrapper, filename, source, expected reason). Every reason is the string
    # that language's own proofs assert, quoted here so a paraphrase in the
    # driver fails this test as well as theirs.
    _FIXTURES = (
        ('check_js', 'always.mjs',
         'it("t [proof:feat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });\n',
         'expect(true).toBe(true) is tautological'),
        ('check_csharp', 'Always.cs',
         'using Xunit;\n'
         'namespace Demo {\n'
         '  public class AlwaysTests {\n'
         '    [Fact]\n'
         '    [Trait("PurlinProof", "feat:PROOF-1:RULE-1:unit")]\n'
         '    public void Always() { Assert.True(true); }\n'
         '  }\n'
         '}\n',
         'Assert.True(true) is tautological'),
        ('check_sql', 'always.sql',
         "-- @purlin feat PROOF-1 RULE-1 unit\n-- Test: always\nSELECT 'PASS';\n",
         "an unconditional SELECT 'PASS' passes whatever the data holds"),
    )

    @pytest.mark.proof("static_checks", "PROOF-64", "RULE-22", tier="integration")
    def test_every_wrapper_delegates_and_keeps_its_reason_string(self):
        path = STATIC_CHECKS_PY
        with open(path, encoding='utf-8') as f:
            tree = ast.parse(f.read())
        functions = [n for n in tree.body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        by_name = {n.name: n for n in functions}

        assert [n.name for n in functions].count('_run_body_checks') == 1, \
            "the driver must be defined exactly once"

        for name in self._WRAPPERS:
            node = by_name[name]
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]          # the docstring is not an inlined check
            assert len(body) == 1 and isinstance(body[0], ast.Return), \
                f"{name} has {len(body)} statements, so its body is inlined again"
            call = body[0].value
            assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) \
                and call.func.id == '_run_body_checks', \
                f"{name} returns something other than a _run_body_checks(...) call"

        langs = {n.args[-1].value for n in
                 [by_name[w].body[-1].value for w in self._WRAPPERS]}
        assert set(static_checks._BODY_CHECKS) == langs == {'js', 'csharp', 'sql'}, \
            "the table and the wrappers name different languages"

        with tempfile.TemporaryDirectory() as tmpdir:
            for wrapper, filename, source, reason in self._FIXTURES:
                path = os.path.join(tmpdir, filename)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(source)
                results = getattr(static_checks, wrapper)(path, 'feat')
                assert len(results) == 1, f"{wrapper} returned {results}"
                got = results[0]
                assert (got['proof_id'], got['rule_id']) == ('PROOF-1', 'RULE-1')
                assert got['status'] == 'fail', got
                assert got['check'] == 'tautology', got
                assert got['reason'] == reason, (
                    f"{wrapper} reason moved: {got['reason']!r} != {reason!r}")

# ===========================================================================
# Cheat matrix (lifted from dev/test_cheat_matrix.py in phase 0)
# ===========================================================================
#
# Five cheat patterns across the languages Purlin keeps: SQL, TypeScript and
# Python. Every test compiles or interprets real code in the target language,
# runs it through the proof plugin, and verifies the proof JSON. Each test
# documents whether the cheat is caught by Pass 1 (deterministic) or requires
# Pass 2 (LLM).
#
# Cheat patterns:
#   1. Tautological - assertion always true regardless of code behavior
#   2. Fixture-only - asserts test setup data, never calls code under test
#   3. Happy-path-only - rule says "rejects X" but test only sends valid input
#   4. Name/value drift - test name claims one thing, assertion checks the opposite
#   5. No real assertion - lots of setup but no actual check on the result

PROOF_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof')


# ---------------------------------------------------------------------------
# Language runners - each takes source code, compiles/runs it, returns proof JSON
# ---------------------------------------------------------------------------

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
    """Run a Python test with pytest and the proof plugin, return the proof JSON."""
    spec_dir = tmp_path / 'specs' / 'test'
    spec_dir.mkdir(parents=True)
    (spec_dir / f'{feature}.md').write_text(
        f'# Feature: {feature}\n\n## Rules\n- RULE-1: test\n\n'
        f'## Proof\n- PROOF-1 (RULE-1): test\n')
    test_file = tmp_path / 'test_it.py'
    test_file.write_text(py_source)
    conftest = tmp_path / 'conftest.py'
    with open(os.path.join(PROOF_SCRIPTS, 'pytest_purlin.py'), encoding='utf-8') as f:
        conftest.write_text(f.read())
    subprocess.run(
        [sys.executable, '-m', 'pytest', str(test_file), '-v', '--tb=short'],
        capture_output=True, text=True, cwd=str(tmp_path))
    proof_path = spec_dir / f'{feature}.proofs-unit.json'
    if proof_path.exists():
        with open(str(proof_path), encoding='utf-8') as f:
            return json.load(f)
    # No proof file written: return the empty shape the caller can still read.
    return {"tier": "unit", "proofs": []}


# ---------------------------------------------------------------------------
# Cheat matrix helpers
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


def _assert_pass1_catches(results, check, msg=""):
    """Assert Pass 1 flags the cheat the runtime plugin happily recorded as pass.

    The runtime assertion beside each of these says the cheat survives the test
    run; this one says the deterministic checker catches it anyway, which is what
    makes the row a Pass 1 catch rather than an LLM job.
    """
    assert len(results) == 1, f"Pass 1 produced {len(results)} proofs. {msg}"
    assert results[0]['status'] == 'fail', f"Pass 1 passed it: {results[0]}. {msg}"
    assert results[0]['check'] == check, f"Pass 1 said {results[0]}. {msg}"


# ===========================================================================
# CHEAT 1: Tautological - assertion always true
# ===========================================================================

class TestTautological:
    """Assertion is always true regardless of what the code does."""

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins_sql", "PROOF-1", "RULE-1")
    def test_sql_tautological(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Validates input')
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: validates input
SELECT CASE WHEN 1 = 1 THEN 'PASS' ELSE 'FAIL' END;
''', 'feat', setup_sql='CREATE TABLE t (id INTEGER);')
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "SQL tautological cheat still passes at runtime")
        _assert_pass1_catches(
            check_sql(str(tmp_path / 'test.sql'), 'feat'), 'tautology',
            "CASE WHEN 1 = 1 THEN 'PASS' compares two constants")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins_vitest", "PROOF-1", "RULE-1")
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
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "TS tautological cheat passes, so it needs the LLM pass")

    @pytest.mark.proof("static_checks", "PROOF-65", "RULE-1", tier="integration")
    def test_python_tautological(self, tmp_path):
        """Python `assert result or True`, caught by the Pass 1 static checks."""
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
        assert results[0]['status'] == 'fail', "Python `or True` caught by the checks"
        assert results[0]['check'] == 'assert_true_literal'


# ===========================================================================
# CHEAT 2: Fixture-only - asserts test data, never calls code under test
# ===========================================================================

class TestFixtureOnly:
    """Test asserts properties of its own constants, never invokes the real code."""

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins_sql", "PROOF-1", "RULE-1")
    def test_sql_fixture_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Unique constraint enforced')
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: unique constraint enforced
SELECT CASE WHEN 'alice' = 'alice' THEN 'PASS' ELSE 'FAIL' END;
''', 'feat', setup_sql='CREATE TABLE users (email TEXT UNIQUE);')
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "SQL fixture-only cheat still passes at runtime")
        _assert_pass1_catches(
            check_sql(str(tmp_path / 'test.sql'), 'feat'), 'tautology',
            "the predicate compares one fixture literal with itself")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins_vitest", "PROOF-1", "RULE-1")
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
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "TS fixture-only cheat passes, so it needs the LLM pass")

    @pytest.mark.proof("static_checks", "PROOF-66", "RULE-7", tier="integration")
    def test_python_fixture_only(self, tmp_path):
        """Python fixture-only: Pass 1 passes it because assertions exist."""
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
        assert results[0]['status'] == 'pass', "Pass 1 passes it: the fixture cheat needs the LLM pass"


# ===========================================================================
# CHEAT 3: Happy-path-only - rule says "rejects X" but test sends valid input
# ===========================================================================

class TestHappyPathOnly:
    """Rule describes rejection behavior, but test only validates the happy path."""

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins_sql", "PROOF-2", "RULE-2")
    def test_sql_happy_path_only(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects duplicate emails')
        data = _run_sql(tmp_path, '''\
-- @purlin feat PROOF-1 RULE-1 unit
-- Test: rejects duplicate emails
INSERT INTO users (email) VALUES ('unique@test.com');
SELECT CASE WHEN (SELECT count(*) FROM users) = 1 THEN 'PASS' ELSE 'FAIL' END;
''', 'feat', setup_sql='CREATE TABLE users (email TEXT UNIQUE);')
        # CHEAT: only inserts one unique row, never tests the duplicate rejection
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "SQL happy-path cheat passes, so it needs the LLM pass")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins_vitest", "PROOF-1", "RULE-1")
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
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "TS happy-path cheat passes, so it needs the LLM pass")

    @pytest.mark.proof("static_checks", "PROOF-67", "RULE-7", tier="integration")
    def test_python_happy_path_only(self, tmp_path):
        """Python happy-path: Pass 1 passes it, the LLM pass catches the missing case."""
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
        assert results[0]['status'] == 'pass', "Pass 1 passes it: the happy-path cheat needs the LLM pass"


# ===========================================================================
# CHEAT 4: Name/value drift - name claims X, assertion checks opposite
# ===========================================================================

class TestNameValueDrift:
    """Test function name describes one behavior, but assertion validates the opposite."""

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins_sql", "PROOF-1", "RULE-1")
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
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "SQL name-drift cheat passes, so it needs the LLM pass")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins_vitest", "PROOF-1", "RULE-1")
    def test_typescript_name_drift(self, tmp_path):
        _setup_spec(tmp_path, 'feat', 'Rejects expired sessions')
        data = _run_typescript(tmp_path, '''\
// Bug: accepts everything
function isSessionValid(token: string): boolean { return true; }
const result = isSessionValid("expired-token-xyz");
// Name says "rejects expired" but asserts result is true, which means accepted
const proofs = [{
    feature: "feat", id: "PROOF-1", rule: "RULE-1",
    test_file: "test.ts", test_name: "test_rejects_expired_session",
    status: (result === true ? "pass" : "fail") as "pass" | "fail", tier: "unit",
}];
console.log(JSON.stringify({ proofs }, null, 2));
''', 'feat')
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "TS name-drift cheat passes, so it needs the LLM pass")

    @pytest.mark.proof("static_checks", "PROOF-68", "RULE-7", tier="integration")
    def test_python_name_drift(self, tmp_path):
        """Python name-drift: Pass 1 passes it, the LLM pass catches it."""
        test_file = tmp_path / 'test_cheat.py'
        test_file.write_text('''\
import pytest
def validate_token(t): return True  # Bug: accepts everything
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_rejects_invalid_token():
    # Name says "rejects" but asserts True, which means accepted
    assert validate_token("INVALID") is True
''')
        results = check_python(str(test_file), 'feat')
        assert results[0]['status'] == 'pass', "Pass 1 passes it: the name-drift cheat needs the LLM pass"


# ===========================================================================
# CHEAT 5: No real assertion - lots of setup, zero actual verification
# ===========================================================================

class TestNoRealAssertion:
    """Test runs code but never checks the output. Setup looks thorough."""

    @pytest.mark.skipif(not shutil.which('sqlite3'), reason='sqlite3 not available')
    @pytest.mark.proof("proof_plugins_sql", "PROOF-2", "RULE-2")
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
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "SQL no-assertion cheat still passes at runtime")
        _assert_pass1_catches(
            check_sql(str(tmp_path / 'test.sql'), 'feat'), 'tautology',
            "SELECT 'PASS' after the DELETE observes nothing")

    @pytest.mark.skipif(not shutil.which('tsc'), reason='tsc not available')
    @pytest.mark.proof("proof_plugins_vitest", "PROOF-1", "RULE-1")
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
        assert data['proofs'][0]['id'] == 'PROOF-1', "proof ID must match spec annotation"
        assert data['proofs'][0]['rule'] == 'RULE-1', "rule linkage must be preserved"
        _assert_proof_passes(data, "TS no-assertion cheat passes, so it needs the LLM pass")

    @pytest.mark.proof("static_checks", "PROOF-69", "RULE-3", tier="integration")
    def test_python_no_assertion(self, tmp_path):
        """Python no-assertion, caught by Pass 1 with the no_assertions check."""
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
        assert results[0]['check'] == 'no_assertion'
