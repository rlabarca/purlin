"""The audit's run: the spot tests, the model's request for each rule, the planted bugs.

`purlin_run.py --audit` runs the tests, then calls `run`. For the rules the
audit reads (`ai_audit.is_read`, ai_audit RULE-1) it runs, in this order:

1. the heuristic spot tests over each test tied to each rule's proofs
   (`plain_checks.check`), with no model;
2. one model call per rule, four at once (`ai_audit.audit_all`), whose reply
   holds a planted bug for each proof that needs one, aimed past that proof's
   test, with the case the model says it breaks, and the model's reading,
   which becomes the explanation and sets no verdict;
3. each bug planted in a copy of the project and its proof's own test run
   (`targeted_break.break_proof`), one at a time. No bug is asked for an
   anchor's rule, a `@manual` proof or a proof tagged for a system this
   machine is not; a proof whose `break_key` is unchanged keeps its last
   result (ai_audit RULE-36).

A rule reads `weak` when a spot test fires on one of its tests or a planted
bug survived, which adds the change and the model's case to its findings
(ai_audit RULE-49), else `strong` when a planted bug was caught, else `spot-checked`
(ai_audit RULE-33). Each entry records under `no_bug` one sentence for each
proof no bug was caught for. One `audit.rules` entry per rule read is written
through `evidence.write_audit`, with the feature's `code` part as `code_hash`.

Where the model could not be reached for a rule, the spot tests and the bugs
kept from earlier audits set its verdict, one line says so and names
`purlin:audit`, and the next audit reads the rule again (ai_audit RULE-43).
The run prints each rule it read with its findings and, last, the share of
rules found strong (ai_audit RULE-35).

`purlin:audit <feature> RULE-N --settle` settles the rules it names and reads
no other (`settle`). Each bug the rule's entry keeps as `survived` is planted
again, with no model asked, and its proof's tests run as they stand now
(`replayed`). A test that fails makes the entry `caught`. A test that still
passes drops the bug, and one new bug is asked for that proof in the usual
request: a second survivor leaves no bug on record, the proof `not made` with
`TWO_SURVIVED`. A recorded change that can no longer be planted is asked for
anew, as any audit asks. `references/review_criteria.md`, "Settling a finding",
is the one home of that contract.

A project file that changes between the first model call and the last planted
bug stops the run before anything is written (planted_bug RULE-6).
"""

import hashlib
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'), os.path.join(_SCRIPTS, 'run'),
              _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import ai_audit                                               # noqa: E402
import evidence as evidence_writer                            # noqa: E402
import plain_checks                                           # noqa: E402
import targeted_break                                         # noqa: E402
from purlin import evidence as evidence_reader                 # noqa: E402
from purlin import fingerprint as fingerprint_module           # noqa: E402
from purlin import payload as payload_module                   # noqa: E402
from purlin import specs as specs_module                       # noqa: E402
from purlin import summary as summary_module                   # noqa: E402

# The last line where no rule passes, and the line before the last where the
# model could not be reached.
NO_RULE_PASSES = 'The audit found no rule that passes its tests.'
NOT_REACHED = 'The model could not be reached: %s.%s Run purlin:audit again.'
ALONE_ONE = ' 1 rule is spot-checked alone.'
ALONE_MANY = ' %d rules are spot-checked alone.'

# What a rule read prints: its name and verdict, then one line per finding
# and per `no_bug` sentence.
RULE_LINE = '%s %s   %s'
FINDING_LINE = '  %s'

# The sentences of `no_bug`, one for each proof no bug was caught for.
NO_BUG = 'No bug was planted: %s.'
MODEL_FOUND_NONE = 'the model found no change that would break %s: %s'   # PROOF-N, its reason
ANSWER_UNUSABLE = "the model's answer for %s could not be used: %s"     # PROOF-N, what was wrong
BASELINE = 'the test of %s does not pass in a copy of the project'       # PROOF-N
UNREACHED = 'the model could not be reached: %s'                         # ai_audit's reason
ANCHOR = "no bug is planted for an anchor's rule"
OTHER_SYSTEM = '%s needs %s, and this machine is %s'                     # PROOF-N, Windows, macOS
NOT_RUN = 'A bug was planted for %s and its test did not run.'           # a whole sentence
ERRORED = 'A bug was planted for %s and its test ended in an error, not a failure.'
NO_PART = targeted_break.NO_PART

