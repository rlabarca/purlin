# Feature: Documentation Consistency Check

> Label: "Release Step: Documentation Consistency Check"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `purlin.doc_consistency_check` release step: an audit that verifies README.md and any project documentation accurately reflect the current feature set. Outdated documentation misleads users and consumers of the project.

## 2. Requirements

### 2.1 Documentation Scope

The Architect checks README.md and any additional documentation files in a `docs/` directory (or equivalent). Feature specification files (`features/*.md`) are the ground truth for expected behavior; documentation must agree with them.

### 2.2 Consistency Checks

For each documentation file in scope, the Architect verifies:

1. **No outdated feature descriptions.** Prose descriptions of features must reflect current spec behavior, not prior iterations.
2. **No references to removed functionality.** Any documentation that describes a feature, command, or behavior that no longer exists in the spec must be updated or removed.
3. **No stale file paths.** Directory structures, file paths, and command invocations mentioned in documentation must match the current codebase layout.
4. **No version inconsistencies.** Version numbers, release names, or dated references must be consistent with the release being prepared.

### 2.3 Remediation

The Architect corrects all inconsistencies found. Each correction is committed with message `docs(<scope>): <description>`. If corrections are extensive, they may be batched into a single commit.

### 2.4 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.doc_consistency_check` |
| Friendly Name | `Documentation Consistency Check` |
| Code | null |
| Agent Instructions | "Check that README.md and any project documentation (in `docs/` or equivalent) accurately reflects the current feature set. Look for: outdated feature descriptions, references to removed functionality, stale file paths, and version numbers inconsistent with the current release. Cross-check with the `features/` directory to confirm documented behavior matches specified behavior. Fix any inconsistencies and commit." |

## 3. Scenarios

### Manual Scenarios (Architect Execution)

#### Scenario: Documentation is fully consistent
Given README.md and all documentation files accurately reflect the current feature set and file layout,
When the Architect executes the `purlin.doc_consistency_check` step,
Then the Architect reports "Documentation check: CLEAN — no inconsistencies found."
And no commits are made.

#### Scenario: Stale feature description corrected
Given README.md describes a feature behavior that was changed in the current release cycle,
When the Architect executes the `purlin.doc_consistency_check` step,
Then the Architect updates the description to match the current spec,
And commits with message `docs(readme): <description of change>`.

#### Scenario: Reference to removed functionality corrected
Given README.md references a command, config option, or behavior that no longer exists in the spec,
When the Architect executes the `purlin.doc_consistency_check` step,
Then the Architect removes or replaces the stale reference,
And commits the correction.

#### Scenario: Stale file path corrected
Given documentation references a directory or file path that has been renamed or relocated,
When the Architect executes the `purlin.doc_consistency_check` step,
Then the Architect updates the path to its current correct location,
And commits with message `docs(<scope>): update stale path reference`.

## Implementation Notes

This step applies to user-facing documentation only. Feature specification files (`features/*.md`) are not "documentation" for the purposes of this step — they are the ground truth source, not the output being checked here.

For the Purlin framework repository, README.md is the primary documentation target. Consumer projects may also have documentation in `docs/` or equivalent locations.
