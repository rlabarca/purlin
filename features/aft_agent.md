# Feature: AFT Agent Interaction Testing

> Label: "AFT Agent Interaction Testing"
> Category: "Automated Feedback Tests"
> Prerequisite: features/arch_automated_feedback_tests.md

[TODO]

## 1. Overview

The AFT:Agent pattern automates verification of agent interaction scenarios -- multi-turn
conversations where an agent presents findings, handles user responses, and takes actions.
Unlike AFT:Web (which scripts browser interactions) or builder unit tests (which verify
detection logic), AFT:Agent scripts the agent-human conversation flow itself using
`claude --print` with session-based multi-turn support.

This is a framework-level concept: any consumer project can use the AFT:Agent pattern to
verify its own agent interaction scenarios. The pattern is: fixture checkout, prompt
construction, multi-turn scripting, assertion, and structured result output.

---

## 2. Requirements

### 2.1 Feature Metadata Convention

Feature files MAY include a `> AFT Agent: <role>` blockquote metadata line (e.g.,
`> AFT Agent: architect`), placed alongside other `>` metadata (Label, Category,
Prerequisite). The role value indicates which agent role's interaction is being tested.

Manual scenarios annotated with `> AFT Agent:` metadata are eligible for automated agent
interaction testing. Non-annotated manual scenarios continue using `/pl-verify` (manual).

### 2.2 Core Pattern

An AFT:Agent test follows this sequence:

1. **Fixture checkout** -- Clone or checkout a fixture repo at a specific tag to establish
   a controlled project state.
2. **Prompt construction** -- Build the system prompt from the project's instruction stack,
   injecting any role-specific or step-specific instructions (e.g., release step
   `agent_instructions` from `tools/release/global_steps.json`).
3. **Multi-turn scripting** -- Execute one or more turns using `claude --print` with
   `--session-id` for session continuity. Each turn sends a user message and captures the
   agent's response.
4. **Assertion** -- Verify the agent's response contains expected content (keywords, table
   structures, action confirmations) or does not contain prohibited content.
5. **Result output** -- Write structured pass/fail results to `tests/<feature>/tests.json`
   in the standard test result format.

### 2.3 Single-Turn vs Multi-Turn

- **Single-turn tests** verify that the agent produces the correct output given a single
  prompt (e.g., "execute this release step" -> agent presents a findings table). These use
  a single `claude --print` invocation.
- **Multi-turn tests** verify conversation flow where the agent's second response depends
  on a scripted user reply to the first response (e.g., agent presents options -> user
  selects one -> agent takes action). These use `--session-id` for session continuity and
  `--resume` for subsequent turns.

### 2.4 Model Selection

AFT:Agent tests default to Haiku for cost efficiency. The model is overridable via a
`--model` flag on the test harness. The test assertions must be model-agnostic -- they
verify structural output (presence of tables, keywords, action confirmations), not exact
phrasing.

### 2.5 Fixture Integration

AFT:Agent tests use the same fixture repo infrastructure as builder tests
(`features/test_fixture_repo.md`). Each test scenario declares the fixture tag it requires
in the feature spec's fixture tag table. The test harness checks out the fixture at the
declared tag before running the test.

For consumer project simulation (e.g., testing `/pl-update-purlin`), a separate external
fixture repo may be used. The feature spec declares this via `> Test Fixtures: <url>`
metadata.

### 2.6 Discovery Feedback

When an AFT:Agent test fails, the harness writes a `[BUG]` entry to the relevant feature's
discovery sidecar file (`features/<name>.discoveries.md`), following the same convention as
AFT:Web failures.

### 2.7 Harness Implementation

The test harness is a shell script that:

- Accepts `--model <model>` to override the default (haiku)
- Accepts `--scenario <name>` to run a single scenario instead of the full suite
- Outputs progress to stderr and results to stdout
- Writes `tests/<feature>/tests.json` result files
- Returns exit code 0 if all tests pass, 1 if any fail

The harness script location and naming is project-specific. In the Purlin framework repo,
it lives at `dev/test_agent_interactions.sh` (Purlin-dev-specific, not distributed to
consumers). Consumer projects build their own harness following this pattern.

