"""Text checks for the spec-from-code skill, `skills/spec-from-code/SKILL.md`.

Every rule of `specs/skills/skill_spec_from_code.md` is proved here, one
case to a test, and each test also points its check at copies of the skill
with one thing broken, which the check must refuse. The readers, the checks and the broken copies this file shares
with the other skill test files are in `dev/skill_checks.py`; the checks that
belong to this skill alone, and the broken copies each test makes, are below.
"""

import re

from skill_checks import (COMMAND_REF, carries, field, flat, frontmatter,
                          frontmatter_problems, on_copy, read, refusals,
                          replace, resub, section, sections, sentence_with,
                          skill_ceiling_problems, skill_path, swap_first,
                          table_rows)

NAME = 'spec-from-code'
SKILL = skill_path(NAME)
CONVENTIONS = 'references/commit_conventions.md'


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
# RULE-2 and RULE-35: the section before the procedure
# ---------------------------------------------------------------------------

ROOT_CALL = ('Call `sync_status` with `project_root` set to the project root, '
             'the top folder of the git checkout.')
INIT_FIRST = ('When the project has no `.purlin/config.json`, run '
              '`purlin:init` first.')
BRANCH = ('Run `git branch --show-current`; when it prints nothing the '
          'checkout is on no branch, so make one with `git switch -c <name>` '
          'before the first commit.')


def start_body():
    return flat(section(read(SKILL), r'^before you start$') or '')


def spec_from_code_start_problems():
    if section(read(SKILL), r'^before you start$') is None:
        return ['%s has no section that runs before the survey' % SKILL]
    problems = ['%s start section does not carry %r' % (SKILL, needle)
                for needle in (ROOT_CALL, INIT_FIRST)
                if needle not in start_body()]
    headings = [heading for heading, _ in sections(read(SKILL))]
    if 'Procedure' not in headings or \
            headings.index('Before you start') > headings.index('Procedure'):
        problems.append('%s start section comes after the Procedure section'
                        % SKILL)
    return problems


def start_section():
    return re.search(r'^## Before you start\n.*?(?=^## )', read(SKILL),
                     re.S | re.M).group(0)


def branch_problems():
    if BRANCH in start_body():
        return []
    return ['%s start section does not carry %r' % (SKILL, BRANCH)]


class TestBeforeYouStart:

    # purlin: skill_spec_from_code PROOF-2
    def test_it_passes_the_project_root_and_sends_a_bare_project_to_init(
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
            (SKILL, resub(r'Call `sync_status` with `project_root` set to the '
                          r'project root,\s+the top folder of the git\s+'
                          r'checkout\.', 'Call `sync_status`.'),
             '%s start section does not carry %r' % (SKILL, ROOT_CALL)),
            (SKILL, replace('When the project has no `.purlin/config.json`, '
                            'run `purlin:init` first.',
                            'Read `.purlin/config.json`.'),
             '%s start section does not carry %r' % (SKILL, INIT_FIRST)),
        ]) == []

    # purlin: skill_spec_from_code PROOF-150
    def test_it_makes_a_branch_on_a_detached_head_before_the_first_commit(
            self, monkeypatch):
        assert branch_problems() == []
        assert refusals(monkeypatch, branch_problems, [
            (SKILL, resub(r' Run\s+`git branch --show-current`;.*?first '
                          r'commit\.'),
             '%s start section does not carry %r' % (SKILL, BRANCH)),
            (SKILL, replace('`git switch -c <name>`', '`git checkout <tag>`'),
             '%s start section does not carry %r' % (SKILL, BRANCH)),
        ]) == []


# ---------------------------------------------------------------------------
# RULE-3: the closing section names the first of three next steps
# ---------------------------------------------------------------------------

FIRST_THAT_APPLIES = ('Report the counts, then name the first of these that '
                      'applies:')
