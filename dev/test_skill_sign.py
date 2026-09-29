"""Text checks for the sign skill, `skills/sign/SKILL.md`.

Every rule of `specs/skills/skill_sign.md` is proved here, one test per
proof. The readers, the checks and the broken copies this file shares with
the other skill test files are in `dev/skill_checks.py`; the checks only
this spec needs are below the tests.
"""

import re

from skill_checks import (COMMAND_REF, flat, frontmatter, frontmatter_problems,
                          field, in_order, next_step_problems, on_copy, read,
                          refusals, replace, section,
                          skill_ceiling_problems, skill_path, swap_first,
                          table_rows, undirected_outcome_problems)

SKILL = skill_path('sign')


class TestSkillSign:

    # RULE-1: the frontmatter and the command reference.

    # purlin: skill_sign PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self):
        assert skill_frontmatter_problems() == []

    # purlin: skill_sign PROOF-23
    def test_the_command_reference_carries_a_row_for_sign(self):
        assert command_row_problems() == []

    # purlin: skill_sign PROOF-24
    def test_a_frontmatter_with_no_name_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace('name: sign\n'),
             "%s frontmatter name is None, expected 'sign'" % SKILL)]) == []

    # purlin: skill_sign PROOF-25
    def test_an_empty_description_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace(description_line(), 'description:'),
             NO_DESCRIPTION)]) == []

    # purlin: skill_sign PROOF-26
    def test_an_empty_description_followed_by_the_name_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace('name: sign\n' + description_line(),
                            'description:\nname: sign'),
             NO_DESCRIPTION)]) == []

    # purlin: skill_sign PROOF-27
    def test_a_description_written_as_a_block_is_reported(self, monkeypatch):
        line = description_line()
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace(line, 'description: |\n  ' + description()),
             NO_DESCRIPTION)]) == []

    # purlin: skill_sign PROOF-28
    def test_a_description_run_onto_a_second_line_is_reported(
            self, monkeypatch):
        line = description_line()
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace(line, line + '\n  and a second line'),
             NO_DESCRIPTION)]) == []

    # purlin: skill_sign PROOF-29
    def test_a_command_reference_with_no_sign_row_is_reported(
            self, monkeypatch):
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:sign'))
        edit = replace(row + '\n')
        # The command's name is still in the reference outside the table.
        assert 'purlin:sign' in edit(read(COMMAND_REF))
        assert refusals(monkeypatch, frontmatter_check, [
            (COMMAND_REF, edit,
             '%s carries no row for purlin:sign' % COMMAND_REF)]) == []

    # RULE-2: what waits, what the audit found, and the two scripts.

    # purlin: skill_sign PROOF-2
    def test_what_waits_is_read_from_sync_status(self):
        assert sign_waiting_problems() == []

    # purlin: skill_sign PROOF-30
    def test_it_says_to_read_what_the_audit_found_before_writing(self):
        assert sign_read_first_problems() == []

    # purlin: skill_sign PROOF-31
    def test_the_audit_script_comes_before_the_signing_script(self):
        assert sign_script_problems() == []

    # purlin: skill_sign PROOF-9
    def test_a_signing_script_named_before_the_audit_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, sign_script_problems, [
            (SKILL, swap_first(SIGN_SCRIPTS[0], SIGN_SCRIPTS[1]),
             'out of order, at offsets')]) == []

    # purlin: skill_sign PROOF-10
    def test_no_sync_status_call_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_waiting_problems, [
            (SKILL, replace('```\nsync_status()\n```\n'),
             '%s does not read left, to_test_by_hand and to_sign from '
             'sync_status' % SKILL)]) == []

    # purlin: skill_sign PROOF-11
    def test_an_audit_path_outside_the_plugin_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_script_problems, [
            (SKILL, replace(SIGN_SCRIPTS[0], '"scripts/review/ai_audit.py"'),
             '%s does not carry %r' % (SKILL, SIGN_SCRIPTS[0]))]) == []

    # RULE-3: the closing section.

    # purlin: skill_sign PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('sign')
                + undirected_outcome_problems('sign')) == []

    # purlin: skill_sign PROOF-32
    def test_a_file_with_no_closing_section_is_reported(self, monkeypatch):
        last = read(SKILL).rindex('\n## ')
        assert refusals(monkeypatch, closing_check, [
            (SKILL, lambda text: text[:last + 1],
             "%s closes with the section 'Step 6: the version and the tag', "
             "which does not name the next step" % SKILL)]) == []

    # purlin: skill_sign PROOF-33
    def test_a_closing_section_with_no_arrow_is_reported(self, monkeypatch):
        last = read(SKILL).rindex('\n## ')
        assert refusals(monkeypatch, closing_check, [
            (SKILL, lambda text: text[:last] + text[last:].replace('→',
                                                                   '->'),
             '%s closing section gives no directive' % SKILL)]) == []

    # purlin: skill_sign PROOF-34
    def test_a_closing_table_of_one_outcome_is_reported(self, monkeypatch):
        last = read(SKILL).rindex('\n## ')
        second = '| `Left to do:` and its lines'
        assert refusals(monkeypatch, closing_check, [
            (SKILL, lambda text: text[:text.index(second, last)],
             '%s closing section names 1 outcomes, expected at least 2'
             % SKILL)]) == []

    # purlin: skill_sign PROOF-35
    def test_one_outcome_with_no_arrow_is_reported(self, monkeypatch):
        row = '| A case was added | `→ Run: purlin:build <feature>` |'
        assert refusals(monkeypatch, closing_check, [
            (SKILL, replace(row, row.replace('→ ', '')),
             '%s closing outcome gives no → directive: | A case was '
             'added |' % SKILL)]) == []

    # RULE-4: the ceiling.

    # purlin: skill_sign PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('sign') == []

    # purlin: skill_sign PROOF-36
    def test_a_skill_of_exactly_185_lines_is_let_through(self, monkeypatch):
        assert on_copy(monkeypatch, SKILL, lengthen_to(185),
                       lambda: skill_ceiling_problems('sign')) == []

    # purlin: skill_sign PROOF-37
    def test_a_skill_of_186_lines_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('sign'), [
            (SKILL, lengthen_to(186),
             '%s is 186 lines, ceiling 185' % SKILL)]) == []

    # RULE-5: when a signature counts.

    # purlin: skill_sign PROOF-5
    def test_a_signature_counts_on_two_conditions(self):
        assert sign_count_problems() == []

    # purlin: skill_sign PROOF-38
    def test_it_says_whose_signature_counts(self):
        assert sign_whose_problems() == []

    # purlin: skill_sign PROOF-12
    def test_a_missing_condition_is_reported(self, monkeypatch):
        row = next(line for line in read(SKILL).splitlines()
                   if line.startswith('| ' + SIGN_COUNTS[0]))
        assert refusals(monkeypatch, sign_count_problems, [
            (SKILL, replace(row + '\n'),
             '%s table A signature counts when has no row %r'
             % (SKILL, SIGN_COUNTS[0]))]) == []

    # purlin: skill_sign PROOF-39
    def test_a_third_condition_is_reported(self, monkeypatch):
        row = next(line for line in read(SKILL).splitlines()
                   if line.startswith('| ' + SIGN_COUNTS[1]))
        extra = '| The signer is on a list | A change to the list |'
        assert refusals(monkeypatch, sign_count_problems, [
            (SKILL, replace(row, row + '\n' + extra),
             '%s table A signature counts when has a third row '
             "'The signer is on a list'" % SKILL)]) == []

    # purlin: skill_sign PROOF-13
    def test_a_changed_clause_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_whose_problems, [
            (SKILL, replace('whoever last committed\nto the test file',
                            'whoever committed last'),
             '%s does not say the signature counts' % SKILL)]) == []

    # RULE-6: the walk's three answers.

    # purlin: skill_sign PROOF-6
    def test_the_walk_takes_one_of_three_answers(self):
        assert sign_answer_problems() == []

    # RULE-7: what each gate leaves it able to do.

    # purlin: skill_sign PROOF-7
    def test_it_says_what_each_gate_leaves_it_able_to_do(self):
        assert sign_gate_problems() == []

    # purlin: skill_sign PROOF-15
    def test_a_gate_table_with_no_passed_row_is_reported(self, monkeypatch):
        passed = next(line for line in read(SKILL).splitlines()
                      if line.startswith('| `passed` |'))
        assert refusals(monkeypatch, sign_gate_problems, [
            (SKILL, replace(passed + '\n'),
             '%s gate table has no `passed` row' % SKILL)]) == []

    # purlin: skill_sign PROOF-16
    def test_a_signed_row_that_asks_nothing_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_gate_problems, [
            (SKILL, replace('| Every rule waits for a signature once',
                            '| Rules wait once'),
             "%s signed row does not name 'Every rule waits for a signature"
             % SKILL)]) == []

    # RULE-8: the package, the tag, and no push.

    # purlin: skill_sign PROOF-8
    def test_at_signed_it_commits_the_package_and_tags_that_commit(self):
        assert sign_tag_problems() == []

    # purlin: skill_sign PROOF-40
    def test_it_prints_the_package_line_above_the_tag_line(self):
        assert sign_tag_line_problems() == []

    # purlin: skill_sign PROOF-17
    def test_the_tag_line_before_the_package_line_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, sign_tag_line_problems, [
            (SKILL, swap_first(SIGN_PACKAGE_LINE, SIGN_TAG_LINE),
             '%s tag section prints the tag line before the package line'
             % SKILL)]) == []

    # purlin: skill_sign PROOF-41
    def test_below_signed_it_writes_no_tag_and_no_package(self):
        assert tag_section_says(BELOW_SIGNED) == []

    # purlin: skill_sign PROOF-18
    def test_a_tag_section_that_does_not_stop_below_signed_is_reported(
            self, monkeypatch):
        assert refusals(monkeypatch, lambda: tag_section_says(BELOW_SIGNED), [
            (SKILL, replace(BELOW_SIGNED + '.', ''),
             '%s tag section does not carry %r'
             % (SKILL, BELOW_SIGNED))]) == []

    # purlin: skill_sign PROOF-42
    def test_it_never_pushes(self):
        assert tag_section_says(NEVER_PUSHES) == []

    # RULE-9: the version.

    # purlin: skill_sign PROOF-19
    def test_it_says_where_the_version_comes_from(self):
        assert sign_version_problems() == []

    # purlin: skill_sign PROOF-43
    def test_with_no_version_it_asks_and_offers_to_write_one(self):
        assert sign_version_offer_problems() == []

    # purlin: skill_sign PROOF-20
    def test_no_offer_to_write_the_version_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_version_offer_problems, [
            (SKILL, replace('offer to write it to a', 'then use'),
             '%s tag section does not offer to write the version'
             % SKILL)]) == []

    # RULE-10: the key.

    # purlin: skill_sign PROOF-21
    def test_it_shows_the_key_commands_and_offers_to_run_them(self):
        assert sign_key_problems() == []

    # purlin: skill_sign PROOF-22
    def test_no_offer_to_run_the_key_commands_is_reported(self, monkeypatch):
        assert refusals(monkeypatch, sign_key_problems, [
            (SKILL, replace('offer to run them', 'tell them'),
             "%s key section does not say 'offer to run them'"
             % SKILL)]) == []