### 2.8 Prompt Construction for Release Steps

Release step agent interaction tests require injecting the step's `agent_instructions`
from `tools/release/global_steps.json` (or `.purlin/release/local_steps.json` for local
steps) into the system prompt. The harness provides a `construct_release_prompt()` function
that assembles the full prompt from:

1. The project's 4-layer instruction stack (base + overrides)
2. The specific step's `agent_instructions` field
3. Any fixture-specific context

### 2.9 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/release_instruction_audit/base-conflict` | Override contradicts base rule |
| `main/release_doc_consistency_check/coverage-gaps` | README missing feature coverage |
| `main/release_doc_consistency_check/new-section-needed` | Gap requires new ## heading |
| `main/release_record_version_notes/no-tags` | Repo with commits, no release tags |
| `main/release_record_version_notes/prior-tag` | Repo with v1.0.0 tag + later commits |
| `main/release_record_version_notes/no-releases-heading` | README lacks ## Releases |
| `main/release_submodule_safety_audit/warning-only` | json.load WARNING, no CRITICALs |
| `main/release_instruction_audit/base-error` | Base instruction file contains stale path |
| `main/release_instruction_audit/clean` | All overrides consistent with base layer |
| `main/release_doc_consistency_check/clean` | README fully covers all features |
| `main/release_record_version_notes/clean` | Clean repo with valid tags and Releases heading |
| `main/release_submodule_safety_audit/clean` | No submodule safety violations |
| *(Builder/QA role fixtures — placeholder)* | |
| `main/builder_*` | Builder role test fixtures (Builder creates) |
| `main/qa_*` | QA role test fixtures (Builder creates) |

### 2.10 Assertion Quality Tiers

AFT:Agent assertions are classified into three tiers of increasing rigor:

| Tier | Name | Description | Example |
|------|------|-------------|---------|
| 1 | Keyword Presence | Asserts that one or more keywords appear in the output. Passes on incidental matches. | `assert_contains "$output" "table\|findings"` |
| 2 | Specific Finding | Asserts a specific finding, value, or structural element that the agent must have actually detected. | `assert_contains "$output" "BUILDER_BASE.md"` (the actual file with the issue) |
| 3 | State Verification | Inspects filesystem or project state after the agent acts, verifying the agent produced a concrete artifact or side effect. | Check that a committed file contains the expected fix content. |

**Rules:**

- Every scenario MUST include at least one Tier 2 or Tier 3 assertion. Tier 1 alone is
  insufficient -- it passes on incidental keyword matches and does not verify the agent
  actually detected the intended problem.
- Tier 3 requires inspecting state after `claude --print` completes. Because `claude --print`
  does not execute tool calls (no file writes), Tier 3 assertions verify the agent's *stated
  intent* to write specific content (e.g., asserting the output contains a proposed commit
  message or file diff), not actual filesystem changes. If future harness capabilities enable
  sandboxed execution, Tier 3 can verify actual file state.

### 2.11 Multi-Role Coverage

The AFT:Agent test suite MUST include scenarios for at least two distinct agent roles to verify
that the harness and prompt construction work across role boundaries. The initial role is
Architect (via release step testing). Additional roles:

- **Builder:** At least one scenario testing Builder-role agent behavior against a Builder
  fixture. Fixture tags follow the `main/builder_*` convention in the tag table (Section 2.9).
- **QA:** At least one scenario testing QA-role agent behavior against a QA fixture. Fixture
  tags follow the `main/qa_*` convention in the tag table (Section 2.9).

The Builder creates the role-specific fixtures and scenarios. The harness's
`construct_release_prompt()` function already accepts a role parameter; multi-role coverage
validates that this parameter produces correct prompt construction for each role.

### 2.12 Negative (Canary) Tests

The test suite MUST include at least one negative scenario per tested release step category.
A negative test:

1. Checks out a **clean** fixture (one where the release step should find no problems).
2. Runs the agent against the clean fixture with the same prompt construction as the positive
   test.
3. Asserts that **prohibited patterns are absent** -- the agent should NOT report problems,
   contradictions, stale paths, or action items that do not exist.

