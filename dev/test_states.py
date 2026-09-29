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

from mcp_project import (NO_PROOF_SPEC, ONE_RULE_SPEC, PROJECT_ROOT,
                         Project, SPEC, _commit_tests, _entry, _git,
                         _marked_tests, _rpc, _write, project)
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import board as purlin_board
from purlin import evidence as purlin_evidence
from purlin import fingerprint as purlin_fingerprint
from purlin import gate as purlin_gate
from purlin import payload as purlin_payload
from purlin import signatures as purlin_signatures
from purlin import states as purlin_states
from purlin import status as purlin_status


def _listed(data, rule_id, feature='login', listed_under=None):
    """A rule's entry in a payload, as the feature it is listed under lists it."""
    under = next(f for f in data['features']
                 if f['name'] == (listed_under or feature))
    return next(r for r in under['rules']
                if r['id'] == rule_id and r['feature'] == feature)


def _sign(made, rule_id, feature='login', category='auth', listed_under=None,
          signer='jane@acme.com', commit_it=True, **fields):
    """Write one signature file over what the rule is now, as `purlin:sign` does.

    It is made for the feature the rule is listed under, over that
    feature's code and the machines its results came from, and names the
    hash of all of them, so it binds the rule until any of them moves.
    `fields` adds or overrides what the file records.
    """
    rule = _listed(made.payload(), rule_id, feature, listed_under)
    data = {
        'schema': 'purlin-signature/2', 'feature': feature, 'rule': rule_id,
        'applies_to': rule['applies_to'],
        'signed_hash': purlin_signatures.signed_hash(rule),
        'rule_hash': rule['rule_hash'], 'proof_hash': rule['proof_hash'],
        'test_hash': rule['test_hash'], 'code_hash': rule['code_hash'],
        'audit_hash': rule['audit_hash'], 'machines': rule['machines'],
        'test_hash_kind': rule['test_hash_kind'], 'signer': signer,
        'key_fingerprint': None, 'timestamp': '2026-09-13T12:00:00Z',
    }
    data.update(fields)
    name = '%s.%s.%s.json' % (rule_id, data['signed_hash'][:8],
                              purlin_signatures.signer_slug(signer))
    path = os.path.join(made.root, 'specs', category,
                        feature + '.signatures', name)
    _write(path, json.dumps(data))
    if commit_it:
        _git(made.root, 'add', '-A')
        _git(made.root, 'commit', '-q', '-m', 'sign(%s): %s' % (feature,
                                                               rule_id))
    return path


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
    # purlin: states PROOF-139
    def test_above_passed_a_rule_with_a_test_and_no_proof_reads_no_proof(
            self):
        for gate in ('strong', 'signed'):
            project = Project(spec=NO_PROOF_SPEC, gate=gate)
            try:
                project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                                   'status': 'pass'}], commit_it=False)
                rule = project.rule('RULE-1')
                assert rule['cells']['passed']['word'] == 'passed'
                assert rule['cells']['strong']['word'] == 'no proof', gate
                assert rule['cells']['strong']['reasons'] == [
                    'the rule has a test and no proof']
                assert rule['left'] == 'no_proof', (gate, rule['left'])
            finally:
                project.close()

    # purlin: states PROOF-140
    def test_at_passed_a_rule_with_a_test_and_no_proof_waits_for_nothing(
            self):
        project = Project(spec=NO_PROOF_SPEC, gate='passed')
        try:
            project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                               'status': 'pass'}], commit_it=False)
            rule = project.rule('RULE-1')
            assert sorted(rule['cells']) == ['passed'], rule
            assert rule['cells']['passed']['word'] == 'passed', rule
            assert rule['left'] is None, rule
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
    # purlin: states PROOF-117
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
        assert rule['left'] == 'to_test', rule['left']
        # The next run clears it.
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}])
        rule = project.rule('RULE-1')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['flags']['out_of_date'] is False, rule

    # purlin: states PROOF-118
    # purlin: states PROOF-119
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
    # purlin: states PROOF-120
    # purlin: states PROOF-121
    def test_the_audit_entry_settles_the_strong_cell(self):
        assert _strong()['word'] == 'not audited'
        assert _strong()['reasons'] == ['no audit has run on this code']
        open_question = _strong(audit=_audit('undecided', [
            'The test body is not shown, so PROOF-1 cannot be read.']))
        assert open_question['word'] == 'weak', open_question
        assert open_question['reasons'] == [
            'the AI audit could not decide: The test body is not shown, so '
            'PROOF-1 cannot be read.'], open_question
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
    # purlin: states PROOF-123
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
    def test_a_new_strength_ends_the_signature_and_says_nothing(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.evidence(PASSING, ci=True, strength=90)
            made.audit('RULE-1')
            _sign(made, 'RULE-1')
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

    # purlin: states PROOF-73
    # purlin: states PROOF-106
    # purlin: states PROOF-107
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
            _sign(made, 'RULE-1')
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
            _sign(made, 'RULE-1')
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
            _sign(made, 'RULE-1')
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
    _sign(made, 'RULE-5', feature='ledger', category='core')
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


class TestEveryRuleIsAskedWhatTheGateAsks:

    @staticmethod
    def _audited(gate):
        """Two rules whose tests pass and whose audit found nothing."""
        made = Project(gate=gate)
        made.evidence(PASSING, strength=90)
        made.audit('RULE-1')
        made.audit('RULE-2')
        return made

    # purlin: states PROOF-90
    def test_the_rollup_counts_the_rules_carrying_each_cell(self):
        made = self._audited('signed')
        try:
            data = made.payload()
            for counted in (_feature(data)['rollup'], data['summary']):
                assert (counted['asks_strong'], counted['asks_signed']) == (
                    2, 2), counted
        finally:
            made.close()

    # purlin: states PROOF-141
    def test_at_strong_the_rollup_asks_no_signature(self):
        made = self._audited('strong')
        try:
            rollup = _feature(made.payload())['rollup']
            assert rollup['asks_strong'] == 2, rollup
            assert 'asks_signed' not in rollup, rollup
        finally:
            made.close()

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
        row = purlin_board.row_cells('login', rollup, 'signed')
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
            _sign(made, 'RULE-1')
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
            'queue', 'left', 'finished', 'last_line', 'os_words', 'evidence',
            'tag', 'remote_url', 'warnings')), sorted(data)
        assert data['gate']['gate'] == 'passed'
        assert data['generated_at'].endswith('Z')

    # purlin: states PROOF-95
    def test_the_remote_url_is_the_origin_or_null(self, project):
        # A project with no remote gets null rather than a broken link.
        assert project.payload()['remote_url'] is None
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

    # purlin: states PROOF-128
    # purlin: states PROOF-129
    # purlin: states PROOF-130
    def test_a_feature_says_whether_its_evidence_is_current_and_committed(
            self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False,
                         os_name='linux')
        feature = _feature(project.payload())
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
        feature = _feature(project.payload())
        assert feature['evidence']['local']['committed'] is True
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
            _sign(made, 'RULE-2')
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
    # purlin: states PROOF-132
    def test_the_signed_cell_carries_the_name_and_the_key(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            _sign(made, 'RULE-2', signer_name='Jane Doe',
                  key_fingerprint='SHA256:q4Xy')
            cell = made.cell('RULE-2', 'signed')
            assert (cell['signer_name'], cell['key_fingerprint']) == (
                'Jane Doe', 'SHA256:q4Xy'), cell
            _sign(made, 'RULE-1')
            other = made.cell('RULE-1', 'signed')
            assert (other['signer_name'], other['key_fingerprint']) == (
                None, None), other
        finally:
            made.close()

    # purlin: states PROOF-133
    def test_a_signature_no_commit_carries_reads_the_files_own_time(self):
        made = Project(gate='signed')
        try:
            _sign(made, 'RULE-2', commit_it=False)
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
        project.evidence(PASSING, os_name='linux')
        for rule_id in ('RULE-1', 'RULE-2'):
            assert project.rule(rule_id)['machines'] == {}

    # purlin: states PROOF-114
    def test_a_hand_check_signed_with_a_note_is_checked(self):
        made = Project(gate='strong', spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'))
        try:
            made.sign_commits()
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            _sign(made, 'RULE-2', note='saw 110.00')
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
            _sign(made, 'RULE-2')
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
            _sign(made, 'RULE-2')
            assert made.rule('RULE-2')['hand_checked'] is False
        finally:
            made.close()

    # purlin: states PROOF-146
    # purlin: states PROOF-147
    def test_at_passed_a_hand_check_is_the_rules_passing(self):
        made = Project(gate='passed', spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'))
        try:
            made.sign_commits()
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            data = made.payload()
            assert _listed(data, 'RULE-2')['left'] == 'to_test_by_hand'
            assert data['summary']['sentence'] == (
                '2 rules. 1 passes its tests.'), data['summary']
            _sign(made, 'RULE-2')
            data = made.payload()
            assert _listed(data, 'RULE-2')['left'] is None
            assert data['summary']['sentence'] == (
                '2 rules. 2 pass their tests.'), data['summary']
        finally:
            made.close()

    # purlin: states PROOF-148
    # purlin: states PROOF-149
    def test_an_anchor_rule_is_signed_once_in_each_feature(self):
        made = Project(gate='signed')
        try:
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
            _sign(made, 'RULE-1', feature='security', category='_anchors',
                  listed_under='login')
            data = made.payload()

            def word(under):
                return _listed(data, 'RULE-1', 'security', under)['cells'][
                    'signed']['word']
            assert (word('login'), word('billing'), word('security')) == (
                'signed', 'unsigned', 'unsigned')
            _sign(made, 'RULE-1', feature='security', category='_anchors',
                  listed_under='billing')
            data = made.payload()
            assert word('security') == 'signed'
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

    # purlin: states PROOF-96
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
    # purlin: states PROOF-100
    # purlin: states PROOF-101
    # purlin: states PROOF-103
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

    # purlin: states PROOF-102
    def test_a_passed_project_with_no_proof_line_is_shown_no_proof_count(
            self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            header = next(line for line in lines if line.startswith('Spec'))
            assert header.split() == ['Spec', 'Rules', 'Tests'], header
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

    # purlin: states PROOF-104
    # purlin: states PROOF-105
    def test_an_updated_project_prints_it_only_once_a_key_returns(self):
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
            sentence = made.payload()['summary']['sentence']
            assert lines[lines.index(sentence) - 1] == (
                '→ Run: purlin:init --update'), lines
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
        # At `strong` and `signed` the Strong and Signed columns and the
        # lines of `Left to do` print too, and hold to the same set.
        for gate in ('strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence(PASSING)
                made.audit('RULE-1')
                made.audit('RULE-2')
                text = purlin_status.sync_status(made.root)
                lines = text.splitlines()
                if gate == 'signed':
                    assert '  2 rules to sign: purlin:sign' in lines, text
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
    # purlin: states PROOF-134
    # purlin: states PROOF-135
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
                # Its tests pass all the same.
                assert [rule['cells']['passed']['word']
                        for rule in feature['rules']] == ['passed', 'passed']
            finally:
                made.close()

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
            _sign(made, 'RULE-2')
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
    # purlin: states PROOF-109
    # purlin: states PROOF-110
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

    # purlin: summary PROOF-26
    def test_at_signed_its_rules_are_left_to_tie_to_their_files(self):
        made = Project(spec=NO_SCOPE_SPEC.replace(' [level: signed]', ''),
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
