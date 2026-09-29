"""Tests for `scripts/run/purlin_run.py`, the one run script.

Every test builds a throwaway project under `tmp_path` and drives the real
script against it: the suites it runs, the two loud failures it raises, the
proofs another operating system owns, the exit codes, the evidence each run
writes and where it is committed. `scripts/run/evidence.py` has tests of its
own for the file's shape, the merge and the table.

The modules only some runs need (`mutation`, `host`, `remote`) are imported
lazily, so those tests inject fakes through `sys.modules` and read back what
the script called them with.
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_REL = os.path.join('.purlin', 'runtime', 'reports')

sys.path.insert(0, os.path.join(REPO, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(REPO, 'dev'))

import fake_claude  # noqa: E402
import suites  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import frameworks  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from run_project import (RUN_SCRIPT, _project,  # noqa: E402,F401
                         _pytest_project, _run, _spec, claude)

# The system this machine is, and a feature's one proof tagged for it: a
# remote runner runs only the tests tied to proofs tagged for its system, so
# every `--ci` fixture tags its proof this way.
HERE_OS = purlin_evidence.host_os()
TAGGED_HERE = (('PROOF-1', 'RULE-1', ' @env(%s)' % HERE_OS),)


# ---------------------------------------------------------------------------
# Building a project to run against
# ---------------------------------------------------------------------------


def _git(root, *args):
    """git in the project, loud about a failure so a broken fixture says so."""
    result = subprocess.run(['git'] + list(args), cwd=str(root),
                            capture_output=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def _git_repo(root):
    """A checkout with one commit, no signing, and a fixed identity."""
    _git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    _git(root, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    _git(root, 'config', 'user.email', 'dev@example.com')
    _git(root, 'config', 'user.name', 'Dev')
    _git(root, 'config', 'commit.gpgsign', 'false')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'the spec and its test')


def _head(root):
    return _git(root, 'rev-parse', 'HEAD').strip()


def _gate(root, gate):
    """Set the project's gate, so one checkout can be read at two of them."""
    path = root / '.purlin' / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config['gate'] = gate
    path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')


def _config(root, **fields):
    """Set keys in the project's `.purlin/config.json`."""
    path = root / '.purlin' / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config.update(fields)
    path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')


def _rule(root, feature, rule_id):
    data = purlin_payload.build_payload(str(root))
    entry = next(f for f in data['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


def _passed_word(root, feature, rule_id):
    """The word the rule's passed cell reads, which is what the evidence moves."""
    return _rule(root, feature, rule_id)['cells']['passed']['word']


def _proofs(root, feature):
    """The `proofs` of this machine's section of a feature's local evidence."""
    path = root / '.purlin' / 'evidence' / 'local' / ('%s.json' % feature)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    section = data['platforms'].get(_load_run_script().host_os())
    return None if section is None else section['proofs']


def _ran(root, name='pytest'):
    """The test names the suite's last report holds."""
    path = root / REPORTS_REL / ('%s.xml' % name)
    if not path.exists():
        return []
    return sorted(re.findall(r'<testcase [^>]*name="([^"]+)"',
                             path.read_text(encoding='utf-8')))


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheMutmutCopy:
    """mutmut leaves `mutants/` behind, a copy of the project, tests included."""

    # purlin: run_script PROOF-62
    def test_the_copy_mutmut_leaves_is_never_collected(self, tmp_path):
        root = _pytest_project(tmp_path)
        _config(root, tests=[suites.pytest_suite(files=('**/test_*.py',),
                                                 extra='--ignore=mutants')])
        _spec(root, 'feat')
        copy = root / 'mutants' / 'tests'
        copy.mkdir(parents=True)
        (copy / 'test_feat.py').write_text(
            (root / 'tests' / 'test_feat.py').read_text(encoding='utf-8'),
            encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert 'import file mismatch' not in output
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert [entry['test'] for entry in data] == [
            'tests/test_feat.py::test_ok'], data


def _refused(tmp_path, *args):
    """Run with `args`; assert exit 2 and the usage line; return the output."""
    code, output = _run(_project(tmp_path), *args)
    assert code == 2, output
    assert any(line.startswith('Usage: purlin_run.py')
               for line in output.splitlines()), output
    return output


def _accepted(tmp_path, *args):
    """Run with `args` in a folder with no spec and no git; the shape gets
    past the command line and stops on the project, exit 1, no usage line."""
    code, output = _run(_project(tmp_path), *args)
    assert code == 1, output
    assert 'Usage:' not in output, output


class TestTheCommandLine:
    """A bad invocation exits 2 and says which part was wrong."""

    # purlin: run_script PROOF-1
    def test_no_action_is_refused(self, tmp_path):
        _refused(tmp_path)

    # purlin: run_script PROOF-144
    def test_two_actions_are_refused(self, tmp_path):
        _refused(tmp_path, '--all', '--test', '--audit')

    # purlin: run_script PROOF-145
    def test_all_and_a_feature_together_are_refused(self, tmp_path):
        _refused(tmp_path, '--all', '--feature', 'x', '--test')

    # purlin: run_script PROOF-146
    def test_audit_remote_is_refused_and_names_the_test_command(
            self, tmp_path):
        output = _refused(tmp_path, '--all', '--audit', '--remote')
        assert 'purlin:test --remote' in output, output

    # purlin: run_script PROOF-147
    def test_a_flag_the_run_does_not_know_is_refused(self, tmp_path):
        _refused(tmp_path, '--all', '--test', '--nonsense')

    # purlin: run_script PROOF-148
    def test_feature_with_no_name_after_it_is_refused(self, tmp_path):
        _refused(tmp_path, '--all', '--test', '--feature')

    # purlin: run_script PROOF-149
    def test_ci_with_commit_is_refused(self, tmp_path):
        _refused(tmp_path, '--all', '--ci', '--commit')

    # purlin: run_script PROOF-150
    def test_test_remote_with_commit_is_refused(self, tmp_path):
        _refused(tmp_path, '--all', '--test', '--remote', '--commit')

    # purlin: run_script PROOF-151
    def test_test_remote_is_accepted(self, tmp_path):
        _accepted(tmp_path, '--all', '--test', '--remote')

    # purlin: run_script PROOF-152
    def test_test_commit_is_accepted(self, tmp_path):
        _accepted(tmp_path, '--all', '--test', '--commit')

    # purlin: run_script PROOF-153
    def test_audit_commit_is_accepted(self, tmp_path):
        _accepted(tmp_path, '--all', '--audit', '--commit')

    # purlin: run_script PROOF-2
    def test_an_unknown_feature_exits_two(self, tmp_path):
        root = _project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--feature', 'nosuch', '--test')
        assert code == 2
        assert 'no spec named nosuch' in output

    # purlin: run_script PROOF-154
    def test_a_missing_project_root_exits_two(self, tmp_path):
        code, output = _run(tmp_path / 'nowhere', '--all', '--test')
        assert code == 2
        assert 'is not a directory' in output


# ---------------------------------------------------------------------------
# --test, per framework
# ---------------------------------------------------------------------------

class TestTheTestArmRunsEachSuite:
    """`--test` runs each suite the settings name and writes the evidence."""

    # purlin: run_script PROOF-3
    def test_a_marked_test_lands_in_the_evidence(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert data == [{'id': 'PROOF-1', 'rule': 'RULE-1', 'result': 'pass',
                         'env': None, 'manual': False,
                         'test': 'tests/test_feat.py::test_ok'}]
        assert code == 0, output

    # purlin: run_script PROOF-113
    def test_nothing_is_written_under_specs(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')

        def tree():
            return {os.path.relpath(os.path.join(folder, name), str(root)):
                    open(os.path.join(folder, name), 'rb').read()
                    for folder, _dirs, names in os.walk(str(root / 'specs'))
                    for name in names}

        before = tree()
        _run(root, '--all', '--test')
        stray = [name for name in os.listdir(str(root / 'specs' / 'a'))
                 if not name.endswith('.md')]
        assert stray == []
        assert tree() == before

    @staticmethod
    def _sql(tmp_path, *inserts):
        """One marked SQL script that makes a unique email column and runs
        `inserts`. `(exit code, the proof's result, output)`."""
        root = _project(tmp_path, tests=[suites.sql_suite()])
        _spec(root, 'feat')
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_users.sql').write_text(
            '-- purlin: feat PROOF-1\n'
            'CREATE TABLE users (email TEXT UNIQUE);\n'
            + ''.join("INSERT INTO users VALUES ('%s');\n" % email
                      for email in inserts)
            + 'SELECT count(*) FROM users;\n', encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        results = [entry['result'] for entry in _proofs(root, 'feat') or []]
        return code, results, output

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 is not installed')
    # purlin: run_script PROOF-4
    def test_a_sql_script_whose_statements_succeed_passes(self, tmp_path):
        code, results, output = self._sql(tmp_path, 'a@test.com')
        assert results == ['pass'], output
        assert code == 0, output

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 is not installed')
    # purlin: run_script PROOF-155
    def test_a_sql_script_with_a_statement_that_errors_fails(self, tmp_path):
        code, results, output = self._sql(tmp_path, 'a@test.com',
                                          'a@test.com')
        assert results == ['fail'], output
        assert code == 1, output

    # purlin: run_script PROOF-5
    def test_a_failing_test_exits_one_and_records_the_failure(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_no():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert 'Evidence is missing' not in output, output
        assert output.strip().splitlines()[-1] == (
            '  1 rule to fix: purlin:build'), output
        assert _proofs(root, 'feat')[0]['result'] == 'fail'


# ---------------------------------------------------------------------------
# The two loud failures
# ---------------------------------------------------------------------------

class TestAProjectWithNoMarker:

    # purlin: run_script PROOF-7
    def test_a_suite_with_no_marker_is_not_a_failure(self, tmp_path):
        root = _pytest_project(tmp_path, body='def test_plain():\n    pass\n')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        # Nothing was marked, so nothing went missing: the table is what
        # says the rule has no evidence yet.
        assert '1 · 1 no test' in output, output
        assert 'Evidence is missing' not in output, output
        # The rule has no test, so the summary says it does not pass and
        # what to do; no test failed, so the run exits 0.
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 0 pass their tests.', 'Left to do:',
            '  1 rule to write a test for: purlin:build'], output
        assert code == 0, output


class TestLoudFailureB:
    """A marker sits in a test source and this run produced no entry for it."""

    # purlin: run_script PROOF-8
    def test_a_marker_with_no_entry_is_named(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert True\n\n'
            '# purlin: feat PROOF-2\n'
            '@pytest.mark.skip(reason="no tool here")\n'
            'def test_skipped():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', '')))
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert ('1 marker has no passing or failing result: feat PROOF-2 '
                'at tests/test_feat.py:7') in output, output
        assert 'feat PROOF-1 at' not in output

    # purlin: run_script PROOF-156
    def test_the_list_is_bounded_and_counted(self, tmp_path):
        body = ['import pytest\n']
        for index in range(1, 9):
            body.append(
                '# purlin: feat PROOF-%d\n'
                '@pytest.mark.skip(reason="no tool here")\n'
                'def test_skipped_%d():\n'
                '    assert True\n' % (index, index))
        root = _pytest_project(tmp_path, body='\n'.join(body))
        _spec(root, 'feat',
              proofs=tuple(('PROOF-%d' % i, 'RULE-1', '') for i in range(1, 9)))
        code, output = _run(root, '--all', '--test')
        assert code == 1
        assert '8 markers have no passing or failing result' in output
        assert 'and 3 more' in output
        line = next(line for line in output.splitlines()
                    if '8 markers have' in line)
        assert re.findall(r'feat PROOF-\d at ', line) == [
            'feat PROOF-%d at ' % n for n in range(1, 6)], line

    @staticmethod
    def _beside_a_passing_test(tmp_path, second, extra=''):
        """A passing test marked PROOF-1, then `second` from line 7 on."""
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert True\n\n' + second))
        if extra:
            _config(root, tests=[suites.pytest_suite(extra=extra)])
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', '')))
        return _run(root, '--all', '--test')

    # purlin: run_script PROOF-157
    def test_a_test_the_report_leaves_out_is_named(self, tmp_path):
        # The suite deselects one test, so its report does not hold it.
        code, output = self._beside_a_passing_test(
            tmp_path, '# purlin: feat PROOF-2\n'
                      'def test_left_out():\n'
                      '    assert True\n',
            extra="-k 'not test_left_out'")
        assert code == 1, output
        assert ('1 marker has no passing or failing result: '
                'feat PROOF-2 at tests/test_feat.py:7') in output, output
        assert 'feat PROOF-1 at' not in output, output

    # purlin: run_script PROOF-158
    def test_a_marker_with_no_test_after_it_is_named(self, tmp_path):
        code, output = self._beside_a_passing_test(
            tmp_path, '# purlin: feat PROOF-2\n')
        assert code == 1, output
        assert ('1 marker has no passing or failing result: '
                'feat PROOF-2 at tests/test_feat.py:7') in output, output
        assert 'feat PROOF-1 at' not in output, output

    # purlin: run_script PROOF-9
    def test_a_marker_for_an_unselected_feature_is_not_named(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _spec(root, 'other')
        (root / 'tests' / 'test_other.py').write_text(
            'import pytest\n\n'
            '# purlin: other PROOF-1\n'
            '@pytest.mark.skip(reason="no tool here")\n'
            'def test_skipped():\n'
            '    assert True\n', encoding='utf-8')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert 'other PROOF-1' not in output
        assert 'Evidence is missing' not in output, output
        # `other` was not run, so the summary leaves it to test; nothing
        # about it was reported as missing, and the test the run did run
        # passed, so it exits 0.
        assert output.strip().splitlines()[-3:] == [
            '2 rules. 1 passes its tests.', 'Left to do:',
            '  1 rule to test: purlin:test'], output
        assert code == 0, output


# ---------------------------------------------------------------------------
# Proofs another operating system owns
# ---------------------------------------------------------------------------

class TestEnvScopedProofs:
    """`@env` for another operating system is listed, never run, never missing."""

    def _other_os(self):
        return 'windows' if not sys.platform.startswith('win') else 'linux'

    SKIPPED_HERE = (
        'import pytest\n\n'
        '# purlin: feat PROOF-1\n'
        'def test_ok():\n'
        '    assert True\n\n'
        '# purlin: feat PROOF-2\n'
        '@pytest.mark.skip(reason="wrong host")\n'
        'def test_elsewhere():\n'
        '    assert True\n')

    # purlin: run_script PROOF-10
    def test_a_foreign_env_proof_is_listed_as_needing_its_os(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path, body=self.SKIPPED_HERE)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other)))
        purlin_run = _load_run_script()
        here = purlin_run.host_os()
        code, output = _run(root, '--all', '--test')
        assert ('1 proof needs %s; this machine is %s. Run purlin:test '
                '--remote.' % (purlin_evidence.os_word(other),
                               purlin_evidence.os_word(here))
                in output.splitlines()), output
        assert 'Evidence is missing' not in output, output
        assert [(entry['id'], entry['result'])
                for entry in _proofs(root, 'feat')] == [
            ('PROOF-1', 'pass'), ('PROOF-2', 'not run')], output
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['platforms'][here]['word'] == 'passed', cell

    # purlin: run_script PROOF-211
    def test_several_foreign_proofs_are_counted_in_one_line(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path, body=self.SKIPPED_HERE + (
            '\n# purlin: feat PROOF-3\n'
            '@pytest.mark.skip(reason="wrong host")\n'
            'def test_elsewhere_too():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other),
                                    ('PROOF-3', 'RULE-1', ' @env(%s)' % other)))
        code, output = _run(root, '--all', '--test')
        needs = [line for line in output.splitlines() if ' need' in line]
        assert needs == [
            '2 proofs need %s; this machine is %s. Run purlin:test --remote.'
            % (purlin_evidence.os_word(other),
               purlin_evidence.os_word(HERE_OS))], output

    # purlin: run_script PROOF-114
    def test_a_foreign_env_proof_is_not_reported_missing(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path, body=self.SKIPPED_HERE)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other)))
        code, output = _run(root, '--all', '--test')
        assert 'have no passing or failing result' not in output
        assert 'Evidence is missing' not in output, output
        # Recorded as a proof another system owns, never as missing.
        assert [(entry['id'], entry['result'])
                for entry in _proofs(root, 'feat')] == [
            ('PROOF-1', 'pass'), ('PROOF-2', 'not run')], output
        # Not counted here: the rule reads `passed` on this machine.
        here = _load_run_script().host_os()
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['platforms'][here]['word'] == 'passed', cell

    # purlin: run_script PROOF-115
    def test_an_env_proof_for_this_os_is_run_normally(self, tmp_path):
        purlin_run = _load_run_script()
        here = purlin_run.host_os()
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ' @env(%s)' % here),))
        code, output = _run(root, '--all', '--test')
        assert 'needs %s' % here not in output
        assert _proofs(root, 'feat') is not None, output
        assert [(entry['id'], entry['result'], entry['env'])
                for entry in _proofs(root, 'feat')] == [
            ('PROOF-1', 'pass', here)], output
        assert code == 0, output


