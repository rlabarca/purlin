"""Tests for the summary sentence and `Left to do`.

Each project here is a list of payload rule entries, built by hand with the
cells a payload gives them, so a test names exactly the state it reads. The
ending is composed the way `payload.build_payload` composes it: the steps and
the sentence over the rules each feature owns, then `left` over every
feature, then the nothing-left line.
"""

import json
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
TAG = {'name': 'passed/1.2.0', 'commit': 'a' * 40}


def rule(passed='passed', strong=None, proofs=1, manual=False,
         missing_env=(), feature='login', strong_reasons=()):
    """One payload rule entry with the cells named. The strong cell reads
    `waiting` while the passed cell is not met and `not audited` otherwise,
    unless named."""
    if strong is None:
        strong = 'not audited' if passed == 'passed' else 'waiting'
    cells = {'passed': {'word': passed, 'missing_env': list(missing_env)},
             'strong': {'word': strong, 'reasons': list(strong_reasons)}}
    return {'feature': feature, 'cells': cells,
            'proofs': [{'id': 'PROOF-%d' % (index + 1), 'manual': manual}
                       for index in range(proofs)]}


def feature(rules, name='login', broken=()):
    return {'name': name, 'rules': rules, 'broken': list(broken)}


def payload(features, gate, tag=None, here=HERE, corrections=0):
    """The part of a payload the ending reads, composed as the builder does."""
    own = [entry for item in features for entry in item['rules']]
    counted = {'rules': len(own), 'steps': summary.steps(own),
               'audit': summary.audit_counts(own)}
    counted['sentence'] = summary.sentence(counted)
    left = summary.left(features, gate, here, corrections)
    return {'summary': counted, 'left': left, 'finished': not left,
            'last_line': summary.last_line(left, gate, tag)}


def ending(rules, gate, tag=None, here=HERE, corrections=0):
    """The ending's lines for one feature's rules."""
    made = payload([feature(rules)], gate, tag, here, corrections)
    return summary.ending(made).splitlines()


# ---------------------------------------------------------------------------
# The sentence
# ---------------------------------------------------------------------------

class TestTheSentence:

    # purlin: summary PROOF-2
    def test_at_passed_it_names_the_tests_alone(self):
        rules = [rule(), rule(), rule(passed='no test')]
        assert ending(rules, 'passed')[0] == '3 rules. 2 pass their tests.'

    # purlin: summary PROOF-4
    def test_an_anchor_rule_is_counted_once_under_its_owner(self):
        features = [
            feature([rule(feature='security')], name='security'),
            feature([rule()], name='login'),
            feature([rule(feature='export')], name='export'),
        ]
        made = payload(features, 'passed')
        assert made['summary']['sentence'] == '3 rules. 3 pass their tests.'
        assert made['left'] == []

    # purlin: summary PROOF-42
    def test_with_no_rule_audited_the_sentence_names_no_audit(self):
        rules = [rule()] * 35 + [rule(passed='failed')] * 5
        assert ending(rules, 'signed')[0] == '40 rules. 35 pass their tests.'

    # purlin: summary PROOF-43
    def test_where_the_audit_read_a_rule_the_sentence_says_what_it_found(
            self):
        rules = ([rule(strong='strong')] * 30 + [rule(strong='weak')] * 2
                 + [rule()] * 3 + [rule(passed='failed')] * 5)
        assert ending(rules, 'passed')[0] == (
            '40 rules. 35 pass their tests. '
            'The audit found 30 strong and 2 weak.')


class TestOneAndNone:

    # purlin: summary PROOF-5
    def test_one_rule_reads_singular(self):
        assert ending([rule()], 'signed')[0] == '1 rule. 1 passes its tests.'

    # purlin: summary PROOF-6
    def test_one_rule_left_reads_singular(self):
        lines = ending([rule(passed='failed')], 'passed')
        assert lines[1:] == ['Left to do:', '  1 rule to fix: purlin:build']

    # purlin: summary PROOF-7
    def test_zero_reads_plural(self):
        rules = [rule(passed='failed')] * 2
        assert ending(rules, 'signed')[0] == '2 rules. 0 pass their tests.'


# ---------------------------------------------------------------------------
# Left to do
# ---------------------------------------------------------------------------

