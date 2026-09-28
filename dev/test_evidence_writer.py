"""Tests for `scripts/run/evidence.py`, the evidence writer, and the run's use of it.

The pure parts, a section, the merge and the table, are called directly. The
run-level parts build a throwaway project under `tmp_path` and drive the real
run script against it.
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

for _path in (os.path.join(REPO, 'scripts', 'run'),
              os.path.join(REPO, 'scripts', 'mcp')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence as writer                                     # noqa: E402
from purlin import evidence as reader                         # noqa: E402
from purlin import fingerprint as fingerprint_module          # noqa: E402
from purlin import payload as payload_module                  # noqa: E402

STAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
HERE = reader.host_os()
OTHER = 'windows' if HERE != 'windows' else 'linux'


# ---------------------------------------------------------------------------
# A throwaway project
# ---------------------------------------------------------------------------

def _project(tmp_path, gate='passed', name='project'):
    root = tmp_path / name
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'gate': gate, 'test_framework': 'pytest',
                    'mutation_engine': 'none'}) + '\n', encoding='utf-8')
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
    (root / 'conftest.py').write_text(
        'import sys\n'
        'sys.path.insert(0, %r)\n'
        'from pytest_purlin import pytest_configure  # noqa: F401\n'
        % PROOF_DIR, encoding='utf-8')
    (root / '.gitignore').write_text('.purlin/runtime/\n__pycache__/\n',
                                     encoding='utf-8')
    (root / 'tests').mkdir()
    return root


def _spec(root, name='feat', rules=1, proofs=(('PROOF-1', 'RULE-1', ''),),
          level='passed'):
    folder = root / 'specs' / 'a'
    folder.mkdir(parents=True, exist_ok=True)
    lines = ['# Feature: %s' % name, '',
             '> Description: A feature.',
             '> Scope: src/feat.py',
             '> Stack: python', '', '## Rules', '']
    for index in range(1, rules + 1):
        lines.append('- RULE-%d: The thing works, case %d [level: %s]'
                     % (index, index, level))
    lines.extend(['', '## Proof', ''])
    for proof_id, rule_id, tail in proofs:
        lines.append('- %s (%s): Call it with 2; verify it answers 4%s'
                     % (proof_id, rule_id, tail))
    (folder / ('%s.md' % name)).write_text('\n'.join(lines) + '\n',
                                           encoding='utf-8')


def _test_file(root, name='test_feat.py', feature='feat'):
    (root / 'tests' / name).write_text(
        'import pytest\n\n'
        '@pytest.mark.proof("%s", "PROOF-1", "RULE-1")\n'
        'def test_ok():\n'
        '    assert 1 + 1 == 2\n' % feature, encoding='utf-8')


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


def _evidence(root, feature='feat', source='local'):
    path = root / '.purlin' / 'evidence' / source / ('%s.json' % feature)
    return json.loads(path.read_text(encoding='utf-8'))


def _section(result='pass', at='2026-09-01T00:00:00Z', commit='a' * 40,
             rules=None):
    return {'commit': commit, 'dirty': False, 'at': at, 'runner': 'dev',
            'fingerprint': {'spec': 's', 'code': 'c', 'tests': 't'},
            'rules': rules or {'RULE-1': 'passed' if result == 'pass'
                               else 'failed'},
            'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'result': result,
                        'env': None, 'manual': False,
                        'test': 'tests/test_feat.py::test_ok'}]}


def _file(source='local', platforms=None, audit=None, feature='feat'):
    data = {'schema': 'purlin-evidence/1', 'feature': feature,
            'source': source, 'spec': 'specs/a/%s.md' % feature,
            'platforms': platforms or {}}
    if audit is not None:
        data['audit'] = audit
    return data


def _put(root, data, source='local', feature='feat'):
    path = root / '.purlin' / 'evidence' / source / ('%s.json' % feature)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(writer.dump(data), encoding='utf-8')
    return path


def _info(rules=('RULE-1',), proofs=None, by_rule=None):
    return {'spec_path': 'specs/a/feat.md', 'rule_order': list(rules),
            'proofs': proofs or {'PROOF-1': {'manual': False, 'env': None,
                                             'rules': ['RULE-1']}},
            'proofs_by_rule': by_rule or {'RULE-1': ['PROOF-1']}}


# ---------------------------------------------------------------------------
# The section a run writes
# ---------------------------------------------------------------------------

@pytest.mark.proof("evidence_writer", "PROOF-1", "RULE-1")
def test_a_test_run_writes_the_feature_file_with_one_section(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    data = _evidence(root)
    assert data['schema'] == 'purlin-evidence/1'
    assert data['source'] == 'local'
    assert data['feature'] == 'feat'
    assert data['spec'] == 'specs/a/feat.md'
    assert list(data['platforms']) == [HERE]
    section = data['platforms'][HERE]
    assert sorted(section) == ['at', 'commit', 'dirty', 'fingerprint',
                               'proofs', 'rules', 'runner']
    assert section['commit'] == _git(root, 'rev-parse', 'HEAD').strip()
    assert len(section['commit']) == 40
    assert STAMP.match(section['at'])
    assert section['runner'] == 'dev'
    assert section['fingerprint'] == fingerprint_module.fingerprint(
        str(root), 'feat')
    assert section['rules'] == {'RULE-1': 'passed'}


@pytest.mark.proof("evidence_writer", "PROOF-2", "RULE-2")
def test_a_rule_reads_the_word_this_run_saw():
    plain = {'PROOF-1': {}, 'PROOF-2': {}}
    assert writer.rule_word(['PROOF-1'], plain, {'PROOF-1': 'pass'},
                            'linux') == 'passed'
    assert writer.rule_word(['PROOF-1', 'PROOF-2'], plain,
                            {'PROOF-1': 'pass', 'PROOF-2': 'fail'},
                            'linux') == 'failed'
    foreign = {'PROOF-1': {}, 'PROOF-2': {'env': 'windows'}}
    assert writer.rule_word(['PROOF-1', 'PROOF-2'], foreign,
                            {'PROOF-1': 'pass'}, 'linux') == 'not run'
    assert writer.rule_word(['PROOF-1'], plain, {}, 'linux') == 'no test'
    assert writer.rule_word([], plain, {}, 'linux') == 'no test'
    assert writer.rule_word(['PROOF-1'], {'PROOF-1': {'manual': True}}, {},
                            'linux') == 'passed'


@pytest.mark.proof("evidence_writer", "PROOF-3", "RULE-3")
def test_one_proof_entry_per_proof_and_test():
    info = _info(rules=('RULE-1', 'RULE-2'),
                 proofs={'PROOF-1': {'manual': False, 'env': None},
                         'PROOF-2': {'manual': False, 'env': None},
                         'PROOF-3': {'manual': False, 'env': OTHER}},
                 by_rule={'RULE-1': ['PROOF-1', 'PROOF-3'],
                          'RULE-2': ['PROOF-2']})
    seen = {'PROOF-1': [
        {'status': 'pass', 'test_file': 'tests/a.py', 'test_name': 'test_a'},
        {'status': 'pass', 'test_file': 'tests/b.py', 'test_name': 'test_b'}]}
    section = writer.build_section(info, seen, HERE, 'a' * 40, False, 'dev',
                                   {'spec': 's', 'code': 'c', 'tests': 't'})
    by_id = {}
    for entry in section['proofs']:
        assert sorted(entry) == ['env', 'id', 'manual', 'result', 'rule',
                                 'test']
        by_id.setdefault(entry['id'], []).append(entry)
    assert [(e['result'], e['test']) for e in by_id['PROOF-1']] == [
        ('pass', 'tests/a.py::test_a'), ('pass', 'tests/b.py::test_b')]
    assert [(e['result'], e['test']) for e in by_id['PROOF-2']] == [
        ('missing', '')]
    assert [(e['result'], e['env']) for e in by_id['PROOF-3']] == [
        ('not run', OTHER)]


# ---------------------------------------------------------------------------
# The merge
# ---------------------------------------------------------------------------

@pytest.mark.proof("evidence_writer", "PROOF-4", "RULE-4")
def test_a_run_replaces_only_its_own_section(tmp_path):
    root = tmp_path
    audit = {'mutation': None, 'rules': {'RULE-1': {
        'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
        'verdict': 'strong', 'findings': [], 'at': 'x', 'commit': 'y'}}}
    windows = _section(at='2026-08-01T00:00:00Z')
    _put(root, _file(platforms={'windows': windows}, audit=audit))

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section())
    data = _evidence(root)
    assert data['platforms']['windows'] == windows
    assert data['audit'] == audit
    assert data['platforms']['linux'] == _section()

    failed = _section(result='fail', at='2026-09-02T00:00:00Z')
    writer.write_section(str(root), 'local', 'feat', _info(), 'linux', failed)
    data = _evidence(root)
    assert data['platforms']['linux'] == failed
    assert data['platforms']['windows'] == windows


@pytest.mark.proof("evidence_writer", "PROOF-5", "RULE-5")
def test_a_rule_the_spec_dropped_is_dropped_from_the_file(tmp_path):
    root = tmp_path
    old = _section(rules={'RULE-1': 'passed', 'RULE-9': 'passed'})
    entry = {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
             'verdict': 'strong', 'findings': [], 'at': 'x', 'commit': 'y'}
    _put(root, _file(platforms={'windows': old},
                     audit={'mutation': None,
                            'rules': {'RULE-1': entry, 'RULE-9': entry}}))

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section())
    data = _evidence(root)
    for section in data['platforms'].values():
        assert sorted(section['rules']) == ['RULE-1']
    assert sorted(data['audit']['rules']) == ['RULE-1']


@pytest.mark.proof("evidence_writer", "PROOF-6", "RULE-6")
def test_a_run_removes_the_evidence_of_a_feature_with_no_spec(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _put(root, _file(feature='gone', platforms={'linux': _section()}),
         feature='gone')
    _put(root, _file(source='ci', feature='gone',
                     platforms={'linux': _section()}),
         source='ci', feature='gone')
    _repo(root)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert not (root / '.purlin' / 'evidence' / 'local' / 'gone.json').exists()
    assert not (root / '.purlin' / 'evidence' / 'ci' / 'gone.json').exists()
    assert (root / '.purlin' / 'evidence' / 'local' / 'feat.json').exists()
    assert ('Removed .purlin/evidence/local/gone.json: no spec defines gone.'
            in out)
    assert ('Removed .purlin/evidence/ci/gone.json: no spec defines gone.'
            in out)


@pytest.mark.proof("evidence_writer", "PROOF-7", "RULE-7")
def test_a_run_that_saw_the_same_thing_leaves_the_file_alone(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    path = root / '.purlin' / 'evidence' / 'local' / 'feat.json'

    _run(root, '--all', '--test')
    first = path.read_bytes()
    _run(root, '--all', '--test')
    assert path.read_bytes() == first

    held = _evidence(root)['platforms'][HERE]
    again = dict(held, at='2030-01-01T00:00:00Z', commit='f' * 40,
                 dirty=not held['dirty'])
    writer.write_section(str(root), 'local', 'feat', _info(), HERE, again)
    assert path.read_bytes() == first


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

@pytest.mark.proof("evidence_writer", "PROOF-8", "RULE-8")
def test_the_table_counts_each_features_newest_section(tmp_path):
    root = tmp_path
    three = _section(at='2026-09-03T00:00:00Z', commit='c' * 40,
                     rules={'RULE-1': 'passed', 'RULE-2': 'failed',
                            'RULE-3': 'not run'})
    _put(root, _file(source='ci', feature='one', platforms={'linux': three}),
         source='ci', feature='one')
    _put(root, _file(feature='one', platforms={
        'macos': _section(at='2026-09-01T00:00:00Z')}), feature='one')
    _put(root, _file(feature='two', platforms={
        'macos': _section(at='2026-09-02T00:00:00Z', commit='b' * 40)}),
         feature='two')

    writer.write_table(str(root))
    text = (root / '.purlin' / 'tests.md').read_text(encoding='utf-8')
    lines = text.splitlines()
    assert lines[0] == '# Tests at ccccccc'
    assert lines[2] == ('| Feature | Rules | Passed | Failing | No test | '
                        'Last run |')
    assert ('| one | 3 | 1 | 1 | 1 | ccccccc · 2026-09-03T00:00:00Z · linux '
            '· ci |') in lines
    assert ('| two | 1 | 1 | 0 | 0 | bbbbbbb · 2026-09-02T00:00:00Z · macos '
            '· local |') in lines


@pytest.mark.proof("evidence_writer", "PROOF-8", "RULE-8")
def test_a_feature_run_leaves_the_other_rows_as_they_were(tmp_path):
    root = _project(tmp_path)
    _spec(root, 'one')
    _spec(root, 'two')
    _test_file(root, 'test_one.py', 'one')
    _test_file(root, 'test_two.py', 'two')
    _repo(root)

    _run(root, '--feature', 'one', '--test')
    table = (root / '.purlin' / 'tests.md').read_text(encoding='utf-8')
    first = [line for line in table.splitlines() if line.startswith('| one')]
    _run(root, '--feature', 'two', '--test')
    table = (root / '.purlin' / 'tests.md').read_text(encoding='utf-8')
    assert [line for line in table.splitlines()
            if line.startswith('| one')] == first
    assert [line for line in table.splitlines() if line.startswith('| two')]


# ---------------------------------------------------------------------------
# Written, and committed when asked
# ---------------------------------------------------------------------------

@pytest.mark.proof("evidence_writer", "PROOF-9", "RULE-9")
def test_a_run_writes_and_does_not_commit(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    head = _git(root, 'rev-parse', 'HEAD').strip()

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert 'Evidence written to .purlin/evidence/local/feat.json.' in out
    assert _git(root, 'rev-parse', 'HEAD').strip() == head
    assert '.purlin/evidence/' in _git(root, 'status', '--porcelain',
                                       '--untracked-files=all')


@pytest.mark.proof("evidence_writer", "PROOF-9", "RULE-9")
def test_several_features_name_the_folder(tmp_path):
    root = _project(tmp_path)
    _spec(root, 'one')
    _spec(root, 'two')
    _test_file(root, 'test_one.py', 'one')
    _test_file(root, 'test_two.py', 'two')
    _repo(root)

    _code, out = _run(root, '--all', '--test')

    assert 'Evidence written to .purlin/evidence/local/ for 2 features.' in out


@pytest.mark.proof("evidence_writer", "PROOF-10", "RULE-10")
def test_commit_commits_the_evidence_and_the_table_once(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    head = _git(root, 'rev-parse', 'HEAD').strip()

    code, out = _run(root, '--all', '--test', '--commit')

    assert code == 0, out
    assert 'Evidence committed.' in out
    assert 'git push' not in out
    assert _git(root, 'log', '-1', '--format=%s').strip() == (
        'purlin: evidence at %s' % head[:7])
    assert _git(root, 'log', '-1', '--format=%ae').strip() == \
        'dev@example.com'
    touched = _git(root, 'show', '--name-only', '--format=', 'HEAD').split()
    assert sorted(touched) == ['.purlin/evidence/local/feat.json',
                               '.purlin/tests.md']

    code, out = _run(root, '--all', '--test', '--commit')
    assert 'Evidence unchanged.' in out, out
    assert len(_git(root, 'log', '--format=%s').splitlines()) == 2


@pytest.mark.proof("evidence_writer", "PROOF-11", "RULE-11")
def test_outside_git_the_files_are_written_and_nothing_is_committed(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)

    _code, out = _run(root, '--all', '--test', '--commit')

    assert (root / '.purlin' / 'evidence' / 'local' / 'feat.json').exists()
    assert (root / '.purlin' / 'tests.md').exists()
    assert 'there is no git repository to commit it to' in out


# ---------------------------------------------------------------------------
# The audit's entries
# ---------------------------------------------------------------------------

def _entry(word='strong'):
    return {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
            'verdict': word, 'findings': [], 'at': 'x', 'commit': 'y'}


@pytest.mark.proof("evidence_writer", "PROOF-12", "RULE-12")
def test_an_audit_replaces_the_entries_it_read_and_no_others(tmp_path):
    root = tmp_path
    info = _info(rules=('RULE-1', 'RULE-2'))
    earlier = _entry('weak')
    _put(root, _file(platforms={'linux': _section()},
                     audit={'mutation': None, 'rules': {'RULE-2': earlier}}))
    first = {'engine': 'mutmut', 'score': 71, 'at': 'a', 'commit': 'c'}

    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': _entry()}, first, True)
    audit = _evidence(root)['audit']
    assert audit['rules'] == {'RULE-1': _entry(), 'RULE-2': earlier}
    assert audit['mutation'] == first

    writer.write_audit(str(root), 'local', 'feat', info, {},
                       {'engine': 'mutmut', 'score': 5, 'at': 'b',
                        'commit': 'd'}, False)
    assert _evidence(root)['audit']['mutation'] == first

    _put(root, _file(feature='fresh'), feature='fresh')
    writer.write_audit(str(root), 'local', 'fresh', info,
                       {'RULE-1': _entry()}, None, False)
    assert _evidence(root, 'fresh')['audit']['mutation'] is None


@pytest.mark.proof("evidence_writer", "PROOF-12", "RULE-12")
def test_an_audit_run_writes_the_entry_for_the_rule_it_read(tmp_path):
    root = _project(tmp_path, gate='strong')
    _spec(root, level='strong')
    _test_file(root)
    _repo(root)

    code, out = _run(root, '--all', '--audit')

    assert 'Evidence written to .purlin/evidence/local/feat.json.' in out
    entry = _evidence(root)['audit']['rules']['RULE-1']
    data = payload_module.build_payload(str(root))
    rule = next(r for f in data['features'] for r in f['rules']
                if r['id'] == 'RULE-1')
    assert (entry['rule_hash'], entry['proof_hash'], entry['test_hash']) == (
        rule['rule_hash'], rule['proof_hash'], rule['test_hash'])
    assert entry['verdict'] == 'strong'
    assert entry['findings'] == []
    assert STAMP.match(entry['at'])
    assert entry['commit'] == _git(root, 'rev-parse', 'HEAD').strip()
    assert rule['cells']['strong']['evidence'] == \
        '.purlin/evidence/local/feat.json'


@pytest.mark.proof("evidence_writer", "PROOF-13", "RULE-13")
def test_neither_the_evidence_nor_the_table_is_ignored():
    for rel in ('templates/gitignore.purlin', '.gitignore'):
        with open(os.path.join(REPO, rel), encoding='utf-8') as handle:
            patterns = [line.strip() for line in handle
                        if line.strip() and not line.startswith('#')]
        for pattern in patterns:
            assert '.purlin/evidence' not in pattern, (rel, pattern)
            assert 'tests.md' not in pattern, (rel, pattern)
