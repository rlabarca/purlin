"""The evidence package `purlin:export` writes.

Every project here is a throwaway git repository in a temporary directory,
with a spec, a test file, evidence, audit entries and, where a signature is
involved, a signing key that exists nowhere but that directory. The package
command runs as a separate process, as a person runs it.

What each group holds:

*the file*        where it is written, its name, what it prints, that it
                  commits nothing, the project with no version, and the
                  commit the package names
*the state*       `finished` and `not finished`, with the total, the count at
                  each step and what is left to do
*the content*     what one rule carries, and what it never carries
*what git holds*  evidence or a signature written and not committed is
                  left out and named
*the bytes*       the same tag gives the same bytes, from a second clone too
*the fingerprint* what it is taken over, and `--check` on a package as
                  written and on one edited after
*committing*      `--commit`, run once, run again, and beside a staged change
*the settings*    a settings file that cannot be read stops the command, the
                  check of a package file included
*the refusals*    a command line it does not take, a root that is not a
                  folder, each reason `--check` gives, and a package git
                  could not check out, write or commit

Each evidence section records the machine it ran on, as the evidence format
has it. The tagged project gets its package from the call `purlin:sign`
makes before it tags, and its tag from git.
"""

import base64
import hashlib
import json
import os
import re
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
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'export'))

import package as package_module                              # noqa: E402
import sign as sign_module                                    # noqa: E402
from purlin import PURLIN_VERSION                             # noqa: E402
from purlin import evidence as evidence_module                # noqa: E402
from purlin import signatures as signatures_module            # noqa: E402
from sign_project import (CRITERIA, MODEL, SIGNING_GATE,  # noqa: E402
                          SPEC, TEST_FILE, Project, commit_all, git,
                          machine_of, name_the_model, signing_key, status,
                          write)

PACKAGE_PY = os.path.join(ROOT, 'scripts', 'export', 'package.py')

TOP_LEVEL = ['schema', 'state', 'rules', 'steps', 'left', 'purlin_version',
             'project', 'version', 'tag', 'commit', 'gate', 'mutation_engine',
             'min_strength', 'features', 'warnings', 'fingerprint']

UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

# A rule with a requirement's number in its words and no proof at all.
SPEC_WITH_A_THIRD_RULE = SPEC.replace(
    '\n\n## Proof',
    '\n- RULE-3: A locked account returns 423 (URS-042)\n\n## Proof')

NO_VERSION = ('No version: nothing in this project states one. '
              'Run purlin:export --release <version>, or write it to a '
              'VERSION file.')

NOT_COMMITTED = '%s is written and not committed; the package leaves it out.'

PACKAGE_REL = '.purlin/evidence/package/2.1.0.json'