Negative tests prevent false positives: if a positive test's assertion pattern also matches on
a clean fixture, the assertion is too loose (Tier 1 problem). Clean fixture tags already exist
in the tag table (Section 2.9) with the `/clean` suffix convention.

### 2.13 Multi-Turn Depth

The test suite MUST include at least one scenario with three or more turns. Multi-turn depth
tests verify decision chains where turn N depends on accumulated context from turns 1 through
N-1. This catches regressions in session state management and context accumulation that
single-turn and two-turn tests miss.

A 3+ turn scenario follows this structure:

1. **Turn 1:** Agent presents initial findings or options.
2. **Turn 2:** User selects an option or asks for detail; agent responds with refined output.
3. **Turn 3:** User confirms action or requests further refinement; agent's response must
   reflect accumulated context from both prior turns.

The harness uses `--session-id` and `--resume` as specified in Section 2.3.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Single-turn test produces structured output
    Given a fixture repo checked out at a tag with a known project state
    And a system prompt constructed from the instruction stack with release step instructions
    When the harness executes a single-turn test via `claude --print`
    Then the agent's response is captured as a string
    And the harness asserts expected content is present
    And writes a PASS or FAIL result to `tests/<feature>/tests.json`

#### Scenario: Multi-turn test resumes session correctly
    Given a fixture repo checked out at a tag with a known project state
    And a session ID generated for the test
    When the harness executes turn 1 via `claude --print --session-id <id>`
    And the agent responds with findings or a prompt for user input
    And the harness executes turn 2 via `claude --print --resume <id>` with a scripted response
    Then the agent's second response reflects the scripted user input
    And the harness asserts the correct action was taken or reported

#### Scenario: Model override accepted
    Given the harness is invoked with `--model sonnet`
    When it executes a test scenario
    Then `claude --print` is called with `--model sonnet` instead of the default haiku

#### Scenario: Single scenario selection
    Given the harness is invoked with `--scenario instruction-audit-halt`
    When it runs
    Then only the specified scenario executes
    And all other scenarios are skipped

#### Scenario: Fixture tag missing causes test skip
    Given a test scenario declares fixture tag `main/feature/slug`
    And that tag does not exist in the fixture repo
    When the harness attempts to run the scenario
    Then the scenario is reported as SKIP (not FAIL)
    And the skip reason includes the missing tag name

#### Scenario: Negative test detects no false positives on clean fixture
    Given a fixture repo checked out at a clean tag (e.g., `main/release_instruction_audit/clean`)
    And the system prompt is constructed with the same release step instructions as the positive test
    When the harness executes a single-turn test via `claude --print`
    Then the agent's response does NOT contain problem indicators (contradictions, stale paths, errors)
    And the harness asserts prohibited patterns are absent
    And writes a PASS result to `tests/<feature>/tests.json`

#### Scenario: Tier 2 assertion verifies specific finding
    Given a fixture repo checked out at a tag with a known defect
    And the system prompt includes the relevant release step instructions
    When the harness executes a single-turn test via `claude --print`
    Then the harness asserts the agent's response contains the specific defect identifier
    (e.g., the exact file name, path, or contradiction text -- not just generic keywords)
    And the assertion would NOT pass on a clean fixture with no defects

#### Scenario: Multi-turn test with three or more turns
    Given a fixture repo checked out at a tag with a known project state
    And a session ID generated for the test
    When the harness executes turn 1 via `claude --print --session-id <id>`
    And the agent responds with findings or options
    And the harness executes turn 2 via `claude --print --resume <id>` with a scripted selection
    And the agent responds with refined output based on the selection
    And the harness executes turn 3 via `claude --print --resume <id>` with a scripted confirmation
    Then the agent's third response reflects accumulated context from turns 1 and 2
    And the harness asserts the final response contains expected outcome content

#### Scenario: State verification after agent action
    Given a fixture repo checked out at a tag with a known defect
    And the system prompt includes release step instructions that direct the agent to take action
    When the harness executes a multi-turn test where the agent states intent to fix the defect
    Then the harness asserts the agent's output contains specific proposed changes
    (e.g., a proposed commit message, file diff, or explicit description of the fix)
    And the proposed changes reference the correct file and defect

### Manual Scenarios (Human Verification Required)

None.
