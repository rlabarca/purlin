"""The evidence package `purlin:sign` builds and commits.

Every project here is a throwaway git repository in a temporary directory,
with a spec, a test file, evidence and audit entries. The package is written
by the sign-off walk, run in the test's own process and answered yes, and
read back from the signed commit.

What each group holds:

*the file*        where it is written, its name, its version and the commit
                  it names
*met*             whether the tests pass, the total, the count that pass and
                  what is left to do
*the content*     what one rule carries: words, proofs, tests, results, the
                  audit, the two statuses, the times
*anchors*         a feature entry, and an anchor's
*the runs*        who ran the tests, where and when, and the same code
*the bytes*       the same commit gives the same bytes, from two clones
*the fingerprint* what it is taken over, and `--check`
*the authors*     who wrote and last changed each rule, proof and test
"""

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
for _path in (os.path.join(ROOT, 'scripts', 'mcp'),
              os.path.join(ROOT, 'scripts', 'review'), DEV):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import sign as sign_module  # noqa: E402
from purlin import PURLIN_VERSION  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from sign_project import (CRITERIA, MODEL, SPEC, TEST_FILE,  # noqa: E402
                          TEST_NAMES, Project, _Out, git, name_the_model,
                          write)

TOP_LEVEL = ['schema', 'met', 'rules', 'steps', 'audit', 'left',
             'purlin_version', 'project', 'version', 'tag', 'commit', 'runs',
             'features', 'hand_checks', 'warnings', 'fingerprint']

UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

EMAIL = 'jane@acme.com'
DANA = 'dana.dev@labconnect.example'
QUINN = 'quinn.qa@labconnect.example'
PAT = 'pat.product@labconnect.example'
MACHINE = 'dana-laptop'
AT = '2026-09-13T12:00:00Z'
PACKAGE = '.purlin/evidence/package/2.1.0.json'

CHECK_FAILED = 'The package does not match its fingerprint: %s.'

# A rule with a requirement's number in its words and no proof at all.
SPEC_WITH_A_THIRD_RULE = SPEC.replace(
    '\n\n## Proof',
    '\n- RULE-3: A locked account returns 423 (URS-042)\n\n## Proof')

# `PROOF-2` is a hand check, and no test carries it.
MANUAL_SPEC = SPEC.replace('verify 401 and the body "denied"',
                           'verify 401 and the body "denied" @manual')
MANUAL_TEST_FILE = TEST_FILE.split('\n\n\n# purlin: login PROOF-2')[0] + '\n'


# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------

def section(made, proofs, rules, source='local', os_name='linux', email=DANA,
            machine=MACHINE, at=AT, commit=None, feature='login'):
    """One evidence section, as the run writes it, over the project as it stands.

    `proofs` is `[(id, rule, result, test name or None, reason or None)]`;
    `rules` is `{RULE-N: word}`. A remote runner's section names no email.
    """
    entries = []
    for proof_id, rule, result, name, reason in proofs:
        entry = {'id': proof_id, 'rule': rule, 'result': result, 'env': None,
                 'manual': False,
                 'test': 'tests/test_%s.py::%s' % (feature, name) if name
                 else ''}
        if reason is not None:
            entry['reason'] = reason
        entries.append(entry)
    found = {'commit': commit or made.head(), 'dirty': False, 'at': at,
             'runner': 'ci' if source == 'ci' else email.split('@')[0],
             'machine': machine,
             'fingerprint': purlin_fingerprint.fingerprint(made.root, feature),
             'rules': dict(rules), 'proofs': entries}
    if source == 'ci':
        found['hostname'] = 'runner-17'
    else:
        found['email'] = email
    rel = '.purlin/evidence/%s/%s.json' % (source, feature)
    path = os.path.join(made.root, *rel.split('/'))
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        data = {'schema': purlin_evidence.SCHEMA, 'feature': feature,
                'source': source,
                'spec': 'specs/auth/%s.md' % feature if feature == 'login'
                else 'specs/_anchors/%s.md' % feature,
                'platforms': {}}
    data['platforms'][os_name] = found
    write(path, json.dumps(data, indent=2, sort_keys=True))
    return rel


