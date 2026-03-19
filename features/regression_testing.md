# Feature: Regression Testing

> Label: "Regression Testing"
> Category: "Test Infrastructure"
> Prerequisite: features/arch_testing.md

[TODO]

## 1. Overview

Provides infrastructure for running full regression suites outside the build cycle. The system has three tiers:

1. **Declarative scenarios** -- QA authors JSON scenario declarations in `tests/qa/scenarios/`. Each file describes what to test, not how to test it.
2. **Framework-provided harness runner** -- A Python harness in `tools/test_support/` consumes scenario JSON files, executes them based on harness type, and writes enriched `tests.json` results. Consumer projects get this via submodule; their Builder never touches it.
3. **Meta-runner** -- A shell script in `tools/test_support/` discovers all scenario files, runs each via the harness runner, continues past failures, and prints a summary.

The Builder focuses on fast unit tests during Step 3; full regression runs at user-chosen intervals, owned end-to-end by QA. QA authors the scenario declarations, composes the regression set, and prints a clear copy-pasteable command for the user to run in an external terminal. Results feed back into the discovery system and enrich `tests.json` with scenario-level context so the Builder can batch-fix failures without re-running the suite.

For the Purlin framework repo, a dev-specific runner script at `dev/regression_runner.sh` provides watch/once modes as an additional convenience (see Section 2.1). This runner is NOT consumer-facing and is NOT part of the composed commands the QA skill prints.

---

## 2. Requirements

### 2.1 Runner Script (Purlin-Dev Only)

A shell script at `dev/regression_runner.sh` (Purlin-dev-specific, not consumer-facing) that dispatches test harnesses in two modes:

- **Watch mode:** `./dev/regression_runner.sh --watch` polls `.purlin/runtime/regression_trigger.json` at 1-second intervals. When a trigger file appears, the runner executes the specified harness, writes `.purlin/runtime/regression_result.json`, deletes the trigger, and resumes polling. SIGINT prints a summary of all executions in the session.
- **Once mode:** `./dev/regression_runner.sh --once <harness> [args...]` runs a single harness invocation and exits with the harness exit code.
- Per-execution timeout defaults to 300 seconds, configurable via `--timeout <seconds>`.
- Generic dispatch: the runner supports any harness that follows the `--write-results` convention. It does not hardcode harness paths.

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
  "tests_json_path": "tests/aft_agent/tests.json",
  "summary": "21/21 passed"
}
```

### 2.2 QA Regression Skill

A QA-owned slash command at `.claude/commands/pl-regression.md`. QA owns the regression tier end-to-end: authoring scenario declarations, composing regression sets, and triaging results.

**Skill architecture:** The skill is a state machine with three modes, determined by the current project state:

1. **Author mode:** Features need scenario files. QA reads each feature spec's `### Regression Testing` section or `## Regression Guidance`, evaluates fixture needs, writes a scenario JSON file to `tests/qa/scenarios/<feature_name>.json`, and commits. One feature at a time.
2. **Run mode:** Existing scenarios need execution (STALE/FAIL/NOT_RUN results). QA composes a single copy-pasteable command for the user to run externally.
3. **Process mode:** Unprocessed results exist. QA reads `tests.json` files, creates BUG discoveries for failures, and reports tier distribution.

**State detection priority:** Author mode takes precedence when both authoring and running are needed. The QA skill detects the current state and enters the appropriate mode automatically.

**Harness authorship:** QA writes and maintains the harness scripts that test behavioral scenarios (agent interaction flows, web UI regression, API contract checks). Harness scripts are behavioral verification artifacts, not application code. They live alongside other QA verification scripts. The Builder does NOT write regression harnesses.

**Skill flow (Run mode):**

1. Read feature status via `tools/cdd/status.sh --role qa`.
2. Identify regression-eligible features: features with `> Web Test:` metadata or `### Regression Testing` sections that have STALE, FAIL, or NOT_RUN test results.
3. Present interactive options to the user: "Found N features eligible for regression. Run all, or select? [all / 1,2,... / skip]".
4. Compose an external command based on user selection -- a direct harness invocation (single feature) or a sequential `&&` chain (multiple features). The runner (`dev/regression_runner.sh`) is a Purlin-dev convenience and is NOT part of the composed command.
5. Print the command in a clearly formatted, self-contained, copy-pasteable block. The user MUST be able to copy the entire command and paste it into a separate terminal without modification.
6. After user confirms completion: read `tests.json` files for each regression-tested feature, create `[BUG]` discovery sidecar entries for any failures, print a summary, and run `tools/cdd/status.sh`.

**UX invariant:** Whenever the QA agent asks the user to run anything in an external terminal -- whether through this skill or ad-hoc during triage -- it MUST print the exact, complete command. Never describe what to run; print the literal command. The user should never have to assemble a command from prose.

### 2.3 Enriched Result Format

Enhance `tests.json` detail entries with optional fields (backward-compatible with existing consumers):

- `scenario_ref` -- Feature file path and scenario name (e.g., `features/instruction_audit.md:Single-turn agent test`).
- `expected` -- Human-readable expected behavior from the Gherkin Then step.
- `actual_excerpt` -- First ~500 characters of actual output when the test fails.

