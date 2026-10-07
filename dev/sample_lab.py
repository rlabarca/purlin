"""The sample lab project: a lab's sample intake, with three weak tests.

The project the audit's own tests audit, and the one of the trial
`docs/audit-research.md` reports: the spec `sample_intake` with 8 rules and
12 proofs, `src/intake.py`, and `tests/test_intake.py`, whose 12 tests hold three
written weak on purpose:

    PROOF-5    the expected age comes from `age_hours`, the code's own helper
    PROOF-7    the test hands in a sample 71 hours old, not the proof's 72
    PROOF-11   the test prints the two numbers and checks nothing

`build(folder)` writes the project into a new git repository and runs its
tests once, so the evidence is there. `audited(folder)` builds it, puts a fake
`claude` first on PATH that answers `REPLY`, and runs the audit twice: once as
`purlin:audit` reads a project never audited, and once reading every rule
again with nothing changed. No call reaches a real model.

`REPLY` holds the parts a real model wrote for three proofs in that trial,
each case word for word:

    PROOF-3    past the test: the record is handed back and never stored
    PROOF-5    past the test: the helper rounds to the nearest hour
    PROOF-6    plain: the limit is 73 hours. Its test checks the proof's case,
               so no change gets past it

The reply names no other proof, so no bug is planted for the other nine.

`settled(folder, ...)` is the project the tests of `purlin:audit --settle`
run on: it builds the lab, audits it once with `REPLY`, so `RULE-2` and
`RULE-3` read `weak` with a bug kept as `survived`, makes the change a test
asks for, and runs `purlin_run.py --audit --feature sample_intake` with
`--settle` for each rule named, as its own process, with a fake `claude`
that answers what the test hands it. `MORE_SURVIVE` is a first reply that
leaves a bug kept as `survived` for `PROOF-7` and `PROOF-11` as well, and
`BOTH_OF_RULE_4_SURVIVE` one that leaves one for `PROOF-6` too, so `RULE-4`
holds two. `sound` names the proofs handed to `--sound`: a settle is refused
for a proof whose test is as it was when its bug got past it, unless the
proof is named there. With no rule named the run is a plain audit:
`refuse_a_bad_site`, `work_out_the_age_inline` and `check_the_helper_on_load`
each change the code and leave every test as it was, which is where that
audit plants a bug that survived again.

**The refusal note** is a second project, for the audit of an AI proof: the
spec `refusal_note`, whose scope is the prompt `prompts/refusal_note.md`,
with `PROOF-1`, tagged `@ai`, and `PROOF-2`, tagged `@ai` and `@graded`, and
`tests/test_note.py`. Each test hands the note `NOTE` to the real helper,
`scripts/ai/purlin_ai.py record`, so an output folder is kept and no model
is asked for one; the test of `PROOF-2` then calls `grade`. The test of
`PROOF-1` is written weak on purpose: it looks for `LC-` and not for the
barcode. `build_note` writes the project and runs its tests once with a
fake grader that accepts, `note_audit` audits it with a fake `claude`
(`dev/fake_claude_session.py`) that answers the audit's request and then
each grade the audit's replays ask for, and `note_settle` runs the script
with `--settle`. `wrong_outputs` is the reply that names one wrong output
for each proof.
"""