def export(root, *args):
    """Run the package command in `root`. `(exit code, printed lines)`."""
    # The command prints UTF-8 on every system; read it so, not in the
    # console's own encoding, which on Windows is a code page.
    done = subprocess.run([sys.executable, PACKAGE_PY, '--project-root', root]
                          + list(args), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', cwd=root)
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


def line(kind, count, text, command):
    return {'kind': kind, 'count': count, 'text': text, 'command': command}


def made_project(gate=SIGNING_GATE, spec=SPEC, version='2.1.0',
                 audited=True):
    """A project whose two rules pass on a runner, both committed.

    With `audited` both rules carry an audit reading `strong`, and `RULE-2`'s
    names the model and the fingerprint of its instructions. The `VERSION`
    file states `version`, and none is written where it is None. The
    signer's key is set up last.
    """
    made = Project(spec=spec, gate=gate, config={'min_strength': 50})
    made.tests_ran_at = made.head()
    made.evidence(strength=90, runner='ci', commit_it=False, source='ci')
    if audited:
        made.audit('RULE-1')
        made.audit('RULE-2')
        name_the_model(made, 'RULE-2')
    if version:
        write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_all(made.root)
    made.public_key = signing_key(made.root)
    return made


def sign_both(made):
    """Jane signs both rules, in one signed commit."""
    assert sign_module.sign_and_commit(
        made.root, [('login', 'RULE-1'), ('login', 'RULE-2')],
        'jane@acme.com')


def tag_it(made):
    """Write and commit the package for the tag, then tag that commit."""
    rel, why = package_module.write_for_tag(made.root)
    assert rel, why
    git(made.root, 'tag', '-s', 'signed/2.1.0', '-m', 'Nothing left to do.')


def key_fingerprint(public_key_path):
    """`SHA256:` and the unpadded base64 of the sha256 of the key's blob."""
    with open(public_key_path, encoding='utf-8') as handle:
        blob = base64.b64decode(handle.read().split()[1])
    return 'SHA256:' + base64.b64encode(
        hashlib.sha256(blob).digest()).decode('ascii').rstrip('=')


@pytest.fixture
def unsigned():
    """At the gate `signed`, both rules pass and are strong, and neither is signed."""
    made = made_project()
    yield made
    made.close()


@pytest.fixture
def tagged():
    """At the gate `signed`, both rules signed, the package committed and tagged."""
    made = made_project()
    sign_both(made)
    tag_it(made)
    yield made
    made.close()


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

class TestTheFile:

    # purlin: package PROOF-1
    # purlin: package PROOF-38
    def test_it_writes_the_version_file_prints_the_state_and_commits_nothing(
            self, unsigned):
        head = unsigned.head()
        code, lines = export(unsigned.root)
        assert code == 0, lines
        assert lines == [
            'Evidence package written to .purlin/evidence/package/2.1.0.json. '
            'State: not finished.'], lines
        assert unsigned.head() == head
        assert status(unsigned.root) == (
            '?? .purlin/evidence/package/2.1.0.json\n')
        assert len(git(unsigned.root, 'worktree', 'list').stdout
                   .splitlines()) == 1

    # purlin: package PROOF-21
    def test_with_no_version_it_writes_nothing_and_says_how_to_name_one(self):
        made = made_project(version=None)
        try:
            code, lines = export(made.root)
            assert (code, lines) == (1, [NO_VERSION])
            assert not os.path.exists(os.path.join(
                made.root, '.purlin', 'evidence', 'package'))
        finally:
            made.close()

    # purlin: package PROOF-2
    def test_release_names_the_version_the_file_and_the_tag(self, unsigned):
        code, lines = export(unsigned.root, '--release', 'beta')
        assert code == 0, lines
        assert lines[0].startswith('Evidence package written to '
                                   '.purlin/evidence/package/beta.json.'), lines
        package = read_package(unsigned.root, 'beta')
        assert (package['version'], package['tag']) == ('beta', 'signed/beta')
        assert not os.path.exists(os.path.join(
            unsigned.root, '.purlin', 'evidence', 'package', '2.1.0.json'))

    # purlin: package PROOF-22
    def test_release_names_a_version_where_the_project_states_none(self):
        made = made_project(version=None)
        try:
            code, lines = export(made.root, '--release', 'beta')
            assert code == 0, lines
            package = read_package(made.root, 'beta')
            assert (package['version'], package['tag']) == (
                'beta', 'signed/beta')
        finally:
            made.close()

    # purlin: package PROOF-3
    def test_the_top_level_keys_come_in_the_format_order(self, unsigned):
        export(unsigned.root)
        package = read_package(unsigned.root)
        assert list(package) == TOP_LEVEL
        assert package['schema'] == 'purlin-package/2'
        assert package['purlin_version'] == PURLIN_VERSION
        assert (package['project'], package['gate'],
                package['mutation_engine'], package['min_strength']) == (
                    'proj', 'signed', 'none', 50)
        assert package['commit'] == unsigned.head()

    # purlin: package PROOF-30
    def test_a_code_change_committed_after_the_evidence_is_the_commit_named(
            self, unsigned):
        evidence_at = unsigned.head()
        write(os.path.join(unsigned.root, 'src', 'login.py'),
              'def login(user, password):\n'
              '    return 200 if password == "secret" else 403\n')
        commit_all(unsigned.root, 'fix(login): refuse with 403')
        code_change = unsigned.head()
        assert code_change != evidence_at
        code, lines = export(unsigned.root)
        assert code == 0, lines
        assert read_package(unsigned.root)['commit'] == code_change


# ---------------------------------------------------------------------------
# The state
# ---------------------------------------------------------------------------

class TestTheState:

    # purlin: package PROOF-4
    def test_a_project_with_no_evidence_is_not_finished(self):
        made = Project(spec=SPEC)
        try:
            write(os.path.join(made.root, 'VERSION'), '1.0.0\n')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'chore: version')
            code, lines = export(made.root)
            assert code == 0, lines
            assert lines[0].endswith('State: not finished.'), lines
            package = read_package(made.root, '1.0.0')
            assert (package['state'], package['rules'], package['steps'],
                    package['left']) == (
                'not finished', 2, {'passed': 0},
                [line('to_test', 2, '2 rules to test', 'purlin:test')])
        finally:
            made.close()

    # purlin: package PROOF-5
    def test_a_rule_with_no_proof_is_left_to_write_one_for(self):
        made = made_project(spec=SPEC_WITH_A_THIRD_RULE)
        try:
            export(made.root)
            package = read_package(made.root)
            third = rule_of(package, 'RULE-3')
            assert third['text'] == 'A locked account returns 423 (URS-042)'
            assert (third['proofs'], third['tests']) == ([], [])
            assert [r['result'] for r in third['results']] == ['no test']
            assert third['left'] == 'no_proof'
            assert package['left'][0] == line(
                'no_proof', 1, '1 rule to write a proof for', 'purlin:spec')
            assert package['state'] == 'not finished'
        finally:
            made.close()

    # purlin: package PROOF-6
    def test_rules_no_audit_has_read_are_left_to_audit(self):
        made = made_project(gate='strong', audited=False)
        try:
            export(made.root)
            package = read_package(made.root)
            second = rule_of(package, 'RULE-2')
            assert second['audit'] is None
            assert second['statuses']['strong']['word'] == 'not audited'
            assert second['left'] == 'to_audit'
            assert (package['state'], package['steps'], package['left']) == (
                'not finished', {'passed': 2, 'strong': 0},
                [line('to_audit', 2, '2 rules to audit', 'purlin:audit')])
        finally:
            made.close()

    # purlin: package PROOF-7
    def test_rules_not_signed_are_left_to_sign(self, unsigned):
        export(unsigned.root)
        package = read_package(unsigned.root)
        second = rule_of(package, 'RULE-2')
        assert second['signatures'] == []
        assert second['statuses']['signed']['word'] == 'unsigned'
        assert second['left'] == 'to_sign'
        assert (package['steps'], package['left']) == (
            {'passed': 2, 'strong': 2, 'signed': 0},
            [line('to_sign', 2, '2 rules to sign', 'purlin:sign')])

    # purlin: package PROOF-8
    def test_at_passed_rules_that_pass_are_finished(self):
        made = made_project(gate='passed', audited=False)
        try:
            code, lines = export(made.root)
            assert lines[0].endswith('State: finished.'), lines
            package = read_package(made.root)
            assert (package['state'], package['rules'], package['steps'],
                    package['left']) == ('finished', 2, {'passed': 2}, [])
        finally:
            made.close()

    # purlin: package PROOF-19
    def test_at_strong_rules_that_are_strong_are_finished(self):
        made = made_project(gate='strong')
        try:
            export(made.root)
            package = read_package(made.root)
            assert (package['state'], package['steps'], package['left']) == (
                'finished', {'passed': 2, 'strong': 2}, [])
        finally:
            made.close()

    # purlin: package PROOF-23
    def test_at_signed_with_every_rule_signed_the_tag_is_left(self, unsigned):
        sign_both(unsigned)
        export(unsigned.root)
        package = read_package(unsigned.root)
        assert (package['state'], package['left']) == (
            'not finished',
            [line('to_tag', 1, 'the version to tag', 'purlin:sign')])

    # purlin: package PROOF-24
    def test_the_package_written_for_the_tag_is_finished(self, unsigned):
        sign_both(unsigned)
        evidence_commit = unsigned.head()
        rel, why = package_module.write_for_tag(unsigned.root)
        assert rel == '.purlin/evidence/package/2.1.0.json', why
        package = json.loads(git(unsigned.root, 'show',
                                 'HEAD:' + rel).stdout)
        assert (package['state'], package['left'], package['steps']) == (
            'finished', [], {'passed': 2, 'strong': 2, 'signed': 2})
        assert git(unsigned.root, 'rev-parse', 'HEAD^').stdout.strip() == \
            evidence_commit == package['commit']


