"""Tests for the cells of each rule, the payload and the status table.

What the cells of each rule read, what the payload and the status table
say about it, the signed tag on HEAD, and a spec that names no files. The
throwaway project and its helpers are in `dev/mcp_project.py`.
"""

import contextlib
import datetime
import io
import json
import os
import re
import shutil
import sys

import pytest

from mcp_project import (NO_PROOF_SPEC, ONE_RULE_SPEC, PROJECT_ROOT,
                         Project, SPEC, _commit_tests, _entry, _git, _listed,
                         _marked_tests, _rpc, _write, project)
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import evidence as purlin_evidence
from purlin import fingerprint as purlin_fingerprint
from purlin import gate as purlin_gate
from purlin import payload as purlin_payload
from purlin import signatures as purlin_signatures
from purlin import states as purlin_states
from purlin import status as purlin_status


def _bound(inp, **fields):
    """A signature dict that binds the rule `inp` describes, as a unit input."""
    entry = dict(inp)
    signature = {key: entry.get(key) for key in (
        'applies_to', 'rule_hash', 'proof_hash', 'test_hash', 'code_hash',
        'audit_hash', 'machines')}
    signature.update({'signed_hash': purlin_signatures.signed_hash(entry),
                      'counts': True, 'count_reason': '',
                      'signer': 'jane@acme.com', 'path': 'x.json'})
    signature.update(fields)
    return signature


# ---------------------------------------------------------------------------
# The sources
# ---------------------------------------------------------------------------

class TestTheSources:

    # purlin: states PROOF-5
    def test_a_current_section_from_either_source_counts_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            for source in ('ci', 'local'):
                made = Project(gate=gate)
                try:
                    made.evidence([_entry('PROOF-2', 'RULE-2')],
                                  source=source, ci=source == 'ci')
                    cell = made.cell('RULE-2', 'passed')
                    assert cell['word'] == 'passed', (gate, source, cell)
                    assert cell['source'] == source, (gate, source, cell)
                    assert cell['counts'] is True, (gate, source, cell)
                finally:
                    made.close()


# ---------------------------------------------------------------------------
# The cells
# ---------------------------------------------------------------------------

def _section(source='ci', os_name='linux', statuses=None, current=True,
             at='2026-09-13T12:00:00Z', commit='a' * 40, out_of_date=()):
    """One checked section, as `evidence.checked_sections` hands it over."""
    statuses = statuses or {'PROOF-1': 'pass'}
    return {'source': source, 'os': os_name,
            'path': '.purlin/evidence/%s/login.json' % source,
            'current': current, 'out_of_date': list(out_of_date),
            'section': {'commit': commit, 'at': at,
                        'proofs': [{'id': proof_id, 'rule': 'RULE-1',
                                    'result': status}
                                   for proof_id, status in statuses.items()]}}


STRONG_INPUT = {
    'proofs': [{'id': 'PROOF-1', 'env': None, 'text': 'x',
                'findings': [], 'tests': [{'file': 'tests/t.py',
                                           'name': 'test_x'}]}],
    'sections': [_section()],
    'test_strength': 90,
}


def _audit(word='strong', findings=(), **extra):
    """An audit entry for the rule's current hashes, as the payload hands it."""
    entry = {'verdict': word, 'findings': list(findings),
             'path': '.purlin/evidence/local/login.json'}
    entry.update(extra)
    return entry


def _strong(cfg=None, **overrides):
    """One rule's strong cell, built straight from its evidence."""
    inp = dict(STRONG_INPUT)
    inp.update(overrides)
    cfg = cfg or purlin_gate.resolve_gate({'gate': 'strong'})
    return purlin_states.rule_cells(inp, cfg)['cells']['strong']


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

    # purlin: states PROOF-173
    def test_a_section_listing_no_marked_test_leaves_no_proof_written(
            self, project):
        project.spec(self.TWO_RULES_NO_PROOF)
        project.evidence([], commit_it=False)
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no proof written'], cell

    @staticmethod
    def _no_proof_rule(gate):
        """The one rule of a spec with no proof line, its marked test passing."""
        project = Project(spec=NO_PROOF_SPEC, gate=gate)
        try:
            project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                               'status': 'pass'}], commit_it=False)
            return project.rule('RULE-1')
        finally:
            project.close()

    # purlin: states PROOF-78
    def test_at_strong_a_rule_with_a_test_and_no_proof_reads_no_proof(self):
        rule = self._no_proof_rule('strong')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['cells']['strong']['word'] == 'no proof', rule
        assert rule['cells']['strong']['reasons'] == [
            'the rule has a test and no proof'], rule
        assert rule['left'] == 'no_proof', rule['left']

    # purlin: states PROOF-139
    def test_at_signed_a_rule_with_a_test_and_no_proof_reads_no_proof(self):
        rule = self._no_proof_rule('signed')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['cells']['strong']['word'] == 'no proof', rule
        assert rule['cells']['strong']['reasons'] == [
            'the rule has a test and no proof'], rule
        assert rule['left'] == 'no_proof', rule['left']

    # purlin: states PROOF-140
    def test_at_passed_a_rule_with_a_test_and_no_proof_waits_for_nothing(
            self):
        rule = self._no_proof_rule('passed')
        assert sorted(rule['cells']) == ['passed'], rule
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['left'] is None, rule


class TestThePassedCell:

    # purlin: states PROOF-3
    def test_a_local_section_meets_level_one_under_the_passed_gate(self,
                                                                  project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert (cell['source'], cell['current'], cell['counts']) == (
            'local', True, True)

    # purlin: states PROOF-150
    def test_a_section_taken_over_other_code_is_out_of_date(self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False,
                         fingerprint={'spec': 's', 'code': 'moved on',
                                      'tests': 't'})
        assert project.cell('RULE-2', 'passed')['word'] == 'out of date'

    # purlin: states PROOF-151
    def test_every_proof_of_the_rule_must_pass(self, project):
        project.spec(SPEC + '- PROOF-3 (RULE-2): POST /login with no '
                     'password; verify 401\n')
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'not run', cell

    # purlin: states PROOF-4
    def test_a_ci_section_meets_level_one(self, project):
        project.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                           'status': 'pass'}], ci=True)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert cell['source'] == 'ci'
        assert (cell['current'], cell['counts']) == (True, True), cell

    # purlin: states PROOF-6
    def test_a_local_section_counts_under_strong_and_signed(self):
        for gate in ('strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}], runner='dev',
                              source='local')
                cell = made.cell('RULE-2', 'passed')
                assert cell['word'] == 'passed', cell
                assert cell['source'] == 'local'
                assert cell['counts'] is True
                assert cell['reasons'] == [], cell
            finally:
                made.close()

    # purlin: states PROOF-7
    def test_a_test_report_alone_is_not_evidence(self):
        made = Project(gate='signed')
        try:
            _write(os.path.join(made.root, '.purlin', 'runtime', 'reports',
                                'pytest.xml'),
                   '<testsuite><testcase classname="tests.test_login" '
                   'name="test_proof_2"/></testsuite>')
            assert made.cell('RULE-2', 'passed')['word'] == 'no test', (
                'a report is not evidence')
        finally:
            made.close()

    # purlin: states PROOF-152
    def test_an_uncommitted_run_counts_at_signed(self):
        made = Project(gate='signed')
        try:
            made.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
            cell = made.cell('RULE-2', 'passed')
            assert cell['word'] == 'passed', cell
            assert cell['source'] == 'local'
            assert cell['counts'] is True
            assert cell['reasons'] == [], cell
        finally:
            made.close()

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
        assert 'windows: no run yet' in cell['reasons'], cell

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

    @staticmethod
    def _an_uncommitted_pass_over_a_marked_test(project):
        """A person's own passing section, left uncommitted. HEAD's sha."""
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert True\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'test(login): proof 1')
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], commit_it=False)
        return project.head()

    # purlin: states PROOF-118
    def test_a_spec_edit_leaves_it_out_of_date(self, project):
        seen = self._an_uncommitted_pass_over_a_marked_test(project)
        project.spec(SPEC.replace('return 200 with a session token',
                                  'return 200 and a session token'))
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['spec changed since %s' % seen[:7]], cell

    # purlin: states PROOF-119
    def test_a_test_edit_leaves_it_out_of_date(self, project):
        seen = self._an_uncommitted_pass_over_a_marked_test(project)
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert 1\n')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['tests changed since %s' % seen[:7]], cell

    # purlin: states PROOF-10
    def test_a_rule_no_test_backs_reads_no_test(self, project):
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'no test'
        assert (cell['source'], cell['current'], cell['counts']) == (
            None, False, False)


