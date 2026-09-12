# Feature: skill_build

> Scope: skills/build/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:build` skill reads a spec, loads all its rules (including `> Requires:` dependencies), and implements the feature. It handles test execution, failure diagnosis, and proof generation.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `build`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Skill requires calling `sync_status` after tests and states it is not optional
- RULE-6: Skill includes test failure diagnosis guidance requiring root cause analysis before fixing
- RULE-7: Skill includes mandatory tier tag review for proof descriptions
- RULE-8: Build skill documents proof fixer mode with instructions to fix proofs based on audit feedback and report back
- RULE-9: Build skill produces a changeset summary after tests pass, with three sections: Changeset (rule→file:line mapping), Decisions (judgment calls), and Review (focus areas)
- RULE-10: The changeset summary is included as the commit message body in the build commit
- RULE-11: When running as proof fixer, the changeset summary maps fixed proofs instead of rules and omits the Decisions section
- RULE-12: Build skill has exit criteria requiring tests pass, changeset summary printed, all changes committed, and no uncommitted proof files before the skill can complete
- RULE-13: The assertion-change guard forbids resolving a description/assertion disagreement by narrowing the proof description, explains that doing so lowers Proof Design while leaving Proof Integrity flatteringly high, and forbids it outright for anchor rules
- RULE-14: The build skill names `purlin:test` as the single owner of test execution and forbids invoking a test runner directly, because `purlin:build` and `purlin:verify` inherit tier classification, remote execution and the `sync_status` call by delegating rather than by each reimplementing them. No retired skill name appears: the skill was renamed from `purlin:unit-test`, and this skill's iteration loop kept pointing at the old name through a release, directing the agent at a skill that does not exist
- RULE-15: The test-writing step branches on `mutation_checks` in `.purlin/config.json`. When it is `true` the skill requires the mutation check before the commit that carries the proof (break the behaviour, run that proof, watch it fail, restore) and records each mutation in the commit body, so the check is re-runnable from git history. When it is `false` the skill prints one visible line saying the check is off and how to turn it on, because an omitted check that is also silent reads as a check that passed

## Proof

- PROOF-1 (RULE-1): Grep `skills/build/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/build/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `build`
- PROOF-4 (RULE-4): Grep `skills/build/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/build/SKILL.md` for `sync_status` and `not optional`; verify both present
- PROOF-6 (RULE-6): Grep `skills/build/SKILL.md` for `diagnose` and `Never weaken`; verify both present
- PROOF-7 (RULE-7): Grep `skills/build/SKILL.md` for tier review instructions and tier tag references (`@integration`/`@e2e`/unit tier); verify present
- PROOF-8 (RULE-8): e2e: Grep skills/build/SKILL.md for proof fixer mode; verify fix proofs and report instructions @e2e
- PROOF-9 (RULE-9): Grep `skills/build/SKILL.md` for "Changeset Summary", "Changeset", "Decisions", "Review" section headers; verify all three summary sections are documented with format examples
- PROOF-10 (RULE-10): Grep `skills/build/SKILL.md` for commit message body instructions that reference the changeset summary and commit_conventions.md; verify present
- PROOF-11 (RULE-11): Grep `skills/build/SKILL.md` for proof fixer changeset instructions in the "When Running as Proof Fixer" section; verify it documents mapping fixed proofs and skipping Decisions
- PROOF-12 (RULE-12): Grep `skills/build/SKILL.md` for "Exit Criteria" section; verify it requires tests pass, changeset summary, committed changes, and no uncommitted proof files
- PROOF-13 (RULE-9): Create a temp project with spec+code+tests, run pytest to emit proofs, build a changeset summary, validate it has all 3 sections with RULE→file:line mappings @e2e
- PROOF-14 (RULE-10): In the temp project, commit with changeset summary as body; verify commit subject uses feat(<name>): prefix and body contains all 3 changeset sections @e2e
- PROOF-15 (RULE-11): Build a proof-fixer-style changeset; verify it maps PROOF-N instead of RULE-N and has no Decisions section @e2e
- PROOF-16 (RULE-12): After the build session in the temp project, verify exit criteria: all tests pass, changeset summary valid, all proofs committed, git status clean @e2e
- PROOF-17 (RULE-9): Run purlin:build via claude -p with a spec containing ambiguous rules; verify agent output contains Changeset with RULE mappings, non-empty Decisions with real judgment calls, and non-empty Review with risk areas @e2e
- PROOF-18 (RULE-10): After the agent build session, verify git log shows a feat(<name>): commit whose body contains RULE references and the changeset summary sections @e2e
- PROOF-19 (RULE-12): After the agent build session, verify git status has no uncommitted proof files or source files, and proof files are tracked in git @e2e
- PROOF-20 (RULE-13): Grep `skills/build/SKILL.md` for the assertion-change guard; verify it forbids narrowing the proof description, names both gauges, and forbids narrowing anchor-rule descriptions
- PROOF-21 (RULE-14): Grep `skills/build/SKILL.md` for `purlin:test` and verify it is named as the single owner of test execution with a prohibition on invoking a runner directly. Verify the retired name `purlin:unit-test` appears nowhere in the file, and that no bare runner invocation (`pytest`, `npx jest`, `npx vitest`) appears as an instruction outside the prohibition itself
- PROOF-22 (RULE-15): Grep `skills/build/SKILL.md` and verify both branches are present and distinguishable: the `true` branch names `references/spec_quality_guide.md#mutation-check`, requires the check before the commit, and says the mutation is recorded in the commit body; the `false` branch carries the literal line the skill prints, naming `purlin:init --mutation-checks on`. Verify the commit step also names the mutation lines, so the two halves cannot drift apart. Deleting either branch fails the proof
