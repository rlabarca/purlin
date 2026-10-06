"""Tests for `scripts/run/purlin_run.py`, the one run script.

Every test builds a throwaway project under `tmp_path` and drives the real
script against it: the suites it runs, the two loud failures it raises, the
proofs another operating system owns, the exit codes, the evidence each run
writes and where it is committed. `scripts/run/evidence.py` has tests of its
own for the file's shape and the merge.
"""

import importlib
import json
import os
import platform
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
from purlin import status as purlin_status  # noqa: E402
from run_project import (RUN_SCRIPT, _project,  # noqa: E402,F401
                         _pytest_project, _run, _spec, claude)

# The system this machine is, and a feature's one proof tagged for it: a
# `--ci` run starts only the tests tied to proofs tagged for its system, so
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


def _script(path, text):
    """Write a shell script whose lines end in `\\n` alone.

    A file written as text on Windows ends each line in `\\r\\n`, which bash
    reads as part of the command: `sleep 5\\r` is refused and
    `echo x >> ran.txt\\r` names another file.
    """
    path.write_bytes(text.encode('utf-8'))


def _config(root, **fields):
    """Set keys in the project's `.purlin/config.json`, written back indented,
    so the file changes even where no key does."""
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


def _started(output):
    """The suites a run said it started, in order, off its `Running` lines."""
    return [line[len('Running '):].split(':', 1)[0]
            for line in output.splitlines() if line.startswith('Running ')]


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

def _refused(tmp_path, *args):
    """Run with `args`; assert exit 2 and the usage line; return the output."""
    code, output = _run(_project(tmp_path), *args)
    assert code == 2, output
    assert any(line.startswith('Usage: purlin_run.py')
               for line in output.splitlines()), output
    return output


class TestTheCommandLine:
    """A bad invocation exits 2 and says which part was wrong."""

    # purlin: run_script PROOF-1
    def test_no_action_is_refused(self, tmp_path):
        code, output = _run(_project(tmp_path))
        lines = output.splitlines()
        assert code == 2, output
        # The `purlin:` line first, then the usage line, and one of each.
        assert lines[0] == (
            'purlin: name exactly one of --test, --audit and --ci.'), output
        assert lines[1].startswith('Usage: purlin_run.py'), output
        assert [index for index, line in enumerate(lines)
                if line.startswith(('purlin:', 'Usage:'))] == [0, 1], output

    @staticmethod
    def _asked_for_help(tmp_path, flag):
        """Run with `flag` alone. `(exit code, stdout, stderr)`."""
        result = subprocess.run(
            [sys.executable, RUN_SCRIPT, flag], capture_output=True,
            encoding='utf-8', cwd=str(_project(tmp_path)))
        return result.returncode, result.stdout, result.stderr

    def _helped(self, tmp_path, flag):
        code, stdout, stderr = self._asked_for_help(tmp_path, flag)
        assert code == 0, stdout + stderr
        assert stdout.splitlines()[0].startswith('Usage: purlin_run.py'), \
            stdout
        assert not [line for line in (stdout + stderr).splitlines()
                    if line.startswith('purlin:')], stdout + stderr

    # purlin: run_script PROOF-235
    def test_help_prints_the_usage_and_exits_0(self, tmp_path):
        self._helped(tmp_path, '--help')

    # purlin: run_script PROOF-2
    def test_an_unknown_feature_exits_two(self, tmp_path):
        root = _project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--feature', 'nosuch', '--test')
        assert code == 2
        assert ('purlin: no spec named nosuch under specs/. Run purlin:status '
                'to see the specs this project has.'
                in output.splitlines()), output

    # purlin: run_script PROOF-284
    def test_an_empty_project_root_is_refused_and_nothing_is_written(
            self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        before = _purlin_files(root)
        result = subprocess.run(
            [sys.executable, RUN_SCRIPT, '--all', '--test',
             '--project-root', ''],
            capture_output=True, encoding='utf-8', cwd=str(root))
        output = result.stdout + result.stderr
        assert result.returncode == 2, output
        assert ('purlin: --project-root needs a directory, not an empty '
                'value.') in output.splitlines(), output
        assert len(before) == 1 and _purlin_files(root) == before


# ---------------------------------------------------------------------------
# --test, per framework
# ---------------------------------------------------------------------------

class TestTheTestArmRunsEachSuite:
    """`--test` runs each suite the settings name and writes the evidence."""

    # purlin: run_script PROOF-3
    def test_one_passing_marked_test_is_the_one_result_for_this_machine(
            self, tmp_path):
        """The one spec `feat`, one passing test marked with its PROOF-1:
        `--all --test` exits 0 and this machine's section lists exactly
        `PROOF-1` of `RULE-1`, `pass`, under `tests/test_feat.py::test_ok`."""
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
        # Nothing was marked, so nothing went missing: the status table is
        # what says the rule has no test.
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

    # purlin: run_script PROOF-244
    def test_one_marker_with_no_result_names_the_check_to_make(
            self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            '@pytest.mark.skip(reason="no tool here")\n'
            'def test_skipped():\n'
            '    assert True\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert ('Evidence is missing: 1 marker has no passing or failing '
                'result: feat PROOF-1 at tests/test_feat.py:3. Check that its '
                'test ran and was not skipped, then run purlin:test.'
                in output.splitlines()), output

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

    # purlin: run_script PROOF-274
    def test_an_anchor_test_with_nothing_to_check_is_not_missing(
            self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: shared PROOF-1\n'
            'def test_every_screen_has_a_title():\n'
            '    pytest.skip("nothing to check: this project has no '
            'screens")\n'))
        (root / 'specs' / '_anchors').mkdir()
        (root / 'specs' / '_anchors' / 'shared.md').write_text(
            '# Anchor: shared\n\n## Rules\n\n- RULE-1: every screen has a '
            'title\n\n## Proof\n\n- PROOF-1 (RULE-1): each screen in the '
            'project shows a title\n', encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        assert 'Evidence is missing' not in output, output
        assert 'has no passing or failing result' not in output, output
        assert code == 0, output


class TestATestCommentToCorrect:

    # purlin: run_script PROOF-271
    def test_a_reworded_proof_is_named_straight_after_markers_before_ran(
            self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _git_repo(root)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'observe thing', 'observe the thing'), encoding='utf-8')
        _git(root, 'commit', '-q', '-am', 'reword feat PROOF-1')
        code, output = _run(root, '--all', '--test')
        lines = output.splitlines()
        markers = next(index for index, line in enumerate(lines)
                       if line.startswith('Markers: '))
        named = [index for index, line in enumerate(lines) if line.startswith(
            'tests/test_feat.py:3 names feat PROOF-1, whose wording changed '
            'after the test was last changed in')]
        # The run's own line, straight after `Markers:`. The status the run
        # ends on names the comment again further down, so a line anywhere
        # after `Markers:` would not show the run printed one.
        assert named and named[0] == markers + 1, output
        # Before the suite's own closing line, which is printed once.
        ran = [index for index, line in enumerate(lines)
               if line == 'Ran pytest on 1 feature.']
        assert len(ran) == 1 and named[0] < ran[0], output
        assert code == 0, output


# ---------------------------------------------------------------------------
# Proofs another operating system owns
# ---------------------------------------------------------------------------

class TestEnvScopedProofs:
    """`@env` for another operating system is listed, never run, never missing."""

    def _other_os(self):
        """Windows here, and macOS on Windows, the system its proof names."""
        return 'windows' if not sys.platform.startswith('win') else 'macos'

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
        assert ('1 proof needs %s; this machine is %s. Run purlin:test on '
                '%s.' % (purlin_evidence.os_word(other),
                         purlin_evidence.os_word(here),
                         purlin_evidence.os_word(other))
                in output.splitlines()), output
        assert 'Evidence is missing' not in output, output
        assert [(entry['id'], entry['result'])
                for entry in _proofs(root, 'feat')] == [
            ('PROOF-1', 'pass'), ('PROOF-2', 'not run')], output
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['platforms'][here]['word'] == 'passed', cell

    # purlin: run_script PROOF-115
    def test_an_env_proof_for_this_os_is_run_normally(self, tmp_path):
        purlin_run = _load_run_script()
        here = purlin_run.host_os()
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ' @env(%s)' % here),))
        code, output = _run(root, '--all', '--test')
        assert not [line for line in output.splitlines()
                    if re.match(r'\d+ proofs? needs? ', line)], output
        assert _proofs(root, 'feat') is not None, output
        assert [(entry['id'], entry['result'], entry['env'])
                for entry in _proofs(root, 'feat')] == [
            ('PROOF-1', 'pass', here)], output
        assert code == 0, output


# ---------------------------------------------------------------------------
# The state table and the next step
# ---------------------------------------------------------------------------

class TestEveryRunEndsOnTheSummary:

    # purlin: run_script PROOF-103
    def test_a_run_over_one_feature_answers_for_the_project(self, tmp_path):
        """`--feature feat --test` over two specs of one rule each, `feat`'s
        test passing and `other`'s rule with none, counts both rules."""
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _spec(root, 'other')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert output.strip().splitlines()[-3:] == [
            '2 rules. 1 passes its tests.', 'Left to do:',
            '  1 rule to write a test for: purlin:build'], output
        assert code == 0, output

    # purlin: run_script PROOF-105
    def test_a_failing_rule_is_left_to_fix(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-3:] == [
            '1 rule. 0 pass their tests.', 'Left to do:',
            '  1 rule to fix: purlin:build'], output
        assert code == 1, output

    # purlin: run_script PROOF-222
    def test_a_file_not_yet_written_is_named_and_the_tests_still_run(
            self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            '# purlin: login PROOF-1\n'
            'def test_login():\n'
            '    assert True\n'))
        (root / 'src').mkdir()
        (root / 'src' / 'login.py').write_text('VALUE = 1\n',
                                               encoding='utf-8')
        _spec(root, 'login', scope='src/login.py, src/gone.py')
        _git_repo(root)
        code, output = _run(root, '--all', '--test')
        lines = output.splitlines()
        assert ('login: 1 file its scope names is not written yet: '
                'src/gone.py. Run purlin:build login, or correct the path '
                'with purlin:spec login.') in lines, output
        assert _started(output) == ['pytest'], output
        assert _proofs(root, 'login') == [{
            'id': 'PROOF-1', 'rule': 'RULE-1', 'result': 'pass', 'env': None,
            'manual': False, 'test': 'tests/test_feat.py::test_login'}], output
        assert code == 0, output


# ---------------------------------------------------------------------------
# The evidence, the audit and the `--ci` run
# ---------------------------------------------------------------------------

def _load_run_script():
    """The run script as a module, with its own sys.path set up."""
    for path in (os.path.join(REPO, 'scripts', 'run'),
                 os.path.join(REPO, 'scripts', 'mcp')):
        if path not in sys.path:
            sys.path.insert(0, path)
    import purlin_run

    return purlin_run


def _evidence(root, feature='feat', source='local'):
    path = root / '.purlin' / 'evidence' / source / ('%s.json' % feature)
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture
def evidence_run():
    """Run the script in this process, so a test reads what it printed
    through `capsys`. The exit code."""

    def go(root, *args):
        purlin_run = _load_run_script()
        return purlin_run.main(['--project-root', str(root)] + list(args))

    return go


