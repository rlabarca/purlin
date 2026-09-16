"""Tests for `scripts/review/brief.py`: the layers, the verdict, the file.

The throwaway project is `dev/test_signatures.py`'s, so a spec, a test file, a
runtime proof file and a record are written by the test and nothing reads this
repository's own specs. No model is ever called: the one test that exercises
the model review replaces the process launch, so nothing here spends money or
reaches a service.

What each group holds:

*layers*    which layers run at which risk, cheapest first
*findings*  the free checks on the proof text and on the test body reach the
            brief under the names `references/review_criteria.md` gives them
*strength*  the test strength comes off the latest record, and reads `n/a`
            when no engine measured one
*verdict*   the four words, and which evidence produces each
*model*     the prompt is the criteria file verbatim, the review runs only for
            a rule that needs one and only with `--ai`
*design*    a design rule shows the mock beside the screenshot
*writing*   the brief is written beside the approval it informs, named for the
            triple, with a text rendering beside it
"""

import json
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
from test_signatures import SPEC, TEST_FILE, Project, git, write  # noqa: E402

BRIEF_PY = os.path.join(ROOT, 'scripts', 'review', 'brief.py')
CRITERIA = os.path.join(ROOT, 'references', 'review_criteria.md')


@pytest.fixture
def proved():
    made = Project()
    made.proofs()
    made.record()
    yield made
    made.close()


@pytest.fixture
def reviewed():
    """The same project at gate `recorded`, where a high-risk rule needs a model."""
    made = Project(gate='recorded')
    made.proofs()
    made.record()
    yield made
    made.close()


def build(project, rule='RULE-1', ai=False):
    return brief_module.build_brief(project.root, None, 'login', rule, ai=ai)


# ---------------------------------------------------------------------------
# The layers
# ---------------------------------------------------------------------------

class TestTheLayers:

    @pytest.mark.proof("brief", "PROOF-1", "RULE-1", tier="integration")
    def test_low_risk_stops_after_the_free_checks(self, proved):
        assert build(proved, 'RULE-1')['layers'] == ['proof text', 'test body']

    @pytest.mark.proof("brief", "PROOF-4", "RULE-3", tier="integration")
    def test_high_risk_runs_every_layer(self, proved):
        assert build(proved, 'RULE-2')['layers'] == [
            'proof text', 'test body', 'test strength', 'model review']

    @pytest.mark.proof("brief", "PROOF-3", "RULE-2", tier="integration")
    def test_medium_risk_stops_after_the_test_strength(self):
        made = Project(spec=SPEC.replace('[risk: high]', '[risk: medium]'))
        try:
            made.proofs()
            made.record()
            assert build(made, 'RULE-2')['layers'] == [
                'proof text', 'test body', 'test strength']
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-5", "RULE-4", tier="integration")
    def test_a_rule_that_is_not_there_has_no_brief(self, proved):
        assert build(proved, 'RULE-99') is None


# ---------------------------------------------------------------------------
# The findings
# ---------------------------------------------------------------------------

class TestTheFindings:

    @pytest.mark.proof("brief", "PROOF-6", "RULE-5", tier="integration")
    def test_the_proof_text_findings_reach_the_brief(self):
        made = Project(spec=SPEC.replace(
            'POST /login with the password "secret"; verify 200 and a token '
            '@integration',
            'The login works correctly @integration'))
        try:
            made.proofs()
            found = build(made, 'RULE-1')['proofs'][0]['findings']
            assert 'no_expected_value' in found
            assert 'vague_verb' in found
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-37", "RULE-25", tier="integration")
    def test_a_path_segment_is_not_a_private_symbol(self):
        original = ('POST /login with the password "secret"; verify 200 and '
                    'a token @integration')
        cases = (
            ('POST /login, then read specs/_anchors/policy.md and '
             'https://dev.azure.com/acme/_git/policies; verify 200 '
             '@integration', False),
            ('Call _resolve_token and verify 200 @integration', True),
        )
        for text, coupled in cases:
            made = Project(spec=SPEC.replace(original, text))
            try:
                made.proofs()
                found = build(made, 'RULE-1')['proofs'][0]['findings']
                assert ('implementation_coupling' in found) is coupled, (
                    text, found)
            finally:
                made.close()

    @pytest.mark.proof("brief", "PROOF-7", "RULE-6", tier="integration")
    def test_the_test_body_findings_reach_the_brief(self, proved):
        proved.edit_test(TEST_FILE.replace(
            'assert login("ada", "secret") == 200', 'login("ada", "secret")'))
        test = build(proved, 'RULE-1')['tests'][0]
        assert test['findings'] == ['no_assertion'], test
        assert test['reasons'], 'a finding names what a reader should look at'

    @pytest.mark.proof("brief", "PROOF-8", "RULE-7", tier="integration")
    def test_the_test_body_is_shown_beside_the_rule(self, proved):
        test = build(proved, 'RULE-1')['tests'][0]
        assert test['file'] == 'tests/test_login.py'
        assert test['name'] == 'test_valid_credentials_return_200'
        assert 'assert login("ada", "secret") == 200' in test['body']

    @pytest.mark.proof("brief", "PROOF-9", "RULE-8", tier="integration")
    def test_a_manual_proof_has_a_note_where_a_test_would_be(self):
        made = Project(spec=SPEC.replace(
            'verify 200 and a token @integration',
            'verify 200 and a token @manual'))
        try:
            test = build(made, 'RULE-1')['tests'][0]
            assert test['file'] is None
            assert test['findings'] == ['manual']
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The test strength
# ---------------------------------------------------------------------------

