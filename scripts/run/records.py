"""Write, prune and commit the records a run produces.

A record is one audit's observations for one feature, written as a file in
the tree and committed:

    .purlin/records/<source>/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json

Adding a file never conflicts, so two runs never collide and the log of what
ran is the git history of that folder.

**The folder is the source.** `purlin:audit` on a person's machine writes
under `.purlin/records/local/` and commits it under their own identity;
the CI job writes under `.purlin/records/ci/` and commits it through the git
host's API. Each record carries the same word in its own `source` field, and
`scripts/mcp/purlin/records.py` ignores a file where the two disagree. What
keeps the ci folder honest is the tag run: it reads the commit that added
each file under `ci/` and fails the job where the identity is not the
runner's own.

CI commits through the REST API with no author and no committer field, so
GitHub signs the commit with its own key and reports `github-actions[bot]`
as the committer; Azure DevOps pushes through its Pushes API with the build
service's token. Either commit carries more than the record: the briefs the
same run wrote travel in it, because a brief that never leaves the runner is
evidence nobody can read.

**Where CI commits.** On a run branch, and nowhere else. A run branch is what
`purlin:test --remote` creates for one run and deletes afterwards, so the
records it writes are pulled home by the command that asked for them. The
other run CI does is the tag run, and that one writes nothing at all: it
reruns the tests on a clean machine and verifies what is already committed.
`commits_here()` is the one question the run asks.

**Retention.** A feature keeps the newest three records per operating system
per source.
"""

import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import records as reader  # noqa: E402

RECORDS_DIR = reader.RECORDS_DIR
BRIEFS_DIR = reader.BRIEFS_DIR
SOURCES = reader.SOURCES
# What git is handed. A pathspec takes `/` on every operating system: the
# `os.path.join` spelling of RECORDS_DIR is `.purlin\\records` on Windows, which
# matches nothing, so a record commit made there staged nothing.
RECORDS_PATHSPEC = '.purlin/records'
LOCAL_RECORDS_PATHSPEC = '.purlin/records/local'
LOCAL_BRIEFS_PATHSPEC = '.purlin/briefs/local'

# What one commit of an audit's own evidence says, whoever made it.
RECORD_SUBJECT = 'purlin: record for %s'
RECORD_COMMITTED = 'Record committed.'
RECORD_UNCHANGED = 'Record unchanged.'
RECORD_NO_REPOSITORY = ('Record written; there is no git repository to commit '
                        'it to.')
RETENTION = reader.RETENTION

# The branch `purlin:test --remote` creates for one run, and the ref prefix
# a git host's own branch variable carries.
RUN_BRANCH_PREFIX = 'run/'
REF_HEADS = 'refs/heads/'
REF_TAGS = 'refs/tags/'
# The tag `purlin:sign` writes when every rule meets the gate, and the one
# ref besides a run branch that starts a CI run.
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
# Delegated readers, so a caller needs one import
# ---------------------------------------------------------------------------

def load_records(project_root, ref=None):
    """`{feature: {os_or_None: record}}`, read by `purlin.records`."""
    return reader.load_records(project_root, ref=ref)


def record_label(project_root, path):
    """`ci` or `local` for one record, read by `purlin.records`."""
    return reader.record_label(project_root, path)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _utc_now():
    """The current time in UTC, the one clock every timestamp reads."""
    return datetime.now(timezone.utc)


def record_filename(commit, runner, os_name=None, when=None):
    """`<timestamp>-<commit7>-<runner>[-<os>].json` for one run."""
    stamp = (when or _utc_now()).strftime('%Y%m%dT%H%M%SZ')
    commit7 = (str(commit or '') + '0000000')[:7]
    slug = 'ci' if runner == 'ci' else reader.runner_slug(runner)
    tail = '-%s' % os_name if os_name else ''
    return '%s-%s-%s%s.json' % (stamp, commit7, slug, tail)


