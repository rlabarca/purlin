"""Text checks for the sign skill, `skills/sign/SKILL.md`.

Every rule of `specs/skills/skill_sign.md` is proved here, one test per
proof; where a broken copy of the skill could slip past a check, the test
also shows that the check reports it. The readers, the checks and the broken
copies this file shares with the other skill test files are in
`dev/skill_checks.py`; the checks only this spec needs are below the tests.
"""

from skill_checks import (COMMAND_REF, field, flat, frontmatter,
                          frontmatter_problems, next_step_problems,
                          next_step_refusals, on_copy, read, refusals,
                          replace, section, skill_ceiling_problems,
                          skill_path, swap_first, table_rows,
                          undirected_outcome_problems)

SKILL = skill_path('sign')


class TestSkillSign:

    # RULE-1: the frontmatter.

    # purlin: skill_sign PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self, monkeypatch):
        assert skill_frontmatter_problems() == []
        line = description_line()
        assert refusals(monkeypatch, frontmatter_check, [
            (SKILL, replace('name: sign\n'),
             "%s frontmatter name is None, expected 'sign'" % SKILL),
            (SKILL, replace(line, 'description:'), NO_DESCRIPTION),
            (SKILL, replace(line, 'description: |\n  ' + description()),
             NO_DESCRIPTION)]) == []

    # RULE-11: the command reference.

    # purlin: skill_sign PROOF-23
    def test_the_command_reference_carries_a_row_for_sign(self, monkeypatch):
        assert command_row_problems() == []
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:sign'))
        assert refusals(monkeypatch, frontmatter_check, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:sign' % COMMAND_REF)]) == []

    # RULE-3: the closing section.

    # purlin: skill_sign PROOF-3
    def test_it_closes_by_naming_the_next_step(self, monkeypatch):
        assert next_step_problems('sign') + \
            undirected_outcome_problems('sign') == []
        assert next_step_refusals(
            monkeypatch, 'sign', '| `Nothing left to do. Push the tag',
            '| `No version:` | `→ Write the version the person gives to '
            'VERSION, then run: purlin:sign` |') == []

    # RULE-4: the ceiling.

    # purlin: skill_sign PROOF-4
    def test_it_stays_under_its_ceiling(self, monkeypatch):
        assert skill_ceiling_problems('sign') == []
        assert on_copy(monkeypatch, SKILL, lengthen_to(185),
                       lambda: skill_ceiling_problems('sign')) == []
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('sign'), [
            (SKILL, lengthen_to(186),
             '%s is 186 lines, ceiling 185' % SKILL)]) == []

    # RULE-5: the two things that make a sign-off count.

    # purlin: skill_sign PROOF-5
    def test_a_sign_off_counts_on_two_conditions(self, monkeypatch):
        assert count_problems() == []
        second = next(line for line in read(SKILL).splitlines()
                      if line.startswith('| ' + COUNTS[1]))
        assert refusals(monkeypatch, count_problems, [
            (SKILL, replace(second + '\n'),
             '%s table A sign-off counts when has no row %r'
             % (SKILL, COUNTS[1])),
            (SKILL, replace(second, second + '\n| The signer is on a list '
                            '| A change to the list |'),
             "%s table A sign-off counts when has a third row "
             "'The signer is on a list'" % SKILL)]) == []

    # RULE-13: whose sign-off counts.

    # purlin: skill_sign PROOF-38
    def test_it_says_whose_sign_off_counts(self, monkeypatch):
        check = lambda: says(WHOSE)  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('whoever wrote it and', 'when'),
             'does not carry %r' % WHOSE)]) == []

    # RULE-10: the key.

    # purlin: skill_sign PROOF-21
    def test_it_shows_the_key_commands_and_offers_to_run_them(
            self, monkeypatch):
        assert key_problems() == []
        assert refusals(monkeypatch, key_problems, [
            (SKILL, replace('offer to run them', 'tell them'),
             "%s key section does not say 'offer to run them'"
             % SKILL)]) == []

    # RULE-15: no push.

    # purlin: skill_sign PROOF-42
    def test_it_never_pushes(self, monkeypatch):
        check = lambda: says(NEVER_PUSHES)  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace(NEVER_PUSHES, 'this skill pushes'),
             'does not carry %r' % NEVER_PUSHES)]) == []

    # RULE-16: no version stated.

    # purlin: skill_sign PROOF-43
    def test_with_no_version_it_asks_and_offers_to_write_one(
            self, monkeypatch):
        check = lambda: section_says(r'refusals', [OFFER])  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('offer to write it to a', 'then use'),
             'does not carry %r' % OFFER)]) == []

    # RULE-20: the line with no version.

    # purlin: skill_sign PROOF-48
    def test_it_quotes_the_no_version_line(self, monkeypatch):
        check = lambda: section_says(r'refusals', [NO_VERSION])  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('Run purlin:sign --release <version>, or',
                            'Name it with --release <version>, or'),
             'does not carry %r' % NO_VERSION)]) == []

    # RULE-23: no narrowing.

    # purlin: skill_sign PROOF-51
    def test_a_rule_is_never_narrowed_to_lose_an_observation(self):
        assert says(NEVER_NARROW) == []

    # RULE-25: the tied test at each stop.

    # purlin: skill_sign PROOF-54
    def test_each_stop_shows_each_proofs_tied_test(self, monkeypatch):
        # The spaces that indent a tied line are its own, so they are read
        # as written, the line breaks around them as spaces.
        check = lambda: section_says(  # noqa: E731
            r'the stops', TIED, lambda text: text.replace('\n', ' '))
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('tied to no test', 'no test'),
             'does not carry %r' % TIED[1])]) == []

    # RULE-29: the walk in two calls.

    # purlin: skill_sign PROOF-59
    def test_it_shows_first_and_asks_about_each_stop(self, monkeypatch):
        assert show_first_problems() == []
        assert refusals(monkeypatch, show_first_problems, [
            (SKILL, replace('sign.py" --show', 'sign.py"'),
             'first sign.py command does not carry --show'),
            (SKILL, replace('in the order printed, one at a time',
                            'one at a time'),
             'does not carry %r' % ASK_EACH)]) == []

    # purlin: skill_sign PROOF-60
    def test_it_writes_the_answers_then_walks_with_them(self, monkeypatch):
        assert answers_problems() == []
        assert refusals(monkeypatch, answers_problems, [
            (SKILL, swap_first(ANSWERS_FILE, ANSWERS_RUN),
             'the answers file is not named before the --answers run'),
            (SKILL, replace(ANSWERS_RUN, 'sign.py" --answers'),
             'does not carry %r' % ANSWERS_RUN)]) == []

    # RULE-30: the gate passed.

    # purlin: skill_sign PROOF-61
    def test_at_passed_nothing_is_signed(self, monkeypatch):
        assert passed_problems() == []
        assert refusals(monkeypatch, passed_problems, [
            (SKILL, replace('To sign releases, run purlin:init --gate '
                            'signed.', ''),
             'passed row does not quote')]) == []

    # RULE-31: the tag at the first sign-off.

    # purlin: skill_sign PROOF-62
    def test_the_first_sign_off_writes_the_tag(self, monkeypatch):
        check = lambda: says(FIRST_TAG, TAG_STAYS)  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('For the first sign-off of the\nversion it '
                            'writes', 'It writes'),
             'does not carry %r' % FIRST_TAG)]) == []


