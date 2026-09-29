"""Text checks for the spec-from-code skill, `skills/spec-from-code/SKILL.md`.

Every rule of `specs/skills/skill_spec_from_code.md` is proved here, one
case to a test, and each test also points its check at copies of the skill
with one thing broken, which the check must refuse. The readers, the checks and the broken copies this file shares
with the other skill test files are in `dev/skill_checks.py`; the checks that
belong to this skill alone, and the broken copies each test makes, are below.
"""

import re

from skill_checks import (COMMAND_REF, carries, closing_outcomes, field, flat,
                          frontmatter, frontmatter_problems, next_step_problems,
                          on_copy, read, refusals, replace, resub, section,
                          sections, sentence_with, skill_ceiling_problems,
                          skill_path, undirected_outcome_problems)

NAME = 'spec-from-code'
SKILL = skill_path(NAME)


# ---------------------------------------------------------------------------
# RULE-1: the frontmatter; RULE-11: the command reference's row
# ---------------------------------------------------------------------------

def skill_frontmatter_problems():
    return [p for p in frontmatter_problems(NAME) if p.startswith(SKILL)]


def command_row_problems():
    return [p for p in frontmatter_problems(NAME) if p.startswith(COMMAND_REF)]


def all_frontmatter_problems():
    return frontmatter_problems(NAME)


def description_line():
    return 'description: %s' % field(frontmatter(read(SKILL)), 'description')


def command_row():
    return next(line for line in read(COMMAND_REF).splitlines()
                if re.match(r'\| `purlin:%s[ `]' % re.escape(NAME), line))


NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL


class TestFrontmatterAndCommandRow:

    # purlin: skill_spec_from_code PROOF-1
    def test_the_frontmatter_names_the_skill_and_describes_it_on_one_line(
            self, monkeypatch):
        assert skill_frontmatter_problems() == []
        line = description_line()
        value = line[len('description: '):]
        assert refusals(monkeypatch, all_frontmatter_problems, [
            (SKILL, replace('name: %s\n' % NAME),
             "%s frontmatter name is None, expected %r" % (SKILL, NAME)),
            (SKILL, replace(line, 'description:'), NO_DESCRIPTION),
            (SKILL, replace(line, 'description:\n' + value), NO_DESCRIPTION),
            (SKILL, replace(line, 'description: |\n  ' + value),
             NO_DESCRIPTION),
            (SKILL, replace(line, line + '\n  and a second line'),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_spec_from_code PROOF-125
    def test_the_command_reference_has_a_row_with_the_purpose(
            self, monkeypatch):
        assert command_row_problems() == []
        row = command_row()
        without = read(COMMAND_REF).replace(row + '\n', '', 1)
        # The name stays elsewhere in the reference, so only a row check
        # can tell the row is gone.
        assert 'purlin:%s' % NAME in without
        assert refusals(monkeypatch, all_frontmatter_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:%s' % (COMMAND_REF, NAME)),
        ]) == []


# ---------------------------------------------------------------------------
# RULE-2: the section before the procedure
# ---------------------------------------------------------------------------

def spec_from_code_start_problems():
    body = section(read(SKILL), r'before you start')
    if body is None:
        return ['%s has no section that runs before the survey' % SKILL]
    flattened = flat(body)
    problems = ['%s start section does not name %r' % (SKILL, needle)
                for needle in ('sync_status', '.purlin/config.json',
                               'purlin:init')
                if needle not in flattened]
    headings = [heading for heading, _ in sections(read(SKILL))]
    if 'Procedure' not in headings or \
            headings.index('Before you start') > headings.index('Procedure'):
        problems.append('%s start section comes after the Procedure section'
                        % SKILL)
    if ('When the project has no `.purlin/config.json`, run `purlin:init` '
            'first') not in flattened:
        problems.append('%s start section does not send the reader to '
                        'purlin:init when .purlin/config.json is missing'
                        % SKILL)
    return problems


def start_section():
    return re.search(r'^## Before you start\n.*?(?=^## )', read(SKILL),
                     re.S | re.M).group(0)


class TestBeforeYouStart:

    # purlin: skill_spec_from_code PROOF-2
    def test_it_calls_sync_status_and_sends_a_bare_project_to_init_first(
            self, monkeypatch):
        assert spec_from_code_start_problems() == []
        start = start_section()
        assert refusals(monkeypatch, spec_from_code_start_problems, [
            (SKILL, replace(start),
             '%s has no section that runs before the survey' % SKILL),
            (SKILL, lambda t: t.replace(start, '').replace(
                '## What the rules look like',
                start + '## What the rules look like'),
             '%s start section comes after the Procedure section' % SKILL),
            (SKILL, replace('When the project has no `.purlin/config.json`,'
                            ' run', 'Read `.purlin/config.json`, then run'),
             '%s start section does not send the reader to purlin:init when '
             '.purlin/config.json is missing' % SKILL),
            (SKILL, replace('Call `sync_status`. '),
             "%s start section does not name 'sync_status'" % SKILL),
        ]) == []



# ---------------------------------------------------------------------------
# RULE-3: the closing section names the next step from the state
# ---------------------------------------------------------------------------

FROM_THE_STATE = 'name the next step from the state'


def from_the_state_problems():
    body = sections(read(SKILL))[-1][1]
    if FROM_THE_STATE not in flat(body):
        return ['%s closing section does not name the next step from the '
                'state' % SKILL]
    return []


def closing_problems():
    return (next_step_problems(NAME) + undirected_outcome_problems(NAME)
            + from_the_state_problems())


def last_heading_offset(text):
    return text.rindex('\n## ')


class TestWhenYouAreDone:

    # purlin: skill_spec_from_code PROOF-3
    def test_it_names_the_next_step_from_the_state_for_each_outcome(
            self, monkeypatch):
        assert closing_problems() == []
        before = sections(read(SKILL))[-2][0]
        assert before == 'What not to do'
        second = '- Rules with no test at all'
        directed = ('- Rules with no test at all: `\u2192 Run: purlin:build '
                    '<name>` on the feature with the most of')
        outcome = [o for o in closing_outcomes(sections(read(SKILL))[-1][1])
                   if o.startswith(second)]
        assert len(outcome) == 1

        def no_arrow(t):
            last = last_heading_offset(t)
            return t[:last] + t[last:].replace('\u2192', '->')
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:last_heading_offset(t) + 1],
             '%s closes with the section %r, which does not name the next '
             'step' % (SKILL, before)),
            (SKILL, no_arrow, '%s closing section gives no directive' % SKILL),
            (SKILL, lambda t: t[:t.index(second, last_heading_offset(t))],
             '%s closing section names 1 outcomes, expected at least 2'
             % SKILL),
            (SKILL, replace(directed, directed.replace('\u2192 ', '')),
             '%s closing outcome gives no \u2192 directive: %s'
             % (SKILL, outcome[0].replace('\u2192 ', ''))),
            (SKILL, replace('then name the next step from the state:',
                            'then name the next step:'),
             '%s closing section does not name the next step from the state'
             % SKILL),
        ]) == []