class TestTheTestStrength:

    @pytest.mark.proof("brief", "PROOF-10", "RULE-9", tier="integration")
    def test_it_comes_off_the_latest_record(self, proved):
        assert build(proved, 'RULE-2')['test_strength'] == 90
        assert build(proved, 'RULE-2')['min_strength'] == 50

    @pytest.mark.proof("brief", "PROOF-2", "RULE-1", tier="integration")
    def test_a_low_risk_rule_never_asks_for_it(self, proved):
        assert build(proved, 'RULE-1')['test_strength'] is None, (
            'the strength layer does not run at low risk')

    @pytest.mark.proof("brief", "PROOF-11", "RULE-9", tier="integration")
    def test_no_engine_reads_as_n_a(self):
        made = Project()
        try:
            made.proofs()
            made.record(strength=None)
            rendered = brief_module.render_brief(build(made, 'RULE-2'))
            assert 'Test strength: n/a' in rendered
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------

class TestTheVerdict:

    @pytest.mark.proof("brief", "PROOF-17", "RULE-13", tier="integration")
    def test_a_clean_rule_is_ready(self, proved):
        assert build(proved, 'RULE-2')['verdict'] == 'ready'

    @pytest.mark.proof("brief", "PROOF-12", "RULE-10", tier="integration")
    def test_a_blocking_proof_finding_is_rewrite_the_proof(self):
        made = Project(spec=SPEC.replace(
            'POST /login with the password "secret"; verify 200 and a token '
            '@integration',
            'The login works correctly @integration'))
        try:
            made.proofs()
            built = build(made, 'RULE-1')
            assert built['verdict'] == 'rewrite the proof'
            assert any('no_expected_value' in reason
                       for reason in built['reasons'])
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-13", "RULE-11", tier="integration")
    def test_a_test_body_finding_needs_a_human(self, proved):
        proved.edit_test(TEST_FILE.replace(
            'assert login("ada", "secret") == 200', 'assert True'))
        built = build(proved, 'RULE-1')
        assert built['verdict'] == 'needs a human'
        assert any('assert_true_literal' in reason or 'tautology' in reason
                   for reason in built['reasons']), built['reasons']

    @pytest.mark.proof("brief", "PROOF-14", "RULE-11", tier="integration")
    def test_a_manual_proof_needs_a_human(self):
        made = Project(spec=SPEC.replace(
            'verify 200 and a token @integration',
            'verify 200 and a token @manual'))
        try:
            made.proofs()
            assert build(made, 'RULE-1')['verdict'] == 'needs a human'
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-15", "RULE-12", tier="integration")
    def test_only_a_happy_path_is_add_a_case(self, proved):
        built = build(proved, 'RULE-1')
        assert 'happy_path_only' in built['proofs'][0]['findings']
        assert built['verdict'] == 'add a case'

    @pytest.mark.proof("brief", "PROOF-16", "RULE-12", tier="integration")
    def test_strength_below_the_minimum_is_add_a_case(self):
        made = Project(config={'min_strength': 70})
        try:
            made.proofs()
            made.record(strength=40)
            built = build(made, 'RULE-2')
            assert built['verdict'] == 'add a case'
            assert any('40 percent' in reason for reason in built['reasons'])
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-18", "RULE-14", tier="integration")
    def test_the_four_words_are_the_only_four(self, proved):
        assert brief_module.VERDICTS == (
            'ready', 'add a case', 'rewrite the proof', 'needs a human')
        assert build(proved, 'RULE-1')['verdict'] in brief_module.VERDICTS


# ---------------------------------------------------------------------------
# The model review
# ---------------------------------------------------------------------------

