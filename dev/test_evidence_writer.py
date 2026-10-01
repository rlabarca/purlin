"""Tests for `scripts/run/evidence.py`, the evidence writer, and the run's use of it.

The pure parts, a section, the merge and the two commits, are called
directly. The run-level parts build a throwaway project under
`tmp_path` and drive the real run script against it.
"""

import hashlib
import json
import os
import platform
import re
import subprocess
import sys

import shutil
import time

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
import fake_claude                                            # noqa: E402
import suites                                                 # noqa: E402

STAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
with open(os.path.join(REPO, 'VERSION'), encoding='utf-8') as _handle:
    VERSION = _handle.read().strip()
HERE = reader.host_os()
OTHER = 'windows' if HERE != 'windows' else 'linux'
PRINT = {'spec': 's', 'code': 'c', 'tests': 't'}
WORK = ['specs/a/feat.md', 'tests/test_feat.py', '.purlin/config.json']


# ---------------------------------------------------------------------------
# A throwaway project
# ---------------------------------------------------------------------------

def _project(tmp_path, name='project'):
    root = tmp_path / name
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'version': VERSION, 'tests': [suites.pytest_suite()]})
        + '\n', encoding='utf-8')
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 2\n', encoding='utf-8')
    # As bytes, so git reads the same two patterns on every system.
    (root / '.gitignore').write_bytes(b'.purlin/runtime/\n__pycache__/\n')
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
             rules=None, machine='build-1'):
    """A section as a run writes it, under either source."""
    return {'commit': commit, 'dirty': False, 'at': at, 'runner': 'dev',
            'email': 'dev@example.com',
            'machine': machine, 'fingerprint': dict(PRINT),
            'rules': rules or {'RULE-1': 'passed' if result == 'pass'
                               else 'failed'},
            'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1',
                        'result': result, 'env': None, 'manual': False,
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
    # As bytes: a file written as text on Windows would end each line in
    # `\r\n`, and the comparisons of bytes below would start from that.
    path.write_bytes(writer.dump(data).encode('utf-8'))
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
        'at', 'commit', 'dirty', 'email', 'fingerprint', 'machine', 'proofs',
        'rules', 'runner']


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


