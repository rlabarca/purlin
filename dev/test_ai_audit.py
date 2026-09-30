"""Tests for `scripts/review/ai_audit.py`: the prompt, the call, the answer.

The throwaway project is `dev/sign_project.py`'s, so a spec, a test file and
the evidence are written by the test and nothing reads this repository's own
specs. No test reaches the real model: every call lands
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
from sign_project import (FIRST_GATE, SIGNING_GATE,  # noqa: E402
                          SPEC, TEST_FILE, Project, git)

AI_AUDIT_PY = os.path.join(ROOT, 'scripts', 'review', 'ai_audit.py')
CRITERIA = os.path.join(ROOT, 'references', 'review_criteria.md')

FINDING = 'PROOF-2 asserts the status but never the body the rule names.'
NO_SETTLED_LINE = 'claude answered without a settled line'
TRAILING_COMMA = '{\n  "gate": "passed",\n}\n'
READ_BY = '  Read by unknown at 2026-09-13T12:05:00Z.'


@contextlib.contextmanager
def passing_project(gate=SIGNING_GATE, spec=SPEC, statuses=None,
                    strength=90):
    """A project at `gate` whose tests ran with `statuses`, closed after."""
    made = Project(spec=spec, gate=gate)
    try:
        made.evidence(statuses, strength=strength)
        yield made
    finally:
        made.close()


@pytest.fixture
def proved():
    with passing_project(gate=FIRST_GATE) as made:
        yield made


@pytest.fixture
def at_signed():
    """The same project at `signed`, where an unmarked rule is read."""
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


def as_anchor(project):
    """Move `login` under `specs/_anchors/`, then take its evidence again,
    measuring a test strength of 90."""
    os.makedirs(os.path.join(project.root, 'specs', '_anchors'))
    git(project.root, 'mv', 'specs/auth/login.md', 'specs/_anchors/login.md')
    git(project.root, 'commit', '-q', '-m', 'spec(login): an anchor')
    project.evidence()


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
    def test_a_passing_rule_with_no_entry_is_read(self, at_signed):
        rule = at_signed.rule('RULE-2')
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
    def test_an_anchors_rules_are_read_once_each_as_the_anchors(
            self, at_signed):
        as_anchor(at_signed)
        at_signed.spec('# Feature: portal\n\n'
                       '> Description: The portal a person signs in to.\n'
                       '> Scope: src/login.py\n\n'
                       '## Rules\n\n'
                       '- RULE-1: The portal opens\n\n'
                       '## Proof\n\n'
                       '- PROOF-1 (RULE-1): Open the portal; it opens\n',
                       name='portal')
        read_as = [(entry['name'], rule['feature'], rule['id'])
                   for entry in at_signed.payload()['features']
                   for rule in entry.get('rules') or ()
                   if audit_module.is_read(rule)]
        assert read_as == [('login', 'login', 'RULE-1'),
                           ('login', 'login', 'RULE-2')], read_as

    # purlin: ai_audit PROOF-3
    def test_a_passing_rule_is_read_at_the_gate_passed(self, proved):
        assert audit_module.is_read(proved.rule('RULE-2')) is True

    # purlin: ai_audit PROOF-50
    def test_a_passing_rule_is_read_at_the_gate_signed(self):
        with passing_project(gate=SIGNING_GATE) as made:
            assert audit_module.is_read(made.rule('RULE-2')) is True

    # purlin: ai_audit PROOF-4
    def test_a_rule_with_a_current_entry_is_not_read(self, at_signed):
        at_signed.audit('RULE-2')
        rule = at_signed.rule('RULE-2')
        assert rule['audit']['verdict'] == 'strong', rule
        assert audit_module.is_read(rule) is False

    # purlin: ai_audit PROOF-51
    def test_a_rule_with_a_current_entry_is_read_when_asked_again(
            self, at_signed):
        at_signed.audit('RULE-2')
        assert audit_module.is_read(at_signed.rule('RULE-2'),
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
    def test_a_rule_whose_text_changed_is_read_again(self, at_signed):
        rule = self._changed_after_its_entry(at_signed, lambda made: made.spec(
            SPEC.replace('return 401 and the body',
                         'return 401 with the body')))
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert not rule.get('audit'), rule
        assert audit_module.is_read(rule) is True

    # purlin: ai_audit PROOF-53
    def test_a_rule_whose_proof_changed_is_read_again(self, at_signed):
        rule = self._changed_after_its_entry(at_signed, lambda made: made.spec(
            SPEC.replace('verify 401 and the body "denied"',
                         'verify 401 and the body reads "denied"')))
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert not rule.get('audit'), rule
        assert audit_module.is_read(rule) is True

    # purlin: ai_audit PROOF-54
    def test_a_rule_whose_test_changed_is_read_again(self, at_signed):
        rule = self._changed_after_its_entry(
            at_signed, lambda made: made.edit_test(TEST_FILE.replace(
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
    def test_the_strength_is_read(self, at_signed):
        reading = read(at_signed, 'RULE-2')
        assert reading['test_strength'] == 90, reading

    # purlin: ai_audit PROOF-63
    def test_no_measured_strength_prints_nothing_of_strength(self, capsys):
        with passing_project(strength=None) as made:
            code, printed = command(made, capsys, '--feature', 'login',
                                    '--rule', 'RULE-2')
        assert code == 0
        assert 'login RULE-2' in printed, printed
        assert 'strength' not in printed.lower(), printed


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
    def test_the_prompt_is_the_criteria_then_the_rule(self, at_signed):
        prompt = audit_module.model_prompt(at_signed.root,
                                           read(at_signed, 'RULE-2'))
        assert prompt.startswith(criteria_text())
        after = prompt[len(criteria_text()):]
        assert 'login RULE-2' in after
        assert 'Invalid credentials return 401 and the body "denied"' in after
        assert ('POST /login with a bad password; verify 401 and the body '
                '"denied"') in after
        assert 'test_a_bad_password_is_denied' in after
        assert 'assert login("ada", "wrong") == 401' in after
        assert 'Test strength 90%.' in after.splitlines(), after[-400:]

    # purlin: ai_audit PROOF-93
    def test_the_prompt_names_the_strength_and_no_minimum(self):
        with passing_project(strength=84) as made:
            prompt = audit_module.model_prompt(made.root,
                                               read(made, 'RULE-2'))
        after = prompt[len(criteria_text()):]
        assert 'Test strength 84%.' in after.splitlines(), after[-400:]
        assert 'minimum' not in after, after[-400:]

    # purlin: ai_audit PROOF-79
    def test_the_prompt_says_in_words_that_no_strength_was_measured(self):
        with passing_project(strength=None) as made:
            prompt = audit_module.model_prompt(made.root,
                                               read(made, 'RULE-2'))
        told = [line for line in prompt.splitlines()
                if line.startswith('Test strength:')]
        assert told == ['Test strength: not measured'], told

    # purlin: ai_audit PROOF-91
    def test_an_anchors_prompt_ends_on_the_anchor_line(self, at_signed):
        as_anchor(at_signed)
        prompt = audit_module.model_prompt(at_signed.root,
                                           read(at_signed, 'RULE-2'))
        assert prompt.splitlines()[-1] == (
            'Anchor: its rules cover the whole project, so its tests must '
            'check the whole project. No test strength is measured for an '
            'anchor.'), prompt[-400:]

    # purlin: ai_audit PROOF-92
    def test_an_anchors_prompt_names_no_strength(self, at_signed):
        as_anchor(at_signed)
        prompt = audit_module.model_prompt(at_signed.root,
                                           read(at_signed, 'RULE-2'))
        assert 'login RULE-2' in prompt
        assert not [line for line in prompt.splitlines()
                    if line.startswith('Test strength')], prompt[-400:]

    # purlin: ai_audit PROOF-12
    def test_the_prompt_asks_for_observations_and_bars_a_recommendation(
            self, at_signed):
        prompt = audit_module.model_prompt(at_signed.root,
                                           read(at_signed, 'RULE-2'))
        assert 'settled: yes' in prompt
        assert 'one line per observation' in prompt
        assert 'Do not recommend a change' in prompt
        assert 'do not grade the rule' in prompt
        assert 'do not score it' in prompt

    # purlin: ai_audit PROOF-39
    def test_the_prompt_asks_for_notes_on_a_long_or_double_proof(
            self, at_signed):
        prompt = audit_module.model_prompt(at_signed.root,
                                           read(at_signed, 'RULE-2'))
        after = prompt[len(criteria_text()):]
        assert '\n    notes:\n' in after
        assert ('a note, under notes:, for a proof longer than 60 words or '
                'one holding more than one case') in after


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

class TestTheCall:

    # purlin: ai_audit PROOF-13
    # purlin: ai_audit PROOF-82
    def test_the_prompt_goes_on_stdin_and_never_in_the_arguments(
            self, at_signed, claude, monkeypatch):
        _install, directory = claude
        # The fake is Python: it reads its input as UTF-8, as `claude` does,
        # and not in a Windows console's default character set.
        monkeypatch.setenv('PYTHONUTF8', '1')
        if os.name == 'nt':
            # Windows finds the stand-in by its ending, `claude.cmd`.
            found = audit_module.claude_path()
            assert os.path.normcase(found) == os.path.normcase(
                os.path.join(str(directory), 'claude.cmd')), found
        reading = read(at_signed, 'RULE-2')
        found = audit_module.audit_one(at_signed.root, reading,
                                       criteria_text())
        calls = fake_claude.calls(directory)
        assert found.get('verdict') == 'strong', found
        assert len(calls) == 1, calls
        assert calls[0]['argv'] == ['-p', '--output-format', 'json']
        # The fake reads its standard input to the end before it answers.
        prompt = audit_module.model_prompt(at_signed.root, reading,
                                           criteria_text())
        assert calls[0]['prompt'] == prompt
        assert not any('Invalid credentials' in part
                       for part in calls[0]['argv'])

    # purlin: ai_audit PROOF-14
    def test_a_call_is_given_300_seconds_and_stdin_closes_after_the_prompt(
            self, at_signed):
        seen = []

        class Done(object):
            returncode = 0
            stdout = json.dumps({'result': 'settled: yes'})

        def runner(command, **kwargs):
            seen.append((command, kwargs))
            return Done()

        audit_module.audit_one(at_signed.root, read(at_signed, 'RULE-2'),
                               'criteria', command='/bin/claude',
                               runner=runner)
        command, kwargs = seen[0]
        assert command == ['/bin/claude', '-p', '--output-format', 'json']
        assert kwargs['timeout'] == 300
        # `input=` writes the prompt and closes stdin behind it.
        assert kwargs['input'].startswith('criteria')
        assert 'stdin' not in kwargs

    # purlin: ai_audit PROOF-15
    def test_one_call_per_rule_and_four_at_once(self, at_signed, claude):
        install, directory = claude
        install(sleep=0.4)
        reading = read(at_signed, 'RULE-2')
        results = audit_module.audit_all(at_signed.root, [reading] * 6, 4)
        calls = fake_claude.calls(directory)
        assert len(calls) == 6, calls
        assert [found['verdict'] for found in results] == ['strong'] * 6
        assert fake_claude.most_at_once(calls) == 4, calls

    # purlin: ai_audit PROOF-55
    def test_six_rules_six_calls_each_answer_beside_its_rule(self, at_signed,
                                                             claude):
        base = read(at_signed, 'RULE-2')
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

        results = audit_module.audit_all(at_signed.root, readings, 4,
                                         runner=runner)
        assert sorted(asked) == ['RULE-%d' % n for n in range(1, 7)], asked
        assert [found['findings'] for found in results] == [
            ['saw RULE-%d' % n] for n in range(1, 7)], results

    # purlin: ai_audit PROOF-16
    def test_the_number_at_once_is_what_it_is_given(self, at_signed, claude):
        install, directory = claude
        install(sleep=0.4)
        reading = read(at_signed, 'RULE-2')
        audit_module.audit_all(at_signed.root, [reading] * 4, 2)
        calls = fake_claude.calls(directory)
        assert len(calls) == 4, calls
        assert fake_claude.most_at_once(calls) == 2, calls

    # purlin: ai_audit PROOF-56
    def test_fewer_rules_than_the_number_all_run_together(self, at_signed,
                                                          claude):
        install, directory = claude
        install(sleep=0.4)
        reading = read(at_signed, 'RULE-2')
        audit_module.audit_all(at_signed.root, [reading] * 2, 4)
        calls = fake_claude.calls(directory)
        assert len(calls) == 2, calls
        assert fake_claude.most_at_once(calls) == 2, calls


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------

class TestTheAnswer:

    # purlin: ai_audit PROOF-17
    def test_settled_with_nothing_found_is_strong(self, at_signed, claude):
        install, _directory = claude
        install(answers=['settled: yes'])
        found = ask(at_signed)
        assert (found['verdict'], found['findings']) == ('strong', [])

    # purlin: ai_audit PROOF-18
    def test_settled_with_a_line_is_weak_and_the_line_is_the_finding(
            self, at_signed, claude):
        install, _directory = claude
        install(answers=['settled: yes\n- %s\n' % FINDING])
        found = ask(at_signed)
        assert (found['verdict'], found['findings']) == ('weak', [FINDING])

    # purlin: ai_audit PROOF-19
    def test_not_settled_is_undecided_with_its_reason(self, at_signed, claude):
        install, _directory = claude
        install(answers=['settled: no\n- The body of PROOF-2 is not shown.'])
        found = ask(at_signed)
        assert (found['verdict'], found['findings']) == (
            'undecided', ['The body of PROOF-2 is not shown.'])

    # purlin: ai_audit PROOF-22
    def test_a_finding_with_no_settled_line_is_no_answer(self, at_signed,
                                                         claude):
        install, _directory = claude
        install(answers=['- %s' % FINDING])
        assert ask(at_signed) == {'why': NO_SETTLED_LINE}

    # purlin: ai_audit PROOF-57
    def test_an_empty_answer_is_no_answer(self, at_signed, claude):
        install, _directory = claude
        install(answers=[''])
        assert ask(at_signed) == {'why': NO_SETTLED_LINE}

    # purlin: ai_audit PROOF-20
    def test_the_answer_names_its_model_and_the_criteria_it_was_sent(
            self, at_signed, claude):
        install, _directory = claude
        install(model='claude-opus-4-1-20250805')
        found = ask(at_signed)
        assert found['model'] == 'claude-opus-4-1-20250805'
        assert found['criteria'] == hashlib.sha256(
            criteria_text().encode('utf-8')).hexdigest()

    # purlin: ai_audit PROOF-58
    def test_an_answer_naming_no_model_names_unknown(self, at_signed, claude):
        install, _directory = claude
        install(model=None)
        assert ask(at_signed)['model'] == 'unknown'

    @staticmethod
    def _model_named(project, install, **fields):
        """The model the audit names when `claude`'s JSON carries `fields`."""
        install(raw=json.dumps(dict({'result': 'settled: yes'}, **fields)))
        return ask(project)['model']

    # purlin: ai_audit PROOF-21
    def test_the_model_that_wrote_most_is_named_when_listed_second(
            self, at_signed, claude):
        install, _directory = claude
        assert self._model_named(at_signed, install, modelUsage={
            'claude-haiku-3-5': {'outputTokens': 12},
            'claude-opus-4-1': {'outputTokens': 900}}) == 'claude-opus-4-1'

    # purlin: ai_audit PROOF-59
    def test_the_model_that_wrote_most_is_named_when_listed_first(
            self, at_signed, claude):
        install, _directory = claude
        assert self._model_named(at_signed, install, modelUsage={
            'claude-opus-4-1': {'outputTokens': 900},
            'claude-haiku-3-5': {'outputTokens': 12}}) == 'claude-opus-4-1'

    # purlin: ai_audit PROOF-60
    def test_the_model_named_follows_the_counts_not_the_name(self, at_signed,
                                                             claude):
        install, _directory = claude
        assert self._model_named(at_signed, install, modelUsage={
            'claude-opus-4-1': {'outputTokens': 12},
            'claude-haiku-3-5': {'outputTokens': 900}}) == 'claude-haiku-3-5'

    # purlin: ai_audit PROOF-61
    def test_a_top_level_model_is_named(self, at_signed, claude):
        install, _directory = claude
        assert self._model_named(at_signed, install,
                                 model='claude-x-1') == 'claude-x-1'

    # purlin: ai_audit PROOF-37
    def test_a_note_is_not_a_finding(self, at_signed, claude):
        install, _directory = claude
        install(answers=['settled: yes\nnotes:\n- PROOF-2 holds two cases.'])
        found = ask(at_signed)
        assert (found['verdict'], found['findings'], found['notes']) == (
            'strong', [], ['PROOF-2 holds two cases.']), found

    # purlin: ai_audit PROOF-38
    def test_a_finding_and_a_note_are_kept_apart(self, at_signed, claude):
        install, _directory = claude
        install(answers=['settled: yes\n- %s\nnotes:\n- PROOF-2 holds two '
                         'cases.' % FINDING])
        found = ask(at_signed)
        assert (found['verdict'], found['findings'], found['notes']) == (
            'weak', [FINDING], ['PROOF-2 holds two cases.']), found