# ---------------------------------------------------------------------------
# The state table and the next step
# ---------------------------------------------------------------------------

class TestEveryRunEndsOnTheSummary:

    # purlin: run_script PROOF-11
    def test_the_table_and_the_summary_are_printed(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert 'Purlin status:' in output
        assert 'Tests' in output
        assert output.strip().splitlines()[-2:] == [
            '1 rule. 1 passes its tests.', 'Nothing left to do.'], output
        assert code == 0, output

    # purlin: run_script PROOF-103
    def test_a_run_over_one_feature_answers_for_the_project(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _spec(root, 'other')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert output.strip().splitlines()[-3:] == [
            '2 rules. 1 passes its tests.', 'Left to do:',
            '  1 rule to write a test for: purlin:build'], output
        assert code == 0, output

    # purlin: run_script PROOF-101
    def test_at_strong_a_passing_rule_is_left_to_audit(self, tmp_path):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 1 passes its tests. 0 are strong.', 'Left to do:',
            '  1 rule to audit: purlin:audit'], output
        assert code == 0, output

    # purlin: run_script PROOF-105
    def test_at_strong_a_failing_rule_is_left_to_fix(self, tmp_path):
        root = _pytest_project(tmp_path, gate='strong', body=(
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 0 pass their tests. 0 are strong.', 'Left to do:',
            '  1 rule to fix: purlin:build'], output
        assert code == 1, output

    # purlin: run_script PROOF-106
    def test_at_passed_a_rule_with_no_test_is_left_to_write_one(
            self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', rules=2,
              proofs=(('PROOF-1', 'RULE-1', ''),))
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-3:] == [
            '2 rules. 1 passes its tests.', 'Left to do:',
            '  1 rule to write a test for: purlin:build'], output
        assert code == 0, output

    # purlin: run_script PROOF-104
    def test_a_project_with_no_specs_says_so(self, tmp_path):
        root = _project(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert 'No specs found under specs/' in output
        assert code == 1


# ---------------------------------------------------------------------------
# The evidence, the audit and the CI run
# ---------------------------------------------------------------------------

def _load_run_script():
    """The run script as a module, with its own sys.path set up."""
    for path in (os.path.join(REPO, 'scripts', 'run'),
                 os.path.join(REPO, 'scripts', 'mcp')):
        if path not in sys.path:
            sys.path.insert(0, path)
    import purlin_run

    return purlin_run


class _FakeModule(object):
    """A stand-in for a module the run imports only when it needs it."""

    def __init__(self, **attributes):
        self.__dict__.update(attributes)


def _evidence(root, feature='feat', source='local'):
    path = root / '.purlin' / 'evidence' / source / ('%s.json' % feature)
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture
def evidence_run(monkeypatch, tmp_path):
    """Run the script in-process with the git host and the engines faked."""
    calls = {'commit': [], 'breaks': [], 'commits_here': True}

    def commit_files(project_root, paths, message, merge=None):
        calls['commit'].append((list(paths), message, merge))
        return 'c' * 40

    def select_engine(config, frameworks):
        return 'mutmut'

    def run_breaks(project_root, engine, scope):
        calls['breaks'].append((engine, scope))
        return {
            'engine': engine, 'available': True, 'reason': '',
            'features': {'feat': {
                'scope_score': {'score': 80, 'killed': 4, 'survived': 1}}},
            'log': 'breaks.log'}

    # `commits_here` answers True here; the cases that turn it off set it
    # for themselves. The machine a runner's section names is the real
    # module's answer.
    _load_run_script()
    loaded = importlib.util.spec_from_file_location(
        'real_host', os.path.join(REPO, 'scripts', 'run', 'host.py'))
    real_host = importlib.util.module_from_spec(loaded)
    loaded.loader.exec_module(real_host)
    monkeypatch.setitem(sys.modules, 'host', _FakeModule(
        commit_files=commit_files,
        commits_here=lambda project_root: calls['commits_here'],
        runner_machine=real_host.runner_machine,
        no_commit_line=lambda project_root: (
            'Tag run: nothing is written. This run reruns the tests on '
            'signed/0.10.0.')))
    monkeypatch.setitem(sys.modules, 'mutation', _FakeModule(
        select_engine=select_engine, run_breaks=run_breaks))

    def go(root, *args):
        purlin_run = _load_run_script()
        code = purlin_run.main(['--project-root', str(root)] + list(args))
        return code, calls

    return go


class TestTheCiArmCommitsItsSection:
    """A runner writes its own operating system's section and commits it."""

    @staticmethod
    def _ci(tmp_path, evidence_run, capsys, gate='strong'):
        root = _pytest_project(tmp_path, gate=gate)
        _spec(root, 'feat', proofs=TAGGED_HERE)
        _git_repo(root)
        code, calls = evidence_run(root, '--all', '--ci')
        return root, code, calls, capsys.readouterr().out

    # purlin: run_script PROOF-12
    def test_the_ci_arm_writes_its_section_and_commits(
            self, tmp_path, evidence_run, capsys):
        root, code, _calls, output = self._ci(tmp_path, evidence_run, capsys)
        here = _load_run_script().host_os()
        data = _evidence(root, source='ci')
        assert list(data['platforms']) == [here]
        section = data['platforms'][here]
        assert section['runner'] == 'ci'
        assert section['machine'] == 'remote runner, %s' % (
            purlin_evidence.os_word(here)), section
        assert section['rules'] == {'RULE-1': 'passed'}
        assert 'Evidence committed.' in output.splitlines(), output
        assert not (root / '.purlin' / 'evidence' / 'local').exists()
        assert code == 0, output

    # purlin: run_script PROOF-116
    def test_the_ci_arm_commits_its_one_path(
            self, tmp_path, evidence_run, capsys):
        root, _code, calls, _output = self._ci(tmp_path, evidence_run,
                                                capsys)
        assert [(paths, message) for paths, message, _m in calls['commit']] \
            == [(['.purlin/evidence/ci/feat.json'],
                 'purlin: evidence at %s' % _head(root)[:7])]

    # purlin: run_script PROOF-117
    def test_the_merge_keeps_another_systems_section(
            self, tmp_path, evidence_run, capsys):
        root, _code, calls, _output = self._ci(tmp_path, evidence_run,
                                                capsys)
        ((paths, _message, merge),) = calls['commit']
        assert callable(merge), 'the commit was handed no merge'
        data = _evidence(root, source='ci')
        here = _load_run_script().host_os()
        other = 'windows' if here != 'windows' else 'linux'
        branch = dict(data, platforms={other: data['platforms'][here]})
        merged = json.loads(merge(paths[0], json.dumps(data),
                                  json.dumps(branch)))
        assert sorted(merged['platforms']) == sorted([here, other]), merged

    # purlin: run_script PROOF-118
    def test_at_passed_the_ci_arm_does_the_same(
            self, tmp_path, evidence_run, capsys):
        _root, _code, calls, output = self._ci(tmp_path, evidence_run,
                                                capsys, gate='passed')
        assert [paths for paths, _m, _merge in calls['commit']] == [
            ['.purlin/evidence/ci/feat.json']]
        assert 'Evidence committed.' in output.splitlines(), output

    # purlin: run_script PROOF-119
    def test_a_failing_test_fails_the_ci_arm(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong', body=(
            '# purlin: feat PROOF-1\n'
            'def test_no():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat', proofs=TAGGED_HERE)
        code, _calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert code == 1, output

    # purlin: run_script PROOF-120
    def test_a_marker_naming_no_spec_does_not_fail_the_ci_arm(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong', body=(
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert True\n\n'
            '# purlin: nosuch PROOF-1\n'
            'def test_other():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=TAGGED_HERE)
        code, _calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert 'names nosuch PROOF-1, which no spec has' in output, output
        assert code == 0, output

    @staticmethod
    def _mixed(tmp_path, evidence_run, capsys, untagged='True'):
        """`feat`'s PROOF-1 (RULE-1) carries no tag and PROOF-2 (RULE-2) is
        tagged for this machine's system; one test file holds both tests,
        the untagged one asserting `untagged`. `(root, code, calls, output)`."""
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_untagged():\n'
            '    assert %s\n\n'
            '# purlin: feat PROOF-2\n'
            'def test_tagged():\n'
            '    assert True\n' % untagged))
        _spec(root, 'feat', rules=2, proofs=(
            ('PROOF-1', 'RULE-1', ''),
            ('PROOF-2', 'RULE-2', ' @env(%s)' % HERE_OS)))
        _git_repo(root)
        code, calls = evidence_run(root, '--all', '--ci')
        return root, code, calls, capsys.readouterr().out

    # purlin: run_script PROOF-207
    def test_the_section_lists_only_the_proofs_tagged_for_its_system(
            self, tmp_path, evidence_run, capsys):
        root, code, _calls, output = self._mixed(tmp_path, evidence_run,
                                                 capsys)
        section = _evidence(root, source='ci')['platforms'][HERE_OS]
        assert [(entry['id'], entry['result'])
                for entry in section['proofs']] == [('PROOF-2', 'pass')], \
            output
        assert section['rules'] == {'RULE-2': 'passed'}, output
        assert code == 0, output

    # purlin: run_script PROOF-208
    def test_a_feature_with_no_proof_tagged_for_its_system_gets_no_file(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert True\n\n'
            '# purlin: other PROOF-1\n'
            'def test_other():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=TAGGED_HERE)
        _spec(root, 'other')
        _git_repo(root)
        code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert (root / '.purlin' / 'evidence' / 'ci' / 'feat.json').exists()
        assert not (root / '.purlin' / 'evidence' / 'ci'
                    / 'other.json').exists(), output
        assert [paths for paths, _m, _merge in calls['commit']] == [
            ['.purlin/evidence/ci/feat.json']], output
        assert code == 0, output

    # purlin: run_script PROOF-209
    def test_an_untagged_test_that_fails_beside_a_tagged_one_does_not_fail_it(
            self, tmp_path, evidence_run, capsys):
        _root, code, _calls, output = self._mixed(
            tmp_path, evidence_run, capsys, untagged='1 == 2')
        assert code == 0, output


class TestTheLog:

    # purlin: run_script PROOF-15
    def test_the_log_is_written(self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', proofs=TAGGED_HERE)
        evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        log = root / '.purlin' / 'runtime' / 'run.log'
        assert '-m pytest' in log.read_text(encoding='utf-8')

    # purlin: run_script PROOF-159
    def test_the_audit_writes_the_log_too(self, tmp_path, evidence_run,
                                          claude, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        log = root / '.purlin' / 'runtime' / 'run.log'
        assert '-m pytest' in log.read_text(encoding='utf-8')


class TestTheBreaks:

    # purlin: run_script PROOF-16
    def test_the_breaks_are_asked_for_each_features_scope_files(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        engine, scope = calls['breaks'][0]
        assert engine == 'mutmut'
        assert scope == {'feat': ['src/']}


class TestWhereEachArmCommits:

    @staticmethod
    def _commits_through_git(tmp_path, evidence_run, capsys, action):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _git_repo(root)
        _code, calls = evidence_run(root, '--all', action, '--commit')
        output = capsys.readouterr().out
        assert calls['commit'] == [], (
            "a person's run commits through git, not the git host's API")
        assert 'Evidence committed.' in output.splitlines(), output
        assert not list(root.glob('specs/**/*.signatures'))
        assert not (root / '.purlin' / 'evidence' / 'ci').exists()

    # purlin: run_script PROOF-17
    def test_a_test_run_never_uses_the_git_hosts_api(
            self, tmp_path, evidence_run, capsys):
        self._commits_through_git(tmp_path, evidence_run, capsys, '--test')

    # purlin: run_script PROOF-161
    def test_an_audit_never_uses_the_git_hosts_api(
            self, tmp_path, evidence_run, claude, capsys):
        self._commits_through_git(tmp_path, evidence_run, capsys, '--audit')

    @staticmethod
    def _on_ref(monkeypatch, ref):
        """The real host's reading of the ref a GitHub runner was started
        for; only the commit through the git host's API stays faked."""
        _load_run_script()
        loaded = importlib.util.spec_from_file_location(
            'real_host', os.path.join(REPO, 'scripts', 'run', 'host.py'))
        real = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(real)
        monkeypatch.setitem(sys.modules, 'host', _FakeModule(
            commit_files=sys.modules['host'].commit_files,
            commits_here=real.commits_here, no_commit_line=real.no_commit_line,
            runner_machine=real.runner_machine))
        monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/project')
        monkeypatch.setenv('GITHUB_REF', ref)
        monkeypatch.setenv('GITHUB_REF_NAME', ref.split('/', 2)[2])

    # purlin: run_script PROOF-68
    def test_a_tag_run_writes_nothing_and_says_so(
            self, tmp_path, evidence_run, capsys, monkeypatch):
        """A tag run reruns the tests and adds no evidence."""
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', proofs=TAGGED_HERE)
        purlin_run = _load_run_script()
        evidence_run(root, '--all', '--test')
        local = _file(root, '.purlin/evidence/local/feat.json')
        self._on_ref(monkeypatch, 'refs/tags/signed/0.10.0')
        _code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert calls['commit'] == []
        assert not (root / '.purlin' / 'evidence' / 'ci').exists()
        assert any(line.startswith('Tag run: nothing is written.')
                   for line in output.splitlines()), output
        assert not (root / '.purlin' / 'runtime' / 'run.log').exists()
        assert _file(root, '.purlin/evidence/local/feat.json') == local
        assert purlin_run.host_os()

    # purlin: run_script PROOF-121
    def test_a_run_on_the_branch_that_keeps_it_commits(
            self, tmp_path, evidence_run, capsys, monkeypatch):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', proofs=TAGGED_HERE)
        self._on_ref(monkeypatch, 'refs/heads/run/main-4f1c2ab')
        _code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert len(calls['commit']) == 1
        assert not any(line.startswith('Tag run:')
                       for line in output.splitlines()), output


class TestTheGateDecidesTheBreaks:
    """The breaks run only where mutation testing is on and a strength is compared."""

    # purlin: run_script PROOF-65
    def test_under_passed_no_break_runs_and_the_strength_is_not_measured(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='passed')
        # Mutation testing is on, so the gate alone keeps the breaks off.
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        capsys.readouterr()

        assert calls['breaks'] == [], 'the breaks ran under the passed gate'
        assert _evidence(root)['audit']['mutation'] is None

    # purlin: run_script PROOF-66
    def test_under_strong_the_audit_measures_and_writes_the_score(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        capsys.readouterr()

        assert len(calls['breaks']) == 1, 'the breaks did not run under strong'
        mutation = _evidence(root)['audit']['mutation']
        assert (mutation['engine'], mutation['score']) == ('mutmut', 80)
        cell = _rule(root, 'feat', 'RULE-1')['cells']['strong']
        assert (cell['word'], cell['reasons']) == ('strong', []), cell

    @staticmethod
    def _ci_measures_nothing(tmp_path, evidence_run, claude, capsys, gate):
        _install, directory = claude
        root = _pytest_project(tmp_path, gate=gate)
        _config(root, mutation_engine='auto')
        _spec(root, 'feat', proofs=TAGGED_HERE)
        _code, calls = evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        assert calls['breaks'] == []
        assert 'audit' not in _evidence(root, source='ci')
        assert fake_claude.calls(directory) == []

    # purlin: run_script PROOF-102
    def test_a_ci_run_at_passed_measures_nothing_and_audits_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        self._ci_measures_nothing(tmp_path, evidence_run, claude, capsys,
                                  'passed')

    # purlin: run_script PROOF-174
    def test_a_ci_run_at_strong_measures_nothing_and_audits_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        self._ci_measures_nothing(tmp_path, evidence_run, claude, capsys,
                                  'strong')

    # purlin: run_script PROOF-175
    def test_a_ci_run_at_signed_measures_nothing_and_audits_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        self._ci_measures_nothing(tmp_path, evidence_run, claude, capsys,
                                  'signed')

    # purlin: run_script PROOF-79
    def test_with_mutation_off_the_audit_alone_decides(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='none')
        _spec(root, 'feat')
        code, calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert calls['breaks'] == [], output
        cell = _rule(root, 'feat', 'RULE-1')['cells']['strong']
        assert (cell['word'], cell['reasons']) == (
            'strong', ['no mutation score measured']), cell
        assert code == 0, output

    # purlin: run_script PROOF-80
    def test_with_mutation_on_a_score_under_the_minimum_is_weak(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, min_strength=90, mutation_engine='auto')
        _spec(root, 'feat')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        cell = _rule(root, 'feat', 'RULE-1')['cells']['strong']
        assert (cell['word'], cell['reasons']) == (
            'weak', ['strength 80% under 90%']), cell
        assert code == 1, output

    # purlin: run_script PROOF-213
    def test_an_engine_that_measured_nothing_says_why(
            self, tmp_path, evidence_run, monkeypatch, capsys):
        sentence = 'mutmut is not installed: run "pip install mutmut"'

        def run_breaks(project_root, engine, scope):
            return {'engine': 'mutmut', 'available': False,
                    'reason': sentence,
                    'features': {'feat': {
                        'scope_score': {'score': None, 'killed': 0,
                                        'survived': 0},
                        'missing': sentence}},
                    'log': ''}
        monkeypatch.setitem(sys.modules, 'mutation', _FakeModule(
            select_engine=lambda config, frameworks: 'mutmut',
            run_breaks=run_breaks))
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert _evidence(root)['audit']['mutation']['missing'] == sentence
        assert output.splitlines().count('purlin: %s' % sentence) == 1, \
            output

    @staticmethod
    def _two_features_audited(tmp_path, evidence_run):
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert 1 + 1 == 2\n\n'
            '# purlin: other PROOF-1\n'
            'def test_other():\n'
            '    assert 2 + 2 == 4\n'))
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        _spec(root, 'other')
        _code, calls = evidence_run(root, '--all', '--audit')
        return root, calls

    # purlin: run_script PROOF-81
    def test_every_feature_with_a_rule_being_read_is_measured(
            self, tmp_path, evidence_run, capsys):
        _root, calls = self._two_features_audited(tmp_path, evidence_run)
        capsys.readouterr()
        assert len(calls['breaks']) == 1, calls['breaks']
        assert sorted(calls['breaks'][0][1]) == ['feat', 'other']

    # purlin: run_script PROOF-173
    def test_a_feature_with_no_rule_being_read_is_not_measured(
            self, tmp_path, evidence_run, capsys):
        root, calls = self._two_features_audited(tmp_path, evidence_run)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing one'), encoding='utf-8')
        _code, calls = evidence_run(root, '--audit')
        capsys.readouterr()
        assert len(calls['breaks']) == 2, calls['breaks']
        assert sorted(calls['breaks'][1][1]) == ['feat'], calls['breaks'][1]


# ---------------------------------------------------------------------------
# The AI audit: which rules, how many calls, what is written
# ---------------------------------------------------------------------------

def _many(tmp_path, count, gate='strong'):
    """A project with one feature of `count` rules, each with a passing test."""
    body = ['import pytest', '']
    for index in range(1, count + 1):
        body.extend(['',
                     '# purlin: feat PROOF-%d' % index,
                     'def test_rule_%d():' % index,
                     '    assert %d == %d' % (index, index), ''])
    root = _pytest_project(tmp_path, gate=gate, body='\n'.join(body))
    _spec(root, 'feat', rules=count,
          proofs=[('PROOF-%d' % n, 'RULE-%d' % n, '')
                  for n in range(1, count + 1)])
    return root


def _audited(root, feature='feat'):
    """`{rule: entry}` the local evidence holds under `audit.rules`."""
    try:
        data = _evidence(root, feature)
    except (IOError, OSError):
        return {}
    return (data.get('audit') or {}).get('rules') or {}


class TestTheAuditCallsTheModel:

    # purlin: run_script PROOF-70
    def test_one_call_per_rule_four_at_a_time_by_default(
            self, tmp_path, evidence_run, claude, capsys):
        install, directory = claude
        install(sleep=0.4)
        root = _many(tmp_path, 6)
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        calls = fake_claude.calls(directory)
        assert len(calls) == 6, calls
        assert fake_claude.most_at_once(calls) == 4, calls
        assert 'AI audit: 6 rules to read, 4 at a time.' in output, output
        entries = _audited(root)
        assert sorted(entries) == ['RULE-%d' % n for n in range(1, 7)]
        with open(os.path.join(REPO, 'references', 'review_criteria.md'),
                  encoding='utf-8') as handle:
            criteria = hashlib.sha256(handle.read().encode('utf-8'))
        for entry in entries.values():
            assert entry['verdict'] == 'strong', entry
            assert entry['findings'] == [], entry
            assert entry['model'] == 'claude-fake-1', entry
            assert entry['criteria'] == criteria.hexdigest(), entry
        assert code == 0, output

    # purlin: run_script PROOF-71
    def test_the_setting_decides_how_many_run_at_once(
            self, tmp_path, evidence_run, claude, capsys):
        install, directory = claude
        install(sleep=0.4)
        root = _many(tmp_path, 4)
        _config(root, audit_parallel=2)
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        calls = fake_claude.calls(directory)
        assert 'AI audit: 4 rules to read, 2 at a time.' in output, output
        assert len(calls) == 4 and fake_claude.most_at_once(calls) == 2, calls

    # purlin: run_script PROOF-177
    def test_a_setting_out_of_range_is_read_as_four_with_one_warning(
            self, tmp_path, evidence_run, claude, capsys):
        install, directory = claude
        install(sleep=0.4)
        root = _many(tmp_path, 5)
        _config(root, audit_parallel=40)
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        self._beside_the_table(output, '40')
        assert 'AI audit: 5 rules to read, 4 at a time.' in output, output
        calls = fake_claude.calls(directory)
        assert len(calls) == 5 and fake_claude.most_at_once(calls) == 4, calls

    @staticmethod
    def _five_rules_at(tmp_path, evidence_run, capsys, value):
        """An audit of five rules with `audit_parallel` set to `value`."""
        root = _many(tmp_path, 5)
        _config(root, audit_parallel=value)
        evidence_run(root, '--all', '--audit')
        return capsys.readouterr().out

    @staticmethod
    def _beside_the_table(output, shown):
        """The warning is printed once, with the status table, as every
        warning resolving the settings raised is."""
        lines = output.splitlines()
        warning = ('"audit_parallel" is %s, which is not a whole number from '
                   '1 to 16; reading it as 4' % shown)
        assert lines.count(warning) == 1, output
        assert lines.index(warning) > lines.index(next(
            line for line in lines if line.startswith('Purlin status:'))), \
            output

    def _warned(self, output, shown):
        self._beside_the_table(output, shown)
        assert 'AI audit: 5 rules to read, 4 at a time.' in output, output

    # purlin: run_script PROOF-178
    def test_sixteen_is_taken_as_it_is(self, tmp_path, evidence_run, claude,
                                       capsys):
        output = self._five_rules_at(tmp_path, evidence_run, capsys, 16)
        assert 'audit_parallel' not in output, output
        assert 'AI audit: 5 rules to read, 5 at a time.' in output, output

    # purlin: run_script PROOF-179
    def test_seventeen_reads_as_four_with_the_warning(
            self, tmp_path, evidence_run, claude, capsys):
        self._warned(self._five_rules_at(tmp_path, evidence_run, capsys, 17),
                     '17')

    # purlin: run_script PROOF-180
    def test_zero_reads_as_four_with_the_warning(
            self, tmp_path, evidence_run, claude, capsys):
        self._warned(self._five_rules_at(tmp_path, evidence_run, capsys, 0),
                     '0')

    # purlin: run_script PROOF-181
    def test_a_fraction_reads_as_four_with_the_warning(
            self, tmp_path, evidence_run, claude, capsys):
        self._warned(self._five_rules_at(tmp_path, evidence_run, capsys, 2.5),
                     '2.5')

    # purlin: run_script PROOF-182
    def test_a_word_reads_as_four_with_the_warning(
            self, tmp_path, evidence_run, claude, capsys):
        self._warned(self._five_rules_at(tmp_path, evidence_run, capsys,
                                         'four'), "'four'")

    # purlin: run_script PROOF-72
    def test_the_line_is_printed_before_the_first_call(
            self, tmp_path, evidence_run, claude, capsys, monkeypatch):
        root = _many(tmp_path, 2)
        _load_run_script()
        import ai_audit
        printed = []
        real = ai_audit.ask_model

        def watched(*args, **kwargs):
            printed.append(sys.stdout.getvalue())
            return real(*args, **kwargs)

        monkeypatch.setattr(ai_audit, 'ask_model', watched)
        evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        assert len(printed) == 2, printed
        assert 'AI audit: 2 rules to read, 2 at a time.' in printed[0], \
            printed[0]

    # purlin: run_script PROOF-73
    def test_nothing_to_read_says_so_and_calls_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _many(tmp_path, 2)
        evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        assert len(fake_claude.calls(directory)) == 2
        evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert ('AI audit: nothing to read; every rule matches its last '
                'audit.') in output, output
        assert len(fake_claude.calls(directory)) == 2
        assert 'AI audit: 0 rules read, 0 strong, 0 weak. 2 rules skipped; ' \
            'their text, proof and test match their last audit. ' \
            'purlin:audit --all reads them again.' in output, output


class TestWhichRulesTheAuditReads:

    # purlin: run_script PROOF-74
    def test_a_rule_that_matches_its_last_audit_is_skipped(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _many(tmp_path, 2)
        evidence_run(root, '--all', '--audit')
        first = _audited(root)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 2', 'does thing two'), encoding='utf-8')
        capsys.readouterr()
        evidence_run(root, '--audit')
        output = capsys.readouterr().out
        calls = fake_claude.calls(directory)
        assert len(calls) == 3, calls
        assert 'does thing two' in calls[2]['prompt']
        assert 'AI audit: 1 rule to read, 1 at a time.' in output, output
        assert '1 rule skipped; its text, proof and test match its last ' \
            'audit.' in output, output
        assert _audited(root)['RULE-1'] == first['RULE-1']

    # purlin: run_script PROOF-75
    def test_all_reads_every_rule_again(self, tmp_path, evidence_run, claude,
                                        capsys):
        _install, directory = claude
        root = _many(tmp_path, 2)
        evidence_run(root, '--all', '--audit')
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert len(fake_claude.calls(directory)) == 4
        assert output.count('AI audit: 2 rules to read, 2 at a time.') == 2

    # purlin: run_script PROOF-77
    def test_a_rule_whose_test_failed_is_not_read(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_bad():\n'
            '    assert 1 == 2\n\n'
            '# purlin: feat PROOF-2\n'
            'def test_good():\n'
            '    assert 2 == 2\n'))
        _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                             ('PROOF-2', 'RULE-2', '')))
        evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        assert len(fake_claude.calls(directory)) == 1
        assert sorted(_audited(root)) == ['RULE-2']

    # purlin: run_script PROOF-78
    def test_with_no_feature_named_every_feature_is_audited(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert 1 + 1 == 2\n\n'
            '# purlin: other PROOF-1\n'
            'def test_other():\n'
            '    assert 2 + 2 == 4\n'))
        _spec(root, 'feat')
        _spec(root, 'other')
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert code == 0, output
        assert len(fake_claude.calls(directory)) == 2
        assert sorted(_audited(root, 'feat')) == ['RULE-1']
        assert sorted(_audited(root, 'other')) == ['RULE-1']

    # purlin: run_script PROOF-176
    def test_a_rule_taken_from_an_anchor_is_read_only_as_the_anchors(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert 1 + 1 == 2\n\n'
            '# purlin: shared PROOF-1\n'
            'def test_json():\n'
            '    assert 2 + 2 == 4\n'))
        (root / 'specs' / '_anchors').mkdir()
        (root / 'specs' / '_anchors' / 'shared.md').write_text(
            '# Anchor: shared\n\n## Rules\n\n- RULE-1: every answer is JSON\n'
            '\n## Proof\n\n- PROOF-1 (RULE-1): an answer parses as JSON\n',
            encoding='utf-8')
        _spec(root, 'feat', requires='shared')
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert code == 0, output
        prompts = [call['prompt'] for call in fake_claude.calls(directory)]
        # One call for feat's own rule and one for the anchor's, under the
        # anchor: the rule feat takes from it is not read again as feat's.
        anchor = [prompt for prompt in prompts
                  if 'every answer is JSON' in prompt]
        assert len(prompts) == 2 and len(anchor) == 1, prompts
        assert re.search(r'^shared RULE-1$', anchor[0], re.M), anchor[0]
        assert sorted(_audited(root, 'feat')) == ['RULE-1']
        assert sorted(_audited(root, 'shared')) == ['RULE-1']