# Settling a rule. The first three are printed under the rule and not stored:
# PROOF-N, the kept bug's file and line. The reason and its sentence are what a
# proof holds once two planted bugs left its test passing.
NOW_CATCHES = '%s: the test now catches the bug it missed at %s:%d.'
DROPPED = '%s: the bug at %s:%d did not break what the proof says.'
NEW_BUG_PLANTED = ' A new bug was planted.'
NOTHING_TO_SETTLE = ('%s %s has no planted bug that survived: nothing to '
                     'settle.')
TWO_SURVIVED = "two planted bugs left the proof's check passing"
NO_BUG_CAUGHT = 'No bug was caught for %s: %s.'       # PROOF-N, TWO_SURVIVED
SPOT_CHECKED = ai_audit.SPOT_CHECKED   # the `no_bug` sentences joined by one space

# The language a test file is read in, for a spot test that cannot read it.
LANGUAGES = (
    (('.sh', '.bash', '.bats'), 'shell'), (('.sql',), 'SQL'),
    (('.py',), 'Python'), (('.js', '.jsx', '.mjs', '.cjs'), 'JavaScript'),
    (('.ts', '.tsx', '.mts', '.cts'), 'TypeScript'), (('.cs',), 'C#'),
    (('.go',), 'Go'),
)


def _git(project_root, *args):
    return subprocess.run(['git'] + list(args), cwd=project_root,
                          capture_output=True, text=True)


def head_commit(project_root):
    """The full sha of HEAD, or '' outside a repository with a commit."""
    found = _git(project_root, 'rev-parse', 'HEAD')
    return found.stdout.strip() if found.returncode == 0 else ''


def language_of(path):
    """The language word a spot test that cannot read a file names."""
    ext = os.path.splitext(str(path or ''))[1].lower()
    for endings, word in LANGUAGES:
        if ext in endings:
            return word
    return ext.lstrip('.') or 'these'


# ---------------------------------------------------------------------------
# Which rules are read
# ---------------------------------------------------------------------------

def _code_part(project_root, features, feature, cache):
    """The `code` part of a feature's fingerprint, taken once a run."""
    if feature not in cache:
        cache[feature] = fingerprint_module.code_part(
            project_root, features.get(feature) or {}, cache.setdefault(
                None, {}))
    return cache[feature]


def audit_entry(project_root, feature, rule, code_part):
    """The rule's audit entry as the evidence holds it, a current one before
    one out of date, with `out_of_date`; or {}."""
    return evidence_reader.audit_entry(
        evidence_reader.load(project_root, feature), rule.get('id'),
        rule.get('rule_hash'), rule.get('proof_hash'), rule.get('test_hash'),
        code_part) or {}


def rules_to_read(project_root, payload, features, selected, again=False,
                  cache=None):
    """`[(feature, rule entry)]` the audit reads, by feature then rule number.

    A rule is its feature's own (an anchor's rules are read once, as the
    anchor's), and `ai_audit.is_read` says whether it is read.
    """
    cache = {} if cache is None else cache
    found = []
    for feature in payload.get('features') or ():
        name = feature.get('name')
        if name not in selected:
            continue
        anchor = bool((features.get(name) or {}).get('is_anchor'))
        for rule in feature.get('rules') or ():
            if rule.get('feature') != name:
                continue
            if not (ai_audit.passes(rule) and ai_audit.tested(rule)):
                continue
            entry = {} if again else audit_entry(
                project_root, name, rule,
                _code_part(project_root, features, name, cache))
            if ai_audit.is_read(rule, again=again, audit=entry,
                                plant=ai_audit.plants_for(rule, anchor)):
                found.append((name, rule))
    found.sort(key=lambda pair: (pair[0], _number(pair[1].get('id'))))
    return found


