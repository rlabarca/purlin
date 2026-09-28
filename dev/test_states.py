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
import sys

from mcp_project import (NO_PROOF_SPEC, ONE_RULE_SPEC, PROJECT_ROOT, Project,
                         SPEC, _commit_tests, _entry, _git, _marked_tests,
                         _rpc, _write, project)
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import board as purlin_board
from purlin import evidence as purlin_evidence
from purlin import gate as purlin_gate
from purlin import payload as purlin_payload
from purlin import states as purlin_states
from purlin import status as purlin_status


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

    # purlin: states PROOF-77
    def test_a_test_marked_with_the_rule_answers_the_passed_cell(self,
                                                                 project):
        project.spec('# Feature: login\n\n> Scope: src/login.py\n\n'
                     '## Rules\n\n- RULE-1: It works\n- RULE-2: It fails\n\n'
                     '## Proof\n\n')
        project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1', 'status': 'pass'},
                          {'id': 'RULE-2', 'rule': 'RULE-2', 'status': 'fail'}],
                         commit_it=False)
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        assert project.cell('RULE-2', 'passed')['word'] == 'failed'
        project.evidence([], commit_it=False)
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no proof written'], cell

    # purlin: states PROOF-78
    def test_above_passed_a_rule_with_a_test_and_no_proof_reads_no_proof(
            self):
        rule_spec = ('# Feature: login\n\n> Scope: src/login.py\n\n'
                     '## Rules\n\n- RULE-1: It works\n'
                     '- RULE-2: It is quick [level: passed]\n\n## Proof\n\n')
        for gate in ('strong', 'signed'):
            project = Project(spec=rule_spec, gate=gate)
            try:
                project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                                   'status': 'pass'},
                                  {'id': 'RULE-2', 'rule': 'RULE-2',
                                   'status': 'pass'}], commit_it=False)
                first = project.rule('RULE-1')
                assert first['cells']['passed']['word'] == 'passed'
                assert first['cells']['strong']['word'] == 'no proof', gate
                assert first['cells']['strong']['reasons'] == [
                    'the rule has a test and no proof']
                assert first['meets_gate'] is False, gate
                second = project.rule('RULE-2')
                assert sorted(second['cells']) == ['passed'], second
                assert second['meets_gate'] is True
            finally:
                project.close()
        # At `passed` proofs are optional: the test alone meets the gate.
        project = Project(spec=rule_spec, gate='passed')
        try:
            project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                               'status': 'pass'}], commit_it=False)
            first = project.rule('RULE-1')
            assert sorted(first['cells']) == ['passed'], first
            assert first['cells']['passed']['word'] == 'passed', first
            assert first['meets_gate'] is True, first
        finally:
            project.close()