class TestTheStrongCell:

    # purlin: states PROOF-13
    def test_a_rule_that_did_not_pass_waits_for_its_tests(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True, strength=48)
            rule = made.rule('RULE-2')
            cell = rule['cells']['strong']
            assert cell['word'] == 'waiting', cell
            assert cell['reasons'] == ['waiting for its tests to pass'], cell
            assert cell['strength'] == 48, cell
            # The rule reads what its passed cell says.
            assert rule['cells']['passed']['word'] == 'no test', rule
        finally:
            made.close()

    @staticmethod
    def _strength_measured(strength):
        """RULE-1's strong cell at `strong` with mutation testing on, both
        proofs passing in a committed `ci` section that measured `strength`,
        and an audit that found nothing."""
        made = Project(gate='strong', extra_config={'mutation_engine': 'auto'})
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=strength)
            made.audit('RULE-1')
            return made.cell('RULE-1', 'strong')
        finally:
            made.close()

    # purlin: states PROOF-14
    def test_a_strength_under_the_minimum_is_weak_and_says_so(self):
        cell = self._strength_measured(48)
        assert cell['word'] == 'weak'
        assert cell['reasons'] == ['strength 48% under 70%'], cell
        assert cell['findings'] == [], cell

    # purlin: states PROOF-157
    def test_a_strength_of_exactly_the_minimum_is_not_under_it(self):
        at_minimum = self._strength_measured(70)
        assert at_minimum['word'] == 'strong', at_minimum
        assert at_minimum['reasons'] == [], at_minimum

    # purlin: states PROOF-15
    def test_with_no_score_the_cell_says_no_mutation_score_was_measured(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=None)
            made.audit('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong', cell
            assert cell['reasons'] == ['no mutation score measured'], cell
        finally:
            made.close()

    # purlin: states PROOF-158
    def test_a_loosely_worded_proof_decides_nothing_by_its_wording(self):
        made = Project(gate='strong', spec=SPEC.replace(
            'POST /login with a bad password; verify 401 and the '
            'body "denied"', 'Check that the login handles it properly'))
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=None)
            made.audit('RULE-2')
            loose = made.rule('RULE-2')
            assert loose['cells']['strong']['word'] == 'strong', loose
        finally:
            made.close()

    # purlin: states PROOF-16
    def test_a_field_the_format_does_not_name_decides_nothing(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-2', 'RULE-2')], ci=True)
            made.audit('RULE-2', tests=[{
                'proof': 'PROOF-2',
                'notes': ['The marked test body holds no assertion.']}])
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong', cell
            assert cell['findings'] == [], cell
            assert cell['evidence'] == '.purlin/evidence/local/login.json', cell
        finally:
            made.close()

    # purlin: states PROOF-159
    def test_a_weak_entry_carries_its_finding_as_the_reason(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-2', 'RULE-2')], ci=True)
            made.audit('RULE-2',
                       observations=['The test reads the status code alone.'])
            found = made.cell('RULE-2', 'strong')
            assert found['word'] == 'weak', found
            assert found['reasons'] == [
                'The test reads the status code alone.'], found
            assert found['findings'] == [
                'The test reads the status code alone.'], found
        finally:
            made.close()

    # purlin: states PROOF-160
    def test_an_entry_for_other_hashes_is_not_read(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-2', 'RULE-2')], ci=True)
            made.audit('RULE-2', rule_hash='0' * 64,
                       observations=['The test reads the status code alone.'])
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'not audited', cell
            assert cell['findings'] == [], cell
        finally:
            made.close()

    # purlin: states PROOF-17
    def test_a_rule_no_audit_read_is_not_audited(self):
        assert _strong()['word'] == 'not audited'
        assert _strong()['reasons'] == ['no audit has run on this code']

    # purlin: states PROOF-120
    def test_an_undecided_entry_gives_its_sentence(self):
        open_question = _strong(audit=_audit('undecided', [
            'The test body is not shown, so PROOF-1 cannot be read.']))
        assert open_question['word'] == 'weak', open_question
        assert open_question['reasons'] == [
            'the AI audit could not decide: The test body is not shown, so '
            'PROOF-1 cannot be read.'], open_question

    # purlin: states PROOF-121
    def test_an_undecided_entry_that_says_nothing(self):
        silent = _strong(audit=_audit('undecided'))
        assert silent['word'] == 'weak', silent
        assert silent['reasons'] == ['the AI audit could not decide'], silent

    # purlin: states PROOF-122
    def test_an_undecided_rule_is_left_to_strengthen(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')], ci=True)
            made.audit('RULE-1', settled=False)
            made.audit('RULE-2', settled=False, observations=[
                'The test body is not shown, so PROOF-2 cannot be read.'])
            rules = [rule for feature in made.payload()['features']
                     for rule in feature['rules']]
            assert [rule['cells']['strong']['word'] for rule in rules] == [
                'weak', 'weak'], rules
            assert [rule['left'] for rule in rules] == [
                'to_strengthen', 'to_strengthen'], rules
        finally:
            made.close()

    # purlin: states PROOF-18
    def test_at_signed_a_rule_no_audit_read_is_not_audited(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        result = purlin_states.rule_cells(STRONG_INPUT, cfg)
        assert result['cells']['strong']['word'] == 'not audited', result
        assert result['flags']['not_audited'] is True, result

    # purlin: states PROOF-19
    def test_a_manual_proof_asks_for_a_manual_test(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong'})
        result = purlin_states.rule_cells(dict(STRONG_INPUT, proofs=[
            {'id': 'PROOF-1', 'manual': True, 'env': None, 'text': 'x',
             'findings': [], 'tests': []}]), cfg)
        cell = result['cells']['strong']
        assert cell['word'] == 'manual test'
        assert cell['reasons'] == ['manual proof'], cell
        assert result['flags']['manual'] is True, result

    # purlin: states PROOF-123
    def test_a_proof_with_a_test_raises_no_manual_flag(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong'})
        tested = purlin_states.rule_cells(STRONG_INPUT, cfg)
        assert tested['flags']['manual'] is False, tested

    # purlin: states PROOF-23
    def test_a_strong_cell_with_an_engine_carries_no_reasons(self):
        made = Project(gate='strong', extra_config={'mutation_engine': 'auto'})
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=90)
            made.audit('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong'
            assert cell['reasons'] == [], cell
        finally:
            made.close()


class TestTheAuditOnTheRule:
    """What the AI audit left decides the strong cell, and every rule shows it."""

    # purlin: states PROOF-70
    def test_with_mutation_off_a_strength_left_behind_is_not_compared(self):
        made = Project(gate='strong', extra_config={'mutation_engine': 'none'})
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=40)
            made.audit('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong', cell
            assert cell['reasons'] == ['no mutation score measured'], cell
        finally:
            made.close()

    @staticmethod
    def _could_not_run(made):
        """RULE-2 passes, and the last audit could not reach the model for it."""
        made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                        'status': 'pass'}], ci=True)
        rule = made.rule('RULE-2')
        _write(os.path.join(made.root, '.purlin', 'runtime',
                            'audit_could_not_run.json'),
               json.dumps({'login': {'RULE-2': {
                   'rule_hash': rule['rule_hash'],
                   'proof_hash': rule['proof_hash'],
                   'test_hash': rule['test_hash'],
                   'why': 'claude is not on PATH'}}}))

    # purlin: states PROOF-71
    def test_a_rule_the_model_could_not_be_reached_for_says_why(self):
        made = Project(gate='strong')
        try:
            self._could_not_run(made)
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'not audited', cell
            assert cell['reasons'] == [
                'the AI audit could not run: claude is not on PATH'], cell
        finally:
            made.close()

    # purlin: states PROOF-172
    def test_a_could_not_run_record_ends_when_the_rule_changes(self):
        made = Project(gate='strong')
        try:
            self._could_not_run(made)
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True)
            cell = made.cell('RULE-2', 'strong')
            assert cell['reasons'] == ['no audit has run on this code'], cell
        finally:
            made.close()

    # purlin: states PROOF-72
    def test_a_new_strength_ends_the_signature_and_says_nothing(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.evidence(PASSING, ci=True, strength=90)
            made.audit('RULE-1')
            made.signature('RULE-1')
            assert made.cell('RULE-1', 'signed')['word'] == 'signed'
            made.evidence(PASSING, ci=True, strength=85)
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'strong', rule
            cell = rule['cells']['signed']
            assert (cell['word'], cell['signer'], cell['reasons']) == (
                'unsigned', None, []), cell
            assert rule['left'] == 'to_sign', rule['left']
        finally:
            made.close()

    @staticmethod
    def _audited_weak(gate, **named):
        """Both rules pass at `gate`, and the audit found RULE-2 weak.

        The project, still open; `named` adds fields to the audit entry.
        """
        made = Project(gate=gate)
        made.evidence(PASSING)
        made.audit('RULE-2', observations=['PROOF-2 reads 401 alone.'],
                   **named)
        return made

    # purlin: states PROOF-73
    def test_every_rule_carries_its_audit_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = self._audited_weak(gate)
            try:
                audit = made.rule('RULE-2')['audit']
                assert sorted(audit) == ['at', 'commit', 'findings', 'model',
                                         'notes', 'path', 'strength',
                                         'verdict'], audit
                assert audit['verdict'] == 'weak', (gate, audit)
                assert audit['findings'] == ['PROOF-2 reads 401 alone.']
                assert audit['notes'] == [], audit
                assert audit['model'] == 'unknown', audit
                assert audit['strength'] == 90, audit
                assert audit['path'] == '.purlin/evidence/local/login.json'
                assert audit['at'] == '2026-09-13T12:05:00Z', audit
                assert audit['commit'] == made.head(), audit
            finally:
                made.close()

    # purlin: states PROOF-106
    def test_a_rule_no_audit_entry_answers_carries_none(self):
        for gate in ('passed', 'strong', 'signed'):
            made = self._audited_weak(gate)
            try:
                assert made.rule('RULE-1')['audit'] is None, gate
            finally:
                made.close()

    # purlin: states PROOF-107
    def test_an_entry_naming_its_model_time_and_commit_is_carried(self):
        for gate in ('passed', 'strong', 'signed'):
            made = self._audited_weak(gate, model='claude-opus-5-5',
                                      at='2026-09-20T08:30:00Z',
                                      commit='b' * 40)
            try:
                audit = made.rule('RULE-2')['audit']
                assert (audit['model'], audit['at'], audit['commit']) == (
                    'claude-opus-5-5', '2026-09-20T08:30:00Z', 'b' * 40), (
                        gate, audit)
            finally:
                made.close()

    # purlin: states PROOF-108
    def test_the_notes_an_audit_wrote_are_carried(self):
        made = Project(gate='strong')
        try:
            made.evidence(PASSING)
            made.audit('RULE-2', notes=['PROOF-2 holds two cases.'])
            assert made.rule('RULE-2')['audit']['notes'] == [
                'PROOF-2 holds two cases.']
        finally:
            made.close()


class TestHoldsAndSignatures:
    """What a person's committed attestation does to the top two cells."""

    @staticmethod
    def _signed_project():
        made = Project(gate='signed')
        made.sign_commits()
        made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                       {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                      ci=True, strength=90)
        made.audit('RULE-1')
        made.audit('RULE-2')
        return made

    # purlin: states PROOF-22
    def test_a_signature_for_the_current_hashes_is_the_hand_check(self):
        made = Project(gate='signed', spec=SPEC.replace(
            'and a token\n', 'and a token @manual\n'))
        try:
            made.sign_commits()
            assert made.rule('RULE-1')['left'] == 'to_test_by_hand'
            made.signature('RULE-1')
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert rule['cells']['strong']['reasons'] == [
                'hand check by jane@acme.com'], rule
            assert rule['cells']['signed']['word'] == 'signed', rule
            assert (rule['hand_checked'], rule['left']) == (True, None), rule
        finally:
            made.close()

    # purlin: states PROOF-124
    def test_a_hand_check_over_another_rule_text_does_not_hold(self):
        made = Project(gate='signed', spec=SPEC.replace(
            'and a token\n', 'and a token @manual\n'))
        try:
            made.sign_commits()
            made.signature('RULE-1')
            made.spec(SPEC.replace('and a token\n', 'and a token @manual\n')
                      .replace('return 200 with a session token',
                               'return 201 with a session token'))
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'manual test', rule
            assert rule['left'] == 'to_test_by_hand', rule['left']
        finally:
            made.close()

    # purlin: states PROOF-125
    def test_a_hand_check_the_check_does_not_count_does_not_hold(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        manual = [{'id': 'PROOF-1', 'manual': True, 'env': None, 'text': 'x',
                   'tests': []}]
        inp = dict(STRONG_INPUT, proofs=manual, applies_to='login',
                   rule_hash='r' * 64, proof_hash='p' * 64,
                   test_hash='t' * 64, code_hash='c' * 64, machines={},
                   audit_hash='a' * 64)
        refused = _bound(inp, counts=False,
                         count_reason='the commit that added it is not signed')
        held = purlin_states.rule_cells(dict(inp, signatures=[refused]), cfg)
        assert held['cells']['strong']['word'] == 'manual test', held
        assert held['hand_checked'] is False, held

    # purlin: states PROOF-24
    def test_a_signature_over_the_current_hashes_signs_the_rule(self):
        made = self._signed_project()
        try:
            made.signature('RULE-1')
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'signed', cell
            assert cell['reasons'] == ['by jane@acme.com'], cell
        finally:
            made.close()

    # purlin: states PROOF-25
    def test_at_signed_every_rule_needs_a_signature(self):
        made = self._signed_project()
        try:
            rule = made.rule('RULE-2')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert rule['cells']['signed']['word'] == 'unsigned', rule
            assert rule['left'] == 'to_sign', rule['left']
        finally:
            made.close()

    # purlin: states PROOF-26
    def test_a_signature_the_check_does_not_count_leaves_it_unsigned(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        inp = dict(STRONG_INPUT, applies_to='login', rule_hash='r' * 64,
                   proof_hash='p' * 64, test_hash='t' * 64,
                   code_hash='c' * 64, machines={}, audit_hash='a' * 64,
                   audit=_audit())
        refused = _bound(inp, counts=False,
                         count_reason='the commit that added it is not signed')
        cell = purlin_states.rule_cells(dict(inp, signatures=[refused]),
                                        cfg)['cells']['signed']
        assert cell['word'] == 'unsigned', cell
        assert cell['reasons'] == ['the commit that added it is not signed']


# One project holding one rule at each of the five buckets, so the bucket, the
# gate and the review list are all read off the same evidence.
FIVE = (
    '# Feature: ledger\n\n'
    '> Description: Five rules, one per bucket.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A rule with no proof names none\n'
    '- RULE-2: A failing rule has a test that fails\n'
    '- RULE-3: A passed rule has no audit yet\n'
    '- RULE-4: A strong rule has no signature yet\n'
    '- RULE-5: A signed rule carries one\n\n'
    '## Proof\n\n'
    '- PROOF-2 (RULE-2): POST /session with the password "wrong"; verify 401\n'
    '- PROOF-3 (RULE-3): POST /session with the password "secret"; verify 200 '
    'and a rejected second attempt\n'
    '- PROOF-4 (RULE-4): POST /session 5 times with a wrong password; verify '
    '423 and an error body\n'
    '- PROOF-5 (RULE-5): POST /session with no body at all; verify 400 and an '
    'error body\n'
)


def _five_bucket_project():
    """A `signed` project with one rule in each of the five buckets."""
    made = Project(gate='signed', spec=None)
    made.spec(FIVE, name='ledger', category='core')
    _git(made.root, 'add', '-A')
    _git(made.root, 'commit', '-q', '-m', 'docs: the spec under test')
    made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'fail'},
                   {'id': 'PROOF-3', 'rule': 'RULE-3', 'status': 'pass'},
                   {'id': 'PROOF-4', 'rule': 'RULE-4', 'status': 'pass'},
                   {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'}],
                  feature='ledger', ci=True, strength=90)
    # RULE-3 is left without an audit entry, so it has only passed. The two
    # rules after it carry an audit entry that settled.
    made.audit('RULE-4', feature='ledger')
    made.audit('RULE-5', feature='ledger')
    made.sign_commits()
    made.signature('RULE-5', feature='ledger', category='core')
    return made


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
    def test_one_entry_per_operating_system_a_current_section_covers(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}],
                          os_name='linux', source='ci')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}],
                          os_name='windows', source='ci',
                          at='2026-09-13T13:00:00Z')
            cell = made.cell('RULE-1', 'passed')
            assert sorted(cell['platforms']) == ['linux', 'windows'], cell
            assert cell['platforms']['linux'] == {
                'word': 'passed', 'source': 'ci',
                'at': '2026-09-13T12:00:00Z'}, cell
            assert cell['platforms']['windows'] == {
                'word': 'passed', 'source': 'ci',
                'at': '2026-09-13T13:00:00Z'}, cell
            assert cell['word'] == 'passed', cell
        finally:
            made.close()

    # purlin: states PROOF-52
    def test_a_platform_a_proof_asks_for_and_nothing_ran_on_is_listed(self):
        made = Project(spec=ENV_SPEC, gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}],
                          os_name='linux', source='ci')
            cell = made.cell('RULE-1', 'passed')
            assert cell['platforms']['windows'] == {
                'word': 'not run', 'source': None, 'at': None}, cell
            assert cell['platforms']['linux']['word'] == 'passed', cell
        finally:
            made.close()

    # purlin: states PROOF-53
    def test_platforms_that_disagree_read_partial(self):
        made = Project(spec=ENV_SPEC, gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}],
                          os_name='linux', source='ci')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-1',
                            'status': 'fail'}],
                          os_name='windows', source='ci',
                          at='2026-09-13T13:00:00Z')
            rule = made.rule('RULE-1')
            cell = rule['cells']['passed']
            assert cell['word'] == 'partial', cell
            assert cell['reasons'] == ['passed on linux',
                                       'windows: failed'], cell
            assert rule['bucket'] == 'partial', rule['bucket']
            assert rule['flags']['partial'] is True, rule['flags']
            assert rule['flags']['failing'] is False, rule['flags']
            assert rule['left'] == 'to_fix', rule['left']
        finally:
            made.close()

    # purlin: states PROOF-54
    def test_an_older_section_that_is_out_of_date_is_not_read(self):
        """A failing section two edits old says nothing about this code."""
        cell = purlin_states.rule_cells({
            'proofs': STRONG_INPUT['proofs'],
            'sections': [
                _section('ci', 'linux', {'PROOF-1': 'fail'}, current=False,
                         at='2026-09-01T00:00:00Z', out_of_date=['code']),
                _section('local', 'macos', {'PROOF-1': 'pass'},
                         at='2026-09-02T00:00:00Z')],
        }, purlin_gate.resolve_gate({'gate': 'strong'}))['cells']['passed']
        assert cell['word'] == 'passed', cell
        assert sorted(cell['platforms']) == ['macos'], cell

    # purlin: states PROOF-50
    def test_a_file_whose_source_field_disagrees_is_left_out(self):
        made = Project(gate='strong')
        try:
            path = made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                   'status': 'pass'}],
                                 source='ci', claimed_source='local')
            data = made.payload()
            assert made.cell('RULE-1', 'passed')['word'] != 'passed'
            cell = made.cell('RULE-1', 'passed')
            assert (cell['word'], cell['source'], cell['platforms']) == (
                'no test', None, {}), cell
            named = [w for w in data['warnings'] if path in w]
            assert len(named) == 1, data['warnings']
            assert 'it is ignored' in named[0], named
        finally:
            made.close()

    # purlin: states PROOF-166
    def test_a_file_whose_source_field_agrees_is_read(self):
        made = Project(gate='strong')
        try:
            path = made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                   'status': 'pass'}], source='ci')
            assert made.cell('RULE-1', 'passed')['word'] == 'passed'
            assert not [w for w in made.payload()['warnings']
                        if '.purlin/evidence/' in w], path
        finally:
            made.close()

    @staticmethod
    def _passed_cell(gate, sections):
        """The passed cell of a rule of one proof, read from `sections`."""
        return purlin_states.rule_cells({
            'proofs': STRONG_INPUT['proofs'], 'sections': sections,
        }, purlin_gate.resolve_gate({'gate': gate}))['cells']['passed']

    # purlin: states PROOF-66
    def test_a_persons_own_section_answers_for_its_platform_at_every_gate(
            self):
        """A failing macOS section beside a passing Linux one reads
        `partial` wherever the gate is set."""
        linux = _section('ci', 'linux', {'PROOF-1': 'pass'},
                         at='2026-09-25T12:00:00Z')
        macos = _section('local', 'macos', {'PROOF-1': 'fail'},
                         at='2026-09-26T12:00:00Z')
        for gate in ('passed', 'strong', 'signed'):
            cell = self._passed_cell(gate, [linux, macos])
            assert cell['word'] == 'partial', (gate, cell)
            assert sorted(cell['platforms']) == ['linux', 'macos'], cell

    # purlin: states PROOF-167
    def test_a_persons_own_section_alone_passes_at_signed(self):
        alone = self._passed_cell('signed', [_section('local', 'macos')])
        assert alone['word'] == 'passed', alone
        assert alone['counts'] is True, alone
        assert alone['reasons'] == [], alone


