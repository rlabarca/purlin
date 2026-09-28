"""Tests for the check of who committed a file under `.purlin/evidence/ci/`.

On Azure DevOps the tag run asks the host two things with the build
service's token: who the run is, from `_apis/connectionData`, and who pushed
the commit that last changed each `ci/` file, from `push.pushedBy` of that
commit. Every request here goes to a fake opener standing in for
`provenance._open`, which answers canned JSON, a refusal or a timeout.
Nothing here reaches a network or a git host.

What each group holds:

*match*      the two ids agree and the file passes, only the last commit
             counts, and the committer's name is never read
*closed*     a mismatch, no `push`, 401, 403, a timeout, no commit and no
             token each name the file, and the gate exits 1
*off*        a machine with no runner variables asks nothing and counts the
             files as not checked
*token*      every request carries the timeout and the token in its header,
             and the token appears in nothing the gate prints
*template*   the rendered Azure DevOps pipeline hands the gate its token
"""

import io
import json
import os
import socket
import sys
import urllib.error

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'ci'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))

import gate_check  # noqa: E402
import workflow  # noqa: E402
from purlin import provenance  # noqa: E402
from test_signatures import Project, commit_as_ci, git, write  # noqa: E402

TOKEN = 's3cret-token-value'
COLLECTION = 'https://dev.azure.com/acme/'
PROJECT = 'demo'
REPOSITORY = 'repo-1'
BUILD_ID = 'build-1'
JANE = {'id': 'jane-1', 'displayName': 'Jane', 'uniqueName': 'jane@acme.com'}
BUILD = {'id': BUILD_ID, 'displayName': 'demo Build Service (acme)',
         'uniqueName': 'Build\\demo'}
CI_FILE = '.purlin/evidence/ci/login.json'

_VARIABLES = ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_REF_NAME',
              'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', 'SYSTEM_ACCESSTOKEN',
              'SYSTEM_TEAMPROJECT', 'BUILD_REPOSITORY_ID',
              'BUILD_SOURCEBRANCH', 'BUILD_SOURCEBRANCHNAME')


# ---------------------------------------------------------------------------
# The fake opener
# ---------------------------------------------------------------------------

class _Answer(object):
    def __init__(self, body):
        self.body = json.dumps(body).encode('utf-8')

    def read(self):
        return self.body

    def close(self):
        pass


class FakeAzure(object):
    """Stands in for `provenance._open`: canned answers, every request kept.

    `commits` maps a sha to the commit's JSON, or to an exception to raise.
    `identity` is the `connectionData` answer, or an exception. A sha nobody
    named answers as a commit pushed by the build identity.
    """

    def __init__(self, identity=None, commits=None, default=None):
        self.identity = ({'authenticatedUser': {'id': BUILD_ID}}
                         if identity is None else identity)
        self.commits = dict(commits or {})
        self.default = ({'commitId': 'x', 'push': {'pushedBy': BUILD}}
                        if default is None else default)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append({'url': request.full_url,
                              'headers': dict(request.header_items()),
                              'timeout': timeout,
                              'method': request.get_method()})
        url = request.full_url
        if '/_apis/connectionData' in url:
            answer = self.identity
        else:
            sha = url.split('/commits/', 1)[1].split('?', 1)[0]
            answer = self.commits.get(sha, self.default)
        if isinstance(answer, BaseException):
            raise answer
        return _Answer(answer)

    def commit_shas(self):
        return [entry['url'].split('/commits/', 1)[1].split('?', 1)[0]
                for entry in self.requests if '/commits/' in entry['url']]


def refused(code):
    return urllib.error.HTTPError(COLLECTION, code, 'Unauthorized', {}, None)


def pushed(who):
    return {'commitId': 'x', 'push': {'pushId': 7, 'pushedBy': who}}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_env(monkeypatch):
    for name in _VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def runner(clean_env):
    """The variables an Azure DevOps tag run carries, token included."""
    clean_env.setenv('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', COLLECTION)
    clean_env.setenv('SYSTEM_TEAMPROJECT', PROJECT)
    clean_env.setenv('BUILD_REPOSITORY_ID', REPOSITORY)
    clean_env.setenv('SYSTEM_ACCESSTOKEN', TOKEN)
    return clean_env


@pytest.fixture
def fake(monkeypatch):
    def install(**kwargs):
        opener = FakeAzure(**kwargs)
        monkeypatch.setattr(provenance, '_open', opener)
        return opener
    return install


@pytest.fixture
def project():
    """A project at `passed` whose evidence CI committed under `ci/`."""
    made = Project(config={'min_strength': 50})
    made.proofs()
    made.evidence(runner='ci', commit_it=False, source='ci')
    commit_as_ci(made.root)
    yield made
    made.close()


def head(made):
    return git(made.root, 'rev-parse', 'HEAD').stdout.strip()


