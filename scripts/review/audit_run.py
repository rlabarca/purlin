"""The audit's run: the spot tests, the model's request for each rule, the planted bugs.

`purlin_run.py --audit` runs the tests, then calls `run`. For the rules the
audit reads (`ai_audit.is_read`, ai_audit RULE-1) it runs, in this order:

1. the heuristic spot tests over each test tied to each rule's proofs
   (`plain_checks.check`), with no model;
2. the model's request for each rule (`ai_audit.audit_all`), whose reply
   holds a planted bug for each proof that needs one, aimed past that proof's
   test, with the case the model says it breaks, and the model's reading,
   which becomes the explanation and sets no verdict;
3. each bug planted in a copy of the project and its proof's own test run
   (`planted_bug.plant_bug`), one at a time. No bug is asked for an
   anchor's rule, a `@manual` proof or a proof tagged for a system this
   machine is not; a proof whose `bug_key` is unchanged keeps its last
   result (ai_audit RULE-36), and a bug that survived is planted again
   before a new one is asked for, where its proof's tests are as they were.

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
no other (`settle`). A rule is read where its entry keeps a bug as `survived`
or holds a finding of the spot tests (`spot_findings_of`): the spot tests run
over its tests as they stand, and `NOW_FIND_NOTHING` names each test they no
longer find anything in. Each bug the rule's entry keeps as `survived` is planted
again, with no model asked, and its proof's tests run as they stand now
(`replayed`). A test that fails makes the entry `caught`. A test that still
passes drops the bug, and one new bug is asked for that proof in the usual
request: a second survivor leaves no bug on record, the proof `not made` with
`TWO_SURVIVED`. A recorded change that can no longer be planted is asked for
anew, as any audit asks.

A settle plants nothing for a proof whose tests are as they were when its bug
got past them (`test_as_it_was`): it prints `REFUSED` under the rule and the
bug stays `survived`. `--sound PROOF-N` says the test was read and judged to
assert what the proof names already: the settle then goes on for that proof,
its entry holds `test_unchanged` and `no_bug` gains `UNCHANGED`. A bug recorded
as `survived` holds `test_key`, the hash of its proof's tests' source, which
is what tells a changed test from changed code. `references/review_criteria.md`,
"Settling a finding", is the one home of that contract.

An audit without `--settle` plants a bug that survived again as well, where
the feature's code changed and the proof's tests are as they were when the bug
got past them (`bug_plan`, `replayed`). The tests still pass: the bug stays
`survived` and the audit prints `STILL_PASSES`. They fail or do not run: the
entry reads `caught` or `not run`, as in a settle. The change can no longer be
planted: a new bug is asked for. A bug whose proof's tests changed is not
planted again: a new bug is asked for.

A project file that changes between the first model call and the last planted
bug stops the run before anything is written (planted_bug RULE-6).

**An AI proof**, one tagged `@ai`, is planted a wrong output in place of a
bug: a change to a copy of the output one passing run of its test kept on
this machine (`ai_audit.kept_output`), with the proof's own test run on that
copy and no model asked for an output. Its entry under `bugs` is a bug's and
holds `output`, the sha256 of the kept folder, and every sentence about it
says `wrong output` (`planted_bug.of_output`). A bug that survived is
planted again in the folder its entry names where this machine still keeps
it, else in the output kept now. Where this machine keeps no passing output
of the proof, nothing is planted and nothing is recorded for it: `no_bug`
holds `NO_OUTPUT`, and the proof is left out of `ai_audit.plants_for`, so
the rule is not read again for it until an output is kept.
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
import planted_bug                                            # noqa: E402
from purlin import evidence as evidence_reader                 # noqa: E402
from purlin import fingerprint as fingerprint_module           # noqa: E402
from purlin import outputs as outputs_module                   # noqa: E402
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
# For an AI proof alone: PROOF-N in each.
NO_GRADE = 'A wrong output was planted for %s and its grader gave no answer.'
NO_OUTPUT = 'this machine keeps no passing output of %s'
NO_PART = planted_bug.NO_PART

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

# A settle and the spot tests. Both are printed under the rule and not stored.
# `NOW_FIND_NOTHING`: the file and the name of a test the entry held a finding
# of the spot tests for, which they no longer find anything in. `NO_BUG_ON_RECORD`:
# PROOF-N, whose result was taken on another test or code and is left out of
# the entry, and the feature.
NOW_FIND_NOTHING = '%s::%s: the spot tests now find nothing.'
NO_BUG_ON_RECORD = ('%s: no bug is on record for its test as it stands. Run '
                    'purlin:audit %s to plant one.')

# A settle and a test that has not changed. `REFUSED` is printed under the
# rule and not stored: PROOF-N. `UNCHANGED` is the sentence `no_bug` holds for
# a proof settled under `--sound` with its test as it was: PROOF-N. The last
# two refuse a `--sound` before anything runs: the feature, PROOF-N.
REFUSED = ('%s: its test is as it was when the bug got past it. Strengthen it '
           'with purlin:build, then settle.')
UNCHANGED = ('%s was settled with its test unchanged: it was judged to assert '
             'what the proof names.')
NOT_SETTLED = ('%s %s is not a proof of a rule named with --settle. Run '
               'purlin:status %s to see its rules.')
NO_SURVIVOR = '%s %s has no planted bug that survived: nothing to settle.'

# An audit without `--settle` and a bug that survived, planted again with its
# proof's tests as they were: printed under the rule and not stored. PROOF-N.
STILL_PASSES = ('%s: its test is as it was and still passes with the bug it '
                'missed. Strengthen it with purlin:build.')

# What a test run over every feature says once it has read the audited rules
# of the anchors again with the spot tests alone: how many rules, then how
# many of them read each word.
ANCHORS_READ = ('Anchors: the spot tests read %s again. %d spot-checked, '
                '%d weak.')

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
                                plant=ai_audit.plants_for(
                                    rule, anchor,
                                    project_root=project_root)):
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


def _ai_proof(reading, proof_id):
    """The proof `proof_id` of the reading where it is an AI proof, else None."""
    for proof in reading.get('proofs') or ():
        if proof.get('id') == proof_id and proof.get('ai'):
            return proof
    return None


def output_for(project_root, reading, proof_id, kept=None):
    """What `planted_bug` plants a wrong output in for one proof: `{'folder',
    'model', 'sha256'}`, or None for a proof that is no AI proof and for one
    this machine keeps no passing output of. `kept` is a recorded bug to
    plant again: the folder its `output` names is used where this machine
    still keeps it, else the output kept now."""
    proof = _ai_proof(reading, proof_id)
    if proof is None:
        return None
    sha, folder = proof.get('output'), proof.get('folder')
    held = (kept or {}).get('output')
    if held and held != sha:
        again = outputs_module.ai_held(project_root, held)
        if again:
            sha, folder = held, again
    if not folder:
        return None
    return {'folder': folder, 'model': proof['ai'][0], 'sha256': sha}


def _words(template, output):
    """A sentence's template, said of a wrong output where `output` holds."""
    return planted_bug.of_output(template) if output else template


