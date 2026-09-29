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
        assert sign_waiting_problems() == []

    # purlin: skill_sign PROOF-9
    def test_a_signature_before_the_audit_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_waiting_problems, [
            (skill_path('sign'), swap_first(SIGN_SCRIPTS[0], SIGN_SCRIPTS[1]),
             'out of order, at offsets')]) == []

    # purlin: skill_sign PROOF-10
    def test_no_sync_status_call_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_waiting_problems, [
            (rel, replace('```\nsync_status()\n```\n'),
             '%s does not read to_test_by_hand and to_sign from sync_status'
             % rel)]) == []

    # purlin: skill_sign PROOF-11
    def test_an_audit_path_outside_the_plugin_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_waiting_problems, [
            (rel, replace(SIGN_SCRIPTS[0], '"scripts/review/ai_audit.py"'),
             '%s does not carry %r' % (rel, SIGN_SCRIPTS[0]))]) == []

    # purlin: skill_sign PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('sign')
                + undirected_outcome_problems('sign')) == []

    # purlin: skill_sign PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'sign', '| `Left to do:` and its lines',
            '| A case was added | `→ Run: purlin:build <feature>` |') == []

    # purlin: skill_sign PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('sign') == []

    # purlin: skill_sign PROOF-5
    def test_a_signature_counts_on_a_signed_commit_and_its_hashes(self):
        assert sign_count_problems() == []

    # purlin: skill_sign PROOF-12
    def test_a_missing_condition_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        row = next(line for line in read(rel).splitlines()
                   if line.startswith('| ' + SIGN_COUNTS[0]))
        assert refusals(monkeypatch, sign_count_problems, [
            (rel, replace(row + '\n'), repr(SIGN_COUNTS[0]))]) == []

    # purlin: skill_sign PROOF-13
    def test_a_changed_clause_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_count_problems, [
            (rel, replace('whoever last committed\nto the test file',
                          'whoever committed last'),
             'does not say the signature counts')]) == []

    # purlin: skill_sign PROOF-6
    def test_the_walk_takes_one_of_three_answers(self):
        assert sign_answer_problems() == []

    # purlin: skill_sign PROOF-7
    def test_it_says_what_each_gate_leaves_it_able_to_do(self):
        assert sign_gate_problems() == []

    # purlin: skill_sign PROOF-15
    def test_a_gate_table_with_no_passed_row_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        passed = next(line for line in read(rel).splitlines()
                      if line.startswith('| `passed` |'))
        assert refusals(monkeypatch, sign_gate_problems, [
            (rel, replace(passed + '\n'),
             '%s gate table has no `passed` row' % rel)]) == []

    # purlin: skill_sign PROOF-16
    def test_a_signed_row_that_asks_nothing_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_gate_problems, [
            (rel, replace('| Every rule waits for a signature once',
                          '| Rules wait once'),
             "%s signed row does not name 'Every rule waits for a signature"
             % rel)]) == []

    # purlin: skill_sign PROOF-8
    def test_the_tag_carries_the_evidence_package_and_nothing_is_pushed(self):
        assert sign_tag_problems() == []

    # purlin: skill_sign PROOF-17
    def test_the_tag_line_before_the_package_line_is_reported(
            self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_tag_problems, [
            (rel, swap_first(SIGN_PACKAGE_LINE, SIGN_TAG_LINE),
             '%s tag section prints the tag line before the package line'
             % rel)]) == []

    # purlin: skill_sign PROOF-18
    def test_a_tag_section_that_does_not_stop_below_signed_is_reported(
            self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_tag_problems, [
            (rel, replace('Below `signed` it writes no tag and no package.',
                          ''),
             "'Below `signed` it writes no tag and no package'")]) == []

    # purlin: skill_sign PROOF-19
    def test_it_says_where_the_version_comes_from_and_asks_for_one(self):
        assert sign_version_problems() == []

    # purlin: skill_sign PROOF-20
    def test_no_offer_to_write_the_version_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_version_problems, [
            (rel, replace('offer to write it to a', 'then use'),
             'does not offer to write the version')]) == []

    # purlin: skill_sign PROOF-21
    def test_it_shows_the_key_commands_and_offers_to_run_them(self):
        assert sign_key_problems() == []

    # purlin: skill_sign PROOF-22
    def test_no_offer_to_run_the_key_commands_is_reported(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_key_problems, [
            (rel, replace('offer to run them', 'tell them'),
             "'offer to run them'")]) == []


