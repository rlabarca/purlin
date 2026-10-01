"""Tests for `scripts/run/host.py`, `scripts/run/ci.py` and `scripts/run/remote.py`.

Every git host call is mocked at the HTTP boundary (`urllib.request.urlopen`),
and every git operation runs against a local repository with a local bare
repository as its remote. Nothing here reaches a network.

What each group proves:

*ci*          one tree request carrying every file's text, then commit, then
              ref update, with no author and no committer field, retried
              when the branch moved and paused when the git host asks
*merge*       on every attempt each file is read again at the branch's head
              and this runner's section is merged into it; on Azure DevOps a
              file the branch holds is an `edit` and one it does not an `add`
*remote*      `--remote` hands the run to the git host and brings it back
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import evidence as writer  # noqa: E402
import host as host_module  # noqa: E402
import remote as remote_module  # noqa: E402

def stand_in(folder, name):
    """A program `name` in `folder` that the system's own lookup finds.

    On POSIX a file with no ending and the exec bit set; on Windows always
    `<name>.cmd`, which `PATHEXT` names, and never an `.exe`.
    """
    if os.name == 'nt':
        path = os.path.join(str(folder), name + '.cmd')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('@echo off\r\n')
    else:
        path = os.path.join(str(folder), name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('#!/bin/sh\n')
        os.chmod(path, 0o755)
    return path


def _no_workspace(monkeypatch):
    """Take the job's own workspace out of a test's environment.

    Every fixture project here is a temporary directory, so on a runner it is
    never the workspace and the git host arms would refuse it, which is the
    behaviour RULE-27 asks for and the wrong starting point for every other
    test in this file.
    """
    for variable in ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY'):
        monkeypatch.delenv(variable, raising=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(cwd, *args, **kwargs):
    result = subprocess.run(['git'] + list(args), cwd=str(cwd),
                            capture_output=True, text=True)
    if kwargs.get('check', True):
        assert result.returncode == 0, ' '.join(args) + ': ' + result.stderr
    return result


def make_repo(path):
    """A git repository with one commit and an identity that is not CI's."""
    os.makedirs(str(path), exist_ok=True)
    git(path, 'init', '--quiet', '-b', 'main')
    git(path, 'config', 'user.name', 'Ada Lovelace')
    git(path, 'config', 'user.email', 'ada@example.com')
    git(path, 'config', 'commit.gpgsign', 'false')
    with open(os.path.join(str(path), 'README.md'), 'w',
              encoding='utf-8') as handle:
        handle.write('the project\n')
    git(path, 'add', '-A')
    git(path, 'commit', '--quiet', '-m', 'the project')
    return str(path)


SECTION_AT = '2026-09-13T12:00:00Z'
SHA_SEEN = '4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7'


def section(result='pass', at=SECTION_AT, commit=SHA_SEEN):
    """One platform section, as a run writes it."""
    return {'commit': commit, 'dirty': False, 'at': at, 'runner': 'ci',
            'fingerprint': {'spec': 's', 'code': 'c', 'tests': 't'},
            'rules': {'RULE-1': 'passed' if result == 'pass' else 'failed'},
            'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'result': result,
                        'env': None, 'manual': False,
                        'test': 'tests/test_greeting.py::test_greet'}]}


def evidence_file(feature='greeting', platforms=None, source='ci'):
    return {'schema': 'purlin-evidence/2', 'feature': feature,
            'source': source, 'spec': 'specs/core/%s.md' % feature,
            'platforms': platforms if platforms is not None
            else {'linux': section()}}


def write_ci(root, feature='greeting', platforms=None):
    """Write `.purlin/evidence/ci/<feature>.json` as a runner would. Its path."""
    rel = '.purlin/evidence/ci/%s.json' % feature
    full = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as handle:
        handle.write(writer.dump(evidence_file(feature, platforms)))
    return rel