def _to_plant(reading, proof_id, key):
    """The plan's entry for a proof a new bug is to be asked for: `plant`
    with its key, or `no output` for an AI proof this machine keeps no
    passing output of."""
    proof = _ai_proof(reading, proof_id)
    if proof is not None and not proof.get('folder'):
        return (proof_id, 'no output', None)
    return (proof_id, 'plant', key)


def spot_tests(project_root, reading, not_read, not_found=None):
    """The spot tests' findings for one rule, in order and once each.
    `not_read` gains `(check, language)` for each check a test's language
    cannot be read for, and `not_found`, a list, `(file, name)` once for each
    marked test whose source was not found, which no check reads."""
    findings = []
    proofs = {proof['id']: proof for proof in reading['proofs']}
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
            {'id': test['proof'],
             'text': (proofs.get(test['proof']) or {}).get('text'),
             'graded': (proofs.get(test['proof']) or {}).get('graded')},
            {'file': test['file'], 'name': test['name'],
             'source': test['body']})
        for check, finding in found or ():
            if finding is None:
                not_read.add((check, language_of(test['file'])))
            elif finding not in findings:
                findings.append(finding)
    return findings


def spot_findings_of(entry):
    """The findings of an audit entry that the spot tests gave: every one
    that is neither sentence of a planted bug that survived."""
    bug = tuple(words.split('%s', 1)[1].split('%s', 1)[0]
                for words in (planted_bug.SURVIVED, planted_bug.AI_SAYS))
    found = []
    for line in (entry or {}).get('findings') or ():
        head, _, rest = str(line).partition(': ')
        if not (head.startswith('PROOF-') and (': ' + rest).startswith(bug)):
            found.append(str(line))
    return found


