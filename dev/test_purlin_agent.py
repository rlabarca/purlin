"""Text checks for the agent definition, `agents/purlin.md`.

Every proof of `specs/instructions/purlin_agent.md` has a test of its own
here, and each reads the file on disk. The test then points the same check at
copies of the file, each with one thing broken, and asserts every copy is
refused: that shows the check can fail, and the file on disk is never touched.
The readers, the checks and the copies this file shares with the other skill
test files are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (AGENT, COMMANDS, COMMAND_REF, ROLES, carries,
                          ceiling_problems, command_rows, field, flat,
                          frontmatter, on_copy, read, refusals, replace, resub,
                          section, table_rows)


class TestFrontmatter:

    # purlin: purlin_agent PROOF-1
    def test_the_frontmatter_names_the_agent(self, monkeypatch):
        assert agent_frontmatter_problems() == []
        assert refusals(monkeypatch, agent_frontmatter_problems, [
            (AGENT, replace('effort: high\n'),
             '%s frontmatter carries no effort' % AGENT),
            (AGENT, replace('effort: high', 'effort:'),
             '%s frontmatter carries no effort' % AGENT),
            (AGENT, replace('name: purlin', 'name: helper'),
             "%s frontmatter name is 'helper', expected 'purlin'" % AGENT),
            (AGENT, resub(r'^description: [^\n]*', 'description:'),
             '%s frontmatter carries no description' % AGENT),
            (AGENT, lambda text: 'The Purlin agent.\n' + text,
             '%s does not open with a frontmatter block' % AGENT),
        ]) == []


class TestCoreLoop:

    # purlin: purlin_agent PROOF-2
    def test_the_core_loop_is_stated_once_in_order(self, monkeypatch):
        assert core_loop_problems() == []
        assert refusals(monkeypatch, core_loop_problems, [
            (AGENT, replace('purlin:build → purlin:test →',
                            'purlin:test → purlin:build →'),
             '%s core loop runs out of order' % AGENT),
            (AGENT, replace(' → purlin:test --release'),
             '%s core loop does not name purlin:test --release' % AGENT),
            (AGENT, replace(' → purlin:sign\n```', '\n```'),
             '%s core loop does not name purlin:sign' % AGENT),
            (AGENT, replace('## Four NEVERs', '```\npurlin:drift → '
                            'purlin:build\n```\n\n## Four NEVERs'),
             '%s states the core loop in 2 fenced blocks, expected 1' % AGENT),
            (AGENT, replace('Every step runs on', 'The loop is purlin:drift '
                            '→ purlin:build. Every step runs on'),
             '%s states the core loop 2 times, expected once' % AGENT),
        ]) == []


def remote_exception_in_the_fourth_never(text):
    """The exception taken out of the third NEVER and put in the fourth:
    every word is still in the section, in the wrong item."""
    moved = ('The one exception is `purlin:test --remote`, which pushes a '
             'run branch of its own. ')
    return replace('The one exception is `purlin:test --remote`,\n   '
                   'which pushes a run branch of its own, waits for it '
                   'and deletes it. ')(text).replace(
                       'No emoji anywhere', moved + 'No emoji anywhere', 1)


class TestNevers:

    # purlin: purlin_agent PROOF-3
    def test_the_four_nevers_each_forbid_their_own_thing(self, monkeypatch):
        assert never_problems() == []
        assert refusals(monkeypatch, never_problems, [
            (AGENT, replace('4. **Never call', '4. **Never guess.**\n'
                            '5. **Never call'),
             '%s carries 5 NEVERs, expected 4' % AGENT),
            (AGENT, resub(r"^2\. \*\*Never sign off.*?(?=^3\. )"),
             '%s carries 3 NEVERs, expected 4' % AGENT),
            (AGENT, replace('Never write evidence or a sign-off by hand',
                            'Never write evidence carelessly'),
             "%s NEVER 1 does not carry 'Never write evidence or a "
             "sign-off by hand'" % AGENT),
            (AGENT, replace("**Never sign off on a person's behalf.**",
                            '**Never guess.**'),
             "%s NEVER 2 does not carry \"Never sign off on a person's "
             "behalf\"" % AGENT),
            (AGENT, replace('never write a tag yourself, '),
             "%s NEVER 3 does not carry 'Never push, never write a "
             "tag yourself" % AGENT),
            (AGENT, remote_exception_in_the_fourth_never,
             "%s NEVER 3 does not carry 'The one exception is "
             "`purlin:test --remote`" % AGENT),
            (AGENT, replace('`references/glossary.md` gives it',
                            'the style guide gives it'),
             "%s NEVERs do not name 'references/glossary.md'" % AGENT),
            (AGENT, replace(' No emoji anywhere, including command output.'),
             "%s NEVER 4 does not carry 'No emoji anywhere'" % AGENT),
        ]) == []


def without_the_export_row(text):
    """The command reference with its `purlin:export` row taken out: the
    agent's row that routes to it is then refused."""
    row = next(line for line in text.splitlines()
               if line.startswith('| `purlin:export` |'))
    return replace(row + '\n')(text)


