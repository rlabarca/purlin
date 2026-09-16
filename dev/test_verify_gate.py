"""Tests for `scripts/ci/verify_gate.py`: what each gate level lets through.

The gate decides whether a branch may merge, from the structured payload. Three
things it must never do: parse a rendered table, write anything, or pass when it
cannot read the evidence.

Every fixture is a throwaway project from `dev/test_signatures.py`, with its
records committed either by a person or under the git host's build identity, and
its approvals signed by a throwaway ssh key that exists only inside the
temporary directory. Nothing here reaches a network or a git host.

What each group holds:

*tested*     a passing tagged test in a record a person or CI committed
*recorded*   a record CI committed, and the test strength at or above the
             minimum
*approved*   a current approval on every high and medium rule, signed by
             someone on the approver list, made by someone other than the
             test's author, and already on the protected branch
*exit codes* 0, 1 and 2, and never 0 when the evidence cannot be read
*json*       the same verdict as a machine reads it
*writes*     nothing on disk moves
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

import approve as approve_module  # noqa: E402
import verify_gate  # noqa: E402
from test_signatures import SPEC, Project, git, signing_key, write  # noqa: E402

GATE_PY = os.path.join(ROOT, 'scripts', 'ci', 'verify_gate.py')

# What the git host's build identity looks like on GitHub.
CI_COMMITTER = 'github-actions[bot]'
CI_EMAIL = '41898282+github-actions[bot]@users.noreply.github.com'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ci_signing_key(root):
    """A throwaway ssh key this project trusts, for the CI commit to sign with.

    The key and the allowed-signers file live inside the project's own `.git`
    and nowhere else. `None` when the machine has no `ssh-keygen`, and then
    the commit is made unsigned.
    """
    key = os.path.join(root, '.git', 'ci-signing-key')
    if not os.path.exists(key + '.pub'):
        made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                               '-C', CI_EMAIL, '-f', key],
                              capture_output=True, text=True)
        if made.returncode != 0:
            return None
    with open(key + '.pub', encoding='utf-8') as handle:
        public = handle.read().strip()
    allowed = os.path.join(root, '.git', 'ci-allowed-signers')
    with open(allowed, 'w', encoding='utf-8') as handle:
        handle.write('%s %s\n' % (CI_EMAIL, ' '.join(public.split()[:2])))
    git(root, 'config', 'gpg.ssh.allowedSignersFile', allowed)
    return key + '.pub'


def commit_as_ci(root, message='purlin: record for abc1234'):
    """Commit everything staged under the build identity, as CI does.

    CI writes through the git host's API, which signs the commit: the reader
    reads an unsigned commit claiming that identity as a person's, so a
    fixture that leaves the signature out is not what CI writes and the gate
    would refuse it on any machine that can check signatures. The signature
    here is a throwaway ssh key the project itself trusts.
    """
    environment = dict(os.environ,
                       GIT_COMMITTER_NAME=CI_COMMITTER,
                       GIT_COMMITTER_EMAIL=CI_EMAIL)
    key = ci_signing_key(root)
    subprocess.run(['git', 'add', '-A'], cwd=root, capture_output=True,
                   text=True)
    command = ['git']
    if key:
        command += ['-c', 'gpg.format=ssh', '-c', 'user.signingkey=' + key]
    command += ['commit', '-q', '-m', message]
    if key:
        command.append('-S')
    subprocess.run(command, cwd=root, env=environment, capture_output=True,
                   text=True)


def run(project, as_json=False):
    """Run the gate over a project and return `(exit code, what it printed)`."""
    out = io.StringIO()
    code = verify_gate.check(project.root, out=out, as_json=as_json)
    return code, out.getvalue()


def project_at(gate, strength=90, by_ci=True, config=None):
    """A project whose rules are recorded, at the gate named."""
    settings = {'min_strength': 50}
    settings.update(config or {})
    made = Project(gate=gate, config=settings)
    made.proofs()
    made.record(strength=strength, runner='ci' if by_ci else 'ada',
                commit_it=not by_ci)
    if by_ci:
        commit_as_ci(made.root)
    return made


# ---------------------------------------------------------------------------
# tested
# ---------------------------------------------------------------------------

class TestTheTestedGate:

    @pytest.mark.proof("signatures", "PROOF-30", "RULE-24", tier="integration")
    def test_a_developer_record_is_enough(self):
        made = project_at('tested', by_ci=False)
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'verify-gate: gate = tested' in output
            assert 'PASS. Every rule meets tested.' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-32", "RULE-25", tier="integration")
    def test_a_rule_with_no_record_fails_and_is_named(self):
        made = Project(gate='tested')
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not tested (2):' in output
            assert 'login RULE-1' in output and 'login RULE-2' in output
            assert 'verify-gate: FAIL. 2 of 2 rules do not meet tested.' \
                in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-33", "RULE-25", tier="integration")
    def test_a_failing_proof_fails_the_gate(self):
        made = Project(gate='tested')
        try:
            made.proofs({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            made.record({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            code, output = run(made)
            assert code == 1
            assert 'login RULE-1' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-31", "RULE-24", tier="integration")
    def test_the_test_strength_is_not_read_at_tested(self):
        made = project_at('tested', strength=10, by_ci=False,
                          config={'min_strength': 80})
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'Below the minimum test strength' not in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# recorded
# ---------------------------------------------------------------------------

class TestTheRecordedGate:

    @pytest.mark.proof("signatures", "PROOF-34", "RULE-26", tier="integration")
    def test_a_record_ci_committed_passes(self):
        made = project_at('recorded')
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'verify-gate: gate = recorded' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-35", "RULE-26", tier="integration")
    def test_a_developer_record_does_not_count(self):
        made = project_at('recorded', by_ci=False)
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not recorded (2):' in output
            assert 'no record CI wrote covers this commit' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-36", "RULE-27", tier="integration")
    def test_below_the_minimum_test_strength_fails(self):
        made = project_at('recorded', strength=40, config={'min_strength': 70})
        try:
            code, output = run(made)
            assert code == 1
            assert 'Below the minimum test strength (2):' in output
            assert 'test strength 40 percent, below 70' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-37", "RULE-27", tier="integration")
    def test_no_engine_leaves_the_strength_alone(self):
        made = project_at('recorded', strength=None,
                          config={'min_strength': 70})
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'Below the minimum test strength' not in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-38", "RULE-28", tier="integration")
    def test_the_report_names_twenty_rules_and_counts_the_rest(self):
        rules = ''.join('- RULE-%d: Something is true about %d [risk: low]\n'
                        % (n, n) for n in range(1, 31))
        spec = ('# Feature: login\n\n> Description: Many rules.\n\n'
                '## Rules\n\n' + rules + '\n## Proof\n\n')
        made = Project(spec=spec, gate='recorded')
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not recorded (30):' in output
            assert 'and 10 more; --json prints every one.' in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# approved
# ---------------------------------------------------------------------------

def approved_project(approver='jane@acme.com', strength=90):
    made = project_at('approved', strength=strength,
                      config={'min_strength': 80, 'approvers': [approver]})
    signing_key(made.root, approver)
    return made


class TestTheApprovedGate:

    @pytest.mark.proof("signatures", "PROOF-39", "RULE-29", tier="integration")
    def test_a_signed_current_approval_by_an_approver_passes(self):
        made = approved_project()
        try:
            assert approve_module.main(
                ['login', 'RULE-2', '--project-root', made.root]) == 0
            code, output = run(made)
            assert code == 0, output
            assert 'verify-gate: gate = approved' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-40", "RULE-29", tier="integration")
    def test_low_risk_needs_no_human_approval(self):
        made = approved_project()
        try:
            approve_module.main(['login', 'RULE-2', '--project-root',
                                 made.root])
            code, output = run(made)
            assert code == 0, output
            assert 'login RULE-1' not in output, (
                'low risk is auto-approved by CI and never blocks the branch')
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-41", "RULE-30", tier="integration")
    def test_a_high_risk_rule_with_no_approval_fails(self):
        made = approved_project()
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not approved (1):' in output
            assert 'login RULE-2: no approval' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-42", "RULE-30", tier="integration")
    def test_a_ci_auto_approval_does_not_count_for_high_risk(self):
        made = approved_project()
        try:
            entry = made.rule('RULE-2')
            approve_module.write_approval(
                made.root, 'login', 'RULE-2', 'ci', None, None, 'approved',
                'high', entry=entry)
            commit_as_ci(made.root, 'purlin: record for abc1234')
            code, output = run(made)
            assert code == 1
            assert 'CI auto-approval' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-43", "RULE-30", tier="integration")
    def test_an_unsigned_approval_is_rejected(self):
        made = approved_project()
        try:
            entry = made.rule('RULE-2')
            approve_module.write_approval(
                made.root, 'login', 'RULE-2', 'jane@acme.com', None, None,
                'approved', 'high', entry=entry)
            git(made.root, 'add', '-A')
            git(made.root, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m',
                'chore: an approval nobody signed')
            code, output = run(made)
            assert code == 1
            assert 'the approval commit is not signed' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-44", "RULE-30", tier="integration")
    def test_the_author_of_the_test_may_not_approve_it(self):
        made = approved_project(approver='dev@example.com')
        try:
            assert approve_module.main(
                ['login', 'RULE-2', '--project-root', made.root]) == 0
            code, output = run(made)
            assert code == 1
            assert 'the approver last touched the test' in output, output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-45", "RULE-31", tier="integration")
    def test_a_stale_approval_fails_and_says_so(self):
        made = approved_project()
        try:
            approve_module.main(['login', 'RULE-2', '--project-root',
                                 made.root])
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            code, output = run(made)
            assert code == 1
            assert 'Stale' in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-46", "RULE-31", tier="integration")
    def test_an_approval_only_on_a_side_branch_is_not_on_the_branch(self):
        made = approved_project()
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
            approve_module.main(['login', 'RULE-2', '--project-root',
                                 made.root])
            code, output = run(made)
            assert code == 1
            assert 'is not on origin/main yet' in output, output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-47", "RULE-32", tier="integration")
    def test_no_approver_list_names_the_command_and_fails(self):
        made = project_at('approved')
        try:
            code, output = run(made)
            assert code == 1
            assert '→ approver list missing: run purlin:init --gate ' \
                   'approved' in output
            assert 'PASS' not in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

class TestExitCodes:

    @pytest.mark.proof("signatures", "PROOF-48", "RULE-33", tier="integration")
    def test_zero_one_and_two(self, tmp_path):
        passing = project_at('tested', by_ci=False)
        failing = Project(gate='tested')
        try:
            assert run(passing)[0] == 0
            assert run(failing)[0] == 1
        finally:
            passing.close()
            failing.close()
        out = io.StringIO()
        assert verify_gate.check(str(tmp_path), out=out) == 2
        assert 'failing closed' in out.getvalue()

    @pytest.mark.proof("signatures", "PROOF-49", "RULE-33", tier="integration")
    def test_a_directory_that_is_not_a_project_never_passes(self, tmp_path):
        out = io.StringIO()
        code = verify_gate.check(str(tmp_path / 'nothing here'), out=out)
        assert code == 2
        assert 'cannot read a Purlin project' in out.getvalue()

    @pytest.mark.proof("signatures", "PROOF-50", "RULE-34")
    def test_check_is_required_and_a_missing_directory_is_two(self):
        assert verify_gate.main([]) == 2
        assert verify_gate.main(['--check', '--project-root',
                                 '/no/such/directory']) == 2

    @pytest.mark.proof("signatures", "PROOF-51", "RULE-38", tier="integration")
    def test_the_script_runs_as_a_command(self):
        made = project_at('tested', by_ci=False)
        try:
            result = subprocess.run(
                [sys.executable, GATE_PY, '--check', '--project-root',
                 made.root], capture_output=True, text=True, timeout=120)
            assert result.returncode == 0, result.stdout + result.stderr
            assert result.stdout.startswith('verify-gate: gate = tested')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The JSON verdict
# ---------------------------------------------------------------------------

class TestTheJsonVerdict:

    @pytest.mark.proof("signatures", "PROOF-52", "RULE-35", tier="integration")
    def test_it_carries_the_verdict_and_every_rule_that_fell_short(self):
        made = Project(gate='tested')
        try:
            code, output = run(made, as_json=True)
            assert code == 1
            data = json.loads(output[output.index('{'):])
            assert data['gate'] == 'tested'
            assert data['verdict'] == 'fail'
            assert data['exit'] == 1
            assert data['rules'] == 2 and data['met'] == 0
            assert len(data['below_state']) == 2
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-53", "RULE-35", tier="integration")
    def test_a_passing_project_says_pass(self):
        made = project_at('tested', by_ci=False)
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 0 and data['verdict'] == 'pass'
            assert data['met'] == data['rules'] == 2
            assert data['below_state'] == []
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-54", "RULE-32", tier="integration")
    def test_a_missing_approver_list_says_so_in_the_json(self):
        made = project_at('approved')
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 1
            assert data['approver_list'] == 'missing'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The gate never writes
# ---------------------------------------------------------------------------

class TestTheGateNeverWrites:

    @pytest.mark.proof("signatures", "PROOF-55", "RULE-36", tier="integration")
    def test_no_file_is_created_or_changed_at_any_level(self):
        for gate in ('tested', 'recorded', 'approved'):
            made = project_at(gate, config={'approvers': ['jane@acme.com']})
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

    @pytest.mark.proof("signatures", "PROOF-56", "RULE-37")
    def test_it_reads_the_payload_and_not_a_rendered_table(self):
        with open(GATE_PY, encoding='utf-8') as handle:
            source = handle.read()
        assert 'build_payload' in source
        for glyph in ('─', '│', '┌'):
            assert glyph not in source, (
                'a gate that parsed a rendered table would move with the '
                'dashboard')

    @pytest.mark.proof("signatures", "PROOF-57", "RULE-37", tier="integration")
    def test_a_caller_may_hand_over_the_payload_it_already_built(self):
        made = project_at('tested', by_ci=False)
        try:
            payload = made.payload()
            out = io.StringIO()
            assert verify_gate.check(made.root, payload=payload, out=out) == 0
            assert 'PASS' in out.getvalue()
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-58", "RULE-38", tier="integration")
    def test_every_line_it_prints_carries_the_prefix_or_is_a_finding(self):
        made = Project(gate='tested')
        try:
            _code, output = run(made)
            heads = [line for line in output.splitlines()
                     if line and not line.startswith(' ')]
            assert heads
            for line in heads:
                assert line.startswith('verify-gate:') or line.endswith(':'), \
                    line
        finally:
            made.close()
