#!/usr/bin/env python3
"""Sign a release's evidence package, as a signed commit.

    sign.py [--release NAME] [--project-root DIR]
    sign.py --show [--release NAME] [--project-root DIR]
    sign.py --answers FILE [--release NAME] [--project-root DIR]

At the gate `signed`, `purlin:test --release` commits the evidence package
`.purlin/evidence/package/<version>.json` and writes no tag. This command is
the sign-off walk over that package: an overview of the rules, the systems
and what the audit found, then one stop per rule a person has something to
look at, then one question, and on yes one file in one signed commit:

    .purlin/evidence/package/<version>.signoffs/<signer-slug>.json

The file carries the package's `fingerprint`, what the signer was shown and
every note typed; `references/formats/signature_format.md` holds it field by
field. Several people may sign, one file each. The first sign-off of a
version writes the tag `signed/<version>` on its commit, signed; the tag
never moves after it.

**The stops**, in this order, each by feature name then rule number: every
hand check (a rule with a `@manual` proof), where the person types what they
saw; every rule the audit found weak; every rule no audit has read; then the
rules the audit found strong, where the person asked to walk them. At a hand
check the answer is the line seen, or `stop`; at any other stop `continue`,
`note` or `stop`. `stop` writes nothing.

`--show` prints the overview, every stop and the strong list, asks nothing
and writes nothing. `--answers FILE` walks with the answers a JSON file gives,
for an agent whose shell has no terminal to ask in.

**Refusals**, in this order, each one line with nothing written: the gate is
not `signed` (exit 0); the working tree holds changes that are not
committed; no version is stated; no package for the version is committed at
HEAD; a commit after the package's touches anything but that version's
sign-offs; a rule does not pass at HEAD; the branch's copy on the host, as
this checkout last fetched it, holds commits this checkout lacks; the signer
already signed this package; there is no key to sign with. The version is
read as `purlin:test --release` reads it; `--release <name>` names another.
Nothing is fetched and nothing is pushed.

A `.purlin/config.json` that cannot be read stops the command before anything
else is read or written: it prints the sentence saying so and writes nothing.

Exit codes: 0 signed, stopped, answered no, or the gate is `passed`; 1 a
refusal, no key, the commit not made, git could not write the tag, or the
settings file cannot be read; 2 the command line was wrong.
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
import marked_tests                                            # noqa: E402
import release                                                 # noqa: E402
from purlin import report_data                                 # noqa: E402
from purlin import (console as console_module,                 # noqa: E402
                    evidence as evidence_module,
                    gate as gate_module,
                    payload as payload_module,
                    signatures as signatures_module,
                    states as states_module,
                    summary as summary_module)

SCHEMA = 'purlin-signoff/1'
USAGE = ('Usage: sign.py [--show | --answers FILE] [--release NAME] '
         '[--project-root DIR]')

# The refusals, in the order they are read.
AT_PASSED = ('Nothing is signed at the gate passed: purlin:test --release tags '
             'the release unsigned. To sign releases, run purlin:init --gate '
             'signed.')
NO_SIGNOFF_WORK = ('No sign-off: the working tree holds changes that are not '
                   'committed. Commit them, then run purlin:test --release.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:sign '
              '--release <version>, or write it to a VERSION file.')
NO_SIGNOFF_PACKAGE = ('No sign-off: no evidence package for %s is committed at '
                      '%s. Run purlin:test --release.')
NO_SIGNOFF_MOVED = ('No sign-off: the evidence package for %s describes %s, and '
                    '%s has changed since. Run purlin:test --release.')
NO_SIGNOFF_FAILING = ('No sign-off: %s at %s: %s. Run purlin:status to see what '
                      'is left, then purlin:test --release.')
NO_SIGNOFF_BEHIND = ('No sign-off: %s holds %s that %s does not, as this '
                     'checkout last fetched it. Pull, then run purlin:sign.')
ALREADY_SIGNED = '%s has already signed %s over this package; nothing was written.'

# The key a signer signs with, and the commands that set one up.
NO_KEY = 'No key to sign with. These commands set one up:'
DEFAULT_KEY = '~/.ssh/id_ed25519'
KEYGEN = 'ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""'
SIGNING_SETUP = (
    'git config gpg.format ssh',
    'git config user.signingkey ~/.ssh/id_ed25519.pub',
)

# The overview.
OVERVIEW = 'Signing %s: %s, at %s.'
OVERVIEW_RULES = '  %s on %s: %s, %s.'
OVERVIEW_AUDIT = '  The audit: %d strong, %d weak, %d not audited.'
OVERVIEW_STOPS = '  %s: %d hand checks, %d weak, %d not audited.'
NO_STOPS = '  No stops: nothing is checked by hand, weak or not audited.'

# The strong list.
STRONG_ASK = '%s the audit found strong. list / walk / go on: '
STRONG_AGAIN = 'walk / go on: '
STRONG_LIST = '  %s %s'

# A stop.
HAND_CHECK = 'hand check'
WEAK_STOP = 'weak'
NOT_AUDITED = 'not audited'
STRONG_STOP = 'strong'
RESULT = '  %s: %s on %s'
NO_SOURCE = "      the test's source was not found"
HAND_ASK = '%s %s   what did you see, in one line, or stop: '
STOP_ASK = '%s %s   continue / note / stop: '
NOTE_ASK = 'Your note, in one line: '
STOPPED = ('Stopped at %s %s: nothing was signed. After the fix, run '
           'purlin:test --release, then purlin:sign.')

# The signature.
SIGN_ASK = 'Sign the evidence package for %s as %s? [y/N] '
NOT_SIGNED = 'Nothing was signed.'
SIGNED_AS = 'Signed %s as %s with the key ending ...%s.'
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push'
SIGNOFFS = 'Sign-offs of %s: %s.'
NOT_MADE = ('The sign-off commit was not made: %s. Nothing was signed; run '
            'purlin:sign again.')

# The agent's walk.
SHOW_NEXT = 'Answer each stop, then run purlin:sign --answers <file>.'
ANSWERS_MISSING = ('No sign-off: %s has no answer in %s. Answer every stop, '
                   'then run purlin:sign --answers %s again.')
ANSWERS_UNREAD = 'No sign-off: %s cannot be read: %s.'

NOT_A_DIRECTORY = 'sign.py: %s is not a directory.'

# What the audit found, as a stop shows it under `What the audit found`: the
# same words the audit printout and the dashboard give.
NO_AUDIT = "No audit has read this rule's text, proof and test yet."
STRONG_NOTHING = 'Strong. It found nothing.'
STRONG = 'Strong.'
WEAK = 'Weak.'
UNDECIDED = ('Undecided. The AI audit could not decide, so the rule reads '
             'weak until its proof or test changes.')

TIED_TO = '    tied to %s'
TIED_TO_NONE = '    tied to no test'

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

STRONG_ANSWERS = ('list', 'walk', 'go on')
STOP_ANSWERS = ('continue', 'note', 'stop')


class Stopped(Exception):
    """The person stopped the walk at a rule; nothing is written."""

    def __init__(self, stop):
        Exception.__init__(self, '%s %s' % (stop['feature'], stop['rule']))
        self.stop = stop


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git_out(project_root, *args):
    """What a git command prints, stripped, or '' when it fails."""
    try:
        result = subprocess.run(['git'] + list(args), capture_output=True,
                                text=True, cwd=project_root, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return ''
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

def _gate(project_root):
    config = config_engine.resolve_config(project_root)
    return gate_module.resolve_gate(config).gate


def _count(one, many, count):
    return one if count == 1 else many % count


def failing_fill(payload):
    """`(count words, rules)` for what stops a release at HEAD, or None.

    The rules whose work left is in `summary.BLOCKING`, by feature then
    number, as `sample_age RULE-2, RULE-3; stability RULE-1`, then a test
    comment that names nothing, as `1 test comment to correct`.
    """
    named = {}
    for entry in payload.get('features') or ():
        for rule in entry.get('rules') or ():
            if rule.get('feature') != entry.get('name'):
                continue
            if rule.get('left') in summary_module.BLOCKING:
                named.setdefault(entry.get('name'), []).append(rule.get('id'))
    corrections = sum(int(item.get('count') or 0)
                      for item in payload.get('left') or ()
                      if item.get('kind') == 'to_correct')
    if not named and not corrections:
        return None
    count = sum(len(rules) for rules in named.values())
    parts = ['%s %s' % (name, ', '.join(sorted(rules, key=_rule_number)))
             for name, rules in sorted(named.items())]
    if corrections:
        parts.append(_count('1 test comment to correct',
                            '%d test comments to correct', corrections))
    return (_count('1 rule does not pass', '%d rules do not pass', count),
            '; '.join(parts))


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _signer(project_root):
    return _git_out(project_root, 'config', '--get', 'user.email')


def refusal(project_root, name=None):
    """What stands in the way of a sign-off: `(lines, exit, release)`.

    `lines` is empty when nothing does, and `release` then holds what the
    walk reads: `version`, `rel`, `package`, `commit` (the commit that added
    the package) and `email`.
    """
    if _gate(project_root) != gate_module.GATES[-1]:
        return [AT_PASSED], EXIT_OK, None
    if release.uncommitted_work(project_root):
        return [NO_SIGNOFF_WORK], EXIT_NOTHING, None
    version = str(name or '').strip() or release.project_version(project_root)
    if not version:
        return [NO_VERSION], EXIT_NOTHING, None
    head = _git_out(project_root, 'rev-parse', 'HEAD')
    found = release.package_at_head(project_root, version)
    if not found:
        return ([NO_SIGNOFF_PACKAGE % (version, head[:7] or 'HEAD')],
                EXIT_NOTHING, None)
    rel, package = found
    commit = _git_out(project_root, 'log', '-1', '--format=%H', '--', rel)
    if not release.only_signoffs_since(project_root, commit):
        return ([NO_SIGNOFF_MOVED % (version, commit[:7], head[:7])],
                EXIT_NOTHING, None)
    failing = failing_fill(payload_module.build_payload(
        project_root, generated_by='sign'))
    if failing:
        return ([NO_SIGNOFF_FAILING % (failing[0], head[:7], failing[1])],
                EXIT_NOTHING, None)
    behind = release.behind_host(project_root)
    if behind:
        ref, count = behind
        return ([NO_SIGNOFF_BEHIND % (ref, release.behind_words(count),
                                      head[:7])], EXIT_NOTHING, None)
    email = _signer(project_root)
    if already_signed(project_root, version, email, package):
        return [ALREADY_SIGNED % (email, version)], EXIT_NOTHING, None
    if not signing_configured(project_root):
        return no_key_lines(), EXIT_NOTHING, None
    return [], EXIT_OK, {'version': version, 'rel': rel, 'package': package,
                         'commit': commit, 'email': email}


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


def why_of(rule):
    """`hand check`, `weak`, `not audited` or `strong`: why a rule stops.

    A rule with a `@manual` proof is a hand check whatever the audit found.
    Otherwise the word comes from the audit's `verdict` alone, an undecided
    one reading weak as the strong cell reads it.
    """
    if any(proof.get('manual') for proof in rule.get('proofs') or ()):
        return HAND_CHECK
    verdict = (rule.get('audit') or {}).get('verdict')
    if verdict == 'strong':
        return STRONG_STOP
    if verdict:
        return WEAK_STOP
    return NOT_AUDITED


def _passes(rule):
    return ((rule.get('statuses') or {}).get('passed') or {}).get('word') \
        == 'passed'


def plan(package):
    """What the walk shows: the overview's numbers, the stops and the strong list.

    Stops are `{feature, rule, why, entry}`: every hand check, then every
    weak rule, then every rule not audited. `strong` lists the strong rules.
    """
    rules = package_rules(package)
    by_why = {HAND_CHECK: [], WEAK_STOP: [], NOT_AUDITED: [], STRONG_STOP: []}
    systems = set()
    passing = 0
    for feature, rule in rules:
        why = why_of(rule)
        by_why[why].append({'feature': feature, 'rule': rule.get('id'),
                            'why': why, 'entry': rule})
        if why != HAND_CHECK and _passes(rule):
            passing += 1
        for result in rule.get('results') or ():
            if result.get('os'):
                systems.add(result['os'])
    overview = {
        'rules': len(rules), 'passing': passing,
        'hand_checks': len(by_why[HAND_CHECK]),
        'strong': len(by_why[STRONG_STOP]), 'weak': len(by_why[WEAK_STOP]),
        'not_audited': len(by_why[NOT_AUDITED]),
        'systems': [name for name in states_module.SYSTEM_ORDER
                    if name in systems]
        + sorted(name for name in systems
                 if name not in states_module.SYSTEM_ORDER)}
    return {'overview': overview,
            'stops': by_why[HAND_CHECK] + by_why[WEAK_STOP]
            + by_why[NOT_AUDITED],
            'strong': by_why[STRONG_STOP]}


def overview_lines(release_info, shown):
    """The overview: what is signed, the rules and systems, the audit, the stops."""
    overview = shown['overview']
    lines = [OVERVIEW % (release_info['version'], release_info['rel'],
                         release_info['commit'][:7])]
    lines.append(OVERVIEW_RULES % (
        _count('1 rule', '%d rules', overview['rules']),
        states_module.systems_text(overview['systems']) or 'no system',
        _count('1 passes its tests', '%d pass their tests',
               overview['passing']),
        _count('1 is checked by hand', '%d are checked by hand',
               overview['hand_checks'])))
    lines.append(OVERVIEW_AUDIT % (overview['strong'], overview['weak'],
                                   overview['not_audited']))
    stops = (overview['hand_checks'] + overview['weak']
             + overview['not_audited'])
    if stops:
        lines.append(OVERVIEW_STOPS % (_count('1 stop', '%d stops', stops),
                                       overview['hand_checks'],
                                       overview['weak'],
                                       overview['not_audited']))
    else:
        lines.append(NO_STOPS)
    return lines


def strong_list_lines(strong):
    """One line per feature: the feature, then its strong rules joined ', '."""
    features = {}
    for stop in strong:
        features.setdefault(stop['feature'], []).append(stop['rule'])
    return [STRONG_LIST % (name, ', '.join(rules))
            for name, rules in sorted(features.items())]


def _proof_tags(proof):
    """` (@manual)`, ` (@env(windows))`, both, or '' for a proof with neither."""
    tags = []
    if proof.get('manual'):
        tags.append('@manual')
    if proof.get('env'):
        tags.append('@env(%s)' % proof['env'])
    return ' (%s)' % ' '.join(tags) if tags else ''


def audit_lines(entry):
    """What the audit found for one rule, one line each, indented two spaces.

    `Strong. It found nothing.`, or `Strong.`, `Weak.` or the undecided
    sentence followed by each finding on a line of its own, or that no audit
    has read the rule yet. It names no reader.
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


