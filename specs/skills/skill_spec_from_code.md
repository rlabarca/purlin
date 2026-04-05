# Feature: skill_spec_from_code

> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:spec-from-code` skill scans codebases and migrates existing specs in any format to the current compliant 3-section format.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `spec-from-code`, matching the directory name
- RULE-4: Skill includes mandatory tier tag review for proof descriptions
- RULE-5: Phase 1 detects existing specs in both `features/` (legacy) and `specs/` (non-compliant) as migration candidates
- RULE-6: Non-compliant specs in `specs/` are detected by checking for: missing `## Rules` section, unnumbered rules, missing `## Proof` section, or missing `> Description:` metadata
- RULE-7: Compliant specs (numbered rules, proofs, proper sections) are left untouched during migration
- RULE-8: Migration preserves the original spec's rules, descriptions, and metadata with minimal loss of fidelity
- RULE-9: Phase 4 offers to remove `features/` after migration but does NOT remove non-compliant specs from `specs/` (they are overwritten in place)

## Proof

- PROOF-1 (RULE-1): Grep `skills/spec-from-code/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/spec-from-code/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `spec-from-code`
- PROOF-4 (RULE-4): Grep `skills/spec-from-code/SKILL.md` for tier review instructions and tier tag references (`@integration`/`@e2e`/unit tier); verify present
- PROOF-5 (RULE-5): Grep SKILL.md for `features/` detection AND `specs/` non-compliant detection in Phase 1; verify both paths exist
- PROOF-6 (RULE-6): Grep SKILL.md for compliance checks: "Missing `## Rules`", "unnumbered", "Missing `## Proof`", "Missing `> Description:`"; verify all four criteria are documented
- PROOF-7 (RULE-7): Grep SKILL.md for "Compliant specs" or "left untouched"; verify compliant specs are explicitly excluded from migration
- PROOF-8 (RULE-8): Grep SKILL.md for "primary input" and "preserve"; verify migration uses old spec as primary input @integration
- PROOF-9 (RULE-9): Grep SKILL.md for `features/` cleanup offer AND "overwritten in place" for specs/; verify both paths exist
