"""What the audit skill, `skills/audit/SKILL.md`, must name.

One test per proof of `specs/skills/skill_audit.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.
"""

from skill_checks import copy_without, flat, must_name, read, skill_path

SKILL = skill_path('audit')

COMMANDS = ('purlin:audit', 'purlin:audit --all', 'purlin:build')
PATHS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"',
         '.purlin/evidence/local/<feature>.json',
         'references/review_criteria.md')


# purlin: skill_audit PROOF-59
def test_a_reader_finds_each_command_and_path_named():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS + PATHS if name not in text] == []
    assert must_name('audit', commands=COMMANDS, paths=PATHS) == []


# purlin: skill_audit PROOF-56
def test_a_copy_without_the_criteria_is_reported():
    with copy_without(SKILL, 'references/review_criteria.md'):
        problems = must_name('audit', commands=COMMANDS, paths=PATHS)
    assert problems == ['audit does not name references/review_criteria.md']
