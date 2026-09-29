"""Text checks for the export skill, `skills/export/SKILL.md`.

Every rule of `specs/skills/skill_export.md` is proved here, one test for each
proof. The readers, the checks and the broken copies this file shares with
the other skill test files are in `dev/skill_checks.py`; the checks only this
skill needs are at the foot of this file.
"""

import re

from skill_checks import (CEILINGS, COMMAND_REF, carries, ceiling_problems,
                          closing_outcomes, field, frontmatter,
                          frontmatter_problems, next_step_problems, on_copy,
                          read, refusals, replace, resub, sections,
                          skill_path, table_rows)

SKILL = skill_path('export')
CEILING = CEILINGS['export']


class TestSkillExport:

    # ---------------------------------------------------------------- RULE-1

    # purlin: skill_export PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self):
        assert skill_frontmatter_problems() == []

    # purlin: skill_export PROOF-14
    def test_the_command_reference_has_a_row_for_export(self):
        assert command_row_problems() == []

    # purlin: skill_export PROOF-15
    def test_a_skill_without_its_name_line_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace('name: export\n'),
             "%s frontmatter name is None, expected 'export'" % SKILL),
        ]) == []

    # purlin: skill_export PROOF-16
    def test_an_empty_description_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace(description_line(), 'description:'),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_export PROOF-17
    def test_a_description_on_the_line_below_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace(description_line(),
                            'description:\n  ' + description()),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_export PROOF-18
    def test_a_description_written_as_a_block_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace(description_line(),
                            'description: |\n  ' + description()),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_export PROOF-19
    def test_a_description_run_on_to_a_second_line_is_refused(self,
                                                             monkeypatch):
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace(description_line(),
                            description_line() + '\n  and a second line'),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_export PROOF-20
    def test_a_command_reference_without_the_row_is_refused(self,
                                                           monkeypatch):
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:export` |'))
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:export' % COMMAND_REF),
        ]) == []

    # ---------------------------------------------------------------- RULE-2

    # purlin: skill_export PROOF-2
    def test_each_form_of_the_command_has_a_line(self):
        assert usage_problems() == []

    # purlin: skill_export PROOF-21
    def test_a_line_runs_the_export_script(self):
        assert run_line_problems() == []

    # purlin: skill_export PROOF-22
    def test_a_skill_without_the_bare_form_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, usage_problems, [
            (SKILL, resub(r'^purlin:export {2,}.*?\n'),
             '%s has no usage line for the bare form purlin:export' % SKILL),
        ]) == []

    # purlin: skill_export PROOF-23
    def test_a_skill_without_the_check_form_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, usage_problems, [
            (SKILL, resub(r'^purlin:export --check <file> .*?\n'),
             '%s has no usage line for the form purlin:export --check '
             '<file>' % SKILL),
        ]) == []

    # purlin: skill_export PROOF-24
    def test_a_skill_that_only_names_the_script_is_refused(self,
                                                          monkeypatch):
        assert refusals(monkeypatch, run_line_problems, [
            (SKILL, lambda t: t.replace(RUN, 'Run scripts/export/package.py'),
             '%s has no line that runs %s' % (SKILL, RUN)),
        ]) == []

    # ---------------------------------------------------------------- RULE-3

    # purlin: skill_export PROOF-3
    def test_it_makes_no_claim_of_compliance(self):
        assert no_claim_problems() == []

    # purlin: skill_export PROOF-25
    def test_it_calls_the_package_evidence_for_review(self):
        assert carries(SKILL, [
            'The package is evidence for review in a regulated document '
            'and sign-off system']) == []

    # purlin: skill_export PROOF-26
    def test_a_skill_that_drops_the_no_claim_sentence_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, no_claim_problems, [
            (SKILL, lambda t: re.sub(r'Purlin makes no claim that the\s+'
                                     r'software is compliant\.\s*', '', t),
             "does not carry %r" % NO_CLAIM),
        ]) == []

    # ---------------------------------------------------------------- RULE-4

    # purlin: skill_export PROOF-4
    def test_the_table_of_states_names_the_two_states(self):
        assert state_problems() == []

    # purlin: skill_export PROOF-27
    def test_the_not_finished_row_says_left_holds_left_to_do(self):
        assert left_problems() == []

    # purlin: skill_export PROOF-7
    def test_a_not_finished_row_without_left_to_do_is_refused(self,
                                                             monkeypatch):
        assert refusals(monkeypatch, left_problems, [
            (SKILL, replace('holds the lines of `Left to do`',
                            'holds the work'),
             'does not say %r' % LEFT),
        ]) == []

    # purlin: skill_export PROOF-28
    def test_a_table_of_states_without_not_finished_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, state_problems, [
            (SKILL, resub(r'^\| `not finished` \|.*?\n'),
             "names the states ['`finished`'], expected "
             "['`finished`', '`not finished`']"),
        ]) == []

    # ---------------------------------------------------------------- RULE-5

    # purlin: skill_export PROOF-5
    def test_the_last_heading_names_the_next_step(self):
        assert heading_problems() == []

    # purlin: skill_export PROOF-29
    def test_each_stop_short_names_the_next_step(self):
        assert row_problems(FAILURE_OUTCOMES) == []

    # purlin: skill_export PROOF-13
    def test_each_state_names_the_next_step(self):
        assert row_problems(STATE_OUTCOMES) == []

    # purlin: skill_export PROOF-30
    def test_every_outcome_row_gives_a_directive(self):
        assert directive_problems() == []

    # purlin: skill_export PROOF-8
    def test_a_skill_without_its_closing_section_is_refused(self,
                                                             monkeypatch):
        last = read(SKILL).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:last + 1],
             "%s closes with the section 'Checking a package', whose "
             "heading does not carry the words next step" % SKILL),
        ]) == []

    # purlin: skill_export PROOF-31
    def test_a_closing_heading_of_when_you_are_done_is_refused(
            self, monkeypatch):
        heading = sections(read(SKILL))[-1][0]
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, replace('## %s\n' % heading, '## When you are done\n'),
             "%s closes with the section 'When you are done', whose "
             "heading does not carry the words next step" % SKILL),
        ]) == []

    # purlin: skill_export PROOF-9
    def test_a_closing_section_without_arrows_is_refused(self, monkeypatch):
        last = read(SKILL).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:last] + t[last:].replace('→', '->'),
             '%s closing section gives no directive' % SKILL),
        ]) == []

    # purlin: skill_export PROOF-10
    def test_a_closing_table_of_one_row_is_refused(self, monkeypatch):
        last = read(SKILL).rindex('\n## ')
        second = '| No version |'
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:t.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % SKILL),
        ]) == []

    # purlin: skill_export PROOF-11
    def test_a_finished_row_without_its_arrow_is_refused(self, monkeypatch):
        row = ('| `finished` | `→ Hand .purlin/evidence/package/'
               '<version>.json to the system of record.` |')
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, replace(row, row.replace('→ ', '')),
             '%s closing outcome gives no → directive: %s'
             % (SKILL, row.replace('→ ', ''))),
        ]) == []

    # purlin: skill_export PROOF-12
    def test_a_table_without_the_mismatch_row_is_refused(self, monkeypatch):
        assert refusals(monkeypatch,
                        lambda: row_problems(FAILURE_OUTCOMES), [
            (SKILL, replace('| `--check` named a mismatch | `→ Export the '
                            'package again at its tag: purlin:export` |\n'),
             '%s closing section has no row for %r'
             % (SKILL, '`--check` named a mismatch')),
        ]) == []

    # ---------------------------------------------------------------- RULE-6

    # purlin: skill_export PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert length_problems() == []

    # purlin: skill_export PROOF-32
    def test_a_skill_of_91_lines_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, length_problems, [
            (SKILL, padded_to(CEILING + 1),
             '%s is 91 lines, ceiling 90' % SKILL),
        ]) == []

    # purlin: skill_export PROOF-33
    def test_a_skill_of_exactly_90_lines_passes(self, monkeypatch):
        assert on_copy(monkeypatch, SKILL, padded_to(CEILING),
                       length_problems) == []


