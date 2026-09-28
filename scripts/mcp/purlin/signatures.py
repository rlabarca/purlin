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
      "audit_hash": "<sha256 of the brief's evidence>",
      "bar": "strong",
      "signer": "jane@acme.com",
      "note": null,
      "timestamp": "2026-09-13T12:00:00Z",
      "gate": "signed",
      "brief": ".purlin/briefs/ci/login/RULE-3.1a2b3c4d.brief.json",
      "record": ".purlin/records/ci/login/20260913T120000Z-abc1234-ci.json"
    }

A signature is **current** when the hashes it binds still equal the
recomputed ones and the bar it names still matches the rule's. Anything else
is a signature stale, and a person has to look. `design_hash` binds the pinned
design files for a rule whose origin is `design`.

`audit_hash` is what locks the audit in beside the rule, the proof and the
test. It is taken over the brief's own evidence: the test strength, the
observations sorted, and whether the audit settled. A re-audit that observes
something different stales the signature, because what was signed was a rule
whose tests an audit had read and found nothing in. Timestamps and commit ids
are not hashed, so running the same audit again over the same code changes
nothing. A rule with no brief carries the hash of the empty string, and one
whose first audit writes a brief is stale from that moment, which is the
honest answer: there is evidence now that there was not before.

A signature **counts** under the `signed` gate when the commit that added it
is signed and the signature verifies (`%G?` is `G`), and its hashes are
current. Who signed is logged, not policed: the file names the signer and
git names the commit's author, and neither is compared with anything. Below
`signed` a committed signature counts.

A **hold** is the opposite attestation, from a person who read the brief and
found the test does not prove the proof as written:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<holder-slug>.hold.json

It binds the same hashes and carries the missing case as `reason`. While it is
current the rule's strong and signed cells read `held`, and a signature for the
same hashes outranks it.
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


def audit_hash(brief):
    """The A a signature binds: what the audit found, and nothing else.

    The strength, the observations in a fixed order and whether the audit
    settled. Nothing that moves on its own goes in: a timestamp, a commit id
    or the path of the record would stale every signature on the next run of
    the same audit over the same code. A rule with no brief hashes the empty
    string, so a rule whose first audit writes a brief goes stale, which is
    what a person should be asked about.
    """
    if not brief:
        return hashlib.sha256(b'').hexdigest()
    strength = brief.get('test_strength')
    settled = brief.get('settled')
    observations = sorted(str(line) for line in
                          (brief.get('observations') or ()))
    parts = ['n/a' if strength is None else str(int(strength)),
             'none' if settled is None else ('yes' if settled else 'no')]
    parts.extend(observations)
    digest = hashlib.sha256()
    digest.update('\n'.join(parts).encode('utf-8'))
    return digest.hexdigest()


def test_hash_kind(proofs):
    """What the T of the triple was taken from, for the signature to record.

    `file` is a test file git tracks, which is what a hash over the tests
    reads. `manual` is a proof with no test at all: the evidence is the
    signer's note. `none` is a rule with nothing behind it yet.
    """
    kinds = set()
    for proof in proofs or ():
        if proof.get('manual'):
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


def is_current(signature, rule_hash, proof_hash, test_hash, bar,
               design_hash=None, audit=None):
    """True when a signature still binds what it was given for.

    Every part of the triple is compared, so changing a rule, rewording a
    proof or editing a test all stale the signature. The bar is compared too,
    because raising a rule from `passed` to `strong` is a change in what
    signing it meant, and so is the audit's own evidence: a re-audit that
    observes something different is a new answer to the question the signer
    was answering.
    """
    if not signature:
        return False
    if str(signature.get('bar', '')) != str(bar):
        return False
    for key, value in (('rule_hash', rule_hash), ('proof_hash', proof_hash),
                       ('test_hash', test_hash)):
        if signature.get(key) != value:
            return False
    if signature.get('design_hash') or design_hash:
        if signature.get('design_hash') != design_hash:
            return False
    if audit is not None and str(signature.get('audit_hash') or '') != str(audit):
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


def commit_date(project_root, rel_path):
    """When the last commit touching a path was authored, ISO 8601 UTC, or None.

    The signed cell shows when a rule was signed, and the commit date is the
    answer git can vouch for: the file's own `timestamp` is what the writer
    put in it, and the commit is what a reader can check.
    """
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--date=format-local:%Y-%m-%dT%H:%M:%SZ',
             '--format=%ad', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10,
            env=dict(os.environ, TZ='UTC'))
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def counts(project_root, signature, gate='signed'):
    """`(True, '')` when a signature counts under the gate, or `(False, reason)`.

    Whether the hashes still match is `is_current`; this answers how the file
    was committed. Below `signed` a committed signature counts. Under
    `signed` the commit that added it must be signed and verify, and that is
    all: the signature counts on whatever commit carries it, whoever wrote
    it and whoever last committed to the test file.
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
    return True, ''
