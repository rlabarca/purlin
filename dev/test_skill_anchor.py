"""Text checks for the anchor skill, `skills/anchor/SKILL.md`.

Every rule of `specs/skills/skill_anchor.md` is proved here, one test per
proof. A refusal is shown by pointing a check at a copy of a file with one
thing broken; the file on disk is never touched. The readers, the shared
checks and the broken-copy helpers are in `dev/skill_checks.py`; the checks
only the anchor skill needs are at the foot of this file.
"""

import re

from skill_checks import (COMMAND_REF, carries, field, flat, frontmatter,
                          frontmatter_problems, next_step_problems, on_copy,
                          read, refusals, replace, same_line, section,
                          sections, skill_ceiling_problems, skill_path,
                          undirected_outcome_problems)

REL = skill_path('anchor')
SCRIPT = '"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"'


def refused(monkeypatch, check, edit, expected, rel=REL):
    """The problems `check` missed on a copy of `rel` broken by `edit`:
    empty when the copy is refused with `expected`."""
    return refusals(monkeypatch, check, [(rel, edit, expected)])


class TestFrontmatter:
    """RULE-1: the frontmatter names the skill and the command reference
    carries its row."""

    # purlin: skill_anchor PROOF-1
    def test_the_skill_opens_with_its_name_and_a_one_line_description(self):
        assert skill_frontmatter_problems() == []

    # purlin: skill_anchor PROOF-9
    def test_the_command_reference_has_a_row_for_the_command(self):
        assert command_row_problems() == []

    # purlin: skill_anchor PROOF-10
    def test_a_skill_with_no_name_line_fails(self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace('name: anchor\n'),
                       "%s frontmatter name is None, expected 'anchor'"
                       % REL) == []

    # purlin: skill_anchor PROOF-11
    def test_an_empty_description_fails(self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(), 'description:'),
                       NO_DESCRIPTION) == []

    # purlin: skill_anchor PROOF-12
    def test_a_description_on_the_line_below_fails(self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               'description:\n' + description()),
                       NO_DESCRIPTION) == []

    # purlin: skill_anchor PROOF-13
    def test_a_description_opened_as_a_block_fails(self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               'description: |\n  ' + description()),
                       NO_DESCRIPTION) == []

    # purlin: skill_anchor PROOF-14
    def test_a_description_running_on_to_a_second_line_fails(
            self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               description_line() + '\n  and a second line'),
                       NO_DESCRIPTION) == []

    # purlin: skill_anchor PROOF-15
    def test_a_command_reference_without_the_row_fails(self, monkeypatch):
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:anchor '))
        assert refused(monkeypatch, command_row_problems,
                       replace(row + '\n'),
                       '%s carries no row for purlin:anchor' % COMMAND_REF,
                       rel=COMMAND_REF) == []


class TestTheScript:
    """RULE-2: the upstream script is run for `add` and `sync`, and the
    `sync` section names the read-only check `purlin:drift` runs too."""

    # purlin: skill_anchor PROOF-2
    def test_the_script_is_given_with_add_and_with_sync(self):
        assert script_problems() == []

    # purlin: skill_anchor PROOF-16
    def test_the_sync_section_names_the_check_drift_runs(self):
        assert sync_section_problems() == []

    # purlin: skill_anchor PROOF-17
    def test_the_script_followed_by_address_fails(self, monkeypatch):
        assert refused(monkeypatch, script_problems,
                       replace('upstream.py" add <git-url>',
                               'upstream.py" address <git-url>'),
                       '%s gives the script on no line as the subcommand add'
                       % REL) == []

    # purlin: skill_anchor PROOF-18
    def test_the_script_followed_by_syncall_fails(self, monkeypatch):
        assert refused(monkeypatch, script_problems,
                       replace('upstream.py" sync [',
                               'upstream.py" syncall ['),
                       '%s gives the script on no line as the subcommand sync'
                       % REL) == []

    # purlin: skill_anchor PROOF-19
    def test_a_check_that_rewrites_fails(self, monkeypatch):
        assert refused(monkeypatch, sync_section_problems,
                       replace('`--check` reports without writing',
                               '`--check` reports and rewrites'),
                       "sync section does not carry '`--check` reports "
                       "without writing'") == []

    # purlin: skill_anchor PROOF-20
    def test_drift_running_its_own_check_fails(self, monkeypatch):
        assert refused(monkeypatch, sync_section_problems,
                       replace('`purlin:drift` runs the same check',
                               '`purlin:drift` runs its own check'),
                       "sync section does not carry '`purlin:drift` runs "
                       "the same check'") == []


