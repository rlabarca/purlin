"""Text checks for the spec skill, `skills/spec/SKILL.md`.

Every rule of `specs/skills/skill_spec.md` is proved here, one case to a test:
the skill as it ships, with the broken copies of it that the check must refuse
as a second assertion. The readers and the broken-copy helpers this file
shares with the other skill test files are in `dev/skill_checks.py`; the
checks below read through this module's `read`, so a broken copy reaches them
too.
"""

import re

from skill_checks import (COMMAND_REF, carries, field, flat, frontmatter,
                          frontmatter_problems, on_copy, read, refusals,
                          replace, resub, section, sections, sentence_with,
                          skill_ceiling_problems, skill_path, swap_first,
                          table_rows)

SKILL = skill_path('spec')
GUIDE = 'references/spec_quality_guide.md'
OFFER = 'Spec saved: <name>. Next: purlin:build <name>'
PRINTING = ('Print each rule with its proofs under it and ask whether to '
            'change any')
SAVING = 'Save the spec when the person is satisfied'
NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL
DRAFTING = ('Draft every proof against `references/spec_quality_guide.md`, '
            '"Writing proofs"')


class TestSkillSpec:

    # purlin: skill_spec PROOF-1
    def test_the_skill_opens_with_its_name_and_a_one_line_description(
            self, monkeypatch):
        assert opening_problems() == []
        value = field(frontmatter(read(SKILL)), 'description')
        line = 'description: %s' % value
        assert refusals(monkeypatch, opening_problems, [
            (SKILL, replace('name: spec\n'),
             "%s frontmatter name is None, expected 'spec'" % SKILL),
            (SKILL, replace(line, 'description:'), NO_DESCRIPTION),
            (SKILL, replace(line, 'description:\n  ' + value),
             NO_DESCRIPTION),
            (SKILL, replace(line, 'description: |\n  ' + value),
             NO_DESCRIPTION),
            (SKILL, replace(line, line + '\n  and a second line'),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_spec PROOF-14
    def test_the_command_reference_has_a_row_for_the_command(
            self, monkeypatch):
        assert command_row_problems() == []
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:spec <name>`'))
        assert '`purlin:spec-from-code' in read(COMMAND_REF)
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:spec' % COMMAND_REF),
        ]) == []

    # purlin: skill_spec PROOF-2
    def test_a_new_rule_counts_from_the_highest_ever_held(self, monkeypatch):
        assert id_problems() == []
        assert refusals(monkeypatch, id_problems, [
            (SKILL, replace('the highest of `> Highest-Rule:` and every rule '
                            'number', 'the highest rule number'),
             '%s Ids section does not carry %r' % (SKILL, ALLOCATION[0])),
            (SKILL, replace('read with `git show origin/main:<spec>`',
                            'as fetched'),
             '%s Ids section does not carry %r' % (SKILL, ALLOCATION[1])),
            (SKILL, replace('5. Allocate ids as "Ids" below says',
                            '5. Allocate ids'),
             '%s procedure step 5 does not point at Ids' % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-42
    def test_it_writes_the_highest_rule_into_the_spec(self, monkeypatch):
        assert highest_rule_problems() == []
        assert refusals(monkeypatch, highest_rule_problems, [
            (SKILL, resub(r'Write that number into `> Highest-Rule:`, adding '
                          r'the line after\s+the spec\'s other `>` lines '
                          r'where\s+it is missing,', 'Keep it,'),
             '%s Ids section does not carry %r' % (SKILL, WRITES_HIGHEST)),
        ]) == []

    # purlin: skill_spec PROOF-43
    def test_it_reads_the_state_at_the_project_root(self, monkeypatch):
        assert root_problems() == []
        assert refusals(monkeypatch, root_problems, [
            (SKILL, resub(r' with `project_root` set to the project root, '
                          r'the top folder of the git\s+checkout,'),
             '%s procedure step 1 does not carry %r' % (SKILL, ROOT_CALL)),
        ]) == []

    # purlin: skill_spec PROOF-44
    def test_the_intake_table_says_what_to_do_with_each_input(
            self, monkeypatch):
        assert intake_problems() == []
        assert refusals(monkeypatch, intake_problems, [
            (SKILL, resub(r'^\| A screenshot \|.*?\n'),
             "%s intake table has no row for 'A screenshot'" % SKILL),
            (SKILL, replace('| Pasted acceptance criteria | One rule per '
                            'criterion |', '| Pasted acceptance criteria | |'),
             "%s intake table has no row for 'Pasted acceptance criteria'"
             % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-45
    def test_a_change_is_made_in_place_and_nothing_is_renumbered(
            self, monkeypatch):
        assert in_place_problems() == []
        assert refusals(monkeypatch, in_place_problems, [
            (SKILL, replace('Edit in place. Never renumber',
                            'Write it again from the top'),
             '%s intake table does not give an existing spec plus a change '
             "'Edit in place. Never renumber'" % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-46
    def test_after_a_merge_the_incoming_id_takes_the_next_number(
            self, monkeypatch):
        check = lambda: merge_problems(MERGE_IDS)  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('give the incoming one the next free number',
                            'renumber both'),
             '%s After a merge conflict does not carry %r'
             % (SKILL, MERGE_IDS[0])),
            (SKILL, resub(r'and move its test markers\s+and its signature '
                          r'filenames with it', 'and stop'),
             '%s After a merge conflict does not carry %r'
             % (SKILL, MERGE_IDS[1])),
        ]) == []

    # purlin: skill_spec PROOF-47
    def test_two_pins_resolve_to_the_newer(self, monkeypatch):
        check = lambda: merge_problems(MERGE_PINS)  # noqa: E731
        assert check() == []
        assert refusals(monkeypatch, check, [
            (SKILL, replace('resolve to the newer sha', 'resolve to the older '
                            'sha'),
             '%s After a merge conflict does not carry %r'
             % (SKILL, MERGE_PINS[0])),
        ]) == []

    # purlin: skill_spec PROOF-48
    def test_the_guide_lets_a_proof_name_a_library_s_public_names(
            self, monkeypatch):
        check = lambda: guide_section_problems(  # noqa: E731
            'Written for a person who cannot read code', LIBRARY)
        assert check() == []
        assert refusals(monkeypatch, check, [
            (GUIDE, resub(r'^Where the product is a library.*?names the '
                          r'line\."\n'),
             "%s section 'Written for a person who cannot read code' does "
             'not state %r' % (GUIDE, LIBRARY[0])),
            (GUIDE, replace('stays out.', 'may appear too.'),
             "%s section 'Written for a person who cannot read code' does "
             'not state %r' % (GUIDE, LIBRARY[1])),
        ]) == []

    # purlin: skill_spec PROOF-49
    def test_the_guide_lets_one_proof_name_a_list_of_like_inputs(
            self, monkeypatch):
        check = lambda: guide_section_problems(  # noqa: E731
            'One proof, one case', LIKE_INPUTS)
        assert check() == []
        assert refusals(monkeypatch, check, [
            (GUIDE, resub(r'^One proof may name a list.*?cases of their '
                          r'own\.\n'),
             "%s section 'One proof, one case' does not state %r"
             % (GUIDE, LIKE_INPUTS[0])),
        ]) == []

    # purlin: skill_spec PROOF-50
    def test_the_guide_s_stuck_row_names_the_runner_file(self, monkeypatch):
        assert stuck_row_problems() == []
        assert refusals(monkeypatch, stuck_row_problems, [
            (GUIDE, replace('whose runner file names that system',
                            'whose matrix covers it'),
             '%s has no stuck row for a system with no run' % GUIDE),
            (GUIDE, replace('`<System>: no run yet`', '`<os>: no run yet`'),
             '%s has no stuck row for a system with no run' % GUIDE),
        ]) == []

    # purlin: skill_spec PROOF-3
    def test_it_closes_by_naming_the_build(self, monkeypatch):
        assert offer_problems() == []
        assert refusals(monkeypatch, offer_problems, [
            (SKILL, replace(OFFER, 'Spec written. Shall I build it?'),
             '%s closing section does not carry the line %r' % (SKILL, OFFER)),
            (SKILL, replace('```\n%s\n```' % OFFER, OFFER),
             '%s closing section does not set the line %r in a fenced block'
             % (SKILL, OFFER)),
            (SKILL, replace(' and nothing after it'),
             '%s closing section does not say nothing follows the line'
             % SKILL),
            (SKILL, replace('Never start the build yourself', 'Then build it'),
             '%s closing section does not say it never starts the build'
             % SKILL),
            (SKILL, lambda text: text + '\n## Notes\n\nMore to say.\n',
             "%s closes with the section 'Notes', not 'When you are done'"
             % SKILL),
            (SKILL, replace('say what moved before the offer',
                            'say what moved after the offer'),
             '%s closing section does not put what moved before the line'
             % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-4
    def test_it_stays_under_its_ceiling(self, monkeypatch):
        assert skill_ceiling_problems('spec') == []
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('spec'), [
            (SKILL, lengthened_to(211), '%s is 211 lines, ceiling 210' % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-28
    def test_a_skill_of_exactly_210_lines_is_accepted(self, monkeypatch):
        assert on_copy(monkeypatch, SKILL, lengthened_to(210),
                       lambda: skill_ceiling_problems('spec')) == []

    # purlin: skill_spec PROOF-5
    def test_it_writes_the_scope_on_every_spec(self, monkeypatch):
        assert scope_problems() == []
        assert refusals(monkeypatch, scope_problems, [
            (SKILL, resub(r'^Write `> Scope:` on every spec you create:.*?'
                          r'for it\. '),
             "%s does not carry 'Write `> Scope:` on every spec you create'"
             % SKILL),
            (SKILL, replace('the files the requirement touches, or '),
             "%s has no sentence carrying all of 'Write `> Scope:` on every "
             "spec you create', 'the files the requirement touches'" % SKILL),
            (SKILL, replace('4. Write the metadata, `> Scope:` included,',
                            '4. Write the metadata,'),
             '%s procedure does not name > Scope: in the metadata step'
             % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-30
    def test_it_says_what_a_spec_naming_no_files_costs(self, monkeypatch):
        assert no_files_problems() == []
        assert refusals(monkeypatch, no_files_problems, [
            (SKILL, replace('at the gate `signed` its rules', 'its rules'),
             "%s has no sentence carrying all of 'A spec that names no "
             "files'" % SKILL),
            (SKILL, replace(', so no tag is written'),
             "%s has no sentence carrying all of 'A spec that names no "
             "files'" % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-6
    def test_it_prints_the_rules_and_asks_before_it_saves(self, monkeypatch):
        assert review_order_problems() == []
        assert refusals(monkeypatch, review_order_problems, [
            (SKILL, resub(r'^6\. Print each rule.*?(?=^7\. )'),
             '%s does not carry %r' % (SKILL, PRINTING)),
            (SKILL, swap_first(
                'Print each rule with its proofs under it and ask whether to '
                'change any. Change what the\n   person asks and print them '
                'again.',
                'Save the spec when the person is satisfied, commit it on its '
                'own, and name `purlin:build`\n   as the next step. This '
                'skill never starts building.'),
             '%s procedure saves the spec before it prints the rules' % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-36
    def test_it_drafts_every_proof_against_the_guideline(self, monkeypatch):
        assert drafting_problems() == []
        assert refusals(monkeypatch, drafting_problems, [
            (SKILL, replace('`references/spec_quality_guide.md`, "Writing '
                            'proofs", the one home', 'the guide, the one home'),
             '%s has no sentence carrying all of %r' % (SKILL, DRAFTING)),
        ]) == []

    # purlin: skill_spec PROOF-7
    def test_it_writes_each_proof_as_one_case(self, monkeypatch):
        assert one_case_problems() == []
        assert refusals(monkeypatch, one_case_problems, [
            (SKILL, resub(r', and a refusal or a boundary as a proof of its\s+'
                          r'own'),
             "%s has no sentence carrying all of 'Write each proof as one "
             "case'" % SKILL),
        ]) == []

    # purlin: skill_spec PROOF-40
    def test_the_guide_says_one_proof_one_case(self, monkeypatch):
        assert guide_one_case_problems() == []
        assert refusals(monkeypatch, guide_one_case_problems, [
            (GUIDE, resub(r'(^### One proof, one case\n.*?)at\s+most 60 '
                          r'words', r'\1briefly'),
             "%s section 'One proof, one case' does not state 'at most 60 "
             "words'" % GUIDE),
            (GUIDE, resub(r'(^### One proof, one case\n.*?)A refusal or a\s+'
                          r'boundary is a case of its own', r'\1It'),
             "%s section 'One proof, one case' does not state 'A refusal or "
             "a boundary is a case of its own'" % GUIDE),
        ]) == []


# ---------------------------------------------------------------------------
# The checks. Each returns the problems it found, empty when the file is right.
# ---------------------------------------------------------------------------

def opening_problems():
    """The skill's own frontmatter: its name and its one-line description."""
    return [p for p in frontmatter_problems('spec') if p.startswith(SKILL)]


def command_row_problems():
    """The command reference's row whose first cell is `purlin:spec <name>`."""
    return [p for p in frontmatter_problems('spec')
            if p.startswith(COMMAND_REF)]


ALLOCATION = (
    'A new rule takes one more than the highest of `> Highest-Rule:` and '
    'every rule number in either copy of the spec',
    "the working copy and `origin/main`'s, read with "
    '`git show origin/main:<spec>`.')
WRITES_HIGHEST = ('Write that number into `> Highest-Rule:`, adding the line '
                  "after the spec's other `>` lines where it is missing")
ROOT_CALL = ('Call `sync_status` with `project_root` set to the project root, '
             'the top folder of the git checkout')


def ids_body():
    return flat(section(read(SKILL), r'^ids$') or '')


def id_problems():
    problems = ['%s Ids section does not carry %r' % (SKILL, needle)
                for needle in ALLOCATION if needle not in ids_body()]
    if not re.search(r'^5\. Allocate ids as "Ids" below says, never against '
                     r'the working tree alone\.$', read(SKILL), re.M):
        problems.append('%s procedure step 5 does not point at Ids' % SKILL)
    return problems


def highest_rule_problems():
    if WRITES_HIGHEST in ids_body():
        return []
    return ['%s Ids section does not carry %r' % (SKILL, WRITES_HIGHEST)]


def root_problems():
    step = re.search(r'^1\. (.*?)(?=^2\. )', read(SKILL), re.S | re.M)
    if step and ROOT_CALL in flat(step.group(1)):
        return []
    return ['%s procedure step 1 does not carry %r' % (SKILL, ROOT_CALL)]


INPUTS = ('One sentence', 'A product description or a ticket',
          'Pasted acceptance criteria', 'A screenshot')


def intake_rows():
    return {cells[0]: cells[1] for cells in
            table_rows(read(SKILL), '| What you are given | What you do |')
            if len(cells) > 1}


def intake_problems():
    rows = intake_rows()
    return ['%s intake table has no row for %r' % (SKILL, name)
            for name in INPUTS if not rows.get(name)]


def in_place_problems():
    if intake_rows().get('An existing spec plus a change') == \
            'Edit in place. Never renumber':
        return []
    return ['%s intake table does not give an existing spec plus a change '
            "'Edit in place. Never renumber'" % SKILL]


MERGE_IDS = ('Keep both rules, give the incoming one the next free number',
             'and move its test markers and its signature filenames with it.')
MERGE_PINS = ('Two branches that advanced the same anchor pin resolve to the '
              'newer sha.',)


def merge_problems(needles):
    body = flat(section(read(SKILL), r'^after a merge conflict$') or '')
    return ['%s After a merge conflict does not carry %r' % (SKILL, needle)
            for needle in needles if needle not in body]


LIBRARY = (
    'Where the product is a library, its public names are what a caller '
    'sees: a proof may name a function or class the library exports and an '
    'error type a caller gets back.',
    'A name from inside the code, a private helper or a module the package '
    'does not export, stays out.',
    '- Poor: "`_split_fields` returns three parts for a line with two '
    'commas."',
    '- Good: "`parse_line` given `a,b` raises `LineTooShort`, and its message '
    'names the line."')
LIKE_INPUTS = (
    'One proof may name a list of like inputs that share one action and one '
    'kind of result: "Each of `0`, `-1` and `-0.5` is refused with `Amount '
    'must be positive`."',
    'Inputs that differ in what is done, or in the kind of result seen, are '
    'cases of their own.')


def guide_section_problems(heading, needles):
    body = re.search(r'^### %s\n(.*?)(?=^#)' % re.escape(heading),
                     read(GUIDE), re.S | re.M)
    text = flat(body.group(1)) if body else ''
    return ['%s section %r does not state %r' % (GUIDE, heading, needle)
            for needle in needles if needle not in text]


STUCK_ROW = ('| passed | `not run`, with `<System>: no run yet` |',
             '| Run `purlin:test --remote`, whose runner file names that '
             'system, or drop the `@env` tag if any operating system could '
             'show it. |')


def stuck_row_problems():
    if any(line.startswith(STUCK_ROW[0]) and line.endswith(STUCK_ROW[1])
           for line in read(GUIDE).splitlines()):
        return []
    return ['%s has no stuck row for a system with no run' % GUIDE]


def offer_problems():
    heading, body = sections(read(SKILL))[-1]
    problems = []
    if heading.strip() != 'When you are done':
        problems.append("%s closes with the section %r, not 'When you are "
                        "done'" % (SKILL, heading.strip()))
    if OFFER not in body.splitlines():
        problems.append('%s closing section does not carry the line %r on its '
                        'own' % (SKILL, OFFER))
    fences = re.findall(r'^```[a-z]*\n(.*?)^```', body, re.S | re.M)
    if not any(OFFER in fence.splitlines() for fence in fences):
        problems.append('%s closing section does not set the line %r in a '
                        'fenced block' % (SKILL, OFFER))
    if 'end with exactly this and nothing after it' not in flat(body):
        problems.append('%s closing section does not say nothing follows the '
                        'line' % SKILL)
    if 'Never start the build yourself' not in flat(body):
        problems.append('%s closing section does not say it never starts '
                        'the build' % SKILL)
    if 'say what moved before the offer' not in flat(body):
        problems.append('%s closing section does not put what moved before '
                        'the line' % SKILL)
    return problems


def lengthened_to(count):
    """An edit that pads the skill with lines of prose to `count` lines."""
    def edit(text):
        missing = count - len(text.splitlines())
        assert missing > 0, 'the skill is already %d lines' % (count - missing)
        padded = text + 'More prose.\n' * missing
        assert len(padded.splitlines()) == count
        return padded
    return edit


def scope_problems():
    problems = carries(SKILL, ['Write `> Scope:` on every spec you create'])
    problems += sentence_with(SKILL, [
        'Write `> Scope:` on every spec you create',
        'the files the requirement touches',
        'the paths `purlin:build` will create'])
    step = re.search(r'^\d+\. Write the metadata.*$', read(SKILL), re.M)
    if step is None or '`> Scope:`' not in step.group(0):
        problems.append('%s procedure does not name > Scope: in the '
                        'metadata step' % SKILL)
    return problems


def no_files_problems():
    return sentence_with(SKILL, [
        'A spec that names no files', 'every run includes it',
        'at the gate `signed` its rules are signed and their signatures do '
        'not count, so no tag is written'])


def review_order_problems():
    problems = carries(SKILL, [PRINTING, SAVING])
    body = next((body for heading, body in sections(read(SKILL))
                 if heading.strip() == 'Procedure'), '')
    steps = [flat(item) for item in re.split(r'^\d+\. ', body, flags=re.M)[1:]]
    at = {needle: next((n for n, step in enumerate(steps) if needle in step),
                       None) for needle in (PRINTING, SAVING)}
    if None in at.values():
        problems.append('%s procedure does not hold both the print step and '
                        'the save step' % SKILL)
    elif at[PRINTING] > at[SAVING]:
        problems.append('%s procedure saves the spec before it prints the '
                        'rules' % SKILL)
    return problems


def drafting_problems():
    return sentence_with(SKILL, [DRAFTING, 'at least one failure case'])


def one_case_problems():
    return sentence_with(SKILL, [
        'Write each proof as one case',
        'one starting situation and one action', 'in at most 60 words',
        'a refusal or a boundary as a proof of its own',
        '"One proof, one case"'])


def guide_one_case_problems():
    body = re.search(r'^### One proof, one case\n(.*?)(?=^#)', read(GUIDE),
                     re.S | re.M)
    if body is None:
        return ["%s has no section 'One proof, one case'" % GUIDE]
    return ["%s section 'One proof, one case' does not state %r"
            % (GUIDE, needle)
            for needle in ('one starting situation, one action',
                           'at most 60 words',
                           'A refusal or a boundary is a case of its own')
            if needle not in flat(body.group(1))]


# purlin: skill_spec PROOF-52
def test_a_new_proof_counts_from_the_highest_ever_held():
    ids = ids_body()
    assert ('A new proof takes one more than the highest of '
            '`> Highest-Proof:` and every proof number in either copy') \
        in ids, ids


# purlin: skill_spec PROOF-53
def test_it_writes_the_highest_proof_into_the_spec():
    ids = ids_body()
    assert ('write that number into `> Highest-Proof:`, adding the line '
            'after `> Highest-Rule:` where it is missing') in ids, ids


# purlin: skill_spec PROOF-51
def test_the_spec_is_committed_before_the_closing_line():
    done = flat(section(read(SKILL), r'^When you are done$') or '')
    commit = done.find('commit it with the `spec(<name>):` prefix')
    closing = done.find('Spec saved: <name>. Next: purlin:build <name>')
    assert 0 <= commit < closing, done