class TestThePassedCell:

    # purlin: states PROOF-3
    def test_a_local_section_meets_level_one_under_the_passed_gate(self,
                                                                  project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert (cell['source'], cell['current'], cell['counts']) == (
            'local', True, True)
        # A section taken over other code is not current, so it decides
        # nothing.
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False,
                         fingerprint={'spec': 's', 'code': 'moved on',
                                      'tests': 't'})
        assert project.cell('RULE-2', 'passed')['word'] == 'out of date'
        # Every proof must pass: a second proof of RULE-2 the section does not
        # show passing keeps the cell short of `passed`.
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
    def test_an_uncommitted_run_counts_and_a_report_alone_does_not(
            self):
        made = Project(gate='signed')
        try:
            _write(os.path.join(made.root, '.purlin', 'runtime', 'reports',
                                'pytest.xml'),
                   '<testsuite><testcase classname="tests.test_login" '
                   'name="test_proof_2"/></testsuite>')
            assert made.cell('RULE-2', 'passed')['word'] == 'no test', (
                'a report is not evidence')
            _write(os.path.join(made.root, '.purlin', 'runtime', 'proofs',
                                'login.json'),
                   json.dumps({'proofs': [_entry('PROOF-2', 'RULE-2')]}))
            assert made.cell('RULE-2', 'passed')['word'] == 'no test', (
                'a runtime proof file is not evidence')
            made.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
            cell = made.cell('RULE-2', 'passed')
            assert cell['word'] == 'passed', cell
            assert cell['source'] == 'local'
            assert cell['counts'] is True
            assert cell['reasons'] == [], cell
        finally:
            made.close()

    # purlin: states PROOF-8
    def test_an_env_proof_needs_a_section_from_that_operating_system(
            self, project):
        project.spec(
            '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
            '- RULE-1: Files lock\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Lock a file; verify a second open '
            'returns 0 handles @env(windows)\n')
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], os_name='linux')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'not run'
        assert cell['missing_env'] == ['windows'], cell
        assert 'windows: no run yet' in cell['reasons'], cell
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], os_name='windows',
                         at='2026-09-13T13:00:00Z')
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'

    # purlin: states PROOF-9
    def test_out_of_date_when_the_code_moved(self, project):
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}])
        seen = _git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 200  # rewritten\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'refactor: login')
        rule = project.rule('RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell
        assert cell['current'] is False, cell
        assert rule['flags']['out_of_date'] is True
        assert rule['meets_gate'] is False
        # The next run clears it.
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}])
        rule = project.rule('RULE-1')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['flags']['out_of_date'] is False, rule

    # purlin: states PROOF-9
    def test_a_spec_edit_and_a_test_edit_leave_it_out_of_date_too(self,
                                                                  project):
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert True\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'test(login): proof 1')
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], commit_it=False)
        seen = project.head()
        project.spec(SPEC.replace('return 200 with a session token',
                                  'return 200 and a session token'))
        cell = project.cell('RULE-1', 'passed')
        assert cell['reasons'] == ['spec changed since %s' % seen[:7]], cell
        project.spec(SPEC)
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

    # purlin: states PROOF-12
    def test_a_cell_above_the_gate_is_absent(self):
        expected = {'passed': ['passed'],
                    'strong': ['passed', 'strong'],
                    'signed': ['passed', 'strong', 'signed']}
        for gate, names in expected.items():
            made = Project(gate=gate)
            try:
                rule = made.rule('RULE-1')
                assert sorted(rule['cells']) == sorted(names), (gate, rule)
            finally:
                made.close()

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
            # The rule reads what its passed cell says, and `waiting` is not
            # met.
            assert rule['cells']['passed']['word'] == 'no test', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (
                False, 'passed'), rule
        finally:
            made.close()

    # purlin: states PROOF-14
    def test_a_strength_under_the_minimum_is_weak_and_says_so(self):
        made = Project(gate='strong', extra_config={'mutation_engine': 'auto'})
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=48)
            made.audit('RULE-1')
            cell = made.cell('RULE-1', 'strong')
            assert cell['word'] == 'weak'
            assert cell['reasons'] == ['strength 48% under 70%'], cell
            assert cell['findings'] == [], cell
            # A strength of exactly the minimum is not under it.
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=70)
            at_minimum = made.cell('RULE-1', 'strong')
            assert at_minimum['word'] == 'strong', at_minimum
            assert at_minimum['reasons'] == [], at_minimum
        finally:
            made.close()

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
            # A loosely worded proof decides nothing by its wording: the
            # strong cell is the audit's.
            made.spec(SPEC.replace(
                'POST /login with a bad password; verify 401 and the '
                'body "denied"', 'Check that the login handles it properly'))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=None)
            made.audit('RULE-2')
            loose = made.rule('RULE-2')
            assert loose['cells']['strong']['word'] == 'strong', loose
        finally:
            made.close()

    # purlin: states PROOF-16
    def test_a_field_the_format_does_not_name_decides_nothing(self):
        # An entry carrying a field the evidence format does not name, here
        # a sentence about the test body, is read for its `verdict` and its
        # `findings` alone, so an entry that found nothing leaves the cell
        # strong.
        cell = _strong(audit=_audit(
            tests=[{'proof': 'PROOF-1',
                    'notes': ['The marked test body holds no assertion.']}]))
        assert cell['word'] == 'strong', cell
        assert cell['findings'] == [], cell
        assert cell['evidence'] == '.purlin/evidence/local/login.json', cell
        found = _strong(audit=_audit('weak', [
            'The test reads the status code alone.']))
        assert found['word'] == 'weak', found
        assert found['reasons'] == [
            'The test reads the status code alone.'], found
        assert found['findings'] == [
            'The test reads the status code alone.'], found

    # purlin: states PROOF-16
    def test_an_entry_for_other_hashes_is_not_read(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-2', 'RULE-2')], ci=True)
            made.audit('RULE-2', rule_hash='0' * 64,
                       observations=['The test reads the status code alone.'])
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'not audited', cell
            assert cell['findings'] == [], cell
            made.audit('RULE-2',
                       observations=['The test reads the status code alone.'])
            assert made.cell('RULE-2', 'strong')['word'] == 'weak'
        finally:
            made.close()

    # purlin: states PROOF-17
    def test_the_audit_entry_settles_level_two_where_the_level_asks(self):
        assert _strong()['word'] == 'not audited'
        assert _strong()['reasons'] == ['no audit has run on this code']
        open_question = _strong(audit=_audit('undecided', [
            'The test body is not shown, so PROOF-1 cannot be read.']))
        assert open_question['word'] == 'weak', open_question
        assert open_question['reasons'] == [
            'the AI audit could not decide: The test body is not shown, so '
            'PROOF-1 cannot be read.'], open_question
        silent = _strong(audit=_audit('undecided'))
        assert silent['reasons'] == ['the AI audit could not decide'], silent
        settled = _strong(audit=_audit('strong'))
        assert settled['word'] == 'strong', settled

    # purlin: states PROOF-17
    def test_an_undecided_rule_is_never_in_the_queue(self):
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')], ci=True)
            made.audit('RULE-1', settled=False)
            made.audit('RULE-2', settled=False, observations=[
                'The test body is not shown, so PROOF-2 cannot be read.'])
            data = made.payload()
            words = [rule['cells']['strong']['word']
                     for feature in data['features']
                     for rule in feature['rules']]
            assert words == ['weak', 'weak'], words
            assert data['queue'] == [], data['queue']
            assert data['summary']['queue'] == 0, data['summary']
        finally:
            made.close()

    # purlin: states PROOF-18
    def test_a_passed_level_is_never_owed_an_audit(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong'})
        lower = purlin_states.rule_cells(
            dict(STRONG_INPUT, level_marked='passed'), cfg)
        assert sorted(lower['cells']) == ['passed'], lower
        assert lower['flags']['not_audited'] is False, lower
        assert lower['meets_gate'] is True, lower
        assert _strong()['word'] == 'not audited'
        assert _strong(level_marked='signed')['word'] == 'not audited'

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

    # purlin: states PROOF-71
    def test_a_rule_the_model_could_not_be_reached_for_says_why(self):
        made = Project(gate='strong')
        try:
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
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'not audited', cell
            assert cell['reasons'] == [
                'the AI audit could not run: claude is not on PATH'], cell
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True)
            cell = made.cell('RULE-2', 'strong')
            assert cell['reasons'] == ['no audit has run on this code'], cell
        finally:
            made.close()

    # purlin: states PROOF-72
    def test_a_fresh_finding_stales_the_signature_and_says_so(self):
        made = Project(gate='signed')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True)
            made.audit('RULE-1')
            made.signature('RULE-1')
            assert made.cell('RULE-1', 'signed')['word'] != 'stale'
            made.audit('RULE-1',
                       observations=['PROOF-2 reads the status alone.'])
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'stale', cell
            assert cell['reasons'] == [
                'audit findings changed after the signature'], cell
        finally:
            made.close()

    # purlin: states PROOF-73
    def test_every_rule_carries_its_audit_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}])
                made.audit('RULE-2', observations=['PROOF-2 reads 401 alone.'])
                audit = made.rule('RULE-2')['audit']
                assert sorted(audit) == ['at', 'commit', 'findings', 'model',
                                         'path', 'strength', 'verdict'], audit
                assert audit['verdict'] == 'weak', (gate, audit)
                assert audit['findings'] == ['PROOF-2 reads 401 alone.']
                assert audit['model'] == 'unknown', audit
                assert audit['strength'] == 90, audit
                assert audit['path'] == '.purlin/evidence/local/login.json'
                assert audit['at'] == '2026-09-13T12:05:00Z', audit
                assert audit['commit'] == made.head(), audit
                assert made.rule('RULE-1')['audit'] is None, gate
                # An entry that names its model, its time and its commit is
                # carried with its own.
                made.audit('RULE-2', observations=['PROOF-2 reads 401 alone.'],
                           model='claude-opus-5-5', at='2026-09-20T08:30:00Z',
                           commit='b' * 40)
                audit = made.rule('RULE-2')['audit']
                assert (audit['model'], audit['at'], audit['commit']) == (
                    'claude-opus-5-5', '2026-09-20T08:30:00Z', 'b' * 40), audit
            finally:
                made.close()


