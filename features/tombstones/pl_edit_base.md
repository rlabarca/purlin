# Feature: Base File Editor

> Label: "/pl-edit-base Base File Editor"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A Purlin-framework-only skill (not distributed to consumer projects) that provides a guided protocol for editing base instruction files (`instructions/*.md`). Enforces the context budget classification (bright-line rules go in base files, protocol detail goes in skill files), runs conflict scans against all corresponding override files, and applies additive-only principles.

---

## 2. Requirements

### 2.1 Role and Repository Gating

- The command MUST only execute when invoked by the PM role in the Purlin framework repository.
- Consumer project agents MUST receive a redirect to `/pl-override-edit`.
- Confirm no `purlin/` submodule directory exists (which would indicate a consumer project).

### 2.2 Context Budget Classification

- Classify each addition as:
  - **Bright-line rule** (behavioral mandate, gate condition): belongs in base file.
  - **Protocol detail** (multi-step workflow, format template): belongs in skill file.
- Test: "If missing from context, would the agent violate a rule?" If yes, base file. If step-by-step procedure, skill file.

### 2.3 Override Conflict Scan

- Run `/pl-override-edit --scan-only` on all corresponding override files before applying changes.
- Surface any conflicts before proceeding.

### 2.4 Change Protocol

- Additive-only where possible.
- Revisionary changes require explicit user confirmation.
- Show proposed edit and ask for confirmation before writing.
- Commit and run `status.sh` after approval.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Consumer project receives redirect

    Given a consumer project with purlin/ submodule directory
    When /pl-edit-base is invoked
    Then the command redirects to /pl-override-edit

#### Scenario: Protocol detail routed to skill file

    Given the proposed addition is a multi-step workflow
    When context budget classification runs
    Then the content is classified as protocol detail
    And the user is advised to put it in a skill file instead

#### Scenario: Override conflict scan runs before edit

    Given a proposed change to BUILDER_BASE.md
    When /pl-edit-base processes the edit
    Then BUILDER_OVERRIDES.md is scanned for conflicts
    And any conflicts are presented before proceeding

#### Scenario: Additive-only principle enforced

    Given the edit attempts to delete existing content
    When /pl-edit-base validates the change
    Then explicit user confirmation is required for revisionary changes

### QA Scenarios

None.
