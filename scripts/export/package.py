"""The evidence package: one data file describing one version.

`purlin:sign` builds it, and nothing else does: `sign.py` calls `build`,
writes the file with `write` and commits it with the first sign-off of the
version. `sign.py --check FILE` calls `check_file`. This module has no
command line of its own.

The package holds, for every rule, its words, its proofs, its tests, each
result on each operating system with who ran it and on which machine, and
for a result carried forward the run that took it, what
the audit found, its two statuses, the one kind of work it waits for and
who wrote and last changed its words, its proofs and its tests. A rule whose
every proof is `@manual` has no test, so each of its results reads
`checked at sign-off`. Above them it carries whether the tests are met, the
total, the count that pass, what the audit found over the rules that pass
their tests and have a tested proof, what is left to do, the runs the
results came from and every hand check. It is written to

    .purlin/evidence/package/<version>.json

**It is evidence for review.** Purlin hands the package to a regulated
document and sign-off system, which holds the controlled document, the
authority to sign it off and the signature that counts under the regulation.
Purlin makes no claim that the software is compliant.

**It reads what git holds.** The package is built from a checkout of the
commit the evidence was taken at, so evidence that is written and not
committed is left out and named in the package's `warnings`. That commit is
`HEAD`, stepping back over any commit that changed nothing but a file under
the package folder, a sign-off included, so the package a tag carries names
the commit below it.

**The same commit always gives the same bytes.** Keys are sorted within
every object except the top level, which keeps the order the format names;
lists keep a fixed order; nothing records when the package was built; the
file is UTF-8 with `\\n` line ends and a trailing newline on every operating
system. The `fingerprint` field is the sha256 of the file's own bytes with
that field set to the empty string.

**The same version of the code.** A result counts for a sign-off only where
every commit from the one its section names to the package's `commit`
changes nothing but files under `.purlin/` and leaves the `tests` setting of
`.purlin/config.json` as it was, read by `only_records_between`:
`same_code`. A result a run carried forward is recorded in a section that
names the run's own commit, so it counts there, and its `carried` names the
run that took it.

`references/formats/package_format.md` holds every field.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'),):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import (PURLIN_VERSION,                            # noqa: E402
                    evidence as evidence_module,
                    fingerprint as fingerprint_module,
                    markers as markers_module,
                    payload as payload_module,
                    project as project_module,
                    signatures as signatures_module,
                    specs as specs_module,
                    states as states_module,
                    summary as summary_module,
                    wording as wording_module)

SCHEMA = 'purlin-package/4'
PACKAGE_DIR = signatures_module.PACKAGE_DIR
RECORDS_DIR = '.purlin/'
# The settings file, whose `tests` setting is part of the code.
CONFIG_PATH = '.purlin/config.json'

# The top-level keys in the order the file carries them. Whether the tests
# are met is what a reader sees first after the schema.
TOP_LEVEL = ('schema', 'met', 'rules', 'steps', 'audit', 'left',
             'purlin_version', 'project', 'version', 'tag', 'commit', 'runs',
             'features', 'hand_checks', 'warnings', 'fingerprint')

CELLS = ('passed', 'strong')

# What a hand check's entry says of it: what each signer saw is in the
# sign-offs beside the package.
CHECKED = 'in the sign-offs'

# The prefix a test's skip reason carries when it found nothing to check.
NOTHING_TO_CHECK = 'nothing to check'

NOT_COMMITTED = '%s is written and not committed; the package leaves it out.'


class PackageError(Exception):
    """The package could not be built or written; the message says why."""


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git(project_root, *args):
    try:
        return subprocess.run(['git'] + list(args), capture_output=True,
                              text=True, cwd=project_root, timeout=120)
    except (subprocess.SubprocessError, OSError) as error:
        return subprocess.CompletedProcess(args, 1, '', str(error))


def _git_out(project_root, *args):
    """What a git command prints, stripped, or '' when it fails."""
    done = _git(project_root, *args)
    return done.stdout.strip() if done.returncode == 0 else ''


def _commit_of(project_root, ref):
    """The full sha `ref` names, or None."""
    if not ref:
        return None
    return _git_out(project_root, 'rev-parse', '--verify', '--quiet',
                    '%s^{commit}' % ref) or None


def _changed_paths(project_root, sha):
    listed = _git(project_root, 'diff-tree', '--no-commit-id', '--name-only',
                  '-r', '--root', sha)
    if listed.returncode != 0:
        return None
    return [line.strip() for line in listed.stdout.splitlines() if line.strip()]


def evidence_commit(project_root, start='HEAD'):
    """The commit the evidence was taken at: `start`, below any package commit.

    A commit that changed nothing but files under the package folder adds no
    evidence, so the walk steps to its parent. The package a tag carries
    therefore names the commit beneath it, and building the package at the
    tag again reads the same commit. None where there is no commit.
    """
    sha = _commit_of(project_root, start)
    if sha is None:
        return None
    while True:
        paths = _changed_paths(project_root, sha)
        if not paths or not all(path.startswith(PACKAGE_DIR + '/')
                                for path in paths):
            return sha
        parent = _commit_of(project_root, '%s^' % sha)
        if parent is None:
            return sha
        sha = parent


def _tests_setting(project_root, ref):
    """The `tests` setting of `.purlin/config.json` as the commit `ref` holds it.

    The value of the key `tests`, as parsed JSON; None where the commit holds
    no settings file or the file holds no such key. A file that cannot be
    parsed answers with its own text, so two that differ read as different.
    """
    held = _git(project_root, 'show', '%s:%s' % (ref, CONFIG_PATH))
    if held.returncode != 0:
        return None
    try:
        settings = json.loads(held.stdout)
    except ValueError:
        return ('unreadable', held.stdout)
    return settings.get('tests') if isinstance(settings, dict) else None


def only_records_between(project_root, older, newer):
    """True when `older` is `newer`, or an ancestor of it from which every commit up
    to `newer` changes only paths under `.purlin/` and the `tests` setting reads the
    same at both ends."""
    older = _commit_of(project_root, older)
    newer = _commit_of(project_root, newer)
    if older is None or newer is None:
        return False
    if older == newer:
        return True
    if _git(project_root, 'merge-base', '--is-ancestor', older,
            newer).returncode != 0:
        return False
    listed = _git(project_root, 'log', '-m', '--format=', '--name-only',
                  '%s..%s' % (older, newer))
    if listed.returncode != 0:
        return False
    paths = {line.strip() for line in listed.stdout.splitlines()
             if line.strip()}
    if not all(path.startswith(RECORDS_DIR) for path in paths):
        return False
    if CONFIG_PATH not in paths:
        return True
    return (_tests_setting(project_root, older)
            == _tests_setting(project_root, newer))


def same_code(project_root, section_commit, head=None):
    """only_records_between(section_commit, head or HEAD); False for an empty commit."""
    if not section_commit:
        return False
    return only_records_between(project_root, section_commit, head or 'HEAD')


def uncommitted_evidence(project_root):
    """The evidence files, sorted, that are not committed as they stand."""
    listed = _git(project_root, 'status', '--porcelain', '--untracked-files=all',
                  '--', evidence_module.EVIDENCE_DIR)
    if listed.returncode != 0:
        return []
    found = set()
    for line in listed.stdout.splitlines():
        if len(line) <= 3:
            continue
        path = line[3:].strip('"').split(' -> ')[-1]
        if not path.endswith('.json'):
            continue
        if any(path.startswith('%s/%s/' % (evidence_module.EVIDENCE_DIR, source))
               for source in evidence_module.SOURCES):
            found.add(path)
    return sorted(found)


class _Checkout(object):
    """A checkout of one commit in a temporary folder, removed on close.

    Its folder carries the project's own folder name, so the project name a
    reader works out from it is the project's.
    """

    def __init__(self, project_root, sha):
        self.project_root = project_root
        self.parent = tempfile.mkdtemp(prefix='purlin-package-')
        name = os.path.basename(os.path.abspath(project_root)) or 'project'
        self.root = os.path.join(self.parent, name)
        added = _git(project_root, 'worktree', 'add', '--detach', '--quiet',
                     self.root, sha)
        if added.returncode != 0:
            shutil.rmtree(self.parent, ignore_errors=True)
            raise PackageError('the commit %s could not be checked out: %s'
                               % (sha[:7], added.stderr.strip()))

    def close(self):
        _git(self.project_root, 'worktree', 'remove', '--force', self.root)
        shutil.rmtree(self.parent, ignore_errors=True)
        _git(self.project_root, 'worktree', 'prune')


# ---------------------------------------------------------------------------
# The version
# ---------------------------------------------------------------------------

def project_version(project_root):
    """The VERSION file, package.json, pyproject.toml or the first root *.csproj, in
    that order; None where none states a version."""
    for reader in (_version_file, _package_json, _pyproject, _csproj):
        named = reader(project_root)
        if named:
            return named
    return None


_PACKAGE_JSON = 'package.json'
_PYPROJECT = 'pyproject.toml'
_PYPROJECT_TABLES = ('project', 'tool.poetry')
_TOML_VERSION = re.compile(r'''^version\s*=\s*(["'])(.*?)\1\s*(#.*)?$''')
_CSPROJ_VERSION = re.compile(r'<Version>\s*([^<]*?)\s*</Version>')


def _read(project_root, name):
    try:
        with open(os.path.join(project_root, name), 'r',
                  encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return ''


def _version_file(project_root):
    return _read(project_root, 'VERSION').strip()


def _package_json(project_root):
    try:
        data = json.loads(_read(project_root, _PACKAGE_JSON) or '{}')
    except ValueError:
        return ''
    version = data.get('version') if isinstance(data, dict) else None
    return version.strip() if isinstance(version, str) else ''


def _pyproject(project_root):
    text = _read(project_root, _PYPROJECT)
    for table in _PYPROJECT_TABLES:
        inside = False
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith('['):
                inside = line.split('#', 1)[0].strip() == '[%s]' % table
                continue
            found = _TOML_VERSION.match(line) if inside else None
            if found and found.group(2).strip():
                return found.group(2).strip()
    return ''


def _csproj(project_root):
    try:
        names = sorted(name for name in os.listdir(project_root)
                       if name.endswith('.csproj'))
    except OSError:
        return ''
    for name in names:
        found = _CSPROJ_VERSION.search(_read(project_root, name))
        if found and found.group(1):
            return found.group(1)
    return ''


def package_path(version):
    """`.purlin/evidence/package/<version>.json`, `/` separated."""
    return signatures_module.package_rel(version)


def tag_name(version):
    """`signed/<version>`."""
    return 'signed/%s' % version


# ---------------------------------------------------------------------------
# Building the package
# ---------------------------------------------------------------------------

def build(project_root, version):
    """The package for `version` as a dict, its top-level keys in the format's order."""
    commit = evidence_commit(project_root)
    if commit is None:
        raise PackageError('the project has no commit yet')
    warnings = [NOT_COMMITTED % path
                for path in uncommitted_evidence(project_root)]

    checkout = _Checkout(project_root, commit)
    try:
        tree = checkout.root
        # A warning about a tag passed over is left out: two clones of one
        # commit may hold different tags, and must build the same bytes.
        payload = payload_module.build_payload(tree, generated_by='sign',
                                               tag_warnings=False)
        features = specs_module.scan_specs(tree)
        seen = []
        entries = _features(tree, payload, features, commit, seen)
        project = project_module.project_name(tree)
    finally:
        checkout.close()

    for warning in payload.get('warnings') or ():
        if warning not in warnings:
            warnings.append(warning)

    left = [dict(item) for item in payload.get('left') or ()]
    summary = payload.get('summary') or {}
    steps = summary.get('steps') or {}
    values = {
        'schema': SCHEMA,
        'met': not any(item.get('kind') in summary_module.BLOCKING
                       for item in left),
        'rules': sum(len(feature['rules']) for feature in entries),
        'steps': {'passed': steps.get('passed') or 0},
        'audit': audit_counts(entries),
        'left': left,
        'purlin_version': PURLIN_VERSION,
        'project': project,
        'version': version,
        'tag': tag_name(version),
        'commit': commit,
        'runs': runs_of(seen),
        'features': entries,
        'hand_checks': _hand_checks(entries),
        'warnings': warnings,
        'fingerprint': '',
    }
    package = {key: values[key] for key in TOP_LEVEL}
    package['fingerprint'] = fingerprint_of(package)
    return package


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _features(tree, payload, features, commit, seen):
    """`features[]`, by name, each carrying its own rules by number.

    A feature entry holds `name`, `spec`, `scope`, `anchor` and `rules`, and
    nothing else; an anchor's `scope` is `[]`, since its rules cover the
    whole project. `seen` gains `(section entry, feature, rule id, taken)`
    for each result, `taken` being `_taken`'s answer, which `runs_of`
    groups.
    """
    index = fingerprint_module.marker_index(tree)
    authors = _Authors(tree)
    authors.prefetch(payload.get('features') or ())
    same = {}
    out = []
    for feature in sorted(payload.get('features') or (),
                          key=lambda entry: entry.get('name') or ''):
        name = feature.get('name')
        loaded = evidence_module.load(tree, name)
        sections = []
        # The feature's `code` part, which an audit entry is checked on.
        code = ''
        if any(loaded['files'].values()):
            now = fingerprint_module.fingerprint(tree, name, features, index)
            sections = evidence_module.checked_sections(loaded, now)
            code = now['code']
        for entry in sections:
            sha = entry['section'].get('commit') or ''
            if sha not in same:
                same[sha] = same_code(tree, sha, commit)
        own = [rule for rule in feature.get('rules') or ()
               if rule.get('feature') == name]
        own.sort(key=lambda rule: _rule_number(rule.get('id')))
        seen.extend((entry, name, rule.get('id'),
                     _taken(entry['section'], _ids(rule)))
                    for rule in own for entry in sections
                    if _speaks(entry['section'], rule.get('id'),
                               _ids(rule)))
        anchor = bool(feature.get('is_anchor'))
        spec = feature.get('spec_path')
        out.append({
            'name': name,
            'spec': spec,
            'scope': [] if anchor else list(feature.get('scope') or ()),
            'anchor': anchor,
            'rules': [_rule(rule, loaded, sections, same,
                            authors.of(name, spec, rule), code)
                      for rule in own],
        })
    return out


