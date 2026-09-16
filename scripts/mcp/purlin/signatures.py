"""Read the signatures and the holds a person committed.

One signature is one file, so two signatures never conflict:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json

`hash8` is the first eight characters of the triple hash the signature binds,
and the slug is the signer's email local part, lowercased, with every
non-alphanumeric character replaced by `-`. Every file in the directory was
written by a person: CI writes no signature, ever.

The file, field by field in `references/formats/signature_format.md`:

    {
      "schema": "purlin-signature/1",
      "feature": "login",
      "rule": "RULE-3",
      "triple": "<the first 16 characters of the triple hash>",
      "rule_hash": "<sha256 of the rule text>",
      "proof_hash": "<sha256 of the proof text>",
      "test_hash": "<sha256 of the test bodies>",
      "test_hash_kind": "file",
      "design_hash": null,
      "risk": "high",
      "signer": "jane@acme.com",
      "note": null,
      "timestamp": "2026-09-13T12:00:00Z",
      "gate": "signed",
      "brief": ".purlin/briefs/login/RULE-3.1a2b3c4d.brief.json",
      "record": ".purlin/records/login/20260913T120000Z-abc1234-ci.json"
    }

A signature is **current** when the three hashes it binds still equal the
recomputed ones and the risk it names still matches the rule's. Anything else
is a signature stale, and a person has to look. `design_hash` binds the pinned
design files for a rule whose origin is `design`.

A signature **counts** under the `signed` gate when the commit that added it
is signed (`%G?` is `G`), its author email is on the signer list as of that
commit, and that author differs from the author of the commit that last
touched the test. Under `strong` a signature from anyone counts, because what
it clears there is a question the machine could not settle.

A **hold** is the opposite attestation, from a person who read the brief and
found the test does not prove the proof as written:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<holder-slug>.hold.json

It binds the same hashes and carries the missing case as `reason`. While it is
current the rule needs a person, and a signature for the same hashes outranks
it.
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

SIGNATURE_NAME_RE = re.compile(r'^(RULE-\d+)\.([0-9a-f]{8})\.([a-z0-9-]+)\.json$')

# A brief written under the same first two parts would read as a signature by
# someone called `brief`, so the reader steps over that one slug.
_BRIEF_SLUG = 'brief'

# A hold carries a fourth part, so the signature pattern never reads one.
HOLD_NAME_RE = re.compile(
    r'^(RULE-\d+)\.([0-9a-f]{8})\.([a-z0-9-]+)\.hold\.json$')

# What the T of the triple was taken from, in the order one wins over another.
TEST_HASH_KINDS = ('file', 'manual', 'none')


def signer_slug(email):
    """The slug a signature file takes for an email address."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def triple_hash(rule_hash, proof_hash, test_hash):
    """The one hash a signature binds: rule text, proof text and test body."""
    digest = hashlib.sha256()
    digest.update(('%s\n%s\n%s' % (rule_hash or '', proof_hash or '',
                                   test_hash or '')).encode('utf-8'))
    return digest.hexdigest()


def test_hash_kind(proofs):
    """What the T of the triple was taken from, for the signature to record.

    `file` is a test file git tracks, which is what a hash over the tests
    reads. `manual` is a proof with no test at all: the evidence is the
    signer's note. `none` is a rule with nothing behind it yet.
    """
    kinds = set()
    for proof in proofs or ():
        if proof.get('tier') == 'manual':
            kinds.add('manual')
            continue
        if proof.get('tests'):
            kinds.add('file')
    for kind in TEST_HASH_KINDS:
        if kind in kinds:
            return kind
    return 'none'


def design_hash(owner_info, origin):
    """The D of the triple: the design a `origin: design` rule rests on.

    A design is a versioned file, so what binds the signature is the spec's
    `> Pinned:` hash of the exported files. A rule from any other origin binds
    no design and this is None.
    """
    if origin != 'design':
        return None
    return (owner_info or {}).get('pinned') or None


def signatures_dir(project_root, info):
    """The `<feature>.signatures/` directory beside a spec."""
    spec_path = info.get('spec_path', '')
    if not spec_path:
        return None
    base = os.path.join(project_root, os.path.dirname(spec_path))
    return os.path.join(base, os.path.basename(spec_path)[:-3] + '.signatures')


def load_signatures(project_root, features):
    """`{(feature, rule_id): [signature, ...]}` for every spec.

    Each signature dict carries the file's keys plus `path`, project-relative.
    """
    return _load_named(project_root, features, SIGNATURE_NAME_RE, _BRIEF_SLUG)


def load_holds(project_root, features):
    """`{(feature, rule_id): [hold, ...]}` for every spec, shaped the same way."""
    return _load_named(project_root, features, HOLD_NAME_RE, None)


def _load_named(project_root, features, name_re, skip_slug):
    found = {}
    for name, info in (features or {}).items():
        directory = signatures_dir(project_root, info)
        if not directory or not os.path.isdir(directory):
            continue
        for basename in sorted(os.listdir(directory)):
            m = name_re.match(basename)
            if not m or m.group(3) == skip_slug:
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
            data.setdefault('feature', name)
            data.setdefault('rule', m.group(1))
            found.setdefault((name, m.group(1)), []).append(data)
    return found


def is_current(signature, rule_hash, proof_hash, test_hash, risk,
               design_hash=None):
    """True when a signature still binds the text and the risk it was given for.

    Every part of the triple is compared, so changing a rule, rewording a
    proof or editing a test all stale the signature; the risk is compared too,
    because raising a rule from low to high is a change in what signing it
    meant.
    """
    if not signature:
        return False
    if str(signature.get('risk', '')) != str(risk):
        return False
    for key, value in (('rule_hash', rule_hash), ('proof_hash', proof_hash),
                       ('test_hash', test_hash)):
        if signature.get(key) != value:
            return False
    if signature.get('design_hash') or design_hash:
        if signature.get('design_hash') != design_hash:
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


def counts(project_root, signature, signers, test_paths=(), gate='signed'):
    """`(True, '')` when a signature counts under the gate, or `(False, reason)`.

    Whether the hashes still match is `is_current`; this answers who wrote the
    file and how. Under `passed` and `strong` a signature from anyone counts,
    because what it clears there is a question the machine could not settle.
    Under `signed` three conditions hold, each with its own reason so the
    status line can say which one failed: the signing commit is signed, its
    author is on the signer list, and that author is not the person who last
    touched the test. The fourth condition of the `signed` gate, that the
    signing commit is on the protected branch, is `is_ancestor`.
    """
    if not signature:
        return False, 'no signature'
    path = signature.get('path')
    if not path:
        return False, 'the signature is not committed'
    if gate != 'signed':
        return True, ''
    if not commit_is_signed(project_root, path):
        return False, 'the signing commit is not signed'
    author = commit_author(project_root, path)
    if signers and author not in signers:
        return False, 'the signer is not on the list'
    for test_path in test_paths or ():
        if commit_author(project_root, test_path) == author:
            return False, 'the signer last touched the test'
    return True, ''


def is_ancestor(project_root, rel_path, branch):
    """True when the commit that added a path is an ancestor of `branch`.

    Under `signed` the gate checks this, so a signature that only exists on a
    side branch does not let a change merge.
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
