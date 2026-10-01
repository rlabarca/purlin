"""What the sign skill, `skills/sign/SKILL.md`, must name.

One test per proof of `specs/skills/skill_sign.md`. The check is `must_name`
in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path

SKILL = skill_path('sign')

COMMANDS = ('purlin:sign', '--show', '--answers', '--check', '--version',
            'purlin:test --all --commit', 'purlin:test --remote',
            'git push origin')
PATHS = ('scripts/review/sign.py', '.purlin/runtime/signoff-answers.json',
         '.purlin/evidence/package/<version>.json', 'VERSION')


# purlin: skill_sign PROOF-63
def test_the_sign_skill_holds_each_command_it_must_name():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS if name not in text] == []
    assert must_name('sign', commands=COMMANDS) == []


# purlin: skill_sign PROOF-64
def test_the_sign_skill_holds_each_path_it_must_name():
    text = flat(read(SKILL))
    assert [name for name in PATHS if name not in text] == []
    assert must_name('sign', paths=PATHS) == []