def counted_rules(payload, selected):
    """`[(feature, rule entry)]` for each rule of a selected feature that
    passes its tests and has a tested proof."""
    return [(feature.get('name'), rule)
            for feature in payload.get('features') or ()
            if feature.get('name') in selected
            for rule in feature.get('rules') or ()
            if rule.get('feature') == feature.get('name')
            and ai_audit.passes(rule) and ai_audit.tested(rule)]


def _number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


# ---------------------------------------------------------------------------
# One rule
# ---------------------------------------------------------------------------

def _sha256(text):
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def test_source_hash(tests):
    """The sha256 of the sorted lines `<file> <name> <sha256 of its source>`."""
    return _sha256('\n'.join(sorted(
        '%s %s %s' % (test.get('file'), test.get('name'),
                      _sha256(test.get('source') or ''))
        for test in tests)))


def _proof_tests(reading, proof_id):
    return [{'file': test.get('file'), 'name': test.get('name'),
             'source': test.get('body')}
            for test in reading.get('tests') or ()
            if test.get('proof') == proof_id and not test.get('manual')
            and test.get('file')]


def spot_tests(project_root, reading, not_read, not_found=None):
    """The spot tests' findings for one rule, in order and once each.
    `not_read` gains `(check, language)` for each check a test's language
    cannot be read for, and `not_found`, a list, `(file, name)` once for each
    marked test whose source was not found, which no check reads."""
    findings = []
    texts = {proof['id']: proof.get('text') for proof in reading['proofs']}
    for test in reading.get('tests') or ():
        if test.get('manual') or not test.get('file'):
            continue
        if test.get('body') is None:
            named = (test['file'], test.get('name'))
            if not_found is not None and named not in not_found:
                not_found.append(named)
            continue
        found = plain_checks.check(
            project_root, reading['feature'],
            {'id': test['proof'], 'text': texts.get(test['proof'])},
            {'file': test['file'], 'name': test['name'],
             'source': test['body']})
        for check, finding in found or ():
            if finding is None:
                not_read.add((check, language_of(test['file'])))
            elif finding not in findings:
                findings.append(finding)
    return findings


def _survived_finding(proof_id, kept, last):
    """The finding a kept `survived` result carries, as its entry wrote it."""
    start = '%s: the test still passes when' % proof_id
    for line in last.get('findings') or ():
        if str(line).startswith(start):
            return line
    changed = (str(kept.get('after') or '').strip().splitlines() or [''])[0]
    return targeted_break.SURVIVED % (proof_id, kept.get('file'),
                                      kept.get('line') or 0, changed.strip())


def survived_findings(proof_id, made, last, finding=None):
    """The findings of a bug that survived, in order: the change the test
    still passes with, `finding` or the line the entry `made` rebuilds, then,
    where the entry holds a case, what the model says the bug breaks."""
    found = [finding or _survived_finding(proof_id, made, last)]
    case = str(made.get('case') or '').strip()
    if case:
        found.append(targeted_break.AI_SAYS % (proof_id, case))
    return found