class TestTheCiArmWritesItsSection:
    """A `--ci` run writes its own operating system's section under `ci/`."""

    @staticmethod
    def _ci(tmp_path):
        """A git checkout of `feat`, its one proof tagged for this
        machine's system and its test passing."""
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=TAGGED_HERE)
        _git_repo(root)
        return root

    # purlin: run_script PROOF-12
    def test_the_ci_arm_writes_its_section_and_commits_nothing(
            self, tmp_path, evidence_run, capsys):
        root = self._ci(tmp_path)
        head = _head(root)
        code = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        data = _evidence(root, source='ci')
        assert list(data['platforms']) == [HERE_OS]
        section = data['platforms'][HERE_OS]
        assert platform.node()
        assert section['machine'] == platform.node(), section
        assert section['rules'] == {'RULE-1': 'passed'}
        assert ('Evidence written to .purlin/evidence/ci/feat.json.'
                in output.splitlines()), output
        assert not (root / '.purlin' / 'evidence' / 'local').exists()
        assert _head(root) == head, 'the run made a commit'
        assert code == 0, output

    # purlin: run_script PROOF-117
    def test_another_systems_section_is_left_and_this_hosts_is_added(
            self, tmp_path, evidence_run, capsys):
        root = self._ci(tmp_path)
        other = 'windows' if HERE_OS != 'windows' else 'linux'
        theirs = {'commit': 'b' * 40, 'dirty': False,
                  'at': '2026-09-01T00:00:00Z', 'runner': 'runner',
                  'email': 'runner@example.com', 'machine': 'build-7',
                  'fingerprint': {'spec': 's', 'code': 'c', 'tests': 't'},
                  'rules': {'RULE-1': 'passed'}, 'proofs': []}
        path = root / '.purlin' / 'evidence' / 'ci' / 'feat.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            'schema': purlin_evidence.SCHEMA, 'feature': 'feat',
            'source': 'ci', 'spec': 'specs/feat.md',
            'platforms': {other: theirs}}), encoding='utf-8')
        evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        platforms = _evidence(root, source='ci')['platforms']
        assert sorted(platforms) == sorted([HERE_OS, other]), output
        assert platforms[other] == theirs, platforms[other]
        # The section added is this machine's own: its host name, not the
        # other section's.
        assert platform.node() and platform.node() != theirs['machine']
        assert platforms[HERE_OS]['machine'] == platform.node(), platforms
        assert platforms[HERE_OS]['rules'] == {'RULE-1': 'passed'}, platforms

    # purlin: run_script PROOF-209
    def test_an_untagged_test_that_fails_beside_a_tagged_one_does_not_fail_it(
            self, tmp_path, evidence_run, capsys):
        """`feat`'s PROOF-1 (RULE-1) carries no tag and its test fails;
        PROOF-2 (RULE-2) is tagged for this machine's system and its test,
        in the same file, passes."""
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_untagged():\n'
            '    assert 1 == 2\n\n'
            '# purlin: feat PROOF-2\n'
            'def test_tagged():\n'
            '    assert True\n'))
        _spec(root, 'feat', rules=2, proofs=(
            ('PROOF-1', 'RULE-1', ''),
            ('PROOF-2', 'RULE-2', ' @env(%s)' % HERE_OS)))
        _git_repo(root)
        code = evidence_run(root, '--all', '--ci')
        assert code == 0, capsys.readouterr().out

    # purlin: run_script PROOF-283
    def test_a_tagged_test_that_fails_exits_1_and_is_written_as_failed(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_untagged():\n'
            '    assert True\n\n'
            '# purlin: feat PROOF-2\n'
            'def test_tagged():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat', proofs=(
            ('PROOF-1', 'RULE-1', ''),
            ('PROOF-2', 'RULE-1', ' @env(%s)' % HERE_OS)))
        _git_repo(root)
        code = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert code == 1, output
        section = _evidence(root, source='ci')['platforms'][HERE_OS]
        assert [(entry['id'], entry['result'])
                for entry in section['proofs']] == [('PROOF-2', 'fail')]
        assert section['rules'] == {'RULE-1': 'failed'}, section


