# Feature: Regression Testing

> Label: "Regression Testing"
> Category: "Test Infrastructure"
> Prerequisite: features/arch_testing.md

[TODO] <!-- PM reset 2026-03-23: new sections 2.2.4, 2.8.1 not yet implemented by Engineer -->

## 1. Overview

Provides infrastructure for running full regression suites outside the build cycle. The system has three tiers:

1. **Declarative scenarios** -- QA authors JSON scenario declarations in `tests/qa/scenarios/`. Each file describes what to test, not how to test it.
2. **Framework-provided harness runner** -- A Python harness in `tools/test_support/` consumes scenario JSON files, executes them based on harness type, and writes enriched `regression.json` results. Consumer projects get this via submodule; their Engineer never touches it.
3. **Meta-runner** -- A shell script in `tools/test_support/` discovers all scenario files, runs each via the harness runner, continues past failures, and prints a summary.

Engineer mode focuses on fast unit tests during Step 3; full regression runs at user-chosen intervals, owned end-to-end by QA. QA authors the scenario declarations, composes the regression set, and prints a clear copy-pasteable command for the user to run in an external terminal. Results feed back into the discovery system and enrich `regression.json` with scenario-level context so Engineer mode can batch-fix failures without re-running the suite.

For the Purlin framework repo, a dev-specific runner script at `dev/regression_runner.sh` provides watch/once modes as an additional convenience (see Section 2.1). This runner is NOT consumer-facing and is NOT part of the composed commands the QA skill prints.

---

## 2. Requirements

### 2.1 Runner Script (Purlin-Dev Only)

A shell script at `dev/regression_runner.sh` (Purlin-dev-specific, not consumer-facing) that dispatches test harnesses in two modes:

- **Watch mode:** `./dev/regression_runner.sh --watch` polls `.purlin/runtime/regression_trigger.json` at 1-second intervals. When a trigger file appears, the runner executes the specified harness, writes `.purlin/runtime/regression_result.json`, deletes the trigger, and resumes polling. SIGINT prints a summary of all executions in the session.
- **Once mode:** `./dev/regression_runner.sh --once <harness> [args...]` runs a single harness invocation and exits with the harness exit code.
- Per-execution timeout defaults to 300 seconds, configurable via `--timeout <seconds>`.
- Generic dispatch: the runner supports any harness that follows the `--write-results` convention. It does not hardcode harness paths.
- **Claude unavailability:** When a harness invocation fails with a non-zero exit code and stderr contains `claude` connection errors or authentication failures, the runner MUST record `exit_code` and include the stderr excerpt in `regression_result.json`. The runner does NOT retry -- it records the failure and continues polling (watch mode) or exits (once mode). The QA skill surfaces these as infrastructure failures distinct from test failures.

**Trigger format** (`.purlin/runtime/regression_trigger.json`):

```json
{
  "harness": "dev/test_agent_interactions.sh",
  "args": ["--write-results"],
  "requested_at": "2026-03-18T14:30:00Z"
}
```

**Result format** (`.purlin/runtime/regression_result.json`):

```json
{
  "harness": "dev/test_agent_interactions.sh",
  "exit_code": 0,
  "started_at": "2026-03-18T14:30:01Z",
  "completed_at": "2026-03-18T14:32:15Z",
  "tests_json_path": "tests/aft_agent/regression.json",
  "summary": "21/21 passed"
}
```

### 2.2 QA Regression Skills

Three QA-owned slash commands that replace the former unified `/pl-regression` skill. Each command has a single, clear purpose. QA owns the regression tier end-to-end: authoring scenario declarations, executing regression sets, and evaluating results.

**Harness authorship:** QA writes and maintains the harness scripts that test behavioral scenarios (agent interaction flows, web UI regression, API contract checks). Harness scripts are behavioral verification artifacts, not application code. They live alongside other QA verification scripts. Engineer mode does NOT write regression harnesses.

**UX invariant:** Whenever the QA agent asks the user to run anything in an external terminal -- whether through any regression skill or ad-hoc during triage -- it MUST print the exact, complete command. Never describe what to run; print the literal command. The user should never have to assemble a command from prose.

#### 2.2.1 `/pl-regression-author` (QA-owned)

**Purpose:** Create scenario JSON files from feature specs. Infrequent -- only needed when new features reach Engineer DONE status with no scenario file.