class TestTheNextStep:
    """RULE-3: the closing section gives a directive for every outcome."""

    # purlin: skill_anchor PROOF-3
    def test_every_closing_outcome_names_the_next_step(self):
        assert closing_problems() == []

    # purlin: skill_anchor PROOF-6
    def test_an_outcome_with_no_directive_fails(self, monkeypatch):
        assert refused(monkeypatch, closing_problems,
                       replace(', `→ Run: purlin:status`'),
                       '%s closing outcome gives no → directive: - Pin '
                       'current and nothing moved' % REL) == []

    # purlin: skill_anchor PROOF-21
    def test_a_skill_with_no_closing_section_fails(self, monkeypatch):
        before = sections(read(REL))[-2][0]
        assert before == 'Changing a pinned rule'
        assert refused(monkeypatch, closing_problems,
                       lambda t: t[:t.rindex('\n## ') + 1],
                       "%s closes with the section 'Changing a pinned rule', "
                       "which does not name the next step" % REL) == []

    # purlin: skill_anchor PROOF-22
    def test_a_closing_section_with_no_arrow_fails(self, monkeypatch):
        def no_arrow(text):
            last = text.rindex('\n## ')
            return text[:last] + text[last:].replace('→', '->')
        assert refused(monkeypatch, closing_problems, no_arrow,
                       '%s closing section gives no directive' % REL) == []

    # purlin: skill_anchor PROOF-23
    def test_a_closing_section_with_one_outcome_fails(self, monkeypatch):
        def one_outcome(text):
            last = text.rindex('\n## ')
            return text[:text.index('- Anchor added or synced', last)]
        assert refused(monkeypatch, closing_problems, one_outcome,
                       '%s closing section names 1 outcomes, expected at '
                       'least 2' % REL) == []


class TestTheCeiling:
    """RULE-4: the skill holds at most 160 lines."""

    # purlin: skill_anchor PROOF-4
    def test_the_skill_holds_at_most_160_lines(self):
        assert skill_ceiling_problems('anchor') == []

    # purlin: skill_anchor PROOF-24
    def test_a_skill_of_exactly_160_lines_passes(self, monkeypatch):
        assert on_copy(monkeypatch, REL, padded_to(160),
                       lambda: skill_ceiling_problems('anchor')) == []

    # purlin: skill_anchor PROOF-25
    def test_a_skill_of_161_lines_fails(self, monkeypatch):
        assert refused(monkeypatch, lambda: skill_ceiling_problems('anchor'),
                       padded_to(161),
                       '%s is 161 lines, ceiling 160' % REL) == []


class TestThePin:
    """RULE-5: a pin is a commit, and a pinned rule is never edited here."""

    # purlin: skill_anchor PROOF-5
    def test_a_pin_is_a_commit_never_a_branch(self):
        assert pin_problems() == []

    # purlin: skill_anchor PROOF-26
    def test_a_pin_that_may_be_a_branch_fails(self, monkeypatch):
        assert refused(monkeypatch, pin_problems,
                       replace('A pin is always a commit, never a branch.',
                               'A pin is a commit or a branch.'),
                       "does not carry 'A pin is always a commit, never a "
                       "branch.'") == []

    # purlin: skill_anchor PROOF-27
    def test_a_pinned_rule_is_never_edited_in_place(self):
        assert changing_problems(NEVER_EDIT) == []

    # purlin: skill_anchor PROOF-28
    def test_editing_a_pinned_rule_in_place_fails(self, monkeypatch):
        assert refused(monkeypatch, lambda: changing_problems(NEVER_EDIT),
                       replace(NEVER_EDIT, 'Edit a pinned rule in place when '
                               'the change is small.'),
                       "Changing a pinned rule section does not carry %r"
                       % NEVER_EDIT) == []

    # purlin: skill_anchor PROOF-29
    def test_a_change_goes_to_the_source_repository(self):
        assert changing_problems(PULL_REQUEST) == []

    # purlin: skill_anchor PROOF-30
    def test_a_change_committed_to_the_local_copy_fails(self, monkeypatch):
        assert refused(monkeypatch, lambda: changing_problems(PULL_REQUEST),
                       replace(PULL_REQUEST, 'a commit to the local copy'),
                       "Changing a pinned rule section does not carry %r"
                       % PULL_REQUEST) == []

    # purlin: skill_anchor PROOF-31
    def test_a_local_rule_goes_in_an_anchor_that_requires_the_pin(self):
        assert local_anchor_problems() == []

    # purlin: skill_anchor PROOF-32
    def test_a_local_rule_in_the_pinned_copy_fails(self, monkeypatch):
        assert refused(monkeypatch, local_anchor_problems,
                       replace('goes in a separate local anchor that says',
                               'goes in the pinned copy, which says'),
                       "Changing a pinned rule section has no sentence "
                       "carrying both 'separate local anchor' and "
                       "'`> Requires: <the pinned one>`'") == []


