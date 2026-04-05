# Feature: skill_rename

> Scope: skills/rename/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:rename` skill renames a feature across all Purlin artifacts — specs, proofs, markers, and references — in one atomic operation.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `rename`, matching the directory name

## Proof

- PROOF-1 (RULE-1): Grep `skills/rename/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/rename/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `rename`
