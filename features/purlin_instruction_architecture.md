# Feature: Purlin Instruction Architecture

> Label: "Tool: Purlin Instruction Architecture"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

## 1. Overview

The Purlin agent uses a single instruction file (`PURLIN_BASE.md`) that replaces both `PURLIN_BASE.md` and the four role-specific instruction files. It contains the CDD philosophy, mode definitions with write-access boundaries, the mode-switching protocol, the Active Deviations protocol, knowledge colocation rules, the startup work-discovery flow, and commit attribution conventions. A single override file (`PURLIN_OVERRIDES.md`) replaces `PURLIN_OVERRIDES.md` and four role-specific overrides, organized by mode sections. The launcher loads only `PURLIN_BASE.md` + `PURLIN_OVERRIDES.md` — no separate HOW_WE_WORK file.

---

## 2. Requirements

### 2.1 Instruction File Structure

- `instructions/PURLIN_BASE.md` is the SOLE instruction file. The launcher loads it directly — no separate `PURLIN_BASE.md`.
- The file MUST contain: CDD philosophy, mode definitions with activation triggers, open mode write block, mode-switching protocol (guard, pre-switch checks, iTerm identity), startup protocol, feature lifecycle, testing split, layered instructions, and shutdown protocol.
- The file MUST NOT contain detailed definitions that belong in reference files. Instead it references: `references/file_classification.md`, `references/commit_conventions.md`, `references/active_deviations.md`, `references/knowledge_colocation.md`.
- Mode write-access rules MUST say "All files classified as CODE/SPEC/QA-OWNED in `references/file_classification.md`" — not inline file pattern lists.
- Target size: 200-300 lines (definitions extracted to references, protocols deferred to skills).

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

- `PURLIN_BASE.md` is an implementation artifact owned by the Engineer (Engineer in the current model).
- Changes to the instruction file are driven by feature specs, same as any other code change.
- The instruction file is NOT a specification — it is an implementation of the spec in this feature file.

### 2.6 Base Instructions vs. Skill Protocols

- PURLIN_BASE.md MUST contain: philosophy, mode definitions, write-access boundaries, mode switching protocol, ownership model, knowledge colocation, lifecycle, testing split.
- PURLIN_BASE.md MUST NOT contain: detailed step-by-step workflow protocols, interpretation logic, or decision trees for specific operations. These belong in skill files.
- **Skills first:** When deciding where logic belongs, default to putting it in a skill. Only put it in the base file if it needs to be active across ALL states of the agent (e.g., the mode guard must always be on, regardless of which skill is running).
- The verify workflow (Phase A/B, smoke gate, regression gate) is a SKILL protocol (`/pl-verify`).
- The build workflow (pre-flight, plan, implement, verify, status tag) is a SKILL protocol (`/pl-build`).
- Work interpretation logic (how to classify scan results into mode-specific work items) is a SKILL protocol (`/pl-status`). The startup protocol in PURLIN_BASE.md invokes `/pl-status`, it does not duplicate its logic.
- **Work discovery delegation:** `/pl-status` is the single source of "what work exists." Workflow skills (`/pl-build`, `/pl-verify`, `/pl-spec`) delegate to `/pl-status` for their work list — they do not call `scan.sh` directly or re-implement detection logic.
- Base instructions set BOUNDARIES. Skills carry PROTOCOLS and LOGIC.

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

#### Scenario: Engineer work includes regression failures

    Given instructions/PURLIN_BASE.md exists
    When the content is parsed
    Then the Engineer work criteria include regression_status: FAIL

### QA Scenarios

#### Scenario: Instruction file size within target @auto

    Given instructions/PURLIN_BASE.md exists
    When the line count is measured
    Then it is between 250 and 500 lines

#### Scenario: Launcher loads only PURLIN_BASE.md @auto

    Given pl-run.sh exists
    When the prompt assembly section is examined
    Then it does NOT concatenate PURLIN_BASE.md
    And it loads PURLIN_BASE.md as the sole base instruction file

## Regression Guidance
- Verify PURLIN_BASE.md does not reference old role names (PM, Engineer) except in transition context
- Verify the instruction file loads correctly when appended via --append-system-prompt-file
- Verify override file sections are not empty (template should have placeholder comments)
- Verify PURLIN_BASE.md is NOT loaded by pl-run.sh (old agents still load it separately)
