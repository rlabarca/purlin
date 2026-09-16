"""Tests for the pathspec a developer's record commit hands git.

`os.path.join` spells the records directory `.purlin\\records` on Windows, and
a git pathspec with `\\` matches nothing, so a record commit made there staged
nothing. These tests stand in for Windows by spelling the directory that way.
"""

import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import records as records_module  # noqa: E402


def _git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          text=True, check=True).stdout


def _write(root, rel, text='{}\n'):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


@pytest.mark.proof("records", "PROOF-26", "RULE-24")
def test_git_is_handed_a_forward_slash_pathspec(tmp_path, monkeypatch):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, '.purlin', 'records'))
    monkeypatch.setattr(records_module, 'RECORDS_DIR', '.purlin\\records')
    calls = []

    def fake_git(project_root, args, check=True):
        calls.append(list(args))
        if args[:2] == ['diff', '--cached']:
            return ''
        return ''

    monkeypatch.setattr(records_module, '_git', fake_git)
    records_module.deleted_records(root)
    records_module.commit_records(
        root, ['.purlin/records/login/20260916T120000Z-abc1234-ada.json'],
        'developer', 'purlin: record for abc1234')
    handed = [(args[0], args[args.index('--') + 1:]) for args in calls
              if args[0] in ('ls-files', 'add')]
    assert [command for command, _specs in handed] == ['ls-files', 'add'], calls
    for command, specs in handed:
        assert specs and not [spec for spec in specs if '\\' in spec], \
            (command, specs)
        assert '.purlin/records' in specs, (command, specs)


@pytest.mark.proof("records", "PROOF-27", "RULE-24", tier="integration")
def test_the_commit_carries_the_new_record_and_the_deletion(tmp_path):
    root = str(tmp_path)
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.email', 'dev@example.com')
    _git(root, 'config', 'user.name', 'Dev')
    _git(root, 'config', 'commit.gpgsign', 'false')
    old = '.purlin/records/login/20260915T120000Z-abc1234-ada.json'
    kept = '.purlin/records/login/20260915T130000Z-abc1234-ada.json'
    new = '.purlin/records/login/20260916T120000Z-def5678-ada.json'
    _write(root, old)
    _write(root, kept)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'records')
    os.remove(os.path.join(root, *old.split('/')))
    _write(root, new)
    assert records_module.deleted_records(root) == [old]
    sha = records_module.commit_records(root, [new], 'developer',
                                        'purlin: record for def5678')
    assert sha
    changed = _git(root, 'show', '--no-renames', '--name-status', '--format=', sha).split('\n')
    assert 'D\t' + old in changed, changed
    assert 'A\t' + new in changed, changed
