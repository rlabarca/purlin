"""What the test skill, `skills/test/SKILL.md`, must name.

One test per proof of `specs/skills/skill_test.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.
"""

from skill_checks import copy_without, must_name, skill_path

SKILL = skill_path('test')

COMMANDS = ('purlin:test --all --commit',)
PATHS = ('scripts/run/purlin_run.py', '.purlin/evidence/local/<feature>.json',
         '.purlin/config.json', 'references/evidence_and_signoff.md')


# purlin: skill_test PROOF-55
def test_the_shipped_skill_file_names_its_command_and_four_paths():
    assert must_name('test', commands=COMMANDS, paths=PATHS) == []


# purlin: skill_test PROOF-52
def test_a_copy_without_the_evidence_and_signoff_reference_is_reported():
    with copy_without(SKILL, 'references/evidence_and_signoff.md'):
        problems = must_name('test', commands=COMMANDS, paths=PATHS)
    assert problems == [
        'test does not name references/evidence_and_signoff.md']
