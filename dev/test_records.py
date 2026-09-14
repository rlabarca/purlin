"""Tests for `scripts/run/records.py`: naming, retention, committing, labels.

Every git host call is mocked at the HTTP boundary (`urllib.request.urlopen`),
and every git operation runs against a local repository with a local bare
repository as its remote. Nothing here reaches a network.

What each group proves:

*naming*      the file name carries the timestamp, the commit, the runner and
              the operating system, and the file's own fields agree with it
*retention*   three records per feature per operating system survive, another
              operating system's records are untouched, and a record an
              annotated `validated/<name>` tag names is kept for ever
*developer*   a plain commit under the developer's identity, pushed when a
              remote and an upstream exist and explained when not
*ci*          blob, tree, commit, ref update, with no author and no committer
              field, retried when the branch moved under the run
*labels*      `ci` for a commit the git host made, which on GitHub is the
              committer `noreply@github.com` with the author
              `github-actions[bot]` and a signature that does not
              contradict it, `developer` for a person's, `local` for a
              file not committed
*publishing*  what a CI run puts where anyone else can read it: the pull
              request comment and the dashboard artifact
*remote*      `--remote` hands the run to the git host and brings it back
"""

import json
import os
import shutil
import subprocess
import sys
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
        'gate': 'recorded',
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
    """

    def __init__(self, fail_patch=0, head='1' * 40, azure=False):
        self.calls = []
        self.fail_patch = fail_patch
        self.head = head
        self.azure = azure
        self.patched = 0

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


@pytest.fixture
def azure_env(monkeypatch):
    monkeypatch.setenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI',
                       'https://dev.azure.com/acme/')
    monkeypatch.setenv('SYSTEM_ACCESSTOKEN', 'a-token')
    monkeypatch.setenv('SYSTEM_TEAMPROJECT', 'widgets')
    monkeypatch.setenv('BUILD_REPOSITORY_ID', 'repo-id')
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
def test_a_validated_tag_keeps_the_records_its_message_names(project):
    oldest = put_record(project, 'greeting',
                        '20260101T120000Z-4f1c2ab-ci.json')
    for day in range(11, 16):
        put_record(project, 'greeting',
                   '202609%dT120000Z-4f1c2ab-ci.json' % day)
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'records')
    records_module.tag_validated(project, '1.0', [oldest])

    assert records_module.validated_paths(project) == {oldest}
    records_module.prune(project, 'greeting')
    kept = names(project, 'greeting')
    assert os.path.basename(oldest) in kept
    assert len(kept) == 4, 'the newest three plus the one the tag names'


@pytest.mark.proof("records", "PROOF-3", "RULE-3")
def test_the_validated_tag_is_annotated_and_lists_every_path(project):
    first = put_record(project, 'greeting', '20260101T120000Z-4f1c2ab-ci.json')
    second = put_record(project, 'greeting', '20260102T120000Z-4f1c2ab-ci.json')
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'records')
    ref = records_module.tag_validated(project, '1.0', [first, second])

    assert ref == 'validated/1.0'
    kind = git(project, 'cat-file', '-t', 'validated/1.0').stdout.strip()
    assert kind == 'tag', 'a lightweight tag carries no message to read'
    message = git(project, 'for-each-ref', '--format=%(contents)',
                  'refs/tags/validated/').stdout
    assert first in message and second in message


@pytest.mark.proof("records", "PROOF-3", "RULE-3")
def test_validated_paths_is_empty_outside_a_repository(tmp_path):
    assert records_module.validated_paths(str(tmp_path)) == set()


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
def test_the_ci_commit_walks_blob_tree_commit_ref(project, github_env,
                                                  monkeypatch):
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci', 'linux')

    sha = records_module.commit_records(project, [path], 'ci',
                                        'purlin: record for 4f1c2ab')

    assert sha == 'c' * 40
    order = [url.rsplit('/git/', 1)[-1].split('?')[0] for url in host.urls()]
    assert order == ['blobs', 'ref/heads/main', 'commits/' + '1' * 40,
                     'trees', 'commits', 'refs/heads/main']


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
    assert entry['sha'] == 'b' * 40
    assert entry[records_module._PERM_KEY] == records_module._FILE_PERM
    blob = host.body_for('/git/blobs', method='POST')
    assert blob['encoding'] == 'utf-8'
    assert json.loads(blob['content'])['feature'] == 'greeting'


@pytest.mark.proof("records", "PROOF-5", "RULE-5")
def test_the_ci_commit_carries_a_path_outside_the_records_directory(
        project, github_env, monkeypatch):
    """A CI run's approvals and briefs ride in the same commit as the record.

    An approval that stayed on the runner is evidence nobody can read, so the
    tree the commit names holds every path the run handed over and not only
    the ones under `.purlin/records/`.
    """
    host = FakeHost()
    monkeypatch.setattr(urllib.request, 'urlopen', host)
    path = records_module.write_record(project, record(), 'ci')
    approval = 'specs/core/greeting.approvals/RULE-1.1a2b3c4d.ci.json'
    brief = 'specs/core/greeting.approvals/RULE-2.5e6f7a8b.brief.json'
    directory = os.path.join(project, 'specs', 'core', 'greeting.approvals')
    os.makedirs(directory)
    for rel, text in ((approval, '{"rule": "RULE-1", "approver": "ci"}\n'),
                      (brief, '{"rule": "RULE-2", "verdict": "ready"}\n')):
        with open(os.path.join(project, *rel.split('/')), 'w',
                  encoding='utf-8') as handle:
            handle.write(text)

    records_module.commit_records(project, [path, approval, brief], 'ci',
                                  'purlin: record for 4f1c2ab')

    tree = host.body_for('/git/trees', method='POST')
    paths = [entry['path'] for entry in tree['tree']]
    assert paths == [path, approval, brief]
    beside_the_spec = [name for name in paths
                       if not name.startswith('.purlin/records/')]
    assert beside_the_spec == [approval, brief]
    blobs = [body for _verb, url, body in host.calls if url.endswith('/blobs')]
    assert len(blobs) == 3, 'a path handed over got no blob'
    assert json.loads(blobs[1]['content'])['approver'] == 'ci'
    assert json.loads(blobs[2]['content'])['verdict'] == 'ready'


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

    verdict = subprocess.run(
        ['git', '-c', 'gpg.format=ssh',
         '-c', 'gpg.ssh.allowedSignersFile=' + allowed,
         'log', '-1', '--format=%G?\t%cn'],
        cwd=project, capture_output=True, text=True).stdout.strip()
    assert verdict.startswith('G\t'), verdict
    assert verdict.endswith(ACTIONS_BOT)
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
    and nothing CI wrote counts under `recorded` or `approved`.
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

    verdict = subprocess.run(
        ['git', '-c', 'gpg.format=ssh',
         '-c', 'gpg.ssh.allowedSignersFile=' + allowed,
         'log', '-1', '--format=%G?\t%cn\t%ce\t%an'],
        cwd=project, capture_output=True, text=True).stdout.strip()
    assert verdict.startswith('G\t'), verdict
    assert verdict.endswith('\t%s\t%s' % (WEB_FLOW_EMAIL, ACTIONS_BOT)), verdict
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
    as a person's, so it never counts under `recorded` or `approved`.
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

    assert ci_module.post_pr_comment(project, 'Purlin: 2 rules Recorded.')
    url, body = sent[0]
    assert url.endswith('/repos/acme/widgets/issues/12/comments')
    assert body == {'body': 'Purlin: 2 rules Recorded.'}


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
    """A `master` repository is not told its approval is off the branch.

    A git configured for `master` makes one, and that repository has no
    `origin/HEAD` to read: answering `main` there sends the gate looking for a
    branch that does not exist and every approval reads as not on it.
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