def passing(made, extra=(), **kwargs):
    """Both of `login`'s proofs passing, then the `(id, rule, test)` in `extra`."""
    proofs = [(proof_id, 'RULE-%s' % proof_id[-1], 'pass',
               TEST_NAMES[proof_id], None) for proof_id in ('PROOF-1',
                                                            'PROOF-2')]
    proofs.extend((proof_id, rule, 'pass', name, None)
                  for proof_id, rule, name in extra)
    rules = {rule: 'passed' for _id, rule, _r, _n, _w in proofs}
    return section(made, proofs, rules, **kwargs)


def commit_all(made, message='purlin: evidence at abc1234', author=None):
    git(made.root, 'add', '-A')
    args = ['-c', 'user.email=%s' % author] if author else []
    git(made.root, *(args + ['commit', '-q', '-m', message]))


def key(root, email=EMAIL, name='Jane', file='signing-key'):
    """A throwaway ssh key, named as this checkout's signing key. Its `.pub`."""
    path = os.path.join(root, '.git', file)
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', email,
                    '-f', path], check=True)
    if os.name == 'nt':
        subprocess.run(['icacls', path, '/inheritance:r', '/grant:r',
                        '%s:F' % os.environ['USERNAME']],
                       check=True, capture_output=True)
    for setting, value in (('user.email', email), ('user.name', name),
                           ('gpg.format', 'ssh'),
                           ('gpg.ssh.program', 'ssh-keygen'),
                           ('user.signingkey', path + '.pub')):
        git(root, 'config', setting, value)
    return path + '.pub'


def made_project(spec=SPEC, version='2.1.0', strong=('RULE-1', 'RULE-2'),
                 weak=(), test_file=None):
    """A project whose rules pass on Dana's laptop, its results committed.

    `strong` and `weak` name the rules the audit read; `RULE-2`'s audit, where
    there is one, names the model and the fingerprint of its instructions.
    The `VERSION` file states `version`, and none is written where it is None.
    """
    made = Project(spec=spec)
    if test_file is not None:
        made.edit_test(test_file)
    if version:
        write(os.path.join(made.root, 'VERSION'), version + '\n')
        commit_all(made, 'chore: version')
    if test_file is MANUAL_TEST_FILE:
        section(made, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'],
                        None)], {'RULE-1': 'passed', 'RULE-2': 'passed'})
    else:
        passing(made)
    for rule in strong:
        made.audit(rule)
    for rule in weak:
        made.audit(rule, findings=['The test checks one bad password.'])
    if 'RULE-2' in strong:
        name_the_model(made, 'RULE-2')
    commit_all(made)
    key(made.root)
    return made


# The walk's answers: go on past the audit's findings, a note at each hand
# check, and yes.
ANSWERS = {'audit': 'go on', 'audit_again': 'go on', 'hand': 'checked',
           'sign': 'y'}


def sign(made, version=None):
    """The sign-off walk, answered yes. `(exit, lines)`."""
    out = _Out()

    def ask(kind, _key, _prompt):
        return ANSWERS[kind]

    code = sign_module.walk(made.root, version, ask=ask, out=out)
    return code, out.text().splitlines()


def signed_package(made, named=None):
    """Sign the version `named`, else the one stated, then read the package
    the signed commit carries."""
    code, lines = sign(made, named)
    assert code == 0, lines
    return committed(made, named or '2.1.0')


def committed(made, version='2.1.0'):
    return json.loads(git_bytes(made.root, 'show', 'HEAD:.purlin/evidence/'
                                'package/%s.json' % version).decode('utf-8'))


