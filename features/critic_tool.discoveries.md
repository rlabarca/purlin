# User Testing Discoveries: Critic Tool

### [BUG] H1: Compact Policy Violation Grouping (Discovered: 2026-03-23)
- **Observed Behavior:** Code emits one line per violation, listing each individually without grouping.
- **Expected Behavior:** Spec requires grouped format: `N x pattern in file (lines N,M,O...+K more)` -- violations of the same pattern in the same file should be collapsed into a single grouped line.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See critic_tool.impl.md for full context.

### [BUG] H2: Weak Traceability Match (Discovered: 2026-03-23)
- **Observed Behavior:** `_test_added_after_commit()` exists but is never wired into action item generation; `weak_matches` is always empty.
- **Expected Behavior:** Weak traceability matches should be detected and surfaced in action items when tests are added after the commit that introduced the code they cover.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See critic_tool.impl.md for full context.

### [BUG] M1: targeted_scope_audit lifecycle condition inverted (Discovered: 2026-03-23)
- **Observed Behavior:** Code emits the targeted_scope_audit block when lifecycle is TODO (should be DONE) and omits it when lifecycle is DONE (should emit).
- **Expected Behavior:** The targeted_scope_audit block should be emitted when the lifecycle state is DONE and omitted when TODO -- the condition is inverted from the spec requirement.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See critic_tool.impl.md for full context.
