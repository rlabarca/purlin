# Discovery Sidecar: pl_web_test

### [BUG] M25: STALE verdict format test too shallow (Discovered: 2026-03-23)
- **Scenario:** Figma-triangulated verification detects STALE spec
- **Observed Behavior:** Test only checks for STALE keyword presence; does not validate 6-field format or commit message content.
- **Expected Behavior:** Test should validate complete 6-field STALE verdict format including commit message field.
- **Action Required:** Engineer
- **Status:** RESOLVED