**Command file:** `.claude/commands/pl-regression-author.md`

**Behavior:**

1. Discover features needing scenario authoring: feature has `### Regression Testing` section or `## Regression Guidance` section or `> Web Test:` metadata, Engineer status is DONE, and no corresponding `tests/qa/scenarios/<feature_name>.json` exists.
2. Present authoring plan to user with feature count and list.
3. Per feature (one at a time, sequential): read spec, evaluate fixture needs (see Section 2.10.1), write scenario JSON to `tests/qa/scenarios/<feature_name>.json`, commit.
4. Print handoff message with next steps (see Section 2.12).

#### 2.2.2 `/pl-regression-run` (QA-owned)

**Purpose:** Execute existing regression scenarios. Routine -- the common operation.

**Command file:** `.claude/commands/pl-regression-run.md`

**Behavior:**

1. Read feature status via `tools/cdd/scan.sh`.
2. Identify regression-eligible features: features with existing scenario JSON that have STALE, FAIL, or NOT_RUN test results. Sort: STALE first, then FAIL, then NOT_RUN. Optional `--frequency <pre-release|per-feature>` filter (see Section 2.7.1).
3. Present interactive options to the user: "Found N features eligible for regression. Run all, or select? [all / 1,2,... / skip]".
4. Compose an external command based on user selection -- a direct harness invocation (single feature) or a sequential `&&` chain (multiple features). The runner (`dev/regression_runner.sh`) is a Purlin-dev convenience and is NOT part of the composed command.
5. Print the command in a clearly formatted, self-contained, copy-pasteable block. The user MUST be able to copy the entire command and paste it into a separate terminal without modification.
6. Offer productive wait: "While tests run, I can author scenarios for other features or review open discoveries."

#### 2.2.3 `/pl-regression-evaluate` (QA-owned)

**Purpose:** Process regression results after execution. Creates BUG discoveries for failures.

**Command file:** `.claude/commands/pl-regression-evaluate.md`

**Behavior:**

1. Read `regression.json` files for features with recently updated regression results (mtime newer than last Critic run).
2. For each feature with failures: create a `[BUG]` discovery sidecar entry in `features/<name>.discoveries.md` with `scenario_ref`, `actual_excerpt`, and `expected` from the enriched results.
3. Compute and report assertion tier distribution across all detail entries.
4. Flag `[SHALLOW]` suites where >50% of assertions are Tier 1.
5. Run `tools/cdd/scan.sh` to refresh the Critic report.
6. Print handoff message if failures were found (see Section 2.12).

#### 2.2.4 Regression Suite Status in `/pl-verify` Phase A Summary

After Phase A completes (auto-pass, smoke gate, @auto scenarios, classification), `/pl-verify` MUST scan for existing regression scenario JSON files and present a status table showing outstanding regression suites. This ensures the user is aware of regression tests that exist but haven't been run (or have stale results).

**Behavior:**

1. Scan `tests/qa/scenarios/*.json` for all scenario files.
2. For each, check the corresponding `tests/<feature>/regression.json` for result status (PASS/FAIL/NOT_RUN/STALE).
3. Read `PURLIN_OVERRIDES.md` tier table (if it exists) to determine each feature's test priority tier.
4. Group by frequency (`per-feature` vs `pre-release`). Within each group, sort by tier (smoke first, then standard, then full-only). Mark smoke-tier features with a `[smoke]` indicator.
5. Print the table in the Phase A Summary, after the existing summary block:

```
Regression suites:
  per-feature:
    [STALE]   critic_tool (3/3, but source modified since) [smoke]
    [PASS]    instruction_audit (5/5, 2h ago)
    [NOT_RUN] terminal_identity
    [NOT_RUN] release_record_version_notes (agent_behavior, 3 scenarios)

  pre-release:
    [NOT_RUN] skill_behavior_regression (agent_behavior, 9 scenarios)

Run regression suites? [all / per-feature / skip]
```

