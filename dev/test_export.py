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
              os.path.join(ROOT, 'scripts', 'review'),
              os.path.join(ROOT, 'scripts', 'export'), DEV):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import package as purlin_package  # noqa: E402
import sign as sign_module  # noqa: E402
from purlin import PURLIN_VERSION  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from sign_project import (AI_SPEC, AI_TEST_FILE,  # noqa: E402
                          AI_TEST_NAMES, CRITERIA, GRADER, MODEL, OPUS,
                          REASON, REPORT_BYTES, REPORT_FROM, SONNET, SPEC,
                          TEST_FILE, TEST_NAMES, Project, _Out, ai_runs,
                          ai_sha, git, name_a_report, name_the_model,
                          name_the_models, report_sha, reported_for, write)

TOP_LEVEL = ['schema', 'met', 'rules', 'steps', 'audit', 'left',
             'purlin_version', 'project', 'version', 'tag', 'commit', 'runs',
             'features', 'hand_checks', 'outputs', 'warnings', 'fingerprint']

UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

EMAIL = 'jane@acme.com'
DANA = 'dana.dev@labconnect.example'
QUINN = 'quinn.qa@labconnect.example'
PAT = 'pat.product@labconnect.example'
MACHINE = 'dana-laptop'
# The git email a project's own run on another system set.
RUNNER = 'runner@example.com'
AT = '2026-09-13T12:00:00Z'
PACKAGE = '.purlin/evidence/package/2.1.0.json'

CHECK_FAILED = 'The package does not match its fingerprint: %s.'

# A rule with a requirement's number in its words and no proof at all.
SPEC_WITH_A_THIRD_RULE = SPEC.replace(
    '\n\n## Proof',
    '\n- RULE-3: A locked account returns 423 (URS-042)\n\n## Proof')

# Four rules: two tested, a third tested and never audited, a fourth checked
# by hand alone.
FOUR_RULES_SPEC = SPEC.replace(
    '\n\n## Proof',
    '\n- RULE-3: A locked account returns 423\n'
    '- RULE-4: The lockout page says how long the lock lasts\n\n## Proof'
) + ('- PROOF-3 (RULE-3): POST /login to a locked account; verify 423\n'
     '- PROOF-4 (RULE-4): Read the lockout page against the support guide '
     '@manual\n')

# `PROOF-2` is a hand check, and no test carries it.
MANUAL_SPEC = SPEC.replace('verify 401 and the body "denied"',
                           'verify 401 and the body "denied" @manual')
MANUAL_TEST_FILE = TEST_FILE.split('\n\n\n# purlin: login PROOF-2')[0] + '\n'


# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------

