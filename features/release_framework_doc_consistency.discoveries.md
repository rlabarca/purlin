# User Testing Discoveries: Release Framework Doc Consistency

### [BUG] H11: Terminology mismatch check absent (Discovered: 2026-03-23)
- **Observed Behavior:** There is no automated detection of terminology mismatches across the 5 base instruction files.
- **Expected Behavior:** An automated check should detect inconsistent terminology usage across all base instruction files to prevent drift.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added `check_terminology_consistency()` to `doc_consistency_check.py` with predefined term groups (section headings, role names, lifecycle labels). Tests added in `test_release_audit.py`.
- **Source:** Spec-code audit (deep mode). See release_framework_doc_consistency.impl.md for full context.

### [DISCOVERY] H12: README-vs-instruction consistency check absent (Discovered: 2026-03-23)
- **Observed Behavior:** There is no automated cross-reference check between README content and instruction file content.
- **Expected Behavior:** An automated consistency check should verify that README documentation aligns with the corresponding instruction files.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added `check_readme_instruction_consistency()` to `doc_consistency_check.py` with three checks: role focus phrase consistency, role section coverage, and critic dual-gate architecture. 6 new tests in `test_release_audit.py`.
- **Source:** Spec-code audit (deep mode). See release_framework_doc_consistency.impl.md for full context.