class TestWhenTheModelCannotBeReached:

    @staticmethod
    def _unreachable(tmp_path, evidence_run, claude, capsys, monkeypatch,
                     settings, why, then, no_claude=False):
        """Two rules whose tests pass, audited with the model out of reach."""
        install, _directory = claude
        install(**settings)
        _load_run_script()
        import ai_audit
        monkeypatch.setattr(ai_audit, 'MODEL_TIMEOUT', 1)
        if no_claude:
            monkeypatch.setattr(ai_audit, 'claude_path', lambda: None)
        root = _many(tmp_path, 2)
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert _audited(root) == {}, _audited(root)
        for rule_id in ('RULE-1', 'RULE-2'):
            cell = _rule(root, 'feat', rule_id)['cells']['strong']
            assert cell['word'] == 'not audited', cell
            assert cell['reasons'] == ['the AI audit could not run: %s' % why]
        assert '2 rules could not be audited: %s. %s' % (why, then) in \
            output, output
        assert code == 1, output

    # purlin: run_script PROOF-82
    def test_no_claude_on_the_path(self, tmp_path, evidence_run, claude,
                                   capsys, monkeypatch):
        self._unreachable(tmp_path, evidence_run, claude, capsys, monkeypatch,
                          {}, 'claude is not on PATH',
                          'Install Claude Code, then run purlin:audit again.',
                          no_claude=True)

    # purlin: run_script PROOF-183
    def test_a_model_that_exits_1(self, tmp_path, evidence_run, claude,
                                  capsys, monkeypatch):
        self._unreachable(tmp_path, evidence_run, claude, capsys, monkeypatch,
                          {'exit_code': 1}, 'claude exited with an error',
                          'Run purlin:audit again.')

    # purlin: run_script PROOF-184
    def test_a_model_past_its_time_limit(self, tmp_path, evidence_run, claude,
                                         capsys, monkeypatch):
        self._unreachable(tmp_path, evidence_run, claude, capsys, monkeypatch,
                          {'sleep': 3}, 'claude timed out after 1 s',
                          'Run purlin:audit again.')

    # purlin: run_script PROOF-185
    def test_a_model_that_answers_with_no_settled_line(
            self, tmp_path, evidence_run, claude, capsys, monkeypatch):
        self._unreachable(tmp_path, evidence_run, claude, capsys, monkeypatch,
                          {'answers': ['It looks fine to me.']},
                          'claude answered without a settled line',
                          'Run purlin:audit again.')

    @staticmethod
    def _two_causes(tmp_path, evidence_run, claude, capsys):
        """Two rules whose tests pass, audited by a model that exits 1 for
        RULE-1 and answers RULE-2 with no settled line. `(root, code,
        output)`."""
        install, directory = claude
        install()
        # The fake's own launcher stays; only what it runs is replaced.
        (directory / 'claude').write_text(
            '#!%s\nimport json, sys\n'
            'if "\\nfeat RULE-1\\n" in sys.stdin.read():\n    sys.exit(1)\n'
            'print(json.dumps({"type": "result", "result": "It looks fine."}))'
            '\n' % sys.executable, encoding='utf-8')
        root = _many(tmp_path, 2)
        code, _calls = evidence_run(root, '--all', '--audit')
        return root, code, capsys.readouterr().out

    # purlin: run_script PROOF-186
    def test_two_causes_in_one_run_print_one_line_each(
            self, tmp_path, evidence_run, claude, capsys):
        root, code, output = self._two_causes(tmp_path, evidence_run, claude,
                                              capsys)
        assert _audited(root) == {}, _audited(root)
        assert [line for line in output.splitlines()
                if 'could not be audited' in line] == [
            '1 rule could not be audited: claude answered without a settled '
            'line. Run purlin:audit again.',
            '1 rule could not be audited: claude exited with an error. Run '
            'purlin:audit again.'], output
        assert code == 1, output

    # purlin: run_script PROOF-206
    def test_two_causes_in_one_run_give_each_cell_its_own(
            self, tmp_path, evidence_run, claude, capsys):
        root, _code, _output = self._two_causes(tmp_path, evidence_run,
                                                claude, capsys)
        for rule_id, why in (('RULE-1', 'claude exited with an error'),
                             ('RULE-2', 'claude answered without a settled '
                                        'line')):
            cell = _rule(root, 'feat', rule_id)['cells']['strong']
            assert (cell['word'], cell['reasons']) == (
                'not audited', ['the AI audit could not run: %s' % why]), cell

    # purlin: run_script PROOF-83
    def test_the_next_audit_tries_again(self, tmp_path, evidence_run, claude,
                                        capsys):
        install, directory = claude
        install(exit_code=1)
        root = _many(tmp_path, 1)
        evidence_run(root, '--all', '--audit')
        install()
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert len(fake_claude.calls(directory)) == 1
        assert _audited(root)['RULE-1']['verdict'] == 'strong'
        cell = _rule(root, 'feat', 'RULE-1')['cells']['strong']
        assert cell['word'] == 'strong', cell
        assert code == 0, output

    # purlin: run_script PROOF-84
    def test_at_the_gate_passed_it_blocks_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install(exit_code=1)
        root = _many(tmp_path, 1, gate='passed')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert '1 rule could not be audited: claude exited with an error.' \
            in output, output
        assert code == 0, output