# ---------------------------------------------------------------------------
# RULE-1
# ---------------------------------------------------------------------------

NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL


def frontmatter_check():
    return frontmatter_problems('sign')


def skill_frontmatter_problems():
    """The shared check's problems with the skill file itself."""
    return [problem for problem in frontmatter_problems('sign')
            if problem.startswith(SKILL)]


def command_row_problems():
    """The shared check's problems with the command reference."""
    return [problem for problem in frontmatter_problems('sign')
            if problem.startswith(COMMAND_REF)]


def description():
    return field(frontmatter(read(SKILL)), 'description')


def description_line():
    return 'description: %s' % description()


# ---------------------------------------------------------------------------
# RULE-2
# ---------------------------------------------------------------------------

# The script that shows what the audit found, and the one that signs.
SIGN_SCRIPTS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"',
                '"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"')

READ_FIRST = ('Read what the audit read and found for a rule before anything '
              'is written')


def waiting_section():
    return section(read(SKILL), r'what waits') or ''


def sign_waiting_problems():
    # The kinds are read off what the sync_status call returns.
    if re.search(r'sync_status\(\).*`left`.*`to_test_by_hand`.*`to_sign`',
                 waiting_section(), re.S):
        return []
    return ['%s does not read left, to_test_by_hand and to_sign from '
            'sync_status in its section on what waits' % SKILL]


