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

*passed*    a passing marked test in a section a person or CI wrote
*strong*    an audit in the evidence, the test strength at or above the
            minimum, and an audit entry that settled where the level asks
*signed*    a current signature in a signed commit, whoever wrote it and on
            whatever branch carries it
*sections*  one section per cell a rule can be blocked at, capped at 20 rules
*exit codes* 0, 1 and 2, and never 0 when the evidence cannot be read
*json*      the same result as a machine reads it
*writes*    nothing on disk moves
*--verify*  the two questions a tag run asks of the committed evidence
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
from purlin import evidence as purlin_evidence  # noqa: E402
from sign_project import (EVERY_RULE_SIGNED, SPEC,  # noqa: E402
                          Project, commit_as_ci, git, signing_key)
from sign_project import (_Out, _read, _signed_project)  # noqa: E402
from sign_project import sign_the_queue as _sign_every_rule  # noqa: E402

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
    """A project whose rules have evidence and an audit entry, at the gate named.

    Mutation testing is on, so the test strength in the evidence is compared
    with the minimum.
    """
    settings = {'min_strength': 50, 'mutation_engine': 'auto'}
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
            # The same project with RULE-1's test failing: only RULE-2 is met.
            made.proofs({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            made.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
            code, output = run(made, as_json=True)
            assert code == 1, output
            assert 'gate: FAIL. 1 of 2 rules do not meet passed.' in output
            data = json.loads(output[output.index('{'):])
            assert data['rules'] == 2 and data['met'] == 1, data
            assert [line.split(':')[0] for line in data['not_passed']] == [
                'login RULE-1'], data
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
            assert ('  login RULE-1: failed (failing: %s, local)'
                    % purlin_evidence.host_os()) in output.splitlines(), output
            assert 'login RULE-2' not in output, output
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
            for title in ('Partial', 'Not audited', 'Queue'):
                assert title not in output, (title, output)
            assert not [line for line in output.splitlines()
                        if line.endswith('):')], output
            # The same project at `strong` prints the minimum and a section.
            made.config(gate='strong')
            code, output = run(made)
            assert code == 1, output
            assert ('gate: 2 rules across 1 features; minimum test strength '
                    '80.') in output.splitlines(), output
            assert 'Not audited (1):' in output.splitlines(), output
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

    # purlin: gate_check PROOF-8
    def test_a_strength_at_the_minimum_is_not_weak(self):
        made = project_at('strong', strength=70, config={'min_strength': 70})
        try:
            code, output = run(made)
            assert code == 0, output
            assert 'Weak' not in output, output
            assert 'PASS. Every rule meets strong.' in output, output
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
            lines = output.splitlines()
            finding = ('  login RULE-2: weak (PROOF-2 asserts the status but '
                       'never the body the rule names.)')
            assert finding in lines, output
            assert lines.index(finding) == lines.index('Weak (1):') + 1, output
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
            lines = output.splitlines()
            unsigned = '  login RULE-2: unsigned (the signing commit is not signed)'
            assert unsigned in lines and 'Queue (1):' in lines, output
            assert lines.index(unsigned) == lines.index('Queue (1):') + 1, output
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
            assert data['partial'] == [] and data['evidence'] == []
            assert data['min_strength'] is None, data
            # The same result from the command line's `--json` flag.
            result = subprocess.run(
                [sys.executable, GATE_PY, '--check', '--json',
                 '--project-root', made.root],
                capture_output=True, text=True, timeout=120)
            assert result.returncode == 1, result.stdout + result.stderr
            assert '{' in result.stdout, result.stdout
            printed = json.loads(result.stdout[result.stdout.index('{'):])
            assert printed == data, (printed, data)
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
        # Met at passed and strong; at signed RULE-2 waits on a signature.
        for gate, expected in (('passed', 0), ('strong', 0), ('signed', 1)):
            made = project_at(gate)
            try:
                before = _tree(made.root)
                inside_git = _tree(made.root, with_git=True)
                code, output = run(made)
                assert code == expected, (gate, output)
                assert _tree(made.root) == before, (
                    'a gate that can edit the evidence it grades is not a gate')
                assert _tree(made.root, with_git=True) == inside_git, (
                    'the refs, the index and the config under .git moved')
                status = git(made.root, 'status', '--porcelain').stdout
                assert status.strip() == '', status
            finally:
                made.close()

    # purlin: gate_check PROOF-29
    def test_a_folder_it_cannot_read_is_left_as_it_was(self, tmp_path):
        (tmp_path / 'notes.txt').write_text('not a project\n')
        before = _tree(str(tmp_path), with_git=True)
        out = io.StringIO()
        assert gate_check.check(str(tmp_path), out=out) == 2, out.getvalue()
        assert _tree(str(tmp_path), with_git=True) == before


def _tree(root, with_git=False):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        if not with_git:
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

    # purlin: gate_check PROOF-30
    def test_the_verdict_follows_meets_gate(self):
        """Neither rule has a test run, and each still reads `no test`."""
        made = Project(gate='passed')
        try:
            payload = made.payload()
            rules = {entry['id']: entry
                     for entry in payload['features'][0]['rules']}
            rules['RULE-2']['meets_gate'] = True
            out = io.StringIO()
            assert gate_check.check(made.root, payload=payload, out=out) == 1
            output = out.getvalue()
            assert 'gate: FAIL. 1 of 2 rules do not meet passed.' in output
            assert 'login RULE-1: no test' in output, output
            assert 'login RULE-2' not in output, output
            rules['RULE-1']['meets_gate'] = True
            out = io.StringIO()
            assert gate_check.check(made.root, payload=payload, out=out) == 0
            assert 'PASS. Every rule meets passed.' in out.getvalue()
        finally:
            made.close()

    # purlin: gate_check PROOF-31
    def test_a_caller_may_hand_over_the_payload_it_already_built(self):
        made = project_at('passed', by_ci=False, audits=())
        try:
            payload = made.payload()
            out = io.StringIO()
            assert gate_check.check(made.root, payload=payload, out=out) == 0
            assert 'PASS' in out.getvalue()
            # A handed payload reading RULE-1 short is the one the gate reads,
            # over a project whose own payload passes.
            for entry in payload['features'][0]['rules']:
                if entry['id'] == 'RULE-1':
                    entry['meets_gate'] = False
            out = io.StringIO()
            assert gate_check.check(made.root, payload=payload, out=out) == 1
            assert ('gate: FAIL. 1 of 2 rules do not meet passed.'
                    in out.getvalue()), out.getvalue()
            assert run(made)[0] == 0
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


ZETA = ('# Feature: zeta\n\n> Description: Two rules.\n'
        '> Scope: src/login.py\n\n## Rules\n\n'
        '- RULE-1: A person checks the page\n'
        '- RULE-2: Nothing tests this yet\n\n## Proof\n\n'
        '- PROOF-1 (RULE-1): A person reads the page @manual\n')


# purlin: gate_check PROOF-34
def test_rules_short_in_five_sections_print_them_in_the_chain_order(
        monkeypatch):
    """`zeta` comes after `login`, yet its `Not passed` line prints first."""
    for name in ('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI', 'GITHUB_REPOSITORY'):
        monkeypatch.delenv(name, raising=False)
    made = Project(gate='signed', config={'min_strength': 80},
                   spec=EVERY_RULE_SIGNED)
    try:
        made.proofs()
        # CI's folder, committed by a person: `--verify` names it.
        made.evidence(strength=90, runner='ci', source='ci', commit_it=False)
        made.audit('RULE-1', findings=['PROOF-1 never checks the token.'])
        made.spec(ZETA, name='zeta')
        git(made.root, 'add', '-A')
        git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
        out = io.StringIO()
        assert gate_check.check(made.root, out=out, verify_evidence=True) == 1
        lines = out.getvalue().splitlines()
        headings = [line for line in lines if line.endswith('):')]
        assert headings == ['Not passed (1):', 'Weak (1):', 'Not audited (1):',
                            'Queue (1):', 'Evidence (1):'], lines
        for line in ('  zeta RULE-2: no test (no proof written)',
                     '  login RULE-1: weak (PROOF-1 never checks the token.)',
                     '  login RULE-2: not audited (no audit has run on this '
                     'code)',
                     '  zeta RULE-1: manual test (manual proof)'):
            assert line in lines, lines
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


class TestTheTagNote:

    # purlin: gate_check PROOF-50
    def test_only_the_gate_signed_names_the_tag(self):
        note = ('gate: the gate is declared in .purlin/config.json, which an '
                'agent can edit. What stands behind it is the tag: '
                'purlin:sign writes signed/<version> only at the gate signed '
                'when every rule meets it, and this run checks the evidence '
                'against the tagged code.')
        for gate in ('signed', 'strong', 'passed'):
            made = project_at(gate)
            try:
                _code, output = run(made)
                assert 'gate: gate = %s' % gate in output, output
                if gate == 'signed':
                    assert note in output.splitlines(), output
                    lines = output.splitlines()
                    assert (lines.index(note)
                            > lines.index('gate: gate = signed')), output
                else:
                    assert 'tag' not in output.lower(), (gate, output)
                    assert 'signed/' not in output, (gate, output)
            finally:
                made.close()


# ---------------------------------------------------------------------------
# The evidence check a tag run makes
# ---------------------------------------------------------------------------

def _gate(root, verify=True):
    out = _Out()
    code = gate_check.check(root, out=out, verify_evidence=verify)
    return code, out.text()


def _assert_the_signature_is_named(made):
    """`--verify` names the one signature, and only `--verify`; the exit."""
    code, printed = _gate(made.root)
    assert 'Evidence (1):' in printed, printed
    named = [line for line in printed.splitlines()
             if 'login.signatures/RULE-2.' in line]
    assert len(named) == 1, printed
    assert named[0].endswith('what it binds is not this code'), printed
    _code, unverified = _gate(made.root, verify=False)
    assert 'Evidence' not in unverified, unverified
    return code


class TestVerify:

    # purlin: gate_check PROOF-35
    def test_a_signature_the_code_moved_under_is_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            assert _gate(made.root)[0] == 0
            made.spec(_read(made.root, 'specs/auth/login.md').replace(
                'Invalid credentials return 401',
                'Invalid credentials return 401 at once'))
            code, printed = _gate(made.root)
            assert code == 1
            assert 'Evidence (1):' in printed, printed
            assert 'what it binds is not this code' in printed, printed
            assert 'login.signatures/RULE-2.' in printed, printed
        finally:
            made.close()

    # purlin: gate_check PROOF-35
    def test_without_verify_the_section_is_not_printed(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            made.spec(_read(made.root, 'specs/auth/login.md').replace(
                'Invalid credentials return 401',
                'Invalid credentials return 401 at once'))
            _code, printed = _gate(made.root, verify=False)
            assert 'Evidence' not in printed, printed
        finally:
            made.close()

    # purlin: gate_check PROOF-35
    def test_a_signature_over_a_reworded_proof_is_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            made.spec(_read(made.root, 'specs/auth/login.md').replace(
                'POST /login with a bad password',
                'POST /login with a wrong password'))
            # Audited again as it was when signed, so only the proof differs.
            # The exit is not asserted: the spec edit also puts the evidence
            # out of date, so the gate exits 1 whatever the signature.
            made.audit('RULE-2')
            _assert_the_signature_is_named(made)
        finally:
            made.close()

    # purlin: gate_check PROOF-35
    def test_a_signature_over_a_changed_test_is_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            made.edit_test(_read(made.root, 'tests/test_login.py').replace(
                'login("ada", "wrong")', 'login("bob", "wrong")'))
            made.audit('RULE-2')
            # The changed test leaves the evidence current, so the exit is
            # the stale signature's alone.
            assert _assert_the_signature_is_named(made) == 1
        finally:
            made.close()

    # purlin: gate_check PROOF-36
    def test_a_signature_naming_a_rule_that_is_gone_is_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            spec = _read(made.root, 'specs/auth/login.md')
            lines = [line for line in spec.splitlines(True)
                     if 'RULE-2' not in line]
            made.spec(''.join(lines))
            # The exit is 1 here whatever the signature: the edit also puts
            # RULE-1 out of date, so the exit says nothing about the check.
            _code, printed = _gate(made.root)
            assert 'Evidence (1):' in printed, printed
            named = [line for line in printed.splitlines()
                     if 'login.signatures/RULE-2.' in line]
            assert len(named) == 1, printed
            assert named[0].endswith(
                'no rule login RULE-2 is in this project'), printed
            assert 'no rule login RULE-2 is in this project' in printed, \
                printed
        finally:
            made.close()

    # purlin: gate_check PROOF-37
    def test_a_fresh_audit_that_finds_more_names_the_signature(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            made.audit('RULE-2', findings=[])
            assert _gate(made.root)[0] == 0, 'the same findings bind the same'
            made.audit('RULE-2', findings=['PROOF-2 reads the status alone.'])
            code, printed = _gate(made.root)
            assert code == 1, printed
            assert 'Evidence (1):' in printed, printed
            assert 'login.signatures/RULE-2.' in printed, printed
            assert 'what it binds is not this code' in printed, printed
            _code, unverified = _gate(made.root, verify=False)
            assert 'Evidence' not in unverified, unverified
        finally:
            made.close()

    # purlin: gate_check PROOF-38
    def test_a_ci_file_a_person_committed_is_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            rel = made.evidence(strength=90, runner='ada', source='ci',
                                at='2026-09-14T12:00:00Z', commit_it=True)
            code, printed = _gate(made.root)
            assert code == 1, printed
            assert 'Evidence (1):' in printed, printed
            named = [line for line in printed.splitlines() if rel in line]
            assert len(named) == 1, printed
            assert named[0].endswith(
                "the commit that added it is not the runner's"), printed
            assert rel in printed, printed
            assert "the commit that added it is not the runner's" in printed
            # Without --verify the same file is not asked about at all.
            unverified_code, unverified = _gate(made.root, verify=False)
            assert unverified_code == 0, unverified
            assert rel not in unverified, unverified
            assert 'Evidence' not in unverified, unverified
        finally:
            made.close()

    # purlin: gate_check PROOF-38
    def test_a_ci_file_the_runner_committed_is_not_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            made.evidence(strength=90, runner='ci', source='ci',
                          at='2026-09-14T12:00:00Z', commit_it=False)
            commit_as_ci(made.root)
            _code, printed = _gate(made.root)
            assert 'Evidence' not in printed, printed
        finally:
            made.close()
