#!/usr/bin/env python3
"""Write the signatures a person attests, and commit them signed.

    sign.py [--release NAME] [--project-root DIR]
    sign.py <feature> [RULE-N ...] [--project-root DIR]
    sign.py --all [--project-root DIR]
    sign.py <feature> RULE-N [RULE-N ...] --note "<what you saw>"
    sign.py <anchor> RULE-N [RULE-N ...] --does-not-apply "<why>"

A signature is one person's attestation that a rule, its proof, its test, the
code its feature lists and what the audit found belong together, over the
results of the machine each system's tests ran on. It is one file, so two
signatures never conflict:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json

`hash8` is the first eight characters of `signed_hash`, and the slug is the
signer's email local part, lowercased, with every character that is not a
letter or a digit replaced by `-`. Every file here is a person's: a run writes
no signature, ever.

With no argument this walks the rules that wait for a person, one at a time:
the rules whose work left is `to_test_by_hand` or `to_sign`. It opens on those
two lines of `Left to do`. At each stop the answer is one of three: sign the
rule, add a case (a proof line to write into the spec), or skip it. Signing a
hand check asks what the person saw, which the signature carries as its note
when one is given. The walk writes nothing until it closes, and then it makes
one signed commit for the signatures. It works at every gate.

A bare feature signs every waiting rule of that feature, and `--all` every
waiting rule, in one signed commit and with no stop. A rule named by id is
signed whatever it waits on; one no spec has is named last, just above the
summary ending, and the rules named beside it are signed all the same. The
walk and `--all` visit every feature's rules before any anchor's. An anchor's
rule is signed once, over every file of the project but Purlin's own records,
so any change to the project ends that signature.

**Not applying.** `--does-not-apply "<why>"` signs a rule of a pinned anchor,
one carrying `> Source:`, as not applying to this project: an ordinary
signature, over the same hashes, that carries the reason. It works at every
gate. A rule of the project's own anchor that does not apply is deleted
instead. Once such a signature has ended, the rule is left `to_confirm`: the
walk stops at it with three answers, confirm (a new signature with the
earlier reason), sign (it then waits as any rule does) or skip; `--all` and a
bare feature leave it.

**The tag.** At the gate `signed`, when the walk closes and nothing is left
to do but the tag, it writes the evidence package, commits it signed, and
writes the signed tag `signed/<version>` on that commit with `git tag -s`.
The version is read from the `VERSION` file, then `package.json`, then
`pyproject.toml`, then the first `*.csproj` at the root; `--release <name>`
names another. No tag is written while a spec writes a number twice or holds
a line left from a merge conflict, while work is left, while the working tree
or any feature's results are not committed, while the branch's copy on the
host, as this checkout last fetched it, holds commits this checkout lacks,
over a tag that already exists, or with no version. Nothing is fetched and
nothing is pushed.

**A broken spec.** Naming a feature whose spec writes a number twice or holds
a line left from a merge conflict signs nothing: the command prints why and
exits 1. `--all` and the walk never reach such a rule, whose work left is
`to_repair`.

A `.purlin/config.json` that cannot be read stops the command before anything
else is read or written: it prints the sentence saying so and writes nothing.

`references/formats/signature_format.md` holds the file shape field by field.
The hashes come from the payload, which is the one place they are computed,
so a signature this script writes is current the moment it lands.

Exit codes: 0 the signatures were written and committed, the walk closed,
nothing was left to tag, or the tag already exists; 1 there is no key to sign
with, the commit was not made, the feature named has a broken spec, a rule
named is not one any spec has or, with `--does-not-apply`, not a rule of a
pinned anchor, the tag was refused for a broken spec, work or results not
committed, a branch behind its host copy, no version or a package not
committed, git could not write the tag, or the settings file cannot be read;
2 the command line was wrong.
"""

import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import config_engine                                           # noqa: E402
from purlin import report_data                                 # noqa: E402
from purlin import (console as console_module,                 # noqa: E402
                    gate as gate_module,
                    payload as payload_module,
                    signatures as signatures_module,
                    specs as specs_module,
                    summary as summary_module)

SCHEMA = 'purlin-signature/2'
USAGE = ('Usage: sign.py [<feature> [RULE-N ...]] [--all] [--note TEXT] '
         '[--does-not-apply TEXT] [--release NAME] [--project-root DIR]')

# The tag `purlin:sign` writes at the gate `signed` when nothing is left but
# the tag itself.
TAG_PREFIX = 'signed/'
TAGGED = 'Tagged %s at %s.'
NO_TAG_EXISTS = ('No tag: %s is already written. Run purlin:sign --release '
                 '<name> to name another.')
NO_TAG_WORK = ('No tag: the working tree holds changes that are not '
               'committed, so the results do not describe a commit. Commit '
               'them, then run purlin:sign.')
