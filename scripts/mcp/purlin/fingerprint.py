"""The fingerprint of a feature: what its evidence was taken over.

A fingerprint has three parts, each a sha256 hex string:

    spec   the rule and proof lines of the feature, and of every spec whose
           rules count inside it: the specs it requires, transitively, and
           every global anchor
    code   the files its `> Scope:` names
    tests  the files that carry a proof marker for it

Every file is read from the working tree through `git hash-object`, so an edit
counts before it is committed. A file git does not track is left out of every
part: it would change the fingerprint on the one machine that holds it and
nowhere else. `untracked` names those files instead, so a caller can say that
they are not part of the evidence until they are added.

`> Description:` and every other metadata field are outside the `spec` part,
so rewording a description leaves every fingerprint as it was.

`references/formats/evidence_format.md` documents where a fingerprint is
stored and how a stored one is compared with one taken now.
"""

import hashlib
import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import specs as specs_module                      # noqa: E402

# The three parts, in the order a message names them.
PARTS = ('spec', 'code', 'tests')

# One pattern per framework, reading the same marker its plugin reads. A
# pattern that drifted from its plugin would report a missing proof for a test
# that never had one, which is why each is the plugin's own marker written
# once, here, and `scripts/run/purlin_run.py` reads it from here.
MARKER_PATTERNS = {
    'pytest': (('.py',), re.compile(
        r'@pytest\.mark\.proof\(\s*["\'](\w+)["\']\s*,\s*["\'](PROOF-\d+)["\']')),
    'jest': (('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'), re.compile(
        r'\[proof:(\w+):(PROOF-\d+):')),
    'vitest': (('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'), re.compile(
        r'\[proof:(\w+):(PROOF-\d+):')),
    'xunit': (('.cs',), re.compile(
        r'\[Trait\(\s*"PurlinProof"\s*,\s*"(\w+):(PROOF-\d+):')),
    'shell': (('.sh',), re.compile(
        r'purlin_proof\s+"(\w+)"\s+"(PROOF-\d+)"')),
    'sql': (('.sql',), re.compile(
        r'^--\s*@purlin\s+(\w+)\s+(PROOF-\d+)\b', re.MULTILINE)),
}

# Directories no marker is read from. `mutants/` is mutmut's copy of the
# project, tests included: reading it would count every marker twice.
SKIP_DIRS = ('node_modules', 'bin', 'obj', 'mutants')

_GLOB_CHARS = ('*', '?', '[')


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git_lines(project_root, args, stdin=None):
    """NUL-separated output of one git command, or `None` when git failed."""
    try:
        result = subprocess.run(
            ['git'] + list(args), capture_output=True, cwd=project_root,
            input=stdin.encode('utf-8') if stdin is not None else None,
            timeout=60)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.decode('utf-8', 'replace')
    return [part for part in text.split('\0') if part]


def blob_ids(project_root, paths):
    """`{path: blob id}` for each path, read from the working tree.

    A path that is not a file on the disk, or that git cannot hash, maps to
    `''`, so a deleted file changes a hash rather than raising.
    """
    ids = {path: '' for path in paths}
    present = [path for path in paths
               if '\n' not in path
               and os.path.isfile(os.path.join(project_root, path))]
    if not present:
        return ids
    try:
        result = subprocess.run(
            ['git', 'hash-object', '--stdin-paths'], capture_output=True,
            cwd=project_root, input='\n'.join(present).encode('utf-8'),
            timeout=120)
    except (subprocess.SubprocessError, OSError):
        return ids
    lines = result.stdout.decode('utf-8', 'replace').split()
    if result.returncode != 0 or len(lines) != len(present):
        # One unreadable path fails the whole batch; hash one at a time so
        # every other path still answers.
        for path in present:
            ids[path] = _one_blob_id(project_root, path)
        return ids
    ids.update(zip(present, lines))
    return ids


