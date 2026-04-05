# Feature: skill_drift

> Scope: skills/drift/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:drift` skill detects spec drift by calling the `drift` MCP tool and summarizing changes since last verification, cross-referenced with specs. It produces PM/QA/eng-readable reports.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `drift`, matching the directory name
- RULE-4: Skill references the `drift` MCP tool by name
- RULE-5: Skill requires reading git diffs for behavioral changes, not just interpreting MCP categories

## Proof

- PROOF-1 (RULE-1): Grep `skills/drift/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/drift/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `drift`
- PROOF-4 (RULE-4): Grep `skills/drift/SKILL.md` for `drift`; verify the MCP tool is referenced
- PROOF-5 (RULE-5): Grep `skills/drift/SKILL.md` for `git diff`; verify the diff-reading requirement is present
