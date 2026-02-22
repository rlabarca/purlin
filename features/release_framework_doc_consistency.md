# Feature: Framework Documentation Consistency

> Label: "Release Step: Framework Documentation Consistency"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `doc_consistency_framework` local release step: a Purlin-repository-specific audit that verifies Purlin's own instruction files are internally consistent with each other and with the framework's README. This step is defined in Purlin's `.purlin/release/local_steps.json` and does not appear in consumer project checklists.

Consumer projects do not own instruction files — those reside inside the Purlin submodule and are read-only from the consumer's perspective. This step is therefore only meaningful in the Purlin framework repository itself.

## 2. Requirements

### 2.1 Audit Scope

The Architect cross-references all five base instruction files and the framework README:

- `instructions/HOW_WE_WORK_BASE.md`
- `instructions/ARCHITECT_BASE.md`
- `instructions/BUILDER_BASE.md`
- `instructions/QA_BASE.md`
- `features/policy_critic.md`
- `README.md`

### 2.2 Consistency Checks

For each pair of files in scope, the Architect verifies:

1. **No direct contradictions.** A rule stated in one instruction file must not be contradicted by a rule in another.
2. **No stale file path references.** All `tools/`, `features/`, and `.purlin/` paths referenced in instruction files must exist in the current codebase.
3. **No terminology mismatches.** Role names, lifecycle status labels, step IDs, and protocol names must be consistent across all files.
4. **No lifecycle or protocol divergence.** Definitions of the Feature Lifecycle, Discovery lifecycle, Critic routing, and release protocol MUST be consistent between `HOW_WE_WORK_BASE` and the role-specific base files.
5. **README accuracy.** README.md must accurately describe the framework's current instruction-file-governed behavior.

### 2.3 Remediation

Any inconsistency found is corrected using `/pl-edit-base` (for base instruction file edits in the Purlin repository). After corrections, the Architect commits with message `fix(instructions): <description>`.

### 2.4 Step Metadata

| Field | Value |
|-------|-------|
| ID | `doc_consistency_framework` |
| Friendly Name | `Framework Documentation Consistency` |
| Scope | Purlin-local (not a global step) |
| Code | null |
| Agent Instructions | "Cross-reference `instructions/HOW_WE_WORK_BASE.md`, `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`, and `features/policy_critic.md`. Check for: direct contradictions between files, stale file path references, terminology mismatches, and lifecycle/protocol definitions that differ between the shared philosophy and role-specific instructions. Also verify that README.md is consistent with the current instruction file content. Fix any inconsistencies and commit." |

## 3. Scenarios

### Manual Scenarios (Architect Execution)

#### Scenario: All instruction files are internally consistent
Given all five instruction files and README.md are mutually consistent,
When the Architect executes the `doc_consistency_framework` step,
Then the Architect reports "Framework instruction audit: CLEAN."
And no commits are made.

#### Scenario: Terminology mismatch between instruction files
Given one instruction file uses a deprecated role name or lifecycle status label that differs from another,
When the Architect executes the `doc_consistency_framework` step,
Then the Architect identifies the specific mismatch (file, section, conflicting term),
And corrects the stale file using `/pl-edit-base`,
And commits with message `fix(instructions): align terminology in <file>`.

#### Scenario: Stale path reference in instruction file
Given an instruction file references a tool path or config path that no longer exists,
When the Architect executes the `doc_consistency_framework` step,
Then the Architect updates the reference to the correct current path using `/pl-edit-base`,
And commits the correction.

#### Scenario: README inconsistent with instruction file content
Given README.md describes framework behavior that no longer matches the current instruction files,
When the Architect executes the `doc_consistency_framework` step,
Then the Architect identifies the specific discrepancy,
And updates README.md to match the current instruction content,
And commits the correction.

## Implementation Notes

This step is positioned immediately after `purlin.instruction_audit` in Purlin's release config, so override consistency (`purlin.instruction_audit`) and instruction-internal consistency (this step) run together before the broader doc check.

This step's scope intentionally excludes `.purlin/` override files — those are covered by `purlin.instruction_audit`. This step focuses on the base instruction layer.