import io
import json
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _path in (_HERE, os.path.join(_ROOT, 'scripts', 'review')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import audit_run  # noqa: E402
import fake_claude  # noqa: E402
import fake_claude_session  # noqa: E402
import suites  # noqa: E402

RUN_SCRIPT = os.path.join(_ROOT, 'scripts', 'run', 'purlin_run.py')
FEATURE = 'sample_intake'
EVIDENCE = '.purlin/evidence/local/sample_intake.json'

SPEC = '''\
# Feature: sample_intake

> Description: What the receiving bench does with one sample: it refuses a sample it cannot
>   identify, works out the sample's age, flags one that is too old or too warm, and gives each
>   accepted sample an accession number.
> Scope: src/intake.py
> Stack: python/stdlib (re, datetime)
> Highest-Rule: 8
> Highest-Proof: 12

## Rules

- RULE-1: A sample with no barcode, or a barcode of spaces only, is refused with `barcode is required`
- RULE-2: A barcode is `LC-` followed by exactly 8 digits; any other is refused with `barcode <barcode> is not LC- and 8 digits`
- RULE-3: A sample's age is the whole hours between collection and receipt, rounded down
- RULE-4: A sample more than 72 hours old at receipt is stored as `expired`; one exactly 72 hours old is not
- RULE-5: A `frozen` sample received warmer than -20.0 C is stored as `temperature excursion`; one at -20.0 C or colder is not
- RULE-6: A sample received before it was collected is refused with `received before collected`
- RULE-7: Each accepted sample gets the accession number `<site>-<year of receipt>-<sequence>`, the sequence five digits wide and counted from 1 for each site
- RULE-8: A barcode already received is refused with `barcode <barcode> was already received`

## Proof

- PROOF-1 (RULE-1): A sample with the barcode `` (empty) is handed in; it is refused with `barcode is required`
- PROOF-2 (RULE-1): A sample with the barcode of three spaces is handed in; it is refused with `barcode is required`
- PROOF-3 (RULE-2): A sample with the barcode `LC-12345678` is handed in; it is stored with the status `accepted`
- PROOF-4 (RULE-2): A sample with the barcode `LC-1234567`, seven digits, is handed in; it is refused with `barcode LC-1234567 is not LC- and 8 digits`
- PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`; its age is `25` hours
- PROOF-6 (RULE-4): A sample collected at `2026-03-01T08:00` is received at `2026-03-04T09:00`, 73 hours later; it is stored as `expired`
- PROOF-7 (RULE-4): A sample collected at `2026-03-01T08:00` is received at `2026-03-04T08:00`, exactly 72 hours later; it is stored as `accepted`
- PROOF-8 (RULE-5): A `frozen` sample is received at `-19.9` C; it is stored as `temperature excursion`
- PROOF-9 (RULE-5): A `frozen` sample is received at `-20.0` C; it is stored as `accepted`
- PROOF-10 (RULE-6): A sample collected at `2026-03-02T08:00` is received at `2026-03-01T08:00`; it is refused with `received before collected`
- PROOF-11 (RULE-7): Two samples from the site `BOS` are received in 2026; the first gets `BOS-2026-00001` and the second `BOS-2026-00002`
- PROOF-12 (RULE-8): The barcode `LC-12345678` is handed in twice; the second is refused with `barcode LC-12345678 was already received`
'''

SOURCE = '''\
"""Sample intake for a clinical lab: what is accepted at the receiving bench."""
import re
from datetime import datetime

BARCODE = re.compile(r'^LC-\\d{8}$')
MAX_AGE_HOURS = 72
FROZEN_MAX_C = -20.0


class IntakeError(Exception):
    """A sample that cannot be received at all."""


def age_hours(collected, received):
    """Whole hours between collection and receipt, rounded down."""
    seconds = (received - collected).total_seconds()
    return int(seconds // 3600)


class Bench:
    """One receiving bench: what it has received, and each site's sequence."""

    def __init__(self):
        self.received = {}
        self.sequence = {}

    def intake(self, barcode, site, collected, received, storage='ambient',
               temperature_c=None):
        """Receive one sample; the record it is stored as."""
        if barcode is None or not barcode.strip():
            raise IntakeError('barcode is required')
        if not BARCODE.match(barcode):
            raise IntakeError('barcode %s is not LC- and 8 digits' % barcode)
        if barcode in self.received:
            raise IntakeError('barcode %s was already received' % barcode)
        if received < collected:
            raise IntakeError('received before collected')
        age = age_hours(collected, received)
        status = 'accepted'
        if age > MAX_AGE_HOURS:
            status = 'expired'
        elif storage == 'frozen' and temperature_c is not None \\
                and temperature_c > FROZEN_MAX_C:
            status = 'temperature excursion'
        accession = None
        if status == 'accepted':
            number = self.sequence.get(site, 0) + 1
            self.sequence[site] = number
            accession = '%s-%d-%05d' % (site, received.year, number)
        record = {'barcode': barcode, 'site': site, 'age_hours': age,
                  'status': status, 'accession': accession}
        self.received[barcode] = record
        return record


def at(text):
    """A time written `2026-03-01T08:00`."""
    return datetime.strptime(text, '%Y-%m-%dT%H:%M')
'''

TESTS = '''\
import pytest

from src.intake import Bench, IntakeError, age_hours, at

T0 = at('2026-03-01T08:00')
T1 = at('2026-03-01T10:00')


# purlin: sample_intake PROOF-1
def test_an_empty_barcode_is_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode is required'


# purlin: sample_intake PROOF-2
def test_a_barcode_of_spaces_is_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('   ', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode is required'


# purlin: sample_intake PROOF-3
def test_eight_digits_are_accepted():
    record = Bench().intake('LC-12345678', 'BOS', T0, T1)
    assert record['status'] == 'accepted'


# purlin: sample_intake PROOF-4
def test_seven_digits_are_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('LC-1234567', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode LC-1234567 is not LC- and 8 digits'


# purlin: sample_intake PROOF-5
def test_age_is_whole_hours():
    collected = at('2026-03-01T08:00')
    received = at('2026-03-02T09:30')
    record = Bench().intake('LC-12345678', 'BOS', collected, received)
    assert record['age_hours'] == age_hours(collected, received)


# purlin: sample_intake PROOF-6
def test_73_hours_is_expired():
    record = Bench().intake('LC-12345678', 'BOS', at('2026-03-01T08:00'),
                            at('2026-03-04T09:00'))
    assert record['status'] == 'expired'


# purlin: sample_intake PROOF-7
def test_72_hours_is_accepted():
    record = Bench().intake('LC-12345678', 'BOS', at('2026-03-01T08:00'),
                            at('2026-03-04T07:00'))
    assert record['status'] == 'accepted'


# purlin: sample_intake PROOF-8
def test_a_warm_frozen_sample_is_an_excursion():
    record = Bench().intake('LC-12345678', 'BOS', T0, T1, storage='frozen',
                            temperature_c=-19.9)
    assert record['status'] == 'temperature excursion'


# purlin: sample_intake PROOF-9
def test_a_frozen_sample_at_minus_20_is_accepted():
    record = Bench().intake('LC-12345678', 'BOS', T0, T1, storage='frozen',
                            temperature_c=-20.0)
    assert record['status'] == 'accepted'


# purlin: sample_intake PROOF-10
def test_received_before_collected_is_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('LC-12345678', 'BOS', at('2026-03-02T08:00'),
                       at('2026-03-01T08:00'))
    assert str(refused.value) == 'received before collected'


# purlin: sample_intake PROOF-11
def test_accession_numbers_count_up():
    bench = Bench()
    first = bench.intake('LC-00000001', 'BOS', T0, T1)
    second = bench.intake('LC-00000002', 'BOS', T0, T1)
    print(first['accession'], second['accession'])


# purlin: sample_intake PROOF-12
def test_a_barcode_received_twice_is_refused():
    bench = Bench()
    bench.intake('LC-12345678', 'BOS', T0, T1)
    with pytest.raises(IntakeError) as refused:
        bench.intake('LC-12345678', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode LC-12345678 was already received'
'''


# What the model said each bug breaks, as it wrote it.
CASE_3 = ('a sample with the barcode `LC-12345678` is handed in; the proof '
          'names it stored with the status `accepted`; the changed code '
          'returns a record with status `accepted` but never stores it, so '
          "the bench's `received` stays empty")
CASE_5 = ('a sample collected at 2026-03-01T08:00 and received at '
          '2026-03-02T09:30; the proof names an age of 25 hours; the changed '
          'code gives 26 hours')
CASE_6 = ('a sample collected at 2026-03-01T08:00 and received at '
          '2026-03-04T09:00, 73 hours later; the proof names it stored as '
          '`expired`; the changed code stores it as `accepted`')

REPLY = {
    'PROOF-3': fake_claude.change(
        'src/intake.py',
        '        self.received[barcode] = record\n        return record',
        '        return record', case=CASE_3, aim='past the test'),
    'PROOF-5': fake_claude.change(
        'src/intake.py', '    return int(seconds // 3600)',
        '    return int(round(seconds / 3600))', case=CASE_5,
        aim='past the test'),
    'PROOF-6': fake_claude.change(
        'src/intake.py', 'MAX_AGE_HOURS = 72', 'MAX_AGE_HOURS = 73',
        case=CASE_6, aim='plain'),
    'reading': '- PROOF-5: the test takes its expected age from the code.',
}


# The test of `PROOF-5` as `purlin:build` strengthens it: the proof's own
# value, `25`, in place of the code's helper.
FROM_THE_HELPER = ("    assert record['age_hours'] == age_hours(collected, "
                   "received)\n")
THE_PROOFS_VALUE = "    assert record['age_hours'] == 25\n"

# A second bug for `PROOF-5` that the test, left as it was, still passes
# with: the helper it trusts is an hour out.
SECOND_SURVIVES = {
    'PROOF-5': fake_claude.change(
        'src/intake.py', '    return int(seconds // 3600)',
        '    return int(seconds // 3600) + 1', case=CASE_5,
        aim='past the test'),
    'reading': '- PROOF-5: the test takes its expected age from the code.',
}
# A second bug the same test catches: the record's age leaves the helper's.
SECOND_CAUGHT = {
    'PROOF-5': fake_claude.change(
        'src/intake.py', '        age = age_hours(collected, received)',
        '        age = age_hours(collected, received) + 1', case=CASE_5,
        aim='plain'),
    'reading': "- PROOF-5: the record's age is compared with the helper's.",
}
# The helper written over two lines, so the kept bug's `before` line is gone,
# and a bug for the helper as it then reads.
HELPER = '    return int(seconds // 3600)\n'
HELPER_IN_TWO = '    hours = seconds // 3600\n    return int(hours)\n'
AFTER_THE_REWRITE = {
    'PROOF-5': fake_claude.change(
        'src/intake.py', '    hours = seconds // 3600',
        '    hours = seconds // 3600 + 1', case=CASE_5, aim='past the test'),
    'reading': '- PROOF-5: the test takes its expected age from the code.',
}
# A bug the strengthened test catches, which is not the one on record.
ANOTHER_BUG = {
    'PROOF-5': fake_claude.change(
        'src/intake.py', '    return int(seconds // 3600)',
        '    return int(seconds // 1800)', case=CASE_5.replace('26', '51'),
        aim='plain'),
    'reading': '- PROOF-5: the test compares the age with 25.',
}
# The first audit's reply with two more bugs, each of which survives: the
# limit taken one hour early, which the test of `PROOF-7`, at 71 hours, never
# reaches, and a sequence four digits wide, which the test of `PROOF-11`,
# checking nothing, cannot see.
CASE_7 = ('a sample received exactly 72 hours after collection; the proof '
          'names it stored as `accepted`; the changed code stores it as '
          '`expired`')
CASE_11 = ('two samples from `BOS` received in 2026; the proof names '
           '`BOS-2026-00001`; the changed code gives `BOS-2026-0001`')
MORE_SURVIVE = dict(REPLY, **{
    'PROOF-7': fake_claude.change(
        'src/intake.py', '        if age > MAX_AGE_HOURS:',
        '        if age >= MAX_AGE_HOURS:', case=CASE_7, aim='past the test'),
    'PROOF-11': fake_claude.change(
        'src/intake.py', "'%s-%d-%05d'", "'%s-%d-%04d'", case=CASE_11,
        aim='past the test'),
})
# A bug for `PROOF-6` that its test, reading the record's status alone, does
# not see: a sample that is not accepted is handed back and never stored. With
# it `RULE-4` keeps two bugs as `survived`.
CASE_6_NOT_STORED = ('a sample received 73 hours after collection; the proof '
                     'names it stored as `expired`; the changed code hands '
                     'back the record and never stores it')
STORED = '        self.received[barcode] = record\n        return record'
STORED_WHEN_ACCEPTED = ("        if status == 'accepted':\n"
                        '            self.received[barcode] = record\n'
                        '        return record')
BOTH_OF_RULE_4_SURVIVE = dict(MORE_SURVIVE, **{
    'PROOF-6': fake_claude.change(
        'src/intake.py', STORED, STORED_WHEN_ACCEPTED,
        case=CASE_6_NOT_STORED, aim='past the test'),
})
SPEC_SCOPE = '> Scope: src/intake.py\n'


def _write(root, path, text):
    full = os.path.join(root, *path.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as handle:
        handle.write(text)


def _git(root, *args):
    return subprocess.run(('git', '-C', root) + args, check=True,
                          capture_output=True, text=True).stdout


def build(folder):
    """Write the project under `folder`, commit it and run its tests once.
    The project's root."""
    root = os.path.join(str(folder), 'project')
    _write(root, 'specs/intake/sample_intake.md', SPEC)
    _write(root, 'src/__init__.py', '')
    _write(root, 'src/intake.py', SOURCE)
    _write(root, 'tests/test_intake.py', TESTS)
    _write(root, '.purlin/config.json', json.dumps(
        {'version': '0.10.0', 'tests': [suites.pytest_suite()]}))
    _write(root, '.gitignore', '__pycache__/\n.purlin/runtime/\n')
    _git(root, 'init', '-q', '-b', 'main')
    _git(root, 'add', '-A')
    _git(root, '-c', 'user.name=Quinn', '-c',
         'user.email=quinn.qa@labconnect.example', '-c',
         'commit.gpgsign=false', 'commit', '-qm', 'chore: the sample lab')
    done = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', root, '--all',
         '--test'], capture_output=True, text=True, cwd=root)
    assert os.path.isfile(os.path.join(root, *EVIDENCE.split('/'))), \
        done.stdout + done.stderr
    return root