6. **Run all suites in-session.** All harness types — including `agent_behavior` — run directly via the harness runner. The `agent_behavior` harness invokes `claude --print` as a non-interactive subprocess; this is safe because `claude --print` is stateless and does not conflict with the parent Claude Code session.
7. **Background execution for slow suites.** When a suite is expected to take >30 seconds (e.g., `agent_behavior` with multiple scenarios), run it via `run_in_background` so QA can continue with other Phase A work (visual smoke, scenario classification) while tests execute. When the background process completes, QA is notified and auto-evaluates the results.
8. **Foreground execution for fast suites.** `web_test` and `custom_script` suites typically complete in seconds. Run these synchronously (foreground) for immediate feedback.
9. When `auto_start` is `true`: run STALE and NOT_RUN suites automatically (smoke first, then standard). For pre-release suites: prompt `"Run pre-release regression suites? [yes / skip]"` even under auto_start.

#### 2.2.5 `/pl-regression` -- RETIRED

The former unified state-machine skill is deleted. The three explicit skills above replace it entirely. No auto-detect alias is provided.

### 2.3 Enriched Result Format

Enhance `regression.json` detail entries with optional fields (backward-compatible with existing consumers):

- `scenario_ref` -- Feature file path and scenario name (e.g., `features/instruction_audit.md:Single-turn agent test`).
- `expected` -- Human-readable expected behavior from the Gherkin Then step.
- `actual_excerpt` -- First ~500 characters of actual output when the test fails.

These fields give Engineer mode enough context to batch-fix failures without re-running the regression suite.

### 2.4 Engineer Consumption Pattern

Engineer mode does NOT trigger or author regression tests. Engineer mode's only role in the regression tier is consuming results to fix application code. The user tells Engineer mode "regression results are ready." Engineer mode then:

1. Reads `regression.json` files for features with updated regression results.
2. Uses enriched fields (`scenario_ref`, `expected`, `actual_excerpt`) to diagnose and fix application code in one pass.
3. Re-runs only unit tests (Step 3 tier) to confirm fixes, without re-running the full regression suite.
4. Does NOT modify the harness scripts or scenario JSON files themselves. If a harness expectation is stale or a scenario assertion is wrong, Engineer mode flags it for QA via the feedback protocol (Section 2.11).

### 2.5 Staleness Detection

A regression result is stale when ANY of these conditions hold:

1. **Feature source changed:** The feature's source code was modified since the `regression.json` file's mtime.
2. **Harness infrastructure changed:** `tools/test_support/harness_runner.py` or the scenario JSON file (`tests/qa/scenarios/<feature>.json`) was modified since the `regression.json` file's mtime. This catches cases where Engineer mode fixes a harness bug — the regression results from before the fix are no longer valid.
3. **Prior failure:** `regression.json` has `status: "FAIL"`. Failed results are always stale (they need re-running after the fix).

The QA regression skill uses staleness to prioritize re-testing: stale features appear first in the eligible list and are marked with a `[STALE]` indicator.

**Completion gate:** A feature with a `[STALE]` or `[FAIL]` `regression.json` MUST NOT be marked `[Complete]` by QA. Features with only passing, non-stale regression results may proceed to `[Complete]`.

### 2.6 Assertion Tier Tracking

Each `regression.json` detail entry MAY include an optional `assertion_tier` field with value `1`,
`2`, or `3`, corresponding to the assertion quality tiers defined in
`features/arch_testing.md` Section "Assertion Quality Invariant". This field is backward-compatible -- existing consumers
that do not recognize it will ignore it.

The QA regression skill reports tier distribution in its summary output:

```
Tier Distribution: T1=3  T2=12  T3=6  (untagged=0)
```

Suites where more than 50% of assertions are Tier 1 are flagged with a `[SHALLOW]` indicator
in the summary, signaling that the suite relies too heavily on keyword-presence assertions
and is vulnerable to false positives.

### 2.7 Declarative Scenario Format

QA authors JSON scenario files in `tests/qa/scenarios/<feature_name>.json`. Each file declares what to test for one feature. The framework-provided harness runner (Section 2.8) consumes these files.

**Scenario file schema:**

```json
{
  "feature": "<feature_name>",
  "harness_type": "<agent_behavior | web_test | custom_script>",
  "frequency": "<optional: per-feature (default) | pre-release>",
  "scenarios": [
    {
      "name": "<scenario-slug>",
      "fixture_tag": "<optional: fixture tag for checkout>",
      "role": "<optional: ARCHITECT | BUILDER | QA -- for agent_behavior>",
      "prompt": "<optional: prompt text for agent_behavior>",
      "web_test_url": "<optional: URL for web_test>",
      "script_path": "<optional: path for custom_script>",
      "setup_commands": ["<optional: shell commands for inline state setup>"],
      "assertions": [
        {
          "tier": 1,
          "pattern": "<regex pattern to match in output>",
          "context": "<human-readable description of what this checks>"
        }
      ]
    }
  ]
}
```

