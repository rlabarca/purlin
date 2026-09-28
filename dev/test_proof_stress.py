"""Stress tests for the proof merge.

Multi-feature, multi-file, multi-language merges. Real plugins write the
files, in the order a real project would run them, and the reader the rest of
Purlin uses (`scripts/mcp/purlin/proofs.py`) reads them back.

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


def _seed(root, feature, entries):
    directory = root / PROOF_REL
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('%s.json' % feature)
    path.write_text(json.dumps({'proofs': entries}, indent=2)
                    + '\n', encoding='utf-8')
    return path


def _entry(feature, proof_id, rule_id, status='pass',
           test_file='tests/test.py', test_name='test_func'):
    return {'feature': feature, 'id': proof_id, 'rule': rule_id,
            'test_file': test_file, 'test_name': test_name,
            'status': status}


def _shell_run(root, script_rel, feature, calls):
    lines = ['source %s' % SHELL_HARNESS]
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
# The merges
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
        _seed(root, 'alpha', [
            _entry('beta', 'PROOF-9', 'RULE-9', test_file='tests/kept.sh')])
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        features = {e['feature'] for e in
                    json.loads((root / PROOF_REL / 'alpha.json')
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


class TestOneProofManyTests:
    """One proof claimed by tests in two files reads as one proof."""

    def test_a_failing_test_wins_over_a_passing_one(self, tmp_path):
        """One proof, two test files, one failing: the proof is not proved."""
        root = _project(tmp_path)
        _shell_run(root, 'tests/u.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'first run')])
        _shell_run(root, 'tests/i.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'fail', 'second run')])
        statuses = proofs_module.status_by_proof(_read(root)['alpha'])
        assert statuses[('alpha', 'PROOF-1')] == 'fail'


class TestMultiLanguageSameFeature:
    """Two plugins writing one feature merge rather than collide."""

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
            "-- @purlin alpha PROOF-2 RULE-2\n"
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
        _seed(root, 'alpha', [
            _entry('alpha', 'PROOF-9', 'RULE-9',
                   test_file='tests/deleted.test.sh')])
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1'}

    def test_an_entry_with_an_empty_test_file_is_reaped(self, tmp_path):
        root = _project(tmp_path)
        _seed(root, 'alpha', [
            _entry('alpha', 'PROOF-9', 'RULE-9', test_file='')])
        _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                   [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1'}

    def test_an_unreadable_file_does_not_stop_the_run(self, tmp_path):
        root = _project(tmp_path)
        directory = root / PROOF_REL
        directory.mkdir(parents=True)
        (directory / 'alpha.json').write_text('{not json',
                                                   encoding='utf-8')
        result = _shell_run(root, 'tests/alpha.test.sh', 'alpha',
                            [('PROOF-1', 'RULE-1', 'pass', 'fresh')])
        assert result.returncode == 0, result.stderr
        assert {e['id'] for e in _read(root)['alpha']} == {'PROOF-1'}