# ---------------------------------------------------------------------------
# RULE-4: the ceiling of 130 lines
# ---------------------------------------------------------------------------

def ceiling_problems():
    return skill_ceiling_problems(NAME)


def padded_to(lines):
    """An edit that appends lines of prose until the file is `lines` long."""
    def edit(text):
        missing = lines - len(text.splitlines())
        assert missing > 0, 'the skill is already %d lines' % (lines - missing)
        return text + 'More prose.\n' * missing
    return edit


class TestCeiling:

    # purlin: skill_spec_from_code PROOF-4
    def test_it_stays_under_its_ceiling(self, monkeypatch):
        assert ceiling_problems() == []
        assert refusals(monkeypatch, ceiling_problems, [
            (SKILL, padded_to(131), '%s is 131 lines, ceiling 130' % SKILL),
        ]) == []

    # purlin: skill_spec_from_code PROOF-141
    def test_a_skill_of_exactly_130_lines_is_accepted(self, monkeypatch):
        assert on_copy(monkeypatch, SKILL, padded_to(130),
                       ceiling_problems) == []



# ---------------------------------------------------------------------------
# RULE-6: a test that already shows the proof gets the marker, not a new test
# ---------------------------------------------------------------------------

OFFER = 'offer to add the marker comment above that test'
MARKER = 'purlin: <feature> PROOF-<n>'
NO_NEW_TEST = 'write no new test'


