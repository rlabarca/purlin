# Feature: QA Completion

> Label: "Agent Skills: QA: /pl-complete QA Completion"
> Category: "Agent Skills: QA"

[TODO]

## 1. Overview

The QA lifecycle completion skill that gates feature completion on verification requirements. Checks that the feature is in TESTING state, all scenarios are verified, zero open discoveries exist, the feature is not phase-gated by a delivery plan, and creates the completion commit with the mandatory `[Verified]` tag that distinguishes QA completions from Engineer auto-completions.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Completion Gates

- **TESTING state:** Feature MUST be in TESTING lifecycle state.
- **All scenarios verified:** All manual scenarios MUST have been verified (PASS).
- **Zero open discoveries:** Zero OPEN or SPEC_UPDATED discoveries in the feature's discovery sidecar.
- **Delivery plan check:** Feature MUST NOT appear in any PENDING phase of a delivery plan.
- **[Verified] tag:** QA completions MUST include the `[Verified]` tag.

### 2.3 Execution

- If all gates pass: create commit with `[Complete features/<name>.md] [Verified]`.
- Run `scan.sh` to confirm the feature transitions to COMPLETE.

### 2.4 Gate Failure Reporting

- Report which gate(s) failed and what is needed to resolve each.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given an Engineer agent session
    When the agent invokes /pl-complete
    Then the command responds with a redirect message

#### Scenario: All gates pass creates completion commit

    Given feature_a is in TESTING state
    And all scenarios are verified
    And zero open discoveries exist
    And feature_a is not in a PENDING delivery phase
    When /pl-complete is invoked for feature_a
    Then a commit is created with "[Complete features/feature_a.md] [Verified]"

#### Scenario: Open discoveries block completion

    Given feature_a has 2 OPEN discoveries
    When /pl-complete is invoked for feature_a
    Then the command reports the 2 open discoveries by title
    And no completion commit is created

#### Scenario: Delivery plan gates completion

    Given feature_a appears in Phase 2 which is PENDING
    When /pl-complete is invoked for feature_a
    Then the command reports the feature is phase-gated
    And no completion commit is created

#### Scenario: Not in TESTING state blocks completion

    Given feature_a is in TODO state
    When /pl-complete is invoked for feature_a
    Then the command reports "Feature must be in TESTING state. Current state: TODO"

### QA Scenarios

None.