class TestHoldsAndSignatures:
    """What a person's committed attestation does to the top two cells."""

    @staticmethod
    def _signed_project():
        made = Project(gate='signed')
        made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                       {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                      ci=True, strength=90)
        # RULE-1 is marked `signed` and RULE-2 takes the gate, so both are at
        # the level `signed`: the AI audit is owed on each, and the strong
        # cell reads `not audited` until an audit entry exists.
        made.audit('RULE-1')
        made.audit('RULE-2')
        return made

    # purlin: states PROOF-22
    def test_a_signature_for_the_current_hashes_clears_the_hand_check(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        manual = [{'id': 'PROOF-1', 'manual': True, 'env': None, 'text': 'x',
                   'tests': []}]
        inp = dict(STRONG_INPUT, proofs=manual, audit_hash='a' * 64)
        before = purlin_states.rule_cells(inp, cfg)
        assert before['cells']['strong']['word'] == 'manual test', before
        assert before['need'] == 'hand check', before
        signature = {'rule_hash': None, 'proof_hash': None, 'test_hash': None,
                     'audit_hash': 'a' * 64, 'counts': True,
                     'signer': 'jane@acme.com', 'path': 'x.json'}
        after = purlin_states.rule_cells(dict(inp, signatures=[signature]),
                                         cfg)
        assert after['cells']['strong']['word'] == 'strong', after
        assert after['cells']['signed']['word'] == 'signed', after
        assert after['need'] is None, after
        # A signature bound to older hashes, or one that does not count,
        # leaves the hand check owed.
        older = dict(signature, rule_hash='0' * 64)
        refused = dict(signature, counts=False,
                       count_reason='the signing commit is not signed')
        for held_by in (older, refused):
            held = purlin_states.rule_cells(dict(inp, signatures=[held_by]),
                                            cfg)
            assert held['cells']['strong']['word'] == 'manual test', held
            assert held['need'] == 'hand check', held

    # purlin: states PROOF-24
    def test_a_signature_is_read_until_the_hashes_move_under_it(self):
        made = self._signed_project()
        try:
            made.sign_commits()
            made.signature('RULE-1')
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'signed', cell
            assert cell['reasons'] == ['by jane@acme.com'], cell
            made.spec(SPEC.replace('return 200 with a session token',
                                   'return 201 with a session token'))
            rule = made.rule('RULE-1')
            assert rule['cells']['signed']['word'] == 'stale'
            assert rule['cells']['signed']['reasons'] == [
                'hashes changed after the signature'], rule
            assert rule['flags']['stale'] is True
        finally:
            made.close()

    # purlin: states PROOF-25
    def test_a_signature_is_needed_where_the_level_is_signed(self):
        made = self._signed_project()
        try:
            made.spec(SPEC.replace(
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied"',
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied" [level: strong]'))
            # The tag is part of the spec the evidence is checked against, so
            # the tests run again; the rule text did not change, so the audit
            # entries still bind.
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=90)
            lower = made.rule('RULE-2')
            assert lower['level'] == 'strong', lower
            assert lower['cells']['strong']['word'] == 'strong', lower
            assert 'signed' not in lower['cells'], lower
            assert (lower['meets_gate'], lower['blocked_by']) == (True, None)
            higher = made.rule('RULE-1')
            assert higher['level'] == 'signed', higher
            assert higher['cells']['signed']['word'] == 'unsigned', higher
            assert (higher['meets_gate'], higher['blocked_by']) == (
                False, 'signed')
            # Whatever signature files it has: one signed for the lower rule
            # in a signed commit still gives it no signed cell.
            made.sign_commits()
            path = made.signature('RULE-2')
            feature = next(f for f in made.payload()['features']
                           if f['name'] == 'login')
            assert [os.path.basename(p) for p in feature['signatures']] == [
                os.path.basename(path)], feature['signatures']
            lower = made.rule('RULE-2')
            assert 'signed' not in lower['cells'], lower
            assert (lower['meets_gate'], lower['blocked_by']) == (True, None)
        finally:
            made.close()

    # purlin: states PROOF-26
    def test_an_unsigned_signing_commit_leaves_the_rule_unsigned(self):
        made = self._signed_project()
        try:
            made.signature('RULE-1')
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'unsigned', cell
            assert cell['reasons'] == [
                'the signing commit is not signed'], cell
        finally:
            made.close()


# One project holding one rule at each of the five buckets, so the bucket, the
# gate and the review list are all read off the same evidence.
FIVE = (
    '# Feature: ledger\n\n'
    '> Description: Five rules, one per bucket.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A rule with no proof names none [level: passed]\n'
    '- RULE-2: A failing rule has a test that fails [level: passed]\n'
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
            assert rule['meets_gate'] is False
            assert rule['blocked_by'] == 'passed'
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
            'level_marked': 'passed',
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
            # The same file with its field agreeing is read.
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], source='ci')
            assert made.cell('RULE-1', 'passed')['word'] == 'passed'
        finally:
            made.close()

    # purlin: states PROOF-66
    def test_a_persons_own_section_answers_for_its_platform_at_every_gate(
            self):
        """A local section is a platform's answer at `signed` as at `strong`.

        Both sources count at every gate, so a red macOS section beside a
        green Linux one reads `partial` wherever the gate is set, and a local
        section alone reads `passed`.
        """
        def cells(gate, sections):
            return purlin_states.rule_cells({
                'proofs': STRONG_INPUT['proofs'], 'sections': sections,
                'level_marked': 'passed',
            }, purlin_gate.resolve_gate({'gate': gate}))['cells']['passed']

        linux = _section('ci', 'linux', {'PROOF-1': 'pass'},
                         at='2026-09-25T12:00:00Z')
        macos = _section('local', 'macos', {'PROOF-1': 'fail'},
                         at='2026-09-26T12:00:00Z')
        for gate in ('passed', 'strong', 'signed'):
            cell = cells(gate, [linux, macos])
            assert cell['word'] == 'partial', (gate, cell)
            assert sorted(cell['platforms']) == ['linux', 'macos'], cell

        alone = cells('signed', [_section('local', 'macos')])
        assert alone['word'] == 'passed', alone
        assert alone['counts'] is True, alone
        assert alone['reasons'] == [], alone

    # purlin: states PROOF-55
    def test_a_passed_level_has_no_strong_cell_whatever_the_audit_found(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        found = {'verdict': 'weak', 'findings': ['PROOF-1 reads 200 alone.'],
                 'path': '.purlin/evidence/local/login.json'}
        signature = {'rule_hash': None, 'proof_hash': None, 'test_hash': None,
                     'audit_hash': None, 'counts': True,
                     'signer': 'jane@acme.com', 'path': 'x.json'}
        for audit in (None, found, dict(found, verdict='strong',
                                        findings=[])):
            for signatures in ([], [signature]):
                result = purlin_states.rule_cells({
                    'proofs': STRONG_INPUT['proofs'],
                    'sections': [_section('local', 'macos')],
                    'level_marked': 'passed', 'audit': audit,
                    'signatures': signatures,
                }, cfg)
                assert sorted(result['cells']) == ['passed'], (audit, result)
                assert result['bucket'] == 'passed', (audit, result)
                assert result['flags']['not_audited'] is False, result
                assert result['flags']['manual'] is False, result
                assert result['meets_gate'] is True, result
                assert 'reads 200 alone' not in json.dumps(result), result
        # Read from a project: the finding is carried under `audit` alone,
        # and a signature in a signed commit gives the rule no signed cell.
        made = Project(gate='signed', spec=SPEC.replace(
            '"denied"\n\n', '"denied" [level: passed]\n\n'))
        try:
            made.evidence(PASSING)
            made.audit('RULE-2', observations=['PROOF-2 reads 401 alone.'])
            made.sign_commits()
            made.signature('RULE-2')
            data = made.payload()
            rule = next(r for r in _feature(data)['rules'] if r['id'] == 'RULE-2')
            assert sorted(rule['cells']) == ['passed'], rule
            assert (rule['bucket'], rule['meets_gate']) == ('passed', True)
            assert (rule['flags']['manual'], rule['flags']['not_audited']) == (
                False, False), rule['flags']
            assert rule['audit']['findings'] == ['PROOF-2 reads 401 alone.']
            rest = dict(data, features=[dict(f, rules=[
                dict(r, audit=None) for r in f['rules']])
                for f in data['features']])
            assert 'reads 401 alone' not in json.dumps(rest), rest
        finally:
            made.close()
        unmarked = purlin_states.rule_cells({
            'proofs': STRONG_INPUT['proofs'],
            'sections': [_section('local', 'macos')], 'audit': found,
        }, cfg)
        assert unmarked['cells']['strong']['word'] == 'weak', unmarked


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

    # purlin: states PROOF-27
    def test_partial_sits_between_failing_and_passed(self):
        assert purlin_states.bucket_keys('signed') == [
            'untested', 'failing', 'partial', 'passed', 'strong', 'signed']
        assert purlin_states.bucket_keys('passed') == [
            'untested', 'failing', 'partial', 'passed']

    # purlin: states PROOF-28
    def test_the_gate_is_met_by_one_of_them_and_blocked_by_name(self):
        made = _five_bucket_project()
        try:
            rules = [made.rule('RULE-%d' % n, 'ledger') for n in range(1, 6)]
            assert [r['meets_gate'] for r in rules] == [
                False, False, False, False, True]
            assert [r['blocked_by'] for r in rules] == [
                'passed', 'passed', 'strong', 'signed', None]
        finally:
            made.close()


class TestLevels:

    # purlin: states PROOF-59
    def test_a_level_is_the_tag_under_the_gate_or_the_gate(self):
        spec = SPEC.replace(
            '[level: signed]', '[level: passed]').replace(
            '"denied"\n\n', '"denied" [level: signed]\n\n', 1).replace(
            '## Proof', '- RULE-3: A locked account returns 423\n\n## Proof', 1)
        made = Project(spec=spec, gate='strong')
        try:
            rules = [made.rule('RULE-%d' % n) for n in (1, 2, 3)]
            assert [r['level'] for r in rules] == [
                'passed', 'strong', 'strong'], rules
            assert [r['level_marked'] for r in rules] == [
                'passed', 'signed', None], rules
            made.config_value('gate', 'signed')
            assert [made.rule('RULE-%d' % n)['level'] for n in (1, 2, 3)] == [
                'passed', 'signed', 'signed']
        finally:
            made.close()

    # purlin: states PROOF-61
    def test_the_level_decides_which_cells_block(self):
        def retag(made, tag):
            made.spec(SPEC.replace('"denied"\n\n', '"denied"%s\n\n' % tag, 1))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], strength=None)
            return made.rule('RULE-2')

        made = Project(gate='signed')
        try:
            rule = retag(made, ' [level: passed]')
            assert sorted(rule['cells']) == ['passed'], rule
            assert rule['cells']['passed']['word'] == 'passed', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (True, None)
            rule = retag(made, ' [level: strong]')
            assert sorted(rule['cells']) == ['passed', 'strong'], rule
            assert rule['cells']['strong']['word'] == 'not audited', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (
                False, 'strong')
            made.audit('RULE-2')
            rule = made.rule('RULE-2')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (True, None)
            rule = retag(made, '')
            assert rule['level'] == 'signed', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (
                False, 'signed')
        finally:
            made.close()


