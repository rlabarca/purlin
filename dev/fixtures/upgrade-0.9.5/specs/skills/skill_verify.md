# Feature: skill_verify

> Scope: skills/verify/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:verify` skill runs the full test suite across all tiers, then issues verification receipts for every feature with complete rule coverage.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `verify`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Skill prohibits modifying code or test files during verification
- RULE-6: Verify skill Step 4e documents independent audit that reports the final integrity score

## Proof

- PROOF-1 (RULE-1): Grep `skills/verify/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/verify/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `verify`
- PROOF-4 (RULE-4): Grep `skills/verify/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/verify/SKILL.md` for `NEVER modify`; verify the read-only constraint is present
- PROOF-6 (RULE-6): e2e: Grep skills/verify/SKILL.md for independent audit; verify integrity score and purlin-auditor reference @e2e
