"""The evidence package `purlin:export` writes.

Every project here is a throwaway git repository in a temporary directory,
with a spec, a test file, evidence, audit entries and, where a signature is
involved, a signing key that exists nowhere but that directory. The package
command runs as a separate process, as a person runs it.

What each group holds:

*the file*        where it is written, its name, what it prints, and that it
                  commits nothing unless asked
*the state*       `work in progress`, `gate <gate> met` and `signed`, with the
                  failure cases: no evidence, no test, no audit, no signature
*the content*     what one rule carries, and what it never carries
*what git holds*  evidence written and not committed is left out and named
*the bytes*       the same tag gives the same bytes, from a second clone too
*the fingerprint* `--check` on a package as written and on one edited after

The projects, the fixtures `signed` and `tagged`, and the tests of the
package `purlin:sign` commits with the tag are in `dev/test_signatures.py`.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import sign as sign_module                                    # noqa: E402
from purlin import PURLIN_VERSION                             # noqa: E402
from test_signatures import (CRITERIA, MODEL, SPEC,           # noqa: E402
                             TEST_FILE, Project, git, sign_the_queue,
                             signed, signed_project, status, tagged,
                             write)

PACKAGE_PY = os.path.join(ROOT, 'scripts', 'export', 'package.py')

TOP_LEVEL = ['schema', 'state', 'not_for_approval', 'rules_meeting_gate',
             'rules_short_of_gate', 'purlin_version', 'project', 'version',
             'tag', 'commit', 'gate', 'trust', 'mutation_engine',
             'min_strength', 'features', 'warnings', 'fingerprint']

UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

# A rule with a requirement's number in its words and no proof at all.
SPEC_WITH_A_THIRD_RULE = SPEC.replace(
    '\n\n## Proof',
    '\n- RULE-3: A locked account returns 423 (URS-042)\n\n## Proof')


def export(root, *args):
    """Run the package command in `root`. `(exit code, printed lines)`."""
    done = subprocess.run([sys.executable, PACKAGE_PY, '--project-root', root]
                          + list(args), capture_output=True, text=True,
                          cwd=root)
    return done.returncode, (done.stdout + done.stderr).splitlines()


def read_bytes(root, rel):
    with open(os.path.join(root, *rel.split('/')), 'rb') as handle:
        return handle.read()


def read_package(root, version='2.1.0'):
    return json.loads(read_bytes(
        root, '.purlin/evidence/package/%s.json' % version).decode('utf-8'))


def fingerprint_by_hand(data):
    """sha256 of a package's bytes with the top-level `fingerprint` emptied.

    Worked on the file's text, not through the package command: the one
    top-level `"fingerprint": "<hex>"` becomes `"fingerprint": ""`.
    """
    blanked, count = re.subn(rb'\n  "fingerprint": "[0-9a-f]*"\n}\n$',
                             b'\n  "fingerprint": ""\n}\n', data)
    assert count == 1, data[-200:]
    return hashlib.sha256(blanked).hexdigest()


def rule_of(package, rule_id, feature='login'):
    entry = next(f for f in package['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

class TestTheFile:

    # purlin: package PROOF-1
    def test_it_writes_the_version_file_prints_the_state_and_commits_nothing(
            self, signed):
        head = signed.head()
        code, lines = export(signed.root)
        assert code == 0, lines
        assert lines[0] == (
            'Evidence package written to .purlin/evidence/package/2.1.0.json. '
            'State: work in progress, 1 of 2 rules meet the gate signed. '
            'Not for approval.'), lines
        assert signed.head() == head
        assert status(signed.root) == (
            '?? .purlin/evidence/package/2.1.0.json\n')
        assert len(git(signed.root, 'worktree', 'list').stdout
                   .splitlines()) == 1

    # purlin: package PROOF-2
    def test_release_names_the_version_the_file_and_the_tag(self, signed):
        code, lines = export(signed.root, '--release', 'beta')
        assert code == 0, lines
        assert lines[0].startswith('Evidence package written to '
                                   '.purlin/evidence/package/beta.json.'), lines
        package = read_package(signed.root, 'beta')
        assert (package['version'], package['tag']) == ('beta', 'signed/beta')
        assert not os.path.exists(os.path.join(
            signed.root, '.purlin', 'evidence', 'package', '2.1.0.json'))

    # purlin: package PROOF-3
    def test_the_top_level_keys_come_in_the_format_order(self, signed):
        export(signed.root)
        package = read_package(signed.root)
        assert list(package) == TOP_LEVEL
        assert package['schema'] == 'purlin-package/1'
        assert package['purlin_version'] == PURLIN_VERSION
        assert (package['project'], package['gate'], package['trust'],
                package['mutation_engine'], package['min_strength']) == (
                    'proj', 'signed', 'local', 'none', 50)
        assert package['commit'] == signed.head()

    # purlin: package PROOF-10
    def test_commit_commits_the_file_as_evidence_and_once(self, signed):
        head = signed.head()
        code, lines = export(signed.root, '--commit')
        assert code == 0, lines
        assert lines[-1] == 'Package committed.', lines
        assert git(signed.root, 'log', '-1', '--format=%s').stdout.strip() == \
            'purlin: evidence at %s' % head[:7]
        assert status(signed.root) == ''
        committed = signed.head()
        code, lines = export(signed.root, '--commit')
        assert lines[-1] == 'Package unchanged.', lines
        assert signed.head() == committed
        assert read_package(signed.root)['commit'] == head

    # purlin: package PROOF-10
    def test_commit_leaves_a_change_staged_elsewhere_out(self, signed):
        write(os.path.join(signed.root, 'src', 'login.py'), '# edited\n')
        git(signed.root, 'add', 'src/login.py')
        code, lines = export(signed.root, '--commit')
        assert code == 0, lines
        assert git(signed.root, 'show', '--name-only', '--format=',
                   'HEAD').stdout.split() == [
            '.purlin/evidence/package/2.1.0.json']
        assert status(signed.root) == 'M  src/login.py\n'


# ---------------------------------------------------------------------------
# The state
# ---------------------------------------------------------------------------

class TestTheState:

    # purlin: package PROOF-4
    def test_a_project_with_no_evidence_is_work_in_progress(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'VERSION'), '1.0.0\n')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'chore: version')
            code, lines = export(made.root)
            assert code == 0, lines
            assert lines[0].endswith('State: work in progress, 0 of 2 rules '
                                     'meet the gate passed. '
                                     'Not for approval.'), lines
            package = read_package(made.root, '1.0.0')
            assert (package['state'], package['not_for_approval'],
                    package['rules_meeting_gate'],
                    package['rules_short_of_gate']) == (
                        'work in progress', True, 0, 2)
            assert rule_of(package, 'RULE-1')['results'] == []
            assert rule_of(package, 'RULE-1')['statuses']['passed'][
                'word'] == 'no test'
        finally:
            made.close()

    # purlin: package PROOF-5
    def test_a_rule_with_no_test_holds_the_state(self):
        made = signed_project(spec=SPEC_WITH_A_THIRD_RULE)
        try:
            sign_the_queue(made)
            export(made.root)
            package = read_package(made.root)
            third = rule_of(package, 'RULE-3')
            assert third['text'] == 'A locked account returns 423 (URS-042)'
            assert (third['proofs'], third['tests']) == ([], [])
            assert [r['result'] for r in third['results']] == ['no test']
            assert third['meets_gate'] is False
            assert package['state'] == 'work in progress'
            assert package['rules_short_of_gate'] == 1
        finally:
            made.close()

    # purlin: package PROOF-6
    def test_a_rule_with_no_audit_holds_the_state(self):
        made = Project(gate='strong')
        try:
            made.proofs()
            made.evidence()
            export(made.root)
            package = read_package(made.root, 'unversioned')
            second = rule_of(package, 'RULE-2')
            assert second['audit'] is None
            assert second['statuses']['strong']['word'] == 'not audited'
            assert second['meets_gate'] is False
            assert package['state'] == 'work in progress'
            assert package['not_for_approval'] is True
        finally:
            made.close()

    # purlin: package PROOF-7
    def test_an_unsigned_rule_holds_the_state(self, signed):
        export(signed.root)
        package = read_package(signed.root)
        second = rule_of(package, 'RULE-2')
        assert second['signatures'] == []
        assert second['statuses']['signed']['word'] == 'unsigned'
        assert (package['state'], package['rules_meeting_gate'],
                package['rules_short_of_gate']) == ('work in progress', 1, 1)

    # purlin: package PROOF-8
    def test_a_met_gate_without_the_tag_is_still_not_for_approval(self):
        made = Project()
        try:
            made.proofs()
            made.evidence()
            code, lines = export(made.root)
            assert lines[0].endswith('State: gate passed met, 2 of 2 rules '
                                     'meet the gate passed. '
                                     'Not for approval.'), lines
            package = read_package(made.root, 'unversioned')
            assert (package['state'], package['not_for_approval']) == (
                'gate passed met', True)
        finally:
            made.close()
        made = signed_project()
        try:
            sign_the_queue(made)
            export(made.root)
            package = read_package(made.root)
            assert (package['state'], package['not_for_approval']) == (
                'gate signed met', True)
        finally:
            made.close()


    # purlin: package PROOF-19
    def test_below_signed_a_tag_on_the_commit_never_reads_signed(self):
        made = signed_project(gate='strong')
        try:
            git(made.root, 'tag', '-a', 'signed/2.1.0', '-m', 'by hand')
            code, lines = export(made.root)
            assert code == 0, lines
            assert lines[0].endswith('State: gate strong met, 2 of 2 rules '
                                     'meet the gate strong. '
                                     'Not for approval.'), lines
            package = read_package(made.root)
            assert (package['state'], package['not_for_approval']) == (
                'gate strong met', True)
        finally:
            made.close()
        made = signed_project(gate='passed')
        try:
            git(made.root, 'tag', '-a', 'signed/2.1.0', '-m', 'by hand')
            code, lines = export(made.root)
            assert code == 0, lines
            assert lines[0].endswith('State: gate passed met, 2 of 2 rules '
                                     'meet the gate passed. '
                                     'Not for approval.'), lines
            package = read_package(made.root)
            assert (package['state'], package['not_for_approval']) == (
                'gate passed met', True)
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The content
# ---------------------------------------------------------------------------

class TestTheContent:

    # purlin: package PROOF-9
    def test_one_rule_carries_its_words_proofs_tests_results_audit_and_signature(
            self, tagged):
        package = read_package(tagged.root)
        rule = rule_of(package, 'RULE-2')
        print(json.dumps(rule, indent=2, sort_keys=True))
        assert rule['text'] == ('Invalid credentials return 401 and the body '
                                '"denied"')
        assert (rule['level'], rule['level_marked']) == ('signed', False)
        assert (rule_of(package, 'RULE-1')['level'],
                rule_of(package, 'RULE-1')['level_marked']) == ('passed', True)
        assert rule['proofs'] == [{
            'id': 'PROOF-2', 'manual': False, 'env': None,
            'text': 'POST /login with a bad password; verify 401 and the body '
                    '"denied"'}]
        assert rule['tests'] == [{'proof': 'PROOF-2',
                                  'file': 'tests/test_login.py',
                                  'name': 'test_a_bad_password_is_denied'}]
        [result] = rule['results']
        assert (result['source'], result['result'], result['runner'],
                result['at'], result['current']) == (
                    'ci', 'passed', 'ci', '2026-09-13T12:00:00Z', True)
        assert result['os'] in ('windows', 'macos', 'linux')
        assert re.match(r'^[0-9a-f]{40}$', result['commit'])
        assert result['commit'] == tagged.tests_ran_at
        audit = rule['audit']
        assert (audit['verdict'], audit['findings'], audit['strength'],
                audit['model'], audit['criteria'], audit['at']) == (
                    'strong', [], 90, MODEL, CRITERIA, '2026-09-13T12:05:00Z')
        [signature] = rule['signatures']
        assert signature['signer'] == 'jane@acme.com'
        assert signature['commit_verifies'] is True
        assert signature['note'] is None
        assert signature['os'] in ('windows', 'macos', 'linux')
        assert signature['machine']
        assert set(signature['locked']) == {
            'triple', 'rule_hash', 'proof_hash', 'test_hash',
            'test_hash_kind', 'audit_hash'}
        now = tagged.rule('RULE-2')
        assert signature['locked'] == dict(
            {key: now[key] for key in ('rule_hash', 'proof_hash', 'test_hash',
                                       'test_hash_kind', 'audit_hash')},
            triple=sign_module.triple_for(now)[:16])
        assert UTC.match(signature['at']), signature['at']
        assert rule['statuses']['signed'] == {'word': 'signed',
                                              'reasons': ['by jane@acme.com']}
        assert rule['meets_gate'] is True

    # purlin: package PROOF-20
    def test_a_rule_carries_only_the_statuses_its_level_asks_for(self,
                                                                  tagged):
        package = read_package(tagged.root)
        lower = rule_of(package, 'RULE-1')
        assert lower['level'] == 'passed', lower
        assert list(lower['statuses']) == ['passed'], lower['statuses']
        assert lower['statuses']['passed']['word'] == 'passed', lower
        assert sorted(rule_of(package, 'RULE-2')['statuses']) == [
            'passed', 'signed', 'strong']
        made = signed_project(spec=SPEC.replace('[level: passed]',
                                                '[level: strong]'))
        try:
            export(made.root)
            middle = rule_of(read_package(made.root), 'RULE-1')
            assert middle['level'] == 'strong', middle
            assert sorted(middle['statuses']) == ['passed', 'strong'], (
                middle['statuses'])
            assert None not in middle['statuses'].values(), middle
        finally:
            made.close()

    # purlin: package PROOF-18
    def test_a_rule_with_no_proof_carries_the_tests_marked_with_its_id(self):
        made = Project(spec=SPEC_WITH_A_THIRD_RULE, gate='passed')
        try:
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login RULE-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'test: the locked account')
            made.proofs()
            rel = made.evidence(commit_it=False)
            path = os.path.join(made.root, *rel.split('/'))
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            for section in data['platforms'].values():
                section['rules']['RULE-3'] = 'passed'
                section['proofs'].append({
                    'id': 'RULE-3', 'rule': 'RULE-3', 'result': 'pass',
                    'env': None, 'manual': False,
                    'test': 'tests/test_login.py::'
                            'test_a_locked_account_returns_423'})
            write(path, json.dumps(data, indent=2, sort_keys=True))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
            export(made.root)
            third = rule_of(read_package(made.root, 'unversioned'), 'RULE-3')
            assert third['proofs'] == []
            assert third['tests'] == [{
                'proof': 'RULE-3', 'file': 'tests/test_login.py',
                'name': 'test_a_locked_account_returns_423'}]
            assert [r['result'] for r in third['results']] == ['passed']
            second = rule_of(read_package(made.root, 'unversioned'), 'RULE-2')
            assert [t['proof'] for t in second['tests']] == ['PROOF-2']
        finally:
            made.close()

    # purlin: package PROOF-11
    def test_nothing_names_who_last_changed_a_test(self, tagged):
        # The test file was committed by dev@example.com, and nothing in the
        # package names that person or asks who changed the test last.
        text = read_bytes(tagged.root,
                          '.purlin/evidence/package/2.1.0.json').decode()
        assert 'dev@example.com' not in text
        assert 'author' not in text


# ---------------------------------------------------------------------------
# What git holds
# ---------------------------------------------------------------------------

class TestWhatGitHolds:

    # purlin: package PROOF-12
    def test_evidence_not_committed_is_left_out_and_named(self, signed):
        sign_the_queue(signed)
        signed.evidence(strength=90, runner='ci', source='ci',
                        commit_it=False, at='2026-09-14T12:00:00Z')
        code, lines = export(signed.root)
        warning = ('.purlin/evidence/ci/login.json is written and not '
                   'committed; the package leaves it out.')
        assert warning in lines, lines
        package = read_package(signed.root)
        assert package['warnings'] == [warning]
        assert [r['at'] for r in rule_of(package, 'RULE-2')['results']] == [
            '2026-09-13T12:00:00Z']


# ---------------------------------------------------------------------------
# The bytes
# ---------------------------------------------------------------------------

def _clone_at_the_tag(made):
    """A second clone of the project, checked out at the tag, able to verify."""
    parent = tempfile.mkdtemp()
    clone = os.path.join(parent, 'second')
    git(parent, 'clone', '-q', made.root, clone)
    allowed = os.path.join(made.root, '.git', 'allowed-signers')
    git(clone, 'config', 'gpg.format', 'ssh')
    git(clone, 'config', 'gpg.ssh.allowedSignersFile', allowed)
    git(clone, 'checkout', '-q', 'signed/2.1.0')
    return parent, clone


class TestTheBytes:

    # purlin: package PROOF-13
    def test_exporting_twice_gives_the_same_bytes(self, signed):
        export(signed.root)
        first = read_bytes(signed.root, '.purlin/evidence/package/2.1.0.json')
        export(signed.root)
        second = read_bytes(signed.root, '.purlin/evidence/package/2.1.0.json')
        assert first == second
        assert first.endswith(b'}\n') and b'\r' not in first

    # purlin: package PROOF-14
    def test_a_second_clone_at_the_tag_gives_the_committed_bytes(self, tagged):
        committed = git(tagged.root, 'show',
                        'signed/2.1.0:.purlin/evidence/package/2.1.0.json')
        parent, clone = _clone_at_the_tag(tagged)
        try:
            code, lines = export(clone)
            assert code == 0, lines
            assert lines[0].endswith('State: signed, 2 of 2 rules meet the '
                                     'gate signed.'), lines
            assert read_bytes(
                clone, '.purlin/evidence/package/2.1.0.json').decode() == \
                committed.stdout
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    # purlin: package PROOF-15
    def test_every_time_is_utc(self, tagged):
        package = read_package(tagged.root)
        times = []

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in ('at', 'committed_at') and item is not None:
                        times.append(item)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(package)
        assert len(times) >= 4
        assert [t for t in times if not UTC.match(t)] == []


# ---------------------------------------------------------------------------
# The fingerprint
# ---------------------------------------------------------------------------

class TestTheFingerprint:

    # purlin: package PROOF-16
    def test_check_passes_a_package_as_written(self, signed):
        export(signed.root)
        path = os.path.join(signed.root, '.purlin', 'evidence', 'package',
                            '2.1.0.json')
        code, lines = export(signed.root, '--check', path)
        assert (code, lines) == (0, ['The package matches its fingerprint.'])
        assert re.match(r'^[0-9a-f]{64}$', read_package(signed.root)[
            'fingerprint'])
        assert read_package(signed.root)['fingerprint'] == \
            fingerprint_by_hand(read_bytes(
                signed.root, '.purlin/evidence/package/2.1.0.json'))

    # purlin: package PROOF-17
    def test_check_names_an_edit_made_after(self, signed):
        export(signed.root)
        path = os.path.join(signed.root, '.purlin', 'evidence', 'package',
                            '2.1.0.json')
        with open(path, 'rb') as handle:
            data = handle.read()
        edited = data.replace(b'"unsigned"', b'"signed"', 1)
        assert edited != data
        with open(path, 'wb') as handle:
            handle.write(edited)
        code, lines = export(signed.root, '--check', path)
        assert code == 1
        assert lines[0].startswith('The package does not match its '
                                   'fingerprint: the package records the '
                                   'fingerprint '), lines
        recorded = json.loads(data.decode('utf-8'))['fingerprint']
        gives = fingerprint_by_hand(edited)
        assert recorded != gives
        assert lines[0] == ('The package does not match its fingerprint: the '
                            'package records the fingerprint %s and its '
                            'content gives %s.' % (recorded, gives)), lines
        with open(path, 'wb') as handle:
            handle.write(data.replace(b'\n', b'\r\n'))
        code, lines = export(signed.root, '--check', path)
        assert code == 1
        assert 'not in the canonical form' in lines[0], lines
