# User Testing Discoveries: Critic Role Status

### [BUG] M27: QA TESTING priority wrong (Discovered: 2026-03-23)
- **Observed Behavior:** Code emits MEDIUM priority for QA TESTING items at 4 separate sites.
- **Expected Behavior:** Spec says QA TESTING items should have HIGH priority.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See critic_role_status.impl.md for full context.
