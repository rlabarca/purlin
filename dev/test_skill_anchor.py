"""What the anchor skill, `skills/anchor/SKILL.md`, must name.

One test per proof of `specs/skills/skill_anchor.md`. The check is
`must_name` in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path

SKILL = skill_path('anchor')

COMMANDS = ('purlin:anchor create', 'purlin:anchor sync', 'purlin:drift',
            'purlin:spec', 'purlin:status')
FILES = ('scripts/purlin_python.sh', 'scripts/anchor/upstream.py',
         'specs/_anchors/', 'references/formats/anchor_format.md',
         'references/spec_quality_guide.md',
         'references/commit_conventions.md')


# purlin: skill_anchor PROOF-2
def test_the_anchor_skill_holds_each_of_its_six_files():
    text = flat(read(SKILL))
    assert [name for name in FILES if name not in text] == []
    assert must_name('anchor', paths=FILES) == []


# purlin: skill_anchor PROOF-16
def test_the_anchor_skill_holds_each_of_its_five_commands():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS if name not in text] == []
    assert must_name('anchor', commands=COMMANDS) == []
