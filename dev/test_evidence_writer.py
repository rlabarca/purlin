"""Tests for `scripts/run/evidence.py`, the evidence writer, and the run's use of it.

The pure parts, a section, the merge and the table, are called directly. The
run-level parts build a throwaway project under `tmp_path` and drive the real
run script against it.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(REPO, 'scripts', 'run', 'purlin_run.py')

for _path in (os.path.join(REPO, 'scripts', 'run'),
              os.path.join(REPO, 'scripts', 'mcp'),
              os.path.join(REPO, 'dev')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence as writer                                     # noqa: E402
from purlin import evidence as reader                         # noqa: E402
from purlin import fingerprint as fingerprint_module          # noqa: E402
from purlin import payload as payload_module                  # noqa: E402
import suites                                                 # noqa: E402

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
        json.dumps({'gate': gate, 'tests': [suites.pytest_suite()],
                    'mutation_engine': 'none'}) + '\n', encoding='utf-8')
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
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
        '# purlin: %s PROOF-1\n'
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
            'proofs': proofs if proofs is not None else {
                'PROOF-1': {'manual': False, 'env': None, 'rules': ['RULE-1']}},
            'proofs_by_rule': (by_rule if by_rule is not None
                               else {'RULE-1': ['PROOF-1']})}


# ---------------------------------------------------------------------------
# The section a run writes
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-1
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
    assert section['dirty'] is False
    assert section['proofs'] == [
        {'id': 'PROOF-1', 'rule': 'RULE-1', 'result': 'pass', 'env': None,
         'manual': False, 'test': 'tests/test_feat.py::test_ok'}]

    # A tracked file changed and not committed, and an email of another shape.
    (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
    _git(root, 'config', 'user.email', 'Jane.Doe+ci@Example.com')
    code, out = _run(root, '--all', '--test')
    assert code == 0, out
    section = _evidence(root)['platforms'][HERE]
    assert section['dirty'] is True
    assert section['runner'] == 'jane-doe-ci'


# purlin: evidence_writer PROOF-2
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
    assert writer.rule_word(['PROOF-1'], {'PROOF-1': {'env': 'linux'}},
                            {'PROOF-1': 'pass'}, 'linux') == 'passed'
    assert writer.rule_word(['PROOF-1', 'PROOF-2'], foreign,
                            {'PROOF-1': 'fail'}, 'linux') == 'failed'
    manual = {'PROOF-1': {'manual': True}, 'PROOF-2': {}}
    assert writer.rule_word(['PROOF-1', 'PROOF-2'], manual,
                            {'PROOF-2': 'fail'}, 'linux') == 'failed'


# purlin: evidence_writer PROOF-3
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
    assert by_id['PROOF-3'][0]['test'] == ''

    # A failing test, a @manual proof, and the rule each entry names.
    info['proofs'].update({'PROOF-4': {'manual': False, 'env': None},
                           'PROOF-5': {'manual': True, 'env': None}})
    info['proofs_by_rule']['RULE-2'] = ['PROOF-2', 'PROOF-4', 'PROOF-5']
    seen['PROOF-4'] = [{'status': 'fail', 'test_file': 'tests/c.py',
                        'test_name': 'test_c'}]
    section = writer.build_section(info, seen, HERE, 'a' * 40, False, 'dev',
                                   {'spec': 's', 'code': 'c', 'tests': 't'})
    assert [(e['id'], e['rule'], e['result'], e['manual'], e['test'])
            for e in section['proofs']] == [
        ('PROOF-1', 'RULE-1', 'pass', False, 'tests/a.py::test_a'),
        ('PROOF-1', 'RULE-1', 'pass', False, 'tests/b.py::test_b'),
        ('PROOF-3', 'RULE-1', 'not run', False, ''),
        ('PROOF-2', 'RULE-2', 'missing', False, ''),
        ('PROOF-4', 'RULE-2', 'fail', False, 'tests/c.py::test_c'),
        ('PROOF-5', 'RULE-2', 'missing', True, '')]


# purlin: evidence_writer PROOF-15
def test_a_rule_with_no_proof_is_answered_by_its_rule_marked_test():
    info = _info(rules=('RULE-1', 'RULE-2', 'RULE-3'), proofs={},
                 by_rule={})
    seen = {
        'RULE-1': [{'status': 'pass', 'test_file': 'tests/a.py',
                    'test_name': 'test_a'}],
        'RULE-2': [{'status': 'fail', 'test_file': 'tests/b.py',
                    'test_name': 'test_b'}]}
    section = writer.build_section(info, seen, HERE, 'a' * 40, False, 'dev',
                                   {'spec': 's', 'code': 'c', 'tests': 't'})
    assert section['rules'] == {'RULE-1': 'passed', 'RULE-2': 'failed',
                                'RULE-3': 'no test'}
    assert [(e['id'], e['rule'], e['result'], e['test'])
            for e in section['proofs']] == [
        ('RULE-1', 'RULE-1', 'pass', 'tests/a.py::test_a'),
        ('RULE-2', 'RULE-2', 'fail', 'tests/b.py::test_b')]

    # Two tests marked with one rule's id, one passing and one failing.
    two = writer.build_section(
        _info(rules=('RULE-4',), proofs={}, by_rule={}),
        {'RULE-4': [{'status': 'pass', 'test_file': 'tests/d.py',
                     'test_name': 'test_d'},
                    {'status': 'fail', 'test_file': 'tests/e.py',
                     'test_name': 'test_e'}]},
        HERE, 'a' * 40, False, 'dev', {'spec': 's', 'code': 'c', 'tests': 't'})
    assert two['rules'] == {'RULE-4': 'failed'}
    assert [(e['id'], e['rule'], e['result'], e['test'])
            for e in two['proofs']] == [
        ('RULE-4', 'RULE-4', 'pass', 'tests/d.py::test_d'),
        ('RULE-4', 'RULE-4', 'fail', 'tests/e.py::test_e')]


# ---------------------------------------------------------------------------
# The merge
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-4
def test_a_run_replaces_only_its_own_section(tmp_path):
    root = tmp_path
    audit = {'mutation': None, 'rules': {'RULE-1': {
        'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
        'verdict': 'strong', 'findings': ['The test reads “4”.'],
        'at': 'x', 'commit': 'y'}}}
    windows = _section(at='2026-08-01T00:00:00Z')
    path = _put(root, _file(platforms={'windows': windows}, audit=audit))
    before = path.read_text(encoding='utf-8')

    def unchanged_text():
        # Each part's text as the file held it, compared as text.
        text = path.read_text(encoding='utf-8')
        for key, value, indent in (('windows', windows, '    '),
                                   ('audit', audit, '  ')):
            part = '"%s": %s' % (key, json.dumps(
                value, indent=2, sort_keys=True).replace('\n', '\n' + indent))
            assert part in before, key
            assert part in text, (key, text)

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section())
    data = _evidence(root)
    assert data['platforms']['windows'] == windows
    assert data['audit'] == audit
    assert data['platforms']['linux'] == _section()
    unchanged_text()

    failed = _section(result='fail', at='2026-09-02T00:00:00Z')
    writer.write_section(str(root), 'local', 'feat', _info(), 'linux', failed)
    data = _evidence(root)
    assert data['platforms']['linux'] == failed
    assert data['platforms']['windows'] == windows
    assert data['audit'] == audit
    unchanged_text()


# purlin: evidence_writer PROOF-5
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

    # An audit's write alone drops the removed rule too.
    _put(root, _file(platforms={'windows': old},
                     audit={'mutation': None,
                            'rules': {'RULE-1': entry, 'RULE-9': entry}}))
    writer.write_audit(str(root), 'local', 'feat', _info(),
                       {'RULE-1': entry}, None, False)
    data = _evidence(root)
    assert sorted(data['platforms']) == ['windows']
    assert sorted(data['platforms']['windows']['rules']) == ['RULE-1']
    assert sorted(data['audit']['rules']) == ['RULE-1']


# purlin: evidence_writer PROOF-6
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


# purlin: evidence_writer PROOF-6
def test_a_feature_run_and_an_audit_run_remove_it_too(tmp_path):
    root = _project(tmp_path, gate='strong')
    _spec(root, level='strong')
    _test_file(root)
    live = _put(root, _file(source='ci', platforms={'linux': _section()}),
                source='ci')
    _repo(root)
    gone = root / '.purlin' / 'evidence' / 'local' / 'gone.json'

    for args in (('--feature', 'feat', '--test'), ('--all', '--audit')):
        _put(root, _file(feature='gone', platforms={'linux': _section()}),
             feature='gone')
        code, out = _run(root, *args)
        assert not gone.exists(), args
        assert ('Removed .purlin/evidence/local/gone.json: no spec defines '
                'gone.' in out), (args, out)
        assert live.exists(), args


# purlin: evidence_writer PROOF-7
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

    # What it saw changed, or the fingerprint did: the file is rewritten.
    failed = dict(held, at='2030-01-02T00:00:00Z', commit='e' * 40,
                  rules={'RULE-1': 'failed'},
                  proofs=[dict(held['proofs'][0], result='fail')])
    writer.write_section(str(root), 'local', 'feat', _info(), HERE, failed)
    assert path.read_bytes() != first
    assert _evidence(root)['platforms'][HERE] == failed
    moved = dict(failed, at='2030-01-03T00:00:00Z', commit='d' * 40,
                 fingerprint=dict(held['fingerprint'], code='other'))
    writer.write_section(str(root), 'local', 'feat', _info(), HERE, moved)
    assert _evidence(root)['platforms'][HERE] == moved


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-8
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

    # An older ci section for two, and a newer feature three, not sorted first.
    _put(root, _file(source='ci', feature='two', platforms={
        'linux': _section(at='2026-09-01T12:00:00Z', commit='e' * 40)}),
         source='ci', feature='two')
    _put(root, _file(feature='three', platforms={
        'linux': _section(at='2026-09-04T00:00:00Z', commit='d' * 40)}),
         feature='three')
    writer.write_table(str(root))
    lines = (root / '.purlin' / 'tests.md').read_text(
        encoding='utf-8').splitlines()
    assert lines[0] == '# Tests at ddddddd'
    assert ('| two | 1 | 1 | 0 | 0 | bbbbbbb · 2026-09-02T00:00:00Z · macos '
            '· local |') in lines


# purlin: evidence_writer PROOF-8
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

# purlin: evidence_writer PROOF-9
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
    assert '?? .purlin/tests.md' in _git(root, 'status', '--porcelain',
                                         '--untracked-files=all')


# purlin: evidence_writer PROOF-9
def test_an_audit_run_writes_and_does_not_commit(tmp_path):
    root = _project(tmp_path, gate='strong')
    _spec(root, level='strong')
    _test_file(root)
    _repo(root)
    head = _git(root, 'rev-parse', 'HEAD').strip()

    _code, out = _run(root, '--all', '--audit')

    assert 'Evidence written to .purlin/evidence/local/feat.json.' in out
    assert _git(root, 'rev-parse', 'HEAD').strip() == head
    listed = _git(root, 'status', '--porcelain', '--untracked-files=all')
    assert '?? .purlin/evidence/local/feat.json' in listed, listed
    assert '?? .purlin/tests.md' in listed, listed


# purlin: evidence_writer PROOF-9
def test_several_features_name_the_folder(tmp_path):
    root = _project(tmp_path)
    _spec(root, 'one')
    _spec(root, 'two')
    _test_file(root, 'test_one.py', 'one')
    _test_file(root, 'test_two.py', 'two')
    _repo(root)

    _code, out = _run(root, '--all', '--test')

    assert 'Evidence written to .purlin/evidence/local/ for 2 features.' in out


# purlin: evidence_writer PROOF-10
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

    assert _git(root, 'log', '-1', '--format=%an').strip() == 'Dev'

    code, out = _run(root, '--all', '--test', '--commit')
    assert 'Evidence unchanged.' in out, out
    assert len(_git(root, 'log', '--format=%s').splitlines()) == 2


# purlin: evidence_writer PROOF-10
def test_commit_carries_the_removal_and_pushes_nothing(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    for source in ('local', 'ci'):
        _put(root, _file(source=source, feature='gone',
                         platforms={'linux': _section()}),
             source=source, feature='gone')
    _repo(root)
    remote = tmp_path / 'remote.git'
    _git(tmp_path, 'init', '--bare', '-q', str(remote))
    _git(root, 'remote', 'add', 'origin', str(remote))
    _git(root, 'push', '-q', 'origin', 'main')
    pushed = _git(remote, 'rev-parse', 'main').strip()

    code, out = _run(root, '--all', '--test', '--commit')

    assert code == 0, out
    assert 'Evidence committed.' in out
    changed = _git(root, 'show', '--no-renames', '--name-status', '--format=',
                   'HEAD').splitlines()
    assert 'D\t.purlin/evidence/local/gone.json' in changed, changed
    assert 'D\t.purlin/evidence/ci/gone.json' in changed, changed
    assert _git(root, 'rev-parse', 'HEAD').strip() != pushed
    assert _git(remote, 'rev-parse', 'main').strip() == pushed


# purlin: evidence_writer PROOF-11
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


# purlin: evidence_writer PROOF-12
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

    # RULE-2 read again: its entry is replaced, RULE-1's kept.
    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-2': _entry('strong')}, None, False)
    assert _evidence(root)['audit']['rules'] == {'RULE-1': _entry(),
                                                 'RULE-2': _entry('strong')}

    writer.write_audit(str(root), 'local', 'feat', info, {},
                       {'engine': 'mutmut', 'score': 5, 'at': 'b',
                        'commit': 'd'}, False)
    assert _evidence(root)['audit']['mutation'] == first

    _put(root, _file(feature='fresh'), feature='fresh')
    writer.write_audit(str(root), 'local', 'fresh', info,
                       {'RULE-1': _entry()}, None, False)
    assert _evidence(root, 'fresh')['audit']['mutation'] is None


# purlin: evidence_writer PROOF-12
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
    assert entry['model'] == 'claude-fake-1'
    with open(os.path.join(REPO, 'references', 'review_criteria.md'),
              encoding='utf-8') as handle:
        assert entry['criteria'] == hashlib.sha256(
            handle.read().encode('utf-8')).hexdigest()
    assert STAMP.match(entry['at'])
    assert entry['commit'] == _git(root, 'rev-parse', 'HEAD').strip()
    assert rule['cells']['strong']['evidence'] == \
        '.purlin/evidence/local/feat.json'


# purlin: evidence_writer PROOF-14
def test_a_repeated_entry_keeps_its_time_and_a_new_model_replaces_it(tmp_path):
    root = tmp_path
    info = _info(rules=('RULE-1',))
    _put(root, _file(platforms={'linux': _section()}))
    found = {'verdict': 'strong', 'findings': [], 'model': 'claude-a',
             'criteria': 'c' * 64}
    rule = {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't'}
    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': writer.audit_entry(rule, found, 'y',
                                                     at='x')}, None, False)
    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': writer.audit_entry(rule, found, 'y',
                                                     at='later')}, None, False)
    assert _evidence(root)['audit']['rules']['RULE-1']['at'] == 'x'
    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': writer.audit_entry(
                           rule, dict(found, model='claude-b'), 'y',
                           at='later')}, None, False)
    entry = _evidence(root)['audit']['rules']['RULE-1']
    assert (entry['model'], entry['at']) == ('claude-b', 'later'), entry

    # A repeat under another commit keeps the commit too.
    found = dict(found, model='claude-b')
    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': writer.audit_entry(rule, found, 'z',
                                                     at='latest')}, None, False)
    entry = _evidence(root)['audit']['rules']['RULE-1']
    assert (entry['at'], entry['commit']) == ('later', 'y'), entry

    # One difference, in any of the six other fields, replaces the entry.
    for key, value in (('rule_hash', 'r2'), ('proof_hash', 'p2'),
                       ('test_hash', 't2'), ('verdict', 'weak'),
                       ('findings', ['The test checks nothing.']),
                       ('criteria', 'd' * 64)):
        if key.endswith('_hash'):
            rule = dict(rule, **{key: value})
        else:
            found = dict(found, **{key: value})
        writer.write_audit(str(root), 'local', 'feat', info,
                           {'RULE-1': writer.audit_entry(rule, found, key,
                                                         at=key)}, None, False)
        entry = _evidence(root)['audit']['rules']['RULE-1']
        assert (entry[key], entry['at'], entry['commit']) == (
            value, key, key), entry


# purlin: evidence_writer PROOF-13
def test_neither_the_evidence_nor_the_table_is_ignored():
    for rel in ('templates/gitignore.purlin', '.gitignore'):
        with open(os.path.join(REPO, rel), encoding='utf-8') as handle:
            patterns = [line.strip() for line in handle
                        if line.strip() and not line.startswith('#')]
        for pattern in patterns:
            assert '.purlin/evidence' not in pattern, (rel, pattern)
            assert 'tests.md' not in pattern, (rel, pattern)


# purlin: evidence_writer PROOF-13
def test_git_ignores_neither_file_after_init(tmp_path):
    root = tmp_path / 'fresh'
    root.mkdir()
    _git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    done = subprocess.run(
        [sys.executable, os.path.join(REPO, 'scripts', 'init', 'scaffold.py'),
         '--project-root', str(root), '--yes', '--gate', 'passed'],
        capture_output=True, encoding='utf-8', env=env,
        stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert '.purlin/runtime/' in (root / '.gitignore').read_text(
        encoding='utf-8')
    for rel in ('.purlin/evidence/local/feat.json', '.purlin/tests.md',
                '.purlin/runtime/run.log'):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text('{}\n', encoding='utf-8')
    asked = subprocess.run(
        ['git', 'check-ignore', '.purlin/evidence/local/feat.json',
         '.purlin/tests.md', '.purlin/runtime/run.log'],
        cwd=str(root), capture_output=True, encoding='utf-8')
    assert asked.stdout.splitlines() == ['.purlin/runtime/run.log'], asked
