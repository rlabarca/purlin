"""Tests for `scripts/run/purlin_run.py`, the one run script.

Every test builds a throwaway project under `tmp_path` and drives the real
script against it: the arms it runs, the two loud failures it raises, the
proofs another operating system owns, the exit codes, the test results the
`--quick` arm writes and commits, and the shape of the `purlin-record/2` dict
the `--ci` arm hands to the record writer.

The modules the record arm needs (`mutation`, `records`, `ci`, `remote`) are
imported lazily inside `--ci` and `--remote`, so those tests inject fakes
through `sys.modules` and read back what the script called them with.
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
          bar=None):
    """A two-section spec. Each proof is `(id, rule, tag_suffix)`.

    `bar` tags every rule, which is what decides whether a brief is owed.
    """
    lines = ['# %s' % feature, '', '> Scope: src/', '', '## Rules', '']
    tag = ' [bar: %s]' % bar if bar else ''
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


def _newest_record(root, feature, source='local'):
    folder = root / '.purlin' / 'records' / source / feature
    newest = sorted(path.name for path in folder.glob('*.json'))[-1]
    return json.loads((folder / newest).read_text(encoding='utf-8'))


def _rule(root, feature, rule_id):
    data = purlin_payload.build_payload(str(root))
    entry = next(f for f in data['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


def _passed_word(root, feature, rule_id):
    """The word the rule's passed cell reads, which is what a record moves."""
    return _rule(root, feature, rule_id)['cells']['passed']['word']


def _proofs(root, feature, tier='unit'):
    path = root / PROOF_REL / ('%s.%s.json' % (feature, tier))
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
        code, output = _run(root, '--all', '--quick')
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
        ('--quick',),                         # no feature and no --all
        ('--all', '--quick', '--audit'),      # two actions
        ('--all', '--feature', 'x', '--quick'),
        ('--all', '--audit', '--remote'),     # --remote belongs to --quick
        ('--all', '--audit', '--tag', '1.0'),  # nothing pins a record now
        ('--all', '--quick', '--tier', 'wide'),
        ('--all', '--quick', '--nonsense'),
        ('--all', '--quick', '--feature'),    # a flag with no value
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
        code, output = _run(root, '--feature', 'nosuch', '--quick')
        assert code == 2
        assert 'no spec named nosuch' in output

    @pytest.mark.proof("run_script", "PROOF-2", "RULE-2")
    def test_a_missing_project_root_exits_two(self, tmp_path):
        code, output = _run(tmp_path / 'nowhere', '--all', '--quick')
        assert code == 2
        assert 'is not a directory' in output


# ---------------------------------------------------------------------------
# --quick, per framework
# ---------------------------------------------------------------------------

