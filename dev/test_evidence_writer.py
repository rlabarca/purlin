"""Tests for `scripts/run/evidence.py`, the evidence writer, and the run's use of it.

The pure parts, a section, the merge, the table and the two commits, are
called directly. The run-level parts build a throwaway project under
`tmp_path` and drive the real run script against it.
"""

import hashlib
import json
import os
import platform
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
PRINT = {'spec': 's', 'code': 'c', 'tests': 't'}
WORK = ['specs/a/feat.md', 'tests/test_feat.py', '.purlin/config.json']


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
          description='A feature.'):
    folder = root / 'specs' / 'a'
    folder.mkdir(parents=True, exist_ok=True)
    lines = ['# Feature: %s' % name, '',
             '> Description: %s' % description,
             '> Scope: src/feat.py',
             '> Stack: python', '', '## Rules', '']
    for index in range(1, rules + 1):
        lines.append('- RULE-%d: The thing works, case %d' % (index, index))
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


def _head(root):
    return _git(root, 'rev-parse', 'HEAD').strip()


def _subjects(root):
    return _git(root, 'log', '--format=%s').splitlines()


def _run(root, *args):
    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root)] + list(args),
        capture_output=True, encoding='utf-8', cwd=str(root))
    return result.returncode, result.stdout + result.stderr


def _evidence(root, feature='feat', source='local'):
    path = root / '.purlin' / 'evidence' / source / ('%s.json' % feature)
    return json.loads(path.read_text(encoding='utf-8'))


def _section(result='pass', at='2026-09-01T00:00:00Z', commit='a' * 40,
             rules=None, machine='build-1', hostname='build-1'):
    return {'commit': commit, 'dirty': False, 'at': at, 'runner': 'dev',
            'machine': machine, 'hostname': hostname,
            'fingerprint': dict(PRINT),
            'rules': rules or {'RULE-1': 'passed' if result == 'pass'
                               else 'failed'},
            'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'result': result,
                        'env': None, 'manual': False,
                        'test': 'tests/test_feat.py::test_ok'}]}


