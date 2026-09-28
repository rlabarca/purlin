"""Tests for `scripts/run/host.py` and `scripts/mcp/purlin/provenance.py`.

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
*sources*     `ci` for a commit the git host made, which on GitHub is the
              committer `noreply@github.com` with the author
              `github-actions[bot]` and a signature that does not
              contradict it, and `local` for everything else: a file nobody
              committed, and a file somebody else committed
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

import ci as ci_module  # noqa: E402
import evidence as writer  # noqa: E402
import host as host_module  # noqa: E402
import remote as remote_module  # noqa: E402
from purlin import provenance  # noqa: E402

def _no_workspace(monkeypatch):
    """Take the job's own workspace out of a test's environment.

    Every fixture project here is a temporary directory, so on a runner it is
    never the workspace and the git host arms would refuse it, which is the
    behaviour RULE-26 and RULE-27 ask for and the wrong starting point for
    every other test in this file.
    """
    for variable in ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY'):
        monkeypatch.delenv(variable, raising=False)


ACTIONS_BOT = 'github-actions[bot]'
WEB_FLOW_EMAIL = 'noreply@github.com'
AZURE_BUILD = 'Project Collection Build Service'


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
    return {'schema': 'purlin-evidence/1', 'feature': feature,
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


def _commit_by_hand(root, message):
    """A person's own commit of whatever is in the tree."""
    git(root, 'add', '-A')
    git(root, 'commit', '--quiet', '-m', message)


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
    # An Azure build reads no GitHub variable. The run this suite runs inside
    # may itself be a GitHub Actions job, whose GITHUB_REF_NAME would
    # otherwise name the branch this fixture is here to decide.
    for name in ('GITHUB_REPOSITORY', 'GITHUB_REF_NAME', 'GITHUB_HEAD_REF'):
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

@pytest.mark.proof("host", "PROOF-5", "RULE-5")
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


@pytest.mark.proof("host", "PROOF-5", "RULE-5")
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


@pytest.mark.proof("host", "PROOF-5", "RULE-5")
def test_the_tree_entry_carries_the_file_and_its_permission(project,
                                                            github_env,
                                                            monkeypatch):
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    tree = host.body_for('/git/trees', method='POST')
    entry = tree['tree'][0]
    assert entry['path'] == path
    assert entry['type'] == 'blob'
    assert 'sha' not in entry, 'a text file asked for a blob of its own'
    assert entry[host_module._PERM_KEY] == host_module._FILE_PERM
    assert json.loads(entry['content'])['feature'] == 'greeting'


@pytest.mark.proof("host", "PROOF-5", "RULE-5")
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


@pytest.mark.proof("host", "PROOF-5", "RULE-5")
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


@pytest.mark.proof("host", "PROOF-22", "RULE-22")
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
    assert 'git host asked for a pause of 1 s' in capsys.readouterr().out


@pytest.mark.proof("host", "PROOF-22", "RULE-22")
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


@pytest.mark.proof("host", "PROOF-22", "RULE-22")
def test_a_pause_longer_than_the_cap_is_shortened_to_it(
        project, github_env, monkeypatch, slept):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '900'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert slept == [float(host_module.PAUSE_CAP_SECONDS)]
    assert host_module.PAUSE_CAP_SECONDS == 120


