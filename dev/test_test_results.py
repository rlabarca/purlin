"""Tests for the test results `purlin:test` writes, and for the reader.

`scripts/run/results.py` writes `.purlin/tests/<feature>.json` and
`.purlin/tests.md` and commits them; `scripts/mcp/purlin/results.py` reads
them back and hands the payload the `local` source. Every test builds a
throwaway project under `tmp_path` and drives the real run script against it.
"""

import json
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(REPO, 'scripts', 'run', 'purlin_run.py')
PROOF_DIR = os.path.join(REPO, 'scripts', 'proof')
FORMAT = os.path.join(REPO, 'references', 'formats', 'tests_format.md')

for _path in (os.path.join(REPO, 'scripts', 'run'),
              os.path.join(REPO, 'scripts', 'mcp')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import results as writer                                      # noqa: E402
from purlin import payload as payload_module                  # noqa: E402
from purlin import results as reader                          # noqa: E402

STAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


# ---------------------------------------------------------------------------
# A throwaway project
# ---------------------------------------------------------------------------

def _project(tmp_path, gate='passed'):
    root = tmp_path / 'project'
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'gate': gate, 'test_framework': 'pytest'}) + '\n',
        encoding='utf-8')
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
    (root / 'conftest.py').write_text(
        'import sys\n'
        'sys.path.insert(0, %r)\n'
        'from pytest_purlin import pytest_configure  # noqa: F401\n'
        % PROOF_DIR, encoding='utf-8')
    (root / 'tests').mkdir()
    return root


def _spec(root, name='feat', rules=1, proofs=(('PROOF-1', 'RULE-1', ''),)):
    folder = root / 'specs' / 'a'
    folder.mkdir(parents=True, exist_ok=True)
    lines = ['# Feature: %s' % name, '',
             '> Description: A feature.',
             '> Scope: src/feat.py',
             '> Stack: python', '', '## Rules', '']
    for index in range(1, rules + 1):
        lines.append('- RULE-%d: The thing works, case %d [bar: passed] '
                     '[origin: eng]' % (index, index))
    lines.extend(['', '## Proof', ''])
    for proof_id, rule_id, tail in proofs:
        lines.append('- %s (%s): Call it with 2; verify it answers 4%s'
                     % (proof_id, rule_id, tail))
    (folder / ('%s.md' % name)).write_text('\n'.join(lines) + '\n',
                                           encoding='utf-8')


def _test_file(root, name='test_feat.py', body=None):
    (root / 'tests' / name).write_text(
        body if body is not None else
        'import pytest\n\n'
        '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
        'def test_ok():\n'
        '    assert 1 + 1 == 2\n', encoding='utf-8')


def _git(root, *args):
    result = subprocess.run(['git'] + list(args), cwd=str(root),
                            capture_output=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def _repo(root):
    _git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    _git(root, 'config', 'user.email', 'dev@example.com')
    _git(root, 'config', 'user.name', 'Dev')
    _git(root, 'config', 'commit.gpgsign', 'false')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'the spec and its test')


def _run(root, *args):
    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root)] + list(args),
        capture_output=True, encoding='utf-8', cwd=str(root))
    return result.returncode, result.stdout + result.stderr


def _results(root, feature='feat'):
    path = root / '.purlin' / 'tests' / ('%s.json' % feature)
    return json.loads(path.read_text(encoding='utf-8'))


def _scope_tree(root):
    from purlin import specs as specs_module
    return specs_module.scope_tree(str(root), ['src/feat.py'])


def _passed_cell(root, rule_id, feature='feat'):
    data = payload_module.build_payload(str(root))
    entry = next(f for f in data['features'] if f['name'] == feature)
    rule = next(r for r in entry['rules'] if r['id'] == rule_id)
    return rule['cells']['passed']


# ---------------------------------------------------------------------------
# The file one run writes
# ---------------------------------------------------------------------------

@pytest.mark.proof("test_results", "PROOF-1", "RULE-1")
def test_the_file_carries_the_run_and_the_commit(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)

    head = _git(root, 'rev-parse', 'HEAD').strip()
    _run(root, '--all', '--test')
    data = _results(root)
    assert data['schema'] == 'purlin-tests/2'
    # The commit the run observed, which the results commit then sits on top of.
    assert data['commit'] == head
    assert STAMP.match(data['at']), data['at']
    assert data['os'] in ('windows', 'macos', 'linux')
    assert data['source'] == 'local'
    assert len(data['scope_tree']) == 64, data['scope_tree']
    assert sorted(data) == sorted(['schema', 'feature', 'source', 'commit',
                                   'at', 'os', 'scope_tree', 'rules',
                                   'proofs'])