class TestQuickRunsEachFramework:
    """`--quick` runs the arms and leaves the runtime proof files behind."""

    @pytest.mark.proof("run_script", "PROOF-3", "RULE-3")
    def test_pytest_arm_writes_the_runtime_proof_file(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--quick')
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert data['tier'] == 'unit'
        assert [e['id'] for e in data['proofs']] == ['PROOF-1']
        entry = data['proofs'][0]
        assert entry['test_file'] == 'tests/test_feat.py'
        assert entry['status'] == 'pass'
        assert set(entry) == {'feature', 'id', 'rule', 'test_file',
                              'test_name', 'status', 'tier'}
        assert code == 0, output

    @pytest.mark.proof("run_script", "PROOF-3", "RULE-3")
    def test_the_proof_file_is_not_written_under_specs(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _run(root, '--all', '--quick')
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
        code, output = _run(root, '--all', '--quick')
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
            "-- @purlin feat PROOF-1 RULE-1 unit\n"
            "-- Test: the select passes\n"
            "SELECT 'PASS';\n", encoding='utf-8')
        code, output = _run(root, '--all', '--quick')
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
        code, output = _run(root, '--all', '--quick')
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
        (stale_dir / 'ghost.unit.json').write_text(
            json.dumps({'tier': 'unit', 'proofs': [
                {'feature': 'ghost', 'id': 'PROOF-1', 'rule': 'RULE-1',
                 'test_file': 'gone.py', 'test_name': 't', 'status': 'pass',
                 'tier': 'unit'}]}), encoding='utf-8')
        _run(root, '--all', '--quick')
        assert not (stale_dir / 'ghost.unit.json').exists()


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
        code, output = _run(root, '--all', '--quick')
        assert code == 1, output
        assert 'the pytest arm ran and its plugin wrote no proof entry' in output
        assert '1 marked test(s)' in output

    @pytest.mark.proof("run_script", "PROOF-7", "RULE-7")
    def test_an_arm_with_no_markers_is_not_a_failure(self, tmp_path):
        root = _project(tmp_path, frameworks='shell')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--quick')
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
        code, output = _run(root, '--all', '--quick')
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
        code, output = _run(root, '--all', '--quick')
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
        code, output = _run(root, '--feature', 'feat', '--quick')
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
        code, output = _run(root, '--all', '--quick')
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
        code, output = _run(root, '--all', '--quick')
        assert 'produced no proof entry' not in output
        assert 'Evidence is missing' not in output, output

    @pytest.mark.proof("run_script", "PROOF-10", "RULE-10")
    def test_an_env_proof_for_this_os_is_run_normally(self, tmp_path):
        purlin_run = _load_run_script()
        here = purlin_run.host_os()
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ' @env(%s)' % here),))
        code, output = _run(root, '--all', '--quick')
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
        _code, output = _run(root, '--all', '--quick')
        assert 'Purlin status:' in output
        assert 'Tests' in output
        lines = [line for line in output.strip().splitlines() if line.strip()]
        assert any(line.startswith('→ ') for line in lines), output
        # A `--quick` run ends with the answer a person came for.
        assert lines[-1].startswith('gate '), output

    @pytest.mark.proof("run_script", "PROOF-11", "RULE-11")
    def test_a_project_with_no_specs_says_so(self, tmp_path):
        root = _project(tmp_path)
        code, output = _run(root, '--all', '--quick')
        assert 'No specs found under specs/' in output
        assert code == 1


# ---------------------------------------------------------------------------
# --ci, the record and the briefs
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
    """A stand-in for a module lane 2B or 2C owns."""

    def __init__(self, **attributes):
        self.__dict__.update(attributes)


def _fake_briefs(monkeypatch, order, briefs):
    """Stand in for the brief writer and note when it ran.

    `order` collects `write_briefs` and `commit` as they happen, which is how
    a test reads whether the files the commit must carry were written before
    it.
    """

    def write_briefs(project_root, payload=None, rules=None, ai=False,
                     source='local'):
        order.append('write_briefs')
        return list(briefs)

    monkeypatch.setitem(sys.modules, 'brief', _FakeModule(
        write_briefs=write_briefs,
        rule_entry=lambda payload, feature, rule: {'bar': 'strong'},
        asks_for_a_review=lambda entry: True))

    records = sys.modules['records']
    committed = records.commit_records

    def commit_records(*args, **kwargs):
        order.append('commit')
        return committed(*args, **kwargs)

    monkeypatch.setattr(records, 'commit_records', commit_records)


