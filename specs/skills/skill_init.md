# Feature: skill_init

> Scope: skills/init/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:init` skill initializes a project for spec-driven development. It creates `.purlin/`, `specs/`, detects the test framework, scaffolds the proof plugin, and manages plugin configuration.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `init`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: `--add-plugin` validates plugin files against language-specific patterns (Python: `proofs`+`json`, JS: `proofs`+`JSON`, Shell: `purlin_proof`, Java: `proofs`+`Proof`) and warns if validation fails
- RULE-6: `--add-plugin` supports both local file paths and git URL sources with distinct handling for each
- RULE-7: `--list-plugins` identifies built-in plugins (`pytest_purlin`, `jest_purlin`, `purlin-proof`) by framework name and labels all others as `custom`

## Proof

- PROOF-1 (RULE-1): Grep `skills/init/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/init/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `init`
- PROOF-4 (RULE-4): Grep `skills/init/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/init/SKILL.md` for language validation entries (`Python`, `JavaScript`, `Shell`, `Java`) and warning text `doesn't look like a standard proof plugin`; verify all present
- PROOF-6 (RULE-6): Grep `skills/init/SKILL.md` for `local file path` and `git URL`; verify both source types are documented with distinct handling steps
- PROOF-7 (RULE-7): Grep `skills/init/SKILL.md` for `pytest_purlin.py` with `Python/pytest`, `jest_purlin.js` with `JavaScript/Jest`, and the label `custom`; verify the labeling table exists
