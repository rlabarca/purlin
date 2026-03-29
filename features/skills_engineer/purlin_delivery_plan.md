# Feature: Delivery Plan

> Label: "Agent Skills: Engineer: purlin:delivery-plan Delivery Plan"
> Category: "Agent Skills: Engineer"

[TODO]

## 1. Overview

Engineer mode's pipeline delivery skill that assesses implementation scope and creates a work plan for coordinated multi-feature, multi-mode delivery. Replaces size-based phasing with a flat, priority-ordered feature list with per-feature pipeline status tracking, verification groups for cross-feature regression testing, and support for cross-mode sub-agent dispatch. The work plan is the coordination artifact that enables features to progress through PM → Engineer → QA stages independently, with parallel execution via worktrees.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by Engineer mode role.
- Non-Engineer agents MUST receive a redirect message.

### 2.2 Existing Plan Review

- If `.purlin/work_plan.md` exists: display the pipeline status table showing each feature's current stage and per-mode status. Offer to adjust the plan.

### 2.3 New Plan Creation

- Run `scan.sh` to get current feature status.
- Read `dependency_graph.json` and build a prerequisite map.
- Assess scope: if 2+ features need work across any role (PM, Engineer, or QA), recommend creating a work plan. Single-feature work does not need a plan.

### 2.4 Feature Ordering

- Features ordered by dependency (foundations first), then by pipeline readiness (features closest to completion dispatched first).
- Validation gate: verify no dependency cycles in the feature ordering before committing.

### 2.5 Verification Group Assignment

- Analyze `dependency_graph.json` interaction density to assign features to verification groups.
- Features sharing data models, APIs, or UI components → same verification group.
- Features with no shared interaction surface → singleton verification group.
- B2 cross-feature regression testing runs per-verification-group after all member features complete Engineer stage.

### 2.6 Pipeline Status Initialization

- For each feature, determine the initial pipeline stage:
  - Features with no spec (`pm: TODO` or spec missing) → stage `pm`, PM column PENDING.
  - Features with complete spec and `engineer: TODO` → stage `engineer`, PM column COMPLETE, Engineer column PENDING.
  - Features with `engineer: TESTING` → stage `qa`, Engineer column COMPLETE, QA column PENDING.
  - Features already `[Complete]` → stage `complete`, all columns COMPLETE.
  - PM column set to SKIPPED for features with existing, unchanged specs that don't need PM work.

### 2.7 Canonical Format

- Work plan file uses the format defined in `references/phased_delivery.md` Section 10.7.3: pipeline status table with Feature, Stage, PM, Engineer, QA, V-Group, and Notes columns, plus verification group definitions and amendments log.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer invocation

    Given a PM agent session
    When the agent invokes purlin:delivery-plan
    Then the command responds with a redirect message

#### Scenario: Existing work plan displays pipeline status

    Given .purlin/work_plan.md exists with 3 features at different stages
    When purlin:delivery-plan is invoked
    Then the pipeline status table is displayed
    And each feature's current stage and per-mode status are shown

#### Scenario: Scope assessment recommends work plan for multi-feature work

    Given 3 features in TODO state across PM and Engineer roles
    When purlin:delivery-plan assesses scope
    Then it recommends creating a work plan

#### Scenario: Single feature does not trigger work plan

    Given 1 feature in TODO state
    When purlin:delivery-plan assesses scope
    Then it does not recommend a work plan

#### Scenario: Dependency validation catches cycle

    Given a proposed plan where feature B depends on feature A
    And feature A is ordered after feature B
    When the validation gate runs
    Then the ordering is corrected before committing

#### Scenario: Verification groups assigned by interaction density

    Given features auth_flow and session_mgmt share the auth data model
    And feature settings has no shared interaction surface
    When purlin:delivery-plan creates a plan
    Then auth_flow and session_mgmt are in the same verification group
    And settings is in a singleton verification group

#### Scenario: Pipeline stage initialization from scan state

    Given feature_a has pm: COMPLETE and engineer: TODO
    And feature_b has no spec (pm: TODO)
    And feature_c has engineer: TESTING
    When purlin:delivery-plan creates a plan
    Then feature_a starts at stage "engineer" with PM COMPLETE
    And feature_b starts at stage "pm" with PM PENDING
    And feature_c starts at stage "qa" with Engineer COMPLETE

#### Scenario: Existing specs marked SKIPPED in PM column

    Given feature_x has an existing, unchanged spec
    And feature_x has engineer: TODO
    When purlin:delivery-plan creates a plan
    Then feature_x PM column is SKIPPED
    And feature_x starts at stage "engineer"

### QA Scenarios

None.