class TestWhereEachArmWrites:

    # purlin: run_script PROOF-17
    def test_a_test_run_writes_nothing_under_ci(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _git_repo(root)
        evidence_run(root, '--all', '--test', '--commit')
        output = capsys.readouterr().out
        assert 'Evidence committed.' in output.splitlines(), output
        assert not (root / '.purlin' / 'evidence' / 'ci').exists()

    # purlin: run_script PROOF-102
    def test_a_ci_run_calls_no_model_and_writes_no_audit(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=TAGGED_HERE)
        code = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert code == 0, output
        assert fake_claude.calls(directory) == []
        assert 'audit' not in _evidence(root, source='ci')


# ---------------------------------------------------------------------------
# The audit's exit code
# ---------------------------------------------------------------------------

class TestTheAuditExitCode:
    """Nothing the audit found makes it exit 1: only the tests set the code."""

    # purlin: run_script PROOF-109
    def test_a_failing_test_is_left_to_fix(self, tmp_path, evidence_run,
                                           claude, capsys):
        # `--audit` as the proof gives it, with no feature named and no
        # `--all`, and then over every feature: each ends the same way.
        for flags in (('--audit',), ('--all', '--audit')):
            root = _pytest_project(tmp_path / flags[0].strip('-'), body=(
                'import pytest\n\n'
                '# purlin: feat PROOF-1\n'
                'def test_bad():\n'
                '    assert 1 == 2\n'))
            _spec(root, 'feat')
            code = evidence_run(root, *flags)
            output = capsys.readouterr().out
            assert output.strip().splitlines()[-1] == (
                '  1 rule to fix: purlin:build'), (flags, output)
            assert code == 1, (flags, output)

    # purlin: run_script PROOF-87
    def test_a_test_with_no_assertion_is_left_to_strengthen(
            self, tmp_path, evidence_run, claude, capsys):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    total = 1 + 1\n'))
        _spec(root, 'feat')
        code = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert output.strip().splitlines()[-1] == (
            '  1 rule to strengthen: purlin:build'), output
        assert code == 0, output


# ---------------------------------------------------------------------------
# The pieces the run script owns, read directly
# ---------------------------------------------------------------------------

class TestTheEvidenceMeetsThePassedCell:
    """The walk from a test run to the passed cell, run for real against a git
    checkout.

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

    def _after_a_code_change(self, tmp_path, committed):
        """Committed evidence, then the scoped file changed, and committed
        when `committed`. `(root, the sha the run started on)`."""
        root, seen = self._with_evidence(tmp_path)
        (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
        if committed:
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'change the scoped code')
        return root, seen

    # purlin: run_script PROOF-163
    def test_a_code_change_not_committed_leaves_the_cell_out_of_date(
            self, tmp_path):
        root, seen = self._after_a_code_change(tmp_path, committed=False)
        rule = _rule(root, 'feat', 'RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell
        assert rule['flags']['out_of_date'] is True, rule

    # purlin: run_script PROOF-165
    def test_the_next_run_clears_out_of_date(self, tmp_path):
        """After `--all --test --commit` and a change to `src/feat.py`, left
        uncommitted, a further `--all --test` reads `passed` again."""
        root, _seen = self._after_a_code_change(tmp_path, committed=False)
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


class TestTheConsoleCodecNeverEndsTheRun:
    """A Windows console hands Python cp1252, which encodes none of the glyphs.

    The first status table would then end the run with `UnicodeEncodeError:
    'charmap' codec can't encode characters`. The run script reconfigures both
    streams to UTF-8 before it prints anything.
    """

    # purlin: run_script PROOF-57
    # purlin: run_script PROOF-229
    def test_a_cp1252_console_gets_the_glyphs_and_no_traceback(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        # On Windows the default is the real one: Python writes to a pipe in
        # the system's own code page, cp1252 on a Western install, unless
        # it is told otherwise. Elsewhere cp1252 is forced.
        environment = dict(os.environ)
        if os.name == 'nt':
            for name in ('PYTHONIOENCODING', 'PYTHONUTF8'):
                environment.pop(name, None)
        else:
            environment['PYTHONIOENCODING'] = 'cp1252'
        result = subprocess.run(
            [sys.executable, RUN_SCRIPT, '--project-root', str(root),
             '--all', '--test'],
            capture_output=True, encoding='utf-8', errors='replace',
            cwd=str(root), env=environment)
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


def _hundred_lines(tmp_path):
    """A project whose one shell test prints `line 1` to `line 100` and
    fails, its proof tagged for this machine's system."""
    root = _project(tmp_path, tests=[suites.shell_suite()])
    _spec(root, 'feat', proofs=TAGGED_HERE)
    (root / 'tests').mkdir()
    _script(root / 'tests' / 'long.test.sh',
            '# purlin: feat PROOF-1\n'
            'for n in $(seq 1 100); do echo "line $n"; done\nexit 1\n')
    return root


class TestAFailingSuiteStatesItsReason:
    """Everything a suite prints is captured, and a job log never shows it.

    A suite that exits 1, or is killed at the cap, would otherwise say nothing
    in a pipeline's job log: its output goes to `.purlin/runtime/run.log`, on a
    machine that is thrown away. The tail goes to stdout as soon as the suite
    fails.
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
        lines = output.splitlines()
        heading = '--- pytest output (last 60 lines) ---'
        end = '--- end of pytest output ---'
        status = next(index for index, line in enumerate(lines)
                      if line.startswith('Purlin status:'))
        assert lines.index(heading) < lines.index(end) < status, output
        assert any(line.startswith('1 failed')
                   for line in _tail(output, 'pytest')), output

    # purlin: run_script PROOF-242
    def test_a_killed_suite_names_the_longer_limit_to_run(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import time\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_slow():\n'
            '    time.sleep(5)\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test', '--arm-timeout', '1')
        assert code == 1, output
        assert ('Evidence is missing: the pytest suite timed out after 1 s. '
                'Run purlin:test --arm-timeout <seconds> to give it longer.'
                in output.splitlines()), output

    # purlin: run_script PROOF-171
    def test_ci_keeps_every_line_past_sixty_in_the_log(
            self, tmp_path, evidence_run, capsys):
        root = _hundred_lines(tmp_path)
        evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        lines = (root / '.purlin' / 'runtime' / 'run.log').read_text(
            encoding='utf-8').splitlines()
        assert [line for line in lines if line.startswith('line ')] == [
            'line %d' % n for n in range(1, 101)]


# ---------------------------------------------------------------------------
# A run covers what the change touched
# ---------------------------------------------------------------------------

def _touched_project(tmp_path, names=('login', 'export')):
    """A committed checkout of features that each own one source file and
    one test file, run once with `--commit` so every feature has evidence.

    Returns `(root, sha)`, where `sha` is the commit that first run started
    on.
    """
    root = _pytest_project(tmp_path, body='')
    (root / 'tests' / 'test_feat.py').unlink()
    # What `purlin:init` has git ignore, so a run leaves nothing uncommitted
    # and its results are ones a sign-off counts.
    (root / '.gitignore').write_text('.purlin/runtime/\n__pycache__/\n'
                                     '.pytest_cache/\n', encoding='utf-8')
    (root / 'src').mkdir()
    for name in names:
        (root / 'src' / ('%s.py' % name)).write_text(
            'VALUE = 1\n', encoding='utf-8')
        (root / 'tests' / ('test_%s.py' % name)).write_text(
            'import pytest\n\n'
            '# purlin: %s PROOF-1\n'
            'def test_%s():\n'
            '    assert True\n' % (name, name), encoding='utf-8')
        _spec(root, name, scope='src/%s.py' % name)
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
    def _login_after_a_code_change(tmp_path):
        """`src/login.py` changed after committed evidence, then a `--test`
        with no feature named. `(root, sha, export's evidence before, code,
        output)`."""
        root, sha = _touched_project(tmp_path)
        export = _file(root, '.purlin/evidence/local/export.json')
        (root / 'src' / 'login.py').write_text('VALUE = 2\n', encoding='utf-8')
        code, output = _run(root, '--test')
        return root, sha, export, code, output

    # purlin: run_script PROOF-88
    def test_a_code_edit_selects_and_runs_alone_the_feature_that_covers_it(
            self, tmp_path):
        root, sha, export, code, output = self._login_after_a_code_change(tmp_path)
        assert code == 0, output
        assert _selection(output) == {
            'login': 'code changed since %s' % sha[:7]}, output
        # Selected alone is run alone: login's one test and no other.
        assert _ran(root) == ['test_login'], output
        assert 'Ran pytest on 1 feature.' in output.splitlines(), output
        assert _file(root, '.purlin/evidence/local/export.json') == export

    # purlin: run_script PROOF-89
    def test_a_spec_edit_selects_its_feature(self, tmp_path):
        root, sha = _touched_project(tmp_path)
        login = _file(root, '.purlin/evidence/local/login.json')
        spec = root / 'specs' / 'a' / 'export.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing one'), encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'spec changed since %s' % sha[:7]}, output
        # Selected alone is run alone: export's one test and no other, and
        # login's evidence is left byte for byte.
        assert _ran(root) == ['test_export'], output
        assert 'Ran pytest on 1 feature.' in output.splitlines(), output
        assert _file(root, '.purlin/evidence/local/login.json') == login

    # purlin: run_script PROOF-90
    def test_an_edit_anywhere_in_the_project_selects_the_anchor(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path, names=('export', 'solo'))
        anchors = root / 'specs' / '_anchors'
        anchors.mkdir()
        (anchors / 'shared.md').write_text(
            '# Anchor: shared\n\n## Rules\n\n- RULE-1: every answer is JSON\n'
            '\n## Proof\n\n- PROOF-1 (RULE-1): an answer parses as JSON\n',
            encoding='utf-8')
        (root / 'tests' / 'test_shared.py').write_text(
            'import pytest\n\n'
            '# purlin: shared PROOF-1\n'
            'def test_shared():\n'
            '    assert True\n', encoding='utf-8')
        # What a run writes and git does not track, as setup ignores it.
        (root / '.gitignore').write_text(
            '.purlin/runtime/\n.purlin/report-data.js\n__pycache__/\n',
            encoding='utf-8')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'the anchor shared')
        _run(root, '--test', '--commit')
        assert _selection(_run(root, '--test')[1]) is None
        export = _file(root, '.purlin/evidence/local/export.json')
        (root / 'src' / 'solo.py').write_text('VALUE = 2\n', encoding='utf-8')
        _code, output = _run(root, '--test')
        chosen = _selection(output)
        assert sorted(chosen or ()) == ['shared', 'solo'], output
        assert chosen['shared'].startswith('code changed since '), output
        # Not `export`: its test is not run and its evidence is left byte
        # for byte. The two selected are the two that run.
        assert _ran(root) == ['test_shared', 'test_solo'], output
        assert _file(root, '.purlin/evidence/local/export.json') == export

    # purlin: run_script PROOF-91
    def test_a_feature_with_no_evidence_is_selected_and_run_alone(
            self, tmp_path):
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
        # This machine's system as a person reads it, off the machine.
        system = {'Darwin': 'macOS', 'Windows': 'Windows'}.get(
            platform.system(), 'Linux/Unix')
        assert _selection(output) == {
            'invoice': 'no run on %s yet' % system}, output
        # Selected alone is run alone: invoice's one test and no other.
        assert _ran(root) == ['test_invoice'], output
        assert 'Ran pytest on 1 feature.' in output.splitlines(), output
        assert ('Skipped 2 features whose spec, code and tests match their '
                'evidence: export, login. purlin:test --clean runs them too.'
                in output.splitlines()), output

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
    def test_an_untracked_file_selects_its_feature_alone_and_is_named(
            self, tmp_path):
        root, _sha = self._untracked_under_login(tmp_path)
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {'login': 'a file is not tracked'}, output
        assert ("src/auth/token.py is under login's scope and is not "
                'tracked, so its content is not part of the evidence until '
                'you git add it.') in output.splitlines(), output

    # purlin: run_script PROOF-290
    def test_an_untracked_file_runs_its_feature_alone(self, tmp_path):
        root, _sha = self._untracked_under_login(tmp_path)
        _code, output = _run(root, '--test')
        assert 'Ran pytest on 1 feature.' in output.splitlines(), output
        # Run alone: the report holds login's one test and no other.
        assert _ran(root) == ['test_login'], output

    # purlin: run_script PROOF-291
    def test_a_result_left_to_test_selects_its_feature(
            self, tmp_path, monkeypatch):
        root, _sha = _touched_project(tmp_path)
        # The suite's command names its Python through the environment, so
        # one committed command can meet a Python that starts no test.
        suite = suites.pytest_suite()
        suite['run'] = suite['run'].replace(suites.PYTHON, '"$TEST_PYTHON"')
        _config(root, tests=[suite])
        monkeypatch.setenv('TEST_PYTHON', sys.executable)
        _code, output = _run(root, '--test', '--commit')
        assert 'Evidence committed.' in output, output
        assert 'Nothing to run' in _run(root, '--test')[1]
        # `src/login.py` changes and the test tool does not start: login's
        # one result is recorded as not run, and committed.
        (root / 'src' / 'login.py').write_text('VALUE = 2\n', encoding='utf-8')
        monkeypatch.setenv('TEST_PYTHON', 'false')
        code, output = _run(root, '--test', '--commit')
        assert code == 1, output
        assert 'Evidence committed.' in output, output
        assert _passed_word(root, 'login', 'RULE-1') == 'not run'
        assert '  1 rule to test: purlin:test' in output.splitlines(), output
        # The test tool starts again, and nothing else has changed.
        monkeypatch.setenv('TEST_PYTHON', sys.executable)
        code, output = _run(root, '--test')
        lines = output.splitlines()
        assert 'Selected 1 of 2 features: login (1 rule to test).' in lines, \
            output
        assert not any(line.startswith('Nothing to run') for line in lines), \
            output
        assert 'Ran pytest on 1 feature.' in lines, output
        assert _ran(root) == ['test_login'], output
        assert code == 0, output
        assert _passed_word(root, 'login', 'RULE-1') == 'passed'

    # purlin: run_script PROOF-94
    def test_the_selected_line_comes_before_the_suite_runs(
            self, twelve_features):
        sha, code, output = twelve_features
        assert code == 0, output
        lines = output.splitlines()
        selected = ('Selected 1 of 12 features: f01 (code changed since %s).'
                    % sha[:7])
        assert selected in lines, output
        assert lines.index(selected) < next(
            index for index, line in enumerate(lines)
            if line.startswith('Running pytest: ')), output

    # purlin: run_script PROOF-95
    def test_nothing_changed_starts_no_suite_and_ends_on_the_sign_off(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        before = {name: _file(root, '.purlin/evidence/local/%s.json' % name)
                  for name in ('login', 'export')}
        code, output = _run(root, '--test')
        assert code == 0, output
        assert ("Nothing to run: every feature's spec, code and tests match "
                'its evidence. purlin:test --clean runs them anyway.'
                in output.splitlines()), output
        assert [line for line in output.splitlines()
                if line.startswith(('Selected', 'Running '))] == [], output
        assert {name: _file(root, '.purlin/evidence/local/%s.json' % name)
                for name in ('login', 'export')} == before
        assert [line for line in output.splitlines() if line.strip()][-1] == (
            'Every rule passes its tests on the committed evidence. Optional: '
            'sign this version with purlin:sign'), output

    # purlin: run_script PROOF-96
    def test_commit_with_nothing_to_run_commits_the_last_run(self, tmp_path):
        """A committed change to `src/login.py`, run with `--test` and its
        evidence left uncommitted, then `--test --commit` with nothing
        changed: `purlin: evidence at <sha7>` for the commit the run started
        on, and nothing under `.purlin/evidence` left uncommitted."""
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
            _script(root / ('%s.test.sh' % name),
                    '# purlin: %s PROOF-1\necho %s >> ran.txt\n' % (name, name))
        return root

    # purlin: run_script PROOF-191
    def test_a_named_feature_runs_only_its_test_files(self, tmp_path):
        root = self._two_shell_scripts(tmp_path)
        code, output = _run(root, '--feature', 'login', '--test')
        assert code == 0, output
        assert (root / 'ran.txt').read_text(encoding='utf-8').split() == [
            'login'], output

    # purlin: run_script PROOF-193
    def test_a_suite_with_none_of_the_features_tests_is_not_started(
            self, tmp_path):
        """Two shell suites, `logins` and `exports`, each script writing its
        feature's name to the one shared file `ran.txt`."""
        root = _project(tmp_path, tests=[
            suites.shell_suite(files=('login/*.test.sh',), name='logins'),
            suites.shell_suite(files=('export/*.test.sh',), name='exports')])
        for name in ('login', 'export'):
            _spec(root, name)
            (root / name).mkdir()
            _script(root / name / ('%s.test.sh' % name),
                    '# purlin: %s PROOF-1\necho %s >> ran.txt\n' % (name, name))
        _code, output = _run(root, '--feature', 'login', '--test')
        assert _started(output) == ['logins'], output
        assert (root / 'ran.txt').read_text(encoding='utf-8').split() == [
            'login'], output

    # purlin: run_script PROOF-98
    def test_clean_runs_every_feature_when_nothing_changed(self, tmp_path):
        """In a checkout of `login` and `export` with committed evidence and
        nothing changed, the report holds `test_export` and `test_login`."""
        root, _sha = _touched_project(tmp_path)
        code, output = _run(root, '--clean', '--test')
        assert code == 0, output
        assert 'Nothing to run' not in output, output
        assert _selection(output) is None, output
        assert _started(output) == ['pytest'], output
        assert _ran(root) == ['test_export', 'test_login'], output

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


def _purlin_tree(root):
    """`{path: bytes}` of every file under `.purlin/`, so a file changed in
    place shows as well as one added."""
    return {rel: (root / rel).read_bytes() for rel in _purlin_files(root)}


def _page_entries():
    """`[(the block as written, the entry it holds)]`, one per JSON block of
    the supported-frameworks page, in the page's order."""
    with open(os.path.join(REPO, 'references', 'supported_frameworks.md'),
              encoding='utf-8') as handle:
        page = handle.read()
    blocks = [block.split('```', 1)[0] for block in page.split('```json\n')[1:]]
    return [(block, json.loads(block)) for block in blocks]


def _one_passing_test(tmp_path):
    """A project with an empty `tests` setting, a `conftest.py` and one
    marked passing test."""
    root = _no_command(tmp_path, 'pytest')
    (root / 'tests').mkdir(exist_ok=True)
    (root / 'tests' / 'test_feat.py').write_text(
        '# purlin: feat PROOF-1\ndef test_ok():\n    assert 1 + 1 == 2\n',
        encoding='utf-8')
    return root


def _first_run_checkout(tmp_path):
    """`_one_passing_test` as a git checkout with everything committed and
    what a test run leaves behind ignored: a project before its first run.
    Its spec covers `src/feat.py`, so a second run finds nothing changed."""
    root = _one_passing_test(tmp_path)
    _spec(root, 'feat', scope='src/feat.py')
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
    (root / '.gitignore').write_text(
        '.purlin/runtime/\n.purlin/report-data.js\n__pycache__/\n'
        '.pytest_cache/\n', encoding='utf-8')
    _git_repo(root)
    return root


def _pytest_entry_in_words():
    """pytest's entry field by field, as the proofs of the written setting
    give it; on Windows its command opens `py -3`."""
    launcher = 'py -3' if sys.platform.startswith('win') else 'python3'
    return {'name': 'pytest',
            'run': launcher + ' -m pytest {files} --junitxml={report}',
            'report': '.purlin/runtime/reports/pytest.xml',
            'format': 'junit',
            'files': ['**/test_*.py', '**/*_test.py']}


def _tests_setting(root):
    with open(str(root / '.purlin' / 'config.json'), encoding='utf-8') as handle:
        return json.load(handle)['tests']


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
        before = _purlin_tree(root)
        code, output = _run(root, '--all', '--test')
        # pytest's entry written out here, field by field: one read from the
        # code under test would agree with whatever that code holds.
        entry = {'name': 'pytest',
                 'run': 'python3 -m pytest {files} --junitxml={report}',
                 'report': '.purlin/runtime/reports/pytest.xml',
                 'format': 'junit',
                 'files': ['**/test_*.py', '**/*_test.py']}
        assert output.splitlines()[-4:-1] == [
            'No test command is set in .purlin/config.json, so nothing ran.',
            'Suggested for pytest: python3 -m pytest {files} '
            '--junitxml={report}',
            'Suggested tests setting: %s' % json.dumps([entry])], output
        assert list(before) == [os.path.join('.purlin', 'config.json')]
        assert _purlin_tree(root) == before, output
        assert code == 1, output

    # purlin: run_script PROOF-127
    def test_no_known_tool_asks_for_a_proposal(self, tmp_path):
        root = _no_command(tmp_path)
        before = _purlin_tree(root)
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-1] == (
            'No test command is set and no test tool Purlin knows was found, '
            'so nothing ran. The agent reads the project and proposes a '
            'command for you to confirm.'), output
        # Nothing written under `.purlin/`: no file added, and the one file
        # there, the settings, left byte for byte.
        assert list(before) == [os.path.join('.purlin', 'config.json')]
        assert _purlin_tree(root) == before, output
        assert code == 1, output

    # purlin: run_script PROOF-287
    def test_with_nothing_to_answer_from_the_setting_is_not_written(
            self, tmp_path):
        root = _one_passing_test(tmp_path)
        before = (root / '.purlin' / 'config.json').read_bytes()
        code, output = _run(root, '--all', '--test')
        assert output.endswith(
            '\nWrite this tests setting to .purlin/config.json and commit that file? [y/N] '), \
            output
        assert (root / '.purlin' / 'config.json').read_bytes() == before
        assert code == 1, output

    # purlin: run_script PROOF-288
    def test_write_tests_writes_pytests_one_entry_unasked_and_runs(
            self, tmp_path):
        root = _one_passing_test(tmp_path)
        code, output = _run(root, '--all', '--test', '--write-tests')
        lines = output.splitlines()
        assert '[y/N]' not in output, output
        wrote = lines.index('Wrote the tests setting to .purlin/config.json.')
        # No question: the `Wrote` line follows the suggested setting with
        # nothing between, and no line is the question or ends as one.
        assert lines[wrote - 1].startswith(SUGGESTED_SETTING), output
        assert [line for line in lines
                if line.startswith('Write this tests setting')
                or line.rstrip().endswith('?')] == [], output
        assert 'Markers: 1 tied to a test, 0 not tied.' in lines[wrote:], \
            output
        assert _tests_setting(root) == [_pytest_entry_in_words()]
        assert code == 0, output

    # purlin: run_script PROOF-289
    def test_answered_y_pytests_one_entry_is_written_and_the_test_runs(
            self, tmp_path):
        root = _one_passing_test(tmp_path)
        code, output = _run(root, '--all', '--test', answer='y\n')
        assert _tests_setting(root) == [_pytest_entry_in_words()]
        assert 'Markers: 1 tied to a test, 0 not tied.' in output, output
        section = list(_evidence(root)['platforms'].values())[0]
        assert [(entry['id'], entry['result'])
                for entry in section['proofs']] == [('PROOF-1', 'pass')]
        assert code == 0, output

    # purlin: run_script PROOF-323
    def test_the_written_setting_is_committed_before_the_tests_run(
            self, tmp_path):
        root = _first_run_checkout(tmp_path)
        before = _head(root)
        code, output = _run(root, '--feature', 'feat', '--test',
                            '--write-tests')
        head = _head(root)
        lines = output.splitlines()
        wrote = lines.index('Wrote the tests setting to .purlin/config.json.')
        assert lines[wrote + 1:wrote + 3] == [
            'Committed %s, the work these results describe:' % head[:7],
            '  .purlin/config.json'], output
        assert lines[wrote + 3].startswith('Running pytest: '), output
        assert head != before
        assert _git(root, 'log', '-1', '--format=%s').strip() == (
            'purlin: specs, tests and settings')
        assert _git(root, 'show', '--name-only', '--format=',
                    'HEAD').split() == ['.purlin/config.json']
        section = list(_evidence(root)['platforms'].values())[0]
        assert section['commit'] == head
        assert code == 0, output

    # purlin: run_script PROOF-324
    def test_the_first_run_then_commit_ends_on_the_simple_last_line(
            self, tmp_path):
        root = _first_run_checkout(tmp_path)
        _run(root, '--feature', 'feat', '--test', '--write-tests')
        code, output = _run(root, '--test', '--commit')
        assert output.splitlines()[-1] == (
            'Every rule passes its tests on the committed evidence. '
            'Optional: sign this version with purlin:sign'), output
        assert code == 0, output

    # purlin: run_script PROOF-325
    def test_outside_a_git_checkout_the_written_setting_is_not_committed(
            self, tmp_path):
        root = _one_passing_test(tmp_path)
        code, output = _run(root, '--all', '--test', '--write-tests')
        assert 'Wrote the tests setting to .purlin/config.json.' \
            in output.splitlines(), output
        assert not [line for line in output.splitlines()
                    if line.startswith('Committed')], output
        assert not (root / '.git').exists()
        assert code == 0, output

    # purlin: run_script PROOF-262
    def test_a_plain_tests_folder_is_suggested_pytest(self, tmp_path):
        root = _no_command(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_cart.py').write_text(
            'def test_cart():\n    assert True\n', encoding='utf-8')
        _code, output = _run(root, '--all', '--test')
        assert ('Suggested for pytest: python3 -m pytest {files} '
                '--junitxml={report}' in output.splitlines()), output

    # purlin: run_script PROOF-221
    def test_on_windows_the_pytest_command_starts_with_the_launcher(
            self, tmp_path):
        root = _no_command(tmp_path, 'pytest')
        (entry,) = frameworks.suggest(str(root), os_name='windows')
        assert entry['run'] == ('py -3 -m pytest {files} '
                                '--junitxml={report}')

    # purlin: run_script PROOF-326
    @pytest.mark.skipif(platform.system() != 'Windows',
                        reason='the machine itself must be Windows')
    def test_a_windows_machine_is_suggested_the_launcher(self, tmp_path):
        root = _one_passing_test(tmp_path)
        _code, output = _run(root, '--all', '--test')
        assert ('Suggested for pytest: py -3 -m pytest {files} '
                '--junitxml={report}') in output.splitlines(), output

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
            # The flag as whole words: `--reporters=jest-junit-reporter`
            # names another reporter and does not carry it.
            assert re.search(r'(?<!\S)%s(?!\S)' % re.escape(flag),
                             suggestions[name]['run']), name

    # purlin: run_script PROOF-133
    def test_the_page_shows_the_same_entries(self, suggestions, tmp_path):
        shown = _page_entries()
        # The order is the run's own: one project holding what all seven
        # tools leave, and the array the run suggests for it, read in order.
        root = _no_command(tmp_path, *reversed(ORDER))
        # vitest and jest are both read from the one `package.json`.
        (root / 'package.json').write_text(
            '{"devDependencies": {"jest": "^29.0.0", "vitest": "^1.0.0"}}',
            encoding='utf-8')
        _code, output = _run(root, '--all', '--test')
        assert [entry for _block, entry in shown] == _suggested(output), \
            output
        assert [entry for _block, entry in shown] == [
            suggestions[name] for name in ORDER]
        # Word for word: each block is the entry and nothing more, so a key
        # written twice, which a JSON reader passes over, is seen.
        assert [block for block, _entry in shown] == [
            json.dumps(suggestions[name], indent=2) + '\n' for name in ORDER]

    # purlin: run_script PROOF-134
    def test_jest_is_told_it_needs_jest_junit(self, tmp_path):
        _code, output = _run(_no_command(tmp_path, 'jest'), '--all', '--test')
        lines = output.splitlines()
        suggested = [index for index, line in enumerate(lines)
                     if line.startswith('Suggested for jest: ')]
        assert len(suggested) == 1, output
        assert lines[suggested[0] + 1] == (
            'jest needs the package jest-junit to write its report: run npm '
            'install --save-dev jest-junit'), output

    # purlin: run_script PROOF-252
    def test_jest_is_handed_the_files_before_its_reporters(
            self, tmp_path, monkeypatch):
        # A stand-in `npx` on PATH writes each word it was handed, one per
        # line, so the command line jest would get is read back.
        bin_dir = tmp_path / 'bin'
        bin_dir.mkdir()
        _script(bin_dir / 'npx',
                '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > npx-args.txt\n')
        os.chmod(str(bin_dir / 'npx'), 0o755)
        monkeypatch.setenv('PATH', str(bin_dir) + os.pathsep
                           + os.environ.get('PATH', ''))
        root = _project(tmp_path, tests=[frameworks.entry_for('jest')])
        (root / 'test').mkdir()
        for name in ('feat', 'other'):
            _spec(root, name)
            (root / 'test' / ('%s.test.js' % name)).write_text(
                '// purlin: %s PROOF-1\ntest("ok", () => {});\n' % name,
                encoding='utf-8')
        _run(root, '--feature', 'feat', '--test')
        words = (root / 'npx-args.txt').read_text(
            encoding='utf-8').splitlines()
        assert words[words.index('--ci'):] == [
            '--ci', 'test/feat.test.js', '--reporters=default',
            '--reporters=jest-junit'], words

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

    # purlin: run_script PROOF-224
    def test_a_settings_file_that_cannot_be_read_stops_the_run(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        text = '{\n  "version": "0.10.0",\n  "tests": [],\n}\n'
        (root / '.purlin' / 'config.json').write_text(text, encoding='utf-8')
        # The cause is the JSON reader's own message and line, which differ
        # between versions of Python.
        with pytest.raises(json.JSONDecodeError) as reading:
            json.loads(text)
        before = _purlin_tree(root)
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines() == [
            '.purlin/config.json cannot be read: %s at line %d. Fix the file '
            'by hand; nothing ran and nothing was saved.'
            % (reading.value.msg, reading.value.lineno)], output
        assert list(before) == [os.path.join('.purlin', 'config.json')]
        assert _purlin_tree(root) == before, output
        assert code == 1, output

    # purlin: run_script PROOF-138
    def test_a_project_an_older_purlin_set_up_stops_the_run(self, tmp_path):
        # The settings file as Purlin 0.9.5 wrote it: the one this
        # repository keeps of such a project, whose stamp is the release
        # that first set the project up, and one stamped `0.9.5`.
        with open(os.path.join(REPO, 'dev', 'fixtures', 'upgrade-0.9.5',
                               '.purlin', 'config.json'),
                  encoding='utf-8') as handle:
            kept = handle.read()
        assert 'tests' not in json.loads(kept)
        assert json.loads(kept)['version'] != '0.9.5'
        for name, text in (('kept', kept), ('stamped', json.dumps(
                {'version': '0.9.5', 'test_framework': 'pytest'}))):
            folder = tmp_path / name
            folder.mkdir()
            root = _pytest_project(folder)
            _spec(root, 'feat')
            (root / '.purlin' / 'config.json').write_text(
                text, encoding='utf-8')
            before = _purlin_tree(root)
            code, output = _run(root, '--all', '--test')
            assert output.strip().splitlines() == [
                'This project was set up by an older Purlin and not '
                'upgraded, so nothing ran. Run purlin:init --update.'], output
            assert list(before) == [os.path.join('.purlin', 'config.json')]
            assert _purlin_tree(root) == before, output
            assert code == 1, output

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


class TestTheTwoCommits:

    @staticmethod
    def _checkout(tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        (root / '.gitignore').write_text('.purlin/runtime/\n__pycache__/\n'
                                         '.pytest_cache/\n', encoding='utf-8')
        _git_repo(root)
        return root

    # purlin: run_script PROOF-270
    def test_the_section_names_the_commit_of_the_work(self, tmp_path):
        root = self._checkout(tmp_path)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8') + '\n',
                        encoding='utf-8')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        work = _git(root, 'rev-parse', 'HEAD~1').strip()
        assert _git(root, 'log', '-1', '--format=%s', work).strip() == (
            'purlin: specs, tests and settings for feat'), output
        section = _evidence(root)['platforms'][HERE_OS]
        assert section['commit'] == work, section

    # purlin: run_script PROOF-257
    def test_nothing_to_run_commits_the_spec_tests_and_settings(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path, names=('feat',))
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8') + '\n',
                        encoding='utf-8')
        test = root / 'tests' / 'test_feat.py'
        test.write_text(test.read_text(encoding='utf-8') + '# edited\n',
                        encoding='utf-8')
        _config(root)
        _run(root, '--test')
        code, output = _run(root, '--test', '--commit')
        assert code == 0, output
        assert 'Nothing to run' in output, output
        first = _git(root, 'rev-parse', 'HEAD~1').strip()
        assert _git(root, 'log', '-1', '--format=%s', first).strip() == (
            'purlin: specs, tests and settings for feat'), output
        assert sorted(_git(root, 'show', '--format=', '--name-only',
                           first).split()) == [
            '.purlin/config.json', 'specs/a/feat.md',
            'tests/test_feat.py'], output
        assert _git(root, 'log', '-1', '--format=%s').strip() == (
            'purlin: evidence at %s' % first[:7]), output


