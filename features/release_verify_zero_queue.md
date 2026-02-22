# Feature: Purlin Verify Zero-Queue Status

> Label: "Release Step: Purlin Verify Zero-Queue Status"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `purlin.verify_zero_queue` release step: a gate check that confirms all features in the project have reached a fully satisfied state before a release is cut. No feature may have outstanding Architect, Builder, or QA work. This step operationalizes the Zero-Queue Mandate from `policy_release.md`.

## 2. Requirements

### 2.1 Status Check

The Architect runs `tools/cdd/status.sh` and inspects the JSON output. For each feature in the `features` array, all three conditions MUST be true:

- `architect` is `"DONE"`
- `builder` is `"DONE"`
- `qa` is `"CLEAN"` or `"N/A"`

### 2.2 Halt Condition

If any feature fails the check, the Architect:

1. Reports the failing feature(s) by label and file path.
2. Reports which specific role column(s) are not satisfied.
3. Halts the release. Subsequent checklist steps are NOT executed until all features pass.

### 2.3 Pass Condition

If all features satisfy the conditions, the Architect reports the total feature count and proceeds to the next release step. No files are modified.

### 2.4 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.verify_zero_queue` |
| Friendly Name | `Purlin Verify Zero-Queue Status` |
| Code | null |
| Agent Instructions | "Run `tools/cdd/status.sh` and confirm that every entry in the `features` array has `architect: \"DONE\"`, `builder: \"DONE\"`, and `qa` is either `\"CLEAN\"` or `\"N/A\"`. If any feature fails this check, halt the release and report which features are not ready." |

## 3. Scenarios

### Manual Scenarios (Architect Execution)

#### Scenario: All features satisfy zero-queue conditions
Given `tools/cdd/status.sh` reports every feature with `architect: "DONE"`, `builder: "DONE"`, and `qa` as `"CLEAN"` or `"N/A"`,
When the Architect executes the `purlin.verify_zero_queue` step,
Then the Architect reports the total feature count and confirms the queue is clear,
And proceeds to the next release step.

#### Scenario: Feature with outstanding Builder work
Given at least one feature has `builder: "TODO"`,
When the Architect executes the `purlin.verify_zero_queue` step,
Then the Architect reports the specific feature(s) blocking the release,
And halts without proceeding to subsequent release steps.

#### Scenario: Feature with open QA discoveries
Given at least one feature has `qa: "HAS_OPEN_ITEMS"`,
When the Architect executes the `purlin.verify_zero_queue` step,
Then the Architect reports the specific feature(s) blocking the release,
And halts without proceeding to subsequent release steps.

#### Scenario: Feature with outstanding Architect work
Given at least one feature has `architect: "TODO"`,
When the Architect executes the `purlin.verify_zero_queue` step,
Then the Architect reports the specific feature(s) blocking the release,
And halts without proceeding to subsequent release steps.

## Implementation Notes

This step is a pre-condition gate and does not modify any files. The only outcome is pass (proceed) or fail (halt with report).

The zero-queue mandate is defined in `policy_release.md`. This step operationalizes that policy at release time.
