"""Text checks for the status skill, `skills/status/SKILL.md`.

Every rule of `specs/skills/skill_status.md` is proved here, one test per
proof. The readers, the checks and the broken copies this file shares with the
other skill test files are in `dev/skill_checks.py`; the checks only this spec
needs are at the bottom of this file.

A refused case points a check at a copy of the file with one thing broken; the
file on disk is never touched. RULE-2's last proof runs the real status tool
against a throwaway project and reads back the data file the dashboard reads.
"""

import json
import os
import re

from mcp_project import Project, _commit_tests, _entry
from purlin import status as purlin_status
from purlin import summary as purlin_summary
from skill_checks import (COMMAND_REF, carries, closing_outcomes,
                          command_rows, field, flat, frontmatter,
                          frontmatter_problems, next_step_problems, on_copy,
                          read, refusals, replace, resub, runs_on, same_line,
                          section, sections, skill_ceiling_problems,
                          skill_path, undirected_outcome_problems)

REL = skill_path('status')
DESCRIPTION = "Show every rule's cells and what blocks the gate"
PRINTS = 'Print the sentence and the `Left to do` lines `sync_status` returned.'
FIRST_LINE = 'The next step is the first line of `Left to do`.'
NO_DESCRIPTION = '%s frontmatter carries no one-line description' % REL
NO_ROW = '%s carries no row for purlin:status' % COMMAND_REF
ARROW = '→'


# ---------------------------------------------------------------------------
# RULE-1: the frontmatter and the command reference's row
# ---------------------------------------------------------------------------

class TestFrontmatter:

    # purlin: skill_status PROOF-1
    def test_the_frontmatter_names_the_skill_and_describes_it_in_one_line(
            self):
        block = frontmatter(read(REL))
        assert block is not None, '%s opens with no frontmatter block' % REL
        assert field(block, 'name') == 'status'
        assert field(block, 'description') == DESCRIPTION
        assert not runs_on(block, 'description')
        assert [p for p in frontmatter_problems('status')
                if 'frontmatter' in p] == []

    # purlin: skill_status PROOF-12
    def test_the_command_reference_has_a_row_for_status_with_its_purpose(
            self):
        rows = [cells for cells in command_rows()
                if cells[0] == '`purlin:status [name]`']
        assert len(rows) == 1, rows
        assert rows[0][1] == DESCRIPTION
        assert NO_ROW not in frontmatter_problems('status')

    # purlin: skill_status PROOF-13
    def test_a_skill_with_no_name_line_is_refused(self, monkeypatch):
        assert frontmatter_refused(monkeypatch, REL, replace('name: status\n'),
                                   "frontmatter name is None, expected "
                                   "'status'") == []

    # purlin: skill_status PROOF-14
    def test_an_empty_description_is_refused(self, monkeypatch):
        assert frontmatter_refused(
            monkeypatch, REL, replace(description_line(), 'description:'),
            NO_DESCRIPTION) == []

    # purlin: skill_status PROOF-15
    def test_a_description_written_as_empty_quotes_is_refused(
            self, monkeypatch):
        assert frontmatter_refused(
            monkeypatch, REL, resub(r'^description: [^\n]*$',
                                    'description: ""'),
            NO_DESCRIPTION) == []

    # purlin: skill_status PROOF-16
    def test_a_description_opened_as_a_block_is_refused(self, monkeypatch):
        assert frontmatter_refused(
            monkeypatch, REL,
            replace(description_line(), description_line().replace(
                ': ', ': |\n  ', 1)),
            NO_DESCRIPTION) == []

    # purlin: skill_status PROOF-17
    def test_a_description_on_the_line_below_is_refused(self, monkeypatch):
        assert frontmatter_refused(
            monkeypatch, REL,
            replace(description_line(), description_line().replace(
                ': ', ':\n  ', 1)),
            NO_DESCRIPTION) == []

    # purlin: skill_status PROOF-18
    def test_a_description_running_on_to_a_second_line_is_refused(
            self, monkeypatch):
        assert frontmatter_refused(
            monkeypatch, REL,
            replace(description_line(), description_line()
                    + '\n  and a second line'),
            NO_DESCRIPTION) == []

    # purlin: skill_status PROOF-19
    def test_a_command_reference_without_the_status_row_is_refused(
            self, monkeypatch):
        assert frontmatter_refused(
            monkeypatch, COMMAND_REF, replace(status_row() + '\n'),
            NO_ROW) == []

    # purlin: skill_status PROOF-20
    def test_a_status_row_with_an_empty_purpose_is_refused(self, monkeypatch):
        row = status_row()
        emptied = re.sub(r'^(\| `purlin:status \[name\]` \|)[^|]*\|',
                         r'\1 |', row)
        assert emptied != row
        assert frontmatter_refused(
            monkeypatch, COMMAND_REF, replace(row, emptied), NO_ROW) == []