class TestTheFolder:
    """RULE-6: the folder for anchors comes with the first anchor."""

    # purlin: skill_anchor PROOF-7
    def test_the_first_anchor_creates_the_folder(self):
        assert folder_problems() == []

    # purlin: skill_anchor PROOF-8
    def test_a_folder_made_at_setup_fails(self, monkeypatch):
        assert refused(monkeypatch, folder_problems,
                       replace('is created with the first anchor, written '
                               'here or brought in by `add`.',
                               'is created at setup.'),
                       'create section does not say the folder is created '
                       'with the first anchor') == []


# ---------------------------------------------------------------------------
# The checks only the anchor skill needs. Each returns a list of problems.
# ---------------------------------------------------------------------------

NO_DESCRIPTION = '%s frontmatter carries no one-line description' % REL
NEVER_EDIT = 'Never edit a pinned rule in place.'
PULL_REQUEST = 'a pull request against the source repository'
REQUIRES = '`> Requires: <the pinned one>`'


def description():
    return field(frontmatter(read(REL)), 'description')


def description_line():
    return 'description: %s' % description()


def skill_frontmatter_problems():
    """The frontmatter's problems, those about the command reference aside."""
    return [p for p in frontmatter_problems('anchor') if p.startswith(REL)]


def command_row_problems():
    return [p for p in frontmatter_problems('anchor')
            if p.startswith(COMMAND_REF)]


def script_problems():
    problems = []
    found = read(REL).count(SCRIPT)
    if found < 2:
        problems.append('%s names %s %d times, expected at least 2'
                        % (REL, SCRIPT, found))
    for subcommand in ('add', 'sync'):
        problems.extend(same_line(REL, [SCRIPT, subcommand]))
        # The subcommand is the word that follows the script, not any
        # letters on the line.
        if not re.search(r'^.*%s %s\b' % (re.escape(SCRIPT), subcommand),
                         read(REL), re.M):
            problems.append('%s gives the script on no line as the '
                            'subcommand %s' % (REL, subcommand))
    return problems


def sync_section_problems():
    body = flat(section(read(REL), r'^sync$') or '')
    return ['%s sync section does not carry %r' % (REL, needle)
            for needle in ('`--check` reports without writing',
                           '`purlin:drift` runs the same check')
            if needle not in body]


def closing_problems():
    return next_step_problems('anchor') + undirected_outcome_problems('anchor')


def padded_to(lines):
    """An edit that adds lines of prose until the skill holds `lines`."""
    def edit(text):
        short = lines - len(text.splitlines())
        assert short > 0, 'the skill already holds %d lines' % lines
        return text + 'A line of prose.\n' * short
    return edit


def pin_problems():
    return carries(REL, ['A pin is always a commit, never a branch.'])


def changing_body():
    return flat(section(read(REL), r'^Changing a pinned rule$') or '')


def changing_problems(needle):
    if needle in changing_body():
        return []
    return ['%s Changing a pinned rule section does not carry %r'
            % (REL, needle)]


def local_anchor_problems():
    sentences = re.split(r'(?<=\.)\s+(?=[A-Z`*])', changing_body())
    if any('separate local anchor' in s and REQUIRES in s for s in sentences):
        return []
    return ["%s Changing a pinned rule section has no sentence carrying both "
            "'separate local anchor' and %r" % (REL, REQUIRES)]


def folder_problems():
    body = flat(section(read(REL), r'^create$') or '')
    needle = ('The folder `specs/_anchors/` is created with the first anchor, '
              'written here or brought in by `add`.')
    if needle in body:
        return []
    return ['%s create section does not say the folder is created with the '
            'first anchor: %r' % (REL, needle)]