**Supported harness types:**

- **`agent_behavior`:** Fixture checkout (if `fixture_tag` specified) -> construct system prompt from fixture's instruction files -> run `claude --print` with the specified `role` and `prompt` -> evaluate assertions against output.
- **`web_test`:** Delegates to the existing web test patterns (dev server against fixture state). Uses `web_test_url` or falls back to the feature's `> Web Test:` metadata.
- **`custom_script`:** Escape hatch. Runs the script at `script_path` with `--write-results` flag. The script is QA-authored and lives in `tests/qa/`.

**File naming:** The JSON filename MUST match the feature file stem (`<feature_name>.json` for `features/<feature_name>.md`). One scenario file per feature.

**Assertion tiers:** Each assertion's `tier` field (1, 2, or 3) maps to the assertion quality tiers defined in `features/arch_testing.md` Section 2.5. The harness runner propagates these to the enriched `regression.json` output.

#### 2.7.1 Frequency Field

The optional `frequency` field at the scenario file level controls when the suite is eligible for execution:

- **`per-feature`** (default when absent): Standard regression -- eligible whenever results are STALE/FAIL/NOT_RUN.
- **`pre-release`**: Long-running suites (e.g., skill behavior tests using `claude --print`) that run only during pre-release verification or manual trigger. `/pl-regression-run` skips `pre-release` suites unless invoked with `--frequency pre-release`.

### 2.8 Harness Runner Framework

**Location:** `tools/test_support/harness_runner.py` -- consumer-facing, submodule-safe.

A Python script that reads a single scenario JSON file and executes it:

**Progress output (mandatory):** The harness runner MUST print progress to stderr as it runs. Users run this from the command line and need to know what's happening, especially for long-running `agent_behavior` suites (30-60 seconds per scenario).

Print at startup:
```
skill_behavior_regression: 9 scenarios (agent_behavior, ~5-10 min)
```

Print per scenario:
```
  [1/9] architect-startup-command-table ... (running)
  [1/9] architect-startup-command-table ... PASS (34s)
  [2/9] builder-startup-identifies-todo ... (running)
  [2/9] builder-startup-identifies-todo ... FAIL (28s)
```

Print at completion:
```
skill_behavior_regression: 7/9 passed (4m 12s total)
Results: tests/skill_behavior_regression/regression.json
```

The `(running)` line is printed before execution starts (flushed immediately so the user sees it). The result line overwrites or follows it. Time estimates at startup are derived from `harness_type`: `agent_behavior` ~30-60s per scenario, `web_test` ~5-10s, `custom_script` ~10-30s.

**Execution steps:**

1. Parse the scenario JSON file.
2. For each scenario entry:
   a. If `fixture_tag` is specified, check out the fixture via `tools/test_support/fixture.sh checkout`.
   b. If `setup_commands` are specified, execute them in order (CWD = fixture dir if checked out, otherwise project root).
   c. Dispatch based on `harness_type`:
      - `agent_behavior`: Construct Claude invocation with `--print` flag, specified role, and prompt. Capture output.
      - `web_test`: Manage dev server lifecycle (see Section 2.8.1), fetch page content from URL, evaluate assertions.
      - `custom_script`: Execute the script at `script_path` with `--write-results`.
   d. Evaluate assertions against captured output (regex match for each pattern).
   e. Clean up: if fixture was checked out, run `fixture cleanup`. If a server was started by the harness, stop it (see Section 2.8.1).
3. Write enriched results to `tests/<feature_name>/regression.json` (NOT `tests.json`) with:
   - Standard fields: `status`, `passed`, `failed`, `total`.
   - Per-detail enriched fields: `scenario_ref`, `expected` (from assertion context), `actual_excerpt`, `assertion_tier`.
4. Exit with 0 if all assertions passed, non-zero otherwise.

**Output path separation:** The harness runner writes to `regression.json`, never `tests.json`. `tests.json` is Engineer-owned (unit test results). Writing regression results to `tests.json` clobbers Engineer counts and breaks the structural completeness gate.

