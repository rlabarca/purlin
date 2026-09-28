"""The tag `purlin:sign` writes, and the evidence check the tag run makes.

The tag is the marker of proven code: the rule, the proof, the test, the bar
and the audit are locked into a signature for every rule, and one annotated
tag says so about one commit. Nothing here pushes, and nothing here writes a
tag outside the temporary project the test made.

What each group holds:

*the tag*       the name, the message, the refusals and the line a person runs
*trust*         what `trust: remote` refuses, and what `trust: local` allows
*the audit*     the hash a signature binds over what the audit found
*--verify*      the two questions a tag run asks of the committed evidence
"""

import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'ci'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import gate_check                                            # noqa: E402
import sign as sign_module                                   # noqa: E402
from purlin import signatures as purlin_signatures           # noqa: E402
from test_signatures import (SIGNING_GATE, SPEC, Project,    # noqa: E402
                             commit_as_ci, git, signing_key, write)


def _read_spec():
    return SPEC


def _read(root, rel):
    with open(os.path.join(root, *rel.split('/')), encoding='utf-8') as handle:
        return handle.read()


class _Out(object):
    """Somewhere for the walk and the tag to print, read back as one string."""

    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass

    def text(self):
        return ''.join(self.lines)


def _signed_project(version='2.1.0', trust='local', key=True):
    """A project at `signed` whose two rules both have what they need.

    `key` writes the signer's own key over the allowed-signers file CI's
    commit left, which is what lets a signature this project writes count.
    A case that signs nothing does not need it, and asking twice would have
    `ssh-keygen` stop for an overwrite nobody is there to answer.
    """
    made = Project(gate=SIGNING_GATE,
                   config={'sign_at': 'strong', 'min_strength': 50,
                           'trust': trust})
    made.proofs()
    made.evidence(strength=90, runner='ci', commit_it=False, source='ci')
    made.audit('RULE-2')
    write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_as_ci(made.root)
    if key:
        signing_key(made.root)
    return made


def _sign_every_rule(made):
    """Sign whatever the sign list holds, as the listed signer, and commit."""
    payload = made.payload()
    targets = sign_module.signable(payload)
    if targets:
        sign_module.sign_and_commit(made.root, targets, 'jane@acme.com',
                                    payload=payload)
    return targets


# ---------------------------------------------------------------------------
# The tag
# ---------------------------------------------------------------------------

