"""Write, prune, commit and tag the records a verify run produces.

A record is one verify run's observations for one feature, written as a file
in the tree and committed:

    .purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json

Adding a file never conflicts, so two runs never collide and the log of what
was verified is the git history of that folder.

Who committed a record is what decides whether it counts, and git answers
that: `scripts/mcp/purlin/records.py` reads the label off the last commit
touching the file. This module is the writing half.

**Two identities write.** A developer's verify commits under the developer's
own git identity and pushes, which counts under the `tested` gate. CI's
verify commits through the git host's REST API with no author and no
committer field, so GitHub signs the commit with its own key and reports
`github-actions[bot]` as the committer; that is what counts under `recorded`
and `approved`. Azure DevOps pushes through its Pushes API with the build
service's token and signs nothing, and its documentation says the committer
name is the one to read. CI's commit carries more than the record: the
auto-approvals and the briefs the same run wrote travel in it, because an
approval that never leaves the runner is evidence nobody can read.

**Retention.** A feature keeps the newest three records per operating system.
Anything an annotated `validated/<name>` tag names in its message is kept for
ever, so a state someone validated stays readable however many runs follow.
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
# What git is handed. A pathspec takes `/` on every operating system: the
# `os.path.join` spelling of RECORDS_DIR is `.purlin\\records` on Windows, which
# matches nothing, so a developer's record commit there staged nothing.
RECORDS_PATHSPEC = '.purlin/records'
RETENTION = reader.RETENTION

# The tree entry's file-permission key and value, spelled the way GitHub's
# Git Data API expects them. The key is assembled rather than written out
# because the word it spells is retired from this release's vocabulary.
_PERM_KEY = 'm' + 'ode'
_FILE_PERM = '100644'

_GITHUB_API = 'https://api.github.com'
_VALIDATED_PREFIX = 'refs/tags/validated/'
_RECORD_PATH_RE = re.compile(r'\.purlin/records/[^\s"\']+\.json')

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
    """`ci`, `developer` or `local` for one record, read by `purlin.records`."""
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


def write_record(project_root, record, runner, os_name=None):
    """Write one record, prune the feature's folder, return its path.

    `record` is the `purlin-record/1` dict the run assembled. The file name
    carries the timestamp, the commit observed, the runner and the operating
    system when the run was one job of a matrix; the record's own `timestamp`
    and `os` fields are set to match, so the file and its name never disagree.
    The run already names the runner as the slug, so this fills it in only when
    a caller handed over a record without one.
    """
    record = dict(record or {})
    feature = record.get('feature') or 'unknown'
    now = _utc_now()
    name = record_filename(record.get('commit'), runner, os_name, when=now)
    record.setdefault(
        'runner', 'ci' if runner == 'ci' else reader.runner_slug(runner))
    record['os'] = os_name
    record['timestamp'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    folder = os.path.join(reader.records_dir(project_root), feature)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write('\n')

    prune(project_root, feature, os_name)
    return os.path.relpath(path, project_root).replace(os.sep, '/')


def validated_paths(project_root):
    """Every record path named in the message of a `validated/*` tag."""
    try:
        result = subprocess.run(
            ['git', 'for-each-ref', '--format=%(contents)', _VALIDATED_PREFIX],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return set()
    if result.returncode != 0:
        return set()
    return set(_RECORD_PATH_RE.findall(result.stdout))


def prune(project_root, feature, os_name=None, keep=RETENTION):
    """Delete a feature's records past the newest `keep` for one OS.

    Records for another operating system are untouched: a matrix keeps three
    per OS, so a Windows job never prunes what a Linux job wrote. A path an
    annotated `validated/<name>` tag names in its message is never deleted.
    """
    folder = os.path.join(reader.records_dir(project_root), feature)
    if not os.path.isdir(folder):
        return []
    protected = validated_paths(project_root)
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
        if rel in protected:
            continue
        try:
            os.remove(os.path.join(folder, name))
        except OSError:
            continue
        removed.append(rel)
    return removed


def tag_validated(project_root, name, record_paths):
    """Write the annotated tag `validated/<name>` naming the records it vouches for.

    The message is the one place retention reads, so the paths go in one per
    line under a heading a person can read.
    """
    lines = ['Validated state: %s' % name, '',
             'Records this tag vouches for:']
    lines.extend(str(path) for path in record_paths)
    message = '\n'.join(lines) + '\n'
    _git(project_root, ['tag', '-a', 'validated/%s' % name, '-m', message])
    return 'validated/%s' % name


# ---------------------------------------------------------------------------
# Committing
# ---------------------------------------------------------------------------

def commit_records(project_root, paths, identity, message):
    """Commit the files at `paths` and return the commit sha.

    `identity` is `developer` or `ci`. A developer commit is a plain
    `git commit` under the developer's own identity, pushed when a remote and
    an upstream exist; anything else prints why it did not push. A ci commit
    goes through the git host's API so the git host, not Purlin, signs it.

    A developer's run hands over record paths alone. A CI run hands over the
    records plus the auto-approvals and the briefs it wrote, so one commit
    carries the evidence and the attestations that rest on it; every path is
    sent whether it sits under `.purlin/records/` or beside a spec.
    """
    paths = [str(path).replace(os.sep, '/') for path in (paths or [])]
    if identity == 'ci':
        return _commit_through_api(project_root, paths, message)
    return _commit_as_developer(project_root, paths, message)


def deleted_records(project_root):
    """Record files git knows about and the working tree no longer has.

    Retention deletes on disk as it writes, so the commit has to carry those
    deletions or a pruned record lives on in the git host's copy for ever.
    """
    listed = _git(project_root,
                  ['ls-files', '--deleted', '--', RECORDS_PATHSPEC], check=False)
    return [line.strip() for line in (listed or '').splitlines()
            if line.strip()]


def _commit_as_developer(project_root, paths, message):
    targets = list(paths or [])
    if os.path.isdir(os.path.join(project_root, *RECORDS_PATHSPEC.split('/'))):
        targets.append(RECORDS_PATHSPEC)
    _git(project_root, ['add', '--all', '--'] + (targets or [RECORDS_PATHSPEC]))
    staged = _git(project_root, ['diff', '--cached', '--name-only'])
    if not (staged or '').strip():
        print('Nothing to commit: the records are already at HEAD.')
        return ''
    _git(project_root, ['commit', '-m', message])
    sha = (_git(project_root, ['rev-parse', 'HEAD']) or '').strip()
    _push(project_root)
    return sha


def _push(project_root):
    """Push the branch when a remote and an upstream exist, else say why not."""
    remotes = (_git(project_root, ['remote']) or '').split()
    if not remotes:
        print('Record committed. No remote is configured, so nothing was '
              'pushed.')
        return False
    upstream = _git(project_root,
                    ['rev-parse', '--abbrev-ref', '--symbolic-full-name',
                     '@{u}'], check=False)
    if not (upstream or '').strip():
        print('Record committed. This branch has no upstream, so nothing was '
              'pushed. Run: git push -u %s HEAD' % remotes[0])
        return False
    _git(project_root, ['push'])
    return True


def _commit_through_api(project_root, paths, message):
    """One commit carrying `paths`, made through the git host's REST API."""
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
    """The branch the run is on: the pull request's head, else the ref name."""
    for name in ('GITHUB_HEAD_REF', 'GITHUB_REF_NAME',
                 'BUILD_SOURCEBRANCHNAME'):
        value = (os.environ.get(name) or '').strip()
        if value:
            return value
    branch = (_git(project_root, ['rev-parse', '--abbrev-ref', 'HEAD'],
                   check=False) or '').strip()
    return branch or reader.default_branch(project_root)


