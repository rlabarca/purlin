# Feature: e2e_teammate_audit_loop

> Scope: skills/audit/SKILL.md, skills/build/SKILL.md, skills/verify/SKILL.md, .claude/agents/purlin-auditor.md, .claude/agents/purlin-builder.md
> Stack: markdown (skill definitions, agent definitions)
> Description: Defines the automatic verify-audit-build loop. The verify skill spawns a purlin-auditor that assesses proof quality, coordinates with a purlin-builder for HOLLOW/WEAK findings, and loops until proofs are fixed. This spec covers the auditor/builder communication protocol and termination conditions.

## Rules

- RULE-1: Audit skill documents independent auditor mode with instructions to read audit criteria and assess proofs as STRONG/WEAK/HOLLOW
- RULE-2: Audit skill independent auditor mode instructs spawning a builder with HOLLOW/WEAK findings
- RULE-3: Build skill documents proof fixer mode with instructions to fix proofs based on audit feedback and report back
- RULE-4: Audit skill independent auditor mode instructs re-auditing fixed proofs after builder responds
- RULE-5: Audit skill independent auditor mode terminates after all findings are addressed or after 3 rounds on any single proof
- RULE-6: Verify skill Step 4e documents independent audit that reports the final integrity score
- RULE-7: Audit skill anchor rule handling instructs reporting to the lead (not the builder) for ambiguous anchor rules

## Proof

- PROOF-1 (RULE-1): Grep `skills/audit/SKILL.md` for `## When Running as Independent Auditor`; verify it contains `audit_criteria.md` and `STRONG/WEAK/HOLLOW` @e2e
- PROOF-2 (RULE-2): Grep `skills/audit/SKILL.md` independent auditor section for `purlin-builder` and `Spawn`; verify the builder spawning protocol is documented @e2e
- PROOF-3 (RULE-3): Grep `skills/build/SKILL.md` for `## When Running as Proof Fixer`; verify it contains instructions to fix proofs and report back @e2e
- PROOF-4 (RULE-4): Grep `skills/audit/SKILL.md` independent auditor section for `re-audit`; verify the re-check loop is documented @e2e
- PROOF-5 (RULE-5): Grep `skills/audit/SKILL.md` independent auditor section for `3 rounds`; verify the termination condition is documented @e2e
- PROOF-6 (RULE-6): Grep `skills/verify/SKILL.md` for independent audit; verify it contains `integrity score` and references the `purlin-auditor` @e2e
- PROOF-7 (RULE-7): Grep `skills/audit/SKILL.md` for anchor rule handling; verify it says to report to the lead for ambiguous anchor rules @e2e