# purlin: evidence_writer PROOF-90
def test_a_local_section_names_the_git_email(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    _git(root, 'config', 'user.email', 'dana.dev@labconnect.example')

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    section = _evidence(root)['platforms'][HERE]
    assert section['email'] == 'dana.dev@labconnect.example'


# purlin: evidence_writer PROOF-17
def test_a_changed_tree_is_dirty(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    (root / 'src' / 'feat.py').write_text('VALUE = 3\n', encoding='utf-8')

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert _evidence(root)['platforms'][HERE]['dirty'] is True


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
    assert section['machine'] == platform.node()


TAGGED_HERE = (('PROOF-1', 'RULE-1', ' @env(%s)' % HERE),)


def _runner_checkout(tmp_path):
    """A git checkout whose git name is `Runner` and email
    `runner@example.com`, holding `feat`, its one proof tagged for this
    machine's system, its passing marked test and a `README.md`."""
    root = _project(tmp_path)
    _spec(root, proofs=TAGGED_HERE)
    _test_file(root)
    (root / 'README.md').write_text('A project.\n', encoding='utf-8')
    _repo(root)
    _git(root, 'config', 'user.email', 'runner@example.com')
    _git(root, 'config', 'user.name', 'Runner')
    return root


# purlin: evidence_writer PROOF-78
def test_a_ci_section_holds_the_fields_a_local_one_does(tmp_path):
    root = _runner_checkout(tmp_path)

    code, out = _run(root, '--all', '--ci')

    assert code == 0, out
    section = _evidence(root, source='ci')['platforms'][HERE]
    assert sorted(section) == [
        'at', 'commit', 'dirty', 'email', 'fingerprint', 'machine', 'proofs',
        'rules', 'runner']
    assert platform.node()
    assert section['machine'] == platform.node()
    assert section['email'] == 'runner@example.com'


# ---------------------------------------------------------------------------
# The word a rule reads
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-18
def test_a_rule_with_a_failing_proof_reads_failed():
    assert _rule_word({'PROOF-1': PLAIN, 'PROOF-2': PLAIN},
                      {'PROOF-1': [_seen('pass')],
                       'PROOF-2': [_seen('fail', 'test_b')]}) == 'failed'


# purlin: evidence_writer PROOF-77
def test_a_rule_with_one_proof_tested_and_one_not_reads_no_test():
    assert _rule_word({'PROOF-1': PLAIN, 'PROOF-2': PLAIN},
                      {'PROOF-1': [_seen('pass')]}) == 'no test'


# purlin: evidence_writer PROOF-21
def test_a_rule_whose_one_proof_is_manual_reads_passed():
    assert _rule_word({'PROOF-1': {'manual': True, 'env': None}},
                      {}) == 'passed'


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


# purlin: evidence_writer PROOF-29
def test_a_skipped_test_of_a_proof_owed_by_another_system_is_not_run():
    listed = _listed({'PROOF-1': {'manual': False, 'env': OTHER}},
                     {'PROOF-1': [_seen('not run', 'test_w', 'tests/w.py')]})
    assert [(entry['result'], entry['test']) for entry in listed] == [
        ('not run', 'tests/w.py::test_w')]


def _no_proof(rule_id, seen):
    """The section for a spec whose one rule has no proof, and what it lists."""
    section = writer.build_section(
        _info(rules=(rule_id,), proofs={}, by_rule={}), seen, HERE, 'a' * 40,
        False, 'dev', PRINT)
    return section['rules'], [(e['id'], e['rule'], e['result'], e['test'])
                              for e in section['proofs']]


# purlin: evidence_writer PROOF-15
def test_a_rule_with_no_proof_and_a_passing_marked_test_reads_passed():
    assert _no_proof('RULE-1', {'RULE-1': [_seen('pass')]}) == (
        {'RULE-1': 'passed'},
        [('RULE-1', 'RULE-1', 'pass', 'tests/a.py::test_a')])


# purlin: evidence_writer PROOF-72
def test_a_rule_with_no_proof_and_no_marked_test_reads_no_test():
    assert _no_proof('RULE-3', {}) == ({'RULE-3': 'no test'}, [])


NO_SCREENS = 'nothing to check: this project has no screens'


def _skipping_with(root, feature, folder):
    """A spec `feature` under `specs/<folder>/`, one rule and one proof,
    whose one marked test skips with the reason `NO_SCREENS`."""
    spec = root / 'specs' / folder / ('%s.md' % feature)
    spec.parent.mkdir(parents=True, exist_ok=True)
    scope = '' if folder == '_anchors' else '> Scope: src/feat.py\n'
    spec.write_text(
        '# Feature: %s\n\n> Description: Screens.\n%s\n## Rules\n\n'
        '- RULE-1: For every screen in the project, its title is set\n\n'
        '## Proof\n\n'
        '- PROOF-1 (RULE-1): Every screen the project holds has a title\n'
        % (feature, scope), encoding='utf-8')
    (root / 'tests' / ('test_%s.py' % feature)).write_text(
        'import pytest\n\n'
        '# purlin: %s PROOF-1\n'
        'def test_every_screen_has_a_title():\n'
        '    pytest.skip(%r)\n' % (feature, NO_SCREENS), encoding='utf-8')


# purlin: evidence_writer PROOF-93
def test_an_anchor_with_nothing_to_check_reads_passed(tmp_path):
    root = _project(tmp_path)
    _skipping_with(root, 'shared', '_anchors')
    _repo(root)

    code, out = _run(root, '--all', '--test')

    section = _evidence(root, 'shared')['platforms'][HERE]
    assert [(entry['id'], entry['result'], entry.get('reason'))
            for entry in section['proofs']] == [
        ('PROOF-1', 'nothing to check', 'this project has no screens')], out
    assert section['rules'] == {'RULE-1': 'passed'}


# purlin: evidence_writer PROOF-94
def test_a_feature_with_nothing_to_check_keeps_the_reason_and_reads_not_run(
        tmp_path):
    root = _project(tmp_path)
    _skipping_with(root, 'feat', 'a')
    _repo(root)

    code, out = _run(root, '--all', '--test')

    section = _evidence(root)['platforms'][HERE]
    assert [(entry['id'], entry.get('reason'))
            for entry in section['proofs']] == [
        ('PROOF-1', 'this project has no screens')], out
    assert section['rules'] == {'RULE-1': 'not run'}


# ---------------------------------------------------------------------------
# The merge
# ---------------------------------------------------------------------------

QUOTED_AUDIT = {'rules': {'RULE-1': {
    'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
    'verdict': 'strong', 'findings': ['The test reads “4”.'],
    'at': 'x', 'commit': 'y'}}}
WINDOWS = _section(at='2026-08-01T00:00:00Z')


def _kept_as_bytes(before, path, held='windows'):
    """The `held` section and the `audit` object as the file held them.

    Each part is compared in the file's bytes, so a write that re-encodes
    the curly quotes of the finding, or ends its lines in `\\r\\n`, while
    the parsed content stays equal, is seen.
    """
    text = path.read_bytes().decode('utf-8')
    for key, value, indent in ((held, WINDOWS, '    '),
                               ('audit', QUOTED_AUDIT, '  ')):
        part = '"%s": %s' % (key, json.dumps(
            value, indent=2, sort_keys=True).replace('\n', '\n' + indent))
        assert part in before, key
        assert part in text, (key, text)


# purlin: evidence_writer PROOF-55
def test_a_run_replaces_its_own_section_and_no_other(tmp_path):
    root = tmp_path
    path = _put(root, _file(platforms={'windows': WINDOWS,
                                       'linux': _section()},
                            audit=QUOTED_AUDIT))
    before = path.read_bytes().decode('utf-8')
    failed = _section(result='fail', at='2026-09-02T00:00:00Z')

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux', failed)

    assert _evidence(root)['platforms']['linux'] == failed
    _kept_as_bytes(before, path)


DROPPED_ENTRY = {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
                 'verdict': 'strong', 'findings': [], 'at': 'x',
                 'commit': 'y'}


def _with_a_dropped_rule(root):
    """A file whose `windows` section and `audit.rules` hold RULE-1 and RULE-9."""
    _put(root, _file(
        platforms={'windows': _section(rules={'RULE-1': 'passed',
                                              'RULE-9': 'passed'})},
        audit={'rules': {'RULE-1': DROPPED_ENTRY, 'RULE-9': DROPPED_ENTRY}}))


# purlin: evidence_writer PROOF-5
def test_a_section_write_drops_the_rules_the_spec_dropped(tmp_path):
    root = tmp_path
    _with_a_dropped_rule(root)

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section())

    data = _evidence(root)
    assert sorted(data['platforms']) == ['linux', 'windows']
    for section in data['platforms'].values():
        assert sorted(section['rules']) == ['RULE-1']
    assert sorted(data['audit']['rules']) == ['RULE-1']


# purlin: evidence_writer PROOF-6
def test_a_run_deletes_both_files_of_gone_writes_feat_and_names_each(tmp_path):
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


def _written_over(root, section):
    """Write `section` over a file holding `_section()`. The bytes before."""
    path = _put(root, _file(platforms={'linux': _section()}))
    before = path.read_bytes()
    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         section)
    return before, path.read_bytes()


