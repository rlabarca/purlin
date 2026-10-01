#!/usr/bin/env python3
"""Sign the evidence package for a version, as a signed commit.

    sign.py [--version <version>] [--project-root DIR]
    sign.py --show [--version <version>] [--project-root DIR]
    sign.py --answers FILE [--version <version>] [--project-root DIR]
    sign.py --check FILE

Any project may run it whenever it chooses. It reads the evidence committed
at HEAD, builds the evidence package for the version and walks it with a
person: who ran the tests, where and when; an overview counting per system
the rules that pass and the hand checks, and what the audit found; the
audit's findings as a list the signer may open; then one stop per hand check,
which shows the rule's last note where a sign-off holds one, and where the
person types what they saw or presses Enter for no note. On yes to
the last question it writes one file in one signed commit:

    .purlin/evidence/package/<version>.signoffs/<signer-slug>.json

The first sign-off of a version commits the package with it,
`.purlin/evidence/package/<version>.json`, and writes the signed tag
`signed/<version>` on that commit; a later sign-off adds its own file alone
and the tag does not move. `references/formats/signature_format.md` holds the
sign-off field by field, and `package_format.md` the package.

**Refusals**, in this order, each one line with nothing written and exit 1:
tracked files are changed and not committed; the evidence is written and not
committed; no version is stated or named; `signed/<version>` is on a commit
this checkout does not hold, or the code changed since it; a result was not
taken on this version of the code; a result was taken while files were
changed and not committed; a rule has no test; a rule does not pass; the
branch's copy on the host, as this checkout last fetched it, holds commits
HEAD lacks; the signer already signed this package. Then,
for the walk and `--answers`, no key to sign with. Nothing is fetched and
nothing is pushed.

`--show` prints what the walk shows, asks nothing, writes nothing and needs
no key. `--answers FILE` walks with the answers a JSON file gives, for an
agent whose shell has no terminal to ask in. `--check FILE` checks a package
against its fingerprint. `--version <version>` names the version in place of
the one the project states.

Exit codes: 0 signed, shown, checked and matching, stopped, or declined; 1
refused, no key, the package or the commit not written, the tag not written,
or not matching; 2 the command line was wrong.
"""

import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'), os.path.join(_SCRIPTS, 'export'),
              _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import config_engine                                           # noqa: E402
import package as package_module                               # noqa: E402
from purlin import report_data                                 # noqa: E402
from purlin import (console as console_module,                 # noqa: E402
                    evidence as evidence_module,
                    payload as payload_module,
                    signatures as signatures_module,
                    states as states_module,
                    summary as summary_module)

SCHEMA = 'purlin-signoff/1'
USAGE = ('Usage: sign.py [--version <version>] [--show | --answers FILE | '
         '--check FILE] [--project-root DIR]')

# The refusals, in the order they are read.
NO_SIGNOFF_WORK_ONE = ('No sign-off: 1 file is changed and not committed. Commit it or '
                       'set it aside, then run purlin:sign again.')
NO_SIGNOFF_WORK_MANY = ('No sign-off: %d files are changed and not committed. Commit them '
                        'or set them aside, then run purlin:sign again.')
NO_SIGNOFF_EVIDENCE = ('No sign-off: the evidence is written and not committed. Run '
                       'purlin:test --commit, then purlin:sign.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:sign --version '
              '<version>, or write it to a VERSION file.')
NO_SIGNOFF_ELSEWHERE = ('No sign-off: %s is at %s, which this checkout does not hold. '
                        'Pull, then run purlin:sign.')
NO_SIGNOFF_MOVED = ('No sign-off: %s is at %s, and the code has changed since. To sign this '
                    'code, name a new version: purlin:sign --version <version>.')
NO_SIGNOFF_NOT_THIS_CODE = ('No sign-off: these results were not taken on this version of '
                            'the code, %s: %s. Run %s, then purlin:sign.')
NO_SIGNOFF_DIRTY = ('No sign-off: these results were taken while files were changed and '
                    'not committed: %s. Run %s, then purlin:sign.')
NO_SIGNOFF_NO_TEST = 'No sign-off: %s at %s: %s. Run purlin:build %s, then purlin:sign.'
NO_SIGNOFF_FAILING = ('No sign-off: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:sign.')
NO_SIGNOFF_BEHIND = ('No sign-off: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:sign.')
ALREADY_SIGNED = '%s has already signed %s over this package; nothing was written.'
NOT_MADE = 'The sign-off commit was not made: %s. Nothing was signed; run purlin:sign again.'
NOT_WRITTEN = ('The evidence package was not written: %s. Nothing was signed; run '
               'purlin:sign again.')
