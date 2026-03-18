# Feature: Critic Test Quality Audit Trail

> Label: "Critic: Test Quality Audit Trail"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/policy_test_quality.md

## 1. Overview

Implements the Critic check defined in `policy_critic.md` Section 2.17 (Test Quality Audit Trail). When a feature has automated scenarios, `builder: "DONE"`, and the companion file lacks a `### Test Quality Audit` section, the Critic generates a LOW-priority Builder action item. This is the backstop that ensures the subagent quality evaluation mandated by `policy_test_quality.md` Section 2.6 is always performed.

---

## 2. Requirements

### 2.1 Companion File Scan

The Critic MUST scan the companion file (`features/<name>.impl.md`) for the heading `### Test Quality Audit` (exact match, case-sensitive) when all of the following conditions are met:

- The feature has one or more automated scenarios (non-zero automated scenario count from the Spec Gate).
- The feature's `builder` role status is `"DONE"`.
- The companion file exists on disk.

When the companion file does not exist, the check triggers (missing file implies missing section).

### 2.2 Action Item Generation

When the `### Test Quality Audit` heading is absent and the conditions in 2.1 are met, the Critic MUST generate an action item with the following properties:

- **Priority:** LOW
- **Role:** Builder
- **Category:** `missing_test_quality_audit`
- **Description:** `"Missing test quality audit for <name> -- run subagent evaluation per policy_test_quality.md Section 2.6"`

### 2.3 Gate Impact

This check is advisory only. It MUST NOT affect the Implementation Gate pass/fail status. The action item appears in the Builder's section of the Critic report but does not block `builder: "DONE"` or release.

### 2.4 Exemptions

- Features with zero automated scenarios are exempt (nothing to audit).
- Features where `builder` status is `"TODO"` are exempt (implementation not yet complete).
- Anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) are exempt (they have no automated scenarios by convention).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Missing audit section generates LOW action item

    Given a feature with 3 automated scenarios
    And builder status is DONE
    And the companion file exists but has no Test Quality Audit section
    When the Critic runs
    Then a LOW-priority Builder action item is generated
    And the category is missing_test_quality_audit
    And the description references the feature name

#### Scenario: Present audit section suppresses action item

    Given a feature with 3 automated scenarios
    And builder status is DONE
    And the companion file contains a Test Quality Audit section
    When the Critic runs
    Then no missing_test_quality_audit action item is generated

#### Scenario: Missing companion file triggers action item

    Given a feature with 2 automated scenarios
    And builder status is DONE
    And no companion file exists at features/<name>.impl.md
    When the Critic runs
    Then a LOW-priority Builder action item is generated with category missing_test_quality_audit

#### Scenario: Feature with zero automated scenarios is exempt

    Given a feature with only manual scenarios
    And builder status is DONE
    When the Critic runs
    Then no missing_test_quality_audit action item is generated

#### Scenario: Feature with builder TODO is exempt

    Given a feature with 3 automated scenarios
    And builder status is TODO
    When the Critic runs
    Then no missing_test_quality_audit action item is generated

#### Scenario: Audit check does not affect Implementation Gate

    Given a feature with missing Test Quality Audit section
    And all other Implementation Gate checks pass
    When the Critic evaluates the Implementation Gate
    Then the gate result is PASS
    And the missing_test_quality_audit item appears only in the action items list

### Manual Scenarios (Human Verification Required)

None.
