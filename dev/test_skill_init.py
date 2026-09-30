"""Checks for the init skill, `skills/init/SKILL.md`.

Every rule of `specs/skills/skill_init.md` is proved here, one case to a
test. Most read the skill's text; inside the test of the proof it guards, a
check is also shown to refuse a copy of the skill with one thing broken. The readers, the shared checks
and the broken-copy helpers are in `dev/skill_checks.py`.

Where the skill says what setup does, a test also runs the setup script
itself, `scripts/init/scaffold.py`, in a new git project in a temporary
folder, and holds the skill's words to what the script asks, lists and
writes. The script runs git and nothing else.
"""

import functools
import json
import os
import re
import subprocess
import sys
import tempfile

from skill_checks import (ROOT, closing_outcomes, flat, frontmatter,
                          frontmatter_problems, next_step_problems,
                          next_step_refusals, read, refusals, replace,
                          same_line, section, sections, sentence_with,
                          skill_ceiling_problems, skill_path, table_rows,
                          undirected_outcome_problems, carries, COMMAND_REF)

SKILL = skill_path('init')


# ---------------------------------------------------------------------------
# The setup script, run for real
# ---------------------------------------------------------------------------

SCAFFOLD = ROOT / 'scripts' / 'init' / 'scaffold.py'

# A flag, as a person types it.
FLAG = re.compile(r'(?<![\w-])--[a-z][a-z-]*')


def _child_env():
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    return env


@functools.lru_cache(maxsize=None)
def scaffold_usage():
    """`(exit code, what the setup script prints for --help)`."""
    done = subprocess.run([sys.executable, str(SCAFFOLD), '--help'],
                          capture_output=True, encoding='utf-8', timeout=120,
                          env=_child_env(), stdin=subprocess.DEVNULL)
    return done.returncode, done.stdout


@functools.lru_cache(maxsize=None)
def first_setup(answers):
    """`(exit code, what setup printed, the settings it wrote)` for a first
    setup of a new git project holding a `conftest.py`, so the tree carries a
    framework that has an engine, with `answers` typed in, one per line."""
    with tempfile.TemporaryDirectory(prefix='purlin-skill-init-') as root:
        subprocess.run(['git', 'init', '-q', root], check=True,
                       capture_output=True, timeout=120)
        with open(os.path.join(root, 'conftest.py'), 'w',
                  encoding='utf-8') as handle:
            handle.write('')
        done = subprocess.run(
            [sys.executable, str(SCAFFOLD), '--project-root', root],
            input=answers, capture_output=True, encoding='utf-8',
            timeout=300, env=_child_env())
        path = os.path.join(root, '.purlin', 'config.json')
        config = None
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                config = json.load(handle)
    return done.returncode, done.stdout + done.stderr, config


# The prompts setup waits at: `[<default>]: ` on a line under the question
# and its answers, and ` [y/N] ` ending a yes-or-no question's own line.
PROMPT = re.compile(r'\[[^\]\n]*\]: |(?<= \[y/N\]) ')


def asked(output):
    """`[(question, [answers offered])]`, one per prompt setup waited at: the
    last unindented line before the prompt, `[y/N]` kept where the question
    ends on it, and the indented lines under it."""
    questions = []
    for chunk in PROMPT.split(output)[:-1]:
        lines = [line for line in chunk.splitlines() if line.strip()]
        heads = [n for n, line in enumerate(lines) if not line.startswith(' ')]
        if not heads:
            questions.append(('', []))
            continue
        offered = [line.split()[0] for line in lines[heads[-1] + 1:]]
        questions.append((lines[heads[-1]], offered))
    return questions


def skill_questions():
    """Each numbered question of the skill's section `The questions`, as the
    one quoted span in it that asks something."""
    body = section(read(SKILL), r'^The questions$') or ''
    items = re.split(r'^\d+\. ', body, flags=re.M)[1:]
    return [next((span for span in re.findall(r'`([^`]+)`', flat(item))
                  if '?' in span), '') for item in items]


def skill_settings():
    """The keys of the first settings block the skill shows."""
    blocks = re.findall(r'```json\n(.*?)```', read(SKILL), re.S)
    return sorted(json.loads(blocks[0])) if blocks else None


# ---------------------------------------------------------------------------
# RULE-2: the run line and the flags
# ---------------------------------------------------------------------------