@pytest.mark.proof("test_results", "PROOF-2", "RULE-2")
@pytest.mark.parametrize('proofs,observed,host,word', [
    ({'PROOF-1': {'env': None}}, {'PROOF-1': 'pass'},
     'linux', 'passed'),
    ({'PROOF-1': {'env': None},
      'PROOF-2': {'env': None}},
     {'PROOF-1': 'pass', 'PROOF-2': 'fail'}, 'linux', 'failed'),
    ({'PROOF-1': {'env': None},
      'PROOF-2': {'env': 'windows'}},
     {'PROOF-1': 'pass'}, 'linux', 'not run'),
    ({'PROOF-1': {'env': None}}, {}, 'linux', 'no test'),
    ({}, {}, 'linux', 'no test'),
    ({'PROOF-1': {'manual': True, 'env': None}}, {}, 'linux', 'passed'),
])
def test_the_word_a_rule_reads(proofs, observed, host, word):
    assert writer.rule_word(sorted(proofs), proofs, observed, host) == word


@pytest.mark.proof("test_results", "PROOF-3", "RULE-3")
def test_every_proof_entry_names_its_test_or_says_it_saw_none(tmp_path):
    root = _project(tmp_path)
    _spec(root, rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                 ('PROOF-2', 'RULE-2', '')))
    _test_file(root)
    _repo(root)

    _run(root, '--all', '--test')
    entries = {entry['id']: entry for entry in _results(root)['proofs']}
    assert sorted(entries) == ['PROOF-1', 'PROOF-2']
    for entry in entries.values():
        assert sorted(entry) == ['env', 'id', 'result', 'rule', 'test']
    assert entries['PROOF-1']['result'] == 'pass'
    assert entries['PROOF-1']['rule'] == 'RULE-1'
    assert entries['PROOF-1']['test'] == 'tests/test_feat.py::test_ok'
    assert entries['PROOF-2']['result'] == 'missing'
    assert entries['PROOF-2']['test'] == ''


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

@pytest.mark.proof("test_results", "PROOF-4", "RULE-4")
def test_a_feature_run_leaves_the_other_rows_as_they_were(tmp_path):
    root = _project(tmp_path)
    _spec(root, 'one')
    _spec(root, 'two')
    (root / 'tests' / 'test_one.py').write_text(
        'import pytest\n\n'
        '@pytest.mark.proof("one", "PROOF-1", "RULE-1")\n'
        'def test_one():\n'
        '    assert True\n', encoding='utf-8')
    (root / 'tests' / 'test_two.py').write_text(
        'import pytest\n\n'
        '@pytest.mark.proof("two", "PROOF-1", "RULE-1")\n'
        'def test_two():\n'
        '    assert True\n', encoding='utf-8')
    _repo(root)

    _run(root, '--feature', 'one', '--test')
    first = (root / '.purlin' / 'tests.md').read_text(encoding='utf-8')
    one_row = [line for line in first.splitlines()
               if line.startswith('| one ')][0]
    _run(root, '--feature', 'two', '--test')
    table = (root / '.purlin' / 'tests.md').read_text(encoding='utf-8')

    lines = [line for line in table.splitlines() if line.strip()]
    assert lines[0].startswith('# Test results at ')
    assert lines[1] == ('| Feature | Rules | Passed | Failing | No test '
                        '| Last run |')
    assert one_row in table, table
    assert [line for line in lines if line.startswith('| two ')], table
    assert lines[-1] == writer.TABLE_NOTE


@pytest.mark.proof("run_script", "PROOF-11", "RULE-11")
def test_the_gate_line_answers_for_the_project_not_for_the_run(tmp_path):
    """A `--feature` run still says where the whole project stands."""
    root = _project(tmp_path)
    _spec(root, 'one')
    _spec(root, 'two')
    (root / 'tests' / 'test_one.py').write_text(
        'import pytest\n\n'
        '@pytest.mark.proof("one", "PROOF-1", "RULE-1")\n'
        'def test_one():\n'
        '    assert True\n', encoding='utf-8')
    _repo(root)

    code, output = _run(root, '--feature', 'one', '--test')
    lines = [line for line in output.strip().splitlines() if line.strip()]
    assert lines[-1] == 'gate not met: 1 of 2', output
    assert code == 1, output


