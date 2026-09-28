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
    match = re.search(r'^%s:\s*(.*)$' % key, block, re.M)
    return match.group(1).strip() if match else None


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


def in_order(rel, needles):
    text = read(rel)
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
    if not description or description == '>':
        problems.append('%s frontmatter carries no one-line description' % rel)
    if ('purlin:%s' % name) not in read('references/purlin_commands.md'):
        problems.append('references/purlin_commands.md carries no row for '
                        'purlin:%s' % name)
    return problems


def next_step_problems(name):
    rel = skill_path(name)
    heading, body = sections(read(rel))[-1]
    problems = []
    if not re.search(r'next step|when you are done', heading, re.I):
        problems.append('%s closes with the section %r, which does not name '
                        'the next step' % (rel, heading))
    outcomes = [line for line in body.splitlines()
                if line.startswith('- ') or line.startswith('| ')]
    if len(outcomes) < 2:
        problems.append('%s closing section names %d outcomes, expected at '
                        'least 2' % (rel, len(outcomes)))
    if '\u2192' not in body:
        problems.append('%s closing section gives no directive' % rel)
    return problems


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
    problems = carries(rel, ['`passed`', '`strong`', '`signed`'])
    body = section(text, r'^The questions$')
    if body is None:
        problems.append('%s has no section headed The questions' % rel)
        return problems
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
    return problems


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
    return problems + carries(rel, ['is not asked', '`.purlin/evidence/`',
                                    'one README'])


class TestSkillInit:

    # purlin: skill_init PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('init') == []

    # purlin: skill_init PROOF-2
    def test_it_runs_the_scaffold_script(self):
        assert scaffold_flag_problems() == []

    # purlin: skill_init PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('init') == []

    # purlin: skill_init PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('init') == []

    # purlin: skill_init PROOF-5
    def test_it_names_the_four_questions_in_order(self):
        assert init_question_problems() == []

    # purlin: skill_init PROOF-6
    def test_it_shows_the_eight_settings(self):
        assert init_config_problems() == []

    # purlin: skill_init PROOF-7
    def test_it_writes_the_tests_setting_and_installs_nothing(self):
        assert carries(skill_path('init'), [
            "installs nothing in the project's tests",
            'one entry of the `tests` setting', 'jest-junit',
            'references/supported_frameworks.md',
            'references/formats/marker_format.md']) == []


# ---------------------------------------------------------------------------
# skill_spec
# ---------------------------------------------------------------------------

class TestSkillSpec:

    # purlin: skill_spec PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec') == []

    # purlin: skill_spec PROOF-2
    def test_it_allocates_ids_against_the_default_branch(self):
        assert carries(skill_path('spec'), [
            'git show origin/main:',
            'allocated against `origin/main`, not against the working tree']) == []

    # purlin: skill_spec PROOF-3
    def test_it_closes_by_naming_the_build(self):
        assert spec_offer_problems() == []

    # purlin: skill_spec PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec') == []

    # purlin: skill_spec PROOF-6
    def test_it_prints_the_proofs_and_asks_before_it_saves(self):
        assert carries(skill_path('spec'), [
            'Print each rule with its proofs under it and ask whether to '
            'change any', 'Save the spec when the person is satisfied',
            'Draft every proof against', 'at least one failure case']) == []

    # purlin: skill_spec PROOF-5
    def test_it_writes_the_scope_on_every_spec(self):
        rel = skill_path('spec')
        problems = carries(rel, [
            'Write `> Scope:` on every spec you create',
            'the paths `purlin:build` will create', 'every run includes it',
            'its rules cannot be signed'])
        step = re.search(r'^\d+\. Write the metadata.*$', read(rel), re.M)
        if step is None or '`> Scope:`' not in step.group(0):
            problems.append('%s procedure does not name > Scope: in the '
                            'metadata step' % rel)
        assert problems == []


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

    # purlin: skill_spec_from_code PROOF-2
    def test_it_reads_the_state_before_it_starts(self):
        assert spec_from_code_start_problems() == []

    # purlin: skill_spec_from_code PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-5
    def test_every_rule_it_writes_is_at_the_passed_level(self):
        assert spec_from_code_tag_problems() == []

    # purlin: skill_spec_from_code PROOF-6
    def test_it_ties_an_existing_test_by_its_marker(self):
        assert carries(skill_path('spec-from-code'), [
            'offer to add the marker comment above that test',
            'purlin: <feature> PROOF-<n>', 'write no new test',
            'is not that test']) == []


