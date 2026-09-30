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
# The remote a run branch is pushed to
# ---------------------------------------------------------------------------

@pytest.fixture
def with_remote(tmp_path, project):
    bare = str(tmp_path / 'origin.git')
    git(tmp_path, 'init', '--bare', '--quiet', '-b', 'main', bare)
    git(project, 'remote', 'add', 'origin', bare)
    git(project, 'push', '--quiet', '-u', 'origin', 'main')
    return bare


# ---------------------------------------------------------------------------
# The CI commit, through the git host's API
# ---------------------------------------------------------------------------

# purlin: host PROOF-5
def test_the_ci_commit_is_one_tree_then_commit_then_ref(project, github_env,
                                                        monkeypatch):
    """The file's text travels in the tree request, so it costs no request.

    A run over several hundred features would otherwise make one
    content-creating request per file, which is what the git host's limit on
    those counts.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                        'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    order = [url.rsplit('/git/', 1)[-1].split('?')[0] for url in host.urls()]
    assert order == ['ref/heads/main', 'commits/' + '1' * 40,
                     'trees', 'commits', 'refs/heads/main']
    assert [url for url in host.urls() if url.endswith('/blobs')] == []


# purlin: host PROOF-54
def test_the_ci_commit_sends_no_author_and_no_committer(project, github_env,
                                                        monkeypatch):
    """The commit is the git host's, so the git host signs it.

    Sending either field makes GitHub attribute the commit to that person and
    leave it unsigned, which is exactly the evidence that must not count.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    body = host.body_for('/git/commits', method='POST')
    assert set(body) == {'message', 'tree', 'parents'}
    assert 'author' not in body and 'committer' not in body