# purlin: evidence_writer PROOF-60
def test_a_section_that_saw_a_failure_replaces_the_one_on_disk(tmp_path):
    failed = _section(result='fail', at='2030-01-02T00:00:00Z',
                      commit='e' * 40)

    _written_over(tmp_path, failed)

    held = _evidence(tmp_path)['platforms']['linux']
    assert (held['rules'], held['proofs'][0]['result'], held['at'],
            held['commit']) == ({'RULE-1': 'failed'}, 'fail',
                                '2030-01-02T00:00:00Z', 'e' * 40)


# purlin: evidence_writer PROOF-43
def test_a_section_from_another_machine_replaces_the_one_on_disk(tmp_path):
    root = tmp_path
    _put(root, _file(platforms={'linux': _section(machine='build-1')}))

    writer.write_section(str(root), 'local', 'feat', _info(), 'linux',
                         _section(machine='build-2',
                                  at='2026-09-02T00:00:00Z'))

    assert _evidence(root)['platforms']['linux']['machine'] == 'build-2'


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
    assert '?? .purlin/evidence/local/feat.json' in _git(
        root, 'status', '--porcelain', '--untracked-files=all')


# purlin: evidence_writer PROOF-10
def test_commit_commits_exactly_the_evidence_file_once(tmp_path):
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
    assert touched == ['.purlin/evidence/local/feat.json']


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


