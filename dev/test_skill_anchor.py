"""Text checks for the anchor skill, `skills/anchor/SKILL.md`.

Every rule of `specs/skills/skill_anchor.md` is proved here, one test per
proof. Each test also points its check at copies of a file with one thing
broken, which the check must refuse; the file on disk is never touched. The readers, the shared
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
SCRIPT = ('sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" '
          '"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"')


class TestFrontmatter:
    """RULE-1: the frontmatter names the skill. RULE-8: the command
    reference carries its row."""

    # purlin: skill_anchor PROOF-1
    def test_the_skill_opens_with_its_name_and_a_one_line_description(
            self, monkeypatch):
        assert skill_frontmatter_problems() == []
        value = description()
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (REL, replace('name: anchor\n'),
             "%s frontmatter name is None, expected 'anchor'" % REL),
            (REL, replace(description_line(), 'description:'),
             NO_DESCRIPTION),
            (REL, replace(description_line(), 'description:\n' + value),
             NO_DESCRIPTION),
            (REL, replace(description_line(), 'description: |\n  ' + value),
             NO_DESCRIPTION),
            (REL, replace(description_line(),
                          description_line() + '\n  and a second line'),
             NO_DESCRIPTION),
        ]) == []

    # purlin: skill_anchor PROOF-9
    def test_the_command_reference_has_a_row_for_the_command(
            self, monkeypatch):
        assert command_row_problems() == []
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:anchor '))
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:anchor' % COMMAND_REF),
        ]) == []


class TestTheScript:
    """RULE-2: the upstream script is started for `add` and `sync`. RULE-9:
    the `sync` section names the read-only check `purlin:drift` runs too."""

    # purlin: skill_anchor PROOF-2
    def test_the_script_is_given_with_add_and_with_sync(self, monkeypatch):
        assert script_problems() == []
        assert refusals(monkeypatch, script_problems, [
            (REL, replace('upstream.py" add <git-url>',
                          'upstream.py" address <git-url>'),
             '%s gives the script on no line as the subcommand add' % REL),
            (REL, replace('upstream.py" sync [', 'upstream.py" syncall ['),
             '%s gives the script on no line as the subcommand sync' % REL),
            (REL, replace('sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" '
                          '"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py" '
                          'add', '"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/'
                          'upstream.py" add'),
             '%s gives the script on no line as the subcommand add' % REL),
        ]) == []

    # purlin: skill_anchor PROOF-16
    def test_the_sync_section_names_the_check_drift_runs(self, monkeypatch):
        assert sync_section_problems() == []
        assert refusals(monkeypatch, sync_section_problems, [
            (REL, replace('`--check` reports without writing',
                          '`--check` reports and rewrites'),
             "sync section does not carry '`--check` reports without "
             "writing'"),
            (REL, replace('`purlin:drift` runs the same check',
                          '`purlin:drift` runs its own check'),
             "sync section does not carry '`purlin:drift` runs the same "
             "check'"),
        ]) == []


class TestTheNextStep:
    """RULE-3: the closing section gives a directive for every outcome."""

    # purlin: skill_anchor PROOF-3
    def test_every_closing_outcome_names_the_next_step(self, monkeypatch):
        assert closing_problems() == []
        before = sections(read(REL))[-2][0]
        assert before == 'Changing a pinned rule'

        def no_arrow(text):
            last = text.rindex('\n## ')
            return text[:last] + text[last:].replace('\u2192', '->')

        def one_outcome(text):
            last = text.rindex('\n## ')
            return text[:text.index('- Anchor added or synced', last)]
        assert refusals(monkeypatch, closing_problems, [
            (REL, replace(', `\u2192 Run: purlin:status`'),
             '%s closing outcome gives no \u2192 directive: - Pin current and '
             'nothing moved' % REL),
            (REL, lambda t: t[:t.rindex('\n## ') + 1],
             "%s closes with the section 'Changing a pinned rule', which does "
             "not name the next step" % REL),
            (REL, no_arrow, '%s closing section gives no directive' % REL),
            (REL, one_outcome,
             '%s closing section names 1 outcomes, expected at least 2' % REL),
        ]) == []


class TestTheCeiling:
    """RULE-4: the skill holds at most 160 lines."""

    # purlin: skill_anchor PROOF-4
    def test_the_skill_holds_at_most_160_lines(self, monkeypatch):
        assert skill_ceiling_problems('anchor') == []
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('anchor'), [
            (REL, padded_to(161), '%s is 161 lines, ceiling 160' % REL),
        ]) == []

    # purlin: skill_anchor PROOF-24
    def test_a_skill_of_exactly_160_lines_passes(self, monkeypatch):
        assert on_copy(monkeypatch, REL, padded_to(160),
                       lambda: skill_ceiling_problems('anchor')) == []


class TestThePin:
    """RULE-5: a pin is a commit. RULE-10: a pinned rule is never edited
    here. RULE-11: a change goes upstream. RULE-12: a rule of this project
    alone goes in a local anchor."""

    # purlin: skill_anchor PROOF-5
    def test_a_pin_is_a_commit_never_a_branch(self, monkeypatch):
        assert pin_problems() == []
        assert refusals(monkeypatch, pin_problems, [
            (REL, replace('A pin is always a commit, never a branch.',
                          'A pin is a commit or a branch.'),
             "does not carry 'A pin is always a commit, never a branch.'"),
        ]) == []

    # purlin: skill_anchor PROOF-27
    def test_a_pinned_rule_is_never_edited_in_place(self, monkeypatch):
        assert changing_problems(NEVER_EDIT) == []
        assert refusals(monkeypatch, lambda: changing_problems(NEVER_EDIT), [
            (REL, replace(NEVER_EDIT, 'Edit a pinned rule in place when the '
                          'change is small.'),
             "Changing a pinned rule section does not carry %r" % NEVER_EDIT),
        ]) == []

    # purlin: skill_anchor PROOF-29
    def test_a_change_goes_to_the_source_repository(self, monkeypatch):
        assert changing_problems(PULL_REQUEST) == []
        assert refusals(monkeypatch, lambda: changing_problems(PULL_REQUEST), [
            (REL, replace(PULL_REQUEST, 'a commit to the local copy'),
             "Changing a pinned rule section does not carry %r"
             % PULL_REQUEST),
        ]) == []

    # purlin: skill_anchor PROOF-31
    def test_a_local_rule_goes_in_an_anchor_that_requires_the_pin(
            self, monkeypatch):
        assert local_anchor_problems() == []
        assert refusals(monkeypatch, local_anchor_problems, [
            (REL, replace('goes in a separate local anchor that says',
                          'goes in the pinned copy, which says'),
             "Changing a pinned rule section has no sentence carrying both "
             "'separate local anchor' and '`> Requires: <the pinned one>`'"),
        ]) == []


class TestTheAnchorRepository:
    """RULE-13: an anchor repository is for rules two or more projects share."""

    # purlin: skill_anchor PROOF-34
    def test_an_anchor_repository_is_for_two_or_more_projects(
            self, monkeypatch):
        assert repository_problems() == []
        assert refusals(monkeypatch, repository_problems, [
            (REL, replace('only when two or more projects must share',
                          'whenever a project wants'),
             "One repository is the default section does not carry %r"
             % SHARED_REPOSITORY[0]),
            (REL, replace("Most projects need nothing but `specs/_anchors/`.",
                          'Most projects need an anchor repository.'),
             "One repository is the default section does not carry %r"
             % SHARED_REPOSITORY[1]),
        ]) == []


class TestTheFolder:
    """RULE-6: the folder for anchors comes with the first anchor."""

    # purlin: skill_anchor PROOF-7
    def test_the_first_anchor_creates_the_folder(self, monkeypatch):
        assert folder_problems() == []
        assert refusals(monkeypatch, folder_problems, [
            (REL, replace('is created with the first anchor, written here or '
                          'brought in by `add`.', 'is created at setup.'),
             'create section does not say the folder is created with the '
             'first anchor'),
        ]) == []


class TestTheSource:
    """RULE-7: an anchor's source is a spec in Purlin's format, kept in a
    git repository; any other source is refused."""

    # purlin: skill_anchor PROOF-33
    def test_the_source_is_a_spec_in_a_repository(self, monkeypatch):
        assert source_problems() == []
        assert refusals(monkeypatch, source_problems, [
            (REL, replace('is refused and\nnothing is written',
                          'is written as it is'),
             "add section does not carry 'is refused and nothing is "
             "written'"),
        ]) == []


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


SOURCE = ("The file is a spec in Purlin's format that holds at least one "
          'rule, kept in a git repository.')


def source_problems():
    body = flat(section(read(REL), r'^add$') or '')
    return ['%s add section does not carry %r' % (REL, needle)
            for needle in (SOURCE, 'Any other source',
                           'is refused and nothing is written',
                           'the refusal names `purlin:anchor create <name>`')
            if needle not in body]


SHARED_REPOSITORY = ('Reach for an anchor repository only when two or more '
                     'projects must share the same rules',
                     'Most projects need nothing but `specs/_anchors/`.')


def repository_problems():
    body = flat(section(read(REL), r'^one repository is the default$') or '')
    return ['%s One repository is the default section does not carry %r'
            % (REL, needle) for needle in SHARED_REPOSITORY
            if needle not in body]
