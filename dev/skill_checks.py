"""The readers, checks and broken-copy helpers the skill test files share.

Every rule of `specs/skills/*.md` and `specs/instructions/purlin_agent.md` is
proved in one test file per spec, `dev/test_skill_<name>.py` and
`dev/test_purlin_agent.py`, and each of them imports what it uses from here.
This file holds no test and no marker, and pytest does not collect it.

Each check reads one file and returns the problems it found as a list, so
a test body is one assertion and its failure prints what is wrong rather than
`False is not True`.

Prose wraps, so a sentence a skill states over two lines is one string here:
`flat()` collapses runs of whitespace before a prose needle is searched for.
A needle that must sit on one line of the source, such as a fenced command,
goes through `same_line()` instead.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / 'scripts' / 'run'))
from purlin_run import bash_command  # noqa: E402

# The bash a shell test runs under. `bash` on PATH is the Windows
# Subsystem for Linux launcher on a Windows runner, which never reads the
# script, so the run script finds Git Bash and this asks it the same
# question rather than asking it again.
BASH = bash_command()

# Every skill, each with the ceiling its spec sets.
CEILINGS = {
    'anchor': 160, 'audit': 105, 'build': 130, 'drift': 150,
    'export': 90, 'init': 250, 'sign': 185, 'spec': 210,
    'spec-from-code': 130, 'status': 100, 'test': 120,
}
COMMANDS = sorted(CEILINGS)

AGENT = 'agents/purlin.md'

# The three roles, and no others, in the words the routing table uses.
ROLES = ('Product', 'Developer', 'QA')


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def skill_path(name):
    return 'skills/%s/SKILL.md' % name


def flat(text):
    return re.sub(r'\s+', ' ', text)


def frontmatter(text):
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    return match.group(1) if match else None


def field(block, key):
    """The value on the `key:` line itself; a value on the next line is not it."""
    match = re.search(r'^%s:[ \t]*(.*)$' % key, block, re.M)
    return match.group(1).strip() if match else None


def runs_on(block, key):
    """True when the line after `key:` is indented, so the value continues."""
    lines = block.splitlines()
    for number, line in enumerate(lines):
        if line.startswith(key + ':'):
            return lines[number + 1:number + 2] != [] and \
                lines[number + 1][:1] in (' ', '\t')
    return False


def sections(text):
    """`[(heading, body)]` for every `## ` heading, in file order."""
    parts = re.split(r'^## (.+)$', text, flags=re.M)
    return list(zip(parts[1::2], parts[2::2]))


def section(text, pattern):
    for heading, body in sections(text):
        if re.search(pattern, heading, re.I):
            return body
    return None


# ---------------------------------------------------------------------------
# The checks. Each returns a list of problems, empty when the file is right.
# ---------------------------------------------------------------------------

def carries(rel, needles):
    """Prose needles, searched with the file's line wrapping collapsed."""
    text = flat(read(rel))
    return ['%s does not carry %r' % (rel, n) for n in needles if n not in text]


def same_line(rel, needles):
    for line in read(rel).splitlines():
        if all(needle in line for needle in needles):
            return []
    return ['%s has no single line carrying all of %s'
            % (rel, ', '.join(repr(n) for n in needles))]


def in_order(rel, needles, wrapped=False):
    """`wrapped` searches with the file's line wrapping collapsed."""
    text = flat(read(rel)) if wrapped else read(rel)
    problems = ['%s does not carry %r' % (rel, n) for n in needles
                if n not in text]
    if problems:
        return problems
    offsets = [text.index(n) for n in needles]
    if offsets != sorted(offsets):
        return ['%s carries %s out of order, at offsets %s'
                % (rel, ', '.join(repr(n) for n in needles), offsets)]
    return []