@pytest.mark.proof("test_results", "PROOF-5", "RULE-5")
def test_each_row_counts_the_words_and_names_the_last_run():
    table = writer.render_table({
        'one': {'feature': 'one', 'commit': '4f1c2ab9e1d', 'os': 'linux',
                'at': '2026-09-26T12:00:00Z', 'source': 'ci',
                'rules': {'RULE-1': 'passed', 'RULE-2': 'failed',
                          'RULE-3': 'not run'}},
        'two': {'feature': 'two', 'commit': 'abc1234def0', 'os': 'macos',
                'at': '2026-09-26T11:00:00Z', 'source': 'local',
                'rules': {'RULE-1': 'passed'}},
    })
    rows = {line.split('|')[1].strip(): line for line in table.splitlines()
            if line.startswith('| one ') or line.startswith('| two ')}
    assert rows['one'] == ('| one | 3 | 1 | 1 | 1 | 4f1c2ab · '
                           '2026-09-26T12:00:00Z · linux · ci |')
    assert rows['two'] == ('| two | 1 | 1 | 0 | 0 | abc1234 · '
                           '2026-09-26T11:00:00Z · macos · local |')


# ---------------------------------------------------------------------------
# The commit
# ---------------------------------------------------------------------------

@pytest.mark.proof("test_results", "PROOF-6", "RULE-6")
def test_the_run_commits_the_two_files_and_never_pushes(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    head = _git(root, 'rev-parse', 'HEAD').strip()

    code, output = _run(root, '--all', '--test')
    assert 'Test results committed.' in output, output
    assert 'git push' not in output, output
    assert _git(root, 'log', '-1', '--format=%s').strip() == (
        'purlin: tests at %s' % head[:7])
    assert _git(root, 'log', '-1', '--format=%ae').strip() == 'dev@example.com'
    touched = sorted(_git(root, 'show', '--name-only', '--format=',
                          'HEAD').split())
    assert touched == ['.purlin/tests.md', '.purlin/tests/feat.json'], touched
    assert code == 0, output


@pytest.mark.proof("test_results", "PROOF-7", "RULE-7")
def test_a_run_that_saw_the_same_thing_commits_nothing(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)

    _code, first = _run(root, '--all', '--test')
    observed = _results(root)['commit']
    assert 'Test results committed.' in first, first
    for _again in range(2):
        _code, output = _run(root, '--all', '--test')
        assert 'Test results unchanged.' in output, output
    subjects = _git(root, 'log', '--format=%s').splitlines()
    assert len([s for s in subjects if s.startswith('purlin: tests at ')]) == 1
    assert _results(root)['commit'] == observed

    (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'change the code')
    _code, output = _run(root, '--all', '--test')
    assert 'Test results committed.' in output, output


@pytest.mark.proof("test_results", "PROOF-8", "RULE-8")
def test_outside_a_repository_the_files_are_still_written(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)

    _code, output = _run(root, '--all', '--test')
    assert 'there is no git repository to commit them to' in output, output
    assert (root / '.purlin' / 'tests' / 'feat.json').exists()
    assert (root / '.purlin' / 'tests.md').exists()


# ---------------------------------------------------------------------------
# The reader
# ---------------------------------------------------------------------------

def _write_results(root, feature, at, statuses):
    folder = root / '.purlin' / 'tests'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ('%s.json' % feature)).write_text(json.dumps({
        'schema': 'purlin-tests/1', 'feature': feature, 'commit': 'a' * 40,
        'at': at, 'os': 'linux', 'rules': {}, 'proofs': [
            {'id': proof, 'rule': 'RULE-1', 'result': status, 'env': None,
             'test': 'tests/test_feat.py::test_ok'}
            for proof, status in sorted(statuses.items())]}) + '\n',
        encoding='utf-8')


@pytest.mark.proof("test_results", "PROOF-9", "RULE-9")
def test_the_newer_of_the_two_answers_for_a_feature(tmp_path):
    root = _project(tmp_path)
    _write_results(root, 'feat', '2026-09-26T11:00:00Z', {'PROOF-1': 'pass'})
    runtime = {'feat': [{'feature': 'feat', 'id': 'PROOF-1',
                         'status': 'fail'}]}
    proofs_dir = root / '.purlin' / 'runtime' / 'proofs'
    proofs_dir.mkdir(parents=True)
    (proofs_dir / 'feat.json').write_text('{"proofs": []}\n',
                                               encoding='utf-8')

    # The runtime file was written now, which is after the results file.
    assert reader.local_status_map(str(root), runtime) == {
        'feat': {'PROOF-1': 'fail'}}

    # A results file written after this checkout's run answers instead.
    _write_results(root, 'feat', '2126-09-26T11:00:00Z', {'PROOF-1': 'pass'})
    assert reader.local_status_map(str(root), runtime) == {
        'feat': {'PROOF-1': 'pass'}}

    assert reader.local_status_map(str(root), {}) == {
        'feat': {'PROOF-1': 'pass'}}

    os.remove(str(root / '.purlin' / 'tests' / 'feat.json'))
    assert reader.local_status_map(str(root), runtime) == {
        'feat': {'PROOF-1': 'fail'}}


