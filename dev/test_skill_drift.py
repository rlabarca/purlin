"""Text checks for the drift skill, `skills/drift/SKILL.md`.

Every rule of `specs/skills/skill_drift.md` is proved here, one test per
proof; a broken copy of the skill is a second assertion inside the test of
the proof it guards. The readers, the checks and the broken copies this
file shares with the other skill test files are in `dev/skill_checks.py`;
the checks only this spec needs are below the tests.
"""

import re

from skill_checks import (COMMAND_REF, carries, field, flat, frontmatter,
                          frontmatter_problems, next_step_problems,
                          next_step_refusals, on_copy, read, refusals,
                          replace, section, sections, skill_ceiling_problems,
                          skill_path, table_rows, undirected_outcome_problems)

SKILL = skill_path('drift')
CRITERIA = 'references/drift_criteria.md'
NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL
NO_ROW = '%s carries no row for purlin:drift' % COMMAND_REF
ROW_START = '| `purlin:drift [role]` |'


class TestSkillDrift:

    # RULE-1: the frontmatter.

    # purlin: skill_drift PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self, monkeypatch):
        assert [problem for problem in frontmatter_check()
                if problem.startswith(SKILL)] == []
        line = description_line()
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace('name: drift\n'),
             "%s frontmatter name is None, expected 'drift'" % SKILL),
            (SKILL, replace(line, 'description:'), NO_DESCRIPTION),
            (SKILL, replace(line, 'description: >-\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(line, 'description: |\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(line, 'description:\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(line, line + '\n  and a second line'),
             NO_DESCRIPTION),
            (SKILL, lambda text: '\n' + text,
             '%s does not open with a frontmatter block' % SKILL)]) == []

    # RULE-9: the command reference.

    # purlin: skill_drift PROOF-9
    def test_the_command_reference_carries_a_row_for_drift(self, monkeypatch):
        assert [problem for problem in frontmatter_check()
                if problem.startswith(COMMAND_REF)] == []
        row = command_row()
        cells = [cell.strip() for cell in row.strip('|').split('|')]
        assert cells[0] == '`purlin:drift [role]`' and cells[1]
        removed = replace(row + '\n')
        # The command's name is still in the reference outside the table.
        assert 'purlin:drift' in removed(read(COMMAND_REF))
        assert refusals(monkeypatch, frontmatter_check, [
            (COMMAND_REF, replace(row, ROW_START + ' |'), NO_ROW),
            (COMMAND_REF, removed, NO_ROW)]) == []

    # RULE-2: the tool, the lines as they come, and the criteria.

    # purlin: skill_drift PROOF-2
    def test_the_data_comes_from_the_drift_tool(self):
        body = section(read(SKILL), r'get the data')
        assert body is not None, '%s has no step that gets the data' % SKILL
        assert '```\ndrift(role="eng")\n```' in body

    # purlin: skill_drift PROOF-19
    def test_it_points_at_the_criteria_for_what_a_line_means(self):
        assert carries(SKILL, [
            'What each line means and which git facts it comes from live '
            'in `references/drift_criteria.md`']) == []

    # purlin: skill_drift PROOF-20
    def test_it_says_to_restate_nothing_and_invent_nothing(self):
        assert carries(SKILL, [
            'do not restate them here and do not invent a line the tool '
            'does not return']) == []

    # purlin: skill_drift PROOF-21
    def test_it_says_to_print_the_lines_as_they_come(self):
        body = section(read(SKILL), r'print the view')
        assert body is not None, '%s has no step that prints the view' % SKILL
        text = flat(body)
        assert 'Print `lines` as they come, one per line' in text
        assert 'Do not reword a line, do not drop one' in text

    # purlin: skill_drift PROOF-22
    def test_it_repeats_no_definition_from_the_criteria(self, monkeypatch):
        assert drift_restated_problems() == []
        fact = 'Rules whose passed cell reads `no test`'
        start = ("Where HEAD stood before the rebase's first step, "
                 '`rebase (start)`')
        condition = 'A `> Source:` with no `> Pinned:`'
        command = 'git reflog show HEAD'
        assert refusals(monkeypatch, drift_restated_problems, [
            (SKILL, paste(fact),
             '%s restates what %s says a line is built from: %r'
             % (SKILL, CRITERIA, fact)),
            (SKILL, paste(start),
             '%s restates where %s says the range starts: %r'
             % (SKILL, CRITERIA, start)),
            (SKILL, paste(condition),
             '%s restates an anchor condition from %s: %r'
             % (SKILL, CRITERIA, condition)),
            (SKILL, paste('`%s`' % command),
             '%s names a git command %s gives as a source: %r'
             % (SKILL, CRITERIA, command))]) == []

    # RULE-3: the closing section.

    # purlin: skill_drift PROOF-3
    def test_it_closes_by_naming_the_next_step(self, monkeypatch):
        assert closing_check() == []
        assert next_step_refusals(
            monkeypatch, 'drift', '| A rule removed',
            '| A rule removed | `\u2192 Run: purlin:status <feature>` |') == []
        last = read(SKILL).rindex('\n## ')
        assert refusals(monkeypatch, closing_check, [
            (SKILL, lambda text: text[:text.index('| A rule added', last)],
             '%s closing section names 0 outcomes, expected at least 2'
             % SKILL)]) == []

    # purlin: skill_drift PROOF-27
    def test_every_kind_of_line_has_its_next_step(self, monkeypatch):
        assert drift_outcome_problems() == []
        row = next(line for line in read(SKILL).splitlines()
                   if line.startswith('| An anchor behind its source |'))
        assert refusals(monkeypatch, drift_outcome_problems, [
            (SKILL, replace(row + '\n'),
             '%s gives no next step for the line anchors_behind: no row %r'
             % (SKILL, 'An anchor behind its source'))]) == []

    # RULE-4: the ceiling.

    # purlin: skill_drift PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('drift') == []

    # purlin: skill_drift PROOF-34
    def test_a_skill_of_exactly_150_lines_is_let_through(self, monkeypatch):
        assert on_copy(monkeypatch, SKILL, lengthen_to(150),
                       lambda: skill_ceiling_problems('drift')) == []

    # purlin: skill_drift PROOF-35
    def test_a_skill_of_151_lines_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('drift'), [
            (SKILL, lengthen_to(151),
             '%s is 151 lines, ceiling 150' % SKILL)]) == []