# purlin: host PROOF-55
# purlin: host PROOF-116
def test_the_tree_entry_carries_the_file_and_its_permission(project,
                                                            github_env,
                                                            monkeypatch):
    """The path is handed over as this system joins it, `\\` on Windows.

    The tree entry names it with `/` all the same, and its text is the bytes
    on disk, whatever line endings this system wrote them with.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)
    as_joined_here = os.path.join(*path.split('/'))

    host_module.commit_files(project, [as_joined_here],
                             'purlin: evidence at 4f1c2ab')

    tree = host.body_for('/git/trees', method='POST')
    entry = tree['tree'][0]
    assert entry['path'] == '.purlin/evidence/ci/greeting.json'
    assert entry['type'] == 'blob'
    assert 'sha' not in entry, 'a text file asked for a blob of its own'
    assert entry[host_module._PERM_KEY] == '100644'
    assert json.loads(entry['content'])['feature'] == 'greeting'
    with open(os.path.join(project, *path.split('/')), 'rb') as handle:
        on_disk = handle.read()
    assert entry['content'].encode('utf-8') == on_disk, \
        'the tree carried text other than the file on disk'


# purlin: host PROOF-56
def test_the_ci_commit_carries_every_file_in_one_tree(project, github_env,
                                                      monkeypatch):
    """One run covers many features, and one tree request carries them all."""
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    first = write_ci(project, 'greeting')
    second = write_ci(project, 'farewell',
                      {'linux': section(result='fail')})

    host_module.commit_files(project, [first, second],
                             'purlin: evidence at 4f1c2ab')

    tree = host.body_for('/git/trees', method='POST')
    assert [entry['path'] for entry in tree['tree']] == [first, second]
    assert json.loads(tree['tree'][0]['content'])['feature'] == 'greeting'
    assert json.loads(tree['tree'][1]['content'])['feature'] == 'farewell'
    assert [url for url in host.urls() if url.endswith('/blobs')] == [], \
        'two files that are all text asked for two blobs'


# purlin: host PROOF-57
def test_a_file_that_is_not_text_gets_a_blob_of_its_own(project, github_env,
                                                        monkeypatch):
    """Bytes that are not UTF-8 cannot travel inline, so they go as a blob.

    Nothing a run writes is such a file, but the tree request would be
    refused rather than carry one, so the branch has to exist.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)
    capture = '.purlin/runtime/greeting/PROOF-1.png'
    os.makedirs(os.path.join(project, '.purlin', 'runtime', 'greeting'))
    with open(os.path.join(project, *capture.split('/')), 'wb') as handle:
        handle.write(b'\x89PNG\r\n\x1a\n\xff\xfe')

    host_module.commit_files(project, [path, capture],
                                  'purlin: evidence at 4f1c2ab')

    blobs = [body for _verb, url, body in host.calls if url.endswith('/blobs')]
    assert len(blobs) == 1, 'only the file that is not text needs a blob'
    assert blobs[0]['encoding'] == 'base64'
    assert base64.b64decode(blobs[0]['content']) == b'\x89PNG\r\n\x1a\n\xff\xfe'
    tree = host.body_for('/git/trees', method='POST')
    assert 'content' in tree['tree'][0] and 'sha' not in tree['tree'][0]
    assert tree['tree'][1]['sha'] == 'b' * 40
    assert 'content' not in tree['tree'][1]


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
    sleep in this process, and under mutmut the module runs under its path
    name, `scripts.run.host`, as well as the `host` imported here.
    """
    waits = []
    stand_in = _RecordedTime(waits)
    running = sys.modules[host_module._api.__module__]
    for module in {id(host_module): host_module,
                   id(running): running}.values():
        monkeypatch.setattr(module, 'time', stand_in)
    return waits


# purlin: host PROOF-22
def test_a_refusal_that_asks_for_a_pause_is_waited_out_and_retried(
        project, github_env, monkeypatch, slept, capsys):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '1'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                        'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert host.trees == 2, 'the refused tree request was not sent again'
    assert slept == [1.0]
    assert 'The git host asked for a pause of 1 s.' in \
        capsys.readouterr().out.splitlines()


# purlin: host PROOF-90
def test_the_reset_time_is_read_when_there_is_no_retry_after(
        project, github_env, monkeypatch, slept):
    reset = str(int(time.time()) + 30)
    host = FakeHost(refuse_trees=1,
                    refuse_headers={'x-ratelimit-reset': reset})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert len(slept) == 1
    assert 25 <= slept[0] <= 30, slept


# purlin: host PROOF-91
def test_a_pause_longer_than_the_cap_is_shortened_to_it(
        project, github_env, monkeypatch, slept):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '900'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert slept == [120.0]


# purlin: host PROOF-93
def test_a_fourth_refusal_is_raised_with_its_status(project, github_env,
                                                    monkeypatch, slept):
    host = FakeHost(refuse_trees=99, refuse_headers={'Retry-After': '1'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 403
    assert '403' in str(raised.value)
    assert host.trees == 4
    assert slept == [1.0, 1.0, 1.0]


# purlin: host PROOF-94
def test_a_refusal_that_asks_for_no_pause_is_raised_at_once(
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


# purlin: host PROOF-92
def test_a_429_asking_for_a_pause_is_waited_out_too(project, github_env,
                                                    monkeypatch, slept):
    host = FakeHost(refuse_trees=1, refuse_status=429,
                    refuse_headers={'Retry-After': '2'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                        'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert slept == [2.0]


# purlin: host PROOF-6
def test_the_ref_update_is_retried_when_the_branch_moved(project, github_env,
                                                         monkeypatch):
    host = FakeHost(fail_patch=1)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                        'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert host.patched == 2, 'the refused update was not retried'
    heads = [url for url in host.urls('GET') if '/git/ref/heads/' in url]
    assert len(heads) == 2, 'the retry did not re-read the branch head'


# purlin: host PROOF-58
def test_the_retry_gives_up_and_raises(project, github_env, monkeypatch):
    host = FakeHost(fail_patch=99)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 422
    assert host.patched == 3


# purlin: host PROOF-59
def test_a_refusal_that_is_not_a_moved_branch_is_raised_at_once(
        project, github_env, monkeypatch):
    class Refusing(FakeHost):
        def _answer(self, method, url, body):
            if '/git/refs/heads/' in url and method == 'PATCH':
                self.patched += 1
                raise urllib.error.HTTPError(url, 403, 'Forbidden', {}, None)
            return FakeHost._answer(self, method, url, body)

    host = Refusing()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 403
    assert host.patched == 1, 'a refusal that is not a race was retried'


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
def test_no_token_writes_no_commit(project, monkeypatch, capsys):
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


# purlin: host PROOF-60
def test_no_repository_name_writes_no_commit(project, monkeypatch, capsys):
    sha, calls, printed = _commit_with_one_variable(
        project, monkeypatch, capsys, ('GITHUB_TOKEN', 'a-token'),
        'GITHUB_REPOSITORY')

    assert sha == ''
    assert calls == [], 'a run with no repository name sent a request'
    assert printed == [NO_GITHUB_VARIABLES], printed


# purlin: host PROOF-8
def test_the_azure_push_sends_the_ref_and_the_content(project, azure_env,
                                                      monkeypatch):
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
    assert json.loads(change['newContent']['content'])['feature'] == 'greeting'


# purlin: host PROOF-61
def test_the_azure_push_retries_when_the_object_id_is_stale(project, azure_env,
                                                            monkeypatch):
    host = FakeHost(fail_patch=1, azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                        'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    assert host.patched == 2
    assert len([url for url in host.urls('GET') if '/refs?' in url]) == 2


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
def test_a_file_the_branch_already_holds_is_pushed_as_an_edit(
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
    assert len(changes) == 1, changes
    change = changes[0]
    assert change['changeType'] == 'edit'
    assert host_module.azure_change('a.json', '{}', False)['changeType'] == \
        'add'
    assert host_module.azure_change('a.json', '{}', True)['changeType'] == \
        'edit'


# ---------------------------------------------------------------------------
# Two runners, one file
# ---------------------------------------------------------------------------

def _linux_merge():
    return writer.merge_for_host('linux', {'greeting': ['RULE-1']})


# purlin: host PROOF-38
def test_the_section_is_merged_into_what_the_branch_holds(
        project, github_env, monkeypatch):
    """A Windows runner committed first; the Linux runner keeps its section."""
    path = write_ci(project)
    held = writer.dump(evidence_file(
        platforms={'windows': section(result='fail', at='2026-09-13T11:00:00Z')}))
    host = FakeHost(files={path: held})
    monkeypatch.setattr(urllib.request, 'urlopen', host)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab',
                             _linux_merge())

    sent = json.loads(host.body_for('/git/trees', method='POST')['tree'][0][
        'content'])
    assert sorted(sent['platforms']) == ['linux', 'windows']
    assert sent['platforms']['windows'] == json.loads(held)['platforms'][
        'windows']
    assert sent['platforms']['windows']['proofs'][0]['result'] == 'fail'
    assert sent['platforms']['linux'] == section()
    contents = [url for url in host.urls('GET') if '/contents/' in url]
    assert len(contents) == 1
    assert contents[0].endswith('ref=' + '1' * 40)


# purlin: host PROOF-99
def test_a_retry_reads_the_file_again_at_the_new_parent(
        project, github_env, monkeypatch):
    """The branch moved because another runner committed; its section stays."""
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
def test_an_azure_retry_merges_and_turns_an_add_into_an_edit(
        project, azure_env, monkeypatch):
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
    first = pushes[0]['commits'][0]['changes'][0]
    second = pushes[1]['commits'][0]['changes'][0]
    assert first['changeType'] == 'add'
    assert second['changeType'] == 'edit'
    merged = json.loads(second['newContent']['content'])
    assert sorted(merged['platforms']) == ['linux', 'windows']


# purlin: host PROOF-100
def test_a_rule_the_spec_does_not_carry_is_dropped_in_the_merge(
        project, github_env, monkeypatch):
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


# purlin: host PROOF-30
def test_with_no_workspace_variable_every_project_is_its_own(
        project, github_env, monkeypatch, capsys):
    """Off a job's checkout nothing is refused: a person's own run commits."""
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, None, None)

    assert sha == 'c' * 40
    assert [url.rsplit('/git/', 1)[-1] for url in host.urls('POST')] == [
        'trees', 'commits']
    assert printed == []


# purlin: host PROOF-32
def test_a_project_that_is_not_the_workspace_commits_nothing(
        project, github_env, monkeypatch, tmp_path, capsys):
    """The API commit names the real repository, never the fixture's.

    A fixture project that reached it would land its own evidence on the
    branch the job is reviewing.
    """
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, 'GITHUB_WORKSPACE',
        str(tmp_path / 'the-checkout'))

    assert sha == ''
    assert host.urls() == []
    assert printed == [NOT_THE_WORKSPACE % project], printed


# purlin: host PROOF-96
# purlin: host PROOF-119
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
def test_an_azure_project_that_is_not_the_workspace_commits_nothing(
        project, azure_env, monkeypatch, tmp_path, capsys):
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, 'BUILD_SOURCESDIRECTORY',
        str(tmp_path / 'the-checkout'), azure=True)

    assert sha == ''
    assert host.urls() == []
    assert printed == [NOT_THE_WORKSPACE % project], printed


# purlin: host PROOF-98
def test_the_azure_project_that_is_the_workspace_pushes(project, azure_env,
                                                        monkeypatch, capsys):
    sha, host, printed = _commit_under_a_workspace(
        project, monkeypatch, capsys, 'BUILD_SOURCESDIRECTORY', project,
        azure=True)

    assert sha == 'c' * 40
    assert len([url for url in host.urls('POST') if '/pushes?' in url]) == 1


# ---------------------------------------------------------------------------
# Handing the run to the git host
# ---------------------------------------------------------------------------

NOT_ON_A_BRANCH = ('This checkout is not on a branch, so there is nothing to '
                   'push. Make one with git switch -c <name>, then run '
                   'purlin:test --remote again.')
NOT_COMMITTED = ('This checkout has changes that are not committed, so a run '
                 'would prove something other than what is here. Commit them, '
                 'then run purlin:test --remote again.')


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


# purlin: host PROOF-12
def test_a_detached_head_has_nothing_to_push(project, capsys, monkeypatch):
    head = git(project, 'rev-parse', 'HEAD').stdout.strip()
    git(project, 'checkout', '--quiet', head)
    started = _record_commands(monkeypatch)

    assert remote_module.run_remote(project) == 1
    assert capsys.readouterr().out.splitlines() == [NOT_ON_A_BRANCH]
    assert started == [], 'a detached HEAD started %r' % started


# purlin: host PROOF-63
def test_a_dirty_tree_is_refused_before_anything_is_pushed(project, capsys,
                                                           monkeypatch):
    """A run against a commit the tree no longer matches proves the wrong thing."""
    with open(os.path.join(project, 'uncommitted.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write('x\n')
    started = _record_commands(monkeypatch)

    assert remote_module.run_remote(project) == 1
    assert capsys.readouterr().out.splitlines() == [NOT_COMMITTED]
    assert started == [], 'a tree with uncommitted changes started %r' % started


# purlin: host PROOF-64
def test_the_run_branch_names_the_branch_and_the_commit(project, with_remote,
                                                        capsys, monkeypatch):
    """The push is recorded and answered as failed, so the run stops there.

    `origin` is a bare repository beside the project, so nothing here can
    reach a git host even if the push were started.
    """
    git(project, 'checkout', '--quiet', '-b', 'feature-x')
    head = git(project, 'rev-parse', 'HEAD').stdout.strip()
    run_branch = 'run/feature-x-%s' % head[:7]
    started = _record_commands(monkeypatch, code=1)
    # A stand-in `gh` ahead of the rest of the search path, which still finds
    # git; it is looked up and never started.
    folder = os.path.join(os.path.dirname(project), 'with-gh')
    os.makedirs(folder)
    stand_in(folder, 'gh')
    monkeypatch.setenv('PATH', folder + os.pathsep + os.environ['PATH'])

    assert remote_module.run_remote(project) == 1
    printed = capsys.readouterr().out.splitlines()
    assert 'Pushing feature-x as %s.' % run_branch in printed, printed
    assert started == [['git', 'push', 'origin',
                        'HEAD:refs/heads/%s' % run_branch]]


class FakeProcesses(object):
    """`subprocess.run` for `remote.py`: git and gh answer, and nothing runs.

    The branch is `feature-x`, HEAD is a fixed sha and `origin` is a GitHub
    URL. Every process other than those reads is kept in `started`, in order,
    with the directory it was started in; `log` holds the same with the
    lookups of the run in their place among them.
    """

    def __init__(self, push=0, watch=0, run_id='987', run_ids=None):
        self.push = push
        self.watch = watch
        self.started = []
        self.cwds = []
        self.listed = []
        self.log = []
        # `run_ids`, when given, is what each lookup answers in turn: `''` is
        # a run not registered yet.
        self.answers = [('[{"databaseId": %s}]' % one if one else '[]')
                        for one in (run_ids if run_ids is not None
                                    else [run_id])]

    def __call__(self, argv, cwd=None, capture_output=False, text=False,
                 timeout=None, env=None, stdin=None):
        argv = list(argv)
        if argv[:3] == ['git', 'rev-parse', '--abbrev-ref']:
            return subprocess.CompletedProcess(argv, 0, 'feature-x\n', '')
        if argv[:2] == ['git', 'rev-parse']:
            return subprocess.CompletedProcess(argv, 0, SHA + '\n', '')
        if argv[:3] == ['git', 'remote', 'get-url']:
            return subprocess.CompletedProcess(
                argv, 0, 'https://github.com/acme/widgets.git\n', '')
        if argv[:3] == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(argv, 0, '', '')
        self.log.append(argv)
        if argv[:3] == ['gh', 'run', 'list']:
            self.listed.append(argv)
            answer = (self.answers.pop(0) if len(self.answers) > 1
                      else self.answers[0])
            return subprocess.CompletedProcess(argv, 0, answer, '')
        self.started.append(argv)
        self.cwds.append(cwd)
        code = 0
        if argv[:2] == ['git', 'push']:
            code = self.push
        elif argv[:1] == ['gh']:
            code = self.watch
        return subprocess.CompletedProcess(argv, code, '', '')


class Clock(object):
    """`time.time` and `time.sleep` for `remote.py`: time moves on a sleep."""

    def __init__(self, waits):
        self.now = 1000.0
        self.waits = waits

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


@pytest.fixture
def remote_run(monkeypatch, tmp_path):
    """Stand in for every process `run_remote` starts, with or without `gh`."""
    def arrange(push=0, watch=0, gh=True, run_id='987', run_ids=None):
        folder = tmp_path / ('with-gh' if gh else 'without-gh')
        folder.mkdir()
        if gh:
            stand_in(folder, 'gh')
        monkeypatch.setenv('PATH', str(folder))
        fake = FakeProcesses(push=push, watch=watch, run_id=run_id,
                             run_ids=run_ids)
        monkeypatch.setattr(remote_module.subprocess, 'run', fake)
        monkeypatch.setattr(remote_module, '_table',
                            lambda project_root: 'the status table')
        # Every wait is recorded rather than spent, and the clock moves by it.
        fake.slept = []
        clock = Clock(fake.slept)
        monkeypatch.setattr(remote_module.time, 'time', clock.time)
        monkeypatch.setattr(remote_module.time, 'sleep', clock.sleep)
        return fake
    return arrange


SHA = '4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7'
RUN_BRANCH = 'run/feature-x-4f1c2ab'
PUSH = ['git', 'push', 'origin', 'HEAD:refs/heads/%s' % RUN_BRANCH]
WATCH = ['gh', 'run', 'watch', '987', '--exit-status']
LIST = ['gh', 'run', 'list', '--branch', RUN_BRANCH, '--limit', '1',
        '--json', 'databaseId']
PULL = ['git', 'pull', '--ff-only', 'origin', RUN_BRANCH]
DELETE = ['git', 'push', 'origin', '--delete', RUN_BRANCH]
NO_GH = ('purlin:test --remote waits for the run with the GitHub CLI, gh, '
         'which is not installed, so nothing was pushed. Install gh, then run '
         'purlin:test --remote again.')
NO_RUN = ('No run registered for %s within 60 seconds, so the run branch was '
          'deleted and nothing came back. Check that the git host runs '
          '.github/workflows/purlin.yml on a push to run/*, then run '
          'purlin:test --remote again.' % RUN_BRANCH)
FAILED_ON_HOST = ('The run failed on the git host. The table below is what '
                  'came back.')


# purlin: host PROOF-24
# purlin: host PROOF-117
def test_a_green_run_pushes_watches_pulls_and_deletes(project, remote_run,
                                                      capsys):
    fake = remote_run()
    found = os.path.basename(shutil.which('gh') or '').lower()
    assert found == ('gh.cmd' if os.name == 'nt' else 'gh'), found

    assert remote_module.run_remote(project) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    assert fake.cwds == [project] * 4
    printed = capsys.readouterr().out
    assert FAILED_ON_HOST not in printed
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-65
def test_a_green_run_says_what_it_pushed_and_what_it_waits_for(project,
                                                               remote_run,
                                                               capsys):
    remote_run()

    assert remote_module.run_remote(project) == 0
    printed = capsys.readouterr().out.splitlines()
    pushing = 'Pushing feature-x as %s.' % RUN_BRANCH
    waiting = 'Waiting for the purlin.yml workflow on %s.' % RUN_BRANCH
    assert pushing in printed and waiting in printed, printed
    assert printed.index(pushing) < printed.index(waiting)


# purlin: host PROOF-66
def test_the_run_is_looked_up_by_its_branch_before_it_is_watched(project,
                                                                 remote_run):
    """`gh run watch` with no id prompts and errors off a terminal."""
    fake = remote_run()

    assert remote_module.run_remote(project) == 0
    assert fake.listed == [LIST]
    assert fake.log == [PUSH, LIST, WATCH, PULL, DELETE]


def _green_at_gate(project, remote_run, gate):
    """A green GitHub run in a project whose settings name `gate`.

    The runner commits its evidence at every gate, so the pull is the same.
    Answers the processes started, in order.
    """
    os.makedirs(os.path.join(project, '.purlin'), exist_ok=True)
    with open(os.path.join(project, '.purlin', 'config.json'), 'w',
              encoding='utf-8') as handle:
        json.dump({'gate': gate, 'tests': []}, handle)
    fake = remote_run()

    assert remote_module.run_remote(project) == 0
    return fake.started


# purlin: host PROOF-67
def test_the_evidence_comes_home_at_the_gate_passed(project, remote_run):
    assert _green_at_gate(project, remote_run, 'passed') == [
        PUSH, WATCH, PULL, DELETE]


# purlin: host PROOF-109
def test_the_evidence_comes_home_at_the_gate_strong(project, remote_run):
    assert _green_at_gate(project, remote_run, 'strong') == [
        PUSH, WATCH, PULL, DELETE]


# purlin: host PROOF-110
def test_the_evidence_comes_home_at_the_gate_signed(project, remote_run):
    assert _green_at_gate(project, remote_run, 'signed') == [
        PUSH, WATCH, PULL, DELETE]


# purlin: host PROOF-68
def test_a_red_run_still_pulls_and_prints_the_table(project, remote_run,
                                                    capsys):
    fake = remote_run(watch=1)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    printed = capsys.readouterr().out
    assert FAILED_ON_HOST in printed.splitlines()
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-69
def test_the_lookup_is_asked_again_while_the_run_registers(project,
                                                          remote_run):
    """A run takes a few seconds to appear after the push."""
    fake = remote_run(run_ids=['', '', '987'])

    assert remote_module.run_remote(project) == 0
    assert fake.listed == [LIST, LIST, LIST]
    assert fake.slept == [3, 3]
    assert fake.started == [PUSH, WATCH, PULL, DELETE]


# purlin: host PROOF-70
def test_a_run_that_never_registers_is_reported_and_the_branch_deleted(
        project, remote_run, capsys):
    fake = remote_run(run_id='')

    assert remote_module.run_remote(project) == 1
    assert fake.listed == [LIST] * 21
    assert fake.slept == [3] * 20
    assert fake.started == [PUSH, DELETE]
    printed = capsys.readouterr().out.splitlines()
    assert NO_RUN in printed, printed
    assert 'the status table' not in printed


# purlin: host PROOF-71
def test_without_gh_the_run_is_neither_watched_nor_pulled(project, remote_run,
                                                          capsys):
    """Checked before the push, so nothing is left on the git host."""
    fake = remote_run(gh=False)

    assert remote_module.run_remote(project) == 1
    assert fake.started == []
    assert capsys.readouterr().out.splitlines() == [NO_GH]


# purlin: host PROOF-72
def test_a_failed_push_starts_no_run(project, remote_run, capsys):
    fake = remote_run(push=1)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH]
    assert fake.listed == []
    printed = capsys.readouterr().out
    assert ('The push failed, so no run was started. Check that git push '
            'origin works from this checkout, then run purlin:test --remote '
            'again.') in printed.splitlines()
    assert 'Waiting for' not in printed


# purlin: host PROOF-131
def test_a_run_branch_that_cannot_be_deleted_is_named_with_its_command(
        project, remote_run, capsys):
    """The run is brought home; only the delete of the run branch fails."""
    fake = remote_run()
    answer = fake.__call__

    def delete_refused(argv, **kwargs):
        done = answer(argv, **kwargs)
        if list(argv) == DELETE:
            return subprocess.CompletedProcess(argv, 1, '', '')
        return done
    remote_module.subprocess.run = delete_refused

    assert remote_module.run_remote(project) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    assert ('The run branch %s is still on origin. Delete it with: git push '
            'origin --delete %s' % (RUN_BRANCH, RUN_BRANCH)) in \
        capsys.readouterr().out.splitlines()


# purlin: host PROOF-132
def test_a_command_that_cannot_be_started_is_named_with_the_error(
        project, remote_run, capsys):
    """The push's program is not found, so the operating system's error is shown."""
    fake = remote_run()
    missing = FileNotFoundError(2, 'No such file or directory', 'git')

    def push_not_found(argv, **kwargs):
        if list(argv) == PUSH:
            raise missing
        return fake(argv, **kwargs)
    remote_module.subprocess.run = push_not_found

    assert remote_module.run_remote(project) == 1
    printed = capsys.readouterr().out.splitlines()
    failed = "git failed: [Errno 2] No such file or directory: 'git'"
    assert failed == 'git failed: %s' % missing
    assert printed[-2:] == [
        failed,
        'The push failed, so no run was started. Check that git push origin '
        'works from this checkout, then run purlin:test --remote again.'], \
        printed
    assert fake.started == []


# purlin: host PROOF-53
def test_a_project_whose_settings_say_ci_none_pushes_nothing(project,
                                                             monkeypatch,
                                                             capsys):
    os.makedirs(os.path.join(project, '.purlin'), exist_ok=True)
    with open(os.path.join(project, '.purlin', 'config.json'), 'w',
              encoding='utf-8') as handle:
        json.dump({'gate': 'passed', 'tests': [], 'ci': 'none'}, handle)
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'the settings')
    git(project, 'remote', 'add', 'origin',
        'https://github.com/acme/widgets.git')
    started = []
    monkeypatch.setattr(remote_module.subprocess, 'run',
                        lambda argv, **_kw: started.append(list(argv)))

    assert remote_module.run_remote(project) == 1
    printed = capsys.readouterr().out
    assert printed.splitlines() == [
        'purlin:test --remote needs a GitHub or Azure DevOps remote, and '
        '.purlin/config.json says ci: none. Add one with git remote add '
        'origin <url>, then run purlin:init.'], printed
    assert started == [], 'a project with ci: none started %r' % started


# purlin: host PROOF-108
def test_a_settings_file_that_cannot_be_read_pushes_nothing(project,
                                                           monkeypatch,
                                                           capsys):
    """A comma after the last entry, the mistake a hand edit makes most."""
    text = '{\n  "gate": "passed",\n  "ci": "github",\n}\n'
    os.makedirs(os.path.join(project, '.purlin'), exist_ok=True)
    with open(os.path.join(project, '.purlin', 'config.json'), 'w',
              encoding='utf-8') as handle:
        handle.write(text)
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'the settings')
    git(project, 'remote', 'add', 'origin',
        'https://github.com/acme/widgets.git')
    with pytest.raises(json.JSONDecodeError) as reader:
        json.loads(text)
    started = []
    monkeypatch.setattr(remote_module.subprocess, 'run',
                        lambda argv, **_kw: started.append(list(argv)))

    assert remote_module.run_remote(project) == 1
    printed = capsys.readouterr().out
    assert printed.splitlines() == [
        '.purlin/config.json cannot be read: %s at line %d. Fix the file by '
        'hand; nothing ran and nothing was saved.'
        % (reader.value.msg, reader.value.lineno)], printed
    assert started == [], 'an unreadable settings file started %r' % started


# ---------------------------------------------------------------------------
# Where a CI run commits
# ---------------------------------------------------------------------------

def _off_a_runner(monkeypatch):
    for name in ('GITHUB_REPOSITORY', 'GITHUB_REF_NAME', 'GITHUB_HEAD_REF',
                 'GITHUB_BASE_REF', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI',
                 'SYSTEM_PULLREQUEST_PULLREQUESTID', 'BUILD_SOURCEBRANCH',
                 'BUILD_SOURCEBRANCHNAME', 'GITHUB_REF'):
        monkeypatch.delenv(name, raising=False)


# purlin: host PROOF-33
def test_off_a_runner_every_commit_is_the_persons_own(project, monkeypatch):
    _off_a_runner(monkeypatch)
    assert host_module.commits_here(project) is True


# purlin: host PROOF-101
def test_a_run_branch_commits(project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'run/main-4f1c2ab')
    assert host_module.commits_here(project) is True


# purlin: host PROOF-102
def test_any_other_branch_commits_nothing(project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'topic')
    assert host_module.commits_here(project) is False


# purlin: host PROOF-103
def test_a_tag_run_commits_nothing_and_says_so(project, monkeypatch,
                                              github_env):
    """A tag run is there to verify, so it has no evidence to add."""
    monkeypatch.setenv('GITHUB_REF', 'refs/tags/signed/0.10.0')
    monkeypatch.setenv('GITHUB_REF_NAME', 'signed/0.10.0')
    assert host_module.commits_here(project) is False
    assert host_module.no_commit_line(project) == (
        'Tag run: nothing is written. This run reruns the tests on '
        'signed/0.10.0.')


# purlin: host PROOF-107
def test_any_other_branch_says_it_is_neither_a_run_branch_nor_a_tag(
        project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'topic')
    assert host_module.no_commit_line(project) == (
        'This run is on topic, which is neither a run branch nor a signed '
        'tag: the tests ran and nothing is written.')


# purlin: host PROOF-104
def test_the_last_part_of_an_azure_ref_alone_commits_nothing(project,
                                                            monkeypatch,
                                                            azure_env):
    """`BUILD_SOURCEBRANCHNAME` is a ref's last part, so `run/x` reaches it as `x`."""
    monkeypatch.setenv('BUILD_SOURCEBRANCHNAME', 'main-4f1c2ab')
    monkeypatch.delenv('BUILD_SOURCEBRANCH', raising=False)
    assert host_module.commits_here(project) is False


# purlin: host PROOF-105
def test_the_whole_azure_ref_is_read_first(project, monkeypatch, azure_env):
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

