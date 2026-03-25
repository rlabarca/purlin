# Feature: QA Status Report

> Label: "Agent Skills: QA: /pl-qa-report QA Status Report"
> Category: "Agent Skills: QA"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The QA summary report skill that produces a structured overview of verification state. Shows TESTING features with manual item counts and scopes, open discoveries grouped by type, completion blockers per feature, delivery plan context, and effort estimates.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the QA role.
- Non-QA agents MUST receive a redirect message.

### 2.2 Report Sections

- **TESTING Features:** Each with manual scenario count, verification scope, and open discovery count.
- **Open Discoveries:** All OPEN and SPEC_UPDATED discoveries grouped by type.
- **Completion Blockers:** Per TESTING feature, what blocks completion.
- **Delivery Plan Context:** Classify features as fully delivered vs phase-gated.
- **Effort Estimate:** Total manual items across all TESTING features.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-qa-report
    Then the command responds with a redirect message

#### Scenario: Report shows TESTING features with counts

    Given 3 features are in TESTING state
    When /pl-qa-report is invoked
    Then all 3 features are listed with manual item counts and scopes

#### Scenario: Open discoveries grouped by type

    Given 2 BUG and 1 SPEC_DISPUTE discoveries are open
    When /pl-qa-report is invoked
    Then the Open Discoveries section shows BUG (2) and SPEC_DISPUTE (1)

#### Scenario: Delivery plan gating shown

    Given feature_a is phase-gated in Phase 2
    When /pl-qa-report is invoked
    Then feature_a is listed as phase-gated in Completion Blockers

### QA Scenarios

None.
