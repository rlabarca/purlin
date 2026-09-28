"""Tests for `scripts/run/purlin_run.py`, the one run script.

Every test builds a throwaway project under `tmp_path` and drives the real
script against it: the arms it runs, the two loud failures it raises, the
proofs another operating system owns, the exit codes, the evidence each arm
writes and where it is committed. `scripts/run/evidence.py` has tests of its
own for the file's shape, the merge and the table.

The modules only some arms need (`mutation`, `host`, `remote`) are imported
lazily, so those tests inject fakes through `sys.modules` and read back what
the script called them with.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(REPO, 'scripts', 'run', 'purlin_run.py')
PROOF_DIR = os.path.join(REPO, 'scripts', 'proof')
# A path a test writes into a shell script is spelled with forward slashes:
# bash reads a backslash as an escape, so a Windows path sourced as it comes
# off os.path.join loses every separator. Git bash reads C:/... unchanged.
SHELL_HARNESS = os.path.join(PROOF_DIR, 'shell_purlin.sh').replace(
    os.sep, '/')
PROOF_REL = os.path.join('.purlin', 'runtime', 'proofs')

sys.path.insert(0, os.path.join(REPO, 'scripts', 'mcp'))

from purlin import payload as purlin_payload  # noqa: E402


# ---------------------------------------------------------------------------
# Building a project to run against
# ---------------------------------------------------------------------------

def _project(tmp_path, frameworks='pytest', gate='passed'):
    """A project root with `.purlin/config.json` and an empty `specs/`.

    `passed` is the default because it is the gate a new project is set up
    at. A test that needs the breaks to run asks for `strong`, which is the
    lowest gate that turns them on.
    """
    root = tmp_path / 'project'
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'gate': gate, 'test_framework': frameworks}),
        encoding='utf-8')
    return root


def _spec(root, feature, proofs=(('PROOF-1', 'RULE-1', ''),), rules=1,
          level=None):
    """A two-section spec. Each proof is `(id, rule, tag_suffix)`.

    `level` marks every rule, which is what decides whether a brief is owed.
    """
    lines = ['# %s' % feature, '', '> Scope: src/', '', '## Rules', '']
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


def _pytest_project(tmp_path, body=None, frameworks='pytest', gate='passed'):
    root = _project(tmp_path, frameworks, gate)
    (root / 'conftest.py').write_text(
        'import sys\n'
        'sys.path.insert(0, %r)\n'
        'from pytest_purlin import pytest_configure  # noqa: F401\n'
        % PROOF_DIR, encoding='utf-8')
    (root / 'tests').mkdir()
    (root / 'tests' / 'test_feat.py').write_text(
        body if body is not None else
        'import pytest\n\n'
        '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
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


def _rule(root, feature, rule_id):
    data = purlin_payload.build_payload(str(root))
    entry = next(f for f in data['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


def _passed_word(root, feature, rule_id):
    """The word the rule's passed cell reads, which is what the evidence moves."""
    return _rule(root, feature, rule_id)['cells']['passed']['word']


def _proofs(root, feature):
    path = root / PROOF_REL / ('%s.json' % feature)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheMutmutCopy:
    """mutmut leaves `mutants/` behind, a copy of the project, tests included."""

    @pytest.mark.proof("run_script", "PROOF-62", "RULE-43")
    def test_the_copy_mutmut_leaves_is_never_collected(self, tmp_path):
        root = _pytest_project(tmp_path)
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
        assert [entry['test_file'] for entry in data['proofs']] == [
            'tests/test_feat.py'], data


