"""Tests for `scripts/mcp/purlin/evidence.py`, the evidence reader.

Every test builds a real git repository in a temporary directory, writes the
evidence files by hand in the shape `references/formats/evidence_format.md`
gives, and reads them back. The fingerprint a section is checked against is
taken by the real fingerprint module over that repository.
"""

import json
import os
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
    data = {'schema': 'purlin-evidence/1', 'feature': 'login',
            'source': source, 'spec': 'specs/auth/login.md',
            'platforms': platforms or {}}
    if audit is not None:
        data['audit'] = audit
    data.update(overrides)
    return data


def _put(root, source, data):
    text = data if isinstance(data, str) else json.dumps(data, indent=2)
    _write(root, '.purlin/evidence/%s/login.json' % source, text)


@pytest.mark.proof("evidence", "PROOF-17", "RULE-11")
def test_a_source_with_no_file_reads_as_no_evidence(root):
    _put(root, 'ci', _file('ci', {'linux': _section()}))
    loaded = evidence.load(root, 'login')
    assert loaded['files']['ci']['source'] == 'ci'
    assert loaded['files']['local'] is None
    assert loaded['paths'] == {'local': '.purlin/evidence/local/login.json',
                               'ci': '.purlin/evidence/ci/login.json'}
    assert loaded['warnings'] == []


@pytest.mark.proof("evidence", "PROOF-18", "RULE-12")
@pytest.mark.parametrize('content', [
    '{not json',
    '[1, 2]',
    json.dumps(_file('local', schema='purlin-evidence/2')),
])
def test_a_malformed_file_or_another_schema_is_ignored_with_one_warning(
        root, content):
    _put(root, 'local', content)
    loaded = evidence.load(root, 'login')
    assert loaded['files']['local'] is None
    assert len(loaded['warnings']) == 1
    assert '.purlin/evidence/local/login.json' in loaded['warnings'][0]


@pytest.mark.proof("evidence", "PROOF-19", "RULE-13")
def test_a_source_that_disagrees_with_its_folder_is_ignored(root):
    _put(root, 'ci', _file('local', {'linux': _section()}))
    loaded = evidence.load(root, 'login')
    assert loaded['files']['ci'] is None
    assert len(loaded['warnings']) == 1
    warning = loaded['warnings'][0]
    assert '.purlin/evidence/ci/login.json' in warning
    assert '"local"' in warning and 'ci/' in warning


@pytest.mark.proof("evidence", "PROOF-20", "RULE-14")
def test_two_operating_systems_in_one_file_are_two_sections(root):
    _put(root, 'local', _file('local', {'linux': _section(),
                                        'macos': _section(),
                                        'solaris': _section()}))
    _put(root, 'ci', _file('ci', {'windows': _section()}))
    listed = [(entry['source'], entry['os'])
              for entry in evidence.sections(evidence.load(root, 'login'))]
    assert listed == [('local', 'macos'), ('local', 'linux'),
                      ('ci', 'windows')]


@pytest.mark.proof("evidence", "PROOF-21", "RULE-15")
def test_a_section_is_current_until_a_part_changes(root):
    now = fingerprint.fingerprint(root, 'login')
    _put(root, 'local', _file('local', {'macos': _section(fp=dict(now))}))

    def state():
        (entry,) = evidence.checked_sections(
            evidence.load(root, 'login'), fingerprint.fingerprint(root, 'login'))
        return entry['current'], entry['out_of_date']

    assert state() == (True, [])
    _write(root, 'src/login.py', 'def login():\n    return 401\n')
    assert state() == (False, ['code'])
    _write(root, 'specs/auth/login.md',
           SPEC.replace('return 200', 'return 201'))
    assert state() == (False, ['spec', 'code'])
    section = _section()
    del section['fingerprint']
    _put(root, 'local', _file('local', {'macos': section}))
    assert state() == (False, ['spec', 'code', 'tests'])


def _audit(at, commit='b' * 40, test_hash='t'):
    return {'mutation': None, 'rules': {'RULE-1': {
        'rule_hash': 'r', 'proof_hash': 'p', 'test_hash': test_hash,
        'verdict': 'strong', 'findings': [], 'at': at, 'commit': commit}}}


@pytest.mark.proof("evidence", "PROOF-22", "RULE-16")
def test_an_audit_entry_answers_only_while_its_three_hashes_match(root):
    _put(root, 'local', _file('local', audit=_audit('2026-09-01T00:00:00Z')))
    loaded = evidence.load(root, 'login')
    entry = evidence.audit_entry(loaded, 'RULE-1', 'r', 'p', 't')
    assert entry['source'] == 'local' and entry['verdict'] == 'strong'
    assert evidence.audit_entry(loaded, 'RULE-1', 'r', 'p', 't2') is None
    _put(root, 'ci', _file('ci', audit=_audit('2026-09-02T00:00:00Z',
                                               commit='c' * 40)))
    entry = evidence.audit_entry(evidence.load(root, 'login'),
                                 'RULE-1', 'r', 'p', 't')
    assert entry['source'] == 'ci' and entry['commit'] == 'c' * 40
    assert entry['path'] == '.purlin/evidence/ci/login.json'


@pytest.mark.proof("evidence", "PROOF-23", "RULE-17")
def test_the_newest_section_across_both_sources(root):
    assert evidence.newest(evidence.load(root, 'login')) is None
    _put(root, 'local', _file('local', {
        'macos': _section('2026-09-01T00:00:00Z')}))
    _put(root, 'ci', _file('ci', {'linux': _section('2026-09-03T00:00:00Z')}))
    best = evidence.newest(evidence.load(root, 'login'))
    assert (best['source'], best['os']) == ('ci', 'linux')
    _put(root, 'ci', _file('ci', {'linux': _section('2026-09-01T00:00:00Z')}))
    best = evidence.newest(evidence.load(root, 'login'))
    assert (best['source'], best['os']) == ('local', 'macos')


def _snapshot(root):
    found = {}
    base = os.path.join(root, '.purlin', 'evidence')
    for dirpath, _, filenames in os.walk(base):
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, 'rb') as handle:
                found[os.path.relpath(path, base)] = handle.read()
    return found


@pytest.mark.proof("evidence", "PROOF-24", "RULE-18")
def test_reading_evidence_writes_nothing(root):
    _put(root, 'local', _file('local', {'macos': _section()},
                              audit=_audit('2026-09-01T00:00:00Z')))
    _put(root, 'ci', '{not json')
    before = _snapshot(root)
    loaded = evidence.load(root, 'login')
    evidence.checked_sections(loaded, fingerprint.fingerprint(root, 'login'))
    evidence.audit_entry(loaded, 'RULE-1', 'r', 'p', 't')
    evidence.newest(loaded)
    assert _snapshot(root) == before
