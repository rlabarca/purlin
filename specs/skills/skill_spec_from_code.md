# Feature: skill_spec_from_code

> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown (skill definition)

## What it does

The `purlin:spec-from-code` skill reverse-engineers 3-section specs from existing code. It uses parallel exploration, interactive taxonomy review, and dependency-ordered generation.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `spec-from-code`, matching the directory name
- RULE-4: Skill includes mandatory tier tag review for proof descriptions

## Proof

- PROOF-1 (RULE-1): Grep `skills/spec-from-code/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/spec-from-code/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `spec-from-code`
- PROOF-4 (RULE-4): Grep `skills/spec-from-code/SKILL.md` for tier review instructions and tier tag references (`@integration`/`@e2e`/unit tier); verify present
