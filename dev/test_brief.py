"""Tests for `scripts/review/brief.py`: the layers, the report, the file.

The throwaway project is `dev/test_signatures.py`'s, so a spec, a test file, a
runtime proof file and the evidence are written by the test and nothing reads
this repository's own specs. No model is ever called: the one test that exercises
the AI audit replaces the process launch, so nothing here spends money or
reaches a service.

What each group holds:

*layers*        which layers run at which level, cheapest first
*tests*         the source of each test backing a proof stands beside it
*strength*      the test strength comes off the evidence, and reads `n/a`
                when no engine measured one
*model*         the prompt is the criteria file verbatim, the AI audit runs
                only for a rule whose level is `strong` or `signed` and only
                with `--ai`
*observations*  the answer becomes one observation per sentence, and whether
                it settled stands beside them
*writing*       building and printing a brief writes no file
"""

import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import brief as brief_module  # noqa: E402
import marked_tests  # noqa: E402
from test_signatures import (REVIEW_GATE, SIGNING_GATE, SPEC,  # noqa: E402
                             TEST_FILE,
                             Project, write)

BRIEF_PY = os.path.join(ROOT, 'scripts', 'review', 'brief.py')
CRITERIA = os.path.join(ROOT, 'references', 'review_criteria.md')

# A model answer in the shape the prompt asks for: whether it settled, then
# one line per observation.
ANSWER = ('settled: no\n'
          '- PROOF-2 asserts the status but never the body the rule names.\n')


@pytest.fixture
def proved():
    made = Project()
    made.proofs()
    made.evidence()
    yield made
    made.close()


@pytest.fixture
def at_strong():
    """The same project at `strong`, where an unmarked rule asks for a model."""
    made = Project(gate=REVIEW_GATE)
    made.proofs()
    made.evidence()
    yield made
    made.close()


@pytest.fixture
def at_signed():
    """A project at `signed`."""
    made = Project(gate=SIGNING_GATE)
    made.proofs()
    made.evidence()
    yield made
    made.close()


def build(project, rule='RULE-1', ai=False):
    return brief_module.build_brief(project.root, None, 'login', rule, ai=ai)


# ---------------------------------------------------------------------------
# The layers
# ---------------------------------------------------------------------------

class TestTheLayers:

    @pytest.mark.proof("brief", "PROOF-1", "RULE-1")
    @pytest.mark.proof("brief", "PROOF-3", "RULE-2")
    def test_a_passed_level_stops_after_the_test_strength(self, proved,
                                                          at_strong):
        assert build(proved, 'RULE-1')['layers'] == ['test strength']
        assert build(at_strong, 'RULE-2')['layers'][-1] == 'AI audit'

    @pytest.mark.proof("brief", "PROOF-4", "RULE-3")
    def test_a_strong_level_runs_every_layer(self, at_strong):
        assert build(at_strong, 'RULE-2')['layers'] == [
            'test strength', 'AI audit']

    @pytest.mark.proof("brief", "PROOF-2", "RULE-1")
    def test_a_passed_level_asks_for_no_model(self, proved):
        built = build(proved, 'RULE-1')
        assert 'AI audit' not in built['layers']
        assert built['ai_review'] is None

    @pytest.mark.proof("brief", "PROOF-5", "RULE-4")
    def test_a_rule_that_is_not_there_has_no_brief(self, proved):
        assert build(proved, 'RULE-99') is None


# ---------------------------------------------------------------------------
# The tests beside the rule
# ---------------------------------------------------------------------------

