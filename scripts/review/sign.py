#!/usr/bin/env python3
"""Write the signatures a person attests, and commit them signed.

    sign.py [--project-root DIR]
    sign.py <feature> [RULE-N ...] [--batch] [--project-root DIR]
    sign.py <feature> RULE-N [RULE-N ...] --note "<what you checked>"
    sign.py <feature> RULE-N [RULE-N ...] --hold "<the missing case>"

A signature is one named person's attestation that a rule, its proof and its
test belong together. It is one file, so two signatures never conflict:

    specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json

`hash8` is the first eight characters of the triple the signature binds, and
the slug is the signer's email local part, lowercased, with every character
that is not a letter or a digit replaced by `-`. Every file here is a person's:
CI writes no signature, ever.

With no argument this walks the review list one brief at a time. At each stop
the answer is one of four: sign the rule, add a case (a proof line to write
into the spec), hold the rule, or skip it. The walk writes nothing until it
closes, and then it makes one signed commit for the signatures and one per
feature for the holds.

`--note` carries the one line a signer writes where the machine could not
settle the question: a `@manual` proof, or a model review that could not tell.
`--hold` writes the opposite attestation, `<RULE-N>.<hash8>.<holder-slug>.
hold.json`, a person's statement that the test does not prove the proof as
written, with the missing case as its reason. A hold only ever withholds, so
the holder need not be on the signer list; it is committed signed all the same.

`references/formats/signature_format.md` holds the file shape field by field.
The three hashes come from the payload, which is the one place they are
computed, so a signature this script writes is current the moment it lands.

Exit codes: 0 the signatures were written and committed, 1 nothing could be
signed or the commit is not signed, 2 the command line was wrong or the gate
asks for no signature.
"""

import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import (console as console_module,                 # noqa: E402
                    gate as gate_module,
                    payload as payload_module,
                    signatures as signatures_module,
                    specs as specs_module)

SCHEMA = 'purlin-signature/1'
HOLD_SCHEMA = 'purlin-hold/1'
USAGE = ('Usage: sign.py [<feature> [RULE-N ...]] [--batch] [--note TEXT] '
         '[--hold CASE] [--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

# The one-time setup a signer runs, in the order they run it.
SIGNING_SETUP = (
    'git config gpg.format ssh',
    'git config user.signingkey ~/.ssh/id_ed25519.pub',
    'git config commit.gpgsign true',
)

# The four answers the walk takes, and the letters that reach each one.
ANSWERS = ('sign', 'case', 'hold', 'skip')

# Where CI commits the briefs, beside the records and under the same branch
# rule.
BRIEFS_DIR = os.path.join('.purlin', 'briefs')

SIGNER_LIST_MISSING = 'signer list missing: run purlin:init --gate signed'

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
    """`(rule_hash, proof_hash, test_hash, test_hash_kind, design_hash)`.

    R is the rule text with its tags stripped and its whitespace normalised,
    P the proof descriptions in order, T the test files backing them and D the
    pinned design a `origin: design` rule rests on. A rule that is not in the
    payload has no hashes and every element is None.
    """
    entry = rule_entry(load_payload(project_root, payload), feature, rule)
    if entry is None:
        return (None, None, None, None, None)
    return (entry.get('rule_hash'), entry.get('proof_hash'),
            entry.get('test_hash'), entry.get('test_hash_kind'),
            entry.get('design_hash'))


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


def write_signature(project_root, feature, rule, signer_email, brief_path,
                    record_path, gate, risk, payload=None, entry=None,
                    note=None):
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
        'design_hash': entry.get('design_hash'),
        'risk': risk if risk is not None else entry.get('risk'),
        'signer': str(signer_email),
        'note': str(note).strip() if str(note or '').strip() else None,
        'timestamp': payload_module.now_iso(),
        'gate': gate,
        'brief': brief_path,
        'record': record_path,
    }
    _write_json(path, body)
    return os.path.relpath(path, project_root).replace(os.sep, '/')


def brief_for(project_root, feature, rule, triple):
    """The brief CI wrote for this triple, or None when nobody wrote one."""
    rel = '%s/%s/%s.%s.brief.json' % (BRIEFS_DIR.replace(os.sep, '/'), feature,
                                      rule, str(triple)[:8])
    if os.path.isfile(os.path.join(project_root, *rel.split('/'))):
        return rel
    return None


def hold_path(project_root, feature, rule, triple, holder_slug):
    """Where a hold on one rule goes, beside the signatures."""
    path = signature_path(project_root, feature, rule, triple, holder_slug)
    return path[:-len('.json')] + '.hold.json' if path else None


