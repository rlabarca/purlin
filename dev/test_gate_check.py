"""Tests for `scripts/ci/gate_check.py`: what each gate lets through.

The gate decides whether a branch may merge, from the structured payload. The
payload has already worked out every rule's cells, so this job groups the rules
by the one cell that blocks each of them and prints that cell's own reasons.
Three things it must never do: parse a rendered table, write anything, or pass
when it cannot read the evidence.

Every fixture is a throwaway project from `dev/test_signatures.py`, with its
records committed either by a person or under the git host's build identity,
and its signatures written by a throwaway ssh key that exists only inside the
temporary directory. Nothing here reaches a network or a git host.

What each group holds:

*passed*    a passing tagged test in a record a person or CI committed
*strong*    a record CI committed, the test strength at or above the minimum,
            and a settled brief where the risk asks for one
*signed*    a current signature by someone on the signer list, made by someone
            other than the test's author and already on the protected branch
*sections*  one section per cell a rule can be blocked at, capped at 20 rules
*exit codes* 0, 1 and 2, and never 0 when the evidence cannot be read
*json*      the same result as a machine reads it
*writes*    nothing on disk moves
"""

import io
import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'ci'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import gate_check  # noqa: E402
import sign as sign_module  # noqa: E402
from test_signatures import (SPEC, Project, commit_as_ci,  # noqa: E402
                             git, signing_key)

GATE_PY = os.path.join(ROOT, 'scripts', 'ci', 'gate_check.py')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(project, as_json=False):
    """Run the gate over a project and return `(exit code, what it printed)`."""
    out = io.StringIO()
    code = gate_check.check(project.root, out=out, as_json=as_json)
    return code, out.getvalue()


def project_at(gate, strength=90, by_ci=True, config=None, briefs=('RULE-2',)):
    """A project whose rules have a record and a brief, at the gate named."""
    settings = {'min_strength': 50}
    settings.update(config or {})
    made = Project(gate=gate, config=settings)
    made.proofs()
    made.record(strength=strength, runner='ci' if by_ci else 'ada',
                commit_it=False)
    for rule in briefs or ():
        made.brief(rule)
    if by_ci:
        commit_as_ci(made.root)
    else:
        git(made.root, 'add', '-A')
        git(made.root, 'commit', '-q', '-m', 'purlin: record for abc1234')
    return made


def signed_project(signer='jane@acme.com', strength=90, config=None):
    """A project at `signed` whose only unsigned rule is the high-risk one."""
    settings = {'min_strength': 80, 'signers': [signer]}
    settings.update(config or {})
    made = project_at('signed', strength=strength, config=settings)
    signing_key(made.root, signer)
    return made


# ---------------------------------------------------------------------------
# passed
# ---------------------------------------------------------------------------

