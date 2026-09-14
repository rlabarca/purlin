"""Tests for `scripts/run/purlin_run.py`, the one run script.

Every test builds a throwaway project under `tmp_path` and drives the real
script against it: the arms it runs, the two loud failures it raises, the
proofs another operating system owns, the exit codes, and the shape of the
`purlin-record/1` dict it hands to the record writer.

The modules lanes 2B and 2C own (`mutation`, `records`, `ci`, `remote`) are
imported lazily inside the `--record` and `--remote` arms, so the `--record`
tests inject fakes through `sys.modules` and read back what the script called
them with.
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
PROOF_REL = os.path.join('.purlin', 'runtime', 'proofs')


# ---------------------------------------------------------------------------
# Building a project to run against
# ---------------------------------------------------------------------------

def _project(tmp_path, frameworks='pytest'):
    """A project root with `.purlin/config.json` and an empty `specs/`."""
    root = tmp_path / 'project'
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'gate': 'tested', 'test_framework': frameworks}),
        encoding='utf-8')
    return root


def _spec(root, feature, proofs=(('PROOF-1', 'RULE-1', ''),), rules=1):
    """A two-section spec. Each proof is `(id, rule, tag_suffix)`."""
    lines = ['# %s' % feature, '', '> Scope: src/', '', '## Rules', '']
    for index in range(1, rules + 1):
        lines.append('- RULE-%d: the software does thing %d' % (index, index))
    lines.extend(['', '## Proof', ''])
    for proof_id, rule_id, suffix in proofs:
        lines.append('- %s (%s): observe thing%s'
                     % (proof_id, rule_id, suffix))
    (root / 'specs' / 'a' / ('%s.md' % feature)).write_text(
        '\n'.join(lines) + '\n', encoding='utf-8')


def _pytest_project(tmp_path, body=None, frameworks='pytest'):
    root = _project(tmp_path, frameworks)
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
        capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout + result.stderr


def _proofs(root, feature, tier='unit'):
    path = root / PROOF_REL / ('%s.%s.json' % (feature, tier))
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:
    """A bad invocation exits 2 and says which part was wrong."""

    @pytest.mark.parametrize('args', [
        (),                                   # no action
        ('--quick',),                         # no feature and no --all
        ('--all', '--quick', '--record'),     # two actions
        ('--all', '--feature', 'x', '--quick'),
        ('--all', '--quick', '--commit'),     # --commit belongs to --record
        ('--all', '--quick', '--tier', 'wide'),
        ('--all', '--quick', '--nonsense'),
        ('--all', '--quick', '--feature'),    # a flag with no value
    ])
    def test_bad_invocation_exits_two(self, tmp_path, args):
        root = _project(tmp_path)
        code, output = _run(root, *args)
        assert code == 2, output
        assert 'Usage: purlin_run.py' in output

    def test_an_unknown_feature_exits_two(self, tmp_path):
        root = _project(tmp_path)
        _spec(root, 'feat')
        code, output = _run(root, '--feature', 'nosuch', '--quick')
        assert code == 2
        assert 'no spec named nosuch' in output

    def test_a_missing_project_root_exits_two(self, tmp_path):
        code, output = _run(tmp_path / 'nowhere', '--all', '--quick')
        assert code == 2
        assert 'is not a directory' in output


# ---------------------------------------------------------------------------
# --quick, per framework
# ---------------------------------------------------------------------------

class TestQuickRunsEachFramework:
    """`--quick` runs the arms and leaves the runtime proof files behind."""

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

    def test_the_proof_file_is_not_written_under_specs(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _run(root, '--all', '--quick')
        stray = [name for name in os.listdir(str(root / 'specs' / 'a'))
                 if not name.endswith('.md')]
        assert stray == []

    def test_shell_arm_runs_the_root_test_scripts(self, tmp_path):
        root = _project(tmp_path, frameworks='shell')
        _spec(root, 'feat')
        (root / 'feat.test.sh').write_text(
            'source %s\n'
            'purlin_proof "feat" "PROOF-1" "RULE-1" pass "shell case"\n'
            'purlin_proof_finish\n'
            % os.path.join(PROOF_DIR, 'shell_purlin.sh'), encoding='utf-8')
        code, output = _run(root, '--all', '--quick')
        data = _proofs(root, 'feat')
        assert data is not None, output
        assert data['proofs'][0]['test_name'] == 'shell case'
        assert code == 0, output

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 is not installed')
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

    def test_an_arm_with_no_markers_is_not_a_failure(self, tmp_path):
        root = _project(tmp_path, frameworks='shell')
        _spec(root, 'feat')
        code, output = _run(root, '--all', '--quick')
        # Nothing was marked, so nothing went missing: the arm is silent and
        # the table is what says the rule has no evidence yet.
        assert 'wrote no proof entry' not in output
        assert 'Drafted 1' in output
        assert code == 0, output


class TestLoudFailureB:
    """A marker sits in a test source and this run produced no entry for it."""

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
        assert code == 0, output


# ---------------------------------------------------------------------------
# Proofs another operating system owns
# ---------------------------------------------------------------------------

class TestEnvScopedProofs:
    """`@env` for another operating system is listed, never run, never missing."""

    def _other_os(self):
        return 'windows' if not sys.platform.startswith('win') else 'linux'

    def test_a_foreign_env_proof_is_listed_as_needing_its_os(self, tmp_path):
        other = self._other_os()
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-1', ' @env(%s)' % other)))
        code, output = _run(root, '--all', '--quick')
        assert 'Proofs another operating system owns:' in output
        assert 'feat PROOF-2: needs %s' % other in output
        assert code == 0, output

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
        assert code == 0, output

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

    def test_the_table_and_one_next_step_are_printed(self, tmp_path):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, output = _run(root, '--all', '--quick')
        assert 'Purlin status:' in output
        assert 'Lowest state' in output
        lines = [line for line in output.strip().splitlines() if line.strip()]
        assert lines[-1].startswith('→ ')

    def test_a_project_with_no_specs_says_so(self, tmp_path):
        root = _project(tmp_path)
        code, output = _run(root, '--all', '--quick')
        assert 'No specs found under specs/' in output
        assert code == 1


# ---------------------------------------------------------------------------
# --record
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


@pytest.fixture
def record_run(monkeypatch, tmp_path):
    """Run `--record` with the 2B and 2C modules faked, and report the calls."""
    calls = {'write': [], 'commit': [], 'tag': [], 'breaks': []}

    def write_record(project_root, record, runner, os_name=None):
        calls['write'].append((record, runner, os_name))
        return os.path.join('.purlin', 'records', 'feat', 'r.json')

    def commit_records(project_root, paths, identity, message):
        calls['commit'].append((paths, identity, message))
        return identity

    def tag_validated(project_root, name, record_paths):
        calls['tag'].append((name, record_paths))

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

    monkeypatch.setitem(sys.modules, 'records', _FakeModule(
        write_record=write_record, commit_records=commit_records,
        tag_validated=tag_validated))
    monkeypatch.setitem(sys.modules, 'mutation', _FakeModule(
        select_engine=select_engine, run_breaks=run_breaks))

    def go(root, *args):
        purlin_run = _load_run_script()
        code = purlin_run.main(['--project-root', str(root), '--record']
                               + list(args))
        return code, calls

    return go


class TestRecordBuildsThePurlinRecord:

    def test_the_record_carries_every_field_the_design_lists(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all')
        capsys.readouterr()
        assert len(calls['write']) == 1
        record, runner, os_name = calls['write'][0]
        assert record['schema'] == 'purlin-record/1'
        assert set(record) >= {'commit', 'dirty', 'runner', 'timestamp',
                               'environment', 'plugins', 'missing', 'features',
                               'scope_tree', 'log'}
        assert isinstance(record['runner'], str)
        assert set(record['environment']) == {'os', 'id', 'kind', 'job',
                                              'host', 'engines'}
        assert record['environment']['os'] in ('windows', 'macos', 'linux')
        assert os_name == record['environment']['os']
        assert runner == record['runner']
        assert record['environment']['kind'] == 'local'
        assert 'pytest' in record['plugins']

    def test_a_rule_carries_its_proofs_tests_result_and_strength(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all')
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
        assert record['scope_tree']['feat']
        assert record['missing'] == []

    def test_a_rule_with_no_evidence_is_listed_as_missing(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat', proofs=(('PROOF-1', 'RULE-1', ''),
                                    ('PROOF-2', 'RULE-2', '')), rules=2)
        _code, calls = record_run(root, '--all')
        capsys.readouterr()
        record = calls['write'][0][0]
        assert record['missing'] == ['feat RULE-2']
        assert record['features']['feat']['rules']['RULE-2']['result'] == 'missing'

    def test_attachments_are_hashed_into_the_record(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        capture = root / '.purlin' / 'runtime' / 'attachments' / 'feat'
        capture.mkdir(parents=True)
        (capture / 'PROOF-1.png').write_bytes(b'not really a png')
        _code, calls = record_run(root, '--all')
        capsys.readouterr()
        rule = calls['write'][0][0]['features']['feat']['rules']['RULE-1']
        assert len(rule['attachments']) == 1
        attachment = rule['attachments'][0]
        assert attachment['proof'] == 'PROOF-1'
        assert len(attachment['sha256']) == 64
        assert attachment['artifact'].endswith('feat/PROOF-1.png')

    def test_the_log_is_written_and_hashed(self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all')
        capsys.readouterr()
        log = calls['write'][0][0]['log']
        assert log['path'] == '.purlin/runtime/run.log'
        assert len(log['sha256']) == 64
        assert (root / '.purlin' / 'runtime' / 'run.log').exists()

    def test_the_breaks_are_asked_for_the_scope_and_the_tests(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--tier', 'unit')
        capsys.readouterr()
        engine, scope, tests, tier = calls['breaks'][0]
        assert engine == 'mutmut'
        assert scope == {'feat': ['src/']}
        assert tests[('feat', 'RULE-1')][0]['file'] == 'tests/test_feat.py'
        assert tier == 'unit'


class TestRecordCommitsAndTags:

    def test_commit_passes_the_developer_identity(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--commit')
        capsys.readouterr()
        paths, identity, message = calls['commit'][0]
        assert identity == 'developer'
        assert message.startswith('purlin: record for ')
        assert len(paths) == 1
        assert calls['write'][0][0]['environment']['kind'] == 'developer'

    def test_ci_passes_the_ci_identity_and_the_ci_runner_slug(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--ci')
        output = capsys.readouterr().out
        assert calls['commit'][0][1] == 'ci'
        assert calls['write'][0][0]['runner'] == 'ci'
        assert calls['write'][0][0]['environment']['kind'] == 'ci'
        # A CI run auto-approves what it may and writes the review list's
        # briefs, and says how many of each in one line.
        assert 'Auto-approved 0 low-risk rules; 0 briefs written.' in output

    def test_tag_names_the_record_it_vouches_for(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all', '--tag', '1.0')
        capsys.readouterr()
        name, paths = calls['tag'][0]
        assert name == '1.0'
        assert paths == ['.purlin/records/feat/r.json'.replace('/', os.sep)]

    def test_without_commit_nothing_is_committed(
            self, tmp_path, record_run, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')
        _code, calls = record_run(root, '--all')
        capsys.readouterr()
        assert calls['commit'] == []


class TestRecordWithoutTheEngines:
    """`--quick` and `--record` both work before lanes 2B and 2C land."""

    def test_missing_break_engines_are_reported_and_the_run_continues(
            self, tmp_path, monkeypatch, capsys):
        root = _pytest_project(tmp_path)
        _spec(root, 'feat')

        def write_record(project_root, record, runner, os_name=None):
            return 'r.json'

        monkeypatch.setitem(sys.modules, 'records', _FakeModule(
            write_record=write_record,
            commit_records=lambda *a, **k: 'developer',
            tag_validated=lambda *a, **k: None))
        purlin_run = _load_run_script()
        # The break engines are taken off the path, which is the state a
        # checkout is in before they are installed: `--record` must still
        # write its record and say what it could not measure.
        run_dir = os.path.join(REPO, 'scripts', 'run')
        monkeypatch.delitem(sys.modules, 'mutation', raising=False)
        monkeypatch.setattr(
            sys, 'path',
            [p for p in sys.path if os.path.abspath(p or '.') != run_dir])
        code = purlin_run.main(['--project-root', str(root), '--all',
                                '--record'])
        output = capsys.readouterr().out
        assert 'test strength is not measured' in output
        assert code == 0


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
    def test_one_marker_is_found(self, tmp_path, framework, name, source):
        purlin_run = _load_run_script()
        (tmp_path / name).write_text(source + '\n', encoding='utf-8')
        assert purlin_run.scan_markers(str(tmp_path), framework) == {
            ('feat', 'PROOF-1')}

    def test_node_modules_is_not_scanned(self, tmp_path):
        purlin_run = _load_run_script()
        vendored = tmp_path / 'node_modules' / 'other'
        vendored.mkdir(parents=True)
        (vendored / 'a.test.js').write_text(
            'it("[proof:vendor:PROOF-1:RULE-1]", () => {});\n',
            encoding='utf-8')
        assert purlin_run.scan_markers(str(tmp_path), 'jest') == set()


class TestHostOs:

    def test_the_answer_is_one_of_the_three_env_names(self):
        purlin_run = _load_run_script()
        assert purlin_run.host_os() in ('windows', 'macos', 'linux')


class TestTheRunScriptCarriesNoRetiredVocabulary:

    # The words this release retired, spelled in halves so this list is not
    # itself a hit when the same scan is run over the test file.
    RETIRED = ('rec' + 'eipt', 'ga' + 'uge', 'HOL' + 'LOW', 'PROV' + 'ABLE',
               '@' + 'on(', 'records ' + 'branch', 'CODE' + 'OWNERS',
               'fo' + 'rge', 'aud' + 'it')

    def test_no_retired_word_and_no_emoji(self):
        source = open(RUN_SCRIPT, encoding='utf-8').read()
        for word in self.RETIRED:
            assert word not in source, word
        # `sys.platform` is the one place the operating system is read.
        marker = 'sys.' + 'plat' + 'form'
        assert source.count(marker[4:]) == source.count(marker)
        assert all(ord(character) < 0x1F000 for character in source)