def section(made, proofs, rules, source='local', os_name='linux', email=DANA,
            machine=MACHINE, at=AT, commit=None, feature='login',
            carried=None):
    """One evidence section, as the run writes it, over the project as it stands.

    `proofs` is `[(id, rule, result, test name or None, reason or None)]`;
    `rules` is `{RULE-N: word}`. A section has the same fields under either
    source. `carried` is `{PROOF-N: where its test really ran}`, for a
    result the section's own run carried forward.
    """
    entries = []
    for proof_id, rule, result, name, reason in proofs:
        entry = {'id': proof_id, 'rule': rule, 'result': result, 'env': None,
                 'manual': False,
                 'test': 'tests/test_%s.py::%s' % (feature, name) if name
                 else ''}
        if reason is not None:
            entry['reason'] = reason
        if proof_id in (carried or {}):
            entry['carried'] = dict(carried[proof_id])
        entries.append(entry)
    found = {'commit': commit or made.head(), 'dirty': False, 'at': at,
             'runner': email.split('@')[0], 'email': email,
             'machine': machine,
             'fingerprint': purlin_fingerprint.fingerprint(made.root, feature),
             'rules': dict(rules), 'proofs': entries}
    rel = '.purlin/evidence/%s/%s.json' % (source, feature)
    path = os.path.join(made.root, *rel.split('/'))
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        data = {'schema': purlin_evidence.SCHEMA, 'feature': feature,
                'source': source,
                'spec': 'specs/auth/%s.md' % feature
                if feature in ('login', 'feat')
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
    def test_the_seventeen_top_level_keys_come_in_order(self, project):
        holds_the_evidence = project.head()
        package = signed_package(project)
        assert len(package) == 17
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
    def test_a_package_folder_that_is_a_file_ends_on_one_line_no_commit_no_tag(
            self, project, capsys):
        folder = os.path.join(project.root, '.purlin', 'evidence', 'package')
        write(folder, 'not a folder\n')
        try:
            os.makedirs(folder, exist_ok=True)
        except (IOError, OSError) as error:
            reason = str(error)
        else:
            raise AssertionError('%s became a folder' % folder)
        before = project.head()
        capsys.readouterr()
        code, lines = sign(project)
        assert code == 1
        named = ('The evidence package was not written: %s. Nothing was '
                 'signed; run purlin:sign again.' % reason)
        assert [text for text in lines if reason in text] == [named]
        # One line: it is the last the walk prints, after the empty line
        # that closes what the walk showed, and nothing is printed beside
        # it anywhere else.
        assert lines[-2:] == ['', named], lines
        printed = capsys.readouterr()
        assert (printed.out, printed.err) == ('', ''), printed
        assert project.head() == before
        assert git(project.root, 'tag', '--list').stdout == ''
        assert git(project.root, 'tag', '--list').stdout == ''


# ---------------------------------------------------------------------------
# Met, the count and what is left
# ---------------------------------------------------------------------------

class TestMet:

    # purlin: package PROOF-8
    def test_two_rules_that_pass_are_met(self, signed):
        package = signed.package
        assert (package['met'], package['rules'], package['steps'],
                package['left']) == (True, 2, {'passed': 2, 'graded': 0}, [])

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
            'ai': [], 'graded': None, 'runs': None, 'models': [],
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
            assert rule_of(package, 'RULE-2')['tests'] == [{
                'proof': 'PROOF-2', 'file': 'tests/test_login.py',
                'name': 'test_a_bad_password_is_denied'}]
        finally:
            made.close()

    # purlin: package PROOF-25
    def test_a_result_under_ci_names_its_machine(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            here = purlin_evidence.host_os()
            ran_at = made.head()
            passing(made, source='ci', os_name=here, email=RUNNER,
                    machine='build-7')
            commit_all(made, 'purlin: results pulled home')
            key(made.root)
            [result] = rule_of(signed_package(made), 'RULE-2')['results']
            assert (result['source'], result['result'], result['runner'],
                    result['at'], result['current'], result['os'],
                    result['machine'], result['commit']) == (
                'ci', 'passed', 'runner', '2026-09-13T12:00:00Z', True, here,
                'build-7', ran_at)
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
    def test_every_time_is_utc(self, project):
        TestTheRuns()._feat_carried(project)
        package = signed_package(project)
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
        walk(package)
        assert len(times) >= 5
        assert '2026-09-13T11:00:00Z' in times, times
        # The whole of each, with nothing after the `Z`.
        assert [t for t in times if not UTC.fullmatch(t)] == []

    # purlin: package PROOF-61
    def test_the_package_counts_what_the_audit_found(self):
        made = made_project(strong=('RULE-1',), weak=('RULE-2',))
        try:
            assert signed_package(made)['audit'] == {
                'strong': 1, 'weak': 1, 'spot_checked': 0, 'out_of_date': 0,
                'not_audited': 0}
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

    # purlin: package PROOF-82
    def test_the_audit_counts_only_rules_that_pass_and_have_a_tested_proof(
            self):
        made = Project(spec=FOUR_RULES_SPEC)
        try:
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login PROOF-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            section(made, [(proof_id, 'RULE-%s' % proof_id[-1], 'pass', name,
                            None) for proof_id, name in (
                                ('PROOF-1', TEST_NAMES['PROOF-1']),
                                ('PROOF-2', TEST_NAMES['PROOF-2']),
                                ('PROOF-3',
                                 'test_a_locked_account_returns_423'))],
                    {'RULE-1': 'passed', 'RULE-2': 'passed',
                     'RULE-3': 'passed', 'RULE-4': 'passed'})
            made.audit('RULE-1')
            made.audit('RULE-2')
            commit_all(made)
            key(made.root)
            package = signed_package(made)
            assert package['rules'] == 4
            assert package['audit'] == {
                'strong': 2, 'weak': 0, 'spot_checked': 0, 'out_of_date': 0,
                'not_audited': 1}
        finally:
            made.close()

    # purlin: package PROOF-83
    def test_a_rule_checked_by_hand_alone_never_reads_passed(self):
        made = made_project(spec=MANUAL_SPEC, test_file=MANUAL_TEST_FILE,
                            strong=())
        try:
            evidence = json.loads(git_bytes(
                made.root, 'show',
                'HEAD:.purlin/evidence/local/login.json').decode('utf-8'))
            assert evidence['platforms']['linux']['rules']['RULE-2'] == 'passed'
            package = signed_package(made)
            assert [result['result'] for result
                    in rule_of(package, 'RULE-2')['results']] == [
                'checked at sign-off']
            assert [result['result'] for result
                    in rule_of(package, 'RULE-1')['results']] == ['passed']
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


# `feat`, whose second proof is slow.
FEAT_SPEC = (
    '# Feature: feat\n\n'
    '> Description: A feature with a slow proof.\n'
    '> Scope: src/feat.py\n\n'
    '## Rules\n\n'
    '- RULE-1: The feature answers 1\n'
    '- RULE-2: The feature settles against the sandbox\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Call it; verify 1\n'
    '- PROOF-2 (RULE-2): Settle against the sandbox; verify `paid` @slow\n')
FEAT_TEST = (
    'from src.feat import feat\n'
    '\n'
    '\n'
    '# purlin: feat PROOF-1\n'
    'def test_feat():\n'
    '    assert feat() == 1\n'
    '\n'
    '\n'
    '# purlin: feat PROOF-2\n'
    'def test_slow():\n'
    '    assert feat() == 1\n')


class TestTheRuns:

    # purlin: package PROOF-65
    def test_one_local_run_is_one_entry(self, project):
        ran_at = git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        runs = signed_package(project)['runs']
        assert runs == [{'by': 'dana.dev@labconnect.example',
                         'machine': 'dana-laptop', 'os': 'linux',
                         'source': 'local', 'at': AT, 'commit': ran_at,
                         'rules': 2, 'carried': False}]

    # purlin: package PROOF-66
    def test_a_run_under_ci_follows_the_local_one(self):
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
                    email=RUNNER, machine='build-7')
            commit_all(made)
            key(made.root)
            runs = signed_package(made)['runs']
            assert len(runs) == 2
            assert (runs[0]['by'], runs[0]['source']) == (DANA, 'local')
            assert (runs[1]['by'], runs[1]['machine'], runs[1]['source'],
                    runs[1]['os'], runs[1]['rules']) == (
                'runner@example.com', 'build-7', 'ci', 'windows', 1)
        finally:
            made.close()

    # purlin: package PROOF-67
    def test_results_pulled_home_after_are_the_same_code(self, project):
        ran_at = git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        section(project, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'],
                           None)], {'RULE-1': 'passed'}, source='ci',
                os_name='windows', email=RUNNER, machine='build-7',
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
            'No sign-off: these results are not recorded on this version of '
            'the code, %s: login on Linux/Unix. Run purlin:test --all --commit, '
            'then purlin:sign.' % before[:7]])
        assert project.head() == before

    # purlin: package PROOF-77
    def test_a_changed_test_command_after_the_run_is_refused(self, project):
        project.config(tests=[{'name': 'pytest', 'run': 'pytest -x {files}',
                               'report': None, 'format': 'junit',
                               'files': ['tests/test_*.py']}])
        commit_all(project, 'chore: the test command')
        assert changed_in_head(project.root) == ['.purlin/config.json']
        before = project.head()
        code, lines = sign(project)
        assert len(lines) == 1, lines
        assert lines[0].startswith('No sign-off: these results are not '
                                   'recorded on this version of the code'), lines
        assert (code, project.head()) == (1, before)

    # purlin: package PROOF-78
    def test_results_from_a_commit_head_does_not_hold_are_refused(
            self, project):
        git(project.root, 'switch', '-q', '-c', 'other')
        git(project.root, 'commit', '-q', '--allow-empty', '-m',
            'chore: another branch')
        elsewhere = project.head()
        git(project.root, 'switch', '-q', 'main')
        assert git(project.root, 'diff', '--name-only', elsewhere,
                   'HEAD').stdout == ''
        assert git(project.root, 'merge-base', '--is-ancestor', elsewhere,
                   'HEAD').returncode == 1
        passing(project, commit=elsewhere)
        commit_all(project)
        before = project.head()
        code, lines = sign(project)
        assert len(lines) == 1, lines
        assert lines[0].startswith('No sign-off: these results are not '
                                   'recorded on this version of the code'), lines
        assert (code, project.head()) == (1, before)

    def _feat_carried(self, project):
        """`feat`, its slow `PROOF-2` taken by Pat at `<c>` and carried into
        a section Dana's run recorded on the commit after it. `(<c>, that
        commit)`."""
        write(os.path.join(project.root, 'specs', 'auth', 'feat.md'),
              FEAT_SPEC)
        write(os.path.join(project.root, 'src', 'feat.py'),
              'def feat():\n    return 1\n')
        write(os.path.join(project.root, 'tests', 'test_feat.py'), FEAT_TEST)
        commit_all(project, 'feat(feat): the feature')
        ran_at = project.head()
        write(os.path.join(project.root, 'README.md'), '# Login\n')
        commit_all(project, 'docs: a readme')
        recorded = project.head()
        passing(project)
        section(project, [('PROOF-1', 'RULE-1', 'pass', 'test_feat', None),
                          ('PROOF-2', 'RULE-2', 'pass', 'test_slow', None)],
                {'RULE-1': 'passed', 'RULE-2': 'passed'}, feature='feat',
                carried={'PROOF-2': {'commit': ran_at,
                                     'at': '2026-09-13T11:00:00Z',
                                     'machine': 'pat-laptop', 'email': PAT}})
        commit_all(project)
        return ran_at, recorded

    # purlin: package PROOF-79
    def test_a_result_carried_from_an_earlier_run_counts(
            self, project, capsys):
        self._feat_carried(project)
        feat = next(entry for entry in project.payload()['features']
                    if entry['name'] == 'feat')
        assert [rule['cells']['passed']['word'] for rule in feat['rules']] \
            == ['passed', 'passed']
        code = sign_module.main(['--show', '--project-root', project.root])
        lines = capsys.readouterr().out.splitlines()
        assert code == 0, lines
        assert not any(line.startswith('No sign-off') for line in lines)

    # purlin: package PROOF-84
    def test_a_result_names_each_proof_carried_and_the_run_that_took_it(
            self, project):
        ran_at, _recorded = self._feat_carried(project)
        package = signed_package(project)
        (slow,) = rule_of(package, 'RULE-2', 'feat')['results']
        assert slow['carried'] == [{
            'proof': 'PROOF-2', 'commit': ran_at,
            'at': '2026-09-13T11:00:00Z', 'machine': 'pat-laptop',
            'email': PAT}], slow
        assert slow['commit'] != ran_at and slow['same_code'] is True, slow
        (plain,) = rule_of(package, 'RULE-1', 'feat')['results']
        assert plain['carried'] == [], plain

    # purlin: package PROOF-85
    def test_carried_results_are_a_run_of_their_own(self, project):
        ran_at, recorded = self._feat_carried(project)
        runs = signed_package(project)['runs']
        assert [(run['by'], run['machine'], run['commit'], run['at'],
                 run['rules'], run['carried']) for run in runs] == [
            (DANA, MACHINE, recorded, AT, 3, False),
            (PAT, 'pat-laptop', ran_at, '2026-09-13T11:00:00Z', 1, True)]

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

    # purlin: package PROOF-81
    def test_a_stray_tag_in_one_clone_leaves_the_bytes_the_same(self, project):
        parent, clones = two_clones(project)
        try:
            done = git(clones[1].root, 'tag', 'signed/9.9.9')
            assert done.returncode == 0, done.stderr
            written = []
            for clone in clones:
                assert sign(clone)[0] == 0
                written.append(git_bytes(clone.root, 'show', 'HEAD:' + PACKAGE))
            assert written[0] == written[1]
            for data in written:
                assert not [line for line in json.loads(data)['warnings']
                            if 'signed/9.9.9' in line]
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
        edited = data.replace(b'"met": true', b'"met": false', 1)
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
                1, ['The package does not match its fingerprint: the file is '
                    'not UTF-8 JSON.']), name

    # purlin: package PROOF-80
    def test_check_names_bytes_not_in_the_canonical_form(self, signed, capsys):
        path = os.path.join(signed.root, *PACKAGE.split('/'))
        with open(path, 'rb') as handle:
            data = handle.read()
        assert b'\r' not in data
        with open(path, 'wb') as handle:
            handle.write(data.replace(b'\n', b'\r\n'))
        assert check(path, capsys) == (1, [
            CHECK_FAILED % 'the fingerprint matches the content, but the '
                           'bytes are not in the canonical form'])

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
                'rule'] == {'written_by': PAT, 'commit': pats,
                            'co_authors': []}
        finally:
            made.close()


