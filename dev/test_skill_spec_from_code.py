"""What the spec-from-code skill, `skills/spec-from-code/SKILL.md`, must name.

One test for the one proof of `specs/skills/skill_spec_from_code.md`. The
check is `must_name` in `dev/skill_checks.py`.
"""

from skill_checks import (flat, must_name, not_named, read, skill_path,
                          under_heading)

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


INSTRUCTIONS = ('**Stop and ask** which model or models each is shown on',
                'Write no test for one: `purlin:build` does.',
                'A rule read from instructions says what they ask for, not '
                'what the AI does.')


# purlin: skill_spec_from_code PROOF-168
def test_the_part_on_prompts_asks_the_model_writes_no_test_and_says_so():
    section = under_heading(read(SKILL),
                            'Prompts, skills and agent definitions')
    assert section
    assert not_named(section, INSTRUCTIONS) == []
