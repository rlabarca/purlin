"""Text checks for the agent definition, `agents/purlin.md`.

Every rule of `specs/instructions/purlin_agent.md` is proved here. The readers,
the checks and the broken copies this file shares with the other skill test
files are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (AGENT, COMMANDS, COMMAND_REF, ROLES, carries,
                          ceiling_problems, command_rows, field, flat,
                          frontmatter, read, refusals, replace, resub, section,
                          table_rows)


class TestPurlinAgent:

    # purlin: purlin_agent PROOF-1
    def test_the_frontmatter_names_the_agent(self):
        assert agent_frontmatter_problems() == []

    # purlin: purlin_agent PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, agent_frontmatter_problems, [
            (AGENT, replace('effort: high\n'),
             '%s frontmatter carries no effort' % AGENT),
            (AGENT, replace('effort: high', 'effort:'),
             '%s frontmatter carries no effort' % AGENT),
            (AGENT, replace('name: purlin', 'name: helper'),
             "%s frontmatter name is 'helper', expected 'purlin'" % AGENT),
            (AGENT, resub(r'^description: [^\n]*', 'description:'),
             '%s frontmatter carries no description' % AGENT),
        ]) == []

    # purlin: purlin_agent PROOF-2
    def test_the_core_loop_runs_in_order(self):
        assert core_loop_problems() == []

    # purlin: purlin_agent PROOF-2
    def test_a_loop_out_of_order_or_stated_twice_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, core_loop_problems, [
            (AGENT, replace('purlin:test → purlin:audit',
                            'purlin:audit → purlin:test'),
             '%s core loop runs out of order' % AGENT),
            (AGENT, replace(' → purlin:sign\n```', '\n```'),
             '%s core loop does not name purlin:sign' % AGENT),
            (AGENT, replace('## Four NEVERs', '```\npurlin:drift → '
                            'purlin:build\n```\n\n## Four NEVERs'),
             '%s states the core loop in 2 fenced blocks, expected 1' % AGENT),
            (AGENT, replace('Every step runs on', 'The loop is purlin:drift → '
                            'purlin:build. Every step runs on'),
             '%s states the core loop 2 times, expected once' % AGENT),
        ]) == []

    # purlin: purlin_agent PROOF-3
    def test_there_are_four_nevers(self):
        assert never_problems() == []

    # purlin: purlin_agent PROOF-3
    def test_a_never_missing_or_misplaced_is_refused(self, monkeypatch):
        moved = ('The one exception is `purlin:test --remote`, which pushes a '
                 'run branch of its own. ')
        assert refusals(monkeypatch, never_problems, [
            (AGENT, replace('4. **Never call', '4. **Never guess.**\n'
                            '5. **Never call'),
             '%s carries 5 NEVERs, expected 4' % AGENT),
            (AGENT, resub(r"^2\. \*\*Never sign on.*?(?=^3\. )"),
             '%s carries 3 NEVERs, expected 4' % AGENT),
            (AGENT, replace('`references/glossary.md` gives it',
                            'the style guide gives it'),
             "%s NEVERs do not name 'references/glossary.md'" % AGENT),
            (AGENT, replace("**Never sign on a person's behalf.**",
                            '**Never guess.**'),
             "%s NEVER 2 does not carry \"Never sign on a person's behalf\""
             % AGENT),
            # The exception taken out of the third NEVER and put in the
            # fourth: every word is still in the section, in the wrong item.
            (AGENT, lambda t: replace(
                'The one exception is `purlin:test --remote`,\n   which '
                'pushes a run branch of its own, waits for it and deletes it. ')(
                t).replace('No emoji anywhere', moved + 'No emoji anywhere', 1),
             "%s NEVER 3 does not carry 'The one exception is `purlin:test "
             "--remote`" % AGENT),
            (AGENT, replace('Never write evidence or a signature by hand',
                            'Never write evidence carelessly'),
             "%s NEVER 1 does not carry 'Never write evidence or a signature "
             "by hand'" % AGENT),
        ]) == []

    # purlin: purlin_agent PROOF-4
    def test_the_routing_table_covers_the_three_roles(self):
        assert routing_problems() == []

    # purlin: purlin_agent PROOF-4
    def test_a_foreign_role_or_command_is_refused(self, monkeypatch):
        export_row = next(line for line in read(COMMAND_REF).splitlines()
                          if line.startswith('| `purlin:export` |'))
        assert refusals(monkeypatch, routing_problems, [
            (AGENT, replace('| QA | "what went stale?"', '| Manager | "how are '
                            'we doing?" | `purlin:status` |\n| QA | "what '
                            'went stale?"'),
             "%s routing table has a row for 'Manager'" % AGENT),
            (AGENT, replace('system of record?" | `purlin:export`',
                            'system of record?" | `purlin:release`'),
             '%s routes to purlin:release, which %s does not list'
             % (AGENT, COMMAND_REF)),
            (AGENT, lambda t: t.replace('| QA |', '| Developer |'),
             "%s routing table has no 'QA' row" % AGENT),
            # The command reference is the list: drop a command from it and
            # the agent's row that routes to it is refused.
            (COMMAND_REF, replace(export_row + '\n'),
             '%s routes to purlin:export, which %s does not list'
             % (AGENT, COMMAND_REF)),
        ]) == []

    # purlin: purlin_agent PROOF-5
    def test_it_reads_the_state_before_it_answers(self):
        assert state_problems() == []

    # purlin: purlin_agent PROOF-5
    def test_a_state_paragraph_broken_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, state_problems, [
            (AGENT, replace('Call `sync_status` before you answer',
                            'Call `sync_status` when you answer'),
             "%s does not carry 'Call `sync_status` before you answer any "
             "question about state.'" % AGENT),
            # `strong` stays in backticks elsewhere in the file.
            (AGENT, replace('`passed`, `strong` and `signed` as far',
                            '`passed` and `signed` as far'),
             "%s sync_status paragraph does not carry '`passed`, `strong` "
             "and `signed`'" % AGENT),
            (AGENT, replace('`out of date` means the spec, the code or the '
                            'tests moved since the run',
                            '`out of date` means the run is old'),
             "%s sync_status paragraph does not carry '`out of date` means "
             "the spec, the code or the tests moved since the run'" % AGENT),
        ]) == []

    # purlin: purlin_agent PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert ceiling_problems(AGENT, 135) == []

    # purlin: purlin_agent PROOF-7
    def test_it_says_what_a_rename_moves(self):
        assert rename_problems() == []

    # purlin: purlin_agent PROOF-7
    def test_a_rename_section_broken_is_refused(self, monkeypatch):
        assert refusals(monkeypatch, rename_problems, [
            (AGENT, replace('every `> Requires:` entry', 'every entry'),
             "%s rename section does not carry '> Requires:'" % AGENT),
            (AGENT, replace('## Renaming a feature', '## Moving a feature'),
             '%s has no Renaming a feature section' % AGENT),
            (AGENT, replace('`specs/<category>/<name>.md` and its', 'and its'),
             "%s rename section does not carry 'specs/<category>/<name>.md'"
             % AGENT),
            (AGENT, replace(' in one commit'),
             "%s rename section does not carry 'moves them together in one "
             "commit'" % AGENT),
            (AGENT, replace('Move files with `git mv`, then call '
                            '`sync_status`:', 'Call `sync_status`, then move '
                            'files with `git mv`:'),
             '%s rename section calls sync_status before git mv' % AGENT),
        ]) == []


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
    ('Never push', 'never open a pull request', 'rewrite a remote branch',
     'The one exception is `purlin:test --remote`, which pushes a run branch '
     'of its own'),
    ('Never call a thing by a name other than the one '
     '`references/glossary.md` gives it',),
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