class Response(object):
    """The smallest thing `urllib.request.urlopen` may return."""

    def __init__(self, body):
        self._body = json.dumps(body).encode('utf-8')

    def read(self):
        return self._body

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class FakeHost(object):
    """A git host at the HTTP boundary: it records calls and answers them.

    `fail_patch` is how many ref updates are refused with 422 before one is
    accepted, which is what a branch moving under the run looks like.
    `refuse_trees` is how many tree requests are refused with `refuse_status`
    carrying `refuse_headers`, which is what the git host's limit on
    content-creating requests looks like.
    """

    def __init__(self, fail_patch=0, head='1' * 40, azure=False,
                 refuse_trees=0, refuse_headers=None, refuse_status=403,
                 files=None, files_after_retry=None):
        # `files` is `{path: text}`, what the branch's head holds; a path not
        # in it answers 404. `files_after_retry` is what the head holds once
        # a first ref update was refused, which is a branch another runner
        # moved in between.
        self.files = dict(files or {})
        self.files_after_retry = files_after_retry
        self.fail_patch = fail_patch
        self.head = head
        self.azure = azure
        self.patched = 0
        self.refuse_trees = refuse_trees
        self.refuse_headers = refuse_headers or {}
        self.refuse_status = refuse_status
        self.trees = 0
        self.calls = []

    def _held(self):
        if self.files_after_retry is not None and self.patched > 0:
            return self.files_after_retry
        return self.files

    def __call__(self, request, timeout=None):
        method = request.get_method()
        url = request.full_url
        body = json.loads(request.data.decode('utf-8')) if request.data else None
        self.calls.append((method, url, body))
        return self._answer(method, url, body)

    def _answer(self, method, url, body):
        if self.azure:
            return self._azure(method, url, body)
        if url.endswith('/blobs'):
            return Response({'sha': 'b' * 40})
        if '/contents/' in url:
            rel = urllib.parse.unquote(url.split('/contents/', 1)[1]
                                       .split('?', 1)[0])
            if rel not in self._held():
                raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)
            return Response({'content': base64.b64encode(
                self._held()[rel].encode('utf-8')).decode('ascii'),
                'encoding': 'base64'})
        if '/git/ref/heads/' in url:
            return Response({'object': {'sha': self.head}})
        if '/git/commits/' in url and method == 'GET':
            return Response({'tree': {'sha': 't' * 40}})
        if url.endswith('/trees'):
            self.trees += 1
            if self.trees <= self.refuse_trees:
                raise urllib.error.HTTPError(
                    url, self.refuse_status, 'Refused',
                    self.refuse_headers, None)
            return Response({'sha': 'n' * 40})
        if url.endswith('/commits') and method == 'POST':
            return Response({'sha': 'c' * 40})
        if '/git/refs/heads/' in url and method == 'PATCH':
            self.patched += 1
            if self.patched <= self.fail_patch:
                raise urllib.error.HTTPError(url, 422, 'Unprocessable', {},
                                             None)
            return Response({'object': {'sha': 'c' * 40}})
        raise AssertionError('no answer for %s %s' % (method, url))

    def _azure(self, method, url, body):
        if '/refs?' in url:
            return Response({'value': [{'objectId': self.head}]})
        if '/items?' in url:
            rel = urllib.parse.unquote(url.split('path=', 1)[1]
                                       .split('&', 1)[0]).lstrip('/')
            if rel not in self._held():
                raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)
            return Response({'content': self._held()[rel]})
        if '/pushes?' in url:
            self.patched += 1
            if self.patched <= self.fail_patch:
                raise urllib.error.HTTPError(url, 409, 'Conflict', {}, None)
            return Response({'commits': [{'commitId': 'c' * 40}]})
        raise AssertionError('no answer for %s %s' % (method, url))

    def urls(self, method=None):
        return [url for verb, url, _ in self.calls
                if method is None or verb == method]

    def body_for(self, needle, method=None):
        for verb, url, body in self.calls:
            if needle in url and (method is None or verb == method):
                return body
        raise AssertionError('no call matching %r' % needle)


@pytest.fixture
def project(tmp_path):
    return make_repo(tmp_path / 'project')


@pytest.fixture
def github_env(monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'acme/widgets')
    monkeypatch.setenv('GITHUB_TOKEN', 'a-token')
    monkeypatch.setenv('GITHUB_REF_NAME', 'main')
    monkeypatch.delenv('GITHUB_HEAD_REF', raising=False)
    monkeypatch.delenv('GITHUB_REF', raising=False)
    monkeypatch.delenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', raising=False)
    _no_workspace(monkeypatch)


@pytest.fixture
def azure_env(monkeypatch):
    monkeypatch.setenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI',
                       'https://dev.azure.com/acme/')
    monkeypatch.setenv('SYSTEM_ACCESSTOKEN', 'a-token')
    monkeypatch.setenv('SYSTEM_TEAMPROJECT', 'widgets')
    monkeypatch.setenv('BUILD_REPOSITORY_ID', 'repo-id')
    _no_workspace(monkeypatch)
    monkeypatch.setenv('BUILD_SOURCEBRANCHNAME', 'main')
    monkeypatch.delenv('BUILD_SOURCEBRANCH', raising=False)
    # An Azure build reads no GitHub variable. The run this suite runs inside
    # may itself be a GitHub Actions job, whose GITHUB_REF_NAME would
    # otherwise name the branch this fixture is here to decide.
    for name in ('GITHUB_REPOSITORY', 'GITHUB_REF_NAME', 'GITHUB_HEAD_REF',
                 'GITHUB_REF'):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# The CI commit, through the git host's API
# ---------------------------------------------------------------------------

