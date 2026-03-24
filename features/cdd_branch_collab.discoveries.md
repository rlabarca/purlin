# User Testing Discoveries: CDD Branch Collab

### [BUG] H4: Join Modal BEHIND+SAME wrong button (Discovered: 2026-03-23)
- **Observed Behavior:** Test asserts [Join] button with checkout action for the BEHIND+SAME state.
- **Expected Behavior:** Spec mandates [Update Remote & Join] button with update-to-head action for the BEHIND+SAME state.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See cdd_branch_collab.impl.md for full context.

### [DISCOVERY] M13: Leave with non-default base branch untested (Discovered: 2026-03-23)
- **Observed Behavior:** No test sets `branch_collab_base_branch` to a non-main value; leave-branch behavior with custom base branches is untested.
- **Expected Behavior:** Test coverage should include scenarios where `branch_collab_base_branch` is set to a value other than `main` to verify correct leave behavior.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See cdd_branch_collab.impl.md for full context.