These fields give the Builder enough context to batch-fix failures without re-running the regression suite.

### 2.4 Builder Consumption Pattern

The Builder does NOT trigger or author regression tests. The Builder's only role in the regression tier is consuming results to fix application code. The user tells the Builder "regression results are ready." The Builder then:

1. Reads `tests.json` files for features with updated results.
2. Uses enriched fields (`scenario_ref`, `expected`, `actual_excerpt`) to diagnose and fix application code in one pass.
3. Re-runs only unit tests (Step 3 tier) to confirm fixes, without re-running the full regression suite.
4. Does NOT modify the harness scripts or scenario JSON files themselves. If a harness expectation is stale or a scenario assertion is wrong, the Builder flags it for QA via the feedback protocol (Section 2.11).

### 2.5 Staleness Detection

A regression result is stale when the feature's source code was modified since the `tests.json` file's mtime. The QA regression skill uses staleness to prioritize re-testing: stale features appear first in the eligible list and are marked with a `[STALE]` indicator.

### 2.6 Assertion Tier Tracking

Each `tests.json` detail entry MAY include an optional `assertion_tier` field with value `1`,
`2`, or `3`, corresponding to the assertion quality tiers defined in
`features/aft_agent.md` Section 2.10. This field is backward-compatible -- existing consumers
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
- **`web_test`:** Delegates to the existing web test patterns (CDD server against fixture state). Uses `web_test_url` or falls back to the feature's `> Web Test:` metadata.
- **`custom_script`:** Escape hatch. Runs the script at `script_path` with `--write-results` flag. The script is QA-authored and lives in `tests/qa/`.

**File naming:** The JSON filename MUST match the feature file stem (`<feature_name>.json` for `features/<feature_name>.md`). One scenario file per feature.

**Assertion tiers:** Each assertion's `tier` field (1, 2, or 3) maps to the assertion quality tiers defined in `features/arch_testing.md` Section 2.5. The harness runner propagates these to the enriched `tests.json` output.

### 2.8 Harness Runner Framework

**Location:** `tools/test_support/harness_runner.py` -- consumer-facing, submodule-safe.

A Python script that reads a single scenario JSON file and executes it:

1. Parse the scenario JSON file.
2. For each scenario entry:
   a. If `fixture_tag` is specified, check out the fixture via `tools/test_support/fixture.sh checkout`.
   b. If `setup_commands` are specified, execute them in order.
   c. Dispatch based on `harness_type`:
      - `agent_behavior`: Construct Claude invocation with `--print` flag, specified role, and prompt. Capture output.
      - `web_test`: Start server (if `> Web Start:` available), navigate to URL, delegate to web test patterns.
      - `custom_script`: Execute the script at `script_path` with `--write-results`.
   d. Evaluate assertions against captured output (regex match for each pattern).
   e. If fixture was checked out, clean up via `fixture cleanup`.
3. Write enriched `tests.json` to `tests/<feature_name>/tests.json` with:
   - Standard fields: `status`, `passed`, `failed`, `total`.
   - Per-detail enriched fields: `scenario_ref`, `expected` (from assertion context), `actual_excerpt`, `assertion_tier`.
4. Exit with 0 if all assertions passed, non-zero otherwise.

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
     PASS  cdd_startup (8/8)

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

QA authors scenario files one feature at a time during `/pl-regression` author mode:

1. Read the feature spec and its `### Regression Testing` section (or `## Regression Guidance`).
2. Evaluate fixture needs per the fixture integration protocol (Section 2.10.1).
3. Write the scenario JSON file to `tests/qa/scenarios/<feature_name>.json`.
4. Commit the scenario file: `git commit -m "qa(<feature>): author regression scenario"`.
5. Print progress: `"Authored 3/8 scenarios. 5 remaining."`.
6. Move to next feature.

**Discovery heuristic (which features need authoring):**

- Feature has `### Regression Testing` section or `## Regression Guidance` section or `> Web Test:` metadata.
- Builder status is DONE (implementation exists to test against).
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

1. Does the `### Regression Testing` section reference fixture tags?
   - Yes: Check if tags exist via `fixture list`. Tags exist -> use them in scenario JSON. Tags missing -> flag for Builder to create (Critic handles this).
2. No explicit fixture tags, but scenario needs controlled state?
   - Simple state (single config, no git history): Use inline `setup_commands` in the scenario JSON.
   - Complex state (elaborate git history, multiple branches, config combinations): Suggest a remote fixture repo. Record the recommendation in `tests/qa/fixture_recommendations.md` (see `features/test_fixture_repo.md` Section 2.12).

### 2.11 Builder Feedback Protocol

When the Builder encounters regression test failures, it follows this triage:

**Code bug:** Builder fixes the application code (existing pattern from Section 2.4).

**Broken test scenario:** Builder creates a `[BUG]` discovery on the feature with:

- `Action Required: QA` -- routes to QA, not back to Builder.
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

**Critic routing:** The Critic recognizes `Action Required: QA` on BUG discoveries and routes them to the QA column instead of the Builder column. This prevents the Builder from seeing its own feedback as a new action item.

