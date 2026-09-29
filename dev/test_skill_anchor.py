"""Text checks for the anchor skill, `skills/anchor/SKILL.md`.

Every rule of `specs/skills/skill_anchor.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems, read,
                          refusals, replace, same_line, section,
                          skill_ceiling_problems, skill_path,
                          undirected_outcome_problems)


class TestSkillAnchor:

    # purlin: skill_anchor PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('anchor') == []

    # purlin: skill_anchor PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'anchor') == []

    # purlin: skill_anchor PROOF-2
    def test_it_runs_the_upstream_script_for_two_subcommands(self):
        assert anchor_command_problems() == []

    # purlin: skill_anchor PROOF-2
    def test_a_broken_command_or_check_sentence_is_refused(self, monkeypatch):
        rel = skill_path('anchor')
        assert refusals(monkeypatch, anchor_command_problems, [
            (rel, replace('upstream.py" add <git-url>',
                          'upstream.py" address <git-url>'),
             '%s gives the script on no line as the subcommand add' % rel),
            (rel, replace('`--check` reports without writing',
                          '`--check` reports and rewrites'),
             "sync section does not carry '`--check` reports without "
             "writing'"),
            (rel, replace('`purlin:drift` runs the same check',
                          '`purlin:drift` runs its own check'),
             "sync section does not carry '`purlin:drift` runs the same "
             "check'"),
        ]) == []

    # purlin: skill_anchor PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('anchor')
                + undirected_outcome_problems('anchor')) == []

    # purlin: skill_anchor PROOF-6
    def test_an_outcome_with_no_directive_is_refused(self, monkeypatch):
        rel = skill_path('anchor')
        assert refusals(
            monkeypatch, lambda: undirected_outcome_problems('anchor'), [
                (rel, replace(', `\u2192 Run: purlin:status`'),
                 '%s closing outcome gives no \u2192 directive: - Pin current '
                 'and nothing moved' % rel),
            ]) == []

    # purlin: skill_anchor PROOF-7
    def test_the_first_anchor_creates_the_folder(self):
        assert anchor_folder_problems() == []

    # purlin: skill_anchor PROOF-8
    def test_a_folder_made_at_setup_is_refused(self, monkeypatch):
        rel = skill_path('anchor')
        assert refusals(monkeypatch, anchor_folder_problems, [
            (rel, replace('is created with the first anchor, written here or '
                          'brought in by `add`.',
                          'is created at setup.'),
             'create section does not say the folder is created with the '
             'first anchor'),
        ]) == []

    # purlin: skill_anchor PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('anchor') == []

    # purlin: skill_anchor PROOF-5
    def test_a_pin_is_a_commit_and_a_pinned_rule_is_never_edited(self):
        assert anchor_pin_problems() == []

    # purlin: skill_anchor PROOF-5
    def test_a_local_anchor_that_requires_nothing_is_refused(
            self, monkeypatch):
        rel = skill_path('anchor')
        assert refusals(monkeypatch, anchor_pin_problems, [
            (rel, replace('goes in a separate local anchor that says',
                          'goes in the pinned copy, which says'),
             "Changing a pinned rule section has no sentence carrying both "
             "'separate local anchor' and '`> Requires: <the pinned one>`'"),
        ]) == []


def anchor_pin_problems():
    rel = skill_path('anchor')
    problems = carries(rel, [
        'A pin is always a commit, never a branch.',
        'Never edit a pinned rule in place.',
        'a pull request against the source repository',
        '> Requires: <the pinned one>'])
    body = flat(section(read(rel), r'^Changing a pinned rule$') or '')
    sentences = re.split(r'(?<=\.)\s+(?=[A-Z`*])', body)
    if not any('separate local anchor' in s
               and '`> Requires: <the pinned one>`' in s for s in sentences):
        problems.append("%s Changing a pinned rule section has no sentence "
                        "carrying both 'separate local anchor' and "
                        "'`> Requires: <the pinned one>`'" % rel)
    return problems


def anchor_command_problems():
    rel = skill_path('anchor')
    script = '"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"'
    problems = []
    found = read(rel).count(script)
    if found < 2:
        problems.append('%s names %s %d times, expected at least 2'
                        % (rel, script, found))
    for subcommand in ('add', 'sync'):
        problems.extend(same_line(rel, [script, subcommand]))
        # The subcommand is the word that follows the script, not any
        # letters on the line.
        if not re.search(r'^.*%s %s\b' % (re.escape(script), subcommand),
                         read(rel), re.M):
            problems.append('%s gives the script on no line as the '
                            'subcommand %s' % (rel, subcommand))
    problems.extend(carries(rel, ['--check', 'purlin:drift']))
    body = flat(section(read(rel), r'^sync$') or '')
    problems.extend('%s sync section does not carry %r' % (rel, needle)
                    for needle in ('`--check` reports without writing',
                                   '`purlin:drift` runs the same check')
                    if needle not in body)
    return problems


def anchor_folder_problems():
    rel = skill_path('anchor')
    body = flat(section(read(rel), r'^create$') or '')
    needle = ('The folder `specs/_anchors/` is created with the first anchor, '
              'written here or brought in by `add`.')
    if needle in body:
        return []
    return ['%s create section does not say the folder is created with the '
            'first anchor: %r' % (rel, needle)]
