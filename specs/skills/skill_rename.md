# Feature: skill_rename

> Scope: skills/rename/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:rename` skill renames a feature across all Purlin artifacts — specs, proofs, markers, and references — in one atomic operation.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `rename`, matching the directory name
- RULE-4: The documented rename surface covers the quality caches: the skill instructs rewriting the `feature` field of every entry in `.purlin/cache/audit_cache.json` and `.purlin/cache/design_cache.json`, because those caches key on feature name and a rename that skips them orphans every cached assessment, dropping the feature to `unmeasured` on both gauges. It also states that `cached_at` must not be re-stamped, since the assessments are unchanged and re-stamping would defeat the staleness check

- RULE-5: The skill states no proof marker syntax of its own. For the marker rewrite it cites `references/formats/proofs_format.md#feature-name-token` and says that the section covers every shipped framework and that the rename must rewrite all of them. That section's token table is the rename's coverage contract: its framework set equals the `###` marker subsections of the same section and equals the framework ids of the per-framework table in `references/proof_plugin_contract.md` section B, and every token literal it lists occurs, with a feature name in it, in that framework's own plugin under `scripts/proof/`. A marker table copied into the skill goes stale against the plugins, which is how the skill came to list three frameworks of eight and leave Vitest, xUnit, C, PHP and SQL markers pointing at the old name after a rename

## Proof

- PROOF-1 (RULE-1): Grep `skills/rename/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/rename/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `rename`
- PROOF-4 (RULE-4): Grep `skills/rename/SKILL.md` for both `audit_cache.json` and `design_cache.json`; verify each appears in the numbered what-it-renames list and in the execute steps, that the text names the `feature` field as what gets rewritten, and that it forbids re-stamping `cached_at`
- PROOF-5 (RULE-5): Parse the `### Feature-name token` table of `references/formats/proofs_format.md` and the section B per-framework table of `references/proof_plugin_contract.md` with the parsers those two files' own proofs use; verify the framework id sets are equal, and that the table's marker-section cells equal the `###` headings of `## Proof Markers by Framework` other than the token section itself. For every row, substitute each known sample feature name into each token literal and verify one of them occurs in a plugin file the contract names for that framework. Then verify `skills/rename/SKILL.md` matches none of those literals with any name in the feature position, contains `proofs_format.md#feature-name-token`, and says both that the section covers every shipped framework and that the rename rewrites all of them. Dropping the vitest row fails the id equality naming vitest; dropping the anchor from the skill fails naming the skill