def bug_plan(reading, last, code_part, here=None, settle=False):
    """`[(proof, what, value)]` for each proof of the rule that has a test and
    is not checked by hand, in the spec's order. `what` is `anchor` for an
    anchor's rule; `system`, with the system the proof is tagged for, where
    this machine is another; `kept`, with the last result, where the proof's
    `break_key` is unchanged; else `plant`, with the key its result will
    carry.

    Under `settle` a proof whose last result reads `survived` is `replay`,
    with that result and the key, whatever its `break_key`; any other proof
    keeps what it has, `kept` with its last result, and a proof with no
    result on record is left out."""
    here = here or evidence_reader.host_os()
    kept_breaks = last.get('breaks') if isinstance(last.get('breaks'),
                                                   dict) else {}
    plan = []
    for proof in reading.get('proofs') or ():
        if proof.get('manual'):
            continue
        tests = _proof_tests(reading, proof['id'])
        if not tests:
            continue
        if reading.get('anchor'):
            plan.append((proof['id'], 'anchor', None))
            continue
        if proof.get('env') and proof['env'] != here:
            plan.append((proof['id'], 'system', proof['env']))
            continue
        key = ai_audit.break_key(test_source_hash(tests), code_part)
        kept = kept_breaks.get(proof['id'])
        if settle:
            if isinstance(kept, dict) and kept.get('result') == 'survived':
                plan.append((proof['id'], 'replay', (kept, key)))
            elif isinstance(kept, dict):
                plan.append((proof['id'], 'kept', kept))
            continue
        if isinstance(kept, dict) and kept.get('break_key') == key:
            plan.append((proof['id'], 'kept', kept))
        else:
            plan.append((proof['id'], 'plant', key))
    return plan


def no_bug_sentence(proof_id, made, cause=None, last=None):
    """The sentence of `no_bug` for one planted bug's result, or None where
    the bug was caught or survived. A `not made` result is worded by where
    its reason came from: `cause` is `targeted_break`'s for a bug this audit
    asked for; for a result kept from an earlier audit it is the sentence
    that audit wrote, found under `no_bug` of `last`, its entry. Only an
    entry that holds no such sentence is read by the words of its reason."""
    result = made.get('result')
    if result == 'not run':
        if made.get('why') == targeted_break.ERRORED:
            return ERRORED % proof_id
        return NOT_RUN % proof_id
    if result != 'not made':
        return None
    why = str(made.get('why') or '').rstrip('.')
    worded = {
        targeted_break.TEST_DOES_NOT_PASS: NO_BUG % (BASELINE % proof_id),
        targeted_break.ANSWER_UNUSABLE: NO_BUG % (ANSWER_UNUSABLE % (proof_id, why)),
        targeted_break.MODEL_FOUND_NONE: NO_BUG % (MODEL_FOUND_NONE % (proof_id, why)),
    }
    if cause not in worded:
        written = [str(line) for line in (last or {}).get('no_bug') or ()]
        two = [NO_BUG_CAUGHT % (proof_id, TWO_SURVIVED)] * (why == TWO_SURVIVED)
        for sentence in two + list(worded.values()):
            if sentence in written:
                return sentence
        if two:
            return two[0]
        cause = targeted_break.cause_of(why)
    return worded[cause]


def replayed(project_root, reading, plan, scope_files):
    """`(plan, said)` for a rule being settled, once each bug its entry keeps
    as `survived` has been planted again and its proof's tests run as they
    stand. No model is asked. In the plan handed back each `replay` reads:

    `kept`     the test failed, so the bug's entry reads `caught`, with the
               change as it was recorded and the key of the test and code
               now; or the test did not run, and the entry reads `not run`
    `second`   the test still passes: the bug is dropped, and one new bug is
               to be asked for, with the key and the line that says so
    `plant`    the recorded change can no longer be planted: a new bug is to
               be asked for, as any audit asks

    `said` is `{proof: line}`, what the audit prints under the rule."""
    settled, said = [], {}
    for proof_id, what, value in plan:
        if what != 'replay':
            settled.append((proof_id, what, value))
            continue
        kept, key = value
        result = targeted_break.replay(
            project_root, reading['feature'], proof_id,
            _proof_tests(reading, proof_id), scope_files, kept)
        place = (proof_id, kept.get('file'), kept.get('line') or 0)
        ran = result.get('result')
        if ran in ('caught', 'not run'):
            settled.append((proof_id, 'kept', dict(
                kept, aim=kept.get('aim') or targeted_break.PLAIN,
                case=kept.get('case') or '', result=ran,
                why=result.get('why') or '', break_key=key)))
            if ran == 'caught':
                said[proof_id] = NOW_CATCHES % place
        elif ran == 'survived':
            settled.append((proof_id, 'second', (key, DROPPED % place)))
        else:
            settled.append((proof_id, 'plant', key))
    return settled, said


