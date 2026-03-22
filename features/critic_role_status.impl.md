# Implementation Notes: Critic Role Status

## Targeted Scope Acknowledgment (2026-03-16)

The last implementation cycle used targeted scope covering 2 of 19 scenarios (the two SPEC_DISPUTE Action Required routing scenarios added in that cycle). All 19 automated scenarios have full traceability (19/19 traced, 30 tests passing). The 17 unscoped scenarios were verified in a previous full-scope cycle and have not changed since. The targeted scope is appropriate for the change that was made. The Builder should use `[Scope: full]` on the next implementation cycle that touches this feature.

## [DISCOVERY] (acknowledged) compute_role_status was not reading sidecar files (2026-03-13)

`compute_role_status()` parsed discovery entries from the inline `## User Testing Discoveries` section of the feature file, but all modern features use sidecar files (`features/<name>.discoveries.md`). This meant QA DISPUTED status and Builder BLOCKED status could not trigger from sidecar-based disputes — only from inline sections (which are deprecated). Fixed by adding sidecar file lookup (matching the pattern in `audit_user_testing_section`) before falling back to inline section parsing. This bug affected all role status computations involving disputes, not just the two new scenarios.

## Targeted Scope: QA AUTO and manual scenario action items (2026-03-22)

Implemented 4 new scenarios covering QA AUTO status, QA TODO with mixed scenarios, manual QA scenario count in action items, and visual spec auto-classification on Web Test features.

### Changes to `parse_scenarios()`

- Added `@auto` tag detection: scenario headings ending with `@auto` are parsed with `is_auto: True` and the suffix is stripped from the title.
- Added `### QA Scenarios` section header recognition (treated equivalently to `### Manual Scenarios`).
- Added `### Unit Tests` header recognition (treated as automated section).

### Changes to `compute_role_status()`

- Added `testing_all_auto` detection: when a TESTING feature has manual/QA scenarios, checks whether all are `@auto`-tagged AND whether all visual spec items are auto-classified.
- Added visual spec auto-classification: visual spec items on `> Web Test:` features are auto-classified (not manual QA items); visual spec items on non-web features remain manual QA items.
- Added QA `AUTO` status in precedence chain: `FAIL > DISPUTED > TODO > AUTO > CLEAN > N/A`.
- Added `role_status_reason` dict to return value with human-readable reasons for all 4 roles.

**[CLARIFICATION]** The spec says "QA scenarios" in scenarios 2-4. Interpreted this as scenarios under `### QA Scenarios` or `### Manual Scenarios` headers (both are `is_manual: True`). The `@auto` tag suffix on scenario titles marks them as automatable despite being in a manual/QA section. (Severity: INFO)

**[CLARIFICATION]** For Scenario 4 (visual spec on Web Test), the feature has NO QA scenarios (only visual items). The `testing_all_auto` flag is set True when there are visual items on a web-test feature with zero non-@auto manual scenarios, even when manual_count is 0. This matches the spec: "Zero manual QA items" means AUTO. (Severity: INFO)
