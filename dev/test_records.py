"""Tests for `scripts/run/records.py`: naming, retention, committing, labels.

Every git host call is mocked at the HTTP boundary (`urllib.request.urlopen`),
and every git operation runs against a local repository with a local bare
repository as its remote. Nothing here reaches a network.

What each group proves:

*naming*      the file name carries the timestamp, the commit, the runner and
              the operating system, and the file's own fields agree with it
*retention*   three records per feature per operating system survive, another
              operating system's records are untouched, and a record an
              annotated `record/<name>` tag names is kept for ever
*developer*   a plain commit under the developer's identity, pushed when a
              remote and an upstream exist and explained when not
*ci*          one tree request carrying every file's text, then commit, then
              ref update, with no author and no committer field, retried
              when the branch moved and paused when the git host asks
*sources*     `ci` for a commit the git host made, which on GitHub is the
              committer `noreply@github.com` with the author
              `github-actions[bot]` and a signature that does not
              contradict it, `developer` for a person's, `local` for a
              file not committed
*publishing*  what a CI run puts where anyone else can read it: the pull
              request comment and the dashboard artifact
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
import urllib.request
from datetime import datetime

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import ci as ci_module  # noqa: E402
import records as records_module  # noqa: E402
import remote as remote_module  # noqa: E402
from purlin import records as reader  # noqa: E402

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


def record(feature='greeting', commit='4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7',
           status='pass'):
    return {
        'schema_version': 1,
        'feature': feature,
        'commit': commit,
        'gate': 'strong',
        'test_strength': 71,
        'scope_tree': 'a' * 40,
        'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': status,
                    'tier': 'unit', 'env': None,
                    'test_file': 'tests/test_greeting.py',
                    'test_name': 'test_greet'}],
    }


def put_record(root, feature, name, body=None):
    """Write a record file by name, bypassing `write_record`'s clock."""
    folder = os.path.join(root, reader.RECORDS_DIR, feature)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(body or record(feature), handle)
    return '%s/%s/%s' % (reader.RECORDS_DIR.replace(os.sep, '/'), feature, name)


def names(root, feature):
    folder = os.path.join(root, reader.RECORDS_DIR, feature)
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


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
                 refuse_trees=0, refuse_headers=None, refuse_status=403):
        self.calls = []
        self.fail_patch = fail_patch
        self.head = head
        self.azure = azure
        self.patched = 0
        self.refuse_trees = refuse_trees
        self.refuse_headers = refuse_headers or {}
        self.refuse_status = refuse_status
        self.trees = 0

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
    monkeypatch.delenv('GITHUB_EVENT_PATH', raising=False)
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
# Naming
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-1", "RULE-1")
def test_the_file_name_carries_the_run(project):
    when = datetime(2026, 9, 13, 12, 0, 0)
    name = records_module.record_filename(
        '4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1', 'ada@example.com', 'linux', when)
    assert name == '20260913T120000Z-4f1c2ab-ada-linux.json'
    parts = reader.record_name_parts(name)
    assert parts == ('20260913T120000Z', '4f1c2ab', 'ada', 'linux')


@pytest.mark.proof("records", "PROOF-1", "RULE-1")
def test_the_runner_slug_is_ci_or_the_email_local_part(project):
    when = datetime(2026, 9, 13, 12, 0, 0)
    assert records_module.record_filename('4f1c2ab', 'ci', None, when) == (
        '20260913T120000Z-4f1c2ab-ci.json')
    assert records_module.record_filename(
        '4f1c2ab', 'Rich.LaBarca+purlin@example.com', None, when) == (
        '20260913T120000Z-4f1c2ab-rich-labarca-purlin.json')


@pytest.mark.proof("records", "PROOF-1", "RULE-1")
def test_write_record_returns_a_path_the_reader_parses(project):
    path = records_module.write_record(project, record(), 'ada@example.com')
    assert path.startswith('.purlin/records/greeting/')
    assert reader.record_name_parts(os.path.basename(path)) is not None
    with open(os.path.join(project, path), encoding='utf-8') as handle:
        written = json.load(handle)
    assert written['runner'] == 'ada'
    assert written['os'] is None
    assert written['timestamp'].endswith('Z')
    assert written['feature'] == 'greeting'
    assert written['proofs'][0]['id'] == 'PROOF-1'


@pytest.mark.proof("records", "PROOF-1", "RULE-1")
def test_write_record_names_the_operating_system_of_a_matrix_job(project):
    path = records_module.write_record(project, record(), 'ci', 'windows')
    assert path.endswith('-ci-windows.json')
    with open(os.path.join(project, path), encoding='utf-8') as handle:
        assert json.load(handle)['os'] == 'windows'


@pytest.mark.proof("records", "PROOF-1", "RULE-1")
def test_write_record_does_not_mutate_what_the_run_handed_it(project):
    original = record()
    records_module.write_record(project, original, 'ada@example.com', 'linux')
    assert 'runner' not in original
    assert 'os' not in original


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-2", "RULE-2")
def test_retention_keeps_the_newest_three(project):
    for hour in range(6):
        put_record(project, 'greeting',
                   '2026091%dT120000Z-4f1c2ab-ci.json' % hour)
    records_module.prune(project, 'greeting')
    kept = names(project, 'greeting')
    assert len(kept) == 3
    assert kept == ['20260913T120000Z-4f1c2ab-ci.json',
                    '20260914T120000Z-4f1c2ab-ci.json',
                    '20260915T120000Z-4f1c2ab-ci.json']


@pytest.mark.proof("records", "PROOF-2", "RULE-2")
def test_retention_counts_each_operating_system_on_its_own(project):
    for day in range(5):
        put_record(project, 'greeting',
                   '2026091%dT120000Z-4f1c2ab-ci-linux.json' % day)
    for day in range(2):
        put_record(project, 'greeting',
                   '2026091%dT120000Z-4f1c2ab-ci-windows.json' % day)
    records_module.prune(project, 'greeting', 'linux')
    kept = names(project, 'greeting')
    assert len([n for n in kept if n.endswith('-linux.json')]) == 3
    assert len([n for n in kept if n.endswith('-windows.json')]) == 2


