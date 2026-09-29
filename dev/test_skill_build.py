"""Text checks for the build skill, `skills/build/SKILL.md`.

Every rule of `specs/skills/skill_build.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re
import subprocess

from skill_checks import (BASH, ROOT, carries, flat, frontmatter_problems,
                          frontmatter_refusals, in_order, next_step_problems,
                          read, refusals, replace, section, sections,
                          sentence_with, skill_ceiling_problems, skill_path,
                          table_rows, undirected_outcome_problems)


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
        assert (next_step_problems('build')
                + undirected_outcome_problems('build')) == []

    # purlin: skill_build PROOF-8
    def test_an_outcome_with_no_directive_is_refused(self, monkeypatch):
        rel = skill_path('build')
        assert refusals(
            monkeypatch, lambda: undirected_outcome_problems('build'), [
                (rel, replace(', `\u2192 Run: purlin:build <feature>`'),
                 '%s closing outcome gives no \u2192 directive: - Some rules '
                 'still have no test' % rel),
            ]) == []

    # purlin: skill_build PROOF-9
    def test_it_repairs_the_comments_that_are_nearly_markers(self):
        assert near_miss_problems() == []

    # purlin: skill_build PROOF-10
    def test_a_repair_with_no_near_miss_line_is_refused(self, monkeypatch):
        rel = skill_path('build')
        assert refusals(monkeypatch, near_miss_problems, [
            (rel, replace(' --near-misses --project-root .',
                          ' --project-root .'),
             '%s gives no line that finds the comments that are nearly '
             'markers' % rel),
        ]) == []

    # purlin: skill_build PROOF-11
    def test_the_test_run_sets_the_test_command(self):
        assert command_setting_problems() == []

    # purlin: skill_build PROOF-12
    def test_writing_the_test_command_itself_is_refused(self, monkeypatch):
        rel = skill_path('build')
        assert refusals(monkeypatch, command_setting_problems, [
            (rel, replace('so\nwrite no entry yourself.',
                          'so\nwrite the entry with the `purlin_config` '
                          'tool.'),
             "%s names the 'purlin_config' tool" % rel),
        ]) == []

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


# The one line that finds the comments that are nearly markers.
NEAR_MISSES = ('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" '
               '--near-misses --project-root .')


def near_miss_problems():
    rel = skill_path('build')
    text = read(rel)
    headings = [heading for heading, _body in sections(text)]
    problems = []
    found = [heading for heading, body in sections(text)
             for fence in re.findall(r'```\w*\n(.*?)```', body, re.S)
             if NEAR_MISSES in fence.splitlines()]
    running = [heading for heading in headings
               if re.match(r'running', heading, re.I)]
    if not found:
        problems.append('%s gives no line that finds the comments that are '
                        'nearly markers: %s' % (rel, NEAR_MISSES))
    elif not running or headings.index(found[0]) > headings.index(running[0]):
        problems.append('%s finds the comments that are nearly markers in %r, '
                        'which does not come before the section on running '
                        'the tests' % (rel, found[0]))
    problems.extend(sentence_with(rel, [
        'Show each `fix` beside its `why`, ask, and make the edits accepted.']))
    return problems


def command_setting_problems():
    rel = skill_path('build')
    running = flat(section(read(rel), r'^running') or '')
    problems = ['%s section on running the tests does not carry %r'
                % (rel, needle) for needle in (
                    'where no test command is set it suggests one and writes '
                    'it once the person confirms',
                    'write no entry yourself')
                if needle not in running]
    if 'purlin_config' in read(rel):
        problems.append("%s names the 'purlin_config' tool" % rel)
    return problems