# ---------------------------------------------------------------------------
# RULE-1: the frontmatter and the command reference's row
# ---------------------------------------------------------------------------

NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL


def skill_frontmatter_problems():
    """What the shared check reports about the skill's own frontmatter."""
    return [p for p in frontmatter_problems('export')
            if not p.startswith(COMMAND_REF)]


def command_row_problems():
    """What the shared check reports about the command reference's row."""
    return [p for p in frontmatter_problems('export')
            if p.startswith(COMMAND_REF)]


def description():
    return field(frontmatter(read(SKILL)), 'description')


def description_line():
    return 'description: %s' % description()


# ---------------------------------------------------------------------------
# RULE-2: the usage lines and the line that runs the script
# ---------------------------------------------------------------------------

RUN = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"'


def usage_problems():
    """Each form opens a line of its own, its gloss two spaces on."""
    text = read(SKILL)
    problems = []
    for form in ('', ' --release <name>', ' --commit', ' --check <file>'):
        if not re.search(r'^purlin:export%s(?: {2,}\S.*)?$' % re.escape(form),
                         text, re.M):
            problems.append('%s has no usage line for the %s' % (
                SKILL, 'form purlin:export' + form if form
                else 'bare form purlin:export'))
    return problems


def run_line_problems():
    if re.search(r'^%s' % re.escape(RUN), read(SKILL), re.M):
        return []
    return ['%s has no line that runs %s' % (SKILL, RUN)]


