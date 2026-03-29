# Feature: File Classification Reference

> Label: "Shared Agent Definitions: File Classification"
> Category: "Shared Agent Definitions"
> Prerequisite: purlin_mode_system.md

## 1. Overview

The file classification reference (`references/file_classification.md`) defines which files are CODE (Engineer-owned), SPEC (PM-owned), or QA-OWNED. All mode write-access rules and the mode guard reference this single file. When a new file type is introduced, this is the only place to update — mode definitions in PURLIN_BASE.md do not maintain inline lists.

---

## 2. Requirements

### 2.1 Three Ownership Categories

- MUST define CODE (Engineer): source code, scripts, tests, config, skill files, instruction files, agent definitions, hooks, build/CI config, launcher scripts, technical anchors, companion files, process config.
- MUST define SPEC (PM): feature specs, design anchors, policy anchors, visual design artifacts, prose documentation.
- MUST define QA-OWNED: discovery sidecars, QA scenario tags, regression JSON, QA verification scripts.

### 2.2 Cross-Mode Recording Rights

- MUST define which files can be written by a mode that doesn't own them (e.g., any mode can add OPEN discoveries to sidecars, QA adds tags to PM-owned scenario headings).
- MUST present this as a table with Owner and "Who can record" columns.

### 2.3 Quick Reference Table

- MUST include a lookup table mapping file patterns to required modes.
- The mode guard in PURLIN_BASE.md references this table before every write.

### 2.4 Single Source of Truth

- PURLIN_BASE.md mode definitions MUST say "All files classified as CODE/SPEC/QA-OWNED in `references/file_classification.md`" — not inline enumerations.
- No other file may maintain a competing list of file ownership patterns.
- When a new file type is added, updating this file is sufficient — no mode definition edits needed.

### 2.5 DevOps and Build Code

- Build scripts, CI configuration, Dockerfiles, Makefiles, and deployment tooling are classified as CODE.
- This applies regardless of file extension (`.yml`, `.yaml`, `.toml`, `.json` for CI/CD are CODE, not config).

---

## 3. Scenarios

### Unit Tests

#### Scenario: All standard file types are classified

    Given references/file_classification.md exists
    When all file patterns are extracted
    Then source code, scripts, tests, config, skill files, instruction files are CODE
    And feature specs, design anchors, policy anchors are SPEC
    And discovery sidecars, QA tags, regression JSON are QA-OWNED

#### Scenario: PURLIN_BASE.md has no inline file lists

    Given instructions/PURLIN_BASE.md exists
    When mode definitions are parsed
    Then Engineer write-access references "references/file_classification.md"
    And PM write-access references "references/file_classification.md"
    And QA write-access references "references/file_classification.md"
    And no mode contains an inline enumeration of file patterns

#### Scenario: Cross-mode recording rights documented

    Given references/file_classification.md exists
    When the cross-mode section is parsed
    Then discovery sidecars list "Any mode can add new OPEN entries"
    And QA Scenarios section lists "QA adds @auto/@manual tags"

#### Scenario: Skill files classified as CODE

    Given references/file_classification.md exists
    When checking .claude/commands/*.md classification
    Then they are listed under CODE (Engineer-owned)

#### Scenario: DevOps files classified as CODE

    Given references/file_classification.md exists
    When checking Dockerfile, Makefile, .github/workflows/*.yml
    Then they are listed under CODE (Engineer-owned)

### QA Scenarios

#### Scenario: Mode guard uses file classification for ownership check @manual

    Given the agent is in PM mode
    And references/file_classification.md classifies .claude/commands/*.md as CODE
    When the agent attempts to write a skill file
    Then the mode guard blocks the write
    And references the file classification in its response

## Regression Guidance
- Verify file_classification.md covers every file type the agent encounters in normal operation
- Verify adding a new file type is reflected in mode guard behavior without editing PURLIN_BASE.md
- Verify no inline file pattern lists remain in PURLIN_BASE.md mode definitions