# purlin: host PROOF-5
def test_the_ci_commit_sends_five_requests_read_read_tree_commit_move(
        project, github_env, monkeypatch):
    """`acme/widgets` on `main`: read `main`, read its head commit, create one
    tree, create the commit, move `main`; no blob, and the sha comes back.

    The file's text travels in the tree request, so it costs no request of
    its own.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert [verb for verb, _url, _body in host.calls] == [
        'GET', 'GET', 'POST', 'POST', 'PATCH']
    assert all(url.startswith('https://api.github.com/repos/acme/widgets/git/')
               for url in host.urls()), host.urls()
    order = [url.rsplit('/git/', 1)[-1].split('?')[0] for url in host.urls()]
    assert order == ['ref/heads/main', 'commits/' + '1' * 40,
                     'trees', 'commits', 'refs/heads/main']
    assert [url for url in host.urls() if url.endswith('/blobs')] == []


# purlin: host PROOF-54
def test_the_commit_request_carries_exactly_message_tree_and_parents(
        project, github_env, monkeypatch):
    """No `author` and no `committer`: the commit is the git host's, so the
    git host signs it."""
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    body = host.body_for('/git/commits', method='POST')
    assert set(body) == {'message', 'tree', 'parents'}
    assert 'author' not in body and 'committer' not in body


# ---------------------------------------------------------------------------
# The pause the git host asks for
# ---------------------------------------------------------------------------

class _RecordedTime(object):
    """The `time` module as `host.py` sees it, with `sleep` captured.

    Every other attribute is the real module's, so `time.time()` still reads
    the clock the reset header is measured against.
    """

    def __init__(self, waits):
        self.sleep = waits.append

    def __getattr__(self, name):
        return getattr(time, name)


@pytest.fixture
def slept(monkeypatch):
    """Every wait `host.py` takes, captured rather than waited out.

    The stand-in replaces the `time` name in the module whose functions run,
    found through a function's own `__module__`, rather than `time.sleep`
    itself: patching the shared `time` module would also record any other
    sleep in this process, and a module loaded under its path name,
    `scripts.run.host`, is a second copy beside the `host` imported here.
    """
    waits = []
    stand_in = _RecordedTime(waits)
    running = sys.modules[host_module._api.__module__]
    for module in {id(host_module): host_module,
                   id(running): running}.values():
        monkeypatch.setattr(module, 'time', stand_in)
    return waits


# purlin: host PROOF-22
def test_a_403_with_retry_after_1_waits_1_second_says_so_and_sends_again(
        project, github_env, monkeypatch, slept, capsys):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '1'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert host.trees == 2, 'the refused tree request was not sent again'
    assert slept == [1.0]
    assert capsys.readouterr().out.splitlines() == [
        'The git host asked for a pause of 1 s.']


# purlin: host PROOF-91
def test_a_retry_after_of_900_seconds_waits_exactly_120(
        project, github_env, monkeypatch, slept):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '900'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert slept == [120.0]


# purlin: host PROOF-94
def test_a_403_naming_no_wait_sends_1_tree_request_and_stops_with_403(
        project, github_env, monkeypatch, slept):
    """A 403 with no header saying how long to wait is a real refusal."""
    host = FakeHost(refuse_trees=99)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 403
    assert host.trees == 1, 'a refusal that asked for no pause was retried'
    assert slept == []


# purlin: host PROOF-58
def test_every_move_refused_with_422_sends_exactly_3_moves_then_stops(
        project, github_env, monkeypatch):
    host = FakeHost(fail_patch=99)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 422
    moves = [url for verb, url, _body in host.calls if verb == 'PATCH']
    assert len(moves) == 3 and host.patched == 3, moves


NO_GITHUB_VARIABLES = ('No GITHUB_REPOSITORY and GITHUB_TOKEN, so no evidence '
                       'was committed.')


def _commit_with_one_variable(project, monkeypatch, capsys, present,
                              missing):
    """A CI commit on GitHub with `present` set and `missing` not set.

    Answers `(the sha, the requests sent, the lines printed)`; an error the
    commit raised fails the test that called it.
    """
    monkeypatch.setenv(present[0], present[1])
    monkeypatch.delenv(missing, raising=False)
    monkeypatch.delenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', raising=False)
    _no_workspace(monkeypatch)
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)
    capsys.readouterr()
    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')
    return sha, host.calls, capsys.readouterr().out.splitlines()


# purlin: host PROOF-7
def test_acme_widgets_with_no_token_sends_nothing_and_says_so(
        project, monkeypatch, capsys):
    """No request, no error raised, no sha, and exactly the one line."""
    sha, calls, printed = _commit_with_one_variable(
        project, monkeypatch, capsys, ('GITHUB_REPOSITORY', 'acme/widgets'),
        'GITHUB_TOKEN')

    assert sha == ''
    assert calls == [], 'a run with no token sent a request'
    assert printed == [NO_GITHUB_VARIABLES], printed


# purlin: host PROOF-127
def test_no_azure_token_writes_no_commit(project, azure_env, monkeypatch,
                                        capsys):
    monkeypatch.delenv('SYSTEM_ACCESSTOKEN', raising=False)
    host = FakeHost(azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)
    capsys.readouterr()

    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')

    assert sha == ''
    assert host.calls == [], 'a run with no token sent a request'
    assert capsys.readouterr().out.splitlines() == [
        'No Azure DevOps build variables, so no evidence was committed.']


# purlin: host PROOF-8
def test_one_azure_push_names_main_its_object_id_and_one_add_as_rawtext(
        project, azure_env, monkeypatch):
    host = FakeHost(azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert host.urls() and all(
        url.startswith('https://dev.azure.com/acme/widgets/_apis/git/')
        for url in host.urls()), host.urls()
    pushes = [body for verb, url, body in host.calls
              if verb == 'POST' and '/pushes?' in url]
    assert len(pushes) == 1, pushes
    body = pushes[0]
    assert body['refUpdates'] == [{'name': 'refs/heads/main',
                                   'oldObjectId': '1' * 40}]
    assert len(body['commits'][0]['changes']) == 1
    change = body['commits'][0]['changes'][0]
    assert change['changeType'] == 'add'
    assert change['item']['path'] == '/' + path
    assert change['newContent']['contentType'] == 'rawtext'
    with open(os.path.join(project, *path.split('/')), encoding='utf-8') as handle:
        assert change['newContent']['content'] == handle.read()


# purlin: host PROOF-52
def test_the_azure_push_names_the_whole_run_branch(project, azure_env,
                                                   monkeypatch):
    """Azure DevOps puts only a ref's last part in `BUILD_SOURCEBRANCHNAME`."""
    monkeypatch.setenv('BUILD_SOURCEBRANCH', 'refs/heads/run/main-4f1c2ab')
    monkeypatch.setenv('BUILD_SOURCEBRANCHNAME', 'main-4f1c2ab')
    host = FakeHost(azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    pushes = [body for verb, url, body in host.calls
              if verb == 'POST' and '/pushes?' in url]
    assert len(pushes) == 1, pushes
    assert [update['name'] for update in pushes[0]['refUpdates']] == [
        'refs/heads/run/main-4f1c2ab']


# purlin: host PROOF-62
def test_a_file_the_branch_already_holds_is_one_change_an_edit(
        project, azure_env, monkeypatch):
    """The Pushes API refuses `add` for a path that exists.

    One file per feature is rewritten on every run, so after the first run
    every push of it is an edit, and which of the two is read off the branch.
    """
    path = write_ci(project)
    held = writer.dump(evidence_file(platforms={'windows': section()}))
    host = FakeHost(azure=True, files={path: held})
    monkeypatch.setattr(urllib.request, 'urlopen', host)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    changes = host.body_for('/pushes?', method='POST')['commits'][0][
        'changes']
    assert [change['changeType'] for change in changes] == ['edit'], changes


# ---------------------------------------------------------------------------
# Two runners, one file
# ---------------------------------------------------------------------------

def _linux_merge():
    return writer.merge_for_host('linux', {'greeting': ['RULE-1']})


# purlin: host PROOF-99
def test_a_refused_move_reads_the_file_twice_and_sends_linux_then_linux_and_macos(
        project, github_env, monkeypatch):
    """The branch moved because a macOS runner committed; its section stays."""
    path = write_ci(project)
    moved = writer.dump(evidence_file(platforms={'macos': section()}))
    host = FakeHost(fail_patch=1, files={}, files_after_retry={path: moved})
    monkeypatch.setattr(urllib.request, 'urlopen', host)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab',
                             _linux_merge())

    trees = [body for verb, url, body in host.calls
             if url.endswith('/trees') and verb == 'POST']
    assert len(trees) == 2
    first = json.loads(trees[0]['tree'][0]['content'])
    second = json.loads(trees[1]['tree'][0]['content'])
    assert sorted(first['platforms']) == ['linux']
    assert sorted(second['platforms']) == ['linux', 'macos']
    assert len([url for url in host.urls('GET') if '/contents/' in url]) == 2


