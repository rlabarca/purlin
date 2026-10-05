"""Tests for the cells of each rule, the payload and the status table.

What the cells of each rule read, what the payload and the status table say
about it, the sign-off on HEAD or behind it, a test comment whose proof was
reworded, and a spec whose scope names files not written yet. The throwaway
project and its helpers are in `dev/mcp_project.py`.
"""

import json
import os
import shutil
import tempfile

import pytest

from mcp_project import (NO_PROOF_SPEC, PROJECT_ROOT, Project, SPEC,
                         _commit_tests, _entry, _git, _listed, _marked_tests,
                         _write, project, spec_with_a_hand_check)
from sign_project import _Out, signing_key
# `mcp_project` puts `scripts/mcp` on the path, `sign_project` `scripts/review`.
import sign as sign_module
from purlin import payload as purlin_payload
from purlin import states as purlin_states
from purlin import status as purlin_status


# One rule proved by two proofs.
TWO_PROOFS_SPEC = (
    '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200\n'
    '- PROOF-2 (RULE-1): POST /login with valid credentials; verify a '
    'token\n')


# An anchor of one rule, which covers the whole project.
SECURITY_ANCHOR = (
    '# Anchor: security\n\n'
    '## Rules\n\n- RULE-1: No eval anywhere\n\n'
    '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n')

PASSING = [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
           {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}]

SIGN_OPTIONAL = ('Every rule passes its tests on the committed evidence. Optional: '
             'sign this version with purlin:sign')


def _dashboard_data(root):
    """The payload `.purlin/report-data.js` holds, as the page reads it."""
    path = os.path.join(root, '.purlin', 'report-data.js')
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    prefix, suffix = 'const PURLIN_DATA = ', ';\n'
    assert text.startswith(prefix) and text.endswith(suffix), text[:80]
    return json.loads(text[len(prefix):-len(suffix)])


def _feature(payload, name='login'):
    return next(f for f in payload['features'] if f['name'] == name)


def _commit(root, message):
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', message)


def _ready_to_sign(made, proof_ids=('PROOF-1', 'PROOF-2'),
                   signer='jane@acme.com'):
    """Commit a marked test and a passing result for each proof, then set
    up `signer`'s throwaway key, so the walk has nothing to refuse."""
    _commit_tests(made, *proof_ids)
    made.evidence([_entry(proof_id, proof_id.replace('PROOF', 'RULE'))
                   for proof_id in proof_ids])
    signing_key(made.root, signer)


def _walk_signs(made, version, answers=('y',)):
    """`purlin:sign --version <version>`, walked with `answers` in order:
    the sign-off's commit and `signed/<version>` on it."""
    left, out = list(answers), _Out()
    code = sign_module.walk(
        made.root, version, out=out,
        ask=lambda _kind, _key, _prompt: left.pop(0) if left else None)
    assert code == 0, out.text()


def _listed_with_no_test(project, missing):
    """A current local section passing `PROOF-1` of `RULE-1` and listing
    `missing` of the same rule as `missing` with no test named, as a run
    writes a proof it found no test for."""
    rel = project.evidence([_entry('PROOF-1', 'RULE-1'),
                            _entry(missing, 'RULE-1', status='missing')],
                           commit_it=False)
    path = os.path.join(project.root, *rel.split('/'))
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    for section in data['platforms'].values():
        for entry in section['proofs']:
            if entry['id'] == missing:
                entry['test'] = ''
    _write(path, json.dumps(data, indent=2, sort_keys=True))


def _skipped_with_nothing_to_check(project, rel, proof_id, reason):
    """Rewrite a written section so `proof_id`'s test skipped with
    `nothing to check: <reason>`, as a run records it."""
    path = os.path.join(project.root, *rel.split('/'))
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    for section in data['platforms'].values():
        for entry in section['proofs']:
            if entry['id'] == proof_id:
                entry['result'] = 'nothing to check'
                entry['reason'] = reason
    _write(path, json.dumps(data, indent=2, sort_keys=True))


def _section(source='ci', os_name='linux', statuses=None, current=True,
             at='2026-09-13T12:00:00Z', commit='a' * 40, out_of_date=()):
    """One checked section, as `evidence.checked_sections` hands it over."""
    statuses = statuses or {'PROOF-1': 'pass'}
    return {'source': source, 'os': os_name,
            'path': '.purlin/evidence/%s/login.json' % source,
            'current': current, 'out_of_date': list(out_of_date),
            'section': {'commit': commit, 'at': at,
                        'proofs': [{'id': proof_id, 'rule': 'RULE-1',
                                    'result': status,
                                    'test': 'tests/test_login.py::test_%s'
                                    % proof_id.lower().replace('-', '_')}
                                   for proof_id, status in statuses.items()]}}


ONE_TESTED_PROOF = [{'id': 'PROOF-1', 'manual': False, 'env': None,
                     'text': 'x', 'tests': [{'file': 'tests/t.py',
                                             'name': 'test_x'}]}]


# ---------------------------------------------------------------------------
# A rule with no proof
# ---------------------------------------------------------------------------

class TestARuleWithNoProof:

    # purlin: states PROOF-1
    def test_no_proof_written_reads_no_test(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n- RULE-1: It works\n'
                     '- RULE-2: It fails\n\n## Proof\n\n'
                     '- PROOF-1 (RULE-2): Call it; verify 401\n')
        rule = project.rule('RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no proof written'], cell
        assert rule['proofs'] == []
        assert rule['flags']['no_proof'] is True
        assert project.rule('RULE-2')['flags']['no_proof'] is False

    TWO_RULES_NO_PROOF = ('# Feature: login\n\n> Scope: src/login.py\n\n'
                          '## Rules\n\n- RULE-1: It works\n- RULE-2: It fails'
                          '\n\n## Proof\n\n')

    # purlin: states PROOF-77
    def test_a_test_marked_with_the_rule_answers_the_passed_cell(self,
                                                                 project):
        project.spec(self.TWO_RULES_NO_PROOF)
        project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1', 'status': 'pass'},
                          {'id': 'RULE-2', 'rule': 'RULE-2', 'status': 'fail'}],
                         commit_it=False)
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        assert project.cell('RULE-2', 'passed')['word'] == 'failed'

    # purlin: states PROOF-139
    def test_a_rule_with_a_passing_test_and_no_proof_reads_no_proof(self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            made.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                            'status': 'pass'}], commit_it=False)
            rule = made.rule('RULE-1')
        finally:
            made.close()
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['cells']['strong']['word'] == 'no proof', rule
        assert rule['left'] == 'no_proof', rule['left']


# ---------------------------------------------------------------------------
# The passed cell
# ---------------------------------------------------------------------------

class TestThePassedCell:

    # purlin: states PROOF-3
    def test_an_uncommitted_local_section_reads_passed_from_local(self,
                                                                 project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert (cell['source'], cell['current'], cell['counts']) == (
            'local', True, True)

    # purlin: states PROOF-151
    def test_every_proof_of_the_rule_must_pass(self, project):
        project.spec(SPEC + '- PROOF-3 (RULE-2): POST /login with no '
                     'password; verify 401\n')
        _commit_tests(project, 'PROOF-2', 'PROOF-3')
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'not run', cell

    # purlin: states PROOF-5
    def test_a_current_section_in_the_ci_folder_reads_passed_from_ci(
            self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], source='ci')
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed', cell
        assert cell['source'] == 'ci', cell
        assert cell['counts'] is True, cell

    # purlin: states PROOF-7
    def test_a_test_report_with_no_evidence_leaves_not_run(self, project):
        """A test marked for PROOF-2 and a report in which it passed: `not run`."""
        marked = _marked_tests('PROOF-2')
        name = marked.split('def ', 1)[1].split('(', 1)[0]
        _write(os.path.join(project.root, 'tests', 'test_login.py'), marked)
        assert project.cell('RULE-2', 'passed')['word'] == 'not run', (
            'the marked test has not run')
        _write(os.path.join(project.root, '.purlin', 'runtime', 'reports',
                            'pytest.xml'),
               '<testsuite tests="1" failures="0" errors="0">'
               '<testcase classname="tests.test_login" name="%s" '
               'file="tests/test_login.py"/></testsuite>' % name)
        assert project.cell('RULE-2', 'passed')['word'] == 'not run', (
            'a test report is not evidence: with it read, the cell would '
            'read `passed`')

    WINDOWS_LOCK_SPEC = (
        '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
        '- RULE-1: Files lock\n\n'
        '## Proof\n\n- PROOF-1 (RULE-1): Lock a file; verify a second open '
        'returns 0 handles @env(windows)\n')

    # purlin: states PROOF-8
    def test_an_env_proof_needs_a_section_from_that_operating_system(
            self, project):
        project.spec(self.WINDOWS_LOCK_SPEC)
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], os_name='linux')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'not run'
        assert cell['missing_env'] == ['windows'], cell
        assert 'Windows: no run yet' in cell['reasons'], cell

    # purlin: states PROOF-153
    def test_an_env_proof_passed_on_its_own_system_reads_passed(
            self, project):
        project.spec(self.WINDOWS_LOCK_SPEC)
        for os_name, at in (('linux', '2026-09-13T12:00:00Z'),
                            ('windows', '2026-09-13T13:00:00Z')):
            project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                               'status': 'pass'}], os_name=os_name, at=at)
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'

    @staticmethod
    def _code_rewritten_after_a_pass(project):
        """A committed passing section, then the scoped code rewritten and
        committed. The section's commit."""
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}])
        seen = _git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 200  # rewritten\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'refactor: login')
        return seen

    # purlin: states PROOF-9
    def test_out_of_date_when_the_code_moved(self, project):
        seen = self._code_rewritten_after_a_pass(project)
        rule = project.rule('RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell
        assert cell['current'] is False, cell
        assert rule['flags']['out_of_date'] is True
        assert rule['left'] == 'to_test', rule['left']

    # purlin: states PROOF-117
    def test_the_next_run_clears_out_of_date(self, project):
        self._code_rewritten_after_a_pass(project)
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}])
        rule = project.rule('RULE-1')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['flags']['out_of_date'] is False, rule

    # purlin: states PROOF-119
    def test_a_test_edit_leaves_it_out_of_date(self, project):
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert True\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'test(login): proof 1')
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], commit_it=False)
        seen = project.head()
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert 1\n')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['tests changed since %s' % seen[:7]], cell

    # purlin: states PROOF-205
    def test_a_rule_one_of_whose_proofs_no_test_backs_reads_no_test(
            self, project):
        project.spec(TWO_PROOFS_SPEC)
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1')], commit_it=False)
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no test for PROOF-2'], cell
        assert (cell['source'], cell['current'], cell['counts']) == (
            None, False, False), cell

    # purlin: states PROOF-221
    def test_a_proof_listed_with_no_test_named_reads_no_test(self, project):
        project.spec(TWO_PROOFS_SPEC)
        _commit_tests(project, 'PROOF-1')
        _listed_with_no_test(project, 'PROOF-2')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no test for PROOF-2'], cell


