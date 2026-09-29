"""Text checks for the test skill, `skills/test/SKILL.md`.

Every rule of `specs/skills/skill_test.md` is proved here, one test for each
proof. The readers, the checks and the broken copies this file shares with
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


class TestTheFrontmatterAndTheCommandRow:
    """RULE-1: the frontmatter, and the row in the command reference."""

    # purlin: skill_test PROOF-1
    def test_the_shipped_frontmatter_names_the_skill_on_one_line(self):
        assert frontmatter_skill_problems() == []

    # purlin: skill_test PROOF-19
    def test_the_shipped_command_reference_has_a_row_for_the_skill(self):
        assert command_row_problems() == []

    # purlin: skill_test PROOF-20
    def test_a_copy_with_no_name_line_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace('name: test\n'),
             "%s frontmatter name is None, expected 'test'" % REL),
        ]) == []

    # purlin: skill_test PROOF-21
    def test_a_copy_with_an_empty_description_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace(description_line(), 'description:'), NO_ONE_LINE),
        ]) == []

    # purlin: skill_test PROOF-22
    def test_a_copy_with_the_description_on_the_next_line_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace(description_line(),
                          'description:\n  ' + description()), NO_ONE_LINE),
        ]) == []

    # purlin: skill_test PROOF-23
    def test_a_copy_with_a_bar_block_description_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace(description_line(),
                          'description: |\n  ' + description()), NO_ONE_LINE),
        ]) == []

    # purlin: skill_test PROOF-24
    def test_a_copy_with_a_folded_block_description_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace(description_line(),
                          'description: >\n  ' + description()), NO_ONE_LINE),
        ]) == []

    # purlin: skill_test PROOF-25
    def test_a_copy_with_the_description_run_onto_a_second_line_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_skill_problems, [
            (REL, replace(description_line(),
                          description_line() + '\n  and a second line'),
             NO_ONE_LINE),
        ]) == []

    # purlin: skill_test PROOF-26
    def test_a_command_reference_without_the_row_is_reported(
            self, monkeypatch):
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:test'))
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:test' % COMMAND_REF),
        ]) == []


class TestTheRunAndItsExitCodes:
    """RULE-2: the command, its exit codes, and what a run cannot do."""

    # purlin: skill_test PROOF-2
    def test_the_shipped_skill_runs_the_script_with_test(self):
        assert command_line_problems() == []

    # purlin: skill_test PROOF-27
    def test_the_shipped_skill_gives_each_exit_code_its_meaning_on_one_line(
            self):
        assert exit_line_problems() == []

    # purlin: skill_test PROOF-28
    def test_the_shipped_skill_says_a_run_cannot_make_an_audit_or_signature(
            self):
        assert cannot_problems() == []

    # purlin: skill_test PROOF-8
    def test_a_copy_with_exit_code_two_on_the_next_line_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, exit_line_problems, [
            (REL, replace(', `2` the invocation', ',\n`2` the invocation'),
             "%s has no single line carrying all of 'Exit codes:'" % REL),
        ]) == []

    # purlin: skill_test PROOF-17
    def test_a_copy_with_exit_code_one_reworded_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, exit_line_problems, [
            (REL, replace(EXIT_ONE, '`1` something failed'),
             "%s has no single line carrying all of 'Exit codes:'" % REL),
        ]) == []

    # purlin: skill_test PROOF-9
    def test_a_copy_with_test_off_the_command_line_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, command_line_problems, [
            (REL, replace('purlin_run.py" --test', 'purlin_run.py"'),
             '%s has no single line carrying all of %r, %r'
             % (REL, RUN_SCRIPT, '--test')),
        ]) == []

    # purlin: skill_test PROOF-29
    def test_a_copy_without_the_cannot_sentence_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, cannot_problems, [
            (REL, replace(CANNOT, 'does not audit or sign'),
             '%s does not carry %r' % (REL, CANNOT)),
        ]) == []


class TestTheNextStep:
    """RULE-3: the closing section names the next step for each outcome."""

    # purlin: skill_test PROOF-3
    def test_the_shipped_closing_section_directs_every_outcome(self):
        assert closing_problems() == []

    # purlin: skill_test PROOF-10
    def test_a_copy_with_no_closing_section_is_reported(self, monkeypatch):
        last = read(REL).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (REL, lambda t: t[:last + 1],
             "%s closes with the section 'Step 5: operating systems'" % REL),
        ]) == []

    # purlin: skill_test PROOF-14
    def test_a_copy_with_no_arrow_in_the_closing_section_is_reported(
            self, monkeypatch):
        last = read(REL).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (REL, lambda t: t[:last] + t[last:].replace('→', '->'),
             '%s closing section gives no directive' % REL),
        ]) == []

    # purlin: skill_test PROOF-15
    def test_a_copy_cut_after_the_first_outcome_is_reported(
            self, monkeypatch):
        last = read(REL).rindex('\n## ')
        second = '| A line `<feature> RULE-<n> fails'
        assert refusals(monkeypatch, closing_problems, [
            (REL, lambda t: t[:t.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % REL),
        ]) == []

    # purlin: skill_test PROOF-16
    def test_a_copy_with_one_outcome_undirected_is_reported(
            self, monkeypatch):
        row = '`→ Run: purlin:build <feature>` (fix the code or the test)'
        assert refusals(monkeypatch, closing_problems, [
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


class TestTheEvidenceAndTheEnding:
    """RULE-5: what the run writes, what `--commit` makes, how the run ends."""

    # purlin: skill_test PROOF-5
    def test_the_shipped_skill_names_the_two_files_the_run_writes(self):
        assert carries(REL, ['.purlin/evidence/local/<feature>.json',
                             '.purlin/tests.md']) == []

    # purlin: skill_test PROOF-32
    def test_the_shipped_skill_names_the_two_commits_in_order(self):
        assert commit_problems() == []

    # purlin: skill_test PROOF-33
    def test_the_shipped_skill_names_the_two_lines_a_commit_prints(self):
        assert carries(REL, ['Evidence committed.',
                             'Evidence unchanged.']) == []

    # purlin: skill_test PROOF-34
    def test_the_shipped_skill_says_it_never_pushes(self):
        assert carries(REL, ['It never pushes.']) == []

    # purlin: skill_test PROOF-35
    def test_the_shipped_skill_says_the_run_ends_on_the_summary(self):
        assert sentence_with(REL, [ENDS_ON]) == []

    # purlin: skill_test PROOF-36
    def test_the_shipped_skill_says_the_first_line_left_is_the_next_step(
            self):
        assert next_line_problems() == []

    # purlin: skill_test PROOF-11
    def test_a_copy_without_the_first_commit_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, commit_problems, [
            (REL, replace(FIRST_COMMIT, 'a commit'),
             '%s does not carry %r' % (REL, FIRST_COMMIT)),
        ]) == []

    # purlin: skill_test PROOF-37
    def test_a_copy_with_the_two_commits_swapped_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, commit_problems, [
            (REL, swap_first(FIRST_COMMIT, SECOND_COMMIT),
             '%s carries %r, %r out of order'
             % (REL, FIRST_COMMIT, SECOND_COMMIT)),
        ]) == []

    # purlin: skill_test PROOF-18
    def test_a_copy_without_the_next_step_sentence_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, next_line_problems, [
            (REL, replace(FIRST_LINE, 'The lines follow'),
             '%s has no sentence carrying all of %r' % (REL, FIRST_LINE)),
        ]) == []


class TestARunWithNoFeatureNamed:
    """RULE-6: what a run with no feature named selects and prints."""

    # purlin: skill_test PROOF-6
    def test_the_shipped_usage_lists_all(self):
        assert usage_problems() == []

    # purlin: skill_test PROOF-38
    def test_the_shipped_paragraph_gives_the_four_reasons(self):
        assert selection_paragraph_problems(REASONS) == []

    # purlin: skill_test PROOF-39
    def test_the_shipped_paragraph_runs_only_the_test_files(self):
        assert selection_paragraph_problems(RUNS_ONLY) == []

    # purlin: skill_test PROOF-40
    def test_the_shipped_paragraph_carries_the_whole_nothing_line(self):
        assert selection_paragraph_problems((NOTHING_TO_RUN,)) == []

    # purlin: skill_test PROOF-41
    def test_a_copy_without_all_in_the_usage_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, usage_problems, [
            (REL, replace('purlin:test --all               Run every '
                          'feature\n'),
             '%s usage does not name purlin:test --all' % REL),
        ]) == []

    # purlin: skill_test PROOF-42
    def test_a_copy_with_the_nothing_line_moved_to_the_end_is_reported(
            self, monkeypatch):
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

    # purlin: skill_test PROOF-43
    def test_a_copy_whose_untracked_reason_names_no_scope_is_reported(
            self, monkeypatch):
        assert refusals(
            monkeypatch, lambda: selection_paragraph_problems(REASONS), [
                (REL, replace('under its `> Scope:` or beside its tests',
                              'in the project'),
                 '%s paragraph on a run with no feature named does not carry '
                 '%r' % (REL, REASONS[2])),
            ]) == []


class TestARunThatStopsBeforeAnyTest:
    """RULE-7: what the skill does when the run has no test command."""

    # purlin: skill_test PROOF-12
    def test_the_shipped_row_for_a_suggestion_asks_writes_and_runs_again(
            self):
        assert stop_row_problems(*SUGGESTED_ROW) == []

    # purlin: skill_test PROOF-44
    def test_the_shipped_row_for_no_tool_reads_proposes_and_runs_again(self):
        assert stop_row_problems(*NO_TOOL_ROW) == []

    # purlin: skill_test PROOF-13
    def test_a_copy_whose_suggestion_row_names_no_tool_is_reported(
            self, monkeypatch):
        assert refusals(
            monkeypatch, lambda: stop_row_problems(*SUGGESTED_ROW), [
                (REL, replace('the `purlin_config` tool', 'a tool'),
                 "%s row for '`Suggested entry: <JSON>`' does not carry "
                 "'the `purlin_config` tool'" % REL),
            ]) == []


# ---------------------------------------------------------------------------
# RULE-1
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
# RULE-2
# ---------------------------------------------------------------------------

RUN_SCRIPT = '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"'

# The meaning of exit code 1, as the skill's one line gives it.
EXIT_ONE = ('`1` a tied test failed or did not run, evidence is missing, a '
            'marker names nothing a spec has, there is no settings file, an '
            'older Purlin set the project up, or no test command is set')

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
# RULE-5
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
# RULE-6
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
# RULE-7
# ---------------------------------------------------------------------------

# Each row of the section on a run that stops before any test: what the run
# prints, and what the row tells the agent to do.
SUGGESTED_ROW = ('`Suggested entry: <JSON>`', (
    'Show the person the command and ask', 'the `purlin_config` tool',
    'key `tests`', 'run Step 1 again'))
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
