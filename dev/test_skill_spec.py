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
                          replace, resub, sections, sentence_with,
                          skill_ceiling_problems, skill_path, swap_first)

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
    def test_it_allocates_ids_against_the_default_branch(self, monkeypatch):
        assert id_problems() == []
        assert refusals(monkeypatch, id_problems, [
            (SKILL, resub(r'^```bash\ngit show origin/main:.*?^```\n'),
             "%s does not carry 'git show origin/main:'" % SKILL),
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
            (SKILL, replace(' and no tag is written'),
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


def id_problems():
    return carries(SKILL, [
        'git show origin/main:',
        'allocated against `origin/main`, not against the working tree',
        'one past the highest in either copy of the spec'])


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
        'at the gate `signed` its rules cannot be signed and no tag is '
        'written'])


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