LOOKUP = 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh"'
RUN_PATH = '"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"'

# The five flags RULE-2 names, the forms a person is handed.
SCAFFOLD_FLAGS = ('--project-root', '--gate', '--mutation', '--yes',
                  '--update')


def run_line_problems():
    return same_line(SKILL, [LOOKUP + ' ' + RUN_PATH, '--project-root',
                             '--gate'])


def handed_flags():
    """Every flag on a line that runs the script, and in the first column of
    the flag table."""
    text = read(SKILL)
    handed = []
    for line in text.splitlines():
        if 'scripts/init/scaffold.py' in line:
            handed.extend(FLAG.findall(line))
    for cells in table_rows(text, '| Flag |'):
        handed.extend(FLAG.findall(cells[0]))
    return handed


def five_flag_problems():
    handed = handed_flags()
    return ['%s does not hand a person %s' % (SKILL, flag)
            for flag in SCAFFOLD_FLAGS if flag not in handed]


def usage_problems():
    code, usage = scaffold_usage()
    problems = []
    if code != 0:
        problems.append('scaffold.py --help exited %d' % code)
    takes = set(FLAG.findall(usage))
    for flag in sorted(set(handed_flags()) - takes):
        problems.append('%s names %s, which scaffold.py does not take'
                        % (SKILL, flag))
    return problems


# ---------------------------------------------------------------------------
# RULE-3: the closing section
# ---------------------------------------------------------------------------

STATES = ('No specs and no code', 'Code but no specs', 'Specs but no tests')


def closing_problems():
    outcomes = closing_outcomes(sections(read(SKILL))[-1][1])
    return (next_step_problems('init') + undirected_outcome_problems('init')
            + ['%s closing section has no outcome for %r' % (SKILL, state)
               for state in STATES
               if not any(o.startswith('- ' + state) for o in outcomes)])


# ---------------------------------------------------------------------------
# RULE-5: the questions
# ---------------------------------------------------------------------------

# The three questions init asks, in order, each by the words the skill uses.
INIT_QUESTIONS = (
    'What must be true of every rule before a version is finished?',
    'Measure test strength by breaking the code on purpose?',
    'Commit the files setup wrote? [y/N]',
)


def question_items():
    body = section(read(SKILL), r'^The questions$')
    if body is None:
        return None
    return re.split(r'^\d+\. ', body, flags=re.M)[1:]


def question_problems():
    items = question_items()
    if items is None:
        return ['%s has no section headed The questions' % SKILL]
    if len(items) != len(INIT_QUESTIONS):
        return ['%s names %d questions, expected %d'
                % (SKILL, len(items), len(INIT_QUESTIONS))]
    return ['%s question %r does not carry %r'
            % (SKILL, flat(item)[:40], needle)
            for item, needle in zip(items, INIT_QUESTIONS)
            if needle not in flat(item)]


def mutation_condition_problems():
    items = question_items() or []
    if len(items) < 2:
        return ['%s has no second question' % SKILL]
    return ['%s mutation question does not carry %r' % (SKILL, needle)
            for needle in ('only at', '`signed`',
                           'only where an engine exists', 'The default is no')
            if needle not in flat(items[1])]


def gate_table_problems():
    body = section(read(SKILL), r'^The questions$') or ''
    problems = []
    if 'The first answer is the **gate**, one of two' not in flat(body):
        problems.append('%s does not give the gate as the first answer'
                        % SKILL)
    gates = [cells[0] for cells in table_rows(body, '| Gate |')]
    if gates != ['`passed`', '`signed`']:
        problems.append('%s gives the gates %s as the first answer, expected '
                        '`passed` and `signed`' % (SKILL, gates))
    return problems


def swap_questions(text):
    """The skill with its first two numbered questions in each other's
    place."""
    first = text.index('1. **The gate**')
    second = text.index('2. **Mutation testing**')
    end = text.index('\n3. **Committing**', second)
    one, two = text[first:second].rstrip('\n'), text[second:end]
    return (text[:first] + '1.' + two[2:] + '\n2.' + one[2:] + text[end:])


def commit_question_problems():
    items = question_items() or []
    if len(items) < 3:
        return ['%s has no third question' % SKILL]
    return ['%s commit question does not carry %r' % (SKILL, needle)
            for needle in ('`Commit the files setup wrote? [y/N]`',
                           'The default is no',
                           '`chore(init): set up Purlin at the gate <gate>`')
            if needle not in flat(items[2])]


