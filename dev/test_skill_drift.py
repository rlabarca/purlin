"""Text checks for the drift skill, `skills/drift/SKILL.md`.

Every rule of `specs/skills/skill_drift.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

from skill_checks import (COMMAND_REF, carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems,
                          next_step_refusals, read, refusals, replace, resub,
                          skill_ceiling_problems, skill_path, table_rows,
                          undirected_outcome_problems)


class TestSkillDrift:

    # purlin: skill_drift PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('drift') == []

    # purlin: skill_drift PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        rel = skill_path('drift')
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:drift [role]` |'))
        assert frontmatter_refusals(monkeypatch, 'drift') == []
        assert refusals(monkeypatch, lambda: frontmatter_problems('drift'), [
            (rel, resub(r'^description: [^\n]*$', 'description: >-'),
             '%s frontmatter carries no one-line description' % rel),
            (rel, lambda t: '\n' + t,
             '%s does not open with a frontmatter block' % rel),
            (COMMAND_REF, replace(row, '| `purlin:drift [role]` | |'),
             '%s carries no row for purlin:drift' % COMMAND_REF),
        ]) == []

    # purlin: skill_drift PROOF-2
    def test_it_takes_its_data_from_the_tool(self):
        assert (carries(skill_path('drift'), [
            'drift(role="eng")', 'references/drift_criteria.md',
            'do not restate them here and do not invent a line the tool '
            'does not return']) + drift_restated_problems()) == []

    # purlin: skill_drift PROOF-2
    def test_a_restated_criterion_is_refused(self, monkeypatch):
        rel = skill_path('drift')
        source = 'Rules whose passed cell reads `no test`'
        assert refusals(monkeypatch, drift_restated_problems, [
            (rel, replace('## Step 2: print the view',
                          'A rule with no test: %s.\n\n## Step 2: print the '
                          'view' % source),
             '%s restates what references/drift_criteria.md says a line is '
             'built from: %r' % (rel, source)),
        ]) == []

    # purlin: skill_drift PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('drift')
                + undirected_outcome_problems('drift')) == []

    # purlin: skill_drift PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        rel = skill_path('drift')
        last = read(rel).rindex('\n## ')
        assert next_step_refusals(
            monkeypatch, 'drift', '| A rule removed',
            '| A rule removed | `→ Run: purlin:status <feature>` |') == []
        # A table with its header and divider and no row lists no outcome.
        assert refusals(monkeypatch, lambda: next_step_problems('drift'), [
            (rel, lambda t: t[:t.index('| A rule added', last)],
             '%s closing section names 0 outcomes, expected at least 2'
             % rel),
        ]) == []

    # purlin: skill_drift PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('drift') == []


def drift_restated_problems():
    """The skill restates none of the git facts the criteria say each `eng`
    and `qa` line is built from, the `From` cell of their tables."""
    rel, criteria = skill_path('drift'), 'references/drift_criteria.md'
    header = '| Key | From | Line |'
    sources = [cells[1] for chunk in read(criteria).split(header)[1:]
               for cells in table_rows(header + chunk, header)]
    if len(sources) < 2:
        return ['%s has %d rows naming what a line is built from, expected '
                'the eng and qa tables' % (criteria, len(sources))]
    text = flat(read(rel))
    return ['%s restates what %s says a line is built from: %r'
            % (rel, criteria, source) for source in sources
            if flat(source) in text]
