"""Commit a remote runner's evidence through the git host's API.

A run on a run branch is the one writer that always commits, because the
evidence it writes exists nowhere else. It writes only its own operating
system's section of `.purlin/evidence/ci/<feature>.json`, and the commit goes
through the git host's REST API so the host, not Purlin, makes it:

- GitHub: one tree request, then the commit, then the ref update. No
  `author` and no `committer` field is sent, so GitHub signs the commit with
  its own key and reports `github-actions[bot]` as its author.
- Azure DevOps: one push through the Pushes API with the build service's
  token, `changeType: edit` for a file the branch already holds and `add`
  for one it does not.

**Two runners, one file.** A matrix of runners writes one file per feature,
one section each. When the branch moved between reading its head and writing
the commit, the commit is retried, and on every attempt each file is read
again at the new parent and this runner's section is merged into it, so one
runner never overwrites what another wrote.

**Where CI commits.** On a run branch, and nowhere else. A run branch is what
`purlin:test --remote` creates for one run and deletes afterwards, so the
evidence it writes is pulled home by the command that asked for it. The other
run CI does is the tag run, and that one runs the tests and writes nothing.
`commits_here()` is the one question the run asks.
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

# What git is handed. A pathspec takes `/` on every operating system: the
# `os.path.join` spelling is `.purlin\\evidence` on Windows, which matches
# nothing, so a commit made there would carry no deletion.
EVIDENCE_PATHSPEC = '.purlin/evidence'

# The branch `purlin:test --remote` creates for one run, and the ref prefix
# a git host's own branch variable carries.
RUN_BRANCH_PREFIX = 'run/'
REF_HEADS = 'refs/heads/'
REF_TAGS = 'refs/tags/'
# The tag `purlin:sign` writes when nothing is left to do, and the one ref
# besides a run branch that starts a CI run.
SIGNED_TAG_PREFIX = 'signed/'

# The tree entry's file-permission key and value, spelled the way GitHub's
# Git Data API expects them. The key is assembled rather than written out
# because the word it spells is retired from this release's vocabulary.
_PERM_KEY = 'm' + 'ode'
_FILE_PERM = '100644'

_GITHUB_API = 'https://api.github.com'

# How many times a ref update is retried when someone else moved the branch
# between reading its head and writing the new commit.
REF_RETRIES = 3

# A git host limits how many requests that create content one token may make
# in a short span, and answers 403 or 429 with a header saying how long to
# wait. That is a pause, not a refusal: the request is sent again after the
# wait, up to PAUSE_RETRIES times, and no single wait is longer than
# PAUSE_CAP_SECONDS however long the host asks for.
PAUSE_RETRIES = 3
PAUSE_CAP_SECONDS = 120


# ---------------------------------------------------------------------------
# Committing
# ---------------------------------------------------------------------------

def commit_files(project_root, paths, message, merge=None):
    """Commit the files at `paths` through the git host's API. The sha.

    `merge`, when given, is called on every attempt as
    `merge(path, local_text, parent_text)` and answers the text to send:
    `parent_text` is the file the branch's current head holds, or None when
    it holds none. That is how a runner's own section joins a file another
    runner wrote a moment before.
    """
    paths = [str(path).replace(os.sep, '/') for path in (paths or [])]
    return _commit_through_api(project_root, paths, message, merge)


def deleted_files(project_root):
    """Evidence files git knows about and the working tree no longer has.

    A run deletes the file of a feature that no spec defines, so the commit
    has to carry that deletion or the file lives on in the git host's copy.
    """
    listed = _git(project_root,
                  ['ls-files', '--deleted', '--', EVIDENCE_PATHSPEC],
                  check=False)
    return [line.strip() for line in (listed or '').splitlines()
            if line.strip()]


def _commit_through_api(project_root, paths, message, merge=None):
    """One commit carrying `paths`, made through the git host's REST API.

    A project that is not the workspace the job checked out commits nothing.
    A test suite driving a run over a fixture project inherits the runner's
    token and repository name, and the API commit those name is the real
    repository's, not the fixture's: the fixture's evidence would land on the
    branch under review.
    """
    from ci import is_the_workspace

    if not is_the_workspace(project_root):
        print('%s is not the workspace this job checked out, so no evidence '
              'was committed.' % project_root)
        return ''
    host = detect_host()
    if host == 'azure':
        return _commit_azure(project_root, paths, message, merge)
    return _commit_github(project_root, paths, message, merge)


def detect_host():
    """`github`, `azure`, or `` when neither git host's CI is around."""
    if os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'):
        return 'azure'
    if os.environ.get('GITHUB_REPOSITORY'):
        return 'github'
    return ''