def _rule(rule, loaded, sections, same, authors, code=''):
    rule_id = rule.get('id')
    proofs = rule.get('proofs') or ()
    return {
        'id': rule_id,
        'text': rule.get('text') or '',
        'left': rule.get('left'),
        'proofs': [{'id': proof.get('id'), 'text': proof.get('text') or '',
                    'manual': bool(proof.get('manual')),
                    'env': proof.get('env')} for proof in proofs],
        'tests': _tests(rule),
        'results': _results(rule_id, proofs, sections, same),
        'audit': _audit(rule, loaded, code),
        'statuses': {name: _status(rule, name) for name in CELLS
                     if name in (rule.get('cells') or {})},
        'authors': authors,
    }


def _tests(rule):
    """`{proof, file, name}` per test backing a proof, then per test marked
    with the rule's own id, whose `proof` is then the `RULE-N`."""
    rule_id = rule.get('id')
    return ([{'proof': proof.get('id'), 'file': test.get('file'),
              'name': test.get('name')}
             for proof in rule.get('proofs') or ()
             for test in proof.get('tests') or ()]
            + [{'proof': rule_id, 'file': test.get('file'),
                'name': test.get('name')}
               for test in rule.get('tests') or ()])


def _entries(section, ids):
    """The section's proof entries for the ids given, by id."""
    found = {}
    for entry in (section or {}).get('proofs') or ():
        if isinstance(entry, dict) and entry.get('id') in ids:
            found.setdefault(entry['id'], []).append(entry)
    return found


