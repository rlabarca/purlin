"""Tests for `scripts/review/ai_audit.py`: the prompt, the call, the answer.

The throwaway project is `dev/sign_project.py`'s, so a spec, a test file, a
runtime proof file and the evidence are written by the test and nothing reads
this repository's own specs. No test reaches the real model: every call lands
on the fake `claude` that `dev/fake_claude.py` writes, first on PATH, or on a
runner handed in its place.

What each group holds:

*reading*   which rules the audit reads, and what it reads for one: the rule,
            its proofs and the source of each test beside it
*prompt*    the criteria file verbatim, then the rule, and a request for what
            was observed rather than a grade
*call*      one call per rule, the prompt on stdin and never in the arguments,
            `parallel` calls at once
*answer*    settled with nothing is `strong`, settled with lines is `weak`,
            not settled is `undecided`; the model and the criteria are named;
            the lines under `notes:` are notes and change no verdict
*failure*   the four ways the model cannot be reached, each with its reason
*writing*   reading, asking and printing a rule write no file
*command*   the command line: its exits and what it prints
"""

import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import ai_audit as audit_module  # noqa: E402
import fake_claude  # noqa: E402
import marked_tests  # noqa: E402
from sign_project import (FIRST_GATE, REVIEW_GATE, SIGNING_GATE,  # noqa: E402
                          SPEC, TEST_FILE, Project)

AI_AUDIT_PY = os.path.join(ROOT, 'scripts', 'review', 'ai_audit.py')
CRITERIA = os.path.join(ROOT, 'references', 'review_criteria.md')

FINDING = 'PROOF-2 asserts the status but never the body the rule names.'
NO_SETTLED_LINE = 'claude answered without a settled line'


@contextlib.contextmanager
def passing_project(gate=REVIEW_GATE, spec=SPEC, statuses=None,
                    strength=90):
    """A project at `gate` whose tests ran with `statuses`, closed after."""
    made = Project(spec=spec, gate=gate)
    try:
        made.proofs(statuses)
        made.evidence(statuses, strength=strength)
        yield made
    finally:
        made.close()


@pytest.fixture
def proved():
    with passing_project(gate=FIRST_GATE) as made:
        yield made


@pytest.fixture
def at_strong():
    """The same project at `strong`, where an unmarked rule is read."""
    with passing_project() as made:
        yield made


@pytest.fixture
def claude(tmp_path, monkeypatch):
    """Install a fake `claude` first on PATH; returns `(install, directory)`."""
    directory = tmp_path / 'claude'

    def install(**settings):
        fake_claude.install(directory, **settings)
        return directory

    install()
    monkeypatch.setenv('PATH', str(directory) + os.pathsep
                       + os.environ.get('PATH', ''))
    return install, directory


def read(project, rule='RULE-1'):
    return audit_module.reading_for(project.root, None, 'login', rule)


def criteria_text():
    with open(CRITERIA, encoding='utf-8') as handle:
        return handle.read()


def ask(project, rule='RULE-2'):
    """What the audit found for `rule`, asked of whichever `claude` is first."""
    return audit_module.audit_one(project.root, read(project, rule),
                                  criteria_text())


def command(project, capsys, *args):
    """`(exit code, printed text)` for the command run on `project`."""
    code = audit_module.main(list(args) + ['--project-root', project.root])
    return code, capsys.readouterr().out


# ---------------------------------------------------------------------------
# Which rules are read
# ---------------------------------------------------------------------------