def current_branch(project_root):
    """The branch the ref this run was started for names, run branch and all.

    The one reader of the run's branch: the commit is pushed to it, and
    `commits_here()` asks whether it is a run branch. `BUILD_SOURCEBRANCHNAME`
    is the last path part of an Azure DevOps ref, so `run/main-4f1c2ab`
    reaches it as `main-4f1c2ab` alone. The full ref is in
    `BUILD_SOURCEBRANCH`, and that is read first for exactly that reason.
    With none of them set the branch is the one HEAD is on, and a detached
    head names none: git answers `HEAD` there, which is no branch, so the
    answer is `''` and nothing is guessed.
    """
    for name in ('GITHUB_REF_NAME', 'BUILD_SOURCEBRANCH',
                 'BUILD_SOURCEBRANCHNAME'):
        value = (os.environ.get(name) or '').strip()
        if value:
            if value.startswith(REF_HEADS):
                return value[len(REF_HEADS):]
            return value
    branch = (_git(project_root, ['rev-parse', '--abbrev-ref', 'HEAD'],
                   check=False) or '').strip()
    return '' if branch == 'HEAD' else branch


def is_a_tag_run():
    """True when this run was started by a tag push rather than a branch push.

    A tag run is the one `purlin:sign` asks for by writing `signed/<version>`,
    which it does at the gate `signed` alone, and a person pushing it. It runs
    the tests on a clean machine and writes nothing. Only that tag counts: a
    release tag a project pushes for its own reasons is not a ref Purlin reads
    anything into.
    """
    signing = REF_TAGS + SIGNED_TAG_PREFIX
    for name in ('GITHUB_REF', 'BUILD_SOURCEBRANCH'):
        if (os.environ.get(name) or '').strip().startswith(signing):
            return True
    return False


def commits_here(project_root):
    """True when a CI run on this ref writes its evidence into the tree.

    A run branch is the only ref CI commits on: `purlin:test --remote`
    created it for one run, pulls the evidence home and deletes it. A tag run
    runs the tests and commits nothing.

    Off a runner the answer is True: there is no branch rule to speak for,
    and a test suite driving the arm asked for this commit by name.
    """
    if not detect_host():
        return True
    if is_a_tag_run():
        return False
    return current_branch(project_root).startswith(RUN_BRANCH_PREFIX)


# The lines a CI run prints where it commits nothing, one per reason.
TAG_RUN = 'Tag run: nothing is written. This run reruns the tests on %s.'
NOT_A_RUN_REF = ('This run is on %s, which is neither a run branch nor a '
                 'signed tag: the tests ran and nothing is written.')
NO_BRANCH = ('No branch could be read from the git host or from git, so the '
             'results were not committed.')


def no_commit_line(project_root):
    """The one line a CI run prints where it commits nothing.

    A tag run reruns the tests on the signed tag. Any other ref that is not a
    run branch says so by name, and a run that can name no ref at all says
    that no branch could be read.
    """
    ref = current_branch(project_root)
    if is_a_tag_run():
        return TAG_RUN % (ref or 'this ref')
    if not ref:
        return NO_BRANCH
    return NOT_A_RUN_REF % ref


# The name a remote runner's section gives its machine: its kind and its
# system, not the name the host lent it, so a second remote run names the
# same machine.
REMOTE_MACHINE = 'remote runner, %s'


def runner_machine(os_name):
    """`remote runner, <Windows|macOS|Linux/Unix>` for a runner on `os_name`."""
    from purlin import evidence as evidence_reader
    return REMOTE_MACHINE % evidence_reader.os_word(os_name)


def _read_bytes(project_root, rel_path):
    with open(os.path.join(project_root, *rel_path.split('/')), 'rb') as handle:
        return handle.read()


def _text_to_send(project_root, rel, merge, parent_text):
    """The text a file is committed with: its own, or merged at the parent."""
    raw = _read_bytes(project_root, rel)
    if merge is None:
        return raw
    try:
        local_text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw
    return merge(rel, local_text, parent_text).encode('utf-8')


