"""Text checks for the sign skill, `skills/sign/SKILL.md`.

Every rule of `specs/skills/skill_sign.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (flat, frontmatter_problems, frontmatter_refusals,
                          in_order, next_step_problems, next_step_refusals,
                          read, refusals, replace, section,
                          skill_ceiling_problems, skill_path, swap_first,
                          table_rows, undirected_outcome_problems)


class TestSkillSign:

    # purlin: skill_sign PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('sign') == []

    # purlin: skill_sign PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'sign') == []

    # purlin: skill_sign PROOF-2
    def test_it_shows_what_the_audit_found_before_it_writes_the_signature(self):
        assert sign_queue_problems() == []

    # purlin: skill_sign PROOF-2
    def test_a_signature_before_the_audit_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_queue_problems, [
            (rel, swap_first(SIGN_SCRIPTS[0], SIGN_SCRIPTS[1]),
             'out of order, at offsets'),
            (rel, replace(SIGN_SCRIPTS[0], '"scripts/review/ai_audit.py"'),
             '%s does not carry %r' % (rel, SIGN_SCRIPTS[0])),
            (rel, replace('```\nsync_status()\n```\n'),
             '%s does not read payload.queue from sync_status' % rel),
        ]) == []

    # purlin: skill_sign PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('sign')
                + undirected_outcome_problems('sign')) == []

    # purlin: skill_sign PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'sign', '| Rules still in the queue',
            '| A case was added | `→ Run: purlin:build <feature>` |') == []

    # purlin: skill_sign PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('sign') == []

    # purlin: skill_sign PROOF-5
    def test_a_signature_counts_on_a_signed_commit_and_its_hashes(self):
        assert sign_count_problems() == []

    # purlin: skill_sign PROOF-5
    def test_a_missing_condition_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        text = read(rel)
        rows = [line for line in text.splitlines()
                if any(line.startswith('| ' + c) for c in SIGN_COUNTS)]

        def out_of_the_table(t):
            t = t.replace(rows[0] + '\n', '', 1)
            return t.replace('Nothing else is read.',
                             SIGN_COUNTS[0] + '. Nothing else is read.', 1)
        assert refusals(monkeypatch, sign_count_problems, [
            (rel, replace(rows[0] + '\n'), repr(SIGN_COUNTS[0])),
            (rel, out_of_the_table, repr(SIGN_COUNTS[0])),
            (rel, replace(rows[1] + '\n'), repr(SIGN_COUNTS[1])),
            (rel, replace('whoever last committed to the test file',
                          'whoever committed last'),
             'does not say the signature counts'),
        ]) == []

    # purlin: skill_sign PROOF-6
    def test_the_walk_takes_one_of_three_answers(self):
        assert sign_answer_problems() == []

    # purlin: skill_sign PROOF-7
    def test_it_says_what_each_gate_leaves_it_able_to_do(self):
        assert sign_gate_problems() == []

    # purlin: skill_sign PROOF-7
    def test_a_gate_row_broken_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        passed = next(line for line in read(rel).splitlines()
                      if line.startswith('| `passed` |'))
        assert refusals(monkeypatch, sign_gate_problems, [
            (rel, replace(passed + '\n'),
             '%s gate table has no `passed` row' % rel),
            (rel, replace(' and stops without writing anything',
                          ' and writes nothing'),
             "%s passed row does not name 'stops'" % rel),
            (rel, replace('Every rule whose level is `signed` has to carry a '
                          'signature before it meets the gate; '),
             "%s signed row does not name 'Every rule whose level" % rel),
            (rel, replace('| The walk and `--note` work.', '| `--note` works.'),
             "%s strong row does not name 'The walk and `--note` work'" % rel),
        ]) == []

    # purlin: skill_sign PROOF-8
    def test_the_tag_carries_the_evidence_package_and_nothing_is_pushed(self):
        assert sign_tag_problems() == []

    # purlin: skill_sign PROOF-8
    def test_a_broken_tag_section_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_tag_problems, [
            (rel, swap_first(SIGN_PACKAGE_LINE, SIGN_TAG_LINE),
             '%s tag section prints the tag line before the package line'
             % rel),
            (rel, replace('package `.purlin/evidence/package/<version>.json`',
                          'package'),
             "'.purlin/evidence/package/<version>.json'"),
            (rel, replace(' Below `signed` it writes no\ntag and no package,',
                          ' Past that,'),
             "'Below `signed` it writes no tag and no package'"),
            (rel, replace('commits it as a\nsigned commit', 'commits it'),
             "'commits it as a signed commit'"),
            (rel, replace('on\nthat commit', 'on\nthe next commit'),
             "'on that commit'"),
        ]) == []


# The script that shows what the audit found, and the one that signs.
SIGN_SCRIPTS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"',
                '"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"')


def sign_queue_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'the queue') or ''
    problems = []
    # The queue is what the sync_status call returns: the call, then the key.
    if not re.search(r'sync_status\(\).*payload\.queue', body, re.S):
        problems.append('%s does not read payload.queue from sync_status in '
                        'its section on the queue' % rel)
    return problems + in_order(rel, SIGN_SCRIPTS)


# The two things that make a signature count under `signed`.
SIGN_COUNTS = (
    'The commit that added the file is signed and the signature verifies',
    'Its bound hashes still match the rule, the proof, the test and what the '
    'audit found')


def sign_count_problems():
    rel = skill_path('sign')
    text = read(rel)
    conditions = [cells[0] for cells in table_rows(
        text, '| Under `signed` the signature counts when |')]
    problems = ['%s table Under `signed` the signature counts when has no row '
                '%r' % (rel, condition)
                for condition in SIGN_COUNTS if condition not in conditions]
    problems.extend('%s table Under `signed` the signature counts when has a '
                    'third row %r' % (rel, condition)
                    for condition in conditions if condition not in SIGN_COUNTS)
    body = section(text, r'when a signature counts') or ''
    if ('the signature counts whoever wrote it, whoever last committed to the '
            'test file, and on whatever branch carries it') not in flat(body):
        problems.append('%s does not say the signature counts whoever wrote '
                        'it, whoever last committed to the test file, and on '
                        'whatever branch carries it' % rel)
    return problems


SIGN_PACKAGE_LINE = ('Evidence package committed: '
                     '.purlin/evidence/package/1.4.0.json.')
SIGN_TAG_LINE = ('Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate '
                 'signed.')


def sign_tag_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'the tag')
    if body is None:
        return ['%s has no section on the tag' % rel]
    problems = ['%s tag section does not carry %r' % (rel, needle)
                for needle in ('At the gate `signed`, when the walk '
                               'leaves every rule meeting it',
                               '.purlin/evidence/package/<version>.json',
                               'commits it as a signed commit',
                               'writes a signed tag',
                               'on that commit',
                               'The tag is `signed/<version>`',
                               'Below `signed` it writes no tag and no '
                               'package',
                               'this skill never pushes')
                if needle not in flat(body)]
    lines = body.splitlines()
    if SIGN_PACKAGE_LINE not in lines or SIGN_TAG_LINE not in lines:
        problems.append('%s tag section does not print %r above %r'
                        % (rel, SIGN_PACKAGE_LINE, SIGN_TAG_LINE))
    elif lines.index(SIGN_PACKAGE_LINE) > lines.index(SIGN_TAG_LINE):
        problems.append('%s tag section prints the tag line before the '
                        'package line' % rel)
    return problems


def sign_answer_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'three answers')
    if body is None:
        return ["%s has no section naming the walk's answers" % rel]
    flattened = flat(body)
    problems = ['%s answers do not name %r' % (rel, label)
                for label in ('**Sign.**', '**Add a case.**', '**Skip.**')
                if label not in flattened]
    if 'A skipped rule is in the queue again next time' not in flattened:
        problems.append('%s answers do not say a skipped rule comes back' % rel)
    return problems


def sign_gate_problems():
    rel = skill_path('sign')
    rows = {cells[0]: cells[-1] for cells in table_rows(read(rel), '| Gate |')}
    problems = []
    for gate in ('`passed`', '`strong`', '`signed`'):
        if gate not in rows:
            problems.append('%s gate table has no %s row' % (rel, gate))
    if problems:
        return problems
    for needle in ('purlin:init --gate strong', 'stops'):
        if needle not in rows['`passed`']:
            problems.append('%s passed row does not name %r' % (rel, needle))
    for needle in ('The walk and `--note` work', '--note', 'hand check'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    if '[level: passed]' not in rows['`signed`']:
        problems.append('%s signed row does not name [level: passed]' % rel)
    needle = 'Every rule whose level is `signed` has to carry a signature'
    if needle not in rows['`signed`']:
        problems.append('%s signed row does not name %r' % (rel, needle))
    return problems