def tied_lines(project_root, feature, entry, proof_id, manual=False):
    """Each test tied to a proof, as `file::name`, with its body six spaces in.

    One line saying there is none where no test is tied. A `@manual` proof
    has no test to name, so it has none.
    """
    if manual:
        return []
    lines = []
    for test in entry.get('tests') or ():
        if test.get('proof') != proof_id:
            continue
        lines.append(TIED_TO % ('%s::%s' % (test.get('file'), test.get('name'))))
        body = marked_tests.source(project_root, feature, proof_id,
                                   test.get('file'), test.get('name'))
        if body:
            lines.extend('      %s' % line if line.strip() else ''
                         for line in body.rstrip('\n').splitlines())
        else:
            lines.append(NO_SOURCE)
    return lines or [TIED_TO_NONE]


def result_lines(entry):
    """One line per system: its words, the word its results read, the machine.

    Where a system has results from both sources, a current one is read
    before one that is not, and the source's own order breaks a tie.
    """
    chosen = {}
    for result in entry.get('results') or ():
        system = result.get('os')
        if not system:
            continue
        rank = (not result.get('current'), result.get('source') != 'ci')
        if system not in chosen or rank < chosen[system][0]:
            chosen[system] = (rank, result)
    lines = []
    for system in states_module.SYSTEM_ORDER + tuple(
            sorted(name for name in chosen
                   if name not in states_module.SYSTEM_ORDER)):
        if system not in chosen:
            continue
        result = chosen[system][1]
        lines.append(RESULT % (evidence_module.os_word(system),
                               result.get('result') or 'not run',
                               result.get('machine') or result.get('runner')
                               or 'an unnamed machine'))
    return lines


