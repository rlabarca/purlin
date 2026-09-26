"""Read the records an audit commits.

A record is one audit's observations for one feature, written as a file in
the tree and committed:

    .purlin/records/<source>/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json

`source` is `ci` or `local`, and it is the folder the file sits in.
`timestamp` is ISO 8601 UTC without separators (`20260913T120000Z`),
`commit7` the first seven characters of the commit the run observed, `runner`
the slug `ci` or a git email's local part (lowercased, every non-alphanumeric
character replaced by `-`), and `os` the operating system
when the run was one job of a matrix. Adding files never conflicts, so two
runs never collide and the log of every run is the git history of the
folder.

The file:

    {
      "schema_version": 3,
      "feature": "login",
      "source": "ci",
      "commit": "<full sha>",
      "timestamp": "2026-09-13T12:00:00Z",
      "runner": "ci",
      "os": "linux",
      "gate": "strong",
      "test_strength": 71,
      "scope_tree": "<sha256 from specs.scope_tree>",
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "status": "pass",
         "tier": "unit", "env": null,
         "test_file": "tests/test_login.py", "test_name": "test_rejects"}
      ]
    }

**The folder is the source, and the file must agree.** A record under
`.purlin/records/ci/` carries `"source": "ci"` and one under
`.purlin/records/local/` carries `"source": "local"`. A file whose own field
disagrees with its folder is ignored, with one warning naming the path: the
two halves of one fact cannot be read apart. What keeps the folder honest is
the git host, whose file-path rule restricts `.purlin/records/ci/**` to the
CI identity, so only CI can put a file there.

`ci` and `local` both count under `passed` and under `strong`: an audit a
person ran measures the same breaks CI measures. Under `signed` only `ci`
counts, because the run on the protected branch after the merge is what a
signature attaches to and a local run there is a preview.
"""

import json
import os
import re
import shutil
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

RECORDS_DIR = os.path.join('.purlin', 'records')
BRIEFS_DIR = os.path.join('.purlin', 'briefs')

# The two source folders, most trusted first. A record's source is the folder
# it sits in, and the file's own `source` field must say the same.
SOURCES = ('ci', 'local')

# `<timestamp>-<commit7>-<runner>[-<os>].json`
_RECORD_NAME_RE = re.compile(
    r'^(\d{8}T\d{6}Z)-([0-9a-f]{7})-([a-z0-9-]+?)'
    r'(?:-(windows|macos|linux))?\.json$')

# The Azure DevOps build identities. Azure DevOps signs nothing, so its
# commits are read on the committer name alone, which its documentation says.
_AZURE_COMMITTERS = ('Project Collection Build Service', 'Azure DevOps')

# What a commit GitHub made through its API looks like. GitHub signs the
# commit with its own key and records its web identity as the committer, so
# the committer is `GitHub <noreply@github.com>` and the Actions token is the
# author. Reading the committer name alone misses it.
_GITHUB_COMMITTERS = ('github-actions[bot]', 'github-actions')
_GITHUB_COMMITTER_EMAIL = 'noreply@github.com'
_GITHUB_ACTIONS_AUTHOR = 'github-actions[bot]'

# How many records a feature keeps per operating system before a run prunes.
RETENTION = 3


def records_dir(project_root, source=None):
    """`.purlin/records/`, or one source's folder inside it."""
    if source is None:
        return os.path.join(project_root, RECORDS_DIR)
    return os.path.join(project_root, RECORDS_DIR, source)


def briefs_dir(project_root, source=None):
    """`.purlin/briefs/`, or one source's folder inside it."""
    if source is None:
        return os.path.join(project_root, BRIEFS_DIR)
    return os.path.join(project_root, BRIEFS_DIR, source)


def record_path(source, feature, name):
    """The project-relative path of one record, with `/` on every system."""
    return '%s/%s/%s/%s' % (RECORDS_DIR.replace(os.sep, '/'), source,
                            feature, name)


def source_of_path(rel_path):
    """The source folder a record path sits in, or None when it is elsewhere.

    A path is `.purlin/records/<source>/<feature>/<file>.json`, so the source
    is the third part. A record still under the pre-0.10.0 layout, with no
    source folder at all, answers None and is not read; `purlin:init --update`
    moves it into the folder its own source names.
    """
    parts = str(rel_path or '').replace(os.sep, '/').split('/')
    if len(parts) < 4 or parts[0] != '.purlin' or parts[1] != 'records':
        return None
    return parts[2] if parts[2] in SOURCES else None


DISAGREES = ('%s says its source is %s and sits under %s, so it is ignored. '
             'A record\'s folder and its source field must agree.')


def record_source(rel_path, data):
    """`(source, warning)` for one record: its folder, checked against the file.

    The folder is the source, because the git host's file-path rule on
    `.purlin/records/ci/**` is what keeps a person out of it. The file's own
    `source` field is the same fact written twice, so a file that disagrees
    with its folder is not read at all: guessing which half is right would
    let a copied file claim a source no rule enforces.
    """
    folder = source_of_path(rel_path)
    if folder is None:
        return None, None
    claimed = (data or {}).get('source')
    if claimed is not None and claimed != folder:
        return None, DISAGREES % (rel_path, claimed, folder)
    return folder, None


