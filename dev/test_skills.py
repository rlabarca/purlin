"""Text checks for the thirteen skills, the agent definition and the two tools.

Every rule of `specs/skills/*.md`, `specs/instructions/purlin_agent.md`,
`specs/tools/pm_anchor_userstories.md` and `specs/tools/qa_report.md` is proved
here. Each check reads one file and returns the problems it found as a list, so
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
import zipfile
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

# The thirteen skills, each with the ceiling its spec sets.
CEILINGS = {
    'anchor': 160, 'approve': 95, 'build': 130, 'drift': 150, 'find': 85,
    'init': 240, 'rename': 85, 'review': 145, 'spec': 210,
    'spec-from-code': 130, 'status': 80, 'test': 90, 'verify': 105,
}
COMMANDS = sorted(CEILINGS)

PM_MD = 'tools/PM/purlin-anchor-userstories.md'
PM_SKILL = 'tools/PM/purlin-anchor-userstories.skill'
QA_MD = 'tools/QA/purlin-qa-report.md'
QA_SKILL = 'tools/QA/purlin-qa-report.skill'
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


def archive_problems(archive, source):
    names = zipfile.ZipFile(ROOT / archive).namelist()
    expected = [Path(source).stem + '/SKILL.md']
    if names != expected:
        return ['%s holds %s, expected %s' % (archive, names, expected)]
    packed = zipfile.ZipFile(ROOT / archive).read(expected[0])
    if packed != (ROOT / source).read_bytes():
        return ['%s does not hold the bytes of %s; run dev/pack_tools.sh'
                % (archive, source)]
    return []


def tool_frontmatter_problems(rel, name, words):
    text = read(rel)
    block = frontmatter(text)
    if block is None:
        return ['%s does not open with a frontmatter block' % rel]
    problems = []
    if field(block, 'name') != name:
        problems.append('%s frontmatter name is %r, expected %r'
                        % (rel, field(block, 'name'), name))
    description = block.split('description:', 1)[-1] if 'description:' in block else ''
    if len(description.strip(' >\n')) < 40:
        problems.append('%s frontmatter carries no description' % rel)
    flattened = flat(description)
    problems.extend('%s description does not name %r' % (rel, word)
                    for word in words if word not in flattened)
    return problems


# ---------------------------------------------------------------------------
# skill_init
# ---------------------------------------------------------------------------

class TestSkillInit:

    @pytest.mark.proof("skill_init", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('init') == []

    @pytest.mark.proof("skill_init", "PROOF-2", "RULE-2")
    def test_it_runs_the_scaffold_script(self):
        assert carries(skill_path('init'), [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"',
            '--project-root', '--gate', '--update', '--ci', '--add',
            '--dry-run']) == []

    @pytest.mark.proof("skill_init", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('init') == []

    @pytest.mark.proof("skill_init", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('init') == []

    @pytest.mark.proof("skill_init", "PROOF-5", "RULE-5")
    def test_it_asks_one_question_and_names_two_exceptions(self):
        assert init_question_problems() == []


def init_question_problems():
    rel = skill_path('init')
    text = read(rel)
    problems = carries(rel, [
        'what must be true before CI lets a change merge',
        '`tested`', '`recorded`', '`approved`'])
    body = section(text, r'exception')
    if body is None:
        problems.append('%s has no section naming the further questions' % rel)
        return problems
    items = re.findall(r'^\d+\. ', body, re.M)
    if len(items) != 2:
        problems.append('%s names %d further questions, expected 2'
                        % (rel, len(items)))
    flattened = flat(body)
    for needle in ('empty repository', 'approver emails'):
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
    def test_every_rule_it_writes_is_engineer_owned_and_low_risk(self):
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
        for tag in ('[origin: eng]', '[risk: low]'):
            if tag not in line:
                problems.append('%s example rule carries no %s: %s'
                                % (rel, tag, line))
    problems.extend(carries(rel, [
        'Do not tag anything `[origin: pm]`',
        'Do not add risk tags above `low`']))
    return problems


# ---------------------------------------------------------------------------
# skill_anchor
# ---------------------------------------------------------------------------

class TestSkillAnchor:

    @pytest.mark.proof("skill_anchor", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('anchor') == []

    @pytest.mark.proof("skill_anchor", "PROOF-2", "RULE-2")
    def test_it_runs_the_upstream_script_for_three_subcommands(self):
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
            '`propose` drafts the pull request',
            '> Requires: <the pinned one>']) == []


def anchor_command_problems():
    rel = skill_path('anchor')
    script = '"${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py"'
    problems = []
    found = read(rel).count(script)
    if found < 3:
        problems.append('%s names %s %d times, expected at least 3'
                        % (rel, script, found))
    for subcommand in ('add', 'sync', 'propose'):
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
            '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--quick'])
            + same_line(rel, ['Exit codes:', '`0`', '`1`', '`2`'])) == []

    @pytest.mark.proof("skill_test", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('test') == []

    @pytest.mark.proof("skill_test", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('test') == []


# ---------------------------------------------------------------------------
# skill_verify
# ---------------------------------------------------------------------------

class TestSkillVerify:

    @pytest.mark.proof("skill_verify", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('verify') == []

    @pytest.mark.proof("skill_verify", "PROOF-2", "RULE-2")
    def test_it_runs_the_run_script_and_leaves_ci_to_ci(self):
        rel = skill_path('verify')
        assert (same_line(rel, [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"',
            '--record', '--commit'])
            + carries(rel, ['You never pass `--ci` by hand.'])) == []

    @pytest.mark.proof("skill_verify", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('verify') == []

    @pytest.mark.proof("skill_verify", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('verify') == []

    @pytest.mark.proof("skill_verify", "PROOF-5", "RULE-5")
    def test_it_says_which_record_counts_under_which_gate(self):
        assert record_label_problems() == []


def record_label_problems():
    rel = skill_path('verify')
    rows = {cells[0]: cells[-1]
            for cells in table_rows(read(rel), '| Label |')}
    problems = []
    for label in ('ci', 'developer', 'local'):
        if label not in rows:
            problems.append('%s record table has no %r row' % (rel, label))
    if problems:
        return problems
    for gate in ('tested', 'recorded', 'approved'):
        if gate not in rows['ci']:
            problems.append('%s ci row does not count under %r' % (rel, gate))
    if 'tested' not in rows['developer']:
        problems.append('%s developer row does not count under tested' % rel)
    for gate in ('recorded', 'approved'):
        if gate in rows['developer']:
            problems.append('%s developer row counts under %r' % (rel, gate))
    if rows['local'] != 'nothing':
        problems.append('%s local row counts under %r, expected nothing'
                        % (rel, rows['local']))
    return problems


# ---------------------------------------------------------------------------
# skill_review
# ---------------------------------------------------------------------------

class TestSkillReview:

    @pytest.mark.proof("skill_review", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('review') == []

    @pytest.mark.proof("skill_review", "PROOF-2", "RULE-2")
    def test_it_reads_the_list_and_runs_the_review_scripts(self):
        assert carries(skill_path('review'), [
            'payload.review_list',
            '"${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py"',
            '"${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py"']) == []

    @pytest.mark.proof("skill_review", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('review') == []

    @pytest.mark.proof("skill_review", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('review') == []

    @pytest.mark.proof("skill_review", "PROOF-5", "RULE-5")
    def test_re_verify_pending_never_reaches_the_list(self):
        assert review_list_problems() == []


def review_list_problems():
    rel = skill_path('review')
    text = read(rel)
    problems = carries(rel, [
        'Rules with only `re-verify pending` are **not** on the list',
        'the approval stands'])
    for cells in table_rows(text, '| Reason |'):
        if 're-verify' in ' '.join(cells):
            problems.append('%s lists re-verify pending as a reason: %s'
                            % (rel, cells))
    return problems


# ---------------------------------------------------------------------------
# skill_approve
# ---------------------------------------------------------------------------

class TestSkillApprove:

    @pytest.mark.proof("skill_approve", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('approve') == []

    @pytest.mark.proof("skill_approve", "PROOF-2", "RULE-2")
    def test_it_shows_the_brief_before_it_writes_the_approval(self):
        assert in_order(skill_path('approve'), [
            '"${CLAUDE_PLUGIN_ROOT}/scripts/review/brief.py"',
            '"${CLAUDE_PLUGIN_ROOT}/scripts/review/approve.py"']) == []

    @pytest.mark.proof("skill_approve", "PROOF-3", "RULE-3")
    def test_it_closes_by_naming_the_next_step(self):
        assert next_step_problems('approve') == []

    @pytest.mark.proof("skill_approve", "PROOF-4", "RULE-4")
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('approve') == []

    @pytest.mark.proof("skill_approve", "PROOF-5", "RULE-5")
    def test_the_author_of_the_test_cannot_approve_it(self):
        assert carries(skill_path('approve'), [
            'An approval also does not count when you are the author of the '
            'commit that last touched the test.',
            'it reaches the default branch by pull request']) == []


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
            'Show the risk and the origin only when the spec carries them',
            'under the `tested` gate both are optional']) == []

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
            'Drafted', 'Proof ready', 'Tested', 'Recorded', 'Reviewed',
            'Approved', 'Stale', 're-verify pending']) == []

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
             'purlin:verify', 'push']
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
    for needle in ('origin', 'proof file', 'record', 'approval',
                   'approve a rule whose test you wrote', 'verify',
                   '`recorded`', '`approved`', 'retired term'):
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
                        'thirteen commands' % (AGENT, command))
    return problems


# ---------------------------------------------------------------------------
# pm_anchor_userstories
# ---------------------------------------------------------------------------

class TestPmAnchorUserstories:

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_tool(self):
        assert tool_frontmatter_problems(
            PM_MD, 'purlin-anchor-userstories',
            ['spec', 'anchor', 'acceptance criteria']) == []

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-2", "RULE-2")
    def test_every_change_lands_as_a_pull_request(self):
        assert carries(PM_MD, [
            'Never commit to the default branch.',
            'specs/<category>/<name>.md', 'specs/_anchors/<name>.md',
            'designs/<feature>/', 'Create no other folder.']) == []

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-3", "RULE-3")
    def test_a_rule_owned_by_someone_else_is_left_alone(self):
        assert pm_owner_problems() == []

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-4", "RULE-4")
    def test_it_names_the_tags_and_the_tiers(self):
        assert carries(PM_MD, [
            '[risk:', '[origin:', '[criterion:', '`[risk: high]`',
            '`[risk: medium]`', '`[risk: low]`',
            'Under the `signed` gate risk and origin are both required',
            '@integration', '@e2e', '@manual',
            '@env(windows)', '@env(macos)', '@env(linux)']) == []

    @pytest.mark.proof("pm_anchor_userstories", "PROOF-5", "RULE-5")
    def test_the_archive_holds_the_markdown(self):
        assert archive_problems(PM_SKILL, PM_MD) == []


def pm_owner_problems():
    body = section(read(PM_MD), r'owner comment')
    if body is None:
        return ['%s has no owner comment section' % PM_MD]
    flattened = flat(body)
    problems = ['%s owner comment section does not carry %r' % (PM_MD, needle)
                for needle in ('[origin: eng]', '[origin: qa]',
                               'Never edit its text', 'never delete it')
                if needle not in flattened]
    if not re.search(r'RULE-\d+', body):
        problems.append('%s owner comment shows no rule id' % PM_MD)
    return problems


# ---------------------------------------------------------------------------
# qa_report
# ---------------------------------------------------------------------------

class TestQaReport:

    @pytest.mark.proof("qa_report", "PROOF-1", "RULE-1")
    def test_the_frontmatter_names_the_tool(self):
        assert tool_frontmatter_problems(
            QA_MD, 'purlin-qa-report',
            ['review list', 'test strength', 'QA report']) == []

    @pytest.mark.proof("qa_report", "PROOF-2", "RULE-2")
    def test_no_credential_is_written_into_a_url(self):
        assert credential_problems() == []

    @pytest.mark.proof("qa_report", "PROOF-3", "RULE-3")
    def test_it_scans_the_project_and_reads_the_rollup(self):
        assert (same_line(QA_MD, ['scripts/report/scan.py', '--repo'])
                + carries(QA_MD, [
                    'each bucket', 'The gate.',
                    'commits the branch has moved past the newest record'])) == []

    @pytest.mark.proof("qa_report", "PROOF-4", "RULE-4")
    def test_every_entry_ends_with_one_of_four_answers(self):
        assert re.findall(r'^- \*\*`([^`]+)`\*\*', read(QA_MD), re.M) == [
            'sign', 'add a case', 'hold', 'skip']

    @pytest.mark.proof("qa_report", "PROOF-5", "RULE-5")
    def test_it_states_its_limits(self):
        assert qa_limit_problems() == []

    @pytest.mark.proof("qa_report", "PROOF-6", "RULE-6")
    def test_the_archive_holds_the_markdown(self):
        assert archive_problems(QA_SKILL, QA_MD) == []


def credential_problems():
    text = read(QA_MD)
    problems = []
    for pattern in (r'://<[A-Z_]+>:<[A-Z_]+>@', r'://[^/\s]+:[^/\s]+@'):
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line):
                problems.append('%s:%d puts a credential in a URL: %s'
                                % (QA_MD, number, line.strip()))
    problems.extend(carries(QA_MD, ['gh auth login', 'credential helper']))
    return problems


def qa_limit_problems():
    body = section(read(QA_MD), r'limits')
    if body is None:
        return ['%s has no limits section' % QA_MD]
    flattened = flat(body)
    problems = ['%s limits do not state %r' % (QA_MD, needle)
                for needle in ("It does not run the project's tests.",
                               'A `@manual` proof has no test.')
                if needle not in flattened]
    problems.extend(carries(QA_MD, ['This skill cannot sign a commit.']))
    return problems
