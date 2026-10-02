"""What the status skill, `skills/status/SKILL.md`, must name.

One test per proof of `specs/skills/skill_status.md`. The check is
`must_name` in `dev/skill_checks.py`; a copy of the skill with one name taken
out is read through `copy_without`, and the file on disk is never touched.
"""

from skill_checks import (copy_without, flat, must_name, read,
                          sentences_with, skill_path)

SKILL = skill_path('status')

COMMANDS = ('purlin:status', 'purlin:spec', 'purlin:build', 'purlin:test',
            'purlin:test --commit', 'purlin:sign')
PATHS = ('references/purlin_commands.md', 'skills/spec/SKILL.md')
# When the line for results that are not committed shows.
NOT_COMMITTED = ('features whose results are not committed',
                 'shows only once nothing else stops the tests being met')


# purlin: skill_status PROOF-37
def test_the_status_skill_names_each_of_its_six_commands():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS if name not in text] == []
    assert must_name('status', commands=COMMANDS) == []


# purlin: skill_status PROOF-38
def test_a_copy_without_the_sign_command_is_reported():
    with copy_without(SKILL, 'purlin:sign'):
        problems = must_name('status', commands=COMMANDS, paths=PATHS)
    assert problems == ['status does not name purlin:sign']


# purlin: skill_status PROOF-39
def test_the_status_skill_names_its_two_paths():
    text = flat(read(SKILL))
    assert [name for name in PATHS if name not in text] == []
    assert must_name('status', paths=PATHS) == []


# purlin: skill_status PROOF-41
def test_one_sentence_says_when_the_uncommitted_results_line_shows():
    assert len(sentences_with(SKILL, NOT_COMMITTED)) == 1


# purlin: skill_status PROOF-42
def test_a_copy_without_those_words_holds_no_such_sentence():
    with copy_without(SKILL, NOT_COMMITTED[1]):
        assert sentences_with(SKILL, NOT_COMMITTED) == []