def _file(source='local', platforms=None, audit=None, feature='feat'):
    data = {'schema': reader.SCHEMA, 'feature': feature,
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


def _seen(status, name='test_a', path='tests/a.py'):
    """What a run tied to a marker: one test and how it ended."""
    return {'status': status, 'test_file': path, 'test_name': name}


def _build(proofs, seen, **extra):
    """The section a run writes for one rule, `RULE-1`, with these proofs."""
    info = _info(proofs=proofs, by_rule={'RULE-1': sorted(proofs)})
    return writer.build_section(info, seen, HERE, 'a' * 40, False, 'dev',
                                PRINT, **extra)


def _rule_word(proofs, seen):
    return _build(proofs, seen)['rules']['RULE-1']


def _listed(proofs, seen, proof_id='PROOF-1'):
    return [entry for entry in _build(proofs, seen)['proofs']
            if entry['id'] == proof_id]


PLAIN = {'manual': False, 'env': None}


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
    assert (data['schema'], data['feature'], data['source'],
            data['spec']) == ('purlin-evidence/2', 'feat', 'local',
                              'specs/a/feat.md')
    assert list(data['platforms']) == [HERE]
    assert sorted(data['platforms'][HERE]) == [
        'at', 'commit', 'dirty', 'fingerprint', 'hostname', 'machine',
        'proofs', 'rules', 'runner']


# purlin: evidence_writer PROOF-16
def test_the_section_names_the_commit_time_runner_and_fingerprint(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    section = _evidence(root)['platforms'][HERE]
    assert section['commit'] == _head(root)
    assert len(section['commit']) == 40
    assert section['dirty'] is False
    assert STAMP.match(section['at'])
    assert section['runner'] == 'dev'
    assert section['fingerprint'] == fingerprint_module.fingerprint(
        str(root), 'feat')
    assert section['rules'] == {'RULE-1': 'passed'}


# purlin: evidence_writer PROOF-17
def test_a_changed_tree_is_dirty_and_the_runner_is_the_email_slug(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')
    _git(root, 'config', 'user.email', 'Jane.Doe+ci@Example.com')

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    section = _evidence(root)['platforms'][HERE]
    assert section['dirty'] is True
    assert section['runner'] == 'jane-doe-ci'


# purlin: evidence_writer PROOF-41
def test_a_run_names_the_machine_its_tests_ran_on(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    section = _evidence(root)['platforms'][HERE]
    assert platform.node()
    assert (section['machine'], section['hostname']) == (
        platform.node(), platform.node())


# purlin: evidence_writer PROOF-42
def test_a_host_with_no_name_is_the_machine_unknown(monkeypatch):
    monkeypatch.setattr(platform, 'node', lambda: '')
    section = _build({'PROOF-1': PLAIN}, {'PROOF-1': [_seen('pass')]})
    assert section['machine'] == 'unknown'


# ---------------------------------------------------------------------------
# The word a rule reads
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-2
def test_a_rule_whose_one_test_passed_reads_passed():
    assert _rule_word({'PROOF-1': PLAIN},
                      {'PROOF-1': [_seen('pass')]}) == 'passed'


# purlin: evidence_writer PROOF-18
def test_a_rule_with_a_failing_proof_reads_failed():
    assert _rule_word({'PROOF-1': PLAIN, 'PROOF-2': PLAIN},
                      {'PROOF-1': [_seen('pass')],
                       'PROOF-2': [_seen('fail', 'test_b')]}) == 'failed'


# purlin: evidence_writer PROOF-19
def test_a_rule_waiting_on_another_system_reads_not_run():
    assert _rule_word({'PROOF-1': PLAIN,
                       'PROOF-2': {'manual': False, 'env': OTHER}},
                      {'PROOF-1': [_seen('pass')]}) == 'not run'


# purlin: evidence_writer PROOF-20
def test_a_rule_whose_proof_has_no_test_reads_no_test():
    assert _rule_word({'PROOF-1': PLAIN}, {}) == 'no test'


# purlin: evidence_writer PROOF-21
def test_a_rule_whose_one_proof_is_manual_reads_passed():
    assert _rule_word({'PROOF-1': {'manual': True, 'env': None}},
                      {}) == 'passed'


# purlin: evidence_writer PROOF-22
def test_a_proof_tagged_for_this_system_that_passed_reads_passed():
    assert _rule_word({'PROOF-1': {'manual': False, 'env': HERE}},
                      {'PROOF-1': [_seen('pass')]}) == 'passed'


# purlin: evidence_writer PROOF-23
def test_a_failure_outweighs_a_proof_owed_by_another_system():
    assert _rule_word({'PROOF-1': PLAIN,
                       'PROOF-2': {'manual': False, 'env': OTHER}},
                      {'PROOF-1': [_seen('fail')]}) == 'failed'


# purlin: evidence_writer PROOF-24
def test_a_manual_proof_does_not_hide_a_failure():
    assert _rule_word({'PROOF-1': {'manual': True, 'env': None},
                       'PROOF-2': PLAIN},
                      {'PROOF-2': [_seen('fail')]}) == 'failed'


# purlin: evidence_writer PROOF-25
def test_a_rule_with_a_skipped_test_beside_a_passing_one_reads_not_run():
    assert _rule_word({'PROOF-1': PLAIN},
                      {'PROOF-1': [_seen('pass'),
                                   _seen('not run', 'test_b')]}) == 'not run'


# purlin: evidence_writer PROOF-26
def test_a_rule_whose_one_test_was_skipped_reads_not_run():
    assert _rule_word({'PROOF-1': PLAIN},
                      {'PROOF-1': [_seen('not run')]}) == 'not run'


# ---------------------------------------------------------------------------
# The proofs a section lists
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-3
def test_one_proof_entry_per_proof_and_test():
    listed = _listed({'PROOF-1': PLAIN}, {'PROOF-1': [
        _seen('pass', 'test_a', 'tests/a.py'),
        _seen('fail', 'test_b', 'tests/b.py')]})
    assert [(entry['result'], entry['test']) for entry in listed] == [
        ('pass', 'tests/a.py::test_a'), ('fail', 'tests/b.py::test_b')]
    for entry in listed:
        assert sorted(entry) == ['env', 'id', 'manual', 'result', 'rule',
                                 'test']


# purlin: evidence_writer PROOF-27
def test_a_proof_with_no_test_is_listed_missing():
    listed = _listed({'PROOF-1': PLAIN}, {})
    assert [(entry['result'], entry['test']) for entry in listed] == [
        ('missing', '')]


# purlin: evidence_writer PROOF-28
def test_a_proof_owed_by_another_system_with_no_test_is_not_run():
    listed = _listed({'PROOF-1': {'manual': False, 'env': OTHER}}, {})
    assert [(entry['result'], entry['env'], entry['test'])
            for entry in listed] == [('not run', OTHER, '')]


# purlin: evidence_writer PROOF-29
def test_a_skipped_test_of_a_proof_owed_by_another_system_is_not_run():
    listed = _listed({'PROOF-1': {'manual': False, 'env': OTHER}},
                     {'PROOF-1': [_seen('not run', 'test_w', 'tests/w.py')]})
    assert [(entry['result'], entry['test']) for entry in listed] == [
        ('not run', 'tests/w.py::test_w')]


# purlin: evidence_writer PROOF-30
def test_a_skipped_test_of_a_proof_owed_here_is_missing():
    listed = _listed({'PROOF-1': PLAIN},
                     {'PROOF-1': [_seen('not run', 'test_s', 'tests/s.py')]})
    assert [(entry['result'], entry['test']) for entry in listed] == [
        ('missing', 'tests/s.py::test_s')]


# purlin: evidence_writer PROOF-31
def test_a_manual_proof_is_listed_missing_and_manual():
    listed = _listed({'PROOF-1': {'manual': True, 'env': None}}, {})
    assert [(entry['result'], entry['manual'], entry['test'])
            for entry in listed] == [('missing', True, '')]


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
                                   PRINT)
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
        HERE, 'a' * 40, False, 'dev', PRINT)
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
    _spec(root)
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


# purlin: evidence_writer PROOF-43
def test_a_section_from_another_machine_replaces_the_one_on_disk(tmp_path):
    root = tmp_path
    _put(root, _file(platforms={'linux': _section(machine='build-1')}))

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section(machine='build-2',
                                  at='2026-09-02T00:00:00Z'))

    assert _evidence(root)['platforms']['linux']['machine'] == 'build-2'


# purlin: evidence_writer PROOF-44
def test_a_section_that_differs_only_in_its_hostname_is_not_written(tmp_path):
    root = tmp_path
    path = _put(root, _file(platforms={
        'linux': _section(hostname='fv-az123')}))
    before = path.read_bytes()

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section(hostname='fv-az456'))

    assert path.read_bytes() == before


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