def audit(root, again=False):
    """`(exit code, printed lines)` of the audit over the sample lab."""
    out = io.StringIO()
    code = audit_run.run(root, None, [FEATURE], again=again, out=out)
    return code, out.getvalue().splitlines()


def entries(root, evidence=EVIDENCE):
    """`{rule: its audit entry}` as the project's evidence holds them."""
    with open(os.path.join(root, *evidence.split('/')),
              encoding='utf-8') as handle:
        return (json.load(handle).get('audit') or {}).get('rules') or {}


class Audited(object):
    """The sample lab after two audits: `first` and `again`, each with
    `code`, `lines`, `entries` and `calls`, the requests the fake took."""

    def __init__(self, root):
        self.root = root
        self.first = None
        self.again = None

    @staticmethod
    def request(run, rule):
        """The one request of `run` that asks about `rule`."""
        found = [call['prompt'] for call in run['calls']
                 if '\n%s %s\n' % (FEATURE, rule) in call['prompt']]
        assert len(found) == 1, (rule, len(found))
        return found[0]

    @staticmethod
    def under(run, rule):
        """The lines `run` printed under `rule`, without the rule's own."""
        lines = run['lines']
        start = [index for index, line in enumerate(lines)
                 if line.startswith('%s %s   ' % (FEATURE, rule))]
        assert len(start) == 1, (rule, lines)
        found = []
        for line in lines[start[0] + 1:]:
            if not line.startswith('  '):
                break
            found.append(line)
        return found