def runner_slug(email):
    """The runner slug for a git email: its local part, lowercased, `-` safe."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def record_name_parts(basename):
    """`(timestamp, commit7, runner, os)` for a record filename, or None."""
    m = _RECORD_NAME_RE.match(basename)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


def signature_confirms(signature, signed=False):
    """True when `%G?` does not contradict a commit the git host claims.

    `G` and `U` are a checked signature and confirm it. `B` is a signature
    that does not match the commit, which is the one answer that says the
    commit was changed after it was made. Every other answer (`E`, `X`, `Y`,
    `R`) is a signature this machine holds no current key for, which is the
    ordinary case for the git host's own key and says nothing against the
    commit.

    `N` is the one answer that means two things. git prints it both for a
    commit that carries no signature at all and for a commit whose signature
    it could not even try to check, which is what an ssh signature read by a
    checkout with no allowed-signers file is. `signed` says which: with a
    signature on the commit, `N` is a machine that cannot check and the
    commit stands; with none, it is an unsigned commit, and then the only
    reason to let it stand is a machine with no gpg, where every commit reads
    as unsigned.
    """
    if signature == 'B':
        return False
    if signature == 'N':
        return signed or shutil.which('gpg') is None
    return True


def carries_a_signature(project_root, commit):
    """True when the commit object holds a signature header.

    `git cat-file commit` prints the commit's headers before a blank line and
    its message after, and a signed commit carries a `gpgsig` header among
    them whether or not this machine can check it. That is the one reading
    that tells `%G?` `N` for "no signature" apart from `N` for "no way to
    check this one".
    """
    try:
        result = subprocess.run(
            ['git', 'cat-file', 'commit', commit],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.split('\n'):
        if not line.strip():
            return False
        if line.startswith('gpgsig'):
            return True
    return False


def record_label(project_root, rel_path):
    """`ci` or `local` for one record, read from git.

    What a record's source is, is its folder. This reads the other answer:
    who committed the file. `purlin:init --update` is what asks, once, when
    it moves a record written before the folders existed into the folder its
    committer names.

    `git log -1 --format='%G? %cn %ce %an %H'` over the record's path names
    the signature status, the committer name and email, the author name and
    the commit of the last commit that touched it. No commit means the file
    is not committed, which is `local`.

    The identity decides and the signature confirms. A commit GitHub made
    through its API carries `GitHub <noreply@github.com>` as the committer
    and `github-actions[bot]` as the author, and it is signed with a key
    almost no checkout holds, so requiring a checked signature would throw
    away every record CI wrote.
    """
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%G?\t%cn\t%ce\t%an\t%H',
             '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return 'local'
    if result.returncode != 0 or not result.stdout.strip():
        return 'local'
    # `%G?` prints nothing at all when git neither found nor could look for a
    # signature, so the first field is empty and stripping the whole line
    # would move every field one place to the left.
    parts = result.stdout.split('\n', 1)[0].split('\t')
    parts += [''] * (5 - len(parts))
    signature, committer, committer_email, author, commit = parts[:5]
    if committer in _AZURE_COMMITTERS:
        return 'ci'
    made_by_github = (committer in _GITHUB_COMMITTERS
                      or (committer_email == _GITHUB_COMMITTER_EMAIL
                          and author == _GITHUB_ACTIONS_AUTHOR))
    if not made_by_github:
        return 'local'
    signed = (signature == 'N'
              and carries_a_signature(project_root, commit))
    if signature_confirms(signature, signed):
        return 'ci'
    return 'local'


def counts_under(gate, source):
    """True when a record from `source` counts under `gate`.

    `passed` and `strong` count both sources. At `passed` the question is
    only whether the tests pass, and a person's own run answers it; at
    `strong` the question is how good the tests are, and the breaks a person
    ran are the same breaks CI runs. `signed` counts a ci record alone,
    because a signature attaches to the run on the protected branch after the
    merge, and a local run there is a preview.
    """
    if gate in ('passed', 'strong'):
        return source in SOURCES
    return source == 'ci'


def load_records(project_root, ref=None, warnings=None):
    """`{feature: {os_or_None: record}}`, the latest record per feature per OS.

    `ref` is accepted so a caller can ask what a commit held rather than what
    the working tree holds; with a ref the files are read out of git, and
    without one they are read from disk. Each record dict carries the keys the
    file holds plus `path` (project-relative), `source` (its folder) and
    `label`, which is the same word under the name schema 5 gave it.

    A record whose `source` field disagrees with its folder is left out and
    one warning naming it is appended to `warnings`, when a list was handed
    in. Where a feature has both a ci and a local record for one operating
    system, the newer answers; where they are the same age, ci does, because
    it is the one every checkout reads alike.
    """
    if ref:
        entries = _read_at_ref(project_root, ref)
    else:
        entries = _read_from_disk(project_root)

    latest = {}
    for rel_path, data in entries:
        parts = record_name_parts(os.path.basename(rel_path))
        if parts is None:
            continue
        source, warning = record_source(rel_path, data)
        if warning is not None:
            if warnings is not None and warning not in warnings:
                warnings.append(warning)
            continue
        if source is None:
            continue
        timestamp, commit7, runner, os_name = parts
        feature = data.get('feature') or os.path.basename(os.path.dirname(rel_path))
        data = dict(data)
        data['path'] = rel_path
        data.setdefault('timestamp', _iso(timestamp))
        data.setdefault('runner', runner)
        data.setdefault('os', os_name)
        data['commit7'] = commit7
        data['source'] = source
        data['label'] = source
        slot = latest.setdefault(feature, {})
        current = slot.get(data.get('os'))
        if current is None or _newer(data, current):
            slot[data.get('os')] = data
    return latest


def _newer(candidate, held):
    """True when `candidate` answers for its operating system over `held`."""
    one = str(candidate.get('timestamp') or '')
    other = str(held.get('timestamp') or '')
    if one != other:
        return one > other
    return (SOURCES.index(candidate['source'])
            <= SOURCES.index(held['source']))


def _iso(compact):
    """`20260913T120000Z` as `2026-09-13T12:00:00Z`."""
    if len(compact) != 16:
        return compact
    return '%s-%s-%sT%s:%s:%sZ' % (compact[0:4], compact[4:6], compact[6:8],
                                   compact[9:11], compact[11:13], compact[13:15])


def _read_from_disk(project_root):
    """`[(rel_path, data)]` for every record under a source folder."""
    entries = []
    for source in SOURCES:
        root = records_dir(project_root, source)
        if not os.path.isdir(root):
            continue
        for feature in sorted(os.listdir(root)):
            feature_dir = os.path.join(root, feature)
            if not os.path.isdir(feature_dir):
                continue
            for name in sorted(os.listdir(feature_dir)):
                if not name.endswith('.json'):
                    continue
                path = os.path.join(feature_dir, name)
                try:
                    with open(path, 'r', encoding='utf-8') as handle:
                        data = json.load(handle)
                except (json.JSONDecodeError, IOError, OSError,
                        UnicodeDecodeError):
                    continue
                if isinstance(data, dict):
                    entries.append((os.path.relpath(path, project_root)
                                    .replace(os.sep, '/'), data))
    return entries


def _read_at_ref(project_root, ref):
    try:
        listing = subprocess.run(
            ['git', 'ls-tree', '-r', '--name-only', '--end-of-options', ref,
             '--', RECORDS_DIR.replace(os.sep, '/')],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return []
    if listing.returncode != 0:
        return []
    entries = []
    for rel_path in listing.stdout.splitlines():
        rel_path = rel_path.strip()
        if not rel_path.endswith('.json'):
            continue
        try:
            blob = subprocess.run(
                ['git', 'show', '--end-of-options', '%s:%s' % (ref, rel_path)],
                capture_output=True, text=True, cwd=project_root, timeout=15)
        except (subprocess.SubprocessError, OSError):
            continue
        if blob.returncode != 0:
            continue
        try:
            data = json.loads(blob.stdout)
        except ValueError:
            continue
        if isinstance(data, dict):
            entries.append((rel_path, data))
    return entries



def head_sha(project_root):
    """The full sha at HEAD, or None outside a git checkout."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def default_branch(project_root):
    """The default branch name: what origin points at, else the branch HEAD is
    on, else `main`.

    A repository with a remote answers this outright. One with no remote, or
    one whose `origin/HEAD` was never set, has only its own branch to go on,
    and `main` is a guess that is wrong for every repository made by a git
    still configured for `master`: the gate would then tell a developer their
    signature is not on the branch when it is the only branch there is.
    """
    try:
        # The whole ref comes back here, and the branch is its last part.
        result = subprocess.run(
            ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
        if result.returncode == 0:
            named = result.stdout.strip().rsplit('/', 1)[-1]
            if named:
                return named
        # The branch itself comes back here, and a branch name may hold a
        # slash of its own, so nothing is cut off it. A detached head has no
        # branch to name and the command fails, which leaves `main`.
        result = subprocess.run(
            ['git', 'symbolic-ref', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return 'main'
    if result.returncode != 0:
        return 'main'
    return result.stdout.strip() or 'main'


def at_head(record, head):
    """True when a record observed the commit the working tree is on."""
    if not head or not record:
        return False
    commit = record.get('commit') or ''
    return bool(commit) and (commit == head or head.startswith(commit)
                             or commit.startswith(head))


def proof_statuses(record):
    """`{proof_id: status}` for one record's observations."""
    statuses = {}
    for entry in (record or {}).get('proofs', []) or ():
        if not isinstance(entry, dict):
            continue
        proof_id = entry.get('id')
        if not proof_id:
            continue
        if statuses.get(proof_id) == 'fail':
            continue
        statuses[proof_id] = entry.get('status')
    return statuses