def _table_lines(root):
    writer.write_table(str(root))
    return (root / '.purlin' / 'tests.md').read_text(
        encoding='utf-8').splitlines()


# purlin: evidence_writer PROOF-8
def test_a_row_counts_the_features_newest_section(tmp_path):
    root = tmp_path
    three = _section(at='2026-09-03T00:00:00Z', commit='c' * 40,
                     rules={'RULE-1': 'passed', 'RULE-2': 'failed',
                            'RULE-3': 'not run'})
    _put(root, _file(source='ci', feature='one', platforms={'linux': three}),
         source='ci', feature='one')
    _put(root, _file(feature='one', platforms={
        'macos': _section(at='2026-09-01T00:00:00Z')}), feature='one')

    assert ('| one | 3 | 1 | 1 | 1 | ccccccc · 2026-09-03T00:00:00Z · '
            'Linux/Unix · ci |') in _table_lines(root)


# purlin: evidence_writer PROOF-32
def test_the_table_opens_on_the_newest_commit_and_its_columns(tmp_path):
    root = tmp_path
    _put(root, _file(feature='one', platforms={
        'macos': _section(at='2026-09-02T00:00:00Z', commit='b' * 40)}),
         feature='one')
    _put(root, _file(feature='two', platforms={
        'linux': _section(at='2026-09-04T00:00:00Z', commit='d' * 40)}),
         feature='two')

    lines = _table_lines(root)

    assert lines[0] == '# Tests at ddddddd'
    assert lines[2] == ('| Feature | Rules | Passed | Failing | No test | '
                        'Last run |')