def write_hold(project_root, feature, rule, holder_email, reason, payload=None,
               entry=None):
    """Write one hold and return its project-relative path, or None.

    A hold binds the same hashes a signature does, so it stops standing the
    moment the rule, the proof or the test changes.
    """
    entry = entry or rule_entry(load_payload(project_root, payload), feature,
                                rule)
    if entry is None or not str(reason or '').strip():
        return None
    triple = triple_for(entry)
    path = hold_path(project_root, feature, rule, triple,
                     signatures_module.signer_slug(holder_email))
    if not path:
        return None
    body = {
        'schema': HOLD_SCHEMA,
        'feature': feature,
        'rule': rule,
        'triple': triple[:16],
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'test_hash_kind': entry.get('test_hash_kind'),
        'design_hash': entry.get('design_hash'),
        'risk': entry.get('risk'),
        'holder': str(holder_email),
        'reason': str(reason).strip(),
        'timestamp': payload_module.now_iso(),
        'brief': brief_for(project_root, feature, rule, triple),
    }
    _write_json(path, body)
    return os.path.relpath(path, project_root).replace(os.sep, '/')


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

_RISK_ORDER = {'high': 0, 'medium': 1, 'low': 2}


def signable(payload, feature=None, rules=None):
    """Every `(feature, rule)` whose next step is this person, in risk order.

    A rule is signable when its signed cell reads `unsigned` or `stale`, or
    when its strong cell reads `needs a person`: those are the three words
    that say the machine has gone as far as it can. Everything else is build
    work and stays on the board.
    """
    found = []
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') != entry.get('name'):
                continue
            if feature and item.get('feature') != feature:
                continue
            if rules and item.get('id') not in rules:
                continue
            if not _needs_a_signature(item):
                continue
            found.append((_RISK_ORDER.get(item.get('risk'), 2),
                          item['feature'], _rule_number(item['id']),
                          item['id']))
    found.sort()
    return [(name, rule) for _rank, name, _number, rule in found]


def _needs_a_signature(entry):
    cells = (entry or {}).get('cells') or {}
    signed = cells.get('signed') or {}
    if signed.get('word') in ('unsigned', 'stale'):
        return True
    return (cells.get('strong') or {}).get('word') == 'needs a person'


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


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


def hold_message(targets):
    """The subject for one hold commit, from `commit_conventions.md`."""
    return _subject('hold', targets)


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
                    payload=None):
    """Write every signature in `targets` and commit them once, signed.

    `targets` is `[(feature, rule), ...]`. One invocation is one commit
    whether it carries one rule or forty. Returns the commit sha, or None when
    nothing was written.
    """
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    paths = []
    written = []
    for feature, rule in targets:
        entry = rule_entry(payload, feature, rule)
        if entry is None:
            continue
        triple = triple_for(entry)
        path = write_signature(
            project_root, feature, rule, signer_email,
            brief_for(project_root, feature, rule, triple),
            _latest_record(payload, feature), gate, entry.get('risk'),
            entry=entry, note=note)
        if path:
            paths.append(path)
            written.append((feature, rule))
    if not paths:
        return None
    return _commit(project_root, paths, commit_message(written))


def hold_and_commit(project_root, targets, holder_email, reason, payload=None):
    """Write every hold in `targets` and commit them once, signed."""
    payload = load_payload(project_root, payload)
    paths = []
    written = []
    for feature, rule in targets:
        path = write_hold(project_root, feature, rule, holder_email, reason,
                          payload=payload)
        if path:
            paths.append(path)
            written.append((feature, rule))
    if not paths:
        return None
    return _commit(project_root, paths, hold_message(written))


def _latest_record(payload, feature):
    for entry in (payload or {}).get('features') or ():
        if entry.get('name') == feature:
            return (entry.get('latest_record') or {}).get('path')
    return None


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

def walk(project_root, payload=None, answer=None, out=None, signer_email=None):
    """Walk the review list one brief at a time. Returns what happened.

    `answer` is called once per stop with the rule entry and the rendered
    brief, and returns one of `sign`, `case`, `hold` or `skip`, optionally as
    `(answer, text)` where the text is the case a reviewer wrote or the
    missing case a hold names. The default reads a line from stdin.

    Nothing is written until the walk closes: one signed commit carries the
    signatures, and one more per feature carries the holds. A skipped rule is
    on the list again next time, which is the intended behaviour: nothing is
    marked as seen by being seen.
    """
    out = sys.stdout if out is None else out
    payload = load_payload(project_root, payload)
    answer = _prompt if answer is None else answer
    email = (signer_email or _config(project_root, 'user.email')).lower()

    entries = [rule_entry(payload, row['owner'], row['rule'])
               for row in payload.get('review_list') or ()]
    entries = [entry for entry in entries if entry is not None]
    result = {'rules': len(entries), 'signed': [], 'cases': [], 'held': [],
              'skipped': [], 'commits': []}
    if not entries:
        print('Nothing on the review list needs a person.', file=out)
        return result

    print('Review list: %d rule%s across %d feature%s'
          % (len(entries), '' if len(entries) == 1 else 's',
             len({entry['feature'] for entry in entries}),
             '' if len({entry['feature'] for entry in entries}) == 1 else 's'),
          file=out)

    import brief as brief_module                               # noqa: PLC0415
    holds = {}
    for entry in entries:
        built = brief_module.build_brief(project_root, payload,
                                         entry['feature'], entry['id'])
        rendered = (brief_module.render_brief(built) if built
                    else '%s %s   no brief was written for this triple.'
                    % (entry['feature'], entry['id']))
        print('', file=out)
        print(rendered, file=out)
        given, text = _one_answer(answer, entry, rendered)
        pair = (entry['feature'], entry['id'])
        if given == 'sign':
            result['signed'].append(pair)
        elif given == 'case':
            result['cases'].append((pair, text))
        elif given == 'hold' and str(text or '').strip():
            holds.setdefault(str(text).strip(), []).append(pair)
            result['held'].append(pair)
        else:
            result['skipped'].append(pair)

    if result['signed']:
        sha = sign_and_commit(project_root, result['signed'], email,
                              payload=payload)
        if sha:
            result['commits'].append(sha)
    for reason, targets in sorted(holds.items()):
        sha = hold_and_commit(project_root, targets, email, reason,
                              payload=payload)
        if sha:
            result['commits'].append(sha)

    _close(out, result)
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
    """Read one answer from the person running the walk."""
    try:
        given = input('%s %s   sign / case / hold / skip: '
                      % (entry['feature'], entry['id']))
    except (EOFError, KeyboardInterrupt):
        return 'skip'
    given = given.strip().lower()
    if given.startswith('h') or given.startswith('c'):
        try:
            return given, input('  in one line: ')
        except (EOFError, KeyboardInterrupt):
            return 'skip', None
    return given, None


