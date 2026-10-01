"""What the drift skill, `skills/drift/SKILL.md`, must name.

One test per proof of `specs/skills/skill_drift.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.
"""

from skill_checks import copy_without, flat, must_name, read, skill_path

SKILL = skill_path('drift')

COMMANDS = ('purlin:drift', 'purlin:spec', 'purlin:build',
            'purlin:anchor sync', 'git fetch')
PATHS = ('references/drift_criteria.md',)


# purlin: skill_drift PROOF-46
def test_the_drift_skill_names_its_commands_and_its_criteria():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS + PATHS if name not in text] == []
    assert must_name('drift', commands=COMMANDS, paths=PATHS) == []


# purlin: skill_drift PROOF-43
def test_a_copy_without_the_spec_command_is_reported():
    with copy_without(SKILL, 'purlin:spec'):
        problems = must_name('drift', commands=COMMANDS, paths=PATHS)
    assert problems == ['drift does not name purlin:spec']
