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
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(REPO, 'scripts', 'run', 'purlin_run.py')
REPORTS_REL = os.path.join('.purlin', 'runtime', 'reports')

sys.path.insert(0, os.path.join(REPO, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(REPO, 'dev'))

import fake_claude  # noqa: E402
import suites  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402


# ---------------------------------------------------------------------------
# Building a project to run against
# ---------------------------------------------------------------------------

def _project(tmp_path, tests=None, gate='passed'):
    """A project root with `.purlin/config.json` and an empty `specs/`.

    `tests` is the `tests` setting, one pytest suite by default. `passed` is
    the default gate because it is the gate a new project is set up at. A
    test that needs the breaks to run asks for `strong`, the lowest gate
    that runs them, and sets `mutation_engine`, which is off until named.
    """
    root = tmp_path / 'project'
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'gate': gate, 'tests': (
            [suites.pytest_suite(extra='--ignore=mutants')] if tests is None
            else tests)}), encoding='utf-8')
    return root


def _spec(root, feature, proofs=(('PROOF-1', 'RULE-1', ''),), rules=1,
          level=None, scope='src/', requires=None):
    """A two-section spec. Each proof is `(id, rule, tag_suffix)`.

    `level` marks every rule with that `[level: ...]` tag.
    `scope` is the `> Scope:` line's value, None for no line at all, and
    `requires` the `> Requires:` line's.
    """
    lines = ['# %s' % feature, '']
    if requires:
        lines.append('> Requires: %s' % requires)
    if scope is not None:
        lines.append('> Scope: %s' % scope)
    lines.extend(['', '## Rules', ''])
    tag = ' [level: %s]' % level if level else ''
    for index in range(1, rules + 1):
        lines.append('- RULE-%d: the software does thing %d%s'
                     % (index, index, tag))
    lines.extend(['', '## Proof', ''])
    for proof_id, rule_id, suffix in proofs:
        lines.append('- %s (%s): observe thing%s'
                     % (proof_id, rule_id, suffix))
    (root / 'specs' / 'a' / ('%s.md' % feature)).write_text(
        '\n'.join(lines) + '\n', encoding='utf-8')


def _pytest_project(tmp_path, body=None, gate='passed'):
    root = _project(tmp_path, gate=gate)
    (root / 'tests').mkdir()
    (root / 'tests' / 'test_feat.py').write_text(
        body if body is not None else
        'import pytest\n\n'
        '# purlin: feat PROOF-1\n'
        'def test_ok():\n'
        '    assert 1 + 1 == 2\n', encoding='utf-8')
    return root


def _run(root, *args):
    """The run script as a subprocess. `(returncode, stdout + stderr)`."""
    cwd = str(root) if os.path.isdir(str(root)) else REPO
    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root)] + list(args),
        capture_output=True, encoding='utf-8', cwd=cwd)
    return result.returncode, result.stdout + result.stderr


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


@pytest.fixture
def claude(tmp_path, monkeypatch):
    """A fake `claude` first on PATH: `(install, directory)`.

    `install(**settings)` rewrites what it answers; see `dev/fake_claude.py`.
    """
    directory = tmp_path / 'claude'

    def install(**settings):
        fake_claude.install(directory, **settings)
        return directory

    install()
    monkeypatch.setenv('PATH', str(directory) + os.pathsep
                       + os.environ.get('PATH', ''))
    return install, directory


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


