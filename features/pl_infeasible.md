# Feature: Infeasible Escalation

> Label: "Agent Skills: Engineer: /pl-infeasible Infeasible Escalation"
> Category: "Agent Skills: Engineer"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/impl_notes_companion.md

[TODO]

## 1. Overview

Engineer mode's escalation skill for halting work on a feature that cannot be implemented as specified. Records an `[INFEASIBLE]` entry with detailed rationale in the companion file, commits it, and runs the Critic to surface the escalation as a CRITICAL-priority PM action item. No code is implemented for infeasible features until PM mode revises the spec.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by Engineer mode role.
- Non-Engineer agents MUST receive a redirect message.

### 2.2 Escalation Workflow

- Read `features/<name>.md` to confirm the feature and its current state.
- Record `[INFEASIBLE]` entry in companion file with detailed rationale.
- Commit with message including `[INFEASIBLE]` tag and brief reason.
- Run `status.sh` to surface the entry in the Critic report.

### 2.3 Constraints

- Do NOT implement any code for the feature.
- PM mode MUST revise the spec before work can resume.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer invocation

    Given a PM agent session
    When the agent invokes /pl-infeasible
    Then the command responds with a redirect message

#### Scenario: INFEASIBLE entry recorded in companion file

    Given Engineer mode cannot implement feature_a as specified
    When /pl-infeasible is invoked for feature_a
    Then features/feature_a.impl.md contains an [INFEASIBLE] entry
    And the entry includes detailed rationale

#### Scenario: No code is implemented

    Given /pl-infeasible is invoked for feature_a
    When the escalation workflow completes
    Then no implementation code exists for feature_a

#### Scenario: Critic surfaces INFEASIBLE as CRITICAL

    Given the INFEASIBLE entry is committed
    When status.sh runs
    Then the Critic report shows a CRITICAL-priority PM action item for feature_a

### QA Scenarios

None.