class TestBucketsAndTheGate:

    # purlin: states PROOF-27
    def test_one_rule_in_each_of_the_five_buckets(self):
        made = _five_bucket_project()
        try:
            buckets = [made.rule('RULE-%d' % n, 'ledger')['bucket']
                       for n in range(1, 6)]
            assert buckets == ['untested', 'failing', 'passed', 'strong',
                               'signed'], buckets
        finally:
            made.close()

    # purlin: states PROOF-161
    def test_at_signed_the_rollup_counts_the_six_buckets_in_order(self):
        made = _five_bucket_project()
        try:
            rollup = _feature(made.payload(), 'ledger')['rollup']
            buckets = ('untested', 'failing', 'partial', 'passed', 'strong',
                       'signed')
            assert [key for key in rollup if key in buckets] == list(
                buckets), rollup
        finally:
            made.close()


class TestEveryRuleIsAskedWhatTheGateAsks:

    @staticmethod
    def _audited(gate):
        """Two rules whose tests pass and whose audit found nothing."""
        made = Project(gate=gate)
        made.evidence(PASSING, strength=90)
        made.audit('RULE-1')
        made.audit('RULE-2')
        return made

    # purlin: states PROOF-91
    def test_the_table_counts_strong_and_signed_over_every_rule(self):
        made = self._audited('signed')
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            header = next(line for line in lines if line.startswith('Spec'))
            login = next(line for line in lines if line.startswith('login '))
            assert login[header.index('Strong'):].split('  ')[0] == (
                '2 of 2 · 90%'), (header, login)
            assert login[header.index('Signed'):] == '0 of 2', (header, login)
        finally:
            made.close()

    # purlin: states PROOF-142
    def test_a_row_counts_strong_and_signed_over_its_rules(self):
        rollup = {'rules': 4, 'untested': 0, 'failing': 0, 'partial': 0,
                  'passed': 2, 'strong': 1, 'signed': 1, 'proofs': 4,
                  'test_strength': 86}
        row = purlin_status._row({'name': 'login', 'is_anchor': False,
                                  'rollup': rollup, 'rules': []}, 'signed')
        assert row[-2:] == ('2 of 4 · 86%', '1 of 4'), row

    # purlin: states PROOF-92
    def test_a_rule_whose_test_fails_waits_in_its_strong_cell(self):
        made = Project(gate='signed')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1', status='fail')])
            rule = made.rule('RULE-1')
            assert rule['cells']['passed']['word'] == 'failed', rule
            assert rule['cells']['strong']['word'] == 'waiting', rule
            assert rule['cells']['strong']['reasons'] == [
                'waiting for its tests to pass'], rule
            assert rule['bucket'] == 'failing', rule['bucket']
        finally:
            made.close()

    # purlin: states PROOF-93
    def test_a_signature_waits_for_the_tests(self):
        made = Project(gate='signed')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1', status='fail')])
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'waiting', rule
            assert rule['cells']['signed']['word'] == 'waiting', rule
            assert rule['cells']['signed']['reasons'] == [
                'waiting for the audit'], rule
        finally:
            made.close()

    # purlin: states PROOF-143
    def test_a_signature_waits_for_the_audit(self):
        made = Project(gate='signed')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'not audited', rule
            assert rule['cells']['signed']['word'] == 'waiting', rule
            assert rule['cells']['signed']['reasons'] == [
                'waiting for the audit'], rule
        finally:
            made.close()

    # purlin: states PROOF-144
    def test_a_hand_check_waits_on_a_person_and_not_on_the_audit(self):
        made = Project(gate='signed', spec=SPEC.replace(
            'and a token\n', 'and a token @manual\n'))
        try:
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'manual test', rule
            assert rule['cells']['signed']['word'] == 'unsigned', rule
            assert rule['cells']['signed']['reasons'] == [], rule
            assert rule['left'] == 'to_test_by_hand', rule['left']
        finally:
            made.close()

    # purlin: states PROOF-94
    def test_a_signature_over_old_text_waits_while_the_tests_do(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.evidence([_entry('PROOF-1', 'RULE-1')], ci=True)
            made.audit('RULE-1')
            made.signature('RULE-1')
            assert made.cell('RULE-1', 'signed')['word'] == 'signed'
            made.spec(SPEC.replace('return 200 with a session token',
                                   'return 201 with a session token'))
            rule = made.rule('RULE-1')
            assert rule['cells']['passed']['word'] == 'out of date', rule
            assert rule['cells']['strong']['word'] == 'waiting', rule
            assert rule['cells']['signed']['word'] == 'waiting', rule
            assert rule['cells']['signed']['reasons'] == [
                'waiting for the audit'], rule
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    # purlin: states PROOF-31
    def test_schema_ten_carries_the_documented_top_level(self, project):
        data = project.payload()
        assert data["schema_version"] == 10
        # Those keys and `schema_version`, and no other.
        assert sorted(data) == sorted((
            'schema_version', 'generated_at', 'generated_by', 'project',
            'version', 'commit', 'dirty', 'gate', 'summary', 'features',
            'left', 'finished', 'last_line', 'os_words', 'evidence',
            'tag', 'remote_url', 'warnings')), sorted(data)
        assert data['gate']['gate'] == 'passed'
        assert data['generated_at'].endswith('Z')

    # purlin: states PROOF-95
    def test_a_project_with_no_remote_has_a_null_remote_url(self, project):
        assert project.payload()['remote_url'] is None

    # purlin: states PROOF-162
    def test_the_remote_url_is_the_origin(self, project):
        _git(project.root, 'remote', 'add', 'origin',
             'https://github.com/acme/ledger.git')
        assert project.payload()['remote_url'] == (
            'https://github.com/acme/ledger.git')

    # purlin: states PROOF-32
    def test_a_feature_with_no_evidence_names_its_spec(self, project):
        feature = _feature(project.payload())
        assert feature['spec_path'] == 'specs/auth/login.md'
        assert feature['category'] == 'auth'
        assert feature['signatures'] == []
        assert feature['current'] is False
        assert feature['evidence'] == {'local': None, 'ci': None}

    # purlin: states PROOF-126
    def test_a_rule_carries_its_proofs_and_no_origin(self, project):
        rule = project.rule('RULE-1')
        assert 'origin' not in rule and 'criterion' not in rule
        assert rule['proofs'][0]['manual'] is False
        assert rule['proofs'][0]['env'] is None
        assert 'findings' not in rule['proofs'][0], rule['proofs'][0]

    # purlin: states PROOF-127
    def test_a_rule_carries_the_hash_of_what_the_audit_found(self, project):
        before = project.rule('RULE-1')['audit_hash']
        assert len(before) == 64 and set(before) <= set('0123456789abcdef')
        project.audit('RULE-1', observations=['PROOF-1 reads 200 alone.'])
        assert project.rule('RULE-1')['audit_hash'] != before

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

    # purlin: states PROOF-130
    def test_a_feature_says_its_evidence_is_no_longer_current(self, project):
        self._an_uncommitted_linux_section(project)
        _write(os.path.join(project.root, 'src', 'login.py'), 'x = 1\n')
        feature = _feature(project.payload())
        assert feature['current'] is False
        assert feature['evidence']['local']['platforms']['linux'][
            'current'] is False

    # purlin: states PROOF-29
    def test_the_rollup_counts_the_buckets_the_gate_reaches(self, project):
        _commit_tests(project, 'PROOF-2')
        project.evidence([_entry('PROOF-2', 'RULE-2')])
        data = project.payload()
        feature = next(f for f in data['features'] if f['name'] == 'login')
        rollup = feature['rollup']
        assert sorted(rollup) == sorted([
            'rules', 'untested', 'failing', 'partial', 'passed',
            'manual', 'not_audited', 'test_strength', 'proofs',
            'proofs_without_test', 'proofs_without_test_ids',
            'incomplete']), rollup
        assert rollup['rules'] == 2, rollup
        assert (rollup['passed'], rollup['untested']) == (1, 1), rollup
        assert (rollup['partial'], rollup['failing']) == (0, 0), rollup
        assert rollup['proofs'] == 2, rollup
        assert rollup['proofs_without_test'] == 1, (
            'PROOF-1 has no test; PROOF-2 was observed by the run')
        assert rollup['proofs_without_test_ids'] == ['PROOF-1'], rollup
        assert data['summary']['features'] == 1

    # purlin: states PROOF-57
    def test_the_proof_counts_call_out_a_proof_with_no_test(self, project):
        project.spec(
            '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
            '- RULE-1: Valid credentials return 200 with a session token\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): POST /login with valid credentials; verify '
            '200 and a token\n'
            '- PROOF-2 (RULE-1): POST /login twice; verify the second reply '
            'carries the same token\n'
            '- PROOF-3 (RULE-1): Sign in on the handset and read that the '
            'home screen names the account; verify it reads the email '
            '@manual\n')
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1')])
        rollup = next(f for f in project.payload()['features']
                      if f['name'] == 'login')['rollup']
        assert rollup['proofs'] == 3, rollup
        assert rollup['proofs_without_test'] == 1, rollup
        assert rollup['proofs_without_test_ids'] == ['PROOF-2'], rollup

    # purlin: states PROOF-84
    def test_a_marked_test_that_has_not_run_is_a_test(self, project):
        path = os.path.join(project.root, 'tests', 'test_login.py')
        _write(path, _marked_tests('PROOF-1'))
        data = project.payload()
        rollup = next(f for f in data['features']
                      if f['name'] == 'login')['rollup']
        for counted in (rollup, data['summary']):
            assert counted['proofs_without_test'] == 1, counted
            assert counted['proofs_without_test_ids'] == ['PROOF-2'], counted
        words = {rule['id']: rule['cells']['passed']['word']
                 for f in data['features'] for rule in f['rules']}
        assert words == {'RULE-1': 'not run', 'RULE-2': 'no test'}, words

    # purlin: states PROOF-175
    def test_a_marker_below_the_last_test_backs_nothing(self, project):
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'def test_x():\n    pass\n\n# purlin: login PROOF-1\n')
        rollup = next(f for f in project.payload()['features']
                      if f['name'] == 'login')['rollup']
        assert rollup['proofs_without_test'] == 2, rollup

    # purlin: states PROOF-56
    def test_the_signed_cell_carries_when_it_was_signed(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.signature('RULE-2')
            cell = made.cell('RULE-2', 'signed')
            assert cell['signer'] == 'jane@acme.com'
            # `at` is when the commit that added the signature was made, in
            # UTC, not the `2026-09-13T12:00:00Z` the file itself records.
            added = _git(made.root, 'log', '-1', '--format=%at').stdout.strip()
            assert cell['at'] == datetime.datetime.fromtimestamp(
                int(added), datetime.timezone.utc).strftime(
                    '%Y-%m-%dT%H:%M:%SZ'), (cell, added)
            assert cell['at'] != '2026-09-13T12:00:00Z', cell
        finally:
            made.close()

    # purlin: states PROOF-131
    def test_the_signed_cell_carries_the_name_and_the_key(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.signature('RULE-2', signer_name='Jane Doe',
                           key_fingerprint='SHA256:q4Xy')
            cell = made.cell('RULE-2', 'signed')
            assert (cell['signer_name'], cell['key_fingerprint']) == (
                'Jane Doe', 'SHA256:q4Xy'), cell
        finally:
            made.close()

    # purlin: states PROOF-132
    def test_a_signature_recording_no_name_or_key_gives_none(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.signature('RULE-1')
            other = made.cell('RULE-1', 'signed')
            assert other['signer'] == 'jane@acme.com', other
            assert (other['signer_name'], other['key_fingerprint']) == (
                None, None), other
        finally:
            made.close()

    # purlin: states PROOF-133
    def test_a_signature_no_commit_carries_reads_the_files_own_time(self):
        made = Project(gate='signed')
        try:
            made.signature('RULE-2', commit_it=False)
            cell = made.cell('RULE-2', 'signed')
            assert cell['signer'] == 'jane@acme.com', cell
            assert cell['at'] == '2026-09-13T12:00:00Z', cell
        finally:
            made.close()

    # purlin: states PROOF-30
    def test_global_anchor_rules_are_counted_once_in_the_summary(self, project):
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        data = project.payload()
        assert data['summary']['rules'] == 3, (
            'two own rules plus the anchor\'s one, counted once')
        assert data['summary']['features'] == 2
        login = next(f for f in data['features'] if f['name'] == 'login')
        assert login['rollup']['rules'] == 3, (
            'the feature must prove the global anchor\'s rule too')

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
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert text.startswith('const PURLIN_DATA = ') and text.endswith(';\n')
        read_back = json.loads(text[len('const PURLIN_DATA = '):-len(';\n')])
        assert read_back['commit'] == data['commit']
        # The whole payload, key for key.
        assert read_back == json.loads(json.dumps(data)), 'not the payload'

    # purlin: states PROOF-97
    def test_the_summary_and_what_is_left_ride_in_the_payload(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            data = made.payload()
            assert data['summary']['sentence'] == (
                '2 rules. 1 passes its tests. 0 are strong.')
            assert data['summary']['steps'] == {'passed': 1, 'strong': 0}
            assert data['left'] == [
                {'kind': 'no_test', 'count': 1,
                 'text': '1 rule to write a test for',
                 'command': 'purlin:build'},
                {'kind': 'to_audit', 'count': 1, 'text': '1 rule to audit',
                 'command': 'purlin:audit'}], data['left']
            assert (data['finished'], data['last_line']) == (False, None)
        finally:
            made.close()

    # purlin: states PROOF-98
    def test_nothing_left_is_finished(self, project):
        project.evidence(PASSING)
        data = project.payload()
        assert (data['left'], data['finished'], data['last_line']) == (
            [], True, 'Nothing left to do.'), data['left']

    # purlin: states PROOF-99
    def test_the_system_words_ride_in_the_payload(self, project):
        assert project.payload()['os_words'] == {
            'windows': {'word': 'Windows', 'short': 'Win'},
            'macos': {'word': 'macOS', 'short': 'Mac'},
            'linux': {'word': 'Linux/Unix', 'short': 'Lin'}}

    # purlin: states PROOF-111
    def test_a_shared_rule_is_signed_over_the_feature_it_is_listed_under(
            self, project):
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        data = project.payload()
        listed = {(f['name'], r['feature'], r['id']): r
                  for f in data['features'] for r in f['rules']}
        under_login = listed[('login', 'security', 'RULE-1')]
        assert under_login['applies_to'] == 'login'
        assert under_login['code_hash'] == purlin_fingerprint.code_hash(
            project.root, ['src/login.py'])
        assert listed[('security', 'security', 'RULE-1')][
            'applies_to'] == 'security'

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

    # purlin: states PROOF-113
    def test_a_section_that_names_no_machine_names_none(self, project):
        rel = project.evidence(PASSING, os_name='linux')
        path = os.path.join(project.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        del data['platforms']['linux']['machine']
        _write(path, json.dumps(data))
        for rule_id in ('RULE-1', 'RULE-2'):
            assert project.rule(rule_id)['machines'] == {}

    # purlin: states PROOF-114
    def test_a_hand_check_signed_with_a_note_is_checked(self):
        made = Project(gate='strong', spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'))
        try:
            made.sign_commits()
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            made.signature('RULE-2', note='saw 110.00')
            assert made.rule('RULE-2')['hand_checked'] is True
        finally:
            made.close()

    # purlin: states PROOF-115
    def test_a_hand_check_signed_without_a_note_is_checked(self):
        made = Project(gate='strong', spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'))
        try:
            made.sign_commits()
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            made.signature('RULE-2')
            assert made.rule('RULE-2')['hand_checked'] is True
        finally:
            made.close()

    # purlin: states PROOF-145
    def test_a_signed_rule_with_no_manual_proof_is_not_hand_checked(self):
        made = Project(gate='strong')
        try:
            made.sign_commits()
            made.evidence(PASSING)
            made.audit('RULE-2')
            made.signature('RULE-2')
            assert made.rule('RULE-2')['hand_checked'] is False
        finally:
            made.close()

    @staticmethod
    def _hand_check_at_passed():
        """At `passed`, RULE-1 passes and RULE-2's only proof is `@manual`."""
        made = Project(gate='passed', spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'))
        made.sign_commits()
        made.evidence([_entry('PROOF-1', 'RULE-1')])
        return made

    # purlin: states PROOF-146
    def test_at_passed_a_hand_check_not_made_is_not_passing(self):
        made = self._hand_check_at_passed()
        try:
            data = made.payload()
            assert _listed(data, 'RULE-2')['left'] == 'to_test_by_hand'
            assert data['summary']['sentence'] == (
                '2 rules. 1 passes its tests.'), data['summary']
        finally:
            made.close()

    # purlin: states PROOF-147
    def test_at_passed_a_hand_check_is_the_rules_passing(self):
        made = self._hand_check_at_passed()
        try:
            made.signature('RULE-2')
            data = made.payload()
            assert _listed(data, 'RULE-2')['left'] is None
            assert data['summary']['sentence'] == (
                '2 rules. 2 pass their tests.'), data['summary']
        finally:
            made.close()

    @staticmethod
    def _anchor_signed_under_login():
        """At `signed`, `login` and `billing` both prove a global anchor's
        audited rule, and only `login` has signed it."""
        made = Project(gate='signed')
        made.sign_commits()
        made.spec(SPEC.replace('login', 'billing'), name='billing',
                  category='billing')
        _write(os.path.join(made.root, 'src', 'billing.py'), 'X = 1\n')
        _git(made.root, 'add', '-A')
        _git(made.root, 'commit', '-q', '-m', 'feat: billing')
        made.spec('# Anchor: security\n\n> Global: true\n\n'
                  '## Rules\n\n- RULE-1: No eval anywhere\n\n'
                  '## Proof\n\n- PROOF-1 (RULE-1): Search the code for '
                  'eval; verify 0 matches\n', name='security',
                  category='_anchors')
        made.evidence([_entry('PROOF-1', 'RULE-1', feature='security')],
                      feature='security')
        made.audit('RULE-1', feature='security')
        made.signature('RULE-1', feature='security', category='_anchors',
                       listed_under='login')
        return made

    @staticmethod
    def _anchor_word(made, under):
        return _listed(made.payload(), 'RULE-1', 'security', under)['cells'][
            'signed']['word']

    # purlin: states PROOF-148
    def test_an_anchor_rule_is_signed_once_in_each_feature(self):
        made = self._anchor_signed_under_login()
        try:
            assert tuple(self._anchor_word(made, under) for under in (
                'login', 'billing', 'security')) == (
                    'signed', 'unsigned', 'unsigned')
        finally:
            made.close()

    # purlin: states PROOF-149
    def test_an_anchor_rule_signed_in_every_feature_reads_signed(self):
        made = self._anchor_signed_under_login()
        try:
            made.signature('RULE-1', feature='security', category='_anchors',
                           listed_under='billing')
            assert self._anchor_word(made, 'security') == 'signed'
        finally:
            made.close()

    # purlin: states PROOF-116
    def test_each_rule_names_the_one_kind_it_waits_for(self):
        made = Project(gate='strong')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            assert made.rule('RULE-1')['left'] is None
            assert made.rule('RULE-2')['left'] == 'to_audit'
        finally:
            made.close()


class TestTheFixturesAreTheContract:
    """The dashboard's fixtures and the builder's output are one shape.

    `dev/fixtures/report/{solo,team,regulated}.json` are written by hand, and
    the dashboard is built against them. A key the builder adds
    and the fixtures do not carry would render nowhere, so the two are
    compared key by key here rather than by eye.
    """

    FIXTURES = os.path.join(PROJECT_ROOT, 'dev', 'fixtures', 'report')

    @staticmethod
    def _fixture(name):
        with open(os.path.join(TestTheFixturesAreTheContract.FIXTURES,
                               name + '.json'), encoding='utf-8') as handle:
            return json.load(handle)

    # Where a payload keys a map by a name rather than by a field, such as
    # an operating system or a source, every name reads as one path.
    MAPS = ('.evidence', '.evidence.*', '.evidence.*.*',
            '.features[].evidence.ci.platforms',
            '.features[].evidence.local.platforms',
            '.features[].rules[].cells', '.features[].rules[].cells.*.platforms',
            '.features[].rules[].machines')

    @classmethod
    def _key_paths(cls, value, prefix='', found=None):
        """Every key path in `value`, lists read as `[]`."""
        found = set() if found is None else found
        if isinstance(value, dict):
            for key, inner in value.items():
                path = prefix + '.' + ('*' if prefix in cls.MAPS else key)
                found.add(path)
                cls._key_paths(inner, path, found)
        elif isinstance(value, list):
            for inner in value:
                cls._key_paths(inner, prefix + '[]', found)
        return found

    @staticmethod
    def _full_payload(gate):
        """A payload that fills every part a fixture fills: evidence from both
        sources, audit entries, a hand check left to do, a signature and
        the signed tag on HEAD."""
        made = Project(gate=gate, spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'),
            extra_config={'mutation_engine': 'auto'})
        try:
            made.sign_commits()
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], source='local')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True)
            made.audit('RULE-1')
            made.audit('RULE-2', observations=['PROOF-2 reads the status.'])
            made.signature('RULE-1')
            _git(made.root, 'tag', 'signed/1.0')
            return made.payload()
        finally:
            made.close()

    # purlin: states PROOF-82
    def test_the_fixtures_carry_exactly_the_keys_the_builder_writes(self):
        fixtures, built = set(), set()
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixtures |= self._key_paths(self._fixture(name))
            built |= self._key_paths(self._full_payload(gate))
        assert sorted(fixtures - built) == [], 'no builder writes these'
        assert sorted(built - fixtures) == [], 'no fixture carries these'

    # purlin: states PROOF-96
    def test_every_fixture_has_the_key_set_the_builder_writes(self):
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixture = self._fixture(name)
            assert fixture['schema_version'] == purlin_payload.SCHEMA_VERSION
            assert fixture['gate']['gate'] == gate
            made = Project(gate=gate)
            try:
                built = made.payload()
            finally:
                made.close()
            assert sorted(fixture) == sorted(built), name
            assert sorted(fixture['gate']) == sorted(built['gate']), name
            assert sorted(fixture['summary']) == sorted(built['summary']), name
            feature = fixture['features'][0]
            assert sorted(feature) == sorted(built['features'][0]), name
            assert sorted(feature['rollup']) == sorted(
                built['features'][0]['rollup']), name
            rule = feature['rules'][0]
            assert sorted(rule) == sorted(built['features'][0]['rules'][0]), name
            assert sorted(rule['cells']) == sorted(purlin_states.cells_for(gate))
            for cell_name, cell in rule['cells'].items():
                built_cell = built['features'][0]['rules'][0]['cells'][cell_name]
                assert sorted(cell) == sorted(built_cell), (name, cell_name)
            assert sorted(rule['flags']) == sorted(
                built['features'][0]['rules'][0]['flags']), name

    # purlin: states PROOF-171
    def test_the_tag_key_is_present_in_every_fixture(self):
        """The board's chip reads this key, so a fixture without it is a lie."""
        for name in ('solo', 'team'):
            assert self._fixture(name)['tag'] is None, name
        tag = self._fixture('regulated')['tag']
        assert sorted(tag) == ['commit', 'name']
        assert tag['name'].startswith('signed/')
        assert tag['commit'] == self._fixture('regulated')['commit']


class TestProofResult:

    @staticmethod
    def _proofs(project):
        rules = next(f for f in project.payload()['features']
                     if f['name'] == 'login')['rules']
        return {proof['id']: proof for rule in rules for proof in rule['proofs']}

    # purlin: states PROOF-85
    def test_a_proof_before_any_run_reads_not_run_or_no_test(self, project):
        _commit_tests(project, 'PROOF-1')
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'not run', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == []
        assert proofs['PROOF-2']['result'] == 'no test', proofs['PROOF-2']

    @staticmethod
    def _one_passes_one_fails(project):
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', status='fail')])

    # purlin: states PROOF-176
    def test_each_proof_carries_its_own_result_and_its_tests(self, project):
        self._one_passes_one_fails(project)
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'passed', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == [
            {'file': 'tests/test_login.py', 'name': 'test_proof_1',
             'result': 'pass'}], proofs['PROOF-1']['tests']
        assert proofs['PROOF-2']['result'] == 'failed', proofs['PROOF-2']
        assert [test['result'] for test in proofs['PROOF-2']['tests']] == [
            'fail'], proofs['PROOF-2']['tests']

    # purlin: states PROOF-177
    def test_a_manual_proof_reads_hand_check(self, project):
        self._one_passes_one_fails(project)
        project.spec(SPEC.replace('body "denied"\n', 'body "denied" @manual\n'))
        proofs = self._proofs(project)
        assert proofs['PROOF-2']['result'] == 'hand check'
        # The spec moved, so no current section lists PROOF-1's test.
        assert proofs['PROOF-1']['tests'] == [
            {'file': 'tests/test_login.py', 'name': 'test_proof_1',
             'result': 'not run'}], proofs['PROOF-1']['tests']

    # purlin: states PROOF-178
    def test_an_env_proof_reads_its_own_systems_sections_alone(self,
                                                               project):
        _commit_tests(project, 'PROOF-1')
        project.spec(SPEC.replace('body "denied"\n', 'body "denied" '
                                  '@env(linux)\n'))
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2')], os_name='linux')
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', status='fail')],
                         os_name='windows')
        proofs = self._proofs(project)
        assert proofs['PROOF-2']['result'] == 'passed', proofs['PROOF-2']
        assert [test['result'] for test in proofs['PROOF-2']['tests']] == [
            'pass'], proofs['PROOF-2']['tests']
        assert proofs['PROOF-1']['result'] == 'passed', proofs['PROOF-1']


# ---------------------------------------------------------------------------
# The status table
# ---------------------------------------------------------------------------

DASHBOARD_PAGE = os.path.join(PROJECT_ROOT, 'scripts', 'report',
                              'purlin-report.html')

# The dashboard's spec table as a reader sees it: its column headings, and
# each spec's name and the text of each of its cells, one line each.
DASHBOARD_ROWS = r"""els => {
  const head = Array.from(document.querySelectorAll('.th > div'))
    .map(d => d.textContent.trim());
  return [head, els.map(e => ({
    name: e.querySelector('.name .n').textContent.trim(),
    cells: head.map((label, i) =>
      e.children[i].innerText.trim().replace(/\s+/g, ' '))}))];
}"""


@pytest.fixture(scope='module')
def browser():
    playwright = pytest.importorskip('playwright.sync_api')
    from browser_launch import launch_browser
    with playwright.sync_playwright() as driver:
        instance = launch_browser(driver, headless=True)
        yield instance
        instance.close()


def _dashboard(browser, folder, payload):
    """`(headings, {spec: cells})` of the dashboard opened over `payload`."""
    os.makedirs(os.path.join(folder, '.purlin'))
    shutil.copyfile(DASHBOARD_PAGE, os.path.join(folder, 'purlin-report.html'))
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
        cells = [line[start:end].strip() for start, end in
                 zip(starts, starts[1:] + [len(line)])]
        rows[cells[0].replace(' (anchor)', '')] = cells
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


SECURITY_ANCHOR = (
    '# Anchor: security\n\n> Global: true\n\n'
    '## Rules\n\n- RULE-1: No eval anywhere\n\n'
    '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n')


def _requiring_api(project):
    """`login` requires `api`, an anchor of one rule that is not global."""
    project.spec(
        '# Anchor: api\n\n## Rules\n\n- RULE-1: Responses carry a type\n'
        '\n## Proof\n\n- PROOF-1 (RULE-1): GET /x; verify the header\n',
        name='api', category='_anchors')
    project.spec(SPEC.replace('# Feature: login\n',
                              '# Feature: login\n\n> Requires: api\n'))


class TestStatusTable:

    # purlin: states PROOF-58
    def test_the_table_and_the_dashboard_show_the_same_cells(
            self, browser, tmp_path):
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            sample = TestTheFixturesAreTheContract._fixture(name)
            headings, table = _table_cells(purlin_status._table(sample))
            shown, dashboard = _dashboard(browser, str(tmp_path / name),
                                          sample)
            assert shown == headings, (name, shown, headings)
            assert sorted(dashboard) == sorted(table), (name, dashboard)
            for spec, cells in table.items():
                assert dashboard[spec][1:] == cells[1:], (
                    name, spec, dashboard[spec], cells)

    # purlin: states PROOF-86
    def test_the_rules_cell_names_the_shared_rules(self, project):
        project.spec(SECURITY_ANCHOR, name='security', category='_anchors')
        lines = _status_lines(project.root)
        header = _header(lines)
        login = _row_of(lines, 'login')
        assert login[header.index('Rules'):].startswith('2 (+1 shared)'), (
            header, login)
        assert _cell_under(lines, 'security', 'Rules') == '1', lines

    # purlin: states PROOF-179
    def test_a_spec_proving_no_shared_rule_reads_its_own_count(self,
                                                              project):
        lines = _status_lines(project.root)
        assert _cell_under(lines, 'login', 'Rules') == '2', lines
        assert not [line for line in lines if 'shared' in line], lines

    # purlin: states PROOF-180
    def test_a_required_anchor_that_is_not_global_is_shared_too(self,
                                                                project):
        _requiring_api(project)
        lines = _status_lines(project.root)
        assert _cell_under(lines, 'login', 'Rules') == '2 (+1 shared)', lines

    # purlin: states PROOF-181
    def test_every_cell_starts_at_its_headings_left_edge(self, project):
        _requiring_api(project)
        # Every proof marked, one test passing and one failing, so under every
        # heading one row's cell is narrower than its column.
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               _marked_tests('PROOF-1', 'PROOF-2'))
        _write(os.path.join(project.root, 'tests', 'test_api.py'),
               _marked_tests('PROOF-1', feature='api'))
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'test: marked tests')
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', status='fail')])
        lines = _status_lines(project.root)
        header = _header(lines)
        rows = _table_rows(lines)
        assert len(rows) == 2, rows
        for heading in header.split():
            at = header.index(heading)
            widths = [len(row[at:].split('  ')[0]) for row in rows]
            assert min(widths) < max(widths + [len(heading)]), (heading, rows)
        for heading in header.split():
            at = header.index(heading)
            for row in rows:
                assert row[at] != ' ' and (at == 0 or row[at - 1] == ' '), (
                    heading, header, row)

    @staticmethod
    def _one_of_two_passing(project):
        _commit_tests(project, 'PROOF-2')
        project.evidence([_entry('PROOF-2', 'RULE-2')])

    # purlin: states PROOF-43
    def test_at_passed_the_table_shows_proofs_and_tests(self, project):
        self._one_of_two_passing(project)
        lines = _status_lines(project.root)
        header = _header(lines)
        assert header.split() == ['Spec', 'Rules', 'Proofs', 'Tests'], header
        assert _cell_under(lines, 'login', 'Proofs') == '2 · 1 no test', lines
        assert _cell_under(lines, 'login', 'Tests') == '1 of 2', lines

    # purlin: states PROOF-100
    def test_the_tests_cell_counts_a_failing_rule(self, project):
        self._one_of_two_passing(project)
        project.evidence([_entry('PROOF-1', 'RULE-1', 'fail'),
                          _entry('PROOF-2', 'RULE-2')])
        lines = _status_lines(project.root)
        assert _cell_under(lines, 'login', 'Tests') == (
            '1 of 2 · 1 failing'), lines

    # purlin: states PROOF-101
    def test_the_tests_cell_counts_a_partial_rule(self, project):
        self._one_of_two_passing(project)
        other = ('windows' if purlin_evidence.host_os() != 'windows'
                 else 'linux')
        project.evidence([_entry('PROOF-1', 'RULE-1', 'fail'),
                          _entry('PROOF-2', 'RULE-2')])
        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2')], os_name=other,
                         at='2026-09-13T13:00:00Z')
        lines = _status_lines(project.root)
        assert _cell_under(lines, 'login', 'Tests') == (
            '1 of 2 · 1 partial'), lines

    # purlin: states PROOF-103
    def test_at_strong_the_table_adds_the_strong_column(self):
        made = Project(gate='strong')
        try:
            lines = _status_lines(made.root)
            assert _header(lines).split() == [
                'Spec', 'Rules', 'Proofs', 'Tests', 'Strong'], lines
            assert _cell_under(lines, 'login', 'Strong') == '0 of 2 · n/a'
        finally:
            made.close()

    # purlin: states PROOF-165
    def test_at_signed_the_table_adds_the_signed_column(self):
        made = Project(gate='signed')
        try:
            lines = _status_lines(made.root)
            assert _header(lines).split() == [
                'Spec', 'Rules', 'Proofs', 'Tests', 'Strong', 'Signed'], lines
            assert _cell_under(lines, 'login', 'Strong') == '0 of 2 · n/a'
            assert _cell_under(lines, 'login', 'Signed') == '0 of 2'
        finally:
            made.close()

    # purlin: states PROOF-102
    def test_a_passed_project_with_no_proof_line_is_shown_no_proof_count(
            self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            lines = _status_lines(made.root)
            assert _header(lines).split() == ['Spec', 'Rules', 'Tests'], lines
            assert not [line for line in lines if 'proof' in line], lines
        finally:
            made.close()

    # purlin: states PROOF-48
    def test_retired_config_keys_print_the_update_directive(self):
        made = Project(extra_config={'spec_dir': 'elsewhere'})
        try:
            text = purlin_status.sync_status(made.root)
            assert '→ Run: purlin:init --update' in text, text
            lines = text.splitlines()
            sentence = made.payload()['summary']['sentence']
            assert lines[lines.index(sentence) - 1] == (
                '→ Run: purlin:init --update'), lines
        finally:
            made.close()

    @staticmethod
    def _brought_up_to_date():
        """A project `purlin:init --update` has brought up to date."""
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'init'))
        import update as purlin_update
        made = Project()
        with contextlib.redirect_stdout(io.StringIO()):
            assert purlin_update.main(['--yes', '--project-root',
                                       made.root]) == 0
        return made

    # purlin: states PROOF-104
    def test_an_updated_project_prints_no_update_line(self):
        made = self._brought_up_to_date()
        try:
            text = purlin_status.sync_status(made.root)
            assert 'purlin:init --update' not in text, text
        finally:
            made.close()

    # purlin: states PROOF-105
    def test_an_updated_project_prints_it_once_a_key_returns(self):
        made = self._brought_up_to_date()
        try:
            made.config_value('spec_dir', 'elsewhere')
            lines = _status_lines(made.root)
            sentence = made.payload()['summary']['sentence']
            assert lines[lines.index(sentence) - 1] == (
                '→ Run: purlin:init --update'), lines
        finally:
            made.close()

    # purlin: states PROOF-46
    def test_an_empty_project_says_what_to_run(self):
        made = Project(spec=None)
        try:
            assert _status_lines(made.root) == [
                'No specs found under specs/.',
                '→ Run: purlin:init to set this project up, or purlin:spec '
                'to write the first one.']
        finally:
            made.close()

    # purlin: states PROOF-47
    def test_no_emoji_and_only_the_four_glyphs(self):
        allowed = set('→▶▼─')
        for gate in ('passed', 'strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence(PASSING)
                made.audit('RULE-1')
                made.audit('RULE-2')
                text = purlin_status.sync_status(made.root)
                lines = text.splitlines()
                # At `signed` the Signed column and the lines of `Left to do`
                # print too, and hold to the same set.
                if gate == 'signed':
                    assert '  2 rules to sign: purlin:sign' in lines, text
                    assert 'Signed' in _header(lines), text
                for char in text:
                    assert ord(char) < 0x2000 or char in allowed, (gate,
                                                                   repr(char))
            finally:
                made.close()

    # purlin: states PROOF-49
    def test_the_repository_own_specs_print_the_table(self):
        text = purlin_status.sync_status(PROJECT_ROOT)
        header = next(line for line in text.splitlines()
                      if line.startswith('Spec'))
        assert 'Proofs' in header and 'Tests' in header, header
        assert any('of' in line for line in text.splitlines()), text
        # One row for every spec under specs/, named by its file, whose Tests
        # cell reads `<passed> of <rules>` over the rules its Rules cell counts.
        lines = text.splitlines()
        rules_at, tests_at = header.index('Rules'), header.index('Tests')
        top = lines.index(header) + 1
        rows = lines[top + 1:lines.index(lines[top], top + 1)]
        stems = sorted(name[:-3] for _, dirs, files in os.walk(
            os.path.join(PROJECT_ROOT, 'specs')) for name in files
            if name.endswith('.md'))
        named = sorted(row.split()[0] for row in rows)
        assert named == stems, (named, stems)
        for row in rows:
            owned = re.match(r'(\d+)(?: \(\+(\d+) shared\))?', row[rules_at:])
            tests = re.match(r'(\d+) of (\d+)(?:  |$| ·)', row[tests_at:])
            assert owned and tests, row
            assert int(tests.group(2)) == int(owned.group(1)) + int(
                owned.group(2) or 0), row
            assert int(tests.group(1)) <= int(tests.group(2)), row


# ---------------------------------------------------------------------------
# The signed tag on HEAD
# ---------------------------------------------------------------------------

class TestTheSignedTag:
    """The payload names the `signed/*` tag pointing at HEAD, or nothing."""

    # purlin: states PROOF-68
    def test_no_tag_reads_none(self):
        made = Project(gate='signed')
        try:
            assert made.payload()['tag'] is None
        finally:
            made.close()

    # purlin: states PROOF-168
    def test_a_tag_on_head_reads_its_name_and_head(self):
        made = Project(gate='signed')
        try:
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            tag = made.payload()['tag']
            assert tag['name'] == 'signed/1.2.0', tag
            assert tag['commit'] == made.head(), tag
        finally:
            made.close()

    # purlin: states PROOF-169
    def test_a_tag_that_is_not_on_head_says_nothing_about_this_code(self):
        made = Project(gate='signed')
        try:
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            _write(os.path.join(made.root, 'src', 'later.py'), 'X = 1\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'feat: more')
            assert made.payload()['tag'] is None
        finally:
            made.close()

    # purlin: states PROOF-170
    def test_the_newest_version_wins_where_several_point_at_head(self):
        made = Project(gate='signed')
        try:
            for name in ('signed/1.9.0', 'signed/1.10.0', 'signed/beta'):
                _git(made.root, 'tag', '-a', name, '-m', name)
            assert made.payload()['tag']['name'] == 'signed/1.10.0'
        finally:
            made.close()

    # purlin: states PROOF-83
    def test_below_signed_the_payload_names_no_tag(self):
        for gate in ('strong', 'passed'):
            made = Project(gate=gate)
            try:
                _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
                assert made.payload()['tag'] is None, gate
            finally:
                made.close()

    # purlin: states PROOF-174
    def test_raising_the_gate_to_signed_names_the_tag(self):
        for gate in ('strong', 'passed'):
            made = Project(gate=gate)
            try:
                _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
                made.config_value('gate', 'signed')
                assert made.payload()['tag']['name'] == 'signed/1.2.0', gate
            finally:
                made.close()


# ---------------------------------------------------------------------------
# A spec that names no files
# ---------------------------------------------------------------------------

NO_SCOPE_SPEC = SPEC.replace('> Scope: src/login.py\n', '')
PASSING = [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
           {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}]


def _feature(payload, name='login'):
    return next(f for f in payload['features'] if f['name'] == name)


class TestASpecThatNamesNoFiles:
    """Its tests still run and pass; only a signature needs its files named."""

    @staticmethod
    def _passing_payload(spec):
        """The payload of a project whose two rules pass, under `spec`."""
        made = Project(spec=spec)
        try:
            made.evidence(PASSING)
            return made.payload()
        finally:
            made.close()

    # purlin: states PROOF-74
    def test_a_spec_with_no_scope_line_is_incomplete(self):
        data = self._passing_payload(NO_SCOPE_SPEC)
        feature = _feature(data)
        assert feature['incomplete'] is True, feature
        assert feature['incomplete_reason'] == 'no > Scope: line', feature
        assert feature['rollup']['incomplete'] is True, feature['rollup']
        assert data['summary']['incomplete'] == 1, data['summary']
        # Its tests pass all the same.
        assert [rule['cells']['passed']['word']
                for rule in feature['rules']] == ['passed', 'passed']

    # purlin: states PROOF-134
    def test_a_scope_naming_nothing_that_exists_is_incomplete(self):
        feature = _feature(self._passing_payload(
            SPEC.replace('src/login.py', 'src/nowhere.py')))
        assert feature['incomplete'] is True, feature
        assert feature['incomplete_reason'] == (
            '> Scope: names nothing that exists'), feature

    # purlin: states PROOF-135
    def test_a_scope_naming_a_file_that_exists_is_complete(self):
        data = self._passing_payload(SPEC)
        feature = _feature(data)
        assert (feature['incomplete'], feature['incomplete_reason']) == (
            False, None), feature
        assert feature['rollup']['incomplete'] is False, feature['rollup']
        assert data['summary']['incomplete'] == 0, data['summary']

    # purlin: states PROOF-136
    def test_an_anchor_is_never_incomplete(self):
        made = Project()
        try:
            made.spec('# Anchor: shared\n\n## Rules\n\n- RULE-1: every '
                      'answer is JSON\n\n## Proof\n\n- PROOF-1 (RULE-1): an '
                      'answer parses as JSON\n', name='shared',
                      category='_anchors')
            data = made.payload()
            anchor = _feature(data, 'shared')
            assert anchor['is_anchor'] is True
            assert (anchor['incomplete'], anchor['incomplete_reason']) == (
                False, None)
            assert data['summary']['incomplete'] == 0
        finally:
            made.close()

    # purlin: states PROOF-75
    def test_at_signed_its_rules_read_unsigned_and_say_why(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='signed')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            for rule in _feature(made.payload())['rules']:
                assert rule['cells']['strong']['word'] == 'strong', rule
                assert rule['cells']['signed']['word'] == 'unsigned', rule
                assert rule['cells']['signed']['reasons'] == [
                    'the spec names no files in > Scope:, so a signature '
                    'cannot be tied to the code it governs'], rule
        finally:
            made.close()

    # purlin: states PROOF-137
    def test_at_signed_a_signature_on_it_does_not_count(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='signed')
        try:
            made.sign_commits()
            made.evidence(PASSING)
            made.audit('RULE-2')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'purlin: evidence at x')
            made.signature('RULE-2')
            rule = made.rule('RULE-2')
            assert rule['cells']['signed']['word'] == 'unsigned', rule
        finally:
            made.close()

    # purlin: states PROOF-138
    def test_below_signed_it_waits_for_nothing(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='strong')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            data = made.payload()
            assert _feature(data)['incomplete'] is True
            rules = _feature(data)['rules']
            assert [rule['cells']['strong']['word'] for rule in rules] == [
                'strong', 'strong'], rules
            assert [rule['left'] for rule in rules] == [None, None], rules
        finally:
            made.close()

    # purlin: states PROOF-76
    def test_status_names_one_spec_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(spec=NO_SCOPE_SPEC, gate=gate)
            try:
                lines = purlin_status.sync_status(made.root).splitlines()
                assert ('1 spec names no files, so its tests run every time: '
                        'login.') in lines, (gate, lines)
            finally:
                made.close()

    # purlin: states PROOF-109
    def test_status_names_two_specs_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.spec(NO_SCOPE_SPEC.replace('login', 'export'),
                          name='export')
                made.spec(NO_SCOPE_SPEC)
                lines = purlin_status.sync_status(made.root).splitlines()
                assert ('2 specs name no files, so their tests run every '
                        'time: export, login.') in lines, (gate, lines)
            finally:
                made.close()

    # purlin: states PROOF-110
    def test_status_says_nothing_when_every_spec_names_its_files(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(gate=gate)
            try:
                text = purlin_status.sync_status(made.root)
                assert ('names no files' not in text
                        and 'name no files' not in text), (gate, text)
            finally:
                made.close()

    # purlin: summary PROOF-26
    def test_at_signed_its_rules_are_left_to_tie_to_their_files(self):
        made = Project(spec=NO_SCOPE_SPEC,
                       gate='signed')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            lines = purlin_status.sync_status(made.root).splitlines()
            assert lines[-2:] == [
                'Left to do:', '  2 rules to tie to their files: purlin:spec'
            ], lines
        finally:
            made.close()
