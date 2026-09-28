#!/usr/bin/env python3
"""Write the evidence package: one data file describing one version.

    package.py [--release NAME] [--commit] [--project-root DIR]
    package.py --check FILE

The package holds, for every rule, its words, its proofs, its tests, each
result on each operating system, what the audit found and who signed it, with
the three statuses and whether the rule meets the gate. It is written to

    .purlin/evidence/package/<version>.json

where `<version>` is the `VERSION` file's value, the config's `version` where
there is none, or what `--release <name>` names: the same name `purlin:sign`
gives the tag `signed/<version>`.

**It is evidence for review.** Purlin hands the package to a regulated
document and sign-off system, which holds the controlled document, the
authority to sign it off and the signature that counts under the regulation.
Purlin makes no claim that the software is compliant.

**It reads what git holds.** The package is built from a checkout of the
commit the evidence was taken at, so evidence or a signature that is written
and not committed is left out, named in the package's `warnings` and on the
terminal. That commit is `HEAD`, stepping back over any commit that changed
nothing but a package file, so the package a tag carries names the commit
below it.

**The same tag always gives the same bytes.** Keys are sorted within every
object except the top level, which keeps the order the format names; lists
keep a fixed order; nothing records when the export ran; the file is UTF-8
with `\\n` line ends and a trailing newline on every operating system. The
`fingerprint` field is the sha256 of the file's own bytes with that field set
to the empty string. `--check FILE` recomputes it.

**State.** `signed` when every rule meets the gate `signed` and the package
is written for the tag, or read at the commit the tag names; `gate <gate> met`
when every rule meets a gate but the version is not signed and tagged: the
gate is `passed` or `strong`, where no tag is ever written and a tag found on
the commit changes nothing, or `signed` with no tag on the commit yet;
`work in progress` otherwise. Every state but `signed` carries
`not_for_approval: true`.

Run by itself it writes the file and commits nothing; `--commit` commits it
as `purlin: evidence at <sha7>`. At the gate `signed`, `purlin:sign` writes
and commits it before it writes the tag; below `signed` it writes neither. `references/formats/package_format.md` holds every field.

Exit codes: 0 written, or the check matched; 1 the check did not match or the
package could not be written; 2 the command line was wrong.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'), os.path.join(_SCRIPTS, 'review')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import (PURLIN_VERSION,                            # noqa: E402
                    console as console_module,
                    evidence as evidence_module,
                    fingerprint as fingerprint_module,
                    gate as gate_module,
                    payload as payload_module,
                    signatures as signatures_module,
                    specs as specs_module)

SCHEMA = 'purlin-package/1'
PACKAGE_DIR = '.purlin/evidence/package'
TAG_PREFIX = 'signed/'

# The top-level keys in the order the file carries them. The state is what a
# reader sees first after the schema.
TOP_LEVEL = ('schema', 'state', 'not_for_approval', 'rules_meeting_gate',
             'rules_short_of_gate', 'purlin_version', 'project', 'version',
             'tag', 'commit', 'gate', 'trust', 'mutation_engine',
             'min_strength', 'features', 'warnings', 'fingerprint')

SIGNED = 'signed'
IN_PROGRESS = 'work in progress'
CELLS = ('passed', 'strong', 'signed')

WRITTEN = 'Evidence package written to %s. State: %s, %d of %d rules meet the gate %s.'
NOT_FOR_APPROVAL = 'Not for approval.'
NOT_COMMITTED = '%s is written and not committed; the package leaves it out.'
MATCHES = 'The package matches its fingerprint.'
COMMITTED = 'Package committed.'
UNCHANGED = 'Package unchanged.'
EVIDENCE_SUBJECT = 'purlin: evidence at %s'

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BAD_INVOCATION = 2


class PackageError(Exception):
    """The package could not be built or written; the message says why."""


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git(project_root, *args):
    return subprocess.run(['git'] + list(args), capture_output=True,
                          text=True, cwd=project_root, timeout=120)


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
    therefore names the commit beneath it, and exporting at the tag again
    reads the same commit. None where there is no commit.
    """
    found = _git(project_root, 'rev-parse', '--verify', '--quiet',
                 '%s^{commit}' % start)
    if found.returncode != 0 or not found.stdout.strip():
        return None
    sha = found.stdout.strip()
    while True:
        paths = _changed_paths(project_root, sha)
        if not paths or not all(path.startswith(PACKAGE_DIR + '/')
                                for path in paths):
            return sha
        parent = _git(project_root, 'rev-parse', '--verify', '--quiet',
                      '%s^' % sha)
        if parent.returncode != 0 or not parent.stdout.strip():
            return sha
        sha = parent.stdout.strip()


