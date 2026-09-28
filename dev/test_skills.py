"""Text checks for every skill and the agent definition.

Every rule of `specs/skills/*.md` and `specs/instructions/purlin_agent.md` is
proved here. Each check reads one file and returns the problems it found as a list, so
a test body is one assertion and its failure prints what is wrong rather than
`False is not True`.

Prose wraps, so a sentence a skill states over two lines is one string here:
`flat()` collapses runs of whitespace before a prose needle is searched for.
A needle that must sit on one line of the source, such as a fenced command,
goes through `same_line()` instead.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

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


def undirected_outcome_problems(name):
    """Every outcome of the closing section that gives no `\u2192` directive."""
    rel = skill_path(name)
    body = sections(read(rel))[-1][1]
    return ['%s closing outcome gives no \u2192 directive: %s' % (rel, outcome)
            for outcome in closing_outcomes(body) if '\u2192' not in outcome]


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
    with monkeypatch.context() as patch:
        patch.setitem(globals(), 'read',
                      lambda path: text if path == rel else real(path))
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


# The four questions init asks, in order, each by the words the skill uses.
INIT_QUESTIONS = (
    'What must be true of every rule before a version is proven?',
    'empty repository',
    'Measure test strength by breaking the code on purpose?',
    'trusted',
)


def init_question_problems():
    rel = skill_path('init')
    text = read(rel)
    problems = []
    body = section(text, r'^The questions$')
    if body is None:
        problems.append('%s has no section headed The questions' % rel)
        return problems
    # The three gates are the answers to the first question: the table the
    # section gives right after saying so.
    if 'The first answer is the **gate**, one of three' not in flat(body):
        problems.append('%s does not give the gate as the first answer' % rel)
    gates = [cells[0] for cells in table_rows(body, '| Gate |')]
    if gates != ['`passed`', '`strong`', '`signed`']:
        problems.append('%s gives the gates %s as the first answer, expected '
                        '`passed`, `strong` and `signed`' % (rel, gates))
    items = re.split(r'^\d+\. ', body, flags=re.M)[1:]
    if len(items) != len(INIT_QUESTIONS):
        problems.append('%s names %d questions, expected %d'
                        % (rel, len(items), len(INIT_QUESTIONS)))
        return problems
    for item, needle in zip(items, INIT_QUESTIONS):
        if needle not in flat(item):
            problems.append('%s question %r does not carry %r'
                            % (rel, flat(item)[:40], needle))
    if 'The default is no' not in flat(items[2]):
        problems.append('%s does not say the mutation default is no' % rel)
    for needle in ('What command runs the tests?',
                   'where that command writes its report'):
        if needle not in flat(items[1]):
            problems.append('%s second question does not carry %r'
                            % (rel, needle))
    return problems


# The eight keys of the settings file init writes, as RULE-6 names them.
INIT_KEYS = ('version', 'gate', 'mutation_engine', 'min_strength',
             'audit_parallel', 'tests', 'ci', 'trust')


def init_config_problems():
    rel = skill_path('init')
    text = read(rel)
    blocks = re.findall(r'```json\n(.*?)```', text, re.S)
    if not blocks:
        return ['%s shows no settings file' % rel]
    shown = sorted(json.loads(blocks[0]))
    template = sorted(json.loads(read('templates/config.json')))
    problems = []
    if shown != template:
        problems.append('%s shows the keys %s, the template carries %s'
                        % (rel, shown, template))
    for key in sorted(set(shown) - set(INIT_KEYS)):
        problems.append('%s shows the key %r, which is not one of the eight'
                        % (rel, key))
    for key in sorted(set(INIT_KEYS) - set(shown)):
        problems.append('%s does not show the key %r' % (rel, key))
    return (problems + carries(rel, ['is not asked', '`.purlin/evidence/`',
                                     'one README'])
            + sentence_with(rel, ['`audit_parallel`', 'is not asked'])
            + sentence_with(rel, ['It writes',
                                  '`.purlin/evidence/` with one README']))


def init_tests_setting_problems():
    return carries(skill_path('init'), [
        "installs nothing in the project's tests",
        'For each framework it detects it writes one entry of the `tests` '
        'setting',
        'with the flag that writes the report Purlin reads already in it',
        'Jest needs the package `jest-junit`',
        'references/supported_frameworks.md',
        'references/formats/marker_format.md'])


class TestSkillInit:

    # purlin: skill_init PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('init') == []

    # purlin: skill_init PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'init') == []

    # purlin: skill_init PROOF-2
    def test_it_runs_the_scaffold_script(self):
        assert scaffold_flag_problems() == []

    # purlin: skill_init PROOF-2
    def test_a_flag_missing_or_foreign_is_refused(self, monkeypatch):
        rel = skill_path('init')
        assert refusals(monkeypatch, scaffold_flag_problems, [
            (rel, replace('| `--dry-run` | Prints the plan and writes '
                          'nothing |\n'),
             '%s does not hand a person --dry-run' % rel),
            (rel, replace('| `--dry-run` |',
                          '| `--force` | Overwrites every file |\n'
                          '| `--dry-run` |'),
             '%s names --force, which scaffold.py does not take' % rel),
            (rel, replace('--project-root . --gate <level>',
                          '--project-root .'),
             '%s has no single line carrying all of' % rel),
        ]) == []

    # purlin: skill_init PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        rel = skill_path('init')
        outcomes = closing_outcomes(sections(read(rel))[-1][1])
        problems = ['%s closing section has no outcome for %r' % (rel, state)
                    for state in ('No specs and no code', 'Code but no specs',
                                  'Specs but no tests')
                    if not any(o.startswith('- ' + state) for o in outcomes)]
        assert (next_step_problems('init') + undirected_outcome_problems('init')
                + problems) == []

    # purlin: skill_init PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'init', '- Code but no specs',
            '- Code but no specs: `→ Next: purlin:spec-from-code`.') == []

    # purlin: skill_init PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('init') == []

    # purlin: skill_init PROOF-5
    def test_it_names_the_four_questions_in_order(self):
        assert init_question_problems() == []

    # purlin: skill_init PROOF-5
    def test_a_fifth_question_or_a_missing_gate_is_refused(self, monkeypatch):
        rel = skill_path('init')
        assert refusals(monkeypatch, init_question_problems, [
            (rel, replace('4. **Trust**', '4. **Colour**, on every first '
                          'run: which colour.\n5. **Trust**'),
             '%s names 5 questions, expected 4' % rel),
            (rel, replace('| `strong` | that, and'),
             '%s gives the gates' % rel),
            (rel, replace('What command runs the tests?', 'What runs?'),
             "%s second question does not carry 'What command runs the "
             "tests?'" % rel),
        ]) == []

    # purlin: skill_init PROOF-6
    def test_it_shows_the_eight_settings(self):
        assert init_config_problems() == []

    # purlin: skill_init PROOF-6
    def test_a_ninth_key_or_a_stray_sentence_is_refused(self, monkeypatch):
        rel = skill_path('init')
        assert refusals(monkeypatch, init_config_problems, [
            (rel, replace('  "ci": "github",', '  "ci": "github",\n'
                          '  "colour": "blue",'),
             "%s shows the key 'colour', which is not one of the eight" % rel),
            (rel, replace('is 4 and is not asked;', 'is 4;'),
             "%s has no sentence carrying all of '`audit_parallel`', "
             "'is not asked'" % rel),
        ]) == []

    # purlin: skill_init PROOF-7
    def test_it_writes_the_tests_setting_and_installs_nothing(self):
        assert init_tests_setting_problems() == []

    # purlin: skill_init PROOF-7
    def test_a_missing_jest_sentence_is_refused(self, monkeypatch):
        rel = skill_path('init')
        assert refusals(monkeypatch, init_tests_setting_problems, [
            (rel, replace('Jest needs the package `jest-junit`, installed '
                          'with\n`npm install --save-dev jest-junit`. '),
             "%s does not carry 'Jest needs the package `jest-junit`'" % rel),
        ]) == []


# ---------------------------------------------------------------------------
# skill_spec
# ---------------------------------------------------------------------------

class TestSkillSpec:

    # purlin: skill_spec PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec') == []

    # purlin: skill_spec PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'spec') == []

    # purlin: skill_spec PROOF-2
    def test_it_allocates_ids_against_the_default_branch(self):
        assert spec_id_problems() == []

    # purlin: skill_spec PROOF-2
    def test_a_missing_id_command_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        assert refusals(monkeypatch, spec_id_problems, [
            (rel, resub(r'^```bash\ngit show origin/main:.*?^```\n'),
             "%s does not carry 'git show origin/main:'" % rel),
        ]) == []

    # purlin: skill_spec PROOF-3
    def test_it_closes_by_naming_the_build(self):
        assert spec_offer_problems() == []

    # purlin: skill_spec PROOF-3
    def test_a_broken_offer_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        offer = 'Spec saved: <name>. Next: purlin:build <name>'
        assert refusals(monkeypatch, spec_offer_problems, [
            (rel, replace(offer, 'Spec written. Shall I build it?'),
             '%s closing section does not carry the line %r' % (rel, offer)),
            (rel, replace('```\n%s\n```' % offer, offer),
             '%s closing section does not set the line %r in a fenced block'
             % (rel, offer)),
            (rel, replace(' and nothing after it'),
             '%s closing section does not say nothing follows the line'
             % rel),
            (rel, replace('Never start the build yourself', 'Then build it'),
             '%s closing section does not say it never starts the build'
             % rel),
        ]) == []

    # purlin: skill_spec PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec') == []

    # purlin: skill_spec PROOF-6
    def test_it_prints_the_proofs_and_asks_before_it_saves(self):
        assert spec_review_problems() == []

    # purlin: skill_spec PROOF-6
    def test_a_missing_or_late_print_step_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        assert refusals(monkeypatch, spec_review_problems, [
            (rel, resub(r'^6\. Print each rule.*?(?=^7\. )'),
             "%s does not carry 'Print each rule with its proofs under it "
             "and ask whether to change any'" % rel),
            (rel, swap_first(
                'Print each rule with its proofs under it and ask whether to '
                'change any. Change what the\n   person asks and print them '
                'again.',
                'Save the spec when the person is satisfied, commit it on its '
                'own, and name `purlin:build`\n   as the next step. This '
                'skill never starts building.'),
             '%s procedure saves the spec before it prints the rules' % rel),
            (rel, replace('`references/spec_quality_guide.md`, "Writing '
                          'proofs", the one home', 'the guide, the one home'),
             '%s does not carry \'Draft every proof against' % rel),
        ]) == []

    # purlin: skill_spec PROOF-5
    def test_it_writes_the_scope_on_every_spec(self):
        assert spec_scope_problems() == []

    # purlin: skill_spec PROOF-5
    def test_a_missing_scope_sentence_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        assert refusals(monkeypatch, spec_scope_problems, [
            (rel, resub(r'^Write `> Scope:` on every spec you create:.*?'
                        r'for it\. '),
             "%s does not carry 'Write `> Scope:` on every spec you create'"
             % rel),
            (rel, replace('the files the requirement touches, or '),
             "%s has no sentence carrying all of 'Write `> Scope:` on every "
             "spec you create', 'the files the requirement touches'" % rel),
            (rel, replace('at the gate `signed` its rules', 'its rules'),
             "%s has no sentence carrying all of 'A spec that names no "
             "files'" % rel),
            (rel, replace('4. Write the metadata, `> Scope:` included,',
                          '4. Write the metadata,'),
             '%s procedure does not name > Scope: in the metadata step'
             % rel),
        ]) == []


def resub(pattern, new=''):
    """An edit that replaces the first match of `pattern`, a line-anchored,
    dot-matches-newline regular expression."""
    def edit(text):
        return re.sub(pattern, new, text, count=1, flags=re.S | re.M)
    return edit


def spec_id_problems():
    return carries(skill_path('spec'), [
        'git show origin/main:',
        'allocated against `origin/main`, not against the working tree'])


def spec_scope_problems():
    rel = skill_path('spec')
    problems = carries(rel, [
        'Write `> Scope:` on every spec you create',
        'the paths `purlin:build` will create', 'every run includes it',
        'its rules cannot be signed'])
    problems += sentence_with(rel, [
        'Write `> Scope:` on every spec you create',
        'the files the requirement touches',
        'the paths `purlin:build` will create'])
    problems += sentence_with(rel, [
        'A spec that names no files', 'every run includes it',
        'at the gate `signed` its rules cannot be signed'])
    step = re.search(r'^\d+\. Write the metadata.*$', read(rel), re.M)
    if step is None or '`> Scope:`' not in step.group(0):
        problems.append('%s procedure does not name > Scope: in the '
                        'metadata step' % rel)
    return problems


def spec_review_problems():
    rel = skill_path('spec')
    printing = ('Print each rule with its proofs under it and ask whether to '
                'change any')
    saving = 'Save the spec when the person is satisfied'
    problems = carries(rel, [
        printing, saving,
        'Draft every proof against `references/spec_quality_guide.md`, '
        '"Writing proofs"', 'at least one failure case'])
    body = section(read(rel), r'^Procedure$') or ''
    steps = [flat(item) for item in re.split(r'^\d+\. ', body, flags=re.M)[1:]]
    at = {needle: next((n for n, step in enumerate(steps) if needle in step),
                       None) for needle in (printing, saving)}
    if None in at.values():
        problems.append('%s procedure does not hold both the print step and '
                        'the save step' % rel)
    elif at[printing] > at[saving]:
        problems.append('%s procedure saves the spec before it prints the '
                        'rules' % rel)
    return problems


def spec_offer_problems():
    rel = skill_path('spec')
    heading, body = sections(read(rel))[-1]
    problems = []
    if not re.search(r'next step|when you are done', heading, re.I):
        problems.append('%s closes with the section %r, which does not name '
                        'the next step' % (rel, heading))
    offer = 'Spec saved: <name>. Next: purlin:build <name>'
    if offer not in body.splitlines():
        problems.append('%s closing section does not carry the line %r on its '
                        'own' % (rel, offer))
    fences = re.findall(r'^```[a-z]*\n(.*?)^```', body, re.S | re.M)
    if not any(offer in fence.splitlines() for fence in fences):
        problems.append('%s closing section does not set the line %r in a '
                        'fenced block' % (rel, offer))
    if 'end with exactly this and nothing after it' not in flat(body):
        problems.append('%s closing section does not say nothing follows the '
                        'line' % rel)
    if 'Never start the build yourself' not in flat(body):
        problems.append('%s closing section does not say it never starts '
                        'the build' % rel)
    return problems


# ---------------------------------------------------------------------------
# skill_spec_from_code
# ---------------------------------------------------------------------------

class TestSkillSpecFromCode:

    # purlin: skill_spec_from_code PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-2
    def test_it_reads_the_state_before_it_starts(self):
        assert spec_from_code_start_problems() == []

    # purlin: skill_spec_from_code PROOF-2
    def test_a_late_or_unconditional_start_is_refused(self, monkeypatch):
        rel = skill_path('spec-from-code')
        start = re.search(r'^## Before you start\n.*?(?=^## )', read(rel),
                          re.S | re.M).group(0)
        assert refusals(monkeypatch, spec_from_code_start_problems, [
            (rel, replace(start),
             '%s has no section that runs before the survey' % rel),
            (rel, lambda t: t.replace(start, '').replace(
                '## What the rules look like', start +
                '## What the rules look like'),
             '%s start section comes after the Procedure section' % rel),
            (rel, replace('When the project has no `.purlin/config.json`, run',
                          'Read `.purlin/config.json`, then run'),
             '%s start section does not send the reader to purlin:init '
             'when .purlin/config.json is missing' % rel),
        ]) == []

    # purlin: skill_spec_from_code PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('spec-from-code')
                + undirected_outcome_problems('spec-from-code')) == []

    # purlin: skill_spec_from_code PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'spec-from-code', '- Rules with no test at all',
            '- Rules with no test at all: `→ Next: purlin:build <name>` on '
            'the feature with the most of') == []

    # purlin: skill_spec_from_code PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-5
    def test_every_rule_it_writes_is_at_the_passed_level(self):
        assert spec_from_code_tag_problems() == []

    # purlin: skill_spec_from_code PROOF-5
    def test_a_rule_above_passed_or_no_stated_level_is_refused(
            self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_tag_problems, [
            (rel, replace('HTTP 429 [level: passed]', 'HTTP 429 [level: strong]'),
             '%s example rule carries no [level: passed]: - RULE-1' % rel),
            (rel, resub(r'^- RULE-.*?\n(?=\n)'),
             '%s shows no example rule' % rel),
            (rel, replace('Every rule this skill writes carries '
                          '`[level: passed]`:', 'For example:'),
             "does not carry 'Every rule this skill writes carries "
             "`[level: passed]`'"),
        ]) == []

    # purlin: skill_spec_from_code PROOF-6
    def test_it_ties_an_existing_test_by_its_marker(self):
        assert spec_from_code_marker_problems() == []

    # purlin: skill_spec_from_code PROOF-6
    def test_a_partial_test_marked_or_an_untied_offer_is_refused(
            self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_marker_problems, [
            (rel, replace('test; leave it unmarked and let', 'test; let'),
             "has no sentence carrying all of 'A test that shows part of "
             "what the proof asks', 'is not that test', 'leave it unmarked'"),
            (rel, replace('never names the test. Then tie the two:',
                          'never names the test.\n\nThen tie the two:'),
             '%s does not offer the marker, and write no new test, in the '
             'paragraph on a test that already shows the proof' % rel),
        ]) == []


def spec_from_code_start_problems():
    rel = skill_path('spec-from-code')
    body = section(read(rel), r'before you start')
    if body is None:
        return ['%s has no section that runs before the survey' % rel]
    flattened = flat(body)
    problems = ['%s start section does not name %r' % (rel, needle)
                for needle in ('sync_status', '.purlin/config.json',
                               'purlin:init')
                if needle not in flattened]
    headings = [heading for heading, _ in sections(read(rel))]
    if 'Procedure' not in headings or \
            headings.index('Before you start') > headings.index('Procedure'):
        problems.append('%s start section comes after the Procedure section'
                        % rel)
    if ('When the project has no `.purlin/config.json`, run `purlin:init` '
            'first') not in flattened:
        problems.append('%s start section does not send the reader to '
                        'purlin:init when .purlin/config.json is missing'
                        % rel)
    return problems


def spec_from_code_marker_problems():
    rel = skill_path('spec-from-code')
    problems = carries(rel, [
        'offer to add the marker comment above that test',
        'purlin: <feature> PROOF-<n>', 'write no new test',
        'is not that test'])
    problems += sentence_with(rel, [
        'A test that shows part of what the proof asks', 'is not that test',
        'leave it unmarked'])
    # The offer belongs to the case of a test that already shows the proof.
    paragraphs = [flat(p) for p in read(rel).split('\n\n')]
    if not any('already shows what a proof asks' in p
               and 'offer to add the marker comment above that test' in p
               and 'write no new test' in p for p in paragraphs):
        problems.append('%s does not offer the marker, and write no new '
                        'test, in the paragraph on a test that already shows '
                        'the proof' % rel)
    return problems


def spec_from_code_tag_problems():
    rel = skill_path('spec-from-code')
    problems = []
    examples = [line for line in read(rel).splitlines()
                if line.startswith('- RULE-')]
    if not examples:
        problems.append('%s shows no example rule' % rel)
    for line in examples:
        if '[level: passed]' not in line:
            problems.append('%s example rule carries no [level: passed]: %s'
                            % (rel, line))
    problems.extend(carries(rel, [
        'Every rule this skill writes carries `[level: passed]`',
        'Do not write `[level: strong]` or `[level: signed]`']))
    return problems


# ---------------------------------------------------------------------------
# skill_anchor
# ---------------------------------------------------------------------------

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
        assert next_step_problems('anchor') == []

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


# ---------------------------------------------------------------------------
# skill_build
# ---------------------------------------------------------------------------

class TestSkillBuild:

    # purlin: skill_build PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('build') == []

    # purlin: skill_build PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'build') == []

    # purlin: skill_build PROOF-2
    def test_it_reads_the_state_and_runs_the_tests_through_the_test_skill(self):
        assert build_command_problems() == []

    # purlin: skill_build PROOF-2
    def test_a_test_framework_run_directly_is_refused(self, monkeypatch):
        rel = skill_path('build')
        assert refusals(monkeypatch, build_command_problems, [
            (rel, replace('```bash\npurlin:test <name>\n```',
                          '```bash\npython3 -m pytest tests/\n```'),
             "%s gives the test framework's own command" % rel),
            (rel, replace('```bash\npurlin:test <name>\n```',
                          '```bash\npython3 -m pytest tests/\n```'),
             '%s section on running the tests gives no fenced line '
             "'purlin:test <name>'" % rel),
            (rel, replace('```bash\npurlin:build [<name>]\n```',
                          '```bash\nnpx jest\n```'),
             "%s gives the test framework's own command" % rel),
        ]) == []

    # purlin: skill_build PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('build') == []

    # purlin: skill_build PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('build') == []

    # purlin: skill_build PROOF-7
    def test_it_looks_for_an_existing_test_before_it_writes_one(self):
        assert build_marker_problems() == []

    # purlin: skill_build PROOF-7
    def test_writing_before_looking_is_refused(self, monkeypatch):
        rel = skill_path('build')
        text = read(rel)
        look = text[text.index('1. **Look first'):text.index('2. **Otherwise')]
        writes = ' with the marker above it.\n'

        def swapped(t):
            t = t.replace(look, '', 1)
            return t.replace(writes, writes + look, 1)
        assert refusals(monkeypatch, build_marker_problems, [
            (rel, swapped, 'out of order, at offsets'),
            (rel, replace("the project's own framework, in the folder"),
             '%s does not carry %r' % (rel, BUILD_STEPS[2])),
            (rel, replace('it names the rule: `purlin: login RULE-2`',
                          '`purlin: login RULE-2`'),
             'Where a rule has no proof'),
        ]) == []

    # purlin: skill_build PROOF-6
    def test_it_keeps_the_scope_in_the_commit_with_the_code(self):
        rel = skill_path('build')
        body = section(read(rel), r'^committing')
        assert body is not None, '%s has no Committing section' % rel
        text = flat(body)
        missing = [needle for needle in (
            'compare the files you created, changed or deleted for the '
            'feature with its `> Scope:`',
            'add each new file no entry covers',
            'remove each entry whose file you deleted',
            'rewrite the line in the same commit as the code')
            if needle not in text]
        assert missing == [], missing

    # purlin: skill_build PROOF-5
    def test_the_commit_body_contract_holds(self):
        result = subprocess.run(
            [BASH, 'dev/test_e2e_build_changeset.sh'], cwd=str(ROOT),
            capture_output=True, text=True)
        assert (result.returncode, '  ok:' in result.stdout) == (0, True), \
            result.stdout + result.stderr

    # purlin: skill_build PROOF-5
    def test_changeset_is_never_left_out(self):
        rel = skill_path('build')
        when = {cells[0]: cells[-1] for cells in table_rows(
            read('references/commit_conventions.md'), '| Section |')}
        problems = sentence_with(rel, ['Changeset is never omitted.'])
        problems.extend(sentence_with(rel, [
            'Omit Decisions when every rule had one obvious implementation',
            'omit Review when nothing needs a second pair of eyes']))
        if when.get('Changeset') != 'Never':
            problems.append('references/commit_conventions.md leaves Changeset '
                            'out %r, expected Never' % when.get('Changeset'))
        assert problems == []


def build_command_problems():
    rel = skill_path('build')
    text = read(rel)
    body = section(text, r'choosing what to build')
    problems = []
    if body is None or 'sync_status' not in body:
        problems.append('%s does not read the state with sync_status before it '
                        'chooses what to build' % rel)
    running = section(text, r'^running') or ''
    fenced = [line for fence in re.findall(r'```\w*\n(.*?)```', running, re.S)
              for line in fence.splitlines()]
    if 'purlin:test <name>' not in fenced:
        problems.append('%s section on running the tests gives no fenced line '
                        "'purlin:test <name>'" % rel)
    if 'Never run the test framework directly.' not in flat(running):
        problems.append('%s section on running the tests does not say '
                        "'Never run the test framework directly.'" % rel)
    for fence in re.findall(r'```\w*\n(.*?)```', text, re.S):
        for line in fence.splitlines():
            if FRAMEWORK_COMMAND.match(line):
                problems.append("%s gives the test framework's own command: %s"
                                % (rel, line))
    return problems


# A line that runs a test framework itself rather than through purlin:test.
FRAMEWORK_COMMAND = re.compile(
    r'\s*(?:python3? -m |npx |bunx )?(?:pytest|jest|vitest|mocha|go test|'
    r'npm test|npm run test|yarn test|dotnet test|cargo test|mvn test|'
    r'gradle test|bun test)\b')

# The steps for a proof with no marked test, in the order the skill takes them.
BUILD_STEPS = (
    'for each proof with no test marked for it',
    '**Look first for a test that already shows it.**',
    "**Otherwise write an ordinary test** in the project's own framework, in "
    'the folder and the style its other tests use')


def build_marker_problems():
    rel = skill_path('build')
    problems = in_order(rel, BUILD_STEPS, wrapped=True)
    problems.extend(carries(rel, [
        'offer to add the marker above it and write nothing new']))
    problems.extend(sentence_with(rel, [
        'Where a rule has no proof',
        'it names the rule: `purlin: login RULE-2`']))
    if '# purlin: login PROOF-1\ndef test_' not in read(rel):
        problems.append('%s shows no marker above a test' % rel)
    return problems


# ---------------------------------------------------------------------------
# skill_test
# ---------------------------------------------------------------------------

class TestSkillTest:

    # purlin: skill_test PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('test') == []

    # purlin: skill_test PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'test') == []

    # purlin: skill_test PROOF-2
    def test_it_runs_the_run_script_and_names_its_exit_codes(self):
        assert run_line_problems() == []

    # purlin: skill_test PROOF-2
    def test_a_broken_exit_code_line_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, run_line_problems, [
            (rel, replace(', `2` the invocation', ',\n`2` the invocation'),
             "%s has no single line carrying all of 'Exit codes:'" % rel),
            (rel, replace('`1` a test failed, evidence is missing or a marker '
                          'names nothing a spec has', '`1` something failed'),
             "%s has no single line carrying all of 'Exit codes:'" % rel),
            (rel, replace('purlin_run.py" --test', 'purlin_run.py"'),
             '%s has no single line carrying all of '
             '\'"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"\', '
             "'--test'" % rel),
        ]) == []

    # purlin: skill_test PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('test')
                + undirected_outcome_problems('test')) == []

    # purlin: skill_test PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'test', '| A rule reads `partial`',
            '| A test failed | `→ Run: purlin:build <feature>` (fix the code '
            'or the test) |') == []

    # purlin: skill_test PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('test') == []

    # purlin: skill_test PROOF-5
    def test_it_names_the_evidence_the_commit_and_the_gate_line(self):
        assert evidence_line_problems() == []

    # purlin: skill_test PROOF-5
    def test_a_missing_gate_line_form_is_refused(self, monkeypatch):
        rel = skill_path('test')
        assert refusals(monkeypatch, evidence_line_problems, [
            (rel, replace(', or\n`gate <gate> not met: <n> of <rules> rules '
                          'meet it`'),
             "%s does not carry 'gate <gate> not met" % rel),
            (rel, replace('counts the rules that meet the gate',
                          'is printed'),
             "'counts the rules that meet the gate'"),
            (rel, replace('rules` is the check', 'rules` is printed'),
             "'`gate passed met: <n> of <rules> rules` is the check'"),
        ]) == []

    # purlin: skill_test PROOF-6
    def test_it_says_what_a_run_with_no_feature_named_runs(self):
        assert selection_problems() == []

    # purlin: skill_test PROOF-6
    def test_a_selection_paragraph_broken_is_refused(self, monkeypatch):
        rel = skill_path('test')
        nothing = ("With nothing selected it prints `Nothing to run: every "
                   "feature's spec, code and tests match its evidence.`")
        assert refusals(monkeypatch, selection_problems, [
            (rel, replace('purlin:test --all               Run every '
                          'feature\n'),
             '%s usage does not name purlin:test --all' % rel),
            (rel, lambda t: resub(r'With nothing selected it prints '
                                  r'`Nothing to run:.*?anyway\.` ')(t)
             + '\n' + nothing + '\n',
             "%s paragraph on a run with no feature named does not carry "
             "\"Nothing to run" % rel),
            (rel, replace('under its `> Scope:` or beside its tests',
                          'in the project'),
             '%s paragraph on a run with no feature named does not carry '
             "'with an untracked file under its `> Scope:`" % rel),
        ]) == []


def run_line_problems():
    rel = skill_path('test')
    return (same_line(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--test'])
        + same_line(rel, [
            'Exit codes:', '`0`', '`1`', '`2`', 'whatever the gate line says',
            '`0` no test failed and no marker is wrong, whatever the gate '
            'line says',
            '`1` a test failed, evidence is missing or a marker names nothing '
            'a spec has',
            '`2` the invocation was wrong'])
        + carries(rel, ['cannot make an audit or a signature appear']))


def evidence_line_problems():
    rel = skill_path('test')
    return (carries(rel, [
        '.purlin/evidence/local/<feature>.json', '.purlin/tests.md',
        '--commit', 'purlin: evidence at <sha7>', 'Evidence committed.',
        'Evidence unchanged.', 'Tests: <p> of <rules> rules pass.',
        'gate <gate> met: <n> of <rules> rules',
        'gate <gate> not met: <n> of <rules> rules meet it',
        'gate passed met: <n> of <rules> rules', 'It never pushes.'])
        + sentence_with(rel, [
            '`gate <gate> met: <n> of <rules> rules`',
            '`gate <gate> not met: <n> of <rules> rules meet it`',
            'counts the rules that meet the gate'])
        + sentence_with(rel, [
            'At `passed`',
            '`gate passed met: <n> of <rules> rules` is the check']))


# The run with no feature named, in the words of the paragraph that says so.
TEST_SELECTION = (
    'with no run on this operating system',
    'whose spec, code or tests changed since its evidence',
    'with an untracked file under its `> Scope:` or beside its tests',
    'whose spec names no files', 'runs only the test files',
    'purlin:test --all runs them too.',
    "Nothing to run: every feature's spec, code and tests match its "
    'evidence.',
)


def selection_problems():
    rel = skill_path('test')
    text = read(rel)
    usage = section(text, r'^usage')
    problems = [] if usage and 'purlin:test --all' in usage else [
        '%s usage does not name purlin:test --all' % rel]
    problems.extend(carries(rel, [
        'no run on this operating system', 'changed since its evidence',
        'untracked file', 'names no files', 'runs only the test files',
        'purlin:test --all runs them too.',
        "Nothing to run: every feature's spec, code and tests match its "
        'evidence.']))
    paragraph = next((flat(p) for p in re.split(r'\n\s*\n', text)
                      if 'With neither, the run selects' in flat(p)), None)
    if paragraph is None:
        return problems + ['%s has no paragraph on a run with no feature '
                           'named' % rel]
    return problems + ['%s paragraph on a run with no feature named does not '
                       'carry %r' % (rel, needle)
                       for needle in TEST_SELECTION if needle not in paragraph]


# ---------------------------------------------------------------------------
# skill_audit
# ---------------------------------------------------------------------------

class TestSkillAudit:

    # purlin: skill_audit PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('audit') == []

    # purlin: skill_audit PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'audit') == []

    # purlin: skill_audit PROOF-2
    def test_it_runs_the_run_script_and_leaves_ci_to_ci(self):
        assert audit_run_problems() == []

    # purlin: skill_audit PROOF-2
    def test_a_run_line_or_a_runner_sentence_broken_is_refused(
            self, monkeypatch):
        rel = skill_path('audit')
        assert refusals(monkeypatch, audit_run_problems, [
            (rel, replace('purlin_run.py" --audit', 'purlin_run.py"\n--audit'),
             '%s has no single line carrying all of' % rel),
            (rel, replace('; you never run it by hand.', '.'),
             "'you never run it by hand'"),
            (rel, replace('runs no audit; you never run it by hand.',
                          'runs no audit. Then you never run it by hand.'),
             '%s has no sentence carrying all of' % rel),
        ]) == []

    # purlin: skill_audit PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('audit')
                + undirected_outcome_problems('audit')) == []

    # purlin: skill_audit PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'audit', '| Test strength below',
            '| A test failed | `→ Run: purlin:build <feature>` |') == []

    # purlin: skill_audit PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('audit') == []

    # purlin: skill_audit PROOF-5
    def test_it_says_which_evidence_counts_under_which_gate(self):
        assert evidence_source_problems() == []

    # purlin: skill_audit PROOF-6
    def test_the_gate_decides_the_breaks_and_the_audit_writes_the_evidence(self):
        assert audit_gate_problems() == []

    # purlin: skill_audit PROOF-6
    def test_a_gate_row_or_a_gate_sentence_broken_is_refused(
            self, monkeypatch):
        rel = skill_path('audit')
        assert refusals(monkeypatch, audit_gate_problems, [
            (rel, replace('not measured; '),
             "%s passed row does not name 'not measured'" % rel),
            (rel, replace('Runs the tests and the AI audit, and no breaks',
                          'Runs the tests, and no breaks'),
             '%s passed row does not say the run reads the rules with the '
             'AI audit' % rel),
            (rel, replace('| The same as `strong`.', '| Runs the tests.'),
             '%s signed row does not run what the strong row runs' % rel),
            (rel, replace('`--commit`, which commits', '`--commit`. That '
                          'commits'),
             "%s has no sentence carrying all of 'you add `--commit`'" % rel),
            (rel, replace(', so a rule waiting on one does not set the code.',
                          '.'),
             "%s has no sentence carrying all of 'An audit cannot make a "
             "signature appear'" % rel),
            (rel, replace('counts here too', 'counts'),
             "%s does not say 'counts here too'" % rel),
        ]) == []

    # purlin: skill_audit PROOF-7
    def test_it_names_the_evidence_and_the_retention(self):
        assert audit_evidence_problems() == []

    # purlin: skill_audit PROOF-7
    def test_a_retention_or_evidence_sentence_broken_is_refused(
            self, monkeypatch):
        rel = skill_path('audit')
        assert refusals(monkeypatch, audit_evidence_problems, [
            (rel, resub(r'^A file keeps the newest section.*?git log`\. '),
             "%s does not carry 'the newest section per operating system'"
             % rel),
            (rel, replace('into\n`.purlin/evidence/local/', 'into\n'
                          '`.purlin/evidence/ci/'),
             "%s does not carry 'into `.purlin/evidence/local/<feature>"
             ".json`'" % rel),
            (rel, replace(' and the newest audit entry per rule'),
             "%s has no sentence carrying all of 'A file keeps the newest "
             "section per operating system', 'the newest audit entry per "
             "rule'" % rel),
            (rel, replace('so `--remote` belongs to', 'so use'),
             "%s does not carry '`--remote` belongs to `purlin:test "
             "--remote`'" % rel),
        ]) == []


# Every flag `scripts/init/scaffold.py` takes a person may type. A flag the
# skill hands a person that the script does not take is an invocation the
# script exits 2 on.
SCAFFOLD_FLAGS = ('--project-root', '--gate', '--mutation', '--yes',
                  '--update', '--add', '--dry-run')


def scaffold_flag_problems():
    rel = skill_path('init')
    problems = carries(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"'] +
        list(SCAFFOLD_FLAGS))
    text = read(rel)
    # The flags a person is handed for scaffold.py: every one on a line that
    # runs the script, and the first cell of each row of the flag table.
    handed = []
    for line in text.splitlines():
        if 'scripts/init/scaffold.py' in line:
            handed.extend(re.findall(r'(?<![\w-])--[a-z][a-z-]*', line))
    for cells in table_rows(text, '| Flag |'):
        handed.extend(re.findall(r'(?<![\w-])--[a-z][a-z-]*', cells[0]))
    for flag in sorted(set(handed) - set(SCAFFOLD_FLAGS)):
        problems.append('%s names %s, which scaffold.py does not take'
                        % (rel, flag))
    for flag in SCAFFOLD_FLAGS:
        if flag not in handed:
            problems.append('%s does not hand a person %s' % (rel, flag))
    # The run itself passes the project root and the gate.
    problems.extend(same_line(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"', '--project-root',
        '--gate']))
    return problems


def audit_run_problems():
    rel = skill_path('audit')
    return (same_line(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--audit'])
        + sentence_with(rel, [
            'A remote runner runs the same script in an arm of its own',
            'you never run it by hand']))


def evidence_source_problems():
    rel = skill_path('audit')
    rows = {cells[0]: cells[-1]
            for cells in table_rows(read(rel), '| Source |')}
    problems = []
    for source in ('ci', 'local'):
        if source not in rows:
            problems.append('%s source table has no %r row' % (rel, source))
    if problems:
        return problems
    for gate in ('passed', 'strong', 'signed'):
        if gate not in rows['ci']:
            problems.append('%s ci row does not count under %r' % (rel, gate))
    for gate in ('passed', 'strong', 'signed'):
        if gate not in rows['local']:
            problems.append('%s local row does not count under %r'
                            % (rel, gate))
    for folder in ('.purlin/evidence/ci/', '.purlin/evidence/local/'):
        if folder not in read(rel):
            problems.append('%s does not name %r' % (rel, folder))
    return problems


def audit_gate_problems():
    rel = skill_path('audit')
    rows = {cells[0]: cells[-1] for cells in table_rows(read(rel), '| Gate |')}
    problems = []
    for gate in ('`passed`', '`strong`', '`signed`'):
        if gate not in rows:
            problems.append('%s gate table has no %s row' % (rel, gate))
    if problems:
        return problems
    for needle in ('not measured', 'Nothing blocks at the gate passed.'):
        if needle not in rows['`passed`']:
            problems.append('%s passed row does not name %r' % (rel, needle))
    if 'the AI audit' not in rows['`passed`']:
        problems.append('%s passed row does not say the run reads the rules '
                        'with the AI audit' % rel)
    for needle in ('breaks', 'minimum'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    if 'The same as `strong`' not in rows['`signed`']:
        problems.append('%s signed row does not run what the strong row runs'
                        % rel)
    for needle in ('counts here too', 'Audit: <n> strong, <n> weak.',
                   'gate strong met: <n> of <rules> rules',
                   'cannot make a signature appear',
                   'purlin: evidence at <sha7>'):
        if needle not in flat(read(rel)):
            problems.append('%s does not say %r' % (rel, needle))
    problems += sentence_with(rel, ['you add `--commit`',
                                    'the subject `purlin: evidence at <sha7>`'])
    problems += sentence_with(rel, ['An audit cannot make a signature appear',
                                    'a rule waiting on one does not set the '
                                    'code'])
    return problems


def audit_evidence_problems():
    rel = skill_path('audit')
    return (carries(rel, [
        'into `.purlin/evidence/local/<feature>.json`',
        'the newest section per operating system', 'purlin:test --remote',
        '`--remote` belongs to `purlin:test --remote`'])
        + sentence_with(rel, [
            'A file keeps the newest section per operating system',
            'the newest audit entry per rule']))


# ---------------------------------------------------------------------------
# skill_sign
# ---------------------------------------------------------------------------

class TestSkillSign:

    # purlin: skill_sign PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('sign') == []

    # purlin: skill_sign PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'sign') == []

    # purlin: skill_sign PROOF-2
    def test_it_shows_what_the_audit_found_before_it_writes_the_signature(self):
        assert sign_queue_problems() == []

    # purlin: skill_sign PROOF-2
    def test_a_signature_before_the_audit_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_queue_problems, [
            (rel, swap_first(SIGN_SCRIPTS[0], SIGN_SCRIPTS[1]),
             'out of order, at offsets'),
            (rel, replace(SIGN_SCRIPTS[0], '"scripts/review/ai_audit.py"'),
             '%s does not carry %r' % (rel, SIGN_SCRIPTS[0])),
            (rel, replace('```\nsync_status()\n```\n'),
             '%s does not read payload.queue from sync_status' % rel),
        ]) == []

    # purlin: skill_sign PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('sign')
                + undirected_outcome_problems('sign')) == []

    # purlin: skill_sign PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'sign', '| Rules still in the queue',
            '| A case was added | `→ Run: purlin:build <feature>` |') == []

    # purlin: skill_sign PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('sign') == []

    # purlin: skill_sign PROOF-5
    def test_a_signature_counts_on_a_signed_commit_and_its_hashes(self):
        assert sign_count_problems() == []

    # purlin: skill_sign PROOF-5
    def test_a_missing_condition_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        text = read(rel)
        rows = [line for line in text.splitlines()
                if any(line.startswith('| ' + c) for c in SIGN_COUNTS)]

        def out_of_the_table(t):
            t = t.replace(rows[0] + '\n', '', 1)
            return t.replace('Nothing else is read.',
                             SIGN_COUNTS[0] + '. Nothing else is read.', 1)
        assert refusals(monkeypatch, sign_count_problems, [
            (rel, replace(rows[0] + '\n'), repr(SIGN_COUNTS[0])),
            (rel, out_of_the_table, repr(SIGN_COUNTS[0])),
            (rel, replace(rows[1] + '\n'), repr(SIGN_COUNTS[1])),
            (rel, replace('whoever last committed to the test file',
                          'whoever committed last'),
             'does not say the signature counts'),
        ]) == []

    # purlin: skill_sign PROOF-6
    def test_the_walk_takes_one_of_three_answers(self):
        assert sign_answer_problems() == []

    # purlin: skill_sign PROOF-7
    def test_it_says_what_each_gate_leaves_it_able_to_do(self):
        assert sign_gate_problems() == []

    # purlin: skill_sign PROOF-7
    def test_a_gate_row_broken_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        passed = next(line for line in read(rel).splitlines()
                      if line.startswith('| `passed` |'))
        assert refusals(monkeypatch, sign_gate_problems, [
            (rel, replace(passed + '\n'),
             '%s gate table has no `passed` row' % rel),
            (rel, replace(' and stops without writing anything',
                          ' and writes nothing'),
             "%s passed row does not name 'stops'" % rel),
            (rel, replace('Every rule whose level is `signed` has to carry a '
                          'signature before it meets the gate; '),
             "%s signed row does not name 'Every rule whose level" % rel),
            (rel, replace('| The walk and `--note` work.', '| `--note` works.'),
             "%s strong row does not name 'The walk and `--note` work'" % rel),
        ]) == []

    # purlin: skill_sign PROOF-8
    def test_the_tag_carries_the_evidence_package_and_nothing_is_pushed(self):
        assert sign_tag_problems() == []

    # purlin: skill_sign PROOF-8
    def test_a_broken_tag_section_is_refused(self, monkeypatch):
        rel = skill_path('sign')
        assert refusals(monkeypatch, sign_tag_problems, [
            (rel, swap_first(SIGN_PACKAGE_LINE, SIGN_TAG_LINE),
             '%s tag section prints the tag line before the package line'
             % rel),
            (rel, replace('package `.purlin/evidence/package/<version>.json`',
                          'package'),
             "'.purlin/evidence/package/<version>.json'"),
            (rel, replace(' Below `signed` it writes no\ntag and no package,',
                          ' Past that,'),
             "'Below `signed` it writes no tag and no package'"),
            (rel, replace('commits it as a\nsigned commit', 'commits it'),
             "'commits it as a signed commit'"),
            (rel, replace('on\nthat commit', 'on\nthe next commit'),
             "'on that commit'"),
        ]) == []


def swap_first(a, b):
    """An edit that swaps the first `a` with the first `b`."""
    def edit(text):
        assert a in text and b in text, 'there is no %r or %r to swap' % (a, b)
        return text.replace(a, '\0', 1).replace(b, a, 1).replace('\0', b, 1)
    return edit


# The script that shows what the audit found, and the one that signs.
SIGN_SCRIPTS = ('"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"',
                '"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"')


def sign_queue_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'the queue') or ''
    problems = []
    # The queue is what the sync_status call returns: the call, then the key.
    if not re.search(r'sync_status\(\).*payload\.queue', body, re.S):
        problems.append('%s does not read payload.queue from sync_status in '
                        'its section on the queue' % rel)
    return problems + in_order(rel, SIGN_SCRIPTS)


# The two things that make a signature count under `signed`.
SIGN_COUNTS = (
    'The commit that added the file is signed and the signature verifies',
    'Its bound hashes still match the rule, the proof, the test and what the '
    'audit found')


def sign_count_problems():
    rel = skill_path('sign')
    text = read(rel)
    conditions = [cells[0] for cells in table_rows(
        text, '| Under `signed` the signature counts when |')]
    problems = ['%s table Under `signed` the signature counts when has no row '
                '%r' % (rel, condition)
                for condition in SIGN_COUNTS if condition not in conditions]
    problems.extend('%s table Under `signed` the signature counts when has a '
                    'third row %r' % (rel, condition)
                    for condition in conditions if condition not in SIGN_COUNTS)
    body = section(text, r'when a signature counts') or ''
    if ('the signature counts whoever wrote it, whoever last committed to the '
            'test file, and on whatever branch carries it') not in flat(body):
        problems.append('%s does not say the signature counts whoever wrote '
                        'it, whoever last committed to the test file, and on '
                        'whatever branch carries it' % rel)
    return problems


SIGN_PACKAGE_LINE = ('Evidence package committed: '
                     '.purlin/evidence/package/1.4.0.json.')
SIGN_TAG_LINE = ('Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate '
                 'signed.')


def sign_tag_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'the tag')
    if body is None:
        return ['%s has no section on the tag' % rel]
    problems = ['%s tag section does not carry %r' % (rel, needle)
                for needle in ('At the gate `signed`, when the walk '
                               'leaves every rule meeting it',
                               '.purlin/evidence/package/<version>.json',
                               'commits it as a signed commit',
                               'writes a signed tag',
                               'on that commit',
                               'The tag is `signed/<version>`',
                               'Below `signed` it writes no tag and no '
                               'package',
                               'this skill never pushes')
                if needle not in flat(body)]
    lines = body.splitlines()
    if SIGN_PACKAGE_LINE not in lines or SIGN_TAG_LINE not in lines:
        problems.append('%s tag section does not print %r above %r'
                        % (rel, SIGN_PACKAGE_LINE, SIGN_TAG_LINE))
    elif lines.index(SIGN_PACKAGE_LINE) > lines.index(SIGN_TAG_LINE):
        problems.append('%s tag section prints the tag line before the '
                        'package line' % rel)
    return problems


def sign_answer_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'three answers')
    if body is None:
        return ["%s has no section naming the walk's answers" % rel]
    flattened = flat(body)
    problems = ['%s answers do not name %r' % (rel, label)
                for label in ('**Sign.**', '**Add a case.**', '**Skip.**')
                if label not in flattened]
    if 'A skipped rule is in the queue again next time' not in flattened:
        problems.append('%s answers do not say a skipped rule comes back' % rel)
    return problems


def sign_gate_problems():
    rel = skill_path('sign')
    rows = {cells[0]: cells[-1] for cells in table_rows(read(rel), '| Gate |')}
    problems = []
    for gate in ('`passed`', '`strong`', '`signed`'):
        if gate not in rows:
            problems.append('%s gate table has no %s row' % (rel, gate))
    if problems:
        return problems
    for needle in ('purlin:init --gate strong', 'stops'):
        if needle not in rows['`passed`']:
            problems.append('%s passed row does not name %r' % (rel, needle))
    for needle in ('The walk and `--note` work', '--note', 'hand check'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    if '[level: passed]' not in rows['`signed`']:
        problems.append('%s signed row does not name [level: passed]' % rel)
    needle = 'Every rule whose level is `signed` has to carry a signature'
    if needle not in rows['`signed`']:
        problems.append('%s signed row does not name %r' % (rel, needle))
    return problems


# ---------------------------------------------------------------------------
# skill_status, skill_drift
# ---------------------------------------------------------------------------

class TestSkillStatus:

    # purlin: skill_status PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('status') == []

    # purlin: skill_status PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        rel = skill_path('status')
        assert frontmatter_refusals(monkeypatch, 'status') == []
        assert refusals(monkeypatch, lambda: frontmatter_problems('status'), [
            (rel, resub(r'^description: [^\n]*$', 'description: ""'),
             '%s frontmatter carries no one-line description' % rel),
        ]) == []

    # purlin: skill_status PROOF-2
    def test_it_prints_the_numbers_the_tool_returned(self):
        assert status_number_problems() == []

    # purlin: skill_status PROOF-2
    def test_a_recount_is_refused(self, monkeypatch):
        rel = skill_path('status')
        assert refusals(monkeypatch, status_number_problems, [
            (rel, replace('Print the numbers `sync_status` returned.',
                          'Count the rules in the table yourself.'),
             "does not carry 'Print the numbers `sync_status` returned. "
             "Never recount them"),
        ]) == []

    # purlin: skill_status PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('status')
                + undirected_outcome_problems('status')) == []

    # purlin: skill_status PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'status', '| A rule has a failing test',
            '| A rule is weak | `→ Next: run purlin:build. <n> rules are '
            'weak.` |') == []

    # purlin: skill_status PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('status') == []

    # purlin: skill_status PROOF-5
    def test_naming_a_spec_shows_its_rules(self):
        assert status_name_problems() == []

    # purlin: skill_status PROOF-5
    def test_a_name_that_matches_several_or_none_is_refused_as_unhandled(
            self, monkeypatch):
        rel = skill_path('status')
        assert refusals(monkeypatch, status_name_problems, [
            (rel, replace('list them and ask which one', 'take the first'),
             "With a name section does not carry 'when several match, list "
             "them and ask which one'"),
            (rel, replace('print the whole table', 'print nothing'),
             "With a name section does not carry 'when none does, print "
             "the whole table'"),
            (rel, replace('its path, its\nheader, and one line per rule',
                          'one line per rule'),
             "With a name section does not carry 'print its path, its "
             "header, and one line per rule with the cells the gate "
             "creates'"),
        ]) == []


def status_number_problems():
    return carries(skill_path('status'), [
        'sync_status', 'Never recount them', 'one answer from one computation',
        'Print the numbers `sync_status` returned. Never recount them: the '
        'command line and the dashboard must show one answer from one '
        'computation.'])


def status_name_problems():
    rel = skill_path('status')
    problems = (carries(rel, [
        'purlin:status <name>',
        'Naming a spec shows its rules and their standing.'])
        + carries('references/purlin_commands.md', ['purlin:status [name]']))
    body = flat(section(read(rel), r'^With a name$') or '')
    problems.extend('%s With a name section does not carry %r' % (rel, needle)
                    for needle in (
                        'when several match, list them and ask which one',
                        'when none does, print the whole table',
                        'print its path, its header, and one line per rule '
                        'with the cells the gate creates')
                    if needle not in body)
    return problems


class TestSkillDrift:

    # purlin: skill_drift PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('drift') == []

    # purlin: skill_drift PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        rel = skill_path('drift')
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:drift [role]` |'))
        assert frontmatter_refusals(monkeypatch, 'drift') == []
        assert refusals(monkeypatch, lambda: frontmatter_problems('drift'), [
            (rel, resub(r'^description: [^\n]*$', 'description: >-'),
             '%s frontmatter carries no one-line description' % rel),
            (rel, lambda t: '\n' + t,
             '%s does not open with a frontmatter block' % rel),
            (COMMAND_REF, replace(row, '| `purlin:drift [role]` | |'),
             '%s carries no row for purlin:drift' % COMMAND_REF),
        ]) == []

    # purlin: skill_drift PROOF-2
    def test_it_takes_its_data_from_the_tool(self):
        assert (carries(skill_path('drift'), [
            'drift(role="eng")', 'references/drift_criteria.md',
            'do not restate them here and do not invent a line the tool '
            'does not return']) + drift_restated_problems()) == []

    # purlin: skill_drift PROOF-2
    def test_a_restated_criterion_is_refused(self, monkeypatch):
        rel = skill_path('drift')
        source = 'Rules whose passed cell reads `no test`'
        assert refusals(monkeypatch, drift_restated_problems, [
            (rel, replace('## Step 2: print the view',
                          'A rule with no test: %s.\n\n## Step 2: print the '
                          'view' % source),
             '%s restates what references/drift_criteria.md says a line is '
             'built from: %r' % (rel, source)),
        ]) == []

    # purlin: skill_drift PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('drift')
                + undirected_outcome_problems('drift')) == []

    # purlin: skill_drift PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        rel = skill_path('drift')
        last = read(rel).rindex('\n## ')
        assert next_step_refusals(
            monkeypatch, 'drift', '| A rule removed',
            '| A rule removed | `→ Run: purlin:status <feature>` |') == []
        # A table with its header and divider and no row lists no outcome.
        assert refusals(monkeypatch, lambda: next_step_problems('drift'), [
            (rel, lambda t: t[:t.index('| A rule added', last)],
             '%s closing section names 0 outcomes, expected at least 2'
             % rel),
        ]) == []

    # purlin: skill_drift PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('drift') == []


def drift_restated_problems():
    """The skill restates none of the git facts the criteria say each `eng`
    and `qa` line is built from, the `From` cell of their tables."""
    rel, criteria = skill_path('drift'), 'references/drift_criteria.md'
    header = '| Key | From | Line |'
    sources = [cells[1] for chunk in read(criteria).split(header)[1:]
               for cells in table_rows(header + chunk, header)]
    if len(sources) < 2:
        return ['%s has %d rows naming what a line is built from, expected '
                'the eng and qa tables' % (criteria, len(sources))]
    text = flat(read(rel))
    return ['%s restates what %s says a line is built from: %r'
            % (rel, criteria, source) for source in sources
            if flat(source) in text]


# ---------------------------------------------------------------------------
# skill_export
# ---------------------------------------------------------------------------

class TestSkillExport:

    # purlin: skill_export PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('export') == []

    # purlin: skill_export PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'export') == []

    # purlin: skill_export PROOF-2
    def test_it_runs_the_script_in_each_form(self):
        assert export_command_problems() == []

    # purlin: skill_export PROOF-2
    def test_a_missing_form_or_run_line_is_refused(self, monkeypatch):
        rel = skill_path('export')
        run = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"'
        assert refusals(monkeypatch, export_command_problems, [
            (rel, resub(r'^purlin:export {2,}.*\n'),
             '%s has no usage line for the bare form purlin:export' % rel),
            (rel, replace('purlin:export --check <file>      Check',
                          'Check'),
             '%s has no usage line for the form purlin:export --check '
             '<file>' % rel),
            (rel, lambda t: t.replace(run, 'Run scripts/export/package.py'),
             '%s has no line that runs %s' % (rel, run)),
        ]) == []

    # purlin: skill_export PROOF-3
    def test_it_makes_no_claim_of_compliance(self):
        assert carries(skill_path('export'), [
            'Purlin makes no claim that the software is compliant.',
            'evidence for review in a regulated document and sign-off '
            'system']) == []

    # purlin: skill_export PROOF-4
    def test_it_names_the_three_states(self):
        assert export_state_problems() == []

    # purlin: skill_export PROOF-4
    def test_another_state_for_the_signer_is_refused(self, monkeypatch):
        rel = skill_path('export')
        assert refusals(monkeypatch, export_state_problems, [
            (rel, replace('whose state is `signed`:',
                          'whose state is `gate <gate> met`:'),
             "does not carry 'Only `purlin:sign` writes a package whose "
             "state is `signed`'"),
        ]) == []

    # purlin: skill_export PROOF-5
    def test_it_closes_by_naming_the_next_step(self):
        assert export_outcome_problems() == []

    # purlin: skill_export PROOF-5
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        rel = skill_path('export')
        assert next_step_refusals(
            monkeypatch, 'export', '| `work in progress` | `→ Run',
            '| `signed` | `→ Hand .purlin/evidence/package/<version>.json '
            'to the system of record.` |') == []
        assert refusals(monkeypatch, export_outcome_problems, [
            (rel, replace('| `--check` named a mismatch | `→ Export the '
                          'package again at its tag: purlin:export` |\n'),
             '%s closing section has no row for %r'
             % (rel, '`--check` named a mismatch')),
        ]) == []

    # purlin: skill_export PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('export') == []


def export_command_problems():
    rel = skill_path('export')
    text = read(rel)
    problems = carries(rel, [
        'scripts/export/package.py', 'purlin:export --release <name>',
        'purlin:export --commit', 'purlin:export --check <file>'])
    # Each form opens a usage line of its own, its gloss two spaces on.
    for form in ('', ' --release <name>', ' --commit', ' --check <file>'):
        if not re.search(r'^purlin:export%s(?: {2,}\S.*)?$' % re.escape(form),
                         text, re.M):
            problems.append('%s has no usage line for the %s' % (
                rel, 'form purlin:export' + form if form
                else 'bare form purlin:export'))
    run = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"'
    if not re.search(r'^%s' % re.escape(run), text, re.M):
        problems.append('%s has no line that runs %s' % (rel, run))
    return problems


def export_state_problems():
    return carries(skill_path('export'), [
        '`work in progress`', '`gate <gate> met`', '`signed`',
        'Only `purlin:sign` writes a package whose state is `signed`'])


# Each outcome of the export's closing table, and the directive its row gives.
EXPORT_OUTCOMES = {
    'Evidence not committed': '`→ Run: purlin:test --commit`',
    '`work in progress`': '`→ Run: purlin:status`',
    '`gate <gate> met` at the gate `signed`': '`→ Run: purlin:sign`',
    '`signed`': '`→ Hand .purlin/evidence/package/<version>.json to the '
                'system of record.`',
    '`--check` named a mismatch': '`→ Export the package again at its tag: '
                                  'purlin:export`',
}


def export_outcome_problems():
    rel = skill_path('export')
    problems = (next_step_problems('export')
                + undirected_outcome_problems('export'))
    rows = [[cell.strip() for cell in row.strip('|').split('|')]
            for row in closing_outcomes(sections(read(rel))[-1][1])]
    for outcome, directive in EXPORT_OUTCOMES.items():
        if [outcome, directive] not in rows:
            problems.append('%s closing section has no row for %r' % (
                rel, outcome))
    return problems


# ---------------------------------------------------------------------------
# purlin_agent
# ---------------------------------------------------------------------------

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