def description_line():
    """The skill's `description:` line as it stands, so a refused copy
    breaks only the form of the line and not its words."""
    return 'description: %s' % field(frontmatter(read(REL)), 'description')


def status_row():
    return next(line for line in read(COMMAND_REF).splitlines()
                if line.startswith('| `purlin:status [name]` |'))


def frontmatter_refused(monkeypatch, rel, edit, expected):
    return refusals(monkeypatch, lambda: frontmatter_problems('status'),
                    [(rel, edit, expected)])


# ---------------------------------------------------------------------------
# RULE-2: print what the tool returned, never recount
# ---------------------------------------------------------------------------

class TestPrintWhatTheToolReturned:

    # purlin: skill_status PROOF-2
    def test_it_prints_the_lines_the_tool_returned_and_never_recounts(self):
        assert status_number_problems() == []

    # purlin: skill_status PROOF-6
    def test_a_skill_that_says_to_count_the_rules_itself_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, status_number_problems, [
            (REL, replace(PRINTS, 'Count the rules in the table yourself.'),
             "does not carry 'Print the sentence and the `Left to do` lines"),
        ]) == []

    # purlin: skill_status PROOF-21
    def test_the_status_text_and_the_dashboard_data_carry_one_answer(self):
        made = Project(gate='strong')
        try:
            _commit_tests(made, 'PROOF-1')
            made.evidence([_entry('PROOF-1', 'RULE-1')], audited=False)
            text = purlin_status.sync_status(made.root)
            data = dashboard_data(made.root)
        finally:
            made.close()
        sentence = '2 rules. 1 passes its tests. 0 are strong.'
        assert text.splitlines()[-4:] == [
            sentence, 'Left to do:',
            '  1 rule to write a test for: purlin:build',
            '  1 rule to audit: purlin:audit'], text
        assert data['summary']['rules'] == 2
        assert data['summary']['steps'] == {'passed': 1, 'strong': 0}
        assert [(item['text'], item['command'], item['count'])
                for item in data['left']] == [
            ('1 rule to write a test for', 'purlin:build', 1),
            ('1 rule to audit', 'purlin:audit', 1)]


def status_number_problems():
    return carries(REL, [
        PRINTS + ' Never recount them: the command line and the dashboard '
        'must show one answer from one computation.'])


def dashboard_data(root):
    """The payload `.purlin/report-data.js` holds, as the page reads it."""
    path = os.path.join(root, '.purlin', 'report-data.js')
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    prefix, suffix = 'const PURLIN_DATA = ', ';\n'
    assert text.startswith(prefix) and text.endswith(suffix), text[:80]
    return json.loads(text[len(prefix):-len(suffix)])


# ---------------------------------------------------------------------------
# RULE-3: the closing section names the next step
# ---------------------------------------------------------------------------

