"""Read the signatures a person committed.

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
      "test_hash": "<sha256 of the test files' blob ids>",
      "test_hash_kind": "file",
      "audit_hash": "<sha256 of what the audit found>",
      "level": "signed",
      "signer": "jane@acme.com",
      "machine": "jane-laptop",
      "os": "macos",
      "note": null,
      "timestamp": "2026-09-13T12:00:00Z",
      "gate": "signed",
      "evidence": ".purlin/evidence/local/login.json"
    }

A signature is **current** when the hashes it binds still equal the
recomputed ones. Anything else is a signature stale, and a person has to
look. `level` logs the rule's level when it was signed; it is logged, not
compared, so marking a rule differently stales nothing. `machine` and `os`
log where it was made, the host's name and `windows`, `macos` or `linux`;
neither is hashed or compared.

`audit_hash` is what locks the audit in beside the rule, the proof and the
test. It is taken over what the audit found: the test strength, the audit
entry's `verdict` and its `findings` sorted. A re-audit that finds something
different stales the signature, because what was signed was a rule whose
tests an audit had read. Timestamps and commit ids are not hashed, so running
the same audit again over the same code changes nothing. A rule with no audit
entry carries the hash of the empty string, and one whose first audit writes
an entry is stale from that moment, which is the honest answer: there is
evidence now that there was not before.

A signature **counts** under the `signed` gate when the commit that added it
is signed and the signature verifies (`%G?` is `G`), and its hashes are
current. Who signed is logged, not policed: the file names the signer and
git names the commit's author, and neither is compared with anything. Below
`signed` a committed signature counts.
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

# What the T of the triple was taken from, in the order one wins over another.
TEST_HASH_KINDS = ('file', 'manual', 'none')


def signer_slug(email):
    """The slug a signature file takes for an email address."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def triple_hash(rule_hash, proof_hash, test_hash):
    """The one hash a signature binds: rule text, proof text and test files."""
    digest = hashlib.sha256()
    digest.update(('%s\n%s\n%s' % (rule_hash or '', proof_hash or '',
                                   test_hash or '')).encode('utf-8'))
    return digest.hexdigest()


def audit_hash(entry, strength=None):
    """The A a signature binds: what the audit found, and nothing else.

    `entry` is the evidence's audit entry for the rule's current hashes and
    `strength` the feature's test strength. The strength, the `verdict` and
    the `findings` in a fixed order. Nothing that moves on its own goes in: a
    timestamp, a commit id or a path would stale every signature on the next
    run of the same audit over the same code. A rule with no entry hashes the
    empty string, so a rule whose first audit writes one goes stale, which is
    what a person should be asked about.
    """
    if not entry:
        return hashlib.sha256(b'').hexdigest()
    findings = sorted(str(line) for line in (entry.get('findings') or ()))
    parts = ['n/a' if strength is None else str(int(strength)),
             str(entry.get('verdict') or '')]
    parts.extend(findings)
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
    found = {}
    for name, info in (features or {}).items():
        directory = signatures_dir(project_root, info)
        if not directory or not os.path.isdir(directory):
            continue
        for basename in sorted(os.listdir(directory)):
            m = SIGNATURE_NAME_RE.match(basename)
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
            found.setdefault((name, m.group(1)), []).append(data)
    return found


# The fields of a rule entry `is_current` compares, in the order they are
# read. `signed_hash` is the one hash format 11 of the signature stores.
BOUND_FIELDS = ('rule_hash', 'proof_hash', 'test_hash', 'audit_hash')


def signed_hash(entry):
    """sha256 over the seven lines a signature is made over.

    `applies_to`, `rule_hash`, `proof_hash`, `test_hash`, `code_hash`,
    `audit_hash`, and `machines` written as `os=machine` pairs, sorted and
    joined with `,`. `entry` is a payload rule entry, or a signature, which
    carries the same fields; a field it lacks reads as the empty string.
    """
    machines = entry.get('machines') or {}
    pairs = ','.join(sorted('%s=%s' % (name, machines[name] or '')
                            for name in machines))
    lines = [str(entry.get(key) or '') for key in (
        'applies_to', 'rule_hash', 'proof_hash', 'test_hash', 'code_hash',
        'audit_hash')]
    lines.append(pairs)
    digest = hashlib.sha256()
    digest.update('\n'.join(lines).encode('utf-8'))
    return digest.hexdigest()


def is_current(signature, entry):
    """True when a signature still binds the rule entry it is compared with.

    `entry` is the payload's rule entry, or any dict carrying its hashes.
    Every part of the triple is compared, so changing a rule, rewording a
    proof or editing a test all stale the signature. So is the audit's own
    evidence: a re-audit that observes something different is a new answer
    to the question the signer was answering, compared wherever the entry
    carries an `audit_hash`. The level the signature logs is not compared.
    """
    if not signature or entry is None:
        return False
    for key in BOUND_FIELDS[:3]:
        if signature.get(key) != entry.get(key):
            return False
    audit = entry.get('audit_hash')
    if audit is not None and str(signature.get('audit_hash') or '') != str(
            audit):
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


def counts(project_root, signature):
    """`(True, '')` when a signature counts, or `(False, reason)`.

    Whether the hashes still match is `is_current`; this answers how the file
    was committed. Below the project's gate `signed` a committed signature
    counts. At `signed` the commit that added it must be signed and verify,
    and that is all: the signature counts on whatever commit carries it,
    whoever wrote it and whoever last committed to the test file. The gate
    is read from the project's `.purlin/config.json`.
    """
    if not signature:
        return False, 'no signature'
    path = signature.get('path')
    if not path:
        return False, 'the signature is not committed'
    if _project_gate(project_root) != 'signed':
        return True, ''
    if not commit_is_signed(project_root, path):
        return False, 'the signing commit is not signed'
    return True, ''


def _project_gate(project_root):
    """The gate `.purlin/config.json` resolves to."""
    from config_engine import resolve_config
    from purlin import gate as gate_module
    return gate_module.resolve_gate(resolve_config(project_root)).gate