@pytest.mark.proof("host", "PROOF-22", "RULE-22")
def test_a_fourth_refusal_is_raised_with_its_status(project, github_env,
                                                    monkeypatch, slept):
    host = FakeHost(refuse_trees=99, refuse_headers={'Retry-After': '1'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 403
    assert '403' in str(raised.value)
    assert host.trees == host_module.PAUSE_RETRIES + 1
    assert len(slept) == host_module.PAUSE_RETRIES


@pytest.mark.proof("host", "PROOF-22", "RULE-22")
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


@pytest.mark.proof("host", "PROOF-22", "RULE-22")
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


@pytest.mark.proof("host", "PROOF-6", "RULE-6")
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


@pytest.mark.proof("host", "PROOF-6", "RULE-6")
def test_the_retry_gives_up_and_raises(project, github_env, monkeypatch):
    host = FakeHost(fail_patch=99)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    with pytest.raises(urllib.error.HTTPError) as raised:
        host_module.commit_files(project, [path], 'purlin: evidence at 4f1c2ab')

    assert raised.value.code == 422
    assert host.patched == host_module.REF_RETRIES


@pytest.mark.proof("host", "PROOF-6", "RULE-6")
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


@pytest.mark.proof("host", "PROOF-7", "RULE-7")
def test_no_token_writes_no_commit(project, monkeypatch, capsys):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'acme/widgets')
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    monkeypatch.delenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', raising=False)
    _no_workspace(monkeypatch)
    path = write_ci(project)

    assert host_module.commit_files(project, [path], 'x') == ''
    assert 'GITHUB_TOKEN' in capsys.readouterr().out


@pytest.mark.proof("host", "PROOF-8", "RULE-8")
def test_the_azure_push_sends_the_ref_and_the_content(project, azure_env,
                                                      monkeypatch):
    host = FakeHost(azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    sha = host_module.commit_files(project, [path],
                                        'purlin: evidence at 4f1c2ab')

    assert sha == 'c' * 40
    body = host.body_for('/pushes?', method='POST')
    assert body['refUpdates'] == [{'name': 'refs/heads/main',
                                   'oldObjectId': '1' * 40}]
    change = body['commits'][0]['changes'][0]
    assert change['changeType'] == 'add'
    assert change['item']['path'] == '/' + path
    assert change['newContent']['contentType'] == 'rawtext'
    assert json.loads(change['newContent']['content'])['feature'] == 'greeting'


@pytest.mark.proof("host", "PROOF-8", "RULE-8")
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


@pytest.mark.proof("host", "PROOF-8", "RULE-8")
def test_the_host_is_read_from_the_build_variables(github_env, azure_env):
    assert host_module.detect_host() == 'azure'


@pytest.mark.proof("host", "PROOF-8", "RULE-8")
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

    change = host.body_for('/pushes?', method='POST')['commits'][0][
        'changes'][0]
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


@pytest.mark.proof("host", "PROOF-36", "RULE-30")
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
    assert sent['platforms']['windows']['proofs'][0]['result'] == 'fail'
    assert sent['platforms']['linux'] == section()
    contents = [url for url in host.urls('GET') if '/contents/' in url]
    assert len(contents) == 1
    assert contents[0].endswith('ref=' + '1' * 40)


@pytest.mark.proof("host", "PROOF-36", "RULE-30")
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


@pytest.mark.proof("host", "PROOF-37", "RULE-30")
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


@pytest.mark.proof("host", "PROOF-36", "RULE-30")
def test_a_rule_the_spec_no_longer_has_is_dropped_in_the_merge(
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
# Who committed a ci/ file, read from git
# ---------------------------------------------------------------------------

@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_a_file_that_is_not_committed_is_local(project):
    path = write_ci(project)
    assert provenance.committed_by(project, path) == 'local'


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_a_persons_commit_is_local(project):
    path = write_ci(project)
    _commit_by_hand(project, 'purlin: evidence at 4f1c2ab')
    assert provenance.committed_by(project, path) == 'local'


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_the_azure_build_service_is_ci_without_a_signature(project):
    path = write_ci(project)
    git(project, 'add', '-A')
    git(project, '-c', 'user.name=' + AZURE_BUILD,
        '-c', 'user.email=build@example.com',
        'commit', '--quiet', '-m', 'purlin: evidence at 4f1c2ab')
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert provenance.committed_by(project, path) == 'ci'


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_a_signed_actions_commit_is_ci(project, tmp_path):
    """A signed commit by the git host's build identity is what counts.

    The signature is made with an ssh key generated here and trusted through
    an allowed-signers file, so `git log --format=%G?` prints `G` exactly as
    it does for a commit GitHub made through its API.
    """
    key = str(tmp_path / 'signing')
    made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                           '-C', ACTIONS_BOT, '-f', key],
                          capture_output=True, text=True)
    if made.returncode != 0:
        pytest.skip('ssh-keygen is not available: %s' % made.stderr.strip())

    with open(key + '.pub', encoding='utf-8') as handle:
        public = handle.read().strip()
    allowed = str(tmp_path / 'allowed_signers')
    with open(allowed, 'w', encoding='utf-8') as handle:
        handle.write('bot@example.com %s\n' % ' '.join(public.split()[:2]))

    path = write_ci(project)
    git(project, 'add', '-A')
    signed = subprocess.run(
        ['git', '-c', 'gpg.format=ssh', '-c', 'user.signingkey=' + key + '.pub',
         '-c', 'gpg.ssh.allowedSignersFile=' + allowed,
         '-c', 'user.name=' + ACTIONS_BOT, '-c', 'user.email=bot@example.com',
         'commit', '--quiet', '-S', '-m', 'purlin: evidence at 4f1c2ab'],
        cwd=project, capture_output=True, text=True)
    if signed.returncode != 0:
        pytest.skip('this git cannot sign with ssh: %s' % signed.stderr.strip())

    shown = subprocess.run(
        ['git', '-c', 'gpg.format=ssh',
         '-c', 'gpg.ssh.allowedSignersFile=' + allowed,
         'log', '-1', '--format=%G?\t%cn'],
        cwd=project, capture_output=True, text=True).stdout.strip()
    assert shown.startswith('G\t'), shown
    assert shown.endswith(ACTIONS_BOT)
    assert provenance.committed_by(project, path) == 'ci'


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_a_signature_this_checkout_cannot_check_is_still_ci(project, tmp_path,
                                                            monkeypatch):
    """`N` on a commit that carries a signature is a reader that cannot check.

    git prints `N` both for a commit with no signature and for one whose
    signature it could not even try to check, which an ssh signature is in
    any checkout with no allowed-signers file: a project CI writes evidence to
    has no reason to hold one. Reading that `N` as an unsigned commit throws
    away everything CI wrote on every machine that has gpg, so the commit
    object is asked whether a signature is there at all.
    """
    monkeypatch.setattr(provenance.shutil, 'which',
                        lambda name: '/usr/bin/gpg' if name == 'gpg' else None)
    key = str(tmp_path / 'signing')
    made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                           '-C', ACTIONS_BOT, '-f', key],
                          capture_output=True, text=True)
    if made.returncode != 0:
        pytest.skip('ssh-keygen is not available: %s' % made.stderr.strip())

    path = write_ci(project)
    git(project, 'add', '-A')
    signed = subprocess.run(
        ['git', '-c', 'gpg.format=ssh',
         '-c', 'user.signingkey=' + key + '.pub',
         '-c', 'user.name=' + ACTIONS_BOT, '-c', 'user.email=bot@example.com',
         'commit', '--quiet', '-S', '-m', 'purlin: evidence at 4f1c2ab'],
        cwd=project, capture_output=True, text=True)
    if signed.returncode != 0:
        pytest.skip('this git cannot sign with ssh: %s' % signed.stderr.strip())

    # No allowed-signers file is configured here, which is the ordinary state
    # of a checkout, so this is what any reader of this commit sees.
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert provenance.committed_by(project, path) == 'ci'