def audited(folder, reply=None):
    """Build the sample lab under `folder` and audit it twice with a fake
    `claude` that answers `reply`, `REPLY` by default. PATH is put back
    after."""
    folder = str(folder)
    root = build(folder)
    directory = fake_claude.install(os.path.join(folder, 'claude'),
                                    answers=[REPLY if reply is None
                                             else reply])
    previous = os.environ.get('PATH', '')
    os.environ['PATH'] = directory + os.pathsep + previous
    try:
        found = shutil.which('claude')
        assert found and os.path.realpath(found).startswith(
            os.path.realpath(folder)), found
        made = Audited(root)
        for name, again in (('first', False), ('again', True)):
            before = len(fake_claude.calls(directory))
            code, lines = audit(root, again=again)
            setattr(made, name, {
                'code': code, 'lines': lines, 'entries': entries(root),
                'calls': fake_claude.calls(directory)[before:]})
        return made
    finally:
        os.environ['PATH'] = previous


def _replace(root, path, old, new):
    full = os.path.join(root, *path.split('/'))
    with open(full, encoding='utf-8') as handle:
        text = handle.read()
    assert text.count(old) == 1, (path, old)
    with open(full, 'w', encoding='utf-8') as handle:
        handle.write(text.replace(old, new))


def strengthen(root):
    """Change the test of `PROOF-5` to expect the proof's own value, `25`."""
    _replace(root, 'tests/test_intake.py', FROM_THE_HELPER, THE_PROOFS_VALUE)