def git_bytes(root, *args):
    """What a git command prints, as bytes, with no line ends translated."""
    done = subprocess.run(['git'] + list(args), cwd=root, capture_output=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


def changed_in_head(root):
    return git(root, 'show', '--name-only', '--format=', 'HEAD').stdout.split()


def rule_of(package, rule_id, feature='login'):
    entry = next(f for f in package['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


def words_naming_compliance(value):
    """Every key and every text value in a package, at any depth, that holds
    `compliant` or `compliance` in any case."""
    found = []
    if isinstance(value, dict):
        for name, inner in value.items():
            if re.search(r'complian(t|ce)', name, re.I):
                found.append(name)
            found.extend(words_naming_compliance(inner))
    elif isinstance(value, list):
        for inner in value:
            found.extend(words_naming_compliance(inner))
    elif isinstance(value, str) and re.search(r'complian(t|ce)', value, re.I):
        found.append(value)
    return found


def line(kind, count, text, command):
    return {'kind': kind, 'count': count, 'text': text, 'command': command}


def fingerprint_by_hand(data):
    """sha256 of a package's bytes with the top-level `fingerprint` emptied.

    Worked on the file's text: the one top-level `"fingerprint": "<hex>"`
    becomes `"fingerprint": ""`.
    """
    blanked, count = re.subn(rb'\n  "fingerprint": "[0-9a-f]*"\n}\n$',
                             b'\n  "fingerprint": ""\n}\n', data)
    assert count == 1, data[-200:]
    return hashlib.sha256(blanked).hexdigest()


def check(path, capsys):
    code = sign_module.main(['--check', path])
    return code, capsys.readouterr().out.splitlines()


@pytest.fixture
def project():
    """Both rules pass on Dana's laptop and are audited strong; `VERSION` reads 2.1.0."""
    made = made_project()
    yield made
    made.close()


@pytest.fixture
def signed(project):
    """`project`, signed for 2.1.0 by Jane; its package as committed."""
    project.package = signed_package(project)
    return project


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

class TestTheFile:

    # purlin: package PROOF-1
    def test_the_signed_commit_carries_the_package_and_no_worktree_is_left(
            self, project):
        assert sign(project)[0] == 0
        assert PACKAGE in changed_in_head(project.root)
        assert len(git(project.root, 'worktree', 'list').stdout
                   .splitlines()) == 1

    # purlin: package PROOF-2
    def test_version_names_the_file_and_the_tag(self, project):
        package = signed_package(project, 'beta')
        assert '.purlin/evidence/package/beta.json' in changed_in_head(
            project.root)
        assert (package['version'], package['tag']) == ('beta', 'signed/beta')
        assert not os.path.exists(os.path.join(project.root,
                                               *PACKAGE.split('/')))

    # purlin: package PROOF-22
    def test_version_names_one_where_the_project_states_none(self):
        made = made_project(version=None)
        try:
            package = signed_package(made, 'beta')
            assert '.purlin/evidence/package/beta.json' in changed_in_head(
                made.root)
            assert (package['version'], package['tag']) == ('beta',
                                                            'signed/beta')
        finally:
            made.close()

    # purlin: package PROOF-3
    def test_the_sixteen_top_level_keys_come_in_order(self, project):
        holds_the_evidence = project.head()
        package = signed_package(project)
        assert list(package) == TOP_LEVEL
        assert package['schema'] == 'purlin-package/4'
        assert package['purlin_version'] == PURLIN_VERSION
        # HEAD before the sign-off's own commit, which is HEAD~1 after it.
        assert package['commit'] == holds_the_evidence
        assert package['commit'] == git(
            project.root, 'rev-parse', 'HEAD~1').stdout.strip()

    # purlin: package PROOF-30
    def test_a_later_version_names_the_code_not_the_sign_off(self, project):
        code_at = project.head()
        assert sign(project)[0] == 0
        assert project.head() != code_at
        package = signed_package(project, '2.2.0')
        assert package['commit'] == code_at

    # purlin: package PROOF-70
    def test_the_version_file_comes_before_package_json(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'package.json'),
                  '{"name": "app", "version": "9.9.9"}\n')
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made)
            commit_all(made)
            key(made.root)
            assert sign(made)[0] == 0
            assert os.path.isfile(os.path.join(made.root, *PACKAGE.split('/')))
            assert committed(made)['version'] == '2.1.0'
        finally:
            made.close()

    # purlin: package PROOF-71
    def test_pyproject_states_the_version_where_nothing_before_it_does(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'pyproject.toml'),
                  '[project]\nname = "app"\nversion = "3.0.0"\n')
            commit_all(made, 'chore: pyproject')
            passing(made)
            commit_all(made)
            key(made.root)
            assert sign(made)[0] == 0
            assert os.path.isfile(os.path.join(
                made.root, '.purlin', 'evidence', 'package', '3.0.0.json'))
            assert committed(made, '3.0.0')['version'] == '3.0.0'
        finally:
            made.close()

    # purlin: package PROOF-52
    def test_a_package_folder_that_is_a_file_is_named_and_nothing_made(
            self, project):
        folder = os.path.join(project.root, '.purlin', 'evidence', 'package')
        write(folder, 'not a folder\n')
        try:
            os.makedirs(folder, exist_ok=True)
        except (IOError, OSError) as error:
            reason = str(error)
        else:
            raise AssertionError('%s became a folder' % folder)
        before = project.head()
        code, lines = sign(project)
        assert code == 1
        assert [text for text in lines if reason in text] == [
            'The evidence package was not written: %s. Nothing was signed; '
            'run purlin:sign again.' % reason]
        assert project.head() == before
        assert git(project.root, 'tag', '--list').stdout == ''


