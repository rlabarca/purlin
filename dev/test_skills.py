"""Text checks for the twelve skills and the agent definition.

Every rule of `specs/skills/*.md` and `specs/instructions/purlin_agent.md` is
proved here. Each check reads one file and returns the problems it found as a list, so
a test body is one assertion and its failure prints what is wrong rather than
`False is not True`.

Prose wraps, so a sentence a skill states over two lines is one string here:
`flat()` collapses runs of whitespace before a prose needle is searched for.
A needle that must sit on one line of the source, such as a fenced command,
goes through `same_line()` instead.
"""

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

# The twelve skills, each with the ceiling its spec sets.
CEILINGS = {
    'anchor': 160, 'audit': 105, 'build': 130, 'drift': 150, 'find': 85,
    'init': 250, 'rename': 85, 'sign': 185, 'spec': 210,
    'spec-from-code': 130, 'status': 80, 'test': 120,
}
COMMANDS = sorted(CEILINGS)

AGENT = 'agents/purlin.md'


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


def init_question_problems():
    rel = skill_path('init')
    text = read(rel)
    problems = carries(rel, [
        'what must be true of every rule before a version is proven',
        '`passed`', '`strong`', '`signed`'])
    body = section(text, r'exception')
    if body is None:
        problems.append('%s has no section naming the further questions' % rel)
        return problems
    items = re.findall(r'^\d+\. ', body, re.M)
    if len(items) != 3:
        problems.append('%s names %d further questions, expected 3'
                        % (rel, len(items)))
    flattened = flat(body)
    for needle in ('empty repository', 'Which rules need a signature?',
                   'trusted'):
        if needle not in flattened:
            problems.append('%s exceptions do not name %r' % (rel, needle))
    return problems


# ---------------------------------------------------------------------------
# skill_spec
# ---------------------------------------------------------------------------