# ---------------------------------------------------------------------------
# RULE-1
# ---------------------------------------------------------------------------

def frontmatter_check():
    return frontmatter_problems('drift')


def description():
    return field(frontmatter(read(SKILL)), 'description')


def description_line():
    return 'description: %s' % description()


def command_row():
    return next(line for line in read(COMMAND_REF).splitlines()
                if line.startswith(ROW_START))


# ---------------------------------------------------------------------------
# RULE-2
# ---------------------------------------------------------------------------

def column(header, index):
    """Cell `index` of every row of every table in the criteria headed
    `header`."""
    return [cells[index] for chunk in read(CRITERIA).split(header)[1:]
            for cells in table_rows(header + chunk, header)]


def git_commands():
    """Every git command the criteria name in backticks, once each."""
    found = re.findall(r'`(git [^`]+)`', read(CRITERIA))
    return list(dict.fromkeys(found))


def drift_restated_problems():
    """The skill repeats none of the criteria's definitions: the `From` cell
    of the `eng` and `qa` tables, the cell saying where the range starts, the
    anchor conditions, and the git commands named as sources."""
    # What each kind is called when too few are found, the cells, and the
    # problem one of them in the skill is reported as.
    kinds = [
        ('the eng and qa tables', column('| Key | From | Line |', 1),
         '%s restates what %s says a line is built from: %r'),
        ('the range table',
         column('| Action | The entry git writes | Where the range starts |',
                2),
         '%s restates where %s says the range starts: %r'),
        ('the anchor table', column('| Condition | Line |', 0),
         '%s restates an anchor condition from %s: %r'),
        ('its git commands', git_commands(),
         '%s names a git command %s gives as a source: %r'),
    ]
    # Two of each at least, so the check never passes on a table it lost.
    problems = ['%s has %d entries in %s, expected at least 2'
                % (CRITERIA, len(cells), name)
                for name, cells, _ in kinds if len(cells) < 2]
    if problems:
        return problems
    text = flat(read(SKILL))
    return [shape % (SKILL, CRITERIA, cell) for _, cells, shape in kinds
            for cell in cells if flat(cell) in text]


def paste(fact):
    """An edit that adds a paragraph carrying `fact` above the print step."""
    heading = '## Step 2: print the view'
    return replace(heading, 'A line: %s.\n\n%s' % (fact, heading))


# ---------------------------------------------------------------------------
# RULE-3
# ---------------------------------------------------------------------------

def closing_check():
    return next_step_problems('drift') + undirected_outcome_problems('drift')


CLOSING_HEADER = '| What the view shows | The line to print |'

# Each kind of line the three views print, by its key in the criteria, and
# the row of the closing table that names its next step. `specs_uncommitted`
# ends every view, and `none of the three` is the PM view with no rule moved.
OUTCOME_ROWS = {
    'rules_added': 'A rule added or changed',
    'rules_changed': 'A rule added or changed',
    'rules_removed': 'A rule removed',
    'none of the three': 'Only the first line, or only `No rule was added, ...`',
    'code_changed': "Code changed under a spec's scope",
    'unscoped': "A changed file under no spec's scope",
    'rules_without_test': 'A rule with no test',
    'anchors_behind': 'An anchor behind its source',
    'out_of_date': 'A feature out of date',
    'tests_changed': 'A test file changed',
    'left': 'A rule to test by hand or to sign',
    'specs_uncommitted': 'Spec files not committed',
}


def drift_outcome_problems():
    """Every kind of line the criteria give the three views, and the view with
    no change, has a row of its own in the closing table. A key whose line
    cell reads `No line` prints nothing and needs none."""
    body = sections(read(SKILL))[-1][1]
    if CLOSING_HEADER not in body:
        return ['%s closing section has no table headed %r'
                % (SKILL, CLOSING_HEADER)]
    rows = {cells[0] for cells in table_rows(body, CLOSING_HEADER)}
    keys = [cells[0] for header, line in (('| Key | Line |', 1),
                                          ('| Key | From | Line |', 2))
            for chunk in read(CRITERIA).split(header)[1:]
            for cells in table_rows(header + chunk, header)
            if cells[line] != 'No line']
    keys = [key.strip('`') for key in keys] + ['specs_uncommitted']
    problems = []
    for key in keys:
        if key not in OUTCOME_ROWS:
            problems.append('%s names the line %s, which this check maps to '
                            'no row' % (CRITERIA, key))
        elif OUTCOME_ROWS[key] not in rows:
            problems.append('%s gives no next step for the line %s: no row %r'
                            % (SKILL, key, OUTCOME_ROWS[key]))
    return problems


# ---------------------------------------------------------------------------
# RULE-4
# ---------------------------------------------------------------------------

def lengthen_to(count):
    """An edit that adds lines of prose until the file is `count` lines."""
    def edit(text):
        missing = count - len(text.splitlines())
        assert missing > 0, 'the file is already %d lines' % count
        return text + 'A line of prose.\n' * missing
    return edit
