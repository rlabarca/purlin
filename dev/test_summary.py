"""Tests for the status's opening lines, its sentence, `Left to do` and its last line.

Most projects here are lists of payload rule entries, built by hand with the
cells a payload gives them, so a test names exactly the state it reads. The
ending is composed the way `payload.build_payload` composes it: the steps and
the sentence over the rules each feature owns, then `left` over every
feature, then the last line. The opening lines and the commit of results are
read from a throwaway git project, `dev/mcp_project.py`'s.
"""

import json
import os
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from purlin import PURLIN_VERSION  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import status as purlin_status  # noqa: E402
from purlin import summary  # noqa: E402
from mcp_project import (NO_PROOF_SPEC, ONE_RULE_SPEC, SPEC,  # noqa: E402
                         Project, _commit_tests, _entry, _git, _write,
                         spec_with_a_hand_check)
from sign_project import _Out, signing_key  # noqa: E402
# `sign_project` puts `scripts/review` on the path.
import sign as sign_module  # noqa: E402

HERE = 'macos'
TWO_PROOFS_SPEC = (
    '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200\n'
    '- PROOF-2 (RULE-1): POST /login with valid credentials; verify a '
    'token\n')
SECURITY_ANCHOR = (
    '# Anchor: security\n\n'
    '## Rules\n\n- RULE-1: No eval anywhere\n\n'
    '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n')
LAST_LINE = ('Every rule passes its tests on the committed evidence. To sign '
             'it: purlin:sign')
# The last line where `purlin:sign` would refuse the results as they stand:
# the run to make first, and why.
OPENS = 'Every rule passes its tests on the committed evidence. '
RUN_FIRST = (OPENS + 'Before a sign-off, run %s: a sign-off counts only '
             'results taken on this version of the code.')
RUN_CLEAN = (OPENS + 'Before a sign-off, run purlin:test --all --commit: a '
             'sign-off counts only results taken with nothing uncommitted.')
NOT_THIS_CODE = ('No sign-off: these results were not taken on this version '
                 'of the code')
OLD_FIRST = (OPENS + 'Before a sign-off, rewrite the 1 test that still '
             'carries a marker from Purlin 0.9.5: purlin:status names it.')
TAKEN_DIRTY = ('No sign-off: these results were taken while files were '
               'changed and not committed')
