"""The tag `purlin:sign` writes.

The tag is the marker of proven code: the rule, the proof, the test and the
audit are locked into a signature for every rule whose level asks for one,
and one signed tag says so about one commit. Nothing here pushes, and nothing here writes a
tag outside the temporary project the test made.

What each group holds:

*the tag*       the name, the message, the signature, the refusals and the
                line a person runs
*trust*         what `trust: remote` refuses, and what `trust: local` allows
*the audit*     the hash a signature binds over what the audit found
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

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
                   config={'min_strength': 50, 'trust': trust})
    made.proofs()
    made.evidence(strength=90, runner='ci', commit_it=False, source='ci')
    made.audit('RULE-2')
    write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_as_ci(made.root)
    if key:
        signing_key(made.root)
    return made


def _audit_again_later(made, rule, at='2026-09-27T09:00:00Z'):
    """The same audit entry written again, with a new `at` and this `commit`."""
    rel = made.audit(rule)
    path = os.path.join(made.root, *rel.split('/'))
    data = json.loads(_read(made.root, rel))
    entry = data['audit']['rules'][rule]
    assert entry['commit'] == made.head() and entry['verdict'] == 'strong'
    entry['at'] = at
    write(path, json.dumps(data, indent=2, sort_keys=True))
    return entry


def _sign_every_rule(made):
    """Sign whatever the queue holds, as the signer, and commit."""
    payload = made.payload()
    targets = sign_module.queued(payload)
    if targets:
        sign_module.sign_and_commit(made.root, targets, 'jane@acme.com',
                                    payload=payload)
    return targets


# ---------------------------------------------------------------------------
# The tag
# ---------------------------------------------------------------------------

class TestTheTag:

    # purlin: signatures PROOF-67
    def test_a_walk_with_nothing_left_writes_the_tag(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            started_at = made.head()
            out = _Out()
            result = sign_module.walk(made.root, out=out,
                                      signer_email='jane@acme.com')
            printed = out.text()
            assert ('Queue: 0 rules. 0 hand checks, 0 signatures.'
                    in printed), printed
            assert result['tag'] == 'signed/2.1.0', printed
            # A signed tag, not an annotated one: its object carries the
            # signature, and git verifies it against the signer's key.
            body = git(made.root, 'cat-file', 'tag', 'signed/2.1.0').stdout
            assert '-----BEGIN SSH SIGNATURE-----' in body, body
            assert git(made.root, 'tag', '-v', 'signed/2.1.0').returncode == 0
            message = git(made.root, 'tag', '-n99', '-l',
                          'signed/2.1.0').stdout
            assert 'Every rule meets the gate signed.' in message, message
            assert made.head()[:7] in message or 'Commit:' in message, message
            # The message names in full the commit the walk began at, which
            # is the one the tagged commit, carrying the package, sits on.
            tagged = git(made.root, 'rev-parse',
                         'signed/2.1.0^{commit}').stdout.strip()
            assert git(made.root, 'rev-parse',
                       tagged + '^').stdout.strip() == started_at
            lines = [line.strip() for line in message.splitlines()]
            assert 'Commit: %s' % started_at in lines, message
            assert 'Gate: signed' in lines, message
            assert 'Run: git push origin signed/2.1.0' in printed, printed
            assert printed.splitlines()[-1] == (
                '%s Run: git push origin signed/2.1.0'
                % sign_module.ARROW), printed
        finally:
            made.close()

    # purlin: signatures PROOF-74
    def test_no_tag_over_evidence_that_is_not_committed(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            made.evidence(strength=90, runner='ci', source='ci',
                          commit_it=False, at='2026-09-14T12:00:00Z')
            out = _Out()
            assert sign_module.tag_if_met(made.root, out) is None
            assert out.text().splitlines() == [
                'sign: login has evidence that is not committed. Run: '
                'purlin:test --commit'], out.text()
            assert git(made.root, 'tag', '-l').stdout.strip() == ''
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
            again = _Out()
            assert sign_module.tag_if_met(made.root, again) == 'signed/2.1.0', \
                again.text()
        finally:
            made.close()

    # purlin: signatures PROOF-67
    def test_the_version_comes_from_the_config_with_no_version_file(self):
        made = _signed_project()
        try:
            os.remove(os.path.join(made.root, 'VERSION'))
            made.config(version='0.9.9')
            assert sign_module.tag_name(made.root) == 'signed/0.9.9'
        finally:
            made.close()

    # purlin: signatures PROOF-68
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

    # purlin: signatures PROOF-68
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

    # purlin: signatures PROOF-67
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

    # purlin: signatures PROOF-67
    def test_a_remote_is_left_as_it_was(self):
        """With an `origin` to push to, the tag is written here alone."""
        made = _signed_project()
        remote = tempfile.mkdtemp()
        try:
            git(remote, 'init', '-q', '--bare')
            git(made.root, 'remote', 'add', 'origin', remote)
            _sign_every_rule(made)
            assert git(made.root, 'push', '-q', 'origin',
                       'main').returncode == 0
            before = git(made.root, 'ls-remote', 'origin').stdout
            assert 'refs/heads/main' in before, before
            out = _Out()
            assert sign_module.tag_if_met(made.root, out) == 'signed/2.1.0', \
                out.text()
            assert git(made.root, 'tag', '-l').stdout.split() == [
                'signed/2.1.0']
            after = git(made.root, 'ls-remote', 'origin').stdout
            assert after == before, after
            assert 'signed/2.1.0' not in after, after
            assert 'Run: git push origin signed/2.1.0' in out.text()
        finally:
            shutil.rmtree(remote, ignore_errors=True)
            made.close()

    # purlin: signatures PROOF-68
    def test_the_release_option_names_the_tag(self, capsys):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            argv = ['--release', 'beta', '--project-root', made.root]
            assert sign_module.main(argv) == sign_module.EXIT_OK
            printed = capsys.readouterr().out
            assert git(made.root, 'tag', '-l').stdout.split() == [
                'signed/beta'], printed
            assert git(made.root, 'tag', '-v', 'signed/beta').returncode == 0
            assert sign_module.main(argv) == sign_module.EXIT_OK
            again = capsys.readouterr().out
            assert 'No tag: signed/beta is already written.' in again, again
            assert git(made.root, 'tag', '-l').stdout.split() == [
                'signed/beta']
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------

class TestTrust:

    # purlin: signatures PROOF-69
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

    # purlin: signatures PROOF-69
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

    # purlin: signatures PROOF-69
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

    # purlin: signatures PROOF-69
    def test_a_ci_run_for_this_commit_is_enough(self):
        made = _signed_project(trust='remote', key=False)
        try:
            payload = made.payload()
            assert sign_module.untrusted(payload, [('login', 'RULE-2')]) == []
        finally:
            made.close()

    # purlin: signatures PROOF-69
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

    # purlin: signatures PROOF-64
    def test_it_reads_the_evidence_and_nothing_that_moves_on_its_own(self):
        one = {'verdict': 'strong', 'findings': [], 'rule_hash': 'r',
               'at': '2026-09-13T12:00:00Z', 'commit': 'a' * 40,
               'path': '.purlin/evidence/local/login.json'}
        same = dict(one, at='2026-09-27T09:00:00Z', commit='b' * 40,
                    path='.purlin/evidence/ci/login.json',
                    model='claude-opus-4-1-20250805', criteria='c' * 64)
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

    # purlin: signatures PROOF-64
    def test_no_entry_hashes_the_empty_string(self):
        import hashlib
        assert purlin_signatures.audit_hash(None) == \
            hashlib.sha256(b'').hexdigest()

    # purlin: signatures PROOF-64
    def test_the_order_of_the_findings_does_not_move_it(self):
        one = {'verdict': 'weak', 'findings': ['b.', 'a.']}
        other = {'verdict': 'weak', 'findings': ['a.', 'b.']}
        assert purlin_signatures.audit_hash(one) == \
            purlin_signatures.audit_hash(other)

    # purlin: signatures PROOF-65
    def test_a_re_audit_that_observes_something_stales_the_signature(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            assert made.rule('RULE-2')['cells']['signed']['word'] == 'signed'
            # The same audit again, at a later time and over the signature's
            # own commit: what it observed is unchanged, so nothing stales.
            _audit_again_later(made, 'RULE-2')
            cell = made.rule('RULE-2')['cells']['signed']
            assert cell['word'] == 'signed', cell
            made.audit('RULE-2', findings=['PROOF-2 reads the status alone.'])
            cell = made.rule('RULE-2')['cells']['signed']
            assert cell['word'] == 'stale', cell
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What holds the tag back, by name
# ---------------------------------------------------------------------------

NO_SCOPE = _read_spec().replace('> Scope: src/login.py\n', '')


def _unscoped_project(gate):
    made = Project(gate=gate, spec=NO_SCOPE.replace(' [level: passed]', ''),
                   config={'min_strength': 50})
    made.proofs()
    made.evidence(strength=90, runner='ci', commit_it=False, source='ci')
    made.audit('RULE-1')
    made.audit('RULE-2')
    write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
    commit_as_ci(made.root)
    signing_key(made.root)
    return made


class TestWhatHoldsTheTagBack:

    # purlin: signatures PROOF-76
    def test_at_signed_a_spec_that_names_no_files_is_refused(self, capsys):
        made = _unscoped_project('signed')
        try:
            assert sign_module.queued(made.payload()) == []
            code = sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root])
            printed = capsys.readouterr().out
            assert code == sign_module.EXIT_NOTHING, printed
            assert ('sign: login names no files in > Scope:, so a signature '
                    'cannot be tied to the code it governs. Run: purlin:spec '
                    'login') in printed.splitlines(), printed
            assert made.signatures() == []
            out = _Out()
            assert sign_module.tag_if_met(made.root, out) is None
            assert out.text().splitlines() == [
                'No tag: login names no files in > Scope:, so a signature '
                'cannot be tied to the code it governs.',
                'No tag: 2 of 2 rules do not meet the gate signed.'], \
                out.text()
            assert git(made.root, 'tag', '-l').stdout.strip() == ''
        finally:
            made.close()

    # purlin: signatures PROOF-76
    def test_at_strong_it_is_signed_like_any_other(self, capsys):
        made = _unscoped_project('strong')
        try:
            code = sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root])
            printed = capsys.readouterr().out
            assert code == sign_module.EXIT_OK, printed
            assert 'names no files' not in printed, printed
            assert len(made.signatures()) == 1, printed
        finally:
            made.close()

    # purlin: signatures PROOF-77
    def test_the_refusal_names_a_feature_whose_evidence_is_out_of_date(self):
        made = _signed_project()
        try:
            _sign_every_rule(made)
            section = next(iter(json.loads(_read(
                made.root, '.purlin/evidence/ci/login.json'))[
                    'platforms'].values()))
            write(os.path.join(made.root, 'src', 'login.py'),
                  'def login(user, password):\n    return 401\n')
            git(made.root, 'commit', '-q', '-am', 'change the code')
            out = _Out()
            assert sign_module.tag_if_met(made.root, out) is None
            assert out.text().splitlines() == [
                'No tag: login is out of date (code changed since %s).'
                % section['commit'][:7],
                'No tag: 2 of 2 rules do not meet the gate signed.'], \
                out.text()
            assert git(made.root, 'tag', '-l').stdout.strip() == ''
        finally:
            made.close()
