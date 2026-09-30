"""Text checks for the export skill, `skills/export/SKILL.md`.

Every rule of `specs/skills/skill_export.md` is proved here, one test for each
proof; where a broken copy of the skill could slip past a check, the test
also shows that the check reports it. The readers, the checks and the broken
copies this file shares with the other skill test files are in
`dev/skill_checks.py`; the checks only this skill needs are at the foot of
this file.
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
    def test_the_frontmatter_names_the_skill_on_one_line(self, monkeypatch):
        assert skill_frontmatter_problems() == []
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace('name: export\n'),
             "%s frontmatter name is None, expected 'export'" % SKILL),
            (SKILL, replace(description_line(), 'description:'),
             NO_DESCRIPTION),
            (SKILL, replace(description_line(),
                            'description:\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(description_line(),
                            'description: |\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(description_line(),
                            description_line() + '\n  and a second line'),
             NO_DESCRIPTION),
        ]) == []

    # ---------------------------------------------------------------- RULE-7

    # purlin: skill_export PROOF-14
    def test_the_command_reference_has_a_row_for_export(self, monkeypatch):
        assert command_row_problems() == []
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:export` |'))
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:export' % COMMAND_REF),
        ]) == []

    # ---------------------------------------------------------------- RULE-8

    # purlin: skill_export PROOF-2
    def test_each_form_of_the_command_has_a_line(self, monkeypatch):
        assert usage_problems() == []
        assert refusals(monkeypatch, usage_problems, [
            (SKILL, resub(r'^purlin:export {2,}.*?\n'),
             '%s has no usage line for the bare form purlin:export' % SKILL),
            (SKILL, resub(r'^purlin:export --check <file> .*?\n'),
             '%s has no usage line for the form purlin:export --check '
             '<file>' % SKILL),
        ]) == []

    # ---------------------------------------------------------------- RULE-2

    # purlin: skill_export PROOF-21
    def test_a_line_runs_the_export_script(self, monkeypatch):
        assert run_line_problems() == []
        assert refusals(monkeypatch, run_line_problems, [
            (SKILL, lambda t: t.replace(RUN, 'Run scripts/export/package.py'),
             '%s has no line that runs %s' % (SKILL, RUN)),
        ]) == []

    # ---------------------------------------------------------------- RULE-3

    # purlin: skill_export PROOF-3
    def test_it_makes_no_claim_of_compliance(self, monkeypatch):
        assert no_claim_problems() == []
        assert refusals(monkeypatch, no_claim_problems, [
            (SKILL, lambda t: re.sub(r'Purlin makes no claim that the\s+'
                                     r'software is compliant\.\s*', '', t),
             "does not carry %r" % NO_CLAIM),
        ]) == []

    # ---------------------------------------------------------------- RULE-9

    # purlin: skill_export PROOF-25
    def test_it_calls_the_package_evidence_for_review(self):
        assert carries(SKILL, [
            'The package is evidence for review in a regulated document '
            'and sign-off system']) == []

    # ---------------------------------------------------------------- RULE-4

    # purlin: skill_export PROOF-4
    def test_the_table_of_states_names_the_two_states(self, monkeypatch):
        assert state_problems() == []
        assert refusals(monkeypatch, state_problems, [
            (SKILL, resub(r'^\| `not finished` \|.*?\n'),
             "names the states ['`finished`'], expected "
             "['`finished`', '`not finished`']"),
        ]) == []

    # --------------------------------------------------------------- RULE-10

    # purlin: skill_export PROOF-27
    def test_the_not_finished_row_says_left_holds_left_to_do(
            self, monkeypatch):
        assert left_problems() == []
        assert refusals(monkeypatch, left_problems, [
            (SKILL, replace('holds the lines of `Left to do`',
                            'holds the work'),
             'does not say %r' % LEFT),
        ]) == []

    # ---------------------------------------------------------------- RULE-5

    # purlin: skill_export PROOF-5
    def test_the_last_heading_names_the_next_step(self, monkeypatch):
        assert heading_problems() == []
        text = read(SKILL)
        last = text.rindex('\n## ')
        heading = sections(text)[-1][0]
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:last + 1],
             "%s closes with the section 'Checking a package', whose "
             "heading does not carry the words next step" % SKILL),
            (SKILL, replace('## %s\n' % heading, '## When you are done\n'),
             "%s closes with the section 'When you are done', whose "
             "heading does not carry the words next step" % SKILL),
        ]) == []

    # --------------------------------------------------------------- RULE-11

    # purlin: skill_export PROOF-29
    def test_each_stop_short_names_the_next_step(self, monkeypatch):
        assert row_problems(FAILURE_OUTCOMES) == []
        assert refusals(monkeypatch,
                        lambda: row_problems(FAILURE_OUTCOMES), [
            (SKILL, replace('| `--check` named a mismatch | %s |\n'
                            % FAILURE_OUTCOMES['`--check` named a mismatch']),
             '%s closing section has no row for %r'
             % (SKILL, '`--check` named a mismatch')),
        ]) == []

    # purlin: skill_export PROOF-13
    def test_each_state_names_the_next_step(self):
        assert row_problems(STATE_OUTCOMES) == []

    # purlin: skill_export PROOF-30
    def test_every_outcome_row_gives_a_directive(self, monkeypatch):
        assert directive_problems() == []
        last = read(SKILL).rindex('\n## ')
        second = '| No version |'
        row = ('| `finished` | `→ Hand .purlin/evidence/package/'
               '<version>.json to the system of record.` |')
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:last] + t[last:].replace('→', '->'),
             '%s closing section gives no directive' % SKILL),
            (SKILL, lambda t: t[:t.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % SKILL),
            (SKILL, replace(row, row.replace('→ ', '')),
             '%s closing outcome gives no → directive: %s'
             % (SKILL, row.replace('→ ', ''))),
        ]) == []

    # --------------------------------------------------------------- RULE-12

    # purlin: skill_export PROOF-34
    def test_it_quotes_the_no_version_line(self, monkeypatch):
        assert no_version_problems() == []
        assert refusals(monkeypatch, no_version_problems, [
            (SKILL, replace('Run purlin:export --release <version>, or write '
                            'it to a VERSION file.',
                            'Name it with --release <version>.'),
             'does not carry %r' % NO_VERSION),
        ]) == []

    # ---------------------------------------------------------------- RULE-6

    # purlin: skill_export PROOF-6
    def test_it_stays_under_its_ceiling(self, monkeypatch):
        assert length_problems() == []
        assert refusals(monkeypatch, length_problems, [
            (SKILL, padded_to(CEILING + 1),
             '%s is 91 lines, ceiling 90' % SKILL),
        ]) == []
        assert on_copy(monkeypatch, SKILL, padded_to(CEILING),
                       length_problems) == []


# ---------------------------------------------------------------------------
# RULE-1 and RULE-7: the frontmatter and the command reference's row
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
# RULE-2 and RULE-8: the line that runs the script and the usage lines
# ---------------------------------------------------------------------------

RUN = ('sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" '
       '"${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"')


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
# RULE-12: the line with no version
# ---------------------------------------------------------------------------

NO_VERSION = ('No version: nothing in this project states one. Run '
              'purlin:export --release <version>, or write it to a VERSION '
              'file.')


def no_version_problems():
    return carries(SKILL, [NO_VERSION])


# ---------------------------------------------------------------------------
# RULE-4 and RULE-10: the two states and what `left` holds
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
# RULE-5 and RULE-11: the closing section
# ---------------------------------------------------------------------------

# The outcomes of the closing table where the export stopped short, and the
# line each row gives.
FAILURE_OUTCOMES = {
    'Evidence not committed': '`→ Run: purlin:test --commit`',
    'No version': '`→ Run: purlin:export --release <version>`',
    '`--check` named a mismatch': '`→ Run: git show signed/<version>:'
                                  '.purlin/evidence/package/<version>.json`',
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


# purlin: skill_export PROOF-35
def test_the_package_is_read_where_the_authority_to_sign_off_is():
    assert ('reads it in the system that holds the authority to sign the '
            'version off') in ' '.join(read(SKILL).split())