class TestWhichRulesAreRead:

    # purlin: ai_audit PROOF-1
    def test_a_passing_rule_with_no_entry_is_read_at_strong(self, at_strong):
        rule = at_strong.rule('RULE-2')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert not rule.get('audit'), rule
        assert audit_module.is_read(rule) is True

    # purlin: ai_audit PROOF-2
    def test_a_rule_whose_test_failed_is_not_read(self):
        failed = {'PROOF-1': 'pass', 'PROOF-2': 'fail'}
        with passing_project(statuses=failed) as made:
            rule = made.rule('RULE-2')
            assert rule['cells']['passed']['word'] == 'failed', rule
            assert audit_module.is_read(rule) is False

    # purlin: ai_audit PROOF-48
    def test_a_rule_whose_one_proof_is_manual_is_not_read(self):
        spec = SPEC.replace('verify 401 and the body "denied"',
                            'verify 401 and the body "denied" @manual')
        with passing_project(spec=spec) as made:
            rule = made.rule('RULE-2')
            assert rule['cells']['passed']['word'] == 'passed', rule
            assert [proof['manual'] for proof in rule['proofs']] == [True]
            assert audit_module.is_read(rule) is False

    # purlin: ai_audit PROOF-49
    def test_a_required_rule_is_read_only_where_its_feature_lists_it(
            self, at_strong):
        at_strong.spec('# Feature: portal\n\n'
                       '> Description: The portal a person signs in to.\n'
                       '> Scope: src/login.py\n'
                       '> Requires: login\n\n'
                       '## Rules\n\n'
                       '- RULE-1: The portal opens\n\n'
                       '## Proof\n\n'
                       '- PROOF-1 (RULE-1): Open the portal; it opens\n',
                       name='portal')
        features = {entry['name']: entry
                    for entry in at_strong.payload()['features']}
        required = [rule for rule in features['portal']['rules']
                    if rule['feature'] == 'login']
        own = features['login']['rules']
        assert sorted(rule['id'] for rule in required) == ['RULE-1',
                                                           'RULE-2']
        assert [audit_module.is_read(rule) for rule in required] == [
            False, False]
        assert [audit_module.is_read(rule) for rule in own] == [True, True]

    # purlin: ai_audit PROOF-3
    def test_a_passing_rule_is_read_at_the_gate_passed(self, proved):
        assert audit_module.is_read(proved.rule('RULE-2')) is True

    # purlin: ai_audit PROOF-50
    def test_a_passing_rule_is_read_at_the_gate_signed(self):
        with passing_project(gate=SIGNING_GATE) as made:
            assert audit_module.is_read(made.rule('RULE-2')) is True

    # purlin: ai_audit PROOF-4
    def test_a_rule_with_a_current_entry_is_not_read(self, at_strong):
        at_strong.audit('RULE-2')
        rule = at_strong.rule('RULE-2')
        assert rule['audit']['verdict'] == 'strong', rule
        assert audit_module.is_read(rule) is False

    # purlin: ai_audit PROOF-51
    def test_a_rule_with_a_current_entry_is_read_when_asked_again(
            self, at_strong):
        at_strong.audit('RULE-2')
        assert audit_module.is_read(at_strong.rule('RULE-2'),
                                    again=True) is True

    @staticmethod
    def _changed_after_its_entry(project, change):
        """RULE-2 after an entry is recorded and `change` runs, tests rerun."""
        project.audit('RULE-2')
        assert project.rule('RULE-2').get('audit')
        change(project)
        project.evidence()
        return project.rule('RULE-2')

    # purlin: ai_audit PROOF-52
    def test_a_rule_whose_text_changed_is_read_again(self, at_strong):
        rule = self._changed_after_its_entry(at_strong, lambda made: made.spec(
            SPEC.replace('return 401 and the body',
                         'return 401 with the body')))
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert not rule.get('audit'), rule
        assert audit_module.is_read(rule) is True

    # purlin: ai_audit PROOF-53
    def test_a_rule_whose_proof_changed_is_read_again(self, at_strong):
        rule = self._changed_after_its_entry(at_strong, lambda made: made.spec(
            SPEC.replace('verify 401 and the body "denied"',
                         'verify 401 and the body reads "denied"')))
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert not rule.get('audit'), rule
        assert audit_module.is_read(rule) is True

    # purlin: ai_audit PROOF-54
    def test_a_rule_whose_test_changed_is_read_again(self, at_strong):
        rule = self._changed_after_its_entry(
            at_strong, lambda made: made.edit_test(TEST_FILE.replace(
                'login("ada", "wrong")', 'login("ada", "bad")')))
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert not rule.get('audit'), rule
        assert audit_module.is_read(rule) is True


# ---------------------------------------------------------------------------
# What one rule is read with
# ---------------------------------------------------------------------------