# ---------------------------------------------------------------------------
# The content
# ---------------------------------------------------------------------------

class TestTheContent:

    # purlin: package PROOF-9
    def test_one_rule_carries_its_words_its_proof_and_its_test(self, tagged):
        rule = rule_of(read_package(tagged.root), 'RULE-2')
        assert rule['text'] == ('Invalid credentials return 401 and the body '
                                '"denied"')
        assert rule['left'] is None
        assert rule['proofs'] == [{
            'id': 'PROOF-2', 'manual': False, 'env': None,
            'text': 'POST /login with a bad password; verify 401 and the body '
                    '"denied"'}]
        assert rule['tests'] == [{'proof': 'PROOF-2',
                                  'file': 'tests/test_login.py',
                                  'name': 'test_a_bad_password_is_denied'}]

    # purlin: package PROOF-25
    def test_one_rule_carries_its_result_and_the_machine(self, tagged):
        [result] = rule_of(read_package(tagged.root), 'RULE-2')['results']
        assert (result['source'], result['result'], result['runner'],
                result['at'], result['current']) == (
                    'ci', 'passed', 'ci', '2026-09-13T12:00:00Z', True)
        assert result['os'] == evidence_module.host_os()
        assert result['machine'] == machine_of('ci', result['os'])
        assert result['commit'] == tagged.tests_ran_at

    # purlin: package PROOF-26
    def test_one_rule_carries_what_the_audit_found(self, tagged):
        audit = rule_of(read_package(tagged.root), 'RULE-2')['audit']
        assert (audit['verdict'], audit['findings'], audit['strength'],
                audit['model'], audit['criteria'], audit['at']) == (
                    'strong', [], 90, MODEL, CRITERIA, '2026-09-13T12:05:00Z')

    # purlin: package PROOF-27
    def test_one_rule_carries_who_signed_it_and_with_which_key(self, tagged):
        [signature] = rule_of(read_package(tagged.root), 'RULE-2')[
            'signatures']
        assert (signature['signer'], signature['signer_name'],
                signature['applies_to'], signature['note'],
                signature['signed_commit']) == (
                    'jane@acme.com', 'Jane', 'login', None, True)
        assert signature['key_fingerprint'] == key_fingerprint(
            tagged.public_key)
        assert UTC.match(signature['at']), signature['at']

    # purlin: package PROOF-28
    def test_one_rule_carries_what_its_signature_locked(self, tagged):
        [signature] = rule_of(read_package(tagged.root), 'RULE-2')[
            'signatures']
        now = tagged.rule('RULE-2')
        assert signature['machines'] == now['machines'] != {}
        assert signature['locked'] == dict(
            {key: now[key] for key in ('rule_hash', 'proof_hash', 'test_hash',
                                       'test_hash_kind', 'code_hash',
                                       'audit_hash')},
            signed_hash=signatures_module.signed_hash(now))

    # purlin: package PROOF-20
    def test_at_signed_a_rule_carries_every_status(self, tagged):
        statuses = rule_of(read_package(tagged.root), 'RULE-1')['statuses']
        assert {name: cell['word'] for name, cell in statuses.items()} == {
            'passed': 'passed', 'strong': 'strong', 'signed': 'signed'}

    # purlin: package PROOF-29
    def test_at_passed_a_rule_carries_one_status(self):
        made = made_project(gate='passed', audited=False)
        try:
            export(made.root)
            statuses = rule_of(read_package(made.root), 'RULE-2')['statuses']
            assert {name: cell['word'] for name, cell in statuses.items()} == {
                'passed': 'passed'}
        finally:
            made.close()

    # purlin: package PROOF-18
    def test_a_rule_with_no_proof_carries_the_tests_marked_with_its_id(self):
        made = Project(spec=SPEC_WITH_A_THIRD_RULE, gate='passed')
        try:
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login RULE-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
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
            third = rule_of(read_package(made.root), 'RULE-3')
            assert third['proofs'] == []
            assert third['tests'] == [{
                'proof': 'RULE-3', 'file': 'tests/test_login.py',
                'name': 'test_a_locked_account_returns_423'}]
            assert [r['result'] for r in third['results']] == ['passed']
            second = rule_of(read_package(made.root), 'RULE-2')
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
    def test_evidence_not_committed_is_left_out_and_named(self, unsigned):
        sign_both(unsigned)
        unsigned.evidence(strength=90, runner='ci', source='ci',
                          commit_it=False, at='2026-09-14T12:00:00Z')
        code, lines = export(unsigned.root)
        warning = NOT_COMMITTED % '.purlin/evidence/ci/login.json'
        assert warning in lines, lines
        package = read_package(unsigned.root)
        assert package['warnings'] == [warning]
        assert [r['at'] for r in rule_of(package, 'RULE-2')['results']] == [
            '2026-09-13T12:00:00Z']

    # purlin: package PROOF-31
    def test_a_signature_not_committed_is_left_out_and_named(self, unsigned):
        assert sign_module.sign_and_commit(
            unsigned.root, [('login', 'RULE-2')], 'jane@acme.com')
        git(unsigned.root, 'reset', '-q', 'HEAD~1')
        [written] = [line[3:] for line in status(unsigned.root).splitlines()]
        assert written.startswith('specs/auth/login.signatures/RULE-2.'), \
            written
        code, lines = export(unsigned.root)
        assert code == 0, lines
        assert NOT_COMMITTED % written in lines, lines
        package = read_package(unsigned.root)
        assert package['warnings'] == [NOT_COMMITTED % written]
        assert rule_of(package, 'RULE-2')['signatures'] == []


