# Feature: Refresh Documentation

> Label: "Release Step: Refresh Documentation"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md
> Prerequisite: features/release_doc_consistency_check.md

## 1. Overview

This feature defines the `refresh_docs` local release step: a local-only documentation freshness review that cross-references each `docs/**/*.md` file against the current implementation state and updates stale content. This step is intentionally decoupled from any publishing destination (Confluence, GitHub Wiki, etc.) so that downstream publishing steps can depend on it without duplicating the freshness logic.

---

## 2. Requirements

### 2.1 Doc Freshness Review

The step reviews each `docs/**/*.md` file against the current implementation:

1. Cross-reference content against `tools/`, `instructions/`, and `features/`.
2. Check for stale command references, outdated workflow descriptions, and removed/renamed concepts.
3. Update stale content and commit: `docs: update <filename> for current implementation`.
4. If no updates needed, confirm docs are current.

### 2.2 Freshness Detection Method

For each `docs/**/*.md` file:

1. Find the last commit date: `git log -1 --format="%ci" -- <doc_path>`.
2. Read the doc and identify which features, tools, and workflows it describes. Extract a list of the key spec files and implementation files the doc covers.
3. For each referenced file, check what has changed since the doc was last updated: `git log --oneline --since="<doc_last_commit_date>" -- <referenced_file>`.
4. If commits exist, read the current version of those files and diff against what the doc describes. Identify specific discrepancies: renamed commands, changed workflows, new capabilities, removed features, changed file paths, updated terminology.

### 2.3 Scope Constraint

This step NEVER creates new documentation files. It only updates existing ones. Documentation gaps are noted in the completion report's Recommendations section.

### 2.4 Completion Report

After review, print a change-focused summary:

```
-- Doc Freshness Review ------------------------------------

Local updates (committed):
  CHANGED  guides/testing-workflow-guide.md -- <description>
  OK       reference/parallel-execution-guide.md

-- Recommendations -----------------------------------------
Consider adding (will auto-sync on next release):
  - guides/release-process-guide.md
  - reference/critic-guide.md
-----------------------------------------------------------
```

Status tags: `CHANGED`/`OK` for local freshness. Recommendations section appears only if gaps are detected.

### 2.5 Step Metadata

| Field | Value |
|-------|-------|
| ID | `refresh_docs` |
| Friendly Name | `Refresh Documentation` |
| Code | `null` (interactive step) |
| Agent Instructions | See Section 2.6 |

### 2.6 Agent Instructions (Release Step Content)

1. Read each `docs/**/*.md` file.
2. For each doc:
   a. Find the last commit date: `git log -1 --format="%ci" -- <doc_path>`.
   b. Read the doc and identify which features, tools, and workflows it describes. Extract a list of the key spec files and implementation files the doc covers (e.g., a doc about parallel execution covers `tools/delivery/phase_analyzer.py`, `features/phase_analyzer.md`, `instructions/BUILDER_BASE.md` sections on parallel execution).
   c. For each referenced file, check what has changed since the doc was last updated: `git log --oneline --since="<doc_last_commit_date>" -- <referenced_file>`.
   d. If commits exist, read the current version and diff against what the doc describes. Identify specific discrepancies: renamed commands, changed workflows, new capabilities, removed features, changed file paths, updated terminology.
3. Present a per-doc freshness report:
   | Doc | Last Updated | Referenced Files Changed | Stale Areas |
4. For docs with identified staleness:
   a. Read the current version of all referenced spec and implementation files in full.
   b. Update the doc content to reflect the current state. Preserve the doc's existing structure and voice — only change what is factually outdated.
   c. Commit each doc update separately: `docs: update <filename> for current implementation`.
5. For docs with no staleness: confirm they are current.
6. Print the completion report per Section 2.4.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Stale documentation detected and updated

    Given docs/guides/testing-workflow-guide.md references a command that was renamed in the current implementation
    When the step executes the freshness review
    Then the stale reference is updated to the current command name
    And the change is committed with message "docs: update testing-workflow-guide.md for current implementation"

#### Scenario: Documentation is current, no changes needed

    Given all docs/**/*.md files accurately reflect the current implementation
    When the step executes the freshness review
    Then no commits are made
    And the step reports docs are current

#### Scenario: Step never creates new doc files

    Given a documentation gap is detected during freshness review
    When the step considers remediation
    Then no new files are created in docs/
    And the gap is listed in the Recommendations section of the completion report

### QA Scenarios

None.