# ---------------------------------------------------------------------------
# Met, the count and what is left
# ---------------------------------------------------------------------------

class TestMet:

    # purlin: package PROOF-8
    def test_two_rules_that_pass_are_met(self, signed):
        package = signed.package
        assert (package['met'], package['rules'], package['steps'],
                package['left']) == (True, 2, {'passed': 2}, [])

    # purlin: package PROOF-63
    def test_a_rule_left_only_to_strengthen_leaves_it_met(self):
        made = made_project(strong=('RULE-1',), weak=('RULE-2',))
        try:
            package = signed_package(made)
            assert (package['met'], package['left']) == (
                True, [line('to_strengthen', 1, '1 rule to strengthen',
                            'purlin:build')])
        finally:
            made.close()

    # purlin: package PROOF-5
    def test_a_rule_with_no_proof_is_left_to_write_one_for(self):
        made = Project(spec=SPEC_WITH_A_THIRD_RULE)
        try:
            # No proof, and one passing test marked with the rule's own id.
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login RULE-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made, extra=[('RULE-3', 'RULE-3',
                                  'test_a_locked_account_returns_423')])
            commit_all(made)
            key(made.root)
            package = signed_package(made)
            third = rule_of(package, 'RULE-3')
            assert third['text'] == 'A locked account returns 423 (URS-042)'
            assert third['proofs'] == []
            assert [r['result'] for r in third['results']] == ['passed']
            assert third['left'] == 'no_proof'
            assert package['left'][0] == line(
                'no_proof', 1, '1 rule to write a proof for', 'purlin:spec')
        finally:
            made.close()

    # purlin: package PROOF-55
    def test_it_states_met_and_claims_no_compliance(self, signed):
        assert list(signed.package) == TOP_LEVEL
        assert signed.package['met'] is True
        assert words_naming_compliance(signed.package) == []
        # A key or a value naming it anywhere in the package is found.
        assert words_naming_compliance(
            {'rules': [{'note': 'Compliant with Part 11'}],
             'compliance': None}) == ['Compliant with Part 11', 'compliance']


# ---------------------------------------------------------------------------
# The content
# ---------------------------------------------------------------------------