class TestTheCommandLine:
    """A bad invocation exits 2 and says which part was wrong."""

    @pytest.mark.parametrize('args', [
        (),                                   # no action
        ('--test',),                          # no feature and no --all
        ('--all', '--test', '--audit'),       # two actions
        ('--all', '--feature', 'x', '--test'),
        ('--all', '--audit', '--remote'),     # --remote belongs to --test
        ('--all', '--audit', '--tag', '1.0'),  # nothing pins the evidence
        ('--all', '--test', '--nonsense'),
        ('--all', '--test', '--feature'),     # a flag with no value
        ('--all', '--quick'),  # retired
        ('--all', '--ci', '--commit'),        # a runner always commits
        ('--all', '--test', '--remote', '--commit'),
    ])
    @pytest.mark.proof("run_script", "PROOF-1", "RULE-1")
    def test_bad_invocation_exits_two(self, tmp_path, args):
        root = _project(tmp_path)
        code, output = _run(root, *args)
        assert code == 2, output
        assert 'Usage: purlin_run.py' in output

    @pytest.mark.proof("run_script", "PROOF-2", "RULE-2")
    def test_an_unknown_feature_exits_two(self, tmp_path):
        root = _project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--feature', 'nosuch', '--test')
        assert code == 2
        assert 'no spec named nosuch' in output

    @pytest.mark.proof("run_script", "PROOF-2", "RULE-2")
    def test_a_missing_project_root_exits_two(self, tmp_path):
        code, output = _run(tmp_path / 'nowhere', '--all', '--test')
        assert code == 2
        assert 'is not a directory' in output


# ---------------------------------------------------------------------------
# --test, per framework
# ---------------------------------------------------------------------------