ENDINGS = (
    ('1', 'Rules whose existing tests now carry their comments: '
          '`→ Run: purlin:test`'),
    ('2', 'Rules with no test at all: `→ Run: purlin:build <name>`'),
    ('3', 'At the gate `passed`, with every rule passing and the team '
          'wanting the paper trail: `→ Run: purlin:init --gate strong`'),
)


def closing_problems():
    heading, body = sections(read(SKILL))[-1]
    if heading.strip() != 'When you are done':
        return ["%s closes with the section %r, not 'When you are done'"
                % (SKILL, heading.strip())]
    problems = []
    if FIRST_THAT_APPLIES not in flat(body):
        problems.append('%s closing section does not say to name the first '
                        'step that applies' % SKILL)
    items = [flat(item).strip() for item in
             re.split(r'^(?=\d+\. )', body, flags=re.M)[1:]]
    found = [(item.split('. ', 1)[0], item.split('. ', 1)[1])
             for item in items]
    for number, text in ENDINGS:
        if not any(n == number and item.startswith(text)
                   for n, item in found):
            problems.append('%s closing section has no step %s. %s'
                            % (SKILL, number, text))
    return problems


class TestWhenYouAreDone:

    # purlin: skill_spec_from_code PROOF-3
    def test_it_names_the_first_of_three_next_steps_that_applies(
            self, monkeypatch):
        assert closing_problems() == []
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, lambda t: t[:t.rindex('\n## ') + 1],
             "%s closes with the section 'What not to do'" % SKILL),
            (SKILL, replace('name the first of these that applies:',
                            'name the next step from the state:'),
             '%s closing section does not say to name the first step that '
             'applies' % SKILL),
            (SKILL, swap_first('1. Rules whose', '2. Rules with'),
             '%s closing section has no step 1. %s' % (SKILL, ENDINGS[0][1])),
            (SKILL, replace('3. At the gate `passed`, with', '3. With'),
             '%s closing section has no step 3. %s' % (SKILL, ENDINGS[2][1])),
            (SKILL, replace('`→ Run: purlin:build <name>`',
                            '`purlin:build <name>`'),
             '%s closing section has no step 2. %s' % (SKILL, ENDINGS[1][1])),
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
# The procedure: RULE-40 to RULE-43, RULE-37, RULE-34, RULE-33, RULE-36, RULE-7
# ---------------------------------------------------------------------------

def steps():
    """`{number: step text}` of the procedure, line wrapping collapsed."""
    body = section(read(SKILL), r'^procedure$') or ''
    found = {}
    for item in re.split(r'^(?=\d+\. )', body, flags=re.M)[1:]:
        number, text = flat(item).strip().split('. ', 1)
        found[number] = text
    return found


def step_problems(number, needles):
    text = steps().get(number)
    if text is None:
        return ['%s procedure has no step %s' % (SKILL, number)]
    return ['%s step %s does not carry %r' % (SKILL, number, needle)
            for needle in needles if needle not in text]


SURVEY = ('**Survey.** Walk the tree once.',
          'Note the entry points, the modules with real branching, the '
          'configuration surface, and the test files.',
          'Ignore generated code, vendored dependencies and build output.')
TAXONOMY = ('**Propose a taxonomy.** Group the behaviour into features',
            'print the list with a one-line description and the files each '
            'would carry in `> Scope:`')
STOP = ('Show the list and stop.',
        'Merge, split and rename until they say it is right.')
ORDER = ('**Write one spec at a time**, in that order',)
ANCHOR = ('**Order by dependency.** Where features share rules, write those '
          'rules once in an anchor with `purlin:anchor create <name>`, first, '
          'and have each feature name it with `> Requires: <name>`.',
          '`> Requires:` names anchors only.')
COMMIT = ('committing each spec with the comments it adds above existing '
          'tests, on its own, with the `spec(<name>):` prefix',)
POSITION = ('After each commit write `.purlin/runtime/spec-from-code.json`, '
            '`{"features": [<the agreed list, in order>], "written": [<each '
            'feature committed so far>]}`;',
            'a session that finds it goes on with the first feature not in '
            '`written`.')
