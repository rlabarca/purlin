"""Text checks for the test skill, `skills/test/SKILL.md`.

Every rule of `specs/skills/skill_test.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems,
                          next_step_refusals, read, refusals, replace, resub,
                          same_line, section, sentence_with,
                          skill_ceiling_problems, skill_path,
                          undirected_outcome_problems)


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

    # purlin: skill_test PROOF-2
    def test_a_broken_exit_code_line_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, run_line_problems, [
            (rel, replace(', `2` the invocation', ',\n`2` the invocation'),
             "%s has no single line carrying all of 'Exit codes:'" % rel),
            (rel, replace('`1` a test failed, evidence is missing or a marker '
                          'names nothing a spec has', '`1` something failed'),
             "%s has no single line carrying all of 'Exit codes:'" % rel),
            (rel, replace('purlin_run.py" --test', 'purlin_run.py"'),
             '%s has no single line carrying all of '
             '\'"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"\', '
             "'--test'" % rel),
        ]) == []

    # purlin: skill_test PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('test')
                + undirected_outcome_problems('test')) == []

    # purlin: skill_test PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'test', '| A rule reads `partial`',
            '| A test failed | `→ Run: purlin:build <feature>` (fix the code '
            'or the test) |') == []

    # purlin: skill_test PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('test') == []

    # purlin: skill_test PROOF-5
    def test_it_names_the_evidence_the_commit_and_the_gate_line(self):
        assert evidence_line_problems() == []

    # purlin: skill_test PROOF-5
    def test_a_missing_gate_line_form_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, evidence_line_problems, [
            (rel, replace(', or\n`gate <gate> not met: <n> of <rules> rules '
                          'meet it`'),
             "%s does not carry 'gate <gate> not met" % rel),
            (rel, replace('counts the rules that meet the gate',
                          'is printed'),
             "'counts the rules that meet the gate'"),
            (rel, replace('rules` is the check', 'rules` is printed'),
             "'`gate passed met: <n> of <rules> rules` is the check'"),
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


def run_line_problems():
    rel = skill_path('test')
    return (same_line(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--test'])
        + same_line(rel, [
            'Exit codes:', '`0`', '`1`', '`2`', 'whatever the gate line says',
            '`0` no test failed and no marker is wrong, whatever the gate '
            'line says',
            '`1` a test failed, evidence is missing or a marker names nothing '
            'a spec has',
            '`2` the invocation was wrong'])
        + carries(rel, ['cannot make an audit or a signature appear']))


def evidence_line_problems():
    rel = skill_path('test')
    return (carries(rel, [
        '.purlin/evidence/local/<feature>.json', '.purlin/tests.md',
        '--commit', 'purlin: evidence at <sha7>', 'Evidence committed.',
        'Evidence unchanged.', 'Tests: <p> of <rules> rules pass.',
        'gate <gate> met: <n> of <rules> rules',
        'gate <gate> not met: <n> of <rules> rules meet it',
        'gate passed met: <n> of <rules> rules', 'It never pushes.'])
        + sentence_with(rel, [
            '`gate <gate> met: <n> of <rules> rules`',
            '`gate <gate> not met: <n> of <rules> rules meet it`',
            'counts the rules that meet the gate'])
        + sentence_with(rel, [
            'At `passed`',
            '`gate passed met: <n> of <rules> rules` is the check']))


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
