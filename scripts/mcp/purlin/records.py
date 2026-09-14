"""Read the records a verify run commits.

A record is one verify run's observations for one feature, written as a file
in the tree and committed:

    .purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json

`timestamp` is ISO 8601 UTC without separators (`20260913T120000Z`),
`commit7` the first seven characters of the commit the run observed, `runner`
the slug `ci` or the developer's git email local part (lowercased, every
non-alphanumeric character replaced by `-`), and `os` the operating system
when the run was one job of a matrix. Adding files never conflicts, so two
runs never collide and the log of what was verified is the git history of the
folder.

The file:

    {
      "schema_version": 1,
      "feature": "login",
      "commit": "<full sha>",
      "timestamp": "2026-09-13T12:00:00Z",
      "runner": "ci",
      "os": "linux",
      "gate": "recorded",
      "test_strength": 71,
      "scope_tree": "<sha256 from specs.scope_tree>",
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "status": "pass",
         "tier": "unit", "env": null,
         "test_file": "tests/test_login.py", "test_name": "test_rejects"}
      ]
    }

**The label comes from git, not from the file.** A file can claim anything.
The last commit touching a record is what decides whether it counts:

`ci`         the git host made the commit: on GitHub the committer email is
             `noreply@github.com` and the author is `github-actions[bot]`,
             on Azure DevOps the committer is the build service
`developer`  a person committed it
`local`      it is not committed at all

Under `tested` a record counts whether ci or developer wrote it. Under
`recorded` and `approved` only a ci record counts, which is what the git
host's file-path rule enforces on the other side.
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

# How many records a feature keeps per operating system before verify prunes.
RETENTION = 3


def records_dir(project_root):
    return os.path.join(project_root, RECORDS_DIR)


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


def signature_confirms(signature):
    """True when `%G?` does not contradict a commit the git host claims.

    `G` and `U` are a checked signature and confirm it. `B` is a signature
    that does not match the commit, which is the one answer that says the
    commit was changed after it was made. `N` is no signature at all, which
    is what git reports when it cannot run gpg, so it is read as a machine
    that cannot check rather than as an unsigned commit only when gpg is
    absent. Every other answer (`E`, `X`, `Y`, `R`) is a signature this
    machine holds no current key for, which is the ordinary case for the git
    host's own key and says nothing against the commit.
    """
    if signature == 'B':
        return False
    if signature == 'N':
        return shutil.which('gpg') is None
    return True


def record_label(project_root, rel_path):
    """`ci`, `developer` or `local` for one record, read from git.

    `git log -1 --format='%G? %cn %ce %an'` over the record's path names the
    signature status, the committer name and email and the author name of the
    last commit that touched it. No commit means the file is not committed,
    which is `local`.

    The identity decides and the signature confirms. A commit GitHub made
    through its API carries `GitHub <noreply@github.com>` as the committer
    and `github-actions[bot]` as the author, and it is signed with a key
    almost no checkout holds, so requiring a checked signature would throw
    away every record CI wrote.
    """
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%G?\t%cn\t%ce\t%an',
             '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return 'local'
    if result.returncode != 0 or not result.stdout.strip():
        return 'local'
    parts = result.stdout.strip().split('\t')
    parts += [''] * (4 - len(parts))
    signature, committer, committer_email, author = parts[:4]
    if committer in _AZURE_COMMITTERS:
        return 'ci'
    made_by_github = (committer in _GITHUB_COMMITTERS
                      or (committer_email == _GITHUB_COMMITTER_EMAIL
                          and author == _GITHUB_ACTIONS_AUTHOR))
    if made_by_github and signature_confirms(signature):
        return 'ci'
    return 'developer'


def counts_under(gate, label):
    """True when a record with `label` counts under `gate`.

    `tested` counts a ci or a developer record, because under `tested` the
    developer's own verify is the evidence. `recorded` and `approved` count a
    ci record only.
    """
    if label == 'local':
        return False
    if gate == 'tested':
        return label in ('ci', 'developer')
    return label == 'ci'


def load_records(project_root, ref=None):
    """`{feature: {os_or_None: record}}`, the latest record per feature per OS.

    `ref` is accepted so a caller can ask what a commit held rather than what
    the working tree holds; with a ref the files are read out of git, and
    without one they are read from disk. Each record dict carries the keys the
    file holds plus `path` (project-relative) and `label` (from git).
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
        timestamp, commit7, runner, os_name = parts
        feature = data.get('feature') or os.path.basename(os.path.dirname(rel_path))
        data = dict(data)
        data['path'] = rel_path
        data.setdefault('timestamp', _iso(timestamp))
        data.setdefault('runner', runner)
        data.setdefault('os', os_name)
        data['commit7'] = commit7
        data['label'] = ('local' if ref is None and not _is_tracked(project_root, rel_path)
                         else record_label(project_root, rel_path))
        slot = latest.setdefault(feature, {})
        current = slot.get(data.get('os'))
        if current is None or str(current.get('timestamp')) <= str(data['timestamp']):
            slot[data.get('os')] = data
    return latest


def _iso(compact):
    """`20260913T120000Z` as `2026-09-13T12:00:00Z`."""
    if len(compact) != 16:
        return compact
    return '%s-%s-%sT%s:%s:%sZ' % (compact[0:4], compact[4:6], compact[6:8],
                                   compact[9:11], compact[11:13], compact[13:15])


def _read_from_disk(project_root):
    root = records_dir(project_root)
    entries = []
    if not os.path.isdir(root):
        return entries
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
            except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError):
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


def _is_tracked(project_root, rel_path):
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0


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
    """The default branch name: what origin points at, else `main`."""
    try:
        result = subprocess.run(
            ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return 'main'
    if result.returncode != 0:
        return 'main'
    return result.stdout.strip().rsplit('/', 1)[-1] or 'main'


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