# A spec writing PROOF-2 twice: its rules read `failed` until it is fixed.
TWICE = (('PROOF-1', 'RULE-1', ''), ('PROOF-2', 'RULE-1', ''),
         ('PROOF-2', 'RULE-2', ''))


def _broken_login(tmp_path):
    """`feat`, sound, and `login`, whose spec writes PROOF-2 twice; every
    marked test of both passes."""
    root = _pytest_project(tmp_path)
    _spec(root, 'feat')
    _spec(root, 'login', rules=2, proofs=TWICE)
    (root / 'tests' / 'test_login.py').write_text(
        'import pytest\n\n'
        '# purlin: login PROOF-1\n'
        'def test_one():\n'
        '    assert 1 == 1\n\n'
        '# purlin: login PROOF-2\n'
        'def test_two():\n'
        '    assert 2 == 2\n', encoding='utf-8')
    return root


class TestABrokenSpec:

    # purlin: run_script PROOF-261
    def test_a_test_run_writes_its_results_and_exits_1(self, tmp_path):
        root = _broken_login(tmp_path)
        code, output = _run(root, '--test', '--all')
        proofs = _evidence(root, 'login')['platforms'][HERE_OS]['proofs']
        assert {(p['id'], p['result']) for p in proofs} == {
            ('PROOF-1', 'pass'), ('PROOF-2', 'pass')}, output
        assert code == 1, output