# What a commit made with an AI's help ends on, and one a person is named in,
# its key in lower case.
CLAUDE = 'Claude Opus 5.5 <noreply@anthropic.com>'
QUINN_NAMED = 'Quinn <%s>' % QUINN


def commit_with(made, subject, trailers, author=None):
    """Commit everything under `subject`, the message ending on `trailers`."""
    git(made.root, 'add', '-A')
    args = ['-c', 'user.email=%s' % author] if author else []
    done = git(made.root, *(args + ['commit', '-q', '-m', subject, '-m',
                                    '\n'.join(trailers)]))
    assert done.returncode == 0, done.stderr


class TestTheCoAuthors:

    # purlin: package PROOF-86
    def test_a_proofs_last_change_names_its_commits_co_authors(self):
        made = Project(spec=SPEC_WITHOUT_PROOF_1)
        try:
            made.spec(SPEC)
            commit_all(made, 'spec(login): PROOF-1', author=QUINN)
            made.spec(SPEC.replace('verify 200 and a token',
                                   'verify 200 and a session token'))
            commit_with(made, 'spec(login): reword PROOF-1',
                        ['Co-Authored-By: %s' % CLAUDE,
                         'co-authored-by: %s' % QUINN_NAMED], author=DANA)
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made)
            commit_all(made)
            key(made.root)
            [proof] = rule_of(signed_package(made), 'RULE-1')['authors'][
                'proofs']
            assert proof['changed_by'] == DANA
            assert proof['changed_co_authors'] == [CLAUDE, QUINN_NAMED]
            assert proof['written_co_authors'] == []
        finally:
            made.close()

    # purlin: package PROOF-87
    def test_a_tests_last_change_names_its_commits_co_authors(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'tests', 'test_login.py'),
                  TEST_FILE.replace('== 200', '== 200  # the token'))
            commit_with(made, 'test(login): the token',
                        ['Co-Authored-By: %s' % CLAUDE], author=DANA)
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made)
            commit_all(made)
            key(made.root)
            package = signed_package(made)
            found = {test['name']: test['changed_co_authors']
                     for rule in ('RULE-1', 'RULE-2')
                     for test in rule_of(package, rule)['authors']['tests']}
            assert found == {'test_valid_credentials_return_200': [CLAUDE],
                             'test_a_bad_password_is_denied': []}
        finally:
            made.close()

    # purlin: package PROOF-88
    def test_a_rule_names_the_co_authors_of_the_commit_that_wrote_it(self):
        made = Project()
        try:
            made.spec(SPEC.replace(
                '\n\n## Proof',
                '\n- RULE-3: A locked account returns 423\n\n## Proof'))
            commit_with(made, 'spec(login): RULE-3',
                        ['Co-Authored-By: %s' % CLAUDE], author=PAT)
            pats = made.head()
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            passing(made)
            commit_all(made)
            # Built, not signed: a sign-off refuses this project.
            package = purlin_package.build(made.root, '2.1.0')
            assert rule_of(package, 'RULE-3')['authors']['rule'] == {
                'written_by': PAT, 'commit': pats, 'co_authors': [CLAUDE]}
            assert rule_of(package, 'RULE-1')['authors']['rule'][
                'co_authors'] == []
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What the test tool reported, and the reports kept with the package
# ---------------------------------------------------------------------------