NO_TAG_GIT = 'No tag: git could not write %s: %s.'

# What runs a result again, by the source it came from. `%s` is the systems
# of the `ci` results named.
RUN_AGAIN = {'local': 'purlin:test --all --commit', 'ci': 'purlin:test on %s'}

# The key a signer signs with, and the commands that set one up.
NO_KEY = 'No key to sign with. These commands set one up:'
DEFAULT_KEY = '~/.ssh/id_ed25519'
KEYGEN = 'ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""'
SIGNING_SETUP = (
    'git config gpg.format ssh',
    'git config user.signingkey ~/.ssh/id_ed25519.pub',
)

# The walk.
OVERVIEW = 'Signing %s at %s.'
OVERVIEW_RULES = '  %s on %s: %s, %s.'
OVERVIEW_AUDIT = '  The audit: %d strong, %d weak, %d not audited.'
AUDIT_ASK = "The audit's findings: %s. list / go on: "
AUDIT_SHOWN = "The audit's findings: %s."
AUDIT_LIST = '  %s %s   %s'
AUDIT_AGAIN = 'go on: '
STOP_HEAD = '%s %s   hand check'
HAND_ASK = '%s %s   what did you see, in one line, or Enter for no note, or stop: '
NO_NOTE = 'no note'
STOPPED = ('Stopped at %s %s: nothing was signed. After the fix, run purlin:test --all '
           '--commit, then purlin:sign.')
SIGN_ASK = 'Sign the evidence package for %s as %s? [y/N] '
NOT_SIGNED = 'Nothing was signed.'
SIGNED_AS = 'Signed %s as %s with the key ending ...%s.'
TAGGED = 'Tagged %s at %s.'
SIGNED_PUSH = 'Push the branch and the tag: git push origin %s'
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push origin%s'
SHOW_NEXT = 'Answer each stop, then run purlin:sign --answers <file>.'
MATCHES = 'The package matches its fingerprint.'
NO_MATCH = 'The package does not match its fingerprint: %s.'

# A stop.
RESULT = '  %s: %s on %s'
NOTHING = '; nothing to check for %s: %s'
TIED_TO = '    tied to %s'
TIED_TO_NONE = '    tied to no test'
AUDIT_WEAK = 'What the audit found'
LAST_NOTE = 'Last note'

# The agent's walk.
ANSWERS_MISSING = ('No sign-off: %s has no answer in %s. Answer every stop, '
                   'then run purlin:sign --answers %s again.')
ANSWERS_UNREAD = 'No sign-off: %s cannot be read: %s.'

NOT_A_DIRECTORY = 'sign.py: %s is not a directory.'

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2


class Stopped(Exception):
    """The person stopped the walk at a hand check; nothing is written."""

    def __init__(self, stop):
        Exception.__init__(self, '%s %s' % (stop['feature'], stop['rule']))
        self.stop = stop


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


_GIT_ERRORS = ('fatal: ', 'error: ')


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
    """How many tracked files outside `.purlin/` are changed and not committed.

    A file git does not track is not counted: it is in no commit, so it is
    in nothing the sign-off signs.
    """
    result = _git(project_root, 'status', '--porcelain', '-z',
                  '--untracked-files=no')
    if result.returncode != 0:
        return 0
    count = 0
    fields = result.stdout.split('\0')
    while fields:
        field = fields.pop(0)
        if len(field) < 4:
            continue
        if field[0] in 'RC' and fields:
            fields.pop(0)
        if not field[3:].startswith('.purlin/'):
            count += 1
    return count


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
        branch = _branch(project_root)
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


def _branch(project_root):
    """The checked-out branch's short name, or '' on a detached HEAD."""
    return _git_out(project_root, 'symbolic-ref', '--quiet', '--short', 'HEAD')


def tag_exists(project_root, name):
    """True when the repository already carries this tag."""
    return _git(project_root, 'rev-parse', '--verify', '--quiet',
                'refs/tags/%s' % name).returncode == 0


def write_tag(project_root, name, message):
    """Write a signed annotated tag on HEAD. `(ok, git's first line)`."""
    made = _git(project_root, 'tag', '-s', name, '-m', message)
    if made.returncode != 0:
        return False, _first_line(made)
    return True, ''