def planted_bugs(project_root, reading, plan, scope_files, last, answer,
                 here=None, said=None):
    """`(breaks, findings, no_bug)` for one rule's proofs.

    `plan` is `bug_plan`'s and `answer` the model's one reply for the rule,
    as `ai_audit.audit_one` gives it. `breaks` is `{proof: entry}` as the
    evidence holds it, each with its `aim` and `case`; `findings` the two
    sentences of each bug that survived, the change and the case the model
    says it breaks;
    `no_bug` one sentence for each proof no bug was caught for. A proof the
    model could not be reached for, or that is tagged for another system, has
    no entry under `breaks`, so the first is asked for again.

    A `second` proof of the plan is one whose kept bug a settle dropped: its
    new bug is planted as any is, and one that survives too is not kept, the
    entry reading `not made` with `TWO_SURVIVED`. `said`, a dict, gains the
    line the audit prints for it.
    """
    here = here or evidence_reader.host_os()
    breaks, findings, no_bug = {}, [], []
    said = {} if said is None else said

    def note(sentence):
        if sentence and sentence not in no_bug:
            no_bug.append(sentence)

    parts = answer.get('parts') or {}
    for proof_id, what, value in plan:
        if what == 'anchor':
            note(NO_BUG % ANCHOR)
        elif what == 'system':
            note(NO_BUG % (OTHER_SYSTEM % (
                proof_id, evidence_reader.os_word(value),
                evidence_reader.os_word(here))))
        elif what == 'kept':
            # An entry written before the aim and the case were kept gains both.
            value = dict(value, aim=value.get('aim') or targeted_break.PLAIN,
                         case=value.get('case') or '')
            breaks[proof_id] = value
            if value.get('result') == 'survived':
                findings.extend(survived_findings(proof_id, value, last))
            note(no_bug_sentence(proof_id, value, last=last))
        elif answer.get('why'):
            if what == 'second':
                said[proof_id] = value[1]
            note(NO_BUG % (UNREACHED % answer['why']))
        else:
            key, dropped = value if what == 'second' else (value, None)
            result = targeted_break.break_proof(
                project_root, reading['feature'], proof_id,
                _proof_tests(reading, proof_id), scope_files,
                parts.get(proof_id))
            entry = {'aim': result.get('aim') or targeted_break.PLAIN,
                     'case': result.get('case') or '',
                     'file': result.get('file'), 'line': result.get('line'),
                     'before': result.get('before'),
                     'after': result.get('after'),
                     'result': result.get('result') or 'not made',
                     'why': result.get('why') or '', 'break_key': key}
            if dropped:
                said[proof_id] = dropped + (
                    '' if entry['result'] == 'not made' else NEW_BUG_PLANTED)
                if entry['result'] == 'survived':
                    # Two bugs left the test passing: neither is kept.
                    breaks[proof_id] = {
                        'aim': targeted_break.PLAIN, 'case': '', 'file': None,
                        'line': None, 'before': None, 'after': None,
                        'result': 'not made', 'why': TWO_SURVIVED,
                        'break_key': key}
                    note(NO_BUG_CAUGHT % (proof_id, TWO_SURVIVED))
                    continue
            breaks[proof_id] = entry
            if entry['result'] == 'survived':
                findings.extend(survived_findings(proof_id, entry, {},
                                                  result.get('finding')))
            note(no_bug_sentence(proof_id, entry, result.get('cause')))
    return breaks, findings, no_bug


