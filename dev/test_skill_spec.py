"""What the spec skill, `skills/spec/SKILL.md`, must name and say.

One test for each proof of `specs/skills/skill_spec.md`. The check of the
names is `must_name` in `dev/skill_checks.py`.
"""

from skill_checks import flat, must_name, read, skill_path, under_heading

SKILL = skill_path('spec')

COMMANDS = ('sync_status', 'purlin:build', 'purlin:drift')
FILES = ('scripts/purlin_python.sh', 'scripts/spec/renumber.py',
         'references/spec_quality_guide.md',
         'references/formats/spec_format.md',
         'references/commit_conventions.md')


# purlin: skill_spec PROOF-62
def test_the_spec_skill_holds_each_command_and_file():
    text = flat(read(SKILL))
    assert [name for name in COMMANDS + FILES if name not in text] == []
    assert must_name('spec', commands=COMMANDS, paths=FILES) == []


WHERE_THE_LINES_GO = (
    'In a spec that has neither line, both go after the last `>` line of '
    'the header: `> Highest-Rule:` first, then `> Highest-Proof:`.')


# purlin: skill_spec PROOF-63
def test_the_spec_skill_says_where_the_two_highest_lines_go():
    text = read(SKILL)
    ids = text[text.index('\n## Ids\n'):]
    ids = ids[:ids.index('\n## ', 1)]
    assert WHERE_THE_LINES_GO in flat(ids)


AI_LINES = (
    '- PROOF-9 (RULE-9): With the sample report, the reply names the three '
    'findings by their ids @ai(claude-opus-5-5)',
    '- PROOF-10 (RULE-10): Asked for a refund over the limit, the reply '
    'refuses and blames nobody @ai(claude-opus-5-5) '
    '@graded(claude-haiku-4-5-20251001)')
ASKS = ('Where a sentence about what an AI does could be checked exactly, '
        'graded or by hand, **Stop and ask** which.',
        'Never pick a model yourself: the model is what is being validated.')


def _proofs():
    return under_heading(read(SKILL), 'Proofs')


# purlin: skill_spec PROOF-64
def test_the_part_on_proofs_shows_the_two_tags_with_their_models():
    lines = _proofs().splitlines()
    assert [line for line in AI_LINES if line not in lines] == []


# purlin: skill_spec PROOF-65
def test_the_part_on_proofs_asks_which_check_and_picks_no_model():
    part = flat(_proofs())
    assert [sentence for sentence in ASKS if sentence not in part] == []
