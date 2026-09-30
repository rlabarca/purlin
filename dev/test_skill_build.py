"""Text checks for the build skill, `skills/build/SKILL.md`.

Every rule of `specs/skills/skill_build.md` is proved here, one case to a
test. Each test also points its check at copies of the file with one thing
broken, which the check must refuse; the file on disk is never touched. The readers and the checks
this file shares with the other skill test files are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, closing_outcomes, flat, frontmatter_problems,
                          frontmatter_refusals, in_order, next_step_problems,
                          read, refusals, replace, resub, section, sections,
                          sentence_with, skill_ceiling_problems, skill_path,
                          table_rows, undirected_outcome_problems)

SKILL = skill_path('build')
CONVENTIONS = 'references/commit_conventions.md'


class TestSkillBuild:

    # purlin: skill_build PROOF-1
    def test_the_frontmatter_names_the_skill_and_the_reference_lists_it(
            self, monkeypatch):
        assert frontmatter_problems('build') == []
        assert frontmatter_refusals(monkeypatch, 'build') == []

    # purlin: skill_build PROOF-2
    def test_it_reads_the_state_and_runs_the_tests_through_the_test_skill(
            self, monkeypatch):
        assert build_command_problems() == []
        pytest_fence = replace('```bash\npurlin:test <name>\n```',
                               '```bash\npython3 -m pytest tests/\n```')
        assert refusals(monkeypatch, build_command_problems, [
            (SKILL, pytest_fence,
             "%s gives the test framework's own command: python3 -m pytest "
             'tests/' % SKILL),
            (SKILL, pytest_fence,
             "%s section on running the tests gives no fenced line "
             "'purlin:test <name>'" % SKILL),
            (SKILL, replace('```bash\npurlin:build [<name>]\n```',
                            '```bash\nnpx jest\n```'),
             "%s gives the test framework's own command: npx jest" % SKILL),
            (SKILL, resub(r'call `sync_status` with `project_root` set to the '
                          r'project root, the top folder of\nthe git checkout, '
                          r'and read the state', 'read the state'),
             '%s does not read the state with sync_status before it chooses '
             'what to build' % SKILL),
        ]) == []

    # purlin: skill_build PROOF-3
    def test_it_closes_by_naming_the_next_step_for_each_outcome(
            self, monkeypatch):
        assert closing_problems() == []
        assert refusals(monkeypatch, closing_problems, [
            (SKILL, replace(', `\u2192 Run: purlin:build <feature>`'),
             '%s closing outcome gives no \u2192 directive: - Some rules still '
             'have no test' % SKILL),
            (SKILL, replace(NEXT_STEP_SOURCE, 'Name the next step:'),
             '%s closing section does not say to name the next step from '
             "purlin:test's summary and Left to do" % SKILL),
            (SKILL, replace('`Nothing left to do.`',
                            '`\u2192 Run: git push`'),
             '%s closing section does not end a finished project at passed '
             'and strong on Nothing left to do.' % SKILL),
        ]) == []

    # purlin: skill_build PROOF-4
    def test_it_stays_under_its_ceiling(self, monkeypatch):
        assert skill_ceiling_problems('build') == []

        def to_131(text):
            return text + 'A line of prose.\n' * max(
                1, 131 - len(text.splitlines()))
        assert refusals(monkeypatch, lambda: skill_ceiling_problems('build'), [
            (SKILL, to_131, '%s is 131 lines, ceiling 130' % SKILL),
        ]) == []

    # purlin: skill_build PROOF-5
    def test_the_commit_it_asks_for_is_named_in_full(self, monkeypatch):
        assert commit_problems() == []
        assert refusals(monkeypatch, commit_problems, [
            (SKILL, replace('open with `Changeset:`,', 'open with'),
             "%s Committing section does not carry '`Changeset:`'" % SKILL),
        ]) == []

    # purlin: skill_build PROOF-35
    def test_changeset_is_never_left_out(self, monkeypatch):
        assert changeset_problems() == []
        assert refusals(monkeypatch, changeset_problems, [
            (CONVENTIONS,
             replace('for every rule the commit addresses | Never |',
                     'for every rule the commit addresses | When empty |'),
             "%s leaves Changeset out 'When empty', expected Never"
             % CONVENTIONS),
        ]) == []

    # purlin: skill_build PROOF-36
    def test_decisions_and_review_are_left_out_when_empty(self):
        assert omission_problems() == []

    # purlin: skill_build PROOF-37
    def test_the_conventions_render_a_build_commit(self, monkeypatch):
        assert example_problems() == []
        assert refusals(monkeypatch, example_problems, [
            (CONVENTIONS, replace('\nChangeset:\nRULE-1', '\nRULE-1'),
             "%s example has no 'Changeset:' line before its mapped lines"
             % CONVENTIONS),
        ]) == []

    # purlin: skill_build PROOF-6
    def test_it_keeps_the_scope_in_the_commit_with_the_code(
            self, monkeypatch):
        assert scope_problems() == []
        assert refusals(monkeypatch, scope_problems, [
            (SKILL, replace('remove each entry whose file you deleted, '),
             "%s Committing section does not carry 'remove each entry whose "
             "file you deleted'" % SKILL),
        ]) == []

    # purlin: skill_build PROOF-7
    def test_it_looks_for_an_existing_test_before_it_writes_one(
            self, monkeypatch):
        assert step_problems() == []

        def swapped(text):
            look = text[text.index('1. **Look first'):
                        text.index('2. **Otherwise')]
            writes = ' with the marker above it.\n'
            text = text.replace(look, '', 1)
            return text.replace(writes, writes + look, 1)
        assert refusals(monkeypatch, step_problems, [
            (SKILL, swapped, 'out of order, at offsets'),
            (SKILL, replace("the project's own framework, in the folder"),
             '%s does not carry %r' % (SKILL, BUILD_STEPS[2])),
        ]) == []

    # purlin: skill_build PROOF-40
    def test_its_example_shows_the_marker_above_a_test(self):
        assert example_marker_problems() == []

    # purlin: skill_build PROOF-41
    def test_a_rule_with_no_proof_is_marked_with_its_own_id(
            self, monkeypatch):
        assert no_proof_problems() == []
        assert refusals(monkeypatch, no_proof_problems, [
            (SKILL, replace('it names the rule: `purlin: login RULE-2`',
                            '`purlin: login RULE-2`'),
             "%s has no sentence carrying all of 'Where a rule has no proof', "
             "'it names the rule: `purlin: login RULE-2`'" % SKILL),
        ]) == []

    # purlin: skill_build PROOF-46
    def test_it_reads_the_state_at_the_project_root(self, monkeypatch):
        assert root_problems() == []
        assert refusals(monkeypatch, root_problems, [
            (SKILL, resub(r' with `project_root` set to the project root, the '
                          r'top folder of\nthe git checkout,'),
             '%s section on choosing what to build does not carry %r'
             % (SKILL, ROOT_CALL)),
        ]) == []

    # purlin: skill_build PROOF-9
    def test_it_repairs_the_comments_that_are_nearly_markers(
            self, monkeypatch):
        assert near_miss_problems() == []

        def moved(text):
            repair = text[text.index('## Repairing'):text.index('## Running')]
            text = text.replace(repair, '', 1)
            return text.replace('## Committing', repair + '## Committing', 1)
        assert refusals(monkeypatch, near_miss_problems, [
            (SKILL, replace(' --near-misses --project-root .',
                            ' --project-root .'),
             '%s gives no line that finds the comments that are nearly '
             'markers' % SKILL),
            (SKILL, moved,
             'which does not come before the section on running the tests'),
        ]) == []

    # purlin: skill_build PROOF-11
    def test_the_test_run_sets_the_test_command(self, monkeypatch):
        assert command_setting_problems() == []
        assert refusals(monkeypatch, command_setting_problems, [
            (SKILL, replace('so write no entry yourself.',
                            'so write the entry with the `purlin_config` '
                            'tool.'),
             "%s names the 'purlin_config' tool" % SKILL),
        ]) == []


# ---------------------------------------------------------------------------
# Choosing what to build and running the tests
# ---------------------------------------------------------------------------

# A line that runs a test framework itself rather than through purlin:test.
FRAMEWORK_COMMAND = re.compile(
    r'\s*(?:python3? -m |npx |bunx )?(?:pytest|jest|vitest|mocha|go test|'
    r'npm test|npm run test|yarn test|dotnet test|cargo test|mvn test|'
    r'gradle test|bun test)\b')


def build_command_problems():
    text = read(SKILL)
    body = section(text, r'choosing what to build')
    problems = []
    if body is None or 'sync_status' not in body:
        problems.append('%s does not read the state with sync_status before it '
                        'chooses what to build' % SKILL)
    running = section(text, r'^running') or ''
    fenced = [line for fence in re.findall(r'```\w*\n(.*?)```', running, re.S)
              for line in fence.splitlines()]
    if 'purlin:test <name>' not in fenced:
        problems.append('%s section on running the tests gives no fenced line '
                        "'purlin:test <name>'" % SKILL)
    if 'Never run the test framework directly.' not in flat(running):
        problems.append('%s section on running the tests does not say '
                        "'Never run the test framework directly.'" % SKILL)
    for fence in re.findall(r'```\w*\n(.*?)```', text, re.S):
        for line in fence.splitlines():
            if FRAMEWORK_COMMAND.match(line):
                problems.append("%s gives the test framework's own command: %s"
                                % (SKILL, line))
    return problems


ROOT_CALL = ('call `sync_status` with `project_root` set to the project root, '
             'the top folder of the git checkout')


def root_problems():
    body = flat(section(read(SKILL), r'choosing what to build') or '')
    if ROOT_CALL in body:
        return []
    return ['%s section on choosing what to build does not carry %r'
            % (SKILL, ROOT_CALL)]


def command_setting_problems():
    running = flat(section(read(SKILL), r'^running') or '')
    problems = ['%s section on running the tests does not carry %r'
                % (SKILL, needle) for needle in (
                    'where no test command is set it suggests one for each '
                    'test tool it recognises and writes them once the person '
                    'confirms',
                    'write no entry yourself')
                if needle not in running]
    if 'purlin_config' in read(SKILL):
        problems.append("%s names the 'purlin_config' tool" % SKILL)
    return problems


# ---------------------------------------------------------------------------
# The closing section
# ---------------------------------------------------------------------------

NEXT_STEP_SOURCE = ('`purlin:test` ended on the summary and `Left to do`. '
                    'Name the next step from them:')


def closing_problems():
    problems = next_step_problems('build') + undirected_outcome_problems('build')
    body = sections(read(SKILL))[-1][1]
    if NEXT_STEP_SOURCE not in flat(body):
        problems.append('%s closing section does not say to name the next step '
                        "from purlin:test's summary and Left to do" % SKILL)
    finished = [outcome for outcome in closing_outcomes(body)
                if '`passed`' in outcome and '`strong`' in outcome
                and outcome.endswith(': `Nothing left to do.`')]
    if not finished:
        problems.append('%s closing section does not end a finished project '
                        'at passed and strong on Nothing left to do.' % SKILL)
    return problems


# ---------------------------------------------------------------------------
# The commit
# ---------------------------------------------------------------------------

def committing():
    body = section(read(SKILL), r'^committing')
    return flat(body) if body is not None else None


def commit_problems():
    body = committing()
    if body is None:
        return ['%s has no Committing section' % SKILL]
    return ['%s Committing section does not carry %r' % (SKILL, needle)
            for needle in (
                'One commit per build', 'the `feat(<name>):` prefix',
                'The body has three sections, which open with',
                '`Changeset:`', '`Decisions:`', '`Review:`',
                '`RULE-N → file:line`',
                '`references/commit_conventions.md` carries the exact '
                'rendering; follow it')
            if needle not in body]


def left_out():
    """When the conventions leave each section of a build commit out."""
    return {cells[0]: cells[-1] for cells in
            table_rows(read(CONVENTIONS), '| Section |')}


def changeset_problems():
    problems = sentence_with(SKILL, ['Changeset is never omitted.'])
    when = left_out().get('Changeset')
    if when != 'Never':
        problems.append('%s leaves Changeset out %r, expected Never'
                        % (CONVENTIONS, when))
    return problems


def omission_problems():
    problems = sentence_with(SKILL, [
        'Omit Decisions when every rule had one obvious implementation',
        'omit Review when nothing needs a second pair of eyes'])
    when = left_out()
    for name, expected in (
            ('Decisions', 'When every rule had one obvious implementation'),
            ('Review', 'When nothing needs a second pass')):
        if when.get(name) != expected:
            problems.append('%s leaves %s out %r, expected %r'
                            % (CONVENTIONS, name, when.get(name), expected))
    return problems


def example_problems():
    body = section(read(CONVENTIONS), r'^the build commit body')
    fences = re.findall(r'```\w*\n(.*?)```', body or '', re.S)
    if not fences:
        return ['%s shows no build commit' % CONVENTIONS]
    lines = fences[0].splitlines()
    problems = []
    if not re.match(r'feat\([a-z0-9_]+\): ', lines[0]):
        problems.append('%s example opens %r, not feat(<name>):'
                        % (CONVENTIONS, lines[0]))
    mapped = [n for n, line in enumerate(lines) if line.startswith('RULE-')]
    if not mapped:
        problems.append('%s example maps no rule' % CONVENTIONS)
    problems.extend('%s example line %r is not RULE-N → file:line'
                    % (CONVENTIONS, lines[n]) for n in mapped
                    if not re.match(r'RULE-\d+ → \S+:\d+(\s|$)', lines[n]))
    named = re.findall(r'RULE-\d+', lines[0])
    problems.extend('%s example names %s in its subject and maps it nowhere'
                    % (CONVENTIONS, rule) for rule in named
                    if not any(lines[n].startswith(rule + ' ')
                               for n in mapped))
    if mapped and not any(line == 'Changeset:' for line in lines[:mapped[0]]):
        problems.append("%s example has no 'Changeset:' line before its "
                        'mapped lines' % CONVENTIONS)
    for heading in ('Decisions:', 'Review:'):
        if heading not in lines or (mapped and
                                    lines.index(heading) < mapped[-1]):
            problems.append('%s example has no %r section after its '
                            'changeset' % (CONVENTIONS, heading))
    return problems


def scope_problems():
    body = committing()
    if body is None:
        return ['%s has no Committing section' % SKILL]
    return ['%s Committing section does not carry %r' % (SKILL, needle)
            for needle in (
                'compare the files you created, changed or deleted for the '
                'feature with its `> Scope:`',
                'add each new file no entry covers',
                'remove each entry whose file you deleted',
                'rewrite the line in the same commit as the code')
            if needle not in body]


# ---------------------------------------------------------------------------
# The tests it writes and the markers above them
# ---------------------------------------------------------------------------

# The steps for a proof with no marked test, in the order the skill takes them.
BUILD_STEPS = (
    'for each proof with no test marked for it',
    '**Look first for a test that already shows it.**',
    "**Otherwise write an ordinary test** in the project's own framework, in "
    'the folder and the style its other tests use')


def step_problems():
    return (in_order(SKILL, BUILD_STEPS, wrapped=True)
            + carries(SKILL, [
                'offer to add the marker above it and write nothing new']))


def example_marker_problems():
    if '# purlin: login PROOF-1\ndef test_' not in read(SKILL):
        return ['%s shows no marker above a test' % SKILL]
    return []


def no_proof_problems():
    return sentence_with(SKILL, [
        'Where a rule has no proof',
        'it names the rule: `purlin: login RULE-2`'])


# ---------------------------------------------------------------------------
# Repairing the comments that are nearly markers
# ---------------------------------------------------------------------------

# The one line that finds the comments that are nearly markers.
NEAR_MISSES = ('sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" '
               '"${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" '
               '--near-misses --project-root .')


def near_miss_problems():
    text = read(SKILL)
    headings = [heading for heading, _body in sections(text)]
    problems = []
    found = [heading for heading, body in sections(text)
             for fence in re.findall(r'```\w*\n(.*?)```', body, re.S)
             if NEAR_MISSES in fence.splitlines()]
    running = [heading for heading in headings
               if re.match(r'running', heading, re.I)]
    if not found:
        problems.append('%s gives no line that finds the comments that are '
                        'nearly markers: %s' % (SKILL, NEAR_MISSES))
    elif not running or headings.index(found[0]) > headings.index(running[0]):
        problems.append('%s finds the comments that are nearly markers in %r, '
                        'which does not come before the section on running '
                        'the tests' % (SKILL, found[0]))
    problems.extend(sentence_with(SKILL, [
        'Show each `fix` beside its `why`, ask, and make the edits accepted.']))
    return problems