class TestWhatOneRuleIsReadWith:

    # purlin: ai_audit PROOF-5
    def test_the_test_source_is_shown_beside_the_rule(self, proved):
        test = read(proved, 'RULE-1')['tests'][0]
        assert test['file'] == 'tests/test_login.py'
        assert test['name'] == 'test_valid_credentials_return_200'
        assert 'assert login("ada", "secret") == 200' in test['body']

    # purlin: ai_audit PROOF-6
    def test_a_manual_proof_has_no_test_where_a_test_would_be(self):
        made = Project(spec=SPEC.replace(
            'verify 200 and a token',
            'verify 200 and a token @manual'))
        try:
            test = read(made, 'RULE-1')['tests'][0]
            assert test['file'] is None
            assert test['body'] is None
            assert test['manual'] is True
        finally:
            made.close()

    # purlin: ai_audit PROOF-7
    def test_a_rule_that_is_not_there_is_not_read(self, proved):
        assert read(proved, 'RULE-99') is None

    # purlin: ai_audit PROOF-8
    def test_the_strength_is_read_beside_the_minimum(self, at_strong):
        reading = read(at_strong, 'RULE-2')
        assert (reading['test_strength'], reading['min_strength']) == (90, 70)

    # purlin: ai_audit PROOF-63
    def test_no_measured_strength_prints_n_a(self, capsys):
        with passing_project(strength=None) as made:
            code, printed = command(made, capsys, '--feature', 'login',
                                    '--rule', 'RULE-2')
        assert code == 0
        assert 'Test strength: n/a   minimum 70' in printed, printed


