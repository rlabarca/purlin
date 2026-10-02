"""What the audit skill, `skills/audit/SKILL.md`, must name.

One test per proof of `specs/skills/skill_audit.md`. The check is `must_name`
in `dev/skill_checks.py`; a copy of the skill with one name taken out is read
through `copy_without`, and the file on disk is never touched.
"""

import re

from skill_checks import (copy_without, flat, must_name, not_named, read,
                          skill_path)

SKILL = skill_path('audit')

COMMANDS = ('purlin:audit', 'purlin:audit --all',
            'purlin:audit <feature> RULE-N --settle', 'purlin:build')
PATHS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"',
         '.purlin/evidence/local/<feature>.json',
         'references/review_criteria.md')


# purlin: skill_audit PROOF-59
def test_a_reader_finds_each_command_and_path_named_the_settle_included():
    text = flat(read(SKILL))
    assert 'purlin:audit <feature> RULE-N --settle' in COMMANDS
    assert [name for name in COMMANDS + PATHS if name not in text] == []
    assert must_name('audit', commands=COMMANDS, paths=PATHS) == []


# purlin: skill_audit PROOF-56
def test_a_copy_without_the_criteria_is_reported():
    with copy_without(SKILL, 'references/review_criteria.md'):
        problems = must_name('audit', commands=COMMANDS, paths=PATHS)
    assert problems == ['audit does not name references/review_criteria.md']


CRITERIA = 'references/review_criteria.md'
SETTLE_LINES = ('the test now catches the bug it missed at',
                'did not break what the proof says. A new bug was planted.')


def under_heading(text, heading):
    """The part of a Markdown text under the heading `heading`, up to the
    next heading of the same or a higher level; empty where there is none."""
    found = re.search(r'^(#+) %s\n' % re.escape(heading), text, re.M)
    if not found:
        return ''
    rest = text[found.end():]
    end = re.search(r'^#{1,%d} ' % len(found.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


# purlin: skill_audit PROOF-60
def test_the_skill_and_the_criteria_hold_the_two_lines_a_settle_prints():
    assert not_named(read(SKILL), SETTLE_LINES) == []
    section = under_heading(read(CRITERIA), 'Settling a finding')
    assert not_named(section, SETTLE_LINES) == []