class TestRouting:

    # purlin: purlin_agent PROOF-4
    def test_the_routing_table_covers_the_three_roles(self, monkeypatch):
        assert routing_problems() == []
        assert refusals(monkeypatch, routing_problems, [
            (AGENT, replace('| QA | "what needs my eyes?"', '| Manager | '
                            '"how are we doing?" | `purlin:status` |\n| QA | '
                            '"what needs my eyes?"'),
             "%s routing table has a row for 'Manager'" % AGENT),
            (AGENT, replace('system of record?" | `purlin:export`',
                            'system of record?" | `purlin:release`'),
             '%s routes to purlin:release, which %s does not list'
             % (AGENT, COMMAND_REF)),
            (AGENT, lambda t: t.replace('| QA |', '| Developer |'),
             "%s routing table has no 'QA' row" % AGENT),
            (COMMAND_REF, without_the_export_row,
             '%s routes to purlin:export, which %s does not list'
             % (AGENT, COMMAND_REF)),
        ]) == []


class TestState:

    # purlin: purlin_agent PROOF-5
    def test_it_reads_the_state_before_it_answers(self, monkeypatch):
        assert state_problems() == []
        assert refusals(monkeypatch, state_problems, [
            (AGENT, replace('before you answer any question',
                            'when you answer any question'),
             '%s carries no sentence opening %r and ending %r'
             % (AGENT, STATE_OPENS, STATE_ENDS)),
            (AGENT, replace('Call `sync_status`', 'Read `sync_status`'),
             '%s carries no sentence opening %r and ending %r'
             % (AGENT, STATE_OPENS, STATE_ENDS)),
            # `strong` stays in backticks elsewhere in the file.
            (AGENT, replace('`passed` and\n`strong`, each cell',
                            '`passed`, each cell'),
             "%s sync_status paragraph does not carry '`passed` and "
             "`strong`'" % AGENT),
            (AGENT, replace('`out of date` means the spec, the code or the '
                            'tests moved since the run',
                            '`out of date` means the run is old'),
             "%s sync_status paragraph does not carry '`out of "
             "date` means the spec, the code or the tests moved "
             "since the run'" % AGENT),
        ]) == []


# The words the first call of `sync_status` carries right after the tool's
# name, so the tool reads the project and not the folder its server started in.
PROJECT_ROOT_CLAUSE = ('with `project_root` set to the project root, the top '
                       'folder of the git checkout')


def project_root_problems():
    text = flat(read(AGENT))
    at = text.find('`sync_status`')
    if at < 0:
        return ['%s never names `sync_status`' % AGENT]
    after = text[at + len('`sync_status`'):].lstrip()
    if not after.startswith(PROJECT_ROOT_CLAUSE):
        return ['%s first `sync_status` is not followed by %r'
                % (AGENT, PROJECT_ROOT_CLAUSE)]
    return []


class TestProjectRoot:

    # purlin: purlin_agent PROOF-47
    def test_the_first_call_names_the_project_root(self, monkeypatch):
        assert project_root_problems() == []
        refused = ('%s first `sync_status` is not followed by %r'
                   % (AGENT, PROJECT_ROOT_CLAUSE))
        assert refusals(monkeypatch, project_root_problems, [
            (AGENT, replace(' with `project_root` set to the project root, '
                            'the top folder of the git checkout,'), refused),
            (AGENT, replace('the top folder of the git checkout',
                            'the folder the server started in'), refused),
            # The clause moved to a later call leaves the first one bare.
            (AGENT, lambda text: text.replace(
                'Call `sync_status` with', 'Read the rules first. Call '
                '`sync_status` and then `sync_status` with', 1), refused),
        ]) == []


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
    def test_it_stays_under_its_ceiling(self, monkeypatch):
        assert ceiling_problems(AGENT, 135) == []
        check = lambda: ceiling_problems(AGENT, 135)  # noqa: E731
        assert on_copy(monkeypatch, AGENT, lines_long(136), check) == [
            '%s is 136 lines, ceiling 135' % AGENT]

    # purlin: purlin_agent PROOF-38
    def test_a_copy_of_exactly_135_lines_is_not_refused(self, monkeypatch):
        check = lambda: ceiling_problems(AGENT, 135)  # noqa: E731
        assert on_copy(monkeypatch, AGENT, lines_long(135), check) == []


class TestRename:

    # purlin: purlin_agent PROOF-7
    def test_it_says_what_a_rename_moves(self, monkeypatch):
        assert rename_problems() == []
        assert refusals(monkeypatch, rename_problems, [
            (AGENT, replace('carried in three places', 'carried in several '
                            'places'),
             "%s rename section does not carry 'carried in three places'"
             % AGENT),
            (AGENT, replace('`specs/<category>/<name>.md` and its', 'and its'),
             "%s rename section does not carry "
             "'specs/<category>/<name>.md'" % AGENT),
            (AGENT, replace(' in one commit'),
             "%s rename section does not carry 'moves them together "
             "in one commit'" % AGENT),
            (AGENT, replace('Move files with `git mv`, then call '
                            '`sync_status`:', 'Call `sync_status`, then '
                            'move files with `git mv`:'),
             '%s rename section calls sync_status before git mv' % AGENT),
            (AGENT, replace('## Renaming a feature', '## Moving a feature'),
             '%s has no Renaming a feature section' % AGENT),
        ]) == []


