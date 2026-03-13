# Implementation Notes: Critic Role Status

## [DISCOVERY] compute_role_status was not reading sidecar files (2026-03-13)

`compute_role_status()` parsed discovery entries from the inline `## User Testing Discoveries` section of the feature file, but all modern features use sidecar files (`features/<name>.discoveries.md`). This meant QA DISPUTED status and Builder BLOCKED status could not trigger from sidecar-based disputes — only from inline sections (which are deprecated). Fixed by adding sidecar file lookup (matching the pattern in `audit_user_testing_section`) before falling back to inline section parsing. This bug affected all role status computations involving disputes, not just the two new scenarios.
