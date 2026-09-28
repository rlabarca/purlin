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
            '- Rules with no test at all: `→ Next: purlin:build <name>` on '
            'the feature with the most of') == []

    # purlin: skill_spec_from_code PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec-from-code') == []

    # purlin: skill_spec_from_code PROOF-5
    def test_every_rule_it_writes_is_at_the_passed_level(self):
        assert spec_from_code_tag_problems() == []

    # purlin: skill_spec_from_code PROOF-5
    def test_a_rule_above_passed_or_no_stated_level_is_refused(
            self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_tag_problems, [
            (rel, replace('HTTP 429 [level: passed]', 'HTTP 429 [level: strong]'),
             '%s example rule carries no [level: passed]: - RULE-1' % rel),
            (rel, resub(r'^- RULE-.*?\n(?=\n)'),
             '%s shows no example rule' % rel),
            (rel, replace('Every rule this skill writes carries '
                          '`[level: passed]`:', 'For example:'),
             "does not carry 'Every rule this skill writes carries "
             "`[level: passed]`'"),
        ]) == []

    # purlin: skill_spec_from_code PROOF-6
    def test_it_ties_an_existing_test_by_its_marker(self):
        assert spec_from_code_marker_problems() == []

    # purlin: skill_spec_from_code PROOF-6
    def test_a_partial_test_marked_or_an_untied_offer_is_refused(
            self, monkeypatch):
        rel = skill_path('spec-from-code')
        assert refusals(monkeypatch, spec_from_code_marker_problems, [
            (rel, replace('test; leave it unmarked and let', 'test; let'),
             "has no sentence carrying all of 'A test that shows part of "
             "what the proof asks', 'is not that test', 'leave it unmarked'"),
            (rel, replace('never names the test. Then tie the two:',
                          'never names the test.\n\nThen tie the two:'),
             '%s does not offer the marker, and write no new test, in the '
             'paragraph on a test that already shows the proof' % rel),
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
        'purlin: <feature> PROOF-<n>', 'write no new test',
        'is not that test'])
    problems += sentence_with(rel, [
        'A test that shows part of what the proof asks', 'is not that test',
        'leave it unmarked'])
    # The offer belongs to the case of a test that already shows the proof.
    paragraphs = [flat(p) for p in read(rel).split('\n\n')]
    if not any('already shows what a proof asks' in p
               and 'offer to add the marker comment above that test' in p
               and 'write no new test' in p for p in paragraphs):
        problems.append('%s does not offer the marker, and write no new '
                        'test, in the paragraph on a test that already shows '
                        'the proof' % rel)
    return problems


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
        'Every rule this skill writes carries `[level: passed]`',
        'Do not write `[level: strong]` or `[level: signed]`']))
    return problems