def _committed_run(tmp_path):
    """A checkout whose `--all --test --commit` run has just committed its
    evidence. The checkout and the commit that evidence describes."""
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    code, out = _run(root, '--all', '--test', '--commit')
    assert code == 0, out
    assert _subjects(root)[0].startswith('purlin: evidence at '), out
    return root, _git(root, 'rev-parse', 'HEAD^').strip()


# purlin: evidence_writer PROOF-91
def test_a_second_run_on_the_evidence_commit_leaves_the_file_as_committed(
        tmp_path):
    root, described = _committed_run(tmp_path)
    path = root / '.purlin' / 'evidence' / 'local' / 'feat.json'
    committed = _git(root, 'show', 'HEAD:.purlin/evidence/local/feat.json')
    assert json.loads(committed)['platforms'][HERE]['commit'] == described

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert path.read_bytes() == committed.encode('utf-8')
    assert _evidence(root)['platforms'][HERE]['commit'] == described


# purlin: evidence_writer PROOF-92
def test_a_run_after_a_commit_outside_the_records_writes_the_new_head(
        tmp_path):
    root, _described = _committed_run(tmp_path)
    before = _evidence(root)['platforms'][HERE]
    (root / 'README.md').write_text('A project.\n', encoding='utf-8')
    _git(root, 'add', 'README.md')
    _git(root, 'commit', '-q', '-m', 'docs: a readme')
    # `at` is written to the second: a run in the same second as the first
    # could not show a new one.
    time.sleep(1.1)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    section = _evidence(root)['platforms'][HERE]
    assert section['commit'] == _head(root)
    assert section['at'] != before['at']
    assert (section['rules'], section['proofs'], section['fingerprint']) == (
        before['rules'], before['proofs'], before['fingerprint'])


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


# purlin: evidence_writer PROOF-95
def test_a_ci_commit_run_commits_exactly_its_ci_file(tmp_path):
    root = _runner_checkout(tmp_path)
    (root / 'README.md').write_text('A project, edited.\n', encoding='utf-8')
    head = _head(root)

    code, out = _run(root, '--all', '--ci', '--commit')

    assert code == 0, out
    assert 'Evidence committed.' in out.splitlines(), out
    assert _subjects(root)[0] == 'purlin: evidence at %s' % head[:7]
    assert _git(root, 'log', '-1', '--format=%an').strip() == 'Runner'
    assert _git(root, 'rev-parse', 'HEAD^').strip() == head
    touched = _git(root, 'show', '--name-only', '--format=', 'HEAD').split()
    assert touched == ['.purlin/evidence/ci/feat.json']