def _ids(rule):
    """The ids a section lists a rule's results under: its proofs', else its own."""
    return {proof.get('id') for proof in rule.get('proofs') or ()} \
        or {rule.get('id')}


def _speaks(section, rule_id, ids):
    """True when a section holds a result for the rule."""
    return (rule_id in ((section or {}).get('rules') or {})
            or bool(_entries(section, ids)))


def _word(section, rule_id, ids):
    """What one section saw for a rule: its own word, else read from its proofs."""
    word = ((section or {}).get('rules') or {}).get(rule_id)
    if word:
        return word
    seen = [entry.get('result')
            for entries in _entries(section, ids).values()
            for entry in entries]
    if not seen:
        return 'no test'
    if 'fail' in seen:
        return 'failed'
    if all(result == 'pass' for result in seen):
        return 'passed'
    return 'not run'


def _nothing_to_check(section, ids):
    """`[{proof, reason}]` for each proof whose every entry found nothing to check."""
    out = []
    for proof_id, entries in sorted(_entries(section, ids).items(),
                                    key=lambda item: _rule_number(item[0])):
        if entries and all(entry.get('result') == NOTHING_TO_CHECK
                           for entry in entries):
            out.append({'proof': proof_id,
                        'reason': str(entries[0].get('reason') or '')})
    return out


