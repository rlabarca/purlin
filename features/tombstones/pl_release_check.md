# Feature: Release Checklist Verification

> Label: "/pl-release-check Release Checklist Verification"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

[TODO]

## 1. Overview

The PM's release readiness skill that executes the CDD release checklist step by step. Verifies the Zero-Queue Mandate (all features DONE across PM, Engineer, and QA), checks the dependency graph for cycles, and works through each enabled release step in the project-specific sequence from `.purlin/release/config.json`.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the PM role.
- Non-PM agents MUST receive a redirect message.

### 2.2 Release Verification Steps

- Run `status.sh` to confirm current project state.
- Verify Zero-Queue Mandate: every feature must have `architect: "DONE"`, `builder: "DONE"`, and `qa` as `"CLEAN"` or `"N/A"`. List any blocking features.
- Check dependency graph for cycles via `dependency_graph.json`.
- Work through each enabled release step in the configured sequence.

### 2.3 Interactive Execution

- Present each step's status and ask for confirmation before proceeding to the next.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-PM invocation

    Given a Engineer agent session
    When the agent invokes /pl-release-check
    Then the command responds with a redirect message

#### Scenario: Zero-Queue Mandate lists blocking features

    Given feature_a has builder status TODO
    When the Zero-Queue Mandate is checked
    Then feature_a is listed as a release blocker

#### Scenario: Cycle detection flags circular dependencies

    Given the dependency graph contains a cycle
    When the graph is checked
    Then the cycle is reported as a release blocker

#### Scenario: Steps executed in configured order

    Given config.json defines steps A, B, C in that order
    When /pl-release-check runs
    Then step A is presented first, then B, then C

### QA Scenarios

None.