# purlin: host PROOF-39
def test_a_push_refused_with_409_is_sent_again_as_an_edit_carrying_both(
        project, azure_env, monkeypatch):
    """The branch held no file; after the 409 it holds a `windows` section."""
    path = write_ci(project)
    moved = writer.dump(evidence_file(platforms={'windows': section()}))
    host = FakeHost(azure=True, fail_patch=1, files={},
                    files_after_retry={path: moved})
    monkeypatch.setattr(urllib.request, 'urlopen', host)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab',
                             _linux_merge())

    pushes = [body for verb, url, body in host.calls
              if '/pushes?' in url and verb == 'POST']
    assert len(pushes) == 2
    assert host.patched == 2
    first = pushes[0]['commits'][0]['changes'][0]
    second = pushes[1]['commits'][0]['changes'][0]
    assert first['changeType'] == 'add'
    assert second['changeType'] == 'edit'
    merged = json.loads(second['newContent']['content'])
    assert sorted(merged['platforms']) == ['linux', 'windows']


# purlin: host PROOF-100
def test_a_windows_section_carrying_rule_9_is_sent_with_rule_1_alone(
        project, github_env, monkeypatch):
    """The spec carries `RULE-1` alone, so the merge drops `RULE-9`."""
    path = write_ci(project)
    old = section()
    old['rules']['RULE-9'] = 'passed'
    held = writer.dump(evidence_file(platforms={'windows': old}))
    host = FakeHost(files={path: held})
    monkeypatch.setattr(urllib.request, 'urlopen', host)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab',
                             _linux_merge())

    sent = json.loads(host.body_for('/git/trees', method='POST')['tree'][0][
        'content'])
    assert sent['platforms']['windows']['rules'] == {'RULE-1': 'passed'}