# What a carried result names of the run that took it.
_CARRIED_KEYS = ('commit', 'at', 'machine', 'email')


def _carried(section, ids):
    """`[{proof, commit, at, machine, email}]`, by proof number, for each
    proof of the rule one of whose entries holds `carried`: a result the
    section's own run did not take, and the run that took it, the newest
    where the proof's tests were taken in several."""
    out = []
    for proof_id, entries in sorted(_entries(section, ids).items(),
                                    key=lambda item: _rule_number(item[0])):
        found = [entry['carried'] for entry in entries
                 if isinstance(entry.get('carried'), dict)]
        if not found:
            continue
        newest = max(found, key=lambda one: str(one.get('at') or ''))
        out.append(dict({key: newest.get(key) or None
                         for key in _CARRIED_KEYS}, proof=proof_id))
    return out


def _taken(section, ids):
    """`{by, machine, at, commit, carried}`: the run a rule's results in one
    section were taken in.

    Where every entry the section holds for the rule was carried forward,
    that is the newest of the runs that took them, and `carried` is true.
    Otherwise it is the section's own run.
    """
    entries = [entry for found in _entries(section, ids).values()
               for entry in found]
    carried = [entry['carried'] for entry in entries
               if isinstance(entry.get('carried'), dict)]
    if entries and len(carried) == len(entries):
        newest = max(carried, key=lambda one: str(one.get('at') or ''))
        return {'by': str(newest.get('email') or 'unknown'),
                'machine': newest.get('machine') or None,
                'at': str(newest.get('at') or ''),
                'commit': newest.get('commit') or None, 'carried': True}
    return {'by': str((section or {}).get('email') or 'unknown'),
            'machine': (section or {}).get('machine') or None,
            'at': str((section or {}).get('at') or ''),
            'commit': (section or {}).get('commit'), 'carried': False}


