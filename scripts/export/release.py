#!/usr/bin/env python3
"""The release run: check the release commit, commit the package, tag it.

`purlin:test --release [<version>]` runs every test and commits the evidence,
then calls `run_release`. It checks, in this order, and stops at the first
that fails, printing its line: a spec that cannot be counted, a rule whose
tests do not pass, work that is not committed, the branch's copy on the host
holding commits this checkout lacks, no version, and the gate's tag already
written. Then it writes the evidence package for the version and commits it
alone. At the gate `passed` it writes the unsigned tag `passed/<version>` on
that commit; at `signed` it writes no tag, and the first sign-off writes
`signed/<version>`.

A weak rule, a rule the audit never read and a rule with no proof are listed
by `purlin:status`, and none refuses the release. A hand check at `passed` is
named in one line, and the package lists it as not checked.

Nothing is fetched and nothing is pushed.
"""

import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'), _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import (gate as gate_module,                       # noqa: E402
                    payload as payload_module,
                    specs as specs_module,
                    summary as summary_module)

NO_RELEASE_SPEC = ('No release: %s cannot be counted: %s. Run purlin:spec %s, then '
                   'purlin:test --release.')
NO_RELEASE_FAILING = ('No release: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:test --release.')
NO_RELEASE_WORK = ('No release: the working tree holds changes that are not committed, so '
                   'the results do not describe a commit. Commit them, then run '
                   'purlin:test --release.')
NO_RELEASE_BEHIND = ('No release: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:test --release.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:test --release '
              '<version>, or write it to a VERSION file.')
NO_RELEASE_EXISTS = ('No release: %s is already written. Run purlin:test --release '
                     '<version> to name another.')
NO_RELEASE_PACKAGE = 'No release: the evidence package was not committed: %s.'
NO_TAG_GIT = 'No tag: git could not write %s: %s.'
PACKAGE_COMMITTED = 'Evidence package committed: %s.'
TAGGED = 'Tagged %s at %s.'
READY_TO_SIGN = 'Run purlin:sign to sign it; the first signature writes %s.'
REFUSED = ('spec', 'failing', 'work', 'behind', 'version', 'exists', 'package', 'git')

# A hand check at the gate passed: nobody signs, so nothing records it.
HAND_CHECKS = ('%s, and the gate passed records no hand check: %s. The package lists '
               'them as not checked.')

TAG_MESSAGE = 'Released at the gate %s.\n\nCommit: %s\nGate: %s\n'
PACKAGE_DIR = '.purlin/evidence/package'
SIGNOFFS_SUFFIX = '.signoffs'

_PACKAGE_JSON = 'package.json'
_PYPROJECT = 'pyproject.toml'
_PYPROJECT_TABLES = ('project', 'tool.poetry')
_TOML_VERSION = re.compile(r'''^version\s*=\s*(["'])(.*?)\1\s*(#.*)?$''')
_CSPROJ_VERSION = re.compile(r'<Version>\s*([^<]*?)\s*</Version>')
_GIT_ERRORS = ('fatal: ', 'error: ')


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git(project_root, *args):
    try:
        return subprocess.run(['git'] + list(args), capture_output=True,
                              text=True, cwd=project_root, timeout=60)
    except (subprocess.SubprocessError, OSError) as error:
        return subprocess.CompletedProcess(args, 1, '', str(error))


def _git_out(project_root, *args):
    """What a git command prints, stripped, or '' when it fails."""
    result = _git(project_root, *args)
    return result.stdout.strip() if result.returncode == 0 else ''


def _first_line(result):
    """The first line of git's own message for a failed command.

    The first line that starts `fatal:` or `error:` answers, with that word
    cut; otherwise the first line printed. The closing stop is cut, since the
    line that carries it adds its own.
    """
    lines = [line.strip() for text in (result.stderr, result.stdout)
             for line in str(text or '').splitlines() if line.strip()]
    for line in lines:
        if line.startswith(_GIT_ERRORS):
            return line.split(': ', 1)[1].rstrip('.')
    if lines:
        return lines[0].rstrip('.')
    return 'git exited with %d' % result.returncode