# purlin: evidence_writer PROOF-96
def test_a_second_ci_commit_run_commits_nothing_and_pushes_nothing(tmp_path):
    root = _runner_checkout(tmp_path)
    remote = tmp_path / 'remote.git'
    _git(tmp_path, 'init', '--bare', '-q', str(remote))
    _git(root, 'remote', 'add', 'origin', str(remote))
    _git(root, 'push', '-q', 'origin', 'main')
    pushed = _git(remote, 'rev-parse', 'main').strip()
    code, out = _run(root, '--all', '--ci', '--commit')
    assert code == 0, out
    commits = len(_subjects(root))

    code, out = _run(root, '--all', '--ci', '--commit')

    assert code == 0, out
    assert 'Evidence unchanged.' in out.splitlines(), out
    assert len(_subjects(root)) == commits
    assert _git(remote, 'rev-parse', 'main').strip() == pushed


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


def _name_the_machine(root, machine, message):
    """Commit `feat`'s local evidence with this system's section naming
    `machine`, as another machine's run would leave it."""
    data = _evidence(root)
    data['platforms'][HERE]['machine'] = machine
    _put(root, data)
    _git(root, 'commit', '-q', '-am', message)


# purlin: evidence_writer PROOF-85
def test_a_run_rewrites_a_section_resolved_to_either_side_of_a_merge(
        tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    code, out = _run(root, '--all', '--test', '--commit')
    assert code == 0, out
    _git(root, 'checkout', '-q', '-b', 'other')
    _name_the_machine(root, 'build-9', 'the run on build-9')
    _git(root, 'checkout', '-q', 'main')
    _name_the_machine(root, 'build-8', 'the run on build-8')
    merged = subprocess.run(['git', 'merge', '-q', 'other'], cwd=str(root),
                            capture_output=True, encoding='utf-8')
    assert merged.returncode != 0, merged.stdout + merged.stderr
    _git(root, 'checkout', '--theirs', '--', '.purlin/evidence/local/feat.json')
    _git(root, 'add', '.purlin/evidence/local/feat.json')
    _git(root, 'commit', '-q', '--no-edit')
    assert _evidence(root)['platforms'][HERE]['machine'] == 'build-9'

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert _evidence(root)['platforms'][HERE]['machine'] == (
        writer.local_machine()), out


def _current_hashes(root, rule_id='RULE-1'):
    """`feat`'s rule, proof and test hashes for `rule_id` as they stand."""
    for feature in payload_module.build_payload(str(root)).get('features'):
        for rule in feature.get('rules') or ():
            if feature['name'] == 'feat' and rule['id'] == rule_id:
                return {key: rule[key]
                        for key in ('rule_hash', 'proof_hash', 'test_hash')}
    raise AssertionError('no %s' % rule_id)


def _audit_and_commit(root, hashes, at, finding, message):
    """Commit `feat`'s local evidence with an audit entry for RULE-1."""
    data = _evidence(root)
    entry = dict(hashes, verdict='strong', findings=[finding], model='m',
                 criteria='c', at=at, commit='a' * 40)
    data['audit'] = {'rules': {'RULE-1': entry}}
    _put(root, data)
    _git(root, 'commit', '-q', '-am', message)


def _conflicted_audits(tmp_path, reword=False):
    """`feat` audited on two branches whose merge conflicts in its evidence;
    with `reword`, the other branch also changes RULE-1's text."""
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    code, out = _run(root, '--all', '--test', '--commit')
    assert code == 0, out
    hashes = _current_hashes(root)
    _git(root, 'checkout', '-q', '-b', 'other')
    if reword:
        spec = root / 'specs' / 'a' / 'feat.md'
        spec.write_text(spec.read_text(encoding='utf-8').replace(
            'The thing works, case 1', 'The thing works, first case'),
            encoding='utf-8')
    _audit_and_commit(root, hashes, '2026-09-02T00:00:00Z', 'b', 'audit b')
    _git(root, 'checkout', '-q', 'main')
    _audit_and_commit(root, hashes, '2026-09-01T00:00:00Z', 'a', 'audit a')
    merged = subprocess.run(['git', 'merge', '-q', 'other'], cwd=str(root),
                            capture_output=True, encoding='utf-8')
    assert merged.returncode != 0, merged.stdout + merged.stderr
    text = (root / '.purlin' / 'evidence' / 'local' / 'feat.json').read_text(
        encoding='utf-8')
    assert '<<<<<<<' in text, text
    return root


# purlin: evidence_writer PROOF-88
def test_a_run_over_a_conflicted_file_keeps_the_audit_that_still_matches(
        tmp_path):
    root = _conflicted_audits(tmp_path)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    entry = _evidence(root)['audit']['rules']['RULE-1']
    assert {key: entry[key] for key in ('rule_hash', 'proof_hash',
                                        'test_hash')} == _current_hashes(root)
    assert entry['findings'] == ['b'], entry


# purlin: evidence_writer PROOF-89
def test_a_run_over_a_conflicted_file_drops_an_audit_of_older_text(tmp_path):
    root = _conflicted_audits(tmp_path, reword=True)

    code, out = _run(root, '--all', '--test')

    assert code == 0, out
    assert 'RULE-1' not in (_evidence(root).get('audit') or {}).get(
        'rules', {}), out


# ---------------------------------------------------------------------------
# The audit's entries
# ---------------------------------------------------------------------------

def _entry(word='strong'):
    return {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
            'verdict': word, 'findings': [], 'breaks': {}, 'explanation': [],
            'model': 'm', 'criteria': 'c', 'at': 'x', 'commit': 'y'}


# purlin: evidence_writer PROOF-12
def test_an_audit_adds_the_entry_it_read_and_keeps_the_others(tmp_path):
    root = tmp_path
    info = _info(rules=('RULE-1', 'RULE-2'))
    earlier = dict(_entry('weak'), findings=['tests/a.py::test_a: the test '
                                             'checks nothing.'])
    path = _put(root, _file(platforms={'linux': _section()},
                            audit={'rules': {'RULE-2': earlier}}))
    before = path.read_text(encoding='utf-8')

    writer.write_audit(str(root), 'local', 'feat', info,
                       {'RULE-1': _entry()})

    audit = _evidence(root)['audit']
    assert audit == {'rules': {'RULE-1': _entry(), 'RULE-2': earlier}}
    held = '"RULE-2": %s' % json.dumps(earlier, indent=2, sort_keys=True
                                       ).replace('\n', '\n      ')
    assert held in before
    assert held in path.read_text(encoding='utf-8')


NOTHING_TO_CHANGE = 'no break: the code has nothing to change'


# purlin: evidence_writer PROOF-54
def test_an_audit_run_writes_the_entry_for_the_rule_it_read(tmp_path):
    root = _project(tmp_path)
    _spec(root)
    _test_file(root)
    _repo(root)
    model = fake_claude.install(tmp_path / 'model', answers=(
        NOTHING_TO_CHANGE,), model='claude-fake-1')
    path = model + os.pathsep + os.environ.get('PATH', '')
    assert shutil.which('claude', path=path).startswith(str(tmp_path))

    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root), '--all',
         '--audit'], capture_output=True, encoding='utf-8', cwd=str(root),
        env=dict(os.environ, PATH=path))
    out = result.stdout + result.stderr

    entry = _evidence(root).get('audit', {}).get('rules', {}).get('RULE-1')
    assert entry, out
    data = payload_module.build_payload(str(root))
    rule = next(r for f in data['features'] for r in f['rules']
                if r['id'] == 'RULE-1')
    assert (entry['rule_hash'], entry['proof_hash'], entry['test_hash']) == (
        rule['rule_hash'], rule['proof_hash'], rule['test_hash']), out
    assert entry['verdict'] == 'strong'
    assert entry['findings'] == []
    assert entry['breaks']['PROOF-1']['result'] == 'not made'
    assert entry['model'] == 'claude-fake-1'
    with open(os.path.join(REPO, 'references', 'review_criteria.md'),
              encoding='utf-8') as handle:
        assert entry['criteria'] == hashlib.sha256(
            handle.read().encode('utf-8')).hexdigest()
    assert STAMP.match(entry['at'])
    assert entry['commit'] == _head(root)


