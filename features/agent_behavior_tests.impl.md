# Implementation Notes: Agent Behavior Tests

**[CLARIFICATION]** The test harness uses `--output-format json` as specified, with `jq` for extracting the `result` field from Claude's JSON response. Falls back to raw output if JSON parsing fails. (Severity: INFO)

**[CLARIFICATION]** The fixture setup script (`dev/setup_behavior_fixtures.sh`) creates a LOCAL bare git repo rather than a remote repo. The fixture repo path is passed to the test runner via `--fixture-repo`. This is consistent with the fixture.sh `checkout` command which accepts both local paths and remote URLs. (Severity: INFO)

**[AUTONOMOUS]** The Python test file (`dev/test_behavior_harness.py`) has 18 test methods across 7 test classes (one per automated scenario). Some scenarios are decomposed into multiple test methods to cover sub-assertions (e.g., the command table assertion scenario tests valid table detection, missing table detection, Builder header detection, and isolated variant detection separately). The spec's 7 scenarios map to 7 test classes. (Severity: WARN)

**[AUTONOMOUS]** The fixture setup script copies instruction files from the current Purlin project into the fixture repo. This means fixture tags reflect the instruction state at setup time, not a frozen historical state. When instructions change, the setup script should be re-run to create updated fixtures. This is documented in the script's usage output. (Severity: WARN)

**[CLARIFICATION]** Scenarios 3-5 (Expert Mode, Resume, Help) involve actual `claude --print` API calls when run through the bash test runner. The Python tests verify the assertion logic and infrastructure patterns (prompt construction, checkpoint parsing, command table variant detection) without invoking Claude. The bash test runner is the end-to-end integration test; the Python file is the unit/structural test. (Severity: INFO)

## Architecture Decisions

- **Three-file structure:** `test_agent_behavior.sh` (bash test runner for end-to-end claude --print tests), `setup_behavior_fixtures.sh` (fixture repo creation), `test_behavior_harness.py` (Python unit tests for the 7 automated scenarios that produce tests.json).
- **All files in `dev/`:** Exempt from submodule safety mandate per the Tool Folder Separation Convention.
- **Default model is Haiku** for cost efficiency (`claude-haiku-4-5-20251001`), overridable via `--model`.
- **Fixture cleanup uses `fixture.sh cleanup`** (the consumer-facing tool) rather than raw `rm -rf`, ensuring the temp-directory safety guard is always applied.