KEPT = '.purlin/evidence/package/2.1.0.outputs/reports/%s.xml' % report_sha()


def reported_project(keep=True):
    """Both rules pass on Dana's laptop, each result naming one report, the
    report's bytes on this machine where `keep`; `VERSION` reads 2.1.0."""
    made = Project()
    write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
    commit_all(made, 'chore: version')
    passing(made)
    name_a_report(made, keep=keep)
    commit_all(made)
    key(made.root)
    return made


class TestWhatTheTestToolReported:

    # purlin: package PROOF-89
    def test_each_result_lists_its_tests_with_what_the_report_held(self):
        made = reported_project()
        try:
            package = signed_package(made)
            [result] = rule_of(package, 'RULE-2')['results']
            assert result['tests'] == [{
                'proof': 'PROOF-2',
                'test': 'tests/test_login.py::test_a_bad_password_is_denied',
                'result': 'pass',
                'reported': {
                    'cases': [{'name': 'test_a_bad_password_is_denied',
                               'class': 'tests.test_login',
                               'outcome': 'pass', 'duration': 0.25}],
                    'report': {'file': REPORT_FROM,
                               'sha256': report_sha()}}}]
        finally:
            made.close()

    # purlin: package PROOF-90
    def test_a_result_the_evidence_keeps_no_report_for_reads_null(self,
                                                                  signed):
        [result] = rule_of(signed.package, 'RULE-1')['results']
        assert result['tests'] == [{
            'proof': 'PROOF-1',
            'test': 'tests/test_login.py::test_valid_credentials_return_200',
            'result': 'pass', 'reported': None}]
        assert signed.package['outputs'] == []

    # purlin: package PROOF-91
    def test_outputs_lists_each_report_the_results_name(self):
        made = reported_project()
        try:
            package = signed_package(made)
            assert package['outputs'] == [{
                'kind': 'report', 'file': KEPT, 'sha256': report_sha(),
                'from': REPORT_FROM, 'tests': 2}]
            assert list(package).index('outputs') == list(package).index(
                'hand_checks') + 1
        finally:
            made.close()

    # purlin: package PROOF-92
    def test_a_clone_with_no_report_builds_the_same_bytes(self):
        made = reported_project()
        parent, clones = two_clones(made)
        try:
            # The first clone holds the report its results name; the second
            # holds none.
            kept = os.path.join(clones[0].root, '.purlin', 'runtime', 'kept',
                                report_sha() + '.xml')
            os.makedirs(os.path.dirname(kept))
            with open(kept, 'wb') as handle:
                handle.write(REPORT_BYTES)
            written, changed = [], []
            for clone in clones:
                assert sign(clone)[0] == 0
                written.append(git_bytes(clone.root, 'show', 'HEAD:' + PACKAGE))
                changed.append(KEPT in changed_in_head(clone.root))
            assert written[0] == written[1]
            assert changed == [True, False]
        finally:
            shutil.rmtree(parent, ignore_errors=True)
            made.close()


