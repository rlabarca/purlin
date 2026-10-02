"""What the build skill, `skills/build/SKILL.md`, must name.

One test for the one proof of `specs/skills/skill_build.md`. The check is
`must_name` in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path

SKILL = skill_path('build')

COMMANDS = ('sync_status', 'purlin:test', 'purlin:test --all --commit',
            'purlin:spec', 'purlin:audit <feature> RULE-N --settle')
FILES = ('scripts/purlin_python.sh', 'scripts/mcp/purlin/markers.py',
         'scripts/mcp/purlin/wording.py', 'references/commit_conventions.md',
         'references/review_criteria.md')


# purlin: skill_build PROOF-51
def test_the_build_skill_holds_each_command_and_file_the_settle_included():
    text = flat(read(SKILL))
    assert 'purlin:audit <feature> RULE-N --settle' in COMMANDS
    assert 'references/review_criteria.md' in FILES
    assert [name for name in COMMANDS + FILES if name not in text] == []
    assert must_name('build', commands=COMMANDS, paths=FILES) == []