# ---------------------------------------------------------------------------
# Slow proofs
# ---------------------------------------------------------------------------

SLOW_BODY = ('import pytest\n\n'
             '# purlin: feat PROOF-1\n'
             'def test_ok():\n'
             '    assert True\n\n'
             '# purlin: feat PROOF-2\n'
             'def test_slow():\n'
             "    open('started', 'a').close()\n")


def _slow_project(tmp_path, tests=None):
    """`feat` of two rules: PROOF-1's test passes, and the test of PROOF-2,
    tagged `@slow`, writes the file `started` when it starts."""
    root = _pytest_project(tmp_path, body=SLOW_BODY)
    if tests is not None:
        _config(root, tests=tests)
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 1\n', encoding='utf-8')
    _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                         ('PROOF-2', 'RULE-2', ' @slow')))
    return root


def _proof(root, proof_id, feature='feat'):
    """`(result, test)` of the one entry the evidence lists for a proof."""
    listed = [entry for entry in _proofs(root, feature)
              if entry['id'] == proof_id]
    assert len(listed) == 1, listed
    return listed[0]['result'], listed[0]['test']


def _slow_test(name, scopes=(), namespace=''):
    markers = importlib.import_module('purlin.markers')
    return markers.Test(name, 3, scopes, namespace=namespace)


class TestSlowProofs:
    """`purlin:test` never starts a slow proof's test; `--all` does."""

    # purlin: run_script PROOF-275
    def test_a_plain_run_leaves_the_slow_test_out_and_says_so(self, tmp_path):
        root = _slow_project(tmp_path)
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        assert ('Left out 1 slow proof: feat PROOF-2. purlin:test --all runs '
                'it when it is due.') in output.splitlines(), output
        assert 'Evidence is missing' not in output, output
        assert not (root / 'started').exists()
        assert _proof(root, 'PROOF-2') == (
            'not run', 'tests/test_feat.py::test_slow')

    # purlin: run_script PROOF-276
    def test_all_starts_the_slow_test(self, tmp_path):
        root = _slow_project(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert (root / 'started').exists()
        assert 'Left out' not in output, output
        assert _proof(root, 'PROOF-2')[0] == 'pass'

    # purlin: run_script PROOF-277
    def test_each_tool_is_given_its_own_option(self, tmp_path):
        markers = importlib.import_module('purlin.markers')
        reports = importlib.import_module('reports')

        def command(tool, path, test):
            entry = frameworks.entry_for(tool)
            suite = markers.Suite(tool, entry['run'], entry['report'],
                                  entry['format'], entry['files'])
            option, held, started = frameworks.leave_out(suite,
                                                         [(path, test)])
            assert held == [(path, test)] and started == [], (tool, started)
            return reports.command_for(suite, [], suite.report_path(), option)

        pattern = "--testNamePattern '^(?!(?:.* )?(?:cart checks out)$)'"
        assert ('--deselect tests/test_cart.py::TestCart::test_checkout'
                in command('pytest', 'tests/test_cart.py',
                           _slow_test('test_checkout', ['TestCart'])))
        for tool in ('vitest', 'jest'):
            assert pattern in command(
                tool, 'tests/cart.test.js',
                _slow_test('checks out', ['cart'])), tool
        assert ("--filter 'FullyQualifiedName!=Shop.Tests.CartTests.ChecksOut'"
                in command('dotnet', 'Shop.Tests/CartTests.cs',
                           _slow_test('ChecksOut', ['CartTests'],
                                      'Shop.Tests')))
        assert "-skip '^(?:TestCheckout)$'" in command(
            'go', 'cart/cart_test.go', _slow_test('TestCheckout'))

        root = _project(tmp_path, tests=[suites.shell_suite()])
        for name, proof_id in (('fast', 'PROOF-1'), ('slow', 'PROOF-2')):
            _script(root / ('%s.test.sh' % name),
                    '# purlin: feat %s\necho %s >> ran.txt\n'
                    % (proof_id, name))
        _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                             ('PROOF-2', 'RULE-2', ' @slow')))
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        assert (root / 'ran.txt').read_text(encoding='utf-8').split() == [
            'fast'], output

    @staticmethod
    def _two_names(tmp_path, slow, ordinary):
        """The slow project with its two tests named `slow`, the test of the
        slow PROOF-2, and `ordinary`, the test of PROOF-1."""
        root = _slow_project(tmp_path)
        (root / 'tests' / 'test_feat.py').write_text(
            SLOW_BODY.replace('def test_slow():', 'def %s():' % slow)
            .replace('def test_ok():', 'def %s():' % ordinary),
            encoding='utf-8')
        return root

    # purlin: run_script PROOF-327
    def test_a_slow_test_whose_name_starts_another_tests_name_is_started(
            self, tmp_path):
        root = self._two_names(tmp_path, 'test_slow', 'test_slow_start')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        assert _proof(root, 'PROOF-1') == (
            'pass', 'tests/test_feat.py::test_slow_start')
        assert (root / 'started').exists()
        lines = output.splitlines()
        assert ('Started 1 slow test in the pytest suite: its command gives '
                'Purlin no way to leave one test out.') in lines, output
        assert not any(line.startswith('Left out') for line in lines), output
        assert '--deselect' not in output, output

    # purlin: run_script PROOF-328
    def test_a_slow_test_whose_name_another_tests_name_starts_is_left_out(
            self, tmp_path):
        root = self._two_names(tmp_path, 'test_ok_slow', 'test_ok')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        (running,) = [line for line in output.splitlines()
                      if line.startswith('Running pytest: ')]
        assert ' --deselect tests/test_feat.py::test_ok_slow ' in running
        assert not (root / 'started').exists()
        assert _proof(root, 'PROOF-1') == ('pass',
                                           'tests/test_feat.py::test_ok')
        assert _proof(root, 'PROOF-2') == (
            'not run', 'tests/test_feat.py::test_ok_slow')

    # purlin: run_script PROOF-278
    def test_a_command_that_cannot_leave_a_test_out_starts_it_and_says_so(
            self, tmp_path):
        runner = suites.pytest_suite(name='runner')
        runner['run'] = '%s run.py {files} --junitxml={report}' % suites.PYTHON
        root = _slow_project(tmp_path, tests=[runner])
        (root / 'run.py').write_text(
            'import sys\nimport pytest\n'
            "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider']"
            ' + sys.argv[1:]))\n', encoding='utf-8')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        assert (root / 'started').exists()
        assert ('Started 1 slow test in the runner suite: its command gives '
                'Purlin no way to leave one test out.') in output.splitlines()
        assert _proof(root, 'PROOF-2')[0] == 'pass'

    @staticmethod
    def _after_a_full_run(tmp_path):
        """A git checkout of the slow project after `--all --test` passed
        PROOF-2, the file its test wrote taken away."""
        root = _slow_project(tmp_path)
        _git_repo(root)
        code, output = _run(root, '--all', '--test')
        assert code == 0 and _proof(root, 'PROOF-2')[0] == 'pass', output
        (root / 'started').unlink()
        return root

    # purlin: run_script PROOF-279
    def test_a_plain_run_keeps_the_slow_result_that_still_counts(
            self, tmp_path):
        root = self._after_a_full_run(tmp_path)
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        assert not (root / 'started').exists()
        assert _proof(root, 'PROOF-2')[0] == 'pass'
        assert _passed_word(root, 'feat', 'RULE-2') == 'passed'

    # purlin: run_script PROOF-280
    def test_a_code_change_puts_the_slow_proof_back_on_the_list(
            self, tmp_path):
        root = self._after_a_full_run(tmp_path)
        (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert list(_selection(output)) == ['feat'], output
        assert _proof(root, 'PROOF-2')[0] == 'not run'
        assert output.rstrip().splitlines()[-1] == (
            '  1 slow proof to run: purlin:test --all'), output

    @staticmethod
    def _carried_after_another_commit(tmp_path):
        """A git checkout where `--all --test --commit` passed the slow
        PROOF-2, `README.md` was then changed and committed, and a plain run
        of `feat` was committed. `(root, the first run's section)`."""
        root = _slow_project(tmp_path)
        (root / 'README.md').write_text('one\n', encoding='utf-8')
        (root / '.gitignore').write_text(
            '.purlin/runtime/\n__pycache__/\n.pytest_cache/\nstarted\n',
            encoding='utf-8')
        _git_repo(root)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0 and _proof(root, 'PROOF-2')[0] == 'pass', output
        taken = _evidence(root)['platforms'][HERE_OS]
        (root / 'started').unlink()
        (root / 'README.md').write_text('two\n', encoding='utf-8')
        _git(root, 'commit', '-q', '-am', 'docs: the readme')
        code, output = _run(root, '--feature', 'feat', '--test', '--commit')
        assert code == 0, output
        assert not (root / 'started').exists()
        return root, taken

    # purlin: run_script PROOF-281
    def test_a_carried_slow_result_names_the_run_that_took_it(
            self, tmp_path):
        root, taken = self._carried_after_another_commit(tmp_path)
        later = _git(root, 'rev-parse', 'HEAD~1').strip()
        assert _git(root, 'log', '-1', '--format=%s', later).strip() == (
            'docs: the readme')
        section = _evidence(root)['platforms'][HERE_OS]
        (slow,) = [entry for entry in section['proofs']
                   if entry['id'] == 'PROOF-2']
        assert slow['result'] == 'pass', slow
        assert later != taken['commit']
        assert section['commit'] == later, section
        assert slow.get('carried') == {
            'commit': taken['commit'], 'at': taken['at'],
            'machine': taken['machine'], 'email': taken['email']}, slow
        assert all('carried' not in entry for entry in section['proofs']
                   if entry['id'] != 'PROOF-2'), section

    # purlin: run_script PROOF-286
    def test_a_clean_run_takes_a_carried_result_again(self, tmp_path):
        """A result `--clean` takes itself replaces the carried one, on the
        same code."""
        root, _taken = self._carried_after_another_commit(tmp_path)
        carried = [entry['id'] for entry in
                   _evidence(root)['platforms'][HERE_OS]['proofs']
                   if 'carried' in entry]
        assert carried == ['PROOF-2'], carried
        code, output = _run(root, '--clean', '--test', '--commit')
        assert code == 0, output
        assert (root / 'started').exists()
        section = _evidence(root)['platforms'][HERE_OS]
        assert all('carried' not in entry
                   for entry in section['proofs']), section
        assert _proof(root, 'PROOF-2')[0] == 'pass'

    # purlin: run_script PROOF-285
    def test_a_slow_nunit_row_test_is_started_and_the_run_says_so(
            self, tmp_path):
        dotnet = dict(frameworks.entry_for('dotnet'),
                      run='bash ./dotnet test --logger trx '
                          '--results-directory {report}')
        root = _project(tmp_path, tests=[dotnet])
        # A stand-in for the tool, which writes down how it was started.
        _script(root / 'dotnet', 'printf \'%s\\n\' "$@" > started-with.txt\n')
        (root / 'Shop.Tests').mkdir()
        (root / 'Shop.Tests' / 'CartTests.cs').write_text(
            'using NUnit.Framework;\n\n'
            'namespace Shop.Tests\n{\n'
            '    public class CartTests\n    {\n'
            '        // purlin: feat PROOF-1\n'
            '        [Test]\n'
            '        public void Adds() { Assert.Pass(); }\n\n'
            '        // purlin: feat PROOF-2\n'
            '        [TestCase(1)]\n'
            '        public void ChecksOut(int count) { Assert.Pass(); }\n'
            '    }\n}\n', encoding='utf-8')
        _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                             ('PROOF-2', 'RULE-2', ' @slow')))
        _code, output = _run(root, '--feature', 'feat', '--test')
        started = (root / 'started-with.txt').read_text(
            encoding='utf-8').split()
        assert started[:3] == ['test', '--logger', 'trx'], output
        assert '--filter' not in started, started
        assert not any('FullyQualifiedName' in word for word in started)
        lines = output.splitlines()
        assert ('Started 1 slow test in the dotnet suite: its command gives '
                'Purlin no way to leave one test out.') in lines, output
        assert not any(line.startswith('Left out') for line in lines), output


    # purlin: run_script PROOF-329
    def test_a_slow_dotnet_test_named_as_another_but_for_case_is_started(
            self, tmp_path):
        dotnet = dict(frameworks.entry_for('dotnet'),
                      run='bash ./dotnet test --logger trx '
                          '--results-directory {report}')
        root = _project(tmp_path, tests=[dotnet])
        # A stand-in for the tool, which writes down how it was started.
        _script(root / 'dotnet', 'printf \'%s\\n\' "$@" > started-with.txt\n')
        (root / 'Shop.Tests').mkdir()
        (root / 'Shop.Tests' / 'CartTests.cs').write_text(
            'using Xunit;\n\n'
            'namespace Shop.Tests\n{\n'
            '    public class CartTests\n    {\n'
            '        // purlin: feat PROOF-1\n'
            '        [Fact]\n'
            '        public void checksout() { }\n\n'
            '        // purlin: feat PROOF-2\n'
            '        [Fact]\n'
            '        public void ChecksOut() { }\n'
            '    }\n}\n', encoding='utf-8')
        _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                             ('PROOF-2', 'RULE-2', ' @slow')))
        _code, output = _run(root, '--feature', 'feat', '--test')
        started = (root / 'started-with.txt').read_text(
            encoding='utf-8').split()
        assert started[:3] == ['test', '--logger', 'trx'], output
        assert '--filter' not in started, started
        lines = output.splitlines()
        assert ('Started 1 slow test in the dotnet suite: its command gives '
                'Purlin no way to leave one test out.') in lines, output
        assert not any(line.startswith('Left out') for line in lines), output


