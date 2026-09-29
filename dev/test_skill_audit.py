"""Text checks for the audit skill, `skills/audit/SKILL.md`.

Every rule of `specs/skills/skill_audit.md` is proved here, one test per
proof; a broken copy of the skill is a second assertion inside the test of
the proof it guards. The readers, the checks and the broken copies this file shares with
the other skill test files are in `dev/skill_checks.py`; the checks that
only this skill needs, each reading one part of the skill, are below the
tests.
"""

import re

import skill_checks
from skill_checks import (COMMAND_REF, carries, field, flat, frontmatter,
                          frontmatter_problems, next_step_problems,
                          read, refusals, replace, resub, same_line,
                          sections, sentence_with, skill_ceiling_problems,
                          skill_path, table_rows,
                          undirected_outcome_problems)

SKILL = skill_path('audit')

LEFT_TO_DO = ('- `Left to do:` lists work: `→ Run:` the command its first line '
              'names')


def refused(monkeypatch, check, edit, expected, rel=SKILL):
    """What `refusals` reports for one broken copy: empty when refused."""
    return refusals(monkeypatch, check, [(rel, edit, expected)])


def description_line():
    return 'description: %s' % description()


def description():
    return field(frontmatter(read(SKILL)), 'description')


class TestSkillAudit:

    # --- RULE-1: the frontmatter -----------------------------------------

    # purlin: skill_audit PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self, monkeypatch):
        assert skill_frontmatter_problems() == []
        line = description_line()
        assert refusals(monkeypatch, skill_frontmatter_problems, [
            (SKILL, replace('name: audit\n'),
             "%s frontmatter name is None, expected 'audit'" % SKILL),
            (SKILL, replace(line, 'description:'), NO_DESCRIPTION),
            (SKILL, replace(line, 'description:\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(line, 'description: |\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(line, 'description: >-\n  ' + description()),
             NO_DESCRIPTION),
            (SKILL, replace(line, line + '\n  and a second line'),
             NO_DESCRIPTION),
        ]) == []

    # --- RULE-11: the command reference's row ----------------------------

    # purlin: skill_audit PROOF-17
    def test_the_command_reference_has_a_row_with_a_purpose(
            self, monkeypatch):
        assert command_row_problems() == []
        row = command_row()
        cells = row.split('|')
        cells[2] = ' '
        assert refusals(monkeypatch, command_row_problems, [
            (COMMAND_REF, replace(row + '\n'), NO_ROW),
            (COMMAND_REF, replace(row, '|'.join(cells)), NO_ROW),
        ]) == []

    # --- RULE-2: the run script ------------------------------------------

    # purlin: skill_audit PROOF-2
    def test_one_line_runs_the_run_script_with_audit(self, monkeypatch):
        assert run_line_problems() == []
        assert refused(monkeypatch, run_line_problems,
                       replace('purlin_run.py" --audit',
                               'purlin_run.py"\n--audit'),
                       '%s has no single line carrying all of' % SKILL) == []

    # --- RULE-12: the remote runner's arm --------------------------------

    # purlin: skill_audit PROOF-26
    def test_one_sentence_says_nobody_runs_the_runner_arm(self, monkeypatch):
        assert runner_sentence_problems() == []
        assert refusals(monkeypatch, runner_sentence_problems, [
            (SKILL, resub(r'; you never\s+run it by hand\.', '.'),
             RUNNER_SENTENCE),
            (SKILL, resub(r'runs no audit; you never\s+run it by hand\.',
                          'runs no audit. Then you never run it by hand.'),
             RUNNER_SENTENCE),
        ]) == []

    # --- RULE-3: the closing section names the next step -----------------

    # purlin: skill_audit PROOF-3
    def test_it_closes_on_the_first_line_of_left_to_do(self, monkeypatch):
        assert audit_next_step_problems() == []
        text = read(SKILL)
        last = text.rindex('\n## ')
        before = sections(text)[-2][0]
        assert refusals(monkeypatch, audit_next_step_problems, [
            (SKILL, lambda t: t[:last + 1],
             '%s closes with the section %r' % (SKILL, before)),
            (SKILL, replace(LEFT_TO_DO, LEFT_TO_DO.replace('→ ', '')),
             '%s closing outcome gives no → directive' % SKILL),
            (SKILL, resub(r'^- `Nothing left to do\.`.*\Z'),
             "%s closing section does not name 'Nothing left to do.'"
             % SKILL),
            (SKILL, replace('; the first line of `Left to do` is the next '
                            'step:', ':'),
             "%s closing section does not name 'the first line of "
             "`Left to do`'" % SKILL),
        ]) == []

    # --- RULE-4: the ceiling ---------------------------------------------

    # purlin: skill_audit PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('audit') == []

    # purlin: skill_audit PROOF-31
    def test_a_copy_of_exactly_105_lines_is_not_refused(self, monkeypatch):
        assert ceiling_report(monkeypatch, 105) == []

    # purlin: skill_audit PROOF-32
    def test_a_copy_of_106_lines_is_refused_with_its_count(self, monkeypatch):
        assert ceiling_report(monkeypatch, 106) == [
            '%s is 106 lines, ceiling 105' % SKILL]

    # --- RULE-5: which evidence counts under which gate ------------------

    # purlin: skill_audit PROOF-5
    def test_both_sources_count_under_every_gate(self, monkeypatch):
        assert source_table_problems() == []
        assert refusals(monkeypatch, source_table_problems, [
            (SKILL, resub(r'(^\| local \|[^\n]*)`strong`, ', r'\1'),
             "%s local row does not count under 'strong'" % SKILL),
            (SKILL, resub(r'^\| ci \|[^\n]*\n'),
             "%s source table has no 'ci' row" % SKILL),
        ]) == []

    # --- RULE-13: both evidence folders ----------------------------------

    # purlin: skill_audit PROOF-33
    def test_both_evidence_folders_are_named(self, monkeypatch):
        assert evidence_folder_problems() == []
        assert refused(monkeypatch, evidence_folder_problems,
                       lambda t: t.replace('.purlin/evidence/ci/',
                                           '.purlin/evidence/remote/'),
                       "%s does not name '.purlin/evidence/ci/'"
                       % SKILL) == []

    # --- RULE-6: what each gate runs -------------------------------------

    # purlin: skill_audit PROOF-6
    def test_the_passed_row_reads_with_the_ai_audit_and_measures_nothing(
            self, monkeypatch):
        assert passed_row_problems() == []
        assert refusals(monkeypatch, passed_row_problems, [
            (SKILL, replace('Runs the tests and the AI audit, and no breaks',
                            'Runs the tests, and no breaks'),
             '%s passed row does not say the run reads the rules with the '
             'AI audit' % SKILL),
            (SKILL, replace('test strength is not measured, and '),
             "%s passed row does not name 'not measured'" % SKILL),
        ]) == []

    # purlin: skill_audit PROOF-37
    def test_the_strong_row_runs_the_breaks_against_the_minimum(
            self, monkeypatch):
        assert strong_row_problems() == []
        assert refused(monkeypatch, strong_row_problems,
                       replace('Runs the breaks too where mutation testing is '
                               'on; a rule', 'A rule'),
                       "%s strong row does not name 'breaks'" % SKILL) == []

    # purlin: skill_audit PROOF-38
    def test_the_signed_row_runs_what_strong_runs_and_counts_both(
            self, monkeypatch):
        assert signed_row_problems() == []
        assert refusals(monkeypatch, signed_row_problems, [
            (SKILL, replace('| The same as `strong`.', '| Runs the tests.'),
             '%s signed row does not run what the strong row runs' % SKILL),
            (SKILL, replace('Evidence either source wrote counts here too'),
             "%s signed row does not say 'counts here too'" % SKILL),
        ]) == []

    # --- RULE-8: the audit's line, its ending, its commit ----------------

    # purlin: skill_audit PROOF-11
    def test_the_audit_line_comes_before_the_ending(self, monkeypatch):
        assert audit_ending_problems() == []
        assert refused(monkeypatch, audit_ending_problems,
                       resub(r'and ends on the status table,\s+the summary and '
                             r'`Left to do`'),
                       "%s has no sentence carrying all of 'AI audit: <n> "
                       "rules read, <s> strong, <w> weak.'" % SKILL) == []

    # purlin: skill_audit PROOF-12
    def test_the_commit_sentence_names_the_evidence_subject(
            self, monkeypatch):
        assert commit_sentence_problems() == []
        assert refused(monkeypatch, commit_sentence_problems,
                       replace('`purlin: evidence at <sha7>`',
                               '`purlin: evidence for <sha7>`'),
                       "%s has no sentence carrying all of 'you add "
                       "`--commit`'" % SKILL) == []

    # --- RULE-9: an audit cannot make a signature appear -----------------

    # purlin: skill_audit PROOF-39
    def test_a_signature_does_not_set_the_exit_code(self, monkeypatch):
        assert signature_sentence_problems() == []
        assert refused(monkeypatch, signature_sentence_problems,
                       resub(r', so a rule waiting on one does not set\s+the '
                             r'code\.', '.'),
                       "%s has no sentence carrying all of 'An audit cannot "
                       "make a signature appear'" % SKILL) == []

    # --- RULE-10: the breaking tool's time limit -------------------------

    # purlin: skill_audit PROOF-50
    def test_the_arm_timeout_is_in_the_usage_and_passed_on(
            self, monkeypatch):
        assert arm_timeout_problems() == []
        assert refusals(monkeypatch, arm_timeout_problems, [
            (SKILL, replace(ARM_TIMEOUT_USAGE + '\n'),
             '%s usage block has no line %r' % (SKILL, ARM_TIMEOUT_USAGE)),
            (SKILL, resub(r',? and\s+`--arm-timeout\s+<seconds>`\s+when the '
                          r'person\s+gave it'),
             "%s step that runs the script does not carry %r"
             % (SKILL, ARM_TIMEOUT_PASSED)),
        ]) == []

    # --- RULE-7: where the audit lands -----------------------------------

    # purlin: skill_audit PROOF-7
    def test_the_audit_is_written_into_the_local_file(self, monkeypatch):
        assert local_file_problems() == []
        assert refused(monkeypatch, local_file_problems,
                       resub(r'into(\s+)`\.purlin/evidence/local/',
                             r'into\1`.purlin/evidence/ci/'),
                       "%s does not carry 'into `.purlin/evidence/local/"
                       "<feature>.json`'" % SKILL) == []

    # --- RULE-14: what a file keeps --------------------------------------

    # purlin: skill_audit PROOF-44
    def test_one_sentence_says_what_a_file_keeps(self, monkeypatch):
        assert retention_problems() == []
        assert refusals(monkeypatch, retention_problems, [
            (SKILL, resub(r'^A file keeps the newest section.*?git log`\. '),
             "%s does not carry 'the newest section per operating system'"
             % SKILL),
            (SKILL, replace(' and the newest audit entry per rule'),
             "%s has no sentence carrying all of 'A file keeps the newest "
             "section per operating system', 'the newest audit entry per "
             "rule'" % SKILL),
        ]) == []

    # --- RULE-15: --remote belongs to purlin:test ------------------------

    # purlin: skill_audit PROOF-45
    def test_remote_belongs_to_purlin_test(self, monkeypatch):
        assert remote_problems() == []
        assert refused(monkeypatch, remote_problems,
                       resub(r'`--remote` belongs\s+to', 'use'),
                       "%s does not carry '`--remote` belongs to `purlin:test "
                       "--remote`'" % SKILL) == []


# ---------------------------------------------------------------------------
# The checks this skill needs. Each reads one part of the skill and returns
# the problems it found, empty when that part is right.
# ---------------------------------------------------------------------------

NO_DESCRIPTION = '%s frontmatter carries no one-line description' % SKILL
NO_ROW = '%s carries no row for purlin:audit' % COMMAND_REF
RUNNER_SENTENCE = '%s has no sentence carrying all of' % SKILL


def skill_frontmatter_problems():
    """The shared frontmatter check, the skill's own lines only."""
    return [p for p in frontmatter_problems('audit') if p.startswith(SKILL)]


def command_row_problems():
    """The shared frontmatter check, the command reference's lines only."""
    return [p for p in frontmatter_problems('audit')
            if p.startswith(COMMAND_REF)]


def command_row():
    return next(line for line in read(COMMAND_REF).splitlines()
                if re.match(r'\| `purlin:audit[ `]', line))


def run_line_problems():
    return same_line(SKILL, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--audit'])


def runner_sentence_problems():
    return sentence_with(SKILL, [
        'A remote runner runs the same script in an arm of its own',
        'you never run it by hand'])


def audit_next_step_problems():
    """The closing section names the next step, the first line of `Left to
    do`, with a directive, and lets `Nothing left to do.` through."""
    problems = (next_step_problems('audit')
                + undirected_outcome_problems('audit'))
    body = sections(read(SKILL))[-1][1]
    problems += ['%s closing section does not name %r' % (SKILL, needle)
                 for needle in ('the first line of `Left to do`',
                                'Nothing left to do.')
                 if needle not in ' '.join(body.split())]
    return problems


def ceiling_report(monkeypatch, count):
    """What the ceiling check reports for a copy of the skill made exactly
    `count` lines long, cut or padded with a line of prose at its end."""
    real = skill_checks.read
    lines = real(SKILL).splitlines(True)[:count]
    lines += ['A padding line of prose.\n'] * (count - len(lines))
    copy = ''.join(lines)
    monkeypatch.setattr(skill_checks, 'read',
                        lambda rel: copy if rel == SKILL else real(rel))
    return skill_ceiling_problems('audit')


def source_rows():
    return {cells[0]: cells[-1]
            for cells in table_rows(read(SKILL), '| Source |')}


def source_table_problems():
    rows = source_rows()
    problems = ['%s source table has no %r row' % (SKILL, source)
                for source in ('ci', 'local') if source not in rows]
    if problems:
        return problems
    for source in ('ci', 'local'):
        for gate in ('passed', 'strong', 'signed'):
            if gate not in rows[source]:
                problems.append('%s %s row does not count under %r'
                                % (SKILL, source, gate))
    return problems


def evidence_folder_problems():
    return ['%s does not name %r' % (SKILL, folder)
            for folder in ('.purlin/evidence/ci/', '.purlin/evidence/local/')
            if folder not in read(SKILL)]


def gate_row(gate):
    rows = {cells[0]: cells[-1]
            for cells in table_rows(read(SKILL), '| Gate |')}
    return rows.get('`%s`' % gate)


def passed_row_problems():
    row = gate_row('passed')
    if row is None:
        return ['%s gate table has no `passed` row' % SKILL]
    problems = []
    if 'the AI audit' not in row:
        problems.append('%s passed row does not say the run reads the rules '
                        'with the AI audit' % SKILL)
    if 'not measured' not in row:
        problems.append("%s passed row does not name 'not measured'" % SKILL)
    return problems


def strong_row_problems():
    row = gate_row('strong')
    if row is None:
        return ['%s gate table has no `strong` row' % SKILL]
    return ['%s strong row does not name %r' % (SKILL, needle)
            for needle in ('breaks', 'minimum') if needle not in row]


def signed_row_problems():
    row = gate_row('signed')
    if row is None:
        return ['%s gate table has no `signed` row' % SKILL]
    problems = []
    if 'The same as `strong`' not in row:
        problems.append('%s signed row does not run what the strong row runs'
                        % SKILL)
    if 'counts here too' not in row:
        problems.append("%s signed row does not say 'counts here too'"
                        % SKILL)
    return problems


def audit_ending_problems():
    return sentence_with(SKILL, [
        'AI audit: <n> rules read, <s> strong, <w> weak.',
        'ends on the status table, the summary and `Left to do`'])


def commit_sentence_problems():
    return sentence_with(SKILL, ['you add `--commit`',
                                 'the subject `purlin: evidence at <sha7>`'])


def signature_sentence_problems():
    return sentence_with(SKILL, ['An audit cannot make a signature appear',
                                 'a rule waiting on one does not set the '
                                 'code'])


def local_file_problems():
    return carries(SKILL, ['into `.purlin/evidence/local/<feature>.json`'])


def retention_problems():
    return (carries(SKILL, ['the newest section per operating system'])
            + sentence_with(SKILL, [
                'A file keeps the newest section per operating system',
                'the newest audit entry per rule']))


def remote_problems():
    return carries(SKILL, ['`--remote` belongs to `purlin:test --remote`'])


# The usage line of `--arm-timeout`, character for character, and what the
# step that runs the script says of it.
ARM_TIMEOUT_USAGE = ('purlin:audit --arm-timeout <seconds>  Give the breaking '
                     'tool longer per feature')
ARM_TIMEOUT_PASSED = '`--arm-timeout <seconds>` when the person gave it'


def arm_timeout_problems():
    text = read(SKILL)
    problems = []
    usage = re.search(r'^## Usage\n+```\n(.*?)\n```', text, re.S | re.M)
    if usage is None or ARM_TIMEOUT_USAGE not in usage.group(1).split('\n'):
        problems.append('%s usage block has no line %r'
                        % (SKILL, ARM_TIMEOUT_USAGE))
    step = next((body for heading, body in sections(text)
                 if heading.startswith('Step 1')), '')
    if ARM_TIMEOUT_PASSED not in flat(step):
        problems.append('%s step that runs the script does not carry %r'
                        % (SKILL, ARM_TIMEOUT_PASSED))
    return problems
