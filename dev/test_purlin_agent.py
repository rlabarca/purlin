"""Text checks for the agent definition, `agents/purlin.md`.

Every rule of `specs/instructions/purlin_agent.md` is proved here, one test
per proof. A proof that the agent says a thing reads the file on disk; a proof
that a broken copy is refused points the same check at a copy of the file with
one thing broken, and the file on disk is never touched. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (AGENT, COMMANDS, COMMAND_REF, ROLES, carries,
                          ceiling_problems, command_rows, field, flat,
                          frontmatter, on_copy, read, refusals, replace, resub,
                          section, table_rows)


def refused(monkeypatch, check, rel, edit, expected):
    """What is wrong when a copy of `rel`, broken by `edit`, is not reported
    with `expected`: an empty list when it is."""
    return refusals(monkeypatch, check, [(rel, edit, expected)])


class TestFrontmatter:

    # purlin: purlin_agent PROOF-1
    def test_the_frontmatter_names_the_agent(self):
        assert agent_frontmatter_problems() == []

    # purlin: purlin_agent PROOF-16
    def test_a_copy_without_the_effort_line_is_refused(self, monkeypatch):
        assert refused(monkeypatch, agent_frontmatter_problems, AGENT,
                       replace('effort: high\n'),
                       '%s frontmatter carries no effort' % AGENT) == []

    # purlin: purlin_agent PROOF-17
    def test_a_copy_with_an_empty_effort_is_refused(self, monkeypatch):
        assert refused(monkeypatch, agent_frontmatter_problems, AGENT,
                       replace('effort: high', 'effort:'),
                       '%s frontmatter carries no effort' % AGENT) == []

    # purlin: purlin_agent PROOF-18
    def test_a_copy_named_helper_is_refused(self, monkeypatch):
        assert refused(monkeypatch, agent_frontmatter_problems, AGENT,
                       replace('name: purlin', 'name: helper'),
                       "%s frontmatter name is 'helper', expected 'purlin'"
                       % AGENT) == []

    # purlin: purlin_agent PROOF-19
    def test_a_copy_with_an_empty_description_is_refused(self, monkeypatch):
        assert refused(monkeypatch, agent_frontmatter_problems, AGENT,
                       resub(r'^description: [^\n]*', 'description:'),
                       '%s frontmatter carries no description' % AGENT) == []

    # purlin: purlin_agent PROOF-20
    def test_a_copy_with_prose_above_the_frontmatter_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, agent_frontmatter_problems, AGENT,
                       lambda text: 'The Purlin agent.\n' + text,
                       '%s does not open with a frontmatter block'
                       % AGENT) == []


class TestCoreLoop:

    # purlin: purlin_agent PROOF-2
    def test_the_core_loop_is_stated_once_in_order(self):
        assert core_loop_problems() == []

    # purlin: purlin_agent PROOF-21
    def test_a_copy_with_audit_before_test_is_refused(self, monkeypatch):
        assert refused(monkeypatch, core_loop_problems, AGENT,
                       replace('purlin:test → purlin:audit',
                               'purlin:audit → purlin:test'),
                       '%s core loop runs out of order' % AGENT) == []

    # purlin: purlin_agent PROOF-22
    def test_a_copy_without_sign_in_the_loop_is_refused(self, monkeypatch):
        assert refused(monkeypatch, core_loop_problems, AGENT,
                       replace(' → purlin:sign\n```', '\n```'),
                       '%s core loop does not name purlin:sign' % AGENT) == []

    # purlin: purlin_agent PROOF-23
    def test_a_copy_with_a_second_loop_block_is_refused(self, monkeypatch):
        assert refused(monkeypatch, core_loop_problems, AGENT,
                       replace('## Four NEVERs', '```\npurlin:drift → '
                               'purlin:build\n```\n\n## Four NEVERs'),
                       '%s states the core loop in 2 fenced blocks, expected 1'
                       % AGENT) == []

    # purlin: purlin_agent PROOF-24
    def test_a_copy_with_the_loop_again_in_prose_is_refused(self, monkeypatch):
        assert refused(monkeypatch, core_loop_problems, AGENT,
                       replace('Every step runs on', 'The loop is purlin:drift '
                               '→ purlin:build. Every step runs on'),
                       '%s states the core loop 2 times, expected once'
                       % AGENT) == []


class TestNevers:

    # purlin: purlin_agent PROOF-3
    def test_the_four_nevers_each_forbid_their_own_thing(self):
        assert never_problems() == []

    # purlin: purlin_agent PROOF-25
    def test_a_copy_with_a_fifth_never_is_refused(self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       replace('4. **Never call', '4. **Never guess.**\n'
                               '5. **Never call'),
                       '%s carries 5 NEVERs, expected 4' % AGENT) == []

    # purlin: purlin_agent PROOF-26
    def test_a_copy_without_the_second_never_is_refused(self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       resub(r"^2\. \*\*Never sign on.*?(?=^3\. )"),
                       '%s carries 3 NEVERs, expected 4' % AGENT) == []

    # purlin: purlin_agent PROOF-27
    def test_a_copy_whose_first_never_is_reworded_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       replace('Never write evidence or a signature by hand',
                               'Never write evidence carelessly'),
                       "%s NEVER 1 does not carry 'Never write evidence or a "
                       "signature by hand'" % AGENT) == []

    # purlin: purlin_agent PROOF-28
    def test_a_copy_whose_second_never_is_reworded_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       replace("**Never sign on a person's behalf.**",
                               '**Never guess.**'),
                       "%s NEVER 2 does not carry \"Never sign on a person's "
                       "behalf\"" % AGENT) == []

    # purlin: purlin_agent PROOF-29
    def test_a_copy_whose_third_never_allows_a_tag_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       replace('never write a tag yourself, '),
                       "%s NEVER 3 does not carry 'Never push, never write a "
                       "tag yourself" % AGENT) == []

    # purlin: purlin_agent PROOF-30
    def test_a_copy_with_the_remote_exception_in_the_fourth_never_is_refused(
            self, monkeypatch):
        # The exception taken out of the third NEVER and put in the fourth:
        # every word is still in the section, in the wrong item.
        moved = ('The one exception is `purlin:test --remote`, which pushes a '
                 'run branch of its own. ')
        assert refused(monkeypatch, never_problems, AGENT,
                       lambda t: replace(
                           'The one exception is `purlin:test --remote`,\n   '
                           'which pushes a run branch of its own, waits for it '
                           'and deletes it. ')(t).replace(
                               'No emoji anywhere',
                               moved + 'No emoji anywhere', 1),
                       "%s NEVER 3 does not carry 'The one exception is "
                       "`purlin:test --remote`" % AGENT) == []

    # purlin: purlin_agent PROOF-31
    def test_a_copy_naming_the_style_guide_for_names_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       replace('`references/glossary.md` gives it',
                               'the style guide gives it'),
                       "%s NEVERs do not name 'references/glossary.md'"
                       % AGENT) == []

    # purlin: purlin_agent PROOF-32
    def test_a_copy_whose_fourth_never_allows_emoji_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, never_problems, AGENT,
                       replace(' No emoji anywhere, including command output.'),
                       "%s NEVER 4 does not carry 'No emoji anywhere'"
                       % AGENT) == []


class TestRouting:

    # purlin: purlin_agent PROOF-4
    def test_the_routing_table_covers_the_three_roles(self):
        assert routing_problems() == []

    # purlin: purlin_agent PROOF-33
    def test_a_copy_with_a_manager_row_is_refused(self, monkeypatch):
        assert refused(monkeypatch, routing_problems, AGENT,
                       replace('| QA | "what needs my eyes?"', '| Manager | '
                               '"how are we doing?" | `purlin:status` |\n| QA | '
                               '"what needs my eyes?"'),
                       "%s routing table has a row for 'Manager'"
                       % AGENT) == []

    # purlin: purlin_agent PROOF-34
    def test_a_copy_routing_to_an_unlisted_command_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, routing_problems, AGENT,
                       replace('system of record?" | `purlin:export`',
                               'system of record?" | `purlin:release`'),
                       '%s routes to purlin:release, which %s does not list'
                       % (AGENT, COMMAND_REF)) == []

    # purlin: purlin_agent PROOF-35
    def test_a_copy_without_a_qa_row_is_refused(self, monkeypatch):
        assert refused(monkeypatch, routing_problems, AGENT,
                       lambda t: t.replace('| QA |', '| Developer |'),
                       "%s routing table has no 'QA' row" % AGENT) == []

    # purlin: purlin_agent PROOF-36
    def test_a_command_dropped_from_the_command_reference_is_refused(
            self, monkeypatch):
        # The command reference is the list: drop a command from it and the
        # agent's row that routes to it is refused.
        export_row = next(line for line in read(COMMAND_REF).splitlines()
                          if line.startswith('| `purlin:export` |'))
        assert refused(monkeypatch, routing_problems, COMMAND_REF,
                       replace(export_row + '\n'),
                       '%s routes to purlin:export, which %s does not list'
                       % (AGENT, COMMAND_REF)) == []


class TestState:

    # purlin: purlin_agent PROOF-5
    def test_it_reads_the_state_before_it_answers(self):
        assert state_problems() == []

    # purlin: purlin_agent PROOF-8
    def test_a_copy_that_calls_sync_status_when_it_answers_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, state_problems, AGENT,
                       replace('Call `sync_status` before you answer',
                               'Call `sync_status` when you answer'),
                       "%s does not carry 'Call `sync_status` before you "
                       "answer any question about state.'" % AGENT) == []

    # purlin: purlin_agent PROOF-9
    def test_a_copy_that_drops_strong_from_the_paragraph_is_refused(
            self, monkeypatch):
        # `strong` stays in backticks elsewhere in the file.
        assert refused(monkeypatch, state_problems, AGENT,
                       replace('`passed`, `strong` and `signed` as far',
                               '`passed` and `signed` as far'),
                       "%s sync_status paragraph does not carry '`passed`, "
                       "`strong` and `signed`'" % AGENT) == []

    # purlin: purlin_agent PROOF-10
    def test_a_copy_that_gives_out_of_date_another_meaning_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, state_problems, AGENT,
                       replace('`out of date` means the spec, the code or the '
                               'tests moved since the run',
                               '`out of date` means the run is old'),
                       "%s sync_status paragraph does not carry '`out of "
                       "date` means the spec, the code or the tests moved "
                       "since the run'" % AGENT) == []

    # purlin: purlin_agent PROOF-37
    def test_a_copy_that_gives_no_proof_written_another_meaning_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, state_problems, AGENT,
                       replace('`no proof written` means no proof line names '
                               'the rule',
                               '`no proof written` means the rule has no test'),
                       "%s sync_status paragraph does not carry '`no proof "
                       "written` means no proof line names the rule'"
                       % AGENT) == []


def lines_long(count):
    """An edit that cuts the file to its first `count - 1` lines, or pads it
    with lines of prose, and ends it on one line of prose: `count` lines."""
    def edit(text):
        lines = text.splitlines()[:count - 1]
        lines += ['A line of prose.'] * (count - len(lines))
        return '\n'.join(lines) + '\n'
    return edit


class TestCeiling:

    # purlin: purlin_agent PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert ceiling_problems(AGENT, 135) == []

    # purlin: purlin_agent PROOF-38
    def test_a_copy_of_exactly_135_lines_is_not_refused(self, monkeypatch):
        check = lambda: ceiling_problems(AGENT, 135)  # noqa: E731
        assert on_copy(monkeypatch, AGENT, lines_long(135), check) == []

    # purlin: purlin_agent PROOF-39
    def test_a_copy_of_136_lines_is_refused(self, monkeypatch):
        check = lambda: ceiling_problems(AGENT, 135)  # noqa: E731
        assert on_copy(monkeypatch, AGENT, lines_long(136), check) == [
            '%s is 136 lines, ceiling 135' % AGENT]


class TestRename:

    # purlin: purlin_agent PROOF-7
    def test_it_says_what_a_rename_moves(self):
        assert rename_problems() == []

    # purlin: purlin_agent PROOF-40
    def test_a_copy_without_requires_is_refused(self, monkeypatch):
        assert refused(monkeypatch, rename_problems, AGENT,
                       replace('every `> Requires:` entry', 'every entry'),
                       "%s rename section does not carry '> Requires:'"
                       % AGENT) == []

    # purlin: purlin_agent PROOF-41
    def test_a_copy_without_the_spec_path_is_refused(self, monkeypatch):
        assert refused(monkeypatch, rename_problems, AGENT,
                       replace('`specs/<category>/<name>.md` and its',
                               'and its'),
                       "%s rename section does not carry "
                       "'specs/<category>/<name>.md'" % AGENT) == []

    # purlin: purlin_agent PROOF-42
    def test_a_copy_without_one_commit_is_refused(self, monkeypatch):
        assert refused(monkeypatch, rename_problems, AGENT,
                       replace(' in one commit'),
                       "%s rename section does not carry 'moves them together "
                       "in one commit'" % AGENT) == []

    # purlin: purlin_agent PROOF-43
    def test_a_copy_calling_sync_status_before_git_mv_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, rename_problems, AGENT,
                       replace('Move files with `git mv`, then call '
                               '`sync_status`:', 'Call `sync_status`, then '
                               'move files with `git mv`:'),
                       '%s rename section calls sync_status before git mv'
                       % AGENT) == []

    # purlin: purlin_agent PROOF-44
    def test_a_copy_without_the_rename_section_is_refused(self, monkeypatch):
        assert refused(monkeypatch, rename_problems, AGENT,
                       replace('## Renaming a feature', '## Moving a feature'),
                       '%s has no Renaming a feature section' % AGENT) == []


class TestLeftToDo:

    # purlin: purlin_agent PROOF-11
    def test_it_says_every_run_ends_on_left_to_do(self):
        assert left_to_do_problems() == []

    # purlin: purlin_agent PROOF-12
    def test_a_copy_that_leaves_the_next_step_unnamed_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, left_to_do_problems, AGENT,
                       replace('The first line of\n`Left to do` is the next '
                               'step', 'The next step\nis yours to choose'),
                       "%s does not carry 'The first line of `Left to do` is "
                       "the next step'" % AGENT) == []

    # purlin: purlin_agent PROOF-45
    def test_a_copy_that_ends_on_other_words_is_refused(self, monkeypatch):
        assert refused(monkeypatch, left_to_do_problems, AGENT,
                       replace('Nothing left to do.', 'Nothing more to do.'),
                       "%s does not carry 'Nothing left to do.'" % AGENT) == []

    # purlin: purlin_agent PROOF-46
    def test_a_copy_whose_summary_drops_a_step_is_refused(self, monkeypatch):
        assert refused(monkeypatch, left_to_do_problems, AGENT,
                       replace(' 30 are strong.'),
                       "%s does not carry '40 rules. 35 pass their tests. 30 "
                       "are strong. 20 are signed.'" % AGENT) == []


# What the agent says every run ends on, all in one paragraph.
LEFT_TO_DO = ('40 rules. 35 pass their tests. 30 are strong. 20 are signed.',
              'The first line of `Left to do` is the next step',
              'Nothing left to do.')


def left_to_do_problems():
    paragraphs = [flat(p) for p in re.split(r'\n\s*\n', read(AGENT))]
    paragraph = next((p for p in paragraphs if LEFT_TO_DO[0] in p), '')
    return ['%s does not carry %r' % (AGENT, needle)
            for needle in LEFT_TO_DO if needle not in paragraph]


def rename_problems():
    body = section(read(AGENT), r'^Renaming a feature$')
    if body is None:
        return ['%s has no Renaming a feature section' % AGENT]
    text = flat(body)
    problems = ['%s rename section does not carry %r' % (AGENT, needle)
                for needle in ('# Feature:', '> Requires:',
                               'purlin: <name> PROOF-<n>', '.signatures/',
                               '.purlin/evidence/<source>/<name>.json',
                               'git mv', 'sync_status',
                               'specs/<category>/<name>.md',
                               'moves them together in one commit',
                               'a reference it cannot resolve is one the '
                               'rename missed')
                if needle not in text]
    if not problems and text.index('sync_status') < text.index('git mv'):
        problems.append('%s rename section calls sync_status before git mv'
                        % AGENT)
    return problems


def state_problems():
    """The sync_status sentence, and what the paragraph holding it names."""
    sentence = 'Call `sync_status` before you answer any question about state.'
    problems = carries(AGENT, [sentence, '`no proof written`', '`passed`',
                               '`strong`', '`signed`', '`out of date`'])
    paragraph = next((flat(p) for p in re.split(r'\n\s*\n', read(AGENT))
                      if sentence in flat(p)), None)
    if paragraph is None:
        return problems
    return problems + [
        '%s sync_status paragraph does not carry %r' % (AGENT, needle)
        for needle in ('`passed`, `strong` and `signed`',
                       '`no proof written` means no proof line names the rule',
                       '`out of date` means the spec, the code or the tests '
                       'moved since the run')
        if needle not in paragraph]


def agent_frontmatter_problems():
    block = frontmatter(read(AGENT))
    if block is None:
        return ['%s does not open with a frontmatter block' % AGENT]
    problems = []
    if field(block, 'name') != 'purlin':
        problems.append('%s frontmatter name is %r, expected %r'
                        % (AGENT, field(block, 'name'), 'purlin'))
    if not field(block, 'description'):
        problems.append('%s frontmatter carries no description' % AGENT)
    if not field(block, 'effort'):
        problems.append('%s frontmatter carries no effort' % AGENT)
    return problems


def core_loop_problems():
    fences = re.findall(r'```\n(.*?)```', read(AGENT), re.S)
    loop = [fence for fence in fences if 'purlin:drift' in fence]
    if not loop:
        return ['%s has no fenced block naming purlin:drift' % AGENT]
    steps = ['purlin:drift', 'purlin:spec', 'purlin:build', 'purlin:test',
             'purlin:audit', 'purlin:sign']
    text = loop[0]
    missing = [step for step in steps if step not in text]
    if missing:
        return ['%s core loop does not name %s' % (AGENT, ', '.join(missing))]
    offsets = [text.index(step) for step in steps]
    if offsets != sorted(offsets):
        return ['%s core loop runs out of order, at offsets %s'
                % (AGENT, offsets)]
    # Stated once: one fenced block, and the chain written out once.
    problems = []
    if len(loop) != 1:
        problems.append('%s states the core loop in %d fenced blocks, '
                        'expected 1' % (AGENT, len(loop)))
    chains = len(re.findall(r'purlin:drift\s*→', read(AGENT)))
    if chains != 1:
        problems.append('%s states the core loop %d times, expected once'
                        % (AGENT, chains))
    return problems


# What each NEVER forbids, in order, in the words of its own item.
NEVERS = (
    ('Never write evidence or a signature by hand',),
    ("Never sign on a person's behalf",),
    ('Never push, never write a tag yourself, never open a pull request, '
     'never delete or rewrite a remote branch',
     'The one exception is `purlin:test --remote`, which pushes a run branch '
     'of its own'),
    ('Never call a thing by a name other than the one '
     '`references/glossary.md` gives it', 'No emoji anywhere'),
)


def never_problems():
    body = section(read(AGENT), r'NEVER')
    if body is None:
        return ['%s has no section of NEVERs' % AGENT]
    items = re.findall(r'^\d+\. ', body, re.M)
    problems = []
    if len(items) != 4:
        problems.append('%s carries %d NEVERs, expected 4' % (AGENT, len(items)))
    flattened = flat(body)
    for needle in ('evidence', 'signature',
                   "sign on a person's behalf", 'Never push',
                   'pull request', 'remote branch', 'purlin:test --remote',
                   'references/glossary.md'):
        if needle not in flattened:
            problems.append('%s NEVERs do not name %r' % (AGENT, needle))
    texts = [flat(item) for item in re.split(r'^\d+\. ', body, flags=re.M)[1:]]
    for number, needles in enumerate(NEVERS, 1):
        text = texts[number - 1] if number <= len(texts) else ''
        problems.extend('%s NEVER %d does not carry %r' % (AGENT, number, n)
                        for n in needles if n not in text)
    return problems


def routing_problems():
    rows = table_rows(read(AGENT), '| Role |')
    problems = []
    if not rows:
        return ['%s has no routing table' % AGENT]
    roles = {cells[0] for cells in rows}
    for role in ROLES:
        if role not in roles:
            problems.append('%s routing table has no %r row' % (AGENT, role))
    for role in sorted(roles - set(ROLES)):
        problems.append('%s routing table has a row for %r, which is not one '
                        'of the three roles' % (AGENT, role))
    # A command is read by its name alone: `purlin:anchor add` and
    # `purlin:init --gate <gate>` name `purlin:anchor` and `purlin:init`.
    named = set(re.findall(r'purlin:([a-z-]+)',
                           '\n'.join('|'.join(cells) for cells in rows)))
    for command in sorted(named - set(COMMANDS)):
        problems.append('%s routes to purlin:%s, which is not one of the '
                        'commands' % (AGENT, command))
    listed = reference_commands()
    if not listed:
        problems.append('%s lists no command' % COMMAND_REF)
    for command in sorted(named - listed):
        problems.append('%s routes to purlin:%s, which %s does not list'
                        % (AGENT, command, COMMAND_REF))
    return problems


def reference_commands():
    """Each command the command reference gives a row, by its name alone."""
    return {match.group(1) for match in
            (re.match(r'`purlin:([a-z-]+)', cells[0]) for cells in command_rows())
            if match}
