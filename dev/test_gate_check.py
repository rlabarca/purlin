"""Tests for `scripts/ci/gate_check.py`: what each gate lets through.

The gate decides whether every rule meets the project's gate, from the
structured payload. The payload has already worked out every rule's cells, so
this job groups the rules by the one cell that blocks each of them and prints
that cell's own reasons.
Three things it must never do: parse a rendered table, write anything, or pass
when it cannot read the evidence.

Every fixture is a throwaway project from `dev/test_signatures.py`, with its
evidence committed either by a person or under the git host's build identity,
and its signatures written by a throwaway ssh key that exists only inside the
temporary directory. Nothing here reaches a network or a git host.

What each group holds:

*passed*    a passing tagged test in a section a person or CI wrote
*strong*    an audit in the evidence, the test strength at or above the
            minimum, and an audit entry that settled where the level asks
*signed*    a current signature in a signed commit, whoever wrote it and on
            whatever branch carries it
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
from test_signatures import (EVERY_RULE_SIGNED, SPEC,  # noqa: E402
                             Project, commit_as_ci, git, signing_key)

GATE_PY = os.path.join(ROOT, 'scripts', 'ci', 'gate_check.py')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(project, as_json=False):
    """Run the gate over a project and return `(exit code, what it printed)`."""
    out = io.StringIO()
    code = gate_check.check(project.root, out=out, as_json=as_json)
    return code, out.getvalue()


def project_at(gate, strength=90, by_ci=True, config=None, audits=('RULE-2',),
               spec=SPEC):
    """A project whose rules have evidence and an audit entry, at the gate named."""
    settings = {'min_strength': 50}
    settings.update(config or {})
    made = Project(gate=gate, config=settings, spec=spec)
    made.proofs()
    made.evidence(strength=strength, runner='ci' if by_ci else 'ada',
                commit_it=False, source='ci' if by_ci else 'local')
    for rule in audits or ():
        made.audit(rule)
    if by_ci:
        commit_as_ci(made.root)
    else:
        git(made.root, 'add', '-A')
        git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
    return made


def signed_project(signer='jane@acme.com', strength=90, config=None,
                   every_rule=False):
    """A project at `signed` whose one unsigned rule is the one at `signed`.

    `RULE-1` is marked `[level: passed]` and asks for no signature, unless
    `every_rule` takes the mark away and both rules are at `signed`.
    """
    settings = {'min_strength': 80}
    settings.update(config or {})
    made = project_at('signed', strength=strength, config=settings,
                      spec=EVERY_RULE_SIGNED if every_rule else SPEC,
                      audits=('RULE-1', 'RULE-2') if every_rule
                      else ('RULE-2',))
    signing_key(made.root, signer)
    return made


# ---------------------------------------------------------------------------
# passed
# ---------------------------------------------------------------------------

class TestThePassedGate:

    # purlin: gate_check PROOF-1
    def test_a_persons_evidence_is_enough(self):
        made = project_at('passed', by_ci=False, audits=())
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'gate: gate = passed' in output
            assert 'PASS. Every rule meets passed.' in output
        finally:
            made.close()

    # purlin: gate_check PROOF-2
    def test_a_rule_with_no_evidence_is_not_passed(self):
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

    # purlin: gate_check PROOF-3
    def test_a_failing_proof_is_named_with_its_reason(self):
        made = Project(gate='passed')
        try:
            made.proofs({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            made.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            code, output = run(made)
            assert code == 1
            assert 'login RULE-1: failed' in output, output
            assert 'failing:' in output
        finally:
            made.close()

    # purlin: gate_check PROOF-4
    def test_a_rule_no_proof_names_reads_no_test_and_says_so(self):
        made = Project(spec=SPEC.replace(
            '- PROOF-1 (RULE-1): POST /login with the password "secret"; '
            'verify 200 and a token\n', ''), gate='passed')
        try:
            made.proofs()
            made.evidence()
            code, output = run(made)
            assert code == 1
            assert 'Not passed (1):' in output, output
            assert 'login RULE-1: no test (no proof written)' in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-5
    def test_no_minimum_test_strength_is_printed_under_passed(self):
        made = project_at('passed', strength=10, by_ci=False, audits=(),
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

    # purlin: gate_check PROOF-6
    def test_ci_evidence_with_a_settled_audit_passes(self):
        made = project_at('strong')
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'gate: gate = strong' in output
            assert 'minimum test strength 50.' in output
        finally:
            made.close()

    # purlin: gate_check PROOF-7
    def test_local_evidence_counts_under_strong(self):
        """An audit a person ran measures the same breaks CI measures."""
        made = project_at('strong', by_ci=False)
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'PASS. Every rule meets strong.' in output
        finally:
            made.close()

    # purlin: gate_check PROOF-7
    def test_local_evidence_counts_under_signed_too(self):
        made = project_at('signed', by_ci=False)
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not passed' not in output, output
            # The tests passed in a local section, so what is left is the
            # signature nobody has written.
            assert 'Queue (1):' in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-33
    def test_a_partial_rule_has_its_own_section(self):
        """Green on one operating system, red on another, is neither."""
        made = Project(gate='strong', config={'min_strength': 50})
        made.proofs()
        made.evidence(strength=90, runner='ci', commit_it=False, source='ci',
                    os_name='linux')
        made.evidence(statuses={'PROOF-1': 'pass', 'PROOF-2': 'fail'},
                    strength=90, runner='ci', commit_it=False, source='ci',
                    os_name='windows', at='2026-09-13T13:00:00Z')
        made.audit('RULE-2')
        commit_as_ci(made.root)
        try:
            code, output = run(made)
            assert code == 1, output
            assert 'Partial (1):' in output, output
            assert 'login RULE-2: partial' in output, output
            assert 'windows: failed' in output, output
            assert 'Not passed' not in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-8
    def test_below_the_minimum_test_strength_is_weak(self):
        made = project_at('strong', strength=40, config={'min_strength': 70})
        try:
            code, output = run(made)
            assert code == 1
            # RULE-1's level is `passed`, so its strong cell does not block.
            assert 'Weak (1):' in output, output
            assert 'login RULE-2: weak' in output, output
            assert 'strength 40% under 70%' in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-9
    def test_a_rule_with_no_audit_entry_is_not_audited(self):
        made = project_at('strong', audits=())
        try:
            code, output = run(made)
            assert code == 1
            assert 'Not audited (1):' in output, output
            assert 'login RULE-2: not audited' in output, output
            assert 'no audit has run on this code' in output
        finally:
            made.close()

    # purlin: gate_check PROOF-9
    def test_an_undecided_audit_is_weak_and_a_manual_proof_is_queued(self):
        made = project_at('strong', audits=())
        try:
            made.audit('RULE-2', settled=False)
            commit_as_ci(made.root, 'purlin: evidence at abc1234')
            code, output = run(made)
            assert code == 1
            assert 'Weak (1):' in output, output
            assert ('login RULE-2: weak (the AI audit could not decide)'
                    in output), output
            assert 'Queue (' not in output, output
            made.spec(SPEC.replace('verify 401 and the body "denied"',
                                   'verify 401 and the body "denied" @manual'))
            code, output = run(made)
            assert code == 1
            assert 'Queue (1):' in output, output
            assert 'login RULE-2: manual test' in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-10
    def test_an_observation_the_model_made_stands_against_the_rule(self):
        made = project_at('strong', audits=())
        try:
            made.audit('RULE-2',
                       findings=['PROOF-2 asserts the status but never '
                                     'the body the rule names.'])
            commit_as_ci(made.root, 'purlin: evidence at abc1234')
            code, output = run(made)
            assert code == 1
            assert 'Weak (1):' in output, output
            assert 'login RULE-2: weak' in output, output
            assert 'never the body the rule names' in output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# signed
# ---------------------------------------------------------------------------

class TestTheSignedGate:

    # purlin: gate_check PROOF-11
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

    # purlin: gate_check PROOF-12
    def test_a_rule_marked_below_signed_needs_no_signature(self):
        made = signed_project()
        try:
            sign_module.main(['login', 'RULE-2', '--project-root', made.root])
            code, output = run(made)
            assert code == 0, output
            assert 'login RULE-1' not in output, (
                'its level is passed, so it needs no signature')
        finally:
            made.close()

    # purlin: gate_check PROOF-13
    def test_a_rule_with_no_signature_is_not_signed(self):
        made = signed_project()
        try:
            code, output = run(made)
            assert code == 1
            assert 'Queue (1):' in output
            assert 'login RULE-2: unsigned' in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-14
    def test_an_unsigned_commit_does_not_carry_a_signature(self):
        made = signed_project()
        try:
            entry = made.rule('RULE-2')
            sign_module.write_signature(
                made.root, 'login', 'RULE-2', 'jane@acme.com', None,
                'signed', 'signed', entry=entry)
            git(made.root, 'add', '-A')
            git(made.root, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m',
                'chore: a signature nobody signed')
            code, output = run(made)
            assert code == 1
            assert 'the signing commit is not signed' in output, output
        finally:
            made.close()

    # purlin: gate_check PROOF-15
    def test_the_author_of_the_test_may_sign_it(self):
        made = signed_project(signer='dev@example.com')
        try:
            assert git(made.root, 'log', '-1', '--format=%ae', '--',
                       'tests/test_login.py').stdout.strip() \
                == 'dev@example.com'
            assert sign_module.main(
                ['login', 'RULE-2', '--project-root', made.root]) == 0
            code, output = run(made)
            assert code == 0, output
        finally:
            made.close()

    # purlin: gate_check PROOF-16
    def test_a_signature_the_text_moved_under_reads_stale(self):
        made = signed_project(every_rule=True)
        try:
            assert sign_module.main(
                ['login', '--project-root', made.root]) == 0
            made.spec(EVERY_RULE_SIGNED.replace(
                'return 200 with a session token',
                'return 200 with a signed session token'))
            # The spec moved, so the tests and the audit run again over it;
            # what is left is the signature the new text no longer matches.
            made.evidence(runner='ci', source='ci', commit_it=False)
            made.audit('RULE-1')
            code, output = run(made)
            assert code == 1
            assert 'login RULE-1: stale' in output, output
            assert 'hashes changed after the signature' in output
        finally:
            made.close()

    # purlin: gate_check PROOF-17
    def test_a_signature_only_on_a_side_branch_counts_there(self):
        made = signed_project()
        try:
            # `origin/HEAD` names `main`, so the project has a default branch
            # the side branch is not. A signature counts on whatever commit
            # carries it all the same.
            git(made.root, 'update-ref', 'refs/remotes/origin/main',
                git(made.root, 'rev-parse', 'HEAD').stdout.strip())
            git(made.root, 'symbolic-ref', 'refs/remotes/origin/HEAD',
                'refs/remotes/origin/main')
            git(made.root, 'checkout', '-q', '-b', 'side')
            assert sign_module.main(
                ['login', 'RULE-2', '--project-root', made.root]) == 0
            code, output = run(made)
            assert code == 0, output
        finally:
            made.close()



# ---------------------------------------------------------------------------
# The sections
# ---------------------------------------------------------------------------

class TestTheSections:

    # purlin: gate_check PROOF-19
    def test_a_section_names_twenty_rules_and_counts_the_rest(self):
        rules = ''.join('- RULE-%d: Something is true about %d [level: passed]\n'
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

    # purlin: gate_check PROOF-20
    def test_a_required_rule_is_counted_once_under_its_owner(self):
        anchor = ('# Feature: policy\n\n'
                  '> Description: The house rules.\n'
                  '> Scope: src/login.py\n\n'
                  '## Rules\n\n'
                  '- RULE-1: Every session token is 32 characters '
                  '[level: passed]\n\n'
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

    # purlin: gate_check PROOF-21
    def test_zero_one_and_two(self, tmp_path):
        passing = project_at('passed', by_ci=False, audits=())
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

    # purlin: gate_check PROOF-22
    def test_a_directory_that_is_not_a_project_never_passes(self, tmp_path):
        out = io.StringIO()
        code = gate_check.check(str(tmp_path / 'nothing here'), out=out)
        assert code == 2
        assert 'cannot read a Purlin project' in out.getvalue()

    # purlin: gate_check PROOF-23
    def test_check_is_required_and_a_missing_directory_is_two(self):
        assert gate_check.main([]) == 2
        assert gate_check.main(['--check', '--project-root',
                                '/no/such/directory']) == 2

    # purlin: gate_check PROOF-24
    def test_the_script_runs_as_a_command(self):
        made = project_at('passed', by_ci=False, audits=())
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

    # purlin: gate_check PROOF-25
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
            assert data['weak'] == [] and data['queue'] == []
            assert data['not_audited'] == []
            assert data['commit'] == made.head()
        finally:
            made.close()

    # purlin: gate_check PROOF-26
    def test_a_passing_project_says_pass(self):
        made = project_at('passed', by_ci=False, audits=())
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 0 and data['result'] == 'pass'
            assert data['met'] == data['rules'] == 2
            assert data['not_passed'] == []
        finally:
            made.close()

    # purlin: gate_check PROOF-27
    def test_a_weak_rule_lands_in_the_weak_list(self):
        made = project_at('strong', strength=40, config={'min_strength': 70})
        try:
            code, output = run(made, as_json=True)
            data = json.loads(output[output.index('{'):])
            assert code == 1
            assert len(data['weak']) == 1 and data['not_passed'] == []
            assert data['min_strength'] == 70
        finally:
            made.close()



# ---------------------------------------------------------------------------
# The gate never writes
# ---------------------------------------------------------------------------

class TestTheGateNeverWrites:

    # purlin: gate_check PROOF-29
    def test_no_file_is_created_or_changed_at_any_level(self):
        for gate in ('passed', 'strong', 'signed'):
            made = project_at(gate)
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

    # purlin: gate_check PROOF-30
    def test_it_reads_the_payload_and_not_a_rendered_table(self):
        with open(GATE_PY, encoding='utf-8') as handle:
            source = handle.read()
        assert 'build_payload' in source
        assert "rule['meets_gate']" in source or "'meets_gate'" in source
        for glyph in ('─', '│', '┌'):
            assert glyph not in source, (
                'a gate that parsed a rendered table would move with the '
                'dashboard')

    # purlin: gate_check PROOF-31
    def test_a_caller_may_hand_over_the_payload_it_already_built(self):
        made = project_at('passed', by_ci=False, audits=())
        try:
            payload = made.payload()
            out = io.StringIO()
            assert gate_check.check(made.root, payload=payload, out=out) == 0
            assert 'PASS' in out.getvalue()
        finally:
            made.close()

    # purlin: gate_check PROOF-32
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


# ---------------------------------------------------------------------------
# The six sections
# ---------------------------------------------------------------------------

# purlin: gate_check PROOF-34
def test_the_report_carries_its_six_sections_in_order():
    """One rule short at each section, and the six headings in the chain's
    own order."""
    made = project_at('signed', audits=(),
                      config={'min_strength': 80})
    try:
        code, output = run(made, as_json=True)
        assert code == 1
        data = json.loads(output[output.index('{'):])
        for key in ('not_passed', 'partial', 'weak', 'not_audited',
                    'queue', 'evidence'):
            assert key in data, sorted(data)
        titles = [title for _key, title, _cells in gate_check._SECTIONS]
        assert titles == ['Not passed', 'Partial', 'Weak', 'Not audited',
                          'Queue', 'Evidence']
        printed = [line for line in output.splitlines()
                   if any(line.startswith(title + ' (') for title in titles)]
        assert printed == ['Not audited (1):'], output
    finally:
        made.close()


# ---------------------------------------------------------------------------
# A spec that names no files
# ---------------------------------------------------------------------------

NO_SCOPE = SPEC.replace('> Scope: src/login.py\n', '')


class TestASpecThatNamesNoFiles:

    # purlin: gate_check PROOF-49
    def test_at_signed_it_is_listed_under_incomplete_and_fails(self):
        made = project_at('signed', config={'min_strength': 80}, spec=NO_SCOPE)
        try:
            code, output = run(made, as_json=True)
            assert code == 1, output
            lines = output.splitlines()
            assert 'Incomplete (1):' in lines, output
            assert '  login: no > Scope: line' in lines, output
            assert 'Queue (' not in output, output
            assert 'gate: FAIL. 1 of 2 rules do not meet signed.' in lines
            data = json.loads(output[output.index('{'):])
            assert data['incomplete'] == ['login: no > Scope: line'], data
            assert data['queue'] == [], data
        finally:
            made.close()

    # purlin: gate_check PROOF-49
    def test_below_signed_it_blocks_nothing(self):
        made = project_at('strong', spec=NO_SCOPE)
        try:
            code, output = run(made, as_json=True)
            assert code == 0, output
            assert 'Incomplete' not in output.split('{')[0], output
            data = json.loads(output[output.index('{'):])
            assert data['incomplete'] == [], data
        finally:
            made.close()
