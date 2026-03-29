# Feature: Override Edit

> Label: "Agent Skills: Common: purlin:override-edit Override Edit"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

A shared skill for editing override files (`.purlin/PURLIN_OVERRIDES.md`) with built-in conflict and consistency scanning. Any active mode can edit any section of the override file — there is no per-section role restriction. Performs a multi-level scan (CONFLICT, WARNING, INFO) against the corresponding base instruction file before applying changes. The scan covers contradictions, stale path references, and terminology mismatches (absorbing the former `purlin.instruction_audit` tool's responsibilities).

---

## 2. Requirements

### 2.1 Access

- Any active mode (Engineer, PM, QA) may edit any section of `PURLIN_OVERRIDES.md`.
- No per-section role restriction. Override files are classified as CODE but have a Cross-Mode Recording Rights entry allowing any mode to edit via this skill (see `references/file_classification.md`).

### 2.2 Conflict and Consistency Scan

- For each rule in the override, classify against the base file:
  - **[CONFLICT]:** directly contradicts a base rule.
  - **[WARNING]:** addresses the same concern but not clearly contradictory.
  - **[INFO]:** cosmetic overlap or redundant phrasing.
- Additionally scan for:
  - **Stale path references:** file paths in the override that no longer resolve to existing files or sections.
  - **Terminology mismatches:** terms in the override that differ from the base file's vocabulary for the same concept (e.g., using a renamed section heading or deprecated term).
- Present findings grouped with cited text and count summary.

### 2.3 Content Guidance

- Override files carry project-specific bright-line rules and domain context.
- Override files do NOT carry workflow procedures or multi-step protocols (those belong in skill files).

### 2.4 Change Constraints

- Additive only -- append, do not delete or restructure.
- No contradictions with base file.
- No code, scripts, JSON config, or executable content.
- Show proposed edit and ask for confirmation before writing.

### 2.5 Scan-Only Mode

- `--scan-only` flag executes conflict scan only, no edits made.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Any mode can edit any override section

    Given an Engineer agent session
    When Engineer mode edits the QA Mode section of PURLIN_OVERRIDES.md
    Then the edit is applied without role restriction

#### Scenario: Conflict scan detects contradiction

    Given PURLIN_OVERRIDES.md contains a rule contradicting PURLIN_BASE.md
    When purlin:override-edit runs the conflict scan
    Then a CONFLICT finding is reported with cited text from both files

#### Scenario: Scan detects stale path reference

    Given PURLIN_OVERRIDES.md references a file path that does not exist
    When purlin:override-edit runs the conflict scan
    Then an INFO finding is reported identifying the stale path

#### Scenario: Scan detects terminology mismatch

    Given PURLIN_OVERRIDES.md uses a deprecated term that PURLIN_BASE.md has renamed
    When purlin:override-edit runs the conflict scan
    Then a WARNING finding is reported citing both the override and base terms

#### Scenario: Scan-only mode does not modify files

    Given purlin:override-edit is invoked with --scan-only
    When the conflict scan completes
    Then no files are modified

#### Scenario: Additive-only constraint enforced

    Given a proposed edit that deletes existing content
    When purlin:override-edit validates the edit
    Then the edit is rejected as non-additive

### QA Scenarios

None.