def uncommitted_evidence(project_root):
    """The evidence and signature files, sorted, that are not committed as they stand."""
    listed = _git(project_root, 'status', '--porcelain', '--untracked-files=all',
                  '--', evidence_module.EVIDENCE_DIR, 'specs')
    if listed.returncode != 0:
        return []
    found = set()
    for line in listed.stdout.splitlines():
        if len(line) <= 3:
            continue
        path = line[3:].strip('"').split(' -> ')[-1]
        if not path.endswith('.json'):
            continue
        evidence = any(path.startswith('%s/%s/' % (evidence_module.EVIDENCE_DIR,
                                                   source))
                       for source in evidence_module.SOURCES)
        signature = '.signatures/' in path
        if evidence or signature:
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
# The version and the tag
# ---------------------------------------------------------------------------

def version_name(project_root, release=None):
    """The version the package and the tag are named for."""
    import sign as sign_module
    return sign_module.tag_name(project_root, release)[len(TAG_PREFIX):]


def package_path(version):
    """`.purlin/evidence/package/<version>.json`, `/` separated."""
    return '%s/%s.json' % (PACKAGE_DIR, version)


def _tag_names_commit(project_root, tag, commit):
    """True when the tag exists and its evidence commit is `commit`."""
    found = _git(project_root, 'rev-parse', '--verify', '--quiet',
                 'refs/tags/%s' % tag)
    if found.returncode != 0:
        return False
    return evidence_commit(project_root, 'refs/tags/%s' % tag) == commit


# ---------------------------------------------------------------------------
# Building the package
# ---------------------------------------------------------------------------

def build(project_root, release=None, for_tag=False):
    """The package as a dict, its top-level keys in the format's order.

    `for_tag` says the package is being written for the tag `purlin:sign` is
    about to write, which is what lets the state read `signed`.
    """
    commit = evidence_commit(project_root)
    if commit is None:
        raise PackageError('the project has no commit yet')
    version = version_name(project_root, release)
    tag = TAG_PREFIX + version
    warnings = [NOT_COMMITTED % path
                for path in uncommitted_evidence(project_root)]

    checkout = _Checkout(project_root, commit)
    try:
        tree = checkout.root
        payload = payload_module.build_payload(tree, generated_by='export')
        features = specs_module.scan_specs(tree)
        entries = _features(tree, payload, features)
    finally:
        checkout.close()

    for warning in payload.get('warnings') or ():
        if warning not in warnings:
            warnings.append(warning)

    rules = [rule for feature in entries for rule in feature['rules']]
    meeting = sum(1 for rule in rules if rule['meets_gate'])
    short = len(rules) - meeting
    settings = payload.get('gate') or {}
    gate = settings.get('gate') or gate_module.DEFAULT_GATE
    if short:
        state = IN_PROGRESS
    elif gate == SIGNED and (for_tag or _tag_names_commit(project_root, tag,
                                                          commit)):
        state = SIGNED
    else:
        state = 'gate %s met' % gate

    values = {
        'schema': SCHEMA,
        'state': state,
        'not_for_approval': state != SIGNED,
        'rules_meeting_gate': meeting,
        'rules_short_of_gate': short,
        'purlin_version': PURLIN_VERSION,
        'project': payload.get('project'),
        'version': version,
        'tag': tag,
        'commit': commit,
        'gate': gate,
        'trust': settings.get('trust'),
        'mutation_engine': settings.get('mutation_engine'),
        'min_strength': settings.get('min_strength'),
        'features': entries,
        'warnings': warnings,
        'fingerprint': '',
    }
    package = {key: values[key] for key in TOP_LEVEL}
    package['fingerprint'] = fingerprint_of(package)
    return package


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _features(tree, payload, features):
    """`features[]`, by name, each carrying its own rules by number."""
    all_signatures = signatures_module.load_signatures(tree, features)
    markers = fingerprint_module.marker_index(tree)
    out = []
    for feature in sorted(payload.get('features') or (),
                          key=lambda entry: entry.get('name') or ''):
        name = feature.get('name')
        loaded = evidence_module.load(tree, name)
        sections = []
        if any(loaded['files'].values()):
            now = fingerprint_module.fingerprint(tree, name, features, markers)
            sections = evidence_module.checked_sections(loaded, now)
        own = [rule for rule in feature.get('rules') or ()
               if rule.get('feature') == name]
        own.sort(key=lambda rule: _rule_number(rule.get('id')))
        out.append({
            'name': name,
            'spec': feature.get('spec_path'),
            'scope': list(feature.get('scope') or ()),
            'requires': list(feature.get('requires') or ()),
            'anchor': bool(feature.get('is_anchor')),
            'rules': [_rule(tree, rule, loaded, sections,
                            all_signatures.get((name, rule.get('id')), []))
                      for rule in own],
        })
    return out


