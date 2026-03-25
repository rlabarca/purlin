# Feature: Purlin Instruction Architecture

> Label: "Install, Update & Scripts: Purlin Instruction Architecture"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

## 1. Overview

The Purlin agent uses a combined instruction file (`PURLIN_BASE.md`) that replaces the four role-specific instruction files. It defines three operating modes with write-access boundaries, the mode-switching protocol, the Active Deviations protocol, the startup work-discovery flow, and commit attribution conventions. A single override file (`PURLIN_OVERRIDES.md`) replaces four role-specific overrides, organized by mode sections.

---

## 2. Requirements

### 2.1 Instruction File Structure

- `instructions/PURLIN_BASE.md` MUST define all three modes (Engineer, PM, QA) with activation triggers and write-access lists.
- The file MUST define open mode (read-only until a mode is activated).
- The file MUST define the mode-switching protocol (activation, pre-switch commit check, mode guard).
- The file MUST define the Active Deviations protocol (companion file table format, decision hierarchy, three Engineer-to-PM flows).
- The file MUST define the startup protocol (scan.sh invocation, work-by-mode presentation, mode activation).
- Target size: 500-600 lines (detailed protocols deferred to skills).

### 2.2 Override File Structure

- `.purlin/PURLIN_OVERRIDES.md` MUST be organized by mode sections: General, Engineer Mode, PM Mode, QA Mode.
- `purlin-config-sample/PURLIN_OVERRIDES.md` MUST provide the template with placeholder sections.

### 2.3 Command Reference

- `instructions/references/purlin_commands.md` MUST provide a mode-organized command table.
- The table MUST list: Common skills, Engineer Mode skills, PM Mode skills, QA Mode skills.
- The startup protocol MUST read and print this table.

### 2.4 Spec Ownership Model

- The instruction file MUST define file ownership: PM owns behavioral specs and design/policy anchors; Engineer owns code, arch anchors, companions, and skill files; QA owns discovery sidecar lifecycle.
- The instruction file MUST describe the Active Deviations table format with columns: Spec says, Implementation does, Tag, PM status.
- The instruction file MUST describe the decision hierarchy: spec is baseline, active deviations are overrides, with PENDING/ACCEPTED/REJECTED status.

### 2.5 Instruction Files Are Code

- `PURLIN_BASE.md` is an implementation artifact owned by the Engineer (Builder in the current model).
- Changes to the instruction file are driven by feature specs, same as any other code change.
- The instruction file is NOT a specification — it is an implementation of the spec in this feature file.

---

## 3. Scenarios

### Unit Tests

#### Scenario: PURLIN_BASE.md defines three modes

    Given instructions/PURLIN_BASE.md exists
    When the content is parsed
    Then it contains a section defining Engineer Mode
    And it contains a section defining PM Mode
    And it contains a section defining QA Mode

#### Scenario: PURLIN_BASE.md defines open mode

    Given instructions/PURLIN_BASE.md exists
    When the content is parsed
    Then it states the agent must not write files until a mode is activated

#### Scenario: Command reference organized by mode

    Given instructions/references/purlin_commands.md exists
    When the content is parsed
    Then it contains an "Engineer Mode" section
    And it contains a "PM Mode" section
    And it contains a "QA Mode" section
    And it contains a "Common" section

#### Scenario: Override template has mode sections

    Given purlin-config-sample/PURLIN_OVERRIDES.md exists
    When the content is parsed
    Then it contains a "General" section
    And it contains an "Engineer Mode" section
    And it contains a "PM Mode" section
    And it contains a "QA Mode" section

#### Scenario: Active Deviations protocol is documented

    Given instructions/PURLIN_BASE.md exists
    When the content is parsed
    Then it contains the Active Deviations table format
    And it describes INFEASIBLE, inline deviation, and SPEC_PROPOSAL flows

#### Scenario: Startup protocol references scan.sh

    Given instructions/PURLIN_BASE.md exists
    When the content is parsed
    Then it instructs the agent to run scan.sh for project state
    And it instructs the agent to present work organized by mode

### QA Scenarios

#### Scenario: Instruction file size within target

    Given instructions/PURLIN_BASE.md exists
    When the line count is measured
    Then it is between 200 and 700 lines

## Regression Guidance
- Verify PURLIN_BASE.md does not reference old role names (Architect, Builder) except in transition context
- Verify the instruction file loads correctly when appended via --append-system-prompt-file
- Verify override file sections are not empty (template should have placeholder comments)
