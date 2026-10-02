"""The fingerprint of a feature: what its evidence was taken over.

A fingerprint has three parts, each a sha256 hex string:

    spec   the spec's own rule and proof lines
    code   the files its `> Scope:` names; for an anchor, the project: every
           tracked file but `RECORDS`, Purlin's records and the settings file
    tests  the test files that carry a marker for it, and the `tests`
           setting of `.purlin/config.json`

Every file is read from the working tree through `git hash-object`, so an edit
counts before it is committed. A file git does not track is left out of every
part: it would change the fingerprint on the one machine that holds it and
nowhere else. `untracked` names those files instead, so a caller can say that
they are not part of the evidence until they are added.

`> Description:` and every other metadata field are outside the `spec` part,
so rewording a description leaves every fingerprint as it was.

`references/formats/evidence_format.md` documents where a fingerprint is
stored and how a stored one is compared with one taken now. `selection` is
that compare, made for every feature at once: it is what a run with no
feature named runs.
"""

import hashlib
import json
import os
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import markers as markers_module                  # noqa: E402
from purlin import specs as specs_module                      # noqa: E402

# The three parts, in the order a message names them.
PARTS = ('spec', 'code', 'tests')

_GLOB_CHARS = ('*', '?', '[')

# What no anchor's code part reads: the records Purlin itself writes, the
# results of every run, the evidence package and its sign-offs; and the
# settings file, whose `tests` setting the `tests` part covers for an anchor
# as for a feature, so a changed `version` alone ends no result.
RECORDS = (':(exclude).purlin/evidence', ':(exclude).purlin/config.json')


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


def project_files(project_root):
    """Every tracked file but `RECORDS`, sorted: what an anchor covers."""
    found = _git_lines(project_root, ['ls-files', '-z', '--'] + list(RECORDS))
    return sorted(set(found or ()))


def project_hash(project_root):
    """The `code` part of an anchor: `_files_part` over `project_files`.

    The blob id of a regular file git reads as unchanged comes from the
    index (`git ls-files -s`); only the files `git ls-files -m` names, and
    any link or submodule, are hashed from the working tree. The answer
    equals `_files_part(project_root, project_files(project_root))`, and a
    large project is not read whole on every status.
    """
    staged = _git_lines(project_root,
                        ['ls-files', '-s', '-z', '--'] + list(RECORDS))
    changed = _git_lines(project_root,
                         ['ls-files', '-m', '-z', '--'] + list(RECORDS))
    if staged is None or changed is None:
        return _files_part(project_root, project_files(project_root))
    changed = set(changed)
    ids = {}
    slow = []
    for entry in staged:
        head, _, path = entry.partition('\t')
        fields = head.split()
        if (len(fields) == 3 and fields[0] in ('100644', '100755')
                and fields[2] == '0' and path not in changed):
            ids[path] = fields[1]
        else:
            slow.append(path)
    ids.update(blob_ids(project_root, sorted(set(slow) - set(ids))))
    return _hash_lines('%s %s' % (path, ids[path]) for path in ids)


def code_part(project_root, info, cache=None):
    """The `code` part of one spec's fingerprint.

    `project_hash` for an anchor, `code_hash` of its `> Scope:` otherwise.
    `cache` is a dict a caller passes to take the project hash once for
    many anchors.
    """
    if not info.get('is_anchor'):
        return code_hash(project_root, info.get('scope') or [])
    if cache is None:
        return project_hash(project_root)
    if 'project_hash' not in cache:
        cache['project_hash'] = project_hash(project_root)
    return cache['project_hash']


# The two reasons a feature spec is incomplete.
NO_SCOPE_LINE = 'no > Scope: line'
SCOPE_NAMES_NOTHING = '> Scope: names nothing that exists'