# ---------------------------------------------------------------------------
# RULE-1 and RULE-11
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


def lengthen_to(count):
    """An edit that adds lines of prose until the file is `count` lines."""
    def edit(text):
        missing = count - len(text.splitlines())
        assert missing > 0, 'the file is already %d lines' % count
        return text + 'A line of prose.\n' * missing
    return edit


# ---------------------------------------------------------------------------
# What the skill says
# ---------------------------------------------------------------------------

COUNTS = ('The last commit that touched the file is signed, with any key, and '
          'that signature verifies',
          'Its `package_hash` is the fingerprint of the package committed '
          'for its version')
WHOSE = ('a sign-off counts whoever wrote it and on whatever branch carries '
         'it')
NEVER_PUSHES = 'this skill never pushes'
OFFER = ('ask the person for the version, offer to write it to a `VERSION` '
         'file')
NO_VERSION = ('No version: nothing in this project states one. Run '
              'purlin:sign --release <version>, or write it to a VERSION '
              'file.')
NEVER_NARROW = ('Never narrow a rule or a proof to make an observation '
                'disappear.')
TIED = ('`    tied to tests/test_login.py::test_valid_credentials_return_200`',
        '`    tied to no test`',
        'Under each proof that is not `@manual`')
ASK_EACH = 'ask about each stop in the order printed, one at a time'
ANSWERS_FILE = 'Write the answers to `.purlin/runtime/signoff-answers.json`'
ANSWERS_RUN = 'sign.py" --answers .purlin/runtime/signoff-answers.json'
AT_PASSED = ('Nothing is signed at the gate passed: purlin:test --release '
             'tags the release unsigned. To sign releases, run purlin:init '
             '--gate signed.')