# The script that shows what the audit found, and the one that signs.
SIGN_SCRIPTS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"',
                '"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"')


def sign_waiting_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'what waits') or ''
    problems = []
    # The two kinds are read off what the sync_status call returns.
    if not re.search(r'sync_status\(\).*to_test_by_hand.*to_sign', body, re.S):
        problems.append('%s does not read to_test_by_hand and to_sign from '
                        'sync_status in its section on what waits' % rel)
    return problems + in_order(rel, SIGN_SCRIPTS)


# The two things that make a signature count.
SIGN_COUNTS = (
    'The last commit that touched the file is signed, with any key',
    'It is still made over the rule, the proof, the test, the code its '
    'feature lists, what the audit found and the machine each system\'s '
    'tests ran on')


def sign_count_problems():
    rel = skill_path('sign')
    text = read(rel)
    conditions = [cells[0] for cells in table_rows(
        text, '| A signature counts when |')]
    problems = ['%s table A signature counts when has no row %r'
                % (rel, condition)
                for condition in SIGN_COUNTS if condition not in conditions]
    problems.extend('%s table A signature counts when has a third row %r'
                    % (rel, condition)
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
SIGN_TAG_LINE = 'Tagged signed/1.4.0 at a1b2c3d.'


def sign_tag_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'the tag')
    if body is None:
        return ['%s has no section on the tag' % rel]
    problems = ['%s tag section does not carry %r' % (rel, needle)
                for needle in ('At the gate `signed`, when nothing is left '
                               'but the tag',
                               '.purlin/evidence/package/<version>.json',
                               'commits it as a signed commit',
                               'writes a signed tag',
                               'on that commit',
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


VERSION_SOURCES = ('`VERSION`', '`package.json`', '`pyproject.toml`',
                   '`*.csproj`')


def sign_version_problems():
    rel = skill_path('sign')
    body = flat(section(read(rel), r'the tag') or '')
    found = [body.find(source) for source in VERSION_SOURCES]
    problems = []
    if -1 in found or found != sorted(found):
        problems.append('%s tag section does not name %s in that order'
                        % (rel, ', '.join(VERSION_SOURCES)))
    if ('ask the person for the version, offer to write it to a `VERSION` '
            'file') not in body:
        problems.append('%s tag section does not offer to write the version '
                        'to a VERSION file' % rel)
    return problems


KEY_LINES = ('No key to sign with. These commands set one up:',
             '  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
             '  git config gpg.format ssh',
             '  git config user.signingkey ~/.ssh/id_ed25519.pub')


def sign_key_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'a key to sign with') or ''
    lines = body.splitlines()
    problems = ['%s key section does not print %r' % (rel, line)
                for line in KEY_LINES if line not in lines]
    problems.extend('%s key section does not say %r' % (rel, words)
                    for words in ('offer to run them', 'carry on')
                    if words not in flat(body))
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
    if 'A skipped rule waits again next time' not in flattened:
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
    for gate in ('`passed`', '`strong`'):
        if 'The walk and `--note` work on the hand checks' not in rows[gate]:
            problems.append("%s %s row does not name 'The walk and `--note` "
                            "work on the hand checks'" % (rel, gate.strip('`')))
    needle = ('Every rule waits for a signature once its tests pass and its '
              'audit is strong')
    if needle not in rows['`signed`']:
        problems.append('%s signed row does not name %r' % (rel, needle))
    return problems