def incomplete_reason(project_root, feature, features=None):
    """Why a feature spec names no files, or None when it names some.

    A feature spec is incomplete when it has no `> Scope:` line, or when its
    scope reaches no tracked file: Purlin then cannot tell which code belongs
    to it. An anchor is never incomplete: its code part is the project.
    """
    features = _features(project_root, features)
    info = _info(feature, features)
    if info.get('is_anchor'):
        return None
    scope = [entry for entry in info.get('scope') or () if entry.strip()]
    if not scope:
        return NO_SCOPE_LINE
    files, _ = expand_scope(project_root, scope)
    return None if files else SCOPE_NAMES_NOTHING


# ---------------------------------------------------------------------------
# spec
# ---------------------------------------------------------------------------

def rule_line(spec_path, rule_id, text):
    """The line one rule contributes to the `spec` part: `<spec> <RULE-N> <text>`.

    This is the one place that decides what of a rule the fingerprint reads.
    """
    return '%s %s %s' % (spec_path, rule_id, _normalise(text))


def proof_line(spec_path, proof_id, proof):
    """`<spec> <PROOF-N> <rules> <text>`, then `@manual`, `@slow` and `@env(<os>)`."""
    parts = [spec_path, proof_id, ','.join(proof.get('rules') or ()),
             _normalise(proof.get('text'))]
    if proof.get('manual'):
        parts.append('@manual')
    if proof.get('slow'):
        parts.append('@slow')
    if proof.get('env'):
        parts.append('@env(%s)' % proof['env'])
    return ' '.join(parts)


def spec_lines(feature, features):
    """The spec's own rule and proof lines, which the `spec` part hashes, sorted."""
    info = _info(feature, features)
    path = info['spec_path']
    lines = [rule_line(path, rule_id, info['rules'][rule_id])
             for rule_id in info.get('rule_order', ())]
    lines += [proof_line(path, proof_id, proof)
              for proof_id, proof in sorted(info.get('proofs', {}).items())]
    return sorted(lines)


def spec_hash(feature, features):
    """The `spec` part."""
    return _hash_lines(spec_lines(feature, features))


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def marker_index(project_root):
    """`{feature: [paths]}` for every tracked test file that carries a marker.

    A test file is one a suite of the `tests` setting names; the markers are
    read as `markers.py` reads them, so the run and the fingerprint read the
    same markers. A tracked file that is no longer on the disk carries none.
    """
    return markers_module.marker_index(project_root)


def marker_files(project_root, feature, index=None):
    """The tracked files that carry a marker for one feature, sorted."""
    if index is None:
        index = marker_index(project_root)
    return list(index.get(feature, []))


def tests_setting_line(project_root):
    """`tests-setting <sha256>` for the `tests` setting of
    `.purlin/config.json`, read from the working tree, or None where the
    file holds no `tests`.

    The sha256 is taken over the setting as JSON with sorted keys, so the
    file's layout, and every other key of it, `version` included, change
    nothing.
    """
    return _setting_line(markers_module.load_config(project_root))


def _setting_line(config):
    if not isinstance(config, dict) or 'tests' not in config:
        return None
    text = json.dumps(config['tests'], sort_keys=True, separators=(',', ':'))
    return 'tests-setting %s' % hashlib.sha256(
        text.encode('utf-8')).hexdigest()


def _setting_line_at(project_root, commit):
    """`tests_setting_line` for the settings file as `commit` holds it, or
    None where that commit holds none, or none that can be read."""
    try:
        shown = subprocess.run(
            ['git', 'show', '%s:.purlin/config.json' % commit],
            capture_output=True, cwd=project_root, timeout=60)
        if shown.returncode != 0:
            return None
        return _setting_line(json.loads(shown.stdout.decode('utf-8')))
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def setting_changed(project_root, features=None, os_name=None, index=None):
    """True where the `tests` setting changed since the evidence was taken.

    Shown, never guessed: for some feature, the newest section for this
    operating system names a commit whose settings file holds another
    `tests` setting than the one on disk, and the feature's marker files as
    they are now, hashed with that earlier setting, give the `tests` part
    the section stored. So the setting is the one thing that moved. A
    section taken over a setting no commit held shows nothing.
    """
    from purlin import evidence as evidence_module

    now = tests_setting_line(project_root)
    if now is None:
        return False
    features = _features(project_root, features)
    os_name = os_name or evidence_module.host_os()
    earlier = {}
    for name in sorted(features):
        mine = [entry['section'] for entry
                in evidence_module.sections(
                    evidence_module.load(project_root, name))
                if entry['os'] == os_name]
        if not mine:
            continue
        newest = max(mine, key=lambda section: _text(section.get('at')))
        commit = _text(newest.get('commit'))
        if not commit:
            continue
        if commit not in earlier:
            earlier[commit] = _setting_line_at(project_root, commit)
        was = earlier[commit]
        if was is None or was == now:
            continue
        if index is None:
            index = marker_index(project_root)
        ids = blob_ids(project_root,
                       sorted(set(marker_files(project_root, name, index))))
        lines = ['%s %s' % (path, ids[path]) for path in ids] + [was]
        stored = newest.get('fingerprint')
        if isinstance(stored, dict) and stored.get('tests') \
                == _hash_lines(lines):
            return True
    return False