def frontmatter_problems(name):
    rel = skill_path(name)
    block = frontmatter(read(rel))
    if block is None:
        return ['%s does not open with a frontmatter block' % rel]
    problems = []
    if field(block, 'name') != name:
        problems.append('%s frontmatter name is %r, expected %r'
                        % (rel, field(block, 'name'), name))
    description = field(block, 'description')
    # `>` and `|`, with or without a chomping sign, open a block scalar; an
    # indented next line continues a plain one. Neither is one line.
    # Empty quotes are an empty value too.
    if (not description or re.fullmatch(r'[>|][+-]?|""|\'\'', description)
            or runs_on(block, 'description')):
        problems.append('%s frontmatter carries no one-line description' % rel)
    command = re.compile(r'`purlin:%s(?: [^`]*)?`$' % re.escape(name))
    # The row counts only with a purpose sentence in its second cell.
    if not any(command.match(cells[0]) and len(cells) > 1 and cells[1]
               for cells in command_rows()):
        problems.append('%s carries no row for purlin:%s' % (COMMAND_REF, name))
    return problems


COMMAND_REF = 'references/purlin_commands.md'
COMMAND_TABLE = '| Command | Purpose |'


def command_rows():
    """The rows of every table in the command reference headed Command, Purpose."""
    chunks = read(COMMAND_REF).split(COMMAND_TABLE)[1:]
    return [cells for chunk in chunks
            for cells in table_rows(COMMAND_TABLE + chunk, COMMAND_TABLE)]


def closing_outcomes(body):
    """Each outcome a closing section lists: a list item with the lines it
    wraps onto, or a table row below the table's header and divider."""
    outcomes, table, item = [], False, False
    for line in body.splitlines():
        if line.startswith('|'):
            if table and not set(line) <= set('|-: '):
                outcomes.append(line)
            table, item = True, False
        elif line.startswith('- '):
            outcomes.append(line)
            table, item = False, True
        elif item and line.startswith('  '):
            outcomes[-1] += ' ' + line.strip()
        else:
            table, item = False, False
    return outcomes


def next_step_problems(name):
    rel = skill_path(name)
    heading, body = sections(read(rel))[-1]
    problems = []
    if not re.search(r'next step|when you are done', heading, re.I):
        problems.append('%s closes with the section %r, which does not name '
                        'the next step' % (rel, heading))
    outcomes = closing_outcomes(body)
    if len(outcomes) < 2:
        problems.append('%s closing section names %d outcomes, expected at '
                        'least 2' % (rel, len(outcomes)))
    if '\u2192' not in body:
        problems.append('%s closing section gives no directive' % rel)
    return problems


NOTHING_LEFT = 'Nothing left to do.'


def undirected_outcome_problems(name):
    """Every outcome of the closing section that gives no `\u2192` directive.

    One outcome is let through with none, the one that reads `Nothing left
    to do.`: at the gate passed a finished project may name no command. A
    second such outcome is reported like any other."""
    rel = skill_path(name)
    body = sections(read(rel))[-1][1]
    undirected = [outcome for outcome in closing_outcomes(body)
                  if '\u2192' not in outcome]
    finished = [outcome for outcome in undirected if NOTHING_LEFT in outcome]
    if finished:
        undirected.remove(finished[0])
    return ['%s closing outcome gives no \u2192 directive: %s' % (rel, outcome)
            for outcome in undirected]


def sentence_with(rel, needles):
    """A problem unless one sentence, line wrapping ignored, carries every needle."""
    sentences = re.split(r'(?<=\.)\s+(?=[A-Z`])', flat(read(rel)))
    if any(all(needle in s for needle in needles) for s in sentences):
        return []
    return ['%s has no sentence carrying all of %s'
            % (rel, ', '.join(repr(n) for n in needles))]


# ---------------------------------------------------------------------------
# Broken copies. A check is shown to refuse by pointing it at a copy of a file
# with one thing broken; the file on disk is never touched.
# ---------------------------------------------------------------------------

def on_copy(monkeypatch, rel, edit, check):
    """What `check()` reports while `rel` reads as `edit` leaves it."""
    real = read
    original = real(rel)
    text = edit(original)
    assert text != original, 'the edit left %s as it was' % rel
    copy = lambda path: text if path == rel else real(path)  # noqa: E731
    with monkeypatch.context() as patch:
        # A check reads through the `read` of the module it is defined in:
        # this one for the shared checks, a test file for its own.
        patch.setitem(globals(), 'read', copy)
        patch.setitem(getattr(check, '__globals__', globals()), 'read', copy)
        return check()