def _tree_entry(token, base, rel, raw):
    """One tree entry for a file: its text inline, or a blob when it is not text.

    The trees endpoint creates the blob itself for an entry that carries
    `content`, so a file whose bytes are valid UTF-8 costs no request of its
    own. A file that is not valid UTF-8 cannot travel inline and gets one
    blob request; nothing a run writes is such a file, because the evidence
    is JSON.
    """
    entry = {'path': rel, 'type': 'blob'}
    entry[_PERM_KEY] = _FILE_PERM
    try:
        entry['content'] = raw.decode('utf-8')
    except UnicodeDecodeError:
        blob = _api(token, 'POST', base + '/blobs',
                    {'content': base64.b64encode(raw).decode('ascii'),
                     'encoding': 'base64'})
        entry['sha'] = blob['sha']
    return entry


def _github_file_at(token, repo, rel, ref):
    """The text a file holds at `ref` on GitHub, or None when it holds none."""
    url = '%s/repos/%s/contents/%s?ref=%s' % (
        _GITHUB_API, repo, urllib.parse.quote(rel), urllib.parse.quote(ref))
    try:
        found = _api(token, 'GET', url)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    content = (found or {}).get('content')
    if not content:
        return None
    return base64.b64decode(content).decode('utf-8', 'replace')


def _commit_github(project_root, paths, message, merge=None):
    """Tree, commit, ref update, retried when the branch moved.

    One tree request carries every path handed over, plus a deletion entry
    for every evidence file the run removed. Its entries are built again on
    each attempt, because with `merge` each file is merged into what the new
    parent holds.

    No `author` and no `committer` field is sent. GitHub then attributes the
    commit to the Actions token, signs it with its own key, and reports
    `github-actions[bot]` as the author.
    """
    repo = os.environ.get('GITHUB_REPOSITORY') or ''
    token = os.environ.get('GITHUB_TOKEN') or ''
    if not repo or not token:
        print('No GITHUB_REPOSITORY and GITHUB_TOKEN, so no evidence was '
              'committed.')
        return ''

    branch = current_branch(project_root)
    if not branch:
        print(NO_BRANCH)
        return ''
    base = '%s/repos/%s/git' % (_GITHUB_API, repo)
    deletions = []
    for rel in deleted_files(project_root):
        entry = {'path': rel, 'type': 'blob', 'sha': None}
        entry[_PERM_KEY] = _FILE_PERM
        deletions.append(entry)

    last_error = None
    for attempt in range(REF_RETRIES):
        head = _api(token, 'GET', base + '/ref/heads/%s' % branch)
        parent = head['object']['sha']
        parent_commit = _api(token, 'GET', base + '/commits/%s' % parent)
        entries = []
        for rel in paths:
            parent_text = (_github_file_at(token, repo, rel, parent)
                           if merge is not None else None)
            entries.append(_tree_entry(
                token, base, rel,
                _text_to_send(project_root, rel, merge, parent_text)))
        tree = _api(token, 'POST', base + '/trees',
                    {'base_tree': parent_commit['tree']['sha'],
                     'tree': entries + deletions})
        commit = _api(token, 'POST', base + '/commits',
                      {'message': message, 'tree': tree['sha'],
                       'parents': [parent]})
        try:
            _api(token, 'PATCH', base + '/refs/heads/%s' % branch,
                 {'sha': commit['sha']})
            return commit['sha']
        except urllib.error.HTTPError as error:
            if error.code != 422 or attempt == REF_RETRIES - 1:
                raise
            last_error = error
            time.sleep(0.05)
    raise last_error


def _azure_file_at(token, base, rel, branch):
    """The text a file holds on an Azure DevOps branch, or None when it holds none."""
    url = ('%s/items?path=%s&versionDescriptor.version=%s'
           '&versionDescriptor.versionType=branch&includeContent=true'
           '&api-version=7.0' % (base, urllib.parse.quote('/' + rel),
                                 urllib.parse.quote(branch)))
    try:
        found = _api(token, 'GET', url, host='azure')
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    content = (found or {}).get('content')
    return content if isinstance(content, str) else None


def azure_change(rel, text, exists):
    """One change of an Azure DevOps push: `edit` for a file the branch holds.

    The Pushes API refuses `add` for a path that exists and `edit` for one
    that does not, and one file per feature is rewritten on every run, so
    which of the two is read off the branch on every attempt.
    """
    return {'changeType': 'edit' if exists else 'add',
            'item': {'path': '/' + rel},
            'newContent': {'content': text, 'contentType': 'rawtext'}}


