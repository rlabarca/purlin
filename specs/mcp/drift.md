# Feature: drift

> Requires: schema_spec_format, security_no_dangerous_patterns
> Scope: scripts/mcp/purlin_server.py, references/drift_criteria.md
> Stack: python/stdlib, json, subprocess (list-only), hashlib

## What it does

Structured change summary tool for the purlin:drift skill. Resolves a "since" anchor, classifies changed files, detects spec drift, and returns machine-readable JSON for the drift skill to interpret and format.

## Rules

- RULE-1: Resolves the "since" anchor from: explicit argument (integer or date), most recent `verify:` commit, most recent tag, or smart fallback based on commits since Purlin initialization
- RULE-2: Classifies changed files into categories: CHANGED_SPECS, TESTS_ADDED, CHANGED_BEHAVIOR, NO_IMPACT, NEW_BEHAVIOR
- RULE-3: Returns JSON with `since`, `commits`, `files`, `spec_changes`, and `proof_status` fields
- RULE-4: proof_status entries include a `structural_checks` count of structural proofs, and `proved`/`total` fields only count behavioral proofs
- RULE-5: proof_status totals include required and global anchor rules, not just own rules
- RULE-6: Classifies files in `skills/`, `agents/`, and `.claude/agents/` as NEW_BEHAVIOR when not in scope — never NO_IMPACT
- RULE-7: Scope matching supports directory prefix: `> Scope: src/api/` matches `src/api/login.js`
- RULE-8: File entries include `behavioral_gap: true` when the file's spec has zero proved rules (total > 0 but proved == 0) and category is CHANGED_BEHAVIOR
- RULE-9: Returns a `drift_flags` array summarizing features with zero proved rules (coverage gap) that have changed files
- RULE-10: Detects broken scope paths — files referenced in `> Scope:` that no longer exist on disk — and returns them in a `broken_scopes` array
- RULE-11: Returns a spec-from-code recommendation when no verification anchor exists and >= 30 commits have been made since Purlin initialization

## Proof

- PROOF-1 (RULE-1): Call with explicit since="5"; verify HEAD~5. Call with verify commit in log; verify that SHA @integration
- PROOF-2 (RULE-2): Create changed spec, test file, and README; verify CHANGED_SPECS, TESTS_ADDED, NO_IMPACT classifications @integration
- PROOF-3 (RULE-3): Call drift; verify all 5 top-level JSON keys present @integration
- PROOF-4 (RULE-4): Create spec with grep-based proof passing; verify proved=1 and total=1 in proof_status @integration
- PROOF-5 (RULE-5): Create feature requiring anchor with 2 rules; verify proof_status total includes anchor rules @integration
- PROOF-6 (RULE-6): Create changed file at skills/new/SKILL.md with no scope; verify classified as NEW_BEHAVIOR @integration
- PROOF-7 (RULE-7): Create spec with `> Scope: src/api/` and changed file src/api/login.js; verify CHANGED_BEHAVIOR @integration
- PROOF-8 (RULE-8): Create spec with zero proofs and changed scope file; verify behavioral_gap: true @integration
- PROOF-9 (RULE-9): Same setup; verify drift_flags array entry with reason behavioral_gap_with_code_change @integration
- PROOF-10 (RULE-10): Create spec with non-existent scope path; verify broken_scopes entry @integration
- PROOF-11 (RULE-11): Create a temp repo with 50+ commits, no verify or tags; call drift; verify spec-from-code recommendation. Create repo with <30 commits; verify normal drift @integration