class TestCheckingTheKeptReports:

    @staticmethod
    def _signed():
        made = reported_project()
        code, lines = sign(made)
        assert code == 0, lines
        return made

    # purlin: package PROOF-93
    def test_check_counts_the_reports_that_match(self, capsys):
        made = self._signed()
        try:
            path = os.path.join(made.root, *PACKAGE.split('/'))
            assert check(path, capsys) == (0, [
                'The package matches its fingerprint.',
                'Reports beside the package that match their sha256: 1 of '
                '1.'])
        finally:
            made.close()

    # purlin: package PROOF-94
    def test_check_names_a_report_changed_after(self, capsys):
        made = self._signed()
        try:
            with open(os.path.join(made.root, *KEPT.split('/')), 'ab') as kept:
                kept.write(b'<!-- edited -->')
            gives = hashlib.sha256(REPORT_BYTES
                                   + b'<!-- edited -->').hexdigest()
            path = os.path.join(made.root, *PACKAGE.split('/'))
            assert check(path, capsys) == (1, [
                'The package matches its fingerprint.',
                'Reports beside the package that match their sha256: 0 of '
                '1.',
                'A report beside the package does not match it: %s gives the '
                'sha256 %s, and the package records %s.'
                % (KEPT, gives, report_sha())])
        finally:
            made.close()

    # purlin: package PROOF-95
    def test_check_passes_a_package_whose_report_is_not_beside_it(self,
                                                                  capsys,
                                                                  tmp_path):
        made = self._signed()
        try:
            # The package alone, copied to a folder that holds nothing else.
            alone = str(tmp_path / '2.1.0.json')
            shutil.copy(os.path.join(made.root, *PACKAGE.split('/')), alone)
            assert check(alone, capsys) == (0, [
                'The package matches its fingerprint.',
                'Reports beside the package that match their sha256: 0 of '
                '1.'])
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What an AI produced: the run folders of `outputs.py`
# ---------------------------------------------------------------------------

from purlin import outputs as purlin_outputs  # noqa: E402