def _results(rule_id, proofs, sections, same):
    """One entry per section: what that run saw for this rule, by operating system.

    A rule whose every proof is `@manual` reads `checked at sign-off`,
    whatever word the section holds: no test ran for it. `same_code` is false
    for a section that names other code. `carried` names each proof whose
    result the section's own run did not take, and the run that took it."""
    ids = {proof.get('id') for proof in proofs} or {rule_id}
    by_hand = bool(proofs) and all(proof.get('manual') for proof in proofs)
    out = []
    for entry in sections:
        section = entry['section']
        if not _speaks(section, rule_id, ids):
            continue
        out.append({'os': entry['os'], 'source': entry['source'],
                    'result': (states_module.CHECKED_AT_SIGNOFF if by_hand
                               else _word(section, rule_id, ids)),
                    'at': section.get('at'),
                    'commit': section.get('commit'),
                    'runner': section.get('runner'),
                    'machine': section.get('machine'),
                    'current': bool(entry['current']),
                    'out_of_date': sorted(entry['out_of_date']),
                    'same_code': bool(same.get(section.get('commit') or '')),
                    'carried': _carried(section, ids),
                    'nothing_to_check': _nothing_to_check(section, ids)})
    out.sort(key=lambda item: (item['os'], item['source']))
    return out


def _audit(rule, loaded, code=''):
    """What the audit last found for the rule, or None where no audit read it.

    `code` is the `code` part of the feature's fingerprint taken now, the
    fourth hash an entry is checked on. `out_of_date` names the parts that
    changed since the entry was written, `[]` for a current one."""
    summary = rule.get('audit')
    if not summary:
        return None
    entry = evidence_module.audit_entry(
        loaded, rule.get('id'), rule.get('rule_hash'), rule.get('proof_hash'),
        rule.get('test_hash'), code) or {}
    return {'verdict': summary.get('verdict'),
            'findings': [str(line) for line in summary.get('findings') or ()],
            'no_bug': [str(line) for line in entry.get('no_bug') or ()],
            'out_of_date': [str(part) for part in
                            entry.get('out_of_date') or ()],
            'notes': [str(line) for line in summary.get('notes') or ()],
            'explanation': [str(line) for line in entry.get('explanation') or ()],
            'bugs': dict(entry.get('bugs') or {}),
            'model': summary.get('model'),
            'criteria': entry.get('criteria'),
            'at': summary.get('at'),
            'commit': summary.get('commit'),
            'source': entry.get('source')}


# The key a rule is counted under, by its strong cell's word.
_AUDIT_KEYS = {word: key for key, word in summary_module.AUDIT_WORDS}


def audit_counts(entries):
    """`{strong, weak, spot_checked, out_of_date, not_audited}`, as
    `summary.audit_counts` counts them.

    A rule is counted where its passed status reads `passed`, under its
    strong status's word where that is one of the five. No other rule is
    counted: one that does not pass, and one checked by hand, whose strong
    status reads `checked at sign-off`."""
    counts = {key: 0 for key, _word in summary_module.AUDIT_WORDS}
    for feature in entries:
        for rule in feature['rules']:
            if (rule['statuses'].get('passed') or {}).get('word') != 'passed':
                continue
            word = (rule['statuses'].get('strong') or {}).get('word')
            if word in _AUDIT_KEYS:
                counts[_AUDIT_KEYS[word]] += 1
    return counts


def _hand_checks(entries):
    """Every rule with a `@manual` proof, by feature then number, with its proofs."""
    out = []
    for feature in entries:
        for rule in feature['rules']:
            manual = [proof['id'] for proof in rule['proofs'] if proof['manual']]
            if manual:
                out.append({'feature': feature['name'], 'rule': rule['id'],
                            'proofs': manual, 'checked': CHECKED})
    return out


def _status(rule, name):
    """One status: its word and its reasons."""
    cell = (rule.get('cells') or {}).get(name) or {}
    return {'word': cell.get('word'),
            'reasons': [str(reason) for reason in cell.get('reasons') or ()]}


# ---------------------------------------------------------------------------
# The runs
# ---------------------------------------------------------------------------

