"""Tests for `scripts/mcp/purlin/evidence.py`, the evidence reader.

Every test builds a real git repository in a temporary directory, writes the
evidence files by hand in the shape `references/formats/evidence_format.md`
gives, and reads them back. The fingerprint a section is checked against is
taken by the real fingerprint module over that repository.
"""

import json
import os
import platform
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from purlin import evidence, fingerprint  # noqa: E402

SPEC = ('# Feature: login\n\n'
        '> Description: Signing in.\n'
        '> Scope: src/login.py\n\n'
        '## Rules\n\n- RULE-1: Valid credentials return 200\n\n'
        '## Proof\n\n- PROOF-1 (RULE-1): POST /login; verify 200\n')


def _git(root, *args):
    result = subprocess.run(['git'] + list(args), cwd=root,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


@pytest.fixture
def root(tmp_path):
    root = str(tmp_path)
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.email', 'dev@example.com')
    _git(root, 'config', 'user.name', 'Dev')
    _git(root, 'config', 'commit.gpgsign', 'false')
    _write(root, 'specs/auth/login.md', SPEC)
    _write(root, 'src/login.py', 'def login():\n    return 200\n')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'feat: fixture')
    return root


def _section(at='2026-09-01T00:00:00Z', fp=None):
    return {'commit': 'a' * 40, 'dirty': False, 'at': at, 'runner': 'dev',
            'fingerprint': fp or {'spec': 's', 'code': 'c', 'tests': 't'},
            'rules': {'RULE-1': 'passed'},
            'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'result': 'pass',
                        'env': None, 'manual': False,
                        'test': 'tests/test_login.py::test_login'}]}


def _file(source, platforms=None, audit=None, **overrides):
    data = {'schema': 'purlin-evidence/2', 'feature': 'login',
            'source': source, 'spec': 'specs/auth/login.md',
            'platforms': platforms or {}}
    if audit is not None:
        data['audit'] = audit
    data.update(overrides)
    return data


def _put(root, source, data):
    text = data if isinstance(data, str) else json.dumps(data, indent=2)
    _write(root, '.purlin/evidence/%s/login.json' % source, text)


# purlin: evidence PROOF-17
def test_only_a_ci_file_reads_the_ci_file_no_local_file_and_no_warning(root):
    written = _file('ci', {'linux': _section()})
    _put(root, 'ci', written)
    loaded = evidence.load(root, 'login')
    # The file as written, its linux section included.
    assert loaded['files']['ci'] == written
    assert loaded['files']['ci']['source'] == 'ci'
    assert loaded['files']['local'] is None
    assert loaded['paths'] == {'local': '.purlin/evidence/local/login.json',
                               'ci': '.purlin/evidence/ci/login.json'}
    assert loaded['warnings'] == []


def _ignored_local(root, content):
    """Load `login` with `content` as its local file; the one warning."""
    _put(root, 'local', content)
    loaded = evidence.load(root, 'login')
    assert loaded['files']['local'] is None
    (warning,) = loaded['warnings']
    return warning


# purlin: evidence PROOF-18
def test_a_file_that_is_not_json_is_ignored_with_one_warning(root):
    assert _ignored_local(root, '{not json') == (
        '.purlin/evidence/local/login.json: evidence file ignored. It is not '
        'valid JSON. Run purlin:test login.')


# purlin: evidence PROOF-52
def test_a_file_of_another_schema_is_ignored_with_one_warning(root):
    content = json.dumps(_file('local', schema='purlin-evidence/1'))
    assert _ignored_local(root, content) == (
        '.purlin/evidence/local/login.json: evidence file ignored. It '
        'carries the schema "purlin-evidence/1", not purlin-evidence/2. '
        'Run purlin:test login.')


# purlin: evidence PROOF-19
def test_a_source_that_disagrees_with_its_folder_is_ignored(root):
    _put(root, 'ci', _file('local', {'linux': _section()}))
    loaded = evidence.load(root, 'login')
    assert loaded['files']['ci'] is None
    assert loaded['warnings'] == [
        '.purlin/evidence/ci/login.json: evidence file ignored. It names '
        'the source "local". Start the run that wrote it again.']


