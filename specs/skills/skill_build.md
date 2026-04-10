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
