"""Tests for the summary sentence and `Left to do`.

Each project here is a list of payload rule entries, built by hand with the
cells a payload gives them, so a test names exactly the state it reads. The
ending is composed the way `payload.build_payload` composes it: the steps and
the sentence over the rules each feature owns, then `left` over every
feature, then the nothing-left line.
"""

import os
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import status as purlin_status  # noqa: E402
from purlin import summary  # noqa: E402
from mcp_project import (Project, _commit_tests, _entry,  # noqa: E402
                         _write)

HERE = 'macos'
TWO_PROOFS_SPEC = (
    '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200\n'
    '- PROOF-2 (RULE-1): POST /login with valid credentials; verify a '
    'token\n')
NO_SCOPE_SPEC = TWO_PROOFS_SPEC.replace('> Scope: src/login.py\n\n', '')
TAG = {'name': 'signed/1.4.0', 'commit': 'a' * 40}


def rule(passed='passed', strong=None, signed=None, proofs=1, manual=False,
         missing_env=(), hand_checked=False, label='own', feature='login',
         strong_reasons=()):
    """One payload rule entry with the cells named; a cell left None is absent,
    as it is above the gate."""
    cells = {'passed': {'word': passed, 'missing_env': list(missing_env)}}
    if strong:
        cells['strong'] = {'word': strong, 'reasons': list(strong_reasons)}
    if signed:
        cells['signed'] = {'word': signed}
    return {'feature': feature, 'label': label, 'cells': cells,
            'hand_checked': hand_checked,
            'proofs': [{'id': 'PROOF-%d' % (index + 1), 'manual': manual}
                       for index in range(proofs)]}


def done(gate):
    """A rule that reached every step up to `gate`."""
    return rule(strong='strong' if gate != 'passed' else None,
                signed='signed' if gate == 'signed' else None)


def feature(rules, name='login', incomplete=None):
    return {'name': name, 'incomplete': incomplete, 'rules': rules}


def payload(features, gate, tag=None, here=HERE, corrections=0):
    """The part of a payload the ending reads, composed as the builder does."""
    own = [entry for item in features for entry in item['rules']
           if entry.get('label') == 'own']
    counted = {'rules': len(own), 'steps': summary.steps(own, gate)}
    counted['sentence'] = summary.sentence(counted, gate)
    left = summary.left(features, gate, here, tag, corrections)
    return {'summary': counted, 'left': left, 'finished': not left,
            'last_line': summary.last_line(left, gate, tag)}


def ending(rules, gate, tag=None, here=HERE, incomplete=None, corrections=0):
    """The ending's lines for one feature's rules."""
    made = payload([feature(rules, incomplete=incomplete)], gate, tag, here,
                   corrections)
    return summary.ending(made).splitlines()


# ---------------------------------------------------------------------------
# The sentence
# ---------------------------------------------------------------------------

class TestTheSentence:

    # purlin: summary PROOF-1
    def test_each_step_contains_the_next_at_signed(self):
        rules = ([done('signed')] * 20
                 + [rule(strong='strong', signed='unsigned')] * 10
                 + [rule(strong='not audited', signed='waiting')] * 5
                 + [rule(passed='failed', strong='waiting',
                         signed='waiting')] * 5)
        assert ending(rules, 'signed')[0] == (
            '40 rules. 35 pass their tests. 30 are strong. 20 are signed.')

    # purlin: summary PROOF-2
    def test_at_passed_it_names_the_tests_alone(self):
        rules = [done('passed'), done('passed'), rule(passed='no test')]
        assert ending(rules, 'passed')[0] == '3 rules. 2 pass their tests.'

    # purlin: summary PROOF-3
    def test_at_strong_it_names_no_signature(self):
        rules = [done('strong'), done('strong'), rule(passed='failed',
                                                      strong='waiting')]
        assert ending(rules, 'strong')[0] == (
            '3 rules. 2 pass their tests. 2 are strong.')

    # purlin: summary PROOF-4
    def test_an_anchor_rule_is_counted_once_under_its_owner(self):
        anchor = rule(feature='security')
        features = [
            feature([anchor], name='security'),
            feature([rule(), dict(anchor, label='global')], name='login'),
            feature([rule(feature='export'), dict(anchor, label='global')],
                    name='export'),
        ]
        made = payload(features, 'passed')
        assert made['summary']['sentence'] == '3 rules. 3 pass their tests.'
        assert made['left'] == []


