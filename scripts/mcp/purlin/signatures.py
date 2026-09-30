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
      "code_hash": "<sha256 of the files the spec lists, or of the project>",
      "audit_hash": "<sha256 of what the audit found>",
      "machines": {"macos": "jane-laptop"},
      "signer": "jane@acme.com",
      "signer_name": "Jane",
      "key_fingerprint": "SHA256:...",
      "test_hash_kind": "file",
      "note": null,
      "does_not_apply": null,
      "timestamp": "2026-09-13T12:00:00Z",
      "gate": "signed",
      "evidence": ".purlin/evidence/local/login.json"
    }

A signature is **current** while `signed_hash` recomputed from the rule's
entry equals the one stored: the spec that holds the rule, the rule, its
proof, its test, the code that spec lists, what the audit found, and the
machine each system's tests ran on. An anchor's rule is signed once, over
every file of the project but Purlin's own records, so any change to the
project ends that signature. A hand check's signature, one whose
`test_hash_kind` is `manual`, is made over the rule's and its proofs' wording
alone: a change to the code, a test or the machines does not end it.

`does_not_apply` is the reason a person gave for signing a pinned anchor's
rule as not applying to this project, or null. Like `note` it is outside
`signed_hash`: the signed commit is what holds it. A result from a system the signature does not name
is left out of the comparison, so a first run on a new system ends nothing.

`audit_hash` is taken over what the audit found: the test strength, the audit
entry's `verdict` and its `findings` sorted. Timestamps and commit ids are not
hashed, so running the same audit again over the same code changes nothing. A
rule with no audit entry carries the hash of the empty string.

