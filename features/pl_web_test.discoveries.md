# User Testing Discoveries: PL Web Test

### [BUG] M25: STALE verdict format test too shallow (Discovered: 2026-03-23)
- **Observed Behavior:** Test only checks for the STALE keyword presence; it does not validate the 6-field format or commit message content.
- **Expected Behavior:** Test should validate the complete 6-field STALE verdict format including the commit message field.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See pl_web_test.impl.md for full context.
