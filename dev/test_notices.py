"""The one shape of a warning: `<what it is about>: <kind>. <what is wrong>
<what to do>`, and a reworded proof shown by the words that changed.

    python3 -m pytest dev/test_notices.py -q
"""

import os
import subprocess
import sys

from mcp_project import Project, SPEC, _git, _write
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import (markers, notices, specs, status as purlin_status, summary,
                    wording)

WORDING_PY = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scripts', 'mcp', 'purlin', 'wording.py')

KEYS_SPEC = (
    '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
    '- RULE-1: The package holds the keys the rule names and no other\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): The package holds exactly the sixteen keys the '
    'rule names\n')
KEYS_TEST = ('# purlin: login PROOF-1\n'
             'def test_keys():\n'
             '    assert True\n')


def _commit(root, message):
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', message)


def _reworded_project():
    """`login`, whose PROOF-1 says `sixteen` when its test is committed and
    `seventeen` one commit later. `(project, sha7 of the test's commit)`."""
    made = Project(spec=None)
    made.spec(KEYS_SPEC)
    _write(os.path.join(made.root, 'src', 'login.py'), 'KEYS = 17\n')
    _write(os.path.join(made.root, 'tests', 'test_login.py'), KEYS_TEST)
    _commit(made.root, 'feat(login): the keys and their test')
    sha7 = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=made.root,
                          capture_output=True, text=True).stdout[:7]
    made.spec(KEYS_SPEC.replace('sixteen', 'seventeen'))
    _commit(made.root, 'spec(login): seventeen keys')
    return made, sha7


def _reworded_line(sha7):
    return ('login PROOF-1 (RULE-1): test comment to correct. "sixteen" '
            'became "seventeen" after tests/test_login.py:1 last changed '
            '(%s). Run purlin:build login.' % sha7)


class TestTheShape:

    # purlin: notices PROOF-1
    def test_a_spec_mistake_names_the_spec_the_kind_and_the_command(self):
        made = Project(spec=SPEC.replace(
            '> Scope:', '> Requires: api\n> Scope:').replace(
            '\n## Proof', '- RULE-2: Written again\n\n## Proof'))
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
        finally:
            made.close()
        assert lines.count(
            'login RULE-2: spec to repair. It is written twice, and the '
            'second is read. Run purlin:spec login.') == 1, lines
        assert lines.count(
            'login: line not read. Every anchor covers the whole project, so '
            '> Requires: is not read. Run purlin:spec login.') == 1, lines

    # purlin: notices PROOF-2
    def test_a_line_of_information_takes_the_same_shape(self):
        made = Project(spec=SPEC.replace('> Scope: src/login.py',
                                         '> Scope: src/gone.py'))
        try:
            information = made.payload()['information']
        finally:
            made.close()
        assert information == [
            'login: spec ahead of its code. src/gone.py is not written yet. '
            'Run purlin:build login, or purlin:spec login to correct the '
            'path.'], information

    # purlin: notices PROOF-3
    def test_every_kind_has_its_own_few_words(self):
        words = [text for _key, text in notices.KINDS]
        assert len(words) == len(notices.KINDS) > 0
        assert len(set(words)) == len(words), words
        left = {kind: one for kind, one, _many, _command in summary.KINDS}
        shared = sorted(set(left) & set(notices.WORDS))
        assert shared == ['no_test', 'to_correct', 'to_fix', 'to_repair']
        assert {kind: notices.WORDS[kind] for kind in shared} == {
            'no_test': left['no_test'], 'to_correct': left['to_correct'],
            'to_fix': left['to_fix'], 'to_repair': left['to_repair']}
        assert [notices.WORDS[kind] for kind in shared] == [
            'rule to write a test for', 'test comment to correct',
            'rule to fix', 'spec to repair']
        assert all(2 <= len(text.split()) <= 5
                   for kind, text in notices.KINDS if kind not in left), words

    # purlin: notices PROOF-4
    def test_a_proof_no_spec_gives_a_rule_is_named_without_one(self):
        made = Project()
        try:
            _write(os.path.join(made.root, 'tests', 'test_login.py'),
                   '# purlin: login PROOF-9\n'
                   'def test_nine():\n'
                   '    assert True\n')
            lines = markers.marker_problems(markers.scan(made.root),
                                            specs.scan_specs(made.root))
        finally:
            made.close()
        assert lines == [
            'login PROOF-9: test comment to correct. tests/test_login.py:1 '
            'names it, and no spec has it. Run purlin:build.'], lines