PER_FEATURE = ('Print one line per feature: its rules, its proofs, how many '
               'proofs an existing test already shows, and how many have no '
               'test.',)
NO_RULE_LAST = ('and last the source files that got no rule, for a person or '
                'an agent to decide.',)


class TestTheProcedure:

    # purlin: skill_spec_from_code PROOF-155
    def test_the_survey_walks_the_tree_once(self, monkeypatch):
        assert step_problems('1', SURVEY) == []
        assert refusals(monkeypatch, lambda: step_problems('1', SURVEY), [
            (SKILL, replace('Walk the tree once.', 'Read every file.'),
             '%s step 1 does not carry %r' % (SKILL, SURVEY[0])),
            (SKILL, resub(r' Ignore generated code,.*?build output\.'),
             '%s step 1 does not carry %r' % (SKILL, SURVEY[2])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-156
    def test_the_taxonomy_lists_each_feature_with_its_files(
            self, monkeypatch):
        assert step_problems('2', TAXONOMY) == []
        assert refusals(monkeypatch, lambda: step_problems('2', TAXONOMY), [
            (SKILL, resub(r' and the files each\s+would carry in '
                          r'`> Scope:`'),
             '%s step 2 does not carry %r' % (SKILL, TAXONOMY[1])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-157
    def test_it_stops_on_the_list_until_the_person_agrees(self, monkeypatch):
        assert step_problems('3', STOP) == []
        assert refusals(monkeypatch, lambda: step_problems('3', STOP), [
            (SKILL, replace('Show the list and stop.', 'Show the list.'),
             '%s step 3 does not carry %r' % (SKILL, STOP[0])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-158
    def test_it_writes_one_spec_at_a_time_in_the_dependency_order(
            self, monkeypatch):
        def check():
            problems = step_problems('5', ORDER)
            if not steps().get('4', '').startswith('**Order by dependency.**'):
                problems.append('%s step 4 is not the dependency order'
                                % SKILL)
            return problems
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace(', in that order,', ','),
             '%s step 5 does not carry %r' % (SKILL, ORDER[0])),
            (SKILL, replace('**Order by dependency.**', '**Share rules.**'),
             '%s step 4 is not the dependency order' % SKILL),
        ]) == []

    # purlin: skill_spec_from_code PROOF-152
    def test_shared_rules_go_once_into_an_anchor_that_features_require(
            self, monkeypatch):
        assert step_problems('4', ANCHOR) == []
        assert refusals(monkeypatch, lambda: step_problems('4', ANCHOR), [
            (SKILL, resub(r' `> Requires:` names anchors only\.'),
             '%s step 4 does not carry %r' % (SKILL, ANCHOR[1])),
            (SKILL, resub(r'write those rules once in an anchor\s+with '
                          r'`purlin:anchor create <name>`, first,',
                          'write those features first,'),
             '%s step 4 does not carry %r' % (SKILL, ANCHOR[0])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-148
    def test_each_spec_is_committed_with_the_comments_it_adds(
            self, monkeypatch):
        assert step_problems('5', COMMIT) == []
        assert refusals(monkeypatch, lambda: step_problems('5', COMMIT), [
            (SKILL, replace('committing each spec with the comments it adds\n'
                            '   above existing tests, on its own,',
                            'committing each spec on its own,'),
             '%s step 5 does not carry %r' % (SKILL, COMMIT[0])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-147
    def test_the_position_file_holds_the_list_and_what_is_written(
            self, monkeypatch):
        assert step_problems('5', POSITION) == []
        assert refusals(monkeypatch, lambda: step_problems('5', POSITION), [
            (SKILL, replace('"written": [<each feature committed so far>]',
                            '"next": <feature>'),
             '%s step 5 does not carry %r' % (SKILL, POSITION[0])),
            (SKILL, resub(r';\s+a session that finds it goes on with the '
                          r'first feature not in `written`\.', '.'),
             '%s step 5 does not carry %r' % (SKILL, POSITION[1])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-151
    def test_the_report_gives_one_line_per_feature(self, monkeypatch):
        assert step_problems('6', PER_FEATURE) == []
        assert refusals(monkeypatch, lambda: step_problems('6', PER_FEATURE), [
            (SKILL, replace('Print one line per feature:',
                            'Print every proof beside its test and, per '
                            'feature:'),
             '%s step 6 does not carry %r' % (SKILL, PER_FEATURE[0])),
            (SKILL, resub(r', and how many\s+have no test\.', '.'),
             '%s step 6 does not carry %r' % (SKILL, PER_FEATURE[0])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-7
    def test_the_report_ends_on_the_files_with_no_rule(self, monkeypatch):
        def check():
            problems = step_problems('6', NO_RULE_LAST)
            if not steps().get('6', '').endswith(NO_RULE_LAST[0]):
                problems.append('%s step 6 does not end on the files with no '
                                'rule' % SKILL)
            return problems
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, resub(r'\s+and last the source files that got no rule, '
                          r'for a person or an agent to decide\.', '.'),
             '%s step 6 does not carry %r' % (SKILL, NO_RULE_LAST[0])),
            (SKILL, replace('for a person or an agent to decide.',
                            'for a person or an agent to decide. Then the '
                            'counts.'),
             '%s step 6 does not end on the files with no rule' % SKILL),
        ]) == []

    # purlin: skill_spec_from_code PROOF-149
    def test_the_conventions_put_the_comments_in_the_spec_commit(
            self, monkeypatch):
        cell = ('Creating or editing a spec or an anchor\'s local rules; from '
                '`purlin:spec-from-code`, with the comments it adds above the '
                'project\'s existing tests')

        def check():
            rows = {cells[0]: cells[1] for cells in
                    table_rows(read(CONVENTIONS), '| Prefix | When |')}
            if rows.get('`spec(<name>):`') == cell:
                return []
            return ['%s spec(<name>): row reads %r'
                    % (CONVENTIONS, rows.get('`spec(<name>):`'))]
        assert check() == []
        assert refusals(monkeypatch, check, [
            (CONVENTIONS, replace('; from `purlin:spec-from-code`, with the '
                                  'comments it adds above the project\'s '
                                  'existing tests'),
             '%s spec(<name>): row reads' % CONVENTIONS),
        ]) == []


# ---------------------------------------------------------------------------
# RULE-8 and RULE-38: the tests left untied, and what is not a test
# ---------------------------------------------------------------------------

def spec_from_code_untied_problems():
    return sentence_with(SKILL, [
        'A test is left untied for one of five reasons',
        'the report lists each such test with its reason',
        'it shows only part of what a rule needs',
        'it repeats a test already tied',
        'it tests code the project does not own',
        'it cannot carry a comment',
        'or it tests code no caller can reach'])


NOT_A_TEST = ('A test that is commented out, or a benchmark the project\'s '
              'test command does not run, is not a test: leave it and count '
              'it nowhere.')


class TestUntiedTests:

    # purlin: skill_spec_from_code PROOF-8
    def test_a_test_is_left_untied_for_five_reasons(self, monkeypatch):
        assert spec_from_code_untied_problems() == []
        assert refusals(monkeypatch, spec_from_code_untied_problems, [
            (SKILL, resub(r', it cannot carry a comment\s+\(an example '
                          r'inside a function\'s documentation\)'),
             "%s has no sentence carrying all of 'A test is left untied for "
             "one of five reasons'" % SKILL),
            (SKILL, resub(r', or it tests code no caller can reach\.', '.'),
             "%s has no sentence carrying all of 'A test is left untied for "
             "one of five reasons'" % SKILL),
        ]) == []

    # purlin: skill_spec_from_code PROOF-153
    def test_a_commented_out_test_or_a_benchmark_is_not_a_test(
            self, monkeypatch):
        assert sentence_with(SKILL, [NOT_A_TEST]) == []
        assert refusals(monkeypatch, lambda: sentence_with(SKILL, [NOT_A_TEST]),
                        [(SKILL, resub(r'count it\s+nowhere', 'tie it'),
                          '%s has no sentence carrying all of %r'
                          % (SKILL, NOT_A_TEST))]) == []


# ---------------------------------------------------------------------------
# RULE-9 and RULE-44: rules from what the tests expect, each one a draft
# ---------------------------------------------------------------------------

EXPECTS = 'Every rule is written from what its test expects, passing or not'
DRAFT = ('so every rule this skill writes is a draft until a person reads it. '
         'Say so when you hand the result over.')


def spec_from_code_expects_problems():
    return sentence_with(SKILL, [EXPECTS, 'no test is run first'])


def draft_problems():
    return carries(SKILL, [DRAFT])


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

    # purlin: skill_spec_from_code PROOF-159
    def test_it_says_at_hand_over_that_every_rule_is_a_draft(
            self, monkeypatch):
        assert draft_problems() == []
        assert refusals(monkeypatch, draft_problems, [
            (SKILL, replace(' Say so when you hand the result over.'),
             '%s does not carry %r' % (SKILL, DRAFT)),
        ]) == []


# ---------------------------------------------------------------------------
# What not to do: RULE-10, RULE-48, RULE-45, RULE-46; RULE-47
# ---------------------------------------------------------------------------

UNREACHED = ('- Do not write a rule for code no caller outside the project can '
             'reach: list its files among the files with no rule.')
REACHED = ('A caller reaches what the package exports:',
           "in Python, the names a module's `__all__` lists, or with no "
           '`__all__` the names with no leading underscore in a module whose '
           'own name has none;',
           "in JavaScript, what `package.json`'s `main` or `exports` reaches;",
           'in C#, the `public` types of a project that is not a test '
           'project.')
IMPLEMENTATION = '- Do not copy an implementation into a rule.'
NO_EVIDENCE = '- Do not write evidence or signatures.'
DESCRIPTION = ('Drop the rule instead and note the behaviour in '
               '`> Description:`.')


def not_to_do_problems(needles):
    body = flat(section(read(SKILL), r'^what not to do$') or '')
    return ['%s What not to do does not carry %r' % (SKILL, needle)
            for needle in needles if needle not in body]


class TestWhatNotToDo:

    # purlin: skill_spec_from_code PROOF-145
    def test_code_no_caller_can_reach_gets_no_rule(self, monkeypatch):
        assert not_to_do_problems([UNREACHED]) == []
        assert refusals(monkeypatch, lambda: not_to_do_problems([UNREACHED]), [
            (SKILL, resub(r': list its files among\s+the files with no rule\.',
                          '.'),
             '%s What not to do does not carry %r' % (SKILL, UNREACHED)),
            (SKILL, replace('code no caller outside the project can',
                            'a private helper someone can'),
             '%s What not to do does not carry %r' % (SKILL, UNREACHED)),
        ]) == []

    # purlin: skill_spec_from_code PROOF-146
    def test_it_says_what_a_caller_reaches_in_each_language(
            self, monkeypatch):
        assert not_to_do_problems(REACHED) == []
        assert refusals(monkeypatch, lambda: not_to_do_problems(REACHED), [
            (SKILL, replace("`__all__` lists, or with no `__all__`",
                            'names, or with none'),
             '%s What not to do does not carry %r' % (SKILL, REACHED[1])),
            (SKILL, resub(r'in JavaScript, what .*?reaches;\s+'),
             '%s What not to do does not carry %r' % (SKILL, REACHED[2])),
            (SKILL, replace(' that is not a test project'),
             '%s What not to do does not carry %r' % (SKILL, REACHED[3])),
        ]) == []

    # purlin: skill_spec_from_code PROOF-160
    def test_no_implementation_is_copied_into_a_rule(self, monkeypatch):
        check = lambda: not_to_do_problems([IMPLEMENTATION])  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('Do not copy an implementation into a rule.',
                            'Name the implementation in a rule.'),
             '%s What not to do does not carry %r' % (SKILL, IMPLEMENTATION)),
        ]) == []

    # purlin: skill_spec_from_code PROOF-161
    def test_it_writes_no_evidence_and_no_signature(self, monkeypatch):
        check = lambda: not_to_do_problems([NO_EVIDENCE])  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('Do not write evidence or signatures.',
                            'Write the evidence.'),
             '%s What not to do does not carry %r' % (SKILL, NO_EVIDENCE)),
        ]) == []

    # purlin: skill_spec_from_code PROOF-162
    def test_an_unobservable_behaviour_goes_to_the_description(
            self, monkeypatch):
        assert carries(SKILL, [DESCRIPTION]) == []
        assert refusals(monkeypatch, lambda: carries(SKILL, [DESCRIPTION]), [
            (SKILL, resub(r'\s+and note\s+the behaviour in `> Description:`'),
             '%s does not carry %r' % (SKILL, DESCRIPTION)),
        ]) == []


# ---------------------------------------------------------------------------
# RULE-39: the spec it writes carries > Highest-Rule:
# ---------------------------------------------------------------------------

def highest_rule_problems():
    # The example's own `## Rules` heading splits the skill's sections, so
    # the fence is read from the whole file.
    fences = re.findall(r'^```markdown\n(.*?)^```', read(SKILL), re.S | re.M)
    if not fences:
        return ['%s shows no spec' % SKILL]
    lines = fences[0].splitlines()
    meta = [n for n, line in enumerate(lines) if line.startswith('> ')]
    rules = [int(n) for n in re.findall(r'^- RULE-(\d+):', fences[0], re.M)]
    if '> Highest-Rule: %d' % max(rules or [0]) not in lines:
        return ['%s example spec carries no > Highest-Rule: %d'
                % (SKILL, max(rules or [0]))]
    if not lines[meta[-1]].startswith('> Highest-Rule: '):
        return ['%s example spec puts > Highest-Rule: before another > line'
                % SKILL]
    return []


class TestHighestRule:

    # purlin: skill_spec_from_code PROOF-154
    def test_the_spec_it_writes_carries_its_highest_rule(self, monkeypatch):
        assert highest_rule_problems() == []
        assert refusals(monkeypatch, highest_rule_problems, [
            (SKILL, replace('> Highest-Rule: 2\n'),
             '%s example spec carries no > Highest-Rule: 2' % SKILL),
            (SKILL, replace('> Highest-Rule: 2', '> Highest-Rule: 1'),
             '%s example spec carries no > Highest-Rule: 2' % SKILL),
            (SKILL, swap_first('> Scope: src/middleware/rate_limit.py',
                               '> Highest-Rule: 2'),
             '%s example spec puts > Highest-Rule: before another > line'
             % SKILL),
        ]) == []


def step_two(text):
    """Step 2 of the procedure, from its bold title to step 3, line breaks
    read as spaces."""
    match = re.search(r'2\. \*\*Propose a taxonomy\.\*\*(.*?)\n3\. ', text,
                      re.S)
    return flat(match.group(1)) if match else ''


def where_the_proofs_come_from():
    return flat(section(read(SKILL), r'^Where the proofs come from$') or '')


# purlin: skill_spec_from_code PROOF-163
def test_the_taxonomy_step_says_how_many_features_is_normal():
    assert ('Twenty to forty features is normal for a mid-sized service; two '
            'hundred means the grouping is too fine.') in step_two(read(SKILL))


# purlin: skill_spec_from_code PROOF-164
def test_a_proof_a_test_already_shows_never_names_the_test():
    body = where_the_proofs_come_from()
    assert ('When a test already shows what a proof asks, the proof says what '
            'that test shows') in body, body
    assert 'and never names the test.' in body, body


# purlin: skill_spec_from_code PROOF-165
def test_the_suites_own_helpers_are_code_no_caller_reaches():
    assert ("A test of the test suite's own helpers tests code no caller can "
            'reach.') in where_the_proofs_come_from()
