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

The Architect corrects all inconsistencies found within existing sections. Each correction is committed with message `docs(<scope>): <description>`. If corrections are extensive, they may be batched into a single commit.

### 2.4 No Unsolicited Major Sections

The Architect MUST NOT add a new top-level section (`##` heading) to README.md without explicit user confirmation of the section name and placement. This applies even when a coverage gap clearly indicates missing content. Refinements within existing sections (updating prose, fixing lists, correcting examples) do not require confirmation.

### 2.5 Coverage Gap Table

After the consistency pass, the Architect compares the current feature set (`features/*.md`) against the documented sections in README.md. For each feature area, behavior, or concept present in the spec but absent or significantly under-represented in the README, the Architect produces a coverage gap table and presents it to the user before writing anything.

The table format is:

| Feature / Concept | Gap Summary | Suggested Action |
|---|---|---|
| `<name>` | One-line description of what is missing | Add to existing section `"<section>"` / New section `"<proposed name>"` |

The Architect then asks: *"The items above are in the spec but not covered in README.md. Would you like to include any? Indicate which rows and I will add content to the suggested section, or to a new section you specify."*

If the user approves additions:
- For content going into an **existing section**: add within that section only, without restructuring.
- For a **new section**: confirm section name and placement with the user before creating it.

If the user declines all gaps, proceed without changes.

### 2.6 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.doc_consistency_check` |
| Friendly Name | `Documentation Consistency Check` |
| Code | null |
| Agent Instructions | "1. CONSISTENCY PASS — Check README.md and any docs/ documentation against the current feature set. Fix within existing sections: outdated feature descriptions, removed functionality references, stale file paths, version inconsistencies. Commit fixes with `docs(<scope>): <description>`. Do NOT add new ## sections in this pass.\n\n2. COVERAGE GAP ANALYSIS — Compare features/*.md against README.md sections. Identify feature areas, behaviors, or concepts present in the spec but absent or significantly under-represented in the README. Do not write any content yet.\n\n3. GAP TABLE PRESENTATION — Present a table to the user:\n\n   | Feature / Concept | Gap Summary | Suggested Action |\n   |---|---|---|\n   | <name> | <one-line description of what is missing> | Add to existing section \"<section>\" / New section \"<proposed name>\" |\n\n   Ask: 'The items above are in the spec but not covered in README.md. Would you like to include any? Indicate which rows and I will add content to the suggested section, or a new one you specify.'\n\n4. USER-DIRECTED ADDITIONS — For each gap the user approves:\n   a. Existing section: add content within that section only.\n   b. New section: confirm section name and placement with the user, then create it.\n   c. No approvals: proceed without changes.\n\n5. MANDATE — NEVER add a ## heading to README.md without explicit user confirmation of name and placement (step 4b). Consistency fixes within existing sections do not require confirmation." |

## 3. Scenarios

### Automated Scenarios
None. All verification is manual (Architect-executed release step).

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

#### Scenario: Coverage gaps exist and user approves some additions
Given the feature set contains areas not represented in README.md,
When the Architect completes the consistency pass,
Then the Architect presents a coverage gap table listing each undocumented area with a gap summary and suggested action,
And asks the user which items to include,
And for each approved item targeting an existing section, adds content within that section only,
And for each approved item requiring a new section, confirms the section name and placement before creating it,
And commits the additions with message `docs(readme): add coverage for <scope>`.

#### Scenario: Coverage gaps exist and user declines all additions
Given the feature set contains areas not represented in README.md,
When the Architect presents the coverage gap table and the user declines all suggestions,
Then the Architect makes no further changes to README.md,
And reports "Documentation check: CLEAN — consistency pass complete, no coverage additions requested."

#### Scenario: New major section added without user confirmation (prohibited)
Given the consistency pass reveals a documentation gap that seems to warrant a new section,
When the Architect has not received explicit user confirmation for the section name and placement,
Then the Architect MUST NOT create the new `##` heading,
And MUST present the gap in the coverage table and await user direction.

## Implementation Notes

This step applies to user-facing documentation only. Feature specification files (`features/*.md`) are not "documentation" for the purposes of this step — they are the ground truth source, not the output being checked here.

For the Purlin framework repository, README.md is the primary documentation target. Consumer projects may also have documentation in `docs/` or equivalent locations.
