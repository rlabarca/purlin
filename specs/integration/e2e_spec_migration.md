# Feature: e2e_spec_migration

> Description: End-to-end validation that purlin:spec-from-code migrates specs from any format to the current compliant format with minimal loss of fidelity.
> Scope: skills/spec-from-code/SKILL.md, scripts/mcp/purlin_server.py
> Requires: schema_spec_format

## Rules

- RULE-1: Legacy Given/When/Then specs from features/ are converted to RULE-N/PROOF-N format with all scenarios preserved as rules
- RULE-2: Specs with unnumbered rules (plain `- Some rule` lines) are renumbered to sequential RULE-N format
- RULE-3: Specs missing `> Description:` metadata get a Description field added from the `## What it does` section or rule content
- RULE-4: Specs missing `## Proof` section get proof descriptions generated that reference each rule
- RULE-5: Migrated specs pass sync_status validation with zero warnings (numbered rules, proof references, sections present)
- RULE-6: Compliant specs (already numbered, with proofs and description) are left byte-identical after migration
- RULE-7: Existing metadata fields (Scope, Stack, Requires) are preserved verbatim during migration
- RULE-8: Migration from features/ preserves the original feature name and category structure
- RULE-9: An LLM evaluating the migrated output rates fidelity as HIGH (original intent preserved, no rules lost, no meaning changed)

## Proof

- PROOF-1 (RULE-1): Create a temp project with a features/auth/login.md containing Given/When/Then scenarios; run spec-from-code migration logic; verify output has RULE-N lines matching each scenario @e2e
- PROOF-2 (RULE-2): Create a spec with unnumbered rules; run migration; verify output has sequential RULE-1, RULE-2, RULE-3 @e2e
- PROOF-3 (RULE-3): Create a spec missing > Description:; run migration; verify output has > Description: with meaningful content @e2e
- PROOF-4 (RULE-4): Create a spec with Rules but no Proof section; run migration; verify output has PROOF-N (RULE-N) for each rule @e2e
- PROOF-5 (RULE-5): Run sync_status on all migrated specs; verify zero warnings for each @e2e
- PROOF-6 (RULE-6): Create a fully compliant spec; run migration; verify file is byte-identical before and after @e2e
- PROOF-7 (RULE-7): Create a spec with Scope, Stack, Requires metadata; run migration; verify all three fields preserved verbatim @e2e
- PROOF-8 (RULE-8): Create features/payments/checkout.md; run migration; verify output is specs/payments/checkout.md with matching name @e2e
- PROOF-9 (RULE-9): For each migration scenario, send the original and migrated spec to an LLM evaluator; verify it rates fidelity as HIGH (no lost rules, preserved intent) @e2e