def expect_24(root):
    """Change the test of `PROOF-5` to expect `24`, so it fails."""
    _replace(root, 'tests/test_intake.py', FROM_THE_HELPER,
             THE_PROOFS_VALUE.replace('25', '24'))


def rewrite_the_helper(root):
    """Write the helper's one line as two, so the bug kept for `PROOF-5`
    names a line the file no longer holds."""
    _replace(root, 'src/intake.py', HELPER, HELPER_IN_TWO)


def change_both_tests_of_rule_4(root):
    """Change the test of `PROOF-7` to hand in a sample exactly 72 hours
    old, the proof's own case, and the test of `PROOF-6` to check only that
    a status is stored."""
    _replace(root, 'tests/test_intake.py', "at('2026-03-04T07:00'))",
             "at('2026-03-04T08:00'))")
    _replace(root, 'tests/test_intake.py',
             "    assert record['status'] == 'expired'",
             "    assert record['status']")


# The test of `PROOF-11` as it stands, which checks nothing, and as
# `purlin:build` strengthens it: the proof's two numbers.
PRINTS_THE_NUMBERS = "    print(first['accession'], second['accession'])\n"
CHECKS_THE_NUMBERS = (
    "    assert (first['accession'], second['accession']) == (\n"
    "        'BOS-2026-00001', 'BOS-2026-00002')\n")
# The end of the test of `PROOF-7`, and the same test with a check that
# cannot fail.
CHECKS_72 = ("at('2026-03-04T07:00'))\n"
             "    assert record['status'] == 'accepted'\n")
CANNOT_FAIL_72 = "at('2026-03-04T07:00'))\n    assert True\n"


def check_the_accession_numbers(root):
    """Change the test of `PROOF-11` to check the proof's two numbers."""
    _replace(root, 'tests/test_intake.py', PRINTS_THE_NUMBERS,
             CHECKS_THE_NUMBERS)


def check_nothing_at_72_hours(root):
    """Change the test of `PROOF-7` to end on `assert True`."""
    _replace(root, 'tests/test_intake.py', CHECKS_72, CANNOT_FAIL_72)


def check_the_status_at_72_hours(root):
    """Change the test of `PROOF-7` back to check the status `accepted`."""
    _replace(root, 'tests/test_intake.py', CANNOT_FAIL_72, CHECKS_72)


def hand_in_72_hours(root):
    """Change the test of `PROOF-7` to hand in a sample exactly 72 hours
    old, the proof's own case, and leave the test of `PROOF-6` as it is."""
    _replace(root, 'tests/test_intake.py', "at('2026-03-04T07:00'))",
             "at('2026-03-04T08:00'))")


# A defect fixed elsewhere in the code file: a site that is not three capital
# letters is refused. The helper moves one line down, and the lines the bugs
# on record change stand as they were.
SITE_PATTERN = "SITE = re.compile(r'^[A-Z]{3}$')\n"
SITE_CHECK = ("        if not SITE.match(site):\n"
              "            raise IntakeError('site %s is not three capital "
              "letters' % site)\n")