RUN_ONE = '.purlin/runtime/ai/login/PROOF-4/model-a/1'
RUN_TWO = '.purlin/runtime/ai/login/PROOF-4/model-a/2'


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _folder(root, rel, **files):
    """Write `files`, `{name with __ for /: text}`, under `root/rel`. The
    folder's full path."""
    folder = os.path.join(str(root), *rel.split('/'))
    for name, text in files.items():
        path = os.path.join(folder, *name.split('__'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
    return folder


class TestAiOutputs:
    """The folder one run of an AI proof's test writes, and how it is named,
    found and removed."""

    # purlin: package PROOF-96
    def test_a_run_folder_names_the_feature_the_proof_the_model_and_the_run(
            self):
        assert purlin_outputs.ai_run_dir(
            'login', 'PROOF-4', 'claude-opus-5-5', 2) == (
            '.purlin/runtime/ai/login/PROOF-4/claude-opus-5-5/2')
        assert purlin_outputs.ai_run_dir(
            'login', 'PROOF-4', 'claude-opus-5-5', 2, test=3) == (
            '.purlin/runtime/ai/login/PROOF-4/claude-opus-5-5/2.3')

    # purlin: package PROOF-97
    def test_a_model_name_is_written_as_a_folder_name(self):
        assert purlin_outputs.ai_run_dir(
            'login', 'PROOF-4', 'vendor/model:1', 1) == (
            '.purlin/runtime/ai/login/PROOF-4/vendor_model_1/1')

    # purlin: package PROOF-98
    def test_a_folders_sha256_is_taken_over_one_line_per_file(self, tmp_path):
        folder = _folder(tmp_path, 'out', **{'reply.md': 'hello',
                                             'files__a.txt': 'a'})
        lines = '%s  files/a.txt\n%s  reply.md\n' % (_sha('a'), _sha('hello'))
        assert purlin_outputs.folder_sha256(folder) == _sha(lines)

    # purlin: package PROOF-99
    def test_the_record_is_outside_the_sha256_and_the_reply_inside(
            self, tmp_path):
        folder = _folder(tmp_path, 'out', **{'reply.md': 'hello',
                                             'files__a.txt': 'a'})
        before = purlin_outputs.folder_sha256(folder)
        purlin_outputs.write_record(folder, {'made': 'helper'})
        assert os.path.isfile(os.path.join(folder, 'purlin.json'))
        assert purlin_outputs.folder_sha256(folder) == before
        _folder(tmp_path, 'out', **{'reply.md': 'hullo'})
        after = purlin_outputs.folder_sha256(folder)
        assert after != before and len(after) == 64

    # purlin: package PROOF-100
    def test_a_folder_holding_the_record_alone_has_no_sha256(self, tmp_path):
        folder = str(tmp_path / 'out')
        purlin_outputs.write_record(folder, {'reached': False})
        assert os.listdir(folder) == ['purlin.json']
        assert purlin_outputs.folder_sha256(folder) is None

    # purlin: package PROOF-101
    def test_a_record_is_read_back_and_a_missing_one_reads_empty(
            self, tmp_path):
        record = {'made': 'helper', 'model': 'model-a', 'reached': True,
                  'why': None}
        folder = str(tmp_path / 'out')
        purlin_outputs.write_record(folder, record)
        assert purlin_outputs.read_record(folder) == record
        assert purlin_outputs.read_record(str(tmp_path / 'none')) == {}
        other = _folder(tmp_path, 'other', **{'purlin.json': '[1]'})
        assert purlin_outputs.read_record(other) == {}

    # purlin: package PROOF-102
    def test_a_kept_folder_is_found_by_its_sha256(self, tmp_path):
        _folder(tmp_path, RUN_ONE, **{'reply.md': 'other'})
        folder = _folder(tmp_path, RUN_TWO, **{'reply.md': 'hello'})
        sha = purlin_outputs.folder_sha256(folder)
        assert purlin_outputs.ai_held(str(tmp_path), sha) == RUN_TWO

    # purlin: package PROOF-103
    def test_a_folder_changed_since_is_not_found(self, tmp_path):
        folder = _folder(tmp_path, RUN_TWO, **{'reply.md': 'hello'})
        sha = purlin_outputs.folder_sha256(folder)
        _folder(tmp_path, RUN_TWO, **{'reply.md': 'hullo'})
        assert purlin_outputs.ai_held(str(tmp_path), sha) is None

    # purlin: package PROOF-104
    def test_a_prune_removes_the_folder_no_evidence_names(self, tmp_path):
        named = _folder(tmp_path, RUN_ONE, **{'reply.md': 'kept'})
        _folder(tmp_path, RUN_TWO, **{'reply.md': 'dropped'})
        _folder(tmp_path, '.purlin/evidence/local', **{
            'login.json': json.dumps(
                {'output': purlin_outputs.folder_sha256(named)})})
        removed = purlin_outputs.prune(str(tmp_path))
        assert removed == [RUN_TWO]
        assert os.listdir(named) == ['reply.md']
        assert os.listdir(os.path.dirname(named)) == ['1']

    # purlin: package PROOF-105
    def test_a_prune_removes_the_folders_it_left_empty(self, tmp_path):
        _folder(tmp_path, '.purlin/runtime/ai/gone/PROOF-1/model-a/1',
                **{'reply.md': 'dropped'})
        purlin_outputs.prune(str(tmp_path))
        assert os.listdir(os.path.join(
            str(tmp_path), '.purlin', 'runtime', 'ai')) == []

    # purlin: package PROOF-106
    def test_the_proofs_own_runs_win_over_the_setting(self):
        assert purlin_outputs.runs_asked({'runs': 10}, 5) == 10
        assert purlin_outputs.runs_asked({'runs': None}, 5) == 5
        assert purlin_outputs.runs_asked({'runs': None}, None) == 3


# ---------------------------------------------------------------------------
# AI proofs: the models, the runs and the outputs kept with the package
# ---------------------------------------------------------------------------

AI_OUTPUTS = '.purlin/evidence/package/2.1.0.outputs/ai-outputs'
# Every run of the project `ai_project` makes, as `(proof, model, run)`.
AI_RUNS = ([('PROOF-3', OPUS, run) for run in (1, 2, 3)]
           + [('PROOF-4', model, run) for model in (OPUS, SONNET)
              for run in (1, 2)])
AI_SHAS = sorted(ai_sha(*run) for run in AI_RUNS)
THE_GRADE = {'model': GRADER, 'accepted': True, 'reason': REASON}
AI_CHECKED = 'AI outputs beside the package that match their sha256: %d of %d.'
AI_DIFFERS = ('An AI output beside the package does not match it: %s gives '
              'the sha256 %s, and the package records %s.')


def ai_project(keep=True, models=None, strong=(), report=False):
    """`login` with two AI proofs beside its two, every rule passing on
    Dana's laptop: `PROOF-3` on 3 runs on one model, `PROOF-4` on 2 runs on
    each of two, graded. `models` is `{PROOF-N: its models}` in place of
    those. With `report` the first run of `PROOF-3` names one report."""
    made = Project(spec=AI_SPEC)
    made.edit_test(AI_TEST_FILE)
    write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
    commit_all(made, 'chore: version')
    passing(made, extra=[(proof_id, 'RULE-%s' % proof_id[-1], name)
                         for proof_id, name in sorted(AI_TEST_NAMES.items())])
    held = {'PROOF-3': [ai_runs(made, 'PROOF-3', OPUS, 3, keep=keep)],
            'PROOF-4': [ai_runs(made, 'PROOF-4', model, 2, GRADER, keep=keep)
                        for model in (OPUS, SONNET)]}
    held.update(models or {})
    if report:
        held['PROOF-3'][0]['runs'][0]['reported'] = reported_for(
            'tests/test_login.py::' + AI_TEST_NAMES['PROOF-3'], report_sha())
    for proof_id, found in held.items():
        name_the_models(made, proof_id, found)
    for rule in strong:
        made.audit(rule)
    commit_all(made)
    key(made.root)
    made.models = held
    return made


def folder_sha(root, rel):
    """An output folder's sha256, worked out here from the files under it:
    every file but `purlin.json`, as `sha256sum` prints them."""
    folder = os.path.join(root, *rel.split('/'))
    lines = []
    for dirpath, _dirnames, names in os.walk(folder):
        for name in names:
            path = os.path.join(dirpath, name)
            inside = os.path.relpath(path, folder).replace(os.sep, '/')
            if inside == 'purlin.json':
                continue
            with open(path, 'rb') as handle:
                lines.append((inside, hashlib.sha256(
                    handle.read()).hexdigest()))
    return hashlib.sha256(''.join(
        '%s  %s\n' % (sha, inside)
        for inside, sha in sorted(lines)).encode('utf-8')).hexdigest()


class TestTheModelsOfAnAIProof:

    # purlin: package PROOF-107
    def test_a_graded_proof_carries_its_models_and_every_run(self):
        made = ai_project()
        try:
            [proof] = rule_of(signed_package(made), 'RULE-4')['proofs']
            assert proof == {
                'id': 'PROOF-4',
                'text': 'With the sample lockout, the reply blames no one',
                'manual': False, 'env': None, 'ai': [OPUS, SONNET],
                'graded': GRADER, 'runs': 2,
                'models': [{
                    'model': model, 'word': 'graded', 'passed': 2, 'of': 2,
                    'runs': [{'result': 'pass', 'made': 'helper',
                              'output': ai_sha('PROOF-4', model, run),
                              'grade': THE_GRADE} for run in (1, 2)]}
                    for model in (OPUS, SONNET)]}
        finally:
            made.close()

    # purlin: package PROOF-108
    def test_an_ai_proof_no_model_grades_reads_passed_on_its_model(self):
        made = ai_project()
        try:
            [proof] = rule_of(signed_package(made), 'RULE-3')['proofs']
            assert (proof['ai'], proof['graded'], proof['runs']) == (
                [OPUS], None, 3)
            assert proof['models'] == [{
                'model': OPUS, 'word': 'passed', 'passed': 3, 'of': 3,
                'runs': [{'result': 'pass', 'made': 'helper',
                          'output': ai_sha('PROOF-3', OPUS, run)}
                         for run in (1, 2, 3)]}]
        finally:
            made.close()

    # purlin: package PROOF-109
    def test_a_result_carries_the_models_as_the_evidence_keeps_them(self):
        made = ai_project(report=True)
        try:
            [result] = rule_of(signed_package(made), 'RULE-3')['results']
            kept = made.models['PROOF-3']
            assert kept[0]['runs'][0]['reported']['report']['sha256'] == \
                report_sha()
            assert result['tests'] == [{
                'proof': 'PROOF-3',
                'test': 'tests/test_login.py::test_the_reply_names_the_wait',
                'result': 'pass', 'reported': None, 'models': kept}]
        finally:
            made.close()

    # purlin: package PROOF-110
    def test_a_graded_rule_is_counted_as_one_that_passes(self):
        made = ai_project(strong=('RULE-4',))
        try:
            package = signed_package(made)
            assert package['steps'] == {'passed': 4, 'graded': 1}
            assert rule_of(package, 'RULE-4')['statuses']['passed'][
                'word'] == 'graded'
            assert package['audit'] == {'strong': 1, 'weak': 0,
                                        'spot_checked': 0, 'out_of_date': 0,
                                        'not_audited': 3}
        finally:
            made.close()

    # purlin: package PROOF-111
    def test_a_model_with_no_result_is_left_to_test(self):
        made = Project(spec=AI_SPEC)
        try:
            made.edit_test(AI_TEST_FILE)
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made, 'chore: version')
            section(made, [
                ('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'], None),
                ('PROOF-2', 'RULE-2', 'pass', TEST_NAMES['PROOF-2'], None),
                ('PROOF-3', 'RULE-3', 'pass', AI_TEST_NAMES['PROOF-3'], None),
                ('PROOF-4', 'RULE-4', 'not run', AI_TEST_NAMES['PROOF-4'],
                 None)],
                {'RULE-1': 'passed', 'RULE-2': 'passed', 'RULE-3': 'passed',
                 'RULE-4': 'not run'})
            name_the_models(made, 'PROOF-3',
                            [ai_runs(made, 'PROOF-3', OPUS, 3)])
            name_the_models(made, 'PROOF-4',
                            [ai_runs(made, 'PROOF-4', OPUS, 2, GRADER)])
            commit_all(made)
            # Built, not signed: a sign-off refuses this project.
            package = purlin_package.build(made.root, '2.1.0')
            assert package['met'] is False
            assert package['left'] == [{
                'kind': 'to_test_model', 'count': 1,
                'text': '1 rule to test on %s' % SONNET,
                'command': 'purlin:test --all', 'model': SONNET}]
            assert rule_of(package, 'RULE-4')['left'] == 'to_test_model'
        finally:
            made.close()