# purlin: evidence_writer PROOF-33
def test_an_older_section_in_the_other_source_does_not_answer(tmp_path):
    root = tmp_path
    _put(root, _file(feature='two', platforms={
        'macos': _section(at='2026-09-02T00:00:00Z', commit='b' * 40)}),
         feature='two')
    _put(root, _file(source='ci', feature='two', platforms={
        'linux': _section(at='2026-09-01T12:00:00Z', commit='e' * 40)}),
         source='ci', feature='two')

    assert ('| two | 1 | 1 | 0 | 0 | bbbbbbb · 2026-09-02T00:00:00Z · macOS '
            '· local |') in _table_lines(root)


# purlin: evidence_writer PROOF-34
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


# purlin: evidence_writer PROOF-35
def test_a_rule_with_a_skipped_test_is_not_counted_passed(tmp_path):
    root = tmp_path
    section = _build({'PROOF-1': PLAIN},
                     {'PROOF-1': [_seen('pass'), _seen('not run', 'test_b')]})
    writer.write_section(str(root), 'local', 'feat', _info(), HERE, section)

    row = [line for line in _table_lines(root) if line.startswith('| feat ')]

    assert [cell.strip() for cell in row[0].split('|')[1:6]] == [
        'feat', '1', '0', '0', '1']


