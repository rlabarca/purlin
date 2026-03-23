# Feature: Delivery Plan

> Label: "/pl-delivery-plan Delivery Plan"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The Builder's phased delivery skill that assesses implementation scope and proposes splitting work into numbered phases for large or complex feature sets. Provides scope assessment heuristics, per-phase sizing caps, dependency-aware phase ordering with execution group detection, and a canonical delivery plan format. Supports both plan creation and cross-session plan review/adjustment.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the Builder role.
- Non-Builder agents MUST receive a redirect message.

### 2.2 Existing Plan Review

- If `.purlin/delivery_plan.md` exists: display current phase, completed phases, remaining phases, and per-feature status. Offer to adjust the plan.

### 2.3 New Plan Creation

- Run `status.sh` to get current feature status.
- Read `dependency_graph.json` and build a prerequisite map.
- Assess scope using heuristics: 2+ HIGH-complexity features or 3+ features of any mix recommends phasing.

### 2.4 Phase Sizing

- Max 2 features per phase.
- Max 1 HIGH-complexity feature per phase if combined with another feature.
- Single HIGH-complexity feature with 5+ scenarios gets its own dedicated phase.

### 2.5 Phase Ordering

- Phases ordered by: dependency order (foundations first), logical cohesion, testability gates, balanced effort, interaction density, and parallelization opportunity.
- Validation gate: verify no dependency cycles between phases before committing.

### 2.6 Execution Groups

- Identify which phases can execute in parallel (no cross-phase dependencies).
- Report parallel build opportunities within phases (independent features).

### 2.7 Canonical Format

- Plan file uses standardized Markdown format with Created date, Total Phases, Summary, and per-phase entries with Features, Completion Commit, Deferred, and QA Bugs Addressed fields.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Builder invocation

    Given an Architect agent session
    When the agent invokes /pl-delivery-plan
    Then the command responds with a redirect message

#### Scenario: Existing plan displays current state

    Given .purlin/delivery_plan.md exists with Phase 1 COMPLETE and Phase 2 IN_PROGRESS
    When /pl-delivery-plan is invoked
    Then Phase 1 status and completion commit are shown
    And Phase 2 features with their implementation status are listed

#### Scenario: Scope assessment recommends phasing for complex work

    Given 3 features in TODO state
    When /pl-delivery-plan assesses scope
    Then it recommends phased delivery

#### Scenario: Dependency validation catches cycle

    Given a proposed plan where Phase 2 feature depends on Phase 3 feature
    When the validation gate runs
    Then the cycle is detected
    And the plan is corrected before committing

#### Scenario: Phase sizing cap enforced

    Given 3 features assigned to a single phase
    When /pl-delivery-plan validates the plan
    Then the phase is split to respect the 2-feature-per-phase cap

### QA Scenarios

None.
