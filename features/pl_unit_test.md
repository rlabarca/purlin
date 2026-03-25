# Feature: Unit Test Protocol

> Label: "Agent Skills: Engineer: /pl-unit-test Unit Test Protocol"
> Category: "Agent Skills: Engineer"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/arch_testing.md

[TODO]

## 1. Overview

Engineer mode's testing skill that enforces a rigorous quality rubric on all automated tests. Defines behavioral test requirements by feature type (Python tool, shell script, Claude skill, web UI), five named anti-patterns to guard against (prose inspection, structural presence, mock-dominated, tautological assertion, representative input neglect), a six-point quality rubric gate, and structured result reporting to `tests.json`.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by Engineer mode role.
- Non-Engineer agents MUST receive a redirect message.

### 2.2 The Cardinal Rule

- Grepping or reading source code to verify its presence is NOT testing.
- Tests MUST import, call, or execute the implementation and assert on its outputs.

### 2.3 Test Requirements by Feature Type

- Python tool features: import and call implementation functions, assert return values and side effects.
- Claude skill/command features: test the infrastructure the skill depends on (parsers, validators, state management).
- Shell script features: execute the script with controlled arguments, assert exit codes and stdout.
- Web UI features: interact with rendered DOM or API endpoints, assert response content and state changes.

### 2.4 Anti-Pattern Checklist

- **AP-1 (Prose Inspection):** Test reads documentation files and asserts string presence instead of calling implementation.
- **AP-2 (Structural Presence):** Test checks that a key exists without verifying its value.
- **AP-3 (Mock-Dominated):** Test mocks the implementation under test then asserts the mock was called.
- **AP-4 (Tautological Assertion):** Asserts something always true regardless of implementation correctness.
- **AP-5 (Representative Input Neglect):** Tests use toy data that does not resemble real inputs.

### 2.5 Quality Rubric Gate

All 6 checks MUST pass before `tests.json` is written:
1. DELETION TEST: If implementation were deleted, at least one test would fail.
2. BEHAVIORAL VERIFICATION: Every test imports, calls, or executes the implementation.
3. VALUE ASSERTIONS: Every test contains at least one value-verifying assertion.
4. ANTI-PATTERN FREE: All 5 AP checks pass.
5. REPRESENTATIVE INPUTS: Tests use realistic data shapes.
6. NO SELF-MOCKING: Mocks limited to external dependencies only.

### 2.6 Result Reporting

- `tests.json` MUST be produced by an actual test runner, never hand-written.
- Required fields: `status`, `passed`, `failed`, `total` with `total > 0`.
- Output location: `tests/<feature_name>/tests.json`.

### 2.7 Companion File Audit Record

- After rubric passes, record test quality audit in companion file with rubric score, test counts, AP scan status, and date.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer invocation

    Given a QA agent session
    When the agent invokes /pl-unit-test
    Then the command responds with a redirect message

#### Scenario: Cardinal rule rejects source-reading tests

    Given a test file that reads features/my_feature.md and asserts string presence
    When the quality rubric gate runs
    Then the test fails AP-1 (Prose Inspection) check
    And tests.json is not written

#### Scenario: Quality rubric blocks on mock-dominated test

    Given a test that mocks the implementation under test and asserts mock was called
    When the quality rubric gate runs
    Then the test fails AP-3 (Mock-Dominated) check
    And tests.json is not written until the test is fixed

#### Scenario: tests.json produced by actual test runner

    Given all 6 rubric checks pass
    When tests.json is written
    Then it contains status, passed, failed, and total fields
    And total is greater than 0
    And it was produced by a test runner, not hand-written

#### Scenario: Audit record written to companion file

    Given the rubric passes for feature_a
    When the audit record is written
    Then features/feature_a.impl.md contains a Test Quality Audit section
    And the section includes rubric score, test count, and date

### QA Scenarios

None.
