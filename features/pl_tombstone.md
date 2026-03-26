# Feature: Feature Retirement

> Label: "Agent Skills: Engineer: /pl-tombstone Feature Retirement"
> Category: "Agent Skills: Engineer"
> Prerequisite: features/purlin_mode_system.md

[TODO]

## 1. Overview

Engineer mode's feature retirement skill that creates tombstone files before deleting retired feature specs. Checks the dependency graph for impact analysis, creates a structured tombstone file listing files to delete and dependencies to check, then moves the feature and its companion artifacts to the tombstones directory. The scan engine detects tombstones and surfaces them as highest-priority Engineer work items via `/pl-status`.

---

## 2. Requirements

### 2.1 Mode Gating

- The command activates Engineer mode.
- If another mode is active, confirm switch first.

### 2.2 Impact Analysis

- Read the dependency graph (`.purlin/cache/dependency_graph.json`) to identify all features that list the retiring feature as a prerequisite.
- Present the impact list to the user before proceeding.

### 2.3 Tombstone Creation

- Tombstone MUST be created BEFORE the feature file is moved.
- Canonical format includes: retired date, reason, files to delete, dependencies to check, and context.
- Tombstone created at `features/tombstones/<name>.md`.

### 2.4 Companion and Discovery Artifact Handling

- When creating a tombstone, move ALL associated artifacts to `features/tombstones/` alongside the spec:
  - `features/<name>.impl.md` → `features/tombstones/<name>.impl.md`
  - `features/<name>.discoveries.md` → `features/tombstones/<name>.discoveries.md`
- These are moved (not deleted) so the tombstone processor has full context about implementation history and known issues.

### 2.5 Test Artifact Discovery

- The tombstone's "Files to Delete" section MUST auto-discover and list all test infrastructure for the feature:
  - `tests/<name>/` directory (if it exists) — unit tests, tests.json
  - `tests/<name>/regression.json` (if it exists) — regression test results
  - `tests/qa/scenarios/<name>.json` (if it exists) — QA regression scenario
  - `tests/qa/test_<name>_regression.sh` (if it exists) — QA regression runner
- These are listed in the tombstone for the Engineer to delete when processing. They are NOT auto-deleted at tombstone creation time.
- **Tombstone processing** (by Engineer via `/pl-build`): Read the tombstone, delete all listed files and companion artifacts in `features/tombstones/`, then delete the tombstone file itself. Commit as a single cleanup commit.

### 2.6 Feature File Handling

- Move `features/<name>.md` to `features/tombstones/<name>.md` after tombstone content is written.
- Commit all moves together with the tombstone file.
- Run `scan.sh` to refresh project state.

### 2.7 Special Cases

- Features specced but never implemented (no code exists): delete directly, no tombstone needed. Still move companions/discoveries if they exist.
- Tombstone files are transient — they exist only until the Engineer processes them.
- When processing a tombstone (deleting the listed files), the Engineer MUST also delete the tombstone file itself and any companion artifacts in `features/tombstones/`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Impact analysis shows dependent features

    Given feature_a is a prerequisite for feature_b and feature_c
    When /pl-tombstone is invoked for feature_a
    Then feature_b and feature_c are listed as impacted

#### Scenario: Tombstone created before feature move

    Given the user confirms retirement of feature_a
    When the tombstone workflow executes
    Then features/tombstones/feature_a.md is created with tombstone content
    And features/feature_a.md is moved to features/tombstones/

#### Scenario: Companion files moved to tombstones

    Given feature_a has features/feature_a.impl.md and features/feature_a.discoveries.md
    When /pl-tombstone is invoked for feature_a
    Then features/tombstones/feature_a.impl.md exists
    And features/tombstones/feature_a.discoveries.md exists
    And features/feature_a.impl.md does not exist
    And features/feature_a.discoveries.md does not exist

#### Scenario: Test artifacts listed in tombstone

    Given feature_a has tests/feature_a/ directory with tests.json
    And tests/qa/scenarios/feature_a.json exists
    When /pl-tombstone is invoked for feature_a
    Then the tombstone's "Files to Delete" section includes "tests/feature_a/"
    And the tombstone's "Files to Delete" section includes "tests/qa/scenarios/feature_a.json"

#### Scenario: Unimplemented feature deleted without tombstone

    Given feature_a was specced but no implementation code exists
    When /pl-tombstone is invoked for feature_a
    Then the feature file is deleted directly
    And no tombstone file is created

#### Scenario: Tombstone processing cleans up all artifacts

    Given features/tombstones/feature_a.md lists tests/feature_a/ and src/feature_a.py
    When the Engineer processes the tombstone
    Then tests/feature_a/ is deleted
    And src/feature_a.py is deleted
    And features/tombstones/feature_a.md is deleted
    And features/tombstones/feature_a.impl.md is deleted (if present)
    And features/tombstones/feature_a.discoveries.md is deleted (if present)

### QA Scenarios

None.