def write_record(project_root, record, runner, os_name=None, source='local'):
    """Write one record, prune the feature's folder, return its path.

    `record` is the `purlin-record/3` dict the run assembled, and `source` is
    `ci` or `local`: the folder it goes in and the word its own `source`
    field carries, which a reader checks against each other. The file name
    carries the timestamp, the commit observed, the runner and the operating
    system when the run was one job of a matrix; the record's own `timestamp`
    and `os` fields are set to match, so the file and its name never disagree.
    The run already names the runner as the slug, so this fills it in only when
    a caller handed over a record without one.
    """
    record = dict(record or {})
    if source not in SOURCES:
        source = 'local'
    feature = record.get('feature') or 'unknown'
    now = _utc_now()
    name = record_filename(record.get('commit'), runner, os_name, when=now)
    record.setdefault(
        'runner', 'ci' if runner == 'ci' else reader.runner_slug(runner))
    record['os'] = os_name
    record['source'] = source
    record['timestamp'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    folder = os.path.join(reader.records_dir(project_root, source), feature)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write('\n')

    prune(project_root, feature, os_name, source=source)
    return os.path.relpath(path, project_root).replace(os.sep, '/')


def prune(project_root, feature, os_name=None, keep=RETENTION,
          source='local'):
    """Delete a feature's records past the newest `keep` for one OS.

    Records for another operating system are untouched: a matrix keeps three
    per OS, so a Windows job never prunes what a Linux job wrote. Records
    under the other source are untouched too: a local audit never prunes
    what CI wrote, and it could not, because the git host will not let it.
    """
    folder = os.path.join(reader.records_dir(project_root, source), feature)
    if not os.path.isdir(folder):
        return []
    candidates = []
    for name in os.listdir(folder):
        parts = reader.record_name_parts(name)
        if parts is None or parts[3] != os_name:
            continue
        candidates.append((parts[0], name))
    candidates.sort(reverse=True)

    removed = []
    for _stamp, name in candidates[keep:]:
        rel = os.path.relpath(os.path.join(folder, name),
                              project_root).replace(os.sep, '/')
        try:
            os.remove(os.path.join(folder, name))
        except OSError:
            continue
        removed.append(rel)
    return removed


# ---------------------------------------------------------------------------
# Committing
# ---------------------------------------------------------------------------

def commit_local_records(project_root, commit):
    """Commit a local audit's record and briefs under the person's identity.

    The same commit path `purlin:test` uses for the test results, because it
    is the same act: a person's own run writing its own evidence under their
    own name. Nothing here pushes, and nothing here touches
    `.purlin/records/ci/`, which the git host reserves for the build
    identity. The line to print comes back.
    """
    from results import commit_paths

    return commit_paths(
        project_root, [LOCAL_RECORDS_PATHSPEC, LOCAL_BRIEFS_PATHSPEC],
        RECORD_SUBJECT % (str(commit or '')[:7] or 'an unknown commit'),
        RECORD_COMMITTED, RECORD_UNCHANGED, RECORD_NO_REPOSITORY)


def commit_records(project_root, paths, message):
    """Commit the files at `paths` through the git host's API. The sha.

    The commit goes through the API so the git host, not Purlin, signs it:
    CI publishes its own evidence and a person pushes theirs. One CI run
    hands over the records plus the briefs it wrote, so one commit carries
    the evidence and the reports that rest on it; every path is sent whether
    it sits under `.purlin/records/` or under `.purlin/briefs/`.
    """
    paths = [str(path).replace(os.sep, '/') for path in (paths or [])]
    return _commit_through_api(project_root, paths, message)


def deleted_records(project_root):
    """Record files git knows about and the working tree no longer has.

    Retention deletes on disk as it writes, so the commit has to carry those
    deletions or a pruned record lives on in the git host's copy for ever.
    """
    listed = _git(project_root,
                  ['ls-files', '--deleted', '--', RECORDS_PATHSPEC], check=False)
    return [line.strip() for line in (listed or '').splitlines()
            if line.strip()]


def _commit_through_api(project_root, paths, message):
    """One commit carrying `paths`, made through the git host's REST API.

    A project that is not the workspace the job checked out commits nothing.
    A test suite driving an audit over a fixture project inherits the
    runner's token and repository name, and the API commit those name is the
    real repository's, not the fixture's: the fixture's records would land on
    the branch under review.
    """
    from ci import is_the_workspace

    if not is_the_workspace(project_root):
        print('%s is not the workspace this job checked out, so no record '
              'was committed.' % project_root)
        return ''
    host = detect_host()
    if host == 'azure':
        return _commit_azure(project_root, paths, message)
    return _commit_github(project_root, paths, message)


def detect_host():
    """`github`, `azure`, or `` when neither git host's CI is around."""
    if os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'):
        return 'azure'
    if os.environ.get('GITHUB_REPOSITORY'):
        return 'github'
    return ''


def current_branch(project_root):
    """The branch the run is on, read from the runner's own ref variables."""
    for name in ('GITHUB_REF_NAME', 'BUILD_SOURCEBRANCHNAME'):
        value = (os.environ.get(name) or '').strip()
        if value:
            return value
    branch = (_git(project_root, ['rev-parse', '--abbrev-ref', 'HEAD'],
                   check=False) or '').strip()
    return branch or reader.default_branch(project_root)


def ref_branch(project_root):
    """The branch the ref this run was started for names, run branch and all.

    `BUILD_SOURCEBRANCHNAME` is the last path part of an Azure DevOps ref, so
    `run/main-4f1c2ab` reaches it as `main-4f1c2ab` alone. The full ref is in
    `BUILD_SOURCEBRANCH`, and that is read first for exactly that reason.
    """
    for name in ('GITHUB_REF_NAME', 'BUILD_SOURCEBRANCH',
                 'BUILD_SOURCEBRANCHNAME'):
        value = (os.environ.get(name) or '').strip()
        if value:
            if value.startswith(REF_HEADS):
                return value[len(REF_HEADS):]
            return value
    return (_git(project_root, ['rev-parse', '--abbrev-ref', 'HEAD'],
                 check=False) or '').strip()


def is_a_tag_run():
    """True when this run was started by a tag push rather than a branch push.

    A tag run is the one `purlin:sign` asks for by writing `signed/<version>`
    and a person pushing it. It writes nothing: what it does is rerun the
    tests on a clean machine and check that the committed evidence still
    hashes to the tagged code. Only that tag counts: a release tag a project
    pushes for its own reasons is not a ref Purlin reads anything into.
    """
    signing = REF_TAGS + SIGNED_TAG_PREFIX
    for name in ('GITHUB_REF', 'BUILD_SOURCEBRANCH'):
        if (os.environ.get(name) or '').strip().startswith(signing):
            return True
    return False


def commits_here(project_root):
    """True when a CI run on this ref writes its records into the tree.

    A run branch is the only ref CI commits on: `purlin:test --remote`
    created it for one run, pulls the records home and deletes it. A tag run
    commits nothing, because it is there to verify rather than to write.

    Off a runner the answer is True: there is no branch rule to speak for,
    and a test suite driving the arm asked for this commit by name.
    """
    if not detect_host():
        return True
    if is_a_tag_run():
        return False
    return ref_branch(project_root).startswith(RUN_BRANCH_PREFIX)


def no_commit_line(project_root):
    """The one line a CI run prints where it commits nothing."""
    return ('Tag run: nothing is written. This run reruns the tests and '
            'checks the evidence already committed to %s.'
            % (ref_branch(project_root) or 'this ref'))


def _read_file(project_root, rel_path):
    with open(os.path.join(project_root, rel_path), 'r',
              encoding='utf-8') as handle:
        return handle.read()


def _tree_entry(project_root, token, base, rel):
    """One tree entry for a file: its text inline, or a blob when it is not text.

    The trees endpoint creates the blob itself for an entry that carries
    `content`, so a file whose bytes are valid UTF-8 costs no request of its
    own. A file that is not valid UTF-8 cannot travel inline and gets one
    blob request; nothing an audit run writes is such a file, because a
    record and a brief are both JSON.
    """
    with open(os.path.join(project_root, rel), 'rb') as handle:
        raw = handle.read()
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


def _commit_github(project_root, paths, message):
    """Tree, commit, ref update, retried when the branch moved.

    One tree request carries every path handed over, wherever in the tree it
    sits, plus a deletion entry for every record retention removed. A run
    that writes a record and several hundred briefs therefore asks the git
    host once rather than once per file, which is what
    its limit on content-creating requests counts. GitHub's own limit on a
    tree request is on the size of the request body, not on the number of
    entries, and the few hundred small JSON files one run writes are far
    inside it, so the entries are never split into successive trees.

    No `author` and no `committer` field is sent. GitHub then attributes the
    commit to the Actions token, signs it with its own key, and reports
    `github-actions[bot]` as the committer, which is exactly what gives the
    record the source `ci`.
    """
    repo = os.environ.get('GITHUB_REPOSITORY') or ''
    token = os.environ.get('GITHUB_TOKEN') or ''
    if not repo or not token:
        print('No GITHUB_REPOSITORY and GITHUB_TOKEN, so no record was '
              'committed.')
        return ''

    base = '%s/repos/%s/git' % (_GITHUB_API, repo)
    branch = current_branch(project_root)
    entries = [_tree_entry(project_root, token, base, rel) for rel in paths]
    for rel in deleted_records(project_root):
        entry = {'path': rel, 'type': 'blob', 'sha': None}
        entry[_PERM_KEY] = _FILE_PERM
        entries.append(entry)

    last_error = None
    for attempt in range(REF_RETRIES):
        head = _api(token, 'GET', base + '/ref/heads/%s' % branch)
        parent = head['object']['sha']
        parent_commit = _api(token, 'GET', base + '/commits/%s' % parent)
        tree = _api(token, 'POST', base + '/trees',
                    {'base_tree': parent_commit['tree']['sha'],
                     'tree': entries})
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


def _commit_azure(project_root, paths, message):
    """One push through the Azure DevOps Pushes API, retried when stale.

    The build service's token signs nothing, so the record is labelled `ci`
    on the committer name alone, which is what Azure DevOps documents.
    """
    token = os.environ.get('SYSTEM_ACCESSTOKEN') or ''
    collection = (os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')
                  or '').rstrip('/')
    project = os.environ.get('SYSTEM_TEAMPROJECT') or ''
    repo = os.environ.get('BUILD_REPOSITORY_ID') or ''
    if not (token and collection and project and repo):
        print('No Azure DevOps build variables, so no record was committed.')
        return ''

    base = '%s/%s/_apis/git/repositories/%s' % (collection, project, repo)
    branch = current_branch(project_root)
    ref = 'refs/heads/%s' % branch
    changes = [{'changeType': 'add',
                'item': {'path': '/' + rel},
                'newContent': {'content': _read_file(project_root, rel),
                               'contentType': 'rawtext'}}
               for rel in paths]

    last_error = None
    for attempt in range(REF_RETRIES):
        refs = _api(token, 'GET',
                    '%s/refs?filter=heads/%s&api-version=7.0' % (base, branch),
                    host='azure')
        values = refs.get('value') or []
        old = values[0]['objectId'] if values else '0' * 40
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