def _rule(tree, rule, loaded, sections, signatures):
    rule_id = rule.get('id')
    proofs = rule.get('proofs') or ()
    return {
        'id': rule_id,
        'text': rule.get('text') or '',
        'level': rule.get('level'),
        'level_marked': bool(rule.get('level_marked')),
        'proofs': [{'id': proof.get('id'), 'text': proof.get('text') or '',
                    'manual': bool(proof.get('manual')),
                    'env': proof.get('env')} for proof in proofs],
        'tests': [{'proof': proof.get('id'), 'file': test.get('file'),
                   'name': test.get('name')}
                  for proof in proofs for test in proof.get('tests') or ()]
                 + [{'proof': rule_id, 'file': test.get('file'),
                     'name': test.get('name')}
                    for test in rule.get('tests') or ()],
        'results': _results(rule_id, proofs, sections),
        'audit': _audit(rule, loaded),
        'signatures': _signatures(tree, rule, signatures),
        'statuses': {name: _status(rule, name) for name in CELLS},
        'meets_gate': bool(rule.get('meets_gate')),
    }


def _results(rule_id, proofs, sections):
    """One entry per section: what that run saw for this rule, by operating system."""
    proof_ids = {proof.get('id') for proof in proofs}
    out = []
    for entry in sections:
        section = entry['section']
        word = (section.get('rules') or {}).get(rule_id)
        if not word:
            seen = [result for proof_id, result in
                    evidence_module.proof_results(section).items()
                    if proof_id in proof_ids]
            word = ('failed' if 'fail' in seen
                    else 'passed' if seen else 'no test')
        out.append({'os': entry['os'], 'source': entry['source'],
                    'result': word, 'at': section.get('at'),
                    'commit': section.get('commit'),
                    'runner': section.get('runner'),
                    'current': bool(entry['current']),
                    'out_of_date': sorted(entry['out_of_date'])})
    out.sort(key=lambda item: (item['os'], item['source']))
    return out


def _audit(rule, loaded):
    """What the audit found for the rule's current hashes, or None."""
    summary = rule.get('audit')
    if not summary:
        return None
    entry = evidence_module.audit_entry(
        loaded, rule.get('id'), rule.get('rule_hash'), rule.get('proof_hash'),
        rule.get('test_hash')) or {}
    return {'verdict': summary.get('verdict'),
            'findings': list(summary.get('findings') or ()),
            'strength': summary.get('strength'),
            'model': summary.get('model'),
            'criteria': entry.get('criteria'),
            'at': summary.get('at'),
            'commit': summary.get('commit'),
            'source': entry.get('source')}


def _signatures(tree, rule, signatures):
    """Every signature that still binds the rule's current hashes."""
    out = []
    for signature in signatures:
        if not signatures_module.is_current(
                signature, rule.get('rule_hash'), rule.get('proof_hash'),
                rule.get('test_hash'), rule.get('audit_hash')):
            continue
        path = signature.get('path')
        out.append({
            'signer': signature.get('signer'),
            'at': signature.get('timestamp'),
            'committed_at': signatures_module.commit_date(tree, path),
            'machine': signature.get('machine'),
            'os': signature.get('os'),
            'note': signature.get('note'),
            'level': signature.get('level'),
            'gate': signature.get('gate'),
            'path': path,
            'commit_verifies': signatures_module.commit_is_signed(tree, path),
            'locked': {key: signature.get(key) for key in (
                'triple', 'rule_hash', 'proof_hash', 'test_hash',
                'test_hash_kind', 'audit_hash')},
        })
    out.sort(key=lambda item: (str(item['at']), str(item['signer']),
                               str(item['path'])))
    return out


