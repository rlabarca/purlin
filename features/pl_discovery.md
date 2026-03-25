# Feature: Discovery Recording

> Label: "Agent Skills: QA: /pl-discovery Discovery Recording"
> Category: "Agent Skills: QA"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The QA discovery recording skill that provides a guided workflow for classifying and recording structured verification findings. Supports four discovery types (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE) with role-based routing, manages the full discovery lifecycle (OPEN through PRUNED), and handles discovery sidecar file creation and pruning.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Scope

- If an argument is provided, record for `features/<arg>.md`.
- If no argument, ask the user which feature the discovery belongs to.

### 2.3 Discovery Classification

- **[BUG]:** Behavior contradicts an existing scenario. Routes to Engineer.
- **[DISCOVERY]:** Behavior exists but no scenario covers it. Routes to PM.
- **[INTENT_DRIFT]:** Behavior matches spec literally but misses actual intent. Routes to PM.
- **[SPEC_DISPUTE]:** User disagrees with scenario's expected behavior. Routes to PM (design disputes triage to PM).

### 2.4 Recording Format

- Record entries in `features/<name>.discoveries.md`, creating if absent.
- Format includes type, title, date, scenario reference, observed/expected behavior, action routing, and OPEN status.
- Commit with message: `qa(<scope>): [TYPE] - <brief title>`.

### 2.5 Discovery Lifecycle

- Status progression: OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED.
- Pruning: remove from sidecar, add one-liner to companion file (no bracket tags).

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given an Engineer agent session
    When the agent invokes /pl-discovery
    Then the command responds with a redirect message

#### Scenario: BUG discovery routes to Engineer

    Given a verification failure contradicting an existing scenario
    When the QA agent classifies it as BUG
    Then the discovery entry has Action Required set to Engineer

#### Scenario: SPEC_DISPUTE suspends scenario

    Given the user disagrees with a scenario's expected behavior
    When the QA agent classifies it as SPEC_DISPUTE
    Then the discovery entry has Action Required set to PM
    And the user is informed the scenario is suspended

#### Scenario: Discovery sidecar file created when absent

    Given no discoveries.md file exists for feature_a
    When a discovery is recorded for feature_a
    Then features/feature_a.discoveries.md is created
    And it contains the proper heading and discovery entry

#### Scenario: Pruning moves entry to companion file

    Given a RESOLVED discovery exists in feature_a.discoveries.md
    When the discovery is pruned
    Then the entry is removed from the sidecar file
    And a one-liner summary is added to feature_a.impl.md

### QA Scenarios

None.