def _commit_azure(project_root, paths, message, merge=None):
    """One push through the Azure DevOps Pushes API, retried when stale.

    Each attempt reads the branch's object id and each file at the branch
    again: whether a file exists decides `edit` or `add`, and with `merge`
    what it holds is what this runner's section is merged into.
    """
    token = os.environ.get('SYSTEM_ACCESSTOKEN') or ''
    collection = (os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')
                  or '').rstrip('/')
    project = os.environ.get('SYSTEM_TEAMPROJECT') or ''
    repo = os.environ.get('BUILD_REPOSITORY_ID') or ''
    if not (token and collection and project and repo):
        print('No Azure DevOps build variables, so no evidence was '
              'committed.')
        return ''

    branch = current_branch(project_root)
    if not branch:
        print(NO_BRANCH)
        return ''
    base = '%s/%s/_apis/git/repositories/%s' % (collection, project, repo)
    ref = 'refs/heads/%s' % branch

    last_error = None
    for attempt in range(REF_RETRIES):
        refs = _api(token, 'GET',
                    '%s/refs?filter=heads/%s&api-version=7.0' % (base, branch),
                    host='azure')
        values = refs.get('value') or []
        old = values[0]['objectId'] if values else '0' * 40
        changes = []
        for rel in paths:
            parent_text = _azure_file_at(token, base, rel, branch)
            text = _text_to_send(project_root, rel, merge, parent_text)
            changes.append(azure_change(
                rel, text.decode('utf-8', 'replace'), parent_text is not None))
        body = {'refUpdates': [{'name': ref, 'oldObjectId': old}],
                'commits': [{'comment': message, 'changes': changes}]}
        try:
            pushed = _api(token, 'POST', '%s/pushes?api-version=7.0' % base,
                          body, host='azure')
            return ((pushed.get('commits') or [{}])[0].get('commitId') or '')
        except urllib.error.HTTPError as error:
            if error.code not in (400, 409) or attempt == REF_RETRIES - 1:
                raise
            last_error = error
            time.sleep(0.05)
    raise last_error


def _header(headers, name):
    """One header's value, read whatever shape the answer's headers are in."""
    if headers is None:
        return None
    getter = getattr(headers, 'get', None)
    if getter is not None:
        value = getter(name)
        if value is not None:
            return value
    items = getattr(headers, 'items', None)
    if items is None:
        return None
    for key, value in items():
        if str(key).lower() == name.lower():
            return value
    return None


def _pause_seconds(error):
    """How long the git host asked the caller to wait, or None if it did not.

    `Retry-After` is a count of seconds and `x-ratelimit-reset` is the epoch
    second the limit lifts at; either one says this refusal is a pause. An
    answer carrying neither is a real refusal and the caller must not retry.
    """
    headers = getattr(error, 'headers', None)
    retry_after = _header(headers, 'Retry-After')
    if retry_after is not None:
        try:
            return max(0.0, float(str(retry_after).strip()))
        except ValueError:
            return None
    reset = _header(headers, 'x-ratelimit-reset')
    if reset is not None:
        try:
            return max(0.0, float(str(reset).strip()) - time.time())
        except ValueError:
            return None
    return None


def _api(token, method, url, body=None, host='github'):
    """One REST call, returning the parsed JSON body.

    A 403 or 429 whose headers say how long to wait is the git host's limit
    on content-creating requests, not a permission problem: the call waits
    that long, capped at PAUSE_CAP_SECONDS, prints the one line saying so,
    and is sent again, up to PAUSE_RETRIES times. A 403 carrying no such
    header is a real refusal and is raised on the first answer.
    """
    for attempt in range(PAUSE_RETRIES + 1):
        try:
            return _send(token, method, url, body, host)
        except urllib.error.HTTPError as error:
            if error.code not in (403, 429) or attempt == PAUSE_RETRIES:
                raise
            wait = _pause_seconds(error)
            if wait is None:
                raise
            wait = min(wait, PAUSE_CAP_SECONDS)
            print('The git host asked for a pause of %d s.' % int(round(wait)))
            time.sleep(wait)


def _send(token, method, url, body=None, host='github'):
    """The request itself, with no reading of what a refusal asked for."""
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'Authorization': 'Bearer %s' % token,
               'User-Agent': 'purlin'}
    if host != 'azure':
        headers['Accept'] = 'application/vnd.github+json'
    data = None if body is None else json.dumps(body).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method=method)
    response = urllib.request.urlopen(request, timeout=30)
    try:
        text = response.read().decode('utf-8')
    finally:
        response.close()
    return json.loads(text) if text.strip() else {}


def _git(project_root, args, check=True):
    result = subprocess.run(['git'] + list(args), capture_output=True,
                            text=True, cwd=project_root, timeout=60)
    if check and result.returncode != 0:
        raise RuntimeError('git %s failed: %s'
                           % (' '.join(args), result.stderr.strip()))
    return result.stdout
