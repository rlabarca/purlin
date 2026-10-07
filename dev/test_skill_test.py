"""What the test skill, `skills/test/SKILL.md`, must name.

One test per proof of `specs/skills/skill_test.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.
"""

from skill_checks import (copy_without, flat, must_name, read, same_line,
                          skill_path)

SKILL = skill_path('test')

COMMANDS = ('purlin:test --all --commit',)
PATHS = ('scripts/run/purlin_run.py', '.purlin/evidence/local/<feature>.json',
         '.purlin/config.json', 'references/evidence_and_signoff.md')
# The hand-off as the run script takes it, on one line.
HAND_OFF = ('scripts/run/purlin_run.py', '--test', '--all', '--commit')


# purlin: skill_test PROOF-55
def test_the_shipped_skill_file_names_its_command_and_four_paths():
    assert must_name('test', commands=COMMANDS, paths=PATHS) == []


# purlin: skill_test PROOF-52
def test_a_copy_without_the_evidence_and_signoff_reference_is_reported():
    with copy_without(SKILL, 'references/evidence_and_signoff.md'):
        problems = must_name('test', commands=COMMANDS, paths=PATHS)
    assert problems == [
        'test does not name references/evidence_and_signoff.md']


# purlin: skill_test PROOF-56
def test_one_line_passes_commit_to_the_run_script():
    assert same_line(SKILL, HAND_OFF) == []


# purlin: skill_test PROOF-57
def test_a_copy_that_passes_no_commit_is_reported():
    with copy_without(SKILL, '--test --all --commit'):
        problems = same_line(SKILL, HAND_OFF)
    assert problems == [
        "skills/test/SKILL.md has no single line carrying all of "
        "'scripts/run/purlin_run.py', '--test', '--all', '--commit'"]


AI_LINES = ('Running <feature> <PROOF-N> on <model>, <i> of <n>',
            '<model>: model not reached. <why>. Run purlin:test --all.',
            '<n> rules to test on <model>: purlin:test --all')


# purlin: skill_test PROOF-58
def test_the_skill_shows_the_three_lines_a_run_prints_about_an_ai_proof():
    text = flat(read(SKILL))
    assert [line for line in AI_LINES if '`%s`' % line not in text] == []


NOT_REACHED = (
    "Check that `claude` is logged in and that the proof's tag spells the "
    "model's name as the model is named, then run `purlin:test --all` again.",
    'It is never a failure: never change the code or the test for it, and '
    'never reword the proof.')


FULL_RUN = (
    'A full run with AI proofs outlasts one command: start it in the '
    'background, and say first that it reaches real models and takes '
    'minutes. Then wait for it to end and read its last lines before you '
    'say anything is done. The work is not finished while the run is going: '
    'never end a reply on a run still in progress.')


# purlin: skill_test PROOF-60
def test_the_skill_waits_for_a_full_run_to_end():
    assert FULL_RUN in flat(read(SKILL))


# purlin: skill_test PROOF-59
def test_the_skill_says_what_to_do_about_a_model_not_reached():
    text = flat(read(SKILL))
    assert [sentence for sentence in NOT_REACHED if sentence not in text] == []
