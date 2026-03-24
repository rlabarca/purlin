# User Testing Discoveries: PL Spec Code Audit

### [BUG] M15: test_support test file missing 3 state fields (Discovered: 2026-03-23)
- **Observed Behavior:** The test_support test file omits 3 state fields: timestamp, code_inventory, and ownership_map_complete.
- **Expected Behavior:** The test file should include assertions for all state fields including timestamp, code_inventory, and ownership_map_complete.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See pl_spec_code_audit.impl.md for full context.

### [BUG] test_support test file hardcodes 11 gap dimensions (Discovered: 2026-03-23)
- **Observed Behavior:** test_all_11_gap_dimensions_listed and test_spec_and_command_both_reference_11_dimensions should reference 12. The newer test file is correct.
- **Expected Behavior:** Both test functions should reference 12 gap dimensions.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (LOW). See pl_spec_code_audit.impl.md for context.