class TestTheAIOutputsListed:

    # purlin: package PROOF-112
    def test_outputs_lists_each_folder_and_each_report_a_run_names(self):
        made = ai_project(report=True)
        try:
            assert signed_package(made)['outputs'] == [
                {'kind': 'ai-output', 'file': '%s/%s' % (AI_OUTPUTS, sha),
                 'sha256': sha, 'runs': 1} for sha in AI_SHAS] + [
                {'kind': 'report', 'file': KEPT, 'sha256': report_sha(),
                 'from': REPORT_FROM, 'tests': 1}]
        finally:
            made.close()

    # purlin: package PROOF-113
    def test_two_runs_that_name_one_folder_are_listed_once(self):
        same = ai_sha('PROOF-3', OPUS, 1)
        made = ai_project(models={'PROOF-3': [{
            'model': OPUS, 'passed': 3, 'of': 3, 'graded': False,
            'runs': [{'result': 'pass', 'made': 'helper', 'output': sha}
                     for sha in (same, same, ai_sha('PROOF-3', OPUS, 3))]}]})
        try:
            listed = [item for item in signed_package(made)['outputs']
                      if item['sha256'] == same]
            assert listed == [{'kind': 'ai-output', 'sha256': same,
                               'file': '%s/%s' % (AI_OUTPUTS, same),
                               'runs': 2}]
        finally:
            made.close()