# `feat` of three rules. The test of PROOF-2, tagged `@slow`, writes the file
# `started` and checks nothing; the test of PROOF-3, tagged `@slow` too,
# writes `started-other`.
SETTLE_BODY = ('from src.feat import VALUE\n\n'
               '# purlin: feat PROOF-1\n'
               'def test_ok():\n'
               '    assert VALUE\n\n'
               '# purlin: feat PROOF-2\n'
               'def test_slow():\n'
               "    open('started', 'a').close()\n\n"
               '# purlin: feat PROOF-3\n'
               'def test_other_slow():\n'
               "    open('started-other', 'a').close()\n"
               '    assert VALUE\n')
CHECKS_NOTHING = "    open('started', 'a').close()\n\n"
CHECKS_THE_VALUE = ("    open('started', 'a').close()\n"
                    '    assert VALUE == 1\n\n')


@pytest.fixture
def slow_rule_settled(tmp_path, claude):
    """A git checkout of `feat` after `--all --audit` kept a bug as
    `survived` for the slow PROOF-2, its test was changed to check the value
    and `--audit --feature feat --settle RULE-2` ran.
    `(root, the settle's exit code, its output)`."""
    install, _directory = claude
    root = _pytest_project(tmp_path, body=SETTLE_BODY)
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 1\n', encoding='utf-8')
    _spec(root, 'feat', rules=3, proofs=(('PROOF-1', 'RULE-1', ''),
                                         ('PROOF-2', 'RULE-2', ' @slow'),
                                         ('PROOF-3', 'RULE-3', ' @slow')))
    (root / '.gitignore').write_text(
        '.purlin/runtime/\n__pycache__/\n.pytest_cache/\nstarted*\n',
        encoding='utf-8')
    _git_repo(root)
    install(answers=[{'PROOF-2': fake_claude.change(
        'src/feat.py', 'VALUE = 1', 'VALUE = 2',
        case='the value is read; the proof says 1; the changed code gives 2',
        aim='past the test')}])
    code, output = _run(root, '--all', '--audit')
    assert code == 0, output
    kept = json.loads((root / '.purlin' / 'evidence' / 'local' / 'feat.json')
                      .read_text(encoding='utf-8'))['audit']['rules']
    assert kept['RULE-2']['bugs']['PROOF-2']['result'] == 'survived', kept
    for name in ('started', 'started-other'):
        (root / name).unlink()
    path = root / 'tests' / 'test_feat.py'
    path.write_text(path.read_text(encoding='utf-8').replace(
        CHECKS_NOTHING, CHECKS_THE_VALUE), encoding='utf-8')
    install()
    code, output = _run(root, '--audit', '--feature', 'feat', '--settle',
                        'RULE-2')
    return root, code, output


class TestASettleStartsTheSlowTestOfItsRule:

    # purlin: run_script PROOF-330
    def test_the_slow_test_of_the_rule_named_is_started(
            self, slow_rule_settled):
        root, code, output = slow_rule_settled
        assert code == 0, output
        assert (root / 'started').exists(), output
        assert _proof(root, 'PROOF-2') == ('pass',
                                           'tests/test_feat.py::test_slow')

    # purlin: run_script PROOF-331
    def test_the_slow_test_of_another_rule_stays_left_out(
            self, slow_rule_settled):
        root, _code, output = slow_rule_settled
        assert ('Left out 1 slow proof: feat PROOF-3. purlin:test --all runs '
                'it when it is due.') in output.splitlines(), output
        assert not (root / 'started-other').exists(), output

    # purlin: run_script PROOF-332
    def test_the_one_command_settles_the_rule(self, slow_rule_settled):
        _root, _code, output = slow_rule_settled
        lines = output.splitlines()
        assert 'feat RULE-2   strong' in lines, output
        under = lines[lines.index('feat RULE-2   strong') + 1:][:2]
        assert ('  PROOF-2: the test now catches the bug it missed at '
                'src/feat.py:1.') in under, output
        assert not any('nothing to settle' in line for line in lines), output


class TestNothingToRunOverAFailure:

    # purlin: run_script PROOF-282
    def test_nothing_to_run_exits_1_while_the_evidence_holds_a_failure(
            self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_bad():\n'
            '    assert 1 == 2\n'))
        (root / 'src').mkdir()
        (root / 'src' / 'feat.py').write_text('VALUE = 1\n', encoding='utf-8')
        (root / '.gitignore').write_text(
            '.purlin/runtime/\n__pycache__/\n.pytest_cache/\n',
            encoding='utf-8')
        _spec(root, 'feat')
        _git_repo(root)
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert _started(output) == ['pytest'], output
        code, output = _run(root, '--test')
        assert any(line.startswith('Nothing to run')
                   for line in output.splitlines()), output
        assert _started(output) == [], output
        assert code == 1, output


# ---------------------------------------------------------------------------
# A test the report names differently
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def renamed_run(tmp_path_factory):
    """A marked test titled `adds two numbers` whose report names the
    passing case `adds  two numbers`. `(exit code, output)`."""
    root = _project(tmp_path_factory.mktemp('renamed'), tests=[{
        'name': 'vitest', 'run': 'cp canned.xml {report}',
        'report': '.purlin/runtime/reports/vitest.xml',
        'format': 'junit', 'files': ['tests/*.test.ts']}])
    _spec(root, 'feat')
    (root / 'tests').mkdir()
    (root / 'tests' / 'feat.test.ts').write_text(
        "// purlin: feat PROOF-1\n"
        "it('adds two numbers', () => {});\n", encoding='utf-8')
    (root / 'canned.xml').write_text(
        '<testsuites><testsuite name="x"><testcase '
        'classname="tests/feat.test.ts" name="adds  two numbers"/>'
        '</testsuite></testsuites>', encoding='utf-8')
    return _run(root, '--all', '--test')


class TestATestTheReportNamesDifferently:

    # purlin: run_script PROOF-292
    def test_both_names_are_shown(self, renamed_run):
        code, output = renamed_run
        assert code == 1, output
        assert ('Evidence is missing: feat PROOF-1 at tests/feat.test.ts:1: '
                'its test ran, and the report names it differently. The '
                'title reads "adds two numbers" and the report reads "adds  '
                'two numbers". Write the title as the report reads, then '
                'run purlin:test.') in output.splitlines(), output

    # purlin: run_script PROOF-293
    def test_the_skipped_sentence_is_not_printed(self, renamed_run):
        _code, output = renamed_run
        assert 'Check that its test ran and was not skipped' not in output


# ---------------------------------------------------------------------------
# The files a run over every feature hands a suite
# ---------------------------------------------------------------------------