A signature **counts** when the last commit that touched its file carries a
signature and that signature verifies over the commit, made with any key. The
key is not compared with the signer: who signed is recorded, not checked.
"""

import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

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


# The test hash kind of a hand check, whose signature is made over the first
# three lines alone.
HAND_CHECK = 'manual'


def signed_hash(entry):
    """sha256 over the seven lines a signature is made over.

    `applies_to`, `rule_hash`, `proof_hash`, `test_hash`, `code_hash`,
    `audit_hash`, and `machines` written as `os=machine` pairs, sorted and
    joined with `,`. `entry` is a payload rule entry, or a signature, which
    carries the same fields; a field it lacks reads as the empty string.
    Where its `test_hash_kind` is `manual`, a hand check, lines 4 to 7 are
    each the empty string: the signature is bound to the wording alone.
    """
    machines = entry.get('machines') or {}
    pairs = ','.join(sorted('%s=%s' % (name, machines[name] or '')
                            for name in machines))
    lines = [str(entry.get(key) or '') for key in SIGNED_FIELDS]
    lines.append(pairs)
    if entry.get('test_hash_kind') == HAND_CHECK:
        lines[3:] = [''] * 4
    digest = hashlib.sha256()
    digest.update('\n'.join(lines).encode('utf-8'))
    return digest.hexdigest()


def is_current(signature, entry):
    """True while a signature is still made over the rule entry it is compared with.

    `entry` is the payload's rule entry, listed under the rule's own spec.
    The hash is taken again from the entry and compared with the stored
    `signed_hash`, the machines restricted to the systems the signature
    names: a system the signature names that the entry no longer has, or has
    under another machine, ends it, and a system the entry has and the
    signature does not name is left out of the comparison.

    Whether the rule is a hand check is read from the entry, never from the
    signature: its `test_hash_kind`, or, where it carries none, the kind its
    `proofs` give. A hand check's signature compares the wording alone.
    """
    if not signature or entry is None:
        return False
    kind = entry.get('test_hash_kind')
    if kind is None and 'proofs' in entry:
        kind = test_hash_kind(entry.get('proofs'))
    if kind == HAND_CHECK:
        return signature.get('signed_hash') == signed_hash(
            dict(entry, test_hash_kind=kind))
    named = signature.get('machines') or {}
    machines = entry.get('machines') or {}
    if any(name not in machines for name in named):
        return False
    restricted = {name: machines[name] for name in named}
    return signature.get('signed_hash') == signed_hash(
        dict(entry, machines=restricted, test_hash_kind=kind))


# ---------------------------------------------------------------------------
# How it was committed
# ---------------------------------------------------------------------------

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


# The reasons a signature does not count.
NOT_SIGNED = 'the commit that added it is not signed'
NOT_VERIFIED = 'the signature on the commit that added it does not verify'

# The commit header that carries a signature, by the length of the commit id:
# SHA-1 and SHA-256 repositories.
_SIGNATURE_HEADER = {40: 'gpgsig', 64: 'gpgsig-sha256'}
_SSH_SIGNATURE = '-----BEGIN SSH SIGNATURE-----'


def counts(project_root, signature):
    """`(True, '')` when a signature counts, or `(False, reason)`.

    Whether it is still made over the rule is `is_current`; this answers how
    the file was committed. The file is tracked, the last commit touching it
    carries a signature header, and that signature verifies over the commit.
    Nothing about the key or the author is read, and the answer is the same
    at every gate.
    """
    path = (signature or {}).get('path')
    if not path or not _tracked(project_root, path):
        return False, NOT_SIGNED
    sha = _last_commit(project_root, path)
    split = _split_signed(project_root, sha) if sha else None
    if split is None:
        return False, NOT_SIGNED
    payload, block = split
    if not _verifies(project_root, sha, payload, block):
        return False, NOT_VERIFIED
    return True, ''


def _tracked(project_root, rel_path):
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0


def _last_commit(project_root, rel_path):
    """The id of the last commit touching a path, or None."""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _split_signed(project_root, sha):
    """`(payload, signature)` of a signed commit as bytes, or None when unsigned.

    The payload is the commit object without its signature header, which is
    what the signature was made over; the header is read among the headers
    alone, never in the message.
    """
    try:
        result = subprocess.run(['git', 'cat-file', 'commit', sha],
                                capture_output=True, cwd=project_root,
                                timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    header = _SIGNATURE_HEADER.get(len(sha), 'gpgsig').encode('ascii')
    payload, block = [], []
    in_headers, in_block = True, False
    for line in result.stdout.splitlines(True):
        if in_headers and in_block and line.startswith(b' '):
            block.append(line[1:])
            continue
        in_block = False
        if in_headers and line in (b'\n', b'\r\n'):
            in_headers = False
        elif in_headers and line.startswith(header + b' '):
            block.append(line[len(header) + 1:])
            in_block = True
            continue
        payload.append(line)
    if not block:
        return None
    return b''.join(payload), b''.join(block)


def _verifies(project_root, sha, payload, block):
    """True when a commit's signature verifies over its payload.

    An SSH signature is checked by `ssh-keygen -Y check-novalidate`, which
    reads the key the signature carries and needs no list of allowed
    signers; any other kind by `git verify-commit`.
    """
    if not block.lstrip().startswith(_SSH_SIGNATURE.encode('ascii')):
        try:
            result = subprocess.run(['git', 'verify-commit', sha],
                                    capture_output=True, cwd=project_root,
                                    timeout=30)
        except (subprocess.SubprocessError, OSError):
            return False
        return result.returncode == 0
    handle, sig_path = tempfile.mkstemp(suffix='.sig')
    try:
        with os.fdopen(handle, 'wb') as out:
            out.write(block)
        result = subprocess.run(
            ['ssh-keygen', '-Y', 'check-novalidate', '-n', 'git', '-s',
             sig_path],
            input=payload, capture_output=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return False
    finally:
        try:
            os.remove(sig_path)
        except OSError:
            pass
    return result.returncode == 0


# ---------------------------------------------------------------------------
# The key a signer signs with
# ---------------------------------------------------------------------------

_KEY_LITERAL = 'key::'


def home_folder():
    """The home folder as git finds it: `HOME`, then `USERPROFILE`, then Python's.

    Python reads `USERPROFILE` first on Windows, where git reads `HOME`
    first, so a key path under `~` would name two different files.
    """
    for name in ('HOME', 'USERPROFILE'):
        found = os.environ.get(name)
        if found:
            return found
    return os.path.expanduser('~')


def expand_home(path):
    """`path` with a leading `~` read as the home folder `home_folder` finds."""
    if path == '~':
        return home_folder()
    if path.startswith(('~/', '~\\')):
        return os.path.join(home_folder(), path[2:])
    return os.path.expanduser(path)


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
    path = expand_home(named)
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