class TestTheContent:

    # purlin: package PROOF-9
    def test_one_rule_carries_its_words_its_proof_and_its_test(self, signed):
        rule = rule_of(signed.package, 'RULE-2')
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

    # purlin: package PROOF-18
    def test_a_rule_with_no_proof_carries_the_tests_marked_with_its_id(self):
        made = Project(spec=SPEC_WITH_A_THIRD_RULE)
        try:
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login RULE-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made, extra=[('RULE-3', 'RULE-3',
                                  'test_a_locked_account_returns_423')])
            commit_all(made)
            key(made.root)
            package = signed_package(made)
            third = rule_of(package, 'RULE-3')
            assert third['proofs'] == []
            assert third['tests'] == [{
                'proof': 'RULE-3', 'file': 'tests/test_login.py',
                'name': 'test_a_locked_account_returns_423'}]
            assert [r['result'] for r in third['results']] == ['passed']
            assert [t['proof'] for t in rule_of(package, 'RULE-2')['tests']] \
                == ['PROOF-2']
        finally:
            made.close()

    # purlin: package PROOF-25
    def test_a_remote_runners_result_names_its_machine(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            here = purlin_evidence.host_os()
            machine = 'remote runner, %s' % purlin_evidence.os_word(here)
            ran_at = made.head()
            passing(made, source='ci', os_name=here, machine=machine)
            commit_all(made, 'purlin: results pulled home')
            key(made.root)
            [result] = rule_of(signed_package(made), 'RULE-2')['results']
            assert (result['source'], result['result'], result['runner'],
                    result['at'], result['current'], result['os'],
                    result['machine'], result['commit']) == (
                'ci', 'passed', 'ci', '2026-09-13T12:00:00Z', True, here,
                machine, ran_at)
        finally:
            made.close()

    # purlin: package PROOF-26
    def test_one_rule_carries_what_the_audit_found(self, signed):
        audit = rule_of(signed.package, 'RULE-2')['audit']
        assert (audit['verdict'], audit['findings'], audit['model'],
                audit['criteria'], audit['at']) == (
            'strong', [], MODEL, CRITERIA, '2026-09-13T12:05:00Z')

    # purlin: package PROOF-20
    def test_a_strong_rule_carries_passed_and_strong(self, signed):
        statuses = rule_of(signed.package, 'RULE-1')['statuses']
        assert {name: cell['word'] for name, cell in statuses.items()} == {
            'passed': 'passed', 'strong': 'strong'}

    # purlin: package PROOF-29
    def test_a_rule_no_audit_read_carries_passed_and_not_audited(self):
        made = made_project(strong=())
        try:
            statuses = rule_of(signed_package(made), 'RULE-2')['statuses']
            assert {name: cell['word'] for name, cell in statuses.items()} == {
                'passed': 'passed', 'strong': 'not audited'}
        finally:
            made.close()

    # purlin: package PROOF-15
    def test_every_time_is_utc(self, signed):
        times = []

        def walk(value):
            if isinstance(value, dict):
                for name, item in value.items():
                    if name == 'at' and item is not None:
                        times.append(item)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(signed.package)
        assert len(times) >= 4
        assert [t for t in times if not UTC.match(t)] == []

    # purlin: package PROOF-61
    def test_the_package_counts_what_the_audit_found(self):
        made = made_project(strong=('RULE-1',), weak=('RULE-2',))
        try:
            assert signed_package(made)['audit'] == {
                'strong': 1, 'weak': 1, 'not_audited': 0}
        finally:
            made.close()

    # purlin: package PROOF-62
    def test_a_hand_check_is_listed_in_the_sign_offs(self):
        made = made_project(spec=MANUAL_SPEC, test_file=MANUAL_TEST_FILE,
                            strong=())
        try:
            assert signed_package(made)['hand_checks'] == [
                {'feature': 'login', 'rule': 'RULE-2', 'proofs': ['PROOF-2'],
                 'checked': 'in the sign-offs'}]
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------

class TestAnchors:

    # purlin: package PROOF-56
    def test_a_feature_entry_holds_five_fields(self, signed):
        entry = next(feature for feature in signed.package['features']
                     if feature['name'] == 'login')
        assert sorted(entry) == ['anchor', 'name', 'rules', 'scope', 'spec']
        assert (entry['name'], entry['spec'], entry['scope'],
                entry['anchor']) == ('login', 'specs/auth/login.md',
                                     ['src/login.py'], False)

    # purlin: package PROOF-57
    def test_an_anchors_scope_is_empty(self, project):
        write(os.path.join(project.root, 'specs', '_anchors', 'secure.md'),
              '# Anchor: secure\n\n'
              '> Description: What every feature does with a password.\n'
              '> Scope: src/login.py\n\n'
              '## Rules\n\n'
              '- RULE-1: A password is never written to a log\n\n'
              '## Proof\n\n'
              '- PROOF-1 (RULE-1): A sign-in with the password "secret" '
              'leaves no line holding "secret" in the log @manual\n')
        commit_all(project, 'spec(secure): the anchor')
        passing(project)
        commit_all(project)
        entry = next(feature for feature in signed_package(project)['features']
                     if feature['name'] == 'secure')
        assert (entry['anchor'], entry['scope']) == (True, [])

    # purlin: package PROOF-72
    def test_a_proof_with_nothing_to_check_carries_its_reason(self, project):
        write(os.path.join(project.root, 'specs', '_anchors', 'screens.md'),
              '# Anchor: screens\n\n'
              '> Description: Every screen.\n\n'
              '## Rules\n\n'
              '- RULE-1: For every screen in the project, its colours pass '
              'contrast\n\n'
              '## Proof\n\n'
              '- PROOF-3 (RULE-1): For every screen, verify a contrast of 7 to '
              '1\n')
        write(os.path.join(project.root, 'tests', 'test_screens.py'),
              '# purlin: screens PROOF-3\n'
              'def test_contrast():\n'
              '    assert True\n')
        commit_all(project, 'spec(screens): the anchor')
        passing(project)
        section(project, [('PROOF-3', 'RULE-1', 'nothing to check',
                           'test_contrast', 'this project has no screens')],
                {'RULE-1': 'passed'}, feature='screens')
        commit_all(project)
        [result] = rule_of(signed_package(project), 'RULE-1',
                           'screens')['results']
        assert (result['os'], result['result'], result['nothing_to_check']) \
            == ('linux', 'passed', [{'proof': 'PROOF-3',
                                     'reason': 'this project has no screens'}])


# ---------------------------------------------------------------------------
# The runs and the same code
# ---------------------------------------------------------------------------

WINDOWS_SPEC = SPEC + (
    '- PROOF-3 (RULE-1): POST /login on Windows; verify 200 @env(windows)\n')
WINDOWS_TEST_FILE = TEST_FILE + (
    '\n\n# purlin: login PROOF-3\n'
    'def test_windows_sign_in():\n'
    '    assert login("ada", "secret") == 200\n')


class TestTheRuns:

    # purlin: package PROOF-65
    def test_one_local_run_is_one_entry(self, project):
        ran_at = git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        runs = signed_package(project)['runs']
        assert runs == [{'by': 'dana.dev@labconnect.example',
                         'machine': 'dana-laptop', 'os': 'linux',
                         'source': 'local', 'at': AT, 'commit': ran_at,
                         'rules': 2}]

    # purlin: package PROOF-66
    def test_a_remote_run_follows_the_local_one(self):
        made = Project(spec=WINDOWS_SPEC)
        try:
            made.edit_test(WINDOWS_TEST_FILE)
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            section(made, [('PROOF-1', 'RULE-1', 'pass',
                            TEST_NAMES['PROOF-1'], None),
                           ('PROOF-2', 'RULE-2', 'pass',
                            TEST_NAMES['PROOF-2'], None),
                           ('PROOF-3', 'RULE-1', 'not run',
                            'test_windows_sign_in', None)],
                    {'RULE-1': 'not run', 'RULE-2': 'passed'})
            section(made, [('PROOF-3', 'RULE-1', 'pass',
                            'test_windows_sign_in', None)],
                    {'RULE-1': 'passed'}, source='ci', os_name='windows',
                    machine='remote runner, Windows')
            commit_all(made)
            key(made.root)
            runs = signed_package(made)['runs']
            assert [(run['by'], run['source'], run['os']) for run in runs] == [
                (DANA, 'local', 'linux'), ('a remote runner', 'ci', 'windows')]
            assert runs[1]['rules'] == 1
        finally:
            made.close()

    # purlin: package PROOF-67
    def test_results_pulled_home_after_are_the_same_code(self, project):
        ran_at = git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        section(project, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'],
                           None)], {'RULE-1': 'passed'}, source='ci',
                os_name='windows', machine='remote runner, Windows',
                commit=ran_at)
        commit_all(project, 'purlin: results pulled home')
        assert changed_in_head(project.root) == [
            '.purlin/evidence/ci/login.json']
        package = signed_package(project)
        found = [result['same_code'] for feature in package['features']
                 for rule in feature['rules'] for result in rule['results']]
        assert len(found) == 3 and all(found)

    # purlin: package PROOF-68
    def test_a_change_outside_the_records_after_the_run_is_refused(
            self, project):
        write(os.path.join(project.root, 'README.md'), '# Login\n')
        commit_all(project, 'docs: a readme')
        before = project.head()
        code, lines = sign(project)
        assert (code, lines) == (1, [
            'No sign-off: these results were not taken on this version of the '
            'code, %s: login on Linux/Unix. Run purlin:test --all --commit, '
            'then purlin:sign.' % before[:7]])
        assert project.head() == before

    # purlin: package PROOF-69
    def test_the_project_is_named_by_its_own_files(self, tmp_path):
        made = Project()
        try:
            work = str(tmp_path / 'work')
            shutil.copytree(made.root, work)
            made.close()
            made.root = work
            write(os.path.join(work, 'pyproject.toml'),
                  '[project]\nname = "labconnect"\n')
            write(os.path.join(work, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: pyproject')
            passing(made)
            commit_all(made)
            key(made.root)
            assert signed_package(made)['project'] == 'labconnect'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The bytes
# ---------------------------------------------------------------------------

def two_clones(made, autocrlf=False):
    """Two clones of the project, each in a folder of the same name, each
    with a signer of its own."""
    parent = tempfile.mkdtemp()
    clones = []
    for index, (email, name) in enumerate(((QUINN, 'Quinn'), (PAT, 'Pat'))):
        clone = os.path.join(parent, str(index), 'labconnect')
        os.makedirs(os.path.dirname(clone))
        args = ['clone', '-q']
        if autocrlf:
            args += ['-c', 'core.autocrlf=true']
        done = git(parent, *(args + [made.root, clone]))
        assert done.returncode == 0, done.stderr
        git(clone, 'config', 'commit.gpgsign', 'false')
        key(clone, email=email, name=name)
        clones.append(Project.__new__(Project))
        clones[-1].root = clone
    return parent, clones


class TestTheBytes:

    # purlin: package PROOF-13
    def test_two_clones_at_one_commit_give_the_same_bytes(self, project):
        parent, clones = two_clones(project)
        try:
            written = []
            for clone in clones:
                assert sign(clone)[0] == 0
                written.append(git_bytes(clone.root, 'show', 'HEAD:' + PACKAGE))
            assert written[0] == written[1]
            assert written[0].endswith(b'}\n') and b'\r' not in written[0]
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    # purlin: package PROOF-39
    @pytest.mark.skipif(os.name != 'nt', reason='core.autocrlf is Windows git')
    def test_on_windows_two_clones_give_the_same_bytes(self, project):
        parent, clones = two_clones(project, autocrlf=True)
        try:
            written = []
            for clone in clones:
                assert sign(clone)[0] == 0
                written.append(git_bytes(clone.root, 'show', 'HEAD:' + PACKAGE))
            assert written[0] == written[1]
            assert b'\r' not in written[0]
        finally:
            shutil.rmtree(parent, ignore_errors=True)


# ---------------------------------------------------------------------------
# The fingerprint
# ---------------------------------------------------------------------------

class TestTheFingerprint:

    # purlin: package PROOF-32
    def test_the_fingerprint_is_the_sha256_with_it_emptied(self, signed):
        data = git_bytes(signed.root, 'show', 'HEAD:' + PACKAGE)
        recorded = json.loads(data.decode('utf-8'))['fingerprint']
        assert re.match(r'^[0-9a-f]{64}$', recorded), recorded
        assert recorded == fingerprint_by_hand(data)

    # purlin: package PROOF-17
    def test_check_names_an_edit_made_after(self, signed, capsys):
        path = os.path.join(signed.root, *PACKAGE.split('/'))
        with open(path, 'rb') as handle:
            data = handle.read()
        edited = data.replace(b'"passed"', b'"failed"', 1)
        assert edited != data
        with open(path, 'wb') as handle:
            handle.write(edited)
        code, lines = check(path, capsys)
        recorded = json.loads(data.decode('utf-8'))['fingerprint']
        gives = fingerprint_by_hand(edited)
        assert recorded != gives
        assert code == 1
        assert lines[0] == ('The package does not match its fingerprint: the '
                            'package records the fingerprint %s and its '
                            'content gives %s.' % (recorded, gives))

    # purlin: package PROOF-45
    def test_check_names_a_file_that_is_not_utf8_json(self, tmp_path, capsys):
        for name, data in (('latin.json', b'{"schema": "caf\xe9"}\n'),
                           ('text.json', b'not a package\n')):
            path = str(tmp_path / name)
            with open(path, 'wb') as handle:
                handle.write(data)
            assert check(path, capsys) == (
                1, [CHECK_FAILED % 'the file is not UTF-8 JSON']), name

    # purlin: package PROOF-46
    def test_check_names_another_schema(self, signed, capsys):
        path = os.path.join(signed.root, *PACKAGE.split('/'))
        package = dict(signed.package, schema='purlin-package/3')
        write(path, json.dumps(package, indent=2) + '\n')
        assert check(path, capsys) == (1, [
            CHECK_FAILED % 'the file does not carry the schema purlin-package/4'])


# ---------------------------------------------------------------------------
# Who wrote and last changed each rule, proof and test
# ---------------------------------------------------------------------------

# `login` before Quinn writes `PROOF-1`.
SPEC_WITHOUT_PROOF_1 = SPEC.replace(
    '- PROOF-1 (RULE-1): POST /login with the password "secret"; verify 200 '
    'and a token\n', '')


class TestTheAuthors:

    # purlin: package PROOF-74
    def test_a_reworded_proof_names_who_wrote_it_and_who_changed_it(self):
        made = Project(spec=SPEC_WITHOUT_PROOF_1)
        try:
            made.spec(SPEC)
            commit_all(made, 'spec(login): PROOF-1', author=QUINN)
            quinns = made.head()
            made.spec(SPEC.replace('verify 200 and a token',
                                   'verify 200 and a session token'))
            commit_all(made, 'spec(login): reword PROOF-1', author=PAT)
            pats = made.head()
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made)
            commit_all(made)
            key(made.root)
            [proof] = rule_of(signed_package(made), 'RULE-1')['authors'][
                'proofs']
            assert (proof['id'], proof['written_by'], proof['written_commit'],
                    proof['changed_by'], proof['changed_commit']) == (
                'PROOF-1', QUINN, quinns, PAT, pats)
        finally:
            made.close()

    # purlin: package PROOF-75
    def test_a_test_names_who_last_changed_it(self):
        made = Project()
        try:
            made.edit_test(TEST_FILE.replace('== 200', '== 200  # the token'))
            git(made.root, 'commit', '-q', '--amend', '--no-edit',
                '--author', 'Dana <%s>' % DANA)
            danas = made.head()
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made)
            commit_all(made)
            key(made.root)
            tests = rule_of(signed_package(made), 'RULE-1')['authors']['tests']
            assert [(test['name'], test['file'], test['changed_by'],
                     test['changed_commit']) for test in tests] == [
                ('test_valid_credentials_return_200', 'tests/test_login.py',
                 DANA, danas)]
        finally:
            made.close()

    # purlin: package PROOF-76
    def test_a_renumbered_rule_names_who_first_wrote_its_words(self):
        made = Project()
        try:
            fourth = SPEC.replace(
                '\n\n## Proof',
                '\n- RULE-4: A locked account returns 423\n\n## Proof') + (
                '- PROOF-3 (RULE-4): Lock the account; verify 423\n')
            made.spec(fourth)
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login PROOF-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
            git(made.root, 'commit', '-q', '--amend', '--no-edit',
                '--author', 'Pat <%s>' % PAT)
            pats = made.head()
            made.spec(fourth.replace('RULE-4', 'RULE-6'))
            commit_all(made, 'spec(login): renumber RULE-4 to RULE-6',
                       author=DANA)
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made, extra=[('PROOF-3', 'RULE-6',
                                  'test_a_locked_account_returns_423')])
            commit_all(made)
            key(made.root)
            assert rule_of(signed_package(made), 'RULE-6')['authors'][
                'rule'] == {'written_by': PAT, 'commit': pats}
        finally:
            made.close()
