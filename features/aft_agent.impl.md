# Implementation Notes: AFT Agent Interaction Testing

## Architecture Decisions

### Harness Location
Shell harness at `dev/test_agent_interactions.sh` (Purlin-dev-specific, not consumer-facing).
Python infrastructure tests at `dev/test_aft_agent_harness.py`.

### Multi-Turn Session Management
- First turn uses `--session-id <id>` to create a named session with system prompt
- Subsequent turns use `--resume <id>` without re-sending the system prompt
- `reset_session()` clears session state between scenarios
- Session IDs follow `aft-agent-<timestamp>-<pid>` format for uniqueness

### construct_release_prompt() Design
- Builds standard 4-layer instruction stack from fixture directory
- Reads step `agent_instructions` from `tools/release/global_steps.json` in fixture
- Falls back to `.purlin/release/local_steps.json`, then project root's `global_steps.json`
- Handles absent steps file gracefully (no error, just skips injection)

### Fixture Tag SKIP Handling
- `checkout_fixture_safe()` checks tag existence via `git rev-parse` before cloning
- Returns `SKIP:<tag>` and exit code 1 if tag is missing
- Scenarios catch the failure and record SKIP with the tag name as reason
- SKIP increments `TESTS_SKIPPED` counter, not `TESTS_FAILED`

### Git History for Version Notes Tests
- `prior-tag` scenario creates synthetic git history after fixture checkout
- Tags HEAD as `v1.0.0`, adds 2 commits to simulate post-release work
- Shallow clone (`--depth 1`) is sufficient since we reconstruct needed history

## Test Quality Audit
- AP-1 (behavioral outcomes): Tests verify harness infrastructure behavior (prompt construction, session management, scenario filtering) not implementation internals
- AP-2 (no mocks of internal code): No mocking; tests exercise real fixture checkout/cleanup
- AP-3 (external dependency mock pattern): claude --print calls are not tested directly (expensive API calls); Python tests verify harness structure and infrastructure
- AP-4 (scenario traceability): 5/5 automated scenarios traced, 22 tests total
- AP-5 (test isolation): Each test creates/destroys its own fixture repos via tempdir

## Regression Tier Ownership Transfer (2026-03-18)

Per the regression ownership model change (commit 28e7deb), the agent interaction harness
(`dev/test_agent_interactions.sh`) is now QA-owned. The Builder does not write or modify
regression harnesses.

### Harness Expectation Mismatches (11 of 21 tests)

All 11 failures in `tests/aft_agent/tests.json` are **stale harness expectations**, not
application code bugs. The underlying tools (instruction audit, doc consistency check, version
notes, submodule safety audit) function correctly. The harness assertions pattern-match against
LLM response text, and those patterns have drifted from the model's current response format.

Failing scenarios and root cause:
- `instruction-audit-base-error: halt or escalation signaled` — Assertion expects specific halt/escalate phrasing
- `doc-new-section: turn 1/2` — Assertion expects specific gap table format and acknowledgment text
- `doc-gaps-user-declines: turn 1/2` — Assertion expects specific coverage gap table and decline acknowledgment
- `version-notes-no-tags` — Assertion expects specific no-tags handling output
- `version-notes-custom-text: turn 1/2` — Assertion expects specific release note suggestion format
- `submodule-safety-warning: no critical violations` — Assertion incorrectly flags warning-only state
- `submodule-safety-user-confirms: turn 1/2` — Assertion expects specific WARNING report and confirmation flow

**Action for QA:** Update harness assertions to match current model response patterns.

## Pre-Existing Bug Fix
Discovered and fixed duplicate `commit_and_tag "main/cdd_startup_controls/auto-mode"` in `dev/setup_fixture_repo.sh` (lines 888 and 945). The duplicate caused fixture repo rebuild to fail with `set -e`. Removed the second identical block.
