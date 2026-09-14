"""Tests for `scripts/report/scan.py`, against local repositories only.

`scan.py` is how QA and a PM read a project without a checkout. The tests
build a small project, push it to a local bare repository, and scan that
repository by path: git fetches from a path exactly as it fetches from a URL,
so nothing here reaches a network and every assertion is about what a real
fetch brings back.

What the groups prove:

*fetch*     only `specs/` and `.purlin/` arrive; the project's code does not
*rollup*    the seven states are counted and named, and the gate is printed
*distance*  how far the scanned ref has moved past the newest record
*ref*       `--ref` reads the branch or tag it names, not the default one
"""

import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'report'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import scan as scan_module  # noqa: E402

SPEC = """# Feature: greeting

> Scope: greeting.py
> Stack: python/stdlib
> Description: One rule any host proves and one a Linux host proves.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`
- RULE-2: On a Linux host, `os_tag()` returns `linux`

## Proof

- PROOF-1 (RULE-1): Call `greet("Ada")` and verify `Hello, Ada!` @unit
- PROOF-2 (RULE-2): Call `os_tag()` and verify `linux` @unit @env(linux)
"""

CONFIG = {'version': '0.10.0', 'gate': 'recorded', 'test_framework': 'pytest'}


def git(cwd, *args, **kwargs):
    result = subprocess.run(['git'] + list(args), cwd=str(cwd),
                            capture_output=True, text=True)
    if kwargs.get('check', True):
        assert result.returncode == 0, ' '.join(args) + ': ' + result.stderr
    return result


def write(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def make_project(path):
    """A project with one spec, one source file and a `.purlin/` config."""
    os.makedirs(path, exist_ok=True)
    git(path, 'init', '--quiet', '-b', 'main')
    git(path, 'config', 'user.name', 'Ada Lovelace')
    git(path, 'config', 'user.email', 'ada@example.com')
    git(path, 'config', 'commit.gpgsign', 'false')
    write(os.path.join(path, 'specs', 'core', 'greeting.md'), SPEC)
    write(os.path.join(path, 'greeting.py'),
          "def greet(name):\n    return 'Hello, %s!' % name\n")
    write(os.path.join(path, '.purlin', 'config.json'),
          json.dumps(CONFIG, indent=2) + '\n')
    git(path, 'add', '-A')
    git(path, 'commit', '--quiet', '-m', 'the project')
    return path


def add_record(path, commit, timestamp='20260913T120000Z', status='pass'):
    """Commit one record naming the commit it observed."""
    body = {'schema_version': 1, 'feature': 'greeting', 'commit': commit,
            'gate': 'recorded', 'test_strength': 71, 'scope_tree': 'a' * 40,
            'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': status,
                        'tier': 'unit', 'env': None,
                        'test_file': 'tests/test_greeting.py',
                        'test_name': 'test_greet'}]}
    rel = '.purlin/records/greeting/%s-%s-ci.json' % (timestamp, commit[:7])
    write(os.path.join(path, rel), json.dumps(body, indent=2) + '\n')
    git(path, 'add', '-A')
    git(path, 'commit', '--quiet', '-m', 'purlin: record for %s' % commit[:7])
    return rel


@pytest.fixture
def remote(tmp_path):
    """A bare repository holding the project, and the working copy behind it."""
    source = make_project(str(tmp_path / 'source'))
    bare = str(tmp_path / 'origin.git')
    git(tmp_path, 'init', '--bare', '--quiet', '-b', 'main', bare)
    git(source, 'remote', 'add', 'origin', bare)
    git(source, 'push', '--quiet', '-u', 'origin', 'main')
    return bare, source


# ---------------------------------------------------------------------------
# The fetch
# ---------------------------------------------------------------------------

@pytest.mark.proof("scan", "PROOF-1", "RULE-1")
def test_the_fetch_brings_the_specs_and_the_records_and_no_code(remote,
                                                                tmp_path):
    bare, source = remote
    add_record(source, git(source, 'rev-parse', 'HEAD').stdout.strip())
    git(source, 'push', '--quiet')

    into = str(tmp_path / 'scanned')
    os.makedirs(into)
    sha = scan_module.fetch(bare, 'main', into)

    assert len(sha) == 40
    assert os.path.isfile(os.path.join(into, 'specs', 'core', 'greeting.md'))
    assert os.path.isfile(os.path.join(into, '.purlin', 'config.json'))
    assert os.path.isdir(os.path.join(into, '.purlin', 'records'))
    assert not os.path.exists(os.path.join(into, 'greeting.py')), (
        'the fetch brought code, which is what sparse checkout exists to avoid')


@pytest.mark.proof("scan", "PROOF-1", "RULE-1")
def test_a_ref_that_does_not_exist_is_refused_by_name(remote, tmp_path):
    bare, _source = remote
    into = str(tmp_path / 'scanned')
    os.makedirs(into)
    with pytest.raises(SystemExit) as raised:
        scan_module.fetch(bare, 'no-such-branch', into)
    assert 'no-such-branch' in str(raised.value)


# ---------------------------------------------------------------------------
# The rollup
# ---------------------------------------------------------------------------