class TestNextStep:

    # purlin: skill_status PROOF-3
    def test_the_last_section_is_headed_as_the_next_step(self):
        assert sections(read(REL))[-1][0] == 'Step 4: name the next step'
        assert [p for p in next_step_problems('status')
                if 'closes with the section' in p] == []

    # purlin: skill_status PROOF-7
    def test_a_skill_with_its_last_section_removed_is_refused(
            self, monkeypatch):
        last = read(REL).rindex('\n## ')
        assert closing_refused(
            monkeypatch, lambda t: t[:last + 1],
            "%s closes with the section 'With a name'" % REL) == []

    # purlin: skill_status PROOF-22
    def test_the_last_section_names_the_first_line_of_left_to_do(self):
        assert first_line_problems() == []

    # purlin: skill_status PROOF-11
    def test_a_last_section_that_names_no_first_line_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, first_line_problems, [
            (REL, replace(FIRST_LINE, 'The next step is yours to choose.'),
             'closing section does not carry %r' % FIRST_LINE),
        ]) == []

    # purlin: skill_status PROOF-23
    def test_every_row_gives_a_directive_but_nothing_left_to_do(self):
        body = sections(read(REL))[-1][1]
        rows = closing_outcomes(body)
        assert len(rows) >= 2, rows
        undirected = [row for row in rows if ARROW not in row]
        assert undirected == [
            '| `Nothing left to do.` | None: every rule reached every step '
            'the gate asks. |'], undirected
        assert (next_step_problems('status')
                + undirected_outcome_problems('status')) == []

    # purlin: skill_status PROOF-8
    def test_a_last_section_with_no_arrow_is_refused(self, monkeypatch):
        last = read(REL).rindex('\n## ')
        assert closing_refused(
            monkeypatch, lambda t: t[:last] + t[last:].replace(ARROW, '->'),
            '%s closing section gives no directive' % REL) == []

    # purlin: skill_status PROOF-9
    def test_a_last_section_cut_after_its_first_row_is_refused(
            self, monkeypatch):
        last = read(REL).rindex('\n## ')
        assert closing_refused(
            monkeypatch,
            lambda t: t[:t.index('| `<n> rules to fix`', last)],
            '%s closing section names 1 outcomes, expected at least 2'
            % REL) == []

    # purlin: skill_status PROOF-10
    def test_the_audit_row_without_its_arrow_is_refused(self, monkeypatch):
        assert closing_refused(
            monkeypatch, replace(AUDIT_ROW, AUDIT_ROW.replace(ARROW + ' ', '')),
            '%s closing outcome gives no %s directive: %s'
            % (REL, ARROW, AUDIT_ROW.replace(ARROW + ' ', ''))) == []

    # purlin: skill_status PROOF-24
    def test_every_kind_of_left_to_do_line_has_a_row_running_its_command(
            self):
        assert kind_row_problems() == []

    # purlin: skill_status PROOF-25
    def test_the_audit_row_running_another_command_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, kind_row_problems, [
            (REL, replace(AUDIT_ROW, AUDIT_ROW.replace('purlin:audit',
                                                       'purlin:test')),
             "%s closing table row for 'rules to audit' runs 'purlin:test', "
             "but the line names 'purlin:audit'" % REL),
        ]) == []

    # purlin: skill_status PROOF-26
    def test_a_table_that_no_longer_names_to_strengthen_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, kind_row_problems, [
            (REL, replace(' or `to strengthen`'),
             "%s closing table names no row for the line 'rules to "
             "strengthen'" % REL),
        ]) == []


AUDIT_ROW = '| `<n> rules to audit` | `%s Run: purlin:audit` |' % ARROW


def closing_refused(monkeypatch, edit, expected):
    def check():
        return (next_step_problems('status')
                + undirected_outcome_problems('status'))
    return refusals(monkeypatch, check, [(REL, edit, expected)])


def first_line_problems():
    body = flat(sections(read(REL))[-1][1])
    if FIRST_LINE in body:
        return []
    return ['%s closing section does not carry %r' % (REL, FIRST_LINE)]


def kind_row_problems():
    """Each kind of `Left to do` line the tool prints with no row in the
    closing table, or whose row runs a command other than the line's own.

    A row's first cell names its lines in backticks, `<n> rules to fix`,
    `to write a test for`; its second cell carries `→ Run: <command>`.
    """
    rows = []
    for row in closing_outcomes(sections(read(REL))[-1][1]):
        cells = [cell.strip() for cell in row.strip().strip('|').split('|')]
        named = [re.sub(r'^<n> rules ', '', phrase)
                 for phrase in re.findall(r'`([^`]*)`', cells[0])]
        command = re.search(r'%s Run: ([^`]+)`' % ARROW, cells[-1])
        rows.append((named, command.group(1) if command else None))
    problems = []
    for _kind, _one, many, command in purlin_summary.KINDS:
        line = many.replace('%s', '<systems>')
        phrase = re.sub(r'^rules ', '', line)
        found = [run for named, run in rows if phrase in named]
        if not found:
            problems.append('%s closing table names no row for the line %r'
                            % (REL, line))
        elif found[0] != command:
            problems.append('%s closing table row for %r runs %r, but the '
                            'line names %r' % (REL, line, found[0], command))
    return problems


