"""Text checks for the test skill, `skills/test/SKILL.md`.

Every rule of `specs/skills/skill_test.md` is proved here, one test for each
proof; a broken copy of the skill is a second assertion inside the test of
the proof it guards. The readers, the checks and the broken copies this file shares with
the other skill test files are in `dev/skill_checks.py`; the checks only this
skill needs are below the tests.
"""

import re

from skill_checks import (COMMAND_REF, carries, flat, frontmatter,
                          frontmatter_problems, in_order, next_step_problems,
                          on_copy, read, refusals, replace, resub, same_line,
                          section, sections, sentence_with,
                          skill_ceiling_problems, skill_path, swap_first,
                          undirected_outcome_problems)

REL = skill_path('test')


class TestTheFrontmatter:
    """RULE-1: the frontmatter."""

    # purlin: skill_test PROOF-1
    def test_the_shipped_frontmatter_names_the_skill_on_one_line(
            self, monkeypatch):
        assert frontmatter_skill_problems() == []
        line = description_line()
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace('name: test\n'),
             "%s frontmatter name is None, expected 'test'" % REL),
            (REL, replace(line, 'description:'), NO_ONE_LINE),
            (REL, replace(line, 'description:\n  ' + description()),
             NO_ONE_LINE),
            (REL, replace(line, 'description: |\n  ' + description()),
             NO_ONE_LINE),
            (REL, replace(line, 'description: >\n  ' + description()),
             NO_ONE_LINE),
            (REL, replace(line, line + '\n  and a second line'),
             NO_ONE_LINE),
        ]) == []


class TestTheCommandRow:
    """RULE-16: the row in the command reference."""

    # purlin: skill_test PROOF-19
    def test_the_shipped_command_reference_has_a_row_for_the_skill(
            self, monkeypatch):
        assert command_row_problems() == []
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:test'))
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:test' % COMMAND_REF),
        ]) == []


class TestTheRun:
    """RULE-2: the command."""

    # purlin: skill_test PROOF-2
    def test_the_shipped_skill_runs_the_script_with_test(self, monkeypatch):
        assert command_line_problems() == []
        assert refusals(monkeypatch, command_line_problems, [
            (REL, replace('purlin_run.py" --test', 'purlin_run.py"'),
             '%s has no single line carrying all of %r, %r'
             % (REL, RUN_SCRIPT, '--test')),
        ]) == []


class TestTheExitCodes:
    """RULE-8: the three exit codes on one line."""

    # purlin: skill_test PROOF-27
    def test_the_shipped_skill_gives_each_exit_code_its_meaning_on_one_line(
            self, monkeypatch):
        assert exit_line_problems() == []
        assert refusals(monkeypatch, exit_line_problems, [
            (REL, replace(', `2` the invocation', ',\n`2` the invocation'),
             "%s has no single line carrying all of 'Exit codes:'" % REL),
            (REL, replace(EXIT_ONE, '`1` something failed'),
             "%s has no single line carrying all of 'Exit codes:'" % REL),
            (REL, replace('the settings file cannot be read, '),
             "%s has no single line carrying all of 'Exit codes:'" % REL),
        ]) == []


class TestWhatARunCannotDo:
    """RULE-9: a test run cannot make an audit or a signature appear."""

    # purlin: skill_test PROOF-28
    def test_the_shipped_skill_says_a_run_cannot_make_an_audit_or_signature(
            self, monkeypatch):
        assert cannot_problems() == []
        assert refusals(monkeypatch, cannot_problems, [
            (REL, replace(CANNOT, 'does not audit or sign'),
             '%s does not carry %r' % (REL, CANNOT)),
        ]) == []


