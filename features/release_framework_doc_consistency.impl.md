# Implementation Notes: Framework Documentation Consistency

This step is positioned immediately after `purlin.instruction_audit` in Purlin's release config, so override consistency (`purlin.instruction_audit`) and instruction-internal consistency (this step) run together before the broader doc check.

This step's scope intentionally excludes `.purlin/` override files — those are covered by `purlin.instruction_audit`. This step focuses on the base instruction layer.

### Audit Findings -- 2026-03-23

**[DISCOVERY]** Terminology mismatch check absent
**Source:** /pl-spec-code-audit --deep (H11)
**Severity:** HIGH
**Details:** Spec §3 scenario requires automated detection of terminology mismatches between base instruction files (role names, lifecycle labels, step IDs across all 5 files). Neither `doc_consistency_check.py` nor any other automated script performs this cross-file comparison. The `CLASS_FEATURE_MAP` in `test_release_audit.py` borrows tests from doc_consistency and instruction_audit, but neither covers the 5-way base-instruction cross-reference.
**Suggested fix:** Add a `check_terminology_consistency()` function to `doc_consistency_check.py` that scans all 5 base instruction files for predefined term variants and flags mismatches.

**[DISCOVERY]** README-vs-instruction consistency check absent
**Source:** /pl-spec-code-audit --deep (H12)
**Severity:** HIGH
**Details:** Spec §3 scenario requires automated detection of README content that contradicts current instruction file content. No such check exists. `doc_consistency_check.py` checks stale file path references in README and feature coverage gaps, but does not parse instruction file behavior descriptions and compare them semantically.
**Suggested fix:** Add a structural check comparing README "The Agents" / "The Critic" sections against the corresponding BASE instruction file declarations.
