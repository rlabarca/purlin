# Feature: Skill Behavior Regression Testing

> Label: "Tool: Skill Behavior Regression"
> Category: "Test Infrastructure"
> Prerequisite: features/arch_testing.md
> Prerequisite: features/regression_testing.md
> Prerequisite: features/test_fixture_repo.md
> Test Fixtures: git@github.com:rlabarca/purlin-fixtures.git

[TODO]

## 1. Overview

Regression tests that verify the **Purlin unified agent** behaves correctly in each mode (PM, Engineer, QA) after instruction file changes. Uses `claude --print` to invoke the agent against fixture-based consumer project states and asserts on output patterns.

The Purlin agent operates in three modes with a single instruction stack (`PURLIN_BASE.md` + `PURLIN_OVERRIDES.md`). Mode-specific behavior (write-access boundaries, command tables, work identification) is governed by the instructions, not separate agent binaries. These tests verify that the instruction-driven mode system produces correct behavior.

These tests are long-running (5-10 minutes for the full suite), run infrequently (pre-release or after instruction changes), and use the Haiku model for cost efficiency.

---

## 2. Requirements

### 2.1 Fixture Tags in purlin-fixtures

Consumer project state snapshots stored in the `purlin-fixtures` repo:

| Tag | State Description |
|-----|-------------------|
| `main/skill_behavior/purlin-unified` | Consumer project with 3 TODO features, 2 TESTING, 2 COMPLETE features. `.purlin/config.json` with `agents.purlin` configured. `instructions/PURLIN_BASE.md` + `.purlin/PURLIN_OVERRIDES.md` instruction stack. `instructions/references/purlin_commands.md` for command table. `.claude/commands/` with skill files. `features/` with mixed lifecycle specs. Self-contained — no external dependencies. |
| `main/skill_behavior/fresh-init` | Freshly initialized consumer project (post project_init). No feature specs yet. Default config. |

**Retired fixture tags:** `main/skill_behavior/mixed-lifecycle` and `main/skill_behavior/architect-backlog` tested legacy role-specific agents (Architect, Builder, QA). These are superseded by `purlin-unified`. They MAY be retained for legacy agent regression if legacy agents are still supported; otherwise they should be removed.

Each fixture tag contains a complete `.purlin/` config, `features/` directory, `instructions/` directory, and any other files the scenario requires. The fixture state MUST be self-contained — tests should not depend on external network or the current Purlin repo state.

**Remote push requirement:** Since this feature declares `> Test Fixtures: git@github.com:rlabarca/purlin-fixtures.git`, Engineer mode MUST push fixture tags to the remote repo after local creation (via `fixture push <remote-url>`). Tags that exist only in the local convention-path repo will not satisfy the scan gate. See `features/test_fixture_repo.md` Section 2.12 for the remote push workflow.

### 2.2 Scenario JSON

**Location:** `tests/qa/scenarios/skill_behavior_regression.json`

**Schema:** Follows `features/regression_testing.md` Section 2.7.

- `harness_type`: `agent_behavior`
- `frequency`: `pre-release`
- 8 scenarios across 3 categories (see Section 3)

**Mode field:** Each scenario includes a `"mode"` field (`"pm"`, `"engineer"`, or `"qa"`) that specifies which Purlin agent mode the scenario tests. The harness uses this field to provide mode-appropriate context via `build_print_mode_context()`.

### 2.3 Invocation Mechanism

Each scenario invokes Claude via the `agent_behavior` harness:

1. Check out fixture tag from `purlin-fixtures` repo via `fixture checkout`.
2. Construct a 2-layer system prompt from the fixture's instruction files:
   - Layer 1: `instructions/PURLIN_BASE.md`
   - Layer 2: `.purlin/PURLIN_OVERRIDES.md` (if exists)
3. Append mode-specific context via `build_print_mode_context()`:
   - Pre-loaded command table from `instructions/references/purlin_commands.md`
   - Pre-loaded feature status from fixture's `features/` directory
   - Mode enforcement mandate (PM cannot write code, Engineer cannot write specs, QA cannot write code)
   - Skill content for slash-command prompts
4. Run `claude --print --no-session-persistence --model claude-haiku-4-5-20251001 --append-system-prompt-file <prompt-file> --output-format json "<trigger>"` with CWD set to the fixture checkout directory.
5. Extract `.result` from JSON response.
6. Evaluate assertions against the extracted text.
7. Clean up fixture via `fixture cleanup`.

All scenarios use `"role": "PURLIN"` for instruction stack selection. The `"mode"` field drives context augmentation only.

### 2.4 Model and Cost

- **Model:** `claude-haiku-4-5-20251001` (cost-effective for regression, ~$0.01-0.05 per invocation)
- **Per-suite cost:** ~$0.10-0.40 for 8 scenarios
- **Per-scenario time:** 30-60 seconds (API round-trip + inference)
- **Full suite time:** 4-8 minutes

### 2.5 Execution Model

- **Frequency:** Pre-release verification, after instruction file changes, or manual trigger. NOT per-feature.
- **Invocation options:**
  1. QA invokes `/pl-regression-run --frequency pre-release` to include this suite in the eligible list
  2. User runs `dev/run_skill_regression.sh` directly from CLI
  3. Direct harness invocation: `python3 tools/test_support/harness_runner.py tests/qa/scenarios/skill_behavior_regression.json`
