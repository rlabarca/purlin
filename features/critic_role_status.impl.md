# Implementation Notes: Critic Role Status

## Targeted Scope Acknowledgment (2026-03-16)

The last implementation cycle used targeted scope covering 2 of 19 scenarios (the two SPEC_DISPUTE Action Required routing scenarios added in that cycle). All 19 automated scenarios have full traceability (19/19 traced, 30 tests passing). The 17 unscoped scenarios were verified in a previous full-scope cycle and have not changed since. The targeted scope is appropriate for the change that was made. The Builder should use `[Scope: full]` on the next implementation cycle that touches this feature.

## [DISCOVERY] (acknowledged) compute_role_status was not reading sidecar files (2026-03-13)

`compute_role_status()` parsed discovery entries from the inline `## User Testing Discoveries` section of the feature file, but all modern features use sidecar files (`features/<name>.discoveries.md`). This meant QA DISPUTED status and Builder BLOCKED status could not trigger from sidecar-based disputes — only from inline sections (which are deprecated). Fixed by adding sidecar file lookup (matching the pattern in `audit_user_testing_section`) before falling back to inline section parsing. This bug affected all role status computations involving disputes, not just the two new scenarios.