NO_TAG_EVIDENCE = ('No tag: %s has results that are not committed. Run '
                   'purlin:test --commit.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:sign '
              '--release <version>, or write it to a VERSION file.')
NO_TAG_PACKAGE = 'No tag: the evidence package was not committed: %s.'
# The package's own refusal when the committed evidence still has work left,
# said with its cause first and the commands that clear it.
NO_TAG_WORK_LEFT = ('No tag: the committed evidence still has work left to '
                    'do, so no evidence package was committed. Run '
                    'purlin:test --commit, then purlin:sign.')
NO_TAG_GIT = 'No tag: git could not write %s: %s.'
PACKAGE_COMMITTED = 'Evidence package committed: %s.'
# A spec that writes a number twice or holds a line left from a merge
# conflict: signing its feature and the tag are refused until it is fixed.
SPEC_REFUSED = ('%s is not signed: %s. Run purlin:spec %s, then purlin:sign '
                'again.')
NO_TAG_SPEC = ('No tag: %s cannot be counted: %s. Run purlin:spec %s, then '
               'purlin:sign.')
# The branch's copy on the host, as this checkout last fetched it, holds
# commits the checkout lacks.
NO_TAG_BEHIND = ('No tag: %s holds %s that %s does not, as this checkout last '
                 'fetched it. Pull, run purlin:test --commit, then purlin:sign.')

# Why no tag was written, as `tag_if_met` answers it. Each but `exists` is
# something the person must fix, so the command exits 1 on it.
REFUSED_WORK = 'work'
REFUSED_EVIDENCE = 'evidence'
REFUSED_VERSION = 'version'
REFUSED_PACKAGE = 'package'
REFUSED_GIT = 'git'
REFUSED_EXISTS = 'exists'
REFUSED_SPEC = 'spec'
REFUSED_BEHIND = 'behind'
MUST_FIX = (REFUSED_WORK, REFUSED_EVIDENCE, REFUSED_VERSION, REFUSED_PACKAGE,
            REFUSED_GIT, REFUSED_SPEC, REFUSED_BEHIND)

# The key a signer signs with, and the commands that set one up.
NO_KEY = 'No key to sign with. These commands set one up:'
DEFAULT_KEY = '~/.ssh/id_ed25519'
KEYGEN = 'ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""'
SIGNING_SETUP = (
    'git config gpg.format ssh',
    'git config user.signingkey ~/.ssh/id_ed25519.pub',
)
SIGNED_AS = 'Signed %s as %s with the key ending ...%s.'

NOTHING_WAITING = 'Nothing is waiting for someone to test by hand or to sign.'
NOT_A_RULE = ('%s %s is not a rule any spec has. Run purlin:status %s to see '
              'its rules.')


def not_a_rule(feature, rule):
    """The line naming a rule no spec has, filled in for `feature` and `rule`."""
    return NOT_A_RULE % (feature, rule, feature)


# Signing a pinned anchor's rule as not applying to this project, and the
# walk's stop at one whose signature has ended.
TO_CONFIRM = 'to_confirm'
NEEDS_A_REASON = ('--does-not-apply needs the reason the rule does not apply '
                  'to this project.')
NAMES_AN_ANCHOR = ('--does-not-apply names a pinned anchor and the rules it '
                   'carries.')
NOT_PINNED = ('%s %s is not a rule of a pinned anchor, so it cannot be signed '
              'as not applying. A rule of this project that does not apply is '
              'deleted: run purlin:spec %s.')
CONFIRM = ('%s %s was signed as not applying by %s: %s. Confirm it still does '
           'not apply?')


def not_pinned(feature, rule):
    """The refusal for a rule `--does-not-apply` names outside a pinned anchor."""
    return NOT_PINNED % (feature, rule, feature)


NOT_MADE = ('The signature commit was not made: %s. Nothing was signed; run '
            'purlin:sign again once git can make a signed commit.')
NOT_A_DIRECTORY = 'sign.py: %s is not a directory.'

# The line under `Signed <n> rules as ...` for one rule signed, and the one it
# takes at the gate `signed` when the rule's own spec names no files, where
# the signature is written and does not count.
SIGNED_RULE = '  %s %s'
NO_FILES = ('  %s %s   does not count until the spec names its files: '
            'purlin:spec %s')

# What the audit found, as the walk shows it under `What the audit found`:
# the same words the audit printout and the dashboard give.
NO_AUDIT = "No audit has read this rule's text, proof and test yet."
STRONG_NOTHING = 'Strong. It found nothing.'
STRONG = 'Strong.'
WEAK = 'Weak.'
UNDECIDED = ('Undecided. The AI audit could not decide, so the rule reads '
             'weak until its proof or test changes.')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

# The three answers the walk takes, and the letters that reach each one; at a
# rule to confirm as not applying, the three it takes there.
ANSWERS = ('sign', 'case', 'skip')
CONFIRM_ANSWERS = ('confirm', 'sign', 'skip')

