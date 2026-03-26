# Feature: Refresh Documentation

> Label: "Release Step: Refresh Documentation"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md
> Prerequisite: features/release_doc_consistency_check.md

## 1. Overview

This feature defines the `refresh_docs` local release step: a local-only documentation freshness review that cross-references each `docs/**/*.md` file against the current implementation state, updates stale content, performs automatic cross-linking of concept mentions, and generates an index page (`docs/index.md`) that serves as the table of contents for all documentation. This step is intentionally decoupled from any publishing destination (Confluence, GitHub Wiki, etc.) so that downstream publishing steps can depend on it without duplicating the freshness, cross-linking, or index logic.

---

## 2. Requirements

### 2.1 Doc Freshness Review

The step reviews each `docs/**/*.md` file (excluding `docs/index.md`) against the current implementation:

1. Cross-reference content against `tools/`, `instructions/`, and `features/`.
2. Check for stale command references, outdated workflow descriptions, and removed/renamed concepts.
3. Update stale content and commit: `docs: update <filename> for current implementation`.
4. If no updates needed, confirm docs are current.

### 2.2 Freshness Detection Method

For each `docs/**/*.md` file (excluding `docs/index.md`):

1. Find the last commit date: `git log -1 --format="%ci" -- <doc_path>`.
2. Read the doc and identify which features, tools, and workflows it describes. Extract a list of the key spec files and implementation files the doc covers.
3. For each referenced file, check what has changed since the doc was last updated: `git log --oneline --since="<doc_last_commit_date>" -- <referenced_file>`.
4. If commits exist, read the current version of those files and diff against what the doc describes. Identify specific discrepancies: renamed commands, changed workflows, new capabilities, removed features, changed file paths, updated terminology.

### 2.3 Index Page Generation

After the freshness review, the step generates or updates `docs/index.md`. This file serves as the root table of contents for all documentation and is used by downstream publishing steps as the landing page content (Confluence parent page, GitHub Wiki Home page, etc.).

The index page contains:

1. A short introduction paragraph explaining that this is the Purlin framework's documentation for the agentic development workflow.
2. A table of contents organized into four fixed sections, with each doc listed under exactly one section (no duplicates):

| Section | Description | Docs |
|---------|-------------|------|
| **Agent Use** | How to interact with individual agents | Guides about using specific agents (PM, Engineer, etc.) |
| **CDD Dashboard** | Features of the CDD Dashboard UI | Guides about dashboard panels, visualizations, and configuration accessed through the dashboard |
| **Workflow & Process** | End-to-end workflows spanning multiple agents | Guides about testing, parallel execution, release processes |
| **Collaboration** | Multi-machine and team coordination | Guides about branch collaboration, remote push/pull |

3. Each entry uses a standard markdown relative link: `[Page Title](filename.md)` followed by a one-line description.
4. If `docs/index.md` already exists, it is regenerated from the current `docs/` directory contents. The introduction text is preserved if present; the TOC sections are always rebuilt.
5. After generation, commit: `docs: update index.md`.

### 2.4 Section Classification Rules

When classifying a doc into a section:

- A doc about a CDD Dashboard panel or feature (agent config, spec map, release checklist UI) goes in **CDD Dashboard**.
- A doc about how to use or interact with a specific agent role goes in **Agent Use**.
- A doc about an end-to-end workflow that spans multiple agents or describes a process goes in **Workflow & Process**.
- A doc about remote branch collaboration, push/pull, or multi-machine coordination goes in **Collaboration**.

Each doc appears in exactly one section. If a doc could fit multiple sections, prefer the most specific match.

### 2.5 Scope Constraint

This step NEVER creates new documentation files other than `docs/index.md`. Existing doc updates and index generation are the only write operations. Documentation gaps are noted in the completion report's Recommendations section.

### 2.6 Cross-Link Pass

After the freshness review and before index generation, the step performs an automatic cross-linking pass using a curated concept registry (`docs/cross_link_registry.json`):

1. Load `docs/cross_link_registry.json` and validate all `target` values resolve to existing files in `docs/`.
2. For each `docs/**/*.md` (excluding `index.md`):
   a. Skip registry entries where the current file IS the target (no self-links).
   b. Process concepts in order of longest term first to prevent substring conflicts.
   c. For each concept, find the first plain-text occurrence NOT inside an existing markdown link, heading (`#`), fenced code block, or inline code.
   d. Replace with `[term](target.md)`.
   e. Only link the first occurrence per concept per document.
3. If any links were inserted, commit: `docs: add cross-links`.

The cross-link pass is idempotent: a second run with no registry or content changes produces no modifications.

### 2.7 Completion Report

After review, print a change-focused summary:

```
-- Doc Freshness Review ------------------------------------

Local updates (committed):
  CHANGED  testing-workflow-guide.md -- <description>
  OK       parallel-execution-guide.md
  LINKED   critic-and-cdd-guide.md -- 3 concepts linked
  UPDATED  index.md -- regenerated TOC

-- Recommendations -----------------------------------------
Consider adding (will auto-sync on next release):
  - release-process-guide.md
  - critic-guide.md
-----------------------------------------------------------
```

Status tags: `CHANGED`/`OK` for local freshness, `LINKED` for cross-linked docs (with concept count), `UPDATED` for index.md. Recommendations section appears only if gaps are detected.

### 2.8 Step Metadata

| Field | Value |
|-------|-------|
| ID | `refresh_docs` |
| Friendly Name | `Refresh Documentation` |
| Code | `null` (interactive step) |
| Agent Instructions | See Section 2.9 |

### 2.9 Agent Instructions (Release Step Content)

**Phase 1: Doc Freshness Review**