def verdict_of(spot, survived, breaks):
    """`weak` when a spot test fired or a planted bug survived, else `strong`
    when a planted bug was caught, else `spot-checked` (ai_audit RULE-33)."""
    if spot or survived:
        return 'weak'
    if any(made.get('result') == 'caught' for made in breaks.values()):
        return 'strong'
    return 'spot-checked'


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def run(project_root, features, selected, again=False, out=None, settle=None):
    """For the rules the audit reads (ai_audit RULE-1; `again` reads every passing rule):
    the spot tests, then the model's request for each rule, then each planted bug.
    Writes one audit.rules entry per rule read, through evidence.write_audit; prints
    each rule read with its findings and, last, the share. Returns 0, or 1 when the
    project changed while it ran (planted_bug RULE-6).

    `settle` names rules, `RULE-N`, of the one feature selected: only those are
    read, each bug kept as `survived` is planted again before any model is asked
    (`replayed`), and the model is asked only for a rule a new bug is needed for.
    A rule named that keeps no such bug is said to have nothing to settle and is
    left as it is; one whose tests do not pass is not read."""
    out = out or sys.stdout

    def say(line=''):
        print(line, file=out)

    if features is None:
        features = specs_module.scan_specs(project_root)
    selected = set(features if selected is None else selected)
    payload = payload_module.build_payload(project_root, generated_by='audit')
    cache = {}
    settle = [str(rule) for rule in settle or ()]
    if settle:
        to_read = sorted(
            (pair for pair in counted_rules(payload, selected)
             if pair[1].get('id') in settle),
            key=lambda pair: (pair[0], _number(pair[1].get('id'))))
    else:
        to_read = rules_to_read(project_root, payload, features, selected,
                                again, cache)

    # 1. The spot tests, and what each rule's one request asks for.
    not_read, not_found = set(), []
    done = []          # one dict per rule read, in order
    nothing = []       # one line per rule named that has nothing to settle
    for feature, rule in to_read:
        info = features.get(feature) or {}
        code = _code_part(project_root, features, feature, cache)
        reading = ai_audit.reading_for(project_root, payload, feature,
                                       rule['id'])
        last = audit_entry(project_root, feature, rule, code)
        plan = bug_plan(reading, last, code, settle=bool(settle))
        if settle and not any(what == 'replay' for _p, what, _v in plan):
            nothing.append(NOTHING_TO_SETTLE % (feature, rule['id']))
            continue
        spot = spot_tests(project_root, reading, not_read, not_found)
        scope_files = fingerprint_module.expand_scope(
            project_root, info.get('scope') or [])[0]
        reading['findings'] = spot
        done.append({'feature': feature, 'rule': rule, 'reading': reading,
                     'spot': spot, 'plan': plan, 'scope_files': scope_files,
                     'last': last, 'code': code, 'said': {}})

    # 2. The model's request for each rule; 3. each bug planted, one at a time.
    try:
        before = targeted_break.snapshot(project_root) if done else None
        for item in done:
            if settle:
                # Each kept bug planted again, before any model is asked.
                item['plan'], item['said'] = replayed(
                    project_root, item['reading'], item['plan'],
                    item['scope_files'])
                targeted_break.check_unchanged(project_root, before)
            reading = item['reading']
            reading['plant'] = [proof for proof, what, _value in item['plan']
                                if what in ('plant', 'second')]
            reading['files'] = (list(item['scope_files'])
                                if reading['plant'] else [])
        # A settled rule that needs no new bug is not asked about: what it
        # holds of the model is what its last entry holds.
        asked = [item for item in done
                 if not settle or item['reading']['plant']]
        with ai_audit.empty_folder() as folder:
            replies = ai_audit.audit_all(
                project_root, [item['reading'] for item in asked], cwd=folder)
        for item, answer in zip(asked, replies):
            item['answer'] = answer
        for item in done:
            answer = item.setdefault('answer', {
                'parts': {}, 'explanation': [], 'notes': [],
                'model': item['last'].get('model'),
                'criteria': item['last'].get('criteria')})
            breaks, survived, no_bug = planted_bugs(
                project_root, item['reading'], item['plan'],
                item['scope_files'], item['last'], answer, said=item['said'])
            targeted_break.check_unchanged(project_root, before)
            item.update(
                breaks=breaks, no_bug=no_bug,
                findings=item['spot'] + [line for line in survived
                                         if line not in item['spot']],
                verdict=verdict_of(item['spot'], survived, breaks))
    except targeted_break.ProjectChanged as stopped:
        say(targeted_break.STOPPED % _changed_path(project_root, stopped))
        return 1

    criteria = ai_audit.criteria_hash(ai_audit.criteria_text(project_root))
    commit = head_commit(project_root)
    by_feature = {}
    reasons, alone = [], 0
    for item in done:
        answer = item['answer']
        reached = not answer.get('why')
        if not reached:
            if answer['why'] not in reasons:
                reasons.append(answer['why'])
            alone += item['verdict'] == 'spot-checked'
        found = {'code_hash': item['code'], 'verdict': item['verdict'],
                 'findings': item['findings'], 'no_bug': item['no_bug'],
                 'breaks': item['breaks'],
                 'explanation': answer.get('explanation') or [],
                 'notes': answer.get('notes') or [],
                 'model': answer.get('model') if reached else 'unknown',
                 'criteria': answer.get('criteria') or criteria}
        by_feature.setdefault(item['feature'], {})[item['rule']['id']] = \
            evidence_writer.audit_entry(item['rule'], found, commit)
    for feature, entries in sorted(by_feature.items()):
        evidence_writer.write_audit(project_root, 'local', feature,
                                    features.get(feature) or {}, entries)

    for check, language in sorted(not_read):
        say(plain_checks.NOT_READ % (check, language))
    for named in not_found:
        say(plain_checks.NOT_FOUND % named)
    for line in nothing:
        say(line)
    for item in done:
        say(RULE_LINE % (item['feature'], item['rule']['id'],
                         item['verdict']))
        # What settling did, by proof, then the rule's lines as any audit's.
        for proof, _what, _value in item['plan']:
            if proof in item['said']:
                say(FINDING_LINE % item['said'][proof])
        for line in rule_lines(item['verdict'], item['findings'],
                               item['no_bug']):
            say(FINDING_LINE % line)
    if reasons:
        say(NOT_REACHED % ('; '.join(reasons),
                           '' if not alone else ALONE_ONE if alone == 1
                           else ALONE_MANY % alone))

    say(share_line(project_root, payload, selected))
    return 0