def render_stop(project_root, stop):
    """One stop: its head, the rule, each proof with its tests, the results
    and what the audit found. A hand check shows the rule and its proofs."""
    entry = stop['entry']
    feature = stop['feature']
    lines = ['%s %s   %s' % (feature, stop['rule'], stop['why']),
             'Rule', '  %s' % (entry.get('text') or ''), 'Proof']
    for proof in entry.get('proofs') or ():
        lines.append('  %s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                     proof.get('text')))
        lines.extend(tied_lines(project_root, feature, entry, proof.get('id'),
                                bool(proof.get('manual'))))
    if any(test.get('proof') == stop['rule']
           for test in entry.get('tests') or ()):
        lines.extend(tied_lines(project_root, feature, entry, stop['rule']))
    if stop['why'] == HAND_CHECK:
        return lines
    lines.append('Results')
    lines.extend(result_lines(entry))
    lines.append('What the audit found')
    lines.extend(audit_lines(entry))
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


def show(project_root, name=None, out=None):
    """`sign.py --show`: the refusal, or the overview, every stop and the
    strong list, then the next step. Asks nothing and writes nothing."""
    out = sys.stdout if out is None else out
    lines, code, info = refusal(project_root, name)
    if lines:
        for line in lines:
            print(line, file=out)
        return code
    shown = plan(info['package'])
    for line in overview_lines(info, shown):
        print(line, file=out)
    for stop in shown['stops']:
        print('', file=out)
        for line in render_stop(project_root, stop):
            print(line, file=out)
    if shown['strong']:
        print('', file=out)
        print((STRONG_ASK % _count('1 rule', '%d rules',
                                   len(shown['strong']))).rstrip(), file=out)
        for line in strong_list_lines(shown['strong']):
            print(line, file=out)
    print('', file=out)
    print(SHOW_NEXT, file=out)
    return EXIT_OK


def walk(project_root, name=None, ask=None, out=None):
    """The sign-off walk. Returns the exit code.

    `ask(kind, key, prompt)` returns the line given, or None where input
    ended: `kind` is `strong`, `strong_again`, `hand`, `stop`, `note` or
    `sign`, and `key` is `<feature> <RULE-N>` at a stop. The default reads
    the terminal. Nothing is written until the person says yes to the last
    question; then one file goes in one signed commit.
    """
    out = sys.stdout if out is None else out
    ask = terminal_ask if ask is None else ask
    lines, code, info = refusal(project_root, name)
    if lines:
        for line in lines:
            print(line, file=out)
        return code
    return _walk(project_root, info, ask, out)


def _walk(project_root, info, ask, out):
    shown = plan(info['package'])
    for line in overview_lines(info, shown):
        print(line, file=out)
    stops = list(shown['stops'])
    in_list = list(shown['strong'])
    list_opened = False
    if in_list:
        print('', file=out)
        given = _choose(ask, 'strong', STRONG_ASK % _count(
            '1 rule', '%d rules', len(in_list)), STRONG_ANSWERS)
        if given == 'list':
            list_opened = True
            for line in strong_list_lines(in_list):
                print(line, file=out)
            given = _choose(ask, 'strong_again', STRONG_AGAIN,
                            STRONG_ANSWERS[1:])
        if given == 'walk':
            stops.extend(in_list)
            in_list = []
    notes = []
    try:
        for stop in stops:
            print('', file=out)
            for line in render_stop(project_root, stop):
                print(line, file=out)
            note = _at_stop(ask, stop)
            if note:
                notes.append(note)
    except Stopped as stopped:
        print(STOPPED % (stopped.stop['feature'], stopped.stop['rule']),
              file=out)
        return EXIT_OK
    print('', file=out)
    given = ask('sign', None, SIGN_ASK % (info['version'], info['email']))
    if str(given or '').strip().lower() not in ('y', 'yes'):
        print(NOT_SIGNED, file=out)
        return EXIT_OK
    record = {
        'overview': shown['overview'],
        'one_by_one': [{'feature': stop['feature'], 'rule': stop['rule'],
                        'why': stop['why']} for stop in stops],
        'in_list': [{'feature': stop['feature'], 'rule': stop['rule']}
                    for stop in in_list],
        'list_opened': list_opened}
    return _sign(project_root, info, record, notes, out)


def _choose(ask, kind, prompt, answers):
    """One of `answers`, an empty line reading as the last; asked again otherwise."""
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
    """Ask at one stop. The note it takes, or None; raises `Stopped` on stop."""
    key = '%s %s' % (stop['feature'], stop['rule'])
    if stop['why'] == HAND_CHECK:
        while True:
            given = ask('hand', key, HAND_ASK % (stop['feature'], stop['rule']))
            if given is None or given.strip().lower() == 'stop':
                raise Stopped(stop)
            if given.strip():
                return {'feature': stop['feature'], 'rule': stop['rule'],
                        'kind': HAND_CHECK, 'note': given.strip()}
    while True:
        given = ask('stop', key, STOP_ASK % (stop['feature'], stop['rule']))
        if given is None:
            raise Stopped(stop)
        given = given.strip().lower()
        if given == 'stop':
            raise Stopped(stop)
        if given == 'continue':
            return None
        if given == 'note':
            line = ask('note', key, NOTE_ASK)
            if line is None:
                raise Stopped(stop)
            if not line.strip():
                return None
            return {'feature': stop['feature'], 'rule': stop['rule'],
                    'kind': 'note', 'note': line.strip()}


# ---------------------------------------------------------------------------
# The sign-off, its commit and the tag
# ---------------------------------------------------------------------------

def signoff_body(project_root, info, record, notes):
    """The sign-off file's fields, in the order the format gives them."""
    return {
        'schema': SCHEMA,
        'version': info['version'],
        'package': info['rel'],
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


def _commit(project_root, rel, message):
    """Stage `rel` and commit it alone, signed. `(sha, None)` or `(None, why)`."""
    add = subprocess.run(['git', 'add', '--', rel], capture_output=True,
                         text=True, cwd=project_root, timeout=30)
    if add.returncode != 0:
        return None, _first_line(add)
    made = subprocess.run(['git', 'commit', '-q', '-S', '-m', message, '--',
                           rel], capture_output=True, text=True,
                          cwd=project_root, timeout=60)
    if made.returncode != 0:
        return None, _first_line(made)
    return _git_out(project_root, 'rev-parse', 'HEAD') or None, None


def _take_back(project_root, rel, earlier):
    """Leave the sign-off file as HEAD holds it after a commit not made."""
    subprocess.run(['git', 'reset', '-q', '--', rel], capture_output=True,
                   cwd=project_root, timeout=30)
    path = os.path.join(project_root, *rel.split('/'))
    if earlier is None:
        try:
            os.remove(path)
        except OSError:
            pass
    else:
        with open(path, 'wb') as handle:
            handle.write(earlier)


def tag_message(package):
    """What the tag says: the gate, and the commit the package describes."""
    gate = gate_module.GATES[-1]
    return ('Released at the gate %s.\n\nCommit: %s\nGate: %s\n'
            % (gate, package.get('commit') or 'unknown', gate))


def _sign(project_root, info, record, notes, out):
    version, email = info['version'], info['email']
    rel = signoff_rel(version, email)
    path = os.path.join(project_root, *rel.split('/'))
    earlier = None
    if os.path.exists(path):
        with open(path, 'rb') as handle:
            earlier = handle.read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(signoff_body(project_root, info, record, notes), handle,
                  indent=2, ensure_ascii=False)
        handle.write('\n')
    sha, why = _commit(project_root, rel, 'sign(%s): %s' % (version, email))
    if not sha:
        _take_back(project_root, rel, earlier)
        print(NOT_MADE % why, file=out)
        return EXIT_NOTHING
    key = signatures_module.key_fingerprint(project_root) or ''
    print(SIGNED_AS % (version, email, key[-4:]), file=out)
    tag = release.tag_name(gate_module.GATES[-1], version)
    code = EXIT_OK
    if release.tag_exists(project_root, tag):
        at = _git_out(project_root, 'rev-parse', '%s^{commit}' % tag)
        print(TAG_STAYS % (tag, at[:7]), file=out)
    else:
        ok, said = release.write_tag(project_root, tag,
                                     tag_message(info['package']), True)
        if ok:
            print(release.TAGGED % (tag, sha[:7]), file=out)
            print(summary_module.RELEASE % tag, file=out)
        else:
            print(release.NO_TAG_GIT % (tag, said), file=out)
            code = EXIT_NOTHING
    signers = [item.get('signer') for item in
               signatures_module.load_signoffs(project_root, version)]
    print(SIGNOFFS % (version, ', '.join(str(item) for item in signers)),
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


def missing_answer(answers, stops):
    """The first stop, as `<feature> <RULE-N>`, the answers leave unanswered."""
    given = answers.get('stops')
    given = given if isinstance(given, dict) else {}
    for stop in stops:
        key = '%s %s' % (stop['feature'], stop['rule'])
        one = given.get(key)
        word = one.get('answer') if isinstance(one, dict) else None
        note = str((one or {}).get('note') or '').strip() \
            if isinstance(one, dict) else ''
        if stop['why'] == HAND_CHECK:
            if word == 'stop' or (word == 'note' and note):
                continue
        elif word in STOP_ANSWERS:
            continue
        return key
    return None


def answers_ask(answers, out):
    """An `ask` that reads the answers file and prints each answer after its question."""
    stops = answers.get('stops') if isinstance(answers.get('stops'),
                                               dict) else {}
    strong = str(answers.get('strong') or 'go on').strip().lower()

    def ask(kind, key, prompt):
        one = stops.get(key) if key else None
        one = one if isinstance(one, dict) else {}
        if kind == 'strong':
            given = strong
        elif kind == 'strong_again':
            given = 'walk' if strong == 'walk' else 'go on'
        elif kind == 'hand':
            given = ('stop' if one.get('answer') == 'stop'
                     else str(one.get('note') or ''))
        elif kind == 'stop':
            given = str(one.get('answer') or '')
        elif kind == 'note':
            given = str(one.get('note') or '')
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
        for line in lines:
            print(line, file=out)
        return code
    answers, why = read_answers(path)
    if answers is None:
        print(ANSWERS_UNREAD % (path, why), file=out)
        return EXIT_NOTHING
    shown = plan(info['package'])
    stops = list(shown['stops'])
    if str(answers.get('strong') or '').strip().lower() == 'walk':
        stops.extend(shown['strong'])
    missing = missing_answer(answers, stops)
    if missing:
        print(ANSWERS_MISSING % (missing, path, path), file=out)
        return EXIT_NOTHING
    return _walk(project_root, info, answers_ask(answers, out), out)


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('show', 'answers', 'release', 'project_root', 'error', 'help')

    def __init__(self):
        self.show = False
        self.answers = None
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
        if item == '--show':
            args.show = True
        elif item == '--answers':
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = '--answers needs the file that holds them.'
                return args
            args.answers = rest.pop(0)
        elif item == '--release':
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = '--release needs the version to sign.'
                return args
            args.release = rest.pop(0)
        elif item == '--project-root':
            if not rest:
                args.error = '--project-root needs a directory.'
                return args
            args.project_root = rest.pop(0)
        elif item.startswith('-'):
            args.error = 'unknown option %s' % item
            return args
        else:
            args.error = 'unexpected argument %s' % item
            return args
    if args.show and args.answers is not None:
        args.error = '--show and --answers are two steps; name one.'
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
    if args.show:
        return show(project_root, args.release)
    if args.answers is not None:
        return walk_with_answers(project_root, args.answers, args.release)
    return walk(project_root, args.release)


if __name__ == '__main__':
    sys.exit(main())
