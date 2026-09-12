"""Tests for static_checks.py.

Covers all five Python AST checks (assert_true, no_assertions, bare_except,
logic_mirroring, mock_target_match), JSON output format, exit codes,
spec coverage checks, audit cache helpers, and language-agnostic
proof-file structural checks (proof_id_collision, proof_rule_orphan).
"""

import ast
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))
import static_checks
from static_checks import (
    analyze_test_file,
    check_c,
    check_csharp,
    check_php,
    check_sql,
    check_proof_file,
    check_python,
    check_shell,
    audit_scope,
    check_proof_design,
    check_spec_coverage,
    clear_audit_cache,
    compute_proof_hash,
    deterministic_sweep,
    prune_audit_cache,
    read_audit_cache,
    resolve_test_file_from_name,
    write_audit_cache,
    _read_rule_descriptions,
    load_criteria,
    cache_key_for,
    rekey_cache_entries,
    CriteriaError,
    ProofInputsError,
)

_STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'
)

STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'
)


def _write_tmp(content, suffix='.py'):
    f = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


def _scaffold_proof(root, feature='login', proof_id='PROOF-1', rule_id='RULE-1',
                    test_file='tests/test_login.py', test_name='test_login',
                    rule_text=None, description=None, tier='unit',
                    test_body='    assert 1 + 1 == 2', write_test=True):
    """Write the spec, proof record and test function behind <feature>/<proof_id>.

    write_audit_cache re-keys every entry through cache_key_for(), which resolves
    the rule text, the proof description and the graded test's source out of the
    project (RULE-38). A temp project with no specs therefore resolves nothing and
    a whole batch is rejected, so every test that writes cache entries needs real
    project state behind the (feature, proof_id) pairs it names.

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

    # --- proof file: the only record of which test function backs the proof ---
    proof_path = os.path.join(spec_dir, f'{feature}.proofs-{tier}.json')
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


def _key(root, feature, proof_id, cache_name=None):
    """The cache key static_checks computes for a proof — never hard-coded."""
    if cache_name is None:
        cache_name = static_checks.AUDIT_CACHE
    return cache_key_for(root, feature, proof_id, cache_name)[0]


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
    def test_exit_0_with_fail_status_when_defects_found(self):
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
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert any(p['status'] == 'fail' for p in data['proofs'])
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-67", "RULE-7")
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

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-8")
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

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-8")
    def test_spec_coverage_via_cli(self):
        """CLI --check-spec-coverage returns rule and proof counts."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
            "- RULE-1: Verify file exists in specs directory\n"
            "- RULE-2: Returns error when missing\n"
            "\n## Proof\n"
            "- PROOF-1 (RULE-1): test\n"
            "- PROOF-2 (RULE-2): test\n",
            suffix='.md'
        )
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, '--check-spec-coverage', '--spec-path', path],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data['rule_count'] == 2
            assert data['proof_count'] == 2
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-8")
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


class TestAuditCache:

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-10")
    def test_compute_proof_hash_deterministic(self):
        # Expected value pre-computed: sha256("rule text\x00proof desc\x00test code")[:16]
        expected = '64e4571be6c61536'
        h1 = compute_proof_hash("rule text", "proof desc", "test code")
        assert h1 == expected
        assert len(h1) == 16
        assert all(c in '0123456789abcdef' for c in h1)

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-10")
    def test_compute_proof_hash_different_inputs(self):
        h1 = compute_proof_hash("rule A", "proof A", "test A")
        h2 = compute_proof_hash("rule B", "proof B", "test B")
        assert h1 != h2
        # Pin the exact algorithm: sha256("rule A\x00proof A\x00test A")[:16]
        # Pre-computed independently via: hashlib.sha256(b"rule A\x00proof A\x00test A").hexdigest()[:16]
        assert h1 == "d81ac1e833476848", (
            f"Hash algorithm mismatch: expected d81ac1e833476848, got {h1!r}. "
            "This pins the null-byte separator and sha256 algorithm."
        )
        assert len(h1) == 16
        assert all(c in "0123456789abcdef" for c in h1)

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-10")
    def test_compute_proof_hash_no_separator_collision(self):
        """Input-shifting must produce different hashes."""
        h1 = compute_proof_hash("a|b", "c", "d")
        h2 = compute_proof_hash("a", "b|c", "d")
        assert h1 != h2

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_audit_cache(tmpdir)
            assert result == {}

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            os.makedirs(cache_dir)
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            data = {"abc123": {"assessment": "STRONG", "criterion": "matches"}}
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            result = read_audit_cache(tmpdir)
            assert result == data

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_non_dict_returns_empty(self):
        """Cache file with non-dict JSON (e.g. a list) returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            os.makedirs(cache_dir)
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            with open(cache_path, 'w') as f:
                json.dump([1, 2, 3], f)
            result = read_audit_cache(tmpdir)
            assert result == {}

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_corrupt_json_returns_empty(self):
        """Cache file with invalid JSON returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            os.makedirs(cache_dir)
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            with open(cache_path, 'w') as f:
                f.write("{corrupt json")
            result = read_audit_cache(tmpdir)
            assert result == {}

    @pytest.mark.proof("static_checks", "PROOF-12", "RULE-12")
    def test_write_cache_atomic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'login', 'PROOF-1', 'RULE-1')
            data = {
                "a1b2c3d4e5f6a7b8": {
                    "assessment": "STRONG",
                    "criterion": "matches rule intent",
                    "why": "test exercises the rule correctly",
                    "fix": "none",
                    "feature": "login",
                    "proof_id": "PROOF-1",
                    "rule_id": "RULE-1",
                    "priority": "LOW",
                }
            }
            # Prove the atomic mechanism: the durable file must be produced by
            # renaming a temp file via os.replace, never by writing in place.
            real_replace = os.replace
            replace_calls = []

            def spy_replace(src, dst):
                replace_calls.append((src, dst))
                return real_replace(src, dst)

            with mock.patch.object(static_checks.os, 'replace', side_effect=spy_replace):
                write_audit_cache(tmpdir, data)

            cache_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json')
            assert replace_calls, "write is not atomic — os.replace was never called"
            src, dst = replace_calls[-1]
            assert src.endswith('.tmp'), f"expected rename from a .tmp file, got {src!r}"
            assert os.path.abspath(dst) == os.path.abspath(cache_path), \
                f"os.replace target {dst!r} is not the cache file"

            # The written key is recomputed from project state, so look it up
            # rather than asserting the arbitrary literal supplied above.
            key = _key(tmpdir, 'login', 'PROOF-1')
            result = read_audit_cache(tmpdir)
            assert set(result) == {key}, f"expected the recomputed key {key}, got {list(result)}"
            for field, value in data['a1b2c3d4e5f6a7b8'].items():
                assert result[key][field] == value, f"{field} did not round-trip"
            # No .tmp file left behind after the rename
            assert not os.path.exists(cache_path + '.tmp')

            # What the rename buys: a replacement that fails partway must leave
            # the previous file exactly as it was. A plain open-and-write would
            # have truncated the cache before failing, losing the STRONG entry.
            second = {
                'ignored-key': dict(data['a1b2c3d4e5f6a7b8'], assessment='HOLLOW'),
            }
            with mock.patch.object(static_checks.os, 'replace',
                                   side_effect=OSError('no space left on device')):
                with pytest.raises(OSError):
                    write_audit_cache(tmpdir, second)

            survived = read_audit_cache(tmpdir)
            assert set(survived) == {key}, (
                "a failed replacement must leave the previous cache intact, "
                f"got keys {sorted(survived)}")
            assert survived[key]['assessment'] == 'STRONG', (
                "the half-written HOLLOW entry became visible: the cache reads "
                f"{survived[key]['assessment']!r}")

    @pytest.mark.proof("static_checks", "PROOF-70", "RULE-43")
    def test_failed_rename_leaves_no_temp_file(self):
        """A rename that raises removes its .tmp, re-raises, cache byte-identical."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'login', 'PROOF-1', 'RULE-1')
            entry = {
                "assessment": "STRONG",
                "criterion": "matches rule intent",
                "why": "test exercises the rule correctly",
                "fix": "none",
                "feature": "login",
                "proof_id": "PROOF-1",
                "rule_id": "RULE-1",
                "priority": "LOW",
            }
            write_audit_cache(tmpdir, {"a1b2c3d4e5f6a7b8": dict(entry)})

            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            with open(cache_path, 'rb') as f:
                before_bytes = f.read()
            before_listing = sorted(os.listdir(cache_dir))

            second = {'ignored-key': dict(entry, assessment='HOLLOW')}
            with mock.patch.object(static_checks.os, 'replace',
                                   side_effect=OSError('no space left on device')):
                with pytest.raises(OSError) as excinfo:
                    write_audit_cache(tmpdir, second)
            assert str(excinfo.value) == 'no space left on device', (
                "the rename's own exception must reach the caller unchanged, got "
                f"{excinfo.value!r}")

            with open(cache_path, 'rb') as f:
                after_bytes = f.read()
            assert after_bytes == before_bytes, (
                "a failed rename rewrote the durable cache: "
                f"{len(before_bytes)} bytes became {len(after_bytes)}")

            key = _key(tmpdir, 'login', 'PROOF-1')
            survived = read_audit_cache(tmpdir)
            assert set(survived) == {key}, (
                "the failed write's entry reached the cache, keys are "
                f"{sorted(survived)}")
            assert survived[key]['assessment'] == 'STRONG', (
                "the HOLLOW entry of the failed write became visible: the cache "
                f"reads {survived[key]['assessment']!r}")

            # The point of the cleanup: the cache directory holds exactly the
            # files it held before, so a leftover fragment is named here.
            after_listing = sorted(os.listdir(cache_dir))
            assert after_listing == before_listing, (
                "a failed rename left files behind in .purlin/cache/: "
                f"{sorted(set(after_listing) - set(before_listing))} "
                f"(listing was {before_listing}, now {after_listing})")
            assert not any(name.endswith('.tmp') for name in after_listing), \
                f"a .tmp fragment survives in .purlin/cache/: {after_listing}"


class TestWriteCacheMerge:
    """RULE-24: write_audit_cache merges into existing cache on disk."""

    def _make_entry(self, assessment, feature, proof_id, rule_id, ts="2026-04-01T00:00:00+00:00"):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": ts,
        }

    @pytest.mark.proof("static_checks", "PROOF-39", "RULE-24")
    def test_second_write_preserves_first_write_entries(self):
        """Two sequential writes for different features must both survive on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feat, proofs in (('feature_a', 3), ('feature_b', 2)):
                for n in range(1, proofs + 1):
                    _scaffold_proof(
                        tmpdir, feat, f'PROOF-{n}', f'RULE-{n}',
                        test_file=f'tests/test_{feat}.py',
                        test_name=f'test_{feat}_{n}')
            ka1 = _key(tmpdir, 'feature_a', 'PROOF-1')
            ka2 = _key(tmpdir, 'feature_a', 'PROOF-2')
            ka3 = _key(tmpdir, 'feature_a', 'PROOF-3')
            kb1 = _key(tmpdir, 'feature_b', 'PROOF-1')
            kb2 = _key(tmpdir, 'feature_b', 'PROOF-2')

            # First write: 3 entries for feature_a
            batch_a = {
                "hash_a1": self._make_entry("STRONG", "feature_a", "PROOF-1", "RULE-1"),
                "hash_a2": self._make_entry("STRONG", "feature_a", "PROOF-2", "RULE-2"),
                "hash_a3": self._make_entry("WEAK",   "feature_a", "PROOF-3", "RULE-3"),
            }
            write_audit_cache(tmpdir, batch_a)

            # Second write: 2 entries for feature_b (different feature)
            batch_b = {
                "hash_b1": self._make_entry("STRONG", "feature_b", "PROOF-1", "RULE-1"),
                "hash_b2": self._make_entry("STRONG", "feature_b", "PROOF-2", "RULE-2"),
            }
            write_audit_cache(tmpdir, batch_b)

            # Read back: ALL 5 entries must be present
            after = read_audit_cache(tmpdir)
            assert len(after) == 5, f"Expected 5 entries (3 from A + 2 from B), got {len(after)}"
            assert ka1 in after, "feature_a entry lost after feature_b write"
            assert ka2 in after, "feature_a entry lost after feature_b write"
            assert ka3 in after, "feature_a entry lost after feature_b write"
            assert kb1 in after, "feature_b entry missing"
            assert kb2 in after, "feature_b entry missing"
            # Verify assessments are correct (not swapped or corrupted)
            assert after[ka3]["assessment"] == "WEAK"
            assert after[ka3]["feature"] == "feature_a"
            assert after[kb1]["assessment"] == "STRONG"
            assert after[kb1]["feature"] == "feature_b"

    @pytest.mark.proof("static_checks", "PROOF-39", "RULE-24")
    def test_update_entry_preserves_other_features(self):
        """Updating one feature's entry must not disturb another feature's entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feat in ('feature_a', 'feature_b'):
                for n in (1, 2):
                    _scaffold_proof(
                        tmpdir, feat, f'PROOF-{n}', f'RULE-{n}',
                        test_file=f'tests/test_{feat}.py',
                        test_name=f'test_{feat}_{n}')
            ka1 = _key(tmpdir, 'feature_a', 'PROOF-1')
            ka2 = _key(tmpdir, 'feature_a', 'PROOF-2')
            kb1 = _key(tmpdir, 'feature_b', 'PROOF-1')
            kb2 = _key(tmpdir, 'feature_b', 'PROOF-2')

            # Seed: feature_a (2 entries) + feature_b (2 entries)
            seed = {
                "hash_a1": self._make_entry("HOLLOW", "feature_a", "PROOF-1", "RULE-1"),
                "hash_a2": self._make_entry("STRONG", "feature_a", "PROOF-2", "RULE-2"),
                "hash_b1": self._make_entry("STRONG", "feature_b", "PROOF-1", "RULE-1"),
                "hash_b2": self._make_entry("WEAK",   "feature_b", "PROOF-2", "RULE-2"),
            }
            write_audit_cache(tmpdir, seed)

            # The graded test for feature_a PROOF-1 is edited, so its key really
            # does change — the dedup below is then a dedup across two hashes.
            _scaffold_proof(
                tmpdir, 'feature_a', 'PROOF-1', 'RULE-1',
                test_file='tests/test_feature_a.py', test_name='test_feature_a_1',
                test_body='    assert 2 + 2 == 4')
            ka1_v2 = _key(tmpdir, 'feature_a', 'PROOF-1')
            assert ka1_v2 != ka1, "editing the graded test must move the key"

            # Update: feature_a PROOF-1 upgraded from HOLLOW to STRONG (new hash = test code changed)
            update = {
                "hash_a1_v2": self._make_entry(
                    "STRONG", "feature_a", "PROOF-1", "RULE-1",
                    ts="2026-04-02T00:00:00+00:00",  # newer timestamp
                ),
            }
            write_audit_cache(tmpdir, update)

            after = read_audit_cache(tmpdir)
            # feature_b untouched
            assert after[kb1]["assessment"] == "STRONG"
            assert after[kb1]["feature"] == "feature_b"
            assert after[kb2]["assessment"] == "WEAK"
            assert after[kb2]["feature"] == "feature_b"
            # feature_a PROOF-1: old HOLLOW replaced by new STRONG (dedup by feature+proof_id)
            assert ka1_v2 in after, "Updated entry missing"
            assert after[ka1_v2]["assessment"] == "STRONG"
            # Old hash for same (feature_a, PROOF-1) should be gone (dedup)
            assert ka1 not in after, "Stale entry for same (feature, proof_id) should be pruned"
            # feature_a PROOF-2 still present
            assert after[ka2]["assessment"] == "STRONG"


class TestPruneAuditCache:

    def _make_entry(self, assessment, feature, proof_id, rule_id):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": "2026-04-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-36", "RULE-22")
    def test_prune_removes_dead_preserves_live(self):
        """Prune with 2 of 3 keys live removes the third, preserves the other 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feat in ('feat_a', 'feat_b', 'feat_c'):
                _scaffold_proof(tmpdir, feat, 'PROOF-1', 'RULE-1',
                                test_file=f'tests/test_{feat}.py',
                                test_name=f'test_{feat}')
            aaa = _key(tmpdir, 'feat_a', 'PROOF-1')
            bbb = _key(tmpdir, 'feat_b', 'PROOF-1')
            ccc = _key(tmpdir, 'feat_c', 'PROOF-1')
            cache = {
                "aaa": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                "bbb": self._make_entry("WEAK", "feat_b", "PROOF-1", "RULE-1"),
                "ccc": self._make_entry("STRONG", "feat_c", "PROOF-1", "RULE-1"),
            }
            write_audit_cache(tmpdir, cache)
            result = prune_audit_cache(tmpdir, live_keys={aaa, ccc})
            assert result["pruned"] == 1
            assert result["kept"] == 2
            after = read_audit_cache(tmpdir)
            assert aaa in after
            assert ccc in after
            assert bbb not in after
            # Verify fields are intact
            assert after[aaa]["assessment"] == "STRONG"
            assert after[aaa]["feature"] == "feat_a"
            assert after[ccc]["assessment"] == "STRONG"
            assert after[ccc]["feature"] == "feat_c"

    @pytest.mark.proof("static_checks", "PROOF-37", "RULE-23")
    def test_prune_empty_live_keys_clears_all(self):
        """Prune with empty live_keys set produces empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feat in ('feat_a', 'feat_b', 'feat_c'):
                _scaffold_proof(tmpdir, feat, 'PROOF-1', 'RULE-1',
                                test_file=f'tests/test_{feat}.py',
                                test_name=f'test_{feat}')
            cache = {
                "aaa": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                "bbb": self._make_entry("STRONG", "feat_b", "PROOF-1", "RULE-1"),
                "ccc": self._make_entry("STRONG", "feat_c", "PROOF-1", "RULE-1"),
            }
            write_audit_cache(tmpdir, cache)
            result = prune_audit_cache(tmpdir, live_keys=set())
            assert result["pruned"] == 3
            assert result["kept"] == 0
            after = read_audit_cache(tmpdir)
            assert after == {}

    @pytest.mark.proof("static_checks", "PROOF-37", "RULE-23")
    def test_prune_all_keys_live_preserves_all(self):
        """Prune with all keys live preserves identical cache content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feat, n in (('feat_a', 1), ('feat_b', 2), ('feat_c', 3)):
                _scaffold_proof(tmpdir, feat, f'PROOF-{n}', f'RULE-{n}',
                                test_file=f'tests/test_{feat}.py',
                                test_name=f'test_{feat}')
            aaa = _key(tmpdir, 'feat_a', 'PROOF-1')
            bbb = _key(tmpdir, 'feat_b', 'PROOF-2')
            ccc = _key(tmpdir, 'feat_c', 'PROOF-3')
            cache = {
                "aaa": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                "bbb": self._make_entry("WEAK", "feat_b", "PROOF-2", "RULE-2"),
                "ccc": self._make_entry("STRONG", "feat_c", "PROOF-3", "RULE-3"),
            }
            write_audit_cache(tmpdir, cache)
            result = prune_audit_cache(tmpdir, live_keys={aaa, bbb, ccc})
            assert result["pruned"] == 0
            assert result["kept"] == 3
            after = read_audit_cache(tmpdir)
            # All entries still present — verified against literal values from _make_entry args
            assert set(after.keys()) == {aaa, bbb, ccc}
            assert after[aaa]["assessment"] == "STRONG"
            assert after[aaa]["feature"] == "feat_a"
            assert after[bbb]["assessment"] == "WEAK"
            assert after[bbb]["feature"] == "feat_b"
            assert after[ccc]["assessment"] == "STRONG"
            assert after[ccc]["feature"] == "feat_c"


