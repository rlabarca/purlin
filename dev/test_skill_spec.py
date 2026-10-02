"""What the spec skill, `skills/spec/SKILL.md`, must name and say.

One test for each proof of `specs/skills/skill_spec.md`. The check of the
names is `must_name` in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path

SKILL = skill_path('spec')

COMMANDS = ('sync_status', 'purlin:build', 'purlin:drift')
FILES = ('scripts/purlin_python.sh', 'scripts/spec/renumber.py',
         'references/spec_quality_guide.md',
         'references/formats/spec_format.md',
         'references/commit_conventions.md')


# purlin: skill_spec PROOF-62
def test_the_spec_skill_holds_each_command_and_file():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS + FILES if name not in text] == []
    assert must_name('spec', commands=COMMANDS, paths=FILES) == []


WHERE_THE_LINES_GO = (
    'In a spec that has neither line, both go after the last `>` line of '
    'the header: `> Highest-Rule:` first, then `> Highest-Proof:`.')


# purlin: skill_spec PROOF-63
def test_the_spec_skill_says_where_the_two_highest_lines_go():
    text = read(SKILL)
    ids = text[text.index('\n## Ids\n'):]
    ids = ids[:ids.index('\n## ', 1)]
    assert WHERE_THE_LINES_GO in flat(ids)
