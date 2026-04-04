# Feature: skill_anchor

> Scope: skills/anchor/SKILL.md
> Stack: markdown (skill definition)

## What it does

The `purlin:anchor` skill creates, syncs, and manages anchor specs — cross-cutting constraints with optional external references. Anchors define shared rules that other features reference via `> Requires:`.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `anchor`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications

## Proof

- PROOF-1 (RULE-1): Grep `skills/anchor/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/anchor/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `anchor`
- PROOF-4 (RULE-4): Grep `skills/anchor/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