class TestSkillSpec:

    @pytest.mark.proof("skill_spec", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec') == []

    @pytest.mark.proof("skill_spec", "PROOF-2", "RULE-2")
    def test_it_allocates_ids_against_the_default_branch(self):
        assert carries(skill_path('spec'), [
            'ids.next_ids', '${CLAUDE_PLUGIN_ROOT}/scripts/mcp',
            'allocated against `origin/main`, not against the working tree']) == []

    @pytest.mark.proof("skill_spec", "PROOF-3", "RULE-3")
    def test_it_closes_with_the_offer_to_build(self):
        assert spec_offer_problems() == []

    @pytest.mark.proof("skill_spec", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec') == []


def spec_offer_problems():
    rel = skill_path('spec')
    heading, body = sections(read(rel))[-1]
    problems = []
    if not re.search(r'next step|when you are done', heading, re.I):
        problems.append('%s closes with the section %r, which does not name '
                        'the next step' % (rel, heading))
    offer = 'Spec created: <name>. Build it now?'
    if offer not in body.splitlines():
        problems.append('%s closing section does not carry the line %r on its '
                        'own' % (rel, offer))
    return problems


# ---------------------------------------------------------------------------
# skill_spec_from_code
# ---------------------------------------------------------------------------

class TestSkillSpecFromCode:

    @pytest.mark.proof("skill_spec_from_code", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec-from-code') == []

    @pytest.mark.proof("skill_spec_from_code", "PROOF-2", "RULE-2")
    def test_it_reads_the_state_before_it_starts(self):
        assert spec_from_code_start_problems() == []

    @pytest.mark.proof("skill_spec_from_code", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('spec-from-code') == []

    @pytest.mark.proof("skill_spec_from_code", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec-from-code') == []

    @pytest.mark.proof("skill_spec_from_code", "PROOF-5", "RULE-5")
    def test_every_rule_it_writes_is_engineer_owned_at_the_passed_bar(self):
        assert spec_from_code_tag_problems() == []


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
        for tag in ('[origin: eng]', '[bar: passed]'):
            if tag not in line:
                problems.append('%s example rule carries no %s: %s'
                                % (rel, tag, line))
    problems.extend(carries(rel, [
        'Do not tag anything `[origin: pm]`',
        'Do not write `[bar: strong]`']))
    return problems


# ---------------------------------------------------------------------------
# skill_anchor
# ---------------------------------------------------------------------------

class TestSkillAnchor:

    @pytest.mark.proof("skill_anchor", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('anchor') == []

    @pytest.mark.proof("skill_anchor", "PROOF-2", "RULE-2")
    def test_it_runs_the_upstream_script_for_two_subcommands(self):
        assert anchor_command_problems() == []

    @pytest.mark.proof("skill_anchor", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('anchor') == []

    @pytest.mark.proof("skill_anchor", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('anchor') == []

    @pytest.mark.proof("skill_anchor", "PROOF-5", "RULE-5")
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

    @pytest.mark.proof("skill_build", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('build') == []

    @pytest.mark.proof("skill_build", "PROOF-2", "RULE-2")
    def test_it_reads_the_state_and_runs_the_tests_through_the_test_skill(self):
        assert build_command_problems() == []

    @pytest.mark.proof("skill_build", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('build') == []

    @pytest.mark.proof("skill_build", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('build') == []

    @pytest.mark.proof("skill_build", "PROOF-5", "RULE-5", tier="integration")
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

    @pytest.mark.proof("skill_test", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('test') == []

    @pytest.mark.proof("skill_test", "PROOF-2", "RULE-2")
    def test_it_runs_the_run_script_and_names_its_exit_codes(self):
        rel = skill_path('test')
        assert (same_line(rel, [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--test'])
            + same_line(rel, ['Exit codes:', '`0`', '`1`', '`2`'])) == []

    @pytest.mark.proof("skill_test", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('test') == []

    @pytest.mark.proof("skill_test", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('test') == []

    @pytest.mark.proof("skill_test", "PROOF-5", "RULE-5")
    def test_it_names_the_results_the_commit_and_the_gate_line(self):
        rel = skill_path('test')
        assert carries(rel, [
            '.purlin/tests/<feature>.json', '.purlin/tests.md',
            'purlin: tests at <sha7>', 'Test results committed.',
            'Test results unchanged.', 'gate passed: <n> of <rules>',
            'It never pushes.']) == []


# ---------------------------------------------------------------------------
# skill_audit
# ---------------------------------------------------------------------------

class TestSkillAudit:

    @pytest.mark.proof("skill_audit", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('audit') == []

    @pytest.mark.proof("skill_audit", "PROOF-2", "RULE-2")
    def test_it_runs_the_run_script_and_leaves_ci_to_ci(self):
        rel = skill_path('audit')
        assert (same_line(rel, [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--audit'])
            + carries(rel, [
                'A remote runner runs the same script in an arm of its own',
                'you never run it by hand'])) == []

    @pytest.mark.proof("skill_audit", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('audit') == []

    @pytest.mark.proof("skill_audit", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('audit') == []

    @pytest.mark.proof("skill_audit", "PROOF-5", "RULE-5")
    def test_it_says_which_record_counts_under_which_gate(self):
        assert record_source_problems() == []

    @pytest.mark.proof("skill_audit", "PROOF-6", "RULE-6")
    def test_the_gate_decides_the_breaks_and_the_audit_writes_the_record(self):
        assert audit_gate_problems() == []

    @pytest.mark.proof("skill_audit", "PROOF-7", "RULE-7")
    def test_it_names_the_briefs_and_the_retention(self):
        assert carries(skill_path('audit'), [
            '.purlin/briefs/',
            'per operating system per source',
            'purlin:test --remote']) == []


# Every flag `scripts/init/scaffold.py` takes, and the one retired flag the
# skill must not name again: `--ci` went when init started asking at `passed`
# whether to add a remote runner, so a skill that still printed it would hand
# a person an invocation the script exits 2 on.
SCAFFOLD_FLAGS = ('--project-root', '--gate', '--update', '--add',
                  '--dry-run')
SCAFFOLD_RETIRED = ('--ci',)


def scaffold_flag_problems():
    rel = skill_path('init')
    problems = carries(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"'] +
        list(SCAFFOLD_FLAGS))
    text = read(rel)
    for flag in SCAFFOLD_RETIRED:
        if re.search(re.escape(flag) + r'\b', text):
            problems.append('%s names %s, which scaffold.py does not take'
                            % (rel, flag))
    return problems


def record_source_problems():
    rel = skill_path('audit')
    rows = {cells[0]: cells[-1]
            for cells in table_rows(read(rel), '| Source |')}
    problems = []
    for source in ('ci', 'local'):
        if source not in rows:
            problems.append('%s record table has no %r row' % (rel, source))
    if problems:
        return problems
    for gate in ('passed', 'strong', 'signed'):
        if gate not in rows['ci']:
            problems.append('%s ci row does not count under %r' % (rel, gate))
    for gate in ('passed', 'strong', 'signed'):
        if gate not in rows['local']:
            problems.append('%s local row does not count under %r'
                            % (rel, gate))
    for folder in ('.purlin/records/ci/', '.purlin/records/local/'):
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
    for needle in ('n/a', 'tests only'):
        if needle not in rows['`passed`']:
            problems.append('%s passed row does not name %r' % (rel, needle))
    for needle in ('breaks', 'minimum'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    for needle in ('counts here too', 'gate strong: <n> of <rules>',
                   'purlin: record for <sha7>'):
        if needle not in read(rel):
            problems.append('%s does not say %r' % (rel, needle))
    return problems


# ---------------------------------------------------------------------------
# skill_sign
# ---------------------------------------------------------------------------

class TestSkillSign:

    @pytest.mark.proof("skill_sign", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('sign') == []

    @pytest.mark.proof("skill_sign", "PROOF-2", "RULE-2")
    def test_it_shows_the_brief_before_it_writes_the_signature(self):
        rel = skill_path('sign')
        assert (carries(rel, ['payload.review_list'])
                + in_order(rel, [
                    '"${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py"',
                    '"${CLAUDE_PLUGIN_ROOT}/scripts/review/sign.py"'])) == []

    @pytest.mark.proof("skill_sign", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('sign') == []

    @pytest.mark.proof("skill_sign", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('sign') == []

    @pytest.mark.proof("skill_sign", "PROOF-5", "RULE-5")
    def test_a_signature_counts_on_a_signed_commit_and_its_hashes(self):
        assert carries(skill_path('sign'), [
            'The commit that added the file is signed and the signature '
            'verifies',
            'Its bound hashes still match the rule, the proof, the test, the '
            'bar and what the audit found',
            'whoever wrote it, whoever last committed to the test file, and on '
            'whatever branch carries it']) == []

    @pytest.mark.proof("skill_sign", "PROOF-6", "RULE-6")
    def test_the_walk_takes_one_of_four_answers(self):
        assert sign_answer_problems() == []

    @pytest.mark.proof("skill_sign", "PROOF-7", "RULE-7")
    def test_it_says_what_each_gate_leaves_it_able_to_do(self):
        assert sign_gate_problems() == []


def sign_answer_problems():
    rel = skill_path('sign')
    body = section(read(rel), r'four answers')
    if body is None:
        return ["%s has no section naming the walk's answers" % rel]
    flattened = flat(body)
    problems = ['%s answers do not name %r' % (rel, label)
                for label in ('**Sign.**', '**Add a case.**', '**Hold.**',
                              '**Skip.**')
                if label not in flattened]
    if 'A skipped rule is on the list again next time' not in flattened:
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
    for needle in ('--note', '--hold'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    if 'sign_at' not in rows['`signed`']:
        problems.append('%s signed row does not name sign_at' % rel)
    return problems


# ---------------------------------------------------------------------------
# skill_status, skill_drift, skill_find, skill_rename
# ---------------------------------------------------------------------------

class TestSkillStatus:

    @pytest.mark.proof("skill_status", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('status') == []

    @pytest.mark.proof("skill_status", "PROOF-2", "RULE-2")
    def test_it_prints_the_numbers_the_tool_returned(self):
        assert carries(skill_path('status'), [
            'sync_status', 'Never recount them',
            'one answer from one computation']) == []

    @pytest.mark.proof("skill_status", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('status') == []

    @pytest.mark.proof("skill_status", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('status') == []


class TestSkillDrift:

    @pytest.mark.proof("skill_drift", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('drift') == []

    @pytest.mark.proof("skill_drift", "PROOF-2", "RULE-2")
    def test_it_takes_its_data_from_the_tool(self):
        assert carries(skill_path('drift'), [
            'drift(role="eng")', 'references/drift_criteria.md',
            'do not restate them here and do not invent a category the tool '
            'does not return']) == []

    @pytest.mark.proof("skill_drift", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('drift') == []

    @pytest.mark.proof("skill_drift", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('drift') == []


class TestSkillFind:

    @pytest.mark.proof("skill_find", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('find') == []

    @pytest.mark.proof("skill_find", "PROOF-2", "RULE-2")
    def test_it_reads_the_state_and_hides_empty_columns(self):
        assert carries(skill_path('find'), [
            'sync_status',
            'Show the bar and the origin only when the spec tagged them',
            'under the `passed` gate both are optional']) == []

    @pytest.mark.proof("skill_find", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('find') == []

    @pytest.mark.proof("skill_find", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('find') == []


class TestSkillRename:

    @pytest.mark.proof("skill_rename", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('rename') == []

    @pytest.mark.proof("skill_rename", "PROOF-2", "RULE-2")
    def test_it_moves_with_git_mv_then_checks_what_it_missed(self):
        rel = skill_path('rename')
        assert (in_order(rel, ['git mv', 'sync_status'])
                + carries(rel, ['Any unresolved reference it reports is a '
                                'miss'])) == []

    @pytest.mark.proof("skill_rename", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('rename') == []

    @pytest.mark.proof("skill_rename", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('rename') == []


# ---------------------------------------------------------------------------
# purlin_agent
# ---------------------------------------------------------------------------

class TestPurlinAgent:

    @pytest.mark.proof("purlin_agent", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_agent(self):
        assert agent_frontmatter_problems() == []

    @pytest.mark.proof("purlin_agent", "PROOF-2", "RULE-2")
    def test_the_core_loop_runs_in_order(self):
        assert core_loop_problems() == []

    @pytest.mark.proof("purlin_agent", "PROOF-3", "RULE-3")
    def test_there_are_five_nevers(self):
        assert never_problems() == []

    @pytest.mark.proof("purlin_agent", "PROOF-4", "RULE-4")
    def test_the_routing_table_covers_the_four_roles(self):
        assert routing_problems() == []

    @pytest.mark.proof("purlin_agent", "PROOF-5", "RULE-5")
    def test_it_reads_the_state_before_it_answers(self):
        assert carries(AGENT, [
            'Call `sync_status` before you answer any question about state.',
            '`drafted`', '`ready`', '`passed`', '`strong`', '`signed`',
            '`code changed`']) == []

    @pytest.mark.proof("purlin_agent", "PROOF-6", "RULE-6")
    def test_it_stays_under_its_ceiling(self):
        assert ceiling_problems(AGENT, 120) == []


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
    if len(items) != 5:
        problems.append('%s carries %d NEVERs, expected 5' % (AGENT, len(items)))
    flattened = flat(body)
    for needle in ('origin', 'proof file', 'record', 'signature',
                   "sign on a person's behalf", 'Never push',
                   'pull request', 'remote branch', 'purlin:test --remote',
                   'retired term'):
        if needle not in flattened:
            problems.append('%s NEVERs do not name %r' % (AGENT, needle))
    return problems


def routing_problems():
    rows = table_rows(read(AGENT), '| Role |')
    problems = []
    if not rows:
        return ['%s has no routing table' % AGENT]
    roles = {cells[0] for cells in rows}
    for role in ('PM', 'Designer', 'Engineer', 'QA'):
        if role not in roles:
            problems.append('%s routing table has no %r row' % (AGENT, role))
    named = set(re.findall(r'purlin:([a-z-]+)',
                           '\n'.join('|'.join(cells) for cells in rows)))
    for command in sorted(named - set(COMMANDS)):
        problems.append('%s routes to purlin:%s, which is not one of the '
                        'twelve commands' % (AGENT, command))
    return problems


