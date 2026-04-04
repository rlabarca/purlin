# Feature: skill_audit

> Scope: skills/audit/SKILL.md
> Stack: markdown (skill definition)

## What it does

The `purlin:audit` skill evaluates proof quality with STRONG/WEAK/HOLLOW assessments. It is read-only — it never modifies code or test files.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `audit`, matching the directory name

## Proof

- PROOF-1 (RULE-1): Grep `skills/audit/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/audit/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `audit`
