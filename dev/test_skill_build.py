"""What the build skill, `skills/build/SKILL.md`, must name.

One test per proof of `specs/skills/skill_build.md`. The check is `must_name`
in `dev/skill_checks.py`.
"""

from skill_checks import (flat, must_name, not_named, read, skill_path,
                          under_heading)

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


SOUND = ('purlin:audit <feature> RULE-N --settle --sound PROOF-N',
         'Never pass it for a test you did not read against its proof')


# purlin: skill_build PROOF-52
def test_the_build_skill_says_how_a_test_left_alone_is_settled():
    section = under_heading(read(SKILL), 'Strengthening a weak rule')
    assert section
    assert not_named(section, SOUND) == []


AI_TEST = ('references/purlin_commands.md', 'references/rule_examples.md',
           'One test makes one output.',
           "A graded proof's test then starts `grade` and asserts it exits 0.",
           'The test passes or skips when `PURLIN_AI` is not set')


# purlin: skill_build PROOF-53
def test_the_build_skill_says_how_the_test_of_an_ai_proof_is_written():
    section = under_heading(read(SKILL), 'The test of an AI proof')
    assert section
    assert not_named(section, AI_TEST) == []


SAYS_FIRST = ('Run `purlin:test --all` once the test is written, and say '
              'first that it reaches a real model and takes minutes.')


# purlin: skill_build PROOF-54
def test_the_build_skill_runs_the_full_run_and_says_so_first():
    section = under_heading(read(SKILL), 'The test of an AI proof')
    assert SAYS_FIRST in flat(section)
