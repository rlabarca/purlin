#!/usr/bin/env python3
"""Write the signatures a person attests, and commit them signed.

    sign.py [--release NAME] [--project-root DIR]
    sign.py <feature> [RULE-N ...] [--batch] [--project-root DIR]
    sign.py <feature> RULE-N [RULE-N ...] --note "<what you saw>"

A signature is one named person's attestation that a rule, its proof and its
test belong together. It is one file, so two signatures never conflict:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json

`hash8` is the first eight characters of the triple the signature binds, and
the slug is the signer's email local part, lowercased, with every character
that is not a letter or a digit replaced by `-`. Every file here is a person's:
CI writes no signature, ever.

With no argument this walks the queue one rule at a time: the payload's one
list of the rules that wait on a person, each saying what it needs. A `hand
check` is a rule whose strong cell reads `manual test`; a
`signature` is a rule whose level is `signed`, whose tests and audit are met
and that has no counting signature. At each stop the answer is one of three:
sign the rule, add a case (a proof line to write into the spec), or skip it.
Signing a hand check asks for one line saying what the person saw, which the
signature carries as its note. The walk writes nothing until it closes, and
then it makes one signed commit for the signatures.

A bare feature signs every rule of that feature in the queue, and `--batch`
every rule in the queue, in one signed commit and with no stop.

**The tag is the marker of proven code.** When the walk closes and every rule
meets the gate, it writes the signed tag `signed/<version>` with `git tag -s`
and the key the signer signs commits with, where the version is the
`VERSION` file at the project root or the one in `.purlin/config.json`;
`--release <name>` names another. The tag's message names the commit and the
gate. No tag is written while any rule falls short, and none is written over
a tag that is already there. Nothing is pushed: the last line names the push
for a person to run.

**The tag carries the evidence package.** Before it writes the tag it writes
`.purlin/evidence/package/<version>.json` from the committed evidence, with
the state `signed`, commits it as a signed commit, and tags that commit. If
the package cannot be written or committed, no tag is written and the line
says why.

**Evidence is committed before anything is signed over it.** A rule whose
feature has evidence that is written and not committed is refused, and so is
the tag while any feature has such evidence, with one line per feature:
`sign: <feature> has evidence that is not committed. Run: purlin:test
--commit`.

**A spec that names no files is not signed at `signed`.** Under the gate
`signed` a rule of a feature spec with no `> Scope:` line, or one that
reaches no file, is refused with `sign: <feature> names no files in > Scope:,
so a signature cannot be tied to the code it governs. Run: purlin:spec
<feature>`, and the tag is not written while any such spec exists. Below
`signed` nothing is refused for it. Anchors are exempt.

**The tag waits on current evidence.** A rule meets the gate only while its
passed cell reads over evidence current for its spec, code and tests, so a
feature whose evidence is older than any of them holds the tag back, and the
refusal names it: `No tag: login is out of date (code changed since
a1b2c3d).`

**Trust.** With `trust: remote` in `.purlin/config.json` a rule with a proof
that has a test, whose feature has no current section in its `ci` evidence,
is refused, and the line says to run `purlin:test --remote` first. A rule
whose proofs are all `@manual` has no test for a runner to run, so it is not
refused. With `trust: local`, the default, your own run is the evidence.

`--note` carries the one line a signer writes where no test can be read: a
rule reading `manual test`. A reviewer
who finds the test does not prove the proof adds the missing case as a proof
line instead, which is the walk's `case`.

**A rule marked below `signed` asks for no signature.** Under the gate
`signed`, a rule whose `[level: ...]` tag names `passed` or `strong` has that
level, and naming it is refused with one line saying so; nothing is written
for it.

**Who signs is logged, not policed.** The signature names the signer, the
machine it was made on and that machine's operating system, and git names
the commit's author; no list says who may sign, and nothing
compares the signer with whoever last committed to the test file.

`references/formats/signature_format.md` holds the file shape field by field.
The three hashes come from the payload, which is the one place they are
computed, so a signature this script writes is current the moment it lands.

Exit codes: 0 the signatures were written and committed, 1 nothing could be
signed or the commit is not signed, 2 the command line was wrong or the gate
asks for no signature.
"""