THE_AGE = '        age = age_hours(collected, received)\n'
THE_AGE_INLINE = ('        age = int((received - collected).total_seconds() '
                  '// 3600)\n')
# The module checks its own helper as it loads, so a bug in the helper stops
# the test file from being collected.
CHECKED_ON_LOAD = (
    "\n\nif age_hours(at('2026-03-01T08:00'), at('2026-03-02T09:30')) != 25:\n"
    "    raise RuntimeError('the age helper is wrong')\n")


def refuse_a_bad_site(root):
    """Change `src/intake.py` to refuse a site that is not three capital
    letters, and leave every test as it is."""
    _replace(root, 'src/intake.py', 'MAX_AGE_HOURS = 72\n',
             SITE_PATTERN + 'MAX_AGE_HOURS = 72\n')
    _replace(root, 'src/intake.py', '        if received < collected:\n',
             SITE_CHECK + '        if received < collected:\n')


def work_out_the_age_inline(root):
    """Change `intake` to work out the age itself, without the helper, and
    leave every test as it is: the test of `PROOF-5` still takes its expected
    age from the helper, so a bug in the helper now fails it."""
    _replace(root, 'src/intake.py', THE_AGE, THE_AGE_INLINE)


def check_the_helper_on_load(root):
    """Change `src/intake.py` to check its helper as it loads, and leave
    every test as it is: with a bug in the helper the module cannot be
    loaded, so the test of `PROOF-5` does not run."""
    path = os.path.join(root, 'src', 'intake.py')
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(CHECKED_ON_LOAD)


def scope_without_the_code(root):
    """Change the spec's `> Scope:` to name `src/__init__.py` alone, so the
    feature no longer covers `src/intake.py`."""
    _replace(root, 'specs/intake/sample_intake.md', SPEC_SCOPE,
             '> Scope: src/__init__.py\n')


def evidence_text(root):
    """The project's evidence file, as text."""
    with open(os.path.join(root, *EVIDENCE.split('/')),
              encoding='utf-8') as handle:
        return handle.read()


def run_script(root, directory, *args):
    """`purlin_run.py` with `args`, as its own process in the project, the
    fake `claude` of `directory` first on PATH. `(exit code, the lines it
    printed, the lines it wrote to its error output)`."""
    env = dict(os.environ)
    env['PATH'] = str(directory) + os.pathsep + env.get('PATH', '')
    done = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', root] + list(args),
        capture_output=True, text=True, cwd=root, env=env)
    return (done.returncode, done.stdout.splitlines(),
            done.stderr.splitlines())


class Settled(object):
    """The sample lab after its first audit and one more run of the script:
    `before`, the entries the first audit wrote; `args`, what the run was
    started with; `code`, `lines`, `errors`, `entries`, `calls` and `text`,
    the evidence file, after the run."""

    def __init__(self, root, directory):
        self.root = root
        self.directory = directory

    def under(self, rule):
        """The lines the run printed under `rule`, without the rule's own."""
        return Audited.under({'lines': self.lines}, rule)

    def rule_lines(self, rule):
        """The lines the audit printed that open `sample_intake <rule>   `."""
        return [line for line in self.lines
                if line.startswith('%s %s   ' % (FEATURE, rule))]


def settled(folder, rules=('RULE-3',), change=None, answers=(None,),
            exit_code=0, reply=None, sound=(), weaken=None):
    """Build the sample lab under `folder`, audit it once with `reply`,
    `REPLY` by default, make `change(root)`, then run the audit of
    `sample_intake` with `--settle` for each of `rules` (a plain audit for
    none) and `--sound` for each proof of `sound`, a fake `claude` answering
    `answers`. `weaken(root)` is a change made before the first audit, after
    which the tests run once more. No call reaches a real model."""
    folder = str(folder)
    root = build(folder)
    if weaken is not None:
        weaken(root)
        done = subprocess.run(
            [sys.executable, RUN_SCRIPT, '--project-root', root, '--all',
             '--test'], capture_output=True, text=True, cwd=root)
        assert done.returncode == 0, done.stdout + done.stderr
    directory = fake_claude.install(os.path.join(folder, 'claude'),
                                    answers=[REPLY if reply is None
                                             else reply])
    previous = os.environ.get('PATH', '')
    os.environ['PATH'] = directory + os.pathsep + previous
    try:
        found = shutil.which('claude')
        assert found and os.path.realpath(found).startswith(
            os.path.realpath(folder)), found
        code, lines = audit(root)
        assert code == 0, lines
    finally:
        os.environ['PATH'] = previous
    made = Settled(root, directory)
    made.before = entries(root)
    if change is not None:
        change(root)
    fake_claude.install(directory, answers=list(answers),
                        exit_code=exit_code)
    args = ['--audit', '--feature', FEATURE]
    for rule in rules:
        args += ['--settle', rule]
    for proof in sound:
        args += ['--sound', proof]
    made.args = args
    made.code, made.lines, made.errors = run_script(root, directory, *args)
    made.entries = entries(root)
    made.calls = fake_claude.calls(directory)
    made.text = evidence_text(root)
    return made