def _web_flow_commit(project, key=None, allowed=None):
    """Commit the way GitHub's API does: its web identity, the Actions author.

    GitHub signs the commit with its own key, records `GitHub
    <noreply@github.com>` as the committer and the Actions token as the
    author. `key` and `allowed` sign it here the way GitHub signs it there.
    """
    git(project, 'add', '-A')
    command = ['git']
    if key:
        command += ['-c', 'gpg.format=ssh', '-c', 'user.signingkey=' + key,
                    '-c', 'gpg.ssh.allowedSignersFile=' + allowed]
    command += ['-c', 'user.name=GitHub', '-c', 'user.email=' + WEB_FLOW_EMAIL,
                'commit', '--quiet',
                '--author=%s <41898282+github-actions[bot]@users.noreply.'
                'github.com>' % ACTIONS_BOT]
    if key:
        command.append('-S')
    command += ['-m', 'purlin: evidence at 4f1c2ab']
    return subprocess.run(command, cwd=project, capture_output=True, text=True)


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_the_web_flow_committer_with_a_good_signature_is_ci(project, tmp_path):
    """The identity GitHub's API actually writes, signed, is CI's.

    The committer is `GitHub <noreply@github.com>`, not the Actions bot, so a
    reader that looks only at the committer name calls this a person's commit
    and nothing CI wrote counts under `strong` or `signed`.
    """
    key = str(tmp_path / 'signing')
    made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                           '-C', ACTIONS_BOT, '-f', key],
                          capture_output=True, text=True)
    if made.returncode != 0:
        pytest.skip('ssh-keygen is not available: %s' % made.stderr.strip())
    with open(key + '.pub', encoding='utf-8') as handle:
        public = handle.read().strip()
    allowed = str(tmp_path / 'allowed_signers')
    with open(allowed, 'w', encoding='utf-8') as handle:
        handle.write('%s %s\n' % (WEB_FLOW_EMAIL,
                                  ' '.join(public.split()[:2])))

    path = write_ci(project)
    signed = _web_flow_commit(project, key + '.pub', allowed)
    if signed.returncode != 0:
        pytest.skip('this git cannot sign with ssh: %s' % signed.stderr.strip())

    shown = subprocess.run(
        ['git', '-c', 'gpg.format=ssh',
         '-c', 'gpg.ssh.allowedSignersFile=' + allowed,
         'log', '-1', '--format=%G?\t%cn\t%ce\t%an'],
        cwd=project, capture_output=True, text=True).stdout.strip()
    assert shown.startswith('G\t'), shown
    assert shown.endswith('\t%s\t%s' % (WEB_FLOW_EMAIL, ACTIONS_BOT)), shown
    assert provenance.committed_by(project, path) == 'ci'


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_the_web_flow_committer_is_ci_when_the_machine_has_no_gpg(project,
                                                                  monkeypatch):
    """git prints `N` when it cannot run gpg, which is not an unsigned commit.

    A checkout without gpg reports no signature for every commit, the git
    host's included. The commit is still the git host's, so the identity
    decides and the missing checker says nothing against it.
    """
    monkeypatch.setattr(provenance.shutil, 'which', lambda name: None)
    path = write_ci(project)
    assert _web_flow_commit(project).returncode == 0
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert provenance.committed_by(project, path) == 'ci'