import json
import os
import platform
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import report_data                                 # noqa: E402
from purlin import (board as board_module,                     # noqa: E402
                    console as console_module,
                    evidence as evidence_module,
                    gate as gate_module,
                    payload as payload_module,
                    signatures as signatures_module,
                    specs as specs_module,
                    states)

SCHEMA = 'purlin-signature/1'
USAGE = ('Usage: sign.py [<feature> [RULE-N ...]] [--batch] [--note TEXT] '
         '[--release NAME] [--project-root DIR]')

# The tag `purlin:sign` writes when every rule meets the gate, and the one
# ref besides a run branch that starts a CI run.
TAG_PREFIX = 'signed/'
NO_TAG_SHORT = 'No tag: %d of %d rules do not meet the gate %s.'
NO_TAG_EXISTS = ('No tag: %s is already written. Name another with '
                 '--release <name>.')
TAGGED = 'Tagged %s at %s: every rule meets the gate %s.'
PUSH_THE_TAG = 'Run: git push origin %s'
NO_CI_RUN = ('sign: %s %s has no ci test run for this code; run '
             'purlin:test --remote first')
MARKED_BELOW = 'sign: %s %s is marked [level: %s]; it asks for no signature.'
NOT_COMMITTED = ('sign: %s has evidence that is not committed. Run: '
                 'purlin:test --commit')
NAMES_NO_FILES = ('sign: %s names no files in > Scope:, so a signature cannot '
                  'be tied to the code it governs. Run: purlin:spec %s')
NO_TAG_NO_FILES = ('No tag: %s names no files in > Scope:, so a signature '
                   'cannot be tied to the code it governs.')
NO_TAG_OUT_OF_DATE = 'No tag: %s is out of date (%s).'
NO_TAG_PACKAGE = 'No tag: the evidence package was not committed: %s.'
PACKAGE_COMMITTED = 'Evidence package committed: %s.'

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

# The one-time setup a signer runs, in the order they run it.
SIGNING_SETUP = (
    'git config gpg.format ssh',
    'git config user.signingkey ~/.ssh/id_ed25519.pub',
    'git config commit.gpgsign true',
)

# The three answers the walk takes, and the letters that reach each one.
ANSWERS = ('sign', 'case', 'skip')

ARROW = '→'


