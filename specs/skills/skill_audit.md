# Feature: skill_audit

> Scope: skills/audit/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:audit` skill evaluates proof quality with STRONG/WEAK/HOLLOW assessments. It is read-only — it never modifies code or test files.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `audit`, matching the directory name
- RULE-4: Independent auditor mode documents instructions to read audit criteria and assess proofs as STRONG/WEAK/HOLLOW
- RULE-5: Independent auditor mode documents spawning a builder with HOLLOW/WEAK findings
- RULE-6: Independent auditor mode documents re-auditing fixed proofs after builder responds
- RULE-7: Independent auditor mode terminates after all findings addressed or after 3 rounds on any single proof
- RULE-8: Anchor rule handling documents reporting to the lead for ambiguous anchor rules
- RULE-9: External LLM detects deliberately hollow tests (assert True, assert None) as non-STRONG
- RULE-10: External LLM rates well-structured tests with real assertions as STRONG or WEAK (never HOLLOW)
- RULE-11: Response parsing extracts all required fields (PROOF-ID, ASSESSMENT, CRITERION, WHY, FIX) from external LLM output
- RULE-12: Two-pass flow works end-to-end: static_checks catches HOLLOW in Pass 1, only surviving proofs go to external LLM in Pass 2
- RULE-13: Custom audit LLM command in config responds to ping, config stores audit_llm and audit_llm_name, and the two-pass audit completes
- RULE-14: Criteria are loaded via the single `load_criteria()` function (`--load-criteria` CLI); built-in criteria always apply, additional team criteria are appended — never replaced

## Proof

- PROOF-1 (RULE-1): Grep `skills/audit/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/audit/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `audit`
- PROOF-4 (RULE-4): e2e: Grep skills/audit/SKILL.md for independent auditor section; verify audit_criteria.md and STRONG/WEAK/HOLLOW @e2e
- PROOF-5 (RULE-5): e2e: Grep independent auditor section for purlin-builder and Spawn; verify builder protocol @e2e
- PROOF-6 (RULE-6): e2e: Grep independent auditor section for re-audit; verify re-check loop @e2e
- PROOF-7 (RULE-7): e2e: Grep independent auditor section for 3 rounds; verify termination condition @e2e
- PROOF-8 (RULE-8): e2e: Grep anchor rule handling for report to lead; verify ambiguous anchor protocol @e2e
- PROOF-9 (RULE-9): e2e: Audit hollow test code with external LLM; verify returns HOLLOW or WEAK @e2e
- PROOF-10 (RULE-10): e2e: Audit strong test code with external LLM; verify STRONG or WEAK (not HOLLOW) @e2e
- PROOF-11 (RULE-11): e2e: Parse external LLM response; verify ASSESSMENT, CRITERION, WHY, FIX fields extracted @e2e
- PROOF-12 (RULE-12): e2e: Mixed-quality test file; static_checks catches assert True; valid test goes to external LLM @e2e
- PROOF-13 (RULE-13): e2e: Write config with fake LLM command; verify ping, config fields, and two-pass audit @e2e
- PROOF-14 (RULE-14): e2e: Create fake git repo with additional criteria; configure project; verify load_criteria returns built-in + additional with separator; verify Pass 1 still catches assert True; verify additional criteria reach fake LLM prompt @e2e
