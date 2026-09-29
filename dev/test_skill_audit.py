"""Text checks for the audit skill, `skills/audit/SKILL.md`.

Every rule of `specs/skills/skill_audit.md` is proved here, one test per
proof. The readers, the checks and the broken copies this file shares with
the other skill test files are in `dev/skill_checks.py`; the checks that
only this skill needs, each reading one part of the skill, are below the
tests.
"""

import re

import skill_checks
from skill_checks import (COMMAND_REF, carries, field, frontmatter,
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

    # --- RULE-1: the frontmatter and the command reference's row ---------

    # purlin: skill_audit PROOF-1
    def test_the_frontmatter_names_the_skill_on_one_line(self):
        assert skill_frontmatter_problems() == []

    # purlin: skill_audit PROOF-17
    def test_the_command_reference_has_a_row_with_a_purpose(self):
        assert command_row_problems() == []

    # purlin: skill_audit PROOF-18
    def test_a_deleted_name_line_is_refused(self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace('name: audit\n'),
                       "%s frontmatter name is None, expected 'audit'"
                       % SKILL) == []

    # purlin: skill_audit PROOF-19
    def test_an_empty_description_is_refused(self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(), 'description:'),
                       NO_DESCRIPTION) == []

    # purlin: skill_audit PROOF-20
    def test_a_description_moved_to_the_line_below_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               'description:\n  ' + description()),
                       NO_DESCRIPTION) == []

    # purlin: skill_audit PROOF-21
    def test_a_description_written_as_a_bar_block_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               'description: |\n  ' + description()),
                       NO_DESCRIPTION) == []

    # purlin: skill_audit PROOF-22
    def test_a_description_written_as_a_folded_block_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               'description: >-\n  ' + description()),
                       NO_DESCRIPTION) == []

    # purlin: skill_audit PROOF-23
    def test_a_description_run_on_to_a_second_line_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, skill_frontmatter_problems,
                       replace(description_line(),
                               description_line() + '\n  and a second line'),
                       NO_DESCRIPTION) == []

    # purlin: skill_audit PROOF-24
    def test_a_deleted_command_row_is_refused(self, monkeypatch):
        assert refused(monkeypatch, command_row_problems,
                       replace(command_row() + '\n'), NO_ROW,
                       rel=COMMAND_REF) == []

    # purlin: skill_audit PROOF-25
    def test_a_command_row_with_no_purpose_is_refused(self, monkeypatch):
        row = command_row()
        cells = row.split('|')
        cells[2] = ' '
        assert refused(monkeypatch, command_row_problems,
                       replace(row, '|'.join(cells)), NO_ROW,
                       rel=COMMAND_REF) == []

    # --- RULE-2: the run script, and the remote runner's arm -------------

    # purlin: skill_audit PROOF-2
    def test_one_line_runs_the_run_script_with_audit(self):
        assert run_line_problems() == []

    # purlin: skill_audit PROOF-26
    def test_one_sentence_says_nobody_runs_the_runner_arm(self):
        assert runner_sentence_problems() == []

    # purlin: skill_audit PROOF-27
    def test_audit_moved_off_the_run_line_is_refused(self, monkeypatch):
        assert refused(monkeypatch, run_line_problems,
                       replace('purlin_run.py" --audit',
                               'purlin_run.py"\n--audit'),
                       '%s has no single line carrying all of' % SKILL) == []

    # purlin: skill_audit PROOF-28
    def test_a_runner_sentence_without_by_hand_is_refused(self, monkeypatch):
        assert refused(monkeypatch, runner_sentence_problems,
                       replace('; you never run it by hand.', '.'),
                       RUNNER_SENTENCE) == []

    # purlin: skill_audit PROOF-29
    def test_by_hand_in_a_sentence_of_its_own_is_refused(self, monkeypatch):
        assert refused(monkeypatch, runner_sentence_problems,
                       replace('runs no audit; you never run it by hand.',
                               'runs no audit. Then you never run it by '
                               'hand.'),
                       RUNNER_SENTENCE) == []

    # --- RULE-3: the closing section names the next step -----------------

    # purlin: skill_audit PROOF-3
    def test_it_closes_on_the_first_line_of_left_to_do(self):
        assert audit_next_step_problems() == []

    # purlin: skill_audit PROOF-8
    def test_a_deleted_closing_section_is_refused(self, monkeypatch):
        last = read(SKILL).rindex('\n## ')
        assert refused(monkeypatch, audit_next_step_problems,
                       lambda t: t[:last + 1],
                       "%s closes with the section 'Step 5: retention'"
                       % SKILL) == []

    # purlin: skill_audit PROOF-9
    def test_an_undirected_left_to_do_outcome_is_refused(self, monkeypatch):
        assert refused(monkeypatch, audit_next_step_problems,
                       replace(LEFT_TO_DO, LEFT_TO_DO.replace('→ ', '')),
                       '%s closing outcome gives no → directive' % SKILL) == []

    # purlin: skill_audit PROOF-10
    def test_a_missing_nothing_left_outcome_is_refused(self, monkeypatch):
        assert refused(monkeypatch, audit_next_step_problems,
                       resub(r'^- `Nothing left to do\.`.*\Z'),
                       "%s closing section does not name 'Nothing left to "
                       "do.'" % SKILL) == []

    # purlin: skill_audit PROOF-30
    def test_a_closing_section_without_the_first_line_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, audit_next_step_problems,
                       replace('; the first line of `Left to do` is the next '
                               'step:', ':'),
                       "%s closing section does not name 'the first line of "
                       "`Left to do`'" % SKILL) == []

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
    def test_both_sources_count_under_every_gate(self):
        assert source_table_problems() == []

    # purlin: skill_audit PROOF-33
    def test_both_evidence_folders_are_named(self):
        assert evidence_folder_problems() == []

    # purlin: skill_audit PROOF-34
    def test_a_local_row_without_strong_is_refused(self, monkeypatch):
        assert refused(monkeypatch, source_table_problems,
                       resub(r'(^\| local \|[^\n]*)`strong`, ', r'\1'),
                       "%s local row does not count under 'strong'"
                       % SKILL) == []

    # purlin: skill_audit PROOF-35
    def test_a_missing_ci_row_is_refused(self, monkeypatch):
        assert refused(monkeypatch, source_table_problems,
                       resub(r'^\| ci \|[^\n]*\n'),
                       "%s source table has no 'ci' row" % SKILL) == []

    # purlin: skill_audit PROOF-36
    def test_a_skill_naming_no_ci_folder_is_refused(self, monkeypatch):
        assert refused(monkeypatch, evidence_folder_problems,
                       lambda t: t.replace('.purlin/evidence/ci/',
                                           '.purlin/evidence/remote/'),
                       "%s does not name '.purlin/evidence/ci/'"
                       % SKILL) == []

    # --- RULE-6: what the gate changes, the audit's line and its ending --

    # purlin: skill_audit PROOF-6
    def test_the_passed_row_reads_with_the_ai_audit_and_measures_nothing(
            self):
        assert passed_row_problems() == []

    # purlin: skill_audit PROOF-37
    def test_the_strong_row_runs_the_breaks_against_the_minimum(self):
        assert strong_row_problems() == []

    # purlin: skill_audit PROOF-38
    def test_the_signed_row_runs_what_strong_runs_and_counts_both(self):
        assert signed_row_problems() == []

    # purlin: skill_audit PROOF-11
    def test_the_audit_line_comes_before_the_ending(self):
        assert audit_ending_problems() == []

    # purlin: skill_audit PROOF-12
    def test_the_commit_sentence_names_the_evidence_subject(self):
        assert commit_sentence_problems() == []

    # purlin: skill_audit PROOF-39
    def test_a_signature_does_not_set_the_exit_code(self):
        assert signature_sentence_problems() == []

    # purlin: skill_audit PROOF-13
    def test_a_passed_row_without_the_ai_audit_is_refused(self, monkeypatch):
        assert refused(monkeypatch, passed_row_problems,
                       replace('Runs the tests and the AI audit, and no breaks',
                               'Runs the tests, and no breaks'),
                       '%s passed row does not say the run reads the rules '
                       'with the AI audit' % SKILL) == []

    # purlin: skill_audit PROOF-40
    def test_a_passed_row_without_not_measured_is_refused(self, monkeypatch):
        assert refused(monkeypatch, passed_row_problems,
                       replace('test strength is not measured, and '),
                       "%s passed row does not name 'not measured'"
                       % SKILL) == []

    # purlin: skill_audit PROOF-41
    def test_a_strong_row_without_the_breaks_is_refused(self, monkeypatch):
        assert refused(monkeypatch, strong_row_problems,
                       replace('Runs the breaks too where mutation testing is '
                               'on; a rule', 'A rule'),
                       "%s strong row does not name 'breaks'" % SKILL) == []

    # purlin: skill_audit PROOF-14
    def test_a_signed_row_that_differs_from_strong_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, signed_row_problems,
                       replace('| The same as `strong`.', '| Runs the tests.'),
                       '%s signed row does not run what the strong row runs'
                       % SKILL) == []

    # purlin: skill_audit PROOF-42
    def test_a_signed_row_without_counts_here_too_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, signed_row_problems,
                       replace('Evidence either source wrote counts here too'),
                       "%s signed row does not say 'counts here too'"
                       % SKILL) == []

    # purlin: skill_audit PROOF-15
    def test_an_audit_line_without_the_ending_is_refused(self, monkeypatch):
        assert refused(monkeypatch, audit_ending_problems,
                       resub(r'and ends on the status table,\s+the summary and '
                             r'`Left to do`'),
                       "%s has no sentence carrying all of 'AI audit: <n> "
                       "rules read, <s> strong, <w> weak.'" % SKILL) == []

    # purlin: skill_audit PROOF-43
    def test_a_commit_sentence_with_another_subject_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, commit_sentence_problems,
                       replace('`purlin: evidence at <sha7>`',
                               '`purlin: evidence for <sha7>`'),
                       "%s has no sentence carrying all of 'you add "
                       "`--commit`'" % SKILL) == []

    # purlin: skill_audit PROOF-16
    def test_a_signature_sentence_without_the_exit_code_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, signature_sentence_problems,
                       resub(r', so a rule waiting on one does not set\s+the '
                             r'code\.', '.'),
                       "%s has no sentence carrying all of 'An audit cannot "
                       "make a signature appear'" % SKILL) == []

    # --- RULE-7: where the audit lands, what a file keeps, --remote ------

    # purlin: skill_audit PROOF-7
    def test_the_audit_is_written_into_the_local_file(self):
        assert local_file_problems() == []

    # purlin: skill_audit PROOF-44
    def test_one_sentence_says_what_a_file_keeps(self):
        assert retention_problems() == []

    # purlin: skill_audit PROOF-45
    def test_remote_belongs_to_purlin_test(self):
        assert remote_problems() == []

    # purlin: skill_audit PROOF-46
    def test_a_deleted_retention_sentence_is_refused(self, monkeypatch):
        assert refused(monkeypatch, retention_problems,
                       resub(r'^A file keeps the newest section.*?git log`\. '),
                       "%s does not carry 'the newest section per operating "
                       "system'" % SKILL) == []

    # purlin: skill_audit PROOF-47
    def test_a_retention_sentence_without_the_audit_entry_is_refused(
            self, monkeypatch):
        assert refused(monkeypatch, retention_problems,
                       replace(' and the newest audit entry per rule'),
                       "%s has no sentence carrying all of 'A file keeps the "
                       "newest section per operating system', 'the newest "
                       "audit entry per rule'" % SKILL) == []

    # purlin: skill_audit PROOF-48
    def test_an_audit_written_into_the_ci_file_is_refused(self, monkeypatch):
        assert refused(monkeypatch, local_file_problems,
                       replace('into\n`.purlin/evidence/local/',
                               'into\n`.purlin/evidence/ci/'),
                       "%s does not carry 'into `.purlin/evidence/local/"
                       "<feature>.json`'" % SKILL) == []

    # purlin: skill_audit PROOF-49
    def test_remote_not_given_to_purlin_test_is_refused(self, monkeypatch):
        assert refused(monkeypatch, remote_problems,
                       replace('so `--remote` belongs to', 'so use'),
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