# ---------------------------------------------------------------------------
# The platforms in the passed cell
# ---------------------------------------------------------------------------

ENV_SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a '
    'token\n'
    '- PROOF-2 (RULE-1): On Windows, POST /login with valid credentials and '
    'read the token file; verify it holds exactly the 200 response\'s token '
    'value @env(windows)\n'
)


class TestThePlatformsInThePassedCell:

    # purlin: states PROOF-51
    def test_a_linux_and_a_windows_ci_section_list_both_platforms(self,
                                                                  project):
        project.evidence(PASSING, os_name='linux', source='ci')
        project.evidence(PASSING, os_name='windows', source='ci',
                         at='2026-09-13T13:00:00Z')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'passed', cell
        assert sorted(cell['platforms']) == ['linux', 'windows'], cell
        assert cell['platforms']['linux'] == {
            'word': 'passed', 'source': 'ci',
            'at': '2026-09-13T12:00:00Z'}, cell
        assert cell['platforms']['windows'] == {
            'word': 'passed', 'source': 'ci',
            'at': '2026-09-13T13:00:00Z'}, cell

    # purlin: states PROOF-52
    def test_a_windows_proof_with_only_a_linux_section_lists_windows_not_run(
            self):
        made = Project(spec=ENV_SPEC)
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], os_name='linux', source='ci')
            cell = made.cell('RULE-1', 'passed')
        finally:
            made.close()
        assert cell['platforms']['windows'] == {
            'word': 'not run', 'source': None, 'at': None}, cell
        assert cell['platforms']['linux']['word'] == 'passed', cell

    # purlin: states PROOF-53
    def test_linux_passing_and_windows_failing_the_second_reads_partial(self):
        made = Project(spec=ENV_SPEC)
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], os_name='linux', source='ci')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-1',
                            'status': 'fail'}],
                          os_name='windows', source='ci',
                          at='2026-09-13T13:00:00Z')
            rule = made.rule('RULE-1')
        finally:
            made.close()
        cell = rule['cells']['passed']
        assert cell['word'] == 'partial', cell
        assert cell['reasons'] == ['passed on Linux/Unix',
                                   'Windows: failed'], cell
        assert rule['bucket'] == 'partial', rule['bucket']
        assert rule['flags']['partial'] is True, rule['flags']
        assert rule['flags']['failing'] is False, rule['flags']
        assert rule['left'] == 'to_fix', rule['left']

    # purlin: states PROOF-54
    def test_an_older_ci_section_out_of_date_is_not_read_beside_a_macos_one(
            self):
        """A failing section two edits old says nothing about this code."""
        cell = purlin_states.rule_cells({
            'proofs': ONE_TESTED_PROOF,
            'sections': [
                _section('ci', 'linux', {'PROOF-1': 'fail'}, current=False,
                         at='2026-09-01T00:00:00Z', out_of_date=['code']),
                _section('local', 'macos', {'PROOF-1': 'pass'},
                         at='2026-09-02T00:00:00Z')],
        })['cells']['passed']
        assert cell['word'] == 'passed', cell
        assert sorted(cell['platforms']) == ['macos'], cell

    # purlin: states PROOF-50
    def test_a_ci_file_whose_source_field_reads_local_is_left_out(self,
                                                                  project):
        path = project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                  'status': 'pass'}],
                                source='ci', claimed_source='local')
        assert path == '.purlin/evidence/ci/login.json'
        data = project.payload()
        cell = _listed(data, 'RULE-1')['cells']['passed']
        assert (cell['word'], cell['source'], cell['platforms']) == (
            'no test', None, {}), cell
        named = [w for w in data['warnings'] if path in w]
        assert len(named) == 1, data['warnings']
        assert 'it is ignored' in named[0], named

    # purlin: states PROOF-66
    def test_a_linux_ci_pass_and_a_macos_local_failure_read_partial(self):
        linux = _section('ci', 'linux', {'PROOF-1': 'pass'},
                         at='2026-09-25T12:00:00Z')
        macos = _section('local', 'macos', {'PROOF-1': 'fail'},
                         at='2026-09-26T12:00:00Z')
        cell = purlin_states.rule_cells({
            'proofs': ONE_TESTED_PROOF, 'sections': [linux, macos],
        })['cells']['passed']
        assert cell['word'] == 'partial', cell
        assert sorted(cell['platforms']) == ['linux', 'macos'], cell
        # The same two sections as a project's evidence files hold them,
        # read through the payload.
        made = Project()
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], source='ci', os_name='linux',
                          at='2026-09-25T12:00:00Z')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'fail'}], source='local',
                          os_name='macos', at='2026-09-26T12:00:00Z')
            read = made.cell('RULE-1', 'passed')
        finally:
            made.close()
        assert read['word'] == 'partial', read
        assert sorted(read['platforms']) == ['linux', 'macos'], read
        assert {name: (entry['word'], entry['source'])
                for name, entry in read['platforms'].items()} == {
            'linux': ('passed', 'ci'), 'macos': ('failed', 'local')}, read


# ---------------------------------------------------------------------------
# The strong cell
# ---------------------------------------------------------------------------

class TestTheStrongCell:

    # purlin: states PROOF-13
    def test_a_rule_no_run_observed_waits_for_its_tests(self, project):
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], source='ci')
        rule = project.rule('RULE-2')
        cell = rule['cells']['strong']
        assert rule['cells']['passed']['word'] == 'no test', rule
        assert cell['word'] == 'waiting', cell
        assert cell['reasons'] == ['waiting for its tests to pass'], cell

    # purlin: states PROOF-159
    def test_a_weak_entry_for_rule_2_carries_its_finding_as_the_reason(
            self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], source='ci')
        project.audit('RULE-2',
                      observations=['The test reads the status code alone.'])
        found = project.cell('RULE-2', 'strong')
        assert found['word'] == 'weak', found
        assert found['reasons'] == [
            'The test reads the status code alone.'], found
        assert found['findings'] == [
            'The test reads the status code alone.'], found

    # purlin: states PROOF-290
    def test_a_spot_checked_entry_says_why_no_bug_was_caught(self, project):
        sentence = ('No bug was planted: the model could not be reached: '
                    'claude is not on PATH.')
        project.evidence([_entry('PROOF-2', 'RULE-2')], source='ci')
        project.audit('RULE-2', word='spot-checked', no_bug=[sentence])
        cell = project.cell('RULE-2', 'strong')
        assert cell['word'] == 'spot-checked', cell
        assert cell['reasons'] == [
            'The spot tests found nothing. No bug was planted: the model '
            'could not be reached: claude is not on PATH.'], cell

    # purlin: states PROOF-19
    def test_before_any_sign_off_a_manual_rule_is_checked_at_sign_off(self):
        result = purlin_states.rule_cells({
            'proofs': [{'id': 'PROOF-1', 'manual': True, 'env': None,
                        'text': 'x', 'tests': []}],
            'sections': [],
        })
        cell = result['cells']['strong']
        assert cell['word'] == 'checked at sign-off', cell
        assert cell['reasons'] == [], cell
        assert result['flags']['manual'] is True, result

    # purlin: states PROOF-264
    def test_a_manual_rule_no_sign_off_has_noted_is_checked_at_sign_off(self):
        manual = ('# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
                  '- RULE-1: The expired tube reads red\n\n## Proof\n\n'
                  '- PROOF-1 (RULE-1): Look at an expired tube; verify it is '
                  'red @manual\n')
        made = Project(spec=manual)
        try:
            rule = made.rule('RULE-1')
        finally:
            made.close()
        cells = rule['cells']
        assert cells['passed']['word'] == 'checked at sign-off', cells
        assert cells['passed']['reasons'] == [
            'no sign-off has checked it yet'], cells
        assert cells['strong']['word'] == 'checked at sign-off', cells
        assert rule['bucket'] == 'by_hand', rule['bucket']

    # purlin: states PROOF-262
    def test_a_weak_audit_leaves_the_rule_passing_and_to_strengthen(
            self, project):
        project.evidence([_entry('PROOF-1', 'RULE-1')])
        project.audit('RULE-1', observations=['PROOF-1 reads 200 alone.'])
        rule = project.rule('RULE-1')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['cells']['strong']['word'] == 'weak', rule
        assert rule['bucket'] == 'passed', rule['bucket']
        assert rule['left'] == 'to_strengthen', rule['left']
        # Counted there: `RULE-1` under `passed`, and `RULE-2`, which has
        # no test, alone under `untested`, in the feature's rollup and in
        # the project's summary.
        data = project.payload()
        for counts in (_feature(data)['rollup'], data['summary']):
            assert {key: counts[key] for key in (
                'rules', 'passed', 'untested', 'failing', 'partial',
                'by_hand', 'weak')} == {
                'rules': 2, 'passed': 1, 'untested': 1, 'failing': 0,
                'partial': 0, 'by_hand': 0, 'weak': 1}, counts