class TestOneAndNone:

    # purlin: summary PROOF-5
    def test_one_rule_reads_singular_throughout(self):
        assert ending([done('signed')], 'signed', tag=TAG)[0] == (
            '1 rule. 1 passes its tests. 1 is strong. 1 is signed.')

    # purlin: summary PROOF-6
    def test_one_rule_left_reads_singular(self):
        lines = ending([rule(strong='not audited')], 'strong')
        assert lines[1:] == ['Left to do:', '  1 rule to audit: purlin:audit']

    # purlin: summary PROOF-7
    def test_zero_reads_plural(self):
        rules = [rule(passed='failed', strong='waiting', signed='waiting')] * 2
        assert ending(rules, 'signed')[0] == (
            '2 rules. 0 pass their tests. 0 are strong. 0 are signed.')


# ---------------------------------------------------------------------------
# Left to do
# ---------------------------------------------------------------------------

NOT_INSTALLED = 'mutmut is not installed: run "pip install mutmut"'
NOT_MEASURED = 'strength not measured: ' + NOT_INSTALLED

# One rule of each kind, at the gate `signed`, on macOS. The rule to tie to
# its files sits in a spec that names no files.
EACH_KIND = (
    ('no_proof', lambda: rule(proofs=0, strong='no proof')),
    ('to_fix', lambda: rule(passed='partial', strong='waiting')),
    ('no_test', lambda: rule(passed='no test', strong='waiting')),
    ('to_test', lambda: rule(passed='not run', strong='waiting')),
    ('to_test_remote', lambda: rule(passed='not run', strong='waiting',
                                    missing_env=['windows'])),
    ('to_test_by_hand', lambda: rule(manual=True, strong='manual test')),
    ('to_audit', lambda: rule(strong='not audited', signed='waiting')),
    ('to_measure', lambda: rule(strong='weak', signed='waiting',
                                strong_reasons=[NOT_MEASURED])),
    ('to_strengthen', lambda: rule(strong='weak', signed='waiting')),
    ('no_scope', lambda: rule(strong='strong', signed='unsigned')),
    ('to_sign', lambda: rule(strong='strong', signed='unsigned')),
)


class TestTheLines:

    # purlin: summary PROOF-8
    def test_each_kind_has_its_words_and_its_command(self):
        features = [feature([make(), make()], name=kind,
                            incomplete='no > Scope: line'
                            if kind == 'no_scope' else None)
                    for kind, make in EACH_KIND]
        lines = summary.ending(payload(features, 'signed')).splitlines()
        assert lines[1:] == [
            'Left to do:',
            '  2 rules to write a proof for: purlin:spec',
            '  2 rules to fix: purlin:build',
            '  2 rules to write a test for: purlin:build',
            '  2 rules to test: purlin:test',
            '  2 rules to test on Windows: purlin:test --remote',
            '  2 rules to test by hand: purlin:sign',
            '  2 rules to audit: purlin:audit',
            '  2 rules to measure: purlin:audit',
            '  2 rules to strengthen: purlin:build',
            '  2 rules to tie to their files: purlin:spec',
            '  2 rules to sign: purlin:sign',
        ]

    # purlin: summary PROOF-9
    def test_one_rule_to_tie_reads_its_files(self):
        lines = ending([rule(strong='strong', signed='unsigned')], 'signed',
                       incomplete='no > Scope: line')
        assert lines[2:] == ['  1 rule to tie to its files: purlin:spec']

    # purlin: summary PROOF-10
    def test_the_lines_follow_the_order_of_the_work(self):
        rules = [rule(strong='strong', signed='unsigned'),
                 rule(passed='failed', strong='waiting', signed='waiting')]
        assert ending(rules, 'signed')[2:] == [
            '  1 rule to fix: purlin:build', '  1 rule to sign: purlin:sign']

    # purlin: summary PROOF-29
    def test_a_comment_naming_nothing_is_a_line_of_its_own(self):
        made = Project()
        try:
            _commit_tests(made, 'PROOF-1', 'PROOF-2', 'PROOF-9')
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')])
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        assert lines[-2:] == ['Left to do:',
                              '  1 test comment to correct: purlin:build'], \
            lines

    # purlin: summary PROOF-35
    def test_a_comment_to_correct_comes_before_a_rule_to_fix(self):
        lines = ending([rule(passed='failed')], 'passed', corrections=1)
        assert lines[1:] == ['Left to do:',
                             '  1 test comment to correct: purlin:build',
                             '  1 rule to fix: purlin:build'], lines

    # purlin: summary PROOF-11
    def test_a_kind_at_zero_has_no_line(self):
        rules = [rule(strong='not audited')] * 3
        assert ending(rules, 'strong')[1:] == [
            'Left to do:', '  3 rules to audit: purlin:audit']