def _close(out, result):
    print('', file=out)
    print('Walked %d rule%s: %d signed, %d case%s added, %d held, %d skipped.'
          % (result['rules'], '' if result['rules'] == 1 else 's',
             len(result['signed']), len(result['cases']),
             '' if len(result['cases']) == 1 else 's',
             len(result['held']), len(result['skipped'])), file=out)
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

    __slots__ = ('feature', 'rules', 'batch', 'hold', 'note', 'project_root',
                 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rules = []
        self.batch = False
        self.hold = None
        self.note = None
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
        elif item in ('--hold', '--note'):
            need = ('the missing case, in words' if item == '--hold'
                    else 'the line you want on the signature')
            if not rest or not rest[0].strip() or rest[0].startswith('--'):
                args.error = '%s needs %s.' % (item, need)
                return args
            setattr(args, item[2:], rest.pop(0))
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
    for option, value in (('--hold', args.hold), ('--note', args.note)):
        if value is not None and (args.batch or not args.rules):
            args.error = '%s names a feature and the rules it carries.' % option
    return args


def _hold_main(project_root, payload, args):
    """Write and commit the holds one invocation names."""
    email = _config(project_root, 'user.email').lower()
    targets = [(args.feature, rule) for rule in args.rules
               if rule_entry(payload, args.feature, rule) is not None]
    if not targets:
        print('sign: no rule named is in %s.' % args.feature)
        return EXIT_NOTHING
    if not signing_configured(project_root):
        for line in signing_help():
            print(line)
        return EXIT_NOTHING
    sha = hold_and_commit(project_root, targets, email, args.hold,
                          payload=payload)
    if not sha:
        print('sign: the hold commit was not made. Check that signing works '
              'and that the files are not already committed.')
        return EXIT_NOTHING
    print('Held %d rule%s in %s: %s'
          % (len(targets), '' if len(targets) == 1 else 's', sha[:7],
             args.hold.strip()))
    for name, rule in targets:
        print('  %s %s' % (name, rule))
    return EXIT_OK


def _gate_is_too_low(gate):
    """The two lines `passed` prints in place of writing a signature."""
    return ['sign: the gate is %s, which asks for no signature.' % gate,
            'sign: purlin:init --gate strong adds the test strength, the free '
            'checks on the test body, the model review and the review list.']


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

    if args.hold is not None:
        return _hold_main(project_root, payload, args)

    email = _config(project_root, 'user.email').lower()
    signers = gate_fields.get('signers') or []
    if gate == 'signed' and not signers:
        print('sign: %s' % SIGNER_LIST_MISSING)
        return EXIT_NOTHING
    if signers and email not in signers:
        print('sign: %s is not on the signer list. Add it by pull request, or '
              'ask someone on it.' % (email or 'this checkout'))
        return EXIT_NOTHING

    if not signing_configured(project_root):
        for line in signing_help():
            print(line)
        return EXIT_NOTHING

    if args.feature is None and not args.batch:
        walk(project_root, payload, signer_email=email)
        return EXIT_OK

    if args.feature and args.rules:
        targets = [(args.feature, rule) for rule in args.rules
                   if rule_entry(payload, args.feature, rule) is not None]
    else:
        targets = signable(payload, args.feature, None)
    if gate == 'strong' and any(
            not _needs_a_signature(rule_entry(payload, name, rule))
            for name, rule in targets):
        print('sign: a signature is required only under the gate signed. '
              'Writing it anyway.')
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
    print('Signed %d rule%s in %s.'
          % (len(targets), '' if len(targets) == 1 else 's', sha[:7]))
    for name, rule in targets:
        print('  %s %s' % (name, rule))
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