def uncommitted_work(project_root):
    """True when `git status` lists a path outside `.purlin/`."""
    result = _git(project_root, 'status', '--porcelain', '-z')
    if result.returncode != 0:
        return False
    fields = result.stdout.split('\0')
    while fields:
        field = fields.pop(0)
        if len(field) < 4:
            continue
        if field[0] in 'RC' and fields:
            fields.pop(0)
        if not field[3:].startswith('.purlin/'):
            return True
    return False


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


def behind_words(count):
    """`1 commit` or `<n> commits`."""
    return '%d commit%s' % (count, '' if count == 1 else 's')


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


def tag_name(gate, version):
    """`passed/<version>` at the gate `passed`, `signed/<version>` at `signed`."""
    return '%s/%s' % (_gate_word(gate), version)


def _gate_word(gate):
    return 'signed' if gate == 'signed' else 'passed'


def tag_exists(project_root, name):
    """True when the repository already carries this tag."""
    return _git(project_root, 'rev-parse', '--verify', '--quiet',
                'refs/tags/%s' % name).returncode == 0


def tag_message(gate, commit):
    """What the tag says: the gate, and the commit the package describes."""
    word = _gate_word(gate)
    return TAG_MESSAGE % (word, commit or 'unknown', word)


def write_tag(project_root, name, message, signed):
    """Write an annotated tag on HEAD, signed with `-s` or not. `(ok, git's first line)`."""
    made = _git(project_root, 'tag', '-s' if signed else '-a', name,
                '-m', message)
    if made.returncode != 0:
        return False, _first_line(made)
    return True, ''


# ---------------------------------------------------------------------------
# The package as the commit holds it
# ---------------------------------------------------------------------------

def package_rel(version):
    """`.purlin/evidence/package/<version>.json`."""
    return '%s/%s.json' % (PACKAGE_DIR, version)


def package_at_head(project_root, version):
    """`(rel, package)` as HEAD's tree holds the package, or None."""
    rel = package_rel(version)
    shown = _git(project_root, 'show', 'HEAD:%s' % rel)
    if shown.returncode != 0:
        return None
    try:
        package = json.loads(shown.stdout)
    except ValueError:
        return None
    return (rel, package) if isinstance(package, dict) else None


def only_signoffs_since(project_root, commit):
    """True when every commit after `commit`, up to HEAD, touches only packages.

    Each may change a package file, `.purlin/evidence/package/<version>.json`,
    or a sign-off under `.purlin/evidence/package/<version>.signoffs/`, and
    nothing else. False when `commit` is not an ancestor of HEAD.
    """
    if _git(project_root, 'merge-base', '--is-ancestor', commit,
            'HEAD').returncode != 0:
        return False
    listed = _git(project_root, 'log', '--format=', '--name-only',
                  '%s..HEAD' % commit)
    if listed.returncode != 0:
        return False
    for path in listed.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if not path.startswith(PACKAGE_DIR + '/'):
            return False
        rest = path[len(PACKAGE_DIR) + 1:]
        head = rest.split('/', 1)[0]
        if '/' in rest and not head.endswith(SIGNOFFS_SUFFIX):
            return False
        if '/' not in rest and not rest.endswith('.json'):
            return False
    return True


# ---------------------------------------------------------------------------
# What the checks read
# ---------------------------------------------------------------------------

def _number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def broken_specs(project_root):
    """`[(name, reasons)]`, by name, for every spec that cannot be counted."""
    found = []
    for name, info in sorted(specs_module.scan_specs(project_root).items()):
        reasons = specs_module.broken_reasons(info)
        if reasons:
            found.append((name, list(reasons)))
    return found


def blocking_rules(payload):
    """`[(feature, [RULE-N, ...])]` for every rule whose `left` stops a release."""
    blocking = summary_module.BLOCKING
    found = {}
    for feature in payload.get('features') or ():
        name = feature.get('name')
        for rule in feature.get('rules') or ():
            if rule.get('feature') == name and rule.get('left') in blocking:
                found.setdefault(name, []).append(rule.get('id'))
    return [(name, sorted(ids, key=_number)) for name, ids in sorted(found.items())]


def corrections(payload):
    """How many test comments are to correct, as `Left to do` counts them."""
    return sum(item.get('count') or 0 for item in payload.get('left') or ()
               if item.get('kind') == 'to_correct')