# The sentence of "Run it" that says how the answers reach the script.
PASS_ANSWERS = (
    'Ask the person each question yourself. Pass `--mutation` when they say '
    'yes to breaking the code on purpose. Pass `--yes` when they say yes to '
    'the commit; otherwise run the script with its input empty, '
    '`< /dev/null`, so every question it would ask takes its default.')


def pass_answers_problems():
    body = section(read(SKILL), r'^Run it$') or ''
    if PASS_ANSWERS in flat(body):
        return []
    return ['%s Run it does not say how the answers reach the script'
            % SKILL]


YES_ROW = ('Takes the default answer to every question and commits the files '
           'setup wrote')


def yes_row_problems():
    rows = [cells for cells in table_rows(read(SKILL), '| Flag |')
            if cells[0] == '`--yes`']
    if [cells[1] for cells in rows] == [YES_ROW]:
        return []
    return ['%s flag table does not say --yes %r' % (SKILL, YES_ROW)]


# ---------------------------------------------------------------------------
# RULE-6: the settings
# ---------------------------------------------------------------------------

# The six keys of the settings file init writes, as RULE-6 names them.
INIT_KEYS = ('version', 'gate', 'mutation_engine', 'audit_parallel', 'tests',
             'ci')


def settings_key_problems():
    shown = skill_settings()
    if shown is None:
        return ['%s shows no settings file' % SKILL]
    return (['%s shows the key %r, which is not one of the six'
             % (SKILL, key) for key in sorted(set(shown) - set(INIT_KEYS))]
            + ['%s does not show the key %r' % (SKILL, key)
               for key in sorted(set(INIT_KEYS) - set(shown))])


def not_asked_problems():
    return sentence_with(SKILL, ['`audit_parallel`', 'is not asked'])


def evidence_problems():
    return sentence_with(SKILL, ['It writes',
                                 '`.purlin/evidence/` with one README'])


# ---------------------------------------------------------------------------
# RULE-7: the tests setting
# ---------------------------------------------------------------------------

def empty_tests_problems():
    return carries(SKILL, [
        "installs nothing in the project's tests",
        'it writes the `tests` setting as an empty list',
        'the first `purlin:test` suggests a command for each test tool it '
        'recognises'])


def pointer_problems():
    return carries(SKILL, ['references/supported_frameworks.md',
                           'references/formats/marker_format.md'])


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

def init_frontmatter():
    return frontmatter_problems('init')


def description_line():
    return 'description: %s' % re.search(
        r'^description:[ \t]*(.*)$', frontmatter(read(SKILL)),
        re.M).group(1).strip()


class TestFrontmatter:

    # purlin: skill_init PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self, monkeypatch):
        assert [p for p in init_frontmatter()
                if not p.startswith(COMMAND_REF)] == []
        value = description_line()[len('description: '):]
        assert refusals(monkeypatch, init_frontmatter, [
            (SKILL, replace('name: init\n'),
             "%s frontmatter name is None, expected 'init'" % SKILL),
            (SKILL, replace(description_line(), 'description:'),
             '%s frontmatter carries no one-line description' % SKILL),
            (SKILL, replace(description_line(), 'description:\n  ' + value),
             '%s frontmatter carries no one-line description' % SKILL),
            (SKILL, replace(description_line(), 'description: |\n  ' + value),
             '%s frontmatter carries no one-line description' % SKILL),
            (SKILL, replace(description_line(),
                            description_line() + '\n  and a second line'),
             '%s frontmatter carries no one-line description' % SKILL),
        ]) == []

    # purlin: skill_init PROOF-16
    def test_the_command_reference_has_a_row_for_init(self, monkeypatch):
        assert [p for p in init_frontmatter()
                if p.startswith(COMMAND_REF)] == []
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if line.startswith('| `purlin:init` |'))
        assert refusals(monkeypatch, init_frontmatter, [
            (COMMAND_REF, replace(row + '\n'),
             '%s carries no row for purlin:init' % COMMAND_REF),
        ]) == []