def commit_ci_file(made, text, name='Dev', rel=CI_FILE):
    """Change one `ci/` file and commit it under the committer name given."""
    path = os.path.join(made.root, *rel.split('/'))
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    data['note'] = text
    write(path, json.dumps(data, indent=2, sort_keys=True))
    git(made.root, 'add', '-A')
    git(made.root, '-c', 'user.name=' + name, '-c',
        'user.email=someone@example.com', 'commit', '-q', '-m',
        'purlin: evidence at abc1234')
    return head(made)


def check(made):
    return provenance.check(made.root, [CI_FILE], 'azure')


def gate(made, as_json=False):
    out = io.StringIO()
    code = gate_check.check(made.root, out=out, as_json=as_json,
                            verify_evidence=True)
    return code, out.getvalue()


# ---------------------------------------------------------------------------
# match
# ---------------------------------------------------------------------------

class TestTheIdsAgree:

    # purlin: gate_check PROOF-39
    def test_a_commit_the_run_pushed_passes(self, project, runner, fake):
        sha = head(project)
        opener = fake(commits={sha: pushed(BUILD)})
        assert check(project) == ([], [], None)
        urls = [entry['url'] for entry in opener.requests]
        assert urls == [
            'https://dev.azure.com/acme/_apis/connectionData?api-version=7.0',
            'https://dev.azure.com/acme/demo/_apis/git/repositories/repo-1/'
            'commits/%s?api-version=7.0' % sha]
        assert all(entry['method'] == 'GET' for entry in opener.requests)

    # purlin: gate_check PROOF-39
    def test_the_gate_passes_when_the_run_pushed_it(self, project, runner,
                                                    fake):
        fake(commits={head(project): pushed(BUILD)})
        code, printed = gate(project)
        assert code == 0, printed
        assert 'Evidence' not in printed, printed

    # purlin: gate_check PROOF-39
    def test_the_build_service_name_is_not_read(self, project, runner, fake):
        sha = commit_ci_file(project, 'typed by hand',
                             name='Project Collection Build Service')
        assert git(project.root, 'log', '-1', '--format=%cn').stdout.strip() \
            == 'Project Collection Build Service'
        fake(commits={sha: pushed(JANE)})
        problems, not_checked, notice = check(project)
        assert [rel for rel, _reason in problems] == [CI_FILE]
        assert not_checked == [] and notice is None

    # purlin: gate_check PROOF-40
    def test_only_the_last_commit_counts(self, project, runner, fake):
        first = commit_ci_file(project, 'one')
        second = commit_ci_file(project, 'two')
        opener = fake(commits={first: pushed(BUILD), second: pushed(JANE)})
        problems, _not_checked, _notice = check(project)
        assert [rel for rel, _reason in problems] == [CI_FILE]
        assert second[:7] in problems[0][1]
        assert opener.commit_shas() == [second]

    # purlin: gate_check PROOF-40
    def test_a_last_commit_the_run_pushed_passes_over_an_earlier_one(
            self, project, runner, fake):
        first = commit_ci_file(project, 'one')
        second = commit_ci_file(project, 'two')
        opener = fake(commits={first: pushed(JANE), second: pushed(BUILD)})
        assert check(project) == ([], [], None)
        assert opener.commit_shas() == [second]


# ---------------------------------------------------------------------------
# closed
# ---------------------------------------------------------------------------