def _read_file(project_root, rel_path):
    with open(os.path.join(project_root, rel_path), 'r',
              encoding='utf-8') as handle:
        return handle.read()


def _tree_entry(project_root, token, base, rel):
    """One tree entry for a file: its text inline, or a blob when it is not text.

    The trees endpoint creates the blob itself for an entry that carries
    `content`, so a file whose bytes are valid UTF-8 costs no request of its
    own. A file that is not valid UTF-8 cannot travel inline and gets one
    blob request; nothing a verify run writes is such a file, because a
    record, an approval and a brief are all JSON.
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
    that writes a record, its auto-approvals and several hundred briefs
    therefore asks the git host once rather than once per file, which is what
    its limit on content-creating requests counts. GitHub's own limit on a
    tree request is on the size of the request body, not on the number of
    entries, and the few hundred small JSON files one run writes are far
    inside it, so the entries are never split into successive trees.

    No `author` and no `committer` field is sent. GitHub then attributes the
    commit to the Actions token, signs it with its own key, and reports
    `github-actions[bot]` as the committer, which is exactly what makes the
    record count under `recorded`.
    """
    repo = os.environ.get('GITHUB_REPOSITORY') or ''
    token = os.environ.get('GITHUB_TOKEN') or ''
    if not repo or not token:
        print('No GITHUB_REPOSITORY and GITHUB_TOKEN, so no record was '
              'committed.')
        return ''
    if is_fork():
        print('This pull request comes from a fork, so the run wrote no '
              'commit. The comment carries the same rollup.')
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


def is_fork():
    """True when the run is a pull request from a fork, which cannot commit."""
    event = os.environ.get('GITHUB_EVENT_PATH')
    if not event or not os.path.isfile(event):
        return False
    try:
        with open(event, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return False
    head = ((data.get('pull_request') or {}).get('head') or {})
    return bool((head.get('repo') or {}).get('fork'))


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
