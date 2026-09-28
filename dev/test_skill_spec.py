"""Text checks for the spec skill, `skills/spec/SKILL.md`.

Every rule of `specs/skills/skill_spec.md` is proved here. The readers, the
checks and the broken copies this file shares with the other skill test files
are in `dev/skill_checks.py`.
"""

import re

from skill_checks import (carries, flat, frontmatter_problems,
                          frontmatter_refusals, read, refusals, replace, resub,
                          section, sections, sentence_with,
                          skill_ceiling_problems, skill_path, swap_first)


class TestSkillSpec:

    # purlin: skill_spec PROOF-1
    def test_the_frontmatter_names_the_skill(self):
        assert frontmatter_problems('spec') == []

    # purlin: skill_spec PROOF-1
    def test_a_broken_frontmatter_is_refused(self, monkeypatch):
        assert frontmatter_refusals(monkeypatch, 'spec') == []

    # purlin: skill_spec PROOF-2
    def test_it_allocates_ids_against_the_default_branch(self):
        assert spec_id_problems() == []

    # purlin: skill_spec PROOF-2
    def test_a_missing_id_command_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        assert refusals(monkeypatch, spec_id_problems, [
            (rel, resub(r'^```bash\ngit show origin/main:.*?^```\n'),
             "%s does not carry 'git show origin/main:'" % rel),
        ]) == []

    # purlin: skill_spec PROOF-3
    def test_it_closes_by_naming_the_build(self):
        assert spec_offer_problems() == []

    # purlin: skill_spec PROOF-3
    def test_a_broken_offer_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        offer = 'Spec saved: <name>. Next: purlin:build <name>'
        assert refusals(monkeypatch, spec_offer_problems, [
            (rel, replace(offer, 'Spec written. Shall I build it?'),
             '%s closing section does not carry the line %r' % (rel, offer)),
            (rel, replace('```\n%s\n```' % offer, offer),
             '%s closing section does not set the line %r in a fenced block'
             % (rel, offer)),
            (rel, replace(' and nothing after it'),
             '%s closing section does not say nothing follows the line'
             % rel),
            (rel, replace('Never start the build yourself', 'Then build it'),
             '%s closing section does not say it never starts the build'
             % rel),
        ]) == []

    # purlin: skill_spec PROOF-4
    def test_it_stays_under_its_ceiling(self):
        assert skill_ceiling_problems('spec') == []

    # purlin: skill_spec PROOF-6
    def test_it_prints_the_proofs_and_asks_before_it_saves(self):
        assert spec_review_problems() == []

    # purlin: skill_spec PROOF-6
    def test_a_missing_or_late_print_step_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        assert refusals(monkeypatch, spec_review_problems, [
            (rel, resub(r'^6\. Print each rule.*?(?=^7\. )'),
             "%s does not carry 'Print each rule with its proofs under it "
             "and ask whether to change any'" % rel),
            (rel, swap_first(
                'Print each rule with its proofs under it and ask whether to '
                'change any. Change what the\n   person asks and print them '
                'again.',
                'Save the spec when the person is satisfied, commit it on its '
                'own, and name `purlin:build`\n   as the next step. This '
                'skill never starts building.'),
             '%s procedure saves the spec before it prints the rules' % rel),
            (rel, replace('`references/spec_quality_guide.md`, "Writing '
                          'proofs", the one home', 'the guide, the one home'),
             '%s does not carry \'Draft every proof against' % rel),
        ]) == []

    # purlin: skill_spec PROOF-5
    def test_it_writes_the_scope_on_every_spec(self):
        assert spec_scope_problems() == []

    # purlin: skill_spec PROOF-5
    def test_a_missing_scope_sentence_is_refused(self, monkeypatch):
        rel = skill_path('spec')
        assert refusals(monkeypatch, spec_scope_problems, [
            (rel, resub(r'^Write `> Scope:` on every spec you create:.*?'
                        r'for it\. '),
             "%s does not carry 'Write `> Scope:` on every spec you create'"
             % rel),
            (rel, replace('the files the requirement touches, or '),
             "%s has no sentence carrying all of 'Write `> Scope:` on every "
             "spec you create', 'the files the requirement touches'" % rel),
            (rel, replace('at the gate `signed` its rules', 'its rules'),
             "%s has no sentence carrying all of 'A spec that names no "
             "files'" % rel),
            (rel, replace('4. Write the metadata, `> Scope:` included,',
                          '4. Write the metadata,'),
             '%s procedure does not name > Scope: in the metadata step'
             % rel),
        ]) == []


def spec_id_problems():
    return carries(skill_path('spec'), [
        'git show origin/main:',
        'allocated against `origin/main`, not against the working tree'])


def spec_scope_problems():
    rel = skill_path('spec')
    problems = carries(rel, [
        'Write `> Scope:` on every spec you create',
        'the paths `purlin:build` will create', 'every run includes it',
        'its rules cannot be signed'])
    problems += sentence_with(rel, [
        'Write `> Scope:` on every spec you create',
        'the files the requirement touches',
        'the paths `purlin:build` will create'])
    problems += sentence_with(rel, [
        'A spec that names no files', 'every run includes it',
        'at the gate `signed` its rules cannot be signed'])
    step = re.search(r'^\d+\. Write the metadata.*$', read(rel), re.M)
    if step is None or '`> Scope:`' not in step.group(0):
        problems.append('%s procedure does not name > Scope: in the '
                        'metadata step' % rel)
    return problems


def spec_review_problems():
    rel = skill_path('spec')
    printing = ('Print each rule with its proofs under it and ask whether to '
                'change any')
    saving = 'Save the spec when the person is satisfied'
    problems = carries(rel, [
        printing, saving,
        'Draft every proof against `references/spec_quality_guide.md`, '
        '"Writing proofs"', 'at least one failure case'])
    body = section(read(rel), r'^Procedure$') or ''
    steps = [flat(item) for item in re.split(r'^\d+\. ', body, flags=re.M)[1:]]
    at = {needle: next((n for n, step in enumerate(steps) if needle in step),
                       None) for needle in (printing, saving)}
    if None in at.values():
        problems.append('%s procedure does not hold both the print step and '
                        'the save step' % rel)
    elif at[printing] > at[saving]:
        problems.append('%s procedure saves the spec before it prints the '
                        'rules' % rel)
    return problems


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
    fences = re.findall(r'^```[a-z]*\n(.*?)^```', body, re.S | re.M)
    if not any(offer in fence.splitlines() for fence in fences):
        problems.append('%s closing section does not set the line %r in a '
                        'fenced block' % (rel, offer))
    if 'end with exactly this and nothing after it' not in flat(body):
        problems.append('%s closing section does not say nothing follows the '
                        'line' % rel)
    if 'Never start the build yourself' not in flat(body):
        problems.append('%s closing section does not say it never starts '
                        'the build' % rel)
    return problems
