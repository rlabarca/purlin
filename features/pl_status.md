# Feature: Status Check

> Label: "Agent Skills: Common: /pl-status Status Check"
> Category: "Agent Skills: Common"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A shared skill available to all roles that wraps `status.sh` to display the current CDD project state. Shows feature counts by lifecycle status (TODO/TESTING/COMPLETE), role-specific action items sorted by priority with explanatory reasons, and open discoveries or tombstones requiring attention. Includes role-filtered shortcut mode and Architect-specific uncommitted changes detection.

---

## 2. Requirements

### 2.1 Shared Access

- The command is available to all roles (Architect, Builder, QA, PM).

### 2.2 Core Output

- Run `status.sh` and summarize: feature counts by status, role-specific action items (highest priority first with reasons), and open discoveries or tombstones.

### 2.3 Role-Filtered Shortcut

- If the agent knows its role, use `status.sh --role <role>` for a filtered view.

### 2.4 Status Value Reference

- Display status meanings per role (Architect: DONE/TODO; Builder: DONE/TODO/FAIL/BLOCKED/INFEASIBLE; QA: CLEAN/TODO/FAIL/DISPUTED/N/A).

### 2.5 Architect-Specific: Uncommitted Changes Check

- After standard output, if Architect role: check for uncommitted changes in Architect-owned files.
- Present summary of changes grouped by type (new, modified, deleted).
- Propose commit message and ask user for confirmation.
- Non-Architect-owned files are noted but not acted upon.

---

## 3. Scenarios

### Unit Tests

#### Scenario: All roles can invoke the command

    Given any agent role
    When the agent invokes /pl-status
    Then the command executes without a role authorization error

#### Scenario: Output includes feature counts by status

    Given a project with 3 TODO, 2 TESTING, and 5 COMPLETE features
    When /pl-status is invoked
    Then the output shows the correct counts for each status

#### Scenario: Role-filtered view shows only relevant items

    Given a Builder agent session
    When /pl-status uses --role builder
    Then only Builder-relevant features and action items are shown

#### Scenario: Architect sees uncommitted changes check

    Given an Architect agent session
    And features/new_spec.md has uncommitted changes
    When /pl-status completes
    Then the output includes the uncommitted changes summary
    And a commit message is proposed

### QA Scenarios

None.
