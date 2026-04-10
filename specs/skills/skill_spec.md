# Feature: skill_spec

> Scope: skills/spec/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:spec` skill scaffolds or edits feature specs in 3-section format. It accepts any input — plain English, PRDs, customer feedback, code files, images — and extracts structured rules.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `spec`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Update workflow (Step 7) presents a delta report showing KEEPING/ADDING/UPDATING/REMOVING before applying changes
- RULE-6: Skill includes mandatory tier tag review for proof descriptions
- RULE-7: Spec skill has exit criteria requiring the spec file is committed and no uncommitted spec files remain before the skill can complete

## Proof

- PROOF-1 (RULE-1): Grep `skills/spec/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/spec/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `spec`
- PROOF-4 (RULE-4): Grep `skills/spec/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/spec/SKILL.md` for `KEEPING`, `ADDING`, `UPDATING`, and `REMOVING`; verify the delta report structure is present
- PROOF-6 (RULE-6): Grep `skills/spec/SKILL.md` for tier review instructions and tier tag references (`@integration`/`@e2e`/unit tier); verify present
- PROOF-7 (RULE-7): Grep `skills/spec/SKILL.md` for "Exit Criteria" section; verify it requires spec committed and no uncommitted spec files
