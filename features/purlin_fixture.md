# Feature: Test Fixture Reference

> Label: "Agent Skills: QA: purlin:fixture Test Fixture Reference"
> Category: "Agent Skills: QA"
> Prerequisite: test_fixture_repo.md

[Complete]

## 1. Overview

A shared skill available to all roles that provides the test fixture convention and lifecycle reference. QA mode has cross-mode access (setup-only): QA can invoke fixture commands for test setup but cannot modify application code. Covers when fixtures are needed, the three-tier fixture repo resolution, slug naming conventions, fixture-aware feature design guidance for Architects, fixture setup workflow for Builders, and fixture awareness for QA during regression authoring.

---

## 2. Requirements

### 2.1 Shared Access

- The command is available to all roles.

### 2.2 Role-Specific Guidance

- **Architects:** When to use fixtures, fixture tag section format, slug naming convention, user communication mandate.
- **Builders:** Fixture detection pre-flight, three-tier resolution, setup script creation, state construction guidance.
- **QA:** Fixture decision tree during regression authoring, fixture repo check, per-feature evaluation.

### 2.3 Fixture Lifecycle

- PM defines tags in spec -> Engineer creates setup script and fixture repo -> QA references tags in regression JSON -> Harness runner checks out tags at test time -> cleanup after each scenario.

---

## 3. Scenarios

### Unit Tests

#### Scenario: All roles can invoke the command

    Given any agent role
    When the agent invokes purlin:fixture
    Then the command executes without a role authorization error

#### Scenario: Content covers fixture lifecycle

    Given the skill is invoked
    When the output is presented
    Then it includes the fixture lifecycle from definition through cleanup

#### Scenario: Role-specific sections presented

    Given an Engineer agent invokes purlin:fixture
    When the output is presented
    Then it includes fixture detection pre-flight and setup workflow guidance

### QA Scenarios

None.