class TestRunLine:

    # purlin: skill_init PROOF-2
    def test_one_line_runs_the_script_with_the_root_and_the_gate(
            self, monkeypatch):
        assert run_line_problems() == []
        assert refusals(monkeypatch, run_line_problems, [
            (SKILL, replace('--project-root . --gate <gate>',
                            '--project-root .'),
             '%s has no single line carrying all of' % SKILL),
            (SKILL, replace(LOOKUP + ' ' + RUN_PATH + ' --project-root . '
                            '--gate', 'python3 ' + RUN_PATH
                            + ' --project-root . --gate'),
             '%s has no single line carrying all of' % SKILL),
        ]) == []

    # purlin: skill_init PROOF-23
    def test_the_five_flags_are_handed_to_the_reader(self, monkeypatch):
        assert five_flag_problems() == []
        assert refusals(monkeypatch, five_flag_problems, [
            (SKILL, replace('| `--mutation` | Turns mutation testing on '
                            'without asking |\n'),
             '%s does not hand a person --mutation' % SKILL),
        ]) == []

    # purlin: skill_init PROOF-96
    def test_the_yes_row_says_it_commits(self, monkeypatch):
        assert yes_row_problems() == []
        assert refusals(monkeypatch, yes_row_problems, [
            (SKILL, replace(' and commits the files setup wrote |', ' |'),
             '%s flag table does not say --yes' % SKILL),
        ]) == []

    # purlin: skill_init PROOF-95
    def test_run_it_says_how_the_answers_reach_the_script(self, monkeypatch):
        assert pass_answers_problems() == []
        assert refusals(monkeypatch, pass_answers_problems, [
            (SKILL, replace('Pass `--yes` when they say yes to the commit; ',
                            ''),
             '%s Run it does not say how the answers reach the script'
             % SKILL),
        ]) == []

    # purlin: skill_init PROOF-24
    def test_every_flag_handed_is_one_the_script_takes(self, monkeypatch):
        assert usage_problems() == []
        assert refusals(monkeypatch, usage_problems, [
            (SKILL, replace('| `--update` |',
                            '| `--force` | Overwrites every file |\n'
                            '| `--update` |'),
             '%s names --force, which scaffold.py does not take' % SKILL),
        ]) == []


class TestClosingSection:

    # purlin: skill_init PROOF-3
    def test_it_closes_with_a_directive_for_each_state(self, monkeypatch):
        assert sections(read(SKILL))[-1][0] == 'When you are done'
        assert closing_problems() == []
        assert next_step_refusals(
            monkeypatch, 'init', '- Code but no specs',
            '- Code but no specs: `→ Run: purlin:spec-from-code`.') == []


class TestCeiling:

    # purlin: skill_init PROOF-4
    def test_it_is_at_most_250_lines(self, monkeypatch):
        assert skill_ceiling_problems('init') == []

        def grow(text):
            return text + 'More prose.\n' * (251 - len(text.splitlines()))
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('init'), [
            (SKILL, grow, '%s is 251 lines, ceiling 250' % SKILL),
        ]) == []