class TestTheCommandLine:
    """A bad invocation exits 2 and says which part was wrong."""

    @pytest.mark.parametrize('args', [
        (),                                   # no action
        ('--all', '--test', '--audit'),       # two actions
        ('--all', '--feature', 'x', '--test'),
        ('--all', '--audit', '--remote'),     # --remote belongs to --test
        ('--all', '--test', '--nonsense'),
        ('--all', '--test', '--feature'),     # a flag with no value
        ('--all', '--ci', '--commit'),        # a runner always commits
        ('--all', '--test', '--remote', '--commit'),
    ])
    # purlin: run_script PROOF-1
    def test_bad_invocation_exits_two(self, tmp_path, args):
        root = _project(tmp_path)
        code, output = _run(root, *args)
        assert code == 2, output
        assert 'Usage: purlin_run.py' in output

    # purlin: run_script PROOF-2
    def test_an_unknown_feature_exits_two(self, tmp_path):
        root = _project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--feature', 'nosuch', '--test')
        assert code == 2
        assert 'no spec named nosuch' in output

    # purlin: run_script PROOF-2
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

    # purlin: run_script PROOF-3
    def test_nothing_is_written_under_specs(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _run(root, '--all', '--test')
        stray = [name for name in os.listdir(str(root / 'specs' / 'a'))
                 if not name.endswith('.md')]
        assert stray == []

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 is not installed')
    # purlin: run_script PROOF-4
    def test_a_sql_script_is_a_test(self, tmp_path):
        root = _project(tmp_path, tests=[suites.sql_suite()])
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', '')))
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_unique.sql').write_text(
            '-- purlin: feat PROOF-1\n'
            'CREATE TABLE users (email TEXT UNIQUE);\n'
            "INSERT INTO users VALUES ('a@test.com');\n"
            'SELECT count(*) FROM users;\n', encoding='utf-8')
        (root / 'tests' / 'test_duplicate.sql').write_text(
            '-- purlin: feat PROOF-2\n'
            'CREATE TABLE users (email TEXT UNIQUE);\n'
            "INSERT INTO users VALUES ('a@test.com');\n"
            "INSERT INTO users VALUES ('a@test.com');\n", encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        results = {entry['id']: entry['result']
                   for entry in _proofs(root, 'feat')}
        assert results == {'PROOF-1': 'pass', 'PROOF-2': 'fail'}, output
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
        assert ('→ Next: run purlin:build. 1 rule has a failing test.'
                in output), output
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
        # The rule has no test, so the last two lines say it does not pass
        # and the gate is not met; no test failed, so the run exits 0.
        assert output.strip().splitlines()[-2:] == [
            'Tests: 0 of 1 rule passes.', 'gate not met: 0 of 1'], output
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

    # purlin: run_script PROOF-8
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
        # `other` was not run, so the project's gate is not met and the gate
        # line says so; nothing about it was reported as missing, and the
        # test the run did run passed, so it exits 0.
        assert output.strip().splitlines()[-1] == 'gate not met: 1 of 2', \
            output
        assert code == 0, output


# ---------------------------------------------------------------------------
# Proofs another operating system owns
# ---------------------------------------------------------------------------

class TestEnvScopedProofs:
    """`@env` for another operating system is listed, never run, never missing."""

    def _other_os(self):
        return 'windows' if not sys.platform.startswith('win') else 'linux'

    # purlin: run_script PROOF-10
    def test_a_foreign_env_proof_is_listed_as_needing_its_os(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other)))
        purlin_run = _load_run_script()
        here = purlin_run.host_os()
        code, output = _run(root, '--all', '--test')
        assert ('feat PROOF-2 needs %s; this machine is %s. A remote runner '
                'runs it: purlin:init adds one.' % (other, here)) in output
        assert 'Evidence is missing' not in output, output

    # purlin: run_script PROOF-10
    def test_a_foreign_env_proof_is_not_reported_missing(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert True\n\n'
            '# purlin: feat PROOF-2\n'
            '@pytest.mark.skip(reason="wrong host")\n'
            'def test_elsewhere():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other)))
        code, output = _run(root, '--all', '--test')
        assert 'have no passing or failing result' not in output
        assert 'Evidence is missing' not in output, output

    # purlin: run_script PROOF-10
    def test_an_env_proof_for_this_os_is_run_normally(self, tmp_path):
        purlin_run = _load_run_script()
        here = purlin_run.host_os()
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ' @env(%s)' % here),))
        code, output = _run(root, '--all', '--test')
        assert 'needs %s' % here not in output
        assert _proofs(root, 'feat') is not None, output
        assert code == 0, output


# ---------------------------------------------------------------------------
# The state table and the next step
# ---------------------------------------------------------------------------