def runs_of(seen):
    """`runs[]`: one per group of results sharing a source, a system, who
    took them, a machine and whether they were carried forward, local first,
    then by system, a group of carried results after the run that carried
    them.

    `seen` is `(section entry, feature, rule id, taken)` per result, `taken`
    being `_taken`'s answer. Each run names `by`, `machine`, `os`, `source`,
    `at` and `commit`, those of the newest run its results were taken in,
    `rules`, how many rules it holds a result for, and `carried`.
    """
    groups = {}
    for entry, feature, rule_id, taken in seen:
        key = (entry['source'], entry['os'], taken['by'],
               taken['machine'] or '', taken['carried'])
        group = groups.setdefault(key, {'rules': set(), 'at': '',
                                        'commit': None,
                                        'machine': taken['machine']})
        group['rules'].add((feature, rule_id))
        if group['commit'] is None or taken['at'] > group['at']:
            group['at'], group['commit'] = taken['at'], taken['commit']
    order = {name: index for index, name in
             enumerate(states_module.SYSTEM_ORDER)}
    out = []
    for key in sorted(groups, key=lambda key: (
            evidence_module.SOURCES.index(key[0])
            if key[0] in evidence_module.SOURCES else 9,
            order.get(key[1], 9), key[1], key[4], key[2], key[3])):
        source, os_name, by, _machine, carried = key
        group = groups[key]
        out.append({'by': by, 'machine': group['machine'], 'os': os_name,
                    'source': source, 'at': group['at'] or None,
                    'commit': group['commit'], 'rules': len(group['rules']),
                    'carried': carried})
    return out


def time_words(at):
    """`2026-10-01 12:17 UTC` for `2026-10-01T12:17:13Z`."""
    return '%s %s UTC' % (at[:10], at[11:16])


RUN_LINE = 'Tests run by %s on %s at %s on %s: %s on %s.'
# The same for results a run carried forward: who took them, on which
# machine, and the time and commit of the newest run among them.
CARRIED_LINE = ('Carried forward from earlier runs by %s on %s, the newest at '
                '%s on %s: %s on %s.')


def _rules_words(count):
    return '1 rule' if count == 1 else '%d rules' % count


def run_lines(package):
    """K8's run lines, local first."""
    lines = []
    for run in package.get('runs') or ():
        at = time_words(str(run.get('at') or ''))
        commit = str(run.get('commit') or '')[:7]
        system = evidence_module.os_word(run.get('os'))
        words = CARRIED_LINE if run.get('carried') else RUN_LINE
        lines.append(words % (run.get('by'), run.get('machine'), at, commit,
                              _rules_words(run.get('rules') or 0), system))
    return lines


def off_code(package, project_root):
    """[(system words, source, [features])]: the results not recorded on
    the package's commit, by system in the order a person reads them."""
    found = {}
    for feature in package.get('features') or ():
        for rule in feature.get('rules') or ():
            for result in rule.get('results') or ():
                if result.get('same_code'):
                    continue
                key = (result.get('os'), result.get('source'))
                names = found.setdefault(key, [])
                if feature['name'] not in names:
                    names.append(feature['name'])
    return _by_system(found)


def _by_system(found):
    """`{(os, source): [features]}` as `[(system words, source, [features])]`,
    by system in the order a person reads them, a person's run first."""
    order = {name: index for index, name in
             enumerate(states_module.SYSTEM_ORDER)}
    return [(evidence_module.os_word(os_name), source, sorted(names))
            for (os_name, source), names in sorted(
                found.items(), key=lambda item: (
                    order.get(item[0][0], 9), item[0][0],
                    evidence_module.SOURCES.index(item[0][1])
                    if item[0][1] in evidence_module.SOURCES else 9))]


def taken_dirty(package, project_root):
    """[(system words, source, [features])]: the committed results taken while
    the working tree held changes that were not committed, in `off_code`'s
    shape and order. A section says so itself, under `dirty`."""
    found = {}
    for feature in package.get('features') or ():
        name = feature['name']
        loaded = evidence_module.load(project_root, name)
        for entry in evidence_module.sections(loaded):
            if entry['section'].get('dirty') is not True:
                continue
            if not any(_speaks(entry['section'], rule.get('id'),
                               {proof.get('id') for proof
                                in rule.get('proofs') or ()}
                               or {rule.get('id')})
                       for rule in feature.get('rules') or ()):
                continue
            names = found.setdefault((entry['os'], entry['source']), [])
            if name not in names:
                names.append(name)
    return _by_system(found)


# ---------------------------------------------------------------------------
# Who wrote and last changed each rule, proof and test
# ---------------------------------------------------------------------------

_PROOF_LINE = r'^\s*-\s+%s\s*\('

# What git prints per commit a rule or a proof is read from: the sha, the
# author's email, then each `Co-Authored-By` trailer's value, whatever the
# case of its key's letters, the values parted by `\x1f`
# as well: a text's `splitlines` leaves that character alone.
_CO_AUTHORS = ('%(trailers:key=Co-authored-by,valueonly,unfold,'
               'separator=%x1f)')
_COMMIT_FORMAT = '--format=%H %ae%x1f' + _CO_AUTHORS
# How many commits one `git log` is asked for the trailers of.
_TRAILER_BATCH = 500