HASHES = {'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't'}
FOUND = {'verdict': 'strong', 'findings': [], 'model': 'claude-a',
         'criteria': 'c' * 64}
FIRST_AT, FIRST_COMMIT = '2026-09-01T00:00:00Z', 'a' * 40
LATER_AT, LATER_COMMIT = '2026-09-02T00:00:00Z', 'b' * 40


def _audited(root, rule=HASHES, found=FOUND, commit=FIRST_COMMIT,
             at=FIRST_AT):
    """Write one audit entry for RULE-1. The entry the file then holds."""
    writer.write_audit(str(root), 'local', 'feat', _info(),
                       {'RULE-1': writer.audit_entry(rule, found, commit,
                                                     at=at)})
    return _evidence(root)['audit']['rules']['RULE-1']


def _on_file_then(root, rule=HASHES, found=FOUND):
    """The first entry on file, then this one written later on another
    commit. The entry the file then holds."""
    _put(root, _file(platforms={'linux': _section()}))
    _audited(root)
    return _audited(root, rule, found, LATER_COMMIT, LATER_AT)


def _one_field_differs(root, key, value):
    """The entry the file holds after one that differs in `key` alone."""
    if key.endswith('_hash'):
        entry = _on_file_then(root, rule=dict(HASHES, **{key: value}))
    else:
        entry = _on_file_then(root, found=dict(FOUND, **{key: value}))
    return entry[key], entry['at'], entry['commit']


# purlin: evidence_writer PROOF-14
def test_a_repeated_entry_keeps_its_time_and_commit(tmp_path):
    entry = _on_file_then(tmp_path)
    assert (entry['at'], entry['commit']) == (FIRST_AT, FIRST_COMMIT)


# purlin: evidence_writer PROOF-64
def test_an_entry_from_another_model_replaces_it(tmp_path):
    entry = _on_file_then(tmp_path, found=dict(FOUND, model='claude-b'))
    assert (entry['model'], entry['at'], entry['commit']) == (
        'claude-b', LATER_AT, LATER_COMMIT)


# purlin: evidence_writer PROOF-65
def test_an_entry_with_another_rule_hash_replaces_it(tmp_path):
    assert _one_field_differs(tmp_path, 'rule_hash', 'r2') == (
        'r2', LATER_AT, LATER_COMMIT)


# ---------------------------------------------------------------------------
# What is ignored
# ---------------------------------------------------------------------------

# purlin: evidence_writer PROOF-63
def test_git_ignores_the_run_log_and_not_the_evidence_after_init(tmp_path):
    root = tmp_path / 'fresh'
    root.mkdir()
    _git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    # With `--yes` setup commits what it wrote, so the checkout gets an
    # identity of its own and no signing.
    _git(root, 'config', 'user.email', 'dev@example.com')
    _git(root, 'config', 'user.name', 'Dev')
    _git(root, 'config', 'commit.gpgsign', 'false')
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    done = subprocess.run(
        [sys.executable, os.path.join(REPO, 'scripts', 'init', 'scaffold.py'),
         '--project-root', str(root), '--yes'],
        capture_output=True, encoding='utf-8', env=env,
        stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert '.purlin/runtime/' in (root / '.gitignore').read_text(
        encoding='utf-8')
    for rel in ('.purlin/evidence/local/feat.json', '.purlin/runtime/run.log'):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text('{}\n', encoding='utf-8')
    asked = subprocess.run(
        ['git', 'check-ignore', '.purlin/evidence/local/feat.json',
         '.purlin/runtime/run.log'],
        cwd=str(root), capture_output=True, encoding='utf-8')
    assert asked.stdout.splitlines() == ['.purlin/runtime/run.log'], asked
