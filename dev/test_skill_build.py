"""What the build skill, `skills/build/SKILL.md`, must name.

One test per proof of `specs/skills/skill_build.md`. The check is `must_name`
in `dev/skill_checks.py`.
"""

import re

from skill_checks import flat, must_name, not_named, read, skill_path

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


def under_heading(text, heading):
    """The part of a Markdown text under the heading `heading`, up to the
    next heading of the same or a higher level; empty where there is none."""
    found = re.search(r'^(#+) %s\n' % re.escape(heading), text, re.M)
    if not found:
        return ''
    rest = text[found.end():]
    end = re.search(r'^#{1,%d} ' % len(found.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


# purlin: skill_build PROOF-52
def test_the_build_skill_says_how_a_test_left_alone_is_settled():
    section = under_heading(read(SKILL), 'Strengthening a weak rule')
    assert section
    assert not_named(section, SOUND) == []