# purlin: evidence PROOF-20
def test_sections_list_local_macos_local_linux_then_ci_windows_and_no_solaris(
        root):
    _put(root, 'local', _file('local', {'linux': _section(),
                                        'macos': _section(),
                                        'solaris': _section()}))
    _put(root, 'ci', _file('ci', {'windows': _section()}))
    listed = [(entry['source'], entry['os'])
              for entry in evidence.sections(evidence.load(root, 'login'))]
    assert listed == [('local', 'macos'), ('local', 'linux'),
                      ('ci', 'windows')]
    assert 'solaris' not in [system for _source, system in listed]


# purlin: evidence PROOF-25
def test_a_system_neither_windows_nor_macos_is_linux(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'freebsd14')
    assert evidence.host_os() == 'linux'


# purlin: evidence PROOF-75
@pytest.mark.skipif(platform.system() != 'Windows',
                    reason='only a Windows machine can show its own name')
def test_on_windows_the_reader_names_its_own_machine_windows():
    # Nothing is simulated: the system is asked by its own call, not through
    # the value the reader reads.
    assert evidence.host_os() == 'windows'


def _stored_now(root):
    """A local `macos` section storing the fingerprint of `login` taken now."""
    now = fingerprint.fingerprint(root, 'login')
    _put(root, 'local', _file('local', {'macos': _section(fp=dict(now))}))


def _state(root):
    (entry,) = evidence.checked_sections(
        evidence.load(root, 'login'), fingerprint.fingerprint(root, 'login'))
    return entry['current'], entry['out_of_date']


# purlin: evidence PROOF-21
def test_a_section_storing_the_fingerprint_taken_now_is_current(root):
    _stored_now(root)
    assert _state(root) == (True, [])


# purlin: evidence PROOF-55
def test_a_code_edit_puts_the_section_out_of_date_on_code(root):
    _stored_now(root)
    _write(root, 'src/login.py', 'def login():\n    return 401\n')
    assert _state(root) == (False, ['code'])


def _settings(root, version='0.10.0', run='python3 -m pytest {files}'):
    """Write `.purlin/config.json`: `version`, and one pytest suite."""
    _write(root, '.purlin/config.json', json.dumps({
        'version': version,
        'tests': [{'name': 'pytest', 'run': run, 'format': 'junit',
                   'report': '.purlin/runtime/reports/pytest.xml',
                   'files': ['tests/**/*.py']}]}, indent=2) + '\n')


# purlin: evidence PROOF-88
def test_a_test_command_changed_to_one_as_long_is_out_of_date_on_tests(root):
    _settings(root)
    _stored_now(root)
    assert _state(root) == (True, [])
    _settings(root, run='python3 -m pytest -x {files}')
    assert _state(root) == (False, ['tests'])
    # A command of the same length as the one stored is a change too.
    _settings(root, run='python2 -m pytest {files}')
    assert len('python2 -m pytest {files}') == len('python3 -m pytest {files}')
    assert _state(root) == (False, ['tests'])
    # So is one that differs from the stored command in nothing but the case
    # of one letter: `-x` stops at the first failure, `-X` is another option.
    _settings(root, run='python3 -m pytest -x {files}')
    _stored_now(root)
    assert _state(root) == (True, [])
    _settings(root, run='python3 -m pytest -X {files}')
    assert _state(root) == (False, ['tests'])


# purlin: evidence PROOF-89
def test_a_changed_version_leaves_the_section_current(root):
    _settings(root, version='0.10.0')
    _stored_now(root)
    _settings(root, version='0.10.1')
    assert _state(root) == (True, [])


# purlin: evidence PROOF-57
def test_a_section_with_no_fingerprint_is_out_of_date_on_all_three(root):
    section = _section()
    del section['fingerprint']
    _put(root, 'local', _file('local', {'macos': section}))
    assert _state(root) == (False, ['spec', 'code', 'tests'])


def _audit(at, commit='b' * 40, verdict='strong'):
    return {'rules': {'RULE-1': {
        'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': 't',
        'code_hash': 'c', 'verdict': verdict, 'findings': [], 'no_bug': [],
        'at': at, 'commit': commit}}}


def _audited(root):
    """The local file of `login` holds an entry for RULE-1: `r`, `p`, `t`
    and `c`."""
    _put(root, 'local', _file('local', audit=_audit('2026-09-01T00:00:00Z')))
    return evidence.load(root, 'login')