class TestTheTests:

    @pytest.mark.proof("brief", "PROOF-8", "RULE-7")
    def test_the_test_body_is_shown_beside_the_rule(self, proved):
        test = build(proved, 'RULE-1')['tests'][0]
        assert test['file'] == 'tests/test_login.py'
        assert test['name'] == 'test_valid_credentials_return_200'
        assert 'assert login("ada", "secret") == 200' in test['body']

    @pytest.mark.proof("brief", "PROOF-9", "RULE-8")
    def test_a_manual_proof_has_a_note_where_a_test_would_be(self):
        made = Project(spec=SPEC.replace(
            'verify 200 and a token',
            'verify 200 and a token @manual'))
        try:
            test = build(made, 'RULE-1')['tests'][0]
            assert test['file'] is None
            assert test['body'] is None
            assert test['manual'] is True
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-12", "RULE-10")
    def test_the_brief_carries_no_recommendation_and_no_grade(self, proved):
        built = build(proved, 'RULE-1')
        assert set(built) == {
            'feature', 'rule', 'level', 'rule_text',
            'proofs', 'rule_hash', 'proof_hash', 'test_hash', 'test_hash_kind',
            'triple_hash', 'layers', 'tests', 'test_strength', 'min_strength',
            'ai_review', 'observations', 'settled',
            'generated_at'}, sorted(built)
        assert built['observations'] == []


class TestTheJavaScriptReader:

    @staticmethod
    def _bodies(feature, text):
        return {proof: body for proof, _rule, _name, body
                in marked_tests._iter_js_proof_bodies(text, feature)}

    @pytest.mark.proof("brief", "PROOF-46", "RULE-28")
    def test_braces_and_apostrophes_do_not_cut_a_body(self, tmp_path):
        text = """import { describe, it, expect } from "vitest";
import { execSync } from "node:child_process";

describe("repro", () => {
  it("execSync options trigger early-truncation [proof:demo:PROOF-1:RULE-1]", () => {
    const out = execSync("ls", { cwd: ".", encoding: "utf8" });
    expect(out).toMatch(/./);
  });

  it("cd's into a sibling [proof:demo:PROOF-2:RULE-2]", () => {
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

    @pytest.mark.proof("brief", "PROOF-47", "RULE-28")
    def test_regex_literals_comments_and_division_do_not_cut_a_body(self):
        text = r"""import { it, expect } from "vitest";

it("division across a line [proof:rx:PROOF-1:RULE-1]", () => {
  const s = "a" +
    / 2;
  expect(s).toBe("a");
});

it("a class holding a brace, a slash and quotes [proof:rx:PROOF-2:RULE-2]", () => {
  const re = /[}/"']+/g;
  expect("a}/b".replace(re, "")).toBe("ab");
});

it("an escaped slash [proof:rx:PROOF-3:RULE-3]", () => {
  const re = /\/}/;
  expect("x/}".match(re)[0]).toBe("/}");
});

it("comments [proof:rx:PROOF-4:RULE-4]", () => {
  // a } in a line comment
  /* and } in a block one */
  expect(1 + 1).toBe(2);
});