@pytest.mark.proof("host", "PROOF-9", "RULE-9")
def test_the_web_flow_committer_with_no_signature_and_gpg_is_local(
        project, monkeypatch):
    """With gpg installed, `N` means the commit really carries no signature.

    Anyone can set those two names on a commit they make by hand. On a machine
    that can check, an unsigned commit claiming the git host's identity is read
    as a person's, so it never counts under `strong` or `signed`.
    """
    monkeypatch.setattr(provenance.shutil, 'which',
                        lambda name: '/usr/bin/gpg' if name == 'gpg' else None)
    path = write_ci(project)
    assert _web_flow_commit(project).returncode == 0
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert provenance.committed_by(project, path) == 'local'


# ---------------------------------------------------------------------------
# What a CI run publishes
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The workspace check
# ---------------------------------------------------------------------------

@pytest.mark.proof("host", "PROOF-30", "RULE-26")
def test_with_no_workspace_variable_every_project_is_its_own(monkeypatch):
    for variable in ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY'):
        monkeypatch.delenv(variable, raising=False)
    assert ci_module.is_the_workspace('/anywhere/at/all') is True


@pytest.mark.proof("host", "PROOF-32", "RULE-27")
def test_a_project_that_is_not_the_workspace_commits_nothing(
        project, github_env, monkeypatch, tmp_path, capsys):
    """The API commit names the real repository, never the fixture's.

    A fixture project that reached it would land its own evidence on the
    branch the job is reviewing.
    """
    monkeypatch.setenv('GITHUB_WORKSPACE', str(tmp_path / 'the-checkout'))
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = write_ci(project)

    assert host_module.commit_files(project, [path],
                                         'purlin: evidence at 4f1c2ab') == ''
    assert host.urls() == []
    assert 'no evidence was committed' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Handing the run to the git host
# ---------------------------------------------------------------------------

@pytest.mark.proof("host", "PROOF-12", "RULE-12")
def test_the_git_host_is_read_from_the_remote(project):
    git(project, 'remote', 'add', 'origin',
        'https://dev.azure.com/acme/widgets/_git/widgets')
    assert remote_module._host(project, None) == 'azure'
    git(project, 'remote', 'set-url', 'origin',
        'https://github.com/acme/widgets.git')
    assert remote_module._host(project, None) == 'github'


@pytest.mark.proof("host", "PROOF-12", "RULE-12")
def test_a_detached_head_has_nothing_to_push(project, capsys):
    head = git(project, 'rev-parse', 'HEAD').stdout.strip()
    git(project, 'checkout', '--quiet', head)
    assert remote_module.run_remote(project) == 1
    assert 'not on a branch' in capsys.readouterr().out