def tag_message(version, package):
    """What the tag says: the version, and the commit the package describes."""
    return 'Signed %s.\n\nCommit: %s\n' % (version, package.get('commit')
                                         or 'unknown')


def signing_configured(project_root):
    """True when this checkout names an SSH key to sign a commit with."""
    return (_git_out(project_root, 'config', '--get', 'gpg.format') == 'ssh'
            and signatures_module.key_fingerprint(project_root) is not None)


def no_key_lines():
    """The lines to print when there is no key to sign with.

    `ssh-keygen` is named only while the key it would write does not exist.
    """
    lines = [NO_KEY]
    if not os.path.exists(signatures_module.expand_home(DEFAULT_KEY)):
        lines.append('  %s' % KEYGEN)
    lines.extend('  %s' % command for command in SIGNING_SETUP)
    return lines


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------

def _count(one, many, count):
    return one if count == 1 else many % count


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def failing_fill(package):
    """`(count words, rules)` for what stops a sign-off, or None.

    The rules whose work left is in `summary.BLOCKING`, by feature then
    number, as `sample_age RULE-2, RULE-3; stability RULE-1`, then the test
    comments to correct, as `1 test comment to correct`.
    """
    named = {}
    for feature in package.get('features') or ():
        for rule in feature.get('rules') or ():
            if rule.get('left') in summary_module.BLOCKING:
                named.setdefault(feature.get('name'), []).append(rule.get('id'))
    corrections = sum(int(item.get('count') or 0)
                      for item in package.get('left') or ()
                      if item.get('kind') == 'to_correct')
    if not named and not corrections and package.get('met'):
        return None
    count = sum(len(rules) for rules in named.values())
    parts = ['%s %s' % (name, ', '.join(sorted(rules, key=_rule_number)))
             for name, rules in sorted(named.items())]
    if corrections:
        parts.append(_count('1 test comment to correct',
                            '%d test comments to correct', corrections))
    if not parts:
        parts = ['%s: %s' % (item.get('text'), item.get('command'))
                 for item in package.get('left') or ()
                 if item.get('kind') in summary_module.BLOCKING]
    return (_count('1 rule does not pass', '%d rules do not pass', count),
            '; '.join(parts))


def no_test_fill(package):
    """`(count words, rules, feature)` for the rules with no test, or None.

    The rules whose work left is `no_test`, a rule with no proof and no test
    among them, named as `failing_fill` names rules; `feature` is the first
    of them, which `purlin:build` is run for.
    """
    named = {}
    for feature in package.get('features') or ():
        for rule in feature.get('rules') or ():
            if rule.get('left') == 'no_test':
                named.setdefault(feature.get('name'), []).append(rule.get('id'))
    if not named:
        return None
    count = sum(len(rules) for rules in named.values())
    parts = ['%s %s' % (name, ', '.join(sorted(rules, key=_rule_number)))
             for name, rules in sorted(named.items())]
    return (_count('1 rule has no test', '%d rules have no test', count),
            '; '.join(parts), sorted(named)[0])


def off_code_fill(package, project_root):
    """`(what, commands)` for the results not taken on this code, or None."""
    return _results_fill(package_module.off_code(package, project_root))


def dirty_fill(package, project_root):
    """`(what, commands)` for the results taken while files were changed and
    not committed, or None."""
    return _results_fill(package_module.taken_dirty(package, project_root))


def _results_fill(found):
    """`(what, commands)` for `[(system words, source, [features])]`, or None."""
    if not found:
        return None
    by_system, sources, elsewhere = [], set(), []
    for words, source, names in found:
        sources.add(source)
        if source == 'ci' and words not in elsewhere:
            elsewhere.append(words)
        known = next((item for item in by_system if item[0] == words), None)
        if known is None:
            by_system.append((words, list(names)))
        else:
            known[1].extend(name for name in names if name not in known[1])
    what = '; '.join('%s on %s' % (', '.join(sorted(names)), words)
                     for words, names in by_system)
    fill = {'local': RUN_AGAIN['local'],
            'ci': RUN_AGAIN['ci'] % ' and '.join(elsewhere)}
    commands = ' and '.join(fill[source] for source in ('local', 'ci')
                            if source in sources)
    return what, commands


def _signer(project_root):
    return _git_out(project_root, 'config', '--get', 'user.email')


