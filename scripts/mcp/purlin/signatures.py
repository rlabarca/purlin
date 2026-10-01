"""Read the sign-offs a person committed over a version's evidence package.

One sign-off is one file per signer per version, beside the package it signs,
so two signers never conflict:

    .purlin/evidence/package/<version>.signoffs/<signer-slug>.json

The slug is the signer's email local part, lowercased, with every
non-alphanumeric character replaced by `-`; a second signer whose slug
another address holds takes `<signer-slug>-2.json`, then `-3`. Every file in
the folder was written by a person, through `purlin:sign`: a run writes no
sign-off, ever. The file, field by field, is in
`references/formats/signature_format.md`.

**A sign-off is read as HEAD holds it.** The files are listed and read from
HEAD's tree, never from the working tree, so a file git does not track is no
sign-off and an edit not committed is not read.

A sign-off **counts** when the last commit that touched its file carries a
signature, that signature verifies over the commit, made with any key, and
its `package_hash` equals the fingerprint computed over the package HEAD
holds for its version. The key is not compared with the signer: who signed is
recorded, not checked.

**Where the status reads `signed`.** `standing` decides it and nothing else
does: `signed/<version>` names a commit that holds the package for that
version, and a sign-off of it counts.
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
_EXPORT_DIR = os.path.join(os.path.dirname(_MCP_DIR), 'export')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import facts as facts_module, states               # noqa: E402

# Where a version's evidence package and its sign-offs sit.
PACKAGE_DIR = '.purlin/evidence/package'


def signer_slug(email):
    """The slug a sign-off file takes for an email address."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def signoffs_dir(version):
    """`.purlin/evidence/package/<version>.signoffs`, `/` separated."""
    return '%s/%s.signoffs' % (PACKAGE_DIR, version)


def package_rel(version):
    """`.purlin/evidence/package/<version>.json`, `/` separated."""
    return '%s/%s.json' % (PACKAGE_DIR, version)


def _package_module():
    """`scripts/export/package.py`, which imports this module at its top."""
    if _EXPORT_DIR not in sys.path:
        sys.path.insert(0, _EXPORT_DIR)
    import package
    return package