class TestThePassedGate:

    @pytest.mark.proof("gate_check", "PROOF-1", "RULE-2", tier="integration")
    def test_a_developer_record_is_enough(self):
        made = project_at('passed', by_ci=False, briefs=())
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'gate: gate = passed' in output
            assert 'PASS. Every rule meets passed.' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-2", "RULE-3", tier="integration")
    def test_a_rule_with_no_record_is_not_passed(self):
        made = Project(gate='passed')
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not passed (2):' in output
            assert 'login RULE-1: no test' in output, output
            assert 'login RULE-2: no test' in output, output
            assert 'gate: FAIL. 2 of 2 rules do not meet passed.' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-3", "RULE-3", tier="integration")
    def test_a_failing_proof_is_named_with_its_reason(self):
        made = Project(gate='passed')
        try:
            made.proofs({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            made.record({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            code, output = run(made)
            assert code == 1
            assert 'login RULE-1: failed' in output, output
            assert 'failing:' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-4", "RULE-3", tier="integration")
    def test_a_drafted_rule_is_not_passed_and_says_which_finding(self):
        made = Project(spec=SPEC.replace(
            'POST /login with the password "secret"; verify 200 and a token '
            '@integration',
            'The login works correctly @integration'), gate='passed')
        try:
            made.proofs()
            made.record()
            code, output = run(made)
            assert code == 1
            assert 'login RULE-1: drafted' in output, output
            assert 'vague_verb' in output, output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-5", "RULE-6", tier="integration")
    def test_no_minimum_test_strength_is_printed_under_passed(self):
        made = project_at('passed', strength=10, by_ci=False, briefs=(),
                          config={'min_strength': 80})
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'minimum test strength' not in output
            assert 'Weak' not in output and 'Not signed' not in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# strong
# ---------------------------------------------------------------------------

class TestTheStrongGate:

    @pytest.mark.proof("gate_check", "PROOF-6", "RULE-2", tier="integration")
    def test_a_record_ci_committed_with_a_settled_brief_passes(self):
        made = project_at('strong')
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'gate: gate = strong' in output
            assert 'minimum test strength 50.' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-7", "RULE-3", tier="integration")
    def test_a_developer_record_does_not_count(self):
        made = project_at('strong', by_ci=False)
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not passed (2):' in output
            assert 'developer record does not count under strong' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-8", "RULE-4", tier="integration")
    def test_below_the_minimum_test_strength_is_weak(self):
        made = project_at('strong', strength=40, config={'min_strength': 70})
        try:
            code, output = run(made)
            assert code == 1
            assert 'Weak (2):' in output
            assert 'strength 40% under 70%' in output, output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-9", "RULE-4", tier="integration")
    def test_a_rule_with_no_brief_needs_a_person(self):
        made = project_at('strong', briefs=())
        try:
            code, output = run(made)
            assert code == 1
            assert 'Weak (1):' in output
            assert 'login RULE-2: needs a person' in output, output
            assert 'no brief for the current hashes' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-10", "RULE-4", tier="integration")
    def test_an_observation_the_model_made_stands_against_the_rule(self):
        made = project_at('strong', briefs=())
        try:
            made.brief('RULE-2',
                       observations=['PROOF-2 asserts the status but never '
                                     'the body the rule names.'])
            commit_as_ci(made.root, 'purlin: record for abc1234')
            code, output = run(made)
            assert code == 1
            assert 'login RULE-2: needs a person' in output, output
            assert 'never the body the rule names' in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# signed
# ---------------------------------------------------------------------------

class TestTheSignedGate:

    @pytest.mark.proof("gate_check", "PROOF-11", "RULE-5", tier="integration")
    def test_a_current_signature_by_a_signer_passes_its_rule(self):
        made = signed_project()
        try:
            assert sign_module.main(
                ['login', 'RULE-2', '--project-root', made.root]) == 0
            code, output = run(made)
            assert code == 0, output
            assert 'gate: gate = signed' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-12", "RULE-5", tier="integration")
    def test_a_rule_below_sign_at_needs_no_signature(self):
        made = signed_project()
        try:
            sign_module.main(['login', 'RULE-2', '--project-root', made.root])
            code, output = run(made)
            assert code == 0, output
            assert 'login RULE-1' not in output, (
                'low risk is below sign_at and never blocks the branch')
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-13", "RULE-5", tier="integration")
    def test_a_rule_with_no_signature_is_not_signed(self):
        made = signed_project()
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not signed (1):' in output
            assert 'login RULE-2: unsigned' in output, output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-14", "RULE-5", tier="integration")
    def test_an_unsigned_commit_does_not_carry_a_signature(self):
        made = signed_project()
        try:
            entry = made.rule('RULE-2')
            sign_module.write_signature(
                made.root, 'login', 'RULE-2', 'jane@acme.com', None, None,
                'signed', 'high', entry=entry)
            git(made.root, 'add', '-A')
            git(made.root, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m',
                'chore: a signature nobody signed')
            code, output = run(made)
            assert code == 1
            assert 'the signing commit is not signed' in output, output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-15", "RULE-5", tier="integration")
    def test_the_author_of_the_test_may_not_sign_it(self):
        made = signed_project(signer='dev@example.com')
        try:
            assert sign_module.main(
                ['login', 'RULE-2', '--project-root', made.root]) == 0
            code, output = run(made)
            assert code == 1
            assert 'the signer last touched the test' in output, output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-16", "RULE-5", tier="integration")
    def test_a_signature_the_text_moved_under_reads_stale(self):
        made = signed_project(config={'sign_at': 'low'})
        try:
            assert sign_module.main(
                ['login', '--project-root', made.root]) == 0
            made.spec(SPEC.replace('return 200 with a session token',
                                   'return 200 with a signed session token'))
            code, output = run(made)
            assert code == 1
            assert 'login RULE-1: stale' in output, output
            assert 'hashes changed after the signature' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-17", "RULE-5", tier="integration")
    def test_a_signature_only_on_a_side_branch_is_not_on_the_branch(self):
        made = signed_project()
        try:
            # A side branch is only a side branch next to a protected one, and
            # what says which that is is `origin/HEAD`. Without it the reader
            # has nothing but the branch it is standing on, and every branch
            # is the branch.
            git(made.root, 'update-ref', 'refs/remotes/origin/main',
                git(made.root, 'rev-parse', 'HEAD').stdout.strip())
            git(made.root, 'symbolic-ref', 'refs/remotes/origin/HEAD',
                'refs/remotes/origin/main')
            git(made.root, 'checkout', '-q', '-b', 'side')
            sign_module.main(['login', 'RULE-2', '--project-root', made.root])
            code, output = run(made)
            assert code == 1
            assert 'the signing commit is not on main' in output, output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-18", "RULE-8", tier="integration")
    def test_no_signer_list_names_the_command_and_fails(self):
        made = project_at('signed', config={'min_strength': 80})
        try:
            code, output = run(made)
            assert code == 1
            assert '→ signer list missing: run purlin:init --gate ' \
                   'signed' in output
            assert 'PASS' not in output
            assert 'Not signed' not in output, (
                'the gate fails without grading a rule')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The sections
# ---------------------------------------------------------------------------

class TestTheSections:

    @pytest.mark.proof("gate_check", "PROOF-19", "RULE-7", tier="integration")
    def test_a_section_names_twenty_rules_and_counts_the_rest(self):
        rules = ''.join('- RULE-%d: Something is true about %d [risk: low]\n'
                        % (n, n) for n in range(1, 31))
        spec = ('# Feature: login\n\n> Description: Many rules.\n\n'
                '## Rules\n\n' + rules + '\n## Proof\n\n')
        made = Project(spec=spec, gate='strong')
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not passed (30):' in output
            assert 'and 10 more; --json prints every one.' in output
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-20", "RULE-2", tier="integration")
    def test_a_required_rule_is_counted_once_under_its_owner(self):
        anchor = ('# Feature: policy\n\n'
                  '> Description: The house rules.\n'
                  '> Scope: src/login.py\n\n'
                  '## Rules\n\n'
                  '- RULE-1: Every session token is 32 characters '
                  '[risk: low]\n\n'
                  '## Proof\n\n')
        made = Project(gate='passed')
        try:
            made.spec(anchor, name='policy', category='_anchors')
            made.spec(SPEC.replace('> Scope: src/login.py',
                                   '> Requires: policy\n> Scope: src/login.py'))
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert data['rules'] == 3, output
            assert len([line for line in data['not_passed']
                        if line.startswith('policy RULE-1')]) == 1, data
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

class TestExitCodes:

    @pytest.mark.proof("gate_check", "PROOF-21", "RULE-9", tier="integration")
    def test_zero_one_and_two(self, tmp_path):
        passing = project_at('passed', by_ci=False, briefs=())
        failing = Project(gate='passed')
        try:
            assert run(passing)[0] == 0
            assert run(failing)[0] == 1
        finally:
            passing.close()
            failing.close()
        out = io.StringIO()
        assert gate_check.check(str(tmp_path), out=out) == 2
        assert 'failing closed' in out.getvalue()

    @pytest.mark.proof("gate_check", "PROOF-22", "RULE-9", tier="integration")
    def test_a_directory_that_is_not_a_project_never_passes(self, tmp_path):
        out = io.StringIO()
        code = gate_check.check(str(tmp_path / 'nothing here'), out=out)
        assert code == 2
        assert 'cannot read a Purlin project' in out.getvalue()

    @pytest.mark.proof("gate_check", "PROOF-23", "RULE-10")
    def test_check_is_required_and_a_missing_directory_is_two(self):
        assert gate_check.main([]) == 2
        assert gate_check.main(['--check', '--project-root',
                                '/no/such/directory']) == 2

    @pytest.mark.proof("gate_check", "PROOF-24", "RULE-13", tier="integration")
    def test_the_script_runs_as_a_command(self):
        made = project_at('passed', by_ci=False, briefs=())
        try:
            result = subprocess.run(
                [sys.executable, GATE_PY, '--check', '--project-root',
                 made.root], capture_output=True, text=True, timeout=120)
            assert result.returncode == 0, result.stdout + result.stderr
            assert result.stdout.startswith('gate: gate = passed')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The JSON result
# ---------------------------------------------------------------------------

class TestTheJsonResult:

    @pytest.mark.proof("gate_check", "PROOF-25", "RULE-11", tier="integration")
    def test_it_carries_the_result_and_every_rule_that_fell_short(self):
        made = Project(gate='passed')
        try:
            code, output = run(made, as_json=True)
            assert code == 1
            data = json.loads(output[output.index('{'):])
            assert data['gate'] == 'passed'
            assert data['result'] == 'fail'
            assert data['exit'] == 1
            assert data['rules'] == 2 and data['met'] == 0
            assert len(data['not_passed']) == 2
            assert data['weak'] == [] and data['not_signed'] == []
            assert data['commit'] == made.head()
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-26", "RULE-11", tier="integration")
    def test_a_passing_project_says_pass(self):
        made = project_at('passed', by_ci=False, briefs=())
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 0 and data['result'] == 'pass'
            assert data['met'] == data['rules'] == 2
            assert data['not_passed'] == []
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-27", "RULE-11", tier="integration")
    def test_a_weak_rule_lands_in_the_weak_list(self):
        made = project_at('strong', strength=40, config={'min_strength': 70})
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 1
            assert len(data['weak']) == 2 and data['not_passed'] == []
            assert data['min_strength'] == 70
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-28", "RULE-8", tier="integration")
    def test_a_missing_signer_list_says_so_in_the_json(self):
        made = project_at('signed', config={'min_strength': 80})
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 1
            assert data['signer_list'] == 'missing'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The gate never writes
# ---------------------------------------------------------------------------

class TestTheGateNeverWrites:

    @pytest.mark.proof("gate_check", "PROOF-29", "RULE-12", tier="integration")
    def test_no_file_is_created_or_changed_at_any_level(self):
        for gate in ('passed', 'strong', 'signed'):
            made = project_at(gate, config={'signers': ['jane@acme.com']})
            try:
                before = _tree(made.root)
                run(made)
                assert _tree(made.root) == before, (
                    'a gate that can edit the evidence it grades is not a gate')
                status = git(made.root, 'status', '--porcelain').stdout
                assert status.strip() == '', status
            finally:
                made.close()


def _tree(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, 'rb') as handle:
                found[os.path.relpath(path, root)] = handle.read()
    return found


# ---------------------------------------------------------------------------
# What the gate reads
# ---------------------------------------------------------------------------

class TestWhatTheGateReads:

    @pytest.mark.proof("gate_check", "PROOF-30", "RULE-1")
    def test_it_reads_the_payload_and_not_a_rendered_table(self):
        with open(GATE_PY, encoding='utf-8') as handle:
            source = handle.read()
        assert 'build_payload' in source
        assert "rule['meets_gate']" in source or "'meets_gate'" in source
        for glyph in ('─', '│', '┌'):
            assert glyph not in source, (
                'a gate that parsed a rendered table would move with the '
                'dashboard')

    @pytest.mark.proof("gate_check", "PROOF-31", "RULE-1", tier="integration")
    def test_a_caller_may_hand_over_the_payload_it_already_built(self):
        made = project_at('passed', by_ci=False, briefs=())
        try:
            payload = made.payload()
            out = io.StringIO()
            assert gate_check.check(made.root, payload=payload, out=out) == 0
            assert 'PASS' in out.getvalue()
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-32", "RULE-13", tier="integration")
    def test_every_line_it_prints_carries_the_prefix_or_is_a_finding(self):
        made = Project(gate='passed')
        try:
            _code, output = run(made)
            heads = [line for line in output.splitlines()
                     if line and not line.startswith(' ')]
            assert heads
            for line in heads:
                assert line.startswith('gate:') or line.endswith(':'), line
        finally:
            made.close()