def spec_from_code_start_problems():
    rel = skill_path('spec-from-code')
    body = section(read(rel), r'before you start')
    if body is None:
        return ['%s has no section that runs before the survey' % rel]
    flattened = flat(body)
    return ['%s start section does not name %r' % (rel, needle)
            for needle in ('sync_status', '.purlin/config.json', 'purlin:init')
            if needle not in flattened]


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
        'Do not write `[level: strong]` or `[level: signed]`']))
    return problems


# ---------------------------------------------------------------------------
# skill_anchor
# ---------------------------------------------------------------------------

class TestSkillAnchor:

    # purlin: skill_anchor PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('anchor') == []

    # purlin: skill_anchor PROOF-2
    def test_it_runs_the_upstream_script_for_two_subcommands(self):
        assert anchor_command_problems() == []

    # purlin: skill_anchor PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('anchor') == []

    # purlin: skill_anchor PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('anchor') == []

    # purlin: skill_anchor PROOF-5
    def test_a_pin_is_a_commit_and_a_pinned_rule_is_never_edited(self):
        assert carries(skill_path('anchor'), [
            'A pin is always a commit, never a branch.',
            'Never edit a pinned rule in place.',
            'a pull request against the source repository',
            '> Requires: <the pinned one>']) == []


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
    problems.extend(carries(rel, ['--check', 'purlin:drift']))
    return problems


# ---------------------------------------------------------------------------
# skill_build
# ---------------------------------------------------------------------------

class TestSkillBuild:

    # purlin: skill_build PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('build') == []

    # purlin: skill_build PROOF-2
    def test_it_reads_the_state_and_runs_the_tests_through_the_test_skill(self):
        assert build_command_problems() == []

    # purlin: skill_build PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('build') == []

    # purlin: skill_build PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('build') == []

    # purlin: skill_build PROOF-7
    def test_it_looks_for_an_existing_test_before_it_writes_one(self):
        rel = skill_path('build')
        problems = carries(rel, [
            'Look first for a test that already shows it',
            'offer to add the marker above it and write nothing new',
            'in the folder and the style its other tests use',
            'purlin: login RULE-2'])
        if '# purlin: login PROOF-1\ndef test_' not in read(rel):
            problems.append('%s shows no marker above a test' % rel)
        assert problems == []

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


def build_command_problems():
    rel = skill_path('build')
    body = section(read(rel), r'choosing what to build')
    problems = []
    if body is None or 'sync_status' not in body:
        problems.append('%s does not read the state with sync_status before it '
                        'chooses what to build' % rel)
    problems.extend(carries(rel, [
        'purlin:test <name>', 'Never run the test framework directly.']))
    return problems


# ---------------------------------------------------------------------------
# skill_test
# ---------------------------------------------------------------------------