class TestTheNextStep:
    """RULE-3: the closing section names the next step for each outcome."""

    # purlin: skill_test PROOF-3
    def test_the_shipped_closing_section_directs_every_outcome(
            self, monkeypatch):
        assert closing_problems() == []
        text = read(REL)
        last = text.rindex('\n## ')
        before = sections(text)[-2][0]
        second = '| A line `<feature> RULE-<n> fails'
        row = '`→ Run: purlin:build <feature>` (fix the code or the test)'
        assert refusals(monkeypatch, closing_problems, [
            (REL, lambda t: t[:last + 1],
             '%s closes with the section %r' % (REL, before)),
            (REL, lambda t: t[:last] + t[last:].replace('→', '->'),
             '%s closing section gives no directive' % REL),
            (REL, lambda t: t[:t.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % REL),
            (REL, replace(row, row.replace('→ ', '')),
             '%s closing outcome gives no → directive: | A line '
             '`<feature> RULE-<n> fails' % REL),
        ]) == []


class TestTheCeiling:
    """RULE-4: the skill is at most 120 lines."""

    # purlin: skill_test PROOF-4
    def test_the_shipped_skill_is_at_most_120_lines(self):
        assert skill_ceiling_problems('test') == []

    # purlin: skill_test PROOF-30
    def test_a_copy_of_exactly_120_lines_is_not_reported(self, monkeypatch):
        assert ceiling_report(monkeypatch, 120) == []

    # purlin: skill_test PROOF-31
    def test_a_copy_of_121_lines_is_reported_with_its_count(
            self, monkeypatch):
        assert ceiling_report(monkeypatch, 121) == [
            '%s is 121 lines, ceiling 120' % REL]


class TestTheFilesTheRunWrites:
    """RULE-5: the two files the run writes."""

    # purlin: skill_test PROOF-5
    def test_the_shipped_skill_names_the_two_files_the_run_writes(self):
        assert carries(REL, ['.purlin/evidence/local/<feature>.json',
                             '.purlin/tests.md']) == []


class TestTheCommits:
    """RULE-10: what `--commit` makes, and the lines it prints."""

    # purlin: skill_test PROOF-32
    def test_the_shipped_skill_names_the_two_commits_in_order(
            self, monkeypatch):
        assert commit_problems() == []
        assert refusals(monkeypatch, commit_problems, [
            (REL, replace(FIRST_COMMIT, 'a commit'),
             '%s does not carry %r' % (REL, FIRST_COMMIT)),
            (REL, swap_first(FIRST_COMMIT, SECOND_COMMIT),
             '%s carries %r, %r out of order'
             % (REL, FIRST_COMMIT, SECOND_COMMIT)),
        ]) == []

    # purlin: skill_test PROOF-33
    def test_the_shipped_skill_names_the_two_lines_a_commit_prints(self):
        assert carries(REL, ['Evidence committed.',
                             'Evidence unchanged.']) == []


class TestNoPush:
    """RULE-11: the run never pushes."""

    # purlin: skill_test PROOF-34
    def test_the_shipped_skill_says_it_never_pushes(self):
        assert carries(REL, ['It never pushes.']) == []


class TestTheEnding:
    """RULE-12: the run ends on the summary, whose first line is the next
    step."""

    # purlin: skill_test PROOF-35
    def test_the_shipped_skill_says_the_run_ends_on_the_summary(self):
        assert sentence_with(REL, [ENDS_ON]) == []

    # purlin: skill_test PROOF-36
    def test_the_shipped_skill_says_the_first_line_left_is_the_next_step(
            self, monkeypatch):
        assert next_line_problems() == []
        assert refusals(monkeypatch, next_line_problems, [
            (REL, resub(r'The first line of `Left to do` is the next\s+step',
                        'The lines follow'),
             '%s has no sentence carrying all of %r' % (REL, FIRST_LINE)),
        ]) == []


class TestARunWithNoFeatureNamed:
    """RULE-6: what a run with no feature named selects."""

    # purlin: skill_test PROOF-38
    def test_the_shipped_paragraph_gives_the_four_reasons(self, monkeypatch):
        assert selection_paragraph_problems(REASONS) == []
        assert refusals(
            monkeypatch, lambda: selection_paragraph_problems(REASONS), [
                (REL, replace('under its `> Scope:` or beside its tests',
                              'in the project'),
                 '%s paragraph on a run with no feature named does not carry '
                 '%r' % (REL, REASONS[2])),
            ]) == []

    # purlin: skill_test PROOF-39
    def test_the_shipped_paragraph_runs_only_the_test_files(self):
        assert selection_paragraph_problems(RUNS_ONLY) == []


class TestEveryFeature:
    """RULE-13: `purlin:test --all` runs every feature."""

    # purlin: skill_test PROOF-6
    def test_the_shipped_usage_lists_all(self, monkeypatch):
        assert usage_problems() == []
        assert refusals(monkeypatch, usage_problems, [
            (REL, replace('purlin:test --all               Run every '
                          'feature\n'),
             '%s usage does not name purlin:test --all' % REL),
        ]) == []


class TestNothingSelected:
    """RULE-14: the line the run prints when it selects nothing."""

    # purlin: skill_test PROOF-40
    def test_the_shipped_paragraph_carries_the_whole_nothing_line(
            self, monkeypatch):
        assert selection_paragraph_problems((NOTHING_TO_RUN,)) == []
        moved = resub(r'With nothing selected it prints `Nothing to run:'
                      r'.*?anyway\.` ')

        def edit(text):
            return moved(text) + '\nWith nothing selected it prints `%s`\n' \
                % NOTHING_TO_RUN
        assert refusals(
            monkeypatch, lambda: selection_paragraph_problems(
                (NOTHING_TO_RUN,)), [
                (REL, edit,
                 '%s paragraph on a run with no feature named does not carry '
                 '%r' % (REL, NOTHING_TO_RUN)),
            ]) == []


class TestASuggestedSetting:
    """RULE-7: what the skill does with a suggested `tests` setting."""

    # purlin: skill_test PROOF-12
    def test_the_shipped_row_for_a_suggestion_asks_writes_and_runs_again(
            self, monkeypatch):
        assert stop_row_problems(*SUGGESTED_ROW) == []
        assert refusals(
            monkeypatch, lambda: stop_row_problems(*SUGGESTED_ROW), [
                (REL, replace('the `purlin_config` tool', 'a tool'),
                 '%s row for %r does not carry '
                 "'the `purlin_config` tool'" % (REL, SUGGESTED_ROW[0])),
            ]) == []


class TestNoToolFound:
    """RULE-15: what the skill does where the run found no test tool."""

    # purlin: skill_test PROOF-44
    def test_the_shipped_row_for_no_tool_reads_proposes_and_runs_again(self):
        assert stop_row_problems(*NO_TOOL_ROW) == []


# ---------------------------------------------------------------------------
# RULE-1 and RULE-16
# ---------------------------------------------------------------------------

NO_ONE_LINE = '%s frontmatter carries no one-line description' % REL


def frontmatter_skill_problems():
    """What the shared frontmatter check finds in the skill file itself."""
    return [problem for problem in frontmatter_problems('test')
            if problem.startswith(REL)]


def command_row_problems():
    """What the shared frontmatter check finds in the command reference."""
    return [problem for problem in frontmatter_problems('test')
            if problem.startswith(COMMAND_REF)]


def description():
    block = frontmatter(read(REL))
    return re.search(r'^description: (.+)$', block, re.M).group(1)


def description_line():
    return 'description: ' + description()


# ---------------------------------------------------------------------------
# RULE-2, RULE-8 and RULE-9
# ---------------------------------------------------------------------------

RUN_SCRIPT = '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"'

# The meaning of exit code 1, as the skill's one line gives it.
EXIT_ONE = ('`1` a tied test failed or did not run, evidence is missing, a '
            'marker names nothing a spec has, there is no settings file, the '
            'settings file cannot be read, an older Purlin set the project '
            'up, or no test command is set')

CANNOT = 'cannot make an audit or a signature appear'


def command_line_problems():
    return same_line(REL, [RUN_SCRIPT, '--test'])


def exit_line_problems():
    return same_line(REL, ['Exit codes:', '`0` everything asked happened',
                           EXIT_ONE, '`2` the invocation was wrong'])


def cannot_problems():
    return carries(REL, [CANNOT])


# ---------------------------------------------------------------------------
# RULE-3
# ---------------------------------------------------------------------------

def closing_problems():
    heading = sections(read(REL))[-1][0]
    named = [] if re.search('next step', heading, re.I) else [
        '%s closing heading %r does not carry next step' % (REL, heading)]
    return (named + next_step_problems('test')
            + undirected_outcome_problems('test'))


# ---------------------------------------------------------------------------
# RULE-4
# ---------------------------------------------------------------------------

def ceiling_report(monkeypatch, lines):
    """What the ceiling check reports on a copy padded to `lines` lines."""
    def pad(text):
        return text + 'A line of prose.\n' * (lines - len(text.splitlines()))
    assert len(pad(read(REL)).splitlines()) == lines
    return on_copy(monkeypatch, REL, pad,
                   lambda: skill_ceiling_problems('test'))


# ---------------------------------------------------------------------------
# RULE-5, RULE-10 and RULE-12
# ---------------------------------------------------------------------------

# The subjects of the two commits `--commit` makes, in the order it makes them.
FIRST_COMMIT = 'purlin: specs, tests and settings for <feature>'
SECOND_COMMIT = 'purlin: evidence at <sha7>'

ENDS_ON = 'The run ends on the summary sentence and `Left to do`'
FIRST_LINE = 'The first line of `Left to do` is the next step'


def commit_problems():
    return (carries(REL, ['--commit'])
            + in_order(REL, [FIRST_COMMIT, SECOND_COMMIT], wrapped=True))


def next_line_problems():
    return sentence_with(REL, [FIRST_LINE])


# ---------------------------------------------------------------------------
# RULE-6, RULE-13 and RULE-14
# ---------------------------------------------------------------------------

# Why a run with no feature named selects a feature.
REASONS = (
    'with no run on this operating system',
    'whose spec, code or tests changed since its evidence',
    'with an untracked file under its `> Scope:` or beside its tests',
    'whose spec names no files',
)

RUNS_ONLY = ('runs only the test files', 'purlin:test --all runs them too.')

# The line the run prints when it selects nothing.
NOTHING_TO_RUN = ("Nothing to run: every feature's spec, code and tests match "
                  'its evidence. purlin:test --all runs them anyway.')


def usage_problems():
    usage = section(read(REL), r'^usage')
    if usage and 'purlin:test --all' in usage:
        return []
    return ['%s usage does not name purlin:test --all' % REL]


def selection_paragraph_problems(needles):
    """The needles the paragraph on a run with no feature named lacks."""
    paragraph = next((flat(p) for p in re.split(r'\n\s*\n', read(REL))
                      if 'With neither, the run selects' in flat(p)), None)
    if paragraph is None:
        return ['%s has no paragraph on a run with no feature named' % REL]
    return ['%s paragraph on a run with no feature named does not carry %r'
            % (REL, needle) for needle in needles if needle not in paragraph]


# ---------------------------------------------------------------------------
# RULE-7 and RULE-15
# ---------------------------------------------------------------------------

# Each row of the section on a run that stops before any test: what the run
# prints, and what the row tells the agent to do.
SUGGESTED_ROW = (
    '`Suggested tests setting: <the entries as one JSON array on one line>`', (
        'Show the person each suggested command', 'ask once',
        'write that array as the `tests` setting',
        'the `purlin_config` tool', 'run Step 1 again'))
NO_TOOL_ROW = ('`no test tool Purlin knows was found`', (
    'Read the project', 'propose one entry', 'Ask',
    'write it the same way', 'run Step 1 again'))


def stop_row_problems(printed, needles):
    body = next((body for heading, body in sections(read(REL))
                 if heading.startswith('Step 2')), None)
    if body is None:
        return ['%s has no section on a run that stops before any test' % REL]
    row = next((line for line in body.splitlines()
                if line.startswith('|') and printed in line), None)
    if row is None:
        return ['%s has no row for %r' % (REL, printed)]
    return ['%s row for %r does not carry %r' % (REL, printed, needle)
            for needle in needles if needle not in row]
