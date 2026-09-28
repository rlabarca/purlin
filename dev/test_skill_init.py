"""Text checks for the init skill, `skills/init/SKILL.md`.

Every rule of `specs/skills/skill_init.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import json
import re

from skill_checks import (carries, closing_outcomes, flat,
                          frontmatter_problems, frontmatter_refusals,
                          next_step_problems, next_step_refusals, read,
                          refusals, replace, same_line, section, sections,
                          sentence_with, skill_ceiling_problems, skill_path,
                          table_rows, undirected_outcome_problems)


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