# ---------------------------------------------------------------------------
# The workspace check
# ---------------------------------------------------------------------------

NOT_THE_WORKSPACE = ('%s is not the project root this job checked out, so no '
                     'evidence was committed.')


def _commit_under_a_workspace(project, monkeypatch, capsys, variable, folder,
                              azure=False):
    """A CI commit of one evidence file with `variable` naming `folder`.

    Answers `(the sha, the fake git host, the lines printed)`.
    """
    if variable:
        monkeypatch.setenv(variable, folder)
    host = FakeHost(azure=azure)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)
    capsys.readouterr()
    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')
    return sha, host, capsys.readouterr().out.splitlines()


# purlin: host PROOF-32
def test_another_github_workspace_sends_nothing_and_names_the_project(
        project, github_env, monkeypatch, tmp_path, capsys):
    """The API commit names the real repository, never the fixture's, so
    no request and no sha, and exactly the one line."""
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, 'GITHUB_WORKSPACE',
        str(tmp_path / 'the-checkout'))

    assert sha == ''
    assert host.urls() == []
    assert printed == [NOT_THE_WORKSPACE % project], printed


# purlin: host PROOF-96
def test_the_project_that_is_the_workspace_commits(project, github_env,
                                                   monkeypatch, capsys):
    """The workspace is spelled as this system spells folders, `\\` on Windows."""
    spelled_here = os.path.normpath(project)
    if os.name == 'nt':
        assert '\\' in spelled_here and '/' not in spelled_here, spelled_here
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, 'GITHUB_WORKSPACE', spelled_here)

    assert sha == 'c' * 40
    assert [url.rsplit('/git/', 1)[-1] for url in host.urls('POST')] == [
        'trees', 'commits']


# purlin: host PROOF-97
def test_another_azure_sources_directory_sends_nothing_and_names_the_project(
        project, azure_env, monkeypatch, tmp_path, capsys):
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, 'BUILD_SOURCESDIRECTORY',
        str(tmp_path / 'the-checkout'), azure=True)

    assert sha == ''
    assert host.urls() == []
    assert printed == [NOT_THE_WORKSPACE % project], printed


# ---------------------------------------------------------------------------
# Handing the run to the git host
# ---------------------------------------------------------------------------

NOT_COMMITTED = ('This checkout has changes that are not committed, so a run '
                 'would prove something other than what is here. Commit them, '
                 'then run purlin:test --remote again.')
GITHUB_ORIGIN = 'https://github.com/acme/widgets.git'
AZURE_ORIGIN = 'https://dev.azure.com/acme/widgets/_git/shop'
GITHUB_RUNNER = '.github/workflows/purlin.yml'
AZURE_RUNNER = 'purlin.azure-pipelines.yml'
# A spec with one proof tagged for Windows, which a macOS machine cannot prove.
WINDOWS_SPEC = """# Feature: greeting

> Scope: README.md

## Rules

- RULE-1: The project says what it is

## Proof

- PROOF-1 (RULE-1): The readme reads `the project` @env(windows)
"""


def _record_commands(monkeypatch, code=0):
    """Every command `--remote` starts to change something, kept and answered.

    Reads of the checkout still run against the real repository; a push, a
    watch, a pull and a delete are recorded here and never started.
    """
    started = []

    def record(root, argv, **_kw):
        started.append(list(argv))
        return code

    monkeypatch.setattr(remote_module, '_run', record)
    return started


def _with_origin(project, url, spec=None):
    """`project` with `origin` at `url` and, where given, a committed spec."""
    git(project, 'remote', 'add', 'origin', url)
    if spec:
        os.makedirs(os.path.join(project, 'specs', 'core'))
        with open(os.path.join(project, 'specs', 'core', 'greeting.md'), 'w',
                  encoding='utf-8') as handle:
            handle.write(spec)
        git(project, 'add', '-A')
        git(project, 'commit', '--quiet', '-m', 'the spec')
    return project