def _one_blob_id(project_root, path):
    try:
        result = subprocess.run(
            ['git', 'hash-object', '--', path], capture_output=True,
            cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    if result.returncode != 0:
        return ''
    return result.stdout.decode('utf-8', 'replace').strip()


def blob_id(project_root, path):
    """The blob id of one working-tree file, or `''`."""
    return blob_ids(project_root, [path])[path]


def _hash_lines(lines):
    digest = hashlib.sha256()
    digest.update('\n'.join(sorted(lines)).encode('utf-8'))
    return digest.hexdigest()


def _files_part(project_root, paths):
    ids = blob_ids(project_root, sorted(set(paths)))
    return _hash_lines('%s %s' % (path, ids[path]) for path in ids)


# ---------------------------------------------------------------------------
# code
# ---------------------------------------------------------------------------

def pathspec(entry):
    """The git pathspec for one `> Scope:` entry.

    An entry holding `*`, `?` or `[` is a glob, so `scripts/**/*.py` reaches
    every Python file under `scripts/` and `src/*.py` stops at `src/`. Any
    other entry is a literal path: a file names itself and a directory names
    every file under it.
    """
    entry = entry.strip().rstrip('/')
    if any(char in entry for char in _GLOB_CHARS):
        return ':(glob)' + entry
    return ':(literal)' + entry


def expand_scope(project_root, scope):
    """`(files, unmatched)` for a list of `> Scope:` entries.

    `files` is every tracked file the entries reach, sorted and without
    repeats. `unmatched` lists, in the order given, each entry that reaches
    no tracked file: a path that does not exist, a glob that matches nothing,
    or a file git does not track.
    """
    files = set()
    unmatched = []
    for entry in scope or ():
        entry = entry.strip()
        if not entry:
            continue
        found = _git_lines(project_root,
                           ['ls-files', '-z', '--', pathspec(entry)]) or []
        if not found:
            unmatched.append(entry)
        files.update(found)
    return sorted(files), unmatched


def code_hash(project_root, scope):
    """The `code` part: sha256 over `<path> <blob>` for each file in scope.

    A scope naming nothing, or naming only paths that reach no tracked file,
    hashes to the sha256 of the empty string.
    """
    files, _ = expand_scope(project_root, scope)
    return _files_part(project_root, files)


def scope_report(project_root, feature, features=None):
    """What a feature's `> Scope:` reaches.

    Returns `{scope, files, unmatched, names_no_files}`: the entries as the
    spec writes them, the tracked files they reach, the entries that reach
    none, and whether the feature names no file at all. A spec with no
    `> Scope:` line names no files. That is a fact about the spec, not an
    error: its evidence is compared on its `spec` and `tests` parts alone.
    """
    features = _features(project_root, features)
    scope = list(_info(feature, features).get('scope') or [])
    files, unmatched = expand_scope(project_root, scope)
    return {'scope': scope, 'files': files, 'unmatched': unmatched,
            'names_no_files': not files}


# ---------------------------------------------------------------------------
# spec
# ---------------------------------------------------------------------------

def rule_line(spec_path, rule_id, text, meta):
    """The line one rule contributes to the `spec` part.

    `<spec> <RULE-N> <text>`, then the rule's tag as the parser reports it.
    This is the one place that decides what of a rule the fingerprint reads.
    """
    line = '%s %s %s' % (spec_path, rule_id, _normalise(text))
    bar = (meta or {}).get('bar')
    if bar:
        line += ' [bar: %s]' % bar
    return line


def proof_line(spec_path, proof_id, proof):
    """`<spec> <PROOF-N> <rules> <text>`, then `@manual` and `@env(<os>)`."""
    parts = [spec_path, proof_id, ','.join(proof.get('rules') or ()),
             _normalise(proof.get('text'))]
    if proof.get('manual'):
        parts.append('@manual')
    if proof.get('env'):
        parts.append('@env(%s)' % proof['env'])
    return ' '.join(parts)


def counted_specs(feature, features):
    """The feature and every spec whose rules count inside it, in walk order."""
    _info(feature, features)
    names = [feature]
    for name, _, _ in specs_module.rule_refs(feature, features):
        if name not in names:
            names.append(name)
    return names


def spec_lines(feature, features):
    """Every rule and proof line the `spec` part hashes, sorted."""
    lines = []
    for name in counted_specs(feature, features):
        info = features[name]
        path = info['spec_path']
        for rule_id in info.get('rule_order', ()):
            lines.append(rule_line(path, rule_id, info['rules'][rule_id],
                                   info.get('rule_meta', {}).get(rule_id)))
        for proof_id, proof in sorted(info.get('proofs', {}).items()):
            lines.append(proof_line(path, proof_id, proof))
    return sorted(lines)


def spec_hash(feature, features):
    """The `spec` part."""
    return _hash_lines(spec_lines(feature, features))


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def _skipped(path):
    return any(part.startswith('.') or part in SKIP_DIRS
               for part in path.split('/')[:-1])


def marker_index(project_root):
    """`{feature: [paths]}` for every tracked file that carries a marker.

    Every framework's pattern is read, whatever the project's framework, so
    the answer does not depend on the configuration. A tracked file that is
    no longer on the disk carries no marker.
    """
    index = {}
    for path in _git_lines(project_root, ['ls-files', '-z']) or []:
        if _skipped(path):
            continue
        patterns = [pattern for extensions, pattern in MARKER_PATTERNS.values()
                    if path.endswith(extensions)]
        if not patterns:
            continue
        full = os.path.join(project_root, path)
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        for pattern in patterns:
            for match in pattern.finditer(text):
                index.setdefault(match.group(1), set()).add(path)
    return {name: sorted(paths) for name, paths in index.items()}


def marker_files(project_root, feature, index=None):
    """The tracked files that carry a marker for one feature, sorted."""
    if index is None:
        index = marker_index(project_root)
    return list(index.get(feature, []))


def tests_hash(project_root, feature, index=None):
    """The `tests` part: sha256 over `<path> <blob>` for each marker file."""
    return _files_part(project_root, marker_files(project_root, feature, index))


# ---------------------------------------------------------------------------
# The fingerprint
# ---------------------------------------------------------------------------

def fingerprint(project_root, feature, features=None, index=None):
    """`{spec, code, tests}` for one feature, taken from the working tree now.

    `features` is `specs.scan_specs`'s answer and `index` is
    `marker_index`'s; a caller taking many fingerprints passes both so the
    specs are parsed and the test sources read once. A feature no spec
    defines raises `KeyError`.
    """
    features = _features(project_root, features)
    info = _info(feature, features)
    return {
        'spec': spec_hash(feature, features),
        'code': code_hash(project_root, info.get('scope') or []),
        'tests': tests_hash(project_root, feature, index),
    }


def differing_parts(stored, now):
    """The parts, in `PARTS` order, on which two fingerprints differ.

    A stored fingerprint that is missing or is not an object differs on all
    three. An empty answer means the evidence is current.
    """
    if not isinstance(stored, dict):
        return list(PARTS)
    return [part for part in PARTS if stored.get(part) != (now or {}).get(part)]


def untracked(project_root, feature, features=None, index=None):
    """Untracked, non-ignored files under a feature's scope or beside its tests.

    A file counts as beside the tests when it sits in the same directory as
    one of the feature's marker files. None of these is in the fingerprint;
    each joins it once `git add` tracks it. Sorted.
    """
    features = _features(project_root, features)
    info = _info(feature, features)
    found = set()
    specs = [pathspec(entry) for entry in info.get('scope') or ()
             if entry.strip()]
    if specs:
        found.update(_git_lines(
            project_root,
            ['ls-files', '-z', '--others', '--exclude-standard', '--']
            + specs) or [])
    folders = {os.path.dirname(path)
               for path in marker_files(project_root, feature, index)}
    if folders:
        listed = _git_lines(
            project_root,
            ['ls-files', '-z', '--others', '--exclude-standard', '--']
            + [':(literal)' + folder if folder else '.'
               for folder in sorted(folders)]) or []
        found.update(path for path in listed
                     if os.path.dirname(path) in folders)
    return sorted(found)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(text):
    return ' '.join((text or '').split())


def _features(project_root, features):
    return specs_module.scan_specs(project_root) if features is None else features


def _info(feature, features):
    info = features.get(feature)
    if info is None:
        raise KeyError('no spec defines the feature %s' % feature)
    return info