class TestCheckingTheKeptAIOutputs:

    @staticmethod
    def _signed(**kwargs):
        made = ai_project(**kwargs)
        code, lines = sign(made)
        assert code == 0, lines
        return made

    @staticmethod
    def _path(made):
        return os.path.join(made.root, *PACKAGE.split('/'))

    def _differs(self, made, capsys, change):
        """Change the first listed folder with `change(its full path)`, then
        check the package: the three lines a folder that differs gives."""
        folder = '%s/%s' % (AI_OUTPUTS, AI_SHAS[0])
        change(os.path.join(made.root, *folder.split('/')))
        gives = folder_sha(made.root, folder)
        assert gives != AI_SHAS[0]
        assert check(self._path(made), capsys) == (1, [
            'The package matches its fingerprint.', AI_CHECKED % (6, 7),
            AI_DIFFERS % (folder, gives, AI_SHAS[0])])

    # purlin: package PROOF-114
    def test_check_counts_the_folders_that_match(self, capsys):
        made = self._signed()
        try:
            assert check(self._path(made), capsys) == (0, [
                'The package matches its fingerprint.', AI_CHECKED % (7, 7)])
        finally:
            made.close()

    # purlin: package PROOF-115
    def test_check_names_a_folder_with_one_file_changed(self, capsys):
        made = self._signed()
        try:
            def change(folder):
                with open(os.path.join(folder, 'reply.md'), 'w',
                          encoding='utf-8') as handle:
                    handle.write('edited')
            self._differs(made, capsys, change)
        finally:
            made.close()

    # purlin: package PROOF-116
    def test_check_names_a_folder_with_one_file_missing(self, capsys):
        made = self._signed()
        try:
            self._differs(made, capsys, lambda folder: os.remove(
                os.path.join(folder, 'transcript.jsonl')))
        finally:
            made.close()

    # purlin: package PROOF-117
    def test_check_names_a_folder_with_one_file_added(self, capsys):
        made = self._signed()
        try:
            self._differs(made, capsys, lambda folder: write(
                os.path.join(folder, 'files', 'more.txt'), 'more\n'))
        finally:
            made.close()

    # purlin: package PROOF-118
    def test_the_record_is_no_part_of_a_folders_sha256(self, capsys):
        made = self._signed()
        try:
            write(os.path.join(made.root, *AI_OUTPUTS.split('/'), AI_SHAS[0],
                               'purlin.json'), '{"made": "project"}\n')
            assert check(self._path(made), capsys) == (0, [
                'The package matches its fingerprint.', AI_CHECKED % (7, 7)])
        finally:
            made.close()

    # purlin: package PROOF-119
    def test_check_passes_a_package_whose_folders_are_not_beside_it(
            self, capsys, tmp_path):
        made = self._signed()
        try:
            alone = str(tmp_path / '2.1.0.json')
            shutil.copy(self._path(made), alone)
            assert check(alone, capsys) == (0, [
                'The package matches its fingerprint.', AI_CHECKED % (0, 7)])
        finally:
            made.close()

    # purlin: package PROOF-120
    def test_check_counts_the_reports_then_the_folders(self, capsys):
        made = ai_project(report=True)
        try:
            kept = os.path.join(made.root, '.purlin', 'runtime', 'kept',
                                report_sha() + '.xml')
            os.makedirs(os.path.dirname(kept), exist_ok=True)
            with open(kept, 'wb') as handle:
                handle.write(REPORT_BYTES)
            code, lines = sign(made)
            assert code == 0, lines
            assert check(self._path(made), capsys) == (0, [
                'The package matches its fingerprint.',
                'Reports beside the package that match their sha256: 1 of '
                '1.', AI_CHECKED % (7, 7)])
        finally:
            made.close()