# One spec with a rule at each level under the gate `signed`, and a rule at
# `passed` and one at `strong` whose tests fail: a rule is asked only what its
# level asks.
LEVELS_SPEC = (
    '# Feature: login\n\n'
    '> Description: One rule at each level.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 [level: passed]\n'
    '- RULE-2: Invalid credentials return 401 [level: strong]\n'
    '- RULE-3: Five failures lock the account\n'
    '- RULE-4: The page loads in a second [level: passed]\n'
    '- RULE-5: A locked account returns 423 [level: strong]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401\n'
    '- PROOF-3 (RULE-3): POST /login 5 times with a bad password; verify the '
    'sixth returns 423\n'
    '- PROOF-4 (RULE-4): GET /; verify the reply arrives within 1000 ms\n'
    '- PROOF-5 (RULE-5): POST /login to a locked account; verify 423\n'
)

ONE_PASSED_SPEC = (
    '# Feature: notes\n\n'
    '> Description: A spec whose one rule asks for its tests alone.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A note keeps its text [level: passed]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Save the note "hi"; verify it reads "hi"\n'
)


def _levels_project(gate='signed'):
    """A `signed` project with a rule at each level, three audited strong."""
    made = Project(spec=LEVELS_SPEC, gate=gate)
    made.evidence([_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2'),
                   _entry('PROOF-3', 'RULE-3'),
                   _entry('PROOF-4', 'RULE-4', status='fail'),
                   _entry('PROOF-5', 'RULE-5', status='fail')])
    for rule_id in ('RULE-1', 'RULE-2', 'RULE-3'):
        made.audit(rule_id)
    return made


