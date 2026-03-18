## Implementation Notes

**[CLARIFICATION]** The spec says watch mode polls at "1-second intervals" — implemented with `sleep 1` in the loop. On macOS without coreutils `timeout`, the fallback uses background process + polling kill with `pkill -P` to kill child processes. (Severity: INFO)

**[CLARIFICATION]** The enriched `tests.json` format (Section 2.3) is documented and tested as a JSON schema convention — test harnesses that support `--write-results` are expected to produce these fields. No changes to existing harnesses were required for the format definition itself. (Severity: INFO)

**[AUTONOMOUS]** The QA skill (`pl-regression.md`) is structured as a protocol document rather than executable code, consistent with other slash commands in `.claude/commands/`. It guides the QA agent through discovery, selection, command composition, and result processing. (Severity: WARN)

### Test Quality Audit
Evaluated via manual review (2026-03-18)
- Scenario: Watch mode polls and executes trigger -> test_watch_executes_trigger_and_resumes -> ALIGNED
- Scenario: Once mode runs single harness invocation -> test_once_mode_runs_harness_and_exits, test_once_mode_failing_harness -> ALIGNED
- Scenario: Watch mode timeout kills long-running harness -> test_timeout_kills_long_harness -> ALIGNED
- Scenario: Watch mode SIGINT prints session summary -> test_sigint_prints_summary -> ALIGNED
- Scenario: Runner handles malformed trigger gracefully -> test_malformed_trigger_is_deleted -> ALIGNED
- Scenario: QA skill identifies regression-eligible features -> test_skill_file_exists_and_has_discovery_flow, test_skill_identifies_aft_metadata_features -> ALIGNED
- Scenario: QA skill composes external command -> test_skill_references_once_mode, test_skill_references_watch_mode -> ALIGNED
- Scenario: QA skill creates BUG discoveries -> test_skill_has_bug_discovery_creation_protocol -> ALIGNED
- Scenario: Enriched results include scenario-level context -> test_enriched_fields_are_valid_json, test_enriched_format_backward_compatible -> ALIGNED
- Scenario: Staleness detection prioritizes re-testing -> test_stale_feature_detected_by_mtime -> ALIGNED