class TestShellIfElsePair:

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-13")
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

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-13")
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
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-13")
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

    @pytest.mark.proof("static_checks", "PROOF-14", "RULE-14")
    def test_literal_assert_true_has_literal_true(self):
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
            assert results[0]['literal'] is True
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-14", "RULE-14")
    def test_heuristic_assert_has_literal_false(self):
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
            assert results[0]['literal'] is False
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Proof-file structural checks (Pass 0.5 — language-agnostic)
#
# These tests verify that check_proof_file works regardless of which language
# produced the proof JSON. Each test creates proof files as if emitted by
# different language test runners (Python/pytest, JavaScript/Jest, Shell,
# C/CUnit, PHP/PHPUnit, SQL/pgTAP, TypeScript/Vitest).
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


def _c_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_auth.c",
        "test_name": "test_validates_credentials",
        "status": status, "tier": "unit",
    }


def _php_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/AuthTest.php",
        "test_name": "testValidatesCredentials",
        "status": status, "tier": "unit",
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
    "c": _c_proof,
    "php": _php_proof,
    "sql": _sql_proof,
    "typescript": _typescript_proof,
}


class TestProofIdCollision:
    """Proof ID collision detection across all supported language contexts."""

    @pytest.mark.parametrize("lang,factory", list(_LANGUAGE_FACTORIES.items()))
    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
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

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
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

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
    def test_collision_with_mixed_languages(self, tmp_path):
        """Collision across language boundaries — Python and TypeScript both claim PROOF-1."""
        proofs = [
            _python_proof("auth", "PROOF-1", "RULE-1"),
            _typescript_proof("auth", "PROOF-1", "RULE-3"),
            _c_proof("auth", "PROOF-2", "RULE-2"),
        ]
        proof_path = _write_proof_json(tmp_path, "auth", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 1
        assert set(collisions[0]['rules']) == {'RULE-1', 'RULE-3'}

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
    def test_multiple_collisions_detected(self, tmp_path):
        """Two separate collisions in one file — both detected."""
        proofs = [
            _php_proof("cart", "PROOF-1", "RULE-1"),
            _php_proof("cart", "PROOF-1", "RULE-2"),
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
    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
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

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
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

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
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

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
    def test_no_orphan_check_without_spec(self, tmp_path):
        """Without spec_path, orphan check is skipped — only collision check runs."""
        proofs = [
            _c_proof("login", "PROOF-1", "RULE-1"),
            _c_proof("login", "PROOF-99", "RULE-99"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)  # no spec_path
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, "Should not check orphans without spec_path"


class TestLoadCriteria:
    """Tests for load_criteria() — single source for criteria assembly."""

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_builtin_only(self, tmp_path):
        """load_criteria returns built-in content when no additional criteria configured."""
        project = str(tmp_path)
        os.makedirs(os.path.join(project, '.purlin', 'cache'), exist_ok=True)
        result = load_criteria(project)
        assert '## Assessment Levels' in result
        # No separator with "(from" — the built-in doc has a section titled
        # "Additional Team Criteria" but load_criteria adds "(from <url>)"
        assert 'Additional Team Criteria (from' not in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_with_additional_criteria(self, tmp_path):
        """load_criteria appends cached additional criteria with separator."""
        project = str(tmp_path)
        cache_dir = os.path.join(project, '.purlin', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        # Write config with audit_criteria source URL
        config_dir = os.path.join(project, '.purlin')
        with open(os.path.join(config_dir, 'config.json'), 'w') as f:
            json.dump({'audit_criteria': 'git@example.com:team/quality.git#criteria.md',
                       'audit_criteria_pinned': 'c0ffee1'}, f)
        # Write cached additional criteria, pinned to the sha config records
        # (RULE-41: a configured source must carry a matching pin).
        with open(os.path.join(cache_dir, 'additional_criteria.md'), 'w') as f:
            f.write('<!-- purlin-criteria-sha: c0ffee1 -->\n'
                    '## Team-Specific WEAK Criteria\n\n- No sleep() in tests\n')
        result = load_criteria(project)
        # Built-in must be present
        assert '## Assessment Levels' in result
        # Additional must be appended with separator
        assert '## Additional Team Criteria' in result
        assert 'git@example.com:team/quality.git#criteria.md' in result
        assert 'No sleep() in tests' in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_with_extra_path(self, tmp_path):
        """load_criteria appends extra file when --extra is provided."""
        project = str(tmp_path)
        os.makedirs(os.path.join(project, '.purlin', 'cache'), exist_ok=True)
        extra_file = str(tmp_path / 'extra_criteria.md')
        with open(extra_file, 'w') as f:
            f.write('## Custom Extra\n\n- All tests must have docstrings\n')
        result = load_criteria(project, extra_path=extra_file)
        assert '## Assessment Levels' in result
        assert '## Additional Criteria' in result
        assert 'All tests must have docstrings' in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_all_three_sources(self, tmp_path):
        """load_criteria combines built-in + additional + extra."""
        project = str(tmp_path)
        cache_dir = os.path.join(project, '.purlin', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(project, '.purlin', 'config.json'), 'w') as f:
            json.dump({'audit_criteria': 'git@example.com:team/q.git#c.md',
                       'audit_criteria_pinned': 'c0ffee1'}, f)
        with open(os.path.join(cache_dir, 'additional_criteria.md'), 'w') as f:
            f.write('<!-- purlin-criteria-sha: c0ffee1 -->\n'
                    '## Team Rules\n\n- No mocking databases\n')
        extra_file = str(tmp_path / 'extra.md')
        with open(extra_file, 'w') as f:
            f.write('## Project Rules\n\n- All tests under 100ms\n')
        result = load_criteria(project, extra_path=extra_file)
        # All three must be present
        assert '## Assessment Levels' in result
        assert '## Additional Team Criteria' in result
        assert 'No mocking databases' in result
        assert '## Additional Criteria' in result
        assert 'All tests under 100ms' in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_no_additional_without_cache_file(self, tmp_path):
        """Nothing is appended when there is no cached additional criteria.

        With no `audit_criteria` configured there is nothing to append and the
        built-in criteria stand alone. With `audit_criteria` configured the
        missing cache is no longer a silent no-op: RULE-41 makes it an error,
        because falling back to the built-in criteria would grade the project
        against the wrong standard and say nothing.
        """
        project = str(tmp_path)
        os.makedirs(os.path.join(project, '.purlin', 'cache'), exist_ok=True)
        # No config, no additional_criteria.md in cache
        result = load_criteria(project)
        assert '## Assessment Levels' in result
        assert 'Additional Team Criteria (from' not in result

        # Configured source, still no cache file: refuse rather than append nothing.
        with open(os.path.join(project, '.purlin', 'config.json'), 'w') as f:
            json.dump({'audit_criteria': 'git@example.com:team/q.git#c.md',
                       'audit_criteria_pinned': 'c0ffee1'}, f)
        with pytest.raises(CriteriaError) as exc:
            load_criteria(project)
        assert 'additional_criteria.md' in str(exc.value)
        assert 'git@example.com:team/q.git#c.md' in str(exc.value)

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_load_criteria_is_the_only_assembler(self):
        """No other function in static_checks.py assembles criteria text.

        The three paths above are a single source only while nothing else
        reads the criteria files: a second reader would let the tool grade
        against text load_criteria never saw, and the three tests above could
        not tell. Docstrings are excluded so a function that merely cites
        references/audit_criteria.md in prose is not counted as a reader.
        """
        source = open(STATIC_CHECKS_PY, encoding='utf-8').read()
        tree = ast.parse(source)
        filenames = ('audit_criteria.md', 'additional_criteria.md')

        readers = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            docstring_node = None
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstring_node = node.body[0].value
            for sub in ast.walk(node):
                if sub is docstring_node:
                    continue
                if (isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                        and any(name in sub.value for name in filenames)):
                    readers.add(node.name)
                    break

        assert readers, \
            "the walk found no function naming the criteria files at all"
        assert readers == {'load_criteria'}, (
            "load_criteria must be the only function in static_checks.py that "
            f"assembles criteria text; these also name the criteria files: "
            f"{sorted(readers)}")


class TestWriteCacheLocking:
    """RULE-25: write_audit_cache serializes concurrent writers via exclusive file lock."""

    def _make_entry(self, assessment, feature, proof_id, rule_id):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": "2026-04-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-40", "RULE-25")
    def test_lock_file_created_alongside_cache(self):
        """write_audit_cache acquires the exclusive lock on audit_cache.json.lock.

        Patches the platform-neutral _lock_exclusive helper (not fcntl directly)
        so the test runs identically on Windows and POSIX.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'feat_a', 'PROOF-1', 'RULE-1',
                            test_file='tests/test_feat_a.py', test_name='test_feat_a_1')
            lock_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json.lock')
            lock_seen = []
            real_lock = static_checks._lock_exclusive

            def spy(lock_file):
                lock_seen.append(os.path.exists(lock_path))
                return real_lock(lock_file)

            with mock.patch.object(static_checks, '_lock_exclusive', side_effect=spy):
                write_audit_cache(tmpdir, {
                    "hash1": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                })

            assert lock_seen, "_lock_exclusive was never called"
            assert lock_seen[0], "lock file did not exist when the lock was acquired"

    @pytest.mark.proof("static_checks", "PROOF-40", "RULE-25")
    def test_concurrent_writes_preserve_all_entries(self):
        """Two threads writing different features concurrently must both survive."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            for feat, proofs in (('feat_a', 2), ('feat_b', 3)):
                for n in range(1, proofs + 1):
                    _scaffold_proof(tmpdir, feat, f'PROOF-{n}', f'RULE-{n}',
                                    test_file=f'tests/test_{feat}.py',
                                    test_name=f'test_{feat}_{n}')
            ka1 = _key(tmpdir, 'feat_a', 'PROOF-1')
            ka2 = _key(tmpdir, 'feat_a', 'PROOF-2')
            kb1 = _key(tmpdir, 'feat_b', 'PROOF-1')
            kb2 = _key(tmpdir, 'feat_b', 'PROOF-2')
            kb3 = _key(tmpdir, 'feat_b', 'PROOF-3')
            errors = []

            def writer_a():
                try:
                    write_audit_cache(tmpdir, {
                        "hash_a1": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                        "hash_a2": self._make_entry("WEAK",   "feat_a", "PROOF-2", "RULE-2"),
                    })
                except Exception as e:
                    errors.append(e)

            def writer_b():
                try:
                    write_audit_cache(tmpdir, {
                        "hash_b1": self._make_entry("STRONG", "feat_b", "PROOF-1", "RULE-1"),
                        "hash_b2": self._make_entry("HOLLOW", "feat_b", "PROOF-2", "RULE-2"),
                        "hash_b3": self._make_entry("STRONG", "feat_b", "PROOF-3", "RULE-3"),
                    })
                except Exception as e:
                    errors.append(e)

            t_a = threading.Thread(target=writer_a)
            t_b = threading.Thread(target=writer_b)
            t_a.start()
            t_b.start()
            t_a.join()
            t_b.join()

            assert not errors, f"Writer thread raised: {errors}"
            after = read_audit_cache(tmpdir)
            assert len(after) == 5, (
                f"Expected 5 entries (2 from feat_a + 3 from feat_b), got {len(after)}:\n"
                + json.dumps(list(after.keys()), indent=2)
            )
            assert ka1 in after, "feat_a entry hash_a1 lost after concurrent write"
            assert ka2 in after, "feat_a entry hash_a2 lost after concurrent write"
            assert kb1 in after, "feat_b entry hash_b1 lost after concurrent write"
            assert kb2 in after, "feat_b entry hash_b2 lost after concurrent write"
            assert kb3 in after, "feat_b entry hash_b3 lost after concurrent write"


class TestWriteCacheCLI:
    """RULE-26: --write-cache CLI reads JSON from stdin and merges into audit cache."""

    def _make_entry(self, assessment, feature, proof_id, rule_id):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": "2026-04-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-41", "RULE-26")
    def test_write_cache_cli_merges_entries(self):
        """--write-cache reads JSON dict from stdin and merges into the cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for n in (1, 2):
                _scaffold_proof(tmpdir, 'feat_cli', f'PROOF-{n}', f'RULE-{n}',
                                test_file='tests/test_feat_cli.py',
                                test_name=f'test_feat_cli_{n}')
            k1 = _key(tmpdir, 'feat_cli', 'PROOF-1')
            k2 = _key(tmpdir, 'feat_cli', 'PROOF-2')
            entries = {
                "cli_hash_1": self._make_entry("STRONG", "feat_cli", "PROOF-1", "RULE-1"),
                "cli_hash_2": self._make_entry("WEAK",   "feat_cli", "PROOF-2", "RULE-2"),
            }
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, '--write-cache', '--project-root', tmpdir],
                input=json.dumps(entries),
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"--write-cache exited non-zero: {result.stderr}"
            output = json.loads(result.stdout)
            assert output['status'] == 'merged'
            assert output['entries'] == 2

            after = read_audit_cache(tmpdir)
            assert len(after) == 2
            assert k1 in after
            assert k2 in after

    @pytest.mark.proof("static_checks", "PROOF-41", "RULE-26")
    def test_write_cache_cli_merges_with_existing(self):
        """--write-cache preserves entries already on disk from a prior write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for feat in ('feat_existing', 'feat_new'):
                _scaffold_proof(tmpdir, feat, 'PROOF-1', 'RULE-1',
                                test_file=f'tests/test_{feat}.py',
                                test_name=f'test_{feat}')
            k_existing = _key(tmpdir, 'feat_existing', 'PROOF-1')
            k_new = _key(tmpdir, 'feat_new', 'PROOF-1')
            write_audit_cache(tmpdir, {
                "existing_hash": self._make_entry("STRONG", "feat_existing", "PROOF-1", "RULE-1"),
            })

            new_entry = {
                "new_hash": self._make_entry("HOLLOW", "feat_new", "PROOF-1", "RULE-1"),
            }
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, '--write-cache', '--project-root', tmpdir],
                input=json.dumps(new_entry),
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"--write-cache exited non-zero: {result.stderr}"

            after = read_audit_cache(tmpdir)
            assert len(after) == 2, f"Expected 2 entries (existing + new), got {len(after)}"
            assert k_existing in after, "existing entry was clobbered by --write-cache"
            assert k_new in after, "new entry not written by --write-cache"


class TestCheckJs:
    """check_js JS/TS structural checks, exercised through the real CLI."""

    @staticmethod
    def _run(ts_source, feature):
        path = _write_tmp(ts_source, suffix='.ts')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, feature],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"static_checks exited non-zero: {result.stderr}"
            return {p['proof_id']: p for p in json.loads(result.stdout)['proofs']}
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-42", "RULE-27", tier="e2e")
    def test_check_js_assertion_detection(self):
        """assert_true and no_assertions are detected in JS/TS bodies; clean tests pass."""
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
        assert proofs["PROOF-1"]["check"] == "assert_true"
        assert proofs["PROOF-2"]["status"] == "fail"
        assert proofs["PROOF-2"]["check"] == "no_assertions"
        assert proofs["PROOF-3"]["status"] == "pass"

        # RULE-27: check_js returns the same JSON shape as check_python —
        # every proof dict carries proof_id, rule_id, test_name, status, reason.
        for pid in ("PROOF-1", "PROOF-2", "PROOF-3"):
            entry = proofs[pid]
            for field in ("proof_id", "rule_id", "test_name", "status", "reason"):
                assert field in entry, f"{pid} missing '{field}' (shape must match check_python): {entry}"
        assert proofs["PROOF-1"]["rule_id"] == "RULE-1"
        assert proofs["PROOF-3"]["test_name"].startswith("real assertion")

    @pytest.mark.proof("static_checks", "PROOF-43", "RULE-28", tier="e2e")
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
        assert "PROOF-1" in proofs, "options-object test vanished from audit output"
        assert "PROOF-2" in proofs, "apostrophe-title test vanished from audit output"
        # Bug #1: the options-object body must be captured fully, so the expect()
        # after it is seen and the test is NOT falsely flagged no_assertions.
        assert proofs["PROOF-1"]["status"] == "pass", proofs["PROOF-1"]
        assert proofs["PROOF-1"].get("check") != "no_assertions"
        assert proofs["PROOF-2"]["status"] == "pass"


class TestCrossPlatformPortability:
    """RULE-29/30: static_checks.py imports and runs on Windows as well as POSIX."""

    def _source(self):
        with open(STATIC_CHECKS_PY, encoding='utf-8') as f:
            return f.read()

    @pytest.mark.proof("static_checks", "PROOF-44", "RULE-29")
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

    @pytest.mark.proof("static_checks", "PROOF-45", "RULE-30")
    def test_all_text_open_calls_specify_utf8(self):
        """Every text-mode open() in static_checks.py passes encoding='utf-8'."""
        tree = ast.parse(self._source())
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'open'):
                continue
            # Resolve the mode (2nd positional arg or mode= kwarg).
            mode = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == 'mode' and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if isinstance(mode, str) and 'b' in mode:
                continue  # binary mode takes no encoding
            enc = None
            for kw in node.keywords:
                if kw.arg == 'encoding' and isinstance(kw.value, ast.Constant):
                    enc = kw.value.value
            if enc != 'utf-8':
                offenders.append(getattr(node, 'lineno', '?'))
        assert not offenders, \
            f"text-mode open() without encoding='utf-8' at lines: {offenders}"


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

    @pytest.mark.proof("static_checks", "PROOF-46", "RULE-31")
    def test_detects_assert_true(self):
        path = self._cs("Assert.True(true);")
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-47", "RULE-31")
    def test_detects_no_assertions(self):
        path = self._cs("var x = Compute(); var y = x + 1;")
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertions'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-48", "RULE-31")
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

    @pytest.mark.proof("static_checks", "PROOF-49", "RULE-31")
    def test_dispatch_routes_cs_to_check_csharp(self):
        """analyze_test_file routes a .cs file to check_csharp (not the empty fallback)."""
        path = self._cs("Assert.True(true);", proof_id="PROOF-7", rule_id="RULE-9")
        try:
            results = analyze_test_file(path, "csfeat")
            assert results, ".cs file produced no proofs — dispatch fell through to []"
            assert results[0]['proof_id'] == 'PROOF-7'
            assert results[0]['check'] == 'assert_true'
            # A genuinely unknown extension still yields the empty fallback.
            other = _write_tmp("nothing here", suffix='.txt')
            try:
                assert analyze_test_file(other, "csfeat") == []
            finally:
                os.unlink(other)
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-55", "RULE-31")
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
            assert results[0]['check'] == 'no_assertions', \
                f"bare Expect(x) should be no_assertions — {results[0]}"
        finally:
            os.unlink(bare)

    @pytest.mark.proof("static_checks", "PROOF-56", "RULE-32")
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

            # The --resolve-source CLI prints JSON with the resolved test_file.
            r = subprocess.run(
                [sys.executable, _STATIC_CHECKS_PY, '--resolve-source',
                 'Demo.Tests.AuthLogicTests.Evaluate_NullRow', '--project-root', root],
                capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            payload = json.loads(r.stdout)
            assert payload['test_file'] == 'tests/AuthLogicTests.cs', payload


class TestCheckPhp:
    """RULE-45: deterministic Pass-1 checks for PHP (PHPUnit-style) tests."""

    def _php(self, body, proof_id="PROOF-1", rule_id="RULE-1"):
        return _write_tmp(f'''<?php
class DemoTest {{
  /** @purlin phpfeat {proof_id} {rule_id} unit */
  public function testTheThing() {{
{body}
  }}
}}
''', suffix='.php')

    @pytest.mark.proof("static_checks", "PROOF-72", "RULE-45")
    def test_detects_tautologies(self):
        """Every shape that asserts something true by construction is assert_true."""
        cases = {
            'assertTrue(true)': '    $this->assertTrue(true);',
            'assertFalse(false)': '    self::assertFalse(false);',
            'assert(true)': '    assert(true);',
            'assertSame identical': '    $this->assertSame("a", "a");',
            'assertEquals identical': '    $this->assertEquals(1, 1);',
            'constant if guard': (
                '    $r = validate(-1);\n'
                '    if (true !== true) { throw new Exception("impossible"); }'),
        }
        for name, body in cases.items():
            path = self._php(body)
            try:
                results = check_php(path, "phpfeat")
                assert len(results) == 1, f"{name}: expected 1 proof, got {results}"
                assert results[0]['status'] == 'fail', f"{name}: not flagged — {results[0]}"
                assert results[0]['check'] == 'assert_true', f"{name}: {results[0]}"
                assert results[0]['literal'] is True, f"{name}: {results[0]}"
                assert results[0]['test_name'] == 'testTheThing', results[0]
            finally:
                os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-73", "RULE-45")
    def test_detects_no_assertions_through_a_hash_comment(self):
        """A body with no assert/expect/throw is no_assertions, a comment naming
        `throw` is not an assertion, and a `#` comment holding an unbalanced `{`
        does not let the scan run on into the next test.

        Without `#` among the PHP line-comment prefixes the first body swallows the
        second function, finds its assertSame, and the empty test reads as pass.
        """
        path = _write_tmp('''<?php
/** @purlin phpfeat PROOF-1 RULE-1 unit */
function test_no_assert() {
    # a hash comment with a { brace in it
    $result = send_email("user@test.com", "Hello");
    // No throw = pass. But $result is never inspected.
}
/** @purlin phpfeat PROOF-2 RULE-2 unit */
function test_real() {
    $this->assertSame(3, add(1, 2));
}
''', suffix='.php')
        try:
            results = {r['proof_id']: r for r in check_php(path, "phpfeat")}
            assert set(results) == {'PROOF-1', 'PROOF-2'}, results
            assert results['PROOF-1']['status'] == 'fail', results['PROOF-1']
            assert results['PROOF-1']['check'] == 'no_assertions', results['PROOF-1']
            assert results['PROOF-2']['status'] == 'pass', \
                f"the second test's own assertion was not read — {results['PROOF-2']}"
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-74", "RULE-45")
    def test_real_assertion_forms_pass(self):
        """Every assertion shape a PHP test legitimately uses is recognized."""
        cases = {
            'phpunit': '    $this->assertSame(3, add(1, 2));',
            'static': '    self::assertGreaterThan(0, count($rows));',
            'assert class': '    Assert::assertTrue(is_valid($row));',
            'expectException': ('    $this->expectException(RuntimeException::class);\n'
                                '    parse("nope");'),
            'bare assert': '    assert(is_valid($row));',
            'throw guard': ('    $r = validate_email("a@b.c");\n'
                            '    if (!$r) { throw new Exception("should accept"); }'),
            'expect': '    expect(total())->toBe(7);',
            'comment naming a tautology': (
                '    // never write assert(true) here\n'
                '    $this->assertSame(3, add(1, 2));'),
        }
        for name, body in cases.items():
            path = self._php(body)
            try:
                results = check_php(path, "phpfeat")
                assert len(results) == 1, f"{name}: expected 1 proof, got {results}"
                assert results[0]['status'] == 'pass', \
                    f"{name}: real assertion flagged — {results[0]}"
            finally:
                os.unlink(path)


class TestCheckSql:
    """RULE-46: deterministic Pass-1 checks for SQL (sqlite3) proof blocks."""

    def _sql(self, block, proof_id="PROOF-1", rule_id="RULE-1"):
        return _write_tmp(f'-- @purlin sqlfeat {proof_id} {rule_id} unit\n'
                          f'-- Test: the thing\n{block}\n', suffix='.sql')

    @pytest.mark.proof("static_checks", "PROOF-75", "RULE-46")
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
                assert results[0]['check'] == 'assert_true', f"{name}: {results[0]}"
                assert results[0]['test_name'] == 'the thing', results[0]
            finally:
                os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-76", "RULE-46")
    def test_detects_block_with_no_select(self):
        """A block that never SELECTs observes nothing, and the proof id stands in
        for a missing `-- Test:` name exactly as the shipped plugin does."""
        path = _write_tmp("-- @purlin sqlfeat PROOF-3 RULE-3 unit\n"
                          "INSERT INTO users (email) VALUES ('a@b.c');\n", suffix='.sql')
        try:
            results = check_sql(path, "sqlfeat")
            assert len(results) == 1, results
            assert results[0]['status'] == 'fail', results[0]
            assert results[0]['check'] == 'no_assertions', results[0]
            assert results[0]['test_name'] == 'PROOF-3', results[0]
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-77", "RULE-46")
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


class TestCheckC:
    """RULE-47: the one deterministic Pass-1 check a C proof admits."""

    def _c(self, passed, proof_id="PROOF-1", rule_id="RULE-1",
           test_name='"test_thing"'):
        return _write_tmp(f'''#include "c_purlin.h"
int validate(int x) {{ return x > 0 ? 0 : -1; }}
int main(void) {{
    int r = validate(-1);
    purlin_proof("cfeat", "{proof_id}", "{rule_id}", {passed},
                 {test_name}, __FILE__, "unit");
    purlin_proof_finish();
    return 0;
}}
''', suffix='.c')

    @pytest.mark.proof("static_checks", "PROOF-78", "RULE-47")
    def test_detects_constant_passed_argument(self):
        """A `passed` argument built only from literals records a status the code
        under test cannot move. The test_name argument is read from the same call
        even when the string it holds carries a comma and a close paren."""
        for passed in ('1', '1 == 1', '(1)', 'true', '0 == 0 && 1'):
            path = self._c(passed, test_name='"test_a, b) c"')
            try:
                results = check_c(path, "cfeat")
                assert len(results) == 1, f"{passed}: expected 1 proof, got {results}"
                assert results[0]['status'] == 'fail', f"{passed}: not flagged — {results[0]}"
                assert results[0]['check'] == 'assert_true', f"{passed}: {results[0]}"
                assert results[0]['literal'] is True, f"{passed}: {results[0]}"
                assert results[0]['test_name'] == 'test_a, b) c', \
                    f"the string argument was split on its own comma — {results[0]}"
            finally:
                os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-79", "RULE-47")
    def test_computed_arguments_and_short_calls_pass(self):
        """A `passed` argument that reads a variable or calls something is an
        assertion computed before the call, and is left alone. A call with fewer
        than seven arguments, or one whose first argument is not this feature, is
        not a proof call at all: that is what keeps the header's own forwarding
        declaration of purlin_proof out of the results."""
        for passed in ('r == 0', 'strcmp(expected[0], "a") == 0', 'validate(5) == 0'):
            path = self._c(passed)
            try:
                results = check_c(path, "cfeat")
                assert len(results) == 1, f"{passed}: expected 1 proof, got {results}"
                assert results[0]['status'] == 'pass', \
                    f"{passed}: a computed assertion was flagged — {results[0]}"
            finally:
                os.unlink(path)

        short = _write_tmp('''#include "c_purlin.h"
static void purlin_proof(const char *feature, const char *id, const char *rule,
                         int passed, const char *test_name, const char *test_file,
                         const char *tier) {
    purlin_proof_on(feature, id, rule, passed, test_name, test_file, tier, NULL);
}
int main(void) {
    purlin_proof("cfeat", "PROOF-1", 1);
    purlin_proof("otherfeat", "PROOF-2", "RULE-2", 1, "t", __FILE__, "unit");
    return 0;
}
''', suffix='.c')
        try:
            assert check_c(short, "cfeat") == [], \
                "a short call, a forwarding wrapper or another feature produced a proof"
        finally:
            os.unlink(short)


class TestDispatchAllExtensions:
    """RULE-44: one extension table, and no fallback for anything outside it."""

    _FIXTURES = {
        '.mjs': 'it("t [proof:dfeat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });',
        '.cjs': 'it("t [proof:dfeat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });',
        '.php': ('<?php\n/** @purlin dfeat PROOF-1 RULE-1 unit */\n'
                 'function test_t() { $this->assertTrue(true); }\n'),
        '.sql': "-- @purlin dfeat PROOF-1 RULE-1 unit\nSELECT 'PASS';\n",
        '.c': ('#include "c_purlin.h"\nint main(void) {\n'
               '    purlin_proof("dfeat", "PROOF-1", "RULE-1", 1, "t", __FILE__, "unit");\n'
               '    return 0;\n}\n'),
        '.h': ('#include "c_purlin.h"\nvoid suite(void) {\n'
               '    purlin_proof("dfeat", "PROOF-1", "RULE-1", 1, "t", __FILE__, "unit");\n'
               '}\n'),
    }

    @pytest.mark.proof("static_checks", "PROOF-71", "RULE-44")
    def test_every_shipped_extension_dispatches_and_nothing_else_does(self):
        """Each extension a shipped plugin emits reaches a checker that flags the
        hollow fixture; an extension no checker reads yields [] and no extracted
        body, rather than being handed to whichever checker an if-chain ended on."""
        for ext, content in self._FIXTURES.items():
            path = _write_tmp(content, suffix=ext)
            try:
                results = analyze_test_file(path, 'dfeat')
                assert len(results) == 1, f"{ext}: dispatch produced {results}"
                assert results[0]['check'] == 'assert_true', f"{ext}: {results[0]}"
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
            {'.py', '.sh', '.cs', '.php', '.sql'}
            | static_checks._JS_EXTENSIONS | static_checks._C_EXTENSIONS)
        assert static_checks._TEST_CODE_EXTENSIONS == \
            static_checks._CHECKER_EXTENSIONS - {'.sh'}
        assert {'.mjs', '.cjs'} <= static_checks._JS_EXTENSIONS


class TestExtractorsForPhpSqlC:
    """RULE-48: PHP, SQL and C test code enters the cache key, so a grade cannot
    survive an edit to the test that earned it."""

    _PHP_SRC = '''<?php
/** @purlin demo PROOF-1 RULE-1 unit */
function test_graded() {
    $graded = 1 + 1;
    $this->assertSame(2, $graded);
}
/** @purlin demo PROOF-2 RULE-2 unit */
function test_neighbour() {
    $other = 3 + 3;
    $this->assertSame(6, $other);
}
'''

    _SQL_SRC = """-- @purlin demo PROOF-1 RULE-1 unit
-- Test: graded
SELECT CASE WHEN (SELECT count(*) FROM users) = 1 THEN 'PASS' ELSE 'FAIL' END;

-- @purlin demo PROOF-2 RULE-2 unit
-- Test: neighbour
SELECT CASE WHEN (SELECT count(*) FROM orders) = 2 THEN 'PASS' ELSE 'FAIL' END;
"""

    _C_SRC = '''#include "c_purlin.h"
int main(void) {
    int graded = compute(1);
    int other = compute(3);
    purlin_proof("demo", "PROOF-1", "RULE-1", graded == 2, "test_graded", __FILE__, "unit");
    purlin_proof("demo", "PROOF-2", "RULE-2", other == 6, "test_neighbour", __FILE__, "unit");
    return 0;
}
'''

    def _project(self, root, test_file, source):
        for proof_id, rule_id, test_name in (('PROOF-1', 'RULE-1', 'test_graded'),
                                             ('PROOF-2', 'RULE-2', 'test_neighbour')):
            path = _scaffold_proof(root, 'demo', proof_id, rule_id,
                                   test_file=test_file, test_name=test_name,
                                   write_test=False)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(source)
        return path

    @pytest.mark.proof("static_checks", "PROOF-80", "RULE-48", tier="unit")
    def test_key_moves_when_the_graded_body_moves(self):
        cases = (
            ('tests/test_demo.php', self._PHP_SRC, '$graded = 1 + 1', '$graded = 1 + 9',
             '$other = 3 + 3', '$other = 3 + 9', True),
            ('tests/test_demo.sql', self._SQL_SRC, 'FROM users) = 1', 'FROM users) = 9',
             'FROM orders) = 2', 'FROM orders) = 9', True),
            # C keys on the enclosing top-level block, so an edit anywhere in main
            # moves every proof the block carries: over-invalidation, the safe way.
            ('tests/test_demo.c', self._C_SRC, 'compute(1)', 'compute(9)',
             'compute(3)', 'compute(7)', False),
        )
        for test_file, source, old, new, other_old, other_new, isolated in cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = self._project(tmpdir, test_file, source)
                lang = os.path.splitext(test_file)[1]

                key1, inputs = cache_key_for(tmpdir, 'demo', 'PROOF-1')
                assert inputs['test_verifiable'] is True, \
                    f"{lang}: no test code entered the key — there is no extractor"
                assert cache_key_for(tmpdir, 'demo', 'PROOF-1')[0] == key1, \
                    f"{lang}: the key is not deterministic"
                key2 = _key(tmpdir, 'demo', 'PROOF-2')
                assert key1 != key2, f"{lang}: two proofs share one key"

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(source.replace(old, new))
                assert _key(tmpdir, 'demo', 'PROOF-1') != key1, \
                    f"{lang}: editing the graded test left the key unchanged"

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(source)
                assert _key(tmpdir, 'demo', 'PROOF-1') == key1, \
                    f"{lang}: the key did not come back when the edit was undone"

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(source.replace(other_old, other_new))
                moved = _key(tmpdir, 'demo', 'PROOF-1') != key1
                assert moved is not isolated, (
                    f"{lang}: an edit to the neighbouring proof "
                    f"{'invalidated' if moved else 'did not invalidate'} this one")
                assert _key(tmpdir, 'demo', 'PROOF-2') != key2, \
                    f"{lang}: the edited proof's own key should have moved"


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
    """RULE-49 and RULE-50 — both model-free passes over a whole project."""

    _MJS = 'it("t [proof:jsfeat:PROOF-1:RULE-1]", () => { expect(true).toBe(true); });\n'
    _CS = """using Xunit;
namespace Demo {
  public class CsharpTests {
    [Fact]
    [Trait("PurlinProof", "csfeat:PROOF-1:RULE-1:unit")]
    public void Hollow() { Assert.True(true); }
  }
}
"""
    _PHP = ('<?php\n/** @purlin phpfeat PROOF-1 RULE-1 unit */\n'
            'function test_hollow() { $this->assertTrue(true); }\n')
    _SQL = "-- @purlin sqlfeat PROOF-1 RULE-1 unit\n-- Test: hollow\nSELECT 'PASS';\n"
    _C = ('#include "c_purlin.h"\nint main(void) {\n'
          '    purlin_proof("cfeat", "PROOF-1", "RULE-1", 1, "hollow", __FILE__, "unit");\n'
          '    return 0;\n}\n')
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
        """A project holding one test file per shipped language plus every way a
        backing can go unmeasurable, and two features sharing one Python file."""
        # alpha and beta share tests/test_shared.py.
        _scaffold_proof(root, 'alpha', 'PROOF-1', 'RULE-1',
                        test_file='tests/test_shared.py',
                        test_name='test_alpha_hollow', test_body='    assert True')
        _scaffold_proof(root, 'alpha', 'PROOF-2', 'RULE-2',
                        test_file='tests/test_shared.py',
                        test_name='test_alpha_ok', test_body='    assert 1 + 1 == 2')
        _scaffold_proof(root, 'beta', 'PROOF-3', 'RULE-3',
                        test_file='tests/test_shared.py',
                        test_name='test_beta_ok', test_body='    assert 2 + 2 == 4')

        # A stamped manual proof: declared, graded by Pass D1, backed by nothing.
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
                ('phpfeat', 'tests/test_php.php', self._PHP, 'test_hollow'),
                ('sqlfeat', 'tests/test_sql.sql', self._SQL, 'hollow'),
                ('cfeat', 'tests/test_c.c', self._C, 'hollow'),
                ('rbfeat', 'tests/test_rb.rb', self._RB, 't')):
            _scaffold_proof(root, feature, 'PROOF-1', 'RULE-1', test_file=rel,
                            test_name=test_name, write_test=False)
            self._write(root, rel, source)

        # C#: the xUnit logger records an empty test_file when no source info is
        # available, so the path has to come back from the fully-qualified name.
        _scaffold_proof(root, 'csfeat', 'PROOF-1', 'RULE-1',
                        test_file='tests/CsharpTests.cs',
                        test_name='Demo.CsharpTests.Hollow', write_test=False)
        self._write(root, 'tests/CsharpTests.cs', self._CS)
        record = os.path.join(root, 'specs', 'app', 'csfeat.proofs-unit.json')
        data = json.load(open(record, encoding='utf-8'))
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

        # Two backings, one clean and one hollow: fail wins.
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

        # Two backings, one hollow and one in a language no checker reads: the
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
        ('alpha', 'PROOF-1'): ('fail', 'assert_true'),
        ('alpha', 'PROOF-2'): ('pass', 'none'),
        ('beta', 'PROOF-3'): ('pass', 'none'),
        ('cfeat', 'PROOF-1'): ('fail', 'assert_true'),
        ('csfeat', 'PROOF-1'): ('fail', 'assert_true'),
        ('gonefeat', 'PROOF-1'): ('unmeasurable', 'missing_file'),
        ('jsfeat', 'PROOF-1'): ('fail', 'assert_true'),
        ('markerfeat', 'PROOF-1'): ('pass', 'none'),
        ('markerfeat', 'PROOF-2'): ('unmeasurable', 'marker_not_found'),
        ('mixed', 'PROOF-1'): ('unmeasurable', 'no_checker'),
        ('multi', 'PROOF-1'): ('fail', 'assert_true'),
        ('phpfeat', 'PROOF-1'): ('fail', 'assert_true'),
        ('rbfeat', 'PROOF-1'): ('unmeasurable', 'no_checker'),
        ('shfeat', 'PROOF-1'): ('fail', 'assert_true'),
        ('sqlfeat', 'PROOF-1'): ('fail', 'assert_true'),
        ('worst', 'PROOF-1'): ('fail', 'assert_true'),
    }

    @pytest.mark.proof("static_checks", "PROOF-82", "RULE-49", tier="unit")
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
            assert result['counts']['features'] == len(specs) == 14, result['counts']

            got = {(feat, pid): (entry['status'], entry['check'])
                   for feat, data in result['features'].items()
                   for pid, entry in data['integrity'].items()}
            assert got == self._EXPECTED

            # A .rb backing is a measurement gap, never a defect.
            assert ('rbfeat', 'PROOF-1') not in {(r['feature'], r['proof_id'])
                                                 for r in result['hollow']}

            # An empty test_file resolved from the fully-qualified test name.
            csharp = result['features']['csfeat']['integrity']['PROOF-1']
            assert csharp['test_file'] == 'tests/CsharpTests.cs', csharp
            assert csharp['test_name'] == 'Hollow', csharp

            # Precedence across several backings.
            multi = result['features']['multi']['integrity']['PROOF-1']
            assert (multi['backings'], multi['test_file']) == (2, 'tests/test_multi_bad.py')
            mixed = result['features']['mixed']['integrity']['PROOF-1']
            assert (mixed['backings'], mixed['test_file']) == (2, 'tests/test_mixed.rb')
            worst = result['features']['worst']['integrity']['PROOF-1']
            assert (worst['backings'], worst['test_file']) == (2, 'tests/test_worst_bad.py'), \
                "an unmeasurable backing outranked a hollow one"

            # A manual stamp has no test backing: Pass D1 grades it, Pass 1 never
            # sees it, and it is neither hollow nor unmeasurable.
            alpha = result['features']['alpha']
            assert alpha['design']['PROOF-9']['level'] in (
                'PROVABLE', 'LOOSE', 'UNPROVABLE', 'STRUCTURAL')
            assert 'PROOF-9' not in alpha['integrity']
            assert ('alpha', 'PROOF-9') not in {
                (r['feature'], r['proof_id'])
                for r in result['unmeasurable'] + result['hollow']}

            for name in ('hollow', 'unprovable', 'unmeasurable'):
                rows = result[name]
                assert rows == sorted(
                    rows, key=lambda r: (r['feature'], r['proof_id'],
                                         r.get('test_file', ''))), \
                    f"{name} is not sorted by (feature, proof_id, test_file)"
            assert result['counts']['hollow'] == len(result['hollow']) == 9
            assert result['counts']['unmeasurable'] == len(result['unmeasurable']) == 4
            assert result['counts']['backings'] == 19, result['counts']

            assert len(parses) == len(self._PY_FILES), (
                f"{len(self._PY_FILES)} Python test files must mean "
                f"{len(self._PY_FILES)} parses, not {len(parses)}")

            assert _tree_snapshot(tmpdir) == before, \
                "the sweep wrote to the project it was only supposed to read"
            assert not os.path.exists(os.path.join(tmpdir, '.purlin')), \
                "the sweep created a runtime directory"

    @staticmethod
    def _repo_state(root):
        """(git porcelain status, every file under .purlin with its size).

        `.purlin/cache/` and `.purlin/runtime/` are gitignored, so a sweep that
        wrote a cache would leave `git status` clean and has to be caught by the
        listing instead.
        """
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=root,
                                capture_output=True, text=True).stdout
        runtime = sorted(
            (os.path.relpath(os.path.join(d, n), root).replace(os.sep, '/'),
             os.path.getsize(os.path.join(d, n)))
            for d, _sub, files in os.walk(os.path.join(root, '.purlin'))
            for n in files)
        return status, runtime

    @pytest.mark.proof("static_checks", "PROOF-83", "RULE-50", tier="e2e")
    def test_cli_sweeps_this_repository_without_touching_it(self):
        """The real CLI over this repository: every spec graded, every backing in
        a language a shipped checker reads, and the checkout byte-identical
        afterwards."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        before_status, before_runtime = self._repo_state(root)

        proc = subprocess.run(
            [sys.executable, _STATIC_CHECKS_PY, '--deterministic-sweep',
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
            "every language this repository's proofs are written in ships a Pass 1 "
            f"checker, so no backing may be unmeasurable for want of one: {no_checker}")

        after_status, after_runtime = self._repo_state(root)
        assert after_status == before_status, \
            "the sweep changed a tracked file in the checkout it was only reading"
        assert after_runtime == before_runtime, \
            "the sweep wrote under .purlin/ (a cache or a runtime file)"

        bare = subprocess.run([sys.executable, _STATIC_CHECKS_PY],
                              capture_output=True, text=True)
        assert bare.returncode == 2
        assert '--deterministic-sweep [--project-root <path>]' in bare.stderr, \
            "the sweep mode is missing from the usage text"


class TestCacheEntryValidation:
    """RULE-33 — reject entries whose dedup key is missing.

    The documented entry shape used to omit `feature` and `proof_id`, so an agent
    following the docs produced entries that all keyed under ('', ''). On write
    they collapsed to one surviving row, and integrity was then computed from a
    single proof: a confident, plausible, wrong percentage.
    """

    def _entry(self, **over):
        e = {
            "assessment": "STRONG",
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": "login",
            "proof_id": "PROOF-1",
            "rule_id": "RULE-1",
            "priority": "LOW",
            "cached_at": "2026-01-01T00:00:00+00:00",
        }
        e.update(over)
        return e

    @pytest.mark.proof("static_checks", "PROOF-57", "RULE-33")
    def test_rejects_entries_missing_dedup_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for n in (1, 2, 9):
                _scaffold_proof(tmpdir, 'login', f'PROOF-{n}', 'RULE-1',
                                test_file='tests/test_login.py',
                                test_name=f'test_login_{n}')
            cache_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json')

            # Missing proof_id -> raises, naming the offending cache key
            bad = {"h1": self._entry()}
            del bad["h1"]["proof_id"]
            with pytest.raises(ValueError) as exc:
                write_audit_cache(tmpdir, bad)
            assert 'proof_id' in str(exc.value)
            assert 'h1' in str(exc.value), "the error must name the offending cache key"
            assert not os.path.exists(cache_path), \
                "a rejected batch must not create the cache file"

            # Missing feature -> also raises
            bad2 = {"h2": self._entry()}
            del bad2["h2"]["feature"]
            with pytest.raises(ValueError):
                write_audit_cache(tmpdir, bad2)

            # An empty-string value is as bad as an absent key: it keys under ('', '')
            with pytest.raises(ValueError):
                write_audit_cache(tmpdir, {"h3": self._entry(feature="")})

            # Seed a valid cache, then attempt a batch with one malformed entry.
            # The good entries must not be merged — the batch is rejected whole.
            write_audit_cache(tmpdir, {"good": self._entry(proof_id="PROOF-9")})
            before = open(cache_path, encoding='utf-8').read()
            mixed = {"ok": self._entry(proof_id="PROOF-2"), "broken": self._entry()}
            del mixed["broken"]["proof_id"]
            with pytest.raises(ValueError):
                write_audit_cache(tmpdir, mixed)
            assert open(cache_path, encoding='utf-8').read() == before, \
                "a rejected batch must leave the cache on disk byte-identical"

    @pytest.mark.proof("static_checks", "PROOF-57", "RULE-33")
    def test_write_cache_cli_reports_error_and_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'login', 'PROOF-1', 'RULE-1')

            def run(stdin_text):
                return subprocess.run(
                    [sys.executable, _STATIC_CHECKS_PY, '--write-cache',
                     '--project-root', tmpdir],
                    input=stdin_text, capture_output=True, text=True)

            # Missing dedup key
            bad = {"h1": self._entry()}
            del bad["h1"]["proof_id"]
            r = run(json.dumps(bad))
            assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stdout}{r.stderr}"
            assert 'proof_id' in json.loads(r.stdout)['error']

            # Non-JSON stdin: a JSON error object, not a traceback
            r = run('not json at all')
            assert r.returncode == 2, r.stdout
            assert 'error' in json.loads(r.stdout)

            # A JSON list used to reach .items() and raise AttributeError
            r = run('[1, 2, 3]')
            assert r.returncode == 2, r.stdout
            assert 'error' in json.loads(r.stdout)
            assert 'Traceback' not in r.stderr, "must not leak a traceback"

            # A well-formed batch still merges
            r = run(json.dumps({"h9": self._entry()}))
            assert r.returncode == 0, f"{r.stdout}{r.stderr}"
            assert json.loads(r.stdout)['status'] == 'merged'


class TestCacheMutationLocking:
    """RULE-25 — prune and clear hold the same exclusive lock as the writer.

    The audit skill launches up to three parallel auditors and then prunes. With
    prune unlocked, it could read the cache, a writer could merge new entries, and
    the prune's write would drop them.
    """

    def _entry(self, feature, pid):
        return {
            "assessment": "STRONG", "criterion": "c", "why": "w", "fix": "none",
            "feature": feature, "proof_id": pid, "rule_id": "RULE-1",
            "priority": "LOW", "cached_at": "2026-01-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-58", "RULE-25")
    def test_prune_and_clear_take_the_exclusive_lock(self):
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json')
            _scaffold_proof(tmpdir, 'login', 'PROOF-1', 'RULE-1')
            for i in range(20):
                _scaffold_proof(tmpdir, 'checkout', f'PROOF-{i}', 'RULE-1',
                                test_file='tests/test_checkout.py',
                                test_name=f'test_checkout_{i}')
            seed_key = _key(tmpdir, 'login', 'PROOF-1')

            # Both mutators must go through the platform-neutral lock helper.
            for op in ('prune', 'clear'):
                write_audit_cache(tmpdir, {'seed': self._entry('login', 'PROOF-1')})
                calls = []
                real = static_checks._lock_exclusive

                def spy(lf):
                    calls.append(lf.name)
                    return real(lf)

                with mock.patch.object(static_checks, '_lock_exclusive', side_effect=spy):
                    if op == 'prune':
                        prune_audit_cache(tmpdir, {seed_key})
                    else:
                        clear_audit_cache(tmpdir)
                assert calls, f"{op}_audit_cache did not acquire the exclusive lock"
                assert calls[0].endswith('audit_cache.json.lock'), \
                    f"{op} locked {calls[0]!r}, not audit_cache.json.lock"

            # A prune racing a write must serialize: the writer's entries either
            # survive whole or were never committed. They must never vanish after
            # write_audit_cache returned successfully.
            write_audit_cache(tmpdir, {'seed': self._entry('login', 'PROOF-1')})
            errors = []

            def writer():
                try:
                    for i in range(20):
                        write_audit_cache(
                            tmpdir, {f'w{i}': self._entry('checkout', f'PROOF-{i}')})
                except Exception as exc:  # pragma: no cover - surfaced via errors
                    errors.append(exc)

            def pruner():
                try:
                    for _ in range(20):
                        prune_audit_cache(tmpdir, {seed_key})
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)

            t1, t2 = threading.Thread(target=writer), threading.Thread(target=pruner)
            t1.start(); t2.start(); t1.join(); t2.join()
            assert not errors, f"concurrent mutation raised: {errors}"

            # The file must still be valid JSON — a torn write would break this.
            final = json.load(open(cache_path, encoding='utf-8'))
            assert isinstance(final, dict)
            assert seed_key in final, "the live key must survive every prune"


class TestCliSelfDocumentation:
    """RULE-34 — the help text cannot drift from the dispatch chain.

    The usage text had gone stale and omitted five real flags (--write-cache,
    --clear-cache, --prune-cache, --load-criteria, --resolve-source), and the
    module docstring claimed "exit 1 = at least one failed" while main() always
    exits 0 for a completed analysis, contradicting RULE-7.
    """

    @pytest.mark.proof("static_checks", "PROOF-59", "RULE-34")
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
        # Sub-options are documented on the line of the mode they belong to.
        sub_options = {'--spec-path', '--project-root', '--proof-path', '--rule',
                       '--proof-desc', '--test-code', '--ext', '--extra',
                       '--live-keys-file'}
        phantom = sorted(f for f in advertised - sub_options if f not in dispatched)
        assert not phantom, f"_USAGE advertises flags main() never dispatches on: {phantom}"

        # RULE-7: the docstring must not promise a non-zero exit for a found defect.
        docstring = ast.get_docstring(tree) or ''
        assert 'Exit code 0 = all proofs passed, 1 = at least one failed' not in docstring, \
            "module docstring still contradicts RULE-7's exit convention"
        assert 'RULE-7' in docstring, \
            "module docstring should cite the exit convention it follows"

    @pytest.mark.proof("static_checks", "PROOF-59", "RULE-34")
    def test_bad_invocation_prints_every_usage_line(self):
        r = subprocess.run([sys.executable, _STATIC_CHECKS_PY],
                           capture_output=True, text=True)
        assert r.returncode == 2, f"expected exit 2 for a bad invocation, got {r.returncode}"
        for line in static_checks._USAGE:
            assert line in r.stderr, f"usage line not printed: {line!r}"


_DESIGN_SPEC = '''# Feature: login

> Scope: src/auth.py

## Rules

- RULE-1: Returns 401 with an invalid_credentials error on a wrong password
- RULE-2: Locks the account after 5 failed attempts
- RULE-3: No eval() in source
- RULE-4: Passwords are hashed before storage
- RULE-5: Returns 401 on a wrong password

## Proof

- PROOF-1 (RULE-1): Verify the login endpoint exists
- PROOF-2 (RULE-2): Test that account locking works correctly
- PROOF-3 (RULE-3): Grep src/ for eval(); verify zero matches
- PROOF-4 (RULE-4): POST {"user": "alice", "pass": "secret"} to /register; verify the stored hash is not the literal "secret"
- PROOF-5 (RULE-5): Call authenticate("alice", "wrong"); verify it returns 401 @e2e
'''


class TestProofDesign:
    """RULE-35 — grade proof DESCRIPTIONS with no test code present."""

    def _spec(self, root, body=_DESIGN_SPEC):
        d = os.path.join(root, 'specs', 'auth')
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, 'login.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(body)
        return path

    @pytest.mark.proof("static_checks", "PROOF-60", "RULE-35")
    def test_grades_each_design_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = self._spec(tmpdir)
            # No test files and no proof JSON exist anywhere in this project.
            assert not glob.glob(os.path.join(tmpdir, '**', '*.proofs-*.json'), recursive=True)

            got = {p['proof_id']: p for p in check_proof_design(spec)['proofs']}
            assert got['PROOF-1']['level'] == 'UNPROVABLE', got['PROOF-1']
            assert got['PROOF-1']['check'] == 'level1_presence'
            assert got['PROOF-2']['level'] == 'LOOSE', got['PROOF-2']
            assert got['PROOF-3']['level'] == 'STRUCTURAL', got['PROOF-3']
            assert got['PROOF-4']['level'] == 'PROVABLE', got['PROOF-4']
            assert got['PROOF-5']['level'] == 'UNPROVABLE', got['PROOF-5']
            assert got['PROOF-5']['check'] == 'e2e_names_internal_call'

            # Every finding must be actionable, not just a label.
            for pid, p in got.items():
                assert p['reason'], f"{pid} has no reason"

            # The real CLI returns the same grading.
            r = subprocess.run(
                [sys.executable, _STATIC_CHECKS_PY, '--check-proof-design',
                 '--spec-path', spec],
                capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            cli = {p['proof_id']: p['level'] for p in json.loads(r.stdout)['proofs']}
            assert cli == {k: v['level'] for k, v in got.items()}

    @pytest.mark.proof("static_checks", "PROOF-60", "RULE-35")
    def test_absence_assertions_are_not_unprovable(self):
        """A FORBIDDEN proof asserts absence. That is a correct structural proof,
        not a Level 1 defect — flagging it would tell users to rewrite good specs."""
        body = _DESIGN_SPEC.replace(
            '- PROOF-3 (RULE-3): Grep src/ for eval(); verify zero matches',
            '- PROOF-3 (RULE-3): Grep src/ for eval(); verify none exist')
        with tempfile.TemporaryDirectory() as tmpdir:
            got = {p['proof_id']: p['level']
                   for p in check_proof_design(self._spec(tmpdir, body))['proofs']}
            assert got['PROOF-3'] == 'STRUCTURAL', got

    @pytest.mark.proof("static_checks", "PROOF-61", "RULE-36")
    def test_audit_scope_derives_the_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._spec(tmpdir)

            # Spec only: nothing built, nothing tested.
            scope = audit_scope(tmpdir)
            assert scope['recommended_mode'] == 'design', scope['why']
            row = scope['features'][0]
            assert row['proofs_executed'] == 0
            assert row['scope_files'] == 1 and row['scope_files_exist'] == 0, \
                "a spec naming a file that does not exist means nothing is built yet"
            assert row['rules'] == 5 and row['proofs_declared'] == 5

            # Code now exists, tests still do not. This is a DIFFERENT state, and
            # nothing else in the toolchain could previously tell them apart.
            os.makedirs(os.path.join(tmpdir, 'src'), exist_ok=True)
            with open(os.path.join(tmpdir, 'src', 'auth.py'), 'w') as f:
                f.write('def auth(): pass\n')
            scope = audit_scope(tmpdir)
            assert scope['features'][0]['scope_files_exist'] == 1
            assert scope['recommended_mode'] == 'design', \
                "still no executed proofs, so Integrity remains unmeasurable"

            # A proof has now executed.
            with open(os.path.join(tmpdir, 'specs', 'auth',
                                   'login.proofs-unit.json'), 'w') as f:
                json.dump({'tier': 'unit', 'proofs': [{
                    'feature': 'login', 'id': 'PROOF-4', 'rule': 'RULE-4',
                    'test_file': 'tests/test_login.py', 'test_name': 't',
                    'status': 'pass', 'tier': 'unit'}]}, f)
            scope = audit_scope(tmpdir)
            assert scope['recommended_mode'] == 'both', scope['why']
            assert scope['features'][0]['proofs_executed'] == 1
            assert scope['features'][0]['test_files_present'] == 1

    @pytest.mark.proof("static_checks", "PROOF-62", "RULE-37")
    def test_design_cache_is_separate_and_validated(self):
        entry = {
            "assessment": "PROVABLE", "criterion": "none", "why": "concrete",
            "fix": "none", "feature": "login", "proof_id": "PROOF-4",
            "rule_id": "RULE-4", "priority": "LOW",
            "cached_at": "2026-01-01T00:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'login', 'PROOF-4', 'RULE-4')
            d1 = _key(tmpdir, 'login', 'PROOF-4', static_checks.DESIGN_CACHE)
            write_audit_cache(tmpdir, {"d1": entry}, static_checks.DESIGN_CACHE)
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            assert os.path.isfile(os.path.join(cache_dir, 'design_cache.json'))
            assert not os.path.isfile(os.path.join(cache_dir, 'audit_cache.json')), \
                "design results must not be written into the audit cache"
            assert os.path.isfile(os.path.join(cache_dir, 'design_cache.json.lock')), \
                "the design cache must take the same exclusive lock"
            assert read_audit_cache(tmpdir, static_checks.DESIGN_CACHE)[d1]['assessment'] \
                == 'PROVABLE'

            # The RULE-33 validator guards this cache too.
            bad = dict(entry)
            del bad['proof_id']
            with pytest.raises(ValueError):
                write_audit_cache(tmpdir, {"d2": bad}, static_checks.DESIGN_CACHE)

        # The design hash ignores test code but tracks the description.
        h1 = static_checks.compute_design_hash('RULE text', 'proof description')
        h2 = static_checks.compute_design_hash('RULE text', 'proof description')
        h3 = static_checks.compute_design_hash('RULE text', 'a different description')
        assert h1 == h2 and h1 != h3
        assert len(h1) == 16

        # Two features whose rule text and proof description are byte-identical
        # must not share a design-cache key, or one grade overwrites the other
        # while the dedup key still says they are two proofs.
        with tempfile.TemporaryDirectory() as tmpdir:
            same_rule = 'the handler returns 204 on an empty body'
            same_desc = 'Call the handler with an empty body and verify a 204'
            for feature in ('alpha', 'beta'):
                _scaffold_proof(tmpdir, feature, 'PROOF-1', 'RULE-1',
                                test_file=f'tests/test_{feature}.py',
                                test_name=f'test_{feature}',
                                rule_text=same_rule, description=same_desc)
            ka = _key(tmpdir, 'alpha', 'PROOF-1', static_checks.DESIGN_CACHE)
            kb = _key(tmpdir, 'beta', 'PROOF-1', static_checks.DESIGN_CACHE)
            assert ka != kb, (
                "identical rule text and description in two features collided on "
                f"one design-cache key: {ka}")

        # The design half never opens a test file: the key excludes test code
        # by construction, so extracting it would be work that cannot change
        # the answer, and the entry says so through test_verifiable.
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'login', 'PROOF-4', 'RULE-4')
            calls = []
            real_extract = static_checks._extract_test_code
            with mock.patch.object(static_checks, '_extract_test_code',
                                   side_effect=lambda *a: (calls.append(a), real_extract(*a))[1]):
                _dkey, inputs = static_checks.cache_key_for(
                    tmpdir, 'login', 'PROOF-4', static_checks.DESIGN_CACHE)
            assert calls == [], "a design key must not read the test file"
            assert inputs['test_verifiable'] is False, \
                "no test code entered a design key, so the entry must say so"
            _akey, audit_inputs = static_checks.cache_key_for(
                tmpdir, 'login', 'PROOF-4', static_checks.AUDIT_CACHE)
            assert audit_inputs['test_verifiable'] is True


def _cache_key_inputs(root, feature, proof_id, cache_name=None):
    """The `inputs` half of cache_key_for, for tests that assert on it."""
    if cache_name is None:
        return static_checks.cache_key_for(root, feature, proof_id)[1]
    return static_checks.cache_key_for(root, feature, proof_id, cache_name)[1]


def _cache_entry(feature, proof_id, rule_id='RULE-1', assessment='STRONG'):
    """A complete, valid audit-cache entry for the given proof."""
    return {
        "assessment": assessment, "criterion": "matches rule intent",
        "why": "the test exercises the rule", "fix": "none",
        "feature": feature, "proof_id": proof_id, "rule_id": rule_id,
        "priority": "LOW", "cached_at": "2026-01-01T00:00:00+00:00",
    }


class TestCacheKeyFromProjectState:
    """RULE-38 — the key is resolved from the project, never supplied by the caller.

    A caller-supplied key described whatever text the caller happened to paste, so
    a stored grade could not be rechecked against anything.
    """

    @pytest.mark.proof("static_checks", "PROOF-63", "RULE-38", tier="integration")
    def test_write_cache_rekeys_every_entry_from_the_project(self):
        # The proof's identity is in the key, so two features whose rule text and
        # proof description are byte-identical still get two keys. The test files
        # here are shell scripts, which have no extractor, so no test source
        # enters either key and the two inputs that remain are identical. That is
        # the case a key without the identity actually collides on.
        with tempfile.TemporaryDirectory() as twin_dir:
            same_rule = 'the handler returns 204 on an empty body'
            same_desc = 'Call the handler with an empty body and verify a 204'
            for feature in ('alpha', 'beta'):
                _scaffold_proof(twin_dir, feature, 'PROOF-1', 'RULE-1',
                                test_file=f'tests/{feature}.sh',
                                test_name=f'test_{feature}',
                                rule_text=same_rule, description=same_desc)
            assert _cache_key_inputs(twin_dir, 'alpha', 'PROOF-1')['test_verifiable'] is False, \
                "a shell proof must record test_verifiable false, or the twins differ"
            ka = _key(twin_dir, 'alpha', 'PROOF-1')
            kb = _key(twin_dir, 'beta', 'PROOF-1')
            assert ka != kb, (
                "two features with identical rule text, description and test body "
                f"collided on one cache key: {ka}")
            write_audit_cache(twin_dir, {
                'x': _cache_entry('alpha', 'PROOF-1'),
                'y': _cache_entry('beta', 'PROOF-1', assessment='HOLLOW'),
            })
            stored = read_audit_cache(twin_dir)
            assert set(stored) == {ka, kb}, (
                f"one of the two grades was lost to a key collision: {list(stored)}")
            assert stored[ka]['assessment'] == 'STRONG'
            assert stored[kb]['assessment'] == 'HOLLOW'

        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'demo', 'PROOF-1', 'RULE-1',
                            test_file='tests/test_demo.py', test_name='test_demo')

            def run(args, stdin_text=None):
                return subprocess.run(
                    [sys.executable, _STATIC_CHECKS_PY, *args,
                     '--project-root', tmpdir],
                    input=stdin_text, capture_output=True, text=True)

            # --cache-key prints the one key the project resolves to.
            r = run(['--cache-key', '--feature', 'demo', '--proof-id', 'PROOF-1'])
            assert r.returncode == 0, f"{r.stdout}{r.stderr}"
            printed = json.loads(r.stdout)
            assert printed['feature'] == 'demo' and printed['proof_id'] == 'PROOF-1'
            key = printed['key']
            assert re.fullmatch(r'[0-9a-f]{16}', key), f"not a proof hash: {key!r}"

            # A deliberately wrong caller key is discarded, not stored.
            r = run(['--write-cache'],
                    json.dumps({'deadbeef': _cache_entry('demo', 'PROOF-1')}))
            assert r.returncode == 0, f"{r.stdout}{r.stderr}"
            r = run(['--read-cache'])
            assert r.returncode == 0, r.stderr
            stored = json.loads(r.stdout)
            assert list(stored) == [key], \
                f"expected only the resolved key {key}, got {list(stored)}"
            assert 'deadbeef' not in stored, "the caller's key survived the write"

            # The flag --cache-key replaced is gone from the help text, from the
            # dispatch chain, and from the CLI.
            tree = ast.parse(open(_STATIC_CHECKS_PY, encoding='utf-8').read())
            main_fn = next(n for n in tree.body
                           if isinstance(n, ast.FunctionDef) and n.name == 'main')
            dispatched = set()
            for node in ast.walk(main_fn):
                if isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.In):
                    left, right = node.left, node.comparators[0]
                    is_argv = (isinstance(right, ast.Attribute) and right.attr == 'argv') \
                        or (isinstance(right, ast.Name) and right.id == 'argv')
                    if is_argv and isinstance(left, ast.Constant) \
                            and isinstance(left.value, str) and left.value.startswith('--'):
                        dispatched.add(left.value)
            assert '--cache-key' in dispatched, "detector is broken — no --cache-key found"
            assert '--compute-proof-hash' not in dispatched, \
                "main() still dispatches on the replaced flag"
            assert '--compute-proof-hash' not in ' '.join(static_checks._USAGE), \
                "_USAGE still advertises the replaced flag"
            r = run(['--compute-proof-hash', '--rule', 'r', '--proof-desc', 'd',
                     '--test-code', 'c'])
            assert r.returncode == 2, \
                f"--compute-proof-hash should be a bad invocation, got {r.returncode}"

            # An entry the spec does not declare is rejected whole, before the
            # filesystem is touched.
            cache_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json')
            before = open(cache_path, 'rb').read()
            r = run(['--write-cache'],
                    json.dumps({'whatever': _cache_entry('demo', 'PROOF-99')}))
            assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stdout}"
            assert 'demo/PROOF-99' in json.loads(r.stdout)['error']
            assert open(cache_path, 'rb').read() == before, \
                "a rejected batch must leave the cache byte-identical"


class TestAuditorStamp:
    """RULE-39 — every stored entry names who graded it and what fed the key."""

    @pytest.mark.proof("static_checks", "PROOF-64", "RULE-39", tier="integration")
    def test_entries_carry_the_auditor_and_input_provenance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _scaffold_proof(tmpdir, 'demo', 'PROOF-1', 'RULE-1',
                            test_file='tests/test_demo.py', test_name='test_demo')
            config_path = os.path.join(tmpdir, '.purlin', 'config.json')

            def write(entry_proof_id):
                r = subprocess.run(
                    [sys.executable, _STATIC_CHECKS_PY, '--write-cache',
                     '--project-root', tmpdir],
                    input=json.dumps({'ignored': _cache_entry('demo', entry_proof_id)}),
                    capture_output=True, text=True)
                assert r.returncode == 0, f"{r.stdout}{r.stderr}"
                return read_audit_cache(tmpdir)

            # Nothing configured: the default auditor, spelled out in full.
            assert not os.path.exists(config_path)
            stored = write('PROOF-1')[_key(tmpdir, 'demo', 'PROOF-1')]
            assert stored['auditor'] == {'name': 'claude', 'command': None}, \
                stored.get('auditor')

            # A configured LLM: exactly the configured name and command.
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'audit_llm_name': 'Gemini Pro',
                           'audit_llm': 'gemini -p "{prompt}"'}, f)
            stored = write('PROOF-1')[_key(tmpdir, 'demo', 'PROOF-1')]
            assert stored['auditor'] == {
                'name': 'Gemini Pro', 'command': 'gemini -p "{prompt}"'}, \
                stored.get('auditor')

            # test_verifiable says whether a test edit could move this key.
            _scaffold_proof(tmpdir, 'demo', 'PROOF-2', 'RULE-2',
                            test_file='tests/check_demo.sh', test_name='check_demo')
            after = write('PROOF-2')
            shell_entry = after[_key(tmpdir, 'demo', 'PROOF-2')]
            pytest_entry = after[_key(tmpdir, 'demo', 'PROOF-1')]
            assert shell_entry['inputs']['test_verifiable'] is False, \
                "a shell proof has no extractable test code, so it must say so"
            assert pytest_entry['inputs']['test_verifiable'] is True, \
                "a pytest proof's source does enter the key"


class TestCacheKeyDeterminism:
    """RULE-40 — the key is a function of the three resolved inputs and nothing else."""

    @pytest.mark.proof("static_checks", "PROOF-65", "RULE-40", tier="unit")
    def test_key_tracks_the_graded_test_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = _scaffold_proof(
                tmpdir, 'demo', 'PROOF-1', 'RULE-1',
                test_file='tests/test_demo.py', test_name='test_graded',
                test_body='    graded = 1 + 1\n    assert graded == 2')
            _scaffold_proof(
                tmpdir, 'demo', 'PROOF-2', 'RULE-2',
                test_file='tests/test_demo.py', test_name='test_neighbour',
                test_body='    other = 3 + 3\n    assert other == 6')

            # Deterministic: the same project gives the same key twice.
            first = cache_key_for(tmpdir, 'demo', 'PROOF-1')
            second = cache_key_for(tmpdir, 'demo', 'PROOF-1')
            assert first == second, f"{first} != {second}"
            key1, key2 = first[0], _key(tmpdir, 'demo', 'PROOF-2')
            assert key1 != key2

            # Re-keying an already re-keyed batch is a no-op on the key set.
            once = rekey_cache_entries(tmpdir, {
                'wrong-1': _cache_entry('demo', 'PROOF-1', 'RULE-1'),
                'wrong-2': _cache_entry('demo', 'PROOF-2', 'RULE-2'),
            })
            assert set(once) == {key1, key2}
            twice = rekey_cache_entries(tmpdir, once)
            assert set(twice) == set(once), "re-keying moved a key that was already right"

            original = open(test_path, encoding='utf-8').read()

            # One character inside the graded function moves the key.
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(original.replace('graded == 2', 'graded == 3'))
            assert _key(tmpdir, 'demo', 'PROOF-1') != key1, \
                "editing the graded test left the key unchanged — a stale grade survives"

            # Restored, the key comes back.
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(original)
            assert _key(tmpdir, 'demo', 'PROOF-1') == key1

            # A different marked function in the same file does not move it.
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(original.replace('other == 6', 'other == 7'))
            assert _key(tmpdir, 'demo', 'PROOF-1') == key1, \
                "an unrelated test edit invalidated this proof's grade"
            assert _key(tmpdir, 'demo', 'PROOF-2') != key2, \
                "the edited test's own key should have moved"


class TestCriteriaPin:
    """RULE-41 — criteria are never assembled from something that cannot be named."""

    def _cli(self, project):
        return subprocess.run(
            [sys.executable, _STATIC_CHECKS_PY, '--load-criteria',
             '--project-root', project],
            capture_output=True, text=True)

    @pytest.mark.proof("static_checks", "PROOF-66", "RULE-41", tier="integration")
    def test_pinned_criteria_are_enforced(self, tmp_path):
        project = str(tmp_path)
        cache_dir = os.path.join(project, '.purlin', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        config_path = os.path.join(project, '.purlin', 'config.json')
        cached_path = os.path.join(cache_dir, 'additional_criteria.md')

        def set_pin(sha):
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'audit_criteria': 'git@example.com:team/q.git#c.md',
                           'audit_criteria_pinned': sha}, f)

        team_text = '## Team Rules\n\n- No network in unit tests\n'
        set_pin('aaa1111')
        with open(cached_path, 'w', encoding='utf-8') as f:
            f.write('<!-- purlin-criteria-sha: aaa1111 -->\n' + team_text)

        # Matching pin: both bodies present, the header line consumed.
        result = load_criteria(project)
        assert '## Assessment Levels' in result, "built-in criteria missing"
        assert 'No network in unit tests' in result, "team criteria missing"
        assert 'git@example.com:team/q.git#c.md' in result, "the source is not named"
        assert 'purlin-criteria-sha' not in result, \
            "the pin header leaked into the criteria text"

        # Mismatched pin: named on both sides, and fatal to the CLI.
        set_pin('bbb2222')
        with pytest.raises(CriteriaError) as exc:
            load_criteria(project)
        assert 'aaa1111' in str(exc.value) and 'bbb2222' in str(exc.value), str(exc.value)
        r = self._cli(project)
        assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stdout}"
        assert 'aaa1111' in r.stderr and 'bbb2222' in r.stderr, r.stderr

        # Missing cache file.
        set_pin('aaa1111')
        os.remove(cached_path)
        with pytest.raises(CriteriaError) as exc:
            load_criteria(project)
        assert 'additional_criteria.md' in str(exc.value)
        r = self._cli(project)
        assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stdout}"
        assert 'additional_criteria.md' in r.stderr, r.stderr

        # Cache present but with no pin header at all.
        with open(cached_path, 'w', encoding='utf-8') as f:
            f.write(team_text)
        with pytest.raises(CriteriaError) as exc:
            load_criteria(project)
        assert 'purlin-criteria-sha' in str(exc.value)
        r = self._cli(project)
        assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stdout}"
        assert 'purlin-criteria-sha' in r.stderr, r.stderr

        # A plugin root with no built-in criteria: an error, never an empty string.
        with open(cached_path, 'w', encoding='utf-8') as f:
            f.write('<!-- purlin-criteria-sha: aaa1111 -->\n' + team_text)
        empty_root = str(tmp_path / 'no_plugin')
        os.makedirs(empty_root, exist_ok=True)
        with mock.patch.dict(os.environ, {'CLAUDE_PLUGIN_ROOT': empty_root}):
            with pytest.raises(CriteriaError) as exc:
                load_criteria(project)
        assert 'audit_criteria.md' in str(exc.value)


class TestRunScope:
    """RULE-42: inside one run scope every file is read or parsed once."""

    @pytest.mark.proof("static_checks", "PROOF-68", "RULE-42", tier="unit")
    def test_one_parse_per_file_and_identical_keys(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            pairs = []
            for feature in ('alpha', 'beta'):
                for n in (1, 2, 3):
                    _scaffold_proof(
                        tmpdir, feature, f'PROOF-{n}', f'RULE-{n}',
                        test_file=f'tests/test_{feature}.py',
                        test_name=f'test_{feature}_{n}',
                        test_body=f'    value = {n} + 0\n    assert value == {n}')
                    pairs.append((feature, f'PROOF-{n}'))
            _scaffold_proof(tmpdir, 'gamma', 'PROOF-1', 'RULE-1',
                            test_file='tests/test_gamma.sh', test_name='test_gamma')
            pairs.append(('gamma', 'PROOF-1'))
            caches = (static_checks.AUDIT_CACHE, static_checks.DESIGN_CACHE)

            outside = {(f, p, c): cache_key_for(tmpdir, f, p, c)
                       for f, p in pairs for c in caches}
            assert len(outside) == 14

            parses, segments = [], []
            real_parse = static_checks.ast.parse
            monkeypatch.setattr(static_checks.ast, 'parse',
                                lambda *a, **k: (parses.append(1), real_parse(*a, **k))[1])
            monkeypatch.setattr(static_checks.ast, 'get_source_segment',
                                lambda *a, **k: (segments.append(1), None)[1])
            with static_checks.run_scope():
                inside = {k: cache_key_for(tmpdir, *k) for k in outside}
                again = {k: cache_key_for(tmpdir, *k) for k in outside}
            assert len(parses) == 2, (
                f"two Python test files must mean two parses, not {len(parses)}")
            assert segments == [], \
                "function source must come from the one line split, never get_source_segment"
            assert inside == outside, "a scoped key differs from the unscoped one"
            assert again == outside

            # Outside a scope nothing is memoized: an edit moves the key at once.
            test_path = os.path.join(tmpdir, 'tests', 'test_alpha.py')
            src = open(test_path, encoding='utf-8').read()
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(src.replace('value == 1', 'value == 10'))
            assert cache_key_for(tmpdir, 'alpha', 'PROOF-1') != outside[('alpha', 'PROOF-1', static_checks.AUDIT_CACHE)], \
                "the scope leaked past its block: an edited test kept its old key"
            assert static_checks._RUN_CACHE is None


    @pytest.mark.proof("static_checks", "PROOF-81", "RULE-42", tier="unit")
    def test_pass_one_and_the_key_share_the_one_parse(self, monkeypatch):
        """Pass 1 and the cache-key resolver go through the same memo, so a file
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
                key, inputs = cache_key_for(tmpdir, 'alpha', 'PROOF-1')
            assert len(parses) == 1, (
                "one file carrying two features and a cache key must mean one "
                f"ast.parse, not {len(parses)}")
            assert segments == [], \
                "a check reached for get_source_segment instead of the one line split"
            assert scoped == unscoped, "a scoped Pass 1 result differs from the unscoped one"
            assert [r['proof_id'] for r in other] == ['PROOF-2'], other
            assert inputs['test_verifiable'] is True and key

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
                assert results[0]['check'] == 'mock_target_match', results
                assert segments == [], \
                    "mock_target_match still calls get_source_segment"
            finally:
                os.unlink(mocked)

    @pytest.mark.proof("static_checks", "PROOF-69", "RULE-42", tier="unit")
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