class TestALevelAsksItsOwnQuestions:

    # purlin: states PROOF-89
    def test_a_rule_has_only_the_cells_its_level_asks_for(self):
        made = _levels_project()
        try:
            rules = {n: made.rule('RULE-%d' % n) for n in (1, 2, 3)}
            assert [rules[n]['level'] for n in (1, 2, 3)] == [
                'passed', 'strong', 'signed']
            assert list(rules[1]['cells']) == ['passed'], rules[1]
            assert sorted(rules[2]['cells']) == ['passed', 'strong'], rules[2]
            assert sorted(rules[3]['cells']) == [
                'passed', 'signed', 'strong'], rules[3]
            for rule in rules.values():
                assert None not in rule['cells'].values(), rule
                assert rule['cells']['passed']['word'] == 'passed', rule
            assert rules[2]['cells']['strong']['word'] == 'strong', rules[2]
            assert rules[3]['cells']['signed']['word'] == 'unsigned', rules[3]
            assert [rules[n]['bucket'] for n in (1, 2, 3)] == [
                'passed', 'strong', 'strong']
            assert [rules[n]['meets_gate'] for n in (1, 2, 3)] == [
                True, True, False]
        finally:
            made.close()

    # purlin: states PROOF-90
    def test_the_rollup_counts_the_rules_each_question_is_asked_of(self):
        made = _levels_project()
        try:
            data = made.payload()
            rollup = data['features'][0]['rollup']
            for counted in (rollup, data['summary']):
                assert (counted['asks_strong'], counted['asks_signed']) == (
                    3, 1), counted
                assert (counted['strong'], counted['signed']) == (2, 0), counted
                assert counted['not_audited'] == 0, counted
            made.config_value('gate', 'strong')
            rollup = made.payload()['features'][0]['rollup']
            assert rollup['asks_strong'] == 3, rollup
            assert 'asks_signed' not in rollup, rollup
        finally:
            made.close()

    # purlin: states PROOF-91
    def test_the_table_counts_strong_and_signed_over_the_rules_asked(self):
        made = _levels_project()
        try:
            data = made.payload()
            row = purlin_status._row(data['features'][0], 'signed')
            assert row[-2:] == ('2 of 3 · 90%', '0 of 1'), row
            lines = purlin_status.sync_status(made.root).splitlines()
            header = next(line for line in lines if line.startswith('Spec'))
            login = next(line for line in lines if line.startswith('login '))
            assert login[header.index('Strong'):].split('  ')[0] == (
                '2 of 3 · 90%'), (header, login)
            assert login[header.index('Signed'):] == '0 of 1', (header, login)
            made.spec(ONE_PASSED_SPEC, name='notes', category='notes')
            notes = next(f for f in made.payload()['features']
                         if f['name'] == 'notes')
            row = purlin_status._row(notes, 'signed')
            assert row[-2:] == ('', ''), row
        finally:
            made.close()

    # purlin: states PROOF-92
    def test_a_rule_whose_test_fails_reads_its_passed_cell(self):
        made = _levels_project()
        try:
            lower = made.rule('RULE-4')
            assert list(lower['cells']) == ['passed'], lower
            assert lower['cells']['passed']['word'] == 'failed', lower
            assert (lower['bucket'], lower['blocked_by']) == (
                'failing', 'passed'), lower
            middle = made.rule('RULE-5')
            assert middle['cells']['strong']['word'] == 'waiting', middle
            assert middle['cells']['strong']['reasons'] == [
                'waiting for its tests to pass'], middle
        finally:
            made.close()

    # purlin: states PROOF-93
    def test_a_signature_waits_for_the_audit(self):
        made = Project(gate='signed')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'fail'}], ci=True)
            rule = made.rule('RULE-1')
            assert rule['level'] == 'signed', rule
            assert rule['cells']['strong']['word'] == 'waiting', rule
            assert rule['cells']['signed']['word'] == 'waiting', rule
            assert rule['cells']['signed']['reasons'] == [
                'waiting for the audit'], rule
            assert made.payload()['queue'] == [], made.payload()['queue']

            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True)
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'not audited', rule
            assert rule['cells']['signed']['word'] == 'waiting', rule
            assert rule['cells']['signed']['reasons'] == [
                'waiting for the audit'], rule
            assert made.payload()['queue'] == [], made.payload()['queue']

            made.audit('RULE-1')
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert rule['cells']['signed']['word'] == 'unsigned', rule
            rows = [(row['rule'], row['need'])
                    for row in made.payload()['queue']]
            assert rows == [('RULE-1', 'signature')], rows

            # A hand check is signed with its note, so it waits on a person
            # and not on the audit.
            made.spec(SPEC.replace('and a token\n', 'and a token @manual\n'))
            rule = made.rule('RULE-1')
            assert rule['cells']['strong']['word'] == 'manual test', rule
            assert rule['cells']['signed']['word'] == 'unsigned', rule
            assert rule['cells']['signed']['reasons'] == [], rule
            rows = [(row['rule'], row['need'])
                    for row in made.payload()['queue']]
            assert rows == [('RULE-1', 'hand check')], rows
        finally:
            made.close()

    # purlin: states PROOF-94
    def test_a_stale_signature_reads_stale_while_the_tests_wait(self):
        made = Project(gate='signed')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True)
            made.audit('RULE-1')
            made.sign_commits()
            made.signature('RULE-1')
            assert made.cell('RULE-1', 'signed')['word'] == 'signed'
            made.spec(SPEC.replace('return 200 with a session token',
                                   'return 201 with a session token'))
            rule = made.rule('RULE-1')
            assert rule['cells']['passed']['word'] == 'out of date', rule
            assert rule['cells']['strong']['word'] == 'waiting', rule
            assert rule['cells']['signed']['word'] == 'stale', rule
            assert rule['cells']['signed']['reasons'] == [
                'hashes changed after the signature'], rule
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    # purlin: states PROOF-31
    def test_schema_nine_carries_the_documented_top_level(self, project):
        data = project.payload()
        assert data["schema_version"] == 9
        # Those keys and `schema_version`, and no other.
        assert sorted(data) == sorted((
            'schema_version', 'generated_at', 'generated_by', 'project',
            'version', 'commit', 'dirty', 'gate', 'summary', 'features',
            'queue', 'evidence', 'tag', 'remote_url', 'warnings')), sorted(data)
        assert data['gate']['gate'] == 'passed'
        assert data['generated_at'].endswith('Z')
        # A project with no remote gets null rather than a broken link.
        assert data['remote_url'] is None
        _git(project.root, 'remote', 'add', 'origin',
             'https://github.com/acme/ledger.git')
        assert project.payload()['remote_url'] == (
            'https://github.com/acme/ledger.git')

    # purlin: states PROOF-32
    def test_a_feature_carries_its_rules_with_their_tags_and_proofs(self,
                                                                   project):
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['spec_path'] == 'specs/auth/login.md'
        assert feature['category'] == 'auth'
        assert feature['signatures'] == []
        rule = next(r for r in feature['rules'] if r['id'] == 'RULE-1')
        # The gate is `passed`, so a rule marked `signed` is read as `passed`.
        assert (rule['level'], rule['level_marked']) == ('passed', 'signed')
        assert project.rule('RULE-2')['level_marked'] is None
        assert 'origin' not in rule and 'criterion' not in rule
        assert rule['proofs'][0]['manual'] is False
        assert rule['proofs'][0]['env'] is None
        assert 'findings' not in rule['proofs'][0], rule['proofs'][0]
        assert feature['current'] is False
        assert feature['evidence'] == {'local': None, 'ci': None}
        # The audit hash a signature binds: 64 hexadecimal characters, which
        # move once the audit finds something in the rule.
        before = rule['audit_hash']
        assert len(before) == 64 and set(before) <= set('0123456789abcdef')
        project.audit('RULE-1', observations=['PROOF-1 reads 200 alone.'])
        assert project.rule('RULE-1')['audit_hash'] != before

    # purlin: states PROOF-32
    def test_a_feature_says_whether_its_evidence_is_current_and_committed(
            self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False,
                         os_name='linux')
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['current'] is True
        local = feature['evidence']['local']
        assert local['path'] == '.purlin/evidence/local/login.json'
        assert local['committed'] is False
        assert local['platforms'] == {'linux': {
            'commit': project.head(), 'at': '2026-09-13T12:00:00Z',
            'current': True}}
        assert feature['evidence']['ci'] is None
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'purlin: evidence')
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['evidence']['local']['committed'] is True
        _write(os.path.join(project.root, 'src', 'login.py'), 'x = 1\n')
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
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
            'rules', 'met', 'untested', 'failing', 'partial', 'passed',
            'stale', 'manual', 'not_audited',
            'queue', 'hand_checks', 'test_strength', 'proofs',
            'proofs_without_test', 'proofs_without_test_ids',
            'incomplete']), rollup
        assert (rollup['rules'], rollup['met']) == (2, 1)
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

        # A marker below the last test is tied to none, so it backs nothing.
        _write(path, 'def test_x():\n    pass\n\n# purlin: login PROOF-1\n')
        rollup = next(f for f in project.payload()['features']
                      if f['name'] == 'login')['rollup']
        assert rollup['proofs_without_test'] == 2, rollup

    # purlin: states PROOF-56
    def test_the_signed_cell_carries_when_it_was_signed(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.signature('RULE-2', machine='jane-laptop', os='macos')
            cell = made.cell('RULE-2', 'signed')
            assert cell['signer'] == 'jane@acme.com'
            assert cell['at'] and cell['at'].endswith('Z'), cell
            assert len(cell['at']) == 20, cell
            assert (cell['machine'], cell['os']) == ('jane-laptop', 'macos')
            # `at` is when the commit that added the signature was made, in
            # UTC, not the `2026-09-13T12:00:00Z` the file itself logs.
            added = _git(made.root, 'log', '-1', '--format=%at').stdout.strip()
            assert cell['at'] == datetime.datetime.fromtimestamp(
                int(added), datetime.timezone.utc).strftime(
                    '%Y-%m-%dT%H:%M:%SZ'), (cell, added)
            assert cell['at'] != '2026-09-13T12:00:00Z', cell
            made.signature('RULE-1')
            other = made.cell('RULE-1', 'signed')
            assert (other['machine'], other['os']) == (None, None), other
            # A signature no commit carries yet falls back to the file's own.
            made.spec(SPEC.replace('return 401 and', 'return 403 and'))
            made.signature('RULE-2', commit_it=False)
            loose = made.cell('RULE-2', 'signed')
            assert loose['signer'] == 'jane@acme.com', loose
            assert loose['at'] == '2026-09-13T12:00:00Z', loose
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
            '.features[].rules[].cells', '.features[].rules[].cells.*.platforms')

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
        sources, audit entries, a hand check in the queue, a signature and
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

    # purlin: states PROOF-31
    # purlin: states PROOF-29
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

    # purlin: states PROOF-68
    def test_the_tag_key_is_present_in_every_fixture(self):
        """The board's chip reads this key, so a fixture without it is a lie."""
        for name in ('solo', 'team'):
            assert self._fixture(name)['tag'] is None, name
        tag = self._fixture('regulated')['tag']
        assert sorted(tag) == ['commit', 'name']
        assert tag['name'].startswith('signed/')
        assert tag['commit'] == self._fixture('regulated')['commit']

    # purlin: states PROOF-34
    def test_every_fixture_queue_row_uses_the_closed_set(self):
        words = {'hand check': {'manual test'},
                 'signature': {'unsigned', 'stale'}}
        keys = ['command', 'feature', 'level', 'need', 'owner', 'reasons',
                'rule', 'text', 'word']
        for name in ('solo', 'team', 'regulated'):
            fixture = self._fixture(name)
            for row in fixture['queue']:
                assert sorted(row) == keys, row
                assert row['word'] in words[row['need']], row
                assert row['command'].startswith(
                    'purlin:sign %s %s' % (row['owner'], row['rule'])), row
            assert fixture['summary']['queue'] == len(fixture['queue']), name