#### 2.8.1 Web Test Server Lifecycle

The harness runner manages dev server lifecycle for `web_test` scenarios. The behavior depends on whether a fixture is checked out:

**No fixture (testing against live project state):**

1. Check if a dev server is already running: read `.purlin/runtime/server.port`. If the file exists and the port is responsive (HTTP GET returns 200), reuse the existing server — do NOT start a new one, do NOT stop it after the test.
2. If no server is running: start one via `/pl-server` (use the port from `web_test_url`, or auto-select if not specified). Track the PID for cleanup. After all scenarios in this file complete, stop the server.
3. **Readiness polling:** After starting a server, poll for readiness (HTTP GET to `http://localhost:<port>/`) with retries: 10 attempts, 1 second apart. If the server is not responsive after 10 attempts, fail the scenario with `"Error: dev server did not become ready within 10 seconds"`. Do NOT use a fixed `sleep`.

**With fixture (testing against controlled project state):**

1. Check if a dev server is already running on the `web_test_url` port. If yes, start the fixture server on a DIFFERENT port (auto-select via OS) to avoid conflict. Update the `web_test_url` for assertions to use the new port.
2. Start the dev server against the fixture directory via `/pl-server --project-root <fixture_dir> --port <port>`. This serves the fixture's feature files, config, and test artifacts — providing the controlled state the fixture was designed for.
3. **Readiness polling:** Same as above (10 attempts, 1 second apart).
4. After all scenarios using this fixture complete, stop the fixture server. The pre-existing server (if any) is left untouched.

**Cleanup mandate:** The harness runner MUST stop any server it started, even if scenarios fail or the harness crashes (use try/finally or atexit). Never leave orphaned server processes.

**Scenario JSON changes:** With this server lifecycle management, `web_test` scenarios do NOT need `setup_commands` to start the dev server. The harness runner handles it. Scenarios should specify `fixture_tag` for controlled state testing and `web_test_url` for the target URL (port). The harness adjusts the port if needed.

**Preference for fixture-based web tests:** When a `web_test` scenario has a `fixture_tag`, the harness MUST start the server against the fixture directory (not the live project). Fixture-based tests provide deterministic, controlled state — testing against live project state should be the fallback, not the default. QA should author `web_test` scenarios with fixture tags whenever the assertions depend on specific feature states, config values, or lifecycle statuses.

**CLI interface:**

```
python3 tools/test_support/harness_runner.py <scenario_json_path> [--project-root <path>]
```

**Submodule safety:**

- Uses `PURLIN_PROJECT_ROOT` for all path resolution, with climbing fallback.
- No artifacts written inside `tools/`.
- All generated files go to `tests/<feature>/` (project root relative).

### 2.9 Meta-Runner

**Location:** `tools/test_support/run_regression.sh` -- consumer-facing, submodule-safe.

A shell wrapper that discovers and runs all scenario files:

1. Discover scenario JSON files via glob: `${SCENARIOS_DIR:-tests/qa/scenarios}/*.json`.
2. For each file, invoke `harness_runner.py <file>`.
3. Continue past failures (do not abort on first failure).
4. After all runs, print a summary:
   ```
   Regression Summary:
     PASS  instruction_audit (5/5)
     FAIL  branch_collab (3/5)
     PASS  config_layering (8/8)

   Total: 16/18 passed (3 features tested, 1 failure)
   ```
5. Exit with 0 if all passed, 1 if any failed.

**CLI interface:**

```
tools/test_support/run_regression.sh [--scenarios-dir <path>]
```

**Consumer project wrapper:** QA generates a thin wrapper at `tests/qa/run_all.sh` (3 lines) during the first authoring session:

```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$(git rev-parse --show-toplevel)/purlin/tools/test_support/run_regression.sh" --scenarios-dir "$SCRIPT_DIR/scenarios"
```

