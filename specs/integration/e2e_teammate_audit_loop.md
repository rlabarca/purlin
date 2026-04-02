# Feature: e2e_teammate_audit_loop

> Scope: skills/audit/SKILL.md, skills/build/SKILL.md, skills/verify/SKILL.md, .claude/agents/purlin-auditor.md, .claude/agents/purlin-builder.md
> Stack: markdown (skill definitions, agent teammate definitions)

## What it does

Defines the teammate-aware verify-audit-build loop. When agent teams are available, the verify skill spawns a purlin-auditor teammate that assesses proof quality, messages the purlin-builder teammate with HOLLOW/WEAK findings, and loops until proofs are fixed. This spec covers the teammate communication protocol and termination conditions.

## Rules

- RULE-1: Audit skill documents teammate mode with instructions to read audit criteria and assess proofs as STRONG/WEAK/HOLLOW
- RULE-2: Audit skill teammate mode instructs messaging the builder directly with HOLLOW/WEAK findings
- RULE-3: Build skill documents teammate mode with instructions to fix proofs based on audit feedback and message the auditor back
- RULE-4: Audit skill teammate mode instructs re-checking fixed proofs after builder responds
- RULE-5: Audit skill teammate mode terminates after all findings are addressed or after 3 rounds on any single proof
- RULE-6: Verify skill Step 4e documents teammate mode that sends the final integrity score to the lead
- RULE-7: Audit skill teammate mode instructs messaging the lead (not the builder) for ambiguous invariant rules

## Proof

- PROOF-1 (RULE-1): Grep `skills/audit/SKILL.md` for `## Teammate Mode`; verify it contains `audit_criteria.md` and `STRONG/WEAK/HOLLOW` @e2e
- PROOF-2 (RULE-2): Grep `skills/audit/SKILL.md` teammate mode section for `purlin-builder` and `message`; verify the builder messaging protocol is documented @e2e
- PROOF-3 (RULE-3): Grep `skills/build/SKILL.md` for `## Teammate Mode`; verify it contains `purlin-auditor` and instructions to fix proofs and message back @e2e
- PROOF-4 (RULE-4): Grep `skills/audit/SKILL.md` teammate mode for `Re-read` and `re-assess`; verify the re-check loop is documented @e2e
- PROOF-5 (RULE-5): Grep `skills/audit/SKILL.md` teammate mode for `3 rounds`; verify the termination condition is documented @e2e
- PROOF-6 (RULE-6): Grep `skills/verify/SKILL.md` for teammate mode; verify it contains `integrity score` and references the `purlin-auditor` agent type @e2e
- PROOF-7 (RULE-7): Grep `skills/audit/SKILL.md` for invariant rule handling in teammate mode; verify it says to message the lead for ambiguous invariant rules @e2e
