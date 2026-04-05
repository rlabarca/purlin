# Feature: skill_find

> Scope: skills/find/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:find` skill searches specs by name and displays rule coverage from `sync_status`.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `find`, matching the directory name
- RULE-4: Skill references the `sync_status` MCP tool by name

## Proof

- PROOF-1 (RULE-1): Grep `skills/find/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/find/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `find`
- PROOF-4 (RULE-4): Grep `skills/find/SKILL.md` for `sync_status`; verify the MCP tool is referenced