@pytest.mark.proof("test_results", "PROOF-10", "RULE-10")
def test_neither_file_is_gitignored_and_the_cell_reads_them(tmp_path):
    template = os.path.join(REPO, 'templates', 'gitignore.purlin')
    for path in (template, os.path.join(REPO, '.gitignore')):
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert '.purlin/tests' not in text, path
        assert '.purlin\\tests' not in text, path

    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _write_results(root, 'feat', '2026-09-26T11:00:00Z', {'PROOF-1': 'pass'})
    payload = payload_module.build_payload(str(root))
    rule = payload['features'][0]['rules'][0]
    assert rule['cells']['passed']['word'] == 'passed'
    assert rule['cells']['passed']['source'] == 'local'


@pytest.mark.proof("test_results", "PROOF-11", "RULE-11")
def test_the_format_file_is_the_contract():
    with open(FORMAT, encoding='utf-8') as handle:
        text = handle.read()
    first = text.splitlines()[0]
    assert first.startswith('> Format-Version: ')
    assert int(first.split(':')[1].strip()) >= 1
    for name in ('.purlin/tests/<feature>.json', '.purlin/tests.md',
                 'purlin: tests at <sha7>'):
        assert name in text, name
    for field in ('schema', 'feature', 'commit', 'at', 'os', 'rules',
                  'proofs'):
        assert '| `%s` |' % field in text, field
    for word in ('passed', 'failed', 'no test', 'not run'):
        assert '| `%s` |' % word in text, word
    for field in ('id', 'rule', 'result', 'env', 'test'):
        assert '| `%s` |' % field in text, field


# ---------------------------------------------------------------------------
# The ci folder a remote run writes into
# ---------------------------------------------------------------------------

@pytest.mark.proof("test_results", "PROOF-12", "RULE-12")
def test_a_ci_run_writes_into_its_own_folder_and_a_person_s_file_stays(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    _run(root, '--all', '--test')
    mine = _results(root)

    written = writer.write_results(root, writer.build_results(
        'feat', {'rule_order': ['RULE-1'],
                 'proofs_by_rule': {'RULE-1': ['PROOF-1']},
                 'proofs': {'PROOF-1': {'env': 'windows'}}},
        {'PROOF-1': 'pass'}, {'PROOF-1': 'tests/test_feat.py::test_ok'},
        'b' * 40, 'windows', '2126-09-26T12:00:00Z', 'ci', 'c' * 64))

    assert written == '.purlin/tests/ci/feat.json', written
    assert _results(root) == mine, 'a person\'s own file was written over'
    ci = reader.load_results(root, 'ci')['feat']
    assert ci['source'] == 'ci' and ci['os'] == 'windows'
    assert reader.load_results(root, 'local')['feat']['source'] == 'local'


@pytest.mark.proof("test_results", "PROOF-13", "RULE-13")
def test_the_ci_results_reach_the_passed_cell_as_that_platform_s_run(tmp_path):
    """A proof nobody here can run is answered by the runner's own results."""
    root = _project(tmp_path)
    _spec(root, proofs=[('PROOF-1', 'RULE-1', ' @env(windows)')])
    _test_file(root)
    _repo(root)

    runs = reader.ci_runs(root)
    assert runs == {}

    writer.write_results(root, writer.build_results(
        'feat', {'rule_order': ['RULE-1'],
                 'proofs_by_rule': {'RULE-1': ['PROOF-1']},
                 'proofs': {'PROOF-1': {'env': 'windows'}}},
        {'PROOF-1': 'pass'}, {'PROOF-1': 'tests/test_feat.py::test_ok'},
        _git(root, 'rev-parse', 'HEAD').strip(), 'windows', None, 'ci',
        _scope_tree(root)))

    runs = reader.ci_runs(root)
    assert sorted(runs['feat']) == ['windows'], runs
    entry = runs['feat']['windows']
    assert entry['source'] == 'ci' and entry['label'] == 'ci'
    assert entry['proofs'] == [{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'}]

    cell = _passed_cell(root, 'RULE-1')
    assert cell['word'] == 'passed', cell
    assert cell['platforms']['windows']['source'] == 'ci', cell