class TestTheJavaScriptReader:
    """Each case is a tricky test followed by a plain one in one file."""

    NEXT = ('it("the next test", () => {\n'
            '  expect(2).toBe(2);\n'
            '});\n', 'expect(2).toBe(2)')

    def _both(self, tmp_path, first, second=None):
        """The source found for the first and the second marked test."""
        second_text, _token = second or self.NEXT
        text = ('import { it, expect } from "vitest";\n\n'
                '// purlin: rx PROOF-1\n' + first + '\n'
                '// purlin: rx PROOF-2\n' + second_text)
        (tmp_path / 'tests').mkdir(exist_ok=True)
        (tmp_path / 'tests' / 'rx.test.ts').write_text(text, encoding='utf-8')
        return [marked_tests.source(str(tmp_path), 'rx', proof,
                                    'tests/rx.test.ts')
                for proof in ('PROOF-1', 'PROOF-2')]

    def _check(self, tmp_path, first, token, second=None):
        second = second or self.NEXT
        found, after = self._both(tmp_path, first, second)
        assert found is not None and after is not None, (found, after)
        assert token in found, found
        assert second[1] not in found, found
        assert second[1] in after, after
        assert token not in after, after

    # purlin: ai_audit PROOF-9
    def test_an_options_object_does_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("passes options", () => {\n'
                    '  const out = execSync("ls", { cwd: ".", encoding: '
                    '"utf8" });\n'
                    '  expect(out).toMatch(/./);\n'
                    '});\n', 'expect(out).toMatch')

    # purlin: ai_audit PROOF-67
    def test_an_apostrophe_in_a_title_does_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("cd\'s into a sibling", () => {\n'
                    '  expect(1).toBe(1);\n'
                    '});\n', 'expect(1).toBe(1)')

    # purlin: ai_audit PROOF-10
    def test_a_division_across_a_line_does_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("division across a line", () => {\n'
                    '  const s = "a" +\n'
                    '    / 2;\n'
                    '  expect(s).toBe("a");\n'
                    '});\n', 'expect(s).toBe("a")')

    # purlin: ai_audit PROOF-68
    def test_a_pattern_holding_a_brace_a_slash_and_quotes(self, tmp_path):
        self._check(tmp_path,
                    'it("a class holding a slash", () => {\n'
                    '  const re = /[/)}"\']+/g;\n'
                    '  expect("a)}/b".replace(re, "")).toBe("ab");\n'
                    '});\n', 'expect("a)}/b".replace(re, ""))')

    # purlin: ai_audit PROOF-69
    def test_a_pattern_with_an_escaped_slash(self, tmp_path):
        self._check(tmp_path,
                    'it("an escaped slash", () => {\n'
                    '  const re = /\\/)}/;\n'
                    '  expect("x/)}".match(re)[0]).toBe("/)}");\n'
                    '});\n', 'expect("x/)}".match(re)[0])')

    # purlin: ai_audit PROOF-70
    def test_braces_in_comments_do_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("comments", () => {\n'
                    '  // a } and a ) in a line comment\n'
                    '  /* a } and a ) in a block one */\n'
                    '  expect(1 + 1).toBe(2);\n'
                    '});\n', 'expect(1 + 1).toBe(2)')

    # purlin: ai_audit PROOF-71
    def test_two_one_line_tests_that_divide(self, tmp_path):
        self._check(tmp_path,
                    'it("division", () => { const q = 4 / 2; '
                    'expect(q).toBe(2); });\n', 'expect(q).toBe(2)',
                    second=('it("division again", () => { '
                            'expect(8 / 4).toBe(2); });\n',
                            'expect(8 / 4).toBe(2)'))


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

class TestThePrompt:

    # purlin: ai_audit PROOF-11
    def test_the_prompt_is_the_criteria_then_the_rule(self, at_strong):
        prompt = audit_module.model_prompt(at_strong.root,
                                           read(at_strong, 'RULE-2'))
        assert prompt.startswith(criteria_text())
        after = prompt[len(criteria_text()):]
        assert 'login RULE-2' in after
        assert 'Invalid credentials return 401 and the body "denied"' in after
        assert ('POST /login with a bad password; verify 401 and the body '
                '"denied"') in after
        assert 'test_a_bad_password_is_denied' in after
        assert 'assert login("ada", "wrong") == 401' in after
        assert 'Test strength: 90 percent (minimum 70)' in after

    # purlin: ai_audit PROOF-12
    def test_the_prompt_asks_for_observations_and_bars_a_recommendation(
            self, at_strong):
        prompt = audit_module.model_prompt(at_strong.root,
                                           read(at_strong, 'RULE-2'))
        assert 'settled: yes' in prompt
        assert 'one line per observation' in prompt
        assert 'Do not recommend a change' in prompt
        assert 'do not grade the rule' in prompt
        assert 'do not score it' in prompt

    # purlin: ai_audit PROOF-39
    def test_the_prompt_asks_for_notes_on_a_long_or_double_proof(
            self, at_strong):
        prompt = audit_module.model_prompt(at_strong.root,
                                           read(at_strong, 'RULE-2'))
        after = prompt[len(criteria_text()):]
        assert '\n    notes:\n' in after
        assert ('a note, under notes:, for a proof longer than 60 words or '
                'one holding more than one case') in after


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

class TestTheCall:

    # purlin: ai_audit PROOF-13
    def test_the_prompt_goes_on_stdin_and_never_in_the_arguments(
            self, at_strong, claude):
        _install, directory = claude
        reading = read(at_strong, 'RULE-2')
        found = audit_module.audit_one(at_strong.root, reading,
                                       criteria_text())
        calls = fake_claude.calls(directory)
        assert found.get('verdict') == 'strong', found
        assert len(calls) == 1, calls
        assert calls[0]['argv'] == ['-p', '--output-format', 'json']
        # The fake reads its standard input to the end before it answers.
        prompt = audit_module.model_prompt(at_strong.root, reading,
                                           criteria_text())
        assert calls[0]['prompt'] == prompt
        assert not any('Invalid credentials' in part
                       for part in calls[0]['argv'])

    # purlin: ai_audit PROOF-14
    def test_a_call_is_given_300_seconds_and_stdin_closes_after_the_prompt(
            self, at_strong):
        seen = []

        class Done(object):
            returncode = 0
            stdout = json.dumps({'result': 'settled: yes'})

        def runner(command, **kwargs):
            seen.append((command, kwargs))
            return Done()

        audit_module.audit_one(at_strong.root, read(at_strong, 'RULE-2'),
                               'criteria', command='/bin/claude',
                               runner=runner)
        command, kwargs = seen[0]
        assert command == ['/bin/claude', '-p', '--output-format', 'json']
        assert kwargs['timeout'] == 300
        # `input=` writes the prompt and closes stdin behind it.
        assert kwargs['input'].startswith('criteria')
        assert 'stdin' not in kwargs

    # purlin: ai_audit PROOF-15
    def test_one_call_per_rule_and_four_at_once(self, at_strong, claude):
        install, directory = claude
        install(sleep=0.4)
        reading = read(at_strong, 'RULE-2')
        results = audit_module.audit_all(at_strong.root, [reading] * 6, 4)
        calls = fake_claude.calls(directory)
        assert len(calls) == 6, calls
        assert [found['verdict'] for found in results] == ['strong'] * 6
        assert fake_claude.most_at_once(calls) == 4, calls

    # purlin: ai_audit PROOF-55
    def test_six_rules_six_calls_each_answer_beside_its_rule(self, at_strong,
                                                             claude):
        base = read(at_strong, 'RULE-2')
        readings = [dict(base, rule='RULE-%d' % n,
                         rule_text='Rule number %d holds' % n)
                    for n in range(1, 7)]
        asked = []

        class Done(object):
            returncode = 0

        def runner(command, **kwargs):
            rule = re.search(r'^login (RULE-\d)$', kwargs['input'],
                             re.M).group(1)
            asked.append(rule)
            # The later the rule, the sooner it answers.
            time.sleep(0.05 * (7 - int(rule[5:])))
            done = Done()
            done.stdout = json.dumps({'result': 'settled: yes\n- saw %s'
                                      % rule})
            return done

        results = audit_module.audit_all(at_strong.root, readings, 4,
                                         runner=runner)
        assert sorted(asked) == ['RULE-%d' % n for n in range(1, 7)], asked
        assert [found['findings'] for found in results] == [
            ['saw RULE-%d' % n] for n in range(1, 7)], results

    # purlin: ai_audit PROOF-16
    def test_the_number_at_once_is_what_it_is_given(self, at_strong, claude):
        install, directory = claude
        install(sleep=0.4)
        reading = read(at_strong, 'RULE-2')
        audit_module.audit_all(at_strong.root, [reading] * 4, 2)
        calls = fake_claude.calls(directory)
        assert len(calls) == 4, calls
        assert fake_claude.most_at_once(calls) == 2, calls

    # purlin: ai_audit PROOF-56
    def test_fewer_rules_than_the_number_all_run_together(self, at_strong,
                                                          claude):
        install, directory = claude
        install(sleep=0.4)
        reading = read(at_strong, 'RULE-2')
        audit_module.audit_all(at_strong.root, [reading] * 2, 4)
        calls = fake_claude.calls(directory)
        assert len(calls) == 2, calls
        assert fake_claude.most_at_once(calls) == 2, calls


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------

class TestTheAnswer:

    # purlin: ai_audit PROOF-17
    def test_settled_with_nothing_found_is_strong(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes'])
        found = ask(at_strong)
        assert (found['verdict'], found['findings']) == ('strong', [])

    # purlin: ai_audit PROOF-18
    def test_settled_with_a_line_is_weak_and_the_line_is_the_finding(
            self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes\n- %s\n' % FINDING])
        found = ask(at_strong)
        assert (found['verdict'], found['findings']) == ('weak', [FINDING])

    # purlin: ai_audit PROOF-19
    def test_not_settled_is_undecided_with_its_reason(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: no\n- The body of PROOF-2 is not shown.'])
        found = ask(at_strong)
        assert (found['verdict'], found['findings']) == (
            'undecided', ['The body of PROOF-2 is not shown.'])

    # purlin: ai_audit PROOF-22
    def test_a_finding_with_no_settled_line_is_no_answer(self, at_strong,
                                                         claude):
        install, _directory = claude
        install(answers=['- %s' % FINDING])
        assert ask(at_strong) == {'why': NO_SETTLED_LINE}

    # purlin: ai_audit PROOF-57
    def test_an_empty_answer_is_no_answer(self, at_strong, claude):
        install, _directory = claude
        install(answers=[''])
        assert ask(at_strong) == {'why': NO_SETTLED_LINE}

    # purlin: ai_audit PROOF-20
    def test_the_answer_names_its_model_and_the_criteria_it_was_sent(
            self, at_strong, claude):
        install, _directory = claude
        install(model='claude-opus-4-1-20250805')
        found = ask(at_strong)
        assert found['model'] == 'claude-opus-4-1-20250805'
        assert found['criteria'] == hashlib.sha256(
            criteria_text().encode('utf-8')).hexdigest()

    # purlin: ai_audit PROOF-58
    def test_an_answer_naming_no_model_names_unknown(self, at_strong, claude):
        install, _directory = claude
        install(model=None)
        assert ask(at_strong)['model'] == 'unknown'

    @staticmethod
    def _model_named(project, install, **fields):
        """The model the audit names when `claude`'s JSON carries `fields`."""
        install(raw=json.dumps(dict({'result': 'settled: yes'}, **fields)))
        return ask(project)['model']

    # purlin: ai_audit PROOF-21
    def test_the_model_that_wrote_most_is_named_when_listed_second(
            self, at_strong, claude):
        install, _directory = claude
        assert self._model_named(at_strong, install, modelUsage={
            'claude-haiku-3-5': {'outputTokens': 12},
            'claude-opus-4-1': {'outputTokens': 900}}) == 'claude-opus-4-1'

    # purlin: ai_audit PROOF-59
    def test_the_model_that_wrote_most_is_named_when_listed_first(
            self, at_strong, claude):
        install, _directory = claude
        assert self._model_named(at_strong, install, modelUsage={
            'claude-opus-4-1': {'outputTokens': 900},
            'claude-haiku-3-5': {'outputTokens': 12}}) == 'claude-opus-4-1'

    # purlin: ai_audit PROOF-60
    def test_the_model_named_follows_the_counts_not_the_name(self, at_strong,
                                                             claude):
        install, _directory = claude
        assert self._model_named(at_strong, install, modelUsage={
            'claude-opus-4-1': {'outputTokens': 12},
            'claude-haiku-3-5': {'outputTokens': 900}}) == 'claude-haiku-3-5'

    # purlin: ai_audit PROOF-61
    def test_a_top_level_model_is_named(self, at_strong, claude):
        install, _directory = claude
        assert self._model_named(at_strong, install,
                                 model='claude-x-1') == 'claude-x-1'

    # purlin: ai_audit PROOF-37
    def test_a_note_is_not_a_finding(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes\nnotes:\n- PROOF-2 holds two cases.'])
        found = ask(at_strong)
        assert (found['verdict'], found['findings'], found['notes']) == (
            'strong', [], ['PROOF-2 holds two cases.']), found

    # purlin: ai_audit PROOF-38
    def test_a_finding_and_a_note_are_kept_apart(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes\n- %s\nnotes:\n- PROOF-2 holds two '
                         'cases.' % FINDING])
        found = ask(at_strong)
        assert (found['verdict'], found['findings'], found['notes']) == (
            'weak', [FINDING], ['PROOF-2 holds two cases.']), found


# ---------------------------------------------------------------------------
# When the model cannot be reached
# ---------------------------------------------------------------------------

class TestWhenTheModelCannotBeReached:

    # purlin: ai_audit PROOF-23
    def test_no_claude_on_the_path_calls_nothing(self, at_strong, claude,
                                                 monkeypatch, tmp_path):
        _install, directory = claude
        empty = tmp_path / 'empty'
        empty.mkdir()
        monkeypatch.setenv('PATH', str(empty))
        results = audit_module.audit_all(at_strong.root,
                                         [read(at_strong, 'RULE-2')] * 2, 4)
        assert results == [{'why': 'claude is not on PATH'}] * 2
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-24
    def test_a_non_zero_exit_is_named(self, at_strong, claude):
        install, _directory = claude
        install(exit_code=1)
        assert ask(at_strong) == {'why': 'claude exited with an error'}

    # purlin: ai_audit PROOF-25
    def test_a_call_past_its_limit_is_named(self, at_strong, claude,
                                            monkeypatch):
        install, _directory = claude
        install(sleep=3)
        monkeypatch.setattr(audit_module, 'MODEL_TIMEOUT', 1)
        assert ask(at_strong) == {'why': 'claude timed out after 1 s'}

    # purlin: ai_audit PROOF-26
    def test_an_answer_with_no_settled_line_twice_is_no_answer(
            self, at_strong, claude):
        install, directory = claude
        install(answers=['It looks fine to me.'])
        assert ask(at_strong) == {'why': NO_SETTLED_LINE}
        assert len(fake_claude.calls(directory)) == 2

    # purlin: ai_audit PROOF-62
    def test_a_second_answer_that_settles_is_the_answer(self, at_strong,
                                                        claude):
        install, directory = claude
        install(answers=['It looks fine to me.', 'settled: yes'])
        found = ask(at_strong)
        assert found.get('verdict') == 'strong', found
        assert len(fake_claude.calls(directory)) == 2


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

class TestWriting:

    @staticmethod
    def _files(root):
        """`{path: sha256}` for every file under `.purlin/`, runtime included."""
        found = {}
        for current, _dirs, names in os.walk(os.path.join(root, '.purlin')):
            for name in names:
                path = os.path.join(current, name)
                with open(path, 'rb') as handle:
                    found[path] = hashlib.sha256(handle.read()).hexdigest()
        return found

    # purlin: ai_audit PROOF-27
    def test_reading_a_rule_writes_no_file(self, at_strong):
        before = self._files(at_strong.root)
        assert any('runtime' in path for path in before), before
        assert read(at_strong, 'RULE-2') is not None
        assert self._files(at_strong.root) == before

    # purlin: ai_audit PROOF-72
    def test_asking_the_model_writes_no_file(self, at_strong, claude):
        _install, directory = claude
        reading = read(at_strong, 'RULE-2')
        before = self._files(at_strong.root)
        found = audit_module.audit_all(at_strong.root, [reading], 4)
        assert found[0]['verdict'] == 'strong', found
        assert len(fake_claude.calls(directory)) == 1
        assert self._files(at_strong.root) == before

    # purlin: ai_audit PROOF-73
    def test_printing_the_feature_writes_no_file(self, at_strong, capsys):
        before = self._files(at_strong.root)
        code, printed = command(at_strong, capsys, '--feature', 'login')
        assert code == 0
        assert 'login RULE-1' in printed and 'login RULE-2' in printed
        assert self._files(at_strong.root) == before


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

def _emoji(text):
    """The characters of `text` that are emoji or pictographs."""
    return [char for char in text
            if 0x1F000 <= ord(char) <= 0x1FAFF
            or 0x2600 <= ord(char) <= 0x27BF
            or ord(char) in (0x2705, 0x274C, 0xFE0F)]


class TestTheCommandLine:

    # purlin: ai_audit PROOF-30
    def test_help_exits_zero_and_prints_the_usage(self, capsys):
        assert audit_module.main(['--help']) == 0
        assert ('ai_audit.py --feature <f> [--rule RULE-N] '
                '[--project-root DIR]') in capsys.readouterr().out

    # purlin: ai_audit PROOF-74
    def test_an_unknown_option_exits_two(self, capsys):
        assert audit_module.main(['--nope']) == 2
        assert 'ai_audit.py: unexpected argument --nope' in \
            capsys.readouterr().err

    # purlin: ai_audit PROOF-75
    def test_no_feature_exits_two(self, capsys):
        assert audit_module.main([]) == 2
        assert 'ai_audit.py: --feature is required.' in \
            capsys.readouterr().err

    # purlin: ai_audit PROOF-31
    def test_an_unknown_feature_exits_one(self, proved, capsys):
        code, printed = command(proved, capsys, '--feature', 'nothing')
        assert code == 1
        assert 'audit: no rule of nothing is in this project.' in printed

    # purlin: ai_audit PROOF-76
    def test_an_unknown_rule_exits_one(self, proved, capsys):
        code, printed = command(proved, capsys, '--feature', 'login',
                                '--rule', 'RULE-99')
        assert code == 1
        assert 'RULE-99' not in printed, printed
        assert 'What the audit found' not in printed, printed

    # purlin: ai_audit PROOF-33
    def test_the_script_runs_as_a_command_and_calls_no_model(self, proved,
                                                             claude):
        _install, directory = claude
        result = subprocess.run(
            [sys.executable, AI_AUDIT_PY, '--feature', 'login', '--rule',
             'RULE-1', '--project-root', proved.root],
            capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'login RULE-1' in result.stdout
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-29
    def test_the_printed_rule_names_what_the_audit_found(self, at_strong,
                                                          capsys):
        at_strong.audit('RULE-2', findings=[FINDING])
        code, printed = command(at_strong, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        for line in ('login RULE-2',
                     'Invalid credentials return 401 and the body "denied"',
                     'PROOF-2: POST /login with a bad password',
                     'assert login("ada", "wrong") == 401',
                     'Test strength: 90 percent   minimum 70',
                     'What the audit found',
                     'Weak, by unknown at 2026-09-13T12:05:00Z.',
                     FINDING):
            assert line in printed, (line, printed)
        assert _emoji(printed) == [], printed

    # purlin: ai_audit PROOF-77
    def test_a_rule_no_audit_has_read_says_so(self, at_strong, capsys):
        code, printed = command(at_strong, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        found = printed.split('What the audit found', 1)
        assert len(found) == 2, printed
        assert ("Nothing yet: no audit has read this rule's text, proof and "
                "test.") in found[1], printed

    # purlin: ai_audit PROOF-32
    def test_one_rule_named_prints_that_rule_alone(self, proved, capsys):
        code, printed = command(proved, capsys, '--feature', 'login',
                                '--rule', 'RULE-1')
        assert code == 0
        assert 'login RULE-1' in printed and 'login RULE-2' not in printed

    # purlin: ai_audit PROOF-78
    def test_a_feature_alone_prints_every_rule(self, proved, capsys):
        code, printed = command(proved, capsys, '--feature', 'login')
        assert code == 0
        assert 'login RULE-1' in printed and 'login RULE-2' in printed
