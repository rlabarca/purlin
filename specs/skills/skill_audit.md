# Feature: skill_audit

> Scope: skills/audit/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:audit` skill evaluates proof quality with STRONG/WEAK/HOLLOW assessments. It is read-only — it never modifies code or test files.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `audit`, matching the directory name
- RULE-4: Independent auditor mode documents instructions to read audit criteria and assess proofs as STRONG/WEAK/HOLLOW
- RULE-5: Independent auditor mode documents routing HOLLOW/WEAK findings to `purlin:build` for remediation, and states that no fixer agent is spawned because the audit is read-only
- RULE-6: Independent auditor mode documents re-auditing the affected proofs after the fixes land
- RULE-7: Independent auditor mode terminates after all findings addressed or after 3 rounds on any single proof
- RULE-8: Anchor rule handling documents reporting to the lead for ambiguous anchor rules
- RULE-9: External LLM detects deliberately hollow tests (assert True, assert None) as non-STRONG
- RULE-10: External LLM rates well-structured tests with real assertions as STRONG or WEAK (never HOLLOW)
- RULE-11: Response parsing extracts all required fields (PROOF-ID, ASSESSMENT, CRITERION, WHY, FIX) from external LLM output
- RULE-12: Two-pass flow works end-to-end: static_checks catches HOLLOW in Pass 1, only surviving proofs go to external LLM in Pass 2
- RULE-13: Custom audit LLM command in config responds to ping, config stores audit_llm and audit_llm_name, and the two-pass audit completes
- RULE-14: Criteria are loaded via the single `load_criteria()` function (`--load-criteria` CLI); built-in criteria always apply, additional team criteria are appended — never replaced
- RULE-15: The skill documents a portable Python interpreter for invoking static_checks.py — falling back from `python3` to `python` to `py -3` — rather than assuming `python3` is always on PATH (it is not on stock Windows)
- RULE-16: When a proof's `test_file` is empty (e.g. C#/xUnit, where `dotnet test` leaves `TestCase.CodeFilePath` null), the skill resolves the source file from the fully-qualified `test_name` via `static_checks.py --resolve-source` before Pass 1 and Pass 2, so C# Pass-1/Pass-2 is reachable through purlin:audit without a populated path. The skill also documents that populating it natively requires source info (`RunConfiguration.CollectSourceInformation=true` with full PDBs)
- RULE-17: The skill documents which lever moves which assessment — that HOLLOW and EXCLUDED are decided by test code and no spec edit moves them, that WEAK must be fixed by strengthening the test rather than narrowing the proof description (never for anchor rules), and that the Proof Design levels are the ones prose is meant to move. It states the arithmetic for reaching a target Integrity score so an agent can answer feasibility in one step
- RULE-18: Writing the audit cache is a numbered step of its own, marked mandatory, naming the literal `--write-cache` command with an explicit `--project-root`. The skill states that an audit which does not write the cache has produced no measurement, and that pruning against an empty live-keys set would delete the entries just written
- RULE-19: The skill derives its mode from observable project state rather than asking or assuming: a Step 0 runs `--audit-scope` and maps the result to design-only or both, treats explicit user intent and `--design`/`--integrity` as overrides, and requires the chosen mode and the state behind it to be announced. It states that Pass 0.5 and Pass 1 must not run without proof files because they exit 2
- RULE-20: The skill documents the Proof Design pass — deterministic `--check-proof-design` followed by an LLM pass — with the four Design levels, the instruction never to use STRONG/WEAK/HOLLOW for a description, and remediation routed to `purlin:spec` because the description is the artifact at fault
- RULE-21: When the project sets `mutation_checks: true`, Pass 2 may ask the author to name the mutation that was run for a proof (which behaviour was broken, and that the proof failed while it was broken) and grades a proof whose author cannot name one no higher than WEAK. Naming a plausible mutation lifts the cap; it does not raise the grade by itself. When the project leaves `mutation_checks` at `false` the criterion does not apply and caps nothing, because the project never claimed the practice

## Proof

- PROOF-1 (RULE-1): Grep `skills/audit/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/audit/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `audit`
- PROOF-4 (RULE-4): e2e: Grep skills/audit/SKILL.md for independent auditor section; verify audit_criteria.md and STRONG/WEAK/HOLLOW @e2e
- PROOF-5 (RULE-5): e2e: Grep the independent auditor section; verify it routes remediation to `purlin:build`, states the audit is read-only, and contains no instruction to spawn a fixer agent @e2e
- PROOF-6 (RULE-6): e2e: Grep the independent auditor section for the re-audit step after fixes land; verify the re-check loop @e2e
- PROOF-7 (RULE-7): e2e: Grep independent auditor section for 3 rounds; verify termination condition @e2e
- PROOF-8 (RULE-8): e2e: Grep anchor rule handling for report to lead; verify ambiguous anchor protocol @e2e
- PROOF-9 (RULE-9): e2e: Audit hollow test code with external LLM; verify returns HOLLOW or WEAK @e2e
- PROOF-10 (RULE-10): e2e: Audit strong test code with external LLM; verify STRONG or WEAK (not HOLLOW) @e2e
- PROOF-11 (RULE-11): e2e: Parse external LLM response; verify ASSESSMENT, CRITERION, WHY, FIX fields extracted @e2e
- PROOF-12 (RULE-12): e2e: Mixed-quality test file; static_checks catches assert True; valid test goes to external LLM @e2e
- PROOF-13 (RULE-13): e2e: Write config with fake LLM command; verify ping, config fields, and two-pass audit @e2e
- PROOF-14 (RULE-14): e2e: Create fake git repo with additional criteria; configure project; verify load_criteria returns built-in + additional with separator; verify Pass 1 still catches assert True; verify additional criteria reach fake LLM prompt @e2e
- PROOF-15 (RULE-15): Grep `skills/audit/SKILL.md` for the interpreter-fallback guidance; verify it documents `python` and `py -3` as fallbacks for `python3`
- PROOF-16 (RULE-16): Grep `skills/audit/SKILL.md` for the empty-`test_file` fallback; verify it documents resolving the source from `test_name` via `--resolve-source` and mentions `CollectSourceInformation` as the native way to populate it
- PROOF-17 (RULE-17): Grep `skills/audit/SKILL.md` for the lever section; verify it names HOLLOW, EXCLUDED, WEAK and the Design levels with what moves each, warns against narrowing a proof description and against reclassifying to raise a score, and contains the ceiling and target formulas
- PROOF-18 (RULE-18): Grep `skills/audit/SKILL.md` for a numbered cache-write step ordered before the prune step; verify it contains `--write-cache`, `--project-root`, the word mandatory, and a warning against pruning with an empty live-keys file
- PROOF-19 (RULE-19): Grep `skills/audit/SKILL.md` for a Step 0 mode-selection section; verify it invokes `--audit-scope`, names both `design` and `both` outcomes with the state that implies each, documents the `--design`/`--integrity` overrides, requires announcing the chosen mode, and warns that Pass 0.5 and Pass 1 exit 2 without proof files
- PROOF-20 (RULE-20): Grep `skills/audit/SKILL.md` for the Proof Design pass; verify it names `--check-proof-design`, all four Design levels, the Design scoring formula, the prohibition on using test vocabulary for descriptions, and routes remediation to `purlin:spec`
- PROOF-21 (RULE-21): Grep `references/audit_criteria.md` and verify the Pass 2 WEAK list carries a mutation criterion that names `mutation_checks`, states the WEAK cap for a proof with no mutation on record, states that naming one lifts the cap rather than raising the grade, and states that the criterion does not apply when the field is `false`. Verify it sits in the WEAK section rather than the HOLLOW or STRONG one, so it caps rather than fails a proof