class _Authors(object):
    """`authors` for each rule, read from git in the checkout."""

    def __init__(self, tree):
        self.tree = tree
        self._text = {}
        self._tests = None
        self._logs = {}
        self._reader = None
        self._changes = {}
        self._co_authors = {}

    def prefetch(self, features):
        """Ask git every question `of` will ask for these features, several
        at once: one `git log` per rule and per proof, one blame per test
        file. `of` then answers from what came back."""
        from concurrent.futures import ThreadPoolExecutor
        asked, files = [], set()
        for feature in features:
            spec = feature.get('spec_path')
            for rule in feature.get('rules') or ():
                if rule.get('feature') != feature.get('name'):
                    continue
                asked.append(self._rule_args(spec, rule.get('text') or ''))
                asked.extend(self._proof_args(spec, proof.get('id'))
                             for proof in rule.get('proofs') or ())
                files.update(test['file'] for test in _tests(rule))
        asked = sorted({args for args in asked if args})
        with ThreadPoolExecutor(max_workers=8) as pool:
            for args, listed in zip(asked, pool.map(
                    lambda args: _git_out(self.tree, *args), asked)):
                self._logs[args] = listed
        self._reader = wording_module.reader(self.tree, files)
        # One more question, for every test at once: the co-authors of the
        # commits the blames named.
        changed = {found[0] for feature in features
                   for rule in feature.get('rules') or ()
                   if rule.get('feature') == feature.get('name')
                   for test in _tests(rule)
                   for found in [self._change(feature.get('name'), test)]
                   if found}
        self._ask_co_authors(sorted(changed))

    def _log(self, args):
        if args not in self._logs:
            self._logs[args] = _git_out(self.tree, *args)
        return self._logs[args]

    def _rule_args(self, spec, text):
        """The `git log` that finds who first wrote a rule's words, or None."""
        if not (text and spec):
            return None
        return ('log', '--reverse', _COMMIT_FORMAT, '-S', text, '--', spec)

    def _proof_args(self, spec, proof_id):
        """The `git log` over a proof's own line, or None where it has none."""
        pattern = re.compile(_PROOF_LINE % re.escape(str(proof_id)))
        for index, line in enumerate(self._lines(spec), 1):
            if pattern.match(line):
                return ('log', '-s', _COMMIT_FORMAT,
                        '-L%d,%d:%s' % (index, index, spec))
        return None

    def of(self, feature, spec, rule):
        """`{rule, proofs, tests}` for one payload rule entry."""
        return {'rule': self._rule(spec, rule.get('text') or ''),
                'proofs': [self._proof(spec, proof.get('id'))
                           for proof in rule.get('proofs') or ()],
                'tests': [self._test(feature, test)
                          for test in _tests(rule)]}

    def _lines(self, spec):
        if spec not in self._text:
            self._text[spec] = _read(self.tree, spec).splitlines()
        return self._text[spec]

    def _rule(self, spec, text):
        """Who first wrote the rule's words, whatever id they stood under."""
        found = None
        args = self._rule_args(spec, text)
        if args:
            listed = self._log(args)
            found = self._commit(listed.splitlines()[0]) if listed else None
        return {'written_by': found[1] if found else None,
                'commit': found[0] if found else None,
                'co_authors': self._named(found)}

    def _proof(self, spec, proof_id):
        """Who first wrote the proof's line and who last changed it."""
        history = []
        args = self._proof_args(spec, proof_id)
        if args:
            listed = self._log(args)
            history = [self._commit(line) for line in listed.splitlines()
                       if re.match(r'^[0-9a-f]{40,64} ', line)]
        written = history[-1] if history else None
        changed = history[0] if history else None
        return {'id': proof_id,
                'written_by': written[1] if written else None,
                'written_commit': written[0] if written else None,
                'written_co_authors': self._named(written),
                'changed_by': changed[1] if changed else None,
                'changed_commit': changed[0] if changed else None,
                'changed_co_authors': self._named(changed)}

    def _commit(self, line):
        """`(sha, email)` for one line of `_COMMIT_FORMAT`, its co-authors
        kept for `_named`."""
        head, _, trailers = line.partition('\x1f')
        found = _pair(head)
        self._co_authors[found[0]] = _values(trailers)
        return found

    def _named(self, found):
        """The co-authors of the commit `found` names, `[]` where it names
        none or there is no commit."""
        if not found:
            return []
        if found[0] not in self._co_authors:
            self._ask_co_authors([found[0]])
        return list(self._co_authors.get(found[0]) or ())

    def _ask_co_authors(self, shas):
        """Read the co-authors of every commit in `shas` git has not given
        yet, `_TRAILER_BATCH` commits to a process."""
        wanted = [sha for sha in shas if sha not in self._co_authors]
        for start in range(0, len(wanted), _TRAILER_BATCH):
            batch = wanted[start:start + _TRAILER_BATCH]
            listed = _git_out(self.tree, 'log', '--no-walk=unsorted',
                              '--format=%H%x1f' + _CO_AUTHORS, *batch)
            for line in listed.splitlines():
                sha, _, trailers = line.partition('\x1f')
                self._co_authors[sha.strip()] = _values(trailers)
            for sha in batch:
                self._co_authors.setdefault(sha, [])

    def _test(self, feature, test):
        """Who last changed one tied test, as `wording.test_last_change` reads it."""
        found = self._change(feature, test)
        return {'file': test['file'], 'name': test['name'],
                'changed_by': found[1] if found else None,
                'changed_commit': found[0] if found else None,
                'changed_co_authors': self._named(found)}

    def _change(self, feature, test):
        """`(sha, email)` of the commit that last changed one tied test, or
        None, each test read once."""
        key = (feature, test['file'], test['name'], test['proof'])
        if key not in self._changes:
            span = self._span(feature, test)
            if self._reader is None:
                self._reader = wording_module.reader(self.tree)
            self._changes[key] = (
                wording_module.test_last_change(
                    self.tree, test['file'], span[0], span[1],
                    reader=self._reader) if span else None)
        return self._changes[key]

    def _span(self, feature, test):
        """`(marker line, last line)` of a tied test, or None where it is not found."""
        if self._tests is None:
            self._tests = {}
            suites = markers_module.read_suites(self.tree)[0]
            for path, found in markers_module.scan(self.tree, suites).items():
                text = _read(self.tree, path)
                for declared in found.tests:
                    for marker in declared.markers:
                        end = declared.end
                        if end is not None and not path.endswith('.py'):
                            end = text.count('\n', 0, end) + 1
                        self._tests[(path, markers_module.test_name(
                            path, declared), marker.feature, marker.id)] = (
                                marker.line, end)
                if found.whole:
                    for marker in found.markers:
                        self._tests[(path, markers_module.test_name(
                            path, None), marker.feature, marker.id)] = (
                                marker.line, len(text.splitlines()))
        return self._tests.get((test['file'], test['name'], feature,
                                test['proof']))


