"""What the sign skill, `skills/sign/SKILL.md`, must name.

One test per proof of `specs/skills/skill_sign.md`. The check is `must_name`
in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path

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


AI_LINES = ('AI proofs run on claude-opus-5-5: 12 proofs, 5 runs each.',
            'Graded by an AI: 6 proofs, by claude-haiku-4-5-20251001.')


# purlin: skill_sign PROOF-66
def test_the_sign_skill_shows_the_two_lines_about_ai_proofs():
    lines = [line.strip() for line in read(SKILL).splitlines()]
    assert [line for line in AI_LINES if line not in lines] == []