class TestTheModelReview:

    @pytest.mark.proof("brief", "PROOF-19", "RULE-15", tier="integration")
    def test_the_prompt_is_the_criteria_file_verbatim(self, reviewed):
        built = build(reviewed, 'RULE-2')
        prompt = brief_module.model_prompt(reviewed.root, built)
        with open(CRITERIA, encoding='utf-8') as handle:
            criteria = handle.read()
        assert prompt.startswith(criteria)
        assert 'RULE-2' in prompt
        assert 'Invalid credentials return 401' in prompt
        assert 'test_a_bad_password_is_denied' in prompt
        assert 'Test strength: 90 percent (minimum 70)' in prompt

    @pytest.mark.proof("brief", "PROOF-20", "RULE-16", tier="integration")
    def test_without_ai_the_brief_says_not_available(self, reviewed):
        built = build(reviewed, 'RULE-2')
        assert built['ai_review'] == 'not available'
        assert 'Model review' in brief_module.render_brief(built)

    @pytest.mark.proof("brief", "PROOF-21", "RULE-16", tier="integration")
    def test_with_no_claude_on_the_path_it_says_not_available(
            self, reviewed, monkeypatch):
        monkeypatch.setattr(brief_module.shutil, 'which', lambda name: None)
        assert build(reviewed, 'RULE-2', ai=True)['ai_review'] == (
            'not available')

    @pytest.mark.proof("brief", "PROOF-23", "RULE-17", tier="integration")
    def test_the_model_answer_decides_the_verdict(self, reviewed, monkeypatch):
        calls = []
        real_run = brief_module.subprocess.run

        class Result(object):
            returncode = 0
            stdout = 'add a case\nNothing proves the lockout boundary.\n'

        def fake_run(command, **kwargs):
            if command and command[0] == 'claude':
                calls.append(command)
                return Result()
            return real_run(command, **kwargs)

        monkeypatch.setattr(brief_module.shutil, 'which',
                            lambda name: '/usr/local/bin/claude')
        monkeypatch.setattr(brief_module.subprocess, 'run', fake_run)
        built = build(reviewed, 'RULE-2', ai=True)
        assert len(calls) == 1 and calls[0][:2] == ['claude', '-p']
        assert built['ai_review'].startswith('add a case')
        assert built['verdict'] == 'add a case'

    @pytest.mark.proof("brief", "PROOF-22", "RULE-16", tier="integration")
    def test_a_low_risk_rule_never_calls_a_model(self, proved, monkeypatch):
        def fail(*args, **kwargs):
            raise AssertionError('a low-risk rule must not call a model')

        monkeypatch.setattr(brief_module.shutil, 'which', fail)
        assert build(proved, 'RULE-1', ai=True)['ai_review'] is None

    @pytest.mark.proof("brief", "PROOF-24", "RULE-17")
    def test_an_answer_that_names_no_verdict_decides_nothing(self):
        assert brief_module.model_verdict('It looks fine to me.') is None
        assert brief_module.model_verdict('not available') is None
        assert brief_module.model_verdict('Ready.') == 'ready'


# ---------------------------------------------------------------------------
# Design rules
# ---------------------------------------------------------------------------

DESIGN_SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in.\n'
    '> Scope: src/login.py\n'
    '> Source: designs/login/*.png\n'
    '> Pinned: 3f2a1b0c9d8e7f6a\n\n'
    '## Rules\n\n'
    '- RULE-1: The sign-in page shows the heading "Sign in" and one button '
    '[origin: design] [risk: low]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Open /sign-in; verify the heading "Sign in" and that '
    'no error is shown @e2e\n'
)


class TestDesignRules:

    @pytest.mark.proof("brief", "PROOF-25", "RULE-18", tier="integration")
    def test_the_mock_and_the_screenshot_stand_beside_each_other(self):
        made = Project(spec=DESIGN_SPEC)
        try:
            write(os.path.join(made.root, '.purlin', 'runtime', 'attachments',
                               'login', 'PROOF-1.png'), 'not really a png')
            write(os.path.join(made.root, 'designs', 'login', 'sign-in.png'),
                  'not really a png either')
            built = brief_module.build_brief(made.root, None, 'login', 'RULE-1')
            assert built['design']['mock'] == ['designs/login/sign-in.png']
            assert built['design']['screenshot'] == [
                '.purlin/runtime/attachments/login/PROOF-1.png']
            assert built['design']['pinned'] == '3f2a1b0c9d8e7f6a'
            assert built['design_hash'] == '3f2a1b0c9d8e7f6a'
        finally:
            made.close()

    @pytest.mark.proof("brief", "PROOF-26", "RULE-18", tier="integration")
    def test_a_design_rule_with_no_screenshot_needs_a_human(self):
        made = Project(spec=DESIGN_SPEC)
        try:
            built = brief_module.build_brief(made.root, None, 'login', 'RULE-1')
            assert built['design']['mock'] == ['designs/login/*.png'], (
                'a glob that matches nothing is shown as the glob')
            assert built['design']['screenshot'] == []
            assert built['verdict'] == 'needs a human'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