# ---------------------------------------------------------------------------
# RULE-4: the ceiling
# ---------------------------------------------------------------------------

class TestCeiling:

    # purlin: skill_status PROOF-4
    def test_the_skill_is_at_most_100_lines(self):
        assert len(read(REL).splitlines()) <= 100
        assert skill_ceiling_problems('status') == []

    # purlin: skill_status PROOF-27
    def test_a_skill_of_exactly_100_lines_passes(self, monkeypatch):
        assert on_copy(monkeypatch, REL, lines_long(100),
                       lambda: skill_ceiling_problems('status')) == []

    # purlin: skill_status PROOF-28
    def test_a_skill_of_101_lines_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('status'),
                        [(REL, lines_long(101),
                          '%s is 101 lines, ceiling 100' % REL)]) == []


def lines_long(count):
    """An edit that keeps the file's first lines and pads it to `count`."""
    def edit(text):
        lines = text.splitlines()[:count - 1]
        lines += ['A line of prose.'] * (count - len(lines))
        return '\n'.join(lines) + '\n'
    return edit


# ---------------------------------------------------------------------------
# RULE-5: naming a spec
# ---------------------------------------------------------------------------

class TestWithAName:

    # purlin: skill_status PROOF-5
    def test_the_skill_shows_the_named_form(self):
        assert (same_line(REL, ['purlin:status <name>',
                                'One spec: its rules and their cells'])
                + carries(REL, ['Naming a spec shows its rules and their '
                                'standing.'])) == []

    # purlin: skill_status PROOF-29
    def test_the_command_reference_names_the_form_with_a_name(self):
        assert reference_form_problems() == []

    # purlin: skill_status PROOF-30
    def test_a_command_reference_without_the_name_is_refused(
            self, monkeypatch):
        assert refusals(monkeypatch, reference_form_problems, [
            (COMMAND_REF, replace('`purlin:status [name]`',
                                  '`purlin:status`'),
             "does not carry 'purlin:status [name]'"),
        ]) == []

    # purlin: skill_status PROOF-31
    def test_the_with_a_name_section_says_what_it_prints(self):
        assert name_section_problems() == []

    # purlin: skill_status PROOF-32
    def test_a_name_section_that_takes_the_first_match_is_refused(
            self, monkeypatch):
        assert name_section_refused(
            monkeypatch, replace('list them and ask which one',
                                 'take the first'), SEVERAL) == []

    # purlin: skill_status PROOF-33
    def test_a_name_section_that_prints_nothing_for_no_match_is_refused(
            self, monkeypatch):
        assert name_section_refused(
            monkeypatch, replace('print the whole table', 'print nothing'),
            NONE) == []

    # purlin: skill_status PROOF-34
    def test_a_name_section_that_prints_only_the_rule_lines_is_refused(
            self, monkeypatch):
        assert name_section_refused(
            monkeypatch, replace('its path, its\nheader, and one line per rule',
                                 'one line per rule'), ONE_SPEC) == []


SEVERAL = 'when several match, list them and ask which one'
NONE = 'when none does, print the whole table'
ONE_SPEC = ('print its path, its header, and one line per rule with the cells '
            'the gate creates')


def reference_form_problems():
    return carries(COMMAND_REF, ['purlin:status [name]'])


def name_section_problems():
    body = flat(section(read(REL), r'^With a name$') or '')
    return ['%s With a name section does not carry %r' % (REL, needle)
            for needle in (SEVERAL, NONE, ONE_SPEC) if needle not in body]


def name_section_refused(monkeypatch, edit, needle):
    return refusals(monkeypatch, name_section_problems, [
        (REL, edit, '%s With a name section does not carry %r'
         % (REL, needle))])
