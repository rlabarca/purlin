"""Tests for `scripts/review/ai_audit.py`: the prompt, the call, the answer.

The throwaway project is `dev/test_signatures.py`'s, so a spec, a test file, a
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
*writing*   reading and printing a rule writes no file
"""

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
from sign_project import (REVIEW_GATE, SIGNING_GATE, SPEC,  # noqa: E402
                          TEST_FILE, Project)

AI_AUDIT_PY = os.path.join(ROOT, 'scripts', 'review', 'ai_audit.py')
CRITERIA = os.path.join(ROOT, 'references', 'review_criteria.md')

FINDING = 'PROOF-2 asserts the status but never the body the rule names.'


@pytest.fixture
def proved():
    made = Project()
    made.proofs()
    made.evidence()
    yield made
    made.close()


@pytest.fixture
def at_strong():
    """The same project at `strong`, where an unmarked rule is read."""
    made = Project(gate=REVIEW_GATE)
    made.proofs()
    made.evidence()
    yield made
    made.close()


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


# ---------------------------------------------------------------------------
# What is read
# ---------------------------------------------------------------------------

class TestWhichRulesAreRead:

    @staticmethod
    def _rule(**overrides):
        rule = {'label': 'own', 'audit': None,
                'cells': {'passed': {'word': 'passed'}},
                'proofs': [{'id': 'PROOF-1', 'manual': False,
                            'tests': [{'file': 't.py', 'name': 'test_x'}]}]}
        rule.update(overrides)
        return rule

    # purlin: ai_audit PROOF-1
    def test_a_passing_rule_with_no_entry_is_read(self):
        assert audit_module.is_read(self._rule(), 'strong') is True

    # purlin: ai_audit PROOF-2
    def test_a_rule_that_did_not_pass_or_has_no_test_is_not_read(self):
        assert audit_module.is_read(self._rule(cells={'passed': {
            'word': 'failed'}}), 'strong') is False
        assert audit_module.is_read(self._rule(proofs=[
            {'id': 'PROOF-1', 'manual': True, 'tests': []}]), 'strong') \
            is False
        assert audit_module.is_read(self._rule(label='required'),
                                    'strong') is False

    # purlin: ai_audit PROOF-3
    def test_a_passing_rule_is_read_at_the_gate_passed(self):
        assert audit_module.is_read(self._rule(), 'passed') is True

    # purlin: ai_audit PROOF-4
    def test_an_entry_for_the_current_hashes_is_skipped_unless_again(self):
        audited = self._rule(audit={'verdict': 'strong', 'findings': []})
        assert audit_module.is_read(audited, 'strong') is False
        assert audit_module.is_read(audited, 'strong', again=True) is True

    # purlin: ai_audit PROOF-4
    def test_an_entry_for_earlier_text_does_not_stop_a_reading(self,
                                                               at_strong):
        assert audit_module.is_read(at_strong.rule('RULE-2'), 'strong')
        at_strong.audit('RULE-2')
        assert not audit_module.is_read(at_strong.rule('RULE-2'), 'strong')
        at_strong.spec(SPEC.replace('return 401 and the body',
                                    'return 401 with the body'))
        at_strong.evidence()
        reworded = at_strong.rule('RULE-2')
        assert reworded['cells']['passed']['word'] == 'passed', reworded
        assert not reworded.get('audit'), reworded
        assert audit_module.is_read(reworded, 'strong') is True


class TestWhatOneRuleIsReadWith:

    # purlin: ai_audit PROOF-5
    def test_the_test_body_is_shown_beside_the_rule(self, proved):
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
    def test_the_strength_comes_off_the_evidence(self, at_strong):
        reading = read(at_strong, 'RULE-2')
        assert (reading['test_strength'], reading['min_strength']) == (90, 70)
        made = Project()
        try:
            made.proofs()
            made.evidence(strength=None)
            assert 'Test strength: n/a' in audit_module.render(
                read(made, 'RULE-2'))
        finally:
            made.close()


