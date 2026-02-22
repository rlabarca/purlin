# Feature: Purlin Agent Instruction Audit

> Label: "Release Step: Purlin Agent Instruction Audit"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `purlin.instruction_audit` release step: a pre-push audit that verifies the `.purlin/` override files do not introduce contradictions or drift against the base instruction layer. It is one of the global release steps defined in `tools/release/global_steps.json` and applies to all projects using the Purlin framework — both the framework repository itself and consumer projects.

## 2. Requirements

### 2.1 Audit Scope

The Architect executes this step against the four standard override files:

- `.purlin/HOW_WE_WORK_OVERRIDES.md`
- `.purlin/ARCHITECT_OVERRIDES.md`
- `.purlin/BUILDER_OVERRIDES.md`
- `.purlin/QA_OVERRIDES.md`

Each override file is cross-referenced against its corresponding base instruction file in `instructions/`. The base files are read-only; the override files are the unit of correction.

### 2.2 Audit Checks

For each override file, the Architect verifies:

1. **No direct contradictions.** An override rule that directly negates or reverses a base-layer rule is a contradiction. A contradiction MUST be resolved by revising the override.
2. **No stale path references.** File paths, tool commands, and directory names referenced in override rules MUST resolve to existing paths in the current codebase.
3. **No terminology mismatches.** Role names, lifecycle status labels, step IDs, and protocol names MUST match the current base-layer definitions. Deprecated terms are mismatches.
4. **No scope violations.** Override files MUST NOT contain code, scripts, or JSON. They are prose instruction documents only.

### 2.3 Remediation

Any issue found during the audit MUST be corrected in the override file before the release proceeds. After correction, the Architect commits the fix with message `fix(overrides): <description>`.

If a contradiction reveals a genuine gap or error in the base layer, the Architect MUST resolve it via the appropriate mechanism:

- In a consumer project: use `/pl-override-edit` to refine the override without modifying the base.
- In the Purlin framework repository: use `/pl-edit-base` to update the base, then re-run the audit.

### 2.4 Step Metadata

This step is registered in `tools/release/global_steps.json` as:

| Field | Value |
|-------|-------|
| ID | `purlin.instruction_audit` |
| Friendly Name | `Purlin Agent Instruction Audit` |
| Code | null |
| Agent Instructions | "Check `.purlin/HOW_WE_WORK_OVERRIDES.md`, `.purlin/ARCHITECT_OVERRIDES.md`, `.purlin/BUILDER_OVERRIDES.md`, and `.purlin/QA_OVERRIDES.md` for rules that directly contradict the base instruction files. Check for stale path references and terminology mismatches. Fix any inconsistencies and commit." |

## 3. Scenarios

### Manual Scenarios (Architect Execution)

#### Scenario: Clean audit with no issues
Given all four `.purlin/` override files are present and consistent with the base layer,
When the Architect executes the `purlin.instruction_audit` step,
Then the Architect reports "Instruction audit: CLEAN — no contradictions, stale paths, or terminology mismatches found."
And no commits are made.

#### Scenario: Contradiction detected and corrected
Given an override file contains a rule that directly negates a base-layer rule,
When the Architect executes the `purlin.instruction_audit` step,
Then the Architect identifies the specific contradiction (file, rule, conflicting base text),
And revises the override to remove or reconcile the contradiction,
And commits with message `fix(overrides): <description>`.

#### Scenario: Stale path reference corrected
Given an override file references a file path that no longer exists in the current codebase,
When the Architect executes the `purlin.instruction_audit` step,
Then the Architect updates the path reference to the correct current location,
And commits with message `fix(overrides): update stale path reference in <file>`.

#### Scenario: Audit blocked by unresolvable base-layer conflict
Given an override rule reveals a genuine error in the base layer that cannot be corrected in the override alone,
When the Architect executes the `purlin.instruction_audit` step,
Then the Architect halts the step and documents the base-layer conflict,
And uses `/pl-edit-base` (Purlin repo) or reports to the framework maintainer (consumer project),
And the release does not proceed until the conflict is resolved.

## Implementation Notes

This feature has no automated test coverage. Verification is performed by the Architect during the release process per the scenarios above. The QA column for this feature will always be `N/A`.

The audit scope covers only the four standard override files. Other files in `.purlin/` (e.g., `config.json`, `runtime/`, `cache/`) are out of scope for this step.