# ---------------------------------------------------------------------------
# The payload, and one rule in it
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='sign')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>`, or None.

    A feature entry lists the rules it must prove, which includes the ones it
    requires from an anchor. The rule that belongs to `feature` is the one
    whose own `feature` field names it, so signing a required rule signs it
    where it lives and not once per consumer.
    """
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def rule_proof_test_hashes(project_root, feature, rule, payload=None):
    """`(rule_hash, proof_hash, test_hash, test_hash_kind)`.

    R is the rule text with its tags stripped and its whitespace normalised,
    P the proof descriptions in order and T the test files backing them. A
    rule that is not in the payload has no hashes and every element is None.
    """
    entry = rule_entry(load_payload(project_root, payload), feature, rule)
    if entry is None:
        return (None, None, None, None)
    return (entry.get('rule_hash'), entry.get('proof_hash'),
            entry.get('test_hash'), entry.get('test_hash_kind'))


def triple_for(entry):
    """The triple hash of one rule entry."""
    return signatures_module.triple_hash(
        entry.get('rule_hash'), entry.get('proof_hash'), entry.get('test_hash'))


# ---------------------------------------------------------------------------
# Writing one signature
# ---------------------------------------------------------------------------

def signature_path(project_root, feature, rule, triple, signer_slug):
    """Where the signature for one rule goes, beside the spec that holds it."""
    info = specs_module.scan_specs(project_root).get(feature)
    directory = signatures_module.signatures_dir(project_root, info or {})
    if not directory:
        return None
    return os.path.join(directory,
                        '%s.%s.%s.json' % (rule, str(triple)[:8], signer_slug))


def write_signature(project_root, feature, rule, signer_email, evidence_path,
                    gate, level, payload=None, entry=None, note=None):
    """Write one signature file and return its project-relative path."""
    entry = entry or rule_entry(load_payload(project_root, payload), feature,
                                rule)
    if entry is None:
        return None
    slug = signatures_module.signer_slug(signer_email)
    triple = triple_for(entry)
    path = signature_path(project_root, feature, rule, triple, slug)
    if not path:
        return None

    body = {
        'schema': SCHEMA,
        'feature': feature,
        'rule': rule,
        'triple': triple[:16],
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'test_hash_kind': entry.get('test_hash_kind'),
        'audit_hash': entry.get('audit_hash'),
        'level': level if level is not None else entry.get('level'),
        'signer': str(signer_email),
        'machine': machine_name(),
        'os': evidence_module.host_os(),
        'note': str(note).strip() if str(note or '').strip() else None,
        'timestamp': payload_module.now_iso(),
        'gate': gate,
        'evidence': evidence_path,
    }
    _write_json(path, body)
    return os.path.relpath(path, project_root).replace(os.sep, '/')


def machine_name():
    """The host's name as the operating system reports it, or `unknown`."""
    return platform.node() or 'unknown'


def evidence_for(payload, feature):
    """The evidence file a signer read for a feature, or None when it has none.

    The file a person's own run wrote comes first, then a runner's: a
    signature names the file a reader can open, not a path nothing wrote.
    """
    for entry in (payload or {}).get('features') or ():
        if entry.get('name') != feature:
            continue
        for source in ('local', 'ci'):
            found = (entry.get('evidence') or {}).get(source)
            if found:
                return found.get('path')
    return None


def _write_json(path, body):
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(body, handle, indent=2, sort_keys=True)
        handle.write('\n')


# ---------------------------------------------------------------------------
# What a person may sign now
# ---------------------------------------------------------------------------

def queued(payload, feature=None, rules=None):
    """Every `(feature, rule)` a bare feature or `--batch` signs, in order.

    The payload works out the queue, so this reads what it wrote rather than
    asking the question again: the hand checks, rules reading `manual test`,
    and the signatures, rules whose level is `signed`, whose
    tests and audit are met and that have no counting signature. Everything
    else is build work and stays on the board.
    """
    found = []
    for row in (payload or {}).get('queue') or ():
        name, rule = row.get('owner'), row.get('rule')
        if feature and name != feature:
            continue
        if rules and rule not in rules:
            continue
        if name and rule and (name, rule) not in found:
            found.append((name, rule))
    return found


def in_queue(payload, targets):
    """The targets the queue carries, which a signature clears at `strong`."""
    rows = {(row.get('owner'), row.get('rule'))
            for row in (payload or {}).get('queue') or ()}
    return [pair for pair in targets or () if pair in rows]


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


# ---------------------------------------------------------------------------
# Trust: whether this machine's own test run is evidence enough to sign on
# ---------------------------------------------------------------------------

def has_a_ci_run(payload, entry):
    """True when the rule's `ci` evidence holds a section current for this code.

    The rule's own feature's `ci` file is read, and one current section of
    it is a run the runner made over this spec, this code and these tests. A
    project that trusts this machine never asks; one that does not asks here,
    and a rule with no such run is refused until `purlin:test --remote` has
    been run. A rule whose proofs are all `@manual` has no test for a runner
    to run, so the question is not asked of it.
    """
    if not any(not proof.get('manual')
               for proof in (entry or {}).get('proofs') or ()):
        return True
    for feature in (payload or {}).get('features') or ():
        if feature.get('name') != (entry or {}).get('feature'):
            continue
        ci = (feature.get('evidence') or {}).get('ci') or {}
        return any((platform or {}).get('current')
                   for platform in (ci.get('platforms') or {}).values())
    return False


def untrusted(payload, targets):
    """`[(feature, rule)]` this project's trust setting refuses to sign.

    Empty under `trust: local`, which is the default and is a project saying
    its own runs count. Under `trust: remote` it is every named rule with a
    proof that has a test, whose `ci` evidence holds no section current for
    this code.
    """
    if (payload.get('gate') or {}).get('trust') != 'remote':
        return []
    refused = []
    for feature, rule in targets or ():
        if not has_a_ci_run(payload, rule_entry(payload, feature, rule)):
            refused.append((feature, rule))
    return refused


def _allowed(payload, targets, out=None):
    """The targets trust allows, printing one line for each it refuses."""
    refused = untrusted(payload, targets)
    for feature, rule in refused:
        print(NO_CI_RUN % (feature, rule), file=out or sys.stdout)
    return [pair for pair in targets if pair not in refused]


# ---------------------------------------------------------------------------
# Evidence that is not committed
# ---------------------------------------------------------------------------

def uncommitted(payload, features=None):
    """The features, sorted, whose evidence is written and not committed.

    `features` narrows the question to the ones a signature reads; None asks
    it of every feature, which is what the tag reads. A feature with no
    evidence file has nothing to commit and is not named.
    """
    found = []
    for entry in (payload or {}).get('features') or ():
        name = entry.get('name')
        if features is not None and name not in features:
            continue
        for source in (entry.get('evidence') or {}).values():
            if source and not source.get('committed', True):
                found.append(name)
                break
    return sorted(set(found))


def _committed_only(payload, targets, out=None):
    """The targets whose feature's evidence is committed, printing the rest.

    One line per feature, so a batch of ten rules over one uncommitted file
    says it once.
    """
    refused = uncommitted(payload, {feature for feature, _rule in targets})
    for feature in refused:
        print(NOT_COMMITTED % feature, file=out or sys.stdout)
    return [pair for pair in targets if pair[0] not in refused]


def names_no_files(payload, features=None):
    """The feature specs, sorted, that name no files, at the gate `signed`.

    Below `signed` nothing is refused for it and the answer is empty.
    `features` narrows the question to the ones a signature reads; None asks
    it of every feature, which is what the tag reads. An anchor is never
    one: the code behind its rules belongs to the features that use it.
    """
    if (payload.get('gate') or {}).get('gate') != gate_module.GATES[-1]:
        return []
    return sorted(entry.get('name')
                  for entry in (payload or {}).get('features') or ()
                  if entry.get('incomplete')
                  and (features is None or entry.get('name') in features))


def _tied_only(payload, targets, out=None):
    """The targets whose spec names its files, printing one line per other."""
    refused = names_no_files(payload, {feature for feature, _rule in targets})
    for feature in refused:
        print(NAMES_NO_FILES % (feature, feature), file=out or sys.stdout)
    return [pair for pair in targets if pair[0] not in refused]


def out_of_date(payload):
    """`[(feature, reasons)]` whose evidence is older than its spec, code or tests.

    Read off each feature's own rules: a passed cell reading `out of date`
    names what changed since its newest run. Sorted by feature, the reasons
    in the order the cells give them, each once.
    """
    found = {}
    for feature in (payload or {}).get('features') or ():
        for entry in feature.get('rules') or ():
            if entry.get('feature') != feature.get('name'):
                continue
            cell = (entry.get('cells') or {}).get('passed') or {}
            if cell.get('word') != states.OUT_OF_DATE:
                continue
            reasons = found.setdefault(feature['name'], [])
            for reason in cell.get('reasons') or ():
                if reason not in reasons:
                    reasons.append(reason)
    return sorted(found.items())


def marked_below(payload, targets):
    """`[(feature, rule, level)]` whose `[level: ...]` tag asks for no signature.

    Only the gate `signed` asks for a signature, so this is empty below it.
    There a rule's level is `signed` unless its tag names `passed` or
    `strong`, and such a rule meets the gate without a signature.
    """
    if (payload.get('gate') or {}).get('gate') != gate_module.GATES[-1]:
        return []
    found = []
    for feature, rule in targets or ():
        entry = rule_entry(payload, feature, rule) or {}
        marked = entry.get('level_marked')
        if marked in gate_module.GATES[:-1]:
            found.append((feature, rule, marked))
    return found


# ---------------------------------------------------------------------------
# The tag
# ---------------------------------------------------------------------------

def project_version(project_root):
    """The version a tag is named for: the `VERSION` file, else the config."""
    path = os.path.join(project_root, 'VERSION')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            named = handle.read().strip()
    except (IOError, OSError, UnicodeDecodeError):
        named = ''
    if named:
        return named
    try:
        with open(os.path.join(project_root, '.purlin', 'config.json'), 'r',
                  encoding='utf-8') as handle:
            return str(json.load(handle).get('version') or '').strip()
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return ''


def tag_name(project_root, release=None):
    """`signed/<version>`, or `signed/<name>` where `--release` named one."""
    named = str(release or '').strip() or project_version(project_root)
    return TAG_PREFIX + (named or 'unversioned')


def tag_exists(project_root, name):
    """True when the repository already carries this tag."""
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', '--quiet', 'refs/tags/%s' % name],
        capture_output=True, text=True, cwd=project_root, timeout=10)
    return result.returncode == 0


def tag_message(commit, gate):
    """What the tag says: the commit it stands for, and the gate it met."""
    return ('Every rule meets the gate %s.\n\nCommit: %s\nGate: %s\n'
            % (gate, commit or 'unknown', gate))


def short_of_the_gate(payload):
    """`(rules that do not meet the gate, rules in the project)`.

    Each rule is counted once, under the feature that owns it, which is how
    the gate check counts them, so the two can never disagree about whether
    a tag is owed.
    """
    short = total = 0
    for feature in payload.get('features') or ():
        for entry in feature.get('rules') or ():
            if entry.get('feature') != feature.get('name'):
                continue
            total += 1
            if not entry.get('meets_gate'):
                short += 1
    return short, total


def _package_module():
    """`scripts/export/package.py`, imported when the tag is about to be written."""
    folder = os.path.join(os.path.dirname(_HERE), 'export')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import package
    return package


def tag_if_met(project_root, out=None, release=None, payload=None):
    """Write `signed/<version>` when every rule meets the gate. The tag name.

    This is the marker of proven code: the rule, the proof, the test and the
    audit are locked into a signature for every rule that asks for one, and
    the tag says so about one commit. It is a signed tag, made with the key
    the signer signs commits with, so git can show who wrote it as surely as
    it shows who signed. It is written after the walk's own commits, so the payload is
    read again rather than reused. The evidence package is committed first
    and the tag names that commit. Nothing is pushed.
    """
    out = sys.stdout if out is None else out
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    short, total = short_of_the_gate(payload)
    stale = out_of_date(payload)
    untied = names_no_files(payload)
    if short or untied:
        # Every feature the tag waits on is named with its reason, then the
        # count, so the refusal says what to run and not only how far off.
        for feature, reasons in stale:
            print(NO_TAG_OUT_OF_DATE % (feature, ', '.join(reasons)),
                  file=out)
        for feature in untied:
            print(NO_TAG_NO_FILES % feature, file=out)
        if short:
            print(NO_TAG_SHORT % (short, total, gate), file=out)
        return None
    refused = uncommitted(payload)
    if refused:
        for feature in refused:
            print(NOT_COMMITTED % feature, file=out)
        return None
    name = tag_name(project_root, release)
    if tag_exists(project_root, name):
        print(NO_TAG_EXISTS % name, file=out)
        return None
    # The package goes into the commit the tag names, so the tagged code
    # carries the evidence that describes it. The evidence commit is the one
    # below it, which is the commit the tag's message names.
    commit = payload.get('commit') or ''
    rel, why = _package_module().write_for_tag(project_root, release)
    if rel is None:
        print(NO_TAG_PACKAGE % why, file=out)
        return None
    print(PACKAGE_COMMITTED % rel, file=out)
    written = subprocess.run(
        ['git', 'tag', '-s', name, '-m', tag_message(commit, gate)],
        capture_output=True, text=True, cwd=project_root, timeout=30)
    if written.returncode != 0:
        print(NO_TAG_EXISTS % name, file=out)
        return None
    tagged = payload_module.head_sha(project_root) or commit
    print(TAGGED % (name, tagged[:7] or 'HEAD', gate), file=out)
    print('%s %s' % (ARROW, PUSH_THE_TAG % name), file=out)
    return name


# ---------------------------------------------------------------------------
# A person's signed commit
# ---------------------------------------------------------------------------

def signing_configured(project_root):
    """True when this checkout is set up to sign a commit."""
    return bool(_config(project_root, 'user.signingkey'))


def _config(project_root, name):
    try:
        result = subprocess.run(['git', 'config', '--get', name],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def signing_help():
    """The lines to print when a person has no signing set up yet."""
    lines = ['Commit signing is not configured, so a signature you write '
             'would not count. Run:']
    lines.extend('  %s' % command for command in SIGNING_SETUP)
    lines.append('Then upload the public key to the git host, under signing '
                 'keys, so it reads the commit as signed.')
    return lines


def commit_message(targets):
    """The subject for one signature commit, from `commit_conventions.md`."""
    return _subject('sign', targets)


def _subject(prefix, targets):
    features = []
    for feature, _rule in targets:
        if feature not in features:
            features.append(feature)
    if len(features) == 1:
        rules = [rule for _feature, rule in targets]
        return '%s(%s): %s' % (prefix, features[0], ' '.join(rules))
    parts = []
    for feature in features:
        rules = [rule for name, rule in targets if name == feature]
        parts.append('%s %s' % (feature, ' '.join(rules)))
    return '%s(batch): %s' % (prefix, ', '.join(parts))


def sign_and_commit(project_root, targets, signer_email, note=None,
                    payload=None, notes=None):
    """Write every signature in `targets` and commit them once, signed.

    `targets` is `[(feature, rule), ...]`. One invocation is one commit
    whether it carries one rule or forty. `note` is the one line every
    signature carries, and `notes` maps a `(feature, rule)` to a line of its
    own, which is how the walk records what a person saw at each hand check.
    Returns the commit sha, or None when nothing was written.
    """
    notes = notes or {}
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    paths = []
    written = []
    for feature, rule in targets:
        entry = rule_entry(payload, feature, rule)
        if entry is None:
            continue
        path = write_signature(
            project_root, feature, rule, signer_email,
            evidence_for(payload, feature), gate, entry.get('level'),
            entry=entry, note=notes.get((feature, rule), note))
        if path:
            paths.append(path)
            written.append((feature, rule))
    if not paths:
        return None
    return _commit(project_root, paths, commit_message(written))


def _commit(project_root, paths, message):
    add = subprocess.run(['git', 'add', '--'] + list(paths),
                         capture_output=True, text=True, cwd=project_root,
                         timeout=30)
    if add.returncode != 0:
        return None
    commit = subprocess.run(['git', 'commit', '-S', '-m', message],
                            capture_output=True, text=True, cwd=project_root,
                            timeout=60)
    if commit.returncode != 0:
        return None
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                          text=True, cwd=project_root, timeout=10)
    return head.stdout.strip() if head.returncode == 0 else None


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

def _count(number, word):
    """`1 rule` or `4 rules`: one place, so no line prints `1 rules`."""
    return '%d %s%s' % (number, word, '' if number == 1 else 's')


def opening_line(payload):
    """What the walk prints before the first rule: how long the queue is."""
    return board_module.queue_line((payload or {}).get('summary') or {})


def _proof_tags(proof):
    """` (@manual)`, ` (@env(windows))`, both, or '' for a proof with neither."""
    tags = []
    if proof.get('manual'):
        tags.append('@manual')
    if proof.get('env'):
        tags.append('@env(%s)' % proof['env'])
    return ' (%s)' % ' '.join(tags) if tags else ''


def audit_lines(entry):
    """What the audit found for one rule, as the walk prints it.

    Read off the rule's own `audit`, so the walk says what the board says:
    `Strong. It found nothing.`, `Weak.` with each finding, `Undecided.` with
    the audit's own sentence, or that no audit has read the rule yet.
    """
    audit = entry.get('audit') or {}
    findings = [str(line) for line in audit.get('findings') or ()]
    answered = audit.get('verdict')
    if answered == 'strong':
        return ['  Strong. It found nothing.']
    if answered == 'weak':
        return ['  Weak. %s' % (findings[0] if findings else '')] + [
            '  %s' % line for line in findings[1:]]
    if answered:
        return ['  Undecided. %s' % (findings[0] if findings
                                     else 'The AI audit could not decide.')] \
            + ['  %s' % line for line in findings[1:]]
    return ["  Nothing yet: no audit has read this rule's text, proof and test."]


def render_row(row, entry):
    """One stop of the walk: the rule, its proofs and what the audit found."""
    head = '%s %s   level %s   %s' % (row.get('owner'), row.get('rule'),
                                      row.get('level'), row.get('need'))
    if row.get('need') == states.SIGNATURE and row.get('word') == 'stale':
        head += '   stale: %s' % '; '.join(row.get('reasons') or ())
    lines = [head, 'Rule', '  %s' % (entry.get('text') or '')]
    lines.append('Proof')
    for proof in entry.get('proofs') or ():
        lines.append('  %s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                     proof.get('text')))
    lines.append('What the audit found')
    lines.extend(audit_lines(entry))
    return '\n'.join(lines)


def walk(project_root, payload=None, answer=None, out=None, signer_email=None,
         release=None):
    """Walk the queue, one rule at a time. Returns what happened.

    `answer` is called once per stop with the rule entry, carrying the
    row's `need`, and the rendered row, and returns one of `sign`, `case` or `skip`, optionally as
    `(answer, text)`: the text is what the person saw, for a hand check they
    sign, or the case a reviewer wrote. The default reads a line from stdin.

    Nothing is written until the walk closes, and then one signed commit
    carries the signatures. A skipped rule is in the queue again next time,
    which is the intended behaviour: nothing is marked as seen by being seen.
    """
    out = sys.stdout if out is None else out
    payload = load_payload(project_root, payload)
    answer = _prompt if answer is None else answer
    email = (signer_email or _config(project_root, 'user.email')).lower()

    rows = []
    for row in payload.get('queue') or ():
        entry = rule_entry(payload, row.get('owner'), row.get('rule'))
        if entry is not None:
            rows.append((row, entry))
    result = {'rules': len(rows), 'signed': [], 'cases': [], 'skipped': [],
              'notes': {}, 'commits': [], 'tag': None}
    print(opening_line(payload), file=out)
    if not rows:
        print('Nothing is waiting for a person.', file=out)
        result['tag'] = tag_if_met(project_root, out, release, payload)
        return result

    for row, entry in rows:
        rendered = render_row(row, entry)
        print('', file=out)
        print(rendered, file=out)
        given, text = _one_answer(answer, dict(entry, need=row.get('need')),
                                  rendered)
        pair = (entry['feature'], entry['id'])
        if given == 'sign':
            result['signed'].append(pair)
            if str(text or '').strip():
                result['notes'][pair] = str(text).strip()
        elif given == 'case':
            result['cases'].append((pair, text))
        else:
            result['skipped'].append(pair)

    if result['signed']:
        allowed = _committed_only(payload, _tied_only(
            payload, _allowed(payload, result['signed'], out), out), out)
        result['skipped'].extend(pair for pair in result['signed']
                                 if pair not in allowed)
        result['signed'] = allowed
    if result['signed']:
        sha = sign_and_commit(project_root, result['signed'], email,
                              payload=payload, notes=result['notes'])
        if sha:
            result['commits'].append(sha)

    _close(out, result)
    result['tag'] = tag_if_met(project_root, out, release)
    return result


def _one_answer(answer, entry, rendered):
    given = answer(entry, rendered)
    text = None
    if isinstance(given, (tuple, list)):
        given, text = (list(given) + [None])[:2]
    given = str(given or 'skip').strip().lower()
    for word in ANSWERS:
        if given == word or (given and word.startswith(given)):
            return word, text
    return 'skip', text


def _prompt(entry, _rendered):
    """Read one answer from the person running the walk.

    Signing a hand check asks what the person saw, which the signature
    carries as its note; adding a case asks for the case.
    """
    try:
        given = input('%s %s   sign / case / skip: '
                      % (entry['feature'], entry['id']))
    except (EOFError, KeyboardInterrupt):
        return 'skip'
    given = given.strip().lower()
    if given.startswith('s') and not given.startswith('sk') and (
            entry.get('need') == states.HAND_CHECK):
        question = 'What did you see, in one line: '
    elif given.startswith('c'):
        question = '  in one line: '
    else:
        return given, None
    try:
        return given, input(question)
    except (EOFError, KeyboardInterrupt):
        return 'skip', None


def _close(out, result):
    print('', file=out)
    print('Walked %d rule%s: %d signed, %d case%s added, %d skipped.'
          % (result['rules'], '' if result['rules'] == 1 else 's',
             len(result['signed']), len(result['cases']),
             '' if len(result['cases']) == 1 else 's',
             len(result['skipped'])), file=out)
    for (feature, rule), text in result['cases']:
        print('  %s %s   add this proof line: %s'
              % (feature, rule, text or 'the reviewer named no case'), file=out)
    if result['commits']:
        print('Commits: %s' % ', '.join(sha[:7] for sha in result['commits']),
              file=out)
    if result['cases']:
        print('%s Run: purlin:build' % ARROW, file=out)
    if result['skipped']:
        print('%s Run: purlin:sign' % ARROW, file=out)


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('feature', 'rules', 'batch', 'note', 'release',
                 'project_root', 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rules = []
        self.batch = False
        self.note = None
        self.release = None
        self.project_root = '.'
        self.error = None
        self.help = False


def _parse(argv):
    """The parsed command line, with `error` or `help` set when it is neither."""
    args = _Args()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ('-h', '--help'):
            args.help = True
            return args
        if item == '--batch':
            args.batch = True
        elif item == '--note':
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = '--note needs the line you want on the signature.'
                return args
            args.note = rest.pop(0)
        elif item == '--release':
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = '--release needs the name to tag.'
                return args
            args.release = rest.pop(0)
        elif item == '--project-root':
            if not rest:
                args.error = '--project-root needs a directory.'
                return args
            args.project_root = rest.pop(0)
        elif item.startswith('--'):
            args.error = 'unknown option %s' % item
            return args
        elif item.startswith('RULE-'):
            args.rules.append(item)
        elif args.feature is None:
            args.feature = item
        else:
            args.error = 'unexpected argument %s' % item
            return args
    if args.note is not None and (args.batch or not args.rules):
        args.error = '--note names a feature and the rules it carries.'
    return args


def _gate_is_too_low(gate):
    """The two lines `passed` prints in place of writing a signature."""
    return ['sign: the gate is %s, which asks for no signature.' % gate,
            'sign: purlin:init --gate strong adds the test strength, the AI '
            'audit and the queue.']


def main(argv=None):
    console_module.force_utf8_stdio()
    args = _parse(sys.argv[1:] if argv is None else argv)
    if args.help:
        print(__doc__.strip())
        return EXIT_OK
    if args.error:
        print(USAGE, file=sys.stderr)
        print('sign.py: %s' % args.error, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    project_root = args.project_root
    if not os.path.isdir(project_root or '.'):
        print('sign.py: not a directory: %r' % project_root, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    payload = load_payload(project_root)
    gate_fields = payload.get('gate') or {}
    gate = gate_fields.get('gate') or gate_module.DEFAULT_GATE
    if gate == gate_module.GATES[0]:
        for line in _gate_is_too_low(gate):
            print(line)
        return EXIT_BAD_INVOCATION

    email = _config(project_root, 'user.email').lower()

    if not signing_configured(project_root):
        for line in signing_help():
            print(line)
        return EXIT_NOTHING

    if args.feature is None and not args.batch:
        walk(project_root, payload, signer_email=email, release=args.release)
        report_data.refresh(project_root)
        return EXIT_OK

    if args.feature and args.rules:
        targets = [(args.feature, rule) for rule in args.rules
                   if rule_entry(payload, args.feature, rule) is not None]
        lowered = marked_below(payload, targets)
        for feature, rule, marked in lowered:
            print(MARKED_BELOW % (feature, rule, marked))
        targets = [pair for pair in targets
                   if pair not in [(f, r) for f, r, _level in lowered]]
        if lowered and not targets:
            return EXIT_NOTHING
    else:
        targets = queued(payload, args.feature, None)
    # A rule in the queue is what a signature clears at `strong`, so only a
    # named rule outside it is told it needs none.
    if gate == 'strong' and len(in_queue(payload, targets)) < len(targets):
        print('sign: a signature is required only under the gate signed. '
              'Writing it anyway.')
    targets = _committed_only(payload, _tied_only(payload,
                                                  _allowed(payload, targets)))
    if not targets:
        print('sign: nothing here needs a signature. Run purlin:status to see '
              'what blocks the gate.')
        return EXIT_NOTHING

    sha = sign_and_commit(project_root, targets, email, note=args.note,
                          payload=payload)
    if not sha:
        print('sign: the signature commit was not made. Check that signing '
              'works and that the files are not already committed.')
        return EXIT_NOTHING
    print('Signed %s in %s.' % (_count(len(targets), 'rule'), sha[:7]))
    for name, rule in targets:
        print('  %s %s' % (name, rule))
    # The tag is the no-argument walk's to write. A run that named its rules
    # says whether the walk would now write one, so the last signature of a
    # release is not a dead end.
    after = load_payload(project_root)
    report_data.refresh(project_root, after)
    if not short_of_the_gate(after)[0]:
        print('%s Run: purlin:sign' % ARROW)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
