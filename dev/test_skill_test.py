"""Text checks for the test skill, `skills/test/SKILL.md`.

Every rule of `specs/skills/skill_test.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems, read,
                          refusals, replace, resub, same_line, section,
                          sections, sentence_with, skill_ceiling_problems,
                          skill_path, undirected_outcome_problems)


class TestSkillTest:

    # purlin: skill_test PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('test') == []

    # purlin: skill_test PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'test') == []

    # purlin: skill_test PROOF-2
    def test_it_runs_the_run_script_and_names_its_exit_codes(self):
        assert run_line_problems() == []

    # purlin: skill_test PROOF-8
    def test_an_exit_code_moved_off_the_line_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, run_line_problems, [
            (rel, replace(', `2` the invocation', ',\n`2` the invocation'),
             "%s has no single line carrying all of 'Exit codes:'" % rel),
        ]) == []

    # purlin: skill_test PROOF-17
    def test_an_exit_code_reworded_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, run_line_problems, [
            (rel, replace(EXIT_ONE, '`1` something failed'),
             "%s has no single line carrying all of 'Exit codes:'" % rel),
        ]) == []

    # purlin: skill_test PROOF-9
    def test_the_command_without_test_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, run_line_problems, [
            (rel, replace('purlin_run.py" --test', 'purlin_run.py"'),
             '%s has no single line carrying all of '
             '\'"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"\', '
             "'--test'" % rel),
        ]) == []

    # purlin: skill_test PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('test')
                + undirected_outcome_problems('test')) == []

    # purlin: skill_test PROOF-10
    def test_a_copy_with_no_closing_section_is_refused(self, monkeypatch):
        rel = skill_path('test')
        last = read(rel).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (rel, lambda t: t[:last + 1],
             "%s closes with the section 'Step 5: operating systems'" % rel),
        ]) == []

    # purlin: skill_test PROOF-14
    def test_a_copy_with_no_directive_is_refused(self, monkeypatch):
        rel = skill_path('test')
        last = read(rel).rindex('\n## ')
        assert refusals(monkeypatch, closing_problems, [
            (rel, lambda t: t[:last] + t[last:].replace('→', '->'),
             '%s closing section gives no directive' % rel),
        ]) == []

    # purlin: skill_test PROOF-15
    def test_a_copy_with_one_outcome_is_refused(self, monkeypatch):
        rel = skill_path('test')
        last = read(rel).rindex('\n## ')
        second = '| A line `<feature> RULE-<n> fails'
        assert refusals(monkeypatch, closing_problems, [
            (rel, lambda t: t[:t.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % rel),
        ]) == []

    # purlin: skill_test PROOF-16
    def test_a_row_with_no_directive_is_refused(self, monkeypatch):
        rel = skill_path('test')
        row = '`→ Run: purlin:build <feature>` (fix the code or the test)'
        assert refusals(monkeypatch, closing_problems, [
            (rel, replace(row, row.replace('→ ', '')),
             '%s closing outcome gives no → directive' % rel),
        ]) == []

    # purlin: skill_test PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('test') == []

    # purlin: skill_test PROOF-5
    def test_it_names_the_evidence_the_commits_and_the_ending(self):
        assert evidence_line_problems() == []

    # purlin: skill_test PROOF-11
    def test_a_copy_without_the_first_commit_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, evidence_line_problems, [
            (rel, replace(FIRST_COMMIT, 'a commit'),
             "%s does not carry %r" % (rel, FIRST_COMMIT)),
        ]) == []

    # purlin: skill_test PROOF-18
    def test_a_copy_without_the_next_step_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, evidence_line_problems, [
            (rel, replace('The first line of `Left to do` is the next step',
                          'The lines follow'),
             "'The first line of `Left to do` is the next step'"),
        ]) == []

    # purlin: skill_test PROOF-6
    def test_it_says_what_a_run_with_no_feature_named_runs(self):
        assert selection_problems() == []

    # purlin: skill_test PROOF-6
    def test_a_selection_paragraph_broken_is_refused(self, monkeypatch):
        rel = skill_path('test')
        nothing = ("With nothing selected it prints `Nothing to run: every "
                   "feature's spec, code and tests match its evidence.`")
        assert refusals(monkeypatch, selection_problems, [
            (rel, replace('purlin:test --all               Run every '
                          'feature\n'),
             '%s usage does not name purlin:test --all' % rel),
            (rel, lambda t: resub(r'With nothing selected it prints '
                                  r'`Nothing to run:.*?anyway\.` ')(t)
             + '\n' + nothing + '\n',
             "%s paragraph on a run with no feature named does not carry "
             "\"Nothing to run" % rel),
            (rel, replace('under its `> Scope:` or beside its tests',
                          'in the project'),
             '%s paragraph on a run with no feature named does not carry '
             "'with an untracked file under its `> Scope:`" % rel),
        ]) == []

    # purlin: skill_test PROOF-12
    def test_it_says_what_to_do_when_the_run_stops(self):
        assert stop_problems() == []

    # purlin: skill_test PROOF-13
    def test_a_stop_section_without_the_tool_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, stop_problems, [
            (rel, lambda t: t.replace('the `purlin_config` tool', 'a tool'),
             "%s stop section does not carry 'purlin_config'" % rel),
        ]) == []


# The meaning of exit code 1, as the skill's one line gives it.
EXIT_ONE = ('`1` a tied test failed or did not run, evidence is missing, a '
            'marker names nothing a spec has, there is no settings file, an '
            'older Purlin set the project up, or no test command is set')

# The subject of the first of the two commits `--commit` makes.
FIRST_COMMIT = 'purlin: specs, tests and settings for <feature>'


def run_line_problems():
    rel = skill_path('test')
    return (same_line(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--test'])
        + same_line(rel, [
            'Exit codes:', '`0` everything asked happened', EXIT_ONE,
            '`2` the invocation was wrong'])
        + carries(rel, ['cannot make an audit or a signature appear']))


def closing_problems():
    return next_step_problems('test') + undirected_outcome_problems('test')


def evidence_line_problems():
    rel = skill_path('test')
    return (carries(rel, [
        '.purlin/evidence/local/<feature>.json', '.purlin/tests.md',
        '--commit', FIRST_COMMIT, 'purlin: evidence at <sha7>',
        'Evidence committed.', 'Evidence unchanged.', 'It never pushes.'])
        + sentence_with(rel, [
            'The run ends on the summary sentence and `Left to do`'])
        + sentence_with(rel, [
            'The first line of `Left to do` is the next step']))


# What the section on a run that stops before any test carries.
STOP_WORDS = ('Suggested entry:', 'purlin_config', 'key `tests`', 'ask',
              'run Step 1 again', 'no test tool Purlin knows was found',
              'Read the project', 'propose one entry')


def stop_problems():
    rel = skill_path('test')
    body = next((body for heading, body in sections(read(rel))
                 if heading.startswith('Step 2')), None)
    if body is None:
        return ['%s has no section on a run that stops before any test' % rel]
    return ['%s stop section does not carry %r' % (rel, needle)
            for needle in STOP_WORDS if needle not in body]


# The run with no feature named, in the words of the paragraph that says so.
TEST_SELECTION = (
    'with no run on this operating system',
    'whose spec, code or tests changed since its evidence',
    'with an untracked file under its `> Scope:` or beside its tests',
    'whose spec names no files', 'runs only the test files',
    'purlin:test --all runs them too.',
    "Nothing to run: every feature's spec, code and tests match its "
    'evidence.',
)


def selection_problems():
    rel = skill_path('test')
    text = read(rel)
    usage = section(text, r'^usage')
    problems = [] if usage and 'purlin:test --all' in usage else [
        '%s usage does not name purlin:test --all' % rel]
    problems.extend(carries(rel, [
        'no run on this operating system', 'changed since its evidence',
        'untracked file', 'names no files', 'runs only the test files',
        'purlin:test --all runs them too.',
        "Nothing to run: every feature's spec, code and tests match its "
        'evidence.']))
    paragraph = next((flat(p) for p in re.split(r'\n\s*\n', text)
                      if 'With neither, the run selects' in flat(p)), None)
    if paragraph is None:
        return problems + ['%s has no paragraph on a run with no feature '
                           'named' % rel]
    return problems + ['%s paragraph on a run with no feature named does not '
                       'carry %r' % (rel, needle)
                       for needle in TEST_SELECTION if needle not in paragraph]
