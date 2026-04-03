# Feature: e2e_cross_model_audit

> Scope: skills/audit/SKILL.md, references/audit_criteria.md
> Stack: shell/bash, gemini CLI (external LLM)

## What it does

End-to-end test of cross-model auditing with a real external LLM (Gemini). Verifies that an external LLM can detect hollow tests, approve strong tests, and that the structured response can be parsed into PROOF-ID, ASSESSMENT, CRITERION, WHY, and FIX fields.

## Rules

- RULE-1: External LLM detects deliberately hollow tests (assert True, assert None) as non-STRONG
- RULE-2: External LLM rates well-structured tests with real assertions as STRONG or WEAK (never HOLLOW)
- RULE-3: Response parsing extracts all required fields (PROOF-ID, ASSESSMENT, CRITERION, WHY, FIX) from the external LLM output
- RULE-4: Two-pass flow works end-to-end: static_checks catches HOLLOW in Pass 1, only surviving proofs go to external LLM in Pass 2
- RULE-5: Custom audit LLM configured via init flow responds to ping, gets saved to config, and completes a two-pass audit

## Proof

- PROOF-1 (RULE-1): Audit hollow test code (assert True, assert result is None) with Gemini; verify it returns HOLLOW or WEAK for both proofs @e2e
- PROOF-2 (RULE-2): Audit strong test code (real HTTP assertions, JWT decode, negative test) with Gemini; verify PROOF-1 returns STRONG, PROOF-2 returns STRONG or WEAK (not HOLLOW) @e2e
- PROOF-3 (RULE-3): Parse the Gemini response from the strong-test audit; verify ASSESSMENT, CRITERION, WHY, FIX fields are all extracted for every PROOF-ID @e2e
- PROOF-4 (RULE-4): Mixed-quality test file — static_checks catches assert True as HOLLOW, passes valid test to Gemini, Gemini rates STRONG or WEAK @e2e
- PROOF-5 (RULE-5): Configure fake LLM wrapper via config; verify init ping returns PURLIN_AUDIT_OK; verify config stores audit_llm and audit_llm_name; run two-pass audit through the configured command; verify structured response parsed @e2e