def cleared_lines(reading, last, spot):
    """`NOW_FIND_NOTHING` for each test of the rule that the entry `last`
    holds a finding of the spot tests for and `spot`, their findings now,
    holds none for, in the order the tests are read."""
    earlier = spot_findings_of(last)
    lines = []
    for test in reading.get('tests') or ():
        if test.get('manual') or not test.get('file'):
            continue
        start = '%s::%s: ' % (test['file'], test.get('name'))
        line = NOW_FIND_NOTHING % (test['file'], test.get('name'))
        if (any(found.startswith(start) for found in earlier)
                and not any(found.startswith(start) for found in spot)
                and line not in lines):
            lines.append(line)
    return lines


def _survived_finding(proof_id, kept, last):
    """The finding a kept `survived` result carries, as its entry wrote it."""
    start = '%s: the test still passes when' % proof_id
    for line in last.get('findings') or ():
        if str(line).startswith(start):
            return line
    changed = (str(kept.get('after') or '').strip().splitlines() or [''])[0]
    return planted_bug.SURVIVED % (proof_id, kept.get('file'),
                                   kept.get('line') or 0, changed.strip())


def survived_findings(proof_id, made, last, finding=None):
    """The findings of a bug that survived, in order: the change the test
    still passes with, `finding` or the line the entry `made` rebuilds, then,
    where the entry holds a case, what the model says the bug breaks."""
    found = [finding or _survived_finding(proof_id, made, last)]
    case = str(made.get('case') or '').strip()
    if case:
        found.append(planted_bug.AI_SAYS % (proof_id, case))
    return found


def test_as_it_was(kept, tests):
    """True where the tests of a proof are the ones its kept bug got past.

    `kept` is the bug's entry and `tests` the proof's own tests as the audit
    reads them now. The entry's `test_key` is compared with the hash of the
    tests' source. A test whose source is not found cannot be compared and
    reads as changed, so no settle is refused for a test nobody can show to
    be the same."""
    if not tests or any(test.get('source') is None for test in tests):
        return False
    return kept.get('test_key') == test_source_hash(tests)


def _with_test_key(entry, tests):
    """A `survived` entry with the `test_key` of `tests`, the tests it got
    past; as it is where the source of one of them is not found."""
    if any(test.get('source') is None for test in tests):
        return entry
    return dict(entry, test_key=test_source_hash(tests))


def _settled_entry(entry, unchanged):
    """An entry as a settle writes it: without the `test_key` of the bug that
    survived, and with `test_unchanged` where the settle went on with the
    proof's test as it was."""
    entry = {name: value for name, value in entry.items()
             if name not in ('test_key', 'test_unchanged')}
    if unchanged:
        entry['test_unchanged'] = True
    return entry