FIRST_TAG = ('For the first sign-off of the version it writes '
             '`signed/<version>` on that commit')
TAG_STAYS = ('`signed/1.2.0 stays at 8de0b6e; this sign-off is added after '
             'it. Push it: git push`')


def says(*needles):
    whole = flat(read(SKILL))
    return ['%s does not carry %r' % (SKILL, needle)
            for needle in needles if needle not in whole]


def section_says(pattern, needles, whole=flat):
    body = whole(section(read(SKILL), pattern) or '')
    return ['%s section %r does not carry %r' % (SKILL, pattern, needle)
            for needle in needles if needle not in body]


def count_problems():
    conditions = [cells[0] for cells in table_rows(
        read(SKILL), '| A sign-off counts when |')]
    problems = ['%s table A sign-off counts when has no row %r'
                % (SKILL, condition)
                for condition in COUNTS if condition not in conditions]
    problems.extend('%s table A sign-off counts when has a third row %r'
                    % (SKILL, condition)
                    for condition in conditions if condition not in COUNTS)
    return problems


KEY_LINES = ('No key to sign with. These commands set one up:',
             '  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
             '  git config gpg.format ssh',
             '  git config user.signingkey ~/.ssh/id_ed25519.pub')


def key_problems():
    body = section(read(SKILL), r'a key to sign with') or ''
    lines = body.splitlines()
    problems = ['%s key section does not print %r' % (SKILL, line)
                for line in KEY_LINES if line not in lines]
    problems.extend('%s key section does not say %r' % (SKILL, words)
                    for words in ('offer to run them', 'carry on')
                    if words not in flat(body))
    return problems


def show_first_problems():
    text = read(SKILL)
    command = next((line for line in text.splitlines()
                    if 'scripts/review/sign.py"' in line), '')
    problems = []
    if ' --show' not in command:
        problems.append('%s first sign.py command does not carry --show'
                        % SKILL)
    problems.extend(section_says(r'the stops', [ASK_EACH]))
    return problems


def answers_problems():
    text = flat(read(SKILL))
    problems = ['%s does not carry %r' % (SKILL, needle)
                for needle in (ANSWERS_FILE, ANSWERS_RUN)
                if needle not in text]
    if not problems and text.index(ANSWERS_FILE) > text.index(ANSWERS_RUN):
        problems.append('%s: the answers file is not named before the '
                        '--answers run' % SKILL)
    return problems


def passed_problems():
    rows = {cells[0]: cells[-1] for cells in table_rows(read(SKILL),
                                                        '| Gate |')}
    if AT_PASSED in rows.get('`passed`', ''):
        return []
    return ['%s gate table passed row does not quote %r' % (SKILL, AT_PASSED)]