# `RULE-1` of `login` proven by hand and by a test.
HAND_AND_TEST_SPEC = (
    '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Sign in on the screen; verify the name is shown '
    '@manual\n'
    '- PROOF-2 (RULE-1): POST /login with valid credentials; verify 200\n')


class TestAnAuditOutOfDate:

    # purlin: states PROOF-286
    def test_code_rewritten_after_a_strong_audit_reads_out_of_date(
            self, project):
        project.evidence(PASSING)
        project.audit('RULE-2')
        audited_at = project.head()
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 401\n')
        _commit(project.root, 'fix(login): deny')
        project.evidence(PASSING)
        rule = project.rule('RULE-2')
        cell = rule['cells']['strong']
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == [
            'code changed since %s' % audited_at[:7],
            'the last audit found it strong on 2026-09-13'], cell

    # purlin: states PROOF-287
    def test_a_weak_entry_for_another_rule_text_is_out_of_date_and_kept(
            self, project):
        finding = 'The test reads the status code alone.'
        project.evidence([_entry('PROOF-2', 'RULE-2')], source='ci')
        project.audit('RULE-2', rule_hash='0' * 64, observations=[finding])
        rule = project.rule('RULE-2')
        cell = rule['cells']['strong']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'][0] == (
            'rule changed since %s' % project.head()[:7]), cell
        assert cell['findings'] == [finding], cell
        assert rule['left'] is None, rule['left']


class TestAHandCheckTheAuditFoundWeak:

    # purlin: states PROOF-288
    def test_a_hand_check_with_a_tested_proof_found_weak_reads_weak(self):
        finding = 'PROOF-2 reads the status alone.'
        made = Project(spec=HAND_AND_TEST_SPEC)
        try:
            made.evidence([_entry('PROOF-2', 'RULE-1')])
            made.audit('RULE-1', observations=[finding])
            rule = made.rule('RULE-1')
        finally:
            made.close()
        cell = rule['cells']['strong']
        assert cell['word'] == 'weak', cell
        assert finding in cell['reasons'], cell
        assert rule['left'] == 'to_strengthen', rule['left']


class TestAHandCheckReadsTheAuditsWord:

    @staticmethod
    def _rule(**audit):
        made = Project(spec=HAND_AND_TEST_SPEC)
        try:
            made.evidence([_entry('PROOF-2', 'RULE-1')])
            made.audit('RULE-1', **audit)
            return made.rule('RULE-1'), made.head()
        finally:
            made.close()

    # purlin: states PROOF-291
    def test_a_hand_check_the_audit_spot_checked_reads_spot_checked(self):
        sentence = ('No bug was planted: PROOF-2 needs Windows, and this '
                    'machine is macOS.')
        rule, _head = self._rule(word='spot-checked', no_bug=[sentence])
        cell = rule['cells']['strong']
        assert cell['word'] == 'spot-checked', cell
        assert cell['reasons'] == [
            'The spot tests found nothing. ' + sentence], cell
        assert rule['flags']['manual'] is True, rule['flags']

    # purlin: states PROOF-292
    def test_a_hand_check_whose_audit_is_out_of_date_reads_out_of_date(self):
        rule, head = self._rule(rule_hash='0' * 64)
        cell = rule['cells']['strong']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'][0] == 'rule changed since %s' % head[:7], cell

    # purlin: states PROOF-293
    def test_a_hand_check_the_audit_found_strong_is_checked_at_sign_off(self):
        rule, _head = self._rule()
        cell = rule['cells']['strong']
        assert cell['word'] == 'checked at sign-off', cell


# A hand check: `RULE-2` of `login` is proven by hand alone.
MANUAL_SPEC = SPEC.replace('body "denied"\n', 'body "denied" @manual\n')
QUINN = 'quinn.qa@labconnect.example'


def _signed_with_a_note(made, note='the tube is red'):
    """`quinn.qa@labconnect.example` signs `0.1.0` at HEAD with `note` on
    `login RULE-2`, by the walk: the sign-off's commit and `signed/0.1.0`
    on it."""
    _ready_to_sign(made, ('PROOF-1',), signer=QUINN)
    _walk_signs(made, '0.1.0', answers=(note, 'y'))


class TestAHandCheck:

    # purlin: states PROOF-276
    def test_a_note_signed_at_head_reads_at_this_commit(self):
        made = Project(spec=MANUAL_SPEC)
        try:
            _signed_with_a_note(made)
            cell = made.cell('RULE-2', 'strong')
        finally:
            made.close()
        assert cell['word'] == 'checked at sign-off', cell
        assert cell['reasons'] == [
            'noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
            'at this commit: the tube is red'], cell

    # purlin: states PROOF-295
    def test_a_hand_check_noted_at_head_reads_passed_with_the_note(self):
        made = Project(spec=MANUAL_SPEC)
        try:
            _signed_with_a_note(made)
            cell = made.cell('RULE-2', 'passed')
        finally:
            made.close()
        assert cell['word'] == 'passed', cell
        assert cell['reasons'] == [
            'noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
            'at this commit: the tube is red'], cell

    # purlin: states PROOF-296
    def test_a_rule_reworded_since_its_note_is_checked_at_sign_off_again(self):
        note = ('noted at the sign-off of 0.1.0 by '
                'quinn.qa@labconnect.example, 1 commit since: the tube is red')
        result = purlin_states.rule_cells({
            'proofs': [{'id': 'PROOF-1', 'manual': True, 'env': None,
                        'text': 'x', 'tests': []}],
            'sections': [], 'hand_notes': [note], 'hand_changed': ['rule'],
        })
        cell = result['cells']['passed']
        assert cell['word'] == 'checked at sign-off', cell
        assert cell['reasons'] == [
            "the rule's wording changed since its last note", note], cell
        # The same in a project: `RULE-2`, checked by hand alone, is noted
        # at the sign-off of `0.1.0` and reworded in the 1 commit after it.
        made = Project(spec=MANUAL_SPEC)
        try:
            _signed_with_a_note(made)
            _write(os.path.join(made.root, 'specs', 'auth', 'login.md'),
                   MANUAL_SPEC.replace('Invalid credentials return 401',
                                       'Wrong credentials return 401'))
            _commit(made.root, 'spec(login): reword RULE-2')
            read = made.cell('RULE-2', 'passed')
        finally:
            made.close()
        assert read['word'] == 'checked at sign-off', read
        assert read['reasons'] == [
            "the rule's wording changed since its last note",
            'noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
            '1 commit since: the tube is red'], read

    # purlin: states PROOF-297
    def test_a_proof_reworded_since_its_note_says_so_in_the_strong_cell(self):
        note = ('noted at the sign-off of 0.1.0 by '
                'quinn.qa@labconnect.example, 1 commit since: the name shows')
        result = purlin_states.rule_cells({
            'proofs': [{'id': 'PROOF-1', 'manual': True, 'env': None,
                        'text': 'x', 'tests': []}] + [
                            dict(ONE_TESTED_PROOF[0], id='PROOF-2')],
            'sections': [_section(statuses={'PROOF-2': 'pass'})],
            'hand_notes': [note], 'hand_changed': ['proof'],
        })
        cells = result['cells']
        assert cells['passed']['word'] == 'passed', cells
        assert cells['strong']['word'] == 'checked at sign-off', cells
        assert cells['strong']['reasons'] == [
            "the proof's wording changed since its last note", note], cells
        # The same in a project: `RULE-1` of `PROOF-1` marked `@manual` and
        # `PROOF-2` passing is noted at the sign-off of `0.1.0`, then
        # `PROOF-1` is reworded, in 1 commit that holds `PROOF-2`'s result
        # on the reworded spec.
        made = Project(spec=HAND_AND_TEST_SPEC)
        try:
            _commit_tests(made, 'PROOF-2')
            made.evidence([_entry('PROOF-2', 'RULE-1')])
            signing_key(made.root, QUINN)
            _walk_signs(made, '0.1.0', answers=('the name shows', 'y'))
            _write(os.path.join(made.root, 'specs', 'auth', 'login.md'),
                   HAND_AND_TEST_SPEC.replace('verify the name is shown',
                                              'verify the full name is shown'))
            made.evidence([_entry('PROOF-2', 'RULE-1')])
            read = made.rule('RULE-1')['cells']
        finally:
            made.close()
        assert read['passed']['word'] == 'passed', read
        assert read['strong']['word'] == 'checked at sign-off', read
        assert read['strong']['reasons'] == [
            "the proof's wording changed since its last note",
            'noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
            '1 commit since: the name shows'], read

    # purlin: states PROOF-277
    def test_four_commits_after_the_sign_off_the_note_reads_four_since(self):
        made = Project(spec=MANUAL_SPEC)
        try:
            _signed_with_a_note(made)
            for number in range(4):
                _write(os.path.join(made.root, 'src', 'later_%d.py' % number),
                       'X = %d\n' % number)
                _commit(made.root, 'feat(login): step %d' % number)
            cell = made.cell('RULE-2', 'strong')
        finally:
            made.close()
        assert cell['reasons'] == [
            'noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
            '4 commits since: the tube is red'], cell