# ---------------------------------------------------------------------------
# Written, and committed when asked
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-9
def test_a_run_writes_and_does_not_commit(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    head = _head(root)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert 'Evidence written to .purlin/evidence/local/feat.json.' in out
    assert _head(root) == head
    assert '.purlin/evidence/' in _git(root, 'status', '--porcelain',
                                       '--untracked-files=all')
    assert '?? .purlin/tests.md' in _git(root, 'status', '--porcelain',
                                         '--untracked-files=all')


# purlin: evidence_writer PROOF-37
def test_an_audit_run_writes_and_does_not_commit(tmp_path):
    root = _project(tmp_path, gate='strong')
    _spec(root)
    _test_file(root)
    _repo(root)
    head = _head(root)

    _code, out = _run(root, '--all', '--audit')

    assert 'Evidence written to .purlin/evidence/local/feat.json.' in out
    assert _head(root) == head
    listed = _git(root, 'status', '--porcelain', '--untracked-files=all')
    assert '?? .purlin/evidence/local/feat.json' in listed, listed
    assert '?? .purlin/tests.md' in listed, listed


# purlin: evidence_writer PROOF-36
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
    head = _head(root)

    code, out = _run(root, '--all', '--test', '--commit')

    assert code == 0, out
    assert 'Evidence committed.' in out
    assert 'git push' not in out
    assert _subjects(root)[0] == 'purlin: evidence at %s' % head[:7]
    assert _git(root, 'log', '-1', '--format=%an %ae').strip() == \
        'Dev dev@example.com'
    touched = _git(root, 'show', '--name-only', '--format=', 'HEAD').split()
    assert sorted(touched) == ['.purlin/evidence/local/feat.json',
                               '.purlin/tests.md']


# purlin: evidence_writer PROOF-38
def test_a_second_commit_run_with_nothing_new_commits_nothing(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    _run(root, '--all', '--test', '--commit')
    commits = len(_subjects(root))

    code, out = _run(root, '--all', '--test', '--commit')

    assert code == 0, out
    assert 'Evidence unchanged.' in out, out
    assert len(_subjects(root)) == commits


# purlin: evidence_writer PROOF-39
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
    assert _head(root) != pushed
    assert _git(remote, 'rev-parse', 'main').strip() == pushed


def _edited(root):
    """A checkout whose spec and test file changed after its last commit."""
    _spec(root, description='A feature, reworded.')
    (root / 'tests' / 'test_feat.py').write_text(
        'import pytest\n\n'
        '# purlin: feat PROOF-1\n'
        'def test_ok():\n'
        '    assert 2 + 2 == 4\n', encoding='utf-8')


# purlin: evidence_writer PROOF-40
def test_the_results_commit_names_the_work_commit(tmp_path, capsys):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    _spec(root, description='A feature, reworded.')
    _put(root, _file(platforms={HERE: _section()}))

    work = writer.commit_work(str(root), WORK)
    writer.commit_local(str(root), work)

    assert _subjects(root)[0] == 'purlin: evidence at %s' % work[:7]
    assert _git(root, 'rev-parse', 'HEAD^').strip() == work


# purlin: evidence_writer PROOF-47
def test_the_work_is_committed_first_and_each_file_named(tmp_path, capsys):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    _edited(root)
    capsys.readouterr()

    work = writer.commit_work(str(root), WORK)

    assert work == _head(root)
    assert _subjects(root)[0] == 'purlin: specs, tests and settings for feat'
    assert sorted(_git(root, 'show', '--name-only', '--format=',
                       'HEAD').split()) == ['specs/a/feat.md',
                                            'tests/test_feat.py']
    assert capsys.readouterr().out.splitlines() == [
        'Committed %s, the work these results describe:' % work[:7],
        '  specs/a/feat.md', '  tests/test_feat.py']


# purlin: evidence_writer PROOF-48
def test_the_work_commit_names_every_feature_run(tmp_path, capsys):
    root = _project(tmp_path)
    _spec(root, 'one')
    _spec(root, 'two')
    _repo(root)
    _spec(root, 'one', description='One, reworded.')
    _spec(root, 'two', description='Two, reworded.')

    writer.commit_work(str(root), ['specs/a/one.md', 'specs/a/two.md',
                                   '.purlin/config.json'])

    assert _subjects(root)[0] == \
        'purlin: specs, tests and settings for one, two'


# purlin: evidence_writer PROOF-49
def test_committed_work_makes_no_commit_and_the_results_name_head(
        tmp_path, capsys):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    head = _head(root)
    _put(root, _file(platforms={HERE: _section()}))
    capsys.readouterr()

    work = writer.commit_work(str(root), WORK)

    assert work == head
    assert capsys.readouterr().out == ''
    assert _head(root) == head
    writer.commit_local(str(root), work)
    assert _subjects(root)[0] == 'purlin: evidence at %s' % head[:7]


# purlin: evidence_writer PROOF-50
def test_a_commit_run_makes_the_two_commits(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    _spec(root, description='A feature, reworded.')

    code, out = _run(root, '--all', '--test', '--commit')

    assert code == 0, out
    work = _git(root, 'rev-parse', 'HEAD^').strip()
    assert _subjects(root)[:2] == [
        'purlin: evidence at %s' % work[:7],
        'purlin: specs, tests and settings for feat']
    lines = out.splitlines()
    at = lines.index('Committed %s, the work these results describe:'
                     % work[:7])
    assert lines[at + 1] == '  specs/a/feat.md'


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


FIRST_MUTATION = {'engine': 'mutmut', 'score': 71, 'at': 'a', 'commit': 'c'}


# purlin: evidence_writer PROOF-12
def test_an_audit_adds_the_entry_it_read_and_keeps_the_others(tmp_path):
    root = tmp_path
    info = _info(rules=('RULE-1', 'RULE-2'))
    earlier = _entry('weak')
    _put(root, _file(platforms={'linux': _section()},
                     audit={'mutation': None, 'rules': {'RULE-2': earlier}}))

    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': _entry()}, FIRST_MUTATION, True)

    audit = _evidence(root)['audit']
    assert audit['rules'] == {'RULE-1': _entry(), 'RULE-2': earlier}
    assert (audit['mutation']['engine'], audit['mutation']['score']) == (
        'mutmut', 71)


# purlin: evidence_writer PROOF-51
def test_an_audit_replaces_the_entry_it_read_again(tmp_path):
    root = tmp_path
    info = _info(rules=('RULE-1', 'RULE-2'))
    _put(root, _file(platforms={'linux': _section()},
                     audit={'mutation': None,
                            'rules': {'RULE-1': _entry(),
                                      'RULE-2': _entry('weak')}}))

    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-2': _entry('strong')}, None, False)

    assert _evidence(root)['audit']['rules'] == {'RULE-1': _entry(),
                                                 'RULE-2': _entry('strong')}


# purlin: evidence_writer PROOF-52
def test_an_audit_without_mutation_testing_keeps_the_score(tmp_path):
    root = tmp_path
    _put(root, _file(platforms={'linux': _section()},
                     audit={'mutation': FIRST_MUTATION, 'rules': {}}))

    writer.write_audit(str(root), 'local', 'feat', _info(), {},
                       {'engine': 'mutmut', 'score': 5, 'at': 'b',
                        'commit': 'd'}, False)

    assert _evidence(root)['audit']['mutation']['score'] == 71


# purlin: evidence_writer PROOF-53
def test_a_first_audit_without_mutation_testing_writes_null(tmp_path):
    root = tmp_path
    _put(root, _file(platforms={'linux': _section()}))

    writer.write_audit(str(root), 'local', 'feat', _info(),
                       {'RULE-1': _entry()}, None, False)

    assert _evidence(root)['audit']['mutation'] is None


# purlin: evidence_writer PROOF-54
def test_an_audit_run_writes_the_entry_for_the_rule_it_read(tmp_path):
    root = _project(tmp_path, gate='strong')
    _spec(root)
    _test_file(root)
    _repo(root)

    _code, out = _run(root, '--all', '--audit')

    entry = _evidence(root)['audit']['rules']['RULE-1']
    data = payload_module.build_payload(str(root))
    rule = next(r for f in data['features'] for r in f['rules']
                if r['id'] == 'RULE-1')
    assert (entry['rule_hash'], entry['proof_hash'], entry['test_hash']) == (
        rule['rule_hash'], rule['proof_hash'], rule['test_hash']), out
    assert entry['verdict'] == 'strong'
    assert entry['findings'] == []
    assert entry['model'] == 'claude-fake-1'
    with open(os.path.join(REPO, 'references', 'review_criteria.md'),
              encoding='utf-8') as handle:
        assert entry['criteria'] == hashlib.sha256(
            handle.read().encode('utf-8')).hexdigest()
    assert STAMP.match(entry['at'])
    assert entry['commit'] == _head(root)


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


HASHES = {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't'}


# purlin: evidence_writer PROOF-45
def test_an_audit_entry_carries_the_notes_the_audit_gave(tmp_path):
    root = tmp_path
    _put(root, _file(platforms={'linux': _section()}))
    found = {'verdict': 'strong', 'findings': [], 'model': 'claude-a',
             'criteria': 'c' * 64, 'notes': ['PROOF-1 holds two cases.']}

    writer.write_audit(str(root), 'local', 'feat', _info(),
                       {'RULE-1': writer.audit_entry(HASHES, found, 'y')},
                       None, False)

    assert _evidence(root)['audit']['rules']['RULE-1']['notes'] == [
        'PROOF-1 holds two cases.']


# purlin: evidence_writer PROOF-46
def test_an_audit_entry_with_no_notes_has_no_notes_field(tmp_path):
    root = tmp_path
    _put(root, _file(platforms={'linux': _section()}))
    found = {'verdict': 'strong', 'findings': [], 'model': 'claude-a',
             'criteria': 'c' * 64}

    writer.write_audit(str(root), 'local', 'feat', _info(),
                       {'RULE-1': writer.audit_entry(HASHES, found, 'y')},
                       None, False)

    assert 'notes' not in _evidence(root)['audit']['rules']['RULE-1']


# ---------------------------------------------------------------------------
# What is ignored
# ---------------------------------------------------------------------------

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