def _on_a_mac(monkeypatch):
    from purlin import evidence as evidence_module
    monkeypatch.setattr(evidence_module, 'host_os', lambda: 'macos')


def _gh_on_the_path(project, monkeypatch):
    """A stand-in `gh` ahead of the search path, which still finds git."""
    folder = os.path.join(os.path.dirname(project), 'with-gh')
    os.makedirs(folder, exist_ok=True)
    stand_in(folder, 'gh')
    monkeypatch.setenv('PATH', folder + os.pathsep + os.environ['PATH'])


# purlin: host PROOF-63
def test_one_uncommitted_file_exits_1_with_the_one_line_and_no_push(
        project, capsys, monkeypatch):
    """A run against a commit the tree no longer matches proves the wrong thing."""
    _with_origin(project, GITHUB_ORIGIN)
    with open(os.path.join(project, 'uncommitted.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write('x\n')
    started = _record_commands(monkeypatch)

    assert remote_module.run_remote(project) == 1
    assert capsys.readouterr().out.splitlines() == [NOT_COMMITTED]
    assert started == [], 'a tree with uncommitted changes started %r' % started


# purlin: host PROOF-53
def test_a_gitlab_origin_exits_1_with_the_one_line_and_pushes_nothing(
        project, monkeypatch, capsys):
    """The one process started is git reading `origin` back: no push."""
    _with_origin(project, 'https://gitlab.com/acme/widgets.git')
    started = []
    real = subprocess.run

    def recorded(argv, **kwargs):
        started.append(list(argv))
        return real(argv, **kwargs)
    monkeypatch.setattr(remote_module.subprocess, 'run', recorded)

    assert remote_module.run_remote(project) == 1
    printed = capsys.readouterr().out
    assert printed.splitlines() == [
        'purlin:test --remote needs a GitHub or Azure DevOps remote, and '
        'origin is neither. Set one with git remote set-url origin <url>, '
        'then run purlin:test --remote again.'], printed
    assert started == [['git', 'remote', 'get-url', 'origin']], started


# purlin: host PROOF-140
def test_on_a_mac_a_github_origin_with_no_runner_file_gets_one_and_no_push(
        project, monkeypatch, capsys):
    _with_origin(project, GITHUB_ORIGIN, WINDOWS_SPEC)
    git(project, 'checkout', '--quiet', '-b', 'feature-x')
    _on_a_mac(monkeypatch)
    _gh_on_the_path(project, monkeypatch)
    started = _record_commands(monkeypatch)

    assert remote_module.run_remote(project) == 0
    with open(os.path.join(project, *GITHUB_RUNNER.split('/')),
              encoding='utf-8') as handle:
        written = handle.read()
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == (
        'Purlin wrote .github/workflows/purlin.yml, the runner for GitHub, to '
        'run the proofs tagged for Windows:'), printed
    assert printed[1:-1] == written.splitlines()
    assert printed[-1] == ('Commit it and run: purlin:test --remote '
                           '--commit-runner'), printed
    assert 'os: [windows-latest]' in written
    assert started == [], 'a first --remote started %r' % started


# purlin: host PROOF-141
def test_on_a_mac_an_azure_origin_with_no_runner_file_gets_one_and_no_push(
        project, monkeypatch, capsys):
    _with_origin(project, AZURE_ORIGIN, WINDOWS_SPEC)
    git(project, 'checkout', '--quiet', '-b', 'feature-x')
    _on_a_mac(monkeypatch)
    started = _record_commands(monkeypatch)

    assert remote_module.run_remote(project) == 0
    assert os.path.isfile(os.path.join(project, AZURE_RUNNER))
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == (
        'Purlin wrote purlin.azure-pipelines.yml, the runner for Azure '
        'DevOps, to run the proofs tagged for Windows:'), printed
    assert started == [], 'a first --remote started %r' % started


class _CommitRunner(object):
    """The command line's answer for `--test --remote --commit-runner`."""
    commit_runner = True


# purlin: host PROOF-143
def test_commit_runner_commits_the_runner_file_alone_then_pushes(
        project, tmp_path, monkeypatch, capsys):
    """git runs for real against a bare repository standing in for GitHub,
    which a push reaches through `pushInsteadOf` and the pull by its path;
    `gh` is a stand-in that finds run 987 and watches it pass."""
    _with_origin(project, GITHUB_ORIGIN, WINDOWS_SPEC)
    bare = str(tmp_path / 'host.git')
    git(tmp_path, 'init', '--bare', '--quiet', bare)
    git(project, 'config', 'url.%s.pushInsteadOf' % bare, GITHUB_ORIGIN)
    git(project, 'checkout', '--quiet', '-b', 'feature-x')
    _on_a_mac(monkeypatch)
    remote_module.ensure_runner(project)
    _gh_on_the_path(project, monkeypatch)
    monkeypatch.setattr(remote_module, 'find_run', lambda *_a, **_k: '987')
    monkeypatch.setattr(remote_module, '_table',
                        lambda project_root: 'the status table')
    started = []
    real = remote_module._run

    def run(root, argv, **kwargs):
        started.append(list(argv))
        if argv[0] == 'gh':
            return 0
        if argv[:2] == ['git', 'pull']:
            argv = [bare if word == 'origin' else word for word in argv]
        return real(root, argv, **kwargs)
    monkeypatch.setattr(remote_module, '_run', run)
    before = git(project, 'rev-parse', 'HEAD').stdout.strip()
    capsys.readouterr()

    assert remote_module.run_remote(project, _CommitRunner()) == 0
    made = git(project, 'log', '--format=%H %s', before + '..HEAD').stdout
    assert [line.split(' ', 1)[1] for line in made.splitlines()] == [
        'ci: the Purlin runner for GitHub']
    commit = made.split()[0]
    assert git(project, 'show', '--format=', '--name-only',
               commit).stdout.split() == [GITHUB_RUNNER]
    printed = capsys.readouterr().out.splitlines()
    committed = ('Committed .github/workflows/purlin.yml, the runner for '
                 'GitHub.')
    pushing = 'Pushing feature-x as run/feature-x-%s.' % commit[:7]
    assert printed.index(committed) < printed.index(pushing), printed
    push = ['git', 'push', 'origin',
            'HEAD:refs/heads/run/feature-x-%s' % commit[:7]]
    assert [argv[:2] for argv in started][:2] == [['git', 'add'],
                                                   ['git', 'commit']]
    assert push in started and started.index(push) == 2, started


class FakeProcesses(object):
    """`subprocess.run` for `remote.py`: git and gh answer, and nothing runs.

    The branch is `feature-x`, HEAD is a fixed sha and `origin` is a GitHub
    URL. Every process other than those reads is kept in `started`, in order,
    with the directory it was started in.
    """

    def __init__(self, push=0, watch=0, run_id='987'):
        self.push = push
        self.watch = watch
        self.started = []
        self.cwds = []
        self.answer = '[{"databaseId": %s}]' % run_id

    def __call__(self, argv, cwd=None, capture_output=False, text=False,
                 timeout=None, env=None, stdin=None):
        argv = list(argv)
        if argv[:3] == ['git', 'rev-parse', '--abbrev-ref']:
            return subprocess.CompletedProcess(argv, 0, 'feature-x\n', '')
        if argv[:2] == ['git', 'rev-parse']:
            return subprocess.CompletedProcess(argv, 0, SHA + '\n', '')
        if argv[:3] == ['git', 'remote', 'get-url']:
            return subprocess.CompletedProcess(argv, 0, GITHUB_ORIGIN + '\n',
                                               '')
        if argv[:3] == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(argv, 0, '', '')
        if argv[:3] == ['gh', 'run', 'list']:
            return subprocess.CompletedProcess(argv, 0, self.answer, '')
        self.started.append(argv)
        self.cwds.append(cwd)
        code = 0
        if argv[:2] == ['git', 'push']:
            code = self.push
        elif argv[:1] == ['gh']:
            code = self.watch
        return subprocess.CompletedProcess(argv, code, '', '')


@pytest.fixture
def remote_run(monkeypatch, tmp_path, project):
    """Stand in for every process `run_remote` starts, with or without `gh`.

    The project already carries its runner file, so the run goes ahead.
    """
    os.makedirs(os.path.join(project, '.github', 'workflows'))
    with open(os.path.join(project, *GITHUB_RUNNER.split('/')), 'w',
              encoding='utf-8') as handle:
        handle.write('name: purlin\n')

    def arrange(push=0, watch=0, gh=True):
        folder = tmp_path / ('with-gh' if gh else 'without-gh')
        folder.mkdir()
        if gh:
            stand_in(folder, 'gh')
        monkeypatch.setenv('PATH', str(folder))
        fake = FakeProcesses(push=push, watch=watch)
        monkeypatch.setattr(remote_module.subprocess, 'run', fake)
        monkeypatch.setattr(remote_module, '_table',
                            lambda project_root: 'the status table')
        monkeypatch.setattr(remote_module.time, 'sleep', lambda seconds: None)
        return fake
    return arrange


SHA = '4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7'
RUN_BRANCH = 'run/feature-x-4f1c2ab'
PUSH = ['git', 'push', 'origin', 'HEAD:refs/heads/%s' % RUN_BRANCH]
WATCH = ['gh', 'run', 'watch', '987', '--exit-status']
PULL = ['git', 'pull', '--ff-only', 'origin', RUN_BRANCH]
DELETE = ['git', 'push', 'origin', '--delete', RUN_BRANCH]
NO_GH = ('purlin:test --remote waits for the run with the GitHub CLI, gh, '
         'which is not installed, so nothing was pushed. Install gh, then run '
         'purlin:test --remote again.')
FAILED_ON_HOST = ('The run failed on the git host. The table below is what '
                  'came back.')


# purlin: host PROOF-24
def test_a_green_run_pushes_watches_pulls_and_deletes(project, remote_run,
                                                      capsys):
    fake = remote_run()

    assert remote_module.run_remote(project) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    assert fake.cwds == [project] * 4
    printed = capsys.readouterr().out
    assert FAILED_ON_HOST not in printed
    assert printed.rstrip().endswith('the status table')


@pytest.mark.skipif(os.name != 'nt', reason='gh.cmd is found on Windows alone')
# purlin: host PROOF-117
def test_on_windows_gh_cmd_is_found_and_the_run_goes_round(project,
                                                           remote_run):
    fake = remote_run()
    assert os.path.basename(shutil.which('gh') or '').lower() == 'gh.cmd'

    assert remote_module.run_remote(project) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]


# purlin: host PROOF-139
def test_no_github_process_can_prompt(project, remote_run, monkeypatch):
    fake = remote_run()
    started = []

    def recorded(argv, **kwargs):
        started.append((list(argv), kwargs.get('stdin'),
                        (kwargs.get('env') or {}).get('GIT_TERMINAL_PROMPT')))
        return fake(argv, **kwargs)
    monkeypatch.setattr(remote_module.subprocess, 'run', recorded)

    assert remote_module.run_remote(project) == 0
    assert {argv[0] for argv, _, _ in started} == {'git', 'gh'}
    assert [argv for argv, stdin, prompt in started
            if stdin is not subprocess.DEVNULL or prompt != '0'] == []


# purlin: host PROOF-68
def test_a_red_run_still_pulls_and_prints_the_table(project, remote_run,
                                                    capsys):
    fake = remote_run(watch=1)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    printed = capsys.readouterr().out
    assert FAILED_ON_HOST in printed.splitlines()
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-71
def test_without_gh_the_run_is_neither_watched_nor_pulled(project, remote_run,
                                                          capsys):
    """Checked before the push, so nothing is left on the git host."""
    fake = remote_run(gh=False)

    assert remote_module.run_remote(project) == 1
    assert fake.started == []
    assert capsys.readouterr().out.splitlines() == [NO_GH]


# ---------------------------------------------------------------------------
# Where a CI run commits
# ---------------------------------------------------------------------------

# purlin: host PROOF-101
def test_github_ref_name_run_main_4f1c2ab_is_a_run_that_commits(
        project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'run/main-4f1c2ab')
    assert host_module.commits_here(project) is True


# purlin: host PROOF-107
def test_a_run_on_topic_says_it_is_not_a_run_branch(
        project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'topic')
    assert host_module.commits_here(project) is False
    assert host_module.no_commit_line(project) == (
        'This run is on topic, which is not a run branch: the tests ran and '
        'nothing is written.')


# purlin: host PROOF-105
def test_the_whole_azure_ref_run_main_4f1c2ab_is_read_so_the_run_commits(
        project, monkeypatch, azure_env):
    """`BUILD_SOURCEBRANCHNAME` carries only `main-4f1c2ab`."""
    monkeypatch.setenv('BUILD_SOURCEBRANCHNAME', 'main-4f1c2ab')
    monkeypatch.setenv('BUILD_SOURCEBRANCH', 'refs/heads/run/main-4f1c2ab')
    assert host_module.commits_here(project) is True


# ---------------------------------------------------------------------------
# A commit with no branch named
# ---------------------------------------------------------------------------

# purlin: host PROOF-106
def test_a_commit_with_no_branch_named_sends_nothing(project, github_env,
                                                     monkeypatch, capsys):
    """Nothing names the branch, so nothing is guessed and nothing is sent."""
    for name in ('GITHUB_REF_NAME', 'BUILD_SOURCEBRANCH',
                 'BUILD_SOURCEBRANCHNAME'):
        monkeypatch.delenv(name, raising=False)
    git(project, 'checkout', '--quiet',
        git(project, 'rev-parse', 'HEAD').stdout.strip())
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)
    capsys.readouterr()

    sha = host_module.commit_files(project, [path],
                                   'purlin: evidence at 4f1c2ab')

    assert sha == ''
    assert host.calls == [], 'a commit with no branch sent %r' % host.calls
    assert capsys.readouterr().out.splitlines() == [
        'No branch could be read from the git host or from git, so the '
        'results were not committed.']


def teardown_module(module):
    """Leave nothing behind: every repository lived under pytest's tmp_path."""
    shutil.rmtree(os.path.join(DEV, '__pycache__'), ignore_errors=True)