class TestEveryRunEndsWithTheNextStep:

    # purlin: run_script PROOF-11
    def test_the_table_and_one_next_step_are_printed(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, output = _run(root, '--all', '--test')
        assert 'Purlin status:' in output
        assert 'Tests' in output
        lines = [line for line in output.strip().splitlines() if line.strip()]
        assert any(line.startswith('→ ') for line in lines), output
        # A `--test` run ends with the answer a person came for.
        assert lines[-1].startswith('gate '), output
        # A run over one feature answers for the project, and exits on the
        # tests it ran.
        _spec(root, 'other')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert output.strip().splitlines()[-1] == 'gate not met: 1 of 2', \
            output
        assert code == 0, output

    # purlin: run_script PROOF-101
    def test_the_tests_line_and_the_gate_line_count_two_things(
            self, tmp_path):
        # At `strong` the test passes and no audit has read the rule: the
        # tests line counts it, the gate line does not, and the run exits on
        # the tests.
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-2:] == [
            'Tests: 1 of 1 rule passes.', 'gate not met: 0 of 1'], output
        assert code == 0, output
        # A test that fails makes the same run exit 1.
        (root / 'tests' / 'test_feat.py').write_text(
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert 1 == 2\n', encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-2:] == [
            'Tests: 0 of 1 rule passes.', 'gate not met: 0 of 1'], output
        assert code == 1, output

    # purlin: run_script PROOF-101
    def test_at_passed_both_lines_carry_the_same_number(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', rules=2,
              proofs=(('PROOF-1', 'RULE-1', ''),))
        code, output = _run(root, '--all', '--test')
        assert output.strip().splitlines()[-2:] == [
            'Tests: 1 of 2 rules pass.', 'gate not met: 1 of 2'], output
        assert code == 0, output

    # purlin: run_script PROOF-11
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

    def run_breaks(project_root, engine, scope, tests):
        calls['breaks'].append((engine, scope, tests))
        return {
            'engine': engine, 'available': True, 'reason': '',
            'features': {'feat': {
                'scope_score': {'score': 80, 'killed': 4, 'survived': 1},
                'rules': {'RULE-1': {'engine': engine, 'score': 80,
                                     'killed': 4, 'survived': 1,
                                     'attribution': 'per_scope'}}}},
            'log': 'breaks.log'}

    # `commits_here` answers True here; the cases that turn it off set it
    # for themselves.
    monkeypatch.setitem(sys.modules, 'host', _FakeModule(
        commit_files=commit_files,
        commits_here=lambda project_root: calls['commits_here'],
        no_commit_line=lambda project_root: (
            'Tag run: nothing is written. This run reruns the tests and '
            'checks the evidence already committed to signed/0.10.0.')))
    monkeypatch.setitem(sys.modules, 'mutation', _FakeModule(
        select_engine=select_engine, run_breaks=run_breaks))

    def go(root, *args):
        purlin_run = _load_run_script()
        code = purlin_run.main(['--project-root', str(root)] + list(args))
        return code, calls

    return go