def rule_lines(verdict, findings, no_bug):
    """The lines under a rule: each finding, then each `no_bug` sentence
    alone; under a `spot-checked` rule the sentences follow `The spot tests
    found nothing. ` on one line."""
    if verdict == 'spot-checked':
        return [(SPOT_CHECKED % ' '.join(no_bug)).strip()]
    return list(findings) + list(no_bug)


def _changed_path(project_root, stopped):
    path = getattr(stopped, 'path', None) or (stopped.args[0] if stopped.args
                                              else '')
    path = str(path)
    if os.path.isabs(path):
        path = os.path.relpath(path, project_root)
    return path.replace(os.sep, '/')


def share_line(project_root, payload, selected):
    """The last line: the share of the rules that pass their tests the audit
    found strong, and each count as the status words it. The counts are
    `summary.audit_counts` over the project as it reads once the entries are
    written, so the line and the status give the same numbers: a rule is
    counted under the word its strong cell reads, and a rule whose strong
    cell reads `checked at sign-off` is in no count. `payload` is the one
    built before the audit, which says whether any rule passes."""
    if not counted_rules(payload, selected):
        return NO_RULE_PASSES
    now = payload_module.build_payload(project_root, generated_by='audit')
    own = [rule for feature in now.get('features') or ()
           if feature.get('name') in selected
           for rule in feature.get('rules') or ()
           if rule.get('feature') == feature.get('name')]
    return summary_module.audit_line(summary_module.audit_counts(own))
