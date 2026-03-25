# User Testing Discoveries: Critic Tool

### [BUG] H1: Compact Policy Violation Grouping (Discovered: 2026-03-23)
- **Observed Behavior:** Code emits one line per violation, listing each individually without grouping.
- **Expected Behavior:** Spec requires grouped format: `N x pattern in file (lines N,M,O...+K more)` -- violations of the same pattern in the same file should be collapsed into a single grouped line.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See critic_tool.impl.md for full context.
- **Resolution:** Replaced individual-line emission in `generate_critic_report()` with grouping by `(feature_file, pattern, file)` tuple. Groups show count and first 3 line numbers with `+K more` for overflow.

### [BUG] H2: Weak Traceability Match (Discovered: 2026-03-23)
- **Observed Behavior:** `_test_added_after_commit()` exists but is never wired into action item generation; `weak_matches` is always empty.
- **Expected Behavior:** Weak traceability matches should be detected and surfaced in action items when tests are added after the commit that introduced the code they cover.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See critic_tool.impl.md for full context.
- **Resolution:** Added weak traceability match detection in `generate_action_items()` that cross-references `_weak_matches` against new scenarios from `scenario_diff`, uses `_test_added_after_commit()` for temporal checks, and generates HIGH Builder action items for pre-existing-test-only matches.

### [BUG] M1: targeted_scope_audit lifecycle condition inverted (Discovered: 2026-03-23)
- **Observed Behavior:** Code emits the targeted_scope_audit block when lifecycle is TODO (should be DONE) and omits it when lifecycle is DONE (should emit).
- **Expected Behavior:** The targeted_scope_audit block should be emitted when the lifecycle state is DONE and omitted when TODO -- the condition is inverted from the spec requirement.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See critic_tool.impl.md for full context.
- **Resolution:** Changed condition from `lifecycle_state == 'todo'` to `lifecycle_state in ('testing', 'complete')` in `generate_critic_json()`.

### [BUG] Figma Dev Status Advisory Gate has no scenario (Discovered: 2026-03-23)
- **Observed Behavior:** Code generates LOW PM action item when lifecycle=TODO and figma_status=Design. No scenario covers this.
- **Expected Behavior:** Need scenario coverage for the Figma Dev Status Advisory Gate behavior.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See critic_tool.impl.md for context.

### [BUG] Regression Guidance Detection has no scenario (Discovered: 2026-03-23)
- **Observed Behavior:** Code detects features with ## Regression Guidance and no regression coverage, generating MEDIUM QA action item. No scenario covers this.
- **Expected Behavior:** Need scenario coverage for the Regression Guidance Detection behavior.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See critic_tool.impl.md for context.