# ---------------------------------------------------------------------------
# When the model cannot be reached
# ---------------------------------------------------------------------------

class TestWhenTheModelCannotBeReached:

    # purlin: ai_audit PROOF-23
    def test_no_claude_on_the_path_calls_nothing(self, at_signed, claude,
                                                 monkeypatch, tmp_path):
        _install, directory = claude
        empty = tmp_path / 'empty'
        empty.mkdir()
        monkeypatch.setenv('PATH', str(empty))
        results = audit_module.audit_all(at_signed.root,
                                         [read(at_signed, 'RULE-2')] * 2, 4)
        assert results == [{'why': 'claude is not on PATH'}] * 2
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-24
    def test_a_non_zero_exit_is_named(self, at_signed, claude):
        install, _directory = claude
        install(exit_code=1)
        assert ask(at_signed) == {'why': 'claude exited with an error'}

    # purlin: ai_audit PROOF-25
    # purlin: ai_audit PROOF-83
    def test_a_call_past_its_limit_is_named(self, at_signed, claude,
                                            monkeypatch):
        install, _directory = claude
        install(sleep=3)
        monkeypatch.setattr(audit_module, 'MODEL_TIMEOUT', 1)
        assert ask(at_signed) == {'why': 'claude timed out after 1 s'}

    # purlin: ai_audit PROOF-26
    def test_an_answer_with_no_settled_line_twice_is_no_answer(
            self, at_signed, claude):
        install, directory = claude
        install(answers=['It looks fine to me.'])
        assert ask(at_signed) == {'why': NO_SETTLED_LINE}
        assert len(fake_claude.calls(directory)) == 2

    # purlin: ai_audit PROOF-62
    def test_a_second_answer_that_settles_is_the_answer(self, at_signed,
                                                        claude):
        install, directory = claude
        install(answers=['It looks fine to me.', 'settled: yes'])
        found = ask(at_signed)
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
    def test_reading_a_rule_writes_no_file(self, at_signed):
        # A run's log sits under `.purlin/runtime/`, so the walk reaches it.
        log = os.path.join(at_signed.root, '.purlin', 'runtime', 'run.log')
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, 'w', encoding='utf-8') as handle:
            handle.write('a run\n')
        before = self._files(at_signed.root)
        assert any('runtime' in path for path in before), before
        assert read(at_signed, 'RULE-2') is not None
        assert self._files(at_signed.root) == before

    # purlin: ai_audit PROOF-72
    def test_asking_the_model_writes_no_file(self, at_signed, claude):
        _install, directory = claude
        reading = read(at_signed, 'RULE-2')
        before = self._files(at_signed.root)
        found = audit_module.audit_all(at_signed.root, [reading], 4)
        assert found[0]['verdict'] == 'strong', found
        assert len(fake_claude.calls(directory)) == 1
        assert self._files(at_signed.root) == before

    # purlin: ai_audit PROOF-73
    def test_printing_the_feature_writes_no_file(self, at_signed, capsys):
        before = self._files(at_signed.root)
        code, printed = command(at_signed, capsys, '--feature', 'login')
        assert code == 0
        assert 'login RULE-1' in printed and 'login RULE-2' in printed
        assert self._files(at_signed.root) == before


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

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
        assert printed == ('login RULE-99 is not a rule any spec has. Run '
                           'purlin:status login to see its rules.\n'), printed

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
    def test_the_printed_rule_names_what_the_audit_found(self, at_signed,
                                                          capsys):
        at_signed.audit('RULE-2', findings=[FINDING])
        code, printed = command(at_signed, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        for line in ('login RULE-2',
                     'Invalid credentials return 401 and the body "denied"',
                     'PROOF-2: POST /login with a bad password',
                     'assert login("ada", "wrong") == 401',
                     'What the audit found'):
            assert line in printed, (line, printed)
        lines = printed.splitlines()
        assert 'Test strength 90%.' in lines, printed
        found = lines[lines.index('What the audit found') + 1:]
        assert found[:3] == ['  Weak.', '  %s' % FINDING, READ_BY], printed
        assert not [line for line in printed.splitlines()
                    if line.strip().startswith('Note:')], printed

    # purlin: ai_audit PROOF-80
    def test_each_note_follows_the_findings(self, at_signed, capsys):
        rel = at_signed.audit('RULE-2', findings=[FINDING])
        path = os.path.join(at_signed.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        data['audit']['rules']['RULE-2']['notes'] = ['PROOF-2 holds two cases.']
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        code, printed = command(at_signed, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        lines = printed.splitlines()
        at = lines.index('  %s' % FINDING)
        assert lines[at + 1:at + 3] == [
            READ_BY, '  Note: PROOF-2 holds two cases.'], printed

    # purlin: ai_audit PROOF-77
    def test_a_rule_no_audit_has_read_says_so(self, at_signed, capsys):
        code, printed = command(at_signed, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        found = printed.split('What the audit found', 1)
        assert len(found) == 2, printed
        assert found[1].splitlines()[1] == (
            "  No audit has read this rule's text, proof and test yet."), printed
        assert 'Read by' not in found[1], printed

    def _entry(self, project, verdict, findings):
        """An audit entry for `RULE-2` reading `verdict` with `findings`."""
        rel = project.audit('RULE-2', findings=findings)
        path = os.path.join(project.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        data['audit']['rules']['RULE-2']['verdict'] = verdict
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, sort_keys=True)

    def _found(self, project, capsys):
        """The lines printed under `What the audit found` for `RULE-2`."""
        code, printed = command(project, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0, printed
        lines = printed.splitlines()
        return lines[lines.index('What the audit found') + 1:]

    # purlin: ai_audit PROOF-84
    def test_a_strong_answer_with_nothing_found_says_so(self, at_signed,
                                                        capsys):
        at_signed.audit('RULE-2')
        assert self._found(at_signed, capsys)[:2] == [
            '  Strong. It found nothing.', READ_BY]

    # purlin: ai_audit PROOF-85
    def test_a_strong_answer_with_a_finding_prints_it(self, at_signed,
                                                      capsys):
        self._entry(at_signed, 'strong', ['PROOF-2 names no body.'])
        assert self._found(at_signed, capsys)[:3] == [
            '  Strong.', '  PROOF-2 names no body.', READ_BY]

    # purlin: ai_audit PROOF-86
    def test_an_undecided_answer_says_the_rule_reads_weak(self, at_signed,
                                                          capsys):
        at_signed.audit('RULE-2', findings=['The body of PROOF-2 is not shown.'],
                        settled=False)
        assert self._found(at_signed, capsys)[:3] == [
            '  Undecided. The AI audit could not decide, so the rule reads '
            'weak until its proof or test changes.',
            '  The body of PROOF-2 is not shown.', READ_BY]

    # purlin: ai_audit PROOF-87
    def test_a_rule_with_no_test_names_the_command(self, capsys):
        spec = SPEC.replace(
            '- RULE-2:', '- RULE-3: A session ends after an hour\n- RULE-2:'
        ) + '- PROOF-3 (RULE-3): A session an hour old is refused\n'
        with passing_project(spec=spec) as made:
            code, printed = command(made, capsys, '--feature', 'login',
                                    '--rule', 'RULE-3')
        assert code == 0, printed
        lines = printed.splitlines()
        assert lines[lines.index('Test') + 1] == (
            '  No test yet. Run purlin:build login.'), printed

    # purlin: ai_audit PROOF-88
    def test_a_manual_proof_prints_manual_under_test(self, capsys):
        spec = SPEC.replace('verify 401 and the body "denied"',
                            'verify 401 and the body "denied" @manual')
        with passing_project(spec=spec) as made:
            code, printed = command(made, capsys, '--feature', 'login',
                                    '--rule', 'RULE-2')
        assert code == 0, printed
        lines = printed.splitlines()
        assert lines[lines.index('Test') + 1] == '  PROOF-2  manual', printed

    # purlin: ai_audit PROOF-89
    def test_the_strength_shows_its_whole_number_part(self, capsys):
        with passing_project(strength=85.7) as made:
            code, printed = command(made, capsys, '--feature', 'login',
                                    '--rule', 'RULE-2')
        assert code == 0, printed
        assert 'Test strength 85%.' in \
            printed.splitlines(), printed

    # purlin: ai_audit PROOF-90
    def test_a_project_root_that_is_not_a_directory_exits_two(self, tmp_path,
                                                              capsys):
        missing = str(tmp_path / 'no' / 'such' / 'folder')
        assert audit_module.main(['--feature', 'login', '--project-root',
                                  missing]) == 2
        assert capsys.readouterr().err == (
            'ai_audit.py: %s is not a directory.\n' % missing)

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

    # purlin: ai_audit PROOF-81
    def test_a_settings_file_that_cannot_be_read_stops_it(self, proved,
                                                          capsys):
        config = os.path.join(proved.root, '.purlin', 'config.json')
        with open(config, 'w', encoding='utf-8') as handle:
            handle.write(TRAILING_COMMA)
        before = TestWriting._files(proved.root)
        code, printed = command(proved, capsys, '--feature', 'login')
        assert code == 1
        # The JSON reader's own words and line, which differ by Python version.
        with pytest.raises(ValueError) as reader:
            json.loads(TRAILING_COMMA)
        assert printed == (
            '.purlin/config.json cannot be read: %s at line %d. Fix the file '
            'by hand; nothing ran and nothing was saved.\n'
            % (reader.value.msg, reader.value.lineno)), printed
        assert TestWriting._files(proved.root) == before