def replace(old, new=''):
    def edit(text):
        assert old in text, 'there is no %r to edit' % old
        return text.replace(old, new, 1)
    return edit


def refusals(monkeypatch, check, cases):
    """`cases` is `[(rel, edit, expected)]`; each copy must report `expected`.
    Returns one line for each copy that did not."""
    missed = []
    for rel, edit, expected in cases:
        problems = on_copy(monkeypatch, rel, edit, check)
        if not any(expected in problem for problem in problems):
            missed.append('a copy of %s expected to report %r reported %r'
                          % (rel, expected, problems))
    return missed


def frontmatter_refusals(monkeypatch, name):
    rel = skill_path(name)
    value = field(frontmatter(read(rel)), 'description')
    line = 'description: %s' % value
    row = next(line for line in read(COMMAND_REF).splitlines()
               if re.match(r'\| `purlin:%s[ `]' % re.escape(name), line))
    return refusals(monkeypatch, lambda: frontmatter_problems(name), [
        (rel, replace('name: %s\n' % name),
         "%s frontmatter name is None, expected %r" % (rel, name)),
        (rel, replace(line, 'description:'),
         '%s frontmatter carries no one-line description' % rel),
        (rel, replace('name: %s\n%s' % (name, line),
                      'description:\nname: %s' % name),
         '%s frontmatter carries no one-line description' % rel),
        (rel, replace(line, 'description: |\n  ' + value),
         '%s frontmatter carries no one-line description' % rel),
        (rel, replace(line, line + '\n  and a second line'),
         '%s frontmatter carries no one-line description' % rel),
        (COMMAND_REF, replace(row + '\n'),
         '%s carries no row for purlin:%s' % (COMMAND_REF, name)),
    ])


def next_step_refusals(monkeypatch, name, second, directed):
    """Four broken copies of the closing section: deleted, every `\u2192` taken
    out of it, cut before `second`, its second outcome, so one is left, and
    the `\u2192` taken out of the one outcome line `directed`."""
    rel = skill_path(name)
    text = read(rel)
    before = sections(text)[-2][0]
    last = text.rindex('\n## ')

    def check():
        return next_step_problems(name) + undirected_outcome_problems(name)
    return refusals(monkeypatch, check, [
        (rel, lambda t: t[:last + 1],
         '%s closes with the section %r' % (rel, before)),
        (rel, lambda t: t[:last] + t[last:].replace('\u2192', '->'),
         '%s closing section gives no directive' % rel),
        (rel, lambda t: t[:t.index(second, last)],
         '%s closing section names 1 outcomes, expected at least 2' % rel),
        (rel, replace(directed, directed.replace('\u2192 ', '')),
         '%s closing outcome gives no \u2192 directive' % rel),
    ])


def ceiling_problems(rel, ceiling):
    count = len(read(rel).splitlines())
    if count > ceiling:
        return ['%s is %d lines, ceiling %d' % (rel, count, ceiling)]
    return []


def skill_ceiling_problems(name):
    return ceiling_problems(skill_path(name), CEILINGS[name])


def table_rows(text, header):
    """The rows of the one table whose header line carries `header`."""
    rows = []
    seen = False
    for line in text.splitlines():
        if not seen:
            seen = header in line
            continue
        if not line.startswith('|'):
            break
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if set(''.join(cells)) <= set('-: '):
            continue
        rows.append(cells)
    return rows


def resub(pattern, new=''):
    """An edit that replaces the first match of `pattern`, a line-anchored,
    dot-matches-newline regular expression."""
    def edit(text):
        return re.sub(pattern, new, text, count=1, flags=re.S | re.M)
    return edit


def swap_first(a, b):
    """An edit that swaps the first `a` with the first `b`."""
    def edit(text):
        assert a in text and b in text, 'there is no %r or %r to swap' % (a, b)
        return text.replace(a, '\0', 1).replace(b, a, 1).replace('\0', b, 1)
    return edit