class TestLeftToDo:

    # purlin: purlin_agent PROOF-11
    def test_it_says_every_run_ends_on_left_to_do(self, monkeypatch):
        assert left_to_do_problems() == []
        assert refusals(monkeypatch, left_to_do_problems, [
            (AGENT, replace('The first line of `Left to do` is the next\n'
                            'step', 'The next step\nis yours to choose'),
             "%s does not carry 'The first line of `Left to do` is "
             "the next step'" % AGENT),
            (AGENT, replace('Nothing left to do.', 'Nothing more to do.'),
             "%s does not carry 'Nothing left to do.'" % AGENT),
            # The old summary's clause put back is refused.
            (AGENT, replace('pass their tests. The audit',
                            'pass their tests. 30 are strong. The audit'),
             "%s does not carry '40 rules. 35 pass their tests. The "
             "audit found 30 strong and 2 weak.'" % AGENT),
        ]) == []


class TestRelease:

    # purlin: purlin_agent PROOF-48
    def test_it_says_how_a_release_is_made(self, monkeypatch):
        assert release_problems() == []
        assert refusals(monkeypatch, release_problems, [
            (AGENT, replace('Nothing is signed while the specs change. '),
             "%s does not carry 'Nothing is signed while the specs "
             "change.'" % AGENT),
            (AGENT, replace('tags `passed/<version>`', 'tags the commit'),
             "%s does not carry 'tags `passed/<version>`'" % AGENT),
            (AGENT, replace('the first sign-off writes `signed/<version>`',
                            'each sign-off moves the tag'),
             "%s does not carry 'the first sign-off writes "
             "`signed/<version>`'" % AGENT),
        ]) == []


# What the agent says of a release, all in one paragraph.
RELEASE = ('Nothing is signed while the specs change.', 'purlin:test --release',
           'tags `passed/<version>`',
           'the first sign-off writes `signed/<version>`')


def release_problems():
    paragraphs = [flat(p) for p in re.split(r'\n\s*\n', read(AGENT))]
    paragraph = next((p for p in paragraphs if RELEASE[1] in p and
                      '```' not in p), '')
    return ['%s does not carry %r' % (AGENT, needle)
            for needle in RELEASE if needle not in paragraph]


# What the agent says every run ends on, all in one paragraph.
LEFT_TO_DO = ('40 rules. 35 pass their tests. The audit found 30 strong and '
              '2 weak.',
              'The first line of `Left to do` is the next step',
              'Nothing left to do.')


def left_to_do_problems():
    paragraphs = [flat(p) for p in re.split(r'\n\s*\n', read(AGENT))]
    paragraph = next((p for p in paragraphs if LEFT_TO_DO[2] in p), '')
    return ['%s does not carry %r' % (AGENT, needle)
            for needle in LEFT_TO_DO if needle not in paragraph]


def rename_problems():
    body = section(read(AGENT), r'^Renaming a feature$')
    if body is None:
        return ['%s has no Renaming a feature section' % AGENT]
    text = flat(body)
    problems = ['%s rename section does not carry %r' % (AGENT, needle)
                for needle in ('# Feature:', 'carried in three places',
                               'purlin: <name> PROOF-<n>',
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


# The sentence that says to read the state: how it opens and how it ends.
STATE_OPENS = 'Call `sync_status`'
STATE_ENDS = 'before you answer any question about state.'


def state_sentence(paragraph):
    """The sentence of a flattened paragraph that opens with STATE_OPENS
    and ends with STATE_ENDS, or None."""
    match = re.search(r'(?:^|(?<=\. ))%s[^.]*?%s' % (
        re.escape(STATE_OPENS), re.escape(STATE_ENDS)), paragraph)
    return match.group(0) if match else None


def state_problems():
    """The sync_status sentence, and what the paragraph holding it names."""
    problems = carries(AGENT, ['`passed`', '`strong`', '`out of date`'])
    paragraph = next((flat(p) for p in re.split(r'\n\s*\n', read(AGENT))
                      if state_sentence(flat(p))), None)
    if paragraph is None:
        return problems + ['%s carries no sentence opening %r and ending %r'
                           % (AGENT, STATE_OPENS, STATE_ENDS)]
    return problems + [
        '%s sync_status paragraph does not carry %r' % (AGENT, needle)
        for needle in ('`passed` and `strong`',
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
    steps = ['purlin:drift', 'purlin:spec', 'purlin:build', 'purlin:test ',
             'purlin:test --release', 'purlin:sign']
    text = loop[0]
    missing = [step.strip() for step in steps if step not in text]
    if missing:
        return ['%s core loop does not name %s' % (AGENT, ', '.join(missing))]
    # `purlin:test ` is the plain run: the first one, before the release.
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
    ('Never write evidence or a sign-off by hand',),
    ("Never sign off on a person's behalf",),
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
    for needle in ('evidence', 'sign-off',
                   "sign off on a person's behalf", 'Never push',
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