@pytest.mark.proof("host", "PROOF-12", "RULE-12")
def test_a_dirty_tree_is_refused_before_anything_is_pushed(project, capsys,
                                                           monkeypatch):
    """A run against a commit the tree no longer matches proves the wrong thing."""
    with open(os.path.join(project, 'uncommitted.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write('x\n')
    started = []
    monkeypatch.setattr(remote_module, '_run',
                        lambda root, argv, marked=False: started.append(argv))
    assert remote_module.run_remote(project) == 1
    printed = capsys.readouterr().out
    assert 'changes that are not committed' in printed
    assert started == []


@pytest.mark.proof("host", "PROOF-12", "RULE-12")
def test_the_run_branch_names_the_branch_and_the_commit(project):
    head = git(project, 'rev-parse', 'HEAD').stdout.strip()
    name = remote_module.run_branch_name(project, 'feature-x')
    assert name == 'run/feature-x-%s' % head[:7]


class FakeProcesses(object):
    """`subprocess.run` for `remote.py`: git and gh answer, and nothing runs.

    The branch is `feature-x`, HEAD is a fixed sha and `origin` is a GitHub
    URL. Every process other than those reads is kept in `started`, in order,
    with the directory it was started in and whether the push marker was in
    its environment.
    """

    def __init__(self, push=0, watch=0, run_id='987'):
        self.push = push
        self.watch = watch
        self.started = []
        self.cwds = []
        self.listed = []
        self.run_id_json = (
            '[{"databaseId": %s}]' % run_id if run_id else '[]')

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
        if argv[:3] == ['gh', 'run', 'list']:
            self.listed.append(argv)
            return subprocess.CompletedProcess(
                argv, 0, self.run_id_json, '')
        self.started.append(argv)
        self.cwds.append(cwd)
        code = 0
        if argv[:2] == ['git', 'push']:
            code = self.push
        elif argv[:1] == ['gh']:
            code = self.watch
        return subprocess.CompletedProcess(argv, code, '', '')


@pytest.fixture
def remote_run(monkeypatch, tmp_path):
    """Stand in for every process `run_remote` starts, with or without `gh`."""
    def arrange(push=0, watch=0, gh=True, run_id='987'):
        folder = tmp_path / ('with-gh' if gh else 'without-gh')
        folder.mkdir()
        if gh:
            (folder / 'gh').write_text('', encoding='utf-8')
        monkeypatch.setenv('PATH', str(folder))
        fake = FakeProcesses(push=push, watch=watch, run_id=run_id)
        monkeypatch.setattr(remote_module.subprocess, 'run', fake)
        monkeypatch.setattr(remote_module, '_table',
                            lambda project_root: 'the status table')
        # A run registers at once here, so no wait is spent on it.
        monkeypatch.setattr(remote_module.time, 'sleep', lambda _s: None)
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


class _Gate(object):
    """The one field `run_remote` reads off the resolved gate."""

    def __init__(self, gate):
        self.gate = gate


STRONG = _Gate('strong')


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_the_github_branch_pushes_watches_pulls_and_deletes(project,
                                                            remote_run,
                                                            capsys):
    fake = remote_run()

    assert remote_module.run_remote(project, cfg=STRONG) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    assert fake.cwds == [project] * 4
    printed = capsys.readouterr().out
    assert 'Pushing feature-x as %s.' % RUN_BRANCH in printed
    assert 'Waiting for the purlin.yml workflow on %s.' % RUN_BRANCH in printed
    assert 'finished red' not in printed
    assert printed.rstrip().endswith('the status table')


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_a_red_run_still_pulls_and_prints_the_table(project, remote_run,
                                                    capsys):
    fake = remote_run(watch=1)

    assert remote_module.run_remote(project, cfg=STRONG) == 1
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    printed = capsys.readouterr().out
    assert 'The run finished red. The table below is what came back.' in printed
    assert printed.rstrip().endswith('the status table')


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_at_passed_the_evidence_comes_home_too(project, remote_run):
    """At `passed` the runner commits its evidence, so the pull is the same."""
    fake = remote_run()

    assert remote_module.run_remote(project) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_without_gh_the_run_is_neither_watched_nor_pulled(project, remote_run,
                                                          capsys):
    fake = remote_run(gh=False)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH]
    printed = capsys.readouterr().out
    assert 'GitHub CLI `gh` is not installed' in printed
    assert 'the status table' not in printed


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_a_failed_push_starts_no_run(project, remote_run, capsys):
    fake = remote_run(push=1)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH]
    printed = capsys.readouterr().out
    assert 'The push failed, so no run was started.' in printed
    assert 'Waiting for' not in printed


# ---------------------------------------------------------------------------
# Where a CI run commits
# ---------------------------------------------------------------------------

def _off_a_runner(monkeypatch):
    for name in ('GITHUB_REPOSITORY', 'GITHUB_REF_NAME', 'GITHUB_HEAD_REF',
                 'GITHUB_BASE_REF', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI',
                 'SYSTEM_PULLREQUEST_PULLREQUESTID', 'BUILD_SOURCEBRANCH',
                 'BUILD_SOURCEBRANCHNAME'):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.proof("host", "PROOF-33", "RULE-28")
