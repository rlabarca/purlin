"""Tests for static_checks.py — 7 rules.

Covers all five Python AST checks (assert_true, no_assertions, bare_except,
logic_mirroring, mock_target_match), JSON output format, and exit codes.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))
from static_checks import (
    check_python,
    _read_rule_descriptions,
)

STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'
)


def _write_tmp(content, suffix='.py'):
    f = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


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

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
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
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
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
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
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
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)


class TestNoAssertions:

    @pytest.mark.proof("static_checks", "PROOF-2", "RULE-2")
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
            assert results[0]['check'] == 'no_assertions'
        finally:
            os.unlink(path)


class TestBareExcept:

    @pytest.mark.proof("static_checks", "PROOF-3", "RULE-3")
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

    @pytest.mark.proof("static_checks", "PROOF-3", "RULE-3")
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

    @pytest.mark.proof("static_checks", "PROOF-4", "RULE-4")
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

    @pytest.mark.proof("static_checks", "PROOF-4", "RULE-4")
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

    @pytest.mark.proof("static_checks", "PROOF-5", "RULE-5")
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
            assert results[0]['check'] == 'mock_target_match'
        finally:
            os.unlink(path)
            os.unlink(spec_path)

    @pytest.mark.proof("static_checks", "PROOF-5", "RULE-5")
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

    @pytest.mark.proof("static_checks", "PROOF-6", "RULE-6")
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
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat"],
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

    @pytest.mark.proof("static_checks", "PROOF-7", "RULE-7")
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

    @pytest.mark.proof("static_checks", "PROOF-7", "RULE-7")
    def test_exit_1_when_any_fail(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat"],
                capture_output=True, text=True
            )
            assert result.returncode == 1
        finally:
            os.unlink(path)