def _pair(line):
    sha, _, email = line.partition(' ')
    return sha, email.strip() or None


def _values(trailers):
    """Each trailer value of a `\\x1f`-parted line, as git gives it."""
    return [value.strip() for value in trailers.split('\x1f')
            if value.strip()]


# ---------------------------------------------------------------------------
# The canonical form and the fingerprint
# ---------------------------------------------------------------------------

def _sorted(value):
    if isinstance(value, dict):
        return {key: _sorted(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted(item) for item in value]
    return value


def canonical_bytes(package):
    """The package's bytes: the top level in the format's order, every other
    object's keys sorted, two-space indent, UTF-8, `\\n`, a trailing newline.

    A key the format does not name at the top level has no place in the
    order, so it is refused rather than guessed at.
    """
    unknown = [key for key in package if key not in TOP_LEVEL]
    if unknown:
        raise PackageError('the package carries keys the format does not '
                           'name: %s' % ', '.join(sorted(unknown)))
    ordered = {key: _sorted(package[key]) for key in TOP_LEVEL
               if key in package}
    text = json.dumps(ordered, indent=2, ensure_ascii=False)
    return (text + '\n').encode('utf-8')


def fingerprint_of(package):
    """sha256 of the canonical bytes with `fingerprint` set to the empty string."""
    blank = dict(package)
    blank['fingerprint'] = ''
    return hashlib.sha256(canonical_bytes(blank)).hexdigest()


def check_bytes(data):
    """`None` when the bytes are a package that matches its fingerprint, else why not."""
    try:
        package = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return 'the file is not UTF-8 JSON'
    if not isinstance(package, dict) or package.get('schema') != SCHEMA:
        return 'the file does not carry the schema %s' % SCHEMA
    try:
        canonical = canonical_bytes(package)
    except PackageError as error:
        return str(error)
    if list(package) != [key for key in TOP_LEVEL if key in package] \
            or len(package) != len(TOP_LEVEL):
        return 'the top-level keys are not the ones the format names, in its order'
    stored = package.get('fingerprint')
    computed = fingerprint_of(package)
    if stored != computed:
        return ('the package records the fingerprint %s and its content '
                'gives %s' % (stored, computed))
    if canonical != data:
        return ('the fingerprint matches the content, but the bytes are not '
                'in the canonical form')
    return None


def check_file(path):
    """`None` when the file matches its fingerprint, else why not."""
    try:
        with open(path, 'rb') as handle:
            data = handle.read()
    except (IOError, OSError) as error:
        return 'the file could not be read: %s' % error
    return check_bytes(data)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write(project_root, package):
    """Write the package's canonical bytes. Its project-relative path."""
    rel = package_path(package['version'])
    full = os.path.join(project_root, *rel.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'wb') as handle:
        handle.write(canonical_bytes(package))
    return rel
