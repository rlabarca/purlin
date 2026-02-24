# Implementation Notes: Release Checklist — Core Data Model

*   The auto-discovery algorithm in Section 2.5 is designed to be idempotent: running it multiple times against the same inputs produces the same result.
*   The Builder MUST update `tools/release/global_steps.json` to contain the 6 step definitions from Section 2.7. Remove the `purlin.mark_release_complete` entry. The exact JSON structure follows the schema in Section 2.1.
*   The Builder MUST update `.purlin/release/config.json` to remove the `{"id": "purlin.mark_release_complete", "enabled": true}` entry from the steps array.
*   **Removal rationale (`purlin.mark_release_complete`):** This step assumed per-version release specification files (e.g., `release_v0.5.md`) marked `[Complete]` at release time. This project does not use per-version release files. The only release-related feature files are specs for the release checklist tool itself, which follow the standard CDD feature lifecycle and are not a release-time Architect action. The step had no valid target and was retired.
*   The `code` field for `purlin.push_to_remote` is the only step with a non-null `code` value in the initial set. The other steps require agent judgment or interactive verification and cannot be safely automated with a single shell command.
*   There are no Manual Scenarios for this feature. Verification is entirely automated (unit tests against the data loading and resolution logic).
