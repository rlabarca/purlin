"""What the test skill, `skills/test/SKILL.md`, must name.

One test per proof of `specs/skills/skill_test.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.
"""

from skill_checks import copy_without, must_name, same_line, skill_path

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