def failing_line(payload, head):
    """`NO_RELEASE_FAILING` filled, or None when every rule's tests pass."""
    rules = blocking_rules(payload)
    comments = corrections(payload)
    if not rules and not comments:
        return None
    count = sum(len(ids) for _name, ids in rules)
    parts = ['%s %s' % (name, ', '.join(ids)) for name, ids in rules]
    comment_words = '%d test comment%s to correct' % (
        comments, '' if comments == 1 else 's')
    if comments:
        parts.append(comment_words)
    if count:
        first = ('1 rule does not pass' if count == 1
                 else '%d rules do not pass' % count)
    else:
        first = ('1 test comment does not count' if comments == 1
                 else '%d test comments do not count' % comments)
    return NO_RELEASE_FAILING % (first, head[:7], '; '.join(parts))


def hand_checks(payload):
    """`[(feature, RULE-N)]`, by feature then number, for every rule with a `@manual` proof."""
    found = []
    for feature in payload.get('features') or ():
        name = feature.get('name')
        for rule in feature.get('rules') or ():
            if rule.get('feature') != name:
                continue
            if any(proof.get('manual') for proof in rule.get('proofs') or ()):
                found.append((name, rule.get('id')))
    return sorted(found, key=lambda pair: (str(pair[0]), _number(pair[1])))


def hand_check_line(pairs):
    """C13's line naming the hand checks at the gate passed."""
    count = ('1 rule is checked by hand' if len(pairs) == 1
             else '%d rules are checked by hand' % len(pairs))
    return HAND_CHECKS % (count, ', '.join('%s %s' % pair for pair in pairs))


def _package_module():
    import package
    return package


# ---------------------------------------------------------------------------
# The release
# ---------------------------------------------------------------------------

def run_release(project_root, version=None, out=None):
    """Check the release commit, write and commit the package, tag at passed.

    Returns (tag name or None, refused kind or None). Nothing is fetched and
    nothing is pushed."""
    out = sys.stdout if out is None else out

    def say(line):
        print(line, file=out)

    broken = broken_specs(project_root)
    if broken:
        for name, reasons in broken:
            say(NO_RELEASE_SPEC % (name, '; '.join(reasons), name))
        return None, 'spec'

    payload = payload_module.build_payload(project_root, generated_by='release')
    gate = _gate_word((payload.get('gate') or {}).get('gate')
                      or gate_module.DEFAULT_GATE)
    head = payload.get('commit') or payload_module.head_sha(project_root) or ''
    failing = failing_line(payload, head)
    if failing:
        say(failing)
        return None, 'failing'
    if uncommitted_work(project_root):
        say(NO_RELEASE_WORK)
        return None, 'work'
    behind = behind_host(project_root)
    if behind:
        ref, count = behind
        say(NO_RELEASE_BEHIND % (ref, behind_words(count), head[:7]))
        return None, 'behind'
    version = str(version or '').strip() or project_version(project_root)
    if not version:
        say(NO_VERSION)
        return None, 'version'
    name = tag_name(gate, version)
    if tag_exists(project_root, name):
        say(NO_RELEASE_EXISTS % name)
        return None, 'exists'

    if gate == 'passed':
        checks = hand_checks(payload)
        if checks:
            say(hand_check_line(checks))
    package_module = _package_module()
    try:
        package = package_module.build(project_root, version)
        rel = package_module.write(project_root, package)
        package_module.commit(project_root, rel, package)
    except (package_module.PackageError, IOError, OSError) as error:
        say(NO_RELEASE_PACKAGE % str(error).rstrip('.'))
        return None, 'package'
    say(PACKAGE_COMMITTED % rel)

    if gate == 'signed':
        say(READY_TO_SIGN % name)
        return None, None
    ok, why = write_tag(project_root, name,
                        tag_message(gate, package['commit']), signed=False)
    if not ok:
        say(NO_TAG_GIT % (name, why))
        return None, 'git'
    tagged = payload_module.head_sha(project_root) or ''
    say(TAGGED % (name, tagged[:7]))
    say(summary_module.RELEASE % name)
    return name, None