def sign_read_first_problems():
    if READ_FIRST in flat(waiting_section()):
        return []
    return ['%s section on what waits does not say %r' % (SKILL, READ_FIRST)]


def sign_script_problems():
    return in_order(SKILL, SIGN_SCRIPTS)


# ---------------------------------------------------------------------------
# RULE-3 and RULE-4
# ---------------------------------------------------------------------------

def closing_check():
    return next_step_problems('sign') + undirected_outcome_problems('sign')


def lengthen_to(count):
    """An edit that adds lines of prose until the file is `count` lines."""
    def edit(text):
        missing = count - len(text.splitlines())
        assert missing > 0, 'the file is already %d lines' % count
        return text + 'A line of prose.\n' * missing
    return edit


# ---------------------------------------------------------------------------
# RULE-5
# ---------------------------------------------------------------------------

# The two things that make a signature count.
SIGN_COUNTS = (
    'The last commit that touched the file is signed, with any key',
    'It is still made over the rule, the proof, the test, the code its '
    'feature lists, what the audit found and the machine each system\'s '
    'tests ran on')

WHOSE = ('the signature counts whoever wrote it, whoever last committed to '
         'the test file, and on whatever branch carries it')


def sign_count_problems():
    conditions = [cells[0] for cells in table_rows(
        read(SKILL), '| A signature counts when |')]
    problems = ['%s table A signature counts when has no row %r'
                % (SKILL, condition)
                for condition in SIGN_COUNTS if condition not in conditions]
    problems.extend('%s table A signature counts when has a third row %r'
                    % (SKILL, condition)
                    for condition in conditions if condition not in SIGN_COUNTS)
    return problems


