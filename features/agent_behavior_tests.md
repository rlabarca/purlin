# Feature: Agent Behavior Test Harness

> Label: "Dev: Agent Behavior Tests"
> Category: "Test Infrastructure"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/test_fixture_repo.md
> Prerequisite: features/cdd_startup_controls.md
> Prerequisite: features/pl_session_resume.md

[TODO]

## 1. Overview

A Purlin-internal test harness that automates verification of agent startup, resume, and help behavior using `claude --print` in single-turn mode against fixture repo states. The harness constructs system prompts using the same 4-layer concatenation as the launcher scripts, runs Claude against them, and asserts expected output patterns.

This is Purlin-internal tooling (`dev/`, not `tools/`). Consumer projects do not need to test framework-level agent behavior -- they benefit from the fixture repo and `/pl-aft-web` instead.

---

## 2. Requirements

### 2.1 Test Runner Location

- **Script:** `dev/test_agent_behavior.sh` (executable, `chmod +x`).
- **Classification:** Purlin-dev-specific (in `dev/`, not consumer-facing). No submodule safety mandate applies.

### 2.2 Fixture Dependency

- Each test scenario has a corresponding fixture tag in the Purlin fixture repo.
- The test runner uses `tools/test_support/fixture.sh checkout` to obtain the fixture state.
- Fixture tags follow the convention: `main/<feature-name>/<scenario-slug>`.
- Fixture cleanup happens after each scenario via `tools/test_support/fixture.sh cleanup`.
- If the fixture repo does not exist when the test runner starts, the runner MUST invoke `dev/setup_behavior_fixtures.sh` to create it before proceeding. This removes the manual prerequisite of running the setup script separately.

### 2.2.1 Fixture Setup Script Contract

The test suite uses `dev/setup_behavior_fixtures.sh` for test fixture preparation:

*   **Success:** Exit code 0. Outputs created tag names to stdout (one per line).
*   **Failure:** Exit code 1. Outputs error description to stderr.
*   **Idempotent:** Safe to run multiple times; skips already-existing fixtures.

### 2.3 System Prompt Construction

- The test runner constructs the system prompt using the same 4-layer concatenation order as the launcher scripts:
  1. Base HOW_WE_WORK (`instructions/HOW_WE_WORK_BASE.md`)
  2. Role-specific base instructions (`instructions/<ROLE>_BASE.md`)
  3. HOW_WE_WORK overrides (`.purlin/HOW_WE_WORK_OVERRIDES.md`)
  4. Role-specific overrides (`.purlin/<ROLE>_OVERRIDES.md`)
- Instruction files are read from the fixture checkout, not from the current working copy. This ensures tests verify the instruction state captured in the fixture tag.
- The concatenated prompt is written to a temp file for `--append-system-prompt-file`.

### 2.4 Test Execution