def bug_plan(reading, last, code_part, here=None, settle=False, sound=()):
    """`[(proof, what, value)]` for each proof of the rule that has a test and
    is not checked by hand, in the spec's order. `what` is `anchor` for an
    anchor's rule; `system`, with the system the proof is tagged for, where
    this machine is another; `kept`, with the last result, where the proof's
    `bug_key` is unchanged; else `plant`, with the key its result will
    carry, or `no output` for an AI proof this machine keeps no passing
    output of.

    Under `settle` a proof whose last result reads `survived` is `replay`,
    with that result, the key and whether its tests are as they were when the
    bug got past them, whatever its `bug_key`. Where they are and `sound`
    does not name the proof it is `refused`, with that result. Any other
    result is `kept` only where its `bug_key` is unchanged. A result taken on
    another test or code is left out, as a proof with no result on record
    is, so the entry holds none for it and the next audit plants a bug for
    that proof (`ai_audit.is_read`).

    Without `settle` a proof whose last result reads `survived`, whose
    `bug_key` changed and whose tests are as they were when the bug got past
    them is `again`, with that result and the key: the feature's code changed
    and the test did not, so the recorded bug is planted again before any new
    one is asked for."""
    here = here or evidence_reader.host_os()
    kept_bugs = last.get('bugs') if isinstance(last.get('bugs'),
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
        key = ai_audit.bug_key(test_source_hash(tests), code_part)
        kept = kept_bugs.get(proof['id'])
        if settle:
            if isinstance(kept, dict) and kept.get('result') == 'survived':
                same = test_as_it_was(kept, tests)
                if same and proof['id'] not in sound:
                    plan.append((proof['id'], 'refused', kept))
                else:
                    plan.append((proof['id'], 'replay', (kept, key, same)))
            elif isinstance(kept, dict) and kept.get('bug_key') == key:
                plan.append((proof['id'], 'kept', kept))
            continue
        if isinstance(kept, dict) and kept.get('bug_key') == key:
            plan.append((proof['id'], 'kept', kept))
        elif (isinstance(kept, dict) and kept.get('result') == 'survived'
              and test_as_it_was(kept, tests)):
            plan.append((proof['id'], 'again', (kept, key)))
        else:
            plan.append(_to_plant(reading, proof['id'], key))
    return plan


def no_bug_sentence(proof_id, made, cause=None, last=None):
    """The sentence of `no_bug` for one planted bug's result, or None where
    the bug was caught or survived. A `not made` result is worded by where
    its reason came from: `cause` is `planted_bug`'s for a bug this audit
    asked for; for a result kept from an earlier audit it is the sentence
    that audit wrote, found under `no_bug` of `last`, its entry. Only an
    entry that holds no such sentence is read by the words of its reason."""
    result = made.get('result')
    output = bool(made.get('output'))
    if result == 'not run':
        if made.get('why') == planted_bug.NO_GRADE:
            return NO_GRADE % proof_id
        if made.get('why') == planted_bug.ERRORED:
            return _words(ERRORED, output) % proof_id
        return _words(NOT_RUN, output) % proof_id
    if result != 'not made':
        return None
    why = str(made.get('why') or '').rstrip('.')
    no_bug = _words(NO_BUG, output)
    worded = {
        planted_bug.TEST_DOES_NOT_PASS:
            no_bug % (_words(BASELINE, output) % proof_id),
        planted_bug.ANSWER_UNUSABLE: no_bug % (ANSWER_UNUSABLE % (proof_id, why)),
        planted_bug.MODEL_FOUND_NONE: no_bug % (MODEL_FOUND_NONE % (proof_id, why)),
    }
    if cause not in worded:
        written = [str(line) for line in (last or {}).get('no_bug') or ()]
        two = [_words(NO_BUG_CAUGHT, output) % (proof_id, why)] * (
            why == _words(TWO_SURVIVED, output))
        for sentence in two + list(worded.values()):
            if sentence in written:
                return sentence
        if two:
            return two[0]
        cause = planted_bug.cause_of(why)
    return worded[cause]


def replayed(project_root, reading, plan, scope_files):
    """`(plan, said, unchanged)` for one rule, once each bug of the plan that
    is to be planted again, a settle's `replay` or any other audit's `again`,
    has been planted and its proof's tests run as they stand. No model is
    asked. A `refused` proof is planted nothing: it reads `kept`, its bug
    still `survived`, and `said` holds `REFUSED` for it. In the plan handed
    back each `replay` reads:

    `kept`     the test failed, so the bug's entry reads `caught`, with the
               change as it was recorded and the key of the test and code
               now; or the test did not run, and the entry reads `not run`
    `second`   the test still passes: the bug is dropped, and one new bug is
               to be asked for, with the key and the line that says so
    `plant`    the recorded change can no longer be planted: a new bug is to
               be asked for, as any audit asks

    An `again` reads the same but where the test still passes: its tests are
    as they were, so the bug is not dropped. It reads `held`, with the entry,
    still `survived`, at the line the change now stands at and with the key
    of the test and code now, and that run's finding; `said` holds
    `STILL_PASSES` for it.

    `said` is `{proof: line}`, what the audit prints under the rule, and
    `unchanged` the proofs settled with their tests as they were, which
    `--sound` named."""
    settled, said, unchanged = [], {}, set()
    for proof_id, what, value in plan:
        if what == 'refused':
            settled.append((proof_id, 'kept', value))
            said[proof_id] = _words(REFUSED, value.get('output')) % proof_id
            continue
        if what not in ('replay', 'again'):
            settled.append((proof_id, what, value))
            continue
        kept, key = value[0], value[1]
        same = what == 'replay' and value[2]
        wrong = bool(kept.get('output'))
        output = output_for(project_root, reading, proof_id, kept)
        if wrong != bool(output):
            # A wrong output with no output kept to plant it in, or a bug
            # recorded before the proof was tagged `@ai`: asked for anew.
            settled.append(_to_plant(reading, proof_id, key))
            continue
        if same:
            unchanged.add(proof_id)
        result = planted_bug.replay(
            project_root, reading['feature'], proof_id,
            _proof_tests(reading, proof_id), scope_files, kept,
            output=output)
        place = (proof_id, kept.get('file'), kept.get('line') or 0)
        ran = result.get('result')
        if ran in ('caught', 'not run'):
            settled.append((proof_id, 'kept', _settled_entry(dict(
                kept, result=ran, why=result.get('why') or '',
                bug_key=key), same)))
            if ran == 'caught':
                said[proof_id] = _words(NOW_CATCHES, wrong) % place
        elif ran == 'survived' and what == 'again':
            settled.append((proof_id, 'held', (
                dict(kept, line=result.get('line'), bug_key=key),
                result.get('finding'))))
            said[proof_id] = _words(STILL_PASSES, wrong) % proof_id
        elif ran == 'survived':
            settled.append((proof_id, 'second',
                            (key, _words(DROPPED, wrong) % place)))
        else:
            settled.append(_to_plant(reading, proof_id, key))
    return settled, said, unchanged


def planted_bugs(project_root, reading, plan, scope_files, last, answer,
                 here=None, said=None, unchanged=()):
    """`(bugs, findings, no_bug)` for one rule's proofs.

    `plan` is `bug_plan`'s and `answer` the model's one reply for the rule,
    as `ai_audit.audit_one` gives it. `bugs` is `{proof: entry}` as the
    evidence holds it, each with its `aim` and `case`, and for a wrong
    output `output`, the sha256 of the kept folder it was planted in;
    `findings` the two
    sentences of each bug that survived, the change and the case the model
    says it breaks;
    `no_bug` one sentence for each proof no bug was caught for. A proof the
    model could not be reached for, or that is tagged for another system, has
    no entry under `bugs`, so the first is asked for again. A `no output`
    proof of the plan has none either, and `no_bug` holds `NO_OUTPUT` for it.

    A `held` proof of the plan is one whose kept bug was planted again and
    still survives: its entry and its two findings are kept.

    A `second` proof of the plan is one whose kept bug a settle dropped: its
    new bug is planted as any is, and one that survives too is not kept, the
    entry reading `not made` with `TWO_SURVIVED`. `said`, a dict, gains the
    line the audit prints for it.

    `unchanged` names the proofs a settle went on for with their tests as
    they were: the entry written for one holds `test_unchanged`, unless its
    new bug reads `survived`, which is a finding of its own, and `no_bug`
    gains `UNCHANGED`. A kept entry that holds the field gives the sentence
    again. A bug that survives holds the `test_key` of the tests it got past.
    """
    here = here or evidence_reader.host_os()
    bugs, findings, no_bug = {}, [], []
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
            bugs[proof_id] = value
            if value.get('result') == 'survived':
                findings.extend(survived_findings(proof_id, value, last))
            note(no_bug_sentence(proof_id, value, last=last))
            if value.get('test_unchanged'):
                note(UNCHANGED % proof_id)
        elif what == 'held':
            bugs[proof_id] = value[0]
            findings.extend(survived_findings(proof_id, value[0], last,
                                              value[1]))
        elif what == 'no output':
            note(planted_bug.of_output(NO_BUG) % (NO_OUTPUT % proof_id))
        elif answer.get('why'):
            if what == 'second':
                said[proof_id] = value[1]
            note(_words(NO_BUG, _ai_proof(reading, proof_id))
                 % (UNREACHED % answer['why']))
            if proof_id in unchanged:
                note(UNCHANGED % proof_id)
        else:
            key, dropped = value if what == 'second' else (value, None)
            tests = _proof_tests(reading, proof_id)
            same = proof_id in unchanged
            output = output_for(project_root, reading, proof_id)
            result = planted_bug.plant_bug(
                project_root, reading['feature'], proof_id, tests,
                scope_files, parts.get(proof_id), output=output)
            entry = {'aim': result.get('aim') or planted_bug.PLAIN,
                     'case': result.get('case') or '',
                     'file': result.get('file'), 'line': result.get('line'),
                     'before': result.get('before'),
                     'after': result.get('after'),
                     'result': result.get('result') or 'not made',
                     'why': result.get('why') or '', 'bug_key': key}
            if output:
                entry['output'] = output['sha256']
            if dropped:
                said[proof_id] = dropped + (
                    '' if entry['result'] == 'not made'
                    else _words(NEW_BUG_PLANTED, output))
                if entry['result'] == 'survived':
                    # Two bugs left the test passing: neither is kept.
                    two = dict({
                        'aim': planted_bug.PLAIN, 'case': '', 'file': None,
                        'line': None, 'before': None, 'after': None,
                        'result': 'not made',
                        'why': _words(TWO_SURVIVED, output), 'bug_key': key},
                        **({'output': output['sha256']} if output else {}))
                    bugs[proof_id] = _settled_entry(two, same)
                    note(_words(NO_BUG_CAUGHT, output) % (proof_id,
                                                          two['why']))
                    if same:
                        note(UNCHANGED % proof_id)
                    continue
            if entry['result'] == 'survived':
                entry = _with_test_key(entry, tests)
                findings.extend(survived_findings(proof_id, entry, {},
                                                  result.get('finding')))
            elif same:
                entry['test_unchanged'] = True
            bugs[proof_id] = entry
            note(no_bug_sentence(proof_id, entry, result.get('cause')))
            if entry.get('test_unchanged'):
                note(UNCHANGED % proof_id)
    return bugs, findings, no_bug


def verdict_of(spot, survived, bugs):
    """`weak` when a spot test fired or a planted bug survived, else `strong`
    when a planted bug was caught, else `spot-checked` (ai_audit RULE-33)."""
    if spot or survived:
        return 'weak'
    if any(made.get('result') == 'caught' for made in bugs.values()):
        return 'strong'
    return 'spot-checked'


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def sound_refusals(project_root, features, feature, rules, sound):
    """The lines that refuse `--sound`, one per proof it names that cannot be
    settled, in the order given; [] where each can. A proof must be one of a
    rule `--settle` names (`NOT_SETTLED`), and its bug on record must read
    `survived` (`NO_SURVIVOR`). Nothing is run and nothing is written."""
    info = (features or {}).get(feature) or {}
    payload = payload_module.build_payload(project_root, generated_by='audit')
    code = _code_part(project_root, features, feature, {})
    survivors, owned = set(), set()
    for entry in payload.get('features') or ():
        if entry.get('name') != feature:
            continue
        for rule in entry.get('rules') or ():
            if rule.get('feature') != feature or rule.get('id') not in rules:
                continue
            owned.update(proof.get('id') for proof in rule.get('proofs') or ())
            bugs = audit_entry(project_root, feature, rule,
                               code).get('bugs')
            for proof, made in (bugs if isinstance(bugs, dict)
                                else {}).items():
                if isinstance(made, dict) and made.get('result') == 'survived':
                    survivors.add(proof)
    lines = []
    for proof in sound:
        if proof not in owned:
            lines.append(NOT_SETTLED % (feature, proof, feature))
        elif proof not in survivors:
            lines.append(NO_SURVIVOR % (feature, proof))
    return lines


def run(project_root, features, selected, again=False, out=None, settle=None,
        sound=None):
    """For the rules the audit reads (ai_audit RULE-1; `again` reads every passing rule):
    the spot tests, then the model's request for each rule, then each planted bug.
    Writes one audit.rules entry per rule read, through evidence.write_audit; prints
    each rule read with its findings and, last, the share. Returns 0, or 1 when the
    project changed while it ran (planted_bug RULE-6).

    `settle` names rules, `RULE-N`, of the one feature selected: only those are
    read, each bug kept as `survived` is planted again before any model is asked
    (`replayed`), and the model is asked only for a rule a new bug is needed for.
    A rule named that keeps no such bug, and whose entry holds no finding of the
    spot tests, is said to have nothing to settle and is left as it is; one
    whose tests do not pass is not read. A rule read for a finding of the spot
    tests alone asks no model. `sound` names
    proofs, `PROOF-N`, whose tests were judged to assert what their proofs name
    already: a settle is refused for any other proof whose tests are as they
    were when its bug got past them."""
    out = out or sys.stdout

    def say(line=''):
        print(line, file=out)

    if features is None:
        features = specs_module.scan_specs(project_root)
    selected = set(features if selected is None else selected)
    payload = payload_module.build_payload(project_root, generated_by='audit')
    cache = {}
    settle = [str(rule) for rule in settle or ()]
    sound = [str(proof) for proof in sound or ()]
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
        plan = bug_plan(reading, last, code, settle=bool(settle), sound=sound)
        if settle and not spot_findings_of(last) and not any(
                what in ('replay', 'refused') for _p, what, _v in plan):
            nothing.append(NOTHING_TO_SETTLE % (feature, rule['id']))
            continue
        spot = spot_tests(project_root, reading, not_read, not_found)
        scope_files = fingerprint_module.expand_scope(
            project_root, info.get('scope') or [])[0]
        reading['findings'] = spot
        # What a settle says before the proofs' own lines: each test the spot
        # tests no longer find anything in, then each proof it asked no bug
        # for and holds no result of.
        first = []
        if settle:
            planned = {proof for proof, _what, _value in plan}
            first = cleared_lines(reading, last, spot) + [
                _words(NO_BUG_ON_RECORD, _ai_proof(reading, proof))
                % (proof, feature)
                for proof in ai_audit.plants_for(
                    rule, bool(info.get('is_anchor')),
                    project_root=project_root)
                if proof not in planned]
        done.append({'feature': feature, 'rule': rule, 'reading': reading,
                     'spot': spot, 'plan': plan, 'scope_files': scope_files,
                     'last': last, 'code': code, 'said': {},
                     'unchanged': set(), 'first': first})

    # 2. The model's request for each rule; 3. each bug planted, one at a time.
    try:
        before = planted_bug.snapshot(project_root) if done else None
        for item in done:
            # Each kept bug planted again, before any model is asked.
            item['plan'], item['said'], item['unchanged'] = replayed(
                project_root, item['reading'], item['plan'],
                item['scope_files'])
            planted_bug.check_unchanged(project_root, before)
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
            bugs, survived, no_bug = planted_bugs(
                project_root, item['reading'], item['plan'],
                item['scope_files'], item['last'], answer, said=item['said'],
                unchanged=item['unchanged'])
            planted_bug.check_unchanged(project_root, before)
            item.update(
                bugs=bugs, no_bug=no_bug,
                findings=item['spot'] + [line for line in survived
                                         if line not in item['spot']],
                verdict=verdict_of(item['spot'], survived, bugs))
    except planted_bug.ProjectChanged as stopped:
        say(planted_bug.STOPPED % _changed_path(project_root, stopped))
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
                 'bugs': item['bugs'],
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
        for line in item['first']:
            say(FINDING_LINE % line)
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


def read_anchors_again(project_root, features, selected):
    """`ANCHORS_READ` filled, once the spot tests have read again each rule
    of an anchor in `selected` that passes its tests and holds an audit
    entry; None where there is no such rule.

    What `purlin:test --all` and `--clean` call after the anchors' tests
    ran. Any change to the project ends an anchor's audit entry, and no bug
    is planted for an anchor's rule, so its audit is the spot tests alone:
    no model is asked. Each entry is written as the audit writes an
    anchor's, `spot-checked` with `ANCHOR` as its reason or `weak` with the
    spot tests' findings. It keeps the `model` and the `criteria` of the
    entry it replaces, and that entry's `explanation` and `notes` where the
    rule, its proofs and its tests are as that entry read them. An anchor's
    rule with no entry is left as it is: the audit is a person's to start.
    """
    anchors = {name for name in selected
               if (features.get(name) or {}).get('is_anchor')}
    if not anchors:
        return None
    payload = payload_module.build_payload(project_root, generated_by='run')
    commit = head_commit(project_root)
    cache, by_feature, words = {}, {}, []
    for feature, rule in counted_rules(payload, anchors):
        code = _code_part(project_root, features, feature, cache)
        last = audit_entry(project_root, feature, rule, code)
        if not last:
            continue
        reading = ai_audit.reading_for(project_root, payload, feature,
                                       rule['id'])
        spot = spot_tests(project_root, reading, set())
        plan = bug_plan(reading, last, code)
        bugs, survived, no_bug = planted_bugs(
            project_root, reading, plan, [], last, {'parts': {}})
        same = not {'rule', 'proof', 'test'} & set(
            last.get('out_of_date') or ())
        verdict = verdict_of(spot, survived, bugs)
        words.append(verdict)
        by_feature.setdefault(feature, {})[rule['id']] = \
            evidence_writer.audit_entry(rule, {
                'code_hash': code, 'verdict': verdict, 'findings': spot,
                'no_bug': no_bug, 'bugs': bugs,
                'explanation': last.get('explanation') if same else [],
                'notes': last.get('notes') if same else [],
                'model': last.get('model'),
                'criteria': last.get('criteria')}, commit)
    for feature, entries in sorted(by_feature.items()):
        evidence_writer.write_audit(project_root, 'local', feature,
                                    features.get(feature) or {}, entries)
    if not words:
        return None
    return ANCHORS_READ % (
        '1 audited rule' if len(words) == 1
        else '%d audited rules' % len(words),
        words.count('spot-checked'), words.count('weak'))


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
    written, so the line and the status give the same numbers, the share counting no rule of an anchor: a rule is
    counted under the word its strong cell reads, and a rule whose strong
    cell reads `checked at sign-off` is in no count. `payload` is the one
    built before the audit, which says whether any rule passes."""
    if not counted_rules(payload, selected):
        return NO_RULE_PASSES
    now = payload_module.build_payload(project_root, generated_by='audit')
    return summary_module.features_audit_line(
        [feature for feature in now.get('features') or ()
         if feature.get('name') in selected])
