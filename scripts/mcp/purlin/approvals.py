"""Read the approvals a person or CI committed.

One approval is one file, so two approvals never conflict:

    specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.<approver-slug>.json
    specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.ci.json

`hash8` is the first eight characters of the triple hash the approval binds,
and the slug is the approver's email local part, lowercased, with every
non-alphanumeric character replaced by `-`. A CI auto-approval takes `ci` in
place of a slug.

The file:

    {
      "feature": "login",
      "rule": "RULE-3",
      "risk": "high",
      "approver": "jane@acme.com",
      "approved_at": "2026-09-13T12:00:00Z",
      "rule_hash": "<sha256 of the rule text>",
      "proof_hash": "<sha256 of the proof text>",
      "test_hash": "<sha256 of the test bodies>",
      "design_hash": null,
      "brief_hash": "<sha256 of the brief the approver read>",
      "record": ".purlin/records/login/20260913T120000Z-abc1234-ci.json",
      "triple_hash": "<sha256 of the three above>"
    }

An approval is **current** when the three hashes it binds still equal the
recomputed ones and the risk it names still matches the rule's. Anything else
is Stale, and a person has to look. `design_hash` binds the pinned design
files for a rule whose origin is `design`.

An approval **counts** when its commit is signed (`%G?` is `G`), its author
email is on the approver list as of that commit, and that author differs from
the author of the commit that last touched the test.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

_APPROVAL_NAME_RE = re.compile(r'^(RULE-\d+)\.([0-9a-f]{8})\.([a-z0-9-]+)\.json$')


def approver_slug(email):
    """The slug an approval file takes for an email address."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def triple_hash(rule_hash, proof_hash, test_hash):
    """The one hash an approval binds: rule text, proof text and test body."""
    digest = hashlib.sha256()
    digest.update(('%s\n%s\n%s' % (rule_hash or '', proof_hash or '',
                                   test_hash or '')).encode('utf-8'))
    return digest.hexdigest()


def approvals_dir(project_root, info):
    """The `<feature>.approvals/` directory beside a spec."""
    spec_path = info.get('spec_path', '')
    if not spec_path:
        return None
    base = os.path.join(project_root, os.path.dirname(spec_path))
    return os.path.join(base, os.path.basename(spec_path)[:-3] + '.approvals')


def load_approvals(project_root, features):
    """`{(feature, rule_id): [approval, ...]}` for every spec.

    Each approval dict carries the file's keys plus `path` (project-relative)
    and `is_ci` (the file's slug was `ci`).
    """
    found = {}
    for name, info in (features or {}).items():
        directory = approvals_dir(project_root, info)
        if not directory or not os.path.isdir(directory):
            continue
        for basename in sorted(os.listdir(directory)):
            m = _APPROVAL_NAME_RE.match(basename)
            if not m:
                continue
            path = os.path.join(directory, basename)
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    data = json.load(handle)
            except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            data = dict(data)
            data['path'] = os.path.relpath(path, project_root).replace(os.sep, '/')
            data['is_ci'] = m.group(3) == 'ci'
            data.setdefault('feature', name)
            data.setdefault('rule', m.group(1))
            found.setdefault((name, m.group(1)), []).append(data)
    return found


def is_current(approval, rule_hash, proof_hash, test_hash, risk,
               design_hash=None):
    """True when an approval still binds the text and the risk it was given for.

    Every part of the triple is compared, so changing a rule, rewording a
    proof or editing a test all stale the approval; the risk is compared too,
    because raising a rule from low to high is a change in what approving it
    meant.
    """
    if not approval:
        return False
    if str(approval.get('risk', '')) != str(risk):
        return False
    for key, value in (('rule_hash', rule_hash), ('proof_hash', proof_hash),
                       ('test_hash', test_hash)):
        if approval.get(key) != value:
            return False
    if approval.get('design_hash') or design_hash:
        if approval.get('design_hash') != design_hash:
            return False
    return True


def commit_is_signed(project_root, rel_path):
    """True when the last commit touching a path is signed (`%G?` is `G`)."""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%G?', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0 and result.stdout.strip() == 'G'


def commit_author(project_root, rel_path):
    """The author email of the last commit touching a path, lowercased."""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ae', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    if result.returncode != 0:
        return ''
    return result.stdout.strip().lower()


def counts(project_root, approval, approvers, test_paths=()):
    """`(True, '')` when an approval counts, or `(False, reason)`.

    Three conditions, each with its own reason so the status line can say
    which one failed: the commit is signed, the author is on the approver
    list, and the author is not the person who last touched the test.
    A CI auto-approval is exempt from all three; what bounds it is the
    auto-approval rule in `states.py`.
    """
    if not approval:
        return False, 'no approval'
    if approval.get('is_ci'):
        return True, ''
    path = approval.get('path')
    if not path:
        return False, 'approval is not committed'
    if not commit_is_signed(project_root, path):
        return False, 'the approval commit is not signed'
    author = commit_author(project_root, path)
    if approvers and author not in approvers:
        return False, 'the approval author is not on the approver list'
    for test_path in test_paths or ():
        if commit_author(project_root, test_path) == author:
            return False, 'the approver last touched the test'
    return True, ''


def is_ancestor(project_root, rel_path, branch):
    """True when the commit that added a path is an ancestor of `branch`.

    Under `approved` the gate checks this, so an approval that only exists on
    a side branch does not let a change merge.
    """
    try:
        commit = subprocess.run(
            ['git', 'log', '-1', '--format=%H', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    sha = commit.stdout.strip()
    if commit.returncode != 0 or not sha:
        return False
    try:
        result = subprocess.run(
            ['git', 'merge-base', '--is-ancestor', '--end-of-options',
             sha, branch],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0