class TestQuestions:

    # purlin: skill_init PROOF-5
    def test_it_names_the_three_questions_in_order(self, monkeypatch):
        assert question_problems() == []
        assert refusals(monkeypatch, question_problems, [
            (SKILL, replace('2. **Mutation testing**', '2. **Colour**, on '
                            'every first run: which colour.\n'
                            '3. **Mutation testing**'),
             '%s names 4 questions, expected 3' % SKILL),
            (SKILL, swap_questions,
             "does not carry %r" % INIT_QUESTIONS[0]),
        ]) == []

    # purlin: skill_init PROOF-30
    def test_the_second_question_is_asked_only_where_it_runs(
            self, monkeypatch):
        assert mutation_condition_problems() == []
        assert refusals(monkeypatch, mutation_condition_problems, [
            (SKILL, replace(' The default is no.'),
             "%s mutation question does not carry 'The default is no'"
             % SKILL),
        ]) == []

    # purlin: skill_init PROOF-31
    def test_the_gate_table_lists_the_two_answers_in_order(
            self, monkeypatch):
        assert gate_table_problems() == []
        row = next(line for line in read(SKILL).splitlines()
                   if line.startswith('| `signed` |'))
        assert refusals(monkeypatch, gate_table_problems, [
            (SKILL, replace(row + '\n'),
             "%s gives the gates ['`passed`'] as the first answer" % SKILL),
        ]) == []

    # purlin: skill_init PROOF-32
    def test_setup_at_signed_asks_the_three_questions_the_skill_quotes(self):
        code, output, _ = first_setup('signed\n\n')
        assert code == 0, output
        quoted = skill_questions()
        assert len(quoted) == 3
        expected = [quoted[0], quoted[1].replace('<engine>', 'mutmut'),
                    quoted[2]]
        assert [question for question, _ in asked(output)] == expected

    # purlin: skill_init PROOF-33
    def test_setup_at_passed_asks_the_gate_then_the_commit(self):
        code, output, _ = first_setup('passed\n')
        assert code == 0, output
        assert [question for question, _ in asked(output)] == [
            INIT_QUESTIONS[0], INIT_QUESTIONS[2]]

    # purlin: skill_init PROOF-94
    def test_the_third_question_is_the_commit(self, monkeypatch):
        assert commit_question_problems() == []
        assert refusals(monkeypatch, commit_question_problems, [
            (SKILL, replace(' The default is no; a yes commits', ' A yes '
                            'commits'),
             "%s commit question does not carry 'The default is no'"
             % SKILL),
        ]) == []

    # purlin: skill_init PROOF-34
    def test_the_gate_question_offers_the_two_gates_in_order(self):
        code, output, _ = first_setup('signed\n\n')
        assert code == 0, output
        assert asked(output)[0][1] == ['passed', 'signed']

    # purlin: skill_init PROOF-35
    def test_no_answer_to_the_second_question_leaves_mutation_off(self):
        code, output, config = first_setup('signed\n\n')
        assert code == 0, output
        assert config['gate'] == 'signed'
        assert config['mutation_engine'] == 'none'
        assert 'min_strength' not in config, config


class TestSettings:

    # purlin: skill_init PROOF-6
    def test_it_shows_the_six_settings(self, monkeypatch):
        assert settings_key_problems() == []
        assert refusals(monkeypatch, settings_key_problems, [
            (SKILL, replace('  "ci": "github"\n', '  "ci": "github",\n'
                            '  "colour": "blue"\n'),
             "%s shows the key 'colour', which is not one of the six"
             % SKILL),
        ]) == []

    # purlin: skill_init PROOF-38
    def test_setup_writes_the_keys_the_skill_shows(self):
        code, output, config = first_setup('passed\n')
        assert code == 0, output
        assert sorted(config) == skill_settings()

    # purlin: skill_init PROOF-39
    def test_one_sentence_says_audit_parallel_is_not_asked(self, monkeypatch):
        assert not_asked_problems() == []
        # The words still stand in another sentence of the copy.
        assert 'is not asked' in flat(read(SKILL)).replace(
            'is 4 and is not asked;', '')
        assert refusals(monkeypatch, not_asked_problems, [
            (SKILL, replace('is 4 and is not asked;', 'is 4;'),
             "%s has no sentence carrying all of '`audit_parallel`', "
             "'is not asked'" % SKILL),
        ]) == []

    # purlin: skill_init PROOF-40
    def test_one_sentence_says_it_writes_the_evidence_folder(
            self, monkeypatch):
        assert evidence_problems() == []
        assert refusals(monkeypatch, evidence_problems, [
            (SKILL, replace('`.purlin/evidence/` with one README saying',
                            '`.purlin/evidence/`, saying'),
             "%s has no sentence carrying all of 'It writes', "
             "'`.purlin/evidence/` with one README'" % SKILL),
        ]) == []


class TestTestsSetting:

    # purlin: skill_init PROOF-7
    def test_it_writes_an_empty_tests_setting_and_installs_nothing(
            self, monkeypatch):
        assert empty_tests_problems() == []
        assert refusals(monkeypatch, empty_tests_problems, [
            (SKILL, replace('the first `purlin:test` suggests a command for',
                            'the first run fills in'),
             "%s does not carry 'the first `purlin:test` suggests a command "
             "for each test tool it recognises'" % SKILL),
        ]) == []

    # purlin: skill_init PROOF-42
    def test_it_points_at_the_two_references(self, monkeypatch):
        assert pointer_problems() == []
        assert refusals(monkeypatch, pointer_problems, [
            (SKILL, replace('`references/formats/marker_format.md`',
                            'the marker format'),
             "%s does not carry 'references/formats/marker_format.md'"
             % SKILL),
        ]) == []