def sign_whose_problems():
    body = section(read(SKILL), r'when a signature counts') or ''
    if WHOSE in flat(body):
        return []
    return ['%s does not say the signature counts whoever wrote it, whoever '
            'last committed to the test file, and on whatever branch carries '
            'it' % SKILL]


# ---------------------------------------------------------------------------
# RULE-6 and RULE-7
# ---------------------------------------------------------------------------

def sign_answer_problems():
    body = section(read(SKILL), r'three answers')
    if body is None:
        return ["%s has no section naming the walk's answers" % SKILL]
    flattened = flat(body)
    problems = ['%s answers do not name %r' % (SKILL, label)
                for label in ('**Sign.**', '**Add a case.**', '**Skip.**')
                if label not in flattened]
    if 'A skipped rule waits again next time' not in flattened:
        problems.append('%s answers do not say a skipped rule comes back'
                        % SKILL)
    return problems


def sign_gate_problems():
    rows = {cells[0]: cells[-1] for cells in table_rows(read(SKILL),
                                                        '| Gate |')}
    problems = ['%s gate table has no %s row' % (SKILL, gate)
                for gate in ('`passed`', '`strong`', '`signed`')
                if gate not in rows]
    if problems:
        return problems
    for gate in ('`passed`', '`strong`'):
        if 'The walk and `--note` work on the hand checks' not in rows[gate]:
            problems.append("%s %s row does not name 'The walk and `--note` "
                            "work on the hand checks'"
                            % (SKILL, gate.strip('`')))
    needle = ('Every rule waits for a signature once its tests pass and its '
              'audit is strong')
    if needle not in rows['`signed`']:
        problems.append('%s signed row does not name %r' % (SKILL, needle))
    return problems


# ---------------------------------------------------------------------------
# RULE-8 and RULE-9: the section on the tag
# ---------------------------------------------------------------------------

SIGN_PACKAGE_LINE = ('Evidence package committed: '
                     '.purlin/evidence/package/1.4.0.json.')
SIGN_TAG_LINE = 'Tagged signed/1.4.0 at a1b2c3d.'
BELOW_SIGNED = 'Below `signed` it writes no tag and no package'
NEVER_PUSHES = 'this skill never pushes'


def tag_section():
    return section(read(SKILL), r'the tag')


def tag_section_says(*needles):
    body = tag_section()
    if body is None:
        return ['%s has no section on the tag' % SKILL]
    return ['%s tag section does not carry %r' % (SKILL, needle)
            for needle in needles if needle not in flat(body)]


def sign_tag_problems():
    return tag_section_says('At the gate `signed`, when nothing is left but '
                            'the tag',
                            '.purlin/evidence/package/<version>.json',
                            'commits it as a signed commit',
                            'writes a signed tag',
                            'on that commit')


def sign_tag_line_problems():
    lines = (tag_section() or '').splitlines()
    if SIGN_PACKAGE_LINE not in lines or SIGN_TAG_LINE not in lines:
        return ['%s tag section does not print %r above %r'
                % (SKILL, SIGN_PACKAGE_LINE, SIGN_TAG_LINE)]
    if lines.index(SIGN_PACKAGE_LINE) > lines.index(SIGN_TAG_LINE):
        return ['%s tag section prints the tag line before the package line'
                % SKILL]
    return []


VERSION_SOURCES = ('`VERSION`', '`package.json`', '`pyproject.toml`',
                   '`*.csproj`')


def sign_version_problems():
    body = flat(tag_section() or '')
    found = [body.find(source) for source in VERSION_SOURCES]
    if -1 in found or found != sorted(found):
        return ['%s tag section does not name %s in that order'
                % (SKILL, ', '.join(VERSION_SOURCES))]
    return []


def sign_version_offer_problems():
    if ('ask the person for the version, offer to write it to a `VERSION` '
            'file') in flat(tag_section() or ''):
        return []
    return ['%s tag section does not offer to write the version to a '
            'VERSION file' % SKILL]


# ---------------------------------------------------------------------------
# RULE-10
# ---------------------------------------------------------------------------

KEY_LINES = ('No key to sign with. These commands set one up:',
             '  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
             '  git config gpg.format ssh',
             '  git config user.signingkey ~/.ssh/id_ed25519.pub')


def sign_key_problems():
    body = section(read(SKILL), r'a key to sign with') or ''
    lines = body.splitlines()
    problems = ['%s key section does not print %r' % (SKILL, line)
                for line in KEY_LINES if line not in lines]
    problems.extend('%s key section does not say %r' % (SKILL, words)
                    for words in ('offer to run them', 'carry on')
                    if words not in flat(body))
    return problems