@pytest.mark.proof("records", "PROOF-2", "RULE-2")
def test_writing_prunes_as_it_goes(project):
    for _ in range(5):
        put_record(project, 'greeting',
                   '2026090%dT120000Z-4f1c2ab-ada.json' % len(
                       names(project, 'greeting')))
    records_module.write_record(project, record(), 'ada@example.com')
    assert len(names(project, 'greeting')) == 3


@pytest.mark.proof("records", "PROOF-3", "RULE-3")
def test_a_record_tag_keeps_the_records_its_message_names(project):
    oldest = put_record(project, 'greeting',
                        '20260101T120000Z-4f1c2ab-ci.json')
    for day in range(11, 16):
        put_record(project, 'greeting',
                   '202609%dT120000Z-4f1c2ab-ci.json' % day)
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'records')
    records_module.tag_record(project, '1.0', [oldest])

    assert records_module.tagged_paths(project) == {oldest}
    records_module.prune(project, 'greeting')
    kept = names(project, 'greeting')
    assert os.path.basename(oldest) in kept
    assert len(kept) == 4, 'the newest three plus the one the tag names'


@pytest.mark.proof("records", "PROOF-3", "RULE-3")
def test_the_record_tag_is_annotated_and_lists_every_path(project):
    first = put_record(project, 'greeting', '20260101T120000Z-4f1c2ab-ci.json')
    second = put_record(project, 'greeting', '20260102T120000Z-4f1c2ab-ci.json')
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'records')
    ref = records_module.tag_record(project, '1.0', [first, second])

    assert ref == 'record/1.0'
    kind = git(project, 'cat-file', '-t', 'record/1.0').stdout.strip()
    assert kind == 'tag', 'a lightweight tag carries no message to read'
    message = git(project, 'for-each-ref', '--format=%(contents)',
                  'refs/tags/record/').stdout
    assert first in message and second in message


@pytest.mark.proof("records", "PROOF-3", "RULE-3")
def test_tagged_paths_is_empty_outside_a_repository(tmp_path):
    assert records_module.tagged_paths(str(tmp_path)) == set()


# ---------------------------------------------------------------------------
# The developer's commit
# ---------------------------------------------------------------------------

@pytest.fixture
def with_remote(tmp_path, project):
    bare = str(tmp_path / 'origin.git')
    git(tmp_path, 'init', '--bare', '--quiet', '-b', 'main', bare)
    git(project, 'remote', 'add', 'origin', bare)
    git(project, 'push', '--quiet', '-u', 'origin', 'main')
    return bare


@pytest.mark.proof("records", "PROOF-4", "RULE-4")
def test_a_developer_commit_lands_and_pushes(project, with_remote):
    path = records_module.write_record(project, record(), 'ada@example.com')
    sha = records_module.commit_records(
        project, [path], 'developer', 'purlin: record for 4f1c2ab')

    assert len(sha) == 40
    subject = git(project, 'log', '-1', '--format=%s').stdout.strip()
    assert subject == 'purlin: record for 4f1c2ab'
    listed = git(with_remote, 'ls-tree', '-r', '--name-only', 'main').stdout
    assert path in listed, 'the record did not reach the remote'


@pytest.mark.proof("records", "PROOF-4", "RULE-4")
def test_a_developer_commit_carries_the_deletions_retention_made(
        project, with_remote):
    old = [put_record(project, 'greeting',
                      '2026091%dT120000Z-4f1c2ab-ada.json' % day)
           for day in range(5)]
    records_module.commit_records(project, old, 'developer', 'purlin: records')
    fresh = records_module.write_record(project, record(), 'ada@example.com')
    records_module.commit_records(project, [fresh], 'developer',
                                  'purlin: record')

    listed = git(with_remote, 'ls-tree', '-r', '--name-only', 'main').stdout
    assert fresh in listed
    assert old[0] not in listed, 'a pruned record stayed in the remote copy'


@pytest.mark.proof("records", "PROOF-4", "RULE-4")
def test_a_developer_commit_without_an_upstream_says_so(project, capsys):
    git(project, 'remote', 'add', 'origin', 'https://example.invalid/x.git')
    path = records_module.write_record(project, record(), 'ada@example.com')
    sha = records_module.commit_records(project, [path], 'developer',
                                        'purlin: record')
    printed = capsys.readouterr().out
    assert len(sha) == 40
    assert 'no upstream' in printed
    assert 'git push -u origin HEAD' in printed


@pytest.mark.proof("records", "PROOF-4", "RULE-4")
def test_a_developer_commit_without_a_remote_says_so(project, capsys):
    path = records_module.write_record(project, record(), 'ada@example.com')
    records_module.commit_records(project, [path], 'developer',
                                  'purlin: record')
    assert 'No remote is configured' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-4", "RULE-4")
def test_nothing_to_commit_is_said_and_not_an_error(project, capsys):
    path = records_module.write_record(project, record(), 'ada@example.com')
    records_module.commit_records(project, [path], 'developer', 'purlin: one')
    capsys.readouterr()
    sha = records_module.commit_records(project, [path], 'developer',
                                        'purlin: again')
    assert sha == ''
    assert 'Nothing to commit' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The CI commit, through the git host's API
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-5", "RULE-5")
def test_the_ci_commit_is_one_tree_then_commit_then_ref(project, github_env,
                                                        monkeypatch):
    """The file's text travels in the tree request, so it costs no request.

    A run that writes a record and several hundred briefs would otherwise
    make one content-creating request per file, which is what the git host's
    limit on those counts.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci', 'linux')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record for 4f1c2ab')

    assert sha == 'c' * 40
    order = [url.rsplit('/git/', 1)[-1].split('?')[0] for url in host.urls()]
    assert order == ['ref/heads/main', 'commits/' + '1' * 40,
                     'trees', 'commits', 'refs/heads/main']
    assert [url for url in host.urls() if url.endswith('/blobs')] == []


@pytest.mark.proof("records", "PROOF-5", "RULE-5")
def test_the_ci_commit_sends_no_author_and_no_committer(project, github_env,
                                                        monkeypatch):
    """The commit is the git host's, so the git host signs it.

    Sending either field makes GitHub attribute the commit to that person and
    leave it unsigned, which is exactly the record that must not count.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    records_module.commit_records(project, [path], 'ci', 'purlin: record')

    body = host.body_for('/git/commits', method='POST')
    assert set(body) == {'message', 'tree', 'parents'}
    assert 'author' not in body and 'committer' not in body