# ---------------------------------------------------------------------------
# The refusal note: a prompt, with one AI proof and one graded by an AI
# ---------------------------------------------------------------------------

NOTE_FEATURE = 'refusal_note'
NOTE_EVIDENCE = '.purlin/evidence/local/refusal_note.json'
MODEL = 'claude-opus-5-5'
GRADER = 'claude-haiku-4-5-20251001'

NOTE_SPEC = '''\
# Feature: refusal_note

> Description: The prompt that writes the note a site gets when the bench refuses a sample.
> Scope: prompts/refusal_note.md
> Stack: prompt
> Highest-Rule: 2
> Highest-Proof: 2

## Rules

- RULE-1: The note names the barcode of the sample that was refused
- RULE-2: The note tells the site what to do next

## Proof

- PROOF-1 (RULE-1): Given the refusal of `LC-1234567`, the reply names the barcode `LC-1234567` @ai(claude-opus-5-5)
- PROOF-2 (RULE-2): Given the refusal of `LC-1234567`, the reply tells the site to send a new sample @ai(claude-opus-5-5) @graded(claude-haiku-4-5-20251001)
'''

NOTE_PROMPT = '''\
Write the note a site gets when the bench refuses a sample. Name the sample's
barcode, say why it was refused, and tell the site to send a new sample.
'''

# What the AI is taken to have said, and the one file it wrote: for the test
# of `PROOF-1`, then for the test of `PROOF-2`, so the two outputs differ.
NOTE_NAMES = 'Sample LC-1234567 was refused: its barcode is not LC- and 8 digits.'
NOTE_NEXT = 'Send a new sample with a new label.'
NOTE = '%s\n%s\n' % (NOTE_NAMES, NOTE_NEXT)
NOTE_FILE = 'site: BOS\n'
NOTE_FILE_2 = 'site: NYC\n'
NOTE_TRANSCRIPT = '{"type": "result", "result": "the transcript line"}\n'

# The check of `PROOF-1` as it is written, which any barcode gets past, and
# as `purlin:build` strengthens it.
ANY_BARCODE = "    assert 'LC-' in note\n"
THE_BARCODE = "    assert 'LC-1234567' in note\n"

NOTE_TESTS = '''\
import os
import subprocess
import sys

NOTE = %r
SITE = %r
SECOND_SITE = %r
TRANSCRIPT = %r


def helper(*args):
    return subprocess.run([sys.executable, os.environ['PURLIN_AI']]
                          + list(args), capture_output=True, text=True)


def output(tmp_path, site=SITE):
    """The folder the helper hands back for the note."""
    made = tmp_path / 'made'
    (made / 'files').mkdir(parents=True)
    (made / 'reply.md').write_text(NOTE, encoding='utf-8')
    (made / 'files' / 'site.txt').write_text(site, encoding='utf-8')
    (made / 'transcript.jsonl').write_text(TRANSCRIPT, encoding='utf-8')
    done = helper('record', '--from', str(made))
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


# purlin: refusal_note PROOF-1
def test_the_note_names_the_barcode(tmp_path):
    folder = output(tmp_path)
    with open(os.path.join(folder, 'reply.md'), encoding='utf-8') as handle:
        note = handle.read()
%s

# purlin: refusal_note PROOF-2
def test_the_note_says_what_to_do_next(tmp_path):
    output(tmp_path, SECOND_SITE)
    graded = helper('grade', '--feature', 'refusal_note', '--proof', 'PROOF-2')
    assert graded.returncode == 0, graded.stdout + graded.stderr
''' % (NOTE, NOTE_FILE, NOTE_FILE_2, NOTE_TRANSCRIPT, ANY_BARCODE)

# The grader's two answers, and the wrong output asked for each proof: another
# sample's barcode, and a note that asks for nothing.
ACCEPT = 'accept: the note tells the site to send a new sample'
REJECT = 'reject: the note asks the site for nothing'
NOTE_OTHER = 'Sample LC-7654321 was refused: its barcode is not LC- and 8 digits.'
NOTE_NOTHING = 'Nothing more is needed.'
CASE_BARCODE = ('the refusal of `LC-1234567`; the proof says the reply names '
                '`LC-1234567`; the changed output names `LC-7654321`')
CASE_NEXT = ('the refusal of `LC-1234567`; the proof says the reply tells the '
             'site to send a new sample; the changed output asks for nothing')
NOTE_READING = '- PROOF-1: the test looks for `LC-` and not for the barcode.'


