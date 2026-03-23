# Feature: Release Step Execution

> Label: "/pl-release-run Release Step Execution"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

[TODO]

## 1. Overview

The Architect's skill for running a single release step from the project's checklist without executing the full sequence. Supports name-based step selection with partial matching, disabled step warning, and execution via agent_instructions or shell code. Resolves the fully merged release step list from global and local step definitions.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the Architect role.
- Non-Architect agents MUST receive a redirect message.

### 2.2 Step Resolution

- Merge `.purlin/release/config.json` with `global_steps.json` and `local_steps.json` to build the full step list.
- If argument provided: match against `friendly_name` (case-insensitive, partial match). Handle zero, one, or multiple matches.
- If no argument: display all steps numbered contiguously (enabled only). Disabled steps shown without number.

### 2.3 Step Execution

- Display step definition (name, source, description, code, agent_instructions).
- Warn if step is disabled.
- Execute via agent_instructions, code, or manual guidance as available.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Architect invocation

    Given a Builder agent session
    When the agent invokes /pl-release-run
    Then the command responds with a redirect message

#### Scenario: Partial name match selects correct step

    Given a step with friendly_name "Push to Remote Repository"
    When /pl-release-run is invoked with argument "push"
    Then that step is selected for execution

#### Scenario: Multiple matches prompts user choice

    Given steps "Push to Remote" and "Push to Wiki" both exist
    When /pl-release-run is invoked with argument "push"
    Then both matches are listed and user is asked to choose

#### Scenario: Disabled step shows warning

    Given step "sync_docs" has enabled: false
    When /pl-release-run selects that step
    Then a warning about disabled status is shown
    And explicit confirmation is required before execution

### QA Scenarios

None.