class TestTheTag:

    @pytest.mark.proof("signatures", "PROOF-67", "RULE-45")
    def test_a_walk_with_nothing_left_writes_the_tag(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            out = _Out()
            result = sign_module.walk(made.root, out=out,
                                      signer_email='jane@acme.com')
            printed = out.text()
            assert 'Review: 0 rules. Sign: 0 rules.' in printed, printed
            assert result['tag'] == 'signed/2.1.0', printed
            message = git(made.root, 'tag', '-n99', '-l',
                          'signed/2.1.0').stdout
            assert 'Every rule meets the gate signed.' in message, message
            assert made.head()[:7] in message or 'Commit:' in message, message
            assert 'Run: git push origin signed/2.1.0' in printed, printed
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-67", "RULE-45")
    def test_the_version_comes_from_the_config_with_no_version_file(self):
        made = _signed_project()
        try:
            os.remove(os.path.join(made.root, 'VERSION'))
            made.config(version='0.9.9')
            assert sign_module.tag_name(made.root) == 'signed/0.9.9'
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-68", "RULE-46")
    def test_no_tag_while_a_rule_falls_short(self):
        made = _signed_project()
        try:
            out = _Out()
            sign_module.tag_if_met(made.root, out)
            printed = out.text()
            assert printed.startswith('No tag: 1 of 2 rules do not meet the '
                                      'gate signed.'), printed
            assert git(made.root, 'tag', '-l').stdout.strip() == ''
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-68", "RULE-46")
    def test_release_names_another_tag_and_a_second_one_is_refused(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            first = _Out()
            assert sign_module.tag_if_met(made.root, first,
                                          release='beta') == 'signed/beta'
            second = _Out()
            assert sign_module.tag_if_met(made.root, second,
                                          release='beta') is None
            assert 'No tag: signed/beta is already written.' in second.text()
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-67", "RULE-45")
    def test_the_tag_is_written_and_nothing_is_pushed(self):
        """The last line names the push; the command makes none."""
        made = _signed_project()
        try:
            _sign_every_rule(made)
            out = _Out()
            sign_module.tag_if_met(made.root, out)
            # No remote exists, so a push would have failed loudly; the point
            # is that the command never reaches for one.
            assert git(made.root, 'remote').stdout.strip() == ''
            assert 'Run: git push origin signed/2.1.0' in out.text()
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------

class TestTrust:

    @pytest.mark.proof("signatures", "PROOF-69", "RULE-47")
    def test_remote_refuses_a_rule_with_no_ci_run_for_this_code(self, capsys):
        made = Project(gate=SIGNING_GATE,
                       config={'min_strength': 50, 'trust': 'remote'})
        try:
            made.proofs()
            made.evidence(strength=90, runner='ada', source='local')
            made.audit('RULE-2')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'purlin: evidence')
            payload = made.payload()
            refused = sign_module.untrusted(payload, [('login', 'RULE-2')])
            assert refused == [('login', 'RULE-2')], refused
            assert sign_module._allowed(payload, [('login', 'RULE-2')]) == []
            assert ('sign: login RULE-2 has no ci test run for this code; run '
                    'purlin:test --remote first') in capsys.readouterr().out
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-69", "RULE-47")
    def test_a_ci_run_out_of_date_for_this_code_is_refused_too(self):
        made = _signed_project(trust='remote', key=False)
        try:
            write(os.path.join(made.root, 'src', 'login.py'),
                  'def login(user, password):\n    return 401\n')
            payload = made.payload()
            assert sign_module.untrusted(payload, [('login', 'RULE-2')]) == [
                ('login', 'RULE-2')]
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-69", "RULE-47")
    def test_a_rule_whose_proofs_are_all_manual_is_not_refused(self):
        spec = _read_spec().replace('verify 401 and the body "denied"',
                                    'verify 401 and the body "denied" @manual')
        made = Project(spec=spec, gate=SIGNING_GATE,
                       config={'trust': 'remote'})
        try:
            made.proofs({'PROOF-1': 'pass'})
            made.evidence({'PROOF-1': 'pass'}, runner='ada', source='local')
            payload = made.payload()
            assert sign_module.untrusted(payload, [('login', 'RULE-2')]) == []
            assert sign_module.untrusted(payload, [('login', 'RULE-1')]) == [
                ('login', 'RULE-1')]
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-69", "RULE-47")
    def test_a_ci_run_for_this_commit_is_enough(self):
        made = _signed_project(trust='remote', key=False)
        try:
            payload = made.payload()
            assert sign_module.untrusted(payload, [('login', 'RULE-2')]) == []
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-69", "RULE-47")
    def test_local_asks_nothing_of_the_source(self):
        made = Project(gate=SIGNING_GATE,
                       config={'trust': 'local'})
        try:
            made.proofs()
            made.evidence(strength=90, runner='ada', source='local')
            payload = made.payload()
            assert sign_module.untrusted(payload, [('login', 'RULE-2')]) == []
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What the audit hash binds
# ---------------------------------------------------------------------------

class TestTheAuditHash:

    @pytest.mark.proof("signatures", "PROOF-64", "RULE-43")
    def test_it_reads_the_evidence_and_nothing_that_moves_on_its_own(self):
        one = {'verdict': 'strong', 'findings': [], 'rule_hash': 'r',
               'at': '2026-09-13T12:00:00Z', 'commit': 'a' * 40,
               'path': '.purlin/evidence/local/login.json'}
        same = dict(one, at='2026-09-27T09:00:00Z', commit='b' * 40,
                    path='.purlin/evidence/ci/login.json')
        assert purlin_signatures.audit_hash(one, 90) == \
            purlin_signatures.audit_hash(same, 90)

        found = dict(one, findings=['PROOF-2 reads the status alone.'])
        found['verdict'] = 'weak'
        assert purlin_signatures.audit_hash(found, 90) != \
            purlin_signatures.audit_hash(one, 90)

        undecided = dict(one)
        undecided['verdict'] = 'undecided'
        assert purlin_signatures.audit_hash(undecided, 90) != \
            purlin_signatures.audit_hash(one, 90)
        assert purlin_signatures.audit_hash(one, 70) != \
            purlin_signatures.audit_hash(one, 90)

    @pytest.mark.proof("signatures", "PROOF-64", "RULE-43")
    def test_no_entry_hashes_the_empty_string(self):
        import hashlib
        assert purlin_signatures.audit_hash(None) == \
            hashlib.sha256(b'').hexdigest()

    @pytest.mark.proof("signatures", "PROOF-64", "RULE-43")
    def test_the_order_of_the_findings_does_not_move_it(self):
        one = {'verdict': 'weak', 'findings': ['b.', 'a.']}
        other = {'verdict': 'weak', 'findings': ['a.', 'b.']}
        assert purlin_signatures.audit_hash(one) == \
            purlin_signatures.audit_hash(other)

    @pytest.mark.proof("signatures", "PROOF-65", "RULE-43")
    def test_a_re_audit_that_observes_something_stales_the_signature(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            assert made.rule('RULE-2')['cells']['signed']['word'] == 'signed'
            made.audit('RULE-2', findings=['PROOF-2 reads the status alone.'])
            cell = made.rule('RULE-2')['cells']['signed']
            assert cell['word'] == 'stale', cell
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-66", "RULE-44")
    def test_a_hold_is_not_bound_to_the_audit(self):
        made = _signed_project()
        try:
            sign_module.hold_and_commit(made.root, [('login', 'RULE-2')],
                                        'jane@acme.com', 'no expired token')
            assert made.rule('RULE-2')['cells']['strong']['word'] == 'held'
            made.audit('RULE-2', findings=['PROOF-2 reads the status alone.'])
            cell = made.rule('RULE-2')['cells']['strong']
            assert cell['word'] == 'held', cell
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The evidence check a tag run makes
# ---------------------------------------------------------------------------

def _gate(root, verify=True):
    out = _Out()
    code = gate_check.check(root, out=out, verify_evidence=verify)
    return code, out.text()


class TestVerify:

    @pytest.mark.proof("gate_check", "PROOF-35", "RULE-15")
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

    @pytest.mark.proof("gate_check", "PROOF-35", "RULE-15")
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

    @pytest.mark.proof("gate_check", "PROOF-36", "RULE-15")
    def test_a_hold_naming_a_rule_that_is_gone_is_named(self):
        made = _signed_project()
        try:
            sign_module.hold_and_commit(made.root, [('login', 'RULE-2')],
                                        'jane@acme.com', 'no expired token')
            spec = _read(made.root, 'specs/auth/login.md')
            lines = [line for line in spec.splitlines(True)
                     if 'RULE-2' not in line]
            made.spec(''.join(lines))
            _code, printed = _gate(made.root)
            assert 'no rule login RULE-2 is in this project' in printed, \
                printed
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-38", "RULE-16")
    def test_a_ci_file_a_person_committed_is_named(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            rel = made.evidence(strength=90, runner='ada', source='ci',
                                at='2026-09-14T12:00:00Z', commit_it=True)
            _code, printed = _gate(made.root)
            assert rel in printed, printed
            assert "the commit that added it is not the runner's" in printed
        finally:
            made.close()

    @pytest.mark.proof("gate_check", "PROOF-38", "RULE-16")
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