it("division [proof:rx:PROOF-5:RULE-5]", () => { const q = 4 / 2; expect(q).toBe(2); }); it("division again [proof:rx:PROOF-6:RULE-6]", () => { expect(8 / 4).toBe(2); });
"""
        bodies = self._bodies('rx', text)
        assert sorted(bodies) == ['PROOF-%d' % n for n in range(1, 7)], (
            'a misread `/` swallowed a test: %s' % sorted(bodies))
        for proof, body in sorted(bodies.items()):
            assert 'expect(' in body, (proof, body)


# ---------------------------------------------------------------------------
# The test strength
# ---------------------------------------------------------------------------

class TestTheTestStrength:

    @pytest.mark.proof("brief", "PROOF-10", "RULE-9")
    def test_it_comes_off_the_evidence(self, at_strong):
        assert build(at_strong, 'RULE-2')['test_strength'] == 90
        assert build(at_strong, 'RULE-2')['min_strength'] == 70

    @pytest.mark.proof("brief", "PROOF-10", "RULE-9")
    def test_a_passed_level_still_reads_the_strength(self, proved):
        assert build(proved, 'RULE-1')['test_strength'] == 90, (
            'the strength layer runs at every level')

    @pytest.mark.proof("brief", "PROOF-11", "RULE-9")
    def test_no_engine_reads_as_n_a(self):
        made = Project()
        try:
            made.proofs()
            made.evidence(strength=None)
            rendered = brief_module.render_brief(build(made, 'RULE-2'))
            assert 'Test strength: n/a' in rendered
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The AI audit
# ---------------------------------------------------------------------------

class TestTheModelReview:

    @pytest.mark.proof("brief", "PROOF-19", "RULE-15")
    def test_the_prompt_is_the_criteria_file_verbatim(self, at_strong):
        built = build(at_strong, 'RULE-2')
        prompt = brief_module.model_prompt(at_strong.root, built)
        with open(CRITERIA, encoding='utf-8') as handle:
            criteria = handle.read()
        assert prompt.startswith(criteria)
        assert 'RULE-2' in prompt
        assert 'Invalid credentials return 401' in prompt
        assert 'test_a_bad_password_is_denied' in prompt
        assert 'Test strength: 90 percent (minimum 70)' in prompt

    @pytest.mark.proof("brief", "PROOF-44", "RULE-15")
    def test_the_prompt_asks_for_observations_and_bars_a_recommendation(
            self, at_strong):
        prompt = brief_module.model_prompt(at_strong.root,
                                           build(at_strong, 'RULE-2'))
        assert 'settled: yes' in prompt
        assert 'one line per observation' in prompt
        assert 'Do not recommend a change' in prompt
        assert 'do not grade the rule' in prompt

    @pytest.mark.proof("brief", "PROOF-20", "RULE-16")
    def test_without_ai_the_brief_says_not_available(self, at_strong):
        built = build(at_strong, 'RULE-2')
        assert built['ai_review'] == 'not available'
        assert built['observations'] == [] and built['settled'] is None
        assert 'Settled: not answered' in brief_module.render_brief(built)

    @pytest.mark.proof("brief", "PROOF-21", "RULE-16")
    def test_with_no_claude_on_the_path_it_says_not_available(
            self, at_strong, monkeypatch):
        monkeypatch.setattr(brief_module.shutil, 'which', lambda name: None)
        assert build(at_strong, 'RULE-2', ai=True)['ai_review'] == (
            'not available')

    @pytest.mark.proof("brief", "PROOF-22", "RULE-16")
    def test_a_rule_whose_level_is_passed_never_calls_a_model(
            self, at_strong, monkeypatch):
        def fail(*args, **kwargs):
            raise AssertionError('a rule whose level is passed calls no model')

        monkeypatch.setattr(brief_module.shutil, 'which', fail)
        built = build(at_strong, 'RULE-1', ai=True)
        assert built['ai_review'] is None
        assert 'Observations' not in brief_module.render_brief(built)


# ---------------------------------------------------------------------------
# The observations
# ---------------------------------------------------------------------------

class TestTheObservations:

    @pytest.mark.proof("brief", "PROOF-23", "RULE-12")
    def test_the_answer_becomes_one_observation_per_sentence(
            self, at_strong, monkeypatch):
        calls = []
        real_run = brief_module.subprocess.run

        class Result(object):
            returncode = 0
            stdout = ANSWER

        def fake_run(command, **kwargs):
            if command and command[0] == 'claude':
                calls.append(command)
                return Result()
            return real_run(command, **kwargs)

        monkeypatch.setattr(brief_module.shutil, 'which',
                            lambda name: '/usr/local/bin/claude')
        monkeypatch.setattr(brief_module.subprocess, 'run', fake_run)
        built = build(at_strong, 'RULE-2', ai=True)
        assert len(calls) == 1 and calls[0][:2] == ['claude', '-p']
        assert built['observations'] == [
            'PROOF-2 asserts the status but never the body the rule names.']
        assert built['settled'] is False

    @pytest.mark.proof("brief", "PROOF-17", "RULE-13")
    def test_settled_reads_yes_no_or_nothing_at_all(self):
        assert brief_module.model_observations(
            'settled: yes\n') == ([], True)
        assert brief_module.model_observations(
            'settled: no\n- PROOF-1 never runs the code.') == (
            ['PROOF-1 never runs the code.'], False)

    @pytest.mark.proof("brief", "PROOF-24", "RULE-17")
    def test_an_answer_in_no_shape_at_all_observes_nothing(self):
        assert brief_module.model_observations('It looks fine to me.') == (
            [], None)
        assert brief_module.model_observations('not available') == ([], None)
        assert brief_module.model_observations('') == ([], None)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

class TestWriting:

    @staticmethod
    def _files(root):
        found = []
        for current, _dirs, names in os.walk(os.path.join(root, '.purlin')):
            if os.sep + 'runtime' in current:
                continue
            found.extend(os.path.join(current, name) for name in names)
        return sorted(found)

    @pytest.mark.proof("brief", "PROOF-27", "RULE-19")
    def test_building_and_printing_a_brief_writes_no_file(self, proved,
                                                         capsys):
        before = self._files(proved.root)
        built = build(proved, 'RULE-1')
        brief_module.render_brief(built)
        assert brief_module.main(['--feature', 'login', '--project-root',
                                  proved.root]) == 0
        capsys.readouterr()
        assert self._files(proved.root) == before

    @pytest.mark.proof("brief", "PROOF-28", "RULE-19")
    def test_the_triple_moves_with_the_text(self, proved):
        built = build(proved, 'RULE-1')
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a short session token'))
        again = build(proved, 'RULE-1')
        assert again['triple_hash'] != built['triple_hash'], (
            'a brief for text that has since changed is not a brief for it')

    @pytest.mark.proof("brief", "PROOF-31", "RULE-22")
    def test_the_rendering_names_the_rule_the_proof_and_what_was_found(
            self, at_strong):
        rendered = brief_module.render_brief(build(at_strong, 'RULE-2'))
        assert 'login RULE-2' in rendered
        assert 'Invalid credentials return 401' in rendered
        assert 'PROOF-2' in rendered
        assert 'Test strength: 90 percent   minimum 70' in rendered
        assert 'Observations' in rendered and 'Settled:' in rendered
        assert '✓' not in rendered and ':)' not in rendered


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    @pytest.mark.proof("brief", "PROOF-32", "RULE-23")
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert brief_module.main(['--help']) == 0
        assert brief_module.main(['--nope']) == 2
        assert brief_module.main([]) == 2

    @pytest.mark.proof("brief", "PROOF-34", "RULE-24")
    def test_one_rule_prints_its_brief_and_writes_nothing(self, proved,
                                                         capsys):
        before = TestWriting._files(proved.root)
        code = brief_module.main(['--feature', 'login', '--rule', 'RULE-1',
                                  '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 0
        assert 'login RULE-1' in output
        assert TestWriting._files(proved.root) == before

    @pytest.mark.proof("brief", "PROOF-35", "RULE-24")
    def test_a_feature_with_no_rule_named_covers_every_rule(self, proved,
                                                            capsys):
        code = brief_module.main(['--feature', 'login',
                                  '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 0
        assert 'login RULE-1' in output and 'login RULE-2' in output

    @pytest.mark.proof("brief", "PROOF-33", "RULE-23")
    def test_an_unknown_feature_exits_one(self, proved, capsys):
        code = brief_module.main(['--feature', 'nothing',
                                  '--project-root', proved.root])
        capsys.readouterr()
        assert code == 1

    @pytest.mark.proof("brief", "PROOF-36", "RULE-23")
    def test_the_script_runs_as_a_command(self, proved):
        result = subprocess.run(
            [sys.executable, BRIEF_PY, '--feature', 'login', '--rule',
             'RULE-1', '--project-root', proved.root],
            capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'login RULE-1' in result.stdout