def wrong_outputs(first=None, second=None):
    """The reply that names one wrong output for each proof of the note, as
    one text both of the audit's requests are answered with. `first` and
    `second` stand in for the part of `PROOF-1` and of `PROOF-2`."""
    return fake_claude.reply({
        'PROOF-1': first or fake_claude.change(
            'reply.md', NOTE_NAMES, NOTE_OTHER, case=CASE_BARCODE,
            aim='past the test'),
        'PROOF-2': second or fake_claude.change(
            'reply.md', NOTE_NEXT, NOTE_NOTHING, case=CASE_NEXT,
            aim='plain')}, NOTE_READING)


def _with_fake(directory, answers):
    """The session fake in `directory` answering `answers`, and the
    environment that puts it first on PATH."""
    fake_claude_session.install(directory, answers=list(answers))
    return fake_claude_session.environment(directory)


def build_note(folder, check=ANY_BARCODE, runs=1):
    """Write the refusal note's project under `folder`, commit it and run
    its tests once, each AI proof `runs` times, the grader a fake that
    accepts. The project's root."""
    folder = str(folder)
    root = os.path.join(folder, 'project')
    _write(root, 'specs/notes/refusal_note.md', NOTE_SPEC)
    _write(root, 'prompts/refusal_note.md', NOTE_PROMPT)
    _write(root, 'tests/test_note.py', NOTE_TESTS.replace(ANY_BARCODE, check))
    _write(root, '.purlin/config.json', json.dumps(
        {'version': '0.10.0', 'tests': [suites.pytest_suite()],
         'runs': runs}))
    _write(root, '.gitignore', '__pycache__/\n.purlin/runtime/\n')
    _git(root, 'init', '-q', '-b', 'main')
    _git(root, 'add', '-A')
    _git(root, '-c', 'user.name=Quinn', '-c',
         'user.email=quinn.qa@labconnect.example', '-c',
         'commit.gpgsign=false', 'commit', '-qm', 'chore: the refusal note')
    done = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', root, '--all',
         '--test'], capture_output=True, text=True, cwd=root,
        env=_with_fake(os.path.join(folder, 'claude'), [ACCEPT]))
    assert done.returncode == 0, done.stdout + done.stderr
    return root


def note_claude(root):
    """The folder of the fake `claude` beside the note's project."""
    return os.path.join(os.path.dirname(root), 'claude')


def note_audit(root, answers, again=False):
    """Audit the refusal note with a fake `claude` answering `answers` in
    order: `{'code', 'lines', 'entries', 'calls'}`. PATH is put back after."""
    directory = note_claude(root)
    fake_claude_session.install(directory, answers=list(answers))
    previous = os.environ.get('PATH', '')
    os.environ['PATH'] = directory + os.pathsep + previous
    try:
        found = shutil.which('claude')
        assert found and os.path.realpath(found).startswith(
            os.path.realpath(os.path.dirname(root))), found
        out = io.StringIO()
        code = audit_run.run(root, None, [NOTE_FEATURE], again=again, out=out)
    finally:
        os.environ['PATH'] = previous
    return {'code': code, 'lines': out.getvalue().splitlines(),
            'entries': entries(root, NOTE_EVIDENCE),
            'calls': fake_claude_session.calls(directory)}


def note_settle(root, rules, answers=(ACCEPT,), sound=()):
    """Run the script's audit of the note with `--settle` for each of
    `rules`, as its own process: `{'code', 'lines', 'entries', 'calls'}`."""
    directory = note_claude(root)
    fake_claude_session.install(directory, answers=list(answers))
    args = ['--audit', '--feature', NOTE_FEATURE]
    for rule in rules:
        args += ['--settle', rule]
    for proof in sound:
        args += ['--sound', proof]
    code, lines, _errors = run_script(root, directory, *args)
    return {'code': code, 'lines': lines,
            'entries': entries(root, NOTE_EVIDENCE),
            'calls': fake_claude_session.calls(directory)}


def the_barcode(root):
    """Change the test of `PROOF-1` to look for the proof's own barcode."""
    _replace(root, 'tests/test_note.py', ANY_BARCODE, THE_BARCODE)


def note_under(run, rule):
    """The lines `run` printed under `rule` of the note."""
    lines = run['lines']
    start = [index for index, line in enumerate(lines)
             if line.startswith('%s %s   ' % (NOTE_FEATURE, rule))]
    assert len(start) == 1, (rule, lines)
    found = []
    for line in lines[start[0] + 1:]:
        if not line.startswith('  '):
            break
        found.append(line)
    return found


def note_runs(root, proof):
    """The runs the evidence holds for `proof` of the note on `MODEL`."""
    with open(os.path.join(root, *NOTE_EVIDENCE.split('/')),
              encoding='utf-8') as handle:
        data = json.load(handle)
    for section in (data.get('platforms') or {}).values():
        for listed in section.get('proofs') or ():
            if listed.get('id') == proof:
                return [made for model in listed.get('models') or ()
                        if model.get('model') == MODEL
                        for made in model.get('runs') or ()]
    return []
