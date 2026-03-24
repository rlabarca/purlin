# User Testing Discoveries: Release Critic Consistency Check

### [BUG] H13: Phase 2 README update not automated (Discovered: 2026-03-23)
- **Observed Behavior:** Scenario is tagged auto-test-only but only Phase 1 detection exists; Phase 2 README update automation is absent.
- **Expected Behavior:** Phase 2 should automate the README update process, not just detect inconsistencies (Phase 1).
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See release_critic_consistency_check.impl.md for full context.

### [BUG] M45: Routing rule severity wrong (Discovered: 2026-03-23)
- **Observed Behavior:** Code emits WARNING severity for routing rule violations.
- **Expected Behavior:** Spec says routing rule violations should be CRITICAL severity.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See release_critic_consistency_check.impl.md for full context.