class TestNothingLeft:

    # purlin: summary PROOF-12
    def test_at_passed_nothing_left_names_no_command(self):
        made = payload([feature([done('passed')] * 2)], 'passed')
        assert summary.ending(made).splitlines() == [
            '2 rules. 2 pass their tests.', 'Nothing left to do.']
        assert (made['finished'], made['last_line']) == (
            True, 'Nothing left to do.')

    # purlin: summary PROOF-13
    def test_at_strong_nothing_left_names_no_command(self):
        assert ending([done('strong')] * 2, 'strong') == [
            '2 rules. 2 pass their tests. 2 are strong.',
            'Nothing left to do.']

    # purlin: summary PROOF-14
    def test_at_signed_it_names_the_release_step(self):
        made = payload([feature([done('signed')] * 2)], 'signed', tag=TAG)
        assert summary.ending(made).splitlines()[-1] == (
            'Nothing left to do. Push the tag to release it: '
            'git push origin signed/1.4.0')
        assert made['finished'] is True


class TestOneKindPerRule:

    # purlin: summary PROOF-15
    def test_no_proof_comes_before_a_failing_test(self):
        entry = rule(proofs=0, passed='failed', strong='waiting')
        assert summary.rule_kind(entry, 'strong', HERE) == 'no_proof'
        assert ending([entry], 'strong')[1:] == [
            'Left to do:', '  1 rule to write a proof for: purlin:spec']

    # purlin: summary PROOF-16
    def test_a_failing_rule_is_only_to_fix(self):
        entry = rule(passed='failed', strong='waiting', signed='waiting')
        assert ending([entry], 'signed')[1:] == [
            'Left to do:', '  1 rule to fix: purlin:build']

    # purlin: summary PROOF-17
    def test_at_passed_a_rule_with_nothing_wants_a_test(self):
        lines = ending([rule(proofs=0, passed='no test')], 'passed')
        assert lines[1:] == ['Left to do:',
                             '  1 rule to write a test for: purlin:build']
        assert not any('proof' in line for line in lines), lines

    # purlin: summary PROOF-18
    def test_out_of_date_is_to_test(self):
        entry = rule(passed='out of date', strong='waiting')
        assert ending([entry], 'strong')[2:] == [
            '  1 rule to test: purlin:test']

    # purlin: summary PROOF-31
    def test_a_rule_weak_only_for_want_of_a_measure_is_to_measure(self):
        entry = rule(strong='weak', strong_reasons=[NOT_MEASURED])
        assert ending([entry], 'strong')[2:] == [
            '  1 rule to measure: purlin:audit']

    # purlin: summary PROOF-32
    def test_at_strong_a_spec_naming_no_code_files_is_to_tie(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='strong',
                       extra_config={'mutation_engine': 'auto'})
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-1')], strength=None)
            made.audit('RULE-1')
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        assert lines[-1] == '  1 rule to tie to its files: purlin:spec', lines

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
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        assert lines[-1] == ('  1 rule to test on Windows: '
                             'purlin:test --remote'), lines

    # purlin: summary PROOF-34
    def test_a_rule_one_proof_of_which_no_test_backs_wants_a_test(self):
        made = Project(spec=TWO_PROOFS_SPEC)
        try:
            _commit_tests(made, 'PROOF-1')
            made.evidence([_entry('PROOF-1', 'RULE-1')])
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        assert lines[-1] == '  1 rule to write a test for: purlin:build', \
            lines

    # purlin: summary PROOF-23
    def test_a_rule_this_machine_can_run_part_of_is_to_test(self):
        entry = rule(passed='not run', missing_env=['macos', 'windows'])
        assert ending([entry], 'passed', here='macos')[2:] == [
            '  1 rule to test: purlin:test']