class TestAllHandsTheSuiteItsFiles:

    # purlin: run_script PROOF-294
    def test_a_project_with_its_pytest_settings_in_a_subfolder_passes(
            self, tmp_path):
        root = _project(tmp_path, tests=[suites.pytest_suite(
            files=('**/test_*.py',))])
        _spec(root, 'feat', scope='pipeline/')
        (root / 'pipeline' / 'tests').mkdir(parents=True)
        (root / 'pipeline' / 'pyproject.toml').write_text(
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
            'pythonpath = ["."]\n', encoding='utf-8')
        (root / 'pipeline' / 'rgm.py').write_text('VALUE = 1\n',
                                                  encoding='utf-8')
        (root / 'pipeline' / 'tests' / 'test_feat.py').write_text(
            'from rgm import VALUE\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n    assert VALUE == 1\n', encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert [(entry['id'], entry['result'])
                for entry in _proofs(root, 'feat')] == [
            ('PROOF-1', 'pass')], output

    # purlin: run_script PROOF-295
    def test_a_command_past_the_limit_is_started_with_no_file_list(
            self, tmp_path):
        command = ('%s -m pytest -q -p no:cacheprovider %%s '
                   '--junitxml=.purlin/runtime/reports/pytest.xml'
                   % suites.PYTHON)
        crowded = ('The pytest suite has 160 test files, more than one '
                   'command line holds, so it runs with no file list.')

        def run(name, length):
            """A project of 160 marked test files whose names are padded
            until the command naming them all is `length` characters, run
            with `--all --test`. `(root, the paths, exit code, lines)`."""
            root = _project(tmp_path / name, tests=[suites.pytest_suite(
                files=('tests/**/test_*.py',))])
            _spec(root, 'feat')
            (root / 'tests').mkdir()
            spare = length - len(command % ' '.join(
                'tests/test_n%03d.py' % index for index in range(160)))
            pad, more = divmod(spare, 160)
            paths = []
            for index in range(160):
                paths.append('tests/test_n%03d%s.py' % (
                    index, 'x' * (pad + (1 if index < more else 0))))
                (root / paths[-1]).write_text(
                    '# purlin: feat PROOF-1\n'
                    'def test_n%03d():\n    assert True\n' % index,
                    encoding='utf-8')
            assert len(command % ' '.join(paths)) == length
            code, output = _run(root, '--all', '--test')
            return root, paths, code, output.splitlines()

        # At 30,000 characters the command names all 160 files: the command
        # the suite starts is the one measured here, character for character.
        _root, paths, _code, lines = run('at', 30000)
        assert crowded not in lines, lines
        assert [line for line in lines if line.startswith('Running ')] == [
            'Running pytest: ' + command % ' '.join(paths)], lines
        # One character more passes 30,000: the line is printed and the
        # command, the whole of it, names no test file.
        root, _paths, code, lines = run('past', 30001)
        assert lines.count(crowded) == 1, lines
        started = [line for line in lines if line.startswith('Running ')]
        assert started == [
            'Running pytest: %s -m pytest -q -p no:cacheprovider '
            '--junitxml=.purlin/runtime/reports/pytest.xml'
            % suites.PYTHON], lines
        assert lines.index(crowded) < lines.index(started[0]), lines
        assert {entry['result'] for entry in _proofs(root, 'feat')} == {
            'pass'}, lines
        assert len(_proofs(root, 'feat')) == 160 and code == 0, lines


# ---------------------------------------------------------------------------
# The line a suite starts on
# ---------------------------------------------------------------------------

class TestTheLineASuiteStartsOn:

    # purlin: run_script PROOF-296
    def test_the_line_is_out_before_the_command_ends(self, tmp_path):
        command = ('while [ ! -f go ]; do sleep 0.1; done; '
                   'cp canned.xml {report}')
        root = _project(tmp_path, tests=[{
            'name': 'slow', 'run': command,
            'report': '.purlin/runtime/reports/slow.xml',
            'format': 'junit', 'files': ['tests/test_*.py']}])
        _spec(root, 'feat')
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            '# purlin: feat PROOF-1\ndef test_ok():\n    pass\n',
            encoding='utf-8')
        (root / 'canned.xml').write_text(
            '<testsuite><testcase classname="tests.test_feat" '
            'name="test_ok"/></testsuite>', encoding='utf-8')
        running = subprocess.Popen(
            [sys.executable, RUN_SCRIPT, '--project-root', str(root),
             '--all', '--test'], stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL, encoding='utf-8', cwd=str(root))
        try:
            first = running.stdout.readline().rstrip('\n')
            waiting = running.poll() is None
            (root / 'go').write_text('', encoding='utf-8')
            rest, _err = running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        assert first == 'Running slow: ' + command.replace(
            '{report}', '.purlin/runtime/reports/slow.xml'), first + rest
        assert waiting, first + rest
        assert running.returncode == 0, first + rest

    # purlin: run_script PROOF-297
    def test_an_exit_suite_counts_its_files(self, tmp_path):
        root = _project(tmp_path, tests=[suites.shell_suite()])
        _spec(root, 'feat')
        for name in ('a', 'b'):
            _script(root / ('%s.test.sh' % name),
                    '# purlin: feat PROOF-1\ntrue\n')
        _code, output = _run(root, '--all', '--test')
        assert ('Running shell: bash {files}, once for each of 2 files'
                in output.splitlines()), output


# ---------------------------------------------------------------------------
# A changed tests setting
# ---------------------------------------------------------------------------

def _setting_gains_v(root):
    path = root / '.purlin' / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config['tests'][0]['run'] = config['tests'][0]['run'].replace(
        ' -q ', ' -q -v ')
    path.write_text(json.dumps(config), encoding='utf-8')


class TestAChangedTestsSetting:

    SAID = 'The tests setting changed, so every result is out of date.'

    # purlin: states PROOF-306
    def test_the_status_says_so_once(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        _setting_gains_v(root)
        lines = purlin_status.sync_status(str(root)).splitlines()
        assert lines.count(self.SAID) == 1, lines

    # purlin: states PROOF-307
    def test_an_edited_test_file_alone_is_not_the_setting(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        test = root / 'tests' / 'test_login.py'
        test.write_text(test.read_text(encoding='utf-8') + '# edited\n',
                        encoding='utf-8')
        text = purlin_status.sync_status(str(root))
        lines = text.splitlines()
        assert self.SAID not in lines, lines
        # No line holds the sentence, with or without anything around it.
        assert self.SAID not in text, lines
        assert [line for line in lines
                if 'tests setting changed' in line] == [], lines
        assert any('tests changed since' in line or 'to test' in line
                   for line in lines), lines

    # purlin: run_script PROOF-298
    def test_the_run_says_so_once_before_it_selects(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        _setting_gains_v(root)
        _code, output = _run(root, '--test')
        lines = output.splitlines()
        said = 'The tests setting changed, so every result is out of date.'
        assert lines.count(said) == 1, output
        assert lines.index(said) < next(
            index for index, line in enumerate(lines)
            if line.startswith('Selected 2 of 2 features')), output


# ---------------------------------------------------------------------------
# A marker Purlin 0.9.5 wrote that is still in a test
# ---------------------------------------------------------------------------

class TestAMarkerFrom095StillInATest:

    # purlin: run_script PROOF-302
    def test_the_run_says_so_once_in_its_status(self, tmp_path):
        root = _pytest_project(tmp_path, body='')
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert True\n'
            '@pytest.mark.proof("feat", "PROOF-1b", "RULE-1")\n'
            'def test_more():\n'
            '    assert True\n', encoding='utf-8')
        _spec(root, 'feat')
        _git_repo(root)
        code, output = _run(root, '--all', '--test')
        lines = output.splitlines()
        said = ['1 test still carries a marker from Purlin 0.9.5, which is '
                'not read:',
                '  tests/test_feat.py:6  feat RULE-1',
                'For each, write the proof with purlin:spec, put the comment '
                'above the test, and take the old tag out.']
        assert code == 0, output
        assert lines.count(said[0]) == 1, output
        at = lines.index(said[0])
        assert lines[at:at + 3] == said, output
        assert output.count('a marker from Purlin 0.9.5') == 1, output
        assert at > next(
            index for index, line in enumerate(lines)
            if line.startswith('Purlin status:')), output


# ---------------------------------------------------------------------------
# What `--commit` left uncommitted
# ---------------------------------------------------------------------------

STILL_DO = ('Commit them, then run purlin:test --all --commit again: a '
            'sign-off needs results taken with nothing uncommitted.')


class TestWhatCommitLeftUncommitted:

    @staticmethod
    def _checkout(tmp_path, others):
        """A committed checkout of `feat` and the files `others`; the spec
        and each of `others` are then edited, and `--all --test --commit`
        runs. Its output's lines."""
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        (root / '.gitignore').write_text('.purlin/runtime/\n__pycache__/\n'
                                         '.pytest_cache/\n', encoding='utf-8')
        for rel in others:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text('one\n', encoding='utf-8')
        _git_repo(root)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8') + '\n',
                        encoding='utf-8')
        for rel in others:
            (root / rel).write_text('two\n', encoding='utf-8')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        return output.splitlines()

    # purlin: run_script PROOF-299
    def test_one_file_left_is_named_with_what_to_do(self, tmp_path):
        lines = self._checkout(tmp_path, ['src/other.py'])
        at = lines.index('1 file is still not committed:')
        assert lines[at + 1:at + 3] == ['  src/other.py', STILL_DO], lines
        assert lines.index('Evidence committed.') < at, lines

    # purlin: run_script PROOF-300
    def test_twelve_files_left_name_ten_and_count_two(self, tmp_path):
        names = ['notes/n%02d.txt' % index for index in range(1, 13)]
        lines = self._checkout(tmp_path, names)
        at = lines.index('12 files are still not committed:')
        assert lines[at + 1:at + 12] == ['  %s' % name
                                         for name in names[:10]] + [
            '  and 2 more'], lines

    # purlin: run_script PROOF-301
    def test_nothing_left_prints_no_such_line(self, tmp_path):
        lines = self._checkout(tmp_path, [])
        assert not [line for line in lines
                    if 'still not committed' in line], lines


# ---------------------------------------------------------------------------
# The test files a full run leaves out
# ---------------------------------------------------------------------------

def _with_unmarked(tmp_path, count):
    """A project whose one marked test passes, beside `count` test files
    that carry no marker and whose test fails."""
    root = _pytest_project(tmp_path)
    for index in range(1, count + 1):
        (root / 'tests' / ('test_plain_%02d.py' % index)).write_text(
            'def test_plain():\n    assert False\n', encoding='utf-8')
    _spec(root, 'feat')
    return root


class TestTheTestFilesAFullRunLeavesOut:

    # purlin: run_script PROOF-303
    def test_twelve_are_counted_under_the_markers_line(self, tmp_path):
        root = _with_unmarked(tmp_path, 12)
        code, output = _run(root, '--all', '--test')
        lines = output.splitlines()
        at = lines.index('Markers: 1 tied to a test, 0 not tied.')
        assert lines[at + 1] == ('12 test files carry no marker and were '
                                 'not run.'), output
        assert code == 0, output
        running = [line for line in lines if line.startswith('Running ')]
        assert len(running) == 1 and 'tests/test_feat.py' in running[0], output
        assert 'test_plain' not in running[0], output

    # purlin: run_script PROOF-304
    def test_one_reads_carries(self, tmp_path):
        root = _with_unmarked(tmp_path, 1)
        _code, output = _run(root, '--all', '--test')
        lines = output.splitlines()
        at = lines.index('Markers: 1 tied to a test, 0 not tied.')
        assert lines[at + 1] == ('1 test file carries no marker and was not '
                                 'run.'), output

    # purlin: run_script PROOF-305
    def test_with_none_nothing_is_said(self, tmp_path):
        root = _with_unmarked(tmp_path, 0)
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert 'no marker' not in output, output

    # purlin: run_script PROOF-306
    def test_a_run_without_all_says_nothing(self, tmp_path):
        root = _with_unmarked(tmp_path, 12)
        code, output = _run(root, '--feature', 'feat', '--test')
        assert code == 0, output
        assert 'no marker' not in output, output

    # purlin: run_script PROOF-307
    def test_a_suite_started_whole_runs_them_and_counts_none(self, tmp_path):
        whole = suites.pytest_suite()
        whole['run'] = whole['run'].replace('{files}', 'tests')
        root = _project(tmp_path, tests=[whole])
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            '# purlin: feat PROOF-1\ndef test_ok():\n    pass\n',
            encoding='utf-8')
        (root / 'tests' / 'test_plain_01.py').write_text(
            'def test_plain():\n    pass\n', encoding='utf-8')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert _ran(root) == ['test_ok', 'test_plain'], output
        assert 'no marker' not in output, output