# ---------------------------------------------------------------------------
# The audit on the rule
# ---------------------------------------------------------------------------

class TestTheAuditOnTheRule:

    # purlin: states PROOF-73
    def test_a_weak_entry_naming_no_model_carries_exactly_eleven_fields(
            self, project):
        project.evidence(PASSING)
        project.audit('RULE-2', observations=['PROOF-2 reads 401 alone.'])
        audit = project.rule('RULE-2')['audit']
        head = project.head()
        assert list(audit) == ['verdict', 'findings', 'no_bug', 'notes',
                               'explanation', 'bugs', 'model', 'at',
                               'commit', 'path', 'out_of_date'], audit
        assert audit['verdict'] == 'weak', audit
        assert audit['findings'] == ['PROOF-2 reads 401 alone.']
        assert audit['no_bug'] == [], audit
        assert audit['out_of_date'] == [], audit
        assert audit['notes'] == [], audit
        assert audit['explanation'] == [], audit
        assert audit['bugs'] == {}, audit
        assert audit['model'] == 'unknown', audit
        assert audit['path'] == '.purlin/evidence/local/login.json'
        assert audit['at'] == '2026-09-13T12:05:00Z', audit
        assert audit['commit'] == head, audit

    # purlin: states PROOF-281
    def test_the_explanation_and_the_planted_bug_are_carried_as_the_entry_holds_them(
            self, project):
        explanation = ['The test calls login and reads no status.']
        bugs = {'PROOF-2': {'file': 'src/login.py', 'line': 12,
                            'before': 'return 401', 'after': 'return 200',
                            'result': 'survived', 'why': '',
                            'bug_key': 'a' * 64}}
        project.evidence(PASSING)
        project.audit('RULE-2', observations=[
            'PROOF-2: the test still passes when src/login.py:12 reads '
            '"return 200"'], explanation=explanation, bugs=bugs)
        audit = project.rule('RULE-2')['audit']
        assert audit['explanation'] == explanation, audit
        assert audit['bugs'] == bugs, audit
        # Value for value: each of the entry's own, of its own type, the
        # line the whole number 12 and no other number equal to it.
        assert audit['explanation'] == [
            'The test calls login and reads no status.'], audit
        assert list(audit['bugs']) == ['PROOF-2'], audit
        carried = audit['bugs']['PROOF-2']
        assert sorted(carried) == ['after', 'before', 'bug_key', 'file',
                                   'line', 'result', 'why'], carried
        assert (carried['file'], carried['before'], carried['after'],
                carried['result']) == ('src/login.py', 'return 401',
                                       'return 200', 'survived'), carried
        assert carried['line'] == 12 and type(carried['line']) is int, carried
        assert json.dumps(audit['bugs'], sort_keys=True) == json.dumps(
            bugs, sort_keys=True), audit


# ---------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------

# One project holding four rules: one per bucket but `partial`, and one the
# audit found strong, so the bucket is read off the same evidence.
FOUR = (
    '# Feature: ledger\n\n'
    '> Description: Four rules, read into their buckets.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A rule with no proof names none\n'
    '- RULE-2: A failing rule has a test that fails\n'
    '- RULE-3: A passed rule has no audit yet\n'
    '- RULE-4: A strong rule has an audit that found nothing\n\n'
    '## Proof\n\n'
    '- PROOF-2 (RULE-2): POST /session with the password "wrong"; verify 401\n'
    '- PROOF-3 (RULE-3): POST /session with the password "secret"; verify 200 '
    'and a rejected second attempt\n'
    '- PROOF-4 (RULE-4): POST /session 5 times with a wrong password; verify '
    '423 and an error body\n'
)


