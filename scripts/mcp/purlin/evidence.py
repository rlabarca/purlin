"""Read a feature's evidence files.

    .purlin/evidence/local/<feature>.json   written on a person's machine
    .purlin/evidence/ci/<feature>.json      written by a remote runner

The folder is the source. Each file holds one section per operating system
that ran the feature's tests, and, once an audit has read the feature, one
audit entry per rule. `references/formats/evidence_format.md` is the shape.

This module reads and never writes. It answers four questions: which sections
exist, whether each is current against a fingerprint taken now and which
parts are out of date, which audit entry answers a rule whose rule, proof and
test hashes are known, and which section is the newest across both sources.
It also reads what a section says about each proof and which tests it
lists, the newest `audit.mutation`, and which operating system this machine
is, so a writer and a reader spell it the same way.

A file that cannot be read, is not JSON, carries another schema, or names a
source other than its folder is ignored, and the reader says so once per file
in `warnings`.

One more file is read here and is not evidence: `.purlin/runtime/
audit_could_not_run.json`, which `purlin:audit` leaves behind for the rules
whose model call could not be made. Nothing is written into the evidence for
such a rule, so the next audit tries it again; this file only lets the strong
cell say why it still reads `not audited`. It sits under `runtime/`, which is
never committed.
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import fingerprint as fingerprint_module          # noqa: E402

SCHEMA = 'purlin-evidence/1'
SOURCES = ('local', 'ci')
PLATFORMS = ('windows', 'macos', 'linux')
EVIDENCE_DIR = '.purlin/evidence'
COULD_NOT_RUN_PATH = '.purlin/runtime/audit_could_not_run.json'


# How `sys.platform` spells each operating system a section is keyed by.
_OS_PREFIXES = (('win', 'windows'), ('darwin', 'macos'), ('linux', 'linux'))


def host_os():
    """`windows`, `macos` or `linux` for the machine this runs on.

    The one answer, so a run that writes a section and a cell that reads one
    never spell an operating system two ways.
    """
    for prefix, name in _OS_PREFIXES:
        if sys.platform.startswith(prefix):
            return name
    return sys.platform


# What a person reads for each stored system word, in full and in a small
# box. A word that is not one of the three is read as `linux`.
OS_WORDS = {'windows': ('Windows', 'Win'), 'macos': ('macOS', 'Mac'),
            'linux': ('Linux/Unix', 'Lin')}


def os_word(key):
    """`Windows`, `macOS` or `Linux/Unix` for a stored system word."""
    return OS_WORDS.get(key, OS_WORDS['linux'])[0]


def os_short(key):
    """`Win`, `Mac` or `Lin` for a stored system word."""
    return OS_WORDS.get(key, OS_WORDS['linux'])[1]


def evidence_path(source, feature):
    """`.purlin/evidence/<source>/<feature>.json`, `/` separated."""
    return '%s/%s/%s.json' % (EVIDENCE_DIR, source, feature)


def feature_names(project_root):
    """Every feature a file under `.purlin/evidence/` names, sorted.

    A name is read off the file name in either source folder; whether the
    file parses is `load`'s question.
    """
    names = set()
    for source in SOURCES:
        folder = os.path.join(project_root, *EVIDENCE_DIR.split('/'))
        folder = os.path.join(folder, source)
        try:
            listed = os.listdir(folder)
        except OSError:
            continue
        names.update(name[:-len('.json')] for name in listed
                     if name.endswith('.json'))
    return sorted(names)


def load(project_root, feature):
    """Both evidence files of one feature.

    Returns `{feature, files, paths, warnings}`: `files` maps each source to
    the parsed file, or `None` when there is none or it was ignored; `paths`
    maps each source to its project-relative path; `warnings` holds one
    sentence per ignored file.
    """
    files = {}
    paths = {}
    warnings = []
    for source in SOURCES:
        path = evidence_path(source, feature)
        paths[source] = path
        files[source] = None
        full = os.path.join(project_root, *path.split('/'))
        if not os.path.isfile(full):
            continue
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (IOError, OSError, UnicodeDecodeError, ValueError):
            warnings.append('%s is not valid JSON; it is ignored.' % path)
            continue
        if not isinstance(data, dict):
            warnings.append('%s is not a JSON object; it is ignored.' % path)
            continue
        if data.get('schema') != SCHEMA:
            warnings.append('%s carries the schema %s, not %s; it is ignored.'
                            % (path, _shown(data.get('schema')), SCHEMA))
            continue
        if data.get('source') != source:
            warnings.append('%s names the source %s but sits in %s/; it is '
                            'ignored.' % (path, _shown(data.get('source')),
                                          source))
            continue
        files[source] = data
    return {'feature': feature, 'files': files, 'paths': paths,
            'warnings': warnings}


def sections(loaded):
    """Every platform section, `local` first, then by operating system.

    Each entry is `{source, os, path, section}`, where `section` is the
    object the file holds for that operating system. A key other than
    `windows`, `macos` or `linux`, or a section that is not an object, is
    skipped.
    """
    out = []
    for source in SOURCES:
        data = loaded['files'].get(source)
        platforms = data.get('platforms') if data else None
        if not isinstance(platforms, dict):
            continue
        for os_name in PLATFORMS:
            section = platforms.get(os_name)
            if isinstance(section, dict):
                out.append({'source': source, 'os': os_name,
                            'path': loaded['paths'][source],
                            'section': section})
    return out


def check(section, now):
    """`{current, out_of_date}` for one section against a fingerprint taken now.

    `out_of_date` lists the parts, of `spec`, `code` and `tests`, whose
    stored hash differs from `now`; the section is current when it is empty.
    A section with no fingerprint is out of date on all three.
    """
    parts = fingerprint_module.differing_parts(section.get('fingerprint'), now)
    return {'current': not parts, 'out_of_date': parts}


def checked_sections(loaded, now):
    """`sections(loaded)`, each entry carrying `check`'s two keys as well."""
    out = []
    for entry in sections(loaded):
        entry = dict(entry)
        entry.update(check(entry['section'], now))
        out.append(entry)
    return out