class TestProofResult:

    @staticmethod
    def _proofs(project):
        rules = next(f for f in project.payload()['features']
                     if f['name'] == 'login')['rules']
        return {proof['id']: proof for rule in rules for proof in rule['proofs']}

    # purlin: states PROOF-85
    def test_each_proof_carries_its_own_result_and_its_tests(self, project):
        _commit_tests(project, 'PROOF-1')
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'not run', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == []
        assert proofs['PROOF-2']['result'] == 'no test', proofs['PROOF-2']

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

        project.spec(SPEC.replace('body "denied"\n', 'body "denied" @manual\n'))
        proofs = self._proofs(project)
        assert proofs['PROOF-2']['result'] == 'hand check'
        # The spec moved, so no current section lists PROOF-1's test.
        assert proofs['PROOF-1']['tests'] == [
            {'file': 'tests/test_login.py', 'name': 'test_proof_1',
             'result': 'not run'}], proofs['PROOF-1']['tests']

        # A proof tagged for Linux reads Linux's sections alone.
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

class TestStatusTable:

    # purlin: states PROOF-58
    def test_the_table_and_the_board_render_the_same_cells(self):
        """One module renders both, so a cell cannot read two ways."""
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixture = TestTheFixturesAreTheContract._fixture(name)
            columns = purlin_status.columns_for(gate)
            assert columns == purlin_board.columns_for(gate), name
            for feature in fixture['features']:
                row = purlin_status._row(feature, gate)
                board = purlin_board.row_cells(
                    feature['name'], feature['rollup'], gate,
                    shared=purlin_board.shared_counts(feature['rules']))
                assert row[1:] == board[1:], (name, feature['name'], row)
                assert len(row) == len(columns), (name, row)

    # purlin: states PROOF-58
    def test_the_board_cells_read_the_way_the_fixtures_say(self):
        fixture = TestTheFixturesAreTheContract._fixture('regulated')
        cells = {f['name']: purlin_board.row_cells(
            f['name'], f['rollup'], 'signed') for f in fixture['features']}
        # login's RULE-3 and invoice's RULE-1 are marked `[level: passed]`,
        # so neither is asked the audit's question or a signature's.
        assert cells['login'] == ('login', '4', '5', '3 of 4 · 1 partial',
                                  '2 of 3 · 86%', '1 of 3'), cells['login']
        assert cells['invoice'] == ('invoice', '3', '3', '3 of 3',
                                    '0 of 2 · 64%', '0 of 2'), cells['invoice']
        team = TestTheFixturesAreTheContract._fixture('team')
        rows = {f['name']: purlin_board.row_cells(
            f['name'], f['rollup'], 'strong') for f in team['features']}
        assert rows['invoice'] == ('invoice', '2', '2 · 1 no test',
                                   '1 of 2', '0 of 2 · 48%'), rows['invoice']

    # purlin: states PROOF-86
    def test_the_rules_cell_names_the_shared_rules(self, project):
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        lines = purlin_status.sync_status(project.root).splitlines()
        header = next(line for line in lines if line.startswith('Spec'))
        login = next(line for line in lines if line.startswith('login '))
        anchor = next(line for line in lines if line.startswith('security '))
        column = header.index('Rules')
        assert login[column:].startswith('2 (+1 shared)'), (header,
                                                                     login)
        assert anchor[column:].split('  ')[0] == '1', (header, anchor)

        os.remove(os.path.join(project.root, 'specs', '_anchors',
                               'security.md'))
        lines = purlin_status.sync_status(project.root).splitlines()
        header = next(line for line in lines if line.startswith('Spec'))
        login = next(line for line in lines if line.startswith('login '))
        assert login[header.index('Rules'):].split('  ')[0] == '2', login
        assert not [line for line in lines if 'shared' in line], lines

        # An anchor the spec requires, not a global one, is shared too.
        project.spec(
            '# Anchor: api\n\n## Rules\n\n- RULE-1: Responses carry a type\n'
            '\n## Proof\n\n- PROOF-1 (RULE-1): GET /x; verify the header\n',
            name='api', category='_anchors')
        project.spec(SPEC.replace('# Feature: login\n',
                                  '# Feature: login\n\n> Requires: api\n'))
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
        lines = purlin_status.sync_status(project.root).splitlines()
        header = next(line for line in lines if line.startswith('Spec'))
        login = next(line for line in lines if line.startswith('login '))
        assert login[header.index('Rules'):].split('  ')[0] == (
            '2 (+1 shared)'), (header, login)
        # Every cell of every row starts at its heading's left edge.
        top = lines.index(header) + 1
        rows = lines[top + 1:lines.index(lines[top], top + 1)]
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

    # purlin: states PROOF-43
    def test_the_columns_scale_with_the_gate(self, project):
        _commit_tests(project, 'PROOF-2')
        project.evidence([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        header = next(line for line in text.splitlines()
                      if line.startswith('Spec'))
        for column in ('Spec', 'Rules', 'Proofs', 'Tests'):
            assert column in header, (column, header)
        assert 'Strong' not in header and 'Signed' not in header, header
        row = next(line for line in text.splitlines()
                   if line.startswith('login '))
        assert '1 of 2' in row, row
        assert '2 · 1 no test' in row, row
        # `Tests` appends the failing count, and then the partial one: the
        # rule fails here and passes on another operating system.
        other = 'windows' if purlin_evidence.host_os() != 'windows' else 'linux'
        for os_name, cell in ((None, '1 of 2 · 1 failing'),
                              (other, '1 of 2 · 1 partial')):
            project.evidence([_entry('PROOF-1', 'RULE-1',
                                     'pass' if os_name else 'fail'),
                              _entry('PROOF-2', 'RULE-2')], os_name=os_name,
                             at='2026-09-13T13:00:00Z' if os_name else
                             '2026-09-13T12:00:00Z')
            row = next(line for line in
                       purlin_status.sync_status(project.root).splitlines()
                       if line.startswith('login '))
            assert row.split('  ')[-1].strip() == cell, row

        for gate, expected in (('strong', ('Strong',)),
                               ('signed', ('Strong', 'Signed'))):
            made = Project(gate=gate)
            try:
                text = purlin_status.sync_status(made.root)
                header = next(line for line in text.splitlines()
                              if line.startswith('Spec'))
                for column in expected:
                    assert column in header, (gate, header)
                row = next(line for line in text.splitlines()
                           if line.startswith('login '))
                assert 'n/a' in row, 'no audit, so no test strength'
            finally:
                made.close()

    # purlin: states PROOF-44
    def test_the_summary_counts_the_rules_that_meet_the_gate(self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        line = next(line for line in text.splitlines()
                    if 'meet the gate' in line)
        assert line == '1 of 2 rules meet the gate passed.', line
        second = text.splitlines()[text.splitlines().index(line) + 1]
        assert 'test strength' not in second, second
        assert 'signature' not in second, second
        # Then the buckets the gate reaches, in the tiles' words and order.
        assert second == 'Untested 1 · Failing 0 · Partial 0 · Passing 1.', \
            second
        made = Project(gate='signed')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')])
            lines = purlin_status.sync_status(made.root).splitlines()
            buckets = lines[lines.index('0 of 2 rules meet the gate signed.')
                            + 1]
            assert buckets == ('Untested 0 · Failing 0 · Partial 0 · '
                               'Passing 2 · Strong 0 · Signed 0.'), buckets
            counts = next(line for line in lines
                          if line.startswith('1 feature'))
            # Counts only: a requirement is not a count.
            assert counts == ('1 feature, 2 proof lines · 2 no test, minimum '
                              'test strength 80%, 2 rules not audited.'), \
                counts
            assert 'every rule' not in counts, counts
        finally:
            made.close()

    # purlin: states PROOF-44
    def test_the_summary_counts_manual_tests_and_stale_signatures(self):
        manual = SPEC.replace('body "denied"\n', 'body "denied" @manual\n')
        made = Project(gate='signed', spec=manual)
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            made.signature('RULE-1')
            made.spec(manual.replace('return 200 with', 'return 201 with'))
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            lines = purlin_status.sync_status(made.root).splitlines()
            counts = next(line for line in lines
                          if line.startswith('1 feature'))
            assert counts == ('1 feature, 2 proof lines · 1 no test, minimum '
                              'test strength 80%, 1 rule with a manual test, '
                              '1 rule not audited, 1 signature stale.'), \
                counts
        finally:
            made.close()

    # purlin: states PROOF-43
    # purlin: states PROOF-81
    def test_a_passed_project_with_no_proof_line_is_shown_no_proof_count(
            self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            header = next(line for line in lines if line.startswith('Spec'))
            assert header.split() == ['Spec', 'Rules', 'Tests'], header
            summary = lines[lines.index('0 of 1 rules meet the gate passed.')
                            + 2]
            assert summary == '1 feature.', summary
            assert not [line for line in lines if 'proof' in line], lines
            assert lines[-1] == '→ Next: run purlin:build. 1 rule has no test.'
        finally:
            made.close()
        made = Project(spec=NO_PROOF_SPEC.replace(
            'token\n', 'token\n- RULE-2: A bad password returns 401\n'))
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            assert not [line for line in lines if 'proof' in line], lines
            assert lines[-1] == ('→ Next: run purlin:build. 2 rules have no '
                                 'test.'), lines
        finally:
            made.close()

    # purlin: states PROOF-79
    def test_rules_out_of_date_are_counted_and_sent_to_the_tests(self):
        moved = {'spec': 's', 'code': 'moved on', 'tests': 't'}
        for spec, count, said in (
                (SPEC, '2 rules out of date', '2 rules are out of date.'),
                (ONE_RULE_SPEC, '1 rule out of date', '1 rule is out of date.')):
            made = Project(spec=spec)
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}], fingerprint=moved)
                lines = purlin_status.sync_status(made.root).splitlines()
                summary = next(line for line in lines
                               if line.startswith(('1 feature', '2 feature')))
                assert summary.rstrip('.').split(', ')[-1] == count, summary
                step = [line for line in lines if line.startswith('→ Next:')]
                assert step == ['→ Next: run purlin:test. ' + said], step
            finally:
                made.close()
        made = Project()
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}])
            text = purlin_status.sync_status(made.root)
            assert 'out of date' not in text, text
        finally:
            made.close()

    # purlin: states PROOF-80
    def test_a_count_of_one_rule_reads_singular(self):
        for spec, said in (
                (ONE_RULE_SPEC, '→ Next: run purlin:build. 1 rule has a '
                                'failing test.'),
                (SPEC, '→ Next: run purlin:build. 2 rules have a failing '
                       'test.')):
            made = Project(spec=spec)
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'fail'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'fail'}])
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert step == [said], step
            finally:
                made.close()

    # purlin: states PROOF-45
    def test_the_table_ends_with_one_next_step(self, project, tmp_path):
        text = purlin_status.sync_status(project.root)
        directives = [line for line in text.splitlines()
                      if line.startswith('→ Next:')]
        assert len(directives) == 1, text
        assert 'purlin:build' in directives[0], directives[0]
        # The same project reports the same step however it is asked for:
        # through the server from its own root, and with the root named from
        # another directory.
        for cwd, arguments in ((project.root, {}),
                               (str(tmp_path),
                                {'project_root': project.root})):
            responses, _stderr = _rpc(cwd, {
                'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'sync_status', 'arguments': arguments}})
            answer = responses[0]['result']['content'][0]['text']
            assert [line for line in answer.splitlines()
                    if line.startswith('→ Next:')] == directives, answer

    # purlin: states PROOF-45
    def test_the_step_follows_the_lowest_cell_that_blocks(self):
        # At the gate `strong`, RULE-1 has no test and is blocked by
        # `passed`; RULE-2 passes, no audit has read it, and it is blocked by
        # `strong`. The step is the lower cell's.
        made = Project(gate='strong')
        try:
            made.evidence([_entry('PROOF-2', 'RULE-2')])
            blocked = {rule: made.rule(rule)['blocked_by']
                       for rule in ('RULE-1', 'RULE-2')}
            assert blocked == {'RULE-1': 'passed', 'RULE-2': 'strong'}, blocked
            step = [line for line in
                    purlin_status.sync_status(made.root).splitlines()
                    if line.startswith('→ Next:')]
            assert step == ['→ Next: run purlin:build. 1 rule has a proof and '
                            'no passing test.'], step
        finally:
            made.close()

    # purlin: states PROOF-69
    def test_a_rule_marked_above_the_gate_is_named_once(self):
        made = Project(gate='strong')
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('1 rule is marked above the gate and is read as strong.'
                    in lines), lines
            made.spec(SPEC.replace('"denied"\n\n', '"denied" [level: signed]'
                                   '\n\n', 1))
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('2 rules are marked above the gate and are read as '
                    'strong.' in lines), lines
            made.config_value('gate', 'signed')
            text = purlin_status.sync_status(made.root)
            assert 'marked above the gate' not in text, text
        finally:
            made.close()

    # purlin: states PROOF-67
    def test_a_rule_waiting_on_a_run_is_sent_to_the_tests(self):
        """A rule whose run is out of date waits on a test run, at every gate.

        The audit is never the step while a test run is: only `trust: remote`
        sends the run to the runner.
        """
        for gate, trust, said in (
                ('passed', 'local',
                 '→ Next: run purlin:test. 2 rules are out of date.'),
                ('strong', 'local',
                 '→ Next: run purlin:test. 2 rules are out of date.'),
                ('signed', 'local',
                 '→ Next: run purlin:test. 2 rules are out of date.'),
                ('signed', 'remote',
                 '→ Next: run purlin:test --remote. 2 rules have no current '
                 'run.')):
            made = Project(gate=gate, extra_config={'trust': trust})
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}],
                              source='ci',
                              fingerprint={'spec': 's', 'code': 'moved on',
                                           'tests': 't'})
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert step == [said], (gate, trust, step)
            finally:
                made.close()
        assert purlin_board.needs_a_person(1) == '1 rule needs a person'
        assert purlin_board.needs_a_person(3) == '3 rules need a person'
        assert purlin_board.needs_a_person(0) == 'no rule needs a person'
        # The report's `Queue:` line reads that sentence, for one rule.
        made = Project(spec=ONE_RULE_SPEC, gate='signed')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}])
            made.audit('RULE-1')
            assert [row['rule'] for row in made.payload()['queue']] == [
                'RULE-1']
            lines = purlin_status.sync_status(made.root).splitlines()
            assert [line for line in lines if line.startswith('→ Queue:')] == [
                '→ Queue: 1 rule needs a person. Run purlin:sign.'], lines
        finally:
            made.close()

    # purlin: states PROOF-87
    def test_a_rule_tagged_for_another_system_is_sent_to_the_runner(self):
        here = purlin_evidence.host_os()
        other = 'windows' if here == 'linux' else 'linux'
        for tag, said in (
                (other, '→ Next: run purlin:test --remote. 2 rules need %s, '
                        'which this machine is not.' % other),
                (here, '→ Next: run purlin:test. 2 rules have no run to '
                       'read.')):
            made = Project(spec=SPEC.replace('token\n', 'token @env(%s)\n'
                                             % tag).replace(
                'denied"\n', 'denied" @env(%s)\n' % tag))
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}],
                              os_name='macos' if here != 'macos'
                              else 'windows')
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert step == [said], (tag, step)
            finally:
                made.close()

    # purlin: states PROOF-88
    def test_the_audit_is_the_step_only_when_no_rule_waits_on_a_run(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}])
            step = [line for line in
                    purlin_status.sync_status(made.root).splitlines()
                    if line.startswith('→ Next:')]
            assert step == ['→ Next: run purlin:audit. 2 rules are not '
                            'audited.'], step
            made.audit('RULE-2', observations=['PROOF-2 reads the code '
                                               'alone.'])
            made.audit('RULE-1')
            step = [line for line in
                    purlin_status.sync_status(made.root).splitlines()
                    if line.startswith('→ Next:')]
            assert step == ['→ Next: run purlin:build. 1 rule is weak.'], step
        finally:
            made.close()

    # purlin: states PROOF-48
    def test_retired_config_keys_print_the_update_directive(self):
        made = Project(extra_config={'spec_dir': 'elsewhere'})
        try:
            text = purlin_status.sync_status(made.root)
            assert '→ Run: purlin:init --update' in text, text
            lines = text.splitlines()
            step = next(i for i, line in enumerate(lines)
                        if line.startswith('→ Next:'))
            assert lines[step - 1] == '→ Run: purlin:init --update', lines
        finally:
            made.close()
        # A project `purlin:init --update` has brought up to date prints no
        # such line until a retired key is written back into its settings.
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'init'))
        import update as purlin_update
        made = Project()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert purlin_update.main(['--yes', '--project-root',
                                           made.root]) == 0
            text = purlin_status.sync_status(made.root)
            assert 'purlin:init --update' not in text, text
            made.config_value('spec_dir', 'elsewhere')
            lines = purlin_status.sync_status(made.root).splitlines()
            assert lines[-2:-1] == ['→ Run: purlin:init --update'], lines
            assert lines[-1].startswith('→ Next:'), lines
        finally:
            made.close()

    # purlin: states PROOF-46
    def test_an_empty_project_says_what_to_run(self):
        made = Project(spec=None)
        try:
            text = purlin_status.sync_status(made.root)
            assert 'No specs found' in text and 'purlin:init' in text
        finally:
            made.close()

    # purlin: states PROOF-47
    def test_no_emoji_and_only_the_four_glyphs(self, project):
        text = purlin_status.sync_status(project.root)
        allowed = set('→▶▼─')
        for char in text:
            assert ord(char) < 0x2000 or char in allowed, repr(char)
        # At `strong` and `signed` the Strong and Signed columns, the queue
        # count and the `Queue:` line print too, and hold to the same set.
        for gate in ('strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence(PASSING)
                made.audit('RULE-1')
                made.audit('RULE-2')
                text = purlin_status.sync_status(made.root)
                lines = text.splitlines()
                assert any(line.startswith('Queue: ') for line in lines), text
                if gate == 'signed':
                    assert ('→ Queue: 2 rules need a person. Run purlin:sign.'
                            in lines), text
                header = next(line for line in lines if line.startswith('Spec'))
                assert 'Strong' in header, header
                assert ('Signed' in header) is (gate == 'signed'), header
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
        assert text.rstrip().splitlines()[-1].startswith('→'), text
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
    def test_no_tag_reads_none_and_a_tag_on_head_reads_its_name(self):
        made = Project(gate='signed')
        try:
            assert made.payload()['tag'] is None
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            tag = made.payload()['tag']
            assert tag['name'] == 'signed/1.2.0', tag
            assert tag['commit'] == made.head(), tag
        finally:
            made.close()

    # purlin: states PROOF-68
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

    # purlin: states PROOF-68
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
                config = os.path.join(made.root, '.purlin', 'config.json')
                with open(config, encoding='utf-8') as handle:
                    settings = json.load(handle)
                settings['gate'] = 'signed'
                _write(config, json.dumps(settings))
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

    # purlin: states PROOF-74
    def test_the_payload_names_why_it_is_incomplete(self):
        for spec, reason in (
                (NO_SCOPE_SPEC, 'no > Scope: line'),
                (SPEC.replace('src/login.py', 'src/nowhere.py'),
                 '> Scope: names nothing that exists'),
                (SPEC, None)):
            made = Project(spec=spec)
            try:
                made.evidence(PASSING)
                data = made.payload()
                feature = _feature(data)
                assert feature['incomplete'] is (reason is not None), spec
                assert feature['incomplete_reason'] == reason, feature
                assert feature['rollup']['incomplete'] is (
                    reason is not None), feature['rollup']
                assert data['summary']['incomplete'] == (
                    1 if reason else 0), data['summary']
                # Its tests pass and it meets the gate `passed` all the same.
                assert [rule['cells']['passed']['word']
                        for rule in feature['rules']] == ['passed', 'passed']
                assert all(rule['meets_gate'] for rule in feature['rules'])
            finally:
                made.close()

    # purlin: states PROOF-74
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
    def test_at_signed_its_rules_read_unsigned_and_wait_on_nobody(self):
        for spec, word, queued in ((SPEC, 'unsigned', True),
                                   (NO_SCOPE_SPEC, 'unsigned', False)):
            made = Project(spec=spec, gate='signed')
            try:
                made.evidence(PASSING)
                made.audit('RULE-1')
                made.audit('RULE-2')
                data = made.payload()
                rule = next(r for r in _feature(data)['rules']
                            if r['id'] == 'RULE-2')
                cell = rule['cells']['signed']
                assert cell['word'] == word, cell
                assert rule['cells']['strong']['word'] == 'strong', rule
                assert rule['meets_gate'] is False
                assert rule['blocked_by'] == 'signed'
                assert bool(data['queue']) is queued, data['queue']
                if queued:
                    rows = sorted((row['rule'], row['need'])
                                  for row in data['queue'])
                    assert rows == [('RULE-1', 'signature'),
                                    ('RULE-2', 'signature')], rows
                if not queued:
                    assert cell['reasons'] == [
                        'the spec names no files in > Scope:, so a signature '
                        'cannot be tied to the code it governs'], cell
            finally:
                made.close()

    # purlin: states PROOF-75
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
            assert rule['meets_gate'] is False
        finally:
            made.close()

    # purlin: states PROOF-75
    def test_below_signed_it_blocks_nothing(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='strong')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            data = made.payload()
            assert _feature(data)['incomplete'] is True
            assert all(rule['meets_gate'] for rule in _feature(data)['rules'])
        finally:
            made.close()

    # purlin: states PROOF-76
    def test_status_names_it_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(spec=NO_SCOPE_SPEC, gate=gate)
            try:
                lines = purlin_status.sync_status(made.root).splitlines()
                assert ('1 spec names no files, so its tests run every time: '
                        'login.') in lines, (gate, lines)
            finally:
                made.close()
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
            made = Project(gate=gate)
            try:
                text = purlin_status.sync_status(made.root)
                assert ('names no files' not in text
                        and 'name no files' not in text), (gate, text)
            finally:
                made.close()

    # purlin: states PROOF-76
    def test_at_signed_with_nothing_else_left_the_next_step_is_the_spec(self):
        made = Project(spec=NO_SCOPE_SPEC.replace(' [level: signed]', ''),
                       gate='signed')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('→ Next: run purlin:spec login. It names no files in '
                    '> Scope:, so its rules cannot be signed.') in lines, lines
        finally:
            made.close()