1. Read each `docs/**/*.md` file (skip `docs/index.md`).
2. For each doc:
   a. Find the last commit date: `git log -1 --format="%ci" -- <doc_path>`.
   b. Read the doc and identify which features, tools, and workflows it describes. Extract a list of the key spec files and implementation files the doc covers.
   c. For each referenced file, check what has changed since the doc was last updated: `git log --oneline --since="<doc_last_commit_date>" -- <referenced_file>`.
   d. If commits exist, read the current version and diff against what the doc describes. Identify specific discrepancies.
3. Present a per-doc freshness report:
   | Doc | Last Updated | Referenced Files Changed | Stale Areas |
4. For docs with identified staleness:
   a. Read the current version of all referenced spec and implementation files in full.
   b. Update the doc content to reflect the current state. Preserve existing structure and voice.
   c. Commit each doc update separately: `docs: update <filename> for current implementation`.
5. For docs with no staleness: confirm they are current.

**Phase 1.5: Cross-Link Pass**

1. Load `docs/cross_link_registry.json`. Validate all `target` values resolve to existing files in `docs/`.
2. For each `docs/**/*.md` (excluding `index.md`):
   a. Skip registry entries where the current file IS the target (no self-links).
   b. For each concept (process longest terms first to prevent substring conflicts):
      - Find the first plain-text occurrence NOT inside an existing markdown link, heading, fenced code block, or inline code.
      - Replace with `[term](target.md)`.
      - Only link the first occurrence per concept per document.
   c. If any links were inserted, write the file.
3. Commit all modified docs: `docs: add cross-links`.

**Phase 2: Index Page Generation**

1. Scan `docs/` for all `*.md` files (excluding `index.md` itself and any files in `images/`).
2. For each doc, read the first heading (`# Title`) to derive the display title.
3. Read the first paragraph or overview section to derive a one-line description.
4. Classify each doc into one of the four sections per Section 2.4.
5. Generate `docs/index.md` with:
   a. Introduction paragraph about Purlin framework documentation.
   b. Four sections in order: Agent Use, CDD Dashboard, Workflow & Process, Collaboration.
   c. Each entry as: `* [Title](filename.md) -- one-line description`.
6. Commit: `docs: update index.md`.

**Phase 3: Completion Report**

Print the change-focused summary per Section 2.7, including `LINKED` status for cross-linked docs.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Stale documentation detected and updated

    Given docs/testing-workflow-guide.md references a command that was renamed in the current implementation
    When the step executes the freshness review
    Then the stale reference is updated to the current command name
    And the change is committed with message "docs: update testing-workflow-guide.md for current implementation"

#### Scenario: Documentation is current, no changes needed

    Given all docs/**/*.md files accurately reflect the current implementation
    When the step executes the freshness review
    Then no commits are made for freshness updates
    And the step reports docs are current

#### Scenario: Step never creates new doc files other than index

    Given a documentation gap is detected during freshness review
    When the step considers remediation
    Then no new files are created in docs/ other than index.md
    And the gap is listed in the Recommendations section of the completion report

#### Scenario: Index page generated with four sections

    Given docs/ contains pm-agent-guide.md, agent-configuration-guide.md, spec-map-guide.md, testing-workflow-guide.md, parallel-execution-guide.md, and branch-collaboration-guide.md
    When the step generates docs/index.md
    Then index.md contains sections "Agent Use", "CDD Dashboard", "Workflow & Process", and "Collaboration"
    And pm-agent-guide.md appears under "Agent Use"
    And agent-configuration-guide.md and spec-map-guide.md appear under "CDD Dashboard"
    And testing-workflow-guide.md and parallel-execution-guide.md appear under "Workflow & Process"
    And branch-collaboration-guide.md appears under "Collaboration"

#### Scenario: No doc appears in multiple sections

    Given docs/ contains six documentation files
    When the step generates docs/index.md
    Then each doc filename appears exactly once in the index

#### Scenario: Index uses relative markdown links

    Given docs/ contains pm-agent-guide.md
    When the step generates docs/index.md
    Then the entry for PM Agent Guide uses the link format "[PM Agent Guide](pm-agent-guide.md)"

#### Scenario: First occurrence linked, subsequent left plain

    Given docs/testing-workflow-guide.md contains two mentions of "Critic"
    And "Critic" maps to critic-and-cdd-guide.md in cross_link_registry.json
    When the cross-link pass runs
    Then the first mention becomes "[Critic](critic-and-cdd-guide.md)"
    And the second mention remains plain text "Critic"

#### Scenario: Self-reference skipped

    Given docs/critic-and-cdd-guide.md contains a mention of "Critic"
    And "Critic" maps to critic-and-cdd-guide.md in cross_link_registry.json
    When the cross-link pass processes critic-and-cdd-guide.md
    Then "Critic" is not linked (self-reference skipped)

#### Scenario: Idempotent on second run

    Given the cross-link pass has already run and inserted links
    When the cross-link pass runs again with no registry or content changes
    Then no files are modified
    And no commit is created

#### Scenario: Code blocks and headings skipped

    Given docs/spec-map-guide.md contains "Critic" inside a fenced code block
    And docs/spec-map-guide.md contains "Critic" in a heading
    And docs/spec-map-guide.md contains "Critic" in plain body text
    When the cross-link pass runs
    Then only the plain body text occurrence is linked
    And the code block and heading occurrences remain unchanged

#### Scenario: Existing links not double-wrapped

    Given docs/parallel-execution-guide.md contains "[Critic](critic-and-cdd-guide.md)" (already linked)
    And no other plain-text occurrence of "Critic" exists in the file
    When the cross-link pass runs
    Then the existing link is left unchanged
    And no new link is inserted for "Critic" in that file

### QA Scenarios

None.
