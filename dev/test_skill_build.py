"""Text checks for the build skill, `skills/build/SKILL.md`.

Every rule of `specs/skills/skill_build.md` is proved here, one case to a
test. A refusal is shown by pointing a check at a copy of the file with one
thing broken; the file on disk is never touched. The readers and the checks
this file shares with the other skill test files are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (COMMAND_REF, carries, field, flat, frontmatter,
                          frontmatter_problems, in_order, next_step_problems,
                          on_copy, read, refusals, replace, section, sections,
                          sentence_with, skill_ceiling_problems, skill_path,
                          table_rows, undirected_outcome_problems)

SKILL = skill_path('build')
CONVENTIONS = 'references/commit_conventions.md'


def refused(monkeypatch, check, rel, edit, expected):
    """`[]` when a copy of `rel` as `edit` leaves it reports `expected`."""
    return refusals(monkeypatch, check, [(rel, edit, expected)])


class TestSkillBuild:

    # purlin: skill_build PROOF-1
    def test_the_frontmatter_names_the_skill_and_the_reference_lists_it(self):
        assert frontmatter_problems('build') == []

    # purlin: skill_build PROOF-24
    def test_a_frontmatter_with_no_name_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, lambda: frontmatter_problems('build'), SKILL,
            replace('name: build\n'),
            "%s frontmatter name is None, expected 'build'" % SKILL) == []

    # purlin: skill_build PROOF-25
    def test_an_empty_description_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, lambda: frontmatter_problems('build'), SKILL,
            replace(description_line(), 'description:'), NO_DESCRIPTION) == []

    # purlin: skill_build PROOF-26
    def test_an_empty_description_is_not_read_from_the_line_below(
            self, monkeypatch):
        assert refused(
            monkeypatch, lambda: frontmatter_problems('build'), SKILL,
            replace('name: build\n' + description_line(),
                    'description:\nname: build'), NO_DESCRIPTION) == []

    # purlin: skill_build PROOF-27
    def test_a_description_written_as_a_block_is_refused(self, monkeypatch):
        line = description_line()
        assert refused(
            monkeypatch, lambda: frontmatter_problems('build'), SKILL,
            replace(line, 'description: |\n  ' + line[len('description: '):]),
            NO_DESCRIPTION) == []

    # purlin: skill_build PROOF-28
    def test_a_description_run_onto_a_second_line_is_refused(
            self, monkeypatch):
        line = description_line()
        assert refused(
            monkeypatch, lambda: frontmatter_problems('build'), SKILL,
            replace(line, line + '\n  and a second line'),
            NO_DESCRIPTION) == []

    # purlin: skill_build PROOF-29
    def test_a_command_reference_with_no_build_row_is_refused(
            self, monkeypatch):
        row = next(line for line in read(COMMAND_REF).splitlines()
                   if re.match(r'\| `purlin:build[ `]', line))
        assert refused(
            monkeypatch, lambda: frontmatter_problems('build'), COMMAND_REF,
            replace(row + '\n'),
            '%s carries no row for purlin:build' % COMMAND_REF) == []

    # purlin: skill_build PROOF-2
    def test_it_reads_the_state_and_runs_the_tests_through_the_test_skill(self):
        assert build_command_problems() == []

    # purlin: skill_build PROOF-30
    def test_pytest_in_place_of_the_test_skill_is_refused_twice(
            self, monkeypatch):
        problems = on_copy(
            monkeypatch, SKILL,
            replace('```bash\npurlin:test <name>\n```',
                    '```bash\npython3 -m pytest tests/\n```'),
            build_command_problems)
        expected = [
            "%s gives the test framework's own command: python3 -m pytest "
            'tests/' % SKILL,
            "%s section on running the tests gives no fenced line "
            "'purlin:test <name>'" % SKILL]
        assert [e for e in expected if e not in problems] == [], problems

    # purlin: skill_build PROOF-31
    def test_jest_in_the_usage_block_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, build_command_problems, SKILL,
            replace('```bash\npurlin:build [<name>]\n```',
                    '```bash\nnpx jest\n```'),
            "%s gives the test framework's own command: npx jest" % SKILL) == []

    # purlin: skill_build PROOF-32
    def test_choosing_without_the_state_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, build_command_problems, SKILL,
            replace('call `sync_status` and read the state', 'read the state'),
            '%s does not read the state with sync_status before it chooses '
            'what to build' % SKILL) == []

    # purlin: skill_build PROOF-3
    def test_it_closes_by_naming_the_next_step_for_each_outcome(self):
        assert closing_problems() == []

    # purlin: skill_build PROOF-8
    def test_an_outcome_with_no_directive_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, closing_problems, SKILL,
            replace(', `→ Run: purlin:build <feature>`'),
            '%s closing outcome gives no → directive: - Some rules still '
            'have no test' % SKILL) == []

    # purlin: skill_build PROOF-33
    def test_a_next_step_named_from_nothing_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, closing_problems, SKILL,
            replace(NEXT_STEP_SOURCE, 'Name the next step:'),
            '%s closing section does not say to name the next step from '
            "purlin:test's summary and Left to do" % SKILL) == []

    # purlin: skill_build PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('build') == []

    # purlin: skill_build PROOF-34
    def test_one_line_over_the_ceiling_is_refused(self, monkeypatch):
        def to_131(text):
            return text + 'A line of prose.\n' * max(
                1, 131 - len(text.splitlines()))
        assert refused(
            monkeypatch, lambda: skill_ceiling_problems('build'), SKILL, to_131,
            '%s is 131 lines, ceiling 130' % SKILL) == []

    # purlin: skill_build PROOF-5
    def test_the_commit_it_asks_for_is_named_in_full(self):
        assert commit_problems() == []

    # purlin: skill_build PROOF-35
    def test_changeset_is_never_left_out(self):
        assert changeset_problems() == []

    # purlin: skill_build PROOF-36
    def test_decisions_and_review_are_left_out_when_empty(self):
        assert omission_problems() == []

    # purlin: skill_build PROOF-37
    def test_the_conventions_render_a_build_commit(self):
        assert example_problems() == []

    # purlin: skill_build PROOF-38
    def test_conventions_that_let_changeset_be_left_out_are_refused(
            self, monkeypatch):
        assert refused(
            monkeypatch, changeset_problems, CONVENTIONS,
            replace('for every rule the commit addresses | Never |',
                    'for every rule the commit addresses | When empty |'),
            "%s leaves Changeset out 'When empty', expected Never"
            % CONVENTIONS) == []

    # purlin: skill_build PROOF-6
    def test_it_keeps_the_scope_in_the_commit_with_the_code(self):
        assert scope_problems() == []

    # purlin: skill_build PROOF-39
    def test_a_scope_that_keeps_deleted_files_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, scope_problems, SKILL,
            replace('remove each entry whose file you deleted, '),
            "%s Committing section does not carry 'remove each entry whose "
            "file you deleted'" % SKILL) == []

    # purlin: skill_build PROOF-7
    def test_it_looks_for_an_existing_test_before_it_writes_one(self):
        assert step_problems() == []

    # purlin: skill_build PROOF-40
    def test_its_example_shows_the_marker_above_a_test(self):
        assert example_marker_problems() == []

    # purlin: skill_build PROOF-41
    def test_a_rule_with_no_proof_is_marked_with_its_own_id(self):
        assert no_proof_problems() == []

    # purlin: skill_build PROOF-42
    def test_writing_before_looking_is_refused(self, monkeypatch):
        def swapped(text):
            look = text[text.index('1. **Look first'):
                        text.index('2. **Otherwise')]
            writes = ' with the marker above it.\n'
            text = text.replace(look, '', 1)
            return text.replace(writes, writes + look, 1)
        assert refused(monkeypatch, step_problems, SKILL, swapped,
                       'out of order, at offsets') == []

    # purlin: skill_build PROOF-43
    def test_a_write_step_not_in_the_projects_framework_is_refused(
            self, monkeypatch):
        assert refused(
            monkeypatch, step_problems, SKILL,
            replace("the project's own framework, in the folder"),
            '%s does not carry %r' % (SKILL, BUILD_STEPS[2])) == []

    # purlin: skill_build PROOF-44
    def test_a_rule_marker_with_no_reason_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, no_proof_problems, SKILL,
            replace('it names the rule: `purlin: login RULE-2`',
                    '`purlin: login RULE-2`'),
            "%s has no sentence carrying all of 'Where a rule has no proof', "
            "'it names the rule: `purlin: login RULE-2`'" % SKILL) == []

    # purlin: skill_build PROOF-9
    def test_it_repairs_the_comments_that_are_nearly_markers(self):
        assert near_miss_problems() == []

    # purlin: skill_build PROOF-10
    def test_a_repair_with_no_near_miss_line_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, near_miss_problems, SKILL,
            replace(' --near-misses --project-root .', ' --project-root .'),
            '%s gives no line that finds the comments that are nearly '
            'markers' % SKILL) == []

    # purlin: skill_build PROOF-45
    def test_a_repair_after_the_test_run_is_refused(self, monkeypatch):
        def moved(text):
            repair = text[text.index('## Repairing'):text.index('## Running')]
            text = text.replace(repair, '', 1)
            return text.replace('## Committing', repair + '## Committing', 1)
        assert refused(
            monkeypatch, near_miss_problems, SKILL, moved,
            'which does not come before the section on running the '
            'tests') == []

    # purlin: skill_build PROOF-11
    def test_the_test_run_sets_the_test_command(self):
        assert command_setting_problems() == []

    # purlin: skill_build PROOF-12
    def test_writing_the_test_command_itself_is_refused(self, monkeypatch):
        assert refused(
            monkeypatch, command_setting_problems, SKILL,
            replace('so\nwrite no entry yourself.',
                    'so\nwrite the entry with the `purlin_config` tool.'),
            "%s names the 'purlin_config' tool" % SKILL) == []


# ---------------------------------------------------------------------------
# The frontmatter
# ---------------------------------------------------------------------------

NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL


def description_line():
    return 'description: %s' % field(frontmatter(read(SKILL)), 'description')


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


def command_setting_problems():
    running = flat(section(read(SKILL), r'^running') or '')
    problems = ['%s section on running the tests does not carry %r'
                % (SKILL, needle) for needle in (
                    'where no test command is set it suggests one and writes '
                    'it once the person confirms',
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
    if NEXT_STEP_SOURCE not in flat(sections(read(SKILL))[-1][1]):
        problems.append('%s closing section does not say to name the next step '
                        "from purlin:test's summary and Left to do" % SKILL)
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
                '**Changeset**', '**Decisions**', '**Review**',
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
NEAR_MISSES = ('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" '
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
