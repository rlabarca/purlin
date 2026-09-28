"""Text checks for the audit skill, `skills/audit/SKILL.md`.

Every rule of `specs/skills/skill_audit.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems,
                          next_step_refusals, read, refusals, replace, resub,
                          same_line, sentence_with, skill_ceiling_problems,
                          skill_path, table_rows, undirected_outcome_problems)


class TestSkillAudit:

    # purlin: skill_audit PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('audit') == []

    # purlin: skill_audit PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'audit') == []

    # purlin: skill_audit PROOF-2
    def test_it_runs_the_run_script_and_leaves_ci_to_ci(self):
        assert audit_run_problems() == []

    # purlin: skill_audit PROOF-2
    def test_a_run_line_or_a_runner_sentence_broken_is_refused(
            self, monkeypatch):
        rel = skill_path('audit')
        assert refusals(monkeypatch, audit_run_problems, [
            (rel, replace('purlin_run.py" --audit', 'purlin_run.py"\n--audit'),
             '%s has no single line carrying all of' % rel),
            (rel, replace('; you never run it by hand.', '.'),
             "'you never run it by hand'"),
            (rel, replace('runs no audit; you never run it by hand.',
                          'runs no audit. Then you never run it by hand.'),
             '%s has no sentence carrying all of' % rel),
        ]) == []

    # purlin: skill_audit PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('audit')
                + undirected_outcome_problems('audit')) == []

    # purlin: skill_audit PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'audit', '| Test strength below',
            '| A test failed | `→ Run: purlin:build <feature>` |') == []

    # purlin: skill_audit PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('audit') == []

    # purlin: skill_audit PROOF-5
    def test_it_says_which_evidence_counts_under_which_gate(self):
        assert evidence_source_problems() == []

    # purlin: skill_audit PROOF-6
    def test_the_gate_decides_the_breaks_and_the_audit_writes_the_evidence(self):
        assert audit_gate_problems() == []

    # purlin: skill_audit PROOF-6
    def test_a_gate_row_or_a_gate_sentence_broken_is_refused(
            self, monkeypatch):
        rel = skill_path('audit')
        assert refusals(monkeypatch, audit_gate_problems, [
            (rel, replace('not measured; '),
             "%s passed row does not name 'not measured'" % rel),
            (rel, replace('Runs the tests and the AI audit, and no breaks',
                          'Runs the tests, and no breaks'),
             '%s passed row does not say the run reads the rules with the '
             'AI audit' % rel),
            (rel, replace('| The same as `strong`.', '| Runs the tests.'),
             '%s signed row does not run what the strong row runs' % rel),
            (rel, replace('`--commit`, which commits', '`--commit`. That '
                          'commits'),
             "%s has no sentence carrying all of 'you add `--commit`'" % rel),
            (rel, replace(', so a rule waiting on one does not set the code.',
                          '.'),
             "%s has no sentence carrying all of 'An audit cannot make a "
             "signature appear'" % rel),
            (rel, replace('counts here too', 'counts'),
             "%s does not say 'counts here too'" % rel),
        ]) == []

    # purlin: skill_audit PROOF-7
    def test_it_names_the_evidence_and_the_retention(self):
        assert audit_evidence_problems() == []

    # purlin: skill_audit PROOF-7
    def test_a_retention_or_evidence_sentence_broken_is_refused(
            self, monkeypatch):
        rel = skill_path('audit')
        assert refusals(monkeypatch, audit_evidence_problems, [
            (rel, resub(r'^A file keeps the newest section.*?git log`\. '),
             "%s does not carry 'the newest section per operating system'"
             % rel),
            (rel, replace('into\n`.purlin/evidence/local/', 'into\n'
                          '`.purlin/evidence/ci/'),
             "%s does not carry 'into `.purlin/evidence/local/<feature>"
             ".json`'" % rel),
            (rel, replace(' and the newest audit entry per rule'),
             "%s has no sentence carrying all of 'A file keeps the newest "
             "section per operating system', 'the newest audit entry per "
             "rule'" % rel),
            (rel, replace('so `--remote` belongs to', 'so use'),
             "%s does not carry '`--remote` belongs to `purlin:test "
             "--remote`'" % rel),
        ]) == []


def audit_run_problems():
    rel = skill_path('audit')
    return (same_line(rel, [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"', '--audit'])
        + sentence_with(rel, [
            'A remote runner runs the same script in an arm of its own',
            'you never run it by hand']))


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
    if 'the AI audit' not in rows['`passed`']:
        problems.append('%s passed row does not say the run reads the rules '
                        'with the AI audit' % rel)
    for needle in ('breaks', 'minimum'):
        if needle not in rows['`strong`']:
            problems.append('%s strong row does not name %r' % (rel, needle))
    if 'The same as `strong`' not in rows['`signed`']:
        problems.append('%s signed row does not run what the strong row runs'
                        % rel)
    for needle in ('counts here too', 'Audit: <n> strong, <n> weak.',
                   'gate strong met: <n> of <rules> rules',
                   'cannot make a signature appear',
                   'purlin: evidence at <sha7>'):
        if needle not in flat(read(rel)):
            problems.append('%s does not say %r' % (rel, needle))
    problems += sentence_with(rel, ['you add `--commit`',
                                    'the subject `purlin: evidence at <sha7>`'])
    problems += sentence_with(rel, ['An audit cannot make a signature appear',
                                    'a rule waiting on one does not set the '
                                    'code'])
    return problems


def audit_evidence_problems():
    rel = skill_path('audit')
    return (carries(rel, [
        'into `.purlin/evidence/local/<feature>.json`',
        'the newest section per operating system', 'purlin:test --remote',
        '`--remote` belongs to `purlin:test --remote`'])
        + sentence_with(rel, [
            'A file keeps the newest section per operating system',
            'the newest audit entry per rule']))