def _before_the_table(output):
    """The lines a run printed before the status table, the last one last."""
    return output.split('Purlin status:')[0].strip().splitlines()


class TestTheLastLines:

    # purlin: run_script PROOF-86
    def test_the_audit_ends_in_the_order_the_design_gives(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.',
                         'It looks fine to me.'])
        root = _many(tmp_path, 2)
        _config(root, audit_parallel=1, mutation_engine='auto')
        _git_repo(root)
        code, _calls = evidence_run(root, '--all', '--audit', '--commit')
        output = capsys.readouterr().out
        order = ['Evidence written to .purlin/evidence/local/feat.json.',
                 'Evidence committed.',
                 'AI audit: 1 rule read, 0 strong, 1 weak.',
                 '1 rule could not be audited: claude answered without a '
                 'settled line. Run purlin:audit again.']
        lines = _before_the_table(output)
        assert lines[-len(order):] == order, lines
        assert output.strip().splitlines()[-4:] == [
            '2 rules. 2 pass their tests. 0 are strong.', 'Left to do:',
            '  1 rule to audit: purlin:audit',
            '  1 rule to strengthen: purlin:build'], output
        assert code == 1

    # purlin: run_script PROOF-107
    def test_the_skipped_rules_take_their_place(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        loose = 'It looks fine to me.'
        # The first audit settles RULE-2 alone: RULE-1 and RULE-3 get no
        # settled line, each asked twice.
        install(answers=[loose, loose, 'settled: yes', loose])
        root = _many(tmp_path, 3, gate='signed')
        _config(root, audit_parallel=1, mutation_engine='auto')
        _git_repo(root)
        evidence_run(root, '--all', '--audit', '--commit')
        capsys.readouterr()
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.',
                         loose])
        code, _calls = evidence_run(root, '--audit', '--commit')
        output = capsys.readouterr().out
        order = ['Evidence written to .purlin/evidence/local/feat.json.',
                 'Evidence committed.',
                 'AI audit: 1 rule read, 0 strong, 1 weak. 1 rule skipped; '
                 'its text, proof and test match its last audit. '
                 'purlin:audit --all reads them again.',
                 '1 rule could not be audited: claude answered without a '
                 'settled line. Run purlin:audit again.']
        lines = _before_the_table(output)
        assert lines[-len(order):] == order, lines
        assert output.strip().splitlines()[-5:] == [
            '3 rules. 3 pass their tests. 1 is strong. 0 are signed.',
            'Left to do:', '  1 rule to audit: purlin:audit',
            '  1 rule to strengthen: purlin:build',
            '  1 rule to tie to its files: purlin:spec'], output
        assert code == 1