### 2.12 Agent Handoff Protocol

Each agent session that performs regression work MUST end with explicit, actionable instructions telling the human exactly what to do next. The human is the orchestrator between agent sessions and needs clear routing instructions.

**QA -> Human (after authoring scenarios):**

```
Regression scenarios authored: N features.

NEXT STEPS:
  1. Run regression tests:
         ./tests/qa/run_all.sh
  2. When tests finish, launch Builder to process results and fix failures.
  3. After Builder fixes, re-run tests:
         ./tests/qa/run_all.sh
  4. When all tests pass, launch QA to process final results.
```

**QA -> Human (harness runner framework missing):**

```
Cannot author regression scenarios -- the harness runner framework
has not been built yet.

NEXT STEP:
  Launch Builder with --qa flag:
      Set PURLIN_BUILDER_QA=true (or /pl-agent-config -> qa_mode: true)
      Then launch Builder -- it will build the harness runner framework.
  After Builder finishes, re-run QA to author scenarios.
```

**QA -> Human (fixtures needed but missing):**

```
N features need fixture repos before regression scenarios can be authored.
Recorded recommendations in tests/qa/fixture_recommendations.md.

NEXT STEP:
  Launch Builder with --qa flag:
      Set PURLIN_BUILDER_QA=true (or /pl-agent-config -> qa_mode: true)
      Tell it: "Create fixture tags for features listed in
      tests/qa/fixture_recommendations.md"
  After Builder finishes, re-run QA to continue authoring.
```

**Builder -> Human (after building harness runner framework):**

```
Harness runner framework built:
  tools/test_support/harness_runner.py
  tools/test_support/run_regression.sh

NEXT STEP:
  Launch QA to author regression scenarios.
  QA will create scenario files in tests/qa/scenarios/ and
  generate tests/qa/run_all.sh for you to execute.
```

**Builder -> Human (after processing regression failures):**

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

**Builder -> Human (after creating fixture tags):**

```
Created fixture tags for N features in .purlin/runtime/fixture-repo.

NEXT STEP:
  Launch QA to continue regression scenario authoring.
  QA will use the new fixtures automatically.
```

These handoff messages are mandatory -- they are a required part of each agent's session conclusion protocol when regression work was performed.

---

## 3. Scenarios

### Automated Scenarios

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
    When the QA agent invokes the regression skill
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

    Given a harness writes tests.json with enriched fields
    When the result file is read
    Then each detail entry contains scenario_ref with feature path and scenario name
    And failed entries contain expected and actual_excerpt fields

#### Scenario: Staleness detection prioritizes re-testing

    Given feature A has tests.json from 2 hours ago and source modified 1 hour ago
    And feature B has tests.json from 1 hour ago and no source modifications
    When the QA skill computes the eligible list
    Then feature A appears first with a STALE indicator
    And feature B does not appear in the eligible list

#### Scenario: Shallow assertion suite flagged when majority are Tier 1

    Given a harness writes tests.json with 10 detail entries
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
    And enriched tests.json is written with scenario_ref and assertion_tier

#### Scenario: Harness runner handles web_test harness type

    Given a scenario JSON file with harness_type "web_test"
    And the scenario specifies a web_test_url
    When the harness runner processes the scenario file
    Then the web test pattern is invoked against the specified URL
    And enriched tests.json is written with pass/fail results

#### Scenario: Harness runner falls back to custom_script

    Given a scenario JSON file with harness_type "custom_script"
    And the scenario specifies a script_path to a QA-authored script
    When the harness runner processes the scenario file
    Then the script at script_path is executed with --write-results
    And the script's tests.json output is consumed as the result

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
    When the QA agent enters author mode via /pl-regression
    Then the feature spec is read
    And a scenario JSON file is written to tests/qa/scenarios/<feature_name>.json
    And the file is committed
    And progress is printed showing authored count vs total

#### Scenario: Builder flags broken scenario via discovery

    Given the Builder processes regression results
    And a test failure is caused by a stale assertion (not a code bug)
    When the Builder creates a BUG discovery
    Then the discovery title includes "test-scenario"
    And Action Required is set to "QA"
    And the discovery body includes scenario_ref and actual_excerpt
    And the Critic routes this to the QA column

#### Scenario: Harness runner writes enriched tests.json

    Given the harness runner has executed all scenarios in a JSON file
    When it writes the tests.json output
    Then each detail entry includes scenario_ref with feature path and scenario name
    And each entry includes assertion_tier from the scenario's assertion tier field
    And failed entries include expected and actual_excerpt fields
    And the standard status, passed, failed, total fields are present

### Manual Scenarios (Human Verification Required)

None.

## Regression Guidance
- Watch mode: trigger file consumed and deleted after execution
- Timeout enforcement: per-execution 300s default, configurable
- Result file written atomically with correct exit code and timing
- Generic dispatch: runner works with any harness following --write-results convention
- Declarative scenarios: JSON files in tests/qa/scenarios/ consumed by framework harness runner
- Meta-runner: discovers and runs all scenario files, continues past failures
- Agent handoff: every regression agent session ends with explicit next-step instructions