# ---------------------------------------------------------------------------
# The bytes
# ---------------------------------------------------------------------------

def _clone_at_the_tag(made):
    """A second clone of the project, checked out at the tag.

    The clone sets `core.autocrlf` to `true`, as Git for Windows does by
    default, so git writes a carriage return before every line feed of the
    files it checks out there, the committed package included.
    """
    parent = tempfile.mkdtemp()
    clone = os.path.join(parent, 'second')
    cloned = git(parent, 'clone', '-q', '-c', 'core.autocrlf=true',
                 made.root, clone)
    assert cloned.returncode == 0, cloned.stderr
    checked_out = git(clone, 'checkout', '-q', 'signed/2.1.0')
    assert checked_out.returncode == 0, checked_out.stderr
    return parent, clone


def git_bytes(root, *args):
    """What a git command prints, as bytes, with no line ends translated."""
    done = subprocess.run(['git'] + list(args), cwd=root, capture_output=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


class TestTheBytes:

    # purlin: package PROOF-13
    def test_exporting_twice_gives_the_same_bytes(self, unsigned):
        export(unsigned.root)
        first = read_bytes(unsigned.root,
                           '.purlin/evidence/package/2.1.0.json')
        export(unsigned.root)
        second = read_bytes(unsigned.root,
                            '.purlin/evidence/package/2.1.0.json')
        assert first == second
        assert first.endswith(b'}\n') and b'\r' not in first

    # purlin: package PROOF-14
    # purlin: package PROOF-39
    def test_a_second_clone_at_the_tag_gives_the_committed_bytes(self, tagged):
        committed = git_bytes(tagged.root, 'show',
                              'signed/2.1.0:' + PACKAGE_REL)
        assert b'\r' not in committed
        parent, clone = _clone_at_the_tag(tagged)
        try:
            # The checkout gave the committed package carriage returns.
            assert read_bytes(clone, PACKAGE_REL) == \
                committed.replace(b'\n', b'\r\n')
            code, lines = export(clone)
            assert code == 0, lines
            assert lines == ['Evidence package written to '
                             '.purlin/evidence/package/2.1.0.json. '
                             'State: finished.'], lines
            written = read_bytes(clone, PACKAGE_REL)
            assert written == committed
            assert b'\r' not in written
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

def _exported(made):
    """Export the project; the package file's path and its bytes."""
    code, lines = export(made.root)
    assert code == 0, lines
    return (os.path.join(made.root, *PACKAGE_REL.split('/')),
            read_bytes(made.root, PACKAGE_REL))


class TestTheFingerprint:

    # purlin: package PROOF-16
    # purlin: package PROOF-40
    def test_check_passes_a_package_as_written(self, unsigned):
        path, _ = _exported(unsigned)
        code, lines = export(unsigned.root, '--check', path)
        assert (code, lines) == (0, ['The package matches its fingerprint.'])

    # purlin: package PROOF-32
    def test_the_fingerprint_is_the_sha256_of_the_file_with_it_emptied(
            self, unsigned):
        _, data = _exported(unsigned)
        recorded = json.loads(data.decode('utf-8'))['fingerprint']
        assert re.match(r'^[0-9a-f]{64}$', recorded), recorded
        assert recorded == fingerprint_by_hand(data)

    # purlin: package PROOF-17
    def test_check_names_an_edit_made_after(self, unsigned):
        path, data = _exported(unsigned)
        edited = data.replace(b'"unsigned"', b'"signed"', 1)
        assert edited != data
        with open(path, 'wb') as handle:
            handle.write(edited)
        code, lines = export(unsigned.root, '--check', path)
        assert code == 1, lines
        recorded = json.loads(data.decode('utf-8'))['fingerprint']
        gives = fingerprint_by_hand(edited)
        assert recorded != gives
        assert lines[0] == ('The package does not match its fingerprint: the '
                            'package records the fingerprint %s and its '
                            'content gives %s.' % (recorded, gives)), lines

    # purlin: package PROOF-33
    def test_check_refuses_carriage_returns_before_each_newline(
            self, unsigned):
        path, data = _exported(unsigned)
        with open(path, 'wb') as handle:
            handle.write(data.replace(b'\n', b'\r\n'))
        code, lines = export(unsigned.root, '--check', path)
        assert (code, lines) == (1, [
            'The package does not match its fingerprint: the fingerprint '
            'matches the content, but the bytes are not in the canonical '
            'form.'])


# ---------------------------------------------------------------------------
# Committing
# ---------------------------------------------------------------------------

class TestCommitting:

    # purlin: package PROOF-10
    def test_commit_commits_the_package_as_evidence_at_head(self, unsigned):
        head = unsigned.head()
        code, lines = export(unsigned.root, '--commit')
        assert code == 0, lines
        assert lines[-1] == 'Package committed.', lines
        assert git(unsigned.root, 'log', '-1',
                   '--format=%s').stdout.strip() == \
            'purlin: evidence at %s' % head[:7]
        assert status(unsigned.root) == ''

    # purlin: package PROOF-34
    def test_a_second_commit_over_the_same_evidence_is_unchanged(
            self, unsigned):
        evidence_at = unsigned.head()
        code, lines = export(unsigned.root, '--commit')
        assert (code, lines[-1]) == (0, 'Package committed.'), lines
        committed = unsigned.head()
        code, lines = export(unsigned.root, '--commit')
        assert code == 0, lines
        assert lines[-1] == 'Package unchanged.', lines
        assert unsigned.head() == committed
        assert read_package(unsigned.root)['commit'] == evidence_at

    # purlin: package PROOF-35
    def test_commit_leaves_a_change_staged_elsewhere_out(self, unsigned):
        write(os.path.join(unsigned.root, 'src', 'login.py'), '# edited\n')
        git(unsigned.root, 'add', 'src/login.py')
        code, lines = export(unsigned.root, '--commit')
        assert code == 0, lines
        assert git(unsigned.root, 'show', '--name-only', '--format=',
                   'HEAD').stdout.split() == [PACKAGE_REL]
        assert status(unsigned.root) == 'M  src/login.py\n'


# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------

# A settings file with a trailing comma, which the JSON reader refuses.
TRAILING_COMMA = '{"gate": "signed",}'


def cannot_be_read():
    """The one line the command prints for TRAILING_COMMA, in the JSON
    reader's own words, which differ from one Python to the next."""
    try:
        json.loads(TRAILING_COMMA)
    except ValueError as error:
        return ('.purlin/config.json cannot be read: %s at line %d. Fix the '
                'file by hand; nothing ran and nothing was saved.'
                % (error.msg, error.lineno))
    raise AssertionError('the JSON reader took a trailing comma')


def break_the_settings(made):
    write(os.path.join(made.root, '.purlin', 'config.json'), TRAILING_COMMA)


class TestTheSettings:

    # purlin: package PROOF-36
    def test_a_settings_file_that_cannot_be_read_stops_the_export(
            self, unsigned):
        break_the_settings(unsigned)
        code, lines = export(unsigned.root)
        assert (code, lines) == (1, [cannot_be_read()])
        assert not os.path.exists(os.path.join(
            unsigned.root, '.purlin', 'evidence', 'package'))

    # purlin: package PROOF-37
    def test_a_settings_file_that_cannot_be_read_stops_the_check(
            self, unsigned):
        path, _ = _exported(unsigned)
        break_the_settings(unsigned)
        code, lines = export(unsigned.root, '--check', path)
        assert (code, lines) == (1, [cannot_be_read()])


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------

USAGE = ['Usage: package.py [--release NAME] [--commit] [--project-root DIR]',
         '       package.py --check FILE']

CHECK_FAILED = 'The package does not match its fingerprint: %s.'

NOT_WRITTEN = 'export: the package was not written: %s.'

NOT_COMMITTED_BY_GIT = 'export: the package was not committed: %s.'


def run_package(cwd, *args):
    """Run the package command in `cwd` with exactly `args`. `(code, lines)`."""
    done = subprocess.run([sys.executable, PACKAGE_PY] + list(args),
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace', cwd=cwd)
    return done.returncode, (done.stdout + done.stderr).splitlines()


@pytest.fixture
def versioned():
    """A git repository with no commit, whose `VERSION` file reads `2.1.0`."""
    parent = tempfile.mkdtemp()
    root = os.path.join(parent, 'proj')
    os.makedirs(root)
    git(root, 'init', '-q')
    write(os.path.join(root, 'VERSION'), '2.1.0\n')
    yield root
    shutil.rmtree(parent, ignore_errors=True)


def no_package_folder(root):
    return not os.path.exists(os.path.join(root, '.purlin', 'evidence',
                                           'package'))


def edited_package(made, edit):
    """Export, rewrite the package through `edit(dict)`, return its path."""
    path, data = _exported(made)
    package = json.loads(data.decode('utf-8'))
    edit(package)
    with open(path, 'wb') as handle:
        handle.write((json.dumps(package, indent=2) + '\n').encode('utf-8'))
    return path


class TestTheRefusals:

    # purlin: package PROOF-41
    def test_a_project_root_that_is_not_a_folder_is_refused(self, versioned):
        missing = os.path.join(versioned, 'missing')
        code, lines = run_package(versioned, '--project-root', missing)
        assert (code, lines) == (
            2, ['package.py: %s is not a directory.' % missing])

    # purlin: package PROOF-42
    def test_an_option_with_no_value_is_refused(self, versioned):
        for option, args in (('--release', ['--project-root', versioned,
                                            '--release']),
                             ('--project-root', ['--project-root']),
                             ('--check', ['--project-root', versioned,
                                          '--check'])):
            code, lines = run_package(versioned, *args)
            assert (code, lines) == (
                2, USAGE + ['package.py: %s needs a value.' % option]), option
        assert no_package_folder(versioned)

    # purlin: package PROOF-43
    def test_an_argument_it_does_not_take_is_refused(self, versioned):
        code, lines = run_package(versioned, '--project-root', versioned,
                                  '--verbose')
        assert (code, lines) == (
            2, USAGE + ['package.py: unexpected argument --verbose'])
        assert no_package_folder(versioned)

    # purlin: package PROOF-44
    def test_check_beside_another_option_is_refused(self, versioned):
        for other in (['--commit'], ['--release', 'beta']):
            code, lines = run_package(versioned, '--check', 'package.json',
                                      *other)
            assert (code, lines) == (2, USAGE + [
                'package.py: --check reads a file and takes nothing else.']), \
                other

    # purlin: package PROOF-45
    def test_check_names_a_file_that_is_not_utf8_json(self, versioned):
        for name, data in (('latin.json', b'{"schema": "caf\xe9"}\n'),
                           ('text.json', b'not a package\n')):
            path = os.path.join(versioned, name)
            with open(path, 'wb') as handle:
                handle.write(data)
            code, lines = run_package(versioned, '--check', path)
            assert (code, lines) == (
                1, [CHECK_FAILED % 'the file is not UTF-8 JSON']), name

    # purlin: package PROOF-46
    def test_check_names_another_schema(self, unsigned):
        path = edited_package(
            unsigned, lambda package: package.update(schema='purlin-package/1'))
        code, lines = export(unsigned.root, '--check', path)
        assert (code, lines) == (1, [
            CHECK_FAILED
            % 'the file does not carry the schema purlin-package/2'])

    # purlin: package PROOF-47
    def test_check_names_a_key_the_format_does_not_name(self, unsigned):
        path = edited_package(
            unsigned, lambda package: package.update(extra=1))
        code, lines = export(unsigned.root, '--check', path)
        assert (code, lines) == (1, [
            CHECK_FAILED
            % 'the package carries keys the format does not name: extra'])

    # purlin: package PROOF-48
    def test_check_names_top_level_keys_out_of_the_format(self, unsigned):
        path = edited_package(
            unsigned, lambda package: package.pop('warnings'))
        code, lines = export(unsigned.root, '--check', path)
        assert (code, lines) == (1, [
            CHECK_FAILED % 'the top-level keys are not the ones the format '
                           'names, in its order'])

    # purlin: package PROOF-49
    def test_check_names_a_file_that_cannot_be_read(self, versioned):
        path = os.path.join(versioned, 'gone.json')
        try:
            open(path, 'rb')
        except (IOError, OSError) as error:
            reason = 'the file could not be read: %s' % error
        else:
            raise AssertionError('%s exists' % path)
        code, lines = run_package(versioned, '--check', path)
        assert (code, lines) == (1, [CHECK_FAILED % reason])

    # purlin: package PROOF-50
    def test_a_project_with_no_commit_is_not_written(self, versioned):
        code, lines = run_package(versioned, '--project-root', versioned)
        assert (code, lines) == (
            1, [NOT_WRITTEN % 'the project has no commit yet'])
        assert no_package_folder(versioned)

    # purlin: package PROOF-51
    def test_a_commit_git_cannot_check_out_is_not_written(self, unsigned):
        worktrees = os.path.join(unsigned.root, '.git', 'worktrees')
        shutil.rmtree(worktrees, ignore_errors=True)
        write(worktrees, 'not a folder\n')
        code, lines = export(unsigned.root)
        prefix = ('export: the package was not written: the commit %s could '
                  'not be checked out: ' % unsigned.head()[:7])
        assert code == 1, lines
        assert len(lines) == 1, lines
        assert lines[0].startswith(prefix) and lines[0].endswith('.'), lines
        assert lines[0][len(prefix):-1].strip(), lines
        assert no_package_folder(unsigned.root)

    # purlin: package PROOF-52
    def test_a_package_folder_that_is_a_file_is_not_written(self, unsigned):
        folder = os.path.join(unsigned.root, '.purlin', 'evidence', 'package')
        write(folder, 'not a folder\n')
        try:
            os.makedirs(folder, exist_ok=True)
        except (IOError, OSError) as error:
            reason = str(error)
        else:
            raise AssertionError('%s became a folder' % folder)
        code, lines = export(unsigned.root)
        assert (code, lines) == (1, [NOT_WRITTEN % reason])

    # purlin: package PROOF-53
    def test_a_commit_git_refuses_is_not_committed(self, unsigned):
        hooks = tempfile.mkdtemp()
        try:
            hook = os.path.join(hooks, 'pre-commit')
            with open(hook, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write('#!/bin/sh\necho "no commits today" >&2\nexit 1\n')
            os.chmod(hook, 0o755)
            git(unsigned.root, 'config', 'core.hooksPath', hooks)
            head = unsigned.head()
            code, lines = export(unsigned.root, '--commit')
            assert code == 1, lines
            assert lines[-1] == NOT_COMMITTED_BY_GIT % (
                'git commit failed: no commits today'), lines
            assert unsigned.head() == head
        finally:
            shutil.rmtree(hooks, ignore_errors=True)

    # purlin: package PROOF-54
    def test_a_file_git_cannot_add_is_not_committed(self, unsigned):
        head = unsigned.head()
        write(os.path.join(unsigned.root, '.git', 'index.lock'), '')
        code, lines = export(unsigned.root, '--commit')
        assert code == 1, lines
        assert lines[0] == ('Evidence package written to %s. State: not '
                            'finished.' % PACKAGE_REL), lines
        prefix = 'export: the package was not committed: git add failed: '
        assert lines[1].startswith(prefix), lines
        assert lines[1][len(prefix):].strip(), lines
        assert unsigned.head() == head