class TestItFailsClosed:

    # purlin: gate_check PROOF-41
    def test_a_commit_someone_else_pushed_fails_the_gate(self, project,
                                                         runner, fake):
        sha = head(project)
        fake(commits={sha: pushed(JANE)})
        code, printed = gate(project)
        assert code == 1, printed
        assert 'Evidence (1):' in printed, printed
        assert ('%s: commit %s was pushed by jane@acme.com, not by the '
                'identity this run holds' % (CI_FILE, sha[:7])) in printed

    # purlin: gate_check PROOF-42
    def test_a_commit_with_no_push_is_named(self, project, runner, fake):
        sha = head(project)
        fake(commits={sha: {'commitId': sha, 'committer': {
            'name': 'Project Collection Build Service'}}})
        problems, _not_checked, _notice = check(project)
        assert problems == [(CI_FILE, 'Azure DevOps names no push for '
                                      'commit %s' % sha[:7])]
        code, printed = gate(project)
        assert code == 1 and 'names no push' in printed, printed

    # purlin: gate_check PROOF-43
    @pytest.mark.parametrize('status', [401, 403])
    def test_a_refused_commit_request_is_named(self, project, runner, fake,
                                               status):
        sha = head(project)
        fake(commits={sha: refused(status)})
        problems, _not_checked, _notice = check(project)
        assert problems == [(CI_FILE, 'Azure DevOps refused the token with '
                                      'HTTP %d when asked for commit %s'
                             % (status, sha[:7]))]
        code, printed = gate(project)
        assert code == 1, printed
        assert 'refused the token with HTTP %d' % status in printed

    # purlin: gate_check PROOF-43
    def test_a_refused_identity_names_every_file(self, project, runner,
                                                 fake):
        other = '.purlin/evidence/ci/extra.json'
        write(os.path.join(project.root, *other.split('/')), '{}\n')
        commit_as_ci(project.root)
        opener = fake(identity=refused(401))
        problems, _not_checked, _notice = provenance.check(
            project.root, [CI_FILE, other], 'azure')
        assert [rel for rel, _reason in problems] == [CI_FILE, other]
        assert all('refused the token with HTTP 401 when asked for the '
                   'identity of this run' in reason
                   for _rel, reason in problems)
        assert opener.commit_shas() == []

    # purlin: gate_check PROOF-44
    @pytest.mark.parametrize('error', [
        socket.timeout('timed out'),
        urllib.error.URLError(socket.timeout('timed out'))])
    def test_no_answer_in_time_is_named(self, project, runner, fake, error):
        fake(commits={head(project): error})
        problems, _not_checked, _notice = check(project)
        assert len(problems) == 1
        assert 'did not answer within 30 seconds' in problems[0][1]
        code, printed = gate(project)
        assert code == 1, printed

    # purlin: gate_check PROOF-44
    def test_a_file_no_commit_changed_is_named(self, project, runner, fake):
        other = '.purlin/evidence/ci/extra.json'
        write(os.path.join(project.root, *other.split('/')), '{}\n')
        opener = fake()
        problems, _not_checked, _notice = provenance.check(
            project.root, [other], 'azure')
        assert problems == [(other, 'no commit has changed it')]
        assert opener.commit_shas() == []

    # purlin: gate_check PROOF-45
    def test_a_run_with_no_token_names_every_file(self, project, runner,
                                                  fake):
        runner.delenv('SYSTEM_ACCESSTOKEN')
        opener = fake()
        problems, not_checked, notice = check(project)
        assert problems == [(CI_FILE, 'the run has no SYSTEM_ACCESSTOKEN, so '
                                      'who pushed it cannot be read')]
        assert not_checked == [] and notice is None
        assert opener.requests == []
        code, printed = gate(project)
        assert code == 1, printed
        assert 'the run has no SYSTEM_ACCESSTOKEN' in printed


# ---------------------------------------------------------------------------
# off
# ---------------------------------------------------------------------------

class TestOffARunner:

    # purlin: gate_check PROOF-46
    def test_an_azure_project_off_a_runner_is_not_checked(self, project,
                                                          clean_env, fake):
        other = '.purlin/evidence/ci/extra.json'
        write(os.path.join(project.root, *other.split('/')), '{}\n')
        commit_as_ci(project.root)
        git(project.root, 'remote', 'add', 'origin',
            'https://dev.azure.com/acme/demo/_git/demo')
        opener = fake()
        code, printed = gate(project, as_json=True)
        assert code == 0, printed
        assert ('gate: ci/ provenance is checked by the tag run; this '
                'machine has no token.\n') in printed
        assert ('gate: 2 files under .purlin/evidence/ci/ are not '
                'checked.\n') in printed
        assert 'Evidence' not in printed, printed
        result = json.loads(printed[printed.index('\n{') + 1:])
        assert result['not_checked'] == [other, CI_FILE]
        assert result['evidence'] == []
        assert opener.requests == []

    # purlin: gate_check PROOF-46
    def test_the_check_off_a_runner_passes_and_fails_nothing(self, project,
                                                             clean_env, fake):
        opener = fake()
        assert check(project) == ([], [CI_FILE], provenance.NO_TOKEN)
        assert opener.requests == []


# ---------------------------------------------------------------------------
# token
# ---------------------------------------------------------------------------

class TestTheToken:

    # purlin: gate_check PROOF-47
    @pytest.mark.parametrize('answer', [
        pushed(BUILD), pushed(JANE), refused(401),
        socket.timeout('timed out')])
    def test_the_token_is_sent_and_never_printed(self, project, runner, fake,
                                                 answer):
        opener = fake(commits={head(project): answer})
        code, printed = gate(project, as_json=True)
        assert code in (0, 1)
        assert opener.requests, 'no request was sent'
        for entry in opener.requests:
            assert entry['timeout'] == 30
            assert entry['headers'].get('Authorization') == 'Bearer ' + TOKEN
            assert TOKEN not in entry['url']
        assert TOKEN not in printed, printed


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------

class TestThePipeline:

    # purlin: gate_check PROOF-48
    def test_the_gate_step_carries_the_token(self):
        text = workflow.render_workflow('azure', [], 'v1.0.0')
        steps = text.split('\n      - ')
        gate_steps = [step for step in steps
                      if 'displayName: Check the gate' in step]
        assert len(gate_steps) == 1, text
        assert ('        env:\n'
                '          SYSTEM_ACCESSTOKEN: $(System.AccessToken)') \
            in gate_steps[0], gate_steps[0]
        assert 'gate_check.py" --check --verify' in gate_steps[0]