@pytest.mark.proof("records", "PROOF-5", "RULE-5")
def test_the_tree_entry_carries_the_file_and_its_permission(project,
                                                            github_env,
                                                            monkeypatch):
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    records_module.commit_records(project, [path], 'ci', 'purlin: record')

    tree = host.body_for('/git/trees', method='POST')
    entry = tree['tree'][0]
    assert entry['path'] == path
    assert entry['type'] == 'blob'
    assert 'sha' not in entry, 'a text file asked for a blob of its own'
    assert entry[records_module._PERM_KEY] == records_module._FILE_PERM
    assert json.loads(entry['content'])['feature'] == 'greeting'


@pytest.mark.proof("records", "PROOF-5", "RULE-5")
def test_the_ci_commit_carries_a_path_outside_the_records_directory(
        project, github_env, monkeypatch):
    """A CI run's briefs ride in the same commit as the record.

    A brief that stayed on the runner is evidence nobody can read, so the
    tree the commit names holds every path the run handed over and not only
    the ones under `.purlin/records/`.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')
    first = '.purlin/briefs/greeting/RULE-1.1a2b3c4d.brief.json'
    second = '.purlin/briefs/greeting/RULE-2.5e6f7a8b.brief.json'
    directory = os.path.join(project, '.purlin', 'briefs', 'greeting')
    os.makedirs(directory)
    for rel, text in ((first, '{"rule": "RULE-1", "settled": true}\n'),
                      (second, '{"rule": "RULE-2", "settled": false}\n')):
        with open(os.path.join(project, *rel.split('/')), 'w',
                  encoding='utf-8') as handle:
            handle.write(text)

    records_module.commit_records(project, [path, first, second], 'ci',
                                  'purlin: record for 4f1c2ab')

    tree = host.body_for('/git/trees', method='POST')
    paths = [entry['path'] for entry in tree['tree']]
    assert paths == [path, first, second]
    outside_the_records = [name for name in paths
                           if not name.startswith('.purlin/records/')]
    assert outside_the_records == [first, second]
    assert json.loads(tree['tree'][1]['content'])['settled'] is True
    assert json.loads(tree['tree'][2]['content'])['settled'] is False
    assert [url for url in host.urls() if url.endswith('/blobs')] == [], \
        'three files that are all text asked for three blobs'


@pytest.mark.proof("records", "PROOF-5", "RULE-5")
def test_a_file_that_is_not_text_gets_a_blob_of_its_own(project, github_env,
                                                        monkeypatch):
    """Bytes that are not UTF-8 cannot travel inline, so they go as a blob.

    Nothing an audit run writes is such a file, but the tree request would
    be refused rather than carry one, so the branch has to exist.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')
    capture = '.purlin/runtime/attachments/greeting/PROOF-1.png'
    os.makedirs(os.path.join(project, '.purlin', 'runtime', 'attachments',
                             'greeting'))
    with open(os.path.join(project, *capture.split('/')), 'wb') as handle:
        handle.write(b'\x89PNG\r\n\x1a\n\xff\xfe')

    records_module.commit_records(project, [path, capture], 'ci',
                                  'purlin: record for 4f1c2ab')

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
    """The `time` module as `records.py` sees it, with `sleep` captured.

    Every other attribute is the real module's, so `time.time()` still reads
    the clock the reset header is measured against.
    """

    def __init__(self, waits):
        self.sleep = waits.append

    def __getattr__(self, name):
        return getattr(time, name)


@pytest.fixture
def slept(monkeypatch):
    """Every wait `records.py` takes, captured rather than waited out.

    The stand-in replaces the `time` name in the module whose functions run,
    found through a function's own `__module__`, rather than `time.sleep`
    itself: patching the shared `time` module would also record any other
    sleep in this process, and under mutmut the module runs under its path
    name, `scripts.run.records`, as well as the `records` imported here.
    """
    waits = []
    stand_in = _RecordedTime(waits)
    running = sys.modules[records_module._api.__module__]
    for module in {id(records_module): records_module,
                   id(running): running}.values():
        monkeypatch.setattr(module, 'time', stand_in)
    return waits


@pytest.mark.proof("records", "PROOF-22", "RULE-22")
def test_a_refusal_that_asks_for_a_pause_is_waited_out_and_retried(
        project, github_env, monkeypatch, slept, capsys):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '1'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record')

    assert sha == 'c' * 40
    assert host.trees == 2, 'the refused tree request was not sent again'
    assert slept == [1.0]
    assert 'git host asked for a pause of 1 s' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-22", "RULE-22")
def test_the_reset_time_is_read_when_there_is_no_retry_after(
        project, github_env, monkeypatch, slept):
    reset = str(int(time.time()) + 30)
    host = FakeHost(refuse_trees=1,
                    refuse_headers={'x-ratelimit-reset': reset})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    records_module.commit_records(project, [path], 'ci', 'purlin: record')

    assert len(slept) == 1
    assert 25 <= slept[0] <= 30, slept