class TestTheAuditExitCode:
    """Above `passed` a rule it read that is weak makes the audit exit 1."""

    @staticmethod
    def _found_weak(tmp_path, evidence_run, claude, capsys):
        """One rule at `strong` that an audit found `PROOF-1 reads the value
        alone.` against. `(root, exit code, output)`."""
        install, _directory = claude
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.'])
        root = _many(tmp_path, 1)
        code, _calls = evidence_run(root, '--all', '--audit')
        return root, code, capsys.readouterr().out

    # purlin: run_script PROOF-69
    def test_a_finding_blocks_at_strong(self, tmp_path, evidence_run, claude,
                                        capsys):
        _root, code, output = self._found_weak(tmp_path, evidence_run,
                                               claude, capsys)
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 1 passes its tests. 0 are strong.', 'Left to do:',
            '  1 rule to strengthen: purlin:build'], output
        assert code == 1, output

    # purlin: run_script PROOF-108
    def test_a_rule_found_weak_then_found_strong_meets_strong(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        root, _code, _output = self._found_weak(tmp_path, evidence_run,
                                                claude, capsys)
        install()
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert output.strip().splitlines()[-2:] == [
            '1 rule. 1 passes its tests. 1 is strong.',
            'Nothing left to do.'], output
        assert code == 0, output

    # purlin: run_script PROOF-109
    def test_a_failing_test_blocks_at_strong(self, tmp_path, evidence_run,
                                             claude, capsys):
        _install, directory = claude
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_bad():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert fake_claude.calls(directory) == []
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 0 pass their tests. 0 are strong.', 'Left to do:',
            '  1 rule to fix: purlin:build'], output
        assert code == 1, output

    # purlin: run_script PROOF-87
    def test_at_the_gate_passed_a_finding_blocks_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.'])
        root = _many(tmp_path, 1, gate='passed')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert output.strip().splitlines()[-2:] == [
            '1 rule. 1 passes its tests.', 'Nothing left to do.'], output
        assert _audited(root)['RULE-1']['findings'] == [
            'PROOF-1 reads the value alone.']
        assert code == 0, output

    # purlin: run_script PROOF-100
    def test_at_signed_the_audit_exits_on_what_it_answers_for(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install()
        root = _many(tmp_path, 1, gate='signed')
        # The spec's scope names a tracked file, so a signature can be tied.
        (root / 'src').mkdir()
        (root / 'src' / 'app.py').write_text('VALUE = 1\n', encoding='utf-8')
        _git_repo(root)
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        # The audit found the rule strong; no one has signed it, and an
        # audit cannot write a signature, so it exits 0.
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 1 passes its tests. 1 is strong. 0 are signed.',
            'Left to do:', '  1 rule to sign: purlin:sign'], output
        assert code == 0, output

    # purlin: run_script PROOF-111
    def test_a_failing_test_still_exits_one_at_passed(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert False\n'))
        _spec(root, 'feat')
        code, out = _run(root, '--all', '--audit')
        assert out.strip().splitlines()[-1] == (
            '  1 rule to fix: purlin:build'), out
        assert code == 1, out


# ---------------------------------------------------------------------------
# The pieces the run script owns, read directly
# ---------------------------------------------------------------------------

class TestTheEvidenceMeetsThePassedCell:
    """The walk from a test run to the gate, run for real against a git checkout.

    The evidence a run wrote meets the passed cell while its fingerprint is
    the one taken now. A person's own run is read like any other: it goes
    out of date when the scoped code, the spec or the tests change, whether
    or not the evidence was committed.
    """

    def _with_evidence(self, tmp_path, commit=True):
        root = _pytest_project(tmp_path)
        (root / 'src').mkdir()
        (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
        _spec(root, 'feat')
        _git_repo(root)
        seen = _head(root)
        args = ['--all', '--test'] + (['--commit'] if commit else [])
        code, out = _run(root, *args)
        assert code == 0, out
        return root, seen

    def _code_changed(self, tmp_path, committed):
        """Committed evidence, then the scoped file changed, and committed
        when `committed`. `(root, the sha the run started on)`."""
        root, seen = self._with_evidence(tmp_path)
        (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
        if committed:
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'change the scoped code')
        return root, seen

    # purlin: run_script PROOF-20
    def test_committed_evidence_makes_the_passed_cell_read_passed(
            self, tmp_path):
        root, _seen = self._with_evidence(tmp_path)
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    # purlin: run_script PROOF-162
    def test_uncommitted_evidence_makes_the_passed_cell_read_passed(
            self, tmp_path):
        root, _seen = self._with_evidence(tmp_path, commit=False)
        assert _git(root, 'status', '--porcelain', '--',
                    '.purlin/evidence').strip() != ''
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    # purlin: run_script PROOF-163
    def test_a_code_change_not_committed_leaves_the_cell_out_of_date(
            self, tmp_path):
        root, seen = self._code_changed(tmp_path, committed=False)
        rule = _rule(root, 'feat', 'RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell
        assert rule['flags']['out_of_date'] is True, rule

    # purlin: run_script PROOF-164
    def test_a_code_change_committed_leaves_the_cell_out_of_date(
            self, tmp_path):
        root, seen = self._code_changed(tmp_path, committed=True)
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell

    # purlin: run_script PROOF-165
    def test_the_next_run_clears_out_of_date(self, tmp_path):
        root, _seen = self._code_changed(tmp_path, committed=True)
        code, out = _run(root, '--all', '--test')
        assert code == 0, out
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    # purlin: run_script PROOF-166
    def test_a_spec_edit_leaves_the_cell_out_of_date(self, tmp_path):
        root, seen = self._with_evidence(tmp_path, commit=False)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'the software does thing 1', 'the software does thing one'),
            encoding='utf-8')
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['spec changed since %s' % seen[:7]], cell

    # purlin: run_script PROOF-167
    def test_a_test_edit_leaves_the_cell_out_of_date(self, tmp_path):
        root, seen = self._with_evidence(tmp_path, commit=False)
        test = root / 'tests' / 'test_feat.py'
        test.write_text(test.read_text(encoding='utf-8') + '\n# edited\n',
                        encoding='utf-8')
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['tests changed since %s' % seen[:7]], cell


class TestHostOs:

    @staticmethod
    def _on(monkeypatch, platform):
        purlin_run = _load_run_script()
        monkeypatch.setattr(sys, 'platform', platform)
        return purlin_run.host_os()

    # purlin: run_script PROOF-21
    def test_darwin_reads_macos(self, monkeypatch):
        assert self._on(monkeypatch, 'darwin') == 'macos'

    # purlin: run_script PROOF-122
    def test_win32_reads_windows(self, monkeypatch):
        assert self._on(monkeypatch, 'win32') == 'windows'

    # purlin: run_script PROOF-123
    def test_linux_reads_linux(self, monkeypatch):
        assert self._on(monkeypatch, 'linux') == 'linux'

    # purlin: run_script PROOF-124
    def test_any_other_system_reads_linux(self, monkeypatch):
        assert self._on(monkeypatch, 'freebsd14') == 'linux'


class TestTheRunScriptCarriesNoEmoji:

    # purlin: run_script PROOF-22
    def test_no_character_is_an_emoji(self):
        source = open(RUN_SCRIPT, encoding='utf-8').read()
        assert all(ord(character) < 0x1F000 for character in source)


class TestTheConsoleCodecNeverEndsTheRun:
    """A Windows console hands Python cp1252, which encodes none of the glyphs.

    The first status table then ends the run with `UnicodeEncodeError: 'charmap'
    codec can't encode characters`, which is how the first CI run of this
    workflow lost its Windows job. The run script reconfigures both streams to
    UTF-8 before it prints anything.
    """

    # purlin: run_script PROOF-57
    def test_a_cp1252_console_gets_the_glyphs_and_no_traceback(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        environment = dict(os.environ, PYTHONIOENCODING='cp1252')
        result = subprocess.run(
            [sys.executable, RUN_SCRIPT, '--project-root', str(root),
             '--all', '--test'],
            capture_output=True, encoding='utf-8', cwd=str(root),
            env=environment)
        output = result.stdout + result.stderr
        assert 'Traceback' not in output, output
        assert 'UnicodeEncodeError' not in output, output
        assert '\u2500' in output, output
        assert result.returncode == 0, output


def _tail(output, suite):
    """The lines a run printed between a suite's tail heading and its end."""
    lines = output.splitlines()
    start = lines.index('--- %s output (last 60 lines) ---' % suite)
    return lines[start + 1:lines.index('--- end of %s output ---' % suite)]


def _hundred_lines(tmp_path, gate='passed', proofs=(('PROOF-1', 'RULE-1', ''),)):
    """A project whose one shell test prints `line 1` to `line 100` and fails."""
    root = _project(tmp_path, tests=[suites.shell_suite()], gate=gate)
    _spec(root, 'feat', proofs=proofs)
    (root / 'tests').mkdir()
    (root / 'tests' / 'long.test.sh').write_text(
        '# purlin: feat PROOF-1\n'
        'for n in $(seq 1 100); do echo "line $n"; done\nexit 1\n',
        encoding='utf-8')
    return root


class TestAFailingSuiteStatesItsReason:
    """Everything a suite prints is captured, and a job log never shows it.

    The Linux job of the first CI runs reported a suite that exited 1 and one
    that was killed at the cap, and said nothing about either: the output had
    gone to `.purlin/runtime/run.log` on a runner that is thrown away. The tail
    goes to stdout as soon as the suite fails.
    """

    # purlin: run_script PROOF-58
    def test_a_failing_arm_prints_its_tail_before_the_table(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_bad():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        heading = '--- pytest output (last 60 lines) ---'
        assert heading in output, output
        assert '1 failed' in output, output
        assert output.index(heading) < output.index('Purlin status:'), output
        assert 'Evidence is missing' not in output, output
        assert any(line.startswith('1 failed')
                   for line in _tail(output, 'pytest')), output

    # purlin: run_script PROOF-168
    def test_only_the_last_60_lines_are_printed(self, tmp_path):
        root = _hundred_lines(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert _tail(output, 'shell') == [
            'line %d' % n for n in range(41, 101)], output
        assert (output.index('--- shell output (last 60 lines) ---')
                < output.index('Purlin status:')), output

    # purlin: run_script PROOF-169
    def test_a_killed_suite_prints_its_tail(self, tmp_path):
        root = _project(tmp_path, tests=[suites.shell_suite()])
        _spec(root, 'feat')
        (root / 'tests').mkdir()
        (root / 'tests' / 'slow.test.sh').write_text(
            '# purlin: feat PROOF-1\necho started\nsleep 5\n',
            encoding='utf-8')
        code, output = _run(root, '--all', '--test', '--arm-timeout', '1')
        assert code == 1, output
        assert 'started' in _tail(output, 'shell'), output
        assert (output.index('--- shell output (last 60 lines) ---')
                < output.index('Purlin status:')), output

    # purlin: run_script PROOF-170
    def test_an_arm_that_passed_prints_no_tail(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert 'output (last 60 lines)' not in output, output

    # purlin: run_script PROOF-59
    def test_ci_writes_the_whole_run_to_the_log_in_the_tree(
            self, tmp_path, evidence_run, capsys):
        """A run uploads nothing, so what it printed has to be in the tree."""
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_bad():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat', proofs=TAGGED_HERE)
        evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        log = root / '.purlin' / 'runtime' / 'run.log'
        text = log.read_text(encoding='utf-8')
        assert '-m pytest' in text, text
        assert '1 failed' in text, text

    @staticmethod
    def _logged(tmp_path, evidence_run, capsys, action):
        """The lines `line N` the run log holds after `action` over a shell
        test that prints `line 1` to `line 100` and fails."""
        root = _hundred_lines(tmp_path, gate='strong', proofs=(
            TAGGED_HERE if action == '--ci' else (('PROOF-1', 'RULE-1', ''),)))
        evidence_run(root, '--all', action)
        capsys.readouterr()
        lines = (root / '.purlin' / 'runtime' / 'run.log').read_text(
            encoding='utf-8').splitlines()
        return [line for line in lines if line.startswith('line ')]

    # purlin: run_script PROOF-171
    def test_ci_keeps_every_line_past_sixty_in_the_log(
            self, tmp_path, evidence_run, capsys):
        assert self._logged(tmp_path, evidence_run, capsys, '--ci') == [
            'line %d' % n for n in range(1, 101)]

    # purlin: run_script PROOF-172
    def test_the_audit_keeps_every_line_past_sixty_in_the_log(
            self, tmp_path, evidence_run, claude, capsys):
        assert self._logged(tmp_path, evidence_run, capsys, '--audit') == [
            'line %d' % n for n in range(1, 101)]


class TestAnEmptyProjectRootIsRefused:
    """`os.path.abspath('')` is the working directory, so an empty value would
    silently run against whatever tree the run was started in. A shell whose
    `mktemp` left a variable empty is how that happens."""

    # purlin: run_script PROOF-60
    def test_an_empty_project_root_exits_2_and_runs_nothing(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        result = subprocess.run(
            [sys.executable, RUN_SCRIPT, '--all', '--test',
             '--project-root', ''],
            capture_output=True, encoding='utf-8', cwd=str(root))
        output = result.stdout + result.stderr
        assert result.returncode == 2, output
        assert '--project-root' in output, output
        assert not (root / REPORTS_REL).exists(), output


# ---------------------------------------------------------------------------
# A run covers what the change touched
# ---------------------------------------------------------------------------

def _touched_project(tmp_path, names=('login', 'export'), gate='passed',
                     requires=None, failing=(),
                     proofs=(('PROOF-1', 'RULE-1', ''),)):
    """A committed checkout of features that each own one source file and
    one test file, run once with `--commit` so every feature has evidence.

    Returns `(root, sha)`, where `sha` is the commit that first run started
    on. A name in `failing` gets a test that fails.
    """
    root = _pytest_project(tmp_path, gate=gate, body='')
    (root / 'tests' / 'test_feat.py').unlink()
    (root / 'src').mkdir()
    for name in names:
        (root / 'src' / ('%s.py' % name)).write_text(
            'VALUE = 1\n', encoding='utf-8')
        (root / 'tests' / ('test_%s.py' % name)).write_text(
            'import pytest\n\n'
            '# purlin: %s PROOF-1\n'
            'def test_%s():\n'
            '    assert %s\n' % (name, name,
                                 '1 == 2' if name in failing else 'True'),
            encoding='utf-8')
        _spec(root, name, scope='src/%s.py' % name, requires=requires,
              proofs=proofs)
    _git_repo(root)
    sha = _head(root)
    _code, output = _run(root, '--test', '--commit')
    assert 'Evidence committed.' in output, output
    return root, sha


def _selection(output):
    """`{feature: reasons}` off the `Selected` line, or None when there is none."""
    for line in output.splitlines():
        if line.startswith('Selected '):
            listed = line.split(': ', 1)[1].rstrip('.')
            return dict(re.findall(r'(\w+) \(([^)]*)\)', listed))
    return None


def _file(root, rel):
    return (root / rel).read_bytes()


@pytest.fixture(scope='module')
def twelve_features(tmp_path_factory):
    """Twelve features, `f01` to `f12`, with committed evidence; `f01`'s
    source file changes and a `--test` with no feature named runs. `(sha the
    evidence was taken on, exit code, output)`."""
    names = tuple('f%02d' % index for index in range(1, 13))
    root, sha = _touched_project(tmp_path_factory.mktemp('twelve'),
                                 names=names)
    (root / 'src' / 'f01.py').write_text('VALUE = 2\n', encoding='utf-8')
    code, output = _run(root, '--test')
    return sha, code, output


class TestARunCoversWhatTheChangeTouched:
    """With no feature named, a run runs the features its change touched."""

    @staticmethod
    def _login_code_changed(tmp_path):
        """`src/login.py` changed after committed evidence, then a `--test`
        with no feature named. `(root, sha, export's evidence before, code,
        output)`."""
        root, sha = _touched_project(tmp_path)
        export = _file(root, '.purlin/evidence/local/export.json')
        (root / 'src' / 'login.py').write_text('VALUE = 2\n', encoding='utf-8')
        code, output = _run(root, '--test')
        return root, sha, export, code, output

    # purlin: run_script PROOF-88
    def test_a_code_edit_runs_only_the_feature_that_covers_the_file(
            self, tmp_path):
        root, sha, export, code, output = self._login_code_changed(tmp_path)
        assert code == 0, output
        assert _selection(output) == {
            'login': 'code changed since %s' % sha[:7]}, output
        assert _file(root, '.purlin/evidence/local/export.json') == export

    # purlin: run_script PROOF-97
    def test_a_narrow_run_hands_the_suite_only_its_features_test_files(
            self, tmp_path):
        root, _sha, _export, code, output = self._login_code_changed(tmp_path)
        assert code == 0, output
        assert _ran(root) == ['test_login'], output

    # purlin: run_script PROOF-89
    def test_a_spec_edit_selects_its_feature(self, tmp_path):
        root, sha = _touched_project(tmp_path)
        spec = root / 'specs' / 'a' / 'export.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing one'), encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'spec changed since %s' % sha[:7]}, output

    # purlin: run_script PROOF-187
    def test_a_test_edit_selects_its_feature(self, tmp_path):
        root, sha = _touched_project(tmp_path)
        test = root / 'tests' / 'test_export.py'
        test.write_text(test.read_text(encoding='utf-8') + '\n# edited\n',
                        encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'tests changed since %s' % sha[:7]}, output

    # purlin: run_script PROOF-90
    def test_an_anchor_edit_selects_every_feature_that_requires_it(
            self, tmp_path):
        root, sha = _touched_project(tmp_path, names=('login', 'export',
                                                      'solo'))
        anchors = root / 'specs' / '_anchors'
        anchors.mkdir()
        (anchors / 'shared.md').write_text(
            '# Anchor: shared\n\n## Rules\n\n- RULE-1: every answer is JSON\n'
            '\n## Proof\n\n- PROOF-1 (RULE-1): an answer parses as JSON\n',
            encoding='utf-8')
        for name in ('login', 'export'):
            _spec(root, name, scope='src/%s.py' % name, requires='shared')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'login and export require shared')
        _run(root, '--test', '--commit')
        assert _selection(_run(root, '--test')[1]) is None
        text = (anchors / 'shared.md').read_text(encoding='utf-8')
        (anchors / 'shared.md').write_text(
            text.replace('every answer is JSON', 'every answer is UTF-8 JSON'),
            encoding='utf-8')
        _code, output = _run(root, '--test')
        chosen = _selection(output)
        assert sorted(chosen) == ['export', 'login', 'shared'], output
        assert chosen['login'].startswith('spec changed since '), output
        assert chosen['export'].startswith('spec changed since '), output

    # purlin: run_script PROOF-91
    def test_a_feature_with_no_evidence_is_selected(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        (root / 'src' / 'invoice.py').write_text('VALUE = 1\n',
                                                 encoding='utf-8')
        (root / 'tests' / 'test_invoice.py').write_text(
            'import pytest\n\n'
            '# purlin: invoice PROOF-1\n'
            'def test_invoice():\n    assert True\n', encoding='utf-8')
        _spec(root, 'invoice', scope='src/invoice.py')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'invoice')
        code, output = _run(root, '--test')
        assert code == 0, output
        purlin_run = _load_run_script()
        assert _selection(output) == {
            'invoice': 'no run on %s yet' % purlin_run.host_os()}, output
        assert ('Skipped 2 features whose spec, code and tests match their '
                'evidence: export, login. purlin:test --all runs them too.'
                in output), output

    @staticmethod
    def _scopes_name_nothing(tmp_path):
        """`export` loses its `> Scope:` line and `login` scopes a file that
        does not exist, committed, then `--test --commit`. `(root, code,
        output)`."""
        root, _sha = _touched_project(tmp_path)
        _spec(root, 'export', scope=None)
        _spec(root, 'login', scope='src/nowhere.py')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'the scopes name nothing')
        code, output = _run(root, '--test', '--commit')
        return root, code, output

    # purlin: run_script PROOF-92
    def test_a_spec_that_names_no_files_is_selected(self, tmp_path):
        # This run also sees the code part move, since the files the scope
        # reaches changed; the reason every run gives comes last.
        _root, code, output = self._scopes_name_nothing(tmp_path)
        assert code == 0, output
        chosen = _selection(output)
        assert sorted(chosen) == ['export', 'login'], output
        for reasons in chosen.values():
            assert reasons.endswith('names no files, so every run includes '
                                    'it'), output

    # purlin: run_script PROOF-188
    def test_a_spec_that_names_no_files_is_selected_every_time(
            self, tmp_path):
        root, _code, _output = self._scopes_name_nothing(tmp_path)
        code, output = _run(root, '--test', '--commit')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'names no files, so every run includes it',
            'login': 'names no files, so every run includes it'}, output

    @staticmethod
    def _untracked_under_login(tmp_path):
        """`login` scopes `src/auth/` too, committed and current; then
        `src/auth/token.py` is written and not added. `(root, sha)`."""
        root, sha = _touched_project(tmp_path)
        # Naming a directory that holds no file yet leaves the fingerprint
        # as it was, so the section the first run wrote stands.
        _spec(root, 'login', scope='src/login.py, src/auth/')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'login covers src/auth/')
        assert 'Nothing to run' in _run(root, '--test')[1]
        (root / 'src' / 'auth').mkdir()
        (root / 'src' / 'auth' / 'token.py').write_text('KEY = 1\n',
                                                        encoding='utf-8')
        return root, sha

    # purlin: run_script PROOF-93
    def test_an_untracked_file_selects_the_feature_and_is_named(
            self, tmp_path):
        root, _sha = self._untracked_under_login(tmp_path)
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {'login': 'a file is not tracked'}, output
        assert ("src/auth/token.py is under login's scope and is not "
                'tracked, so its content is not part of the evidence until '
                'you git add it.') in output.splitlines(), output

    @staticmethod
    def _untracked_then_committed(tmp_path):
        root, sha = TestARunCoversWhatTheChangeTouched._untracked_under_login(
            tmp_path)
        _run(root, '--test')
        _git(root, 'add', 'src/auth/token.py')
        _git(root, 'commit', '-q', '-m', 'track the token')
        return root, sha

    # purlin: run_script PROOF-189
    def test_the_file_once_committed_selects_it_as_a_code_change(
            self, tmp_path):
        root, sha = self._untracked_then_committed(tmp_path)
        code, output = _run(root, '--test', '--commit')
        assert code == 0, output
        assert _selection(output) == {
            'login': 'code changed since %s' % sha[:7]}, output

    # purlin: run_script PROOF-190
    def test_the_run_after_that_has_nothing_to_run(self, tmp_path):
        root, _sha = self._untracked_then_committed(tmp_path)
        _run(root, '--test', '--commit')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert "Nothing to run: every feature's spec, code and tests " \
            'match its evidence. purlin:test --all runs them anyway.' \
            in output.splitlines(), output

    # purlin: run_script PROOF-94
    def test_the_selected_line_comes_before_the_suite_runs(
            self, twelve_features):
        sha, code, output = twelve_features
        assert code == 0, output
        lines = output.splitlines()
        selected = ('Selected 1 of 12 features: f01 (code changed since %s).'
                    % sha[:7])
        assert selected in lines, output
        assert lines.index(selected) < lines.index(
            'Running the pytest suite.'), output

    # purlin: run_script PROOF-205
    def test_the_skipped_line_names_ten_and_counts_the_rest(
            self, twelve_features):
        _sha, _code, output = twelve_features
        assert ('Skipped 11 features whose spec, code and tests match their '
                'evidence: f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, '
                'and 1 more. purlin:test --all runs them too.'
                in output.splitlines()), output

    # purlin: run_script PROOF-95
    def test_nothing_changed_runs_nothing_and_exits_on_the_gate(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        before = {name: _file(root, '.purlin/evidence/local/%s.json' % name)
                  for name in ('login', 'export')}
        code, output = _run(root, '--test')
        assert code == 0, output
        assert ("Nothing to run: every feature's spec, code and tests match "
                'its evidence. purlin:test --all runs them anyway.'
                in output.splitlines()), output
        assert 'Running the' not in output, output
        assert _selection(output) is None, output
        assert {name: _file(root, '.purlin/evidence/local/%s.json' % name)
                for name in ('login', 'export')} == before
        assert [line for line in output.splitlines() if line.strip()][-2:] == [
            '2 rules. 2 pass their tests.', 'Nothing left to do.'], output

    # purlin: run_script PROOF-112
    def test_nothing_changed_over_a_failing_test_exits_one(self, tmp_path):
        root, _sha = _touched_project(tmp_path, failing=('export',))
        code, output = _run(root, '--test')
        assert 'Nothing to run' in output, output
        assert [line for line in output.splitlines() if line.strip()][-3:] == [
            '2 rules. 1 passes its tests.', 'Left to do:',
            '  1 rule to fix: purlin:build'], output
        assert code == 1, output

    # purlin: run_script PROOF-96
    def test_commit_with_nothing_to_run_commits_the_last_run(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        (root / 'src' / 'login.py').write_text('VALUE = 2\n', encoding='utf-8')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'change login')
        _run(root, '--test')
        head = _head(root)
        code, output = _run(root, '--test', '--commit')
        assert code == 0, output
        assert 'Nothing to run' in output, output
        assert 'Evidence committed.' in output, output
        subject = _git(root, 'log', '-1', '--format=%s').strip()
        assert subject == 'purlin: evidence at %s' % head[:7], subject
        assert _git(root, 'status', '--porcelain', '--',
                    '.purlin/evidence').strip() == ''

    @staticmethod
    def _two_shell_scripts(tmp_path):
        """One shell suite over two scripts, one marked for `login` and one
        for `export`, each writing its feature's name to `ran.txt`."""
        root = _project(tmp_path, tests=[suites.shell_suite()])
        for name in ('login', 'export'):
            _spec(root, name)
            (root / ('%s.test.sh' % name)).write_text(
                '# purlin: %s PROOF-1\necho %s >> ran.txt\n' % (name, name),
                encoding='utf-8')
        return root

    # purlin: run_script PROOF-191
    def test_a_named_feature_runs_only_its_test_files(self, tmp_path):
        root = self._two_shell_scripts(tmp_path)
        code, output = _run(root, '--feature', 'login', '--test')
        assert code == 0, output
        assert (root / 'ran.txt').read_text(encoding='utf-8').split() == [
            'login'], output

    # purlin: run_script PROOF-192
    def test_a_run_over_every_feature_runs_the_suite_whole(self, tmp_path):
        root = self._two_shell_scripts(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert sorted((root / 'ran.txt').read_text(
            encoding='utf-8').split()) == ['export', 'login'], output

    # purlin: run_script PROOF-193
    def test_a_suite_with_none_of_the_features_tests_is_not_started(
            self, tmp_path):
        root = _project(tmp_path, tests=[
            suites.shell_suite(files=('login/*.test.sh',), name='logins'),
            suites.shell_suite(files=('export/*.test.sh',), name='exports')])
        for name in ('login', 'export'):
            _spec(root, name)
            (root / name).mkdir()
            (root / name / ('%s.test.sh' % name)).write_text(
                '# purlin: %s PROOF-1\necho %s >> ran.txt\n' % (name, name),
                encoding='utf-8')
        _code, output = _run(root, '--feature', 'login', '--test')
        assert 'Running the logins suite.' in output.splitlines(), output
        assert 'Running the exports suite.' not in output, output
        assert (root / 'ran.txt').read_text(encoding='utf-8').split() == [
            'login'], output

    # purlin: run_script PROOF-98
    def test_all_runs_every_feature_when_nothing_changed(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert 'Nothing to run' not in output, output
        assert _selection(output) is None, output
        assert 'Running the pytest suite.' in output, output
        assert _ran(root) == ['test_export', 'test_login'], output

    # purlin: run_script PROOF-194
    def test_ci_with_no_feature_named_runs_every_feature(
            self, tmp_path, evidence_run, capsys):
        root, _sha = _touched_project(tmp_path, proofs=TAGGED_HERE)
        code, calls = evidence_run(root, '--ci')
        output = capsys.readouterr().out
        assert code == 0, output
        assert [sorted(paths) for paths, _m, _merge in calls['commit']] == [
            ['.purlin/evidence/ci/export.json',
             '.purlin/evidence/ci/login.json']], output

    @staticmethod
    def _audited_once(tmp_path, evidence_run, capsys):
        """`login` and `export` at `strong`, committed and current evidence,
        then one `--audit` with no feature named. `(root, code, output)`."""
        root, _sha = _touched_project(tmp_path, gate='strong')
        code, _calls = evidence_run(root, '--audit')
        return root, code, capsys.readouterr().out

    # purlin: run_script PROOF-99
    def test_the_audit_with_nothing_selected_still_reads_every_rule(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        _root, code, output = self._audited_once(tmp_path, evidence_run,
                                                 capsys)
        assert 'Nothing to run' in output, output
        assert 'Running the' not in output, output
        assert 'AI audit: 2 rules to read, 2 at a time.' in output, output
        assert len(fake_claude.calls(directory)) == 2
        assert code == 0, output

    # purlin: run_script PROOF-195
    def test_a_second_audit_reads_nothing(self, tmp_path, evidence_run,
                                          claude, capsys):
        _install, directory = claude
        root, _code, _output = self._audited_once(tmp_path, evidence_run,
                                                  capsys)
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert ('AI audit: nothing to read; every rule matches its last '
                'audit.') in output, output
        assert len(fake_claude.calls(directory)) == 2
        assert code == 0, output

    # purlin: run_script PROOF-196
    def test_a_spec_edit_selects_and_reads_that_feature_alone(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root, _code, _output = self._audited_once(tmp_path, evidence_run,
                                                  capsys)
        spec = root / 'specs' / 'a' / 'login.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing one'), encoding='utf-8')
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert sorted(_selection(output)) == ['login'], output
        assert 'AI audit: 1 rule to read, 1 at a time.' in output, output
        assert len(fake_claude.calls(directory)) == 3
        assert code == 0, output


class TestAWeakRuleNotReadAgain:

    # purlin: run_script PROOF-125
    def test_an_audit_that_reads_nothing_exits_0(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.'])
        root = _many(tmp_path, 1)
        code, _calls = evidence_run(root, '--all', '--audit')
        assert code == 1, capsys.readouterr().out
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert 'AI audit: nothing to read' in output, output
        assert output.strip().splitlines()[-1] == (
            '  1 rule to strengthen: purlin:build'), output
        assert code == 0, output


# ---------------------------------------------------------------------------
# Before any test runs
# ---------------------------------------------------------------------------

# What each test tool leaves in a project, which is how the run finds it.
TOOLS = {
    'pytest': {'conftest.py': ''},
    'vitest': {'package.json': '{"devDependencies": {"vitest": "^1.0.0"}}'},
    'jest': {'package.json': '{"devDependencies": {"jest": "^29.0.0"}}'},
    'dotnet': {'App.Tests/App.Tests.csproj':
               '<Project><ItemGroup><PackageReference Include="xunit" '
               'Version="2.6.0" /></ItemGroup></Project>'},
    'go': {'go.mod': 'module example.com/shop\n',
           'cart/cart_test.go': 'package cart\n'},
    'sql': {'tests/test_orders.sql': 'SELECT 1;\n'},
    'shell': {'tests/login.test.sh': 'exit 0\n'},
}

ORDER = ('pytest', 'vitest', 'jest', 'dotnet', 'go', 'sql', 'shell')

_JS_GLOBS = ['**/*.%s.%s' % (kind, ext) for kind in ('test', 'spec')
             for ext in ('js', 'jsx', 'mjs', 'cjs', 'ts', 'tsx')]


def _no_command(tmp_path, *tools):
    """One spec, an empty `tests` setting, and what each of `tools` leaves."""
    root = _project(tmp_path, tests=[])
    _spec(root, 'feat')
    for tool in tools:
        for rel, body in TOOLS[tool].items():
            path = root.joinpath(*rel.split('/'))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding='utf-8')
    return root


def _purlin_files(root):
    return sorted(os.path.relpath(os.path.join(folder, name), str(root))
                  for folder, _dirs, names in os.walk(str(root / '.purlin'))
                  for name in names)


SUGGESTED_SETTING = 'Suggested tests setting: '


def _suggested(output):
    """The entries off the `Suggested tests setting:` line, or None."""
    for line in output.splitlines():
        if line.startswith(SUGGESTED_SETTING):
            return json.loads(line[len(SUGGESTED_SETTING):])
    return None


@pytest.fixture(scope='module')
def suggestions(tmp_path_factory):
    """`{tool: entry}`, what the run suggests in a project holding only what
    each of the seven tools leaves."""
    found = {}
    for tool in ORDER:
        root = _no_command(tmp_path_factory.mktemp(tool), tool)
        _code, output = _run(root, '--all', '--test')
        entries = _suggested(output)
        assert entries is not None and len(entries) == 1, output
        found[tool] = entries[0]
    return found


class TestNoTestCommand:

    # purlin: run_script PROOF-126
    def test_a_known_tool_gets_its_entry_suggested(self, tmp_path):
        root = _no_command(tmp_path, 'pytest')
        code, output = _run(root, '--all', '--test')
        entry = frameworks.entry_for('pytest')
        assert output.strip().splitlines()[-3:] == [
            'No test command is set in .purlin/config.json, so nothing ran.',
            'Suggested for pytest: python3 -m pytest --ignore=mutants '
            '{files} --junitxml={report}',
            'Suggested tests setting: %s' % json.dumps([entry])], output
        assert _purlin_files(root) == [
            os.path.join('.purlin', 'config.json')], output
        assert code == 1, output

    # purlin: run_script PROOF-127
    def test_no_known_tool_asks_for_a_proposal(self, tmp_path):
        root = _no_command(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-1] == (
            'No test command is set in .purlin/config.json, and no test tool '
            'Purlin knows was found, so nothing ran. Run purlin:test to have '
            'one proposed.'), output
        assert _purlin_files(root) == [
            os.path.join('.purlin', 'config.json')], output
        assert code == 1, output

    @staticmethod
    def _suggested_for(tmp_path, tool):
        """The entry the run suggests in a project holding only what `tool`
        leaves."""
        _code, output = _run(_no_command(tmp_path, tool), '--all', '--test')
        entries = _suggested(output)
        assert entries is not None and len(entries) == 1, output
        return entries[0]

    # purlin: run_script PROOF-128
    def test_pytest_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'pytest')['name'] == 'pytest'

    # purlin: run_script PROOF-197
    def test_vitest_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'vitest')['name'] == 'vitest'

    # purlin: run_script PROOF-198
    def test_jest_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'jest')['name'] == 'jest'

    # purlin: run_script PROOF-199
    def test_dotnet_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'dotnet')['name'] == 'dotnet'

    # purlin: run_script PROOF-200
    def test_go_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'go')['name'] == 'go'

    # purlin: run_script PROOF-201
    def test_sql_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'sql')['name'] == 'sql'

    # purlin: run_script PROOF-202
    def test_shell_is_suggested_its_own_entry(self, tmp_path):
        assert self._suggested_for(tmp_path, 'shell')['name'] == 'shell'

    # purlin: run_script PROOF-129
    def test_every_tool_found_is_suggested_in_the_order(self, tmp_path):
        root = _no_command(tmp_path, 'pytest', 'vitest')
        _code, output = _run(root, '--all', '--test')
        assert [entry['name'] for entry in _suggested(output)] == [
            'pytest', 'vitest'], output
        assert [line.split(':', 1)[0] for line in output.splitlines()
                if line.startswith('Suggested for ')] == [
            'Suggested for pytest', 'Suggested for vitest'], output

    # purlin: run_script PROOF-221
    def test_on_windows_the_pytest_command_starts_with_the_launcher(
            self, tmp_path):
        root = _no_command(tmp_path, 'pytest')
        (entry,) = frameworks.suggest(str(root), os_name='windows')
        assert entry['run'] == ('py -3 -m pytest --ignore=mutants {files} '
                                '--junitxml={report}')

    # purlin: run_script PROOF-130
    def test_each_command_carries_the_flag_that_writes_its_report(
            self, suggestions):
        expected = {
            'pytest': '--junitxml={report}',
            'vitest': '--outputFile.junit={report}',
            'jest': '--reporters=jest-junit',
            'dotnet': '--logger trx --results-directory {report}',
            'go': 'go test -json', 'sql': 'sqlite3 -bail',
            'shell': 'bash {files}'}
        assert sorted(suggestions) == sorted(expected)
        for name, flag in expected.items():
            assert flag in suggestions[name]['run'], name

    # purlin: run_script PROOF-131
    def test_each_format_and_report(self, suggestions):
        assert {name: (suggestions[name]['format'],
                       suggestions[name]['report'])
                for name in ORDER} == {
            'pytest': ('junit', '.purlin/runtime/reports/pytest.xml'),
            'vitest': ('junit', '.purlin/runtime/reports/vitest.xml'),
            'jest': ('junit', '.purlin/runtime/reports/jest.xml'),
            'dotnet': ('trx', '.purlin/runtime/reports/dotnet'),
            'go': ('gotest', '-'), 'sql': ('exit', None),
            'shell': ('exit', None)}

    # purlin: run_script PROOF-132
    def test_each_set_of_globs(self, suggestions):
        assert {name: suggestions[name]['files'] for name in ORDER} == {
            'pytest': ['**/test_*.py', '**/*_test.py'],
            'vitest': _JS_GLOBS, 'jest': _JS_GLOBS, 'dotnet': ['**/*.cs'],
            'go': ['**/*_test.go'],
            'sql': ['**/test_*.sql', '**/*_test.sql', '**/*.test.sql'],
            'shell': ['**/*.test.sh']}
        assert len(_JS_GLOBS) == 12

    # purlin: run_script PROOF-133
    def test_the_page_shows_the_same_entries(self, suggestions):
        with open(os.path.join(REPO, 'references', 'supported_frameworks.md'),
                  encoding='utf-8') as handle:
            page = handle.read()
        shown = [json.loads(block.split('```', 1)[0])
                 for block in page.split('```json\n')[1:]]
        assert shown == [suggestions[name] for name in ORDER]

    # purlin: run_script PROOF-134
    def test_jest_is_told_it_needs_jest_junit(self, tmp_path):
        _code, output = _run(_no_command(tmp_path, 'jest'), '--all', '--test')
        lines = output.strip().splitlines()
        assert lines[-3].startswith('Suggested for jest: '), output
        assert lines[-2] == ('jest needs the package jest-junit to write its '
                             'report: run npm install --save-dev jest-junit')

    # purlin: run_script PROOF-135
    def test_sql_is_told_it_runs_through_sqlite3(self, tmp_path):
        _code, output = _run(_no_command(tmp_path, 'sql'), '--all', '--test')
        lines = output.strip().splitlines()
        assert lines[-3].startswith('Suggested for sql: '), output
        assert lines[-2].startswith(
            'sql runs each test file through the sqlite3 command, and a test '
            'fails by raising an error'), output

    # purlin: run_script PROOF-136
    def test_pytest_needs_nothing_added(self, tmp_path):
        _code, output = _run(_no_command(tmp_path, 'pytest'), '--all',
                             '--test')
        lines = output.strip().splitlines()
        assert lines[-2].startswith('Suggested for pytest: '), output
        assert lines[-1].startswith(SUGGESTED_SETTING), output