# ---------------------------------------------------------------------------
# The steps
# ---------------------------------------------------------------------------

class TestTheSteps:

    # purlin: summary PROOF-19
    def test_a_signature_does_not_count_above_a_weak_rule(self):
        entry = rule(strong='weak', signed='signed')
        assert ending([entry], 'signed')[0] == (
            '1 rule. 1 passes its tests. 0 are strong. 0 are signed.')

    # purlin: summary PROOF-20
    def test_a_hand_check_not_yet_made_is_not_passed(self):
        assert ending([rule(manual=True)], 'passed') == [
            '1 rule. 0 pass their tests.', 'Left to do:',
            '  1 rule to test by hand: purlin:sign']

    # purlin: summary PROOF-21
    def test_a_hand_check_made_passes(self):
        assert ending([rule(manual=True, hand_checked=True)], 'passed') == [
            '1 rule. 1 passes its tests.', 'Nothing left to do.']


class TestTheSystems:

    # purlin: summary PROOF-22
    def test_two_systems_are_named_in_their_words_and_order(self):
        rules = [rule(passed='not run', missing_env=['windows']),
                 rule(passed='not run', missing_env=['linux'])]
        assert ending(rules, 'passed', here='macos')[2:] == [
            '  2 rules to test on Linux/Unix and Windows: '
            'purlin:test --remote']

    # purlin: summary PROOF-28
    def test_this_machines_own_system_is_never_named_on_the_line(self):
        rules = [rule(passed='not run', missing_env=['macos']),
                 rule(passed='not run', missing_env=['windows'])]
        lines = ending(rules, 'passed', here='macos')
        assert lines[2:] == ['  1 rule to test: purlin:test',
                             '  1 rule to test on Windows: '
                             'purlin:test --remote'], lines
        assert not any('macOS' in line for line in lines), lines


class TestTheTag:

    # purlin: summary PROOF-24
    def test_a_finished_version_with_no_tag_is_to_tag(self):
        made = payload([feature([done('signed')] * 2)], 'signed', tag=None)
        assert summary.ending(made).splitlines()[1:] == [
            'Left to do:', '  the version to tag: purlin:sign']
        assert made['finished'] is False

    # purlin: summary PROOF-30
    def test_a_comment_to_correct_holds_back_the_tag(self):
        made = payload([feature([done('signed')] * 2)], 'signed', tag=None,
                       corrections=1)
        lines = summary.ending(made).splitlines()
        assert lines[1:] == ['Left to do:',
                             '  1 test comment to correct: purlin:build'], \
            lines
        assert not any('the version to tag' in line for line in lines)

    # purlin: summary PROOF-25
    def test_below_signed_no_tag_is_asked_for(self):
        lines = ending([done('strong')] * 2, 'strong', tag=None)
        assert lines[-1] == 'Nothing left to do.'
        assert not any('tag' in line for line in lines), lines