def spec_from_code_marker_problems():
    problems = carries(SKILL, [OFFER, MARKER, NO_NEW_TEST])
    # The offer belongs to the case of a test that already shows the proof.
    paragraphs = [flat(p) for p in read(SKILL).split('\n\n')]
    if not any('already shows what a proof asks' in p and OFFER in p
               and MARKER in p and NO_NEW_TEST in p for p in paragraphs):
        problems.append('%s does not offer the marker, and write no new '
                        'test, in the paragraph on a test that already shows '
                        'the proof' % SKILL)
    return problems


class TestAnExistingTestIsTied:

    # purlin: skill_spec_from_code PROOF-6
    def test_it_offers_the_marker_and_writes_no_new_test(self, monkeypatch):
        assert spec_from_code_marker_problems() == []
        assert refusals(monkeypatch, spec_from_code_marker_problems, [
            (SKILL, replace('never names the test. Then tie the two:',
                            'never names the test.\n\nThen tie the two:'),
             '%s does not offer the marker, and write no new test, in the '
             'paragraph on a test that already shows the proof' % SKILL),
            (SKILL, resub(r',\s+and write no new test'),
             "%s does not carry 'write no new test'" % SKILL),
        ]) == []



# ---------------------------------------------------------------------------
# RULE-7: every source file gets a rule, and the report lists those that did not
# ---------------------------------------------------------------------------

def spec_from_code_files_problems():
    return sentence_with(SKILL, [
        'Give every source file a rule where you can',
        'end the report by listing the source files that got none',
        'for a person or an agent to decide'])


class TestEverySourceFile:

    # purlin: skill_spec_from_code PROOF-7
    def test_the_report_ends_on_the_files_with_no_rule(self, monkeypatch):
        assert spec_from_code_files_problems() == []
        assert refusals(monkeypatch, spec_from_code_files_problems, [
            (SKILL, resub(r'end the report by listing the source files that '
                          r'got\s+none', 'end the report'),
             "%s has no sentence carrying all of 'Give every source file a "
             "rule where you can'" % SKILL),
        ]) == []



# ---------------------------------------------------------------------------
# RULE-8: the three reasons a test is left untied
# ---------------------------------------------------------------------------

def spec_from_code_untied_problems():
    return sentence_with(SKILL, [
        'A test is left untied for one of three reasons',
        'the report lists each such test with its reason',
        'it shows only part of what a rule needs',
        'it repeats a test already tied',
        'it tests code the project does not own'])


class TestUntiedTests:

    # purlin: skill_spec_from_code PROOF-8
    def test_a_test_is_left_untied_for_three_reasons(self, monkeypatch):
        assert spec_from_code_untied_problems() == []
        assert refusals(monkeypatch, spec_from_code_untied_problems, [
            (SKILL, resub(r', or it tests code the project\s+does not own'),
             "%s has no sentence carrying all of 'A test is left untied for "
             "one of three reasons'" % SKILL),
        ]) == []



# ---------------------------------------------------------------------------
# RULE-9: rules from what the tests expect, no test run first
# ---------------------------------------------------------------------------

EXPECTS = 'Every rule is written from what its test expects, passing or not'


def spec_from_code_expects_problems():
    return sentence_with(SKILL, [EXPECTS, 'no test is run first'])


class TestRulesFromWhatTheTestsExpect:

    # purlin: skill_spec_from_code PROOF-9
    def test_every_rule_is_written_from_what_its_test_expects(
            self, monkeypatch):
        assert spec_from_code_expects_problems() == []
        assert refusals(monkeypatch, spec_from_code_expects_problems, [
            (SKILL, resub(r', and\s+no test is run first'),
             "%s has no sentence carrying all of %r" % (SKILL, EXPECTS)),
            (SKILL, replace(', passing or not'),
             "%s has no sentence carrying all of %r" % (SKILL, EXPECTS)),
        ]) == []


# ---------------------------------------------------------------------------
# RULE-10: no rule for a private helper
# ---------------------------------------------------------------------------

PRIVATE_HELPER = ('Do not write a rule for a private helper.',
                  'Rules describe behaviour someone outside the module can see')


def private_helper_problems():
    return carries(SKILL, PRIVATE_HELPER)


class TestNoRuleForAPrivateHelper:

    # purlin: skill_spec_from_code PROOF-145
    def test_it_writes_no_rule_for_a_private_helper(self, monkeypatch):
        assert private_helper_problems() == []
        assert refusals(monkeypatch, private_helper_problems, [
            (SKILL, replace('Do not write a rule for a private helper. '),
             "%s does not carry %r" % (SKILL, PRIVATE_HELPER[0])),
        ]) == []