class TestTheJavaScriptReader:

    @staticmethod
    def _bodies(feature, text, tmp_path):
        """`{proof: source}` for every marked test in one TypeScript file."""
        (tmp_path / 'tests').mkdir(exist_ok=True)
        (tmp_path / 'tests' / 'rx.test.ts').write_text(text, encoding='utf-8')
        found = {}
        for number in range(1, 10):
            proof = 'PROOF-%d' % number
            body = marked_tests.source(str(tmp_path), feature, proof,
                                       'tests/rx.test.ts')
            if body is not None:
                found[proof] = body
        return found

    # purlin: ai_audit PROOF-9
    def test_braces_and_apostrophes_do_not_cut_a_body(self, tmp_path):
        text = """import { describe, it, expect } from "vitest";
import { execSync } from "node:child_process";

describe("repro", () => {
  // purlin: demo PROOF-1
  it("execSync options trigger early-truncation", () => {
    const out = execSync("ls", { cwd: ".", encoding: "utf8" });
    expect(out).toMatch(/./);
  });

  // purlin: demo PROOF-2
  it("cd's into a sibling", () => {
    expect(1).toBe(1);
  });
});
"""
        (tmp_path / 'tests').mkdir()
        (tmp_path / 'tests' / 'a.test.ts').write_text(text, encoding='utf-8')
        first = marked_tests.source(str(tmp_path), 'demo', 'PROOF-1',
                                    'tests/a.test.ts')
        second = marked_tests.source(str(tmp_path), 'demo', 'PROOF-2',
                                     'tests/a.test.ts')
        assert first is not None and second is not None, (first, second)
        assert 'expect(out).toMatch' in first, first
        assert 'expect(1).toBe(1)' in second, second

    # purlin: ai_audit PROOF-10
    def test_regex_literals_comments_and_division_do_not_cut_a_body(
            self, tmp_path):
        text = r"""import { it, expect } from "vitest";

// purlin: rx PROOF-1
it("division across a line", () => {
  const s = "a" +
    / 2;
  expect(s).toBe("a");
});

// purlin: rx PROOF-2
it("a class holding a brace, a slash and quotes", () => {
  const re = /[}/"']+/g;
  expect("a}/b".replace(re, "")).toBe("ab");
});

// purlin: rx PROOF-3
it("an escaped slash", () => {
  const re = /\/}/;
  expect("x/}".match(re)[0]).toBe("/}");
});

// purlin: rx PROOF-4
it("comments", () => {
  // a } in a line comment
  /* and } in a block one */
  expect(1 + 1).toBe(2);
});

// purlin: rx PROOF-5
it("division", () => { const q = 4 / 2; expect(q).toBe(2); });
// purlin: rx PROOF-6
it("division again", () => { expect(8 / 4).toBe(2); });
"""
        bodies = self._bodies('rx', text, tmp_path)
        assert sorted(bodies) == ['PROOF-%d' % n for n in range(1, 7)], (
            'a misread `/` swallowed a test: %s' % sorted(bodies))
        for proof, body in sorted(bodies.items()):
            assert 'expect(' in body, (proof, body)


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

class TestThePrompt:

    # purlin: ai_audit PROOF-11
    def test_the_prompt_is_the_criteria_file_verbatim(self, at_strong):
        prompt = audit_module.model_prompt(at_strong.root,
                                           read(at_strong, 'RULE-2'))
        assert prompt.startswith(criteria_text())
        assert 'RULE-2' in prompt
        assert 'Invalid credentials return 401' in prompt
        assert 'test_a_bad_password_is_denied' in prompt
        assert 'Test strength: 90 percent (minimum 70)' in prompt
        after = prompt[len(criteria_text()):]
        assert ('POST /login with a bad password; verify 401 and the body '
                '"denied"') in after
        assert 'assert login("ada", "wrong") == 401' in after

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
        assert found['verdict'] == 'strong', found
        assert len(calls) == 1, calls
        assert calls[0]['argv'] == ['-p', '--output-format', 'json']
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

    # purlin: ai_audit PROOF-15
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


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------