(The `purlin/` path adapts to the project's submodule location.)

### 2.10 QA Authoring Workflow

QA authors scenario files one feature at a time during `/pl-regression-author`:

1. Read the feature spec and its `### Regression Testing` section (or `## Regression Guidance`).
2. Evaluate fixture needs per the fixture integration protocol (Section 2.10.1).
3. Write the scenario JSON file to `tests/qa/scenarios/<feature_name>.json`.
4. Commit the scenario file: `git commit -m "qa(<feature>): author regression scenario"`.
5. Print progress: `"Authored 3/8 scenarios. 5 remaining."`.
6. Move to next feature.

**Discovery heuristic (which features need authoring):**

- Feature has `### Regression Testing` section or `## Regression Guidance` section or `> Web Test:` metadata.
- Engineer status is DONE (implementation exists to test against).
- No corresponding `tests/qa/scenarios/<feature_name>.json` exists.

**Context management:**

- Each scenario file is independent (no cross-feature state).
- QA loads one spec at a time (~200 lines), writes one JSON file (~30 lines), commits.
- Context per feature: ~300 lines consumed, then discardable.
- Estimated capacity: 20-30 features per session before context pressure.
- For larger projects: human re-runs QA, it continues where it left off.
- Mid-session checkpoint via `/pl-resume save` captures regression authoring state.
- If context runs out mid-feature (scenario file not yet committed), the next session re-authors from scratch (acceptable because authoring one file is fast).

#### 2.10.1 Fixture Integration During Authoring

Per feature, QA applies this decision logic:

1. **Fixture repo check:** If no fixture repo exists at the convention path and the feature needs controlled state, QA prompts the user to create a local repo (via `fixture init`), configure a remote repo URL, or skip fixtures.
2. Does the `### Regression Testing` section reference fixture tags?
   - Yes: Check if tags exist via `fixture list`. Tags exist -> use them in scenario JSON. Tags missing -> QA creates them directly via `fixture add-tag` if the state can be constructed. For complex state requiring Engineer expertise, flag for Engineer.
3. No explicit fixture tags, but scenario needs controlled state?
   - Simple state (single config, no git history): Use inline `setup_commands` in the scenario JSON.
   - Moderate state (specific file content, config combinations): QA creates a fixture tag directly via `fixture add-tag`, then references it in the scenario JSON.
   - Complex state (elaborate git history, build artifacts, database state): Record the recommendation in `tests/qa/fixture_recommendations.md` (see `features/test_fixture_repo.md` Section 2.13) for Engineer mode to handle.

### 2.11 Engineer Feedback Protocol

When Engineer mode encounters regression test failures, it follows this triage:

**Code bug:** Engineer fixes the application code (existing pattern from Section 2.4).

**Broken test scenario:** Engineer creates a `[BUG]` discovery on the feature with:

- `Action Required: QA` -- routes to QA, not back to Engineer.
- Title includes `test-scenario` to distinguish from implementation bugs.
- Body includes `scenario_ref` and `actual_excerpt` from the enriched test results.

**Discovery format for broken scenarios:**

```
### [BUG] test-scenario: <assertion context> (Discovered: YYYY-MM-DD)
- **Scenario:** <feature_file>:<scenario_name>
- **Observed Behavior:** <actual_excerpt from enriched results>
- **Expected Behavior:** <assertion pattern/context that failed>
- **Action Required:** QA
- **Status:** OPEN
```

QA picks this up in the next session via Critic action items. QA fixes the scenario JSON and commits.

**Critic routing:** The Critic recognizes `Action Required: QA` on BUG discoveries and routes them to the QA column instead of Engineer mode column. This prevents Engineer mode from seeing its own feedback as a new action item.

### 2.12 Agent Handoff Protocol

Each agent session that performs regression work MUST end with explicit, actionable instructions telling the human exactly what to do next. The human is the orchestrator between agent sessions and needs clear routing instructions.

**QA -> Human (after authoring scenarios):**

```
Regression scenarios authored: N features.

NEXT STEPS:
  1. Run regression tests:
         ./tests/qa/run_all.sh
  2. When tests finish, launch Engineer to process results and fix failures.
  3. After Engineer fixes, re-run tests:
         ./tests/qa/run_all.sh
  4. When all tests pass, launch QA to process final results.
```

**QA -> Human (harness runner framework missing):**

```
Cannot author regression scenarios -- the harness runner framework
has not been built yet.

NEXT STEP:
  Launch Engineer. Engineer mode will build the harness runner framework
  as part of its normal TODO work.
  After Engineer finishes, re-run QA to author scenarios.
```

**QA -> Human (fixtures needed but missing):**

```
N features need fixture repos before regression scenarios can be authored.
Recorded recommendations in tests/qa/fixture_recommendations.md.

NEXT STEP:
  Launch Engineer. Tell it: "Create fixture tags for features listed in
  tests/qa/fixture_recommendations.md"
  After Engineer finishes, re-run QA to continue authoring.
```

**Engineer -> Human (after building harness runner framework):**

```
Harness runner framework built:
  tools/test_support/harness_runner.py
  tools/test_support/run_regression.sh

NEXT STEP:
  Launch QA to author regression scenarios.
  QA will create scenario files in tests/qa/scenarios/ and
  generate tests/qa/run_all.sh for you to execute.
```

**Engineer -> Human (after processing regression failures):**

```
Fixed N code bugs from regression results.
Flagged M broken test scenarios (routed to QA).

NEXT STEPS:
  1. Re-run regression tests to verify fixes:
         ./tests/qa/run_all.sh
  2. If all pass: done.
     If flagged scenarios still fail: launch QA to fix the
     broken scenario files.
```

**Engineer -> Human (after creating fixture tags):**

```
Created fixture tags for N features in .purlin/runtime/fixture-repo.

NEXT STEP:
  Launch QA to continue regression scenario authoring.
  QA will use the new fixtures automatically.
```

These handoff messages are mandatory -- they are a required part of each agent's session conclusion protocol when regression work was performed.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Watch mode polls and executes trigger

    Given the runner is started in watch mode
    When a trigger file is written to .purlin/runtime/regression_trigger.json
    Then the runner executes the specified harness
    And writes a result file to .purlin/runtime/regression_result.json
    And deletes the trigger file
    And resumes polling

#### Scenario: Once mode runs single harness invocation

    Given the runner is invoked with --once dev/test_agent_interactions.sh --write-results
    When the harness completes
    Then the runner exits with the harness exit code
    And a result file is written to .purlin/runtime/regression_result.json

#### Scenario: Watch mode timeout kills long-running harness

    Given the runner is started with --watch --timeout 5
    When a trigger specifies a harness that runs longer than 5 seconds
    Then the runner kills the harness process
    And writes a result file with a non-zero exit code
    And resumes polling

#### Scenario: Watch mode SIGINT prints session summary

    Given the runner is in watch mode and has completed 3 executions
    When the user sends SIGINT
    Then the runner prints a summary of all 3 executions with pass/fail counts
    And exits cleanly

#### Scenario: Runner handles malformed trigger gracefully

    Given the runner is in watch mode
    When a trigger file contains invalid JSON
    Then the runner logs an error message
    And deletes the malformed trigger file
    And resumes polling without crashing

#### Scenario: QA skill identifies regression-eligible features

    Given the project has 5 features with test metadata
    And 2 features have STALE test results
    And 1 feature has FAIL test results
    When the QA agent invokes /pl-regression-run
    Then the skill lists 3 eligible features sorted by staleness
    And presents the interactive selection prompt

#### Scenario: QA skill composes external command for selected features

    Given the QA agent selects features 1 and 3 from the eligible list
    When the skill composes the regression command
    Then the command is a direct harness invocation chain (not wrapped in the runner)
    And the composed command includes the correct harness path and --write-results args

#### Scenario: QA skill creates BUG discoveries for regression failures

    Given regression results show 2 failed scenarios across 2 features
    When the QA agent reads the regression results
    Then a [BUG] discovery sidecar entry is created for each failed feature
    And each entry includes the scenario_ref and actual_excerpt from enriched results

#### Scenario: Enriched results include scenario-level context

    Given a harness writes regression.json with enriched fields
    When the result file is read
    Then each detail entry contains scenario_ref with feature path and scenario name
    And failed entries contain expected and actual_excerpt fields

#### Scenario: Staleness detection prioritizes re-testing

    Given feature A has regression.json from 2 hours ago and source modified 1 hour ago
    And feature B has regression.json from 1 hour ago and no source modifications
    When the QA skill computes the eligible list
    Then feature A appears first with a STALE indicator
    And feature B does not appear in the eligible list

#### Scenario: Shallow assertion suite flagged when majority are Tier 1

    Given a harness writes regression.json with 10 detail entries
    And 6 entries have assertion_tier: 1
    And 4 entries have assertion_tier: 2
    When the QA regression skill reads the results and computes tier distribution
    Then the summary shows "T1=6  T2=4  T3=0"
    And the suite is flagged with a [SHALLOW] indicator
    And the indicator message notes that >50% of assertions are Tier 1

#### Scenario: Harness runner executes agent_behavior scenario from JSON

    Given a scenario JSON file with harness_type "agent_behavior"
    And the scenario specifies role "ARCHITECT" and a prompt
    And the scenario has a fixture_tag pointing to a valid fixture
    When the harness runner processes the scenario file
    Then the fixture is checked out
    And claude --print is invoked with the specified role and prompt
    And assertions are evaluated against the output
    And the fixture is cleaned up
    And enriched regression.json is written with scenario_ref and assertion_tier

#### Scenario: Harness runner handles web_test with no fixture and no running server

    Given a scenario JSON file with harness_type "web_test"
    And the scenario specifies web_test_url "http://localhost:9086"
    And no dev server is currently running
    When the harness runner processes the scenario file
    Then the harness starts a dev server on port 9086
    And polls for readiness before running assertions
    And enriched regression.json is written with pass/fail results
    And the server is stopped after all scenarios complete

#### Scenario: Harness runner reuses existing server for non-fixture web_test

    Given a scenario JSON file with harness_type "web_test"
    And a dev server is already running on port 9086
    And no fixture_tag is specified
    When the harness runner processes the scenario file
    Then the harness reuses the existing server (does not start a new one)
    And the existing server is NOT stopped after scenarios complete

#### Scenario: Harness runner starts fixture-scoped server for fixture web_test

    Given a scenario JSON file with harness_type "web_test"
    And the scenario has a fixture_tag and web_test_url "http://localhost:9086"
    And a dev server is already running on port 9086
    When the harness runner processes the scenario file
    Then the fixture is checked out
    And the harness starts a SEPARATE dev server against the fixture directory on a different port
    And assertions run against the fixture server (not the existing one)
    And the fixture server is stopped after scenarios complete
    And the pre-existing server on port 9086 is left running

#### Scenario: Harness runner falls back to custom_script

    Given a scenario JSON file with harness_type "custom_script"
    And the scenario specifies a script_path to a QA-authored script
    When the harness runner processes the scenario file
    Then the script at script_path is executed with --write-results
    And the script's regression.json output is consumed as the result

#### Scenario: Meta-runner discovers and runs all scenario files

    Given tests/qa/scenarios/ contains 3 scenario JSON files
    And one scenario will fail
    When run_regression.sh is invoked
    Then all 3 scenario files are processed
    And processing continues past the failure
    And a summary is printed with pass/fail counts per feature
    And exit code is 1 (at least one failure)

#### Scenario: QA authors scenario file during regression authoring

    Given a feature has a Regression Testing section and builder status DONE
    And no scenario file exists at tests/qa/scenarios/<feature_name>.json
    When the QA agent invokes /pl-regression-author
    Then the feature spec is read
    And a scenario JSON file is written to tests/qa/scenarios/<feature_name>.json
    And the file is committed
    And progress is printed showing authored count vs total

#### Scenario: Engineer flags broken scenario via discovery

    Given Engineer mode processes regression results
    And a test failure is caused by a stale assertion (not a code bug)
    When Engineer mode creates a BUG discovery
    Then the discovery title includes "test-scenario"
    And Action Required is set to "QA"
    And the discovery body includes scenario_ref and actual_excerpt
    And the Critic routes this to the QA column

#### Scenario: Harness runner writes enriched regression.json

    Given the harness runner has executed all scenarios in a JSON file
    When it writes the regression.json output
    Then each detail entry includes scenario_ref with feature path and scenario name
    And each entry includes assertion_tier from the scenario's assertion tier field
    And failed entries include expected and actual_excerpt fields
    And the standard status, passed, failed, total fields are present

### QA Scenarios

None.

## Regression Guidance
- Watch mode: trigger file consumed and deleted after execution
- Timeout enforcement: per-execution 300s default, configurable
- Result file written atomically with correct exit code and timing
- Generic dispatch: runner works with any harness following --write-results convention
- Declarative scenarios: JSON files in tests/qa/scenarios/ consumed by framework harness runner
- Meta-runner: discovers and runs all scenario files, continues past failures
- Agent handoff: every regression agent session ends with explicit next-step instructions
