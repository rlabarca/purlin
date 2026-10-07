"""What the status skill, `skills/status/SKILL.md`, must name.

One test per proof of `specs/skills/skill_status.md`. The check is
`must_name` in `dev/skill_checks.py`; a copy of the skill with one name taken
out is read through `copy_without`, and the file on disk is never touched.
The example of one spec's view is held to what the status script prints for a
sample project in the state it shows.
"""

import os
import re
import subprocess
import sys

import skill_checks
from mcp_project import (OPUS, PROJECT_ROOT, SONNET, Project, _ai_entry,
                         _commit_tests, _entry, _model, ai_spec,
                         spec_with_a_hand_check)
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


# ---------------------------------------------------------------------------
# With a name: one spec's view
# ---------------------------------------------------------------------------

STATUS_PY = os.path.join(PROJECT_ROOT, 'scripts', 'run', 'purlin_status.py')


def _with_a_name(text):
    """The skill's part `With a name`, from its heading to the next."""
    start = text.index('\n## With a name\n')
    end = text.find('\n## ', start + 1)
    return text[start:end if end >= 0 else len(text)]


def _example(text, at=0):
    """The lines of one code block of the part `With a name` that names no
    language, the first where `at` is 0: an example of what the script
    prints."""
    blocks = re.findall(r'^```(\w*)\n(.*?)^```', _with_a_name(text),
                        re.MULTILINE | re.DOTALL)
    return [body for language, body in blocks
            if not language][at].rstrip('\n').splitlines()


def _printed(made):
    """What `purlin_status.py --spec login` prints for the project `made`,
    which is closed."""
    try:
        result = subprocess.run(
            [sys.executable, STATUS_PY, '--project-root', made.root,
             '--spec', 'login'], capture_output=True, text=True,
            encoding='utf-8', cwd=made.root, stdin=subprocess.DEVNULL,
            timeout=180)
    finally:
        made.close()
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.rstrip('\n').splitlines()


def _printed_for_the_example():
    """What `purlin_status.py --spec login` prints for `login` of 3 rules:
    `RULE-1` tested, passing and found strong, `RULE-2` with no test, and
    `RULE-3` whose one proof is `@manual`."""
    made = Project(spec=spec_with_a_hand_check(3))
    try:
        _commit_tests(made, 'PROOF-1')
        made.evidence([_entry('PROOF-1', 'RULE-1')])
        made.audit('RULE-1')
    except Exception:
        made.close()
        raise
    return _printed(made)


def _printed_for_the_ai_example():
    """What it prints for `login` of 2 rules whose `PROOF-2` is an AI proof
    naming two models: passed 3 of 3 on the first, not run on the second."""
    made = Project(spec=ai_spec('@ai(%s, %s)' % (OPUS, SONNET)))
    try:
        _commit_tests(made, 'PROOF-1', 'PROOF-2')
        made.evidence([_entry('PROOF-1', 'RULE-1'),
                       _ai_entry('PROOF-2', 'RULE-2',
                                 _model(OPUS, 'pass', 'pass', 'pass'),
                                 status='not run')])
    except Exception:
        made.close()
        raise
    return _printed(made)


# purlin: skill_status PROOF-43
def test_the_part_with_a_name_gives_the_command_with_spec():
    part = _with_a_name(skill_checks.read(SKILL))
    assert [line for line in part.splitlines()
            if 'scripts/run/purlin_status.py' in line
            and '--spec <name>' in line], part


# purlin: skill_status PROOF-44
def test_a_copy_without_spec_name_holds_no_such_line():
    with copy_without(SKILL, '--spec <name>'):
        part = _with_a_name(skill_checks.read(SKILL))
    assert [line for line in part.splitlines()
            if 'scripts/run/purlin_status.py' in line
            and '--spec <name>' in line] == []


# purlin: skill_status PROOF-45
def test_the_example_is_what_the_script_prints():
    assert _example(skill_checks.read(SKILL), 0) == _printed_for_the_example()


# purlin: skill_status PROOF-46
def test_a_copy_with_one_word_changed_differs():
    text = skill_checks.read(SKILL)
    assert 'PROOF-1  passed' in _with_a_name(text)
    changed = text.replace('PROOF-1  passed', 'PROOF-1  passing')
    assert _example(changed) != _printed_for_the_example()


# purlin: skill_status PROOF-47
def test_the_second_example_is_what_the_script_prints_for_an_ai_proof():
    assert (_example(skill_checks.read(SKILL), 1)
            == _printed_for_the_ai_example())


# purlin: skill_status PROOF-48
def test_a_copy_with_one_count_changed_differs():
    text = skill_checks.read(SKILL)
    assert '0 of 3 on claude-sonnet-5-5' in _with_a_name(text)
    changed = text.replace('0 of 3 on claude-sonnet-5-5',
                           '1 of 3 on claude-sonnet-5-5')
    assert _example(changed, 1) != _printed_for_the_ai_example()


GRADED_SUMMARY = '40 rules. 40 pass their tests, 6 of them graded by an AI.'
ON_A_MODEL = ('<n> rules to test on <model>', '→ Run: purlin:test --all')


# purlin: skill_status PROOF-49
def test_the_skill_shows_the_graded_summary_and_the_row_for_a_model():
    lines = read(SKILL).splitlines()
    assert GRADED_SUMMARY in lines
    rows = [line for line in lines if line.startswith('|')
            and all(name in line for name in ON_A_MODEL)]
    assert len(rows) == 1, rows
