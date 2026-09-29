"""Read the signatures a person committed.

One signature is one file, so two signatures never conflict:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json

`hash8` is the first eight characters of `signed_hash`, the one hash the
signature is made over, and the slug is the signer's email local part,
lowercased, with every non-alphanumeric character replaced by `-`. Every file
in the directory was written by a person: a run writes no signature, ever.

The file, field by field in `references/formats/signature_format.md`:

    {
      "schema": "purlin-signature/2",
      "feature": "login",
      "rule": "RULE-3",
      "applies_to": "login",
      "signed_hash": "<sha256 over the seven lines below>",
      "rule_hash": "<sha256 of the rule text>",
      "proof_hash": "<sha256 of the proof text>",
      "test_hash": "<sha256 of the test files' blob ids>",
      "code_hash": "<sha256 of the files the feature lists>",
      "audit_hash": "<sha256 of what the audit found>",
      "machines": {"macos": "jane-laptop"},
      "signer": "jane@acme.com",
      "signer_name": "Jane",
      "key_fingerprint": "SHA256:...",
      "test_hash_kind": "file",
      "note": null,
      "timestamp": "2026-09-13T12:00:00Z",
      "gate": "signed",
      "evidence": ".purlin/evidence/local/login.json"
    }

A signature is **current** while `signed_hash` recomputed from the rule's
entry equals the one stored: the feature it applies to, the rule, its proof,
its test, the code that feature lists, what the audit found, and the machine
each system's tests ran on. A result from a system the signature does not name
is left out of the comparison, so a first run on a new system ends nothing.

`audit_hash` is taken over what the audit found: the test strength, the audit
entry's `verdict` and its `findings` sorted. Timestamps and commit ids are not
hashed, so running the same audit again over the same code changes nothing. A
rule with no audit entry carries the hash of the empty string.

A signature **counts** when the last commit that touched its file carries a
signature, made with any key. Purlin checks that the commit is signed and
looks no further: who signed is recorded, not checked.
"""

import base64
import binascii
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

# What the test hash was taken from, in the order one wins over another.
TEST_HASH_KINDS = ('file', 'manual', 'none')


def signer_slug(email):
    """The slug a signature file takes for an email address."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def triple_hash(rule_hash, proof_hash, test_hash):
    """sha256 over the rule, proof and test hashes, one per line."""
    digest = hashlib.sha256()
    digest.update(('%s\n%s\n%s' % (rule_hash or '', proof_hash or '',
                                   test_hash or '')).encode('utf-8'))
    return digest.hexdigest()


def audit_hash(entry, strength=None):
    """What the audit found, and nothing else, as a signature is made over it.

    `entry` is the evidence's audit entry for the rule's current hashes and
    `strength` the feature's test strength. The strength, the `verdict` and
    the `findings` in a fixed order. Nothing that moves on its own goes in: a
    timestamp, a commit id or a path would end every signature on the next
    run of the same audit over the same code. A rule with no entry hashes the
    empty string, so a rule whose first audit writes one needs signing again,
    which is what a person should be asked about.
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
    """What the test hash was taken from, for the signature to record.

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




# ---------------------------------------------------------------------------
# What a signature is made over
# ---------------------------------------------------------------------------

# The six fields `signed_hash` reads one per line before the machines, in
# that order.
SIGNED_FIELDS = ('applies_to', 'rule_hash', 'proof_hash', 'test_hash',
                 'code_hash', 'audit_hash')


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
    lines = [str(entry.get(key) or '') for key in SIGNED_FIELDS]
    lines.append(pairs)
    digest = hashlib.sha256()
    digest.update('\n'.join(lines).encode('utf-8'))
    return digest.hexdigest()


def is_current(signature, entry):
    """True while a signature is still made over the rule entry it is compared with.

    `entry` is the payload's rule entry for the feature the signature applies
    to. The hash is taken again from the entry and compared with the stored
    `signed_hash`, the machines restricted to the systems the signature
    names: a system the signature names that the entry no longer has, or has
    under another machine, ends it, and a system the entry has and the
    signature does not name is left out of the comparison.
    """
    if not signature or entry is None:
        return False
    named = signature.get('machines') or {}
    machines = entry.get('machines') or {}
    if any(name not in machines for name in named):
        return False
    restricted = {name: machines[name] for name in named}
    return signature.get('signed_hash') == signed_hash(
        dict(entry, machines=restricted))


# ---------------------------------------------------------------------------
# How it was committed
# ---------------------------------------------------------------------------

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


# The reason a signature does not count.
NOT_SIGNED = 'the commit that added it is not signed'

# The commit headers that carry a signature, SHA-1 and SHA-256 repositories.
_SIGNATURE_HEADERS = ('gpgsig ', 'gpgsig-sha256 ')


def counts(project_root, signature):
    """`(True, '')` when a signature counts, or `(False, reason)`.

    Whether it is still made over the rule is `is_current`; this answers how
    the file was committed. The file is tracked, and the last commit touching
    it carries a signature header, made with any key. Nothing about the key
    or the author is read, and the answer is the same at every gate.
    """
    path = (signature or {}).get('path')
    if path and _tracked(project_root, path) and _signed_commit(project_root,
                                                                path):
        return True, ''
    return False, NOT_SIGNED


def _tracked(project_root, rel_path):
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0


def _signed_commit(project_root, rel_path):
    """True when the last commit touching a path carries a signature header."""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=raw', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if not line:
            return False
        if line.startswith(_SIGNATURE_HEADERS):
            return True
    return False


# ---------------------------------------------------------------------------
# The key a signer signs with
# ---------------------------------------------------------------------------

_KEY_LITERAL = 'key::'


def key_fingerprint(project_root):
    """`SHA256:<base64>` of the SSH key `user.signingkey` names, or None.

    `user.signingkey` is a `key::` literal, the path of a public key, or the
    path of a private key whose public half sits beside it as `<path>.pub`.
    The fingerprint is the unpadded base64 of the sha256 of the key blob,
    as `ssh-keygen -l` prints it. None when no SSH key can be read.
    """
    try:
        result = subprocess.run(['git', 'config', '--get', 'user.signingkey'],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    named = result.stdout.strip() if result.returncode == 0 else ''
    if not named:
        return None
    if named.startswith(_KEY_LITERAL):
        return _fingerprint_of(named[len(_KEY_LITERAL):])
    path = os.path.expanduser(named)
    if not os.path.isabs(path):
        path = os.path.join(project_root, path)
    if not path.endswith('.pub'):
        path += '.pub'
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return _fingerprint_of(handle.read())
    except (IOError, OSError, UnicodeDecodeError):
        return None


def _fingerprint_of(public_key):
    """The fingerprint of one `<type> <base64 blob> [comment]` line, or None."""
    parts = public_key.strip().split()
    if len(parts) < 2 or not parts[0].startswith(('ssh-', 'ecdsa-', 'sk-')):
        return None
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (ValueError, binascii.Error):
        return None
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode('ascii')
    return 'SHA256:' + digest.rstrip('=')
