"""What the audit skill, `skills/audit/SKILL.md`, must name.

One test per proof of `specs/skills/skill_audit.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.

The last test is of an AI proof: it hands the sample lab of
`dev/sample_lab.py` to a real session with this repository as its plugin,
through the helper the run names in `PURLIN_AI`, and asserts on the folder
the helper prints. It skips where `PURLIN_AI` is not set, so this file run
by hand, and the sweep, reach no model.
"""

import os

import pytest

import sample_lab
from skill_checks import (copy_without, flat, must_name, not_named, read,
                          skill_path, under_heading)

SKILL = skill_path('audit')

COMMANDS = ('purlin:audit', 'purlin:audit --all',
            'purlin:audit <feature> RULE-N --settle', 'purlin:build')
PATHS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"',
         '.purlin/evidence/local/<feature>.json',
         'references/review_criteria.md')


# purlin: skill_audit PROOF-59
def test_a_reader_finds_each_command_and_path_named_the_settle_included():
    text = flat(read(SKILL))
    assert 'purlin:audit <feature> RULE-N --settle' in COMMANDS
    assert [name for name in COMMANDS + PATHS if name not in text] == []
    assert must_name('audit', commands=COMMANDS, paths=PATHS) == []


# purlin: skill_audit PROOF-56
def test_a_copy_without_the_criteria_is_reported():
    with copy_without(SKILL, 'references/review_criteria.md'):
        problems = must_name('audit', commands=COMMANDS, paths=PATHS)
    assert problems == ['audit does not name references/review_criteria.md']


CRITERIA = 'references/review_criteria.md'
SETTLE_LINES = ('the test now catches the bug it missed at',
                'did not break what the proof says. A new bug was planted.')


# purlin: skill_audit PROOF-60
def test_the_skill_and_the_criteria_hold_the_two_lines_a_settle_prints():
    assert not_named(read(SKILL), SETTLE_LINES) == []
    section = under_heading(read(CRITERIA), 'Settling a finding')
    assert not_named(section, SETTLE_LINES) == []


UNCHANGED_LINES = ('its test is as it was when the bug got past it. Strengthen '
                   'it with purlin:build, then settle.',
                   'was settled with its test unchanged: it was judged to '
                   'assert what the proof names.')


# purlin: skill_audit PROOF-61
def test_the_skill_and_the_criteria_hold_the_refusal_and_the_sound_sentence():
    assert not_named(read(SKILL), UNCHANGED_LINES) == []
    section = under_heading(read(CRITERIA), 'Settling a finding')
    assert not_named(section, UNCHANGED_LINES) == []


STILL_PASSES = ('its test is as it was and still passes with the bug it '
                'missed. Strengthen it with purlin:build.')


# purlin: skill_audit PROOF-62
def test_the_skill_and_the_criteria_hold_the_line_for_a_bug_planted_again():
    assert not_named(read(SKILL), (STILL_PASSES,)) == []
    section = under_heading(read(CRITERIA), 'The planted bug')
    assert not_named(section, (STILL_PASSES,)) == []


WRONG_OUTPUT = ('For an AI proof the planted bug is a wrong output, and '
                '`<file>` is a file of that output, as in `PROOF-4: the test '
                'still passes when reply.md:12 reads "Refund approved."`')


# purlin: skill_audit PROOF-63
def test_the_skill_says_what_is_planted_for_an_ai_proof():
    assert WRONG_OUTPUT in flat(read(SKILL))


needs_the_helper = pytest.mark.skipif(not os.environ.get('PURLIN_AI'),
                                      reason=sample_lab.NOT_STARTED)

AUDIT = 'Run purlin:audit sample_intake. Work only in this folder.'
EVIDENCE = '.purlin/evidence/local/sample_intake.json'


# purlin: skill_audit PROOF-64
@needs_the_helper
def test_a_session_runs_the_audit_and_names_the_build_for_a_weak_rule(
        tmp_path, no_real_model):
    root = sample_lab.for_a_session(tmp_path, audit_first=False)
    assert sample_lab.entries(root) == {}
    output = sample_lab.session(root, AUDIT, no_real_model)
    assert EVIDENCE in sample_lab.files_of(output)
    rules = sample_lab.entries(os.path.join(output, 'files'))
    assert rules['RULE-7']['verdict'] == 'weak'
    assert 'purlin:build sample_intake' in sample_lab.reply_of(output)
