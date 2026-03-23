# Feature: Feature Retirement

> Label: "/pl-tombstone Feature Retirement"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The Architect's feature retirement skill that creates tombstone files before deleting retired feature specs. Checks the dependency graph for impact analysis, creates a structured tombstone file listing files to delete and dependencies to check, then deletes the original feature file. The Builder discovers tombstones through the Critic and processes the deletions.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the Architect role.
- Non-Architect agents MUST receive a redirect message.

### 2.2 Impact Analysis

- Read the dependency graph to identify all features that list the retiring feature as a prerequisite.
- Present the impact list to the user before proceeding.

### 2.3 Tombstone Creation

- Tombstone MUST be created BEFORE the feature file is deleted.
- Canonical format includes: retired date, reason, files to delete, dependencies to check, and context.
- Tombstone created at `features/tombstones/<name>.md`.

### 2.4 Feature Deletion

- Delete `features/<name>.md` after tombstone is created.
- Commit both changes together.
- Run `status.sh` to update the Critic report.

### 2.5 Special Cases

- Features specced but never implemented (no code exists): delete directly, no tombstone needed.
- Tombstone files are transient -- they exist only until the Builder processes them.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Architect invocation

    Given a Builder agent session
    When the agent invokes /pl-tombstone
    Then the command responds with a redirect message

#### Scenario: Impact analysis shows dependent features

    Given feature_a is a prerequisite for feature_b and feature_c
    When /pl-tombstone is invoked for feature_a
    Then feature_b and feature_c are listed as impacted

#### Scenario: Tombstone created before feature deletion

    Given the user confirms retirement of feature_a
    When the tombstone workflow executes
    Then features/tombstones/feature_a.md is created first
    And features/feature_a.md is deleted second

#### Scenario: Unimplemented feature deleted without tombstone

    Given feature_a was specced but no implementation code exists
    When /pl-tombstone is invoked for feature_a
    Then the feature file is deleted directly
    And no tombstone file is created

### QA Scenarios

None.