class TestTheCiArmCommitsItsSection:
    """A runner writes its own operating system's section and commits it."""

    # purlin: run_script PROOF-12
    def test_the_ci_arm_writes_and_commits_its_section(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _git_repo(root)
        code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert code == 0, output
        data = _evidence(root, source='ci')
        purlin_run = _load_run_script()
        assert list(data['platforms']) == [purlin_run.host_os()]
        section = data['platforms'][purlin_run.host_os()]
        assert section['runner'] == 'ci'
        assert section['rules'] == {'RULE-1': 'passed'}
        assert len(calls['commit']) == 1
        paths, message, merge = calls['commit'][0]
        assert paths == ['.purlin/evidence/ci/feat.json']
        assert message == 'purlin: evidence at %s' % _head(root)[:7]
        assert callable(merge), 'the commit was handed no merge'
        assert 'Evidence committed.' in output
        assert not (root / '.purlin' / 'evidence' / 'local').exists()

    # purlin: run_script PROOF-12
    def test_at_passed_the_ci_arm_does_the_same(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='passed')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert [paths for paths, _m, _merge in calls['commit']] == [
            ['.purlin/evidence/ci/feat.json']]
        assert 'Evidence committed.' in output


class TestTheLog:

    # purlin: run_script PROOF-15
    def test_the_log_is_written(self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        log = root / '.purlin' / 'runtime' / 'run.log'
        assert '-m pytest' in log.read_text(encoding='utf-8')


class TestTheBreaks:

    # purlin: run_script PROOF-16
    def test_the_breaks_are_asked_for_the_scope_and_the_tests(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        engine, scope, tests = calls['breaks'][0]
        assert engine == 'mutmut'
        assert scope == {'feat': ['src/']}
        assert tests[('feat', 'RULE-1')][0]['file'] == 'tests/test_feat.py'


class TestWhereEachArmCommits:

    # purlin: run_script PROOF-17
    def test_a_test_run_and_an_audit_never_use_the_git_hosts_api(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _git_repo(root)
        for action in ('--test', '--audit'):
            _code, calls = evidence_run(root, '--all', action, '--commit')
        output = capsys.readouterr().out
        assert calls['commit'] == [], (
            "a person's run commits through git, not the git host's API")
        assert 'Evidence committed.' in output
        assert not list(root.glob('specs/**/*.signatures'))
        assert not (root / '.purlin' / 'evidence' / 'ci').exists()

    # purlin: run_script PROOF-68
    def test_a_tag_run_writes_nothing_and_says_so(
            self, tmp_path, evidence_run, capsys):
        """A tag run reruns the tests and verifies; it adds no evidence."""
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        purlin_run = _load_run_script()
        calls = evidence_run(root, '--all', '--test')[1]
        calls['commits_here'] = False
        _code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert calls['commit'] == []
        assert not (root / '.purlin' / 'evidence' / 'ci').exists()
        assert 'Tag run: nothing is written.' in output
        assert purlin_run.host_os()

    # purlin: run_script PROOF-68
    def test_a_run_on_the_branch_that_keeps_it_commits(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert len(calls['commit']) == 1
        assert 'Tag run:' not in output


class TestTheGateDecidesTheBreaks:
    """The breaks run only where mutation testing is on and a strength is compared."""

    # purlin: run_script PROOF-65
    def test_under_passed_no_break_runs_and_the_strength_is_not_measured(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='passed')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert calls['breaks'] == [], 'the breaks ran under the passed gate'
        assert 'Test strength: not measured; the gate is passed.' in output, \
            output
        assert _evidence(root)['audit']['mutation'] is None

    # purlin: run_script PROOF-66
    def test_under_strong_the_audit_measures_and_writes_the_score(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='auto')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert len(calls['breaks']) == 1, 'the breaks did not run under strong'
        assert 'Test strength: feat 80% (minimum 70%).' in output, output
        mutation = _evidence(root)['audit']['mutation']
        assert (mutation['engine'], mutation['score']) == ('mutmut', 80)
        cell = _rule(root, 'feat', 'RULE-1')['cells']['strong']
        assert (cell['word'], cell['reasons']) == ('strong', []), cell

    # purlin: run_script PROOF-66
    def test_a_ci_run_measures_nothing_and_audits_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', level='strong')
        _code, calls = evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        assert calls['breaks'] == []
        assert 'audit' not in _evidence(root, source='ci')
        assert fake_claude.calls(directory) == []

    # purlin: run_script PROOF-79
    def test_with_mutation_off_the_audit_alone_decides(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _config(root, mutation_engine='none')
        _spec(root, 'feat')
        code, calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert calls['breaks'] == [], output
        assert 'Test strength: not measured; mutation testing is off.' in \
            output, output
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
        assert 'Test strength: feat 80% (minimum 90%).' in output, output
        assert code == 1, output

    # purlin: run_script PROOF-81
    def test_a_feature_with_no_rule_being_read_is_not_measured(
            self, tmp_path, evidence_run, capsys):
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
        assert sorted(calls['breaks'][0][1]) == ['feat', 'other']
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

def _many(tmp_path, count, gate='strong', level=None):
    """A project with one feature of `count` rules, each with a passing test."""
    body = ['import pytest', '']
    for index in range(1, count + 1):
        body.extend(['',
                     '# purlin: feat PROOF-%d' % index,
                     'def test_rule_%d():' % index,
                     '    assert %d == %d' % (index, index), ''])
    root = _pytest_project(tmp_path, gate=gate, body='\n'.join(body))
    _spec(root, 'feat', rules=count, level=level,
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

    # purlin: run_script PROOF-71
    def test_a_setting_out_of_range_is_read_as_four_with_one_warning(
            self, tmp_path, evidence_run, claude, capsys):
        root = _many(tmp_path, 5)
        _config(root, audit_parallel=40)
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        # The run opens with the warning, as it opens with every warning
        # resolving the settings raised, and the status repeats it.
        assert output.splitlines()[0] == (
            '"audit_parallel" is 40, which is not a whole number from 1 to '
            '16; reading it as 4'), output
        assert 'AI audit: 5 rules to read, 4 at a time.' in output, output

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

    # purlin: run_script PROOF-76
    def test_a_passed_level_is_read_only_at_the_gate_passed(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _many(tmp_path, 2)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing 1 [level: passed]'), encoding='utf-8')
        evidence_run(root, '--all', '--audit')
        assert len(fake_claude.calls(directory)) == 1
        assert sorted(_audited(root)) == ['RULE-2']
        _gate(root, 'passed')
        evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        assert len(fake_claude.calls(directory)) == 3
        assert sorted(_audited(root)) == ['RULE-1', 'RULE-2']

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


class TestWhenTheModelCannotBeReached:

    CAUSES = [
        ('path', {}, 'claude is not on PATH',
         'Install Claude Code, then run purlin:audit again.'),
        ('exit', {'exit_code': 1}, 'claude exited with an error',
         'Run purlin:audit again.'),
        ('timeout', {'sleep': 3}, 'claude timed out after 1 s',
         'Run purlin:audit again.'),
        ('no answer', {'answers': ['It looks fine to me.']},
         'claude answered without a settled line', 'Run purlin:audit again.'),
    ]

    @pytest.mark.parametrize('cause,settings,why,then', CAUSES)
    # purlin: run_script PROOF-82
    def test_nothing_is_written_and_the_cell_says_why(
            self, tmp_path, evidence_run, claude, capsys, monkeypatch,
            cause, settings, why, then):
        install, _directory = claude
        install(**settings)
        _load_run_script()
        import ai_audit
        monkeypatch.setattr(ai_audit, 'MODEL_TIMEOUT', 1)
        if cause == 'path':
            monkeypatch.setattr(ai_audit, 'claude_path', lambda: None)
        root = _many(tmp_path, 2)
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert _audited(root) == {}, _audited(root)
        cell = _rule(root, 'feat', 'RULE-1')['cells']['strong']
        assert cell['word'] == 'not audited', cell
        assert cell['reasons'] == ['the AI audit could not run: %s' % why]
        assert '2 rules could not be audited: %s. %s' % (why, then) in \
            output, output
        assert code == 1, output

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


class TestAFreshAuditStalesASignature:

    @staticmethod
    def _sign(root, rule_id):
        rule = _rule(root, 'feat', rule_id)
        _load_run_script()
        from purlin import signatures as signatures_module
        triple = signatures_module.triple_hash(
            rule['rule_hash'], rule['proof_hash'], rule['test_hash'])
        data = {'schema': 'purlin-signature/1', 'feature': 'feat',
                'rule': rule_id, 'triple': triple[:16],
                'rule_hash': rule['rule_hash'],
                'proof_hash': rule['proof_hash'],
                'test_hash': rule['test_hash'],
                'test_hash_kind': rule['test_hash_kind'],
                'audit_hash': rule['audit_hash'], 'level': rule['level'],
                'signer': 'dev@example.com', 'machine': 'box', 'os': 'linux',
                'note': None, 'timestamp': '2026-09-28T12:00:00Z',
                'gate': 'signed', 'evidence': '.purlin/evidence/local/feat.json'}
        directory = root / 'specs' / 'a' / 'feat.signatures'
        directory.mkdir(exist_ok=True)
        (directory / ('%s.%s.dev.json' % (rule_id, triple[:8]))).write_text(
            json.dumps(data), encoding='utf-8')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'sign(feat): %s' % rule_id)

    # purlin: run_script PROOF-85
    def test_changed_findings_stale_the_signature_and_the_run_says_so(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        root = _many(tmp_path, 1, gate='signed')
        _git_repo(root)
        evidence_run(root, '--all', '--audit', '--commit')
        self._sign(root, 'RULE-1')
        assert _rule(root, 'feat', 'RULE-1')['cells']['signed']['word'] != \
            'stale'
        capsys.readouterr()
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.'])
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert '1 signature went stale: its audit findings changed.' in \
            output, output
        cell = _rule(root, 'feat', 'RULE-1')['cells']['signed']
        assert cell['word'] == 'stale', cell
        assert cell['reasons'] == [
            'audit findings changed after the signature'], cell

    # purlin: run_script PROOF-85
    def test_the_same_findings_stale_nothing(self, tmp_path, evidence_run,
                                             claude, capsys):
        root = _many(tmp_path, 1, gate='signed')
        _git_repo(root)
        evidence_run(root, '--all', '--audit', '--commit')
        self._sign(root, 'RULE-1')
        capsys.readouterr()
        evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert 'went stale' not in output, output
        assert _rule(root, 'feat', 'RULE-1')['cells']['signed']['word'] != \
            'stale'


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
        lines = capsys.readouterr().out.strip().splitlines()
        order = ['AI audit: 1 rule read, 0 strong, 1 weak.',
                 'Test strength: feat 80% (minimum 70%).',
                 '1 rule could not be audited: claude answered without a '
                 'settled line. Run purlin:audit again.',
                 'Evidence written to .purlin/evidence/local/feat.json.',
                 'Evidence committed.',
                 'Audit: 0 strong, 1 weak.',
                 'gate not met: 0 of 2']
        assert lines[-len(order):] == order, lines
        assert code == 1


class TestTheAuditGateLine:
    """Above `passed` the audit answers level 2; at `passed` it blocks nothing."""

    # purlin: run_script PROOF-69
    def test_a_finding_blocks_at_strong(self, tmp_path, evidence_run, claude,
                                        capsys):
        install, _directory = claude
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.'])
        root = _many(tmp_path, 1)
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert output.strip().splitlines()[-1] == 'gate not met: 0 of 1', \
            output
        assert code == 1, output
        install()
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert output.strip().splitlines()[-1] == 'gate strong: 1 of 1', \
            output
        assert code == 0, output

    # purlin: run_script PROOF-69
    def test_a_passed_level_meets_the_strong_line_on_its_tests(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root = _many(tmp_path, 1, level='passed')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert fake_claude.calls(directory) == []
        assert output.strip().splitlines()[-1] == 'gate strong: 1 of 1', \
            output
        assert code == 0, output

    # purlin: run_script PROOF-87
    def test_at_the_gate_passed_a_finding_blocks_nothing(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install(answers=['settled: yes\n- PROOF-1 reads the value alone.'])
        root = _many(tmp_path, 1, gate='passed')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        assert output.strip().splitlines()[-2:] == [
            'Audit: 0 strong, 1 weak. Nothing blocks at the gate passed.',
            'gate passed: 1 of 1'], output
        assert _audited(root)['RULE-1']['findings'] == [
            'PROOF-1 reads the value alone.']
        assert code == 0, output

    # purlin: run_script PROOF-100
    def test_at_signed_the_line_counts_the_gate_and_the_exit_the_audit(
            self, tmp_path, evidence_run, claude, capsys):
        install, _directory = claude
        install()
        root = _many(tmp_path, 1, gate='signed')
        code, _calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out
        # The audit found the rule strong; no one has signed it, so the gate
        # is not met, and an audit cannot write a signature, so it exits 0.
        assert output.strip().splitlines()[-2:] == [
            'Audit: 1 strong, 0 weak.', 'gate not met: 0 of 1'], output
        assert code == 0, output

    # purlin: run_script PROOF-87
    def test_a_failing_test_still_exits_one_at_passed(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '# purlin: feat PROOF-1\n'
            'def test_ok():\n'
            '    assert False\n'))
        _spec(root, 'feat')
        code, out = _run(root, '--all', '--audit')
        assert 'Nothing blocks at the gate passed.' in out, out
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

    # purlin: run_script PROOF-20
    def test_the_evidence_makes_the_passed_cell_read_passed(self, tmp_path):
        root, _seen = self._with_evidence(tmp_path)
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    # purlin: run_script PROOF-20
    def test_a_code_change_leaves_the_cell_out_of_date(self, tmp_path):
        root, seen = self._with_evidence(tmp_path)
        (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell
        assert _rule(root, 'feat', 'RULE-1')['flags']['out_of_date'] is True
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'change the scoped code')
        assert _passed_word(root, 'feat', 'RULE-1') == 'out of date'
        code, out = _run(root, '--all', '--test')
        assert code == 0, out
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    # purlin: run_script PROOF-20
    def test_a_spec_edit_and_a_test_edit_leave_it_out_of_date(self, tmp_path):
        root, seen = self._with_evidence(tmp_path, commit=False)
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'the software does thing 1', 'the software does thing one'),
            encoding='utf-8')
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['reasons'] == ['spec changed since %s' % seen[:7]], cell
        _git(root, 'checkout', '--', 'specs')
        test = root / 'tests' / 'test_feat.py'
        test.write_text(test.read_text(encoding='utf-8') + '\n# edited\n',
                        encoding='utf-8')
        cell = _rule(root, 'feat', 'RULE-1')['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['tests changed since %s' % seen[:7]], cell


class TestHostOs:

    # purlin: run_script PROOF-21
    def test_the_answer_is_one_of_the_three_env_names(self):
        purlin_run = _load_run_script()
        assert purlin_run.host_os() in ('windows', 'macos', 'linux')


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
        assert '\u2192' in output, output


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

    # purlin: run_script PROOF-58
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
        _spec(root, 'feat')
        evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        log = root / '.purlin' / 'runtime' / 'run.log'
        text = log.read_text(encoding='utf-8')
        assert '-m pytest' in text, text
        assert '1 failed' in text, text


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
                     requires=None, failing=()):
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
        _spec(root, name, scope='src/%s.py' % name, requires=requires)
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


class TestARunCoversWhatTheChangeTouched:
    """With no feature named, a run runs the features its change touched."""

    # purlin: run_script PROOF-88
    # purlin: run_script PROOF-97
    def test_a_code_edit_runs_only_the_feature_that_covers_the_file(
            self, tmp_path):
        root, sha = _touched_project(tmp_path)
        export = _file(root, '.purlin/evidence/local/export.json')
        (root / 'src' / 'login.py').write_text('VALUE = 2\n', encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {
            'login': 'code changed since %s' % sha[:7]}, output
        assert _file(root, '.purlin/evidence/local/export.json') == export
        # Only the test file of the feature being run was run.
        assert _ran(root) == ['test_login'], output

    # purlin: run_script PROOF-89
    def test_a_spec_edit_and_a_test_edit_select_their_feature(self, tmp_path):
        root, sha = _touched_project(tmp_path)
        # The run below starts on the commit that holds the first evidence,
        # and the section it writes names that commit.
        later = _head(root)
        spec = root / 'specs' / 'a' / 'export.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing one'), encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'spec changed since %s' % sha[:7]}, output
        test = root / 'tests' / 'test_export.py'
        test.write_text(test.read_text(encoding='utf-8') + '\n# edited\n',
                        encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'tests changed since %s' % later[:7]}, output

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

    # purlin: run_script PROOF-92
    def test_a_spec_that_names_no_files_is_selected_every_time(
            self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        _spec(root, 'export', scope=None)
        _spec(root, 'login', scope='src/nowhere.py')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'the scopes name nothing')
        # The first run also sees the code part move, since the files the
        # scope reaches changed; the one reason every run gives is the last.
        code, output = _run(root, '--test', '--commit')
        assert code == 0, output
        chosen = _selection(output)
        assert sorted(chosen) == ['export', 'login'], output
        for reasons in chosen.values():
            assert reasons.endswith('names no files, so every run includes '
                                    'it'), output
        code, output = _run(root, '--test', '--commit')
        assert code == 0, output
        assert _selection(output) == {
            'export': 'names no files, so every run includes it',
            'login': 'names no files, so every run includes it'}, output

    # purlin: run_script PROOF-93
    def test_an_untracked_file_selects_the_feature_and_is_named(
            self, tmp_path):
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
        code, output = _run(root, '--test')
        assert code == 0, output
        assert _selection(output) == {'login': 'a file is not tracked'}, output
        assert ("src/auth/token.py is under login's scope and is not "
                'tracked, so its content is not part of the evidence until '
                'you git add it.') in output.splitlines(), output
        _git(root, 'add', 'src/auth/token.py')
        _git(root, 'commit', '-q', '-m', 'track the token')
        _code, output = _run(root, '--test', '--commit')
        assert _selection(output) == {
            'login': 'code changed since %s' % sha[:7]}, output
        _code, output = _run(root, '--test')
        assert 'Nothing to run' in output, output

    # purlin: run_script PROOF-94
    def test_the_skipped_line_names_ten_and_counts_the_rest(self, tmp_path):
        names = tuple('f%02d' % index for index in range(1, 13))
        root, sha = _touched_project(tmp_path, names=names)
        (root / 'src' / 'f01.py').write_text('VALUE = 2\n', encoding='utf-8')
        code, output = _run(root, '--test')
        assert code == 0, output
        lines = output.splitlines()
        assert ('Selected 1 of 12 features: f01 (code changed since %s).'
                % sha[:7]) in lines, output
        assert ('Skipped 11 features whose spec, code and tests match their '
                'evidence: f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, '
                'and 1 more. purlin:test --all runs them too.') in lines, output
        assert lines.index(
            'Selected 1 of 12 features: f01 (code changed since %s).'
            % sha[:7]) < lines.index('Running the pytest suite.'), output

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
        assert [line for line in output.splitlines() if line.strip()][-1] == \
            'gate passed: 2 of 2', output

    # purlin: run_script PROOF-95
    def test_nothing_changed_over_a_failing_test_exits_one(self, tmp_path):
        root, _sha = _touched_project(tmp_path, failing=('export',))
        code, output = _run(root, '--test')
        assert 'Nothing to run' in output, output
        assert [line for line in output.splitlines() if line.strip()][-1] == \
            'gate not met: 1 of 2', output
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

    # purlin: run_script PROOF-97
    def test_a_named_feature_runs_only_its_test_files(self, tmp_path):
        root = _project(tmp_path, tests=[suites.shell_suite()])
        for name in ('login', 'export'):
            _spec(root, name)
            (root / ('%s.test.sh' % name)).write_text(
                '# purlin: %s PROOF-1\necho %s >> ran.txt\n' % (name, name),
                encoding='utf-8')
        _code, output = _run(root, '--feature', 'login', '--test')
        assert (root / 'ran.txt').read_text(encoding='utf-8').split() == [
            'login'], output
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert sorted((root / 'ran.txt').read_text(
            encoding='utf-8').split()) == ['export', 'login', 'login'], output

    # purlin: run_script PROOF-98
    def test_all_runs_every_feature_when_nothing_changed(self, tmp_path):
        root, _sha = _touched_project(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert 'Nothing to run' not in output, output
        assert _selection(output) is None, output
        assert 'Running the pytest suite.' in output, output
        assert _ran(root) == ['test_export', 'test_login'], output

    # purlin: run_script PROOF-98
    def test_ci_with_no_feature_named_runs_every_feature(
            self, tmp_path, evidence_run, capsys):
        root, _sha = _touched_project(tmp_path)
        code, calls = evidence_run(root, '--ci')
        output = capsys.readouterr().out
        assert code == 0, output
        assert [sorted(paths) for paths, _m, _merge in calls['commit']] == [
            ['.purlin/evidence/ci/export.json',
             '.purlin/evidence/ci/login.json']], output

    # purlin: run_script PROOF-99
    def test_the_audit_tests_the_selection_and_reads_every_feature(
            self, tmp_path, evidence_run, claude, capsys):
        _install, directory = claude
        root, _sha = _touched_project(tmp_path, gate='strong')
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert 'Nothing to run' in output, output
        assert 'Running the' not in output, output
        assert 'AI audit: 2 rules to read, 2 at a time.' in output, output
        assert len(fake_claude.calls(directory)) == 2
        assert code == 0, output
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert ('AI audit: nothing to read; every rule matches its last '
                'audit.') in output, output
        assert len(fake_claude.calls(directory)) == 2
        spec = root / 'specs' / 'a' / 'login.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'does thing 1', 'does thing one'), encoding='utf-8')
        code, _calls = evidence_run(root, '--audit')
        output = capsys.readouterr().out
        assert sorted(_selection(output)) == ['login'], output
        assert 'AI audit: 1 rule to read, 1 at a time.' in output, output
        assert len(fake_claude.calls(directory)) == 3
        assert code == 0, output