class TestTheAnswer:

    # purlin: ai_audit PROOF-17
    def test_settled_with_nothing_found_is_strong(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes'])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert (found['verdict'], found['findings']) == ('strong', [])

    # purlin: ai_audit PROOF-18
    def test_settled_with_a_line_is_weak_and_the_line_is_the_finding(
            self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes\n- %s\n' % FINDING])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert (found['verdict'], found['findings']) == ('weak', [FINDING])

    # purlin: ai_audit PROOF-19
    def test_not_settled_is_undecided_with_its_reason(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: no\n- The body of PROOF-2 is not shown.'])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert (found['verdict'], found['findings']) == (
            'undecided', ['The body of PROOF-2 is not shown.'])

    # purlin: ai_audit PROOF-20
    def test_the_answer_names_its_model_and_the_criteria_it_was_sent(
            self, at_strong, claude):
        install, _directory = claude
        install(model='claude-opus-4-1-20250805')
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert found['model'] == 'claude-opus-4-1-20250805'
        assert found['criteria'] == hashlib.sha256(
            criteria_text().encode('utf-8')).hexdigest()
        install(model=None)
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert found['model'] == 'unknown'

    # purlin: ai_audit PROOF-21
    def test_the_model_that_wrote_most_is_the_one_named(self):
        body = {'modelUsage': {'claude-haiku-3-5': {'outputTokens': 12},
                               'claude-opus-4-1': {'outputTokens': 900}}}
        assert audit_module.model_name(body) == 'claude-opus-4-1'
        body = {'modelUsage': {'claude-opus-4-1': {'outputTokens': 900},
                               'claude-haiku-3-5': {'outputTokens': 12}}}
        assert audit_module.model_name(body) == 'claude-opus-4-1'
        body = {'modelUsage': {'claude-opus-4-1': {'outputTokens': 12},
                               'claude-haiku-3-5': {'outputTokens': 900}}}
        assert audit_module.model_name(body) == 'claude-haiku-3-5'
        assert audit_module.model_name({'model': 'claude-x-1'}) == \
            'claude-x-1'
        assert audit_module.model_name({}) == 'unknown'

    # purlin: ai_audit PROOF-37
    def test_a_note_is_not_a_finding(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes\nnotes:\n- PROOF-2 holds two cases.'])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert (found['verdict'], found['findings'], found['notes']) == (
            'strong', [], ['PROOF-2 holds two cases.']), found

    # purlin: ai_audit PROOF-38
    def test_a_finding_and_a_note_are_kept_apart(self, at_strong, claude):
        install, _directory = claude
        install(answers=['settled: yes\n- %s\nnotes:\n- PROOF-2 holds two '
                         'cases.' % FINDING])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert (found['verdict'], found['findings'], found['notes']) == (
            'weak', [FINDING], ['PROOF-2 holds two cases.']), found

    # purlin: ai_audit PROOF-22
    def test_an_answer_in_no_shape_says_nothing(self):
        assert audit_module.parse_answer('It looks fine to me.') == ([], None)
        assert audit_module.parse_answer('') == ([], None)
        assert audit_module.verdict_of([], None) is None


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
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert found == {'why': 'claude exited with an error'}

    # purlin: ai_audit PROOF-25
    def test_a_call_past_its_limit_is_named(self, at_strong, claude,
                                            monkeypatch):
        install, _directory = claude
        install(sleep=3)
        monkeypatch.setattr(audit_module, 'MODEL_TIMEOUT', 1)
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert found == {'why': 'claude timed out after 1 s'}

    # purlin: ai_audit PROOF-26
    def test_an_answer_with_no_settled_line_is_asked_once_more(
            self, at_strong, claude):
        install, directory = claude
        install(answers=['It looks fine to me.'])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert found == {'why': 'claude answered without a settled line'}
        assert len(fake_claude.calls(directory)) == 2
        install(answers=['It looks fine to me.', 'settled: yes'])
        found = audit_module.audit_one(at_strong.root,
                                       read(at_strong, 'RULE-2'),
                                       criteria_text())
        assert found['verdict'] == 'strong', found
        assert len(fake_claude.calls(directory)) == 2


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

class TestWriting:

    @staticmethod
    def _files(root):
        found = []
        for current, _dirs, names in os.walk(os.path.join(root, '.purlin')):
            found.extend(os.path.join(current, name) for name in names)
        return sorted(found)

    # purlin: ai_audit PROOF-27
    def test_reading_asking_and_printing_write_no_file(self, at_strong,
                                                       claude, capsys):
        before = self._files(at_strong.root)
        reading = read(at_strong, 'RULE-2')
        audit_module.audit_all(at_strong.root, [reading], 4)
        audit_module.render(reading)
        assert audit_module.main(['--feature', 'login', '--project-root',
                                  at_strong.root]) == 0
        capsys.readouterr()
        assert self._files(at_strong.root) == before

    # purlin: ai_audit PROOF-28
    def test_the_triple_moves_with_the_text(self, proved):
        first = read(proved, 'RULE-1')
        assert read(proved, 'RULE-1')['triple_hash'] == first['triple_hash']
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a short session token'))
        assert read(proved, 'RULE-1')['triple_hash'] != first['triple_hash']
        proved.spec(SPEC)
        assert read(proved, 'RULE-1')['triple_hash'] == first['triple_hash']
        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200 and a token that expires'))
        assert read(proved, 'RULE-1')['triple_hash'] != first['triple_hash']
        proved.spec(SPEC)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200  # checked'))
        assert read(proved, 'RULE-1')['triple_hash'] != first['triple_hash']

    # purlin: ai_audit PROOF-29
    def test_the_rendering_names_the_rule_and_what_the_audit_found(
            self, at_strong):
        at_strong.audit('RULE-2', findings=[FINDING])
        rendered = audit_module.render(read(at_strong, 'RULE-2'))
        assert 'login RULE-2' in rendered
        assert 'Invalid credentials return 401' in rendered
        assert 'PROOF-2' in rendered
        assert 'Test strength: 90 percent   minimum 70' in rendered
        assert 'What the audit found' in rendered
        assert 'Weak, by unknown at 2026-09-13T12:05:00Z.' in rendered
        assert FINDING in rendered
        assert '✓' not in rendered and ':)' not in rendered
        fresh = Project(gate=SIGNING_GATE)
        try:
            fresh.proofs()
            fresh.evidence()
            assert "Nothing yet: no audit has read this rule's text" in \
                audit_module.render(read(fresh, 'RULE-2'))
        finally:
            fresh.close()


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    # purlin: ai_audit PROOF-30
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert audit_module.main(['--help']) == 0
        assert audit_module.main(['--nope']) == 2
        assert audit_module.main([]) == 2

    # purlin: ai_audit PROOF-31
    def test_an_unknown_feature_exits_one(self, proved, capsys):
        code = audit_module.main(['--feature', 'nothing',
                                  '--project-root', proved.root])
        capsys.readouterr()
        assert code == 1

    # purlin: ai_audit PROOF-32
    def test_one_rule_prints_and_a_feature_prints_every_rule(self, proved,
                                                             capsys):
        code = audit_module.main(['--feature', 'login', '--rule', 'RULE-1',
                                  '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 0
        assert 'login RULE-1' in output and 'login RULE-2' not in output
        code = audit_module.main(['--feature', 'login',
                                  '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 0
        assert 'login RULE-1' in output and 'login RULE-2' in output

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