def committed_package(project_root, version):
    """The package HEAD's tree holds for `version`, or None."""
    text = _git_out(project_root, 'show',
                    'HEAD:%s' % signatures_module.package_rel(version))
    try:
        package = json.loads(text) if text else None
    except ValueError:
        return None
    return package if isinstance(package, dict) else None


def refusal(project_root, name=None):
    """What stands in the way of a sign-off: `(lines, exit, info)`.

    `lines` is empty when nothing does, and `info` then holds what the walk
    reads: `version`, `tag`, `first` (no tag is written yet), `package`,
    `written` (the package is to be written with the sign-off), `head` and
    `email`.
    """
    changed = uncommitted_work(project_root)
    if changed:
        return ([_count(NO_SIGNOFF_WORK_ONE, NO_SIGNOFF_WORK_MANY, changed)],
                EXIT_NOTHING, None)
    if package_module.uncommitted_evidence(project_root):
        return [NO_SIGNOFF_EVIDENCE], EXIT_NOTHING, None
    version = (str(name or '').strip()
               or package_module.project_version(project_root))
    if not version:
        return [NO_VERSION], EXIT_NOTHING, None
    head = _git_out(project_root, 'rev-parse', 'HEAD')
    tag = package_module.tag_name(version)
    first = not tag_exists(project_root, tag)
    if not first:
        at = _git_out(project_root, 'rev-parse', '%s^{commit}' % tag)
        if _git(project_root, 'merge-base', '--is-ancestor', at,
                'HEAD').returncode != 0:
            return [NO_SIGNOFF_ELSEWHERE % (tag, at[:7])], EXIT_NOTHING, None
        if not package_module.only_records_between(project_root, at, 'HEAD'):
            return [NO_SIGNOFF_MOVED % (tag, at[:7])], EXIT_NOTHING, None
    package = None if first else committed_package(project_root, version)
    written = package is None
    if written:
        try:
            package = package_module.build(project_root, version)
        except (package_module.PackageError, IOError, OSError) as error:
            return [NOT_WRITTEN % str(error).rstrip('.')], EXIT_NOTHING, None
    off = off_code_fill(package, project_root)
    if off:
        return ([NO_SIGNOFF_NOT_THIS_CODE % (head[:7], off[0], off[1])],
                EXIT_NOTHING, None)
    dirty = dirty_fill(package, project_root)
    if dirty:
        return [NO_SIGNOFF_DIRTY % dirty], EXIT_NOTHING, None
    no_test = no_test_fill(package)
    if no_test:
        return ([NO_SIGNOFF_NO_TEST % (no_test[0], head[:7], no_test[1],
                                       no_test[2])], EXIT_NOTHING, None)
    failing = failing_fill(package)
    if failing:
        return ([NO_SIGNOFF_FAILING % (failing[0], head[:7], failing[1])],
                EXIT_NOTHING, None)
    behind = behind_host(project_root)
    if behind:
        ref, count = behind
        return ([NO_SIGNOFF_BEHIND % (ref, behind_words(count), head[:7])],
                EXIT_NOTHING, None)
    email = _signer(project_root)
    if already_signed(project_root, version, email, package):
        return [ALREADY_SIGNED % (email, version)], EXIT_NOTHING, None
    return [], EXIT_OK, {'version': version, 'tag': tag, 'first': first,
                         'package': package, 'written': written,
                         'head': head, 'email': email}


def signoff_rel(version, email):
    """Where one signer's sign-off of `version` goes, `/` separated."""
    return '%s/%s.json' % (signatures_module.signoffs_dir(version),
                           signatures_module.signer_slug(email))


def already_signed(project_root, version, email, package):
    """True when HEAD holds this signer's sign-off over this very package."""
    text = _git_out(project_root, 'show',
                    'HEAD:%s' % signoff_rel(version, email))
    try:
        earlier = json.loads(text) if text else None
    except ValueError:
        return False
    return (isinstance(earlier, dict)
            and earlier.get('package_hash') == package.get('fingerprint'))


# ---------------------------------------------------------------------------
# What the package shows
# ---------------------------------------------------------------------------

def package_rules(package):
    """Every rule of the package as `(feature, rule entry)`, by feature and number."""
    found = []
    for feature in sorted(package.get('features') or (),
                          key=lambda entry: str(entry.get('name'))):
        for rule in sorted(feature.get('rules') or (),
                           key=lambda entry: _rule_number(entry.get('id'))):
            found.append((feature.get('name'), rule))
    return found


def _hand_check(rule):
    return any(proof.get('manual') for proof in rule.get('proofs') or ())