def _at_head(project_root, rel_path, ref='HEAD'):
    """The bytes `ref`'s tree holds at a path, or None where it holds none."""
    try:
        result = subprocess.run(
            ['git', 'show', '%s:%s' % (ref, rel_path)],
            capture_output=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    return result.stdout if result.returncode == 0 else None


def _names_at_head(project_root, rel_dir):
    """The names HEAD's tree holds directly under a folder, sorted."""
    try:
        result = subprocess.run(
            ['git', '-c', 'core.quotepath=false', 'ls-tree', '--name-only',
             'HEAD', '%s/' % rel_dir],
            capture_output=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []
    listed = result.stdout.decode('utf-8', 'replace').splitlines()
    return sorted(line.strip().strip('"').rsplit('/', 1)[-1]
                  for line in listed if line.strip())


def committed_fingerprint(project_root, version):
    """The fingerprint computed over the package HEAD's tree holds for `version`.

    It is computed from the package's content; the `fingerprint` the file
    stores is not taken on trust. None where HEAD holds no package for the
    version, or holds one that does not match its own fingerprint.
    """
    data = _at_head(project_root, package_rel(version))
    if data is None:
        return None
    package = _package_module()
    if package.check_bytes(data) is not None:
        return None
    return package.fingerprint_of(json.loads(data.decode('utf-8')))


def load_signoffs(project_root, version):
    """Every sign-off of `version` HEAD holds, oldest first by `timestamp`.

    Each is the file's dict as HEAD's tree holds it, plus `path`,
    project-relative, `counts` and `count_reason`, as `counts` answers them
    for the commit and as the committed package's fingerprint answers them
    for `package_hash`. The working tree is not read. A file that is not a
    JSON object is left out.
    """
    rel_dir = signoffs_dir(version)
    names = [name for name in _names_at_head(project_root, rel_dir)
             if name.endswith('.json')]
    if not names:
        return []
    fingerprint = committed_fingerprint(project_root, version)
    found = []
    for basename in names:
        rel = '%s/%s' % (rel_dir, basename)
        raw = _at_head(project_root, rel)
        try:
            data = json.loads(raw.decode('utf-8')) if raw is not None else None
        except (UnicodeDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        data = dict(data)
        data['path'] = rel
        ok, reason = counts(project_root, data)
        if ok and (not fingerprint or data.get('package_hash') != fingerprint):
            ok, reason = False, OTHER_PACKAGE
        data['counts'], data['count_reason'] = ok, reason
        found.append(data)
    found.sort(key=lambda item: (str(item.get('timestamp') or ''),
                                 item['path']))
    return found


# Why a `signed/<version>` tag is passed over, each one warning: the tag and
# the version, or the tag, the version and why no sign-off of it counts.
NO_PACKAGE_AT_TAG = ('%s: it names a commit that holds no evidence package for %s, so it '
                     'is not a sign-off. Delete it: git tag -d %s.')
NO_SIGNOFF_COUNTS = ('%s: no sign-off of %s counts: %s. Restore the files as they were '
                     'signed, or sign this code: purlin:sign --version <version>.')
# Why none counts where HEAD holds no sign-off file for the version at all.
NONE_AT_HEAD = 'HEAD holds none'


def standing(project_root, version):
    """`(True, '')` where the status may read `signed <version>`, else `(False, why)`.

    It may where `signed/<version>` names a commit that holds the package
    for that version, and `load_signoffs` gives a sign-off that counts.
    `why` is the warning: `NO_PACKAGE_AT_TAG`, or `NO_SIGNOFF_COUNTS` with
    the reason the oldest sign-off does not count.
    """
    tag = facts_module.TAG_PREFIX + version
    commit = facts_module.git_line(project_root, 'rev-list', '-n', '1', tag)
    if not commit or _at_head(project_root, package_rel(version),
                              commit) is None:
        return False, NO_PACKAGE_AT_TAG % (tag, version, tag)
    signoffs = load_signoffs(project_root, version)
    if any(item['counts'] for item in signoffs):
        return True, ''
    reason = signoffs[0]['count_reason'] if signoffs else NONE_AT_HEAD
    return False, NO_SIGNOFF_COUNTS % (tag, version, reason)


# The reasons a signature does not count.
NOT_SIGNED = 'the commit that added it is not signed'
NOT_VERIFIED = 'the signature on the commit that added it does not verify'
OTHER_PACKAGE = 'it signs another evidence package than the one committed'

# The commit header that carries a signature, by the length of the commit id:
# SHA-1 and SHA-256 repositories.
_SIGNATURE_HEADER = {40: 'gpgsig', 64: 'gpgsig-sha256'}
_SSH_SIGNATURE = '-----BEGIN SSH SIGNATURE-----'


def counts(project_root, signature):
    """`(True, '')` when a sign-off's commit counts, or `(False, reason)`.

    This answers how the file was committed: it is tracked, the last commit
    touching it carries a signature header, and that signature verifies over
    the commit. Nothing about the key or the author is read.
    `load_signoffs` adds the package's hash.
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

    `user.signingkey` is the path of a public key, or the path of a private
    key whose public half sits beside it as `<path>.pub`.
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


def hand_notes(project_root):
    """`{(feature, rule): [reason]}` from the newest sign-off holding a note on each rule.

    Every sign-off HEAD holds, of every version, is read, whatever code it
    was taken on, and only one that counts is shown. Each note becomes
    `states.HAND_NOTE`: the version, the signer, how far HEAD is from the
    signed commit, the note. The signed commit is the one `signed/<version>`
    names, or the commit that added the file.
    """
    signoffs = []
    for name in _names_at_head(project_root, PACKAGE_DIR):
        if not name.endswith('.signoffs'):
            continue
        for data in load_signoffs(project_root, name[:-len('.signoffs')]):
            if data['counts'] and isinstance(data.get('notes'), list):
                signoffs.append((str(data.get('timestamp') or ''),
                                 data['path'], data))
    found = {}
    distances = {}
    for _at, rel, data in sorted(signoffs, key=lambda item: item[:2],
                                 reverse=True):
        version = str(data.get('version') or '')
        held = {}
        for note in data['notes']:
            if isinstance(note, dict) and note.get('feature') and note.get('rule'):
                held.setdefault((note['feature'], note['rule']), []).append(
                    str(note.get('note') or ''))
        for key, notes in held.items():
            if key in found:
                continue
            if rel not in distances:
                distances[rel] = _distance(project_root, version, rel)
            found[key] = [states.HAND_NOTE % (version, data.get('signer'),
                                              distances[rel], note)
                          for note in notes]
    return found


def _distance(project_root, version, rel):
    """How far HEAD is from the commit a sign-off signed, as a note says it."""
    commit = facts_module.git_line(project_root, 'rev-list', '-n', '1',
                                   facts_module.TAG_PREFIX + version)
    if not commit:
        commit = facts_module.git_line(project_root, 'log', '-n', '1',
                                       '--diff-filter=A', '--format=%H', '--', rel)
    if not commit:
        return facts_module.AT_THIS_COMMIT
    return facts_module.distance(project_root, commit)