class TestARewordedProof:

    # purlin: notices PROOF-5
    def test_one_word_changed_prints_that_word_alone(self):
        made, sha7 = _reworded_project()
        try:
            done = subprocess.run(
                [sys.executable, WORDING_PY, '--project-root', made.root],
                capture_output=True, text=True)
        finally:
            made.close()
        assert done.returncode == 0, done.stderr
        assert done.stdout.splitlines() == [
            _reworded_line(sha7), '1 test comment to correct.'], done.stdout

    # purlin: notices PROOF-6
    def test_neither_wording_is_printed_whole(self):
        made, sha7 = _reworded_project()
        try:
            (entry,) = wording.stale_comments(made.root,
                                              specs.scan_specs(made.root))
        finally:
            made.close()
        assert entry['text'] == _reworded_line(sha7)
        assert 'The package holds' not in entry['text']
        assert 'keys the rule names' not in entry['text']
        assert '\n' not in entry['text']

    # purlin: notices PROOF-7
    def test_a_word_added_is_shown_with_the_word_before_it(self):
        assert notices.changed_words(
            'A sample taken 90 minutes ago reads 90',
            'A sample taken 90 minutes ago reads 90 minutes') == (
            '"90" became "90 minutes"')

    # purlin: notices PROOF-8
    def test_a_word_taken_out_is_shown_with_the_word_on_each_side(self):
        assert notices.changed_words(
            'The export holds a header line and then one line per row',
            'The export holds a line and then one line per row') == (
            '"a header line" became "a line"')

    # purlin: notices PROOF-9
    def test_a_side_over_eight_words_is_cut_to_eight(self):
        assert notices.changed_words(
            'Open the page and read one two three four five six seven eight '
            'nine ten words then stop',
            'Open the page and read nothing then stop') == (
            '"one two three four five six seven eight ..." became "nothing"')

    # purlin: notices PROOF-10
    def test_wordings_that_share_too_little_read_was_reworded(self):
        assert notices.changed_words('A', 'B') == 'was reworded'
        before = 'Start ' + ' '.join('old%d' % n for n in range(9)) + ' end'
        after = 'Start ' + ' '.join('new%d' % n for n in range(9)) + ' end'
        assert notices.changed_words(before, after) == 'was reworded'


class TestTheDashboardsData:

    # purlin: notices PROOF-11
    def test_the_payload_carries_the_line_in_its_parts(self):
        made, sha7 = _reworded_project()
        try:
            data = made.payload()
        finally:
            made.close()
        line = _reworded_line(sha7)
        assert data['notices'] == [{
            'tone': 'warn', 'kind': 'to_correct',
            'label': 'test comment to correct',
            'about': 'login PROOF-1 (RULE-1)', 'feature': 'login',
            'rule': 'RULE-1',
            'rest': '"sixteen" became "seventeen" after tests/test_login.py:1 '
                    'last changed (%s). Run purlin:build login.' % sha7,
            'text': line}], data['notices']

    # purlin: notices PROOF-12
    def test_a_line_with_no_kind_is_carried_whole(self):
        assert notices.entries(['A line of some other sort.'], 'warn') == [{
            'tone': 'warn', 'kind': None, 'label': None, 'about': None,
            'feature': None, 'rule': None,
            'rest': 'A line of some other sort.',
            'text': 'A line of some other sort.'}]


STATUS_PY = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scripts', 'run', 'purlin_status.py')


def _requires(name):
    """The spec `name`, carrying `> Requires: api`, a line Purlin does not read."""
    return SPEC.replace('# Feature: login', '# Feature: %s' % name).replace(
        '> Scope:', '> Requires: api\n> Scope:')


def _unread(name):
    return ('%s: line not read. Every anchor covers the whole project, so '
            '> Requires: is not read. Run purlin:spec %s.' % (name, name))


def _status_of(names):
    """`(the status's lines, what --spec prints for the first name)` in a
    project whose specs `names` each carry `> Requires: api`."""
    made = Project(spec=None)
    try:
        for name in names:
            made.spec(_requires(name), name=name)
        lines = purlin_status.sync_status(made.root).splitlines()
        one = subprocess.run(
            [sys.executable, STATUS_PY, '--project-root', made.root, '--spec',
             names[0]], capture_output=True, text=True, encoding='utf-8')
    finally:
        made.close()
    return lines, one.stdout.splitlines()


class TestTheTerminalFolds:

    # purlin: notices PROOF-13
    def test_four_specs_with_one_kind_of_warning_fold_into_one_line(self):
        lines, one = _status_of(['alpha', 'beta', 'delta', 'gamma'])
        assert lines.count(
            'line not read: 4 specs, alpha, beta and 2 more. Run '
            'purlin:status for each.') == 1, lines
        assert not [line for line in lines if ': line not read.' in line], \
            lines
        assert one[0] == _unread('alpha'), one

    # purlin: notices PROOF-14
    def test_two_specs_with_one_kind_of_warning_are_each_printed_whole(self):
        lines, _one = _status_of(['alpha', 'beta'])
        assert [line for line in lines if 'line not read' in line] == [
            _unread('alpha'), _unread('beta')], lines

    # purlin: notices PROOF-15
    def test_folded_lines_keep_their_place_and_others_stand(self):
        made = [notices.line('to_fix', 'a RULE-%d' % n, None,
                             notices.run('purlin:build a'), feature='a',
                             rule='RULE-%d' % n) for n in (1, 2, 3)]
        other = notices.line('no_test', 'b RULE-1', None,
                             notices.run('purlin:build b'), feature='b',
                             rule='RULE-1')
        assert notices.folded([other] + made + ['A line of another sort.']) \
            == ['b RULE-1: rule to write a test for. Run purlin:build b.',
                'rule to fix: a, in 3 places. Run purlin:status a.',
                'A line of another sort.']