class TestTheSettingsFile:

    # purlin: run_script PROOF-137
    def test_no_settings_file_stops_the_run(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        (root / '.purlin' / 'config.json').unlink()

        def tree():
            return {os.path.relpath(os.path.join(folder, name), str(root)):
                    open(os.path.join(folder, name), 'rb').read()
                    for folder, _dirs, names in os.walk(str(root))
                    for name in names}

        before = tree()
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines() == [
            'No .purlin/config.json here, so nothing ran. Run purlin:init to '
            'write it.'], output
        assert tree() == before
        assert code == 1, output

    # purlin: run_script PROOF-138
    def test_a_project_an_older_purlin_set_up_stops_the_run(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        (root / '.purlin' / 'config.json').write_text(
            json.dumps({'version': '0.9.2', 'gate': 'passed'}),
            encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines() == [
            'This project was set up by an older Purlin and not upgraded, so '
            'nothing ran. Run purlin:init --update.'], output
        assert _purlin_files(root) == [
            os.path.join('.purlin', 'config.json')], output
        assert code == 1, output

    @staticmethod
    def _stops(root):
        """`--all --test` stops on the upgrade line and writes nothing."""
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines() == [
            'This project was set up by an older Purlin and not upgraded, so '
            'nothing ran. Run purlin:init --update.'], output
        assert _purlin_files(root) == [
            os.path.join('.purlin', 'config.json')], output
        assert code == 1, output

    @classmethod
    def _key_only_095_wrote(cls, tmp_path, key):
        root = _project(tmp_path)
        _spec(root, 'feat')
        _config(root, **{key: 'pytest'})
        cls._stops(root)

    # purlin: run_script PROOF-214
    def test_the_key_test_framework_stops_the_run(self, tmp_path):
        self._key_only_095_wrote(tmp_path, 'test_framework')

    # purlin: run_script PROOF-215
    def test_the_key_spec_dir_stops_the_run(self, tmp_path):
        self._key_only_095_wrote(tmp_path, 'spec_dir')

    # purlin: run_script PROOF-216
    def test_the_key_pre_push_stops_the_run(self, tmp_path):
        self._key_only_095_wrote(tmp_path, 'pre_push')

    # purlin: run_script PROOF-217
    def test_the_key_report_stops_the_run(self, tmp_path):
        self._key_only_095_wrote(tmp_path, 'report')

    # purlin: run_script PROOF-218
    def test_the_key_digest_stops_the_run(self, tmp_path):
        self._key_only_095_wrote(tmp_path, 'digest')

    @classmethod
    def _file_only_095_wrote(cls, tmp_path, name):
        root = _project(tmp_path)
        _spec(root, 'feat')
        (root / 'specs' / 'a' / name).write_text('{}\n', encoding='utf-8')
        cls._stops(root)

    # purlin: run_script PROOF-219
    def test_a_proof_file_under_specs_stops_the_run(self, tmp_path):
        self._file_only_095_wrote(tmp_path, 'feat.proofs-unit.json')

    # purlin: run_script PROOF-220
    def test_a_receipt_file_under_specs_stops_the_run(self, tmp_path):
        self._file_only_095_wrote(tmp_path, 'feat.receipt.json')


class TestEachRuleThatFailsOrHasNoTest:

    # purlin: run_script PROOF-139
    def test_a_failing_rule_is_named_with_its_test(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            '# purlin: feat PROOF-1\n'
            'def test_no():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        _code, output = _run(root, '--all', '--test')
        line = ('feat RULE-1 fails: tests/test_feat.py::test_no. Run '
                'purlin:build feat.')
        lines = output.splitlines()
        assert line in lines, output
        assert lines.index(line) < lines.index(
            next(text for text in lines if text.startswith('Purlin status:')))

    # purlin: run_script PROOF-140
    def test_a_rule_with_no_test_is_named(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),))
        _code, output = _run(root, '--all', '--test')
        line = 'feat RULE-2 has no test. Run purlin:build feat.'
        lines = output.splitlines()
        assert line in lines, output
        assert lines.index(line) < lines.index(
            next(text for text in lines if text.startswith('Purlin status:')))
        assert not [text for text in lines if text.startswith('feat RULE-1 ')]

    # purlin: run_script PROOF-212
    def test_a_rule_with_a_proof_no_test_carries_names_that_proof(
            self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', '')))
        _code, output = _run(root, '--all', '--test')
        line = 'feat RULE-1 has no test for PROOF-2. Run purlin:build feat.'
        lines = output.splitlines()
        assert line in lines, output
        assert lines.index(line) < lines.index(
            next(text for text in lines if text.startswith('Purlin status:')))

    # purlin: run_script PROOF-210
    def test_a_proof_for_another_system_with_no_test_is_named(self, tmp_path):
        other = 'windows' if HERE_OS != 'windows' else 'linux'
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', rules=2, proofs=(
            ('PROOF-1', 'RULE-1', ''),
            ('PROOF-2', 'RULE-2', ' @env(%s)' % other)))
        _code, output = _run(root, '--all', '--test')
        lines = output.splitlines()
        assert 'feat RULE-2 has no test. Run purlin:build feat.' in lines, \
            output
        assert not [text for text in lines if ' need' in text], output

    # purlin: run_script PROOF-141
    def test_a_feature_not_run_is_not_named(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _spec(root, 'other')
        _code, output = _run(root, '--feature', 'feat', '--test')
        assert 'other RULE-1' not in output, output


class TestTheTwoCommits:

    @staticmethod
    def _checkout(tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        (root / '.gitignore').write_text('.purlin/runtime/\n__pycache__/\n'
                                         '.pytest_cache/\n', encoding='utf-8')
        _git_repo(root)
        return root

    def _work_changed(self, tmp_path):
        """The spec, its marked test file and the settings each changed and
        not committed, then `--all --test --commit`. `(root, output)`."""
        root = self._checkout(tmp_path)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8') + '\n',
                        encoding='utf-8')
        test = root / 'tests' / 'test_feat.py'
        test.write_text(test.read_text(encoding='utf-8') + '# edited\n',
                        encoding='utf-8')
        _config(root, min_strength=80)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        return root, output

    # purlin: run_script PROOF-203
    def test_the_first_commit_is_named_for_the_work(self, tmp_path):
        root, output = self._work_changed(tmp_path)
        assert _git(root, 'log', '-1', '--format=%s', 'HEAD~1').strip() == (
            'purlin: specs, tests and settings for feat'), output

    # purlin: run_script PROOF-204
    def test_the_run_lists_each_file_of_the_first_commit(self, tmp_path):
        root, output = self._work_changed(tmp_path)
        first = _git(root, 'rev-parse', 'HEAD~1').strip()
        lines = output.splitlines()
        heading = 'Committed %s, the work these results describe:' % first[:7]
        assert heading in lines, output
        start = lines.index(heading) + 1
        assert lines[start:start + 3] == [
            '  .purlin/config.json', '  specs/a/feat.md',
            '  tests/test_feat.py'], output
        assert not lines[start + 3].startswith('  '), output

    # purlin: run_script PROOF-142
    def test_the_work_is_committed_before_the_evidence(self, tmp_path):
        root, output = self._work_changed(tmp_path)
        first = _git(root, 'rev-parse', 'HEAD~1').strip()
        assert sorted(_git(root, 'show', '--format=', '--name-only',
                           'HEAD~1').split()) == [
            '.purlin/config.json', 'specs/a/feat.md',
            'tests/test_feat.py'], output
        assert _git(root, 'log', '-1', '--format=%s').strip() == (
            'purlin: evidence at %s' % first[:7]), output
        assert sorted(_git(root, 'show', '--format=', '--name-only',
                           'HEAD').split()) == [
            '.purlin/evidence/local/feat.json', '.purlin/tests.md'], output

    # purlin: run_script PROOF-143
    def test_a_clean_checkout_gets_one_commit(self, tmp_path):
        root = self._checkout(tmp_path)
        head = _head(root)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert _git(root, 'rev-parse', 'HEAD~1').strip() == head, output
        assert _git(root, 'log', '-1', '--format=%s').strip() == (
            'purlin: evidence at %s' % head[:7]), output
        assert _git(root, 'status', '--porcelain', '--',
                    '.purlin/evidence').strip() == '', output
