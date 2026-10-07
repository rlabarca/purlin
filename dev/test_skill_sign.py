"""What the sign skill, `skills/sign/SKILL.md`, must name.

One test per proof of `specs/skills/skill_sign.md`. The check is `must_name`
in `dev/skill_checks.py`, and the lines the skill shows are compared with
the ones `scripts/review/sign.py` prints.
"""

import os
import sys

from skill_checks import flat, must_name, read, skill_path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scripts', 'review'))
import sign  # noqa: E402

SKILL = skill_path('sign')

COMMANDS = ('purlin:sign', '--show', '--answers', '--check', '--version',
            'purlin:test --all --commit', 'git push origin')
PATHS = ('scripts/review/sign.py', '.purlin/runtime/signoff-answers.json',
         '.purlin/evidence/package/<version>.json', 'VERSION')


# purlin: skill_sign PROOF-63
def test_the_sign_skill_holds_each_of_its_seven_commands():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS if name not in text] == []
    assert must_name('sign', commands=COMMANDS) == []


# purlin: skill_sign PROOF-64
def test_the_sign_skill_holds_each_path_it_must_name():
    text = flat(read(SKILL))
    assert [name for name in PATHS if name not in text] == []
    assert must_name('sign', paths=PATHS) == []


def blocks(text):
    """Each fenced block of a Markdown text, as its lines, indentation
    kept."""
    found, block = [], None
    for line in text.splitlines():
        if line.startswith('```'):
            if block is None:
                block = []
            else:
                found.append(block)
                block = None
        elif block is not None:
            block.append(line)
    return found


def in_order(block, lines):
    """True where the block holds each of `lines` as a whole line, in that
    order."""
    at = -1
    for line in lines:
        if line not in block[at + 1:]:
            return False
        at = block.index(line, at + 1)
    return True


WALK_LINES = ['AI proofs run on claude-opus-5-5: 12 proofs, 5 runs each.',
              '  Graded by an AI: 6 proofs, by claude-haiku-4-5-20251001.',
              '  AI outputs kept with the package: 60 of 60.',
              "The audit's findings: 1 weak, 6 proofs graded by an AI."]


# purlin: skill_sign PROOF-66
def test_the_sign_skill_shows_the_walks_four_lines_about_ai_proofs():
    found = [block for block in blocks(read(SKILL))
             if in_order(block, WALK_LINES)]
    assert len(found) == 1, found
    # A line with another indent, or the lines in another order, is not it.
    assert not in_order([line.strip() for line in found[0]], WALK_LINES)
    assert not in_order(found[0], WALK_LINES[::-1])
    # They are the walk's own lines with these values.
    assert WALK_LINES == [
        sign.MODEL_LINE % ('claude-opus-5-5', '12 proofs', '5 runs'),
        sign.OVERVIEW_GRADED % ('6 proofs', 'claude-haiku-4-5-20251001'),
        sign.OVERVIEW_AI_OUTPUTS % (60, 60),
        sign.AUDIT_SHOWN % ', '.join(['1 weak', sign.GRADED_MANY % 6])]


CHECK_LINE = 'AI outputs beside the package that match their sha256: 59 of 60.'
GRADED_RUN = ('  refund_skill RULE-3: PROOF-6 on claude-opus-5-5, run 1 of 5, '
              'accepted by claude-haiku-4-5-20251001: The reply refuses, gives '
              'the limit as the reason and blames nobody.')


# purlin: skill_sign PROOF-67
def test_the_sign_skill_shows_the_check_line_and_one_graded_run():
    lines = [line for block in blocks(read(SKILL)) for line in block]
    assert lines.count(CHECK_LINE) == 1, CHECK_LINE
    assert lines.count(GRADED_RUN) == 1, GRADED_RUN
    assert CHECK_LINE == sign.AI_OUTPUTS_MATCH % (59, 60)
    assert GRADED_RUN == sign.AUDIT_GRADED % (
        'refund_skill', 'RULE-3', 'PROOF-6', 'claude-opus-5-5', 1, 5,
        sign.GRADE_WORDS[True], 'claude-haiku-4-5-20251001',
        'The reply refuses, gives the limit as the reason and blames nobody.')
