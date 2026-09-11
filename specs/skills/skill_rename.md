# Feature: skill_rename

> Scope: skills/rename/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:rename` skill renames a feature across all Purlin artifacts — specs, proofs, markers, and references — in one atomic operation.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `rename`, matching the directory name
- RULE-4: The documented rename surface covers the quality caches: the skill instructs rewriting the `feature` field of every entry in `.purlin/cache/audit_cache.json` and `.purlin/cache/design_cache.json`, because those caches key on feature name and a rename that skips them orphans every cached assessment, dropping the feature to `unmeasured` on both gauges. It also states that `cached_at` must not be re-stamped, since the assessments are unchanged and re-stamping would defeat the staleness check

## Proof

- PROOF-1 (RULE-1): Grep `skills/rename/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/rename/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `rename`
- PROOF-4 (RULE-4): Grep `skills/rename/SKILL.md` for both `audit_cache.json` and `design_cache.json`; verify each appears in the numbered what-it-renames list and in the execute steps, that the text names the `feature` field as what gets rewritten, and that it forbids re-stamping `cached_at`
