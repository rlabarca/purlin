"""Text checks for the status skill, `skills/status/SKILL.md`.

Every rule of `specs/skills/skill_status.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems,
                          next_step_refusals, read, refusals, replace, resub,
                          section, skill_ceiling_problems, skill_path,
                          undirected_outcome_problems)


class TestSkillStatus:

    # purlin: skill_status PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('status') == []

    # purlin: skill_status PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        rel = skill_path('status')
        assert frontmatter_refusals(monkeypatch, 'status') == []
        assert refusals(monkeypatch, lambda: frontmatter_problems('status'), [
            (rel, resub(r'^description: [^\n]*$', 'description: ""'),
             '%s frontmatter carries no one-line description' % rel),
        ]) == []

    # purlin: skill_status PROOF-2
    def test_it_prints_the_numbers_the_tool_returned(self):
        assert status_number_problems() == []

    # purlin: skill_status PROOF-2
    def test_a_recount_is_refused(self, monkeypatch):
        rel = skill_path('status')
        assert refusals(monkeypatch, status_number_problems, [
            (rel, replace('Print the numbers `sync_status` returned.',
                          'Count the rules in the table yourself.'),
             "does not carry 'Print the numbers `sync_status` returned. "
             "Never recount them"),
        ]) == []

    # purlin: skill_status PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('status')
                + undirected_outcome_problems('status')) == []

    # purlin: skill_status PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'status', '| A rule has a failing test',
            '| A rule is weak | `→ Next: run purlin:build. <n> rules are '
            'weak.` |') == []

    # purlin: skill_status PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('status') == []

    # purlin: skill_status PROOF-5
    def test_naming_a_spec_shows_its_rules(self):
        assert status_name_problems() == []

    # purlin: skill_status PROOF-5
    def test_a_name_that_matches_several_or_none_is_refused_as_unhandled(
            self, monkeypatch):
        rel = skill_path('status')
        assert refusals(monkeypatch, status_name_problems, [
            (rel, replace('list them and ask which one', 'take the first'),
             "With a name section does not carry 'when several match, list "
             "them and ask which one'"),
            (rel, replace('print the whole table', 'print nothing'),
             "With a name section does not carry 'when none does, print "
             "the whole table'"),
            (rel, replace('its path, its\nheader, and one line per rule',
                          'one line per rule'),
             "With a name section does not carry 'print its path, its "
             "header, and one line per rule with the cells the gate "
             "creates'"),
        ]) == []


def status_number_problems():
    return carries(skill_path('status'), [
        'sync_status', 'Never recount them', 'one answer from one computation',
        'Print the numbers `sync_status` returned. Never recount them: the '
        'command line and the dashboard must show one answer from one '
        'computation.'])


def status_name_problems():
    rel = skill_path('status')
    problems = (carries(rel, [
        'purlin:status <name>',
        'Naming a spec shows its rules and their standing.'])
        + carries('references/purlin_commands.md', ['purlin:status [name]']))
    body = flat(section(read(rel), r'^With a name$') or '')
    problems.extend('%s With a name section does not carry %r' % (rel, needle)
                    for needle in (
                        'when several match, list them and ask which one',
                        'when none does, print the whole table',
                        'print its path, its header, and one line per rule '
                        'with the cells the gate creates')
                    if needle not in body)
    return problems