class TestWriting:

    @pytest.mark.proof("brief", "PROOF-27", "RULE-19", tier="integration")
    def test_the_brief_lands_beside_the_approval_named_for_the_triple(
            self, proved):
        built = build(proved, 'RULE-1')
        path = brief_module.write_brief(proved.root, built)
        assert path == ('specs/auth/login.signatures/RULE-1.%s.brief.json'
                        % built['triple_hash'][:8])
        text = os.path.join(proved.root, path[:-5] + '.txt')
        assert os.path.isfile(text)
        with open(os.path.join(proved.root, path), encoding='utf-8') as handle:
            assert json.load(handle)['schema'] == 'purlin-brief/1'

    @pytest.mark.proof("brief", "PROOF-28", "RULE-20", tier="integration")
    def test_a_brief_for_the_current_text_makes_the_rule_reviewed(self, proved):
        brief_module.write_brief(proved.root, build(proved, 'RULE-1'))
        assert proved.rule('RULE-1')['state'] == 'Reviewed'
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a short session token'))
        assert proved.rule('RULE-1')['state'] != 'Reviewed', (
            'a brief for text that has since changed is not a brief for it')

    @pytest.mark.proof("brief", "PROOF-29", "RULE-21", tier="integration")
    def test_write_briefs_covers_the_review_list(self, reviewed):
        written = brief_module.write_briefs(reviewed.root)
        assert written, 'the review list holds the high-risk rule'
        assert all(path.endswith('.brief.json') for path in written)
        assert any('RULE-2' in path for path in written)

    @pytest.mark.proof("brief", "PROOF-30", "RULE-21", tier="integration")
    def test_write_briefs_takes_a_narrower_list(self, proved):
        written = brief_module.write_briefs(
            proved.root, rules=[('login', 'RULE-1')])
        assert len(written) == 1 and 'RULE-1' in written[0]

    @pytest.mark.proof("brief", "PROOF-31", "RULE-22", tier="integration")
    def test_the_rendering_names_the_rule_the_proof_and_the_verdict(
            self, proved):
        rendered = brief_module.render_brief(build(proved, 'RULE-2'))
        assert 'login RULE-2' in rendered
        assert 'Invalid credentials return 401' in rendered
        assert 'PROOF-2' in rendered
        assert 'Verdict: ready' in rendered
        assert '✓' not in rendered and ':)' not in rendered


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    @pytest.mark.proof("brief", "PROOF-32", "RULE-23", tier="integration")
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert brief_module.main(['--help']) == 0
        assert brief_module.main(['--nope']) == 2
        assert brief_module.main([]) == 2

    @pytest.mark.proof("brief", "PROOF-34", "RULE-24", tier="integration")
    def test_one_rule_prints_its_brief_and_writes_it(self, proved, capsys):
        code = brief_module.main(['--feature', 'login', '--rule', 'RULE-1',
                                  '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 0
        assert 'login RULE-1' in output
        assert 'Verdict:' in output
        assert os.path.isdir(os.path.join(proved.root, 'specs', 'auth',
                                          'login.signatures'))

    @pytest.mark.proof("brief", "PROOF-35", "RULE-24", tier="integration")
    def test_a_feature_with_no_rule_named_covers_every_rule(self, proved,
                                                            capsys):
        code = brief_module.main(['--feature', 'login',
                                  '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 0
        assert 'login RULE-1' in output and 'login RULE-2' in output

    @pytest.mark.proof("brief", "PROOF-33", "RULE-23", tier="integration")
    def test_an_unknown_feature_exits_one(self, proved, capsys):
        code = brief_module.main(['--feature', 'nothing',
                                  '--project-root', proved.root])
        capsys.readouterr()
        assert code == 1

    @pytest.mark.proof("brief", "PROOF-36", "RULE-23", tier="integration")
    def test_the_script_runs_as_a_command(self, proved):
        result = subprocess.run(
            [sys.executable, BRIEF_PY, '--feature', 'login', '--rule',
             'RULE-1', '--project-root', proved.root],
            capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'Verdict:' in result.stdout
