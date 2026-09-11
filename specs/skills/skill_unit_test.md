# Feature: skill_unit_test

> Scope: skills/unit-test/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:unit-test` skill runs tests (unit tier unless `--all`), emits proof files via feature-scoped overwrite, and reports coverage per feature.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `unit-test`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Skill requires calling `sync_status` after tests and states it is not optional
- RULE-6: The freshness check distinguishes "no tests were collected" from "the proof plugin failed to emit". Zero collected tests reports that the plugin is fine and routes to `purlin:build`; only a run that executed tests without refreshing proof files reports a plugin problem and suggests `purlin:init --force`

## Proof

- PROOF-1 (RULE-1): Grep `skills/unit-test/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/unit-test/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `unit-test`
- PROOF-4 (RULE-4): Grep `skills/unit-test/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/unit-test/SKILL.md` for `sync_status` and `not optional`; verify both present
- PROOF-6 (RULE-6): Grep `skills/unit-test/SKILL.md` for the freshness check; verify the zero-tests branch states the plugin is fine and routes to `purlin:build`, and that the `purlin:init --force` suggestion appears only in the branch where tests actually ran