@pytest.mark.proof("scan", "PROOF-2", "RULE-2")
def test_the_rollup_names_the_project_the_gate_and_the_states(remote):
    bare, _source = remote
    text = scan_module.scan(bare, 'main')

    assert 'gate recorded' in text
    assert '1 features, 2 rules.' in text
    assert 'Proof ready' in text, 'no state was counted'
    assert 'No record has been committed yet.' in text


@pytest.mark.proof("scan", "PROOF-2", "RULE-2")
def test_the_rollup_names_the_newest_record_and_its_label(remote):
    bare, source = remote
    head = git(source, 'rev-parse', 'HEAD').stdout.strip()
    rel = add_record(source, head)
    git(source, 'push', '--quiet')

    text = scan_module.scan(bare, 'main')

    assert rel in text
    assert 'developer' in text, 'the label a person\'s commit earns'
    assert '0 commits behind the latest record.' in text


@pytest.mark.proof("scan", "PROOF-2", "RULE-2")
def test_every_state_the_package_names_can_be_printed():
    from purlin import states
    payload = {'project': 'x', 'gate': {'gate': 'tested'},
               'project_rollup': {'features': 1, 'rules': len(states.STATE_ORDER),
                                  'counts': {s: 1 for s in states.STATE_ORDER},
                                  'stale': 1, 're_verify_pending': 2},
               'records': {}}
    text = scan_module.rollup_text('.', payload)
    for state in states.STATE_ORDER:
        assert state in text, '%s was not printed' % state
    assert '1 rules are Stale' in text
    assert '2 rules are re-verify pending' in text


# ---------------------------------------------------------------------------
# The distance from the newest record
# ---------------------------------------------------------------------------

@pytest.mark.proof("scan", "PROOF-3", "RULE-3")
def test_the_rollup_counts_the_commits_since_the_record(remote):
    bare, source = remote
    head = git(source, 'rev-parse', 'HEAD').stdout.strip()
    add_record(source, head)
    for index in range(2):
        write(os.path.join(source, 'greeting.py'),
              "def greet(name):\n    return 'Hello, %%s!' %% name  # %d\n" % index)
        git(source, 'add', '-A')
        git(source, 'commit', '--quiet', '-m', 'change %d' % index)
    git(source, 'push', '--quiet')

    text = scan_module.scan(bare, 'main')

    assert '2 commits behind the latest record.' in text, (
        'the commit carrying the record is not one the code moved by')


@pytest.mark.proof("scan", "PROOF-3", "RULE-3")
def test_a_commit_the_fetch_did_not_reach_is_said_to_be_unknown(remote,
                                                                tmp_path):
    bare, _source = remote
    into = str(tmp_path / 'scanned')
    os.makedirs(into)
    scan_module.fetch(bare, 'main', into)
    assert scan_module.commits_behind(into, 'f' * 40) is None


@pytest.mark.proof("scan", "PROOF-3", "RULE-3")
def test_the_newest_record_is_the_one_with_the_latest_timestamp():
    older = {'timestamp': '2026-09-13T12:00:00Z', 'path': 'a'}
    newer = {'timestamp': '2026-09-14T12:00:00Z', 'path': 'b'}
    payload = {'records': {'greeting': {'': older},
                           'login': {'linux': newer}}}
    assert scan_module.newest_record(payload) is newer
    assert scan_module.newest_record({'records': {}}) is None


# ---------------------------------------------------------------------------
# Choosing a ref, and the command line
# ---------------------------------------------------------------------------

@pytest.mark.proof("scan", "PROOF-4", "RULE-4")
def test_a_tag_is_read_rather_than_the_default_branch(remote):
    bare, source = remote
    git(source, 'tag', '-a', 'v1.0', '-m', 'the first release')
    git(source, 'push', '--quiet', 'origin', 'v1.0')
    write(os.path.join(source, 'specs', 'core', 'greeting.md'),
          SPEC.replace('- RULE-2:', '- RULE-3: a third rule\n- RULE-2:'))
    git(source, 'add', '-A')
    git(source, 'commit', '--quiet', '-m', 'a third rule')
    git(source, 'push', '--quiet')

    assert '2 rules.' in scan_module.scan(bare, 'v1.0')
    assert '3 rules.' in scan_module.scan(bare, 'main')


@pytest.mark.proof("scan", "PROOF-4", "RULE-4")
def test_the_command_prints_the_rollup(remote, capsys):
    bare, _source = remote
    assert scan_module.main(['--repo', bare, '--ref', 'main']) == 0
    assert 'gate recorded' in capsys.readouterr().out


@pytest.mark.proof("scan", "PROOF-4", "RULE-4")
def test_the_command_requires_a_repository():
    with pytest.raises(SystemExit):
        scan_module.main([])


@pytest.mark.proof("scan", "PROOF-4", "RULE-4")
def test_the_scan_leaves_nothing_behind(remote, tmp_path, monkeypatch):
    bare, _source = remote
    holder = str(tmp_path / 'scratch')
    os.makedirs(holder)
    monkeypatch.setenv('TMPDIR', holder)
    scan_module.scan(bare, 'main')
    assert os.listdir(holder) == [], 'the temporary checkout was not removed'