def _status(rule, name):
    """One status: its word and its reasons, or None above the gate."""
    cell = (rule.get('cells') or {}).get(name)
    if not cell:
        return None
    return {'word': cell.get('word'),
            'reasons': [str(reason) for reason in cell.get('reasons') or ()]}


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
# Writing and committing
# ---------------------------------------------------------------------------

def write(project_root, package):
    """Write the package's canonical bytes. Its project-relative path."""
    rel = package_path(package['version'])
    full = os.path.join(project_root, *rel.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'wb') as handle:
        handle.write(canonical_bytes(package))
    return rel


def commit(project_root, rel, package, signed=False):
    """Commit the one package file. True when a commit was made.

    False when the file was already committed as it stands. Raises
    `PackageError` when git refused.
    """
    added = _git(project_root, 'add', '--', rel)
    if added.returncode != 0:
        raise PackageError('git add failed: %s' % added.stderr.strip())
    staged = _git(project_root, 'diff', '--cached', '--quiet', '--', rel)
    if staged.returncode == 0:
        return False
    command = ['commit', '-q', '-m', EVIDENCE_SUBJECT % package['commit'][:7]]
    if signed:
        command.insert(1, '-S')
    made = _git(project_root, *(command + ['--', rel]))
    if made.returncode != 0:
        raise PackageError('git commit failed: %s'
                           % (made.stderr.strip() or made.stdout.strip()))
    return True


def summary_lines(rel, package):
    """What the command prints: the path and the state, then the warnings."""
    total = package['rules_meeting_gate'] + package['rules_short_of_gate']
    lines = [WRITTEN % (rel, package['state'], package['rules_meeting_gate'],
                        total, package['gate'])]
    if package['not_for_approval']:
        lines[0] += ' ' + NOT_FOR_APPROVAL
    lines.extend(package['warnings'])
    return lines


def write_for_tag(project_root, release=None):
    """Build, write and commit the package the tag carries. `(path, None)` or `(None, why)`.

    Every rule must meet the gate in the committed evidence, so a package
    that would read `work in progress` stops the tag. The commit is signed,
    with the key the signer signs every other commit with.
    """
    try:
        package = build(project_root, release, for_tag=True)
    except PackageError as error:
        return None, str(error)
    if package['rules_short_of_gate']:
        return None, ('the committed evidence reads %d of %d rules short of '
                      'the gate' % (package['rules_short_of_gate'],
                                    package['rules_short_of_gate']
                                    + package['rules_meeting_gate']))
    try:
        rel = write(project_root, package)
        commit(project_root, rel, package, signed=True)
    except (PackageError, IOError, OSError) as error:
        return None, str(error)
    return rel, None


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

USAGE = ('Usage: package.py [--release NAME] [--commit] [--project-root DIR]\n'
         '       package.py --check FILE')


def _parse(argv):
    args = {'release': None, 'commit': False, 'root': '.', 'check': None,
            'error': None, 'help': False}
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ('-h', '--help'):
            args['help'] = True
        elif item == '--commit':
            args['commit'] = True
        elif item in ('--release', '--project-root', '--check'):
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args['error'] = '%s needs a value.' % item
                return args
            key = {'--release': 'release', '--project-root': 'root',
                   '--check': 'check'}[item]
            args[key] = rest.pop(0)
        else:
            args['error'] = 'unexpected argument %s' % item
            return args
    if args['check'] and (args['commit'] or args['release']):
        args['error'] = '--check reads a file and takes nothing else.'
    return args


def main(argv=None):
    console_module.force_utf8_stdio()
    args = _parse(sys.argv[1:] if argv is None else argv)
    if args['help']:
        print(__doc__.strip())
        return EXIT_OK
    if args['error']:
        print(USAGE, file=sys.stderr)
        print('package.py: %s' % args['error'], file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if args['check']:
        why = check_file(args['check'])
        if why:
            print('The package does not match its fingerprint: %s.' % why)
            return EXIT_FAILED
        print(MATCHES)
        return EXIT_OK

    root = args['root']
    if not os.path.isdir(root):
        print('package.py: not a directory: %r' % root, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    try:
        package = build(root, args['release'])
        rel = write(root, package)
    except (PackageError, IOError, OSError) as error:
        print('export: the package was not written: %s.' % error)
        return EXIT_FAILED
    for line in summary_lines(rel, package):
        print(line)
    if args['commit']:
        try:
            made = commit(root, rel, package)
        except PackageError as error:
            print('export: the package was not committed: %s.' % error)
            return EXIT_FAILED
        print(COMMITTED if made else UNCHANGED)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