- Each scenario runs: `claude --print --no-session-persistence --append-system-prompt-file <prompt-file> --output-format json "<trigger-message>"`
- The trigger message simulates a session start (e.g., `"Begin Builder session."`) or a command invocation (e.g., `"/pl-help"`).
- The `--output-format json` flag enables structured parsing of Claude's response.
- Each test invocation is independent (no session state carries between tests).
- The test runner uses `jq` for JSON response parsing (extracting the result field from Claude's `--output-format json` output). If `jq` is unavailable, the runner falls back to raw output string matching.

### 2.5 Assertion Strategy

- Assert patterns, not exact output. Claude may word things differently but the structural elements are deterministic:
  - Command table format (Unicode horizontal rules, command/description columns)
  - Presence/absence of work plan sections
  - Specific phrases (e.g., "find_work disabled -- awaiting instruction.")
  - Checkpoint field echoing (feature name, protocol step number)
  - Correct command table variant (main vs collab)
- Assertions use `grep -q` or `grep -c` against the JSON response text field.
- Each assertion prints PASS or FAIL with the assertion description.

### 2.6 Cost and Speed

- Each test invokes Claude once. Cost estimate: ~$0.01-0.05 per scenario at Haiku, ~$0.10-0.50 at Sonnet.
- 10 scenarios = ~$0.10-5.00 per full run.
- Slower than unit tests (~30-60 sec per scenario due to API latency) but fully automated.
- Run on-demand, not on every commit. Intended for pre-release verification or after instruction file changes.
- The test runner SHOULD default to the cheapest model (Haiku) with an optional `--model <model>` flag override.

### 2.7 Test Output

- Each scenario prints: `PASS: <description>` or `FAIL: <description>` followed by diagnostic details on failure.
- At the end, print a summary: `N/M tests passed`. Exit with non-zero status if any test failed.
- Optionally write results to `tests/<feature>/tests.json` per the CDD test reporting convention.

### 2.8 Scenarios Covered

The following manual scenarios are automated by this harness:

**From `cdd_startup_controls.md`:**
1. Startup Print Sequence Appears First
2. Expert Mode Bypasses Orientation
3. Guided Mode Presents Work Plan
4. Auto Mode Begins Executing Immediately

**From `pl_session_resume.md`:**
5. Builder Mid-Feature Resume
6. QA Mid-Verification Resume
7. Full Reboot Without Launcher

**From `pl_help.md`:**
8. Architect Re-displays Command Table
9. Builder Re-displays Command Table on Collaboration Branch
10. QA Re-displays Command Table on Collaboration Branch

### 2.9 Scenarios That Remain Manual

The following scenarios are NOT covered by this harness because they require human judgment:

- `pl_update_purlin.md` merge review scenarios -- require human assessment of merge correctness.
- `cdd_startup_controls.md` dashboard toggle scenarios -- these are web UI scenarios, covered by `/pl-aft-web` instead.

### 2.10 Fixture Tags Required

The Builder MUST create these fixture tags in the Purlin fixture repo:

| Tag | State Description |
|-----|-------------------|
| `main/cdd_startup_controls/startup-print-sequence` | Default config (find_work: true, auto_start: false) |
| `main/cdd_startup_controls/expert-mode` | Config with find_work: false, auto_start: false for builder |
| `main/cdd_startup_controls/guided-mode` | Config with find_work: true, auto_start: false for builder |
| `main/cdd_startup_controls/auto-mode` | Config with find_work: true, auto_start: true for builder |
| `main/pl_session_resume/builder-mid-feature` | Checkpoint file showing builder at protocol step 2 for a feature |
| `main/pl_session_resume/qa-mid-verification` | Checkpoint file showing QA at scenario 6 of 8 for a feature |
| `main/pl_session_resume/full-reboot-no-launcher` | Project state with checkpoint but no system prompt (simulating non-launcher start) |
| `main/pl_help/architect-main-branch` | Project on main branch, default config |
| `main/pl_help/builder-collab-branch` | Project with .purlin/runtime/active_branch containing "collab/feat1" |
| `main/pl_help/qa-collab-branch` | Project with .purlin/runtime/active_branch containing "collab/v2" |

---

## 3. Scenarios

### Unit Tests
#### Scenario: Test runner checks out fixture and constructs prompt

    Given the fixture repo has tag "main/cdd_startup_controls/expert-mode"
    When the test runner executes the expert-mode test
    Then the fixture is checked out to a temp directory
    And the system prompt is constructed from the fixture's instruction files
    And the prompt contains all 4 layers in the correct order

#### Scenario: Command table assertion passes for valid output

    Given claude --print returns output containing a Unicode-bordered command table
    When the test runner asserts "command table present"
    Then the assertion passes (grep matches the table header pattern)

#### Scenario: Expert mode outputs correct message

    Given the fixture tag "main/cdd_startup_controls/expert-mode" is checked out
    When claude --print is invoked with "Begin Builder session."
    Then the output contains "find_work disabled"
    And the output does NOT contain a work plan or Critic report

#### Scenario: Resume test echoes checkpoint fields

    Given the fixture tag "main/pl_session_resume/builder-mid-feature" is checked out
    And the checkpoint contains feature "my_feature" at step 2
    When claude --print is invoked with "/pl-resume"
    Then the output contains "my_feature"
    And the output references step 2 or the saved protocol position

#### Scenario: Help test shows correct variant for branch

    Given the fixture tag "main/pl_help/builder-collab-branch" is checked out
    And the project has .purlin/runtime/active_branch containing "collab/feat1"
    When claude --print is invoked with "/pl-help"
    Then the output contains the Branch Collaboration Variant table
    And the output contains "feat1"

#### Scenario: Fixture cleanup runs after each test

    Given a test scenario has completed (pass or fail)
    When the test runner moves to the next scenario
    Then the previous fixture checkout directory has been removed

#### Scenario: Test summary reports correct counts

    Given 8 tests passed and 2 tests failed
    When the test runner prints the summary
    Then the output reads "8/10 tests passed"
    And the exit code is non-zero

#### Scenario: Test runner auto-creates fixtures when missing

    Given the fixture repo does not exist at the expected path
    When the test runner is invoked
    Then the runner executes dev/setup_behavior_fixtures.sh
    And the fixture repo is created with all required tags
    And tests proceed normally after setup

### QA Scenarios
None.