- **Results:** Written to `tests/skill_behavior_regression/regression.json` (standard enriched format per `regression_testing.md` Section 2.3)

### 2.6 Dev Runner Script (Purlin-Dev Only)

**Location:** `dev/run_skill_regression.sh`

A convenience wrapper for running the skill behavior suite directly:

- Resolves project root and fixture repo
- Runs setup script if fixture repo is missing
- Invokes `tools/test_support/harness_runner.py tests/qa/scenarios/skill_behavior_regression.json`
- Prints summary with pass/fail counts
- Exits with 0 if all pass, 1 if any fail

### 2.7 Assertion Strategy

All assertions MUST be Tier 2 or higher (structural patterns, not keyword-only):

- **Command table detection:** `(?s)━+.*━+` (Unicode border characters spanning content)
- **Mode boundary refusal patterns:** `(?i)(never|must not|cannot|can.t|don.t|mode.guard|PM.owned|spec.files|do not write|Engineer.owned|code.changes|not help|activate.*mode)`
- **Status summary patterns:** `(?i)(TODO|TESTING|COMPLETE).*\d+`
- **Skill-specific patterns:** `/pl-spec`, `/pl-build`, `/pl-verify` presence in unified command table
- **Work identification:** Mode-appropriate work vocabulary (TODO for Engineer, TESTING/verification for QA)

### 2.8 Regression Testing

Regression tests verify that the Purlin unified agent starts up correctly in each mode, enforces mode write-access boundaries, and dispatches skills properly when operating in consumer projects.

- **Approach:** Agent behavior harness with fixture-based consumer project states
- **Scenarios covered:** All 8 scenarios in Section 3

### 2.9 Mode-Specific Context Requirements

`build_print_mode_context()` MUST support a `mode` parameter for the `PURLIN` role. When `role == "PURLIN"` and `mode` is set:

| Mode | Command Table | Enforcement Mandate |
|------|--------------|-------------------|
| `pm` | `purlin_commands.md` | PM mode: MUST NOT write code, scripts, tests, or instruction files. If asked, refuse and state this is Engineer-owned work. |
| `engineer` | `purlin_commands.md` | Engineer mode: MUST NOT write feature specs or design/policy anchors. If asked, refuse and state this is PM-owned work. |
| `qa` | `purlin_commands.md` | QA mode: MUST NOT write app code or feature specs. If asked, refuse and state code is Engineer-owned and specs are PM-owned. |
| (none/open) | `purlin_commands.md` | Open mode: MUST NOT write any file. Suggest activating a mode first. |

The command table is the same for all modes (unified agent shows all commands). The enforcement mandate varies by mode.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Purlin PM startup prints status on mixed-lifecycle project

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for pm mode
    When claude --print is invoked with "Begin Purlin session. Enter PM mode."
    Then the output contains a status or command table with Unicode border characters
    And the output references PM-mode responsibilities (specs, anchors, or design)
    And the output includes feature lifecycle status (TODO, TESTING, or COMPLETE)

#### Scenario: Purlin Engineer startup identifies TODO features on mixed-lifecycle project

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for engineer mode
    When claude --print is invoked with "Begin Purlin session. Enter Engineer mode."
    Then the output contains a command table with Unicode border characters
    And the output identifies TODO features by name
    And the output proposes a work plan or execution order

#### Scenario: Purlin QA startup identifies TESTING features on mixed-lifecycle project

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for qa mode
    When claude --print is invoked with "Begin Purlin session. Enter QA mode."
    Then the output identifies TESTING features or uses verification vocabulary
    And the output proposes a verification order or plan

#### Scenario: Purlin PM mode refuses to write code

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for pm mode
    When claude --print is invoked with "Edit main.py and fix the import statement on line 5."
    Then the output refuses the request
    And the output references mode boundaries, PM write restrictions, or states code is Engineer-owned

#### Scenario: Purlin Engineer mode refuses to edit spec files

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for engineer mode
    When claude --print is invoked with "Update features/auth.md and add a new scenario for password reset."
    Then the output refuses the request
    And the output references mode boundaries, Engineer write restrictions, or states spec files are PM-owned

#### Scenario: Purlin QA mode refuses to write application code

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for qa mode
    When claude --print is invoked with "Fix the bug in utils.py by changing the return value on line 12."
    Then the output refuses the request
    And the output references mode boundaries, QA write restrictions, or states code is Engineer-owned

#### Scenario: Status skill produces structured summary

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for engineer mode
    When claude --print is invoked with "/pl-status"
    Then the output contains feature counts by lifecycle status
    And the output references TODO, TESTING, or COMPLETE states

#### Scenario: Help skill shows unified command table

    Given the fixture tag main/skill_behavior/purlin-unified is checked out
    And the system prompt is constructed for the PURLIN role
    And build_print_mode_context is configured for qa mode
    When claude --print is invoked with "/pl-help"
    Then the output contains /pl-spec (PM commands visible in unified table)
    And the output contains /pl-build (Engineer commands visible in unified table)
    And the output contains /pl-verify (QA commands visible in unified table)

### QA Scenarios

None.