PASSING = [_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2')]


def rule(passed='passed', strong=None, proofs=1, manual=False,
         missing_env=(), feature='login'):
    """One payload rule entry with the cells named. The strong cell reads
    `waiting` while the passed cell is not met and `not audited` otherwise,
    unless named."""
    if strong is None:
        strong = 'not audited' if passed == 'passed' else 'waiting'
    cells = {'passed': {'word': passed, 'missing_env': list(missing_env)},
             'strong': {'word': strong, 'reasons': []}}
    return {'feature': feature, 'cells': cells,
            'proofs': [{'id': 'PROOF-%d' % (index + 1), 'manual': manual}
                       for index in range(proofs)]}


def feature(rules, name='login', broken=(), anchor=False):
    return {'name': name, 'rules': rules, 'broken': list(broken),
            'is_anchor': anchor}


def payload(features, here=HERE, corrections=0, signoff=None):
    """The part of a payload the ending reads, composed as the builder does."""
    own = [entry for item in features for entry in item['rules']]
    counted = {'rules': len(own), 'steps': summary.steps(own),
               'audit': summary.audit_counts(own)}
    counted['sentence'] = summary.sentence(
        counted, summary.anchors_audit(features))
    left = summary.left(features, here, corrections)
    return {'summary': counted, 'left': left,
            'last_line': summary.last_line(left, signoff)}


def ending(rules, here=HERE, corrections=0):
    """The ending's lines for one feature's rules."""
    return summary.ending(payload([feature(rules)], here,
                                  corrections)).splitlines()


def _status(made):
    return purlin_status.sync_status(made.root).splitlines()


# ---------------------------------------------------------------------------
# The opening lines
# ---------------------------------------------------------------------------

class TestTheOpeningLines:

    # purlin: summary PROOF-48
    def test_the_status_opens_on_the_project_named_by_pyproject_then_tests_met(
            self):
        made = Project()
        try:
            _write(os.path.join(made.root, 'pyproject.toml'),
                   '[project]\nname = "labconnect"\nversion = "0.1.0"\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'chore: name the project')
            made.evidence(PASSING)
            lines = _status(made)
        finally:
            made.close()
        assert lines[:2] == ['Purlin status: labconnect, plugin %s'
                             % PURLIN_VERSION, 'Tests: met'], lines

    # purlin: summary PROOF-53
    def test_one_failing_rule_makes_the_second_line_tests_not_met(self):
        made = Project(spec=ONE_RULE_SPEC)
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1', status='fail')])
            lines = _status(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: not met', lines

    # purlin: summary PROOF-50
    def test_a_commit_to_the_code_after_the_walk_reads_one_commit_since(self):
        made = Project()
        try:
            _commit_tests(made, 'PROOF-1', 'PROOF-2')
            made.evidence(PASSING)
            signing_key(made.root)
            out = _Out()
            assert sign_module.walk(
                made.root, '0.1.0', out=out,
                ask=lambda _kind, _key, _prompt: 'y') == 0, out.text()
            _write(os.path.join(made.root, 'src', 'age.py'),
                   'def age():\n    return 0\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'feat(age): the age')
            lines = _status(made)
        finally:
            made.close()
        assert lines[2] == 'Sign-off: signed 0.1.0, 1 commit since', lines


# ---------------------------------------------------------------------------
# The sentence
# ---------------------------------------------------------------------------

class TestTheSentence:

    # purlin: summary PROOF-5
    def test_one_rule_that_passes_reads_one_rule_one_passes_its_tests(self):
        assert ending([rule()])[0] == '1 rule. 1 passes its tests.'

    # purlin: summary PROOF-4
    def test_an_anchor_rule_beside_two_features_reads_three_rules(self):
        features = [
            feature([rule(feature='security')], name='security'),
            feature([rule()], name='login'),
            feature([rule(feature='export')], name='export'),
        ]
        made = payload(features)
        assert made['summary']['sentence'] == '3 rules. 3 pass their tests.'
        assert made['left'] == []

    # purlin: summary PROOF-43
    def test_fifty_rules_forty_two_strong_read_the_audits_share_84(self):
        rules = [rule(strong='strong')] * 42 + [rule(strong='weak')] * 8
        assert ending(rules)[0] == (
            '50 rules. 50 pass their tests. '
            'The audit found 42 of 50 rules strong (84%): 42 strong, 8 weak.')

    # purlin: summary PROOF-57
    def test_forty_rules_read_each_count_that_is_not_zero(self):
        rules = ([rule(strong='strong')] * 34 + [rule(strong='weak')] * 4
                 + [rule(strong='spot-checked')] * 2)
        assert ending(rules)[0] == (
            '40 rules. 40 pass their tests. The audit found 34 of 40 rules '
            'strong (85%): 34 strong, 4 weak, 2 spot-checked.')


    # purlin: summary PROOF-61
    def test_an_anchors_rules_are_left_out_of_the_share_and_kept_in_the_counts(
            self):
        features = [
            feature([rule(strong='strong')] * 2 + [rule(strong='weak')]),
            feature([rule(strong='spot-checked', feature='security')] * 8,
                    name='security', anchor=True),
        ]
        assert payload(features)['summary']['sentence'] == (
            '11 rules. 11 pass their tests. The audit found 2 of 3 rules '
            'strong (66%): 2 strong, 1 weak, 8 spot-checked.')

    # purlin: summary PROOF-62
    def test_a_project_reaches_100_per_cent_beside_a_spot_checked_anchor(self):
        made = Project(spec=ONE_RULE_SPEC)
        try:
            made.spec(SECURITY_ANCHOR, name='security', category='_anchors')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'anchor(security): create')
            _commit_tests(made, 'PROOF-1')
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            made.evidence([_entry('PROOF-1', 'RULE-1', feature='security',
                                  test_file='tests/test_security.py')],
                          feature='security')
            made.audit('RULE-1')
            made.audit('RULE-1', feature='security', word='spot-checked')
            sentence = made.payload()['summary']['sentence']
        finally:
            made.close()
        assert sentence == (
            '2 rules. 2 pass their tests. The audit found 1 of 1 rules '
            'strong (100%): 1 strong, 1 spot-checked.'), sentence

    # purlin: summary PROOF-63
    def test_an_audit_that_read_an_anchor_alone_lists_what_it_found(self):
        features = [
            feature([rule(strong='spot-checked', feature='security')] * 7
                    + [rule(strong='weak', feature='security')],
                    name='security', anchor=True),
        ]
        assert payload(features)['summary']['sentence'] == (
            '8 rules. 8 pass their tests. The audit found 1 weak, '
            '7 spot-checked.')


def _nine_tested_rules_and_a_hand_check(audited=False):
    """A project of 10 rules on committed evidence: 9 pass their tests, and
    the tenth's one proof is `@manual` and no sign-off has noted it. With
    `audited` the audit found each of the 9 strong."""
    made = Project(spec=spec_with_a_hand_check(10))
    tested = ['PROOF-%d' % number for number in range(1, 10)]
    _commit_tests(made, *tested)
    made.evidence([_entry(proof_id, proof_id.replace('PROOF', 'RULE'))
                   for proof_id in tested])
    if audited:
        for proof_id in tested:
            made.audit(proof_id.replace('PROOF', 'RULE'))
    return made


class TestAHandCheckInTheSentence:

    # purlin: summary PROOF-58
    def test_nine_passing_rules_and_a_hand_check_read_one_is_checked(self):
        made = _nine_tested_rules_and_a_hand_check()
        try:
            sentence = made.payload()['summary']['sentence']
        finally:
            made.close()
        assert sentence == ('10 rules. 9 pass their tests. '
                            '1 is checked at sign-off.'), sentence

    # purlin: summary PROOF-60
    def test_nine_strong_rules_and_a_hand_check_read_nine_of_nine_strong(self):
        made = _nine_tested_rules_and_a_hand_check(audited=True)
        try:
            sentence = made.payload()['summary']['sentence']
        finally:
            made.close()
        assert sentence == (
            '10 rules. 9 pass their tests. 1 is checked at sign-off. '
            'The audit found 9 of 9 rules strong (100%): 9 strong.'), sentence

    # purlin: summary PROOF-59
    def test_an_unchecked_hand_check_leaves_the_tests_met(self):
        made = _nine_tested_rules_and_a_hand_check()
        try:
            lines = _status(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert 'Left to do:' not in lines, lines
        assert lines[-1] == LAST_LINE, lines

# ---------------------------------------------------------------------------
# Left to do
# ---------------------------------------------------------------------------

# One rule of each kind of rule work, on macOS.
EACH_KIND = (
    ('no_proof', lambda: rule(proofs=0, strong='no proof')),
    ('to_fix', lambda: rule(passed='partial')),
    ('no_test', lambda: rule(passed='no test')),
    ('to_test', lambda: rule(passed='not run')),
    ('to_test_remote', lambda: rule(passed='not run',
                                    missing_env=['windows'])),
    ('to_strengthen', lambda: rule(strong='weak')),
)


class TestTheLines:

    # purlin: summary PROOF-8
    def test_two_rules_of_each_of_the_six_kinds_read_in_rule_23s_order(self):
        features = [feature([make(), make()], name=kind)
                    for kind, make in EACH_KIND]
        lines = summary.ending(payload(features)).splitlines()
        assert lines[1:] == [
            'Left to do:',
            '  2 rules to write a proof for: purlin:spec',
            '  2 rules to fix: purlin:build',
            '  2 rules to write a test for: purlin:build',
            '  2 rules to test: purlin:test',
            '  2 rules to test on Windows: run purlin:test on Windows',
            '  2 rules to strengthen: purlin:build',
        ]

    # purlin: summary PROOF-40
    def test_a_broken_spec_reads_one_spec_to_repair_before_one_rule_to_fix(
            self):
        twice = ['PROOF-2 is written twice in the spec']
        made = payload([feature([rule(passed='failed')] * 3, broken=twice),
                        feature([rule(passed='failed')], name='export')])
        lines = summary.ending(made).splitlines()
        assert lines[1:] == ['Left to do:',
                             '  1 spec to repair: purlin:spec',
                             '  1 rule to fix: purlin:build'], lines

    # purlin: summary PROOF-29
    def test_a_comment_naming_login_proof_9_on_committed_evidence(self):
        made = Project()
        try:
            _commit_tests(made, 'PROOF-1', 'PROOF-2', 'PROOF-9')
            made.evidence(PASSING)
            lines = _status(made)
        finally:
            made.close()
        assert lines[-2:] == ['Left to do:',
                              '  1 test comment to correct: purlin:build'], \
            lines

    # purlin: summary PROOF-52
    def test_two_features_with_results_not_committed_end_on_the_commit(self):
        made = Project(spec=ONE_RULE_SPEC)
        try:
            made.spec(ONE_RULE_SPEC.replace('login', 'export'), name='export')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'spec(export): one rule')
            for name in ('login', 'export'):
                made.evidence([_entry('PROOF-1', 'RULE-1', feature=name)],
                              feature=name, commit_it=False)
            lines = _status(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: not met', lines
        assert lines[-2:] == [
            'Left to do:',
            '  2 features whose results are not committed: '
            'purlin:test --commit'], lines


class TestOneKindPerRule:

    # purlin: summary PROOF-15
    def test_a_rule_with_no_proof_whose_test_fails_is_one_rule_to_fix(self):
        entry = rule(proofs=0, passed='failed')
        assert summary.rule_kind(entry, HERE) == 'to_fix'
        assert ending([entry])[1:] == [
            'Left to do:', '  1 rule to fix: purlin:build']

    # purlin: summary PROOF-23
    def test_a_rule_this_machine_can_run_part_of_is_to_test(self):
        entry = rule(passed='not run', missing_env=['macos', 'windows'])
        assert ending([entry], here='macos')[2:] == [
            '  1 rule to test: purlin:test']

    # purlin: summary PROOF-33
    def test_a_rule_waiting_only_on_windows_is_to_test_there(
            self, monkeypatch):
        monkeypatch.setattr(purlin_evidence, 'host_os', lambda: 'macos')
        made = Project(spec=TWO_PROOFS_SPEC.replace(
            'a token\n', 'a token @env(windows)\n'))
        try:
            _commit_tests(made, 'PROOF-1', 'PROOF-2')
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-1', status='not run')],
                          os_name='macos')
            lines = _status(made)
        finally:
            made.close()
        assert lines[-1] == ('  1 rule to test on Windows: '
                             'run purlin:test on Windows'), lines


# ---------------------------------------------------------------------------
# The kinds that do not block, and the last line
# ---------------------------------------------------------------------------

def slow_rule(result='not run', env=None, passed='not run'):
    """A rule whose one proof is tagged `@slow`, with the proof's own word."""
    made = rule(passed, missing_env=[env] if env else ())
    made['proofs'] = [{'id': 'PROOF-1', 'manual': False, 'slow': True,
                       'env': env, 'result': result}]
    return made


class TestSlowProofsToRun:

    # purlin: summary PROOF-55
    def test_one_slow_proof_not_run_is_the_one_line_and_stops_the_sign_off(
            self):
        made = payload([feature([slow_rule()])])
        lines = summary.ending(made).splitlines()
        assert lines[1:] == ['Left to do:',
                             '  1 slow proof to run: purlin:test --all'], lines
        assert not [line for line in lines if 'to test' in line], lines
        assert made['last_line'] is None
        assert 'purlin:sign' not in '\n'.join(lines)

    # purlin: summary PROOF-56
    def test_a_slow_proof_tagged_for_windows_is_to_test_on_windows(self):
        rules = [feature([slow_rule()], name='cart'),
                 feature([slow_rule()], name='checkout'),
                 feature([slow_rule(env='windows')], name='locks')]
        lines = summary.ending(payload(rules, here='macos')).splitlines()
        assert lines[2:] == [
            '  2 slow proofs to run: purlin:test --all',
            '  1 rule to test on Windows: run purlin:test on Windows'], lines


class TestWhatLetsTheTestsBeMet:

    # purlin: summary PROOF-47
    def test_a_weak_rule_on_committed_evidence_is_to_strengthen_tests_met(
            self):
        made = Project()
        try:
            made.evidence(PASSING)
            made.audit('RULE-2', word='weak',
                       observations=['PROOF-2 reads 401 alone.'])
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
            assert made.rule('RULE-2')['left'] == 'to_strengthen'
            lines = _status(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines

    # purlin: summary PROOF-54
    def test_a_rule_with_no_proof_whose_test_passes_is_to_write_a_proof_for(
            self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            made.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                            'status': 'pass'}])
            lines = _status(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert '  1 rule to write a proof for: purlin:spec' in lines, lines

    # purlin: summary PROOF-44
    def test_two_passing_rules_with_no_tag_end_on_the_sign_off(self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING)
            lines = _status(made)
        finally:
            made.close()
        assert lines[-1] == LAST_LINE, lines
        assert lines[-2] == '2 rules. 2 pass their tests.', lines


# ---------------------------------------------------------------------------
# The last line, where the sign-off would refuse the results
# ---------------------------------------------------------------------------

def _commit_all(made, subject):
    _git(made.root, 'add', '-A')
    _git(made.root, 'commit', '-q', '-m', subject)


def _local_section(made):
    """`(path, data, section)` of login's local evidence file."""
    path = os.path.join(made.root, '.purlin', 'evidence', 'local',
                        'login.json')
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    return path, data, data['platforms'][purlin_evidence.host_os()]


def _refusal(made):
    """The first line `purlin:sign` refuses the project with, '' for none."""
    lines = sign_module.refusal(made.root, '1.0.0')[0]
    return lines[0] if lines else ''


class TestTheLastLineAgreesWithTheSignOff:

    # purlin: summary PROOF-64
    def test_results_taken_before_a_later_commit_name_the_run_first(self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING)
            _write(os.path.join(made.root, 'notes.txt'), 'a note\n')
            _commit_all(made, 'docs: a note')
            lines = _status(made)
            refused = _refusal(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert lines[-1] == RUN_FIRST % 'purlin:test --all --commit', lines
        assert refused.startswith(NOT_THIS_CODE), refused
        assert refused.endswith('Run purlin:test --all --commit, then '
                                'purlin:sign.'), refused

    # purlin: summary PROOF-65
    def test_results_taken_on_this_code_end_on_the_sign_off(self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING)
            lines = _status(made)
            refused = _refusal(made)
        finally:
            made.close()
        assert lines[-1] == LAST_LINE, lines
        assert not refused.startswith((NOT_THIS_CODE, TAKEN_DIRTY)), refused

    # purlin: summary PROOF-66
    def test_a_kept_slow_result_names_the_run_first(self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING, commit_it=False)
            path, data, section = _local_section(made)
            section['proofs'][1]['kept'] = {
                'commit': made.head(), 'at': '2026-09-12T12:00:00Z',
                'machine': 'dev-machine', 'email': 'dev@example.com'}
            _write(path, json.dumps(data, indent=2, sort_keys=True))
            _commit_all(made, 'purlin: evidence at abc1234')
            lines = _status(made)
            refused = _refusal(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert lines[-1] == RUN_FIRST % 'purlin:test --all --commit', lines
        assert refused.startswith(NOT_THIS_CODE), refused

    # purlin: summary PROOF-67
    def test_results_from_another_system_name_the_run_there(self):
        other = 'windows' if purlin_evidence.host_os() != 'windows' else 'linux'
        word = purlin_evidence.os_word(other)
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING, ci=True, os_name=other)
            _write(os.path.join(made.root, 'notes.txt'), 'a note\n')
            _commit_all(made, 'docs: a note')
            made.evidence(PASSING)
            lines = _status(made)
            refused = _refusal(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert lines[-1] == RUN_FIRST % ('purlin:test on %s' % word), lines
        assert refused.startswith(NOT_THIS_CODE), refused
        assert refused.endswith('Run purlin:test on %s, then purlin:sign.'
                                % word), refused

    # purlin: summary PROOF-68
    def test_results_taken_with_files_uncommitted_name_the_run_first(self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING, commit_it=False)
            path, data, section = _local_section(made)
            section['dirty'] = True
            _write(path, json.dumps(data, indent=2, sort_keys=True))
            _commit_all(made, 'purlin: evidence at abc1234')
            lines = _status(made)
            refused = _refusal(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert lines[-1] == RUN_CLEAN, lines
        assert refused.startswith(TAKEN_DIRTY), refused

    # purlin: summary PROOF-70
    def test_a_test_with_a_095_marker_names_the_rewrite_before_a_sign_off(
            self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING)
            _write(os.path.join(made.root, 'tests', 'test_old.py'),
                   'import pytest\n\n\n'
                   '@pytest.mark.proof("login", "PROOF-2b", "RULE-2")\n'
                   'def test_denied():\n    pass\n')
            _commit_all(made, 'test: an old test')
            made.evidence(PASSING)
            lines = _status(made)
            refused = _refusal(made)
        finally:
            made.close()
        assert lines[1] == 'Tests: met', lines
        assert lines[-1] == OLD_FIRST, lines
        assert refused.startswith('No sign-off: 1 test still carries'), \
            refused

    # purlin: summary PROOF-69
    def test_the_dashboard_data_carries_the_same_last_line(self):
        made = Project(spec=SPEC)
        try:
            made.evidence(PASSING)
            _write(os.path.join(made.root, 'notes.txt'), 'a note\n')
            _commit_all(made, 'docs: a note')
            lines = _status(made)
            with open(os.path.join(made.root, '.purlin', 'report-data.js'),
                      encoding='utf-8') as handle:
                written = handle.read()
        finally:
            made.close()
        data = json.loads(written[written.index('{'):written.rindex('}') + 1])
        assert data['last_line'] == lines[-1], data['last_line']
        assert data['last_line'] == RUN_FIRST % 'purlin:test --all --commit'