def tests_hash(project_root, feature, index=None):
    """The `tests` part: sha256 over `<path> <blob>` for each marker file
    and, where the settings file holds `tests`, `tests_setting_line`."""
    ids = blob_ids(project_root,
                   sorted(set(marker_files(project_root, feature, index))))
    lines = ['%s %s' % (path, ids[path]) for path in ids]
    setting = tests_setting_line(project_root)
    if setting is not None:
        lines.append(setting)
    return _hash_lines(lines)


# ---------------------------------------------------------------------------
# The fingerprint
# ---------------------------------------------------------------------------

def fingerprint(project_root, feature, features=None, index=None, cache=None):
    """`{spec, code, tests}` for one feature, taken from the working tree now.

    `features` is `specs.scan_specs`'s answer, `index` is `marker_index`'s
    and `cache` is `code_part`'s; a caller taking many fingerprints passes
    all three so the specs are parsed, the test sources read and the project
    hashed once. A feature no spec defines raises `KeyError`.
    """
    features = _features(project_root, features)
    info = _info(feature, features)
    return {
        'spec': spec_hash(feature, features),
        'code': code_part(project_root, info, cache),
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
    parts = untracked_parts(project_root, feature, features, index)
    return sorted(set(parts['scope']) | set(parts['tests']))


def untracked_parts(project_root, feature, features=None, index=None):
    """`{scope, tests}`: `untracked`'s answer, split by why each file counts.

    `scope` lists the files under a `> Scope:` entry and `tests` the files
    beside a marker file that no scope entry reaches, each sorted. An anchor
    names no files, so for an anchor `scope` is empty.
    """
    features = _features(project_root, features)
    info = _info(feature, features)
    in_scope = set()
    scope = () if info.get('is_anchor') else info.get('scope') or ()
    specs = [pathspec(entry) for entry in scope if entry.strip()]
    if specs:
        in_scope.update(_git_lines(
            project_root,
            ['ls-files', '-z', '--others', '--exclude-standard', '--']
            + specs) or [])
    beside = set()
    folders = {os.path.dirname(path)
               for path in marker_files(project_root, feature, index)}
    if folders:
        listed = _git_lines(
            project_root,
            ['ls-files', '-z', '--others', '--exclude-standard', '--']
            + [':(literal)' + folder if folder else '.'
               for folder in sorted(folders)]) or []
        beside.update(path for path in listed
                      if os.path.dirname(path) in folders)
    return {'scope': sorted(in_scope), 'tests': sorted(beside - in_scope)}


def any_untracked(project_root):
    """True when the tree holds any untracked, non-ignored file at all.

    One git call, so a caller asking about every feature asks per feature
    only when the answer could be yes.
    """
    listed = _git_lines(project_root,
                        ['ls-files', '-z', '--others', '--exclude-standard'])
    return listed is None or bool(listed)


# ---------------------------------------------------------------------------
# Which features a run selects
# ---------------------------------------------------------------------------

def selection(project_root, features=None, os_name=None, index=None):
    """`[{feature, selected, reasons, untracked}]` for every spec, sorted.

    A feature is selected when any of these holds, and each that holds adds
    one reason, in this order:

    - no section for this operating system exists in either source of its
      evidence: `no run on <System> yet`, the system as a person reads it;
    - the newest such section's fingerprint differs from the one taken now:
      `<part> changed since <sha7>` for each part that differs;
    - that fingerprint is the one taken now and the status counts one of
      its rules under `rules to test` (`_left_to_test`): `<n> rules to
      test`, or `1 rule to test`, the status's own words;
    - an untracked, non-ignored file sits under its scope or beside one of
      its marker files: `a file is not tracked`, with the files under
      `untracked` as `{scope, tests}`;
    - it names no files (`incomplete_reason`), so which code belongs to it
      cannot be told: `names no files, so every run includes it`.

    No commit is compared, so the answer survives a rebase, a merge and a
    tree with changes no commit holds. An anchor's `code` part is the
    project, so an edit to any tracked file outside `RECORDS` selects every
    anchor.
    """
    from purlin import evidence as evidence_module

    features = _features(project_root, features)
    os_name = os_name or evidence_module.host_os()
    if index is None:
        index = marker_index(project_root)
    look_for_untracked = any_untracked(project_root)
    cache = {}
    to_test = None
    out = []
    for name in sorted(features):
        reasons = []
        loaded = evidence_module.load(project_root, name)
        mine = [entry for entry in evidence_module.sections(loaded)
                if entry['os'] == os_name]
        if not mine:
            reasons.append(NO_RUN_YET % evidence_module.os_word(os_name))
        else:
            newest = mine[0]
            for entry in mine[1:]:
                if (_text(entry['section'].get('at'))
                        > _text(newest['section'].get('at'))):
                    newest = entry
            now = fingerprint(project_root, name, features, index, cache)
            commit = _text(newest['section'].get('commit'))[:7]
            for part in differing_parts(newest['section'].get('fingerprint'),
                                        now):
                reasons.append(CHANGED_SINCE % (part, commit or 'unknown'))
            if not reasons:
                # The evidence is current and may still hold a result the
                # status sends the person to `purlin:test` for.
                if to_test is None:
                    to_test = _left_to_test(project_root)
                if to_test.get(name):
                    reasons.append(to_test[name])
        loose = {'scope': [], 'tests': []}
        if look_for_untracked:
            loose = untracked_parts(project_root, name, features, index)
            if loose['scope'] or loose['tests']:
                reasons.append(NOT_TRACKED)
        if incomplete_reason(project_root, name, features):
            reasons.append(NAMES_NO_FILES)
        out.append({'feature': name, 'selected': bool(reasons),
                    'reasons': reasons, 'untracked': loose})
    return out


def _left_to_test(project_root):
    """`{feature: reason}` for each feature the status counts a rule of
    under `rules to test`.

    The status decides it, in `summary.rule_kind`, and the payload carries
    its answer as each rule's `left`; the reason is the status's own words
    for the count, so the line `Left to do` prints and what a run selects
    cannot disagree.
    """
    from purlin import payload as payload_module
    from purlin import summary as summary_module
    one, many = next((kind[1], kind[2]) for kind in summary_module.KINDS
                     if kind[0] == 'to_test')
    found = {}
    for feature in payload_module.build_payload(project_root)['features']:
        count = sum(1 for rule in feature.get('rules') or ()
                    if rule.get('left') == 'to_test')
        if count:
            found[feature.get('name')] = '%d %s' % (
                count, one if count == 1 else many)
    return found


# The reasons `selection` gives, in the words a run prints them in.
NO_RUN_YET = 'no run on %s yet'
CHANGED_SINCE = '%s changed since %s'
NOT_TRACKED = 'a file is not tracked'
NAMES_NO_FILES = 'names no files, so every run includes it'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(text):
    return ' '.join((text or '').split())


def _text(value):
    return value if isinstance(value, str) else ''


def _features(project_root, features):
    return specs_module.scan_specs(project_root) if features is None else features


def _info(feature, features):
    info = features.get(feature)
    if info is None:
        raise KeyError('no spec defines the feature %s' % feature)
    return info