# The version files a project already states its version in, read in order.
_PACKAGE_JSON = 'package.json'
_PYPROJECT = 'pyproject.toml'
_PYPROJECT_TABLES = ('project', 'tool.poetry')
_TOML_VERSION = re.compile(r'''^version\s*=\s*(["'])(.*?)\1\s*(#.*)?$''')
_CSPROJ_VERSION = re.compile(r'<Version>\s*([^<]*?)\s*</Version>')


# ---------------------------------------------------------------------------
# The payload, and one rule in it
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='sign')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>` as its own spec lists it, or None.

    Every rule is listed once, under the spec that holds it, an anchor's
    included, and that one listing is what its signature is made over.
    """
    for entry in (payload or {}).get('features') or ():
        if entry.get('name') != feature:
            continue
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def is_pinned_anchor(project_root, feature):
    """True when `feature` is an anchor carrying `> Source:`, pinned from elsewhere."""
    info = specs_module.scan_specs(project_root).get(feature) or {}
    return bool(info.get('is_anchor') and info.get('source'))


def broken_specs(project_root, feature=None):
    """`[(name, reasons), ...]`, by name, for every spec whose rules all read failed.

    A spec is broken while it writes a number twice or holds a line left
    from a merge conflict; `specs.broken_reasons` names why. `feature`
    narrows the question to one spec.
    """
    found = []
    for name, info in sorted(specs_module.scan_specs(project_root).items()):
        if feature is not None and name != feature:
            continue
        reasons = specs_module.broken_reasons(info)
        if reasons:
            found.append((name, list(reasons)))
    return found


def spec_refused(name, reasons):
    """The line refusing to sign a feature whose spec is broken."""
    return SPEC_REFUSED % (name, '; '.join(reasons), name)


def one_line(text):
    """`text` with its whitespace, line ends included, run into single spaces."""
    return ' '.join(str(text or '').split())


# ---------------------------------------------------------------------------
# Writing one signature
# ---------------------------------------------------------------------------

def signature_path(project_root, feature, rule, signed, signer_slug):
    """Where the signature for one rule goes, beside the spec that holds it."""
    info = specs_module.scan_specs(project_root).get(feature)
    directory = signatures_module.signatures_dir(project_root, info or {})
    if not directory:
        return None
    return os.path.join(directory,
                        '%s.%s.%s.json' % (rule, str(signed)[:8], signer_slug))


def write_signature(project_root, entry, signer_email, evidence_path=None,
                    gate=None, note=None, signer_name=None, key=None,
                    does_not_apply=None):
    """Write one signature file for a rule entry. Its project-relative path.

    `entry` is the payload's rule entry, listed under the rule's own spec,
    which carries every hash the signature is made over. `key` is the
    signing key's fingerprint. `does_not_apply` is the reason a pinned
    anchor's rule does not apply to this project, or None for any other
    signature; like `note` it is outside `signed_hash`.
    """
    feature, rule = entry.get('feature'), entry.get('id')
    signed = signatures_module.signed_hash(entry)
    path = signature_path(project_root, feature, rule, signed,
                          signatures_module.signer_slug(signer_email))
    if not path:
        return None
    body = {
        'schema': SCHEMA,
        'feature': feature,
        'rule': rule,
        'applies_to': entry.get('applies_to') or feature,
        'signed_hash': signed,
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'code_hash': entry.get('code_hash'),
        'audit_hash': entry.get('audit_hash'),
        'machines': dict(entry.get('machines') or {}),
        'signer': str(signer_email),
        'signer_name': signer_name or None,
        'key_fingerprint': key,
        'test_hash_kind': entry.get('test_hash_kind'),
        'note': str(note).strip() if str(note or '').strip() else None,
        'does_not_apply': one_line(does_not_apply) or None,
        'timestamp': payload_module.now_iso(),
        'gate': gate,
        'evidence': evidence_path,
    }
    _write_json(path, body)
    return os.path.relpath(path, project_root).replace(os.sep, '/')


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
# What waits for a person
# ---------------------------------------------------------------------------

def waiting(payload, feature=None, rules=None, confirm=False):
    """The rule entries that wait for a person: features' first, then anchors'.

    A rule waits for a person when its work left is `to_test_by_hand` or
    `to_sign`, read off the payload rather than worked out again, and with
    `confirm` also `to_confirm`, which the walk alone stops at. Each rule is
    read once, as the spec that owns it lists it. Every feature's rules come
    before any anchor's, each group by name and rule number.
    """
    kinds = [kind for kind in summary_module.FOR_A_PERSON
             if kind != TO_CONFIRM]
    if confirm:
        kinds.append(TO_CONFIRM)
    anchors = set()
    found = []
    for entry in (payload or {}).get('features') or ():
        if entry.get('is_anchor'):
            anchors.add(entry.get('name'))
        for item in entry.get('rules') or ():
            if item.get('feature') != entry.get('name'):
                continue
            if item.get('left') not in kinds:
                continue
            if feature and item.get('feature') != feature:
                continue
            if rules and item.get('id') not in rules:
                continue
            found.append(item)
    return sorted(found, key=lambda item: (item.get('feature') in anchors,
                                           item.get('feature') or '',
                                           _rule_number(item.get('id'))))


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def uncommitted(payload, features=None):
    """The features, sorted, whose evidence is written and not committed.

    `features` narrows the question; None asks it of every feature, which is
    what the tag reads. A feature with no evidence file has nothing to commit
    and is not named.
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


def uncommitted_work(project_root):
    """The paths outside `.purlin/` that `git status` lists, sorted."""
    try:
        result = subprocess.run(['git', 'status', '--porcelain', '-z'],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []
    found = []
    fields = result.stdout.split('\0')
    while fields:
        field = fields.pop(0)
        if len(field) < 4:
            continue
        if field[0] in 'RC' and fields:
            fields.pop(0)
        path = field[3:]
        if not path.startswith('.purlin/'):
            found.append(path)
    return sorted(found)


# ---------------------------------------------------------------------------
# The version and the tag
# ---------------------------------------------------------------------------

def project_version(project_root):
    """The version the project states, or ''. The first of these that names one.

    The `VERSION` file at the root, `package.json`'s `version`,
    `pyproject.toml`'s `[project]` then `[tool.poetry]` `version`, and the
    `<Version>` of the root `*.csproj` files, read in name order.
    """
    for reader in (_version_file, _package_json, _pyproject, _csproj):
        named = reader(project_root)
        if named:
            return named
    return ''


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


def tag_name(project_root, release=None):
    """`signed/<version>`, `signed/<name>` where `--release` named one, or None."""
    named = str(release or '').strip() or project_version(project_root)
    return TAG_PREFIX + named if named else None


def tag_exists(project_root, name):
    """True when the repository already carries this tag."""
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', '--quiet', 'refs/tags/%s' % name],
        capture_output=True, text=True, cwd=project_root, timeout=10)
    return result.returncode == 0


def tag_message(commit):
    """What the tag says: that nothing was left, and the commit it stands for."""
    gate = gate_module.GATES[-1]
    return ('Nothing left to do at the gate %s.\n\nCommit: %s\nGate: %s\n'
            % (gate, commit or 'unknown', gate))


def _package_module():
    """`scripts/export/package.py`, imported when the tag is about to be written."""
    folder = os.path.join(os.path.dirname(_HERE), 'export')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import package
    return package


def behind_host(project_root):
    """`(ref, count)` when the branch's copy on the host holds commits HEAD lacks.

    The ref is the checked-out branch's upstream, else `origin/<branch>`
    where that exists; the count is `git rev-list --count HEAD..<ref>`, as
    this checkout last fetched it. None when there is no such ref, when HEAD
    names no branch, or when the copy holds nothing HEAD lacks. Nothing is
    fetched.
    """
    ref = _git_out(project_root, 'rev-parse', '--abbrev-ref', '@{upstream}')
    if not ref:
        branch = _git_out(project_root, 'symbolic-ref', '--quiet', '--short',
                          'HEAD')
        if not branch:
            return None
        ref = 'origin/%s' % branch
        if not _git_out(project_root, 'rev-parse', '--verify', '--quiet',
                        'refs/remotes/%s' % ref):
            return None
    count = _git_out(project_root, 'rev-list', '--count', 'HEAD..%s' % ref)
    if not count.isdigit() or int(count) == 0:
        return None
    return ref, int(count)


def behind_line(project_root, ref, count):
    """`No tag: <ref> holds <n> commit(s) that <sha> does not, ...`."""
    head = payload_module.head_sha(project_root) or 'HEAD'
    return NO_TAG_BEHIND % (ref, '%d commit%s' % (count, '' if count == 1
                                                   else 's'), head[:7])


def _git_out(project_root, *args):
    """What a git command prints, stripped, or '' when it fails."""
    try:
        result = subprocess.run(['git'] + list(args), capture_output=True,
                                text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def tag_if_met(project_root, out=None, release=None, payload=None):
    """Write `signed/<version>` at the gate `signed` when nothing else is left.

    Returns `(name, refused)`: the tag's name, or None, and why no tag was
    written, one of the `REFUSED_*` kinds, or None when a tag was written or
    none was due. Below `signed` it writes nothing and prints nothing. At
    `signed` it prints one line per broken spec, then the summary ending;
    the summary ending while any work but the tag is left; one line saying
    why when the working tree or a feature's results are not committed, when
    the branch's copy on the host holds commits this checkout lacks, when no
    version is stated, when the tag already exists, or when git could not
    write it. Otherwise it commits the evidence package, signed, writes a
    signed tag on that commit, and names the push. Nothing is fetched and
    nothing is pushed.
    """
    out = sys.stdout if out is None else out
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    if gate != gate_module.GATES[-1]:
        return None, None
    broken = broken_specs(project_root)
    if broken:
        for name, reasons in broken:
            print(NO_TAG_SPEC % (name, '; '.join(reasons), name), file=out)
        print(summary_module.ending(payload), file=out)
        return None, REFUSED_SPEC
    if any(item.get('kind') != 'to_tag' for item in payload.get('left') or ()):
        print(summary_module.ending(payload), file=out)
        return None, None
    if uncommitted_work(project_root):
        print(NO_TAG_WORK, file=out)
        return None, REFUSED_WORK
    refused = uncommitted(payload)
    if refused:
        for feature in refused:
            print(NO_TAG_EVIDENCE % feature, file=out)
        return None, REFUSED_EVIDENCE
    behind = behind_host(project_root)
    if behind:
        print(behind_line(project_root, *behind), file=out)
        return None, REFUSED_BEHIND
    name = tag_name(project_root, release)
    if name is None:
        print(NO_VERSION, file=out)
        return None, REFUSED_VERSION
    if tag_exists(project_root, name):
        print(NO_TAG_EXISTS % name, file=out)
        return None, REFUSED_EXISTS
    # The package goes into the commit the tag names, so the tagged code
    # carries the evidence that describes it. The commit below it is the one
    # the tag's message names.
    commit = payload.get('commit') or ''
    package = _package_module()
    rel, why = package.write_for_tag(project_root, release)
    if rel is None:
        print(NO_TAG_WORK_LEFT if why == package.WORK_LEFT
              else NO_TAG_PACKAGE % why, file=out)
        return None, REFUSED_PACKAGE
    print(PACKAGE_COMMITTED % rel, file=out)
    written = subprocess.run(
        ['git', 'tag', '-s', name, '-m', tag_message(commit)],
        capture_output=True, text=True, cwd=project_root, timeout=30)
    if written.returncode != 0:
        print(NO_TAG_GIT % (name, _first_line(written)), file=out)
        return None, REFUSED_GIT
    tagged = payload_module.head_sha(project_root) or commit
    print(TAGGED % (name, tagged[:7] or 'HEAD'), file=out)
    print(summary_module.RELEASE % name, file=out)
    return name, None


_GIT_ERRORS = ('fatal: ', 'error: ')


def _first_line(result):
    """The first line of git's own message for a failed command.

    Git may print a note before its error, such as where it left the tag
    message, so the first line that starts `fatal:` or `error:` answers, with
    that word cut; otherwise the first line printed. The closing stop is cut,
    since the line that carries it adds its own.
    """
    lines = [line.strip() for text in (result.stderr, result.stdout)
             for line in str(text or '').splitlines() if line.strip()]
    for line in lines:
        if line.startswith(_GIT_ERRORS):
            return line.split(': ', 1)[1].rstrip('.')
    if lines:
        return lines[0].rstrip('.')
    return 'git exited with %d' % result.returncode


# ---------------------------------------------------------------------------
# A person's signed commit
# ---------------------------------------------------------------------------

def signing_configured(project_root):
    """True when this checkout names an SSH key to sign a commit with."""
    return (_config(project_root, 'gpg.format') == 'ssh'
            and signatures_module.key_fingerprint(project_root) is not None)


def _config(project_root, name):
    try:
        result = subprocess.run(['git', 'config', '--get', name],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def no_key_lines():
    """The lines to print when there is no key to sign with.

    `ssh-keygen` is named only while the key it would write does not exist.
    """
    lines = [NO_KEY]
    if not os.path.exists(signatures_module.expand_home(DEFAULT_KEY)):
        lines.append('  %s' % KEYGEN)
    lines.extend('  %s' % command for command in SIGNING_SETUP)
    return lines


def signed_line(project_root, count, signer_email):
    """`Signed <n> rules as <email> with the key ending ...<last 4>.`"""
    key = signatures_module.key_fingerprint(project_root) or ''
    return SIGNED_AS % ('%d rule%s' % (count, '' if count == 1 else 's'),
                        signer_email, key[-4:])


def commit_message(targets):
    """The subject for one signature commit, from `commit_conventions.md`."""
    features = []
    for feature, _rule in targets:
        if feature not in features:
            features.append(feature)
    if len(features) == 1:
        rules = [rule for _feature, rule in targets]
        return 'sign(%s): %s' % (features[0], ' '.join(rules))
    parts = []
    for feature in features:
        rules = [rule for name, rule in targets if name == feature]
        parts.append('%s %s' % (feature, ' '.join(rules)))
    return 'sign(batch): %s' % ', '.join(parts)


def sign_and_commit(project_root, targets, signer_email, note=None,
                    payload=None, notes=None, does_not_apply=None,
                    reasons=None):
    """Write every signature in `targets` and commit them once, signed.

    `targets` is `[(feature, rule), ...]`. One invocation is one commit
    whether it carries one rule or forty, one file per rule. `note` is the
    one line every signature carries, and `notes` maps a `(feature, rule)` to
    a line of its own, which is how the walk records what a person saw at
    each hand check. `does_not_apply` and `reasons` carry the reason a rule
    does not apply the same way. Returns `(sha, None)`, or `(None, why)` when
    the commit was not made, `why` being git's own message; `(None, None)`
    when no signature file was written.
    """
    notes = notes or {}
    reasons = reasons or {}
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    key = signatures_module.key_fingerprint(project_root)
    name = _config(project_root, 'user.name')
    paths = []
    written = []
    for feature, rule in targets:
        entry = rule_entry(payload, feature, rule)
        if entry is None:
            continue
        path = write_signature(
            project_root, entry, signer_email,
            evidence_for(payload, feature), gate,
            note=notes.get((feature, rule), note), signer_name=name,
            key=key,
            does_not_apply=reasons.get((feature, rule), does_not_apply))
        if path:
            paths.append(path)
            if (feature, rule) not in written:
                written.append((feature, rule))
    if not paths:
        return None, None
    return _commit(project_root, paths, commit_message(written))


def _commit(project_root, paths, message):
    """Stage `paths` and commit them signed. `(sha, None)` or `(None, why)`.

    `why` is git's own message, read as the tag's refusal reads it.
    """
    add = subprocess.run(['git', 'add', '--'] + list(paths),
                         capture_output=True, text=True, cwd=project_root,
                         timeout=30)
    if add.returncode != 0:
        return None, _first_line(add)
    commit = subprocess.run(['git', 'commit', '-S', '-m', message],
                            capture_output=True, text=True, cwd=project_root,
                            timeout=60)
    if commit.returncode != 0:
        return None, _first_line(commit)
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                          text=True, cwd=project_root, timeout=10)
    if head.returncode != 0:
        return None, _first_line(head)
    return head.stdout.strip(), None


def not_made(why):
    """The line saying the signature commit was not made, with git's reason."""
    return NOT_MADE % why


def signed_rule_line(payload, feature, rule):
    """The line naming one rule signed, under `Signed <n> rules as ...`.

    At the gate `signed` a rule whose own spec names no files is signed and
    its signature does not count, so its line says so and names the command
    that adds the files.
    """
    if does_not_count(payload, feature):
        return NO_FILES % (feature, rule, feature)
    return SIGNED_RULE % (feature, rule)


def does_not_count(payload, feature):
    """True at the gate `signed` when `feature`'s own spec names no files."""
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    if gate != gate_module.GATES[-1]:
        return False
    for entry in payload.get('features') or ():
        if entry.get('name') == feature:
            return bool(entry.get('incomplete'))
    return False


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

def opening_lines(payload):
    """What the walk prints first: the lines of `Left to do` it walks."""
    lines = summary_module.left_lines(
        payload, tuple(summary_module.FOR_A_PERSON) + (TO_CONFIRM,))
    return lines or [NOTHING_WAITING]


def last_not_applying(project_root, feature, rule):
    """The last signature for a rule, when it carried `does_not_apply`, or None.

    The last is the one written last, by the time the file records; the walk
    asks the person to confirm its reason once it has ended.
    """
    info = specs_module.scan_specs(project_root).get(feature)
    if not info:
        return None
    found = signatures_module.load_signatures(
        project_root, {feature: info}).get((feature, rule)) or []
    if not found:
        return None
    last = max(found, key=lambda signature: (str(signature.get('timestamp')
                                                  or ''),
                                              str(signature.get('path'))))
    return last if one_line(last.get('does_not_apply')) else None


def confirm_line(entry, earlier):
    """The walk's question at a rule to confirm as not applying."""
    return CONFIRM % (entry.get('feature'), entry.get('id'),
                      earlier.get('signer'),
                      one_line(earlier.get('does_not_apply')).rstrip('.'))


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

    Read off the rule's own `audit`, so the walk says what the audit printout
    and the board say, one line each, indented two spaces: `Strong. It found
    nothing.`, or `Strong.`, `Weak.` or the undecided sentence followed by
    each finding on a line of its own, or that no audit has read the rule
    yet. The walk prints no read-by line.
    """
    audit = entry.get('audit') or {}
    findings = [str(line) for line in audit.get('findings') or ()]
    answered = audit.get('verdict')
    if not answered:
        heads = [NO_AUDIT]
    elif answered == 'strong':
        heads = [STRONG if findings else STRONG_NOTHING]
    elif answered == 'weak':
        heads = [WEAK]
    else:
        heads = [UNDECIDED]
    if answered:
        heads.extend(findings)
    return ['  %s' % line for line in heads]


TIED_TO = '    tied to %s'
TIED_TO_NONE = '    tied to no test'


def tied_lines(proof):
    """The lines naming each test a proof is tied to, as `file::name`.

    One line per test the rule entry lists for the proof, or one line saying
    there is none. A `@manual` proof has no test to name, so it has none.
    """
    if proof.get('manual'):
        return []
    named = []
    for test in proof.get('tests') or ():
        if isinstance(test, dict):
            test = '%s::%s' % (test.get('file'), test.get('name'))
        named.append(TIED_TO % test)
    return named or [TIED_TO_NONE]


def render_row(entry):
    """One stop of the walk: the rule, its proofs and what the audit found.

    Under each proof that is not `@manual` go the tests it is tied to.
    """
    head = '%s %s   %s' % (entry.get('feature'), entry.get('id'),
                           str(entry.get('left') or '').replace('_', ' '))
    lines = [head, 'Rule', '  %s' % (entry.get('text') or '')]
    lines.append('Proof')
    for proof in entry.get('proofs') or ():
        lines.append('  %s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                     proof.get('text')))
        lines.extend(tied_lines(proof))
    lines.append('What the audit found')
    lines.extend(audit_lines(entry))
    return '\n'.join(lines)


def walk(project_root, payload=None, answer=None, out=None, signer_email=None,
         release=None):
    """Walk the rules that wait for a person, one at a time. Returns what happened.

    `answer` is called once per stop with the rule entry and the rendered
    stop, and returns one of `sign`, `case` or `skip`, optionally as
    `(answer, text)`: the text is what the person saw, for a hand check they
    sign, or the case a reviewer wrote. The default reads a line from stdin.

    Nothing is written until the walk closes, and then one signed commit
    carries the signatures. A skipped rule waits again next time: nothing is
    marked as seen by being seen. The walk ends on the summary ending, or at
    the gate `signed` on what the tag says.
    """
    out = sys.stdout if out is None else out
    payload = load_payload(project_root, payload)
    answer = _prompt if answer is None else answer
    email = signer_email or _config(project_root, 'user.email')

    rows = waiting(payload, confirm=True)
    result = {'rules': len(rows), 'signed': [], 'cases': [], 'skipped': [],
              'notes': {}, 'reasons': {}, 'commits': [], 'not_made': False,
              'why': None,
              'tag': None, 'refused': None}
    for line in opening_lines(payload):
        print(line, file=out)
    if not rows:
        result['tag'], result['refused'] = _finish(project_root, out, release,
                                                   payload)
        return result

    for entry in rows:
        rendered = render_row(entry)
        earlier = (last_not_applying(project_root, entry['feature'],
                                     entry['id'])
                   if entry.get('left') == TO_CONFIRM else None)
        if earlier:
            rendered += '\n' + confirm_line(entry, earlier)
        print('', file=out)
        print(rendered, file=out)
        given, text = _one_answer(answer, entry, rendered,
                                  CONFIRM_ANSWERS if earlier else ANSWERS)
        pair = (entry['feature'], entry['id'])
        if given == 'confirm':
            result['signed'].append(pair)
            result['reasons'][pair] = earlier.get('does_not_apply')
        elif given == 'sign':
            result['signed'].append(pair)
            if str(text or '').strip():
                result['notes'][pair] = str(text).strip()
        elif given == 'case':
            result['cases'].append((pair, text))
        else:
            result['skipped'].append(pair)

    if result['signed']:
        sha, why = sign_and_commit(project_root, result['signed'], email,
                                   payload=payload, notes=result['notes'],
                                   reasons=result['reasons'])
        if sha:
            result['commits'].append(sha)
        else:
            result['not_made'], result['why'] = True, why

    _close(project_root, out, result, email, payload)
    result['tag'], result['refused'] = _finish(project_root, out, release)
    return result


def _finish(project_root, out, release, payload=None):
    """The walk's last lines: the tag at `signed`, the summary ending below.

    Returns `(tag, refused)` as `tag_if_met` answers them.
    """
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    if gate == gate_module.GATES[-1]:
        return tag_if_met(project_root, out, release, payload)
    print(summary_module.ending(payload), file=out)
    return None, None


def _one_answer(answer, entry, rendered, answers=ANSWERS):
    given = answer(entry, rendered)
    text = None
    if isinstance(given, (tuple, list)):
        given, text = (list(given) + [None])[:2]
    given = str(given or 'skip').strip().lower()
    for word in answers:
        if given == word or (given and word.startswith(given)):
            return word, text
    return 'skip', text


def _prompt(entry, _rendered):
    """Read one answer from the person running the walk.

    Signing a hand check asks what the person saw, which the signature
    carries as its note when one is given; adding a case asks for the case.
    At a rule to confirm as not applying the answers are confirm, sign or
    skip, and none asks a second question.
    """
    if entry.get('left') == TO_CONFIRM:
        try:
            return input('%s %s   confirm / sign / skip: '
                         % (entry['feature'], entry['id']))
        except (EOFError, KeyboardInterrupt):
            return 'skip'
    try:
        given = input('%s %s   sign / case / skip: '
                      % (entry['feature'], entry['id']))
    except (EOFError, KeyboardInterrupt):
        return 'skip'
    given = given.strip().lower()
    if given.startswith('s') and not given.startswith('sk') and (
            entry.get('left') == 'to_test_by_hand'):
        question = 'What did you see, in one line: '
    elif given.startswith('c'):
        question = '  in one line: '
    else:
        return given, None
    try:
        return given, input(question)
    except (EOFError, KeyboardInterrupt):
        return 'skip', None


def _close(project_root, out, result, email, payload):
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
        for feature, rule in result['signed']:
            if does_not_count(payload, feature):
                print(NO_FILES % (feature, rule, feature), file=out)
        print(signed_line(project_root, len(result['signed']), email),
              file=out)
        print('Commits: %s' % ', '.join(sha[:7] for sha in result['commits']),
              file=out)
    if result['why']:
        print(not_made(result['why']), file=out)


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('feature', 'rules', 'all', 'note', 'does_not_apply',
                 'release', 'project_root', 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rules = []
        self.all = False
        self.note = None
        self.does_not_apply = None
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
        if item == '--all':
            args.all = True
        elif item == '--note':
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = '--note needs the line you want on the signature.'
                return args
            args.note = rest.pop(0)
        elif item == '--does-not-apply':
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = NEEDS_A_REASON
                return args
            args.does_not_apply = one_line(rest.pop(0))
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
    if args.does_not_apply is not None and (
            args.all or not args.rules or args.note is not None
            or args.release is not None):
        args.error = NAMES_AN_ANCHOR
    elif args.note is not None and (args.all or not args.rules):
        args.error = '--note names a feature and the rules it carries.'
    return args


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
        print(NOT_A_DIRECTORY % project_root, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    # A settings file that cannot be read stops the command before anything
    # else is read or written.
    problem = config_engine.config_problem(project_root)
    if problem:
        print(problem)
        return EXIT_NOTHING

    # A feature whose spec is broken is signed by no invocation that names
    # it, whatever the rules, the note or the reason.
    if args.feature is not None:
        broken = broken_specs(project_root, args.feature)
        if broken:
            print(spec_refused(*broken[0]))
            return EXIT_NOTHING

    if not signing_configured(project_root):
        for line in no_key_lines():
            print(line)
        return EXIT_NOTHING

    payload = load_payload(project_root)
    email = _config(project_root, 'user.email')

    if args.feature is None and not args.all:
        result = walk(project_root, payload, signer_email=email,
                      release=args.release)
        report_data.refresh(project_root)
        failed = result['not_made'] or result['refused'] in MUST_FIX
        return EXIT_NOTHING if failed else EXIT_OK

    unknown = []
    if args.does_not_apply is not None and not is_pinned_anchor(
            project_root, args.feature):
        # Only a pinned anchor's rule is signed as not applying; nothing is
        # written for any rule named.
        for rule in args.rules:
            print(not_pinned(args.feature, rule)
                  if rule_entry(payload, args.feature, rule)
                  else not_a_rule(args.feature, rule))
        return EXIT_NOTHING
    if args.feature and args.rules:
        # A rule no spec has is named last, just above the summary ending,
        # and the rules named beside it are signed all the same; the exit
        # says something asked for was not done.
        unknown = [rule for rule in args.rules
                   if rule_entry(payload, args.feature, rule) is None]
        targets = [(args.feature, rule) for rule in args.rules
                   if rule not in unknown]
        if not targets:
            for rule in unknown:
                print(not_a_rule(args.feature, rule))
            print(summary_module.ending(payload))
            return EXIT_NOTHING
    else:
        targets = [(item['feature'], item['id'])
                   for item in waiting(payload, args.feature)]
    if not targets:
        print(NOTHING_WAITING)
        _tag, refused = _finish(project_root, sys.stdout, args.release,
                                payload)
        report_data.refresh(project_root)
        return EXIT_NOTHING if refused in MUST_FIX else EXIT_OK

    sha, why = sign_and_commit(project_root, targets, email, note=args.note,
                               payload=payload,
                               does_not_apply=args.does_not_apply)
    if not sha:
        for rule in unknown:
            print(not_a_rule(args.feature, rule))
        if why:
            print(not_made(why))
        return EXIT_NOTHING
    print(signed_line(project_root, len(targets), email))
    for name, rule in targets:
        print(signed_rule_line(payload, name, rule))
    for rule in unknown:
        print(not_a_rule(args.feature, rule))
    after = load_payload(project_root)
    report_data.refresh(project_root, after)
    print(summary_module.ending(after))
    return EXIT_NOTHING if unknown else EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
