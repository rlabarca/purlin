"""What the spec-from-code skill, `skills/spec-from-code/SKILL.md`, must name.

One test for the one proof of `specs/skills/skill_spec_from_code.md`. The
check is `must_name` in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path

SKILL = skill_path('spec-from-code')

COMMANDS = ('sync_status', 'purlin:init', 'purlin:anchor create',
            'purlin:build', 'purlin:test')
FILES = ('.purlin/runtime/spec-from-code.json',
         'references/spec_quality_guide.md',
         'references/formats/spec_format.md',
         'references/commit_conventions.md')


# purlin: skill_spec_from_code PROOF-167
def test_the_spec_from_code_skill_holds_each_command_and_file():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS + FILES if name not in text] == []
    assert must_name('spec-from-code', commands=COMMANDS, paths=FILES) == []