def newest(loaded):
    """The section with the latest `at` across both sources, or `None`.

    Two sections with the same `at` resolve to the first in `sections`
    order, so `local` wins a tie.
    """
    best = None
    for entry in sections(loaded):
        at = _text(entry['section'].get('at'))
        if best is None or at > _text(best['section'].get('at')):
            best = entry
    return best


def audit_entry(loaded, rule_id, rule_hash, proof_hash, test_hash):
    """The audit entry for a rule whose three hashes match, or `None`.

    An entry answers only while its `rule_hash`, `proof_hash` and
    `test_hash` all equal the ones given; its `commit` and `at` do not
    matter. Where both sources hold a matching entry the later `at` wins.
    The entry comes back as a copy carrying `source` and `path`.
    """
    best = None
    for source in SOURCES:
        data = loaded['files'].get(source)
        audit = data.get('audit') if data else None
        rules = audit.get('rules') if isinstance(audit, dict) else None
        entry = rules.get(rule_id) if isinstance(rules, dict) else None
        if not isinstance(entry, dict):
            continue
        if (entry.get('rule_hash'), entry.get('proof_hash'),
                entry.get('test_hash')) != (rule_hash, proof_hash, test_hash):
            continue
        if best is None or _text(entry.get('at')) > _text(best.get('at')):
            best = dict(entry, source=source, path=loaded['paths'][source])
    return best


def could_not_run(project_root):
    """`{feature: {rule: {rule_hash, proof_hash, test_hash, why}}}`, or `{}`.

    What the last audit could not do: the rules whose model call failed,
    each keyed by the hashes it would have read. A file that is missing or
    cannot be read is the same as an empty one.
    """
    path = os.path.join(project_root, *COULD_NOT_RUN_PATH.split('/'))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, UnicodeDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def why_not_audited(table, feature, rule_id, rule_hash, proof_hash,
                    test_hash):
    """Why the last audit could not read this rule's current hashes, or None."""
    entry = ((table or {}).get(feature) or {}).get(rule_id)
    if not isinstance(entry, dict):
        return None
    if (entry.get('rule_hash'), entry.get('proof_hash'),
            entry.get('test_hash')) != (rule_hash, proof_hash, test_hash):
        return None
    return entry.get('why') or None


def proof_results(section):
    """`{proof_id: 'pass' | 'fail'}` for one section.

    `fail` wins over `pass` where two tests claim one proof, and `missing`
    and `not run` are left out, so a proof nothing observed reads as nothing
    observed.
    """
    results = {}
    for entry in (section or {}).get('proofs') or ():
        if not isinstance(entry, dict):
            continue
        proof_id = entry.get('id')
        result = entry.get('result')
        if not proof_id or result not in ('pass', 'fail'):
            continue
        if results.get(proof_id) != 'fail':
            results[proof_id] = result
    return results


def proof_tests(section, proof_id):
    """`[(file, name)]` for the tests one section lists against a proof."""
    out = []
    for entry in (section or {}).get('proofs') or ():
        if not isinstance(entry, dict) or entry.get('id') != proof_id:
            continue
        test = entry.get('test') or ''
        if not test:
            continue
        path, _, name = test.partition('::')
        if (path, name) not in out:
            out.append((path, name))
    return out


def mutation(loaded):
    """The newest `audit.mutation` across both sources, or `None`."""
    best = None
    for source in SOURCES:
        data = loaded['files'].get(source)
        audit = data.get('audit') if data else None
        found = audit.get('mutation') if isinstance(audit, dict) else None
        if not isinstance(found, dict):
            continue
        if best is None or _text(found.get('at')) > _text(best.get('at')):
            best = found
    return best


def _text(value):
    return value if isinstance(value, str) else ''


def _shown(value):
    return 'none' if value is None else json.dumps(value)