@pytest.fixture
def record_run(monkeypatch, tmp_path):
    """Run `--ci` with the record modules faked, and report the calls."""
    calls = {'write': [], 'commit': [], 'breaks': [],
             'local_commit': [], 'commits_here': True}

    def write_record(project_root, record, runner, os_name=None,
                     source='local'):
        calls['write'].append((record, runner, os_name, source))
        return '.purlin/records/%s/feat/r.json' % source

    def commit_records(project_root, paths, message):
        calls['commit'].append((paths, message))
        return 'ci'

    def commit_local_records(project_root, commit):
        calls['local_commit'].append(commit)
        return 'Record committed.'

    def select_engine(config, frameworks):
        return 'mutmut'

    def run_breaks(project_root, engine, scope, tests, tier):
        calls['breaks'].append((engine, scope, tests, tier))
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
    monkeypatch.setitem(sys.modules, 'records', _FakeModule(
        write_record=write_record, commit_records=commit_records,
        load_records=lambda project_root: {},
        commit_local_records=commit_local_records,
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


class TestRecordBuildsThePurlinRecord:
    """The record is CI's, so every test here drives the `--ci` arm.

    At `passed` there is no record at all, which is its own test below, so
    each project here is at `strong`.
    """

    @pytest.mark.proof("run_script", "PROOF-12", "RULE-12")
    def test_the_record_carries_every_field_the_design_lists(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        capsys.readouterr()
        assert len(calls['write']) == 1
        record, runner, os_name, source = calls['write'][0]
        assert source == 'ci', 'the CI arm writes into the ci folder'
        assert record['schema'] == 'purlin-record/3'
        assert record['schema_version'] == 3
        assert set(record) >= {'commit', 'dirty', 'runner', 'timestamp',
                               'environment', 'plugins', 'missing', 'features',
                               'scope_tree', 'log'}
        assert isinstance(record['runner'], str)
        assert set(record['environment']) == {'os', 'id', 'kind', 'job',
                                              'host', 'engines'}
        assert record['environment']['os'] in ('windows', 'macos', 'linux')
        assert os_name == record['environment']['os']
        assert runner == record['runner']
        assert record['environment']['kind'] == 'ci'
        assert 'pytest' in record['plugins']

    @pytest.mark.proof("run_script", "PROOF-13", "RULE-13")
    def test_a_rule_carries_its_proofs_tests_result_and_strength(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--audit')
        capsys.readouterr()
        record = calls['write'][0][0]
        feature = record['features']['feat']
        assert feature['spec'] == 'specs/a/feat.md'
        rule = feature['rules']['RULE-1']
        assert rule['proofs'] == ['PROOF-1']
        assert rule['result'] == 'pass'
        assert rule['tests'][0]['name'] == 'test_ok'
        assert rule['tests'][0]['file'] == 'tests/test_feat.py'
        assert rule['test_strength']['engine'] == 'mutmut'
        assert rule['test_strength']['attribution'] == 'per_scope'
        assert feature['scope_score']['score'] == 80
        assert record['feature'] == 'feat'
        assert isinstance(record['scope_tree'], str)
        assert len(record['scope_tree']) == 64
        assert record['missing'] == []

    @pytest.mark.proof("run_script", "PROOF-13", "RULE-13")
    def test_a_ci_run_measures_no_breaks_and_says_so(
            self, tmp_path, record_run, capsys):
        """The breaks are a person's to measure; CI reruns and verifies."""
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert calls['breaks'] == []
        assert 'Strength n/a: no breaks run on CI.' in output
        rule = calls['write'][0][0]['features']['feat']['rules']['RULE-1']
        assert rule['test_strength']['engine'] == 'none', rule

    @pytest.mark.proof("run_script", "PROOF-13", "RULE-13")
    def test_a_rule_with_no_evidence_is_listed_as_missing(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-2', '')), rules=2)
        _code, calls = record_run(root, '--all', '--ci')
        capsys.readouterr()
        record = calls['write'][0][0]
        assert record['missing'] == ['feat RULE-2']
        assert record['features']['feat']['rules']['RULE-2']['result'] == 'missing'

    @pytest.mark.proof("run_script", "PROOF-14", "RULE-14")
    def test_attachments_are_hashed_into_the_record(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        capture = root / '.purlin' / 'runtime' / 'attachments' / 'feat'
        capture.mkdir(parents=True)
        (capture / 'PROOF-1.png').write_bytes(b'not really a png')
        _code, calls = record_run(root, '--all', '--ci')
        capsys.readouterr()
        rule = calls['write'][0][0]['features']['feat']['rules']['RULE-1']
        assert len(rule['attachments']) == 1
        attachment = rule['attachments'][0]
        assert attachment['proof'] == 'PROOF-1'
        assert len(attachment['sha256']) == 64
        assert attachment['artifact'].endswith('feat/PROOF-1.png')

    @pytest.mark.proof("run_script", "PROOF-15", "RULE-15")
    def test_the_log_is_written_and_hashed(self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        capsys.readouterr()
        log = calls['write'][0][0]['log']
        assert log['path'] == '.purlin/runtime/run.log'
        assert len(log['sha256']) == 64
        assert (root / '.purlin' / 'runtime' / 'run.log').exists()

    @pytest.mark.proof("run_script", "PROOF-16", "RULE-16")
    def test_the_breaks_are_asked_for_the_scope_and_the_tests(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--audit', '--tier', 'unit')
        capsys.readouterr()
        engine, scope, tests, tier = calls['breaks'][0]
        assert engine == 'mutmut'
        assert scope == {'feat': ['src/']}
        assert tests[('feat', 'RULE-1')][0]['file'] == 'tests/test_feat.py'
        assert tier == 'unit'


class TestRecordCommitsAndTags:

    @pytest.mark.proof("run_script", "PROOF-17", "RULE-17")
    def test_the_ci_commit_carries_the_record_and_the_ci_runner_slug(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', bar='passed')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        paths, message = calls['commit'][0]
        assert len(paths) == 1
        assert message.startswith('purlin: record for ')
        assert calls['write'][0][0]['runner'] == 'ci'
        assert calls['write'][0][0]['environment']['kind'] == 'ci'
        # A CI run writes the briefs and nothing else, and says how many in
        # one line. It writes no signature file, ever.
        assert '0 briefs written.' in output
        assert 'Record committed.' in output

    @pytest.mark.proof("run_script", "PROOF-17", "RULE-17")
    def test_at_passed_a_ci_run_commits_the_test_results_instead(
            self, tmp_path, record_run, capsys):
        """There is no record at `passed`, so the results are the evidence."""
        root = _pytest_project(tmp_path, gate='passed')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert calls['write'] == []
        assert 'The gate is passed, so this run writes no record.' in output
        assert (root / '.purlin' / 'tests' / 'ci' / 'feat.json').exists()
        assert len(calls['commit']) == 1, calls['commit']
        paths, message = calls['commit'][0]
        assert message.startswith('purlin: tests at '), message
        assert '.purlin/tests/ci/feat.json' in paths, paths
        assert '.purlin/tests.md' in paths, paths
        assert 'Test results committed.' in output

    @pytest.mark.proof("run_script", "PROOF-68", "RULE-47")
    def test_a_tag_run_writes_nothing_and_says_so(
            self, tmp_path, record_run, capsys):
        """A tag run reruns the tests and verifies; it adds no record."""
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        calls['commits_here'] = False
        calls['commit'] = []
        calls['write'] = []
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out

        assert calls['commit'] == []
        assert calls['write'] == []
        assert 'Tag run: nothing is written.' in output

    @pytest.mark.proof("run_script", "PROOF-68", "RULE-47")
    def test_a_run_on_the_branch_that_keeps_them_commits(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert len(calls['commit']) == 1
        assert 'Tag run:' not in output

    @pytest.mark.proof("run_script", "PROOF-61", "RULE-42")
    def test_ci_hands_the_briefs_to_the_commit(
            self, tmp_path, record_run, monkeypatch, capsys):
        """A brief that exists only on a runner is evidence nobody reads.

        So the files the CI run writes go into the same commit as the record
        they rest on, which means they have to be written before it.
        """
        brief = '.purlin/briefs/ci/feat/RULE-2.5e6f7a8b.brief.json'
        order = []
        _fake_briefs(monkeypatch, order, [brief])

        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out

        paths, _message = calls['commit'][0]
        assert paths == ['.purlin/records/ci/feat/r.json', brief]
        assert order == ['write_briefs', 'commit'], (
            'the commit was made before the files it must carry')
        assert '1 brief written.' in output

    @pytest.mark.proof("run_script", "PROOF-61", "RULE-42")
    @pytest.mark.proof("records", "PROOF-35", "RULE-29")
    def test_an_audit_writes_its_record_into_the_local_folder(
            self, tmp_path, record_run, capsys):
        """`purlin:audit` writes its own record and commits it itself."""
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert len(calls['write']) == 1, output
        _record, _runner, _os_name, source = calls['write'][0]
        assert source == 'local'
        assert calls['local_commit'], 'the audit committed nothing'
        assert calls['commit'] == [], (
            "a local audit does not commit through the git host's API")
        assert 'Record written: .purlin/records/local/feat/r.json' in output
        assert 'Record committed.' in output, output

    @pytest.mark.proof("run_script", "PROOF-61", "RULE-42")
    def test_the_ci_arm_hands_back_the_briefs_and_nothing_else(
            self, tmp_path, monkeypatch, capsys):
        """CI writes no signature file, ever: a runner is nobody."""
        written = '.purlin/briefs/ci/feat/RULE-1.1a2b3c4d.brief.json'
        order = []

        named = []

        def write_briefs(project_root, payload=None, rules=None, ai=False,
                         source='local'):
            order.append('write_briefs')
            named.extend(rules or ())
            return [written]

        monkeypatch.setitem(sys.modules, 'brief', _FakeModule(
            write_briefs=write_briefs,
            rule_entry=lambda payload, feature, rule: {'bar': 'strong'},
            asks_for_a_review=lambda entry: True))

        root = _pytest_project(tmp_path)
        _spec(root, 'feat', bar='strong')
        purlin_run = _load_run_script()
        assert purlin_run._ci_review(str(root), [('feat', 'RULE-1')]) == [
            written]
        assert named == [('feat', 'RULE-1')], (
            'the brief writer chose the rules instead of being handed them')
        assert order == ['write_briefs']
        assert '1 brief written.' in capsys.readouterr().out

    @pytest.mark.proof("run_script", "PROOF-17", "RULE-17")
    def test_a_quick_run_commits_no_record(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--quick')
        capsys.readouterr()
        assert calls['write'] == []
        assert calls['commit'] == []


class TestTheBriefsACiRunCommits:
    """The brief writer is handed the rules; it does not choose them.

    Left to choose, it reads each rule's passed cell, and while the briefs
    are being written the record this run wrote is still uncommitted: its
    source is `local`, which `signed` does not count. Every brief would be
    skipped and the review list would carry rules with nothing for anyone to
    read.
    """

    @pytest.mark.proof("run_script", "PROOF-67", "RULE-46")
    def test_a_strong_bar_rule_that_passed_gets_its_brief_in_the_commit(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', bar='strong')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out

        briefs = sorted(
            path.name for path in
            (root / '.purlin' / 'briefs' / 'ci' / 'feat').glob('*.brief.json'))
        assert len(briefs) == 1, output
        assert briefs[0].startswith('RULE-1.'), briefs
        assert '1 brief written.' in output, output

        paths, _message = calls['commit'][0]
        assert paths == ['.purlin/records/ci/feat/r.json',
                         '.purlin/briefs/ci/feat/%s' % briefs[0]]

    @pytest.mark.proof("run_script", "PROOF-67", "RULE-46")
    def test_a_rule_whose_bar_is_passed_gets_no_brief(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat', bar='passed')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out

        assert not (root / '.purlin' / 'briefs').exists(), output
        assert '0 briefs written.' in output, output
        paths, _message = calls['commit'][0]
        assert paths == ['.purlin/records/ci/feat/r.json']


class TestTheGateDecidesTheBreaks:
    """Under `passed` nothing measures test strength, so nothing is broken.

    Raising the gate to `strong` turns the breaks on, locally and in CI. An
    audit run on this machine measures and prints, and says on its last line
    that what it measured counts only when CI runs it.
    """

    @pytest.mark.proof("run_script", "PROOF-65", "RULE-45")
    def test_under_passed_no_break_runs_and_the_strength_is_n_a(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='passed')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert calls['breaks'] == [], 'the breaks ran under the passed gate'
        assert 'Strength n/a: the gate is passed.' in output, output
        assert 'feat: test strength n/a' in output, output

    @pytest.mark.proof("run_script", "PROOF-65", "RULE-45")
    def test_under_passed_a_ci_run_writes_a_null_strength(
            self, tmp_path, record_run, capsys):
        """A record CI writes above `passed` carries what the breaks found.

        Under `passed` a CI run writes no record at all, so the null strength
        is what the record carries when the engines measured nothing.
        """
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        purlin_run = _load_run_script()
        breaks = purlin_run._no_breaks('passed')
        capsys.readouterr()
        assert breaks == {'engine': None, 'available': False, 'features': {}}

    @pytest.mark.proof("run_script", "PROOF-66", "RULE-45")
    def test_under_strong_the_audit_measures_and_counts(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert len(calls['breaks']) == 1, 'the breaks did not run under strong'
        assert 'feat: test strength 80 percent' in output, output
        assert len(calls['write']) == 1, 'the audit wrote no record'
        assert 'preview' not in output, (
            'a record an audit wrote counts at every gate')

    @pytest.mark.proof("run_script", "PROOF-66", "RULE-45")
    def test_a_ci_run_says_nothing_about_counting(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')
        record_run(root, '--all', '--ci')
        output = capsys.readouterr().out

        assert 'preview' not in output, output

    @pytest.mark.proof("run_script", "PROOF-66", "RULE-45")
    def test_at_signed_a_local_audit_counts_like_any_other(
            self, tmp_path, record_run, capsys):
        """Local counts at every gate, so nothing calls this a preview."""
        root = _pytest_project(tmp_path, gate='signed')
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--audit')
        output = capsys.readouterr().out

        assert len(calls['write']) == 1, 'the audit wrote no record'
        assert 'preview' not in output, output


class TestRecordWithoutTheEngines:
    """`--quick` and `--ci` both work where the break engines are absent."""

    @pytest.mark.proof("run_script", "PROOF-18", "RULE-18")
    def test_missing_break_engines_are_reported_and_the_run_continues(
            self, tmp_path, monkeypatch, capsys):
        root = _pytest_project(tmp_path, gate='strong')
        _spec(root, 'feat')

        def write_record(project_root, record, runner, os_name=None,
                         source='local'):
            return 'r.json'

        monkeypatch.setitem(sys.modules, 'records', _FakeModule(
            write_record=write_record,
            commit_records=lambda *a, **k: 'ci',
            commit_local_records=lambda *a, **k: 'Record committed.',
            load_records=lambda project_root: {},
            commits_here=lambda project_root: True,
            no_commit_line=lambda project_root: ''))
        purlin_run = _load_run_script()
        # The break engines are taken off the path, which is the state a
        # checkout is in before they are installed: `--ci` must still write
        # its record and say what it could not measure.
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


# ---------------------------------------------------------------------------
# The pieces the run script owns, read directly
# ---------------------------------------------------------------------------

class TestTheMarkerScanReadsEveryFrameworkSMarker:

    @pytest.mark.parametrize('framework,name,source', [
        ('pytest', 'test_a.py',
         '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")'),
        ('jest', 'a.test.js',
         'it("does [proof:feat:PROOF-1:RULE-1:unit]", () => {});'),
        ('vitest', 'a.test.ts',
         'it("does [proof:feat:PROOF-1:RULE-1]", () => {});'),
        ('xunit', 'A.cs',
         '[Trait("PurlinProof", "feat:PROOF-1:RULE-1:unit")]'),
        ('shell', 'a.test.sh',
         'purlin_proof "feat" "PROOF-1" "RULE-1" pass "x"'),
        ('sql', 'test_a.sql', '-- @purlin feat PROOF-1 RULE-1 unit'),
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

    # The bar is `passed`, so the AI audit is not owed on the rule and the
    # free checks are the whole of level 2.
    SPEC = ('# Feature: feat\n\n> Scope: src/feat.py\n\n## Rules\n\n'
            '- RULE-1: The value is 2 [bar: passed]\n\n## Proof\n\n'
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

    @pytest.mark.proof("run_script", "PROOF-69", "RULE-48", tier="integration")
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

    @pytest.mark.proof("run_script", "PROOF-69", "RULE-48", tier="integration")
    def test_a_strong_rule_ends_the_run_at_gate_strong(self, tmp_path):
        root = self._project(tmp_path)
        code, out = _run(root, '--all', '--audit')
        assert 'gate strong: 1 of 1' in out, out
        assert code == 0, out

    @pytest.mark.proof("run_script", "PROOF-69", "RULE-48", tier="integration")
    def test_under_passed_the_line_names_the_passed_cell(self, tmp_path):
        root = self._project(tmp_path)
        _gate(root, 'passed')
        code, out = _run(root, '--all', '--audit')
        assert 'gate passed: 1 of 1' in out, out
        assert code == 0, out


class TestARecordMeetsThePassedCell:
    """The walk the design traces, run for real against a git checkout.

    A record is almost never at the literal HEAD: CI writes its record as a
    commit of its own on top of the one it observed. What tells the reader
    the record still describes the code is `scope_tree`, the hash of the
    feature's scoped files, and the passed cell reads `passed` only when the
    record writes that hash the way the reader reads it.
    """

    def _with_a_record(self, tmp_path):
        """A checkout whose CI arm wrote a record, then read at `passed`.

        The record is written at `strong`, which is the gate that writes one
        at all, and the project is then read at `passed`. The CI arm files it
        under `.purlin/records/ci/`, which is the folder that says it is CI's.
        """
        root = _pytest_project(tmp_path, gate='strong')
        (root / 'src').mkdir()
        (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
        _spec(root, 'feat')
        _git_repo(root)
        code, out = _run(root, '--all', '--ci')
        assert code == 0, out
        _gate(root, 'passed')
        return root, out

    @pytest.mark.proof("run_script", "PROOF-20", "RULE-20")
    def test_a_record_makes_the_passed_cell_read_passed(self, tmp_path):
        root, out = self._with_a_record(tmp_path)

        record = _newest_record(root, 'feat', source='ci')
        assert record['source'] == 'ci'
        assert isinstance(record['scope_tree'], str), record['scope_tree']
        assert record['proofs'][0]['id'] == 'PROOF-1'
        assert record['proofs'][0]['status'] == 'pass'
        assert record['feature'] == 'feat'
        assert record['gate'] == 'strong'
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

    @pytest.mark.proof("run_script", "PROOF-20", "RULE-20")
    def test_the_cell_reads_code_changed_when_the_scope_changed(self, tmp_path):
        root, _out = self._with_a_record(tmp_path)
        assert _passed_word(root, 'feat', 'RULE-1') == 'passed'

        (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
        _git(root, 'add', '-A')
        _git(root, 'commit', '-q', '-m', 'change the scoped code')
        assert _passed_word(root, 'feat', 'RULE-1') == 'code changed'


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
             '--all', '--quick'],
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
        code, output = _run(root, '--all', '--quick')
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
        code, output = _run(root, '--all', '--quick')
        assert code == 0, output
        assert 'output (last 60 lines)' not in output, output

    @pytest.mark.proof("run_script", "PROOF-59", "RULE-40")
    def test_ci_writes_the_whole_run_to_the_log_in_the_tree(
            self, tmp_path, record_run, capsys):
        """A run uploads nothing, so what it printed has to be in the tree."""
        root = _pytest_project(tmp_path, gate='strong', body=(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_bad():\n'
            '    assert 1 == 2\n'))
        _spec(root, 'feat')
        record_run(root, '--all', '--ci')
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
            [sys.executable, RUN_SCRIPT, '--all', '--quick',
             '--project-root', ''],
            capture_output=True, encoding='utf-8', cwd=str(root))
        output = result.stdout + result.stderr
        assert result.returncode == 2, output
        assert '--project-root' in output, output
        assert not (root / PROOF_REL).exists(), output
