# Feature: Commit Conventions Reference

> Label: "Shared Agent Definitions: Commit Conventions"
> Category: "Shared Agent Definitions"
> Prerequisite: features/purlin_mode_system.md

## 1. Overview

The commit conventions reference (`instructions/references/commit_conventions.md`) defines commit message format, mode attribution prefixes, status tag format, scope types, and lifecycle reset exemption tags. All skills and instruction files reference this single file for commit format.

---

## 2. Requirements

### 2.1 Mode Attribution

- MUST define commit prefixes per mode: Engineer (`feat/fix/test`), PM (`spec/design`), QA (`qa/status`), Shared (`chore/docs`).
- MUST define the `Purlin-Mode: <mode>` trailer requirement.

### 2.2 Status Tag Format

- MUST define the `[Complete features/FILENAME.md]` and `[Ready for Verification features/FILENAME.md]` formats.
- MUST define QA `[Verified]` tag.
- MUST define scope types: `full`, `targeted`, `cosmetic`, `dependency-only`.

### 2.3 Exemption Tags

- MUST define `[QA-Tags]`, `[Spec-FMT]`, and `[Migration]` with meaning and usage.
- MUST state: if ALL commits since last status commit carry exempt tags, lifecycle is preserved.
- scan.py MUST recognize these tags (see `purlin_scan_engine.md` Section 2.10).

### 2.4 Commit Discipline

- Commit at logical milestones, not batched until session end.
- Status tag commits MUST be standalone (no code changes in same commit).

---

## 3. Scenarios

### Unit Tests

#### Scenario: All mode prefixes defined

    Given references/commit_conventions.md exists
    When the mode attribution section is parsed
    Then Engineer prefixes include feat, fix, test
    And PM prefixes include spec, design
    And QA prefixes include qa, status

#### Scenario: Exemption tags defined with usage

    Given references/commit_conventions.md exists
    When the exemption tags section is parsed
    Then [QA-Tags], [Spec-FMT], and [Migration] are defined
    And each has a "When to Use" description

#### Scenario: Status tag format includes scope

    Given references/commit_conventions.md exists
    When the status tag section is parsed
    Then it defines full, targeted, cosmetic, and dependency-only scopes

## Regression Guidance
- Verify commit conventions match actual git log conventions in the project
- Verify scan.py exemption tag regex matches the tags defined here
