# Feature: Override Edit

> Label: "Agent Skills: Common: /pl-override-edit Override Edit"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

A role-scoped skill for editing override files (`.purlin/PURLIN_OVERRIDES.md`) with built-in conflict scanning. Each role can only edit their own override file (Engineer: the Engineer Mode section of PURLIN_OVERRIDES, QA: the QA Mode section of PURLIN_OVERRIDES, PM: the PM Mode section of PURLIN_OVERRIDES) while PM mode can edit any. Performs a three-level conflict scan (CONFLICT, WARNING, INFO) against the corresponding base instruction file before applying changes.

---

## 2. Requirements

### 2.1 Role Scoping

- Engineer: may edit ONLY `PURLIN_OVERRIDES.md`.
- QA: may edit ONLY `PURLIN_OVERRIDES.md`.
- PM: may edit ONLY `PURLIN_OVERRIDES.md`.
- PM: may edit any `PURLIN_OVERRIDES.md` file.

### 2.2 Conflict Scan

- For each rule in the override, classify against the base file:
  - **[CONFLICT]:** directly contradicts a base rule.
  - **[WARNING]:** addresses the same concern but not clearly contradictory.
  - **[INFO]:** cosmetic overlap or redundant phrasing.
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

#### Scenario: Engineer cannot edit QA overrides

    Given an Engineer agent session
    When Engineer mode attempts to edit PURLIN_OVERRIDES.md
    Then the command declines and names the QA role as the owner

#### Scenario: Conflict scan detects contradiction

    Given PURLIN_OVERRIDES.md contains a rule contradicting PURLIN_BASE.md
    When /pl-override-edit runs the conflict scan
    Then a CONFLICT finding is reported with cited text from both files

#### Scenario: Scan-only mode does not modify files

    Given /pl-override-edit is invoked with --scan-only
    When the conflict scan completes
    Then no files are modified

#### Scenario: Additive-only constraint enforced

    Given a proposed edit that deletes existing content
    When /pl-override-edit validates the edit
    Then the edit is rejected as non-additive

### QA Scenarios

None.