# purlin: evidence PROOF-22
def test_an_audit_entry_answers_while_its_four_hashes_match(root):
    entry = evidence.audit_entry(_audited(root), 'RULE-1', 'r', 'p', 't', 'c')
    assert entry['source'] == 'local' and entry['verdict'] == 'strong'
    assert entry['out_of_date'] == []
    head = _git(root, 'rev-parse', 'HEAD')
    assert entry['commit'] == 'b' * 40 != head


# purlin: evidence PROOF-58
def test_an_audit_entry_for_another_test_hash_is_out_of_date_on_test(root):
    entry = evidence.audit_entry(_audited(root), 'RULE-1', 'r', 'p', 't2', 'c')
    assert entry['verdict'] == 'strong' and entry['source'] == 'local'
    assert entry['out_of_date'] == ['test']


# purlin: evidence PROOF-87
def test_an_audit_entry_for_another_code_hash_is_out_of_date_on_code(root):
    entry = evidence.audit_entry(_audited(root), 'RULE-1', 'r', 'p', 't', 'c2')
    assert entry['verdict'] == 'strong' and entry['source'] == 'local'
    assert entry['out_of_date'] == ['code']


# purlin: evidence PROOF-86
def test_of_two_current_audit_entries_the_later_one_answers(root):
    """Whichever file holds the later entry: `local` is read first and `ci`
    last, so neither the first read nor the last read can answer for both."""
    earlier, later = '2026-09-01T00:00:00Z', '2026-09-02T00:00:00Z'
    answers = []
    for local_at, ci_at in ((earlier, later), (later, earlier)):
        _put(root, 'local', _file('local', audit=_audit(local_at)))
        _put(root, 'ci', _file('ci', audit=_audit(ci_at, verdict='weak')))
        entry = evidence.audit_entry(evidence.load(root, 'login'), 'RULE-1',
                                     'r', 'p', 't', 'c')
        answers.append((entry['verdict'], entry['source'], entry['at']))
    assert answers == [('weak', 'ci', later), ('strong', 'local', later)]


# purlin: evidence PROOF-23
def test_with_no_evidence_there_is_no_newest_section(root):
    assert evidence.newest(evidence.load(root, 'login')) is None


def _newest(root, local_at, ci_at):
    _put(root, 'local', _file('local', {'macos': _section(local_at)}))
    _put(root, 'ci', _file('ci', {'linux': _section(ci_at)}))
    best = evidence.newest(evidence.load(root, 'login'))
    return best['source'], best['os']


# purlin: evidence PROOF-63
def test_the_newest_section_is_the_latest_across_both_sources(root):
    assert _newest(root, '2026-09-01T00:00:00Z', '2026-09-03T00:00:00Z') == (
        'ci', 'linux')


def _snapshot(root):
    found = {}
    base = os.path.join(root, '.purlin', 'evidence')
    for dirpath, _, filenames in os.walk(base):
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, 'rb') as handle:
                found[os.path.relpath(path, base)] = handle.read()
    return found


# purlin: evidence PROOF-24
def test_loading_checking_and_asking_leaves_the_same_files_and_bytes(root):
    _put(root, 'local', _file('local', {'macos': _section()},
                              audit=_audit('2026-09-01T00:00:00Z')))
    _put(root, 'ci', '{not json')
    before = _snapshot(root)
    loaded = evidence.load(root, 'login')
    evidence.checked_sections(loaded, fingerprint.fingerprint(root, 'login'))
    evidence.audit_entry(loaded, 'RULE-1', 'r', 'p', 't', 'c')
    evidence.newest(loaded)
    assert _snapshot(root) == before


def _listed(*results):
    return {'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'result': result,
                        'env': None, 'manual': False, 'test': test}
                       for result, test in results]}


# purlin: evidence PROOF-28
def test_a_proof_with_a_test_that_did_not_run_has_not_passed():
    section = _listed(('pass', 'tests/a.py::test_a'),
                      ('missing', 'tests/b.py::test_b'))
    assert evidence.proof_results(section) == {'PROOF-1': {'result': 'not run'}}


# purlin: evidence PROOF-29
def test_a_failing_test_outweighs_one_that_did_not_run():
    section = _listed(('missing', 'tests/a.py::test_a'),
                      ('fail', 'tests/b.py::test_b'))
    assert evidence.proof_results(section) == {'PROOF-1': {'result': 'fail'}}
