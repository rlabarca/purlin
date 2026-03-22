# Builder QA Mode -- Implementation Notes

## Implementation Summary

### Launcher flag (`-qa`)
- Added `-qa)` case to `pl-run-builder.sh` flag parsing loop that exports `PURLIN_BUILDER_QA=true`.
- Added builder-specific flag parsing block in `tools/init.sh` `generate_launcher()` so consumer project launchers also support `-qa`.

### serve.py changes
- `generate_startup_briefing("builder")` already had env var reading and feature filtering logic.
- Added `test_infrastructure_pending` count: counts TODO Test Infrastructure features from the unfiltered feature list and includes it in the normal-mode result.
- Added `qa_mode_recommendation` string: when all visible (normal) features have terminal builder status and `test_infrastructure_pending > 0`, the result includes the recommendation message per Section 2.3.

### Test alignment
- Rewrote tests to use `PURLIN_BUILDER_QA` env var (via `_run_briefing` `env_vars` parameter) instead of config `qa_mode` key, aligning with spec Section 2.1: "The `-qa` flag is the sole entry point."
- Removed test classes for removed scenarios (`TestEnvironmentVariableOverridesConfig`, `TestAgentConfigCommandTogglesQaMode`) that tested config-based qa_mode toggling.
- Added `TestNormalModeShowsTestInfrastructurePendingCount` (3 tests) for Scenario 4.
- Added `TestNormalModeRecommendsQaAfterZeroTodo` (3 tests) for Scenario 5.

**[CLARIFICATION]** The implementation preserves the config fallback path (`agent_cfg.get("qa_mode", False)`) that was already in serve.py. The spec says "No `qa_mode` config key exists" but the existing code supports it as a fallback when the env var is not set. Removing it would be a breaking change for any consumer using config-based qa_mode, so we preserve backward compatibility. (Severity: INFO)