# ---------------------------------------------------------------------------
# RULE-3: no claim of compliance
# ---------------------------------------------------------------------------

NO_CLAIM = 'Purlin makes no claim that the software is compliant.'


def no_claim_problems():
    return carries(SKILL, [NO_CLAIM])


# ---------------------------------------------------------------------------
# RULE-4: the two states
# ---------------------------------------------------------------------------

STATES = ['`finished`', '`not finished`']
LEFT = '`left` holds the lines of `Left to do`'


def state_rows():
    return table_rows(read(SKILL), '| State |')


def state_problems():
    names = [row[0] for row in state_rows()]
    if names != STATES:
        return ['%s table of states names the states %s, expected %s'
                % (SKILL, names, STATES)]
    return []


def left_problems():
    rows = [row for row in state_rows() if row[0] == '`not finished`']
    if rows and LEFT in rows[0][1]:
        return []
    return ['%s row for `not finished` does not say %r' % (SKILL, LEFT)]


# ---------------------------------------------------------------------------
# RULE-5: the closing section
# ---------------------------------------------------------------------------

# The outcomes of the closing table where the export stopped short, and the
# line each row gives.
FAILURE_OUTCOMES = {
    'Evidence not committed': '`→ Run: purlin:test --commit`',
    'No version': '`→ Run: purlin:export --release <version>`',
    '`--check` named a mismatch': '`→ Export the package again at its '
                                  'tag: purlin:export`',
}

# The outcomes of the closing table for each state the package reads.
STATE_OUTCOMES = {
    '`not finished`': '`→ Run: <the command of the first line of left>`',
    '`finished`': '`→ Hand .purlin/evidence/package/<version>.json to the '
                  'system of record.`',
}

OUTCOMES = len(FAILURE_OUTCOMES) + len(STATE_OUTCOMES)


def closing_rows():
    """The cells of each outcome row of the closing table."""
    body = sections(read(SKILL))[-1][1]
    return [[cell.strip() for cell in row.strip('|').split('|')]
            for row in closing_outcomes(body)]


def heading_problems():
    """The shared check also takes `when you are done`; this rule does not."""
    heading = sections(read(SKILL))[-1][0]
    if re.search(r'next step', heading, re.I):
        return []
    return ['%s closes with the section %r, whose heading does not carry the '
            'words next step' % (SKILL, heading)]


def directive_problems():
    rows = closing_rows()
    problems = []
    if len(rows) != OUTCOMES:
        problems.append('%s closing table has %d outcome rows, expected %d'
                        % (SKILL, len(rows), OUTCOMES))
    for row in rows:
        if len(row) < 2 or not row[1].startswith('`→ '):
            problems.append('%s closing outcome gives no → directive: %s'
                            % (SKILL, '| %s |' % ' | '.join(row)))
    return problems


def closing_problems():
    return (heading_problems() + next_step_problems('export')
            + directive_problems())


def row_problems(outcomes):
    rows = closing_rows()
    return ['%s closing section has no row for %r' % (SKILL, outcome)
            for outcome, line in outcomes.items() if [outcome, line] not in rows]


# ---------------------------------------------------------------------------
# RULE-6: the ceiling
# ---------------------------------------------------------------------------

def length_problems():
    return ceiling_problems(SKILL, CEILING)


def padded_to(count):
    """An edit that adds lines of prose until the skill is `count` lines."""
    def edit(text):
        lines = text.splitlines()
        assert len(lines) < count, 'the skill is already %d lines' % len(lines)
        return '\n'.join(lines + ['More prose.'] * (count - len(lines))) + '\n'
    return edit
