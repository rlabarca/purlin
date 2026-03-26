# Feature: Status Check

> Label: "Agent Skills: Common: /pl-status Status Check"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

A shared skill available to all roles that wraps `scan.sh` to display the current CDD project state. Shows feature counts by lifecycle status (TODO/TESTING/COMPLETE), role-specific action items sorted by priority with explanatory reasons, and open discoveries or tombstones requiring attention. Includes role-filtered shortcut mode and PM-specific uncommitted changes detection.

---

## 2. Requirements

### 2.1 Shared Access

- The command is available to all roles (PM, Engineer, QA, PM).

### 2.2 Core Output

- Run `scan.sh` and summarize: feature counts by status, role-specific action items (highest priority first with reasons), and open discoveries or tombstones.
- Tombstone files (features with `tombstone: true` in scan output) MUST be surfaced as Engineer work items with highest priority — tombstones are processed before regular feature work.

### 2.3 Role-Filtered Shortcut

- If the agent knows its role, use `scan.sh <role>` for a filtered view.

### 2.4 Status Value Reference

- Display status meanings per role (PM: DONE/TODO; Engineer: DONE/TODO/FAIL/BLOCKED/INFEASIBLE; QA: CLEAN/TODO/FAIL/DISPUTED/N/A).

### 2.5 QA-Specific: Regression and Smoke Status

- **Regression status:** Features with `regression_status` of STALE or FAIL in scan results MUST appear as QA work items with the reason `"regression STALE"` or `"regression FAIL"` and the hint `"Run /pl-regression to update."`.
- **Smoke candidates:** Read `smoke_candidates` from scan results. If non-empty, display after QA work items as an informational block showing feature name and dependent count. No action required — QA can promote via `/pl-smoke`.

### 2.6 PM-Specific: Uncommitted Changes Check

- After standard output, if PM role: check for uncommitted changes in PM-owned files.
- Present summary of changes grouped by type (new, modified, deleted).
- Propose commit message and ask user for confirmation.
- Non-PM-owned files are noted but not acted upon.

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

    Given an Engineer agent session
    When /pl-status uses --role builder
    Then only Engineer-relevant features and action items are shown

#### Scenario: PM sees uncommitted changes check

    Given a PM agent session
    And features/new_spec.md has uncommitted changes
    When /pl-status completes
    Then the output includes the uncommitted changes summary
    And a commit message is proposed

#### Scenario: QA section shows regression failures with hint

    Given a feature has regression_status "FAIL" in scan results
    When /pl-status is invoked
    Then the QA work items include the feature with reason "regression FAIL"
    And the hint "Run /pl-regression to update" is shown

#### Scenario: QA section shows smoke candidates

    Given scan results contain smoke_candidates with "hub_feature" (4 dependents)
    When /pl-status is invoked
    Then the output includes "Smoke candidates (unclassified):"
    And "hub_feature — 4 dependents" is shown

### QA Scenarios

None.