class TestTheTestArmRunsEachFramework:
    """`--test` runs the arms and leaves the runtime proof files behind."""

    @pytest.mark.proof("run_script", "PROOF-3", "RULE-3")
    def test_pytest_arm_writes_the_runtime_proof_file(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert set(data) == {'proofs'}
        assert [e['id'] for e in data['proofs']] == ['PROOF-1']
        entry = data['proofs'][0]
        assert entry['test_file'] == 'tests/test_feat.py'
        assert entry['status'] == 'pass'
        assert set(entry) == {'feature', 'id', 'rule', 'test_file',
                              'test_name', 'status'}
        assert code == 0, output

    @pytest.mark.proof("run_script", "PROOF-3", "RULE-3")
    def test_the_proof_file_is_not_written_under_specs(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _run(root, '--all', '--test')
        stray = [name for name in os.listdir(str(root / 'specs' / 'a'))
                 if not name.endswith('.md')]
        assert stray == []

    @pytest.mark.proof("run_script", "PROOF-4", "RULE-4")
    def test_shell_arm_runs_the_root_test_scripts(self, tmp_path):
        root = _project(tmp_path, frameworks='shell')
        _spec(root, 'feat')
        (root / 'feat.test.sh').write_text(
            'source %s\n'
            'purlin_proof "feat" "PROOF-1" "RULE-1" pass "shell case"\n'
            'purlin_proof_finish\n'
            % SHELL_HARNESS, encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert data['proofs'][0]['test_name'] == 'shell case'
        assert code == 0, output

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 is not installed')
    @pytest.mark.proof("run_script", "PROOF-4", "RULE-4")
    def test_sql_arm_runs_the_tests_directory(self, tmp_path):
        root = _project(tmp_path, frameworks='sql')
        _spec(root, 'feat')
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.sql').write_text(
            "-- @purlin feat PROOF-1 RULE-1\n"
            "-- Test: the select passes\n"
            "SELECT 'PASS';\n", encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert data['proofs'][0]['status'] == 'pass'
        assert code == 0, output

    @pytest.mark.proof("run_script", "PROOF-5", "RULE-5")
    def test_a_failing_test_exits_one_and_records_the_failure(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_no():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert 'the pytest runner exited' in output
        assert _proofs(root, 'feat')['proofs'][0]['status'] == 'fail'

    @pytest.mark.proof("run_script", "PROOF-6", "RULE-6")
    def test_the_run_starts_from_an_empty_proof_directory(self, tmp_path):
        """A file from an earlier run never survives into this run's reading."""
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        stale_dir = root / PROOF_REL
        stale_dir.mkdir(parents=True)
        (stale_dir / 'ghost.json').write_text(
            json.dumps({'proofs': [
                {'feature': 'ghost', 'id': 'PROOF-1', 'rule': 'RULE-1',
                 'test_file': 'gone.py', 'test_name': 't', 'status': 'pass'}]}), encoding='utf-8')
        _run(root, '--all', '--test')
        assert not (stale_dir / 'ghost.json').exists()


# ---------------------------------------------------------------------------
# The two loud failures
# ---------------------------------------------------------------------------

class TestLoudFailureA:
    """An arm ran and its plugin appended nothing."""

    @pytest.mark.proof("run_script", "PROOF-7", "RULE-7")
    def test_an_arm_that_wrote_nothing_is_named(self, tmp_path):
        # The markers are in the tree and the plugin is not loaded: pytest
        # passes, and nothing at all is written. This is the failure the test
        # framework itself reports as success.
        root = _project(tmp_path)
        _spec(root, 'feat')
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n'
            '    assert True\n', encoding='utf-8')
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert 'the pytest arm ran and its plugin wrote no proof entry' in output
        assert '1 marked test(s)' in output

    @pytest.mark.proof("run_script", "PROOF-7", "RULE-7")
    def test_an_arm_with_no_markers_is_not_a_failure(self, tmp_path):
        root = _project(tmp_path, frameworks='shell')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        # Nothing was marked, so nothing went missing: the arm is silent and
        # the table is what says the rule has no evidence yet.
        assert 'wrote no proof entry' not in output
        assert '1 · 1 without a test' in output, output
        assert 'Evidence is missing' not in output, output
        # The rule has no test, so the passed level is not met and the run
        # says so on its last line.
        assert code == 1, output


class TestLoudFailureB:
    """A marker sits in a test source and this run produced no entry for it."""

    @pytest.mark.proof("run_script", "PROOF-8", "RULE-8")
    def test_a_marker_with_no_entry_is_named(self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n'
            '    assert True\n\n'
            '@pytest.mark.proof("feat", "PROOF-2", "RULE-1")\n'
            '@pytest.mark.skip(reason="no tool here")\n'
            'def test_skipped():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', '')))
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        assert 'produced no proof entry' in output
        assert 'feat PROOF-2' in output
        assert 'feat PROOF-1' not in output

    @pytest.mark.proof("run_script", "PROOF-8", "RULE-8")
    def test_the_list_is_bounded_and_counted(self, tmp_path):
        body = ['import pytest\n']
        for index in range(1, 9):
            body.append(
                '@pytest.mark.proof("feat", "PROOF-%d", "RULE-1")\n'
                '@pytest.mark.skip(reason="no tool here")\n'
                'def test_skipped_%d():\n'
                '    assert True\n' % (index, index))
        root = _pytest_project(tmp_path, body='\n'.join(body))
        _spec(root, 'feat',
              proofs=tuple(('PROOF-%d' % i, 'RULE-1', '') for i in range(1, 9)))
        code, output = _run(root, '--all', '--test')
        assert code == 1
        assert '8 marker(s) produced no proof entry' in output
        assert 'and 3 more' in output

    @pytest.mark.proof("run_script", "PROOF-9", "RULE-9")
    def test_a_marker_for_an_unselected_feature_is_not_named(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _spec(root, 'other')
        (root / 'tests' / 'test_other.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("other", "PROOF-1", "RULE-1")\n'
            '@pytest.mark.skip(reason="no tool here")\n'
            'def test_skipped():\n'
            '    assert True\n', encoding='utf-8')
        code, output = _run(root, '--feature', 'feat', '--test')
        assert 'other PROOF-1' not in output
        assert 'Evidence is missing' not in output, output
        # `other` was not run, so the project's passed level is not met and
        # the gate line says so; nothing about it was reported as missing.
        assert code == 1, output


# ---------------------------------------------------------------------------
# Proofs another operating system owns
# ---------------------------------------------------------------------------

class TestEnvScopedProofs:
    """`@env` for another operating system is listed, never run, never missing."""

    def _other_os(self):
        return 'windows' if not sys.platform.startswith('win') else 'linux'

    @pytest.mark.proof("run_script", "PROOF-10", "RULE-10")
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

    @pytest.mark.proof("run_script", "PROOF-10", "RULE-10")
    def test_a_foreign_env_proof_is_not_reported_missing(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n'
            '    assert True\n\n'
            '@pytest.mark.proof("feat", "PROOF-2", "RULE-1")\n'
            '@pytest.mark.skip(reason="wrong host")\n'
            'def test_elsewhere():\n'
            '    assert True\n'))
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other)))
        code, output = _run(root, '--all', '--test')
        assert 'produced no proof entry' not in output
        assert 'Evidence is missing' not in output, output

    @pytest.mark.proof("run_script", "PROOF-10", "RULE-10")
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

    @pytest.mark.proof("run_script", "PROOF-11", "RULE-11")
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

    @pytest.mark.proof("run_script", "PROOF-11", "RULE-11")
    def test_a_project_with_no_specs_says_so(self, tmp_path):
        root = _project(tmp_path)
        code, output = _run(root, '--all', '--test')
        assert 'No specs found under specs/' in output
        assert code == 1


