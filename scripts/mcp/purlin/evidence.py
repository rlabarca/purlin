"""Read a feature's evidence files.

    .purlin/evidence/local/<feature>.json   written on a person's machine
    .purlin/evidence/ci/<feature>.json      written by a project's own run
                                            on another system

The folder is the source. Each file holds one section per operating system
that ran the feature's tests, and, once an audit has read the feature, one
audit entry per rule. `references/formats/evidence_format.md` is the shape.

This module reads and never writes. It answers four questions: which sections
exist, whether each is current against a fingerprint taken now and which
parts are out of date, which audit entry answers a rule whose rule, proof and
test hashes are known, and which section is the newest across both sources.
It also reads what a section says about each proof and which tests it
lists, and which operating system this machine is, so a writer and a reader
spell it the same way, and the words a person reads for each operating
system.

A file that cannot be read, is not JSON, carries another schema, or names a
source other than its folder is ignored, and the reader says so once per file
in `warnings`, naming the run that writes it again.
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import fingerprint as fingerprint_module, notices  # noqa: E402

SCHEMA = 'purlin-evidence/2'
SOURCES = ('local', 'ci')
PLATFORMS = ('windows', 'macos', 'linux')
EVIDENCE_DIR = '.purlin/evidence'

# The parts an audit entry is checked on, each with the key that stores it.
AUDIT_PARTS = (('rule', 'rule_hash'), ('proof', 'proof_hash'),
               ('test', 'test_hash'), ('code', 'code_hash'))

# A proof whose every tied test skipped with a reason starting with these
# words reads this result, its reason the text after them.
NOTHING_TO_CHECK = 'nothing to check'
NOTHING_TO_CHECK_PREFIX = 'nothing to check:'


def nothing_reason(reason):
    """The text after `nothing to check: ` where a skip's reason starts
    exactly `nothing to check:`, else None."""
    if not isinstance(reason, str) or not reason.startswith(
            NOTHING_TO_CHECK_PREFIX):
        return None
    return reason[len(NOTHING_TO_CHECK_PREFIX):].strip()


# How `sys.platform` spells each operating system a section is keyed by.
_OS_PREFIXES = (('win', 'windows'), ('darwin', 'macos'))


def host_os():
    """`windows`, `macos` or `linux` for the machine this runs on.

    The one answer, so a run that writes a section and a cell that reads one
    never spell an operating system two ways. A system that is neither
    Windows nor macOS is `linux`.
    """
    for prefix, name in _OS_PREFIXES:
        if sys.platform.startswith(prefix):
            return name
    return 'linux'


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


# The step that writes an ignored file again, by the folder it sits in.
REWRITE_LOCAL = 'Run purlin:test %s.'
REWRITE_CI = 'Start the run that wrote it again.'


# Why an evidence file is ignored, after `<path>: evidence file ignored.`
NOT_JSON = 'It is not valid JSON.'
NOT_AN_OBJECT = 'It is not a JSON object.'
OTHER_SCHEMA = 'It carries the schema %s, not %s.'
OTHER_SOURCE = 'It names the source %s.'


def _ignored(path, feature, why, fix):
    return notices.line('evidence_ignored', path, why, fix, feature=feature)


def rewrite_fix(source, feature):
    """The sentence an ignored evidence file's warning ends on."""
    return REWRITE_CI if source == 'ci' else REWRITE_LOCAL % feature


def load(project_root, feature):
    """Both evidence files of one feature.

    Returns `{feature, files, paths, warnings}`: `files` maps each source to
    the parsed file, or `None` when there is none or it was ignored; `paths`
    maps each source to its project-relative path; `warnings` holds one
    line per ignored file, ending on the step that writes it again.
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
        fix = rewrite_fix(source, feature)
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (IOError, OSError, UnicodeDecodeError, ValueError):
            warnings.append(_ignored(path, feature, NOT_JSON, fix))
            continue
        if not isinstance(data, dict):
            warnings.append(_ignored(path, feature, NOT_AN_OBJECT, fix))
            continue
        if data.get('schema') != SCHEMA:
            warnings.append(_ignored(path, feature, OTHER_SCHEMA % (
                _shown(data.get('schema')), SCHEMA), fix))
            continue
        if data.get('source') != source:
            warnings.append(_ignored(path, feature, OTHER_SOURCE % _shown(
                data.get('source')), fix))
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


def audit_entry(loaded, rule_id, rule_hash, proof_hash, test_hash, code_hash):
    """The rule's audit entry, or None: a current one before one out of date,
    then the later `at`. A copy carrying `source`, `path` and `out_of_date`,
    the parts of `rule`, `proof`, `test` and `code` whose stored hash is not
    the one given, in that order; [] for a current entry."""
    given = {'rule_hash': rule_hash, 'proof_hash': proof_hash,
             'test_hash': test_hash, 'code_hash': code_hash}
    best = best_rank = None
    for source in SOURCES:
        data = loaded['files'].get(source)
        audit = data.get('audit') if data else None
        rules = audit.get('rules') if isinstance(audit, dict) else None
        entry = rules.get(rule_id) if isinstance(rules, dict) else None
        if not isinstance(entry, dict):
            continue
        parts = [part for part, key in AUDIT_PARTS
                 if entry.get(key) != given[key]]
        rank = (not parts, _text(entry.get('at')))
        if best is None or rank > best_rank:
            best_rank = rank
            best = dict(entry, source=source, path=loaded['paths'][source],
                        out_of_date=parts)
    return best


# A proof's result in one section is the worst of its tests', in this order.
_WORST = {'fail': 3, 'not run': 2, NOTHING_TO_CHECK: 1, 'pass': 0}
_READ_AS = {'pass': 'pass', 'fail': 'fail', 'missing': 'not run',
            'not run': 'not run', NOTHING_TO_CHECK: NOTHING_TO_CHECK}


def proof_results(section):
    """`{proof_id: {'result': ..., 'reason': ...}}` for one section.

    Each proof reads the worst of the entries the section lists against it:
    `fail` where one failed, else `not run` where one is `missing` or `not
    run`, else `nothing to check` where one reads so, else `pass`. A proof
    has passed only when every test tied to it ran and passed. `reason` is
    there only where an entry gave one.
    """
    results = {}
    for entry in (section or {}).get('proofs') or ():
        if not isinstance(entry, dict):
            continue
        proof_id = entry.get('id')
        result = _READ_AS.get(entry.get('result'))
        if not proof_id or result is None:
            continue
        known = results.get(proof_id)
        if known is None or _WORST[result] > _WORST[known['result']]:
            known = results[proof_id] = {'result': result}
        if (known['result'] == result and 'reason' not in known
                and isinstance(entry.get('reason'), str)):
            known['reason'] = entry['reason']
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


def _text(value):
    return value if isinstance(value, str) else ''


def _shown(value):
    return 'none' if value is None else json.dumps(value)