class TestSkillTest:

    # purlin: skill_test PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('test') == []

    # purlin: skill_test PROOF-2
    def test_it_runs_the_run_script_and_names_its_exit_codes(self):
        rel = skill_path('test')
        assert (same_line(rel, [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--test'])
            + same_line(rel, ['Exit codes:', '`0`', '`1`', '`2`'])) == []

    # purlin: skill_test PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('test') == []

    # purlin: skill_test PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('test') == []

    # purlin: skill_test PROOF-5
    def test_it_names_the_evidence_the_commit_and_the_gate_line(self):
        rel = skill_path('test')
        assert carries(rel, [
            '.purlin/evidence/local/<feature>.json', '.purlin/tests.md',
            '--commit', 'purlin: evidence at <sha7>', 'Evidence committed.',
            'Evidence unchanged.', 'gate passed: <n> of <rules>',
            'It never pushes.']) == []

    # purlin: skill_test PROOF-6
    def test_it_says_what_a_run_with_no_feature_named_runs(self):
        rel = skill_path('test')
        usage = section(read(rel), r'^usage')
        problems = [] if usage and 'purlin:test --all' in usage else [
            '%s usage does not name purlin:test --all' % rel]
        problems.extend(carries(rel, [
            'no run on this operating system', 'changed since its evidence',
            'untracked file', 'names no files', 'runs only the test files',
            'purlin:test --all runs them too.',
            "Nothing to run: every feature's spec, code and tests match its "
            'evidence.']))
        assert problems == []


# ---------------------------------------------------------------------------
# skill_audit
# ---------------------------------------------------------------------------

class TestSkillAudit:

    # purlin: skill_audit PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('audit') == []

    # purlin: skill_audit PROOF-2
    def test_it_runs_the_run_script_and_leaves_ci_to_ci(self):
        rel = skill_path('audit')
        assert (same_line(rel, [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--audit'])
            + carries(rel, [
                'A remote runner runs the same script in an arm of its own',
                'you never run it by hand'])) == []

    # purlin: skill_audit PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('audit') == []

    # purlin: skill_audit PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('audit') == []

    # purlin: skill_audit PROOF-5
    def test_it_says_which_evidence_counts_under_which_gate(self):
        assert evidence_source_problems() == []

    # purlin: skill_audit PROOF-6
    def test_the_gate_decides_the_breaks_and_the_audit_writes_the_evidence(self):
        assert audit_gate_problems() == []

    # purlin: skill_audit PROOF-7
    def test_it_names_the_evidence_and_the_retention(self):
        assert carries(skill_path('audit'), [
            'into `.purlin/evidence/local/<feature>.json`',
            'the newest section per operating system',
            'purlin:test --remote']) == []


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
    return problems


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
    for needle in ('breaks', 'minimum'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    for needle in ('counts here too', 'gate strong: <n> of <rules>',
                   'purlin: evidence at <sha7>'):
        if needle not in read(rel):
            problems.append('%s does not say %r' % (rel, needle))
    return problems


# ---------------------------------------------------------------------------
# skill_sign
# ---------------------------------------------------------------------------

class TestSkillSign:

    # purlin: skill_sign PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('sign') == []

    # purlin: skill_sign PROOF-2
    def test_it_shows_what_the_audit_found_before_it_writes_the_signature(self):
        rel = skill_path('sign')
        assert (carries(rel, ['payload.queue'])
                + in_order(rel, [
                    '"${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py"',
                    '"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"'])) == []

    # purlin: skill_sign PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('sign') == []

    # purlin: skill_sign PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('sign') == []

    # purlin: skill_sign PROOF-5
    def test_a_signature_counts_on_a_signed_commit_and_its_hashes(self):
        assert carries(skill_path('sign'), [
            'The commit that added the file is signed and the signature '
            'verifies',
            'Its bound hashes still match the rule, the proof, the test and '
            'what the audit found',
            'whoever wrote it, whoever last committed to the test file, and on '
            'whatever branch carries it']) == []

    # purlin: skill_sign PROOF-6
    def test_the_walk_takes_one_of_three_answers(self):
        assert sign_answer_problems() == []

    # purlin: skill_sign PROOF-7
    def test_it_says_what_each_gate_leaves_it_able_to_do(self):
        assert sign_gate_problems() == []

    # purlin: skill_sign PROOF-8
    def test_the_tag_carries_the_evidence_package_and_nothing_is_pushed(self):
        rel = skill_path('sign')
        body = section(read(rel), r'the tag')
        assert body is not None, '%s has no section on the tag' % rel
        problems = ['%s tag section does not carry %r' % (rel, needle)
                    for needle in ('At the gate `signed`, when the walk '
                                   'leaves every rule meeting it',
                                   '.purlin/evidence/package/<version>.json',
                                   'Below `signed` it writes no tag and no '
                                   'package',
                                   'this skill never pushes')
                    if needle not in flat(body)]
        package = 'Evidence package committed: .purlin/evidence/package/1.4.0.json.'
        tagged = 'Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate signed.'
        lines = body.splitlines()
        if package not in lines or tagged not in lines:
            problems.append('%s tag section does not print %r above %r'
                            % (rel, package, tagged))
        elif lines.index(package) > lines.index(tagged):
            problems.append('%s tag section prints the tag line before the '
                            'package line' % rel)
        assert problems == []


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
    for needle in ('--note', 'hand check'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    if '[level: passed]' not in rows['`signed`']:
        problems.append('%s signed row does not name [level: passed]' % rel)
    return problems


# ---------------------------------------------------------------------------
# skill_status, skill_drift
# ---------------------------------------------------------------------------

class TestSkillStatus:

    # purlin: skill_status PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('status') == []

    # purlin: skill_status PROOF-2
    def test_it_prints_the_numbers_the_tool_returned(self):
        assert carries(skill_path('status'), [
            'sync_status', 'Never recount them',
            'one answer from one computation']) == []

    # purlin: skill_status PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('status') == []

    # purlin: skill_status PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('status') == []

    # purlin: skill_status PROOF-5
    def test_naming_a_spec_shows_its_rules(self):
        assert (carries(skill_path('status'), [
            'purlin:status <name>',
            'Naming a spec shows its rules and their standing.'])
            + carries('references/purlin_commands.md',
                      ['purlin:status [name]'])) == []


class TestSkillDrift:

    # purlin: skill_drift PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('drift') == []

    # purlin: skill_drift PROOF-2
    def test_it_takes_its_data_from_the_tool(self):
        assert carries(skill_path('drift'), [
            'drift(role="eng")', 'references/drift_criteria.md',
            'do not restate them here and do not invent a line the tool '
            'does not return']) == []

    # purlin: skill_drift PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('drift') == []

    # purlin: skill_drift PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('drift') == []


# ---------------------------------------------------------------------------
# skill_export
# ---------------------------------------------------------------------------

class TestSkillExport:

    # purlin: skill_export PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('export') == []

    # purlin: skill_export PROOF-2
    def test_it_runs_the_script_in_each_form(self):
        assert carries(skill_path('export'), [
            'scripts/export/package.py', 'purlin:export --release <name>',
            'purlin:export --commit', 'purlin:export --check <file>']) == []

    # purlin: skill_export PROOF-3
    def test_it_makes_no_claim_of_compliance(self):
        assert carries(skill_path('export'), [
            'Purlin makes no claim that the software is compliant.',
            'evidence for review in a regulated document and sign-off '
            'system']) == []

    # purlin: skill_export PROOF-4
    def test_it_names_the_three_states(self):
        assert carries(skill_path('export'), [
            '`work in progress`', '`gate <gate> met`', '`signed`',
            'Only `purlin:sign` writes a package whose state is']) == []

    # purlin: skill_export PROOF-5
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('export') == []

    # purlin: skill_export PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('export') == []


# ---------------------------------------------------------------------------
# purlin_agent
# ---------------------------------------------------------------------------

class TestPurlinAgent:

    # purlin: purlin_agent PROOF-1
    def test_the_frontmatter_names_the_agent(self):
        assert agent_frontmatter_problems() == []

    # purlin: purlin_agent PROOF-2
    def test_the_core_loop_runs_in_order(self):
        assert core_loop_problems() == []

    # purlin: purlin_agent PROOF-3
    def test_there_are_four_nevers(self):
        assert never_problems() == []

    # purlin: purlin_agent PROOF-4
    def test_the_routing_table_covers_the_three_roles(self):
        assert routing_problems() == []

    # purlin: purlin_agent PROOF-5
    def test_it_reads_the_state_before_it_answers(self):
        assert carries(AGENT, [
            'Call `sync_status` before you answer any question about state.',
            '`no proof written`', '`passed`', '`strong`', '`signed`',
            '`out of date`']) == []

    # purlin: purlin_agent PROOF-6
    def test_it_stays_under_its_ceiling(self):
        assert ceiling_problems(AGENT, 135) == []

    # purlin: purlin_agent PROOF-7
    def test_it_says_what_a_rename_moves(self):
        assert rename_problems() == []


def rename_problems():
    body = section(read(AGENT), r'^Renaming a feature$')
    if body is None:
        return ['%s has no Renaming a feature section' % AGENT]
    text = flat(body)
    return ['%s rename section does not carry %r' % (AGENT, needle)
            for needle in ('# Feature:', '> Requires:', 'purlin: <name> PROOF-<n>',
                           '.signatures/',
                           '.purlin/evidence/<source>/<name>.json', 'git mv',
                           'sync_status')
            if needle not in text]


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
    return []


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
    return problems