def _weak(rule):
    return (rule.get('audit') or {}).get('verdict') == 'weak'


def _chosen_results(rule):
    """`{os: result}`: per system, a current result before one that is not,
    then one under the source `ci` before one under `local`."""
    chosen = {}
    for result in rule.get('results') or ():
        system = result.get('os')
        if not system:
            continue
        rank = (not result.get('current'), result.get('source') != 'ci')
        if system not in chosen or rank < chosen[system][0]:
            chosen[system] = (rank, result)
    return {system: pair[1] for system, pair in chosen.items()}


def _systems(names):
    return ([name for name in states_module.SYSTEM_ORDER if name in names]
            + sorted(name for name in names
                     if name not in states_module.SYSTEM_ORDER))


def last_notes(project_root):
    """`{(feature, rule): [line]}`: each hand check's last note, from the same
    source and in the same words as the dashboard shows it."""
    return payload_module.hand_notes(project_root)


def plan(package, notes=None):
    """What the walk shows: the overview's numbers, the weak rules and the stops.

    `notes` is what `last_notes` gives; each stop carries its rule's lines."""
    notes = notes or {}
    rules = package_rules(package)
    per_system = {}
    weak, stops = [], []
    for feature, rule in rules:
        for system, result in _chosen_results(rule).items():
            counts = per_system.setdefault(system, {'rules': 0, 'passing': 0,
                                                    'hand_checks': 0})
            counts['rules'] += 1
            if result.get('result') == 'passed':
                counts['passing'] += 1
            if _hand_check(rule):
                counts['hand_checks'] += 1
        if _weak(rule):
            weak.append({'feature': feature, 'rule': rule.get('id'),
                         'entry': rule})
        if _hand_check(rule):
            stops.append({'feature': feature, 'rule': rule.get('id'),
                          'entry': rule,
                          'last_notes': list(notes.get(
                              (feature, rule.get('id'))) or ())})
    audit = package.get('audit') or {}
    audited = any(audit.get(key) for key in ('strong', 'weak'))
    overview = {
        'systems': [dict(per_system[name], os=name)
                    for name in _systems(per_system)],
        'audit': ({'strong': audit.get('strong') or 0,
                   'weak': audit.get('weak') or 0,
                   'not_audited': audit.get('not_audited') or 0}
                  if audited else None)}
    return {'overview': overview, 'weak': weak, 'stops': stops}


def overview_lines(info, shown):
    """The run lines, then what is signed, the rules per system and the audit."""
    package = info['package']
    lines = package_module.run_lines(package)
    lines.append(OVERVIEW % (info['version'],
                             str(package.get('commit') or '')[:7]))
    for system in shown['overview']['systems']:
        lines.append(OVERVIEW_RULES % (
            _count('1 rule', '%d rules', system['rules']),
            evidence_module.os_word(system['os']),
            _count('1 passes its tests', '%d pass their tests',
                   system['passing']),
            'no hand check' if not system['hand_checks']
            else _count('1 has a hand check', '%d have a hand check',
                        system['hand_checks'])))
    audit = shown['overview']['audit']
    if audit:
        lines.append(OVERVIEW_AUDIT % (audit['strong'], audit['weak'],
                                       audit['not_audited']))
    return lines


def audit_list_lines(weak):
    """One line per finding of each weak rule, the rule named on each."""
    lines = []
    for item in weak:
        findings = (item['entry'].get('audit') or {}).get('findings') or ()
        for finding in findings or ('',):
            lines.append((AUDIT_LIST % (item['feature'], item['rule'],
                                        finding)).rstrip())
    return lines


def _proof_tags(proof):
    """` (@manual)`, ` (@env(windows))`, both, or '' for a proof with neither."""
    tags = []
    if proof.get('manual'):
        tags.append('@manual')
    if proof.get('env'):
        tags.append('@env(%s)' % proof['env'])
    return ' (%s)' % ' '.join(tags) if tags else ''


def tied_lines(entry, proof_id, manual=False):
    """Each test tied to a proof, as `file::name`; one line saying there is
    none where no test is tied. A `@manual` proof has no test to name."""
    if manual:
        return []
    lines = [TIED_TO % ('%s::%s' % (test.get('file'), test.get('name')))
             for test in entry.get('tests') or ()
             if test.get('proof') == proof_id]
    return lines or [TIED_TO_NONE]