@pytest.mark.proof("records", "PROOF-22", "RULE-22")
def test_a_pause_longer_than_the_cap_is_shortened_to_it(
        project, github_env, monkeypatch, slept):
    host = FakeHost(refuse_trees=1, refuse_headers={'Retry-After': '900'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    records_module.commit_records(project, [path], 'ci', 'purlin: record')

    assert slept == [float(records_module.PAUSE_CAP_SECONDS)]
    assert records_module.PAUSE_CAP_SECONDS == 120


@pytest.mark.proof("records", "PROOF-22", "RULE-22")
def test_a_fourth_refusal_is_raised_with_its_status(project, github_env,
                                                    monkeypatch, slept):
    host = FakeHost(refuse_trees=99, refuse_headers={'Retry-After': '1'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    with pytest.raises(urllib.error.HTTPError) as raised:
        records_module.commit_records(project, [path], 'ci', 'purlin: record')

    assert raised.value.code == 403
    assert '403' in str(raised.value)
    assert host.trees == records_module.PAUSE_RETRIES + 1
    assert len(slept) == records_module.PAUSE_RETRIES


@pytest.mark.proof("records", "PROOF-22", "RULE-22")
def test_a_refusal_that_asks_for_no_pause_is_raised_at_once(
        project, github_env, monkeypatch, slept):
    """A 403 with no header saying how long to wait is a real refusal."""
    host = FakeHost(refuse_trees=99)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    with pytest.raises(urllib.error.HTTPError) as raised:
        records_module.commit_records(project, [path], 'ci', 'purlin: record')

    assert raised.value.code == 403
    assert host.trees == 1, 'a refusal that asked for no pause was retried'
    assert slept == []


@pytest.mark.proof("records", "PROOF-22", "RULE-22")
def test_a_429_asking_for_a_pause_is_waited_out_too(project, github_env,
                                                    monkeypatch, slept):
    host = FakeHost(refuse_trees=1, refuse_status=429,
                    refuse_headers={'Retry-After': '2'})
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record')

    assert sha == 'c' * 40
    assert slept == [2.0]


@pytest.mark.proof("records", "PROOF-6", "RULE-6")
def test_the_ref_update_is_retried_when_the_branch_moved(project, github_env,
                                                         monkeypatch):
    host = FakeHost(fail_patch=1)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record')

    assert sha == 'c' * 40
    assert host.patched == 2, 'the refused update was not retried'
    heads = [url for url in host.urls('GET') if '/git/ref/heads/' in url]
    assert len(heads) == 2, 'the retry did not re-read the branch head'


@pytest.mark.proof("records", "PROOF-6", "RULE-6")
def test_the_retry_gives_up_and_raises(project, github_env, monkeypatch):
    host = FakeHost(fail_patch=99)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    with pytest.raises(urllib.error.HTTPError) as raised:
        records_module.commit_records(project, [path], 'ci', 'purlin: record')

    assert raised.value.code == 422
    assert host.patched == records_module.REF_RETRIES


@pytest.mark.proof("records", "PROOF-6", "RULE-6")
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
    path = records_module.write_record(project, record(), 'ci')

    with pytest.raises(urllib.error.HTTPError) as raised:
        records_module.commit_records(project, [path], 'ci', 'purlin: record')

    assert raised.value.code == 403
    assert host.patched == 1, 'a refusal that is not a race was retried'


@pytest.mark.proof("records", "PROOF-7", "RULE-7")
def test_a_forked_pull_request_writes_no_commit(project, github_env,
                                                monkeypatch, tmp_path, capsys):
    event = tmp_path / 'event.json'
    with open(str(event), 'w', encoding='utf-8') as handle:
        json.dump({'pull_request': {'number': 7,
                                    'head': {'repo': {'fork': True}}}}, handle)
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record')

    assert sha == ''
    assert host.calls == [], 'a forked pull request reached the git host'
    assert 'fork' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-7", "RULE-7")
def test_no_token_writes_no_commit(project, monkeypatch, capsys):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'acme/widgets')
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    monkeypatch.delenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', raising=False)
    _no_workspace(monkeypatch)
    path = records_module.write_record(project, record(), 'ci')

    assert records_module.commit_records(project, [path], 'ci', 'x') == ''
    assert 'GITHUB_TOKEN' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-8", "RULE-8")
def test_the_azure_push_sends_the_ref_and_the_content(project, azure_env,
                                                      monkeypatch):
    host = FakeHost(azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record')

    assert sha == 'c' * 40
    body = host.body_for('/pushes?', method='POST')
    assert body['refUpdates'] == [{'name': 'refs/heads/main',
                                   'oldObjectId': '1' * 40}]
    change = body['commits'][0]['changes'][0]
    assert change['changeType'] == 'add'
    assert change['item']['path'] == '/' + path
    assert change['newContent']['contentType'] == 'rawtext'


@pytest.mark.proof("records", "PROOF-8", "RULE-8")
def test_the_azure_push_retries_when_the_object_id_is_stale(project, azure_env,
                                                            monkeypatch):
    host = FakeHost(fail_patch=1, azure=True)
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record')

    assert sha == 'c' * 40
    assert host.patched == 2
    assert len([url for url in host.urls('GET') if '/refs?' in url]) == 2


@pytest.mark.proof("records", "PROOF-8", "RULE-8")
def test_the_host_is_read_from_the_build_variables(github_env, azure_env):
    assert records_module.detect_host() == 'azure'


@pytest.mark.proof("records", "PROOF-8", "RULE-8")
def test_the_branch_is_the_pull_requests_head_when_there_is_one(
        project, github_env, monkeypatch):
    assert records_module.current_branch(project) == 'main'
    monkeypatch.setenv('GITHUB_HEAD_REF', 'feature/login')
    assert records_module.current_branch(project) == 'feature/login'


# ---------------------------------------------------------------------------
# The label, read from git
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_a_file_that_is_not_committed_is_local(project):
    path = records_module.write_record(project, record(), 'ada@example.com')
    assert records_module.record_label(project, path) == 'local'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_a_persons_commit_is_developer(project):
    path = records_module.write_record(project, record(), 'ada@example.com')
    records_module.commit_records(project, [path], 'developer',
                                  'purlin: record')
    assert records_module.record_label(project, path) == 'developer'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_the_azure_build_service_is_ci_without_a_signature(project):
    path = records_module.write_record(project, record(), 'ci')
    git(project, 'add', '-A')
    git(project, '-c', 'user.name=' + AZURE_BUILD,
        '-c', 'user.email=build@example.com',
        'commit', '--quiet', '-m', 'purlin: record for 4f1c2ab')
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert records_module.record_label(project, path) == 'ci'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
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

    path = records_module.write_record(project, record(), 'ci')
    git(project, 'add', '-A')
    signed = subprocess.run(
        ['git', '-c', 'gpg.format=ssh', '-c', 'user.signingkey=' + key + '.pub',
         '-c', 'gpg.ssh.allowedSignersFile=' + allowed,
         '-c', 'user.name=' + ACTIONS_BOT, '-c', 'user.email=bot@example.com',
         'commit', '--quiet', '-S', '-m', 'purlin: record for 4f1c2ab'],
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
    assert records_module.record_label(project, path) == 'ci'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_a_signature_this_checkout_cannot_check_is_still_ci(project, tmp_path,
                                                            monkeypatch):
    """`N` on a commit that carries a signature is a reader that cannot check.

    git prints `N` both for a commit with no signature and for one whose
    signature it could not even try to check, which an ssh signature is in
    any checkout with no allowed-signers file: a project CI writes records to
    has no reason to hold one. Reading that `N` as an unsigned commit throws
    away every record CI wrote on every machine that has gpg, so the commit
    object is asked whether a signature is there at all.
    """
    monkeypatch.setattr(reader.shutil, 'which',
                        lambda name: '/usr/bin/gpg' if name == 'gpg' else None)
    key = str(tmp_path / 'signing')
    made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                           '-C', ACTIONS_BOT, '-f', key],
                          capture_output=True, text=True)
    if made.returncode != 0:
        pytest.skip('ssh-keygen is not available: %s' % made.stderr.strip())

    path = records_module.write_record(project, record(), 'ci')
    git(project, 'add', '-A')
    signed = subprocess.run(
        ['git', '-c', 'gpg.format=ssh',
         '-c', 'user.signingkey=' + key + '.pub',
         '-c', 'user.name=' + ACTIONS_BOT, '-c', 'user.email=bot@example.com',
         'commit', '--quiet', '-S', '-m', 'purlin: record for 4f1c2ab'],
        cwd=project, capture_output=True, text=True)
    if signed.returncode != 0:
        pytest.skip('this git cannot sign with ssh: %s' % signed.stderr.strip())

    # No allowed-signers file is configured here, which is the ordinary state
    # of a checkout, so this is what any reader of this commit sees.
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert records_module.record_label(project, path) == 'ci'


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
    command += ['-m', 'purlin: record for 4f1c2ab']
    return subprocess.run(command, cwd=project, capture_output=True, text=True)


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_the_web_flow_committer_with_a_good_signature_is_ci(project, tmp_path):
    """The identity GitHub's API actually writes, signed, is a CI record.

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

    path = records_module.write_record(project, record(), 'ci')
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
    assert records_module.record_label(project, path) == 'ci'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_the_web_flow_committer_is_ci_when_the_machine_has_no_gpg(project,
                                                                  monkeypatch):
    """git prints `N` when it cannot run gpg, which is not an unsigned commit.

    A checkout without gpg reports no signature for every commit, the git
    host's included. The commit is still the git host's, so the identity
    decides and the missing checker says nothing against it.
    """
    monkeypatch.setattr(reader.shutil, 'which', lambda name: None)
    path = records_module.write_record(project, record(), 'ci')
    assert _web_flow_commit(project).returncode == 0
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert records_module.record_label(project, path) == 'ci'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_the_web_flow_committer_with_no_signature_and_gpg_is_a_person(
        project, monkeypatch):
    """With gpg installed, `N` means the commit really carries no signature.

    Anyone can set those two names on a commit they make by hand. On a machine
    that can check, an unsigned commit claiming the git host's identity is read
    as a person's, so it never counts under `strong` or `signed`.
    """
    monkeypatch.setattr(reader.shutil, 'which',
                        lambda name: '/usr/bin/gpg' if name == 'gpg' else None)
    path = records_module.write_record(project, record(), 'ci')
    assert _web_flow_commit(project).returncode == 0
    assert git(project, 'log', '-1', '--format=%G?').stdout.strip() in ('N', '')
    assert records_module.record_label(project, path) == 'developer'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_the_reader_is_reachable_through_this_module(project):
    path = records_module.write_record(project, record(), 'ada@example.com')
    records_module.commit_records(project, [path], 'developer', 'purlin: r')
    loaded = records_module.load_records(project)
    assert list(loaded) == ['greeting']
    entry = loaded['greeting'][None]
    assert entry['path'] == path
    assert entry['label'] == 'developer'
    assert entry['commit7'] == '4f1c2ab'


@pytest.mark.proof("records", "PROOF-9", "RULE-9")
def test_a_matrix_keeps_one_latest_record_per_operating_system(project):
    for name in ('linux', 'windows'):
        records_module.write_record(project, record(), 'ci', name)
    loaded = records_module.load_records(project)['greeting']
    assert sorted(k for k in loaded) == ['linux', 'windows']


def _put_text(root, feature, name, text):
    """Write a file under `.purlin/records/<feature>/` holding `text` as it is."""
    folder = os.path.join(root, reader.RECORDS_DIR, feature)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'w', encoding='utf-8') as handle:
        handle.write(text)


@pytest.mark.proof("records", "PROOF-25", "RULE-23")
def test_records_read_at_a_ref_come_out_of_git(project):
    name = '20260913T120000Z-4f1c2ab-ada.json'
    greeting = put_record(project, 'greeting', name)
    _put_text(project, 'broken', name, 'not json')
    _put_text(project, 'listed', name, '[1, 2]')
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'the records')
    put_record(project, 'farewell', '20260913T130000Z-4f1c2ab-ada.json',
               record('farewell'))
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'one more record')
    edited = record()
    edited['test_strength'] = 5
    put_record(project, 'greeting', name, edited)

    at_parent = records_module.load_records(project, 'HEAD~1')
    assert sorted(at_parent) == ['greeting'], at_parent
    entry = at_parent['greeting'][None]
    assert entry['test_strength'] == 71
    assert entry['label'] == 'developer'
    assert entry['path'] == greeting

    at_head = records_module.load_records(project, 'HEAD')
    assert sorted(at_head) == ['farewell', 'greeting'], at_head
    assert at_head['greeting'][None]['test_strength'] == 71
    # Without a ref the disk is read, and the disk holds the edit.
    assert records_module.load_records(project)['greeting'][None][
        'test_strength'] == 5

    assert records_module.load_records(project, 'no-such-ref') == {}


# ---------------------------------------------------------------------------
# What a CI run publishes
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-10", "RULE-10")
def test_the_comment_goes_to_the_pull_request_this_run_belongs_to(
        project, github_env, monkeypatch, tmp_path):
    event = tmp_path / 'event.json'
    with open(str(event), 'w', encoding='utf-8') as handle:
        json.dump({'pull_request': {'number': 12,
                                    'head': {'repo': {'fork': False}}}}, handle)
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    sent = []

    def urlopen(request, timeout=None):
        sent.append((request.full_url,
                     json.loads(request.data.decode('utf-8'))))
        return Response({})

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)

    assert ci_module.post_pr_comment(project, 'Purlin: 2 rules meet the gate.')
    url, body = sent[0]
    assert url.endswith('/repos/acme/widgets/issues/12/comments')
    assert body == {'body': 'Purlin: 2 rules meet the gate.'}


@pytest.mark.proof("records", "PROOF-10", "RULE-10")
def test_a_run_that_is_not_a_pull_request_posts_nothing(project, github_env,
                                                        capsys):
    assert ci_module.post_pr_comment(project, 'anything') is False
    assert 'not a pull request' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-10", "RULE-10")
def test_a_local_run_posts_nothing_and_is_not_an_error(project, monkeypatch,
                                                       capsys):
    monkeypatch.delenv('GITHUB_REPOSITORY', raising=False)
    monkeypatch.delenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', raising=False)
    _no_workspace(monkeypatch)
    assert ci_module.post_pr_comment(project, 'anything') is False
    assert 'Not running on a git host' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-10", "RULE-10")
def test_a_refused_comment_is_reported_rather_than_raised(project, github_env,
                                                          monkeypatch,
                                                          tmp_path, capsys):
    event = tmp_path / 'event.json'
    with open(str(event), 'w', encoding='utf-8') as handle:
        json.dump({'pull_request': {'number': 3, 'head': {'repo': {}}}}, handle)
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))

    def refuse(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 403, 'Forbidden', {},
                                     None)

    monkeypatch.setattr(urllib.request, 'urlopen', refuse)
    assert ci_module.post_pr_comment(project, 'anything') is False
    assert 'The comment was not posted' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The workspace check
# ---------------------------------------------------------------------------

@pytest.fixture
def pull_request_event(monkeypatch, tmp_path):
    """A pull request event on disk, so the run reads itself as number 12."""
    event = tmp_path / 'event.json'
    with open(str(event), 'w', encoding='utf-8') as handle:
        json.dump({'pull_request': {'number': 12,
                                    'head': {'repo': {'fork': False}}}}, handle)
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    return str(event)


@pytest.mark.proof("records", "PROOF-30", "RULE-26")
def test_a_project_that_is_not_the_workspace_posts_nothing(
        project, github_env, pull_request_event, monkeypatch, tmp_path,
        capsys):
    """A test suite driving an audit over a fixture must not speak for the job.

    The fixture inherits the runner's token, repository and pull request, so
    without this check every fixture project posts its own table to the pull
    request the job is reviewing.
    """
    monkeypatch.setenv('GITHUB_WORKSPACE', str(tmp_path / 'the-checkout'))

    def urlopen(request, timeout=None):
        raise AssertionError('a fixture project reached the git host')

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)

    assert ci_module.post_pr_comment(project, 'anything') is False
    assert 'is not the workspace this job checked out' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-30", "RULE-26")
def test_a_project_that_is_not_the_workspace_publishes_into_itself(
        project, github_env, monkeypatch, tmp_path):
    monkeypatch.setenv('GITHUB_WORKSPACE', str(tmp_path / 'the-checkout'))
    monkeypatch.setenv('RUNNER_TEMP', '/tmp/rt')

    assert ci_module.publish_dir(project) == os.path.join(
        project, '.purlin', 'runtime', 'report')


@pytest.mark.proof("records", "PROOF-30", "RULE-26")
def test_with_no_workspace_variable_every_project_is_its_own(monkeypatch):
    for variable in ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY'):
        monkeypatch.delenv(variable, raising=False)
    assert ci_module.is_the_workspace('/anywhere/at/all') is True


@pytest.mark.proof("records", "PROOF-31", "RULE-26")
def test_the_workspace_itself_still_posts_and_publishes(
        project, github_env, pull_request_event, monkeypatch, tmp_path):
    """The comparison is between real paths, not between the strings.

    A runner hands over a path that reaches the checkout through a symbolic
    link often enough that comparing the strings would refuse the job's own
    project.
    """
    linked = tmp_path / 'workspace-link'
    os.symlink(project, str(linked))
    monkeypatch.setenv('GITHUB_WORKSPACE', str(linked))
    monkeypatch.setenv('RUNNER_TEMP', '/tmp/rt')
    sent = []

    def urlopen(request, timeout=None):
        sent.append(request.full_url)
        return Response({})

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)

    assert ci_module.post_pr_comment(project, 'the table') is True
    assert len(sent) == 1
    assert sent[0].endswith('/repos/acme/widgets/issues/12/comments')
    assert ci_module.publish_dir(project) == '/tmp/rt/purlin-dashboard'


@pytest.mark.proof("records", "PROOF-32", "RULE-27")
def test_a_project_that_is_not_the_workspace_commits_nothing(
        project, github_env, monkeypatch, tmp_path, capsys):
    """The API commit names the real repository, never the fixture's.

    A fixture project that reached it would land its own records on the
    branch the job is reviewing.
    """
    monkeypatch.setenv('GITHUB_WORKSPACE', str(tmp_path / 'the-checkout'))
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')

    assert records_module.commit_records(project, [path], 'ci',
                                         'purlin: record for 4f1c2ab') == ''
    assert host.urls() == []
    assert 'no record was committed' in capsys.readouterr().out


AZURE_THREADS = ('https://dev.azure.com/acme/widgets/_apis/git/repositories/'
                 'repo-id/pullRequests/42/threads?api-version=7.0')


@pytest.fixture
def azure_pr(azure_env, monkeypatch):
    monkeypatch.setenv('SYSTEM_PULLREQUEST_PULLREQUESTID', '42')


@pytest.mark.proof("records", "PROOF-23", "RULE-10")
def test_the_azure_comment_opens_a_thread_on_the_pull_request(
        project, azure_pr, monkeypatch):
    sent = []

    def urlopen(request, timeout=None):
        sent.append((request.get_method(), request.full_url, timeout,
                     dict(request.header_items()),
                     json.loads(request.data.decode('utf-8'))))
        return Response({})

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)

    assert ci_module.post_pr_comment(project,
                                     'Purlin: 2 rules meet the gate.') is True
    assert len(sent) == 1, sent
    method, url, timeout, headers, body = sent[0]
    assert method == 'POST'
    # The collection URI ends in a slash, and the thread URL carries one
    # separator, not two.
    assert url == AZURE_THREADS
    assert timeout == 30
    assert headers['Authorization'] == 'Bearer a-token'
    assert headers['Content-type'] == 'application/json'
    assert body == {'comments': [{'parentCommentId': 0,
                                  'content': 'Purlin: 2 rules meet the gate.',
                                  'commentType': 'text'}],
                    'status': 'closed'}


@pytest.mark.proof("records", "PROOF-23", "RULE-10")
@pytest.mark.parametrize('missing', ['SYSTEM_ACCESSTOKEN', 'SYSTEM_TEAMPROJECT',
                                     'BUILD_REPOSITORY_ID',
                                     'SYSTEM_PULLREQUEST_PULLREQUESTID'])
def test_an_azure_run_missing_a_variable_posts_nothing(project, azure_pr,
                                                       monkeypatch, capsys,
                                                       missing):
    monkeypatch.delenv(missing)
    sent = []
    monkeypatch.setattr(urllib.request, 'urlopen',
                        lambda request, timeout=None: sent.append(request))

    assert ci_module.post_pr_comment(project, 'anything') is False
    assert sent == []
    assert 'not an Azure DevOps pull request' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-23", "RULE-10")
def test_a_refused_azure_comment_is_reported_rather_than_raised(
        project, azure_pr, monkeypatch, capsys):
    def refuse(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 401, 'Unauthorized', {},
                                     None)

    monkeypatch.setattr(urllib.request, 'urlopen', refuse)
    assert ci_module.post_pr_comment(project, 'anything') is False
    printed = capsys.readouterr().out
    assert 'The comment was not posted' in printed
    assert '401' in printed


@pytest.mark.proof("records", "PROOF-11", "RULE-11")
def test_the_artifact_carries_the_page_and_the_data(project, tmp_path):
    data = os.path.join(project, ci_module.DATA_FILE)
    os.makedirs(os.path.dirname(data))
    with open(data, 'w', encoding='utf-8') as handle:
        handle.write('const PURLIN_DATA = {};\n')
    out = str(tmp_path / 'artifact')

    assert ci_module.publish_dashboard(project, out) == out
    assert os.path.isfile(os.path.join(out, 'purlin-report.html'))
    with open(os.path.join(out, '.purlin', 'report-data.js'),
              encoding='utf-8') as handle:
        assert handle.read() == 'const PURLIN_DATA = {};\n'


@pytest.mark.proof("records", "PROOF-11", "RULE-11")
def test_the_artifact_says_when_there_is_no_data_to_carry(project, tmp_path,
                                                          capsys):
    out = str(tmp_path / 'artifact')
    ci_module.publish_dashboard(project, out)
    assert 'No dashboard data' in capsys.readouterr().out
    assert os.path.isdir(out)


def _no_runner_temp(monkeypatch):
    monkeypatch.delenv('RUNNER_TEMP', raising=False)
    monkeypatch.delenv('AGENT_TEMPDIRECTORY', raising=False)
    # The fixture project stands in for the job's own checkout here, so the
    # workspace check has to read it as one rather than as a stranger.
    _no_workspace(monkeypatch)


@pytest.mark.proof("records", "PROOF-11", "RULE-11")
def test_the_artifact_goes_to_the_github_runner_temp_directory(project,
                                                               monkeypatch):
    _no_runner_temp(monkeypatch)
    monkeypatch.setenv('RUNNER_TEMP', os.path.join(project, 'runner-temp'))

    # The workflow spells this path with a forward slash and the run has to
    # write where the upload step reads, so the separator is the one the
    # workflow can write rather than the local one.
    expected = '%s/purlin-dashboard' % os.path.join(project, 'runner-temp')
    assert ci_module.publish_dir(project) == expected
    assert ci_module.publish_dashboard(project) == expected, (
        'the upload step names $RUNNER_TEMP/purlin-dashboard, so a run that '
        'publishes anywhere else attaches an empty artifact')
    assert os.path.isdir(expected)


@pytest.mark.proof("records", "PROOF-11", "RULE-11")
def test_the_artifact_goes_to_the_azure_agent_temp_directory(project,
                                                             monkeypatch):
    _no_runner_temp(monkeypatch)
    monkeypatch.setenv('AGENT_TEMPDIRECTORY',
                       os.path.join(project, 'agent-temp'))

    expected = '%s/purlin-dashboard' % os.path.join(project, 'agent-temp')
    assert ci_module.publish_dir(project) == expected
    assert ci_module.publish_dashboard(project) == expected
    assert os.path.isdir(expected)


@pytest.mark.proof("records", "PROOF-11", "RULE-11")
def test_the_artifact_goes_under_the_project_when_no_runner_names_a_directory(
        project, monkeypatch):
    _no_runner_temp(monkeypatch)

    expected = os.path.join(project, '.purlin', 'runtime', 'report')
    assert ci_module.publish_dir(project) == expected
    assert ci_module.publish_dashboard(project) == expected
    assert os.path.isdir(expected)


# ---------------------------------------------------------------------------
# Handing the run to the git host
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-12", "RULE-12")
def test_the_git_host_is_read_from_the_remote(project):
    git(project, 'remote', 'add', 'origin',
        'https://dev.azure.com/acme/widgets/_git/widgets')
    assert remote_module._host(project, None) == 'azure'
    git(project, 'remote', 'set-url', 'origin',
        'https://github.com/acme/widgets.git')
    assert remote_module._host(project, None) == 'github'


@pytest.mark.proof("records", "PROOF-12", "RULE-12")
def test_the_azure_branch_prints_the_pipeline_and_returns(project, capsys):
    url = 'https://dev.azure.com/acme/widgets/_git/widgets'
    git(project, 'remote', 'add', 'origin', url)

    assert remote_module._azure(project, 'main') == 0
    printed = capsys.readouterr().out
    assert 'Azure DevOps runs the pipeline for main' in printed
    assert url in printed
    assert 'git pull --ff-only' in printed


@pytest.mark.proof("records", "PROOF-12", "RULE-12")
def test_a_detached_head_has_nothing_to_push(project, capsys):
    head = git(project, 'rev-parse', 'HEAD').stdout.strip()
    git(project, 'checkout', '--quiet', head)
    assert remote_module.run_remote(project) == 1
    assert 'not on a branch' in capsys.readouterr().out


@pytest.mark.proof("records", "PROOF-12", "RULE-12")
def test_the_follow_up_for_azure_is_marked_in_the_source():
    with open(os.path.join(ROOT, 'scripts', 'run', 'remote.py'),
              encoding='utf-8') as handle:
        assert 'TODO(ado-remote)' in handle.read()


class FakeProcesses(object):
    """`subprocess.run` for `remote.py`: git and gh answer, and nothing runs.

    The branch is `feature-x` and `origin` is a GitHub URL. Every process
    other than those two reads is kept in `started`, in order, with the
    directory it was started in.
    """

    def __init__(self, push=0, watch=0):
        self.push = push
        self.watch = watch
        self.started = []
        self.cwds = []

    def __call__(self, argv, cwd=None, capture_output=False, text=False,
                 timeout=None):
        argv = list(argv)
        if argv[:3] == ['git', 'rev-parse', '--abbrev-ref']:
            return subprocess.CompletedProcess(argv, 0, 'feature-x\n', '')
        if argv[:3] == ['git', 'remote', 'get-url']:
            return subprocess.CompletedProcess(
                argv, 0, 'https://github.com/acme/widgets.git\n', '')
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
    def arrange(push=0, watch=0, gh=True):
        folder = tmp_path / ('with-gh' if gh else 'without-gh')
        folder.mkdir()
        if gh:
            (folder / 'gh').write_text('', encoding='utf-8')
        monkeypatch.setenv('PATH', str(folder))
        fake = FakeProcesses(push=push, watch=watch)
        monkeypatch.setattr(remote_module.subprocess, 'run', fake)
        monkeypatch.setattr(remote_module, '_table',
                            lambda project_root: 'the status table')
        return fake
    return arrange


PUSH = ['git', 'push', '-u', 'origin', 'feature-x']
WATCH = ['gh', 'run', 'watch', '--exit-status']
PULL = ['git', 'pull', '--ff-only']


@pytest.mark.proof("records", "PROOF-24", "RULE-12")
def test_the_github_branch_pushes_watches_and_pulls(project, remote_run,
                                                    capsys):
    fake = remote_run()

    assert remote_module.run_remote(project) == 0
    assert fake.started == [PUSH, WATCH, PULL]
    assert fake.cwds == [project, project, project]
    printed = capsys.readouterr().out
    assert 'Pushing feature-x.' in printed
    assert 'Waiting for the purlin.yml workflow on feature-x.' in printed
    assert 'finished red' not in printed
    assert printed.rstrip().endswith('the status table')


@pytest.mark.proof("records", "PROOF-24", "RULE-12")
def test_a_red_run_still_pulls_and_prints_the_table(project, remote_run,
                                                    capsys):
    fake = remote_run(watch=1)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH, WATCH, PULL]
    printed = capsys.readouterr().out
    assert 'The run finished red. The table below is what came back.' in printed
    assert printed.rstrip().endswith('the status table')


@pytest.mark.proof("records", "PROOF-24", "RULE-12")
def test_without_gh_the_run_is_neither_watched_nor_pulled(project, remote_run,
                                                          capsys):
    fake = remote_run(gh=False)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH]
    printed = capsys.readouterr().out
    assert 'GitHub CLI `gh` is not installed' in printed
    assert 'the status table' not in printed


@pytest.mark.proof("records", "PROOF-24", "RULE-12")
def test_a_failed_push_starts_no_run(project, remote_run, capsys):
    fake = remote_run(push=1)

    assert remote_module.run_remote(project) == 1
    assert fake.started == [PUSH]
    printed = capsys.readouterr().out
    assert 'The push failed, so no run was started.' in printed
    assert 'Waiting for' not in printed


# ---------------------------------------------------------------------------
# The default branch
# ---------------------------------------------------------------------------

@pytest.mark.proof("records", "PROOF-21", "RULE-21")
def test_the_default_branch_is_what_origin_points_at(project):
    git(project, 'update-ref', 'refs/remotes/origin/trunk',
        git(project, 'rev-parse', 'HEAD').stdout.strip())
    git(project, 'symbolic-ref', 'refs/remotes/origin/HEAD',
        'refs/remotes/origin/trunk')
    assert reader.default_branch(project) == 'trunk'


@pytest.mark.proof("records", "PROOF-21", "RULE-21")
def test_with_no_remote_the_default_branch_is_the_one_head_names(tmp_path):
    """A `master` repository is not told its signature is off the branch.

    A git configured for `master` makes one, and that repository has no
    `origin/HEAD` to read: answering `main` there sends the gate looking for a
    branch that does not exist and every signature reads as not on it.
    """
    root = str(tmp_path / 'no-remote')
    os.makedirs(root)
    git(root, '-c', 'init.defaultBranch=master', 'init', '--quiet')
    assert reader.default_branch(root) == 'master'


@pytest.mark.proof("records", "PROOF-21", "RULE-21")
def test_a_detached_head_falls_back_to_main(project):
    git(project, 'checkout', '--quiet',
        git(project, 'rev-parse', 'HEAD').stdout.strip())
    assert reader.default_branch(project) == 'main'


def teardown_module(module):
    """Leave nothing behind: every repository lived under pytest's tmp_path."""
    shutil.rmtree(os.path.join(DEV, '__pycache__'), ignore_errors=True)
