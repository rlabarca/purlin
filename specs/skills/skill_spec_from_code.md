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
- RULE-10: A spec generated from a plain description contains sequentially numbered RULE-N lines starting at RULE-1 with no gaps
- RULE-11: A spec generated from a plain description contains PROOF-N (RULE-N) lines where every rule has at least one proof
- RULE-12: A spec generated from a plain description contains no (assumed) tags when all values were explicitly stated
- RULE-13: A spec generated from a PRD extracts every testable constraint as a RULE-N line — at least 5 rules for a multi-requirement PRD
- RULE-14: A spec generated from a PRD contains valid metadata: `> Description:`, `> Scope:`, and `> Stack:` fields are present
- RULE-15: A spec generated from a PRD includes `> Requires:` referencing anchors whose scope overlaps with the feature's scope
- RULE-16: A spec generated from a vague description adds `(assumed — <context>)` tags to rules where the agent inferred specific values
- RULE-17: Rules with (assumed) tags still follow RULE-N format and are parseable by sync_status
- RULE-18: A spec generated from customer feedback translates complaints into testable RULE-N constraints with specific thresholds or behaviors
- RULE-19: Every proof line across all four scenarios ends with an appropriate tier tag (@integration, @e2e, @manual, or no tag for unit)
- RULE-20: sync_status successfully parses specs from all four scenarios without errors, reporting correct rule counts and UNTESTED status
- RULE-21: The `## Rules` and `## Proof` sections are both present in specs from all four scenarios
- RULE-22: When a vague-input spec's (assumed) rule is updated with an explicit value, the (assumed) tag is removed and the rule remains valid

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
- PROOF-10 (RULE-5): e2e: Create features/auth/login.md with Given/When/Then; verify 3 scenarios detected for conversion @e2e
- PROOF-11 (RULE-6): e2e: Create spec with unnumbered rules; verify sync_status warns about non-numbered rules @e2e
- PROOF-12 (RULE-6): e2e: Create spec missing > Description:; verify field absent and ## What it does present for derivation @e2e
- PROOF-13 (RULE-6): e2e: Create spec with Rules but no Proof section; verify Proof section absent @e2e
- PROOF-14 (RULE-7): e2e: Create fully compliant spec; verify sync_status reports zero warnings @e2e
- PROOF-15 (RULE-7): e2e: Verify compliant spec has Description, numbered rules, and proofs (excluded from migration) @e2e
- PROOF-16 (RULE-8): e2e: Create spec with Scope, Stack metadata but missing Description; verify Scope and Stack preserved verbatim @e2e
- PROOF-17 (RULE-5): e2e: Create features/auth/login.md; verify category=auth name=login maps to specs/auth/login.md @e2e
- PROOF-18 (RULE-8): e2e: Migrate unnumbered spec; verify all original rule content preserved in numbered format with proofs @e2e
- PROOF-19 (RULE-10): e2e: Create spec with 4 sequentially numbered rules; verify numbers are 1,2,3,4 with no gaps @e2e
- PROOF-20 (RULE-11): e2e: Verify every RULE-N has at least one PROOF referencing it @e2e
- PROOF-21 (RULE-12): e2e: Verify plain-description spec with explicit values has no (assumed) tags @e2e
- PROOF-22 (RULE-13): e2e: Create PRD spec with 6 constraints; verify at least 5 RULE-N lines @e2e
- PROOF-23 (RULE-14): e2e: Verify PRD spec has Description, Scope, and Stack metadata @e2e
- PROOF-24 (RULE-15): e2e: Create project with overlapping anchor; verify Requires references it and sync_status shows required rules @e2e
- PROOF-25 (RULE-16): e2e: Create vague-input spec; verify (assumed) tags present @e2e
- PROOF-26 (RULE-17): e2e: Run sync_status on vague-input spec; verify parses without errors with correct rule count @e2e
- PROOF-27 (RULE-18): e2e: Create customer feedback spec; verify rules have specific thresholds @e2e
- PROOF-28 (RULE-19): e2e: Parse proof lines across all four scenarios; verify tier tags present @e2e
- PROOF-29 (RULE-20): e2e: Run sync_status on all four scenarios; verify UNTESTED status and correct rule counts @e2e
- PROOF-30 (RULE-21): e2e: Verify ## Rules and ## Proof sections exist in all four scenario specs @e2e
- PROOF-31 (RULE-22): e2e: Update (assumed) rule with explicit value; verify tag removed and RULE-N format valid @e2e