def result_lines(entry):
    """One line per system: its words, the word its results read, the machine,
    and each proof that found nothing to check, with its reason."""
    chosen = _chosen_results(entry)
    lines = []
    for system in _systems(chosen):
        result = chosen[system]
        line = RESULT % (evidence_module.os_word(system),
                         result.get('result') or 'not run',
                         result.get('machine') or result.get('runner')
                         or 'an unnamed machine')
        for item in result.get('nothing_to_check') or ():
            line += NOTHING % (item.get('proof'), item.get('reason'))
        lines.append(line)
    return lines


def render_stop(stop):
    """One hand check's stop: its head, the rule, each proof with its tests,
    the results on each system, the audit's findings where it found the rule
    weak, and its last note where a sign-off holds one."""
    entry = stop['entry']
    lines = [STOP_HEAD % (stop['feature'], stop['rule']),
             'Rule', '  %s' % (entry.get('text') or ''), 'Proof']
    for proof in entry.get('proofs') or ():
        lines.append('  %s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                     proof.get('text')))
        lines.extend(tied_lines(entry, proof.get('id'),
                                bool(proof.get('manual'))))
    lines.append('Results')
    lines.extend(result_lines(entry))
    if _weak(entry):
        lines.append(AUDIT_WEAK)
        lines.extend('  %s' % finding for finding in
                     (entry.get('audit') or {}).get('findings') or ())
    if stop.get('last_notes'):
        lines.append(LAST_NOTE)
        lines.extend('  %s' % note for note in stop['last_notes'])
    return lines


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

def terminal_ask(_kind, _key, prompt):
    """Read one line from the person at the terminal; the end of input stops."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return None


def _say(lines, out):
    for line in lines:
        print(line, file=out)


def show(project_root, name=None, out=None):
    """`sign.py --show`: the refusal, or what the walk shows, then the next step.
    Asks nothing, writes nothing and needs no key."""
    out = sys.stdout if out is None else out
    lines, code, info = refusal(project_root, name)
    if lines:
        _say(lines, out)
        return code
    shown = plan(info['package'], last_notes(project_root))
    _say(overview_lines(info, shown), out)
    if shown['weak']:
        print(AUDIT_SHOWN % _weak_words(shown['weak']), file=out)
        _say(audit_list_lines(shown['weak']), out)
    for stop in shown['stops']:
        print('', file=out)
        _say(render_stop(stop), out)
    print('', file=out)
    print(SHOW_NEXT, file=out)
    return EXIT_OK


def _weak_words(weak):
    return '%d weak' % len(weak)


def walk(project_root, name=None, ask=None, out=None):
    """The sign-off walk. Returns the exit code.

    `ask(kind, key, prompt)` returns the line given, or None where input
    ended: `kind` is `audit`, `audit_again`, `hand` or `sign`, and `key` is
    `<feature> <RULE-N>` at a hand check. The default reads the terminal.
    Nothing is written until the person says yes to the last question.
    """
    out = sys.stdout if out is None else out
    ask = terminal_ask if ask is None else ask
    lines, code, info = refusal(project_root, name)
    if lines:
        _say(lines, out)
        return code
    if not signing_configured(project_root):
        _say(no_key_lines(), out)
        return EXIT_NOTHING
    return _walk(project_root, info, ask, out)


def _walk(project_root, info, ask, out):
    shown = plan(info['package'], last_notes(project_root))
    _say(overview_lines(info, shown), out)
    list_opened = False
    if shown['weak']:
        given = _choose(ask, 'audit', AUDIT_ASK % _weak_words(shown['weak']),
                        ('list', 'go on'))
        if given == 'list':
            list_opened = True
            _say(audit_list_lines(shown['weak']), out)
            _choose(ask, 'audit_again', AUDIT_AGAIN, ('go on',))
    notes, walked = [], []
    try:
        for stop in shown['stops']:
            print('', file=out)
            _say(render_stop(stop), out)
            notes.append(_at_stop(ask, stop))
            walked.append({'feature': stop['feature'], 'rule': stop['rule']})
    except Stopped as stopped:
        print(STOPPED % (stopped.stop['feature'], stopped.stop['rule']),
              file=out)
        return EXIT_OK
    print('', file=out)
    given = ask('sign', None, SIGN_ASK % (info['version'], info['email']))
    if str(given or '').strip().lower() not in ('y', 'yes'):
        print(NOT_SIGNED, file=out)
        return EXIT_OK
    record = {'overview': shown['overview'],
              'runs': list(info['package'].get('runs') or ()),
              'hand_checks': walked,
              'audit_list_opened': list_opened}
    return _sign(project_root, info, record, notes, out)


def _choose(ask, kind, prompt, answers):
    """One of `answers`, an empty line or the end of input reading as the last."""
    while True:
        given = ask(kind, None, prompt)
        if given is None:
            return answers[-1]
        given = given.strip().lower()
        if not given:
            return answers[-1]
        if given in answers:
            return given


def _at_stop(ask, stop):
    """Ask at one hand check. The note it takes; raises `Stopped` on stop."""
    key = '%s %s' % (stop['feature'], stop['rule'])
    given = ask('hand', key, HAND_ASK % (stop['feature'], stop['rule']))
    if given is None or given.strip().lower() == 'stop':
        raise Stopped(stop)
    return {'feature': stop['feature'], 'rule': stop['rule'],
            'note': given.strip() or NO_NOTE}


# ---------------------------------------------------------------------------
# The sign-off, its commit and the tag
# ---------------------------------------------------------------------------

def signoff_body(project_root, info, record, notes):
    """The sign-off file's fields, in the order the format gives them."""
    return {
        'schema': SCHEMA,
        'version': info['version'],
        'package': signatures_module.package_rel(info['version']),
        'package_hash': info['package'].get('fingerprint'),
        'commit': info['package'].get('commit'),
        'signer': info['email'],
        'signer_name': _git_out(project_root, 'config', '--get',
                                'user.name') or None,
        'key_fingerprint': signatures_module.key_fingerprint(project_root),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'shown': record,
        'notes': notes,
    }


def _read_bytes(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except (IOError, OSError):
        return None


def _take_back(project_root, kept):
    """Leave each file as it was before a commit not made."""
    rels = list(kept)
    subprocess.run(['git', 'reset', '-q', '--'] + rels, capture_output=True,
                   cwd=project_root, timeout=30)
    for rel, earlier in kept.items():
        path = os.path.join(project_root, *rel.split('/'))
        if earlier is None:
            try:
                os.remove(path)
            except OSError:
                pass
        else:
            with open(path, 'wb') as handle:
                handle.write(earlier)


def _commit(project_root, rels, message):
    """Stage `rels` and commit them alone, signed. `(sha, None)` or `(None, why)`."""
    add = _git(project_root, 'add', '--', *rels)
    if add.returncode != 0:
        return None, _first_line(add)
    made = _git(project_root, 'commit', '-q', '-S', '-m', message, '--', *rels)
    if made.returncode != 0:
        return None, _first_line(made)
    return _git_out(project_root, 'rev-parse', 'HEAD') or None, None


def _sign(project_root, info, record, notes, out):
    version, email = info['version'], info['email']
    package = info['package']
    rels = []
    kept = {}
    try:
        if info['written']:
            rel = signatures_module.package_rel(version)
            kept[rel] = _read_bytes(os.path.join(project_root, *rel.split('/')))
            package_module.write(project_root, package)
            rels.append(rel)
    except (package_module.PackageError, IOError, OSError) as error:
        print(NOT_WRITTEN % str(error).rstrip('.'), file=out)
        return EXIT_NOTHING
    rel = signoff_rel(version, email)
    path = os.path.join(project_root, *rel.split('/'))
    try:
        kept[rel] = _read_bytes(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(signoff_body(project_root, info, record, notes), handle,
                      indent=2, ensure_ascii=False)
            handle.write('\n')
    except (IOError, OSError) as error:
        _take_back(project_root, kept)
        print(NOT_WRITTEN % str(error).rstrip('.'), file=out)
        return EXIT_NOTHING
    rels.append(rel)
    sha, why = _commit(project_root, rels, 'sign(%s): %s' % (version, email))
    if not sha:
        _take_back(project_root, kept)
        print(NOT_MADE % why, file=out)
        return EXIT_NOTHING
    key = signatures_module.key_fingerprint(project_root) or ''
    print(SIGNED_AS % (version, email, key[-4:]), file=out)
    tag = info['tag']
    branch = _branch(project_root)
    code = EXIT_OK
    if info['first']:
        ok, said = write_tag(project_root, tag, tag_message(version, package))
        if ok:
            print(TAGGED % (tag, sha[:7]), file=out)
            print(SIGNED_PUSH % ' '.join(part for part in (branch, tag) if part),
                  file=out)
        else:
            print(NO_TAG_GIT % (tag, said), file=out)
            code = EXIT_NOTHING
    else:
        at = _git_out(project_root, 'rev-parse', '%s^{commit}' % tag)
        print(TAG_STAYS % (tag, at[:7], ' ' + branch if branch else ''),
              file=out)
    report_data.refresh(project_root)
    return code


# ---------------------------------------------------------------------------
# The agent's walk
# ---------------------------------------------------------------------------

def read_answers(path):
    """`(answers, None)` from the JSON file, or `(None, why it cannot be read)`."""
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError) as error:
        return None, error.strerror or str(error)
    except (UnicodeDecodeError, ValueError) as error:
        return None, str(error)
    if not isinstance(data, dict):
        return None, 'it holds no JSON object'
    return data, None


def _stop_answer(answers, key):
    given = answers.get('stops')
    one = given.get(key) if isinstance(given, dict) else None
    return one if isinstance(one, dict) else {}


def missing_answer(answers, stops):
    """The first stop, as `<feature> <RULE-N>`, the answers leave unanswered."""
    for stop in stops:
        key = '%s %s' % (stop['feature'], stop['rule'])
        if _stop_answer(answers, key).get('answer') not in ('note', 'stop'):
            return key
    return None


def answers_ask(answers, out):
    """An `ask` that reads the answers file and prints each answer after its question."""
    audit = str(answers.get('audit') or 'go on').strip().lower()

    def ask(kind, key, prompt):
        if kind == 'audit':
            given = 'list' if audit == 'list' else 'go on'
        elif kind == 'audit_again':
            given = 'go on'
        elif kind == 'hand':
            one = _stop_answer(answers, key)
            given = ('stop' if one.get('answer') == 'stop'
                     else str(one.get('note') or ''))
        else:
            given = 'y' if answers.get('sign') is True else 'n'
        print('%s%s' % (prompt, given), file=out)
        return given
    return ask


def walk_with_answers(project_root, path, name=None, out=None):
    """`sign.py --answers FILE`: the walk, answered from the file."""
    out = sys.stdout if out is None else out
    lines, code, info = refusal(project_root, name)
    if lines:
        _say(lines, out)
        return code
    if not signing_configured(project_root):
        _say(no_key_lines(), out)
        return EXIT_NOTHING
    answers, why = read_answers(path)
    if answers is None:
        print(ANSWERS_UNREAD % (path, why), file=out)
        return EXIT_NOTHING
    missing = missing_answer(answers, plan(info['package'])['stops'])
    if missing:
        print(ANSWERS_MISSING % (missing, path, path), file=out)
        return EXIT_NOTHING
    return _walk(project_root, info, answers_ask(answers, out), out)


def check(path, out=None):
    """`sign.py --check FILE`: whether the package matches its fingerprint."""
    out = sys.stdout if out is None else out
    why = package_module.check_file(path)
    if why:
        print(NO_MATCH % why, file=out)
        return EXIT_NOTHING
    print(MATCHES, file=out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('show', 'answers', 'check', 'version', 'project_root',
                 'error', 'help')

    def __init__(self):
        self.show = False
        self.answers = None
        self.check = None
        self.version = None
        self.project_root = '.'
        self.error = None
        self.help = False


_NEEDS = {'--answers': ('answers', '--answers needs the file that holds them.'),
          '--check': ('check', '--check needs the package file to check.'),
          '--version': ('version', '--version needs the version to sign.'),
          '--project-root': ('project_root', '--project-root needs a directory.')}


def _parse(argv):
    """The parsed command line, with `error` or `help` set when it is neither."""
    args = _Args()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ('-h', '--help'):
            args.help = True
            return args
        if item == '--show':
            args.show = True
        elif item in _NEEDS:
            field, why = _NEEDS[item]
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = why
                return args
            setattr(args, field, rest.pop(0))
        elif item.startswith('-'):
            args.error = 'unknown option %s' % item
            return args
        else:
            args.error = 'unexpected argument %s' % item
            return args
    if sum([args.show, args.answers is not None, args.check is not None]) > 1:
        args.error = '--show, --answers and --check are three steps; name one.'
    elif args.check is not None and args.version is not None:
        args.error = '--check reads a file and takes no version.'
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
    if args.check is not None:
        return check(args.check)
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
    if args.show:
        return show(project_root, args.version)
    if args.answers is not None:
        return walk_with_answers(project_root, args.answers, args.version)
    return walk(project_root, args.version)


if __name__ == '__main__':
    sys.exit(main())
