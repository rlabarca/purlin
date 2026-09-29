"""Text checks for the spec-from-code skill, `skills/spec-from-code/SKILL.md`.

Every rule of `specs/skills/skill_spec_from_code.md` is proved here. The
readers, the checks and the broken copies this file shares with the other skill
test files are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, next_step_problems,
                          next_step_refusals, read, refusals, replace, resub,
                          section, sections, sentence_with,
                          skill_ceiling_problems, skill_path,
                          undirected_outcome_problems)


class TestSkillSpecFromCode:

    # purlin: skill_spec_from_code PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-2
    def test_it_reads_the_state_before_it_starts(self):
        assert spec_from_code_start_problems() == []

    # purlin: skill_spec_from_code PROOF-2
    def test_a_late_or_unconditional_start_is_refused(self, monkeypatch):
        rel = skill_path('spec-from-code')
        start = re.search(r'^## Before you start\n.*?(?=^## )', read(rel),
                          re.S | re.M).group(0)
        assert refusals(monkeypatch, spec_from_code_start_problems, [
            (rel, replace(start),
             '%s has no section that runs before the survey' % rel),
            (rel, lambda t: t.replace(start, '').replace(
                '## What the rules look like', start +
                '## What the rules look like'),
             '%s start section comes after the Procedure section' % rel),
            (rel, replace('When the project has no `.purlin/config.json`, run',
                          'Read `.purlin/config.json`, then run'),
             '%s start section does not send the reader to purlin:init '
             'when .purlin/config.json is missing' % rel),
        ]) == []

    # purlin: skill_spec_from_code PROOF-3
    def test_it_closes_by_naming_the_next_step(self):
        assert (next_step_problems('spec-from-code')
                + undirected_outcome_problems('spec-from-code')) == []

    # purlin: skill_spec_from_code PROOF-3
    def test_a_broken_closing_section_is_refused(self, monkeypatch):
        assert next_step_refusals(
            monkeypatch, 'spec-from-code', '- Rules with no test at all',
            '- Rules with no test at all: `→ Run: purlin:build <name>` on '
            'the feature with the most of') == []

    # purlin: skill_spec_from_code PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-6
    def test_it_ties_an_existing_test_by_its_marker(self):
        assert spec_from_code_marker_problems() == []

    # purlin: skill_spec_from_code PROOF-10
    def test_an_offer_outside_its_paragraph_is_refused(self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_marker_problems, [
            (rel, replace('never names the test. Then tie the two:',
                          'never names the test.\n\nThen tie the two:'),
             '%s does not offer the marker, and write no new test, in the '
             'paragraph on a test that already shows the proof' % rel),
        ]) == []

    # purlin: skill_spec_from_code PROOF-7
    def test_the_report_ends_on_the_files_with_no_rule(self):
        assert spec_from_code_files_problems() == []

    # purlin: skill_spec_from_code PROOF-11
    def test_a_report_without_the_files_is_refused(self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_files_problems, [
            (rel, resub(r'end the report by listing the source files that '
                        r'got\s+none', 'end the report'),
             "%s has no sentence carrying all of 'Give every source file a "
             "rule where you can'" % rel),
        ]) == []

    # purlin: skill_spec_from_code PROOF-8
    def test_a_test_is_left_untied_for_three_reasons(self):
        assert spec_from_code_untied_problems() == []

    # purlin: skill_spec_from_code PROOF-12
    def test_a_missing_reason_is_refused(self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_untied_problems, [
            (rel, resub(r', or it tests code the project\s+does not own'),
             "%s has no sentence carrying all of 'A test is left untied for "
             "one of three reasons'" % rel),
        ]) == []

    # purlin: skill_spec_from_code PROOF-9
    def test_every_rule_is_written_from_what_its_test_expects(self):
        assert spec_from_code_expects_problems() == []

    # purlin: skill_spec_from_code PROOF-13
    def test_a_skill_that_may_run_the_tests_first_is_refused(
            self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_expects_problems, [
            (rel, resub(r', and\s+no test is run first'),
             "%s has no sentence carrying all of 'Every rule is written from "
             "what its test expects, passing or not'" % rel),
        ]) == []


def spec_from_code_start_problems():
    rel = skill_path('spec-from-code')
    body = section(read(rel), r'before you start')
    if body is None:
        return ['%s has no section that runs before the survey' % rel]
    flattened = flat(body)
    problems = ['%s start section does not name %r' % (rel, needle)
                for needle in ('sync_status', '.purlin/config.json',
                               'purlin:init')
                if needle not in flattened]
    headings = [heading for heading, _ in sections(read(rel))]
    if 'Procedure' not in headings or \
            headings.index('Before you start') > headings.index('Procedure'):
        problems.append('%s start section comes after the Procedure section'
                        % rel)
    if ('When the project has no `.purlin/config.json`, run `purlin:init` '
            'first') not in flattened:
        problems.append('%s start section does not send the reader to '
                        'purlin:init when .purlin/config.json is missing'
                        % rel)
    return problems


def spec_from_code_marker_problems():
    rel = skill_path('spec-from-code')
    problems = carries(rel, [
        'offer to add the marker comment above that test',
        'purlin: <feature> PROOF-<n>', 'write no new test'])
    # The offer belongs to the case of a test that already shows the proof.
    paragraphs = [flat(p) for p in read(rel).split('\n\n')]
    if not any('already shows what a proof asks' in p
               and 'offer to add the marker comment above that test' in p
               and 'write no new test' in p for p in paragraphs):
        problems.append('%s does not offer the marker, and write no new '
                        'test, in the paragraph on a test that already shows '
                        'the proof' % rel)
    return problems


def spec_from_code_files_problems():
    return sentence_with(skill_path('spec-from-code'), [
        'Give every source file a rule where you can',
        'end the report by listing the source files that got none'])


def spec_from_code_untied_problems():
    return sentence_with(skill_path('spec-from-code'), [
        'A test is left untied for one of three reasons',
        'the report lists each such test with its reason',
        'it shows only part of what a rule needs',
        'it repeats a test already tied',
        'it tests code the project does not own'])


def spec_from_code_expects_problems():
    return sentence_with(skill_path('spec-from-code'), [
        'Every rule is written from what its test expects, passing or not',
        'no test is run first'])
