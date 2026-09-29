"""Text checks for the export skill, `skills/export/SKILL.md`.

Every rule of `specs/skills/skill_export.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, closing_outcomes, frontmatter_problems,
                          frontmatter_refusals, next_step_problems, read,
                          refusals, replace, resub, sections,
                          skill_ceiling_problems, skill_path,
                          undirected_outcome_problems)


class TestSkillExport:

    # purlin: skill_export PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('export') == []

    # purlin: skill_export PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'export') == []

    # purlin: skill_export PROOF-2
    def test_it_runs_the_script_in_each_form(self):
        assert export_command_problems() == []

    # purlin: skill_export PROOF-2
    def test_a_missing_form_or_run_line_is_refused(self, monkeypatch):
        rel = skill_path('export')
        run = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"'
        assert refusals(monkeypatch, export_command_problems, [
            (rel, resub(r'^purlin:export {2,}.*\n'),
             '%s has no usage line for the bare form purlin:export' % rel),
            (rel, replace('purlin:export --check <file>      Check',
                          'Check'),
             '%s has no usage line for the form purlin:export --check '
             '<file>' % rel),
            (rel, lambda t: t.replace(run, 'Run scripts/export/package.py'),
             '%s has no line that runs %s' % (rel, run)),
        ]) == []

    # purlin: skill_export PROOF-3
    def test_it_makes_no_claim_of_compliance(self):
        assert carries(skill_path('export'), [
            'Purlin makes no claim that the software is compliant.',
            'evidence for review in a regulated document and sign-off '
            'system']) == []

    # purlin: skill_export PROOF-4
    def test_it_names_the_two_states(self):
        assert export_state_problems() == []

    # purlin: skill_export PROOF-7
    def test_a_state_row_that_drops_left_to_do_is_refused(self, monkeypatch):
        rel = skill_path('export')
        assert refusals(monkeypatch, export_state_problems, [
            (rel, replace('holds the lines of `Left to do`',
                          'holds the work'),
             "does not carry 'holds the lines of `Left to do`'"),
        ]) == []

    # purlin: skill_export PROOF-5
    def test_it_closes_by_naming_the_next_step(self):
        assert export_outcome_problems(FAILURE_OUTCOMES) == []

    # purlin: skill_export PROOF-13
    def test_each_state_names_the_next_step(self):
        assert export_outcome_problems(STATE_OUTCOMES) == []

    # purlin: skill_export PROOF-8
    def test_a_skill_without_its_closing_section_is_refused(self,
                                                             monkeypatch):
        rel = skill_path('export')
        text = read(rel)
        last = text.rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (rel, lambda t: t[:last + 1],
             '%s closes with the section %r' % (rel, 'Checking a package')),
        ]) == []

    # purlin: skill_export PROOF-9
    def test_a_closing_section_without_arrows_is_refused(self, monkeypatch):
        rel = skill_path('export')
        last = read(rel).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (rel, lambda t: t[:last] + t[last:].replace('\u2192', '->'),
             '%s closing section gives no directive' % rel),
        ]) == []

    # purlin: skill_export PROOF-10
    def test_a_closing_table_of_one_row_is_refused(self, monkeypatch):
        rel = skill_path('export')
        last = read(rel).rindex('\n## ')
        second = '| No version |'
        assert refusals(monkeypatch, closing_problems, [
            (rel, lambda t: t[:t.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % rel),
        ]) == []

    # purlin: skill_export PROOF-11
    def test_a_finished_row_without_its_arrow_is_refused(self, monkeypatch):
        rel = skill_path('export')
        row = ('| `finished` | `\u2192 Hand .purlin/evidence/package/'
               '<version>.json to the system of record.` |')
        assert refusals(monkeypatch, closing_problems, [
            (rel, replace(row, row.replace('\u2192 ', '')),
             '%s closing outcome gives no \u2192 directive' % rel),
        ]) == []

    # purlin: skill_export PROOF-12
    def test_a_table_without_the_mismatch_row_is_refused(self, monkeypatch):
        rel = skill_path('export')
        assert refusals(monkeypatch,
                        lambda: export_outcome_problems(FAILURE_OUTCOMES), [
            (rel, replace('| `--check` named a mismatch | `\u2192 Export the '
                          'package again at its tag: purlin:export` |\n'),
             '%s closing section has no row for %r'
             % (rel, '`--check` named a mismatch')),
        ]) == []

    # purlin: skill_export PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('export') == []


def export_command_problems():
    rel = skill_path('export')
    text = read(rel)
    problems = carries(rel, [
        'scripts/export/package.py', 'purlin:export --release <name>',
        'purlin:export --commit', 'purlin:export --check <file>'])
    # Each form opens a usage line of its own, its gloss two spaces on.
    for form in ('', ' --release <name>', ' --commit', ' --check <file>'):
        if not re.search(r'^purlin:export%s(?: {2,}\S.*)?$' % re.escape(form),
                         text, re.M):
            problems.append('%s has no usage line for the %s' % (
                rel, 'form purlin:export' + form if form
                else 'bare form purlin:export'))
    run = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"'
    if not re.search(r'^%s' % re.escape(run), text, re.M):
        problems.append('%s has no line that runs %s' % (rel, run))
    return problems


def export_state_problems():
    return carries(skill_path('export'), [
        '`finished`', '`not finished`', 'holds the lines of `Left to do`'])


# The outcomes of the export's closing table where the export stopped short,
# and the directive each row gives.
FAILURE_OUTCOMES = {
    'Evidence not committed': '`→ Run: purlin:test --commit`',
    'No version': '`→ Run: purlin:export --release <version>`',
    '`--check` named a mismatch': '`→ Export the package again at its tag: '
                                  'purlin:export`',
}

# The outcomes of the closing table for each state the package reads.
STATE_OUTCOMES = {
    '`not finished`': '`→ Run: <the command of the first line of left>`',
    '`finished`': '`→ Hand .purlin/evidence/package/<version>.json to the '
                  'system of record.`',
}


def closing_problems():
    return (next_step_problems('export')
            + undirected_outcome_problems('export'))


def export_outcome_problems(outcomes):
    rel = skill_path('export')
    problems = closing_problems()
    rows = [[cell.strip() for cell in row.strip('|').split('|')]
            for row in closing_outcomes(sections(read(rel))[-1][1])]
    for outcome, directive in outcomes.items():
        if [outcome, directive] not in rows:
            problems.append('%s closing section has no row for %r' % (
                rel, outcome))
    return problems