# ---------------------------------------------------------------------------
# A run over every feature carries forward what did not change
# ---------------------------------------------------------------------------

def _readme_commit(root, text='two\n'):
    """Change and commit `README.md`, which no feature's scope names. The
    new commit."""
    (root / 'README.md').write_text(text, encoding='utf-8')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'docs: the readme')
    return _head(root)


def _section(root, feature, source='local', os_name=None):
    return _evidence(root, feature, source)['platforms'][os_name or HERE_OS]


OTHER_OS = 'windows' if HERE_OS != 'windows' else 'linux'


def _other_system_section(root, feature='export', machine='other-box',
                          fingerprint=None):
    """Write and commit `ci/<feature>.json` holding one section for another
    system, a copy of this system's as another machine took it. The
    section."""
    local = _evidence(root, feature)
    section = dict(local['platforms'][HERE_OS], machine=machine,
                   email='ci@example.com', runner='ci',
                   at='2026-01-02T03:04:05Z')
    if fingerprint is not None:
        section['fingerprint'] = fingerprint
    path = root / '.purlin' / 'evidence' / 'ci' / ('%s.json' % feature)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(local, source='ci',
                                    platforms={OTHER_OS: section}),
                               indent=2, sort_keys=True) + '\n',
                    encoding='utf-8')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'purlin: evidence from the other box')
    return section


class TestARunOverEveryFeatureCarriesForward:
    """`--all` runs what changed and records the rest again on this commit."""

    # purlin: run_script PROOF-308
    def test_all_runs_the_changed_feature_alone(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        (root / 'src' / 'login.py').write_text('VALUE = 2\n',
                                               encoding='utf-8')
        _git(root, 'commit', '-q', '-am', 'login returns 2')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert _started(output) == ['pytest'], output
        assert _ran(root) == ['test_login'], output

    # purlin: run_script PROOF-309
    def test_a_failing_feature_runs_again_with_nothing_changed(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        test = root / 'tests' / 'test_export.py'
        test.write_text(test.read_text(encoding='utf-8').replace(
            'assert True', 'assert False'), encoding='utf-8')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 1 and _ran(root) == ['test_export'], output
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 1, output
        assert _ran(root) == ['test_export'], output
        assert _started(output) == ['pytest'], output

    # purlin: run_script PROOF-310
    def test_an_anchor_runs_with_nothing_changed(self, tmp_path):
        root, _sha = _touched_project(tmp_path, names=('export',))
        anchors = root / 'specs' / '_anchors'
        anchors.mkdir()
        (anchors / 'shared.md').write_text(
            '# Anchor: shared\n\n## Rules\n\n- RULE-1: every answer is JSON\n'
            '\n## Proof\n\n- PROOF-1 (RULE-1): an answer parses as JSON\n',
            encoding='utf-8')
        (root / 'tests' / 'test_shared.py').write_text(
            'import pytest\n\n'
            '# purlin: shared PROOF-1\n'
            'def test_shared():\n'
            '    assert True\n', encoding='utf-8')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'the anchor shared')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert _ran(root) == ['test_shared'], output

    # purlin: run_script PROOF-311
    def test_a_section_taken_with_uncommitted_changes_runs_again(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        (root / 'notes.txt').write_text('a note\n', encoding='utf-8')
        code, output = _run(root, '--feature', 'export', '--test')
        assert code == 0 and _section(root, 'export')['dirty'] is True, output
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'a note and the evidence')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert _ran(root) == ['test_export'], output
        assert _section(root, 'export')['dirty'] is False

    # purlin: run_script PROOF-312
    def test_a_carried_section_names_this_commit_and_the_run_that_took_it(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        taken = _section(root, 'export')
        later = _readme_commit(root)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert _started(output) == [], output
        section = _section(root, 'export')
        assert taken['commit'] != later and section['commit'] == later
        assert [entry.get('carried') for entry in section['proofs']] == [{
            'commit': taken['commit'], 'at': taken['at'],
            'machine': taken['machine'], 'email': taken['email']}], section
        for key in ('at', 'machine', 'email', 'runner', 'dirty',
                    'fingerprint', 'rules'):
            assert section[key] == taken[key], key
        assert _git(root, 'status', '--porcelain', '--',
                    '.purlin/evidence').strip() == '', output

    # purlin: run_script PROOF-313
    def test_a_second_carry_keeps_the_first_run_named(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        taken = _section(root, 'export')
        _readme_commit(root)
        _run(root, '--all', '--test', '--commit')
        latest = _readme_commit(root, 'three\n')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        section = _section(root, 'export')
        assert section['commit'] == latest, section
        assert section['proofs'][0]['carried']['commit'] == taken['commit']

    # purlin: run_script PROOF-314
    def test_a_run_with_nothing_committed_since_leaves_the_files_alone(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        before = {name: _file(root, '.purlin/evidence/local/%s.json' % name)
                  for name in ('login', 'export')}
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert 'Evidence unchanged.' in output.splitlines(), output
        assert not any(line.startswith('Evidence written')
                       for line in output.splitlines()), output
        assert before == {
            name: _file(root, '.purlin/evidence/local/%s.json' % name)
            for name in ('login', 'export')}

    # purlin: run_script PROOF-315
    # purlin: run_script PROOF-322
    def test_another_systems_section_is_carried_and_committed(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        taken = _other_system_section(root)
        later = _readme_commit(root)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        section = _section(root, 'export', 'ci', OTHER_OS)
        assert section['commit'] == later, section
        assert section['machine'] == 'other-box', section
        assert [entry.get('carried') for entry in section['proofs']] == [{
            'commit': taken['commit'], 'at': '2026-01-02T03:04:05Z',
            'machine': 'other-box', 'email': 'ci@example.com'}], section
        assert _git(root, 'status', '--porcelain', '--',
                    '.purlin/evidence').strip() == '', output
        assert ('Carried the %s results of 1 feature forward.'
                % purlin_evidence.os_word(OTHER_OS)) in output.splitlines()

    # purlin: run_script PROOF-316
    def test_another_systems_section_over_other_code_is_left_as_it_was(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        _other_system_section(root, fingerprint={
            'spec': 'a', 'code': 'b', 'tests': 'c'})
        before = _file(root, '.purlin/evidence/ci/export.json')
        _readme_commit(root)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert _file(root, '.purlin/evidence/ci/export.json') == before
        assert not any(line.startswith('Carried the ')
                       for line in output.splitlines()), output

    # purlin: run_script PROOF-317
    def test_the_run_says_how_many_it_ran_and_how_many_it_carried(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        (root / 'src' / 'login.py').write_text('VALUE = 2\n',
                                               encoding='utf-8')
        _git(root, 'commit', '-q', '-am', 'login returns 2')
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert ('Ran pytest on 1 feature and carried 1 forward. purlin:test '
                '--clean runs every test.') in output.splitlines(), output

    # purlin: run_script PROOF-318
    def test_a_run_that_carries_every_feature_says_so(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        _readme_commit(root)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0, output
        assert ('Ran nothing on 0 features and carried 2 forward. '
                'purlin:test --clean runs every test.'
                ) in output.splitlines(), output

    # purlin: run_script PROOF-319
    def test_clean_takes_every_result_again(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        _readme_commit(root)
        _run(root, '--all', '--test', '--commit')
        assert 'carried' in _section(root, 'export')['proofs'][0]
        code, output = _run(root, '--clean', '--test', '--commit')
        assert code == 0, output
        assert _ran(root) == ['test_export', 'test_login'], output
        assert 'Ran pytest on 2 features.' in output.splitlines(), output
        for name in ('login', 'export'):
            assert all('carried' not in entry
                       for entry in _section(root, name)['proofs']), name

    # purlin: run_script PROOF-320
    def test_clean_with_a_feature_named_is_refused(self, tmp_path):
        code, output = _run(_project(tmp_path),
                            '--clean', '--feature', 'feat', '--test')
        lines = output.splitlines()
        assert code == 2, output
        # The refusal first, then the usage line, and one of each.
        assert lines[0] == 'purlin: name features or --clean, not both.', \
            output
        assert lines[1].startswith('Usage: purlin_run.py'), output
        assert [index for index, line in enumerate(lines)
                if line.startswith(('purlin:', 'Usage:'))] == [0, 1], output

    # purlin: run_script PROOF-321
    def test_clean_beside_ci_is_refused(self, tmp_path):
        code, output = _run(_project(tmp_path), '--clean', '--ci')
        lines = output.splitlines()
        assert code == 2, output
        # The refusal as one whole line, first, then the usage line.
        assert lines[0] == 'purlin: --clean goes with --test.', output
        assert lines[1].startswith('Usage: purlin_run.py'), output
        assert [index for index, line in enumerate(lines)
                if line.startswith(('purlin:', 'Usage:'))] == [0, 1], output


SIGN_SCRIPT = os.path.join(REPO, 'scripts', 'review', 'sign.py')


def _shown(root):
    """`purlin:sign --show` for the version 1.0.0. `(exit, lines)`."""
    result = subprocess.run(
        [sys.executable, SIGN_SCRIPT, '--show', '--version', '1.0.0',
         '--project-root', str(root)], capture_output=True, encoding='utf-8')
    return result.returncode, (result.stdout + result.stderr).splitlines()


def _signable_project(tmp_path):
    """`_touched_project`, ignoring the dashboard's files as setup has git
    do, then `README.md` changed and committed. `(root, that commit)`."""
    root, _sha = _touched_project(tmp_path)
    with open(str(root / '.gitignore'), 'a', encoding='utf-8') as handle:
        handle.write('.purlin/report-data.js\npurlin-report.html\n')
    return root, _readme_commit(root)


class TestASignOffAfterARunOverEveryFeature:

    # purlin: signatures PROOF-292
    def test_results_carried_onto_this_commit_count(self, tmp_path):
        root, _later = _signable_project(tmp_path)
        code, output = _run(root, '--all', '--test', '--commit')
        assert code == 0 and _started(output) == [], output
        code, lines = _shown(root)
        assert code == 0, lines
        assert not any(line.startswith('No sign-off') for line in lines), lines
        assert lines[0].startswith('Carried forward from earlier runs by '
                                   'dev@example.com on '), lines

    # purlin: signatures PROOF-293
    def test_a_project_run_in_part_is_still_refused(self, tmp_path):
        root, later = _signable_project(tmp_path)
        code, output = _run(root, '--feature', 'login', '--test', '--commit')
        assert code == 0, output
        assert _shown(root) == (1, [
            'No sign-off: these results are not recorded on this version of '
            'the code, %s: export on %s. Run purlin:test --all --commit, then '
            'purlin:sign.' % (_head(root)[:7],
                              purlin_evidence.os_word(HERE_OS))])
        assert later != _head(root)