# ---------------------------------------------------------------------------
# The evidence, the audit and the CI arm
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

    @pytest.mark.proof("run_script", "PROOF-12", "RULE-12")
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

    @pytest.mark.proof("run_script", "PROOF-12", "RULE-12")
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

    @pytest.mark.proof("run_script", "PROOF-15", "RULE-15")
    def test_the_log_is_written(self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        log = root / '.purlin' / 'runtime' / 'run.log'
        assert '-m pytest' in log.read_text(encoding='utf-8')


class TestTheBreaks:

    @pytest.mark.proof("run_script", "PROOF-16", "RULE-16")
    def test_the_breaks_are_asked_for_the_scope_and_the_tests(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        capsys.readouterr()
        engine, scope, tests = calls['breaks'][0]
        assert engine == 'mutmut'
        assert scope == {'feat': ['src/']}
        assert tests[('feat', 'RULE-1')][0]['file'] == 'tests/test_feat.py'


class TestWhereEachArmCommits:

    @pytest.mark.proof("run_script", "PROOF-17", "RULE-17")
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

    @pytest.mark.proof("run_script", "PROOF-68", "RULE-47")
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

    @pytest.mark.proof("run_script", "PROOF-68", "RULE-47")
    def test_a_run_on_the_branch_that_keeps_it_commits(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert len(calls['commit']) == 1
        assert 'Tag run:' not in output


class TestTheGateDecidesTheBreaks:
    """Under `passed` nothing measures test strength, so nothing is broken."""

    @pytest.mark.proof("run_script", "PROOF-65", "RULE-45")
    def test_under_passed_no_break_runs_and_the_strength_is_n_a(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='passed')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert calls['breaks'] == [], 'the breaks ran under the passed gate'
        assert 'Strength n/a: the gate is passed.' in output, output
        assert 'feat: test strength n/a' in output, output
        assert _evidence(root)['audit']['mutation'] is None

    @pytest.mark.proof("run_script", "PROOF-65", "RULE-45")
    def test_no_breaks_answers_no_engine(self, capsys):
        purlin_run = _load_run_script()
        breaks = purlin_run._no_breaks('passed')
        capsys.readouterr()
        assert breaks == {'engine': None, 'available': False, 'features': {}}

    @pytest.mark.proof("run_script", "PROOF-66", "RULE-45")
    def test_under_strong_the_audit_measures_and_writes_the_score(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = evidence_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert len(calls['breaks']) == 1, 'the breaks did not run under strong'
        assert 'feat: test strength 80 percent' in output, output
        mutation = _evidence(root)['audit']['mutation']
        assert (mutation['engine'], mutation['score']) == ('mutmut', 80)

    @pytest.mark.proof("run_script", "PROOF-66", "RULE-45")
    def test_a_ci_run_measures_nothing_and_audits_nothing(
            self, tmp_path, evidence_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', level='strong')
        _code, calls = evidence_run(root, '--all', '--ci')
        capsys.readouterr()
        assert calls['breaks'] == []
        assert 'audit' not in _evidence(root, source='ci')


class TestTheAuditWithoutTheEngines:
    """`--audit` still writes its evidence where the break engines are absent."""

    @pytest.mark.proof("run_script", "PROOF-18", "RULE-18")
    def test_missing_break_engines_are_reported_and_the_run_continues(
            self, tmp_path, monkeypatch, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        purlin_run = _load_run_script()
        # The break engines are taken off the path, which is the state a
        # checkout is in before they are installed: `--audit` must still
        # write its evidence and say what it could not measure.
        # Compared through realpath, not abspath: a checkout reached along a
        # symlink (a clone under /tmp on macOS) puts both spellings of this
        # one directory on the path, and abspath leaves the second in place.
        run_dir = os.path.realpath(os.path.join(REPO, 'scripts', 'run'))
        monkeypatch.delitem(sys.modules, 'mutation', raising=False)
        monkeypatch.setattr(
            sys, 'path',
            [p for p in sys.path if os.path.realpath(p or '.') != run_dir])
        code = purlin_run.main(['--project-root', str(root), '--all',
                                '--audit'])
        output = capsys.readouterr().out
        assert 'test strength is not measured' in output
        assert code in (0, 1)
        assert (root / '.purlin' / 'evidence' / 'local' / 'feat.json').exists()


# ---------------------------------------------------------------------------
# The pieces the run script owns, read directly
# ---------------------------------------------------------------------------

class TestTheMarkerScanReadsEveryFrameworkSMarker:

    @pytest.mark.parametrize('framework,name,source', [
        ('pytest', 'test_a.py',
         '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")'),
        ('jest', 'a.test.js',
         'it("does [proof:feat:PROOF-1:RULE-1]", () => {});'),
        ('vitest', 'a.test.ts',
         'it("does [proof:feat:PROOF-1:RULE-1]", () => {});'),
        ('xunit', 'A.cs',
         '[Trait("PurlinProof", "feat:PROOF-1:RULE-1")]'),
        ('shell', 'a.test.sh',
         'purlin_proof "feat" "PROOF-1" "RULE-1" pass "x"'),
        ('sql', 'test_a.sql', '-- @purlin feat PROOF-1 RULE-1'),
    ])
    @pytest.mark.proof("run_script", "PROOF-19", "RULE-19")
    def test_one_marker_is_found(self, tmp_path, framework, name, source):
        purlin_run = _load_run_script()
        (tmp_path / name).write_text(source + '\n', encoding='utf-8')
        assert purlin_run.scan_markers(str(tmp_path), framework) == {
            ('feat', 'PROOF-1')}

    @pytest.mark.proof("run_script", "PROOF-19", "RULE-19")
    def test_node_modules_is_not_scanned(self, tmp_path):
        purlin_run = _load_run_script()
        vendored = tmp_path / 'node_modules' / 'other'
        vendored.mkdir(parents=True)
        (vendored / 'a.test.js').write_text(
            'it("[proof:vendor:PROOF-1:RULE-1]", () => {});\n',
            encoding='utf-8')
        assert purlin_run.scan_markers(str(tmp_path), 'jest') == set()


class TestTheAuditGateLine:
    """The audit answers level 2, so its last line names the strong cell."""

    # The level is `passed`, so the AI audit is not owed on the rule and the
    # strength is the whole of level 2.
    SPEC = ('# Feature: feat\n\n> Scope: src/feat.py\n\n## Rules\n\n'
            '- RULE-1: The value is 2 [level: passed]\n\n## Proof\n\n'
            '- PROOF-1 (RULE-1): Import feat and read VALUE; verify it is '
            'exactly 2\n')

    def _project(self, tmp_path, body=None):
        root = _pytest_project(tmp_path, body=body, gate='strong')
        (root / 'src').mkdir()
        (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
        (root / 'specs' / 'a').mkdir(parents=True, exist_ok=True)
        (root / 'specs' / 'a' / 'feat.md').write_text(self.SPEC,
                                                      encoding='utf-8')
        _git_repo(root)
        return root

    @pytest.mark.proof("run_script", "PROOF-69", "RULE-48")
    def test_a_failing_test_leaves_the_gate_not_met_and_exits_one(self,
                                                                  tmp_path):
        root = self._project(tmp_path, body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n'
            '    assert False\n'))
        code, out = _run(root, '--all', '--audit')
        assert 'gate not met: 0 of 1' in out, out
        assert code == 1, out

    @pytest.mark.proof("run_script", "PROOF-69", "RULE-48")
    def test_a_strong_rule_ends_the_run_at_gate_strong(self, tmp_path):
        root = self._project(tmp_path)
        code, out = _run(root, '--all', '--audit')
        assert 'gate strong: 1 of 1' in out, out
        assert code == 0, out

    @pytest.mark.proof("run_script", "PROOF-69", "RULE-48")
    def test_under_passed_the_line_names_the_passed_cell(self, tmp_path):
        root = self._project(tmp_path)
        _gate(root, 'passed')
        code, out = _run(root, '--all', '--audit')
        assert 'gate passed: 1 of 1' in out, out
        assert code == 0, out


class TestTheEvidenceMeetsThePassedCell:
    """The walk the design traces, run for real against a git checkout.

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

    @pytest.mark.proof("run_script", "PROOF-20", "RULE-20")
    def test_the_evidence_makes_the_passed_cell_read_passed(self, tmp_path):
        root, _seen = self._with_evidence(tmp_path)
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    @pytest.mark.proof("run_script", "PROOF-20", "RULE-20")
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

    @pytest.mark.proof("run_script", "PROOF-20", "RULE-20")
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

    @pytest.mark.proof("run_script", "PROOF-21", "RULE-21")
    def test_the_answer_is_one_of_the_three_env_names(self):
        purlin_run = _load_run_script()
        assert purlin_run.host_os() in ('windows', 'macos', 'linux')


class TestTheRunScriptCarriesNoRetiredVocabulary:

    # The words this release retired, spelled in halves so this list is not
    # itself a hit when the same scan is run over the test file.
    RETIRED = ('rec' + 'eipt', 'ga' + 'uge', 'HOL' + 'LOW', 'PROV' + 'ABLE',
               '@' + 'on(', 'records ' + 'branch', 'CODE' + 'OWNERS',
               'fo' + 'rge', 'appro' + 'val', 'verd' + 'ict',
               'valid' + 'ated/')

    @pytest.mark.proof("run_script", "PROOF-22", "RULE-22")
    def test_no_retired_word_and_no_emoji(self):
        source = open(RUN_SCRIPT, encoding='utf-8').read()
        for word in self.RETIRED:
            assert word not in source, word
        assert all(ord(character) < 0x1F000 for character in source)


class TestTheConsoleCodecNeverEndsTheRun:
    """A Windows console hands Python cp1252, which encodes none of the glyphs.

    The first status table then ends the run with `UnicodeEncodeError: 'charmap'
    codec can't encode characters`, which is how the first CI run of this
    workflow lost its Windows job. The run script reconfigures both streams to
    UTF-8 before it prints anything.
    """

    @pytest.mark.proof("run_script", "PROOF-57", "RULE-39")
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


class TestAFailingArmStatesItsReason:
    """Everything an arm prints is captured, and a job log never shows it.

    The Linux job of the first CI runs reported an arm that exited 1 and an arm
    that was killed at the cap, and said nothing about either: the output had
    gone to `.purlin/runtime/run.log` on a runner that is thrown away. The tail
    goes to stdout as soon as the arm fails, and a CI run publishes each arm's
    whole output beside the dashboard.
    """

    @pytest.mark.proof("run_script", "PROOF-58", "RULE-40")
    def test_a_failing_arm_prints_its_tail_before_the_missing_evidence(
            self, tmp_path):
        root = _pytest_project(tmp_path, body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_bad():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 1, output
        heading = '--- pytest output (last 60 lines) ---'
        assert heading in output, output
        assert '1 failed' in output, output
        assert output.index(heading) < output.index('Evidence is missing'), \
            output

    @pytest.mark.proof("run_script", "PROOF-58", "RULE-40")
    def test_an_arm_that_passed_prints_no_tail(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--test')
        assert code == 0, output
        assert 'output (last 60 lines)' not in output, output

    @pytest.mark.proof("run_script", "PROOF-59", "RULE-40")
    def test_ci_writes_the_whole_run_to_the_log_in_the_tree(
            self, tmp_path, evidence_run, capsys):
        """A run uploads nothing, so what it printed has to be in the tree."""
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
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

    @pytest.mark.proof("run_script", "PROOF-60", "RULE-41")
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
        assert not (root / PROOF_REL).exists(), output