class TestBuckets:

    # purlin: states PROOF-27
    def test_four_rules_read_untested_failing_passed_and_passed(self):
        made = Project(spec=None)
        try:
            made.spec(FOUR, name='ledger', category='core')
            _commit(made.root, 'spec(ledger): four rules')
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'fail'},
                           {'id': 'PROOF-3', 'rule': 'RULE-3',
                            'status': 'pass'},
                           {'id': 'PROOF-4', 'rule': 'RULE-4',
                            'status': 'pass'}], feature='ledger', source='ci')
            made.audit('RULE-4', feature='ledger', word='strong')
            buckets = [made.rule('RULE-%d' % n, 'ledger')['bucket']
                       for n in range(1, 5)]
            strong = made.cell('RULE-4', 'strong', 'ledger')['word']
        finally:
            made.close()
        assert strong == 'strong'
        assert buckets == ['untested', 'failing', 'passed', 'passed'], buckets


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    # purlin: states PROOF-31
    def test_schema_sixteen_carries_exactly_the_seventeen_keys(self, project):
        data = project.payload()
        assert data['schema_version'] == 17
        assert sorted(data) == sorted((
            'schema_version', 'generated_at', 'generated_by', 'project',
            'version', 'branch', 'commit', 'dirty', 'summary', 'features',
            'left', 'met', 'signoff', 'last_line', 'os_words', 'evidence',
            'information', 'warnings')), sorted(data)
        assert len(data) - 1 == 17
        assert data['generated_at'].endswith('Z')

    @staticmethod
    def _an_uncommitted_linux_section(project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False,
                         os_name='linux')

    # purlin: states PROOF-128
    def test_a_feature_says_its_evidence_is_current_and_uncommitted(
            self, project):
        self._an_uncommitted_linux_section(project)
        feature = _feature(project.payload())
        assert feature['current'] is True
        local = feature['evidence']['local']
        assert local['path'] == '.purlin/evidence/local/login.json'
        assert local['committed'] is False
        assert local['platforms'] == {'linux': {
            'commit': project.head(), 'at': '2026-09-13T12:00:00Z',
            'current': True}}
        assert feature['evidence']['ci'] is None

    # purlin: states PROOF-129
    def test_a_feature_says_its_evidence_is_committed(self, project):
        self._an_uncommitted_linux_section(project)
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'purlin: evidence')
        feature = _feature(project.payload())
        assert feature['evidence']['local']['committed'] is True

    # purlin: states PROOF-84
    def test_a_marked_test_that_has_not_run_is_a_test(self, project):
        path = os.path.join(project.root, 'tests', 'test_login.py')
        _write(path, _marked_tests('PROOF-1'))
        data = project.payload()
        rollup = _feature(data)['rollup']
        for counted in (rollup, data['summary']):
            assert counted['proofs_without_test'] == 1, counted
            assert counted['proofs_without_test_ids'] == ['PROOF-2'], counted
        words = {rule['id']: rule['cells']['passed']['word']
                 for f in data['features'] for rule in f['rules']}
        assert words == {'RULE-1': 'not run', 'RULE-2': 'no test'}, words

    # purlin: states PROOF-30
    def test_an_anchors_rules_are_counted_once_in_the_summary(self, project):
        project.spec(SECURITY_ANCHOR, name='security', category='_anchors')
        data = project.payload()
        assert data['summary']['rules'] == 3, (
            'two rules of login and the anchor\'s one, counted once')
        assert data['summary']['features'] == 2

    # purlin: states PROOF-39
    def test_a_section_carries_the_result_of_the_run_it_names(self, project):
        """Two operating systems, one run each: one failed, one passed."""
        project.evidence([{'id': 'PROOF-1', 'status': 'pass'},
                          {'id': 'PROOF-2', 'status': 'fail'}],
                         os_name='linux')
        project.evidence([{'id': 'PROOF-1', 'status': 'pass'},
                          {'id': 'PROOF-2', 'status': 'pass'}],
                         os_name='windows')
        evidence = project.payload()['evidence']['login']
        assert sorted(evidence) == ['local']
        assert evidence['local']['linux']['result'] == 'fail'
        assert evidence['local']['windows']['result'] == 'pass'
        for entry in evidence['local'].values():
            assert len(entry['commit']) == 40
            assert entry['current'] is True
            assert entry['path'] == '.purlin/evidence/local/login.json'

    # purlin: states PROOF-37
    def test_the_data_file_is_a_const_assignment_and_round_trips(self, project):
        data = project.payload()
        path = purlin_payload.write_report_data(project.root, data)
        # The bytes, before a text read on Windows folds `\r\n` into `\n`.
        with open(path, 'rb') as handle:
            raw = handle.read()
        assert raw.endswith(b';\n'), raw[-8:]
        assert b'\r' not in raw, 'the data file holds a carriage return'
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert text.startswith('const PURLIN_DATA = ') and text.endswith(';\n')
        read_back = json.loads(text[len('const PURLIN_DATA = '):-len(';\n')])
        assert read_back['commit'] == data['commit']
        # The whole payload, key for key.
        assert read_back == json.loads(json.dumps(data)), 'not the payload'

    # purlin: states PROOF-98
    def test_two_passing_rules_on_committed_evidence_are_met_and_end_on_sign(
            self, project):
        project.evidence(PASSING)
        data = project.payload()
        assert data['left'] == [], data['left']
        assert data['met'] is True, data
        assert data['signoff']['word'] == 'not signed', data['signoff']
        assert data['last_line'] == SIGN_OPTIONAL, data['last_line']

    # purlin: states PROOF-213
    def test_the_status_text_and_the_dashboard_data_carry_one_answer(
            self, project):
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1')], audited=False)
        text = purlin_status.sync_status(project.root)
        data = _dashboard_data(project.root)
        sentence = '2 rules. 1 passes its tests.'
        assert text.splitlines()[-3:] == [
            sentence, 'Left to do:',
            '  1 rule to write a test for: purlin:build'], text
        assert data['summary']['rules'] == 2
        assert data['summary']['passed'] == 1, data['summary']
        assert data['summary']['untested'] == 1, data['summary']
        assert data['summary']['steps'] == {'passed': 1, 'by_hand': 0}
        assert data['summary']['sentence'] == sentence, data['summary']
        assert [(item['text'], item['command'], item['count'])
                for item in data['left']] == [
            ('1 rule to write a test for', 'purlin:build', 1)]

    # purlin: states PROOF-112
    def test_a_rule_names_the_machine_its_section_ran_on(self, project):
        rel = project.evidence(PASSING, os_name='linux')
        path = os.path.join(project.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        data['platforms']['linux']['machine'] = 'build-7'
        _write(path, json.dumps(data))
        for rule_id in ('RULE-1', 'RULE-2'):
            assert project.rule(rule_id)['machines'] == {'linux': 'build-7'}

    # purlin: states PROOF-326
    def test_a_proof_names_the_commit_its_results_were_carried_from(
            self, project):
        rel = project.evidence(PASSING, os_name='linux')
        path = os.path.join(project.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        taken_at = 'a1b2c3d4' * 5
        first = data['platforms']['linux']['proofs'][0]
        assert first['id'] == 'PROOF-1', first
        first['carried'] = {'commit': taken_at, 'at': '2026-09-12T08:00:00Z',
                            'machine': 'build-7',
                            'email': 'runner@example.com'}
        _write(path, json.dumps(data))
        assert project.rule('RULE-1')['proofs'][0]['carried'] == {
            'linux': taken_at}
        assert project.rule('RULE-2')['proofs'][0]['carried'] == {}

    # purlin: states PROOF-271
    def test_a_project_in_work_named_by_pyproject_reads_labconnect(self):
        made = Project()
        parent = tempfile.mkdtemp()
        try:
            moved = os.path.join(parent, 'work')
            shutil.move(made.root, moved)
            made.root = moved
            _write(os.path.join(moved, 'pyproject.toml'),
                   '[build-system]\nrequires = ["setuptools"]\n\n'
                   '[project]\nname = "labconnect"\nversion = "0.1.0"\n')
            data = made.payload()
        finally:
            made.close()
            shutil.rmtree(parent, ignore_errors=True)
        assert os.path.basename(moved) == 'work'
        assert data['project'] == 'labconnect', data['project']


class TestProofResult:

    @staticmethod
    def _proofs(project):
        rules = _feature(project.payload())['rules']
        return {proof['id']: proof for rule in rules for proof in rule['proofs']}

    # purlin: states PROOF-85
    def test_a_proof_before_any_run_reads_not_run_or_no_test(self, project):
        _commit_tests(project, 'PROOF-1')
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'not run', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == []
        assert proofs['PROOF-2']['result'] == 'no test', proofs['PROOF-2']

    # purlin: states PROOF-176
    def test_each_proof_carries_its_own_result_and_its_tests(self, project):
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', status='fail')])
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'passed', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == [
            {'file': 'tests/test_login.py', 'name': 'test_proof_1',
             'result': 'pass'}], proofs['PROOF-1']['tests']
        assert proofs['PROOF-2']['result'] == 'failed', proofs['PROOF-2']
        assert [test['result'] for test in proofs['PROOF-2']['tests']] == [
            'fail'], proofs['PROOF-2']['tests']


# ---------------------------------------------------------------------------
# A rule's test hash, one test at a time
# ---------------------------------------------------------------------------

AGE_SPEC = (
    '# Feature: sample_age\n\n> Scope: src/age.py\n\n## Rules\n\n'
    '- RULE-1: A sample is aged in whole minutes\n'
    '- RULE-2: A sample over 150 minutes old is rejected\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): A sample taken 90 minutes ago reads 90\n'
    '- PROOF-2 (RULE-2): A sample taken 151 minutes ago reads rejected\n')

AGE_TESTS = (
    'from src.age import age\n'
    '\n'
    '# purlin: sample_age PROOF-1\n'
    'def test_proof_1():\n'
    '    assert age(90) == 90\n'
    '\n'
    '\n'
    '# purlin: sample_age PROOF-2\n'
    'def test_proof_2():\n'
    '    assert age(151) == "rejected"\n')


def _age_project():
    """`sample_age` of two rules, each test in `tests/test_age.py`, both run."""
    made = Project(spec=None)
    made.spec(AGE_SPEC, name='sample_age', category='lab')
    _write(os.path.join(made.root, 'src', 'age.py'),
           'def age(minutes):\n    return minutes\n')
    _write(os.path.join(made.root, 'tests', 'test_age.py'), AGE_TESTS)
    _commit(made.root, 'feat(sample_age): the age and its tests')
    made.evidence([_entry('PROOF-1', 'RULE-1', feature='sample_age',
                          test_file='tests/test_age.py'),
                   _entry('PROOF-2', 'RULE-2', feature='sample_age',
                          test_file='tests/test_age.py')],
                  feature='sample_age')
    return made


def _edit_age_test(made, before, after):
    path = os.path.join(made.root, 'tests', 'test_age.py')
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    assert before in text
    _write(path, text.replace(before, after))


class TestTheTestHash:

    # purlin: states PROOF-265
    def test_editing_the_proof_2_test_leaves_rule_1s_hash_unchanged(self):
        made = _age_project()
        try:
            first = made.rule('RULE-1', 'sample_age')
            _edit_age_test(made, 'age(151) == "rejected"',
                           'age(152) == "rejected"')
            after = made.rule('RULE-1', 'sample_age')
            # An edit that makes the second test, and so the file, longer.
            _edit_age_test(
                made, '    assert age(152) == "rejected"\n',
                '    aged = age(1520)\n\n    assert aged == "rejected"\n')
            longer = made.rule('RULE-1', 'sample_age')
            second = made.rule('RULE-2', 'sample_age')
        finally:
            made.close()
        assert first['test_hash_kind'] == 'test', first['test_hash_kind']
        assert after['test_hash'] == first['test_hash']
        assert len(first['test_hash']) == 64, first['test_hash']
        assert longer['test_hash_kind'] == 'test', longer['test_hash_kind']
        assert longer['test_hash'] == first['test_hash']
        # The edits were read: the hash of the rule they belong to moved.
        assert second['test_hash'] != first['test_hash']

    # purlin: states PROOF-266
    def test_editing_the_body_of_the_proof_1_test_changes_rule_1s_hash(self):
        made = _age_project()
        try:
            first = made.rule('RULE-1', 'sample_age')['test_hash']
            _edit_age_test(made, 'age(90) == 90', 'age(91) == 91')
            after = made.rule('RULE-1', 'sample_age')['test_hash']
            # Edits to the body that change its spacing and nothing else:
            # a deeper indent, then one line broken in two.
            _edit_age_test(made, '    assert age(91) == 91\n',
                           '        assert age(91) == 91\n')
            indented = made.rule('RULE-1', 'sample_age')['test_hash']
            _edit_age_test(made, '        assert age(91) == 91\n',
                           '        assert age(91) == \\\n            91\n')
            broken = made.rule('RULE-1', 'sample_age')['test_hash']
        finally:
            made.close()
        assert after != first
        assert len({first, after, indented, broken}) == 4, (
            first, after, indented, broken)


# ---------------------------------------------------------------------------
# A test comment whose proof was reworded
# ---------------------------------------------------------------------------

class TestATestCommentToCorrect:

    @staticmethod
    def _reworded(made):
        """`sample_age PROOF-1` reworded in a commit after its test."""
        made.spec(AGE_SPEC.replace('reads 90', 'reads 90 minutes'),
                  name='sample_age', category='lab')
        _commit(made.root, 'spec(sample_age): PROOF-1 names its unit')

    # purlin: states PROOF-269
    def test_a_test_at_line_3_marked_for_a_reworded_proof_is_named(self):
        made = _age_project()
        try:
            self._reworded(made)
            data = made.payload()
        finally:
            made.close()
        named = [line for line in data['warnings']
                 if line.startswith('tests/test_age.py:3 names sample_age '
                                    'PROOF-1, whose wording changed after '
                                    'the test was last changed')]
        assert len(named) == 1, data['warnings']
        assert '1 test comment to correct' in [item['text']
                                               for item in data['left']], \
            data['left']

    # purlin: states PROOF-270
    def test_once_the_test_body_is_committed_changed_nothing_is_named(self):
        made = _age_project()
        try:
            self._reworded(made)
            _edit_age_test(made, 'age(90) == 90', 'age(90) == 90  # minutes')
            _commit(made.root, 'test(sample_age): PROOF-1 in minutes')
            data = made.payload()
        finally:
            made.close()
        assert not [line for line in data['warnings']
                    if 'whose wording changed' in line], data['warnings']
        assert 'to_correct' not in [item['kind'] for item in data['left']], \
            data['left']

    # purlin: states PROOF-285
    def test_adding_slow_to_a_proof_names_no_test_comment(self):
        made = _age_project()
        try:
            assert AGE_SPEC.count('PROOF-1 (RULE-1)') == 1
            lines = AGE_SPEC.splitlines(True)
            made.spec(''.join(line.rstrip('\n') + ' @slow\n'
                              if line.startswith('- PROOF-1 ') else line
                              for line in lines),
                      name='sample_age', category='lab')
            _commit(made.root, 'spec(sample_age): PROOF-1 is slow')
            data = made.payload()
            slow = made.rule('RULE-1', 'sample_age')['proofs'][0]['slow']
        finally:
            made.close()
        assert slow is True
        assert not [line for line in data['warnings']
                    if 'whose wording changed' in line], data['warnings']
        assert 'to_correct' not in [item['kind'] for item in data['left']], \
            data['left']


# ---------------------------------------------------------------------------
# Nothing to check
# ---------------------------------------------------------------------------

NO_SCREENS_ANCHOR = (
    '# Anchor: security_no_dangerous_patterns\n\n'
    '## Rules\n\n'
    '- RULE-1: No eval anywhere\n'
    '- RULE-2: No shell=True anywhere\n'
    '- RULE-3: Every screen escapes what it shows\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n'
    '- PROOF-2 (RULE-2): Grep for shell=True; verify 0 matches\n'
    '- PROOF-3 (RULE-3): For every screen in the project, render a name '
    'holding <b>; verify it shows as text\n')


class TestNothingToCheck:

    # purlin: states PROOF-274
    def test_an_anchor_proof_with_nothing_to_check_passes_with_its_reason(
            self, project):
        name = 'security_no_dangerous_patterns'
        project.spec(NO_SCREENS_ANCHOR, name=name, category='_anchors')
        _commit(project.root, 'anchor(%s): create' % name)
        rel = project.evidence(
            [_entry('PROOF-%d' % n, 'RULE-%d' % n, feature=name,
                    test_file='tests/test_security.py') for n in (1, 2, 3)],
            feature=name, commit_it=False)
        _skipped_with_nothing_to_check(project, rel, 'PROOF-3',
                                       'this project has no screens')
        cell = project.cell('RULE-3', 'passed', name)
        lines = purlin_status.sync_status(project.root).splitlines()
        assert cell['word'] == 'passed', cell
        assert cell['reasons'] == ['PROOF-3: this project has no screens'], \
            cell
        assert ('security_no_dangerous_patterns RULE-3 passes with nothing to '
                'check here: this project has no screens.') in lines, lines

    # purlin: states PROOF-278
    def test_a_feature_proof_with_nothing_to_check_reads_not_run(self,
                                                                 project):
        _commit_tests(project, 'PROOF-1', 'PROOF-2')
        rel = project.evidence(PASSING, commit_it=False)
        _skipped_with_nothing_to_check(project, rel, 'PROOF-1',
                                       'no screens here')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'not run', cell
        assert cell['reasons'] == ['no screens here'], cell


# ---------------------------------------------------------------------------
# A slow proof
# ---------------------------------------------------------------------------

SLOW_REASON = 'slow: runs with purlin:test --all'
SLOW_SPEC = SPEC.replace('the body "denied"\n', 'the body "denied" @slow\n')
SLOW_ANCHOR = SECURITY_ANCHOR.replace('verify 0 matches\n',
                                      'verify 0 matches @slow\n')


class TestASlowProof:

    # purlin: states PROOF-282
    def test_a_slow_proof_no_run_answered_reads_not_run_with_its_reason(
            self, project):
        project.spec(SLOW_SPEC)
        _commit_tests(project, 'PROOF-1', 'PROOF-2')
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', status='not run')],
                         commit_it=False)
        rule = project.rule('RULE-2')
        proof = rule['proofs'][0]
        assert proof['id'] == 'PROOF-2' and proof['slow'] is True, proof
        assert proof['result'] == 'not run', proof
        cell = rule['cells']['passed']
        assert cell['word'] == 'not run', cell
        assert cell['reasons'] == [SLOW_REASON], cell

    # purlin: states PROOF-283
    def test_a_slow_proof_passes_and_goes_out_of_date_like_any_other(
            self, project):
        project.spec(SLOW_SPEC)
        _commit_tests(project, 'PROOF-1', 'PROOF-2')
        project.evidence(PASSING)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed' and cell['reasons'] == [], cell
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 200  # rewritten\n')
        _commit(project.root, 'refactor: login')
        rule = project.rule('RULE-2')
        assert rule['cells']['passed']['word'] == 'out of date', rule['cells']
        assert rule['proofs'][0]['result'] == 'not run', rule['proofs']

    # purlin: states PROOF-284
    def test_an_anchors_slow_proof_reads_not_run_with_the_same_reason(
            self, project):
        project.spec(SLOW_ANCHOR, name='security', category='_anchors')
        _write(os.path.join(project.root, 'tests', 'test_security.py'),
               _marked_tests('PROOF-1', feature='security'))
        _commit(project.root, 'anchor(security): create')
        cell = project.cell('RULE-1', 'passed', 'security')
        assert cell['word'] == 'not run', cell
        assert cell['reasons'] == [SLOW_REASON], cell


# ---------------------------------------------------------------------------
# A spec ahead of its code
# ---------------------------------------------------------------------------

class TestASpecAheadOfItsCode:

    # purlin: states PROOF-279
    def test_three_files_not_written_are_one_line_for_the_spec(self):
        made = Project(spec=None)
        try:
            made.spec('# Feature: states\n\n'
                      '> Scope: facts.py, project.py, wording.py\n\n'
                      '## Rules\n\n- RULE-1: The two facts read met\n\n'
                      '## Proof\n\n- PROOF-1 (RULE-1): Read them; verify met\n',
                      name='states', category='mcp')
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        found = [line for line in lines if 'not written yet' in line]
        assert found == [
            'states: 3 files its scope names are not written yet: facts.py, '
            'project.py, wording.py. Run purlin:build states, or correct the '
            'path with purlin:spec states.'], lines

    # purlin: states PROOF-280
    def test_one_file_not_written_beside_one_in_git_is_information(self):
        line = ('login: 1 file its scope names is not written yet: '
                'src/gone.py. Run purlin:build login, or correct the path with '
                'purlin:spec login.')
        made = Project(spec=SPEC.replace('> Scope: src/login.py',
                                         '> Scope: src/login.py, src/gone.py'))
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            data = _dashboard_data(made.root)
        finally:
            made.close()
        assert line in lines, lines
        assert data['information'] == [line], data['information']
        assert line not in data['warnings'], data['warnings']


# ---------------------------------------------------------------------------
# The page after a run
# ---------------------------------------------------------------------------

# purlin: states PROOF-223
def test_a_test_run_leaves_its_results_in_the_page_data(tmp_path):
    from run_project import _pytest_project, _run, _spec
    root = _pytest_project(tmp_path)
    _spec(root, 'feat')
    assert not os.path.exists(os.path.join(str(root), '.purlin',
                                           'report-data.js'))
    code, output = _run(root, '--all', '--test')
    assert code == 0, output
    data = _dashboard_data(str(root))
    feature = next(f for f in data['features'] if f['name'] == 'feat')
    rule = next(r for r in feature['rules'] if r['id'] == 'RULE-1')
    assert rule['cells']['passed']['word'] == 'passed', rule


# ---------------------------------------------------------------------------
# The status table
# ---------------------------------------------------------------------------

# The dashboard's spec table as a reader sees it: its column headings, and
# each spec's name and the text of each of its cells, one line each.
DASHBOARD_ROWS = r"""els => {
  const head = Array.from(document.querySelector('.th').children)
    .map(d => d.textContent.trim());
  return [head, els.map(e => ({
    name: e.querySelector('.name .n').textContent.trim(),
    cells: head.map((label, i) =>
      e.children[i].innerText.trim().replace(/\s+/g, ' '))}))];
}"""

FIXTURES = os.path.join(PROJECT_ROOT, 'dev', 'fixtures', 'report')


def _fixture(name):
    with open(os.path.join(FIXTURES, name + '.json'), encoding='utf-8') as handle:
        return json.load(handle)


@pytest.fixture(scope='module')
def browser():
    playwright = pytest.importorskip('playwright.sync_api')
    from browser_launch import launch_browser
    with playwright.sync_playwright() as driver:
        instance = launch_browser(driver, headless=True)
        yield instance
        instance.close()


@pytest.fixture(scope='module')
def dashboard_page():
    """The dashboard's page, built from its sources as it ships."""
    from build_report import build
    return build()


def _dashboard(browser, page_text, folder, payload):
    """`(headings, {spec: cells})` of the dashboard opened over `payload`."""
    os.makedirs(os.path.join(folder, '.purlin'))
    _write(os.path.join(folder, 'purlin-report.html'), page_text)
    _write(os.path.join(folder, '.purlin', 'report-data.js'),
           'const PURLIN_DATA = ' + json.dumps(payload) + ';\n')
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    try:
        page.goto('file://' + os.path.join(folder, 'purlin-report.html'))
        page.wait_for_selector('.topbar', timeout=10000)
        head, rows = page.eval_on_selector_all('.tr', DASHBOARD_ROWS)
    finally:
        page.close()
    return head, {row['name']: row['cells'] for row in rows}


def _table_cells(lines):
    """`(headings, {spec: cells})` of a printed status table."""
    header = lines[0]
    headings = header.split()
    starts = [header.index(heading) for heading in headings]
    rows = {}
    for line in lines[2:-1]:
        if line in (purlin_status.ANCHORS, purlin_status.SPECS):
            continue
        cells = [line[start:end].strip() for start, end in
                 zip(starts, starts[1:] + [len(line)])]
        rows[cells[0]] = cells
    return headings, rows


def _status_lines(root):
    return purlin_status.sync_status(root).splitlines()


def _header(lines):
    return next(line for line in lines if line.startswith('Spec'))


def _row_of(lines, name):
    return next(line for line in lines if line.startswith(name + ' '))


def _cell_under(lines, name, heading):
    """The text of spec `name`'s cell under `heading`, from its left edge."""
    header = _header(lines)
    return _row_of(lines, name)[header.index(heading):].split('  ')[0]


def _table_rows(lines):
    """The table's rows, between the two rules under the header."""
    top = lines.index(_header(lines)) + 1
    return lines[top + 1:lines.index(lines[top], top + 1)]


class TestStatusTable:

    # purlin: states PROOF-58
    def test_the_three_samples_show_the_same_cells_in_the_table_and_page(
            self, browser, dashboard_page, tmp_path):
        for name in ('solo', 'team', 'regulated'):
            sample = _fixture(name)
            headings, table = _table_cells(purlin_status._table(sample))
            shown, dashboard = _dashboard(browser, dashboard_page,
                                          str(tmp_path / name), sample)
            assert shown == headings, (name, shown, headings)
            assert sorted(dashboard) == sorted(table), (name, dashboard)
            for spec, cells in table.items():
                assert dashboard[spec][1:] == cells[1:], (
                    name, spec, dashboard[spec], cells)

    @staticmethod
    def _one_of_two_passing(project):
        _commit_tests(project, 'PROOF-2')
        project.evidence([_entry('PROOF-2', 'RULE-2')])

    # purlin: states PROOF-43
    def test_two_rules_one_passing_none_audited_show_no_strong_column(
            self, project):
        self._one_of_two_passing(project)
        lines = _status_lines(project.root)
        header = _header(lines)
        assert header.split() == ['Spec', 'Rules', 'Proofs', 'Tests'], header
        assert 'Strong' not in header, header
        assert _cell_under(lines, 'login', 'Proofs') == '2 · 1 no test', lines
        assert _cell_under(lines, 'login', 'Tests') == '1 of 2', lines

    # purlin: states PROOF-294
    def test_an_audit_entry_on_a_rule_that_now_fails_keeps_the_strong_column(
            self, project):
        _commit_tests(project, 'PROOF-1', 'PROOF-2')
        project.evidence(PASSING)
        project.audit('RULE-2')
        assert _header(_status_lines(project.root)).split()[-1] == 'Strong'
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', 'fail')])
        assert project.rule('RULE-2')['audit'] is not None
        assert project.cell('RULE-2', 'strong')['word'] == 'waiting'
        assert project.cell('RULE-1', 'strong')['word'] == 'not audited'
        lines = _status_lines(project.root)
        assert _header(lines).split()[-1] == 'Strong', lines
        assert _cell_under(lines, 'login', 'Strong') == '0 of 1', lines

    # purlin: states PROOF-298
    def test_two_passing_rules_and_a_hand_check_read_two_of_three_one_by_hand(
            self):
        made = Project(spec=spec_with_a_hand_check(3))
        try:
            _commit_tests(made, 'PROOF-1', 'PROOF-2')
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')])
            lines = _status_lines(made.root)
        finally:
            made.close()
        assert _cell_under(lines, 'login', 'Tests') == (
            '2 of 3 · 1 by hand'), lines

    # purlin: states PROOF-299
    def test_nine_strong_rules_and_a_hand_check_read_nine_of_nine_strong(
            self):
        made = Project(spec=spec_with_a_hand_check(10))
        tested = ['PROOF-%d' % number for number in range(1, 10)]
        try:
            _commit_tests(made, *tested)
            made.evidence([_entry(proof_id, proof_id.replace('PROOF', 'RULE'))
                           for proof_id in tested])
            for proof_id in tested:
                made.audit(proof_id.replace('PROOF', 'RULE'))
            lines = _status_lines(made.root)
        finally:
            made.close()
        assert _cell_under(lines, 'login', 'Tests') == (
            '9 of 10 · 1 by hand'), lines
        assert _cell_under(lines, 'login', 'Strong') == '9 of 9', lines

    # purlin: states PROOF-100
    def test_one_passing_and_one_failing_here_read_one_of_two_one_failing(
            self, project):
        self._one_of_two_passing(project)
        project.evidence([_entry('PROOF-1', 'RULE-1', 'fail'),
                          _entry('PROOF-2', 'RULE-2')])
        lines = _status_lines(project.root)
        assert _cell_under(lines, 'login', 'Tests') == (
            '1 of 2 · 1 failing'), lines

    # purlin: states PROOF-236
    def test_the_specs_of_a_project_not_set_up_are_read(self):
        made = Project()
        try:
            _git(made.root, 'rm', '-q', '--', '.purlin/config.json')
            _git(made.root, 'commit', '-q', '-m', 'chore: not set up')
            lines = _status_lines(made.root)
            assert _row_of(lines, 'login').split()[:2] == ['login', '2'], lines
            assert '2 rules. 0 pass their tests.' in lines
        finally:
            made.close()

    # purlin: states PROOF-212
    def test_a_settings_file_holding_version_and_a_comma_is_the_whole_report(
            self, project):
        _write(os.path.join(project.root, '.purlin', 'config.json'),
               '{"version": "0.10.0",')
        text = purlin_status.sync_status(project.root)
        written = os.path.exists(os.path.join(
            project.root, '.purlin', 'report-data.js'))
        assert text == (
            '.purlin/config.json cannot be read: Expecting property name '
            'enclosed in double quotes at line 1. Fix the file by hand; '
            'nothing ran and nothing was saved.'), text
        assert written is False


# ---------------------------------------------------------------------------
# The sign-off on HEAD or behind it
# ---------------------------------------------------------------------------

class TestTheSignOff:
    """The payload names the newest `signed/*` tag on HEAD or an ancestor
    whose sign-off counts."""

    # purlin: states PROOF-168
    def test_a_walk_at_head_reads_its_version_the_signed_commit_and_signed_at(
            self, project):
        _ready_to_sign(project)
        _walk_signs(project, '1.2.0')
        signoff = project.payload()['signoff']
        signed = _git(project.root, 'rev-list', '-n', '1',
                      'signed/1.2.0').stdout.strip()
        assert signed == project.head(), signed
        assert signoff['version'] == '1.2.0', signoff
        assert signoff['commit'] == signed, signoff
        assert signoff['word'] == 'signed 1.2.0 at %s' % signed[:7], signoff

    # purlin: states PROOF-169
    def test_a_commit_of_evidence_alone_after_the_tag_still_reads_signed_at(
            self, project):
        _ready_to_sign(project)
        _walk_signs(project, '1.2.0')
        tagged = project.head()
        path = os.path.join(project.root, '.purlin', 'evidence', 'local',
                            'login.json')
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        _write(path, text + '\n')
        _commit(project.root, 'purlin: evidence at %s' % tagged[:7])
        assert project.head() != tagged
        signoff = project.payload()['signoff']
        assert signoff['word'] == 'signed 1.2.0 at %s' % tagged[:7], signoff

    # purlin: states PROOF-170
    def test_of_three_versions_signed_1_10_0_is_the_newest(self, project):
        _ready_to_sign(project)
        for version in ('1.9.0', '1.10.0', 'beta'):
            _walk_signs(project, version)
        assert project.payload()['signoff']['version'] == '1.10.0'


# ---------------------------------------------------------------------------
# The settings and anchors beside the table
# ---------------------------------------------------------------------------

def _anchor_source(folder):
    """A git repository holding an anchor's rules. Its HEAD's sha."""
    os.makedirs(folder)
    _write(os.path.join(folder, 'policy.md'), '# Anchor: policy\n')
    _git(folder, 'init', '-q')
    _git(folder, 'config', 'user.email', 'dev@example.com')
    _git(folder, 'config', 'user.name', 'Dev')
    _git(folder, 'add', '-A')
    _git(folder, 'commit', '-q', '-m', 'first')
    return _git(folder, 'rev-parse', 'HEAD').stdout.strip()


def _advance(folder):
    """One more commit in the anchor's source. Its sha."""
    _write(os.path.join(folder, 'policy.md'), '# Anchor: policy\n\nv2\n')
    _git(folder, 'commit', '-q', '-am', 'second')
    return _git(folder, 'rev-parse', 'HEAD').stdout.strip()


def _anchored_status(source, pinned=None):
    """The status report's lines for a project whose anchor `policy` names
    `source`, pinned to `pinned` when given."""
    meta = '> Source: %s\n' % source
    if pinned:
        meta += '> Pinned: %s\n' % pinned
    made = Project()
    try:
        made.spec('# Anchor: policy\n\n%s\n## Rules\n\n- RULE-1: Every '
                  'answer is JSON\n\n## Proof\n\n- PROOF-1 (RULE-1): An '
                  'answer parses as JSON\n' % meta,
                  name='policy', category='_anchors')
        _commit(made.root, 'anchor(policy): create')
        return purlin_status.sync_status(made.root).splitlines()
    finally:
        made.close()


class TestTheAnchorLines:

    # purlin: states PROOF-231
    def test_a_pin_behind_its_source_names_both_commits(self, tmp_path):
        source = str(tmp_path / 'policy-source')
        old = _anchor_source(source)
        new = _advance(source)
        lines = _anchored_status(source, old)
        assert ('policy: the pin %s is behind its source, now %s. Run '
                'purlin:anchor sync policy.' % (old[:7], new[:7])) in lines, \
            lines

    # purlin: states PROOF-234
    def test_a_source_refused_names_the_reason(self):
        lines = _anchored_status('--upload-pack=/bin/echo', 'abc1234')
        assert 'policy: (source rejected: begins with "-")' in lines, lines


# ---------------------------------------------------------------------------
# Anchors: counted once, listed first
# ---------------------------------------------------------------------------

def _spec_of(heading, count, scope=None):
    """A spec of `count` rules, each proved by one proof of the same number."""
    meta = '> Scope: %s\n\n' % scope if scope else ''
    rules = ''.join('- RULE-%d: Rule %d holds\n' % (n, n)
                    for n in range(1, count + 1))
    proofs = ''.join('- PROOF-%d (RULE-%d): Case %d reads %d\n' % (n, n, n, n)
                     for n in range(1, count + 1))
    return '%s\n\n%s## Rules\n\n%s\n## Proof\n\n%s' % (
        heading, meta, rules, proofs)


def _all_passing(made, feature, count):
    """A current section passing every proof of a spec of `count` rules."""
    made.evidence([_entry('PROOF-%d' % n, 'RULE-%d' % n, feature=feature,
                          test_file='tests/test_%s.py' % feature)
                   for n in range(1, count + 1)], feature=feature)


class TestAnchors:

    # purlin: states PROOF-238
    def test_login_of_eleven_beside_security_of_eight_reads_11_of_11(self):
        made = Project(spec=_spec_of('# Feature: login', 11, 'src/login.py'))
        try:
            made.spec(_spec_of('# Anchor: security', 8), name='security',
                      category='_anchors')
            _commit(made.root, 'anchor(security): create')
            _all_passing(made, 'login', 11)
            _all_passing(made, 'security', 8)
            lines = _status_lines(made.root)
        finally:
            made.close()
        assert (_cell_under(lines, 'login', 'Rules'),
                _cell_under(lines, 'login', 'Tests')) == ('11', '11 of 11')
        assert _cell_under(lines, 'security', 'Tests') == '8 of 8'

    @staticmethod
    def _anchor_strong_cell(found, **entry):
        """The `Strong` cell of the anchor `security`, two rules that pass
        their tests, after the audit entries `found` names by rule id are
        written; `entry` adds fields to `RULE-1`'s."""
        made = Project(spec=_spec_of('# Feature: login', 1, 'src/login.py'))
        try:
            made.spec(_spec_of('# Anchor: security', 2), name='security',
                      category='_anchors')
            _commit(made.root, 'anchor(security): create')
            _all_passing(made, 'login', 1)
            _all_passing(made, 'security', 2)
            made.audit('RULE-1', feature='login')
            for rule_id, word in sorted(found.items()):
                made.audit(rule_id, feature='security', word=word,
                           **(entry if rule_id == 'RULE-1' else {}))
            lines = _status_lines(made.root)
        finally:
            made.close()
        assert _cell_under(lines, 'login', 'Strong') == '1 of 1', lines
        return _row_of(lines, 'security')[
            _header(lines).index('Strong'):].rstrip()

    # purlin: states PROOF-300
    def test_an_anchor_whose_rules_are_all_spot_checked_reads_spot_checked(
            self):
        assert self._anchor_strong_cell(
            {'RULE-1': 'spot-checked', 'RULE-2': 'spot-checked'}
        ) == 'spot-checked'

    # purlin: states PROOF-301
    def test_an_anchor_with_one_weak_rule_reads_weak(self):
        assert self._anchor_strong_cell(
            {'RULE-1': 'spot-checked', 'RULE-2': 'weak'}) == 'weak'

    # purlin: states PROOF-302
    def test_an_anchor_with_an_entry_out_of_date_reads_out_of_date(self):
        assert self._anchor_strong_cell(
            {'RULE-1': 'spot-checked', 'RULE-2': 'spot-checked'},
            code_hash='0' * 64) == 'out of date'

    # purlin: states PROOF-303
    def test_an_anchor_with_a_rule_no_audit_read_has_an_empty_strong_cell(
            self):
        assert self._anchor_strong_cell({'RULE-1': 'spot-checked'}) == ''

    @staticmethod
    def _tests_cells_after_a_code_change(security, tested):
        """The `Tests` cells of `security` and of `login`, 2 rules, after
        `login`'s proofs and `security`'s first `tested` passed in a section
        taken before a commit that changes `src/login.py`."""
        made = Project(spec=_spec_of('# Feature: login', 2, 'src/login.py'))
        try:
            made.spec(security, name='security', category='_anchors')
            _commit(made.root, 'anchor(security): create')
            _all_passing(made, 'login', 2)
            _all_passing(made, 'security', tested)
            _write(os.path.join(made.root, 'src', 'login.py'),
                   'def login():\n    return 201\n')
            _commit(made.root, 'feat(login): 201')
            lines = _status_lines(made.root)
        finally:
            made.close()
        return (_cell_under(lines, 'security', 'Tests'),
                _cell_under(lines, 'login', 'Tests'))

    # purlin: states PROOF-323
    def test_an_anchor_of_eleven_rules_out_of_date_says_so(self):
        cells = self._tests_cells_after_a_code_change(
            _spec_of('# Anchor: security', 11), 11)
        assert cells[0] == '0 of 11 · 11 out of date', cells

    # purlin: states PROOF-324
    def test_the_out_of_date_part_follows_by_hand(self):
        security = _spec_of('# Anchor: security', 3).replace(
            'Case 3 reads 3', 'Case 3 reads 3 @manual')
        cells = self._tests_cells_after_a_code_change(security, 2)
        assert cells[0] == '0 of 3 · 1 by hand · 2 out of date', cells

    # purlin: states PROOF-325
    def test_a_features_row_out_of_date_reads_as_before(self):
        cells = self._tests_cells_after_a_code_change(
            _spec_of('# Anchor: security', 1), 1)
        assert cells[1] == '0 of 2', cells

    # purlin: states PROOF-242
    def test_the_anchors_are_listed_first_under_their_label(self, project):
        project.spec(SECURITY_ANCHOR, name='security', category='_anchors')
        rows = _table_rows(_status_lines(project.root))
        assert [row.split()[0] for row in rows] == [
            'Anchors', 'security', 'Specs', 'login'], rows
        assert rows[0] == 'Anchors' and rows[2] == 'Specs', rows


# ---------------------------------------------------------------------------
# A spec that writes a number twice
# ---------------------------------------------------------------------------

# `login` writing `PROOF-2` twice.
PROOF_TWICE_SPEC = SPEC + (
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n')
EXPORT_SPEC = SPEC.replace('login', 'export')


class TestABrokenSpecFails:

    # purlin: states PROOF-248
    def test_a_proof_written_twice_fails_every_rule_of_its_spec(self):
        made = Project(spec=PROOF_TWICE_SPEC)
        try:
            made.evidence(PASSING)
            data = made.payload()
        finally:
            made.close()
        for rule_id in ('RULE-1', 'RULE-2'):
            cell = _listed(data, rule_id)['cells']['passed']
            assert (cell['word'], cell['reasons']) == (
                'failed', ['PROOF-2 is written twice in the spec']), (
                    rule_id, cell)

    # purlin: states PROOF-250
    def test_a_sound_spec_beside_a_broken_one_passes(self):
        made = Project(spec=PROOF_TWICE_SPEC)
        try:
            made.evidence(PASSING)
            made.spec(EXPORT_SPEC, name='export')
            made.evidence([_entry('PROOF-1', 'RULE-1', feature='export'),
                           _entry('PROOF-2', 'RULE-2', feature='export')],
                          feature='export')
            data = made.payload()
        finally:
            made.close()
        for rule_id in ('RULE-1', 'RULE-2'):
            cell = _listed(data, rule_id, 'export')['cells']['passed']
            assert cell['word'] == 'passed', (rule_id, cell)
