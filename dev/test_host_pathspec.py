"""Tests for the pathspec the CI commit hands git.

`os.path.join` spells the evidence directory `.purlin\\evidence` on Windows,
and a git pathspec with `\\` matches nothing, so a run there would find none
of the files it had removed and the CI commit would carry no deletion. The
pathspec is written with `/` once, and these tests hold it there.
"""

import json
import ntpath
import os
import subprocess
import sys
import urllib.request

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import host as host_module  # noqa: E402


def _git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          text=True, check=True).stdout


def _write(root, rel, text='{}\n'):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


class _WindowsOs(object):
    """The `os` module as Windows has it: paths joined with `\\`."""

    path = ntpath
    sep = '\\'

    def __getattr__(self, name):
        return getattr(os, name)


class _Host(object):
    """Just enough of GitHub for one commit: every call is kept."""

    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout=None):
        body = json.loads(request.data.decode('utf-8')) if request.data \
            else None
        self.calls.append((request.get_method(), request.full_url, body))
        url = request.full_url
        if '/git/ref/heads/' in url:
            answer = {'object': {'sha': '1' * 40}}
        elif '/git/commits/' in url:
            answer = {'tree': {'sha': 't' * 40}}
        elif url.endswith('/trees'):
            answer = {'sha': 'n' * 40}
        elif url.endswith('/commits'):
            answer = {'sha': 'c' * 40}
        else:
            answer = {'object': {'sha': 'c' * 40}}

        class _Answer(object):
            def read(self_inner):
                return json.dumps(answer).encode('utf-8')

            def close(self_inner):
                return None
        return _Answer()


def _repository_with_a_removed_file(root):
    """A repository whose last commit holds two evidence files, one gone.

    Answers the two paths, `(removed, kept)`.
    """
    _git(root, 'init', '-q', '-b', 'main')
    _git(root, 'config', 'user.email', 'dev@example.com')
    _git(root, 'config', 'user.name', 'Dev')
    _git(root, 'config', 'commit.gpgsign', 'false')
    gone = '.purlin/evidence/ci/retired.json'
    kept = '.purlin/evidence/ci/login.json'
    _write(root, gone)
    _write(root, kept)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'evidence')
    os.remove(os.path.join(root, *gone.split('/')))
    return gone, kept


def _on_github(monkeypatch):
    """The GitHub variables of a run branch job, and its answers recorded."""
    for variable in ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY',
                     'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'acme/widgets')
    monkeypatch.setenv('GITHUB_TOKEN', 'a-token')
    monkeypatch.setenv('GITHUB_REF_NAME', 'main')
    fake = _Host()
    monkeypatch.setattr(urllib.request, 'urlopen', fake)
    return fake


def _tree_sent(fake):
    return [body for verb, url, body in fake.calls
            if url.endswith('/trees')][0]['tree']


# purlin: host PROOF-118
def test_a_run_that_spells_paths_the_windows_way_commits_the_removal(
        tmp_path, monkeypatch):
    """Paths joined with `\\`, as on Windows; git itself is this machine's.

    Elsewhere the Windows spelling is given to the module; on Windows it is
    the system's own, and nothing is given.
    """
    root = str(tmp_path)
    gone, _kept = _repository_with_a_removed_file(root)
    fake = _on_github(monkeypatch)
    if os.name != 'nt':
        monkeypatch.setattr(host_module, 'os', _WindowsOs())
    assert host_module.os.path.join('.purlin', 'evidence') == \
        '.purlin\\evidence'

    host_module.commit_files(root, [], 'purlin: evidence at 1111111')

    tree = _tree_sent(fake)
    assert [entry['path'] for entry in tree] == [gone]
    assert tree[0]['sha'] is None and 'content' not in tree[0]


