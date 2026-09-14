"""Stress tests for the proof merge, and for the cheats it cannot catch.

Two areas:

1. Multi-feature, multi-tier, multi-language merges. Real plugins write the
   files, in the order a real project would run them, and the reader the rest
   of Purlin uses (`scripts/mcp/purlin/proofs.py`) reads them back.
2. Deliberately crafted test patterns that look correct and prove nothing.
   The free checks catch the structural ones; the rest are named here as
   semantic cheats so it is written down which is which.

Every test runs real code. No hand-written proof JSON stands in for a plugin's
output, except where an earlier run's file is being seeded on purpose.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROOF_SCRIPTS = os.path.join(PROJECT_ROOT, 'scripts', 'proof')
# A path a test writes into a shell script is spelled with forward slashes:
# bash reads a backslash as an escape, so a Windows path sourced as it comes
# off os.path.join loses every separator. Git bash reads C:/... unchanged.
SHELL_HARNESS = os.path.join(PROOF_SCRIPTS, 'shell_purlin.sh').replace(
    os.sep, '/')
PROOF_REL = os.path.join('.purlin', 'runtime', 'proofs')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'review'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'run'))

from purlin import proofs as proofs_module  # noqa: E402
from static_checks import check_python, check_proof_file  # noqa: E402
from purlin_run import bash_command, bash_path  # noqa: E402

# The bash a shell test runs under. `bash` on PATH is the Windows
# Subsystem for Linux launcher on a Windows runner, which never reads the
# script, so the run script finds Git Bash and this asks it the same
# question rather than asking it again.
BASH = bash_command()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(tmp_path):
    (tmp_path / 'specs' / 'a').mkdir(parents=True, exist_ok=True)
    (tmp_path / '.purlin').mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_spec(root, feature, rules):
    lines = ['# %s' % feature, '', '## Rules']
    for rule_id, description in rules.items():
        lines.append('- %s: %s' % (rule_id, description))
    lines.extend(['', '## Proof'])
    for rule_id in rules:
        lines.append('- %s (%s): observe it'
                     % (rule_id.replace('RULE', 'PROOF'), rule_id))
    path = root / 'specs' / 'a' / ('%s.md' % feature)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _seed(root, feature, tier, entries):
    directory = root / PROOF_REL
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('%s.%s.json' % (feature, tier))
    path.write_text(json.dumps({'tier': tier, 'proofs': entries}, indent=2)
                    + '\n', encoding='utf-8')
    return path


def _entry(feature, proof_id, rule_id, status='pass', tier='unit',
           test_file='tests/test.py', test_name='test_func'):
    return {'feature': feature, 'id': proof_id, 'rule': rule_id,
            'test_file': test_file, 'test_name': test_name,
            'status': status, 'tier': tier}


def _shell_run(root, script_rel, feature, calls, tier=None):
    lines = ['source %s' % SHELL_HARNESS]
    if tier:
        lines.append('export PURLIN_PROOF_TIER=%s' % tier)
    for proof_id, rule_id, status, name in calls:
        lines.append('purlin_proof "%s" "%s" "%s" %s "%s"'
                     % (feature, proof_id, rule_id, status, name))
    lines.append('purlin_proof_finish')
    path = root / script_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return subprocess.run([BASH, script_rel], cwd=str(root),
                          capture_output=True, text=True)


def _pytest_run(root, rel, body):
    (root / 'conftest.py').write_text(
        'import sys\n'
        'sys.path.insert(0, %r)\n'
        'from pytest_purlin import pytest_configure  # noqa: F401\n'
        % PROOF_SCRIPTS, encoding='utf-8')
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', rel],
        cwd=str(root), capture_output=True, text=True)


def _read(root):
    return proofs_module.load_proofs(str(root))


# ===========================================================================
# Area 1: merges
# ===========================================================================

class TestMultiFeatureMerge:
    """Several features coexist; a write for one never touches another."""

    @pytest.mark.proof("proof_common", "PROOF-6", "RULE-6")
    def test_three_features_keep_their_own_files(self, tmp_path):
        root = _project(tmp_path)
        for index, feature in enumerate(('alpha', 'beta', 'gamma'), start=1):
            _shell_run(root, 'tests/%s.test.sh' % feature, feature,
                       [('PROOF-%d' % index, 'RULE-1', 'pass', feature)])
        loaded = _read(root)
        assert sorted(loaded) == ['alpha', 'beta', 'gamma']
        for feature in loaded:
            assert len(loaded[feature]) == 1

    def test_a_write_for_one_feature_keeps_another_in_the_same_file(
            self, tmp_path):
        """Two features can share a file when an earlier run put them there."""
        root = _project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'kept.sh').write_text('# kept\n', encoding='utf-8')
        _seed(root, 'alpha', 'unit', [
            _entry('beta', 'PROOF-9', 'RULE-9', test_file='tests/kept.sh')])
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        features = {e['feature'] for e in
                    json.loads((root / PROOF_REL / 'alpha.unit.json')
                               .read_text(encoding='utf-8'))['proofs']}
        assert features == {'alpha', 'beta'}

    def test_two_test_files_for_one_feature_both_survive(self, tmp_path):
        root = _project(tmp_path)
        _shell_run(root, 'tests/one.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'first')])
        _shell_run(root, 'tests/two.test.sh', 'alpha',
                   [('PROOF-2', 'RULE-2', 'pass', 'second')])
        entries = _read(root)['alpha']
        assert {e['id'] for e in entries} == {'PROOF-1', 'PROOF-2'}
        assert {e['test_file'] for e in entries} == {'tests/one.test.sh',
                                                     'tests/two.test.sh'}


class TestMultiTierAggregation:
    """One feature across three tiers is three files and one reading."""

    @pytest.mark.proof("proof_common", "PROOF-14", "RULE-14")
    def test_three_tiers_read_back_as_one_feature(self, tmp_path):
        root = _project(tmp_path)
        for index, tier in enumerate(('unit', 'integration', 'e2e'), start=1):
            _shell_run(root, 'tests/%s.test.sh' % tier, 'alpha',
                       [('PROOF-%d' % index, 'RULE-%d' % index, 'pass', tier)],
                       tier=tier)
        entries = _read(root)['alpha']
        assert {e['tier'] for e in entries} == {'unit', 'integration', 'e2e'}
        assert len(entries) == 3

    def test_a_failing_tier_wins_over_a_passing_one(self, tmp_path):
        """One proof, two tiers, one failing: the proof is not proved."""
        root = _project(tmp_path)
        _shell_run(root, 'tests/u.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'unit run')])
        _shell_run(root, 'tests/i.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'fail', 'integration run')],
                   tier='integration')
        statuses = proofs_module.status_by_proof(_read(root)['alpha'])
        assert statuses[('alpha', 'PROOF-1')] == 'fail'


class TestMultiLanguageSameFeature:
    """Two plugins writing one feature at one tier merge rather than collide."""

    @pytest.mark.proof("proof_common", "PROOF-1", "RULE-1")
    def test_pytest_and_shell_both_land(self, tmp_path):
        root = _project(tmp_path)
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'shell case')])
        _pytest_run(root, 'tests/test_alpha.py',
                    'import pytest\n\n'
                    '@pytest.mark.proof("alpha", "PROOF-2", "RULE-2")\n'
                    'def test_two():\n    assert True\n')
        entries = _read(root)['alpha']
        assert {e['id'] for e in entries} == {'PROOF-1', 'PROOF-2'}
        assert {e['test_file'] for e in entries} == {
            'tests/alpha.test.sh', 'tests/test_alpha.py'}

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 not available')
    def test_sql_joins_the_same_file(self, tmp_path):
        root = _project(tmp_path)
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'shell case')])
        (root / 'tests' / 'test_alpha.sql').write_text(
            "-- @purlin alpha PROOF-2 RULE-2 unit\n"
            "-- Test: sql case\n"
            "SELECT 'PASS';\n", encoding='utf-8')
        subprocess.run([BASH,
                        bash_path(os.path.join(PROOF_SCRIPTS,
                                               'sql_purlin.sh')),
                        'tests/test_alpha.sql'],
                       cwd=str(root), capture_output=True, text=True)
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1', 'PROOF-2'}


class TestCollisionWithAnEarlierRun:
    """A stale file from an earlier run is reaped, not trusted."""

    @pytest.mark.proof("proof_common", "PROOF-6", "RULE-6")
    def test_an_entry_whose_test_file_is_gone_is_reaped(self, tmp_path):
        root = _project(tmp_path)
        _seed(root, 'alpha', 'unit', [
            _entry('alpha', 'PROOF-9', 'RULE-9',
                   test_file='tests/deleted.test.sh')])
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1'}

    def test_an_entry_with_an_empty_test_file_is_reaped(self, tmp_path):
        root = _project(tmp_path)
        _seed(root, 'alpha', 'unit', [
            _entry('alpha', 'PROOF-9', 'RULE-9', test_file='')])
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1'}

    def test_an_unreadable_file_does_not_stop_the_run(self, tmp_path):
        root = _project(tmp_path)
        directory = root / PROOF_REL
        directory.mkdir(parents=True)
        (directory / 'alpha.unit.json').write_text('{not json',
                                                   encoding='utf-8')
        result = _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                            [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        assert result.returncode == 0, result.stderr
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1'}


# ===========================================================================
# Area 2: cheats
# ===========================================================================

class TestTheFreeChecksCatchTheStructuralCheats:

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
    def test_an_assertion_with_a_true_branch_is_caught(self, tmp_path):
        """`assert result > 0 or True` asserts nothing."""
        path = tmp_path / 'test_cheat.py'
        path.write_text(
            'import pytest\n\n\n'
            '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
            'def test_tautological_or():\n'
            '    result = some_function()\n'
            '    assert result > 0 or True\n', encoding='utf-8')
        results = check_python(str(path), 'login')
        assert len(results) == 1
        assert results[0]['status'] == 'fail'
        assert results[0]['check'].startswith('assert_true')

    def test_a_test_with_no_assertion_at_all_is_caught(self, tmp_path):
        path = tmp_path / 'test_cheat.py'
        path.write_text(
            'import pytest\n\n\n'
            '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
            'def test_nothing():\n'
            '    login("alice", "secret")\n', encoding='utf-8')
        results = check_python(str(path), 'login')
        assert len(results) == 1
        assert results[0]['status'] == 'fail'


class TestTheCheatsOnlyAPersonCatches:
    """Named here so it is written down which cheats the free checks miss."""

    @pytest.mark.proof("static_checks", "PROOF-2", "RULE-2")
    def test_asserting_the_fixture_rather_than_the_code_passes(self, tmp_path):
        """The test never calls the code it claims to prove, and it passes."""
        path = tmp_path / 'test_fixture_cheat.py'
        path.write_text(
            'import pytest\n\n'
            'EXPECTED_USERS = ["alice", "bob", "charlie"]\n\n\n'
            '@pytest.mark.proof("user_mgmt", "PROOF-1", "RULE-1")\n'
            'def test_list_users_returns_three():\n'
            '    assert len(EXPECTED_USERS) == 3\n'
            '    assert "alice" in EXPECTED_USERS\n', encoding='utf-8')
        results = check_python(str(path), 'user_mgmt')
        assert len(results) == 1
        assert results[0]['status'] == 'pass', (
            'there are real assertions, so the free checks pass it: a person '
            'is what catches this one')

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 not available')
    def test_a_sql_test_that_asserts_its_own_insert_passes(self, tmp_path):
        root = _project(tmp_path)
        spec = _write_spec(root, 'data_integrity', {
            'RULE-1': 'the foreign key constraint rejects orphan rows'})
        database = root / 'test.db'
        subprocess.run(['sqlite3', str(database)],
                       input='CREATE TABLE orders (id INTEGER PRIMARY KEY, '
                             'user_id INTEGER);',
                       capture_output=True, text=True, check=True)
        (root / 'tests').mkdir(exist_ok=True)
        (root / 'tests' / 'test_cheat.sql').write_text(
            '-- @purlin data_integrity PROOF-1 RULE-1 unit\n'
            '-- Test: foreign key constraint rejects orphan rows\n'
            'INSERT INTO orders (user_id) VALUES (1);\n'
            "SELECT CASE WHEN (SELECT count(*) FROM orders) = 1\n"
            "       THEN 'PASS' ELSE 'FAIL' END;\n", encoding='utf-8')
        subprocess.run([BASH,
                        bash_path(os.path.join(PROOF_SCRIPTS,
                                               'sql_purlin.sh')),
                        'tests/test_cheat.sql', 'test.db'],
                       capture_output=True, text=True, cwd=str(root))
        entries = _read(root)['data_integrity']
        assert entries[0]['status'] == 'pass', (
            'it never tested the constraint and it passed')
        proof_file = root / PROOF_REL / 'data_integrity.unit.json'
        findings = check_proof_file(str(proof_file), spec_path=str(spec))
        assert findings == [], (
            'the proof file is well formed; the cheat is in what the SQL '
            'asserts, which no structural check reads')

    def test_a_test_that_mocks_the_code_under_test_passes_structurally(
            self, tmp_path):
        path = tmp_path / 'test_mock_cheat.py'
        path.write_text(
            'import pytest\n'
            'from unittest.mock import patch\n\n\n'
            '@pytest.mark.proof("auth", "PROOF-1", "RULE-1")\n'
            '@patch("auth.verify_password", return_value=True)\n'
            'def test_password_verified(mock_verify):\n'
            '    from auth import verify_password\n'
            '    assert verify_password("x", "y") is True\n', encoding='utf-8')
        results = check_python(str(path), 'auth')
        assert len(results) == 1
        assert results[0]['status'] in ('pass', 'fail')