# One rule of each kind of rule work, at the gate `signed`, on macOS.
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
    def test_each_kind_has_its_words_and_its_command(self):
        features = [feature([make(), make()], name=kind)
                    for kind, make in EACH_KIND]
        lines = summary.ending(payload(features, 'signed')).splitlines()
        assert lines[1:] == [
            'Left to do:',
            '  2 rules to write a proof for: purlin:spec',
            '  2 rules to fix: purlin:build',
            '  2 rules to write a test for: purlin:build',
            '  2 rules to test: purlin:test',
            '  2 rules to test on Windows: purlin:test --remote',
            '  2 rules to strengthen: purlin:build',
        ]

    # purlin: summary PROOF-10
    def test_the_lines_follow_the_order_of_the_work(self):
        rules = [rule(strong='weak'), rule(passed='failed')]
        assert ending(rules, 'signed')[2:] == [
            '  1 rule to fix: purlin:build',
            '  1 rule to strengthen: purlin:build']

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

    # purlin: summary PROOF-36
    def test_three_comments_naming_nothing_read_plural(self):
        made = Project()
        try:
            _commit_tests(made, 'PROOF-1', 'PROOF-2', 'PROOF-7', 'PROOF-8',
                          'PROOF-9')
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')])
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        assert lines[-2:] == ['Left to do:',
                              '  3 test comments to correct: purlin:build'], \
            lines

    # purlin: summary PROOF-35
    def test_a_comment_to_correct_comes_before_a_rule_to_fix(self):
        lines = ending([rule(passed='failed')], 'passed', corrections=1)
        assert lines[1:] == ['Left to do:',
                             '  1 test comment to correct: purlin:build',
                             '  1 rule to fix: purlin:build'], lines

    # purlin: summary PROOF-11
    def test_a_kind_at_zero_has_no_line(self):
        rules = [rule(strong='weak')] * 3
        assert ending(rules, 'passed')[1:] == [
            'Left to do:', '  3 rules to strengthen: purlin:build']


class TestNothingLeft:

    # purlin: summary PROOF-12
    def test_with_nothing_left_the_ending_is_two_lines(self):
        made = payload([feature([rule()] * 2)], 'passed')
        lines = summary.ending(made).splitlines()
        assert len(lines) == 2, lines
        assert lines[0] == '2 rules. 2 pass their tests.'
        assert lines[1].startswith('Nothing left to do.'), lines
        assert made['finished'] is True

    # purlin: summary PROOF-44
    def test_at_passed_it_names_the_release_run(self):
        assert ending([rule()] * 2, 'passed')[-1] == (
            'Nothing left to do. To release a version: purlin:test --release')

    # purlin: summary PROOF-45
    def test_at_signed_it_names_the_release_run_and_the_sign_off(self):
        assert ending([rule()] * 2, 'signed')[-1] == (
            'Nothing left to do. To release a version: '
            'purlin:test --release, then purlin:sign')

    # purlin: summary PROOF-46
    def test_a_release_tag_on_head_names_the_push(self):
        assert ending([rule()] * 2, 'passed', tag=TAG)[-1] == (
            'Nothing left to do. Push the tag to release it: '
            'git push origin passed/1.2.0')


class TestOneKindPerRule:

    # purlin: summary PROOF-15
    def test_no_proof_comes_before_a_failing_test(self):
        entry = rule(proofs=0, passed='failed')
        assert summary.rule_kind(entry, 'signed', HERE) == 'no_proof'
        assert ending([entry], 'signed')[1:] == [
            'Left to do:', '  1 rule to write a proof for: purlin:spec']

    # purlin: summary PROOF-16
    def test_a_failing_rule_is_only_to_fix(self):
        entry = rule(passed='failed')
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
        entry = rule(passed='out of date')
        assert ending([entry], 'passed')[2:] == [
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

    # purlin: summary PROOF-37
    def test_a_proof_listed_with_no_test_named_wants_a_test(self):
        made = Project(spec=TWO_PROOFS_SPEC)
        try:
            _commit_tests(made, 'PROOF-1')
            rel = made.evidence([_entry('PROOF-1', 'RULE-1'),
                                 _entry('PROOF-2', 'RULE-1',
                                        status='missing')])
            path = os.path.join(made.root, *rel.split('/'))
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            for section in data['platforms'].values():
                for entry in section['proofs']:
                    if entry['id'] == 'PROOF-2':
                        entry['test'] = ''
            _write(path, json.dumps(data, indent=2, sort_keys=True))
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

    # purlin: summary PROOF-20
    def test_a_rule_checked_by_hand_passes_and_adds_no_work(self):
        assert ending([rule(manual=True, strong='manual test')],
                      'passed') == [
            '1 rule. 1 passes its tests.',
            'Nothing left to do. To release a version: purlin:test --release']

    # purlin: summary PROOF-47
    def test_a_weak_rule_is_to_strengthen_and_blocks_no_release(self):
        entry = rule(strong='weak')
        kind = summary.rule_kind(entry, 'signed', HERE)
        assert kind == 'to_strengthen'
        assert kind not in summary.BLOCKING


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


# ---------------------------------------------------------------------------
# A spec to repair
# ---------------------------------------------------------------------------

TWICE = ['PROOF-2 is written twice in the spec']


class TestASpecToRepair:

    # purlin: summary PROOF-40
    def test_one_broken_spec_is_the_first_line(self):
        made = payload([feature([rule(passed='failed')] * 3, broken=TWICE),
                        feature([rule(passed='failed')], name='export')],
                       'passed')
        lines = summary.ending(made).splitlines()
        assert lines[1:] == ['Left to do:',
                             '  1 spec to repair: purlin:spec',
                             '  1 rule to fix: purlin:build'], lines

    # purlin: summary PROOF-41
    def test_two_broken_specs_read_plural(self):
        made = payload([feature([rule(passed='failed')] * 2, broken=TWICE),
                        feature([rule(passed='failed')], name='export',
                                broken=TWICE)], 'passed')
        lines = summary.ending(made).splitlines()
        assert lines[1:] == ['Left to do:',
                             '  2 specs to repair: purlin:spec'], lines