def test_off_a_runner_every_commit_is_the_persons_own(project, monkeypatch):
    _off_a_runner(monkeypatch)
    assert host_module.commits_here(project) is True


@pytest.mark.proof("host", "PROOF-33", "RULE-28")
def test_a_run_branch_commits(project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'run/main-4f1c2ab')
    assert host_module.commits_here(project) is True


@pytest.mark.proof("host", "PROOF-33", "RULE-28")
def test_any_other_branch_commits_nothing(project, monkeypatch, github_env):
    monkeypatch.setenv('GITHUB_REF_NAME', 'topic')
    assert host_module.commits_here(project) is False


@pytest.mark.proof("host", "PROOF-33", "RULE-28")
def test_a_tag_run_commits_nothing_and_says_so(project, monkeypatch,
                                              github_env):
    """A tag run is there to verify, so it has no evidence to add."""
    monkeypatch.setenv('GITHUB_REF', 'refs/tags/signed/0.10.0')
    monkeypatch.setenv('GITHUB_REF_NAME', 'signed/0.10.0')
    assert host_module.is_a_tag_run() is True
    assert host_module.commits_here(project) is False
    line = host_module.no_commit_line(project)
    assert line.startswith('Tag run: nothing is written.'), line


@pytest.mark.proof("host", "PROOF-33", "RULE-28")
def test_the_azure_ref_is_read_whole(project, monkeypatch, azure_env):
    """`BUILD_SOURCEBRANCHNAME` is a ref's last part, so `run/x` reaches it as `x`."""
    monkeypatch.setenv('BUILD_SOURCEBRANCHNAME', 'main-4f1c2ab')
    monkeypatch.delenv('BUILD_SOURCEBRANCH', raising=False)
    assert host_module.commits_here(project) is False
    monkeypatch.setenv('BUILD_SOURCEBRANCH', 'refs/heads/run/main-4f1c2ab')
    assert host_module.commits_here(project) is True


# ---------------------------------------------------------------------------
# The default branch
# ---------------------------------------------------------------------------

@pytest.mark.proof("host", "PROOF-21", "RULE-21")
def test_the_default_branch_is_what_origin_points_at(project):
    git(project, 'update-ref', 'refs/remotes/origin/trunk',
        git(project, 'rev-parse', 'HEAD').stdout.strip())
    git(project, 'symbolic-ref', 'refs/remotes/origin/HEAD',
        'refs/remotes/origin/trunk')
    assert host_module.default_branch(project) == 'trunk'


@pytest.mark.proof("host", "PROOF-21", "RULE-21")
def test_with_no_remote_the_default_branch_is_the_one_head_names(tmp_path):
    """A `master` repository is not told its signature is off the branch.

    A git configured for `master` makes one, and that repository has no
    `origin/HEAD` to read: answering `main` there sends the gate looking for a
    branch that does not exist and every signature reads as not on it.
    """
    root = str(tmp_path / 'no-remote')
    os.makedirs(root)
    git(root, '-c', 'init.defaultBranch=master', 'init', '--quiet')
    assert host_module.default_branch(root) == 'master'


@pytest.mark.proof("host", "PROOF-21", "RULE-21")
def test_a_detached_head_falls_back_to_main(project):
    git(project, 'checkout', '--quiet',
        git(project, 'rev-parse', 'HEAD').stdout.strip())
    assert host_module.default_branch(project) == 'main'


def teardown_module(module):
    """Leave nothing behind: every repository lived under pytest's tmp_path."""
    shutil.rmtree(os.path.join(DEV, '__pycache__'), ignore_errors=True)


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_the_run_is_looked_up_by_its_branch_before_it_is_watched(project,
                                                                 remote_run):
    """`gh run watch` with no id prompts and errors off a terminal."""
    fake = remote_run()

    assert remote_module.run_remote(project, cfg=STRONG) == 0
    assert fake.listed == [LIST]
    assert WATCH in fake.started


@pytest.mark.proof("host", "PROOF-24", "RULE-12")
def test_a_run_that_never_registers_is_reported_and_the_branch_deleted(
        project, remote_run, capsys):
    fake = remote_run(run_id='')

    assert remote_module.run_remote(project, cfg=STRONG) == 1
    assert fake.started == [PUSH, DELETE]
    printed = capsys.readouterr().out
    assert 'No run registered for %s' % RUN_BRANCH in printed
