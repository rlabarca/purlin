# Feature: Purlin Mode System

> Label: "Install, Update & Scripts: Purlin Mode System"
> Category: "Install, Update & Scripts"
> Prerequisite: features/purlin_agent_launcher.md

## 1. Overview

The mode system is the core behavioral mechanism of the Purlin unified agent. Three modes (Engineer, PM, QA) define write-access boundaries and workflow protocols. Modes are activated by skill invocations or the explicit `/pl-mode` command. A mode guard prevents file writes outside the active mode's access list. Cross-mode capabilities allow QA to run tests without switching to Engineer mode.

---

## 2. Requirements

### 2.1 Mode Activation

- Skills MUST declare their mode via `**Purlin mode: <mode>**` header.
- Invoking a mode-activating skill MUST activate that mode.
- `/pl-mode <pm|engineer|qa>` MUST explicitly switch mode.
- Until a mode is activated (open mode), the agent MUST NOT write to any file.

### 2.2 Mode Write Access

- **Engineer mode** write access: all code, tests, scripts, app config, `features/arch_*.md`, `features/*.impl.md`, `features/*.discoveries.md` (recording only), skill files, instruction files.
- **PM mode** write access: `features/*.md` (behavioral specs), `features/design_*.md`, `features/policy_*.md`, design artifacts.
- **QA mode** write access: `features/*.discoveries.md` (lifecycle), QA scenario tags (`@auto`/`@manual`), regression JSON, `tests/qa/`.
- Each mode MUST NOT write to files outside its access list.

### 2.3 Mode Guard

- Before any file write, the agent MUST check if the target file is in the current mode's write-access list.
- If no mode is active: suggest the appropriate mode.
- If wrong mode is active: suggest switching.

### 2.4 Pre-Switch Check

- Before switching modes, if uncommitted work exists: prompt to commit first.
- The commit MUST use the current mode's prefix convention.

### 2.5 Cross-Mode Test Execution

- QA mode MUST be able to invoke `/pl-unit-test`, `/pl-web-test`, `/pl-fixture`, `/pl-server` for verification without activating Engineer mode.
- QA cross-mode execution MUST NOT allow modifying application code.
- If QA discovers a test failure, it MUST record a `[BUG]` discovery, not fix the code.

### 2.6 Dual Skill Headers

- All skill files MUST have both legacy (`**Purlin command owner:**`) and new (`**Purlin mode:**`) headers.
- Legacy agents match on line 1 (old format). The Purlin agent matches on line 2 (new format).
- New purlin-only skills MUST have `**Purlin command: Purlin agent only**` on line 1 so legacy agents skip them.

### 2.7 Skill Consolidation

- `/pl-release` consolidates `/pl-release-check`, `/pl-release-run`, `/pl-release-step` with subcommands.
- `/pl-regression` consolidates `/pl-regression-run`, `/pl-regression-author`, `/pl-regression-evaluate` with subcommands.
- `/pl-remote` consolidates `/pl-remote-push`, `/pl-remote-pull`, `/pl-remote-add` with subcommands.
- Old consolidated skill files MUST be deleted.
- `/pl-edit-base` MUST be removed (absorbed into Engineer mode).

### 2.8 Commit Attribution

- Engineer commits: `feat()`, `fix()`, `test()` prefixes.
- PM commits: `spec()`, `design()` prefixes.
- QA commits: `qa()`, `status()` prefixes.
- All commits MUST include `Purlin-Mode: <mode>` trailer.

### 2.9 iTerm Terminal Identity

- On mode activation, the agent MUST set the iTerm badge to the mode name (e.g., `Engineer`, `PM`, `QA`).
- On mode activation, the agent MUST set the iTerm remote control name to `<project> - <mode>` (e.g., `purlin - Engineer`).
- When no mode is active (open mode), the iTerm badge MUST be `Purlin`.
- When no mode is active (open mode), the iTerm remote control name MUST be `<project> - Purlin`.
- `<project>` is derived from the working directory name (basename of the project root).
- The agent MUST use iTerm2 proprietary escape sequences: badge via `\033]1337;SetBadgeFormat=<base64>\a`, remote control name via `\033]1337;SetMark\a` or the appropriate `\033]0;<name>\a` title sequence.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Skill activates correct mode

    Given the agent is in open mode (no mode active)
    When the user invokes /pl-build
    Then Engineer mode is activated
    And the agent can write to code files

#### Scenario: Mode guard blocks write in wrong mode

    Given the agent is in QA mode
    When the agent attempts to write to src/app.py
    Then the write is blocked
    And the agent suggests switching to Engineer mode

#### Scenario: Cross-mode QA runs tests without switching

    Given the agent is in QA mode
    When the user invokes /pl-unit-test
    Then tests are executed
    And QA mode remains active (not switched to Engineer)
    And no application code files are modified

#### Scenario: Pre-switch commit prompt

    Given the agent is in Engineer mode with uncommitted changes
    When the user invokes /pl-spec (PM mode skill)
    Then the agent prompts to commit the uncommitted work
    And waits for user confirmation before switching

#### Scenario: Dual skill header for legacy compatibility

    Given pl-build.md skill file
    When a legacy Builder agent reads the file
    Then line 1 contains "Purlin command owner: Builder"
    And the legacy agent recognizes it as a Builder command

#### Scenario: Purlin-only skill blocked by legacy agents

    Given pl-mode.md skill file
    When a legacy Builder agent reads the file
    Then line 1 contains "Purlin command: Purlin agent only"
    And the legacy agent skips this command

#### Scenario: Consolidated release skill subcommands

    Given the agent is in Engineer mode
    When the user invokes /pl-release check
    Then the release check protocol executes
    And old /pl-release-check file does not exist

#### Scenario: pl-anchor dual-mode activation

    Given the agent is in open mode
    When the user invokes /pl-anchor arch_data_layer
    Then Engineer mode is activated (arch_* target)

#### Scenario: pl-anchor activates PM for design anchors

    Given the agent is in open mode
    When the user invokes /pl-anchor design_visual_standards
    Then PM mode is activated (design_* target)

#### Scenario: Commit attribution with mode trailer

    Given the agent is in Engineer mode
    When the agent commits code changes
    Then the commit message starts with "feat(" or "fix(" or "test("
    And the commit body contains "Purlin-Mode: Engineer"

#### Scenario: iTerm badge set on mode activation

    Given the agent is in open mode
    When the user activates Engineer mode
    Then the iTerm badge is set to "Engineer"
    And the iTerm remote control name is set to "<project> - Engineer"

#### Scenario: iTerm badge reset to Purlin in open mode

    Given the agent has just started with no mode active
    Then the iTerm badge is "Purlin"
    And the iTerm remote control name is "<project> - Purlin"

#### Scenario: iTerm badge updates on mode switch

    Given the agent is in PM mode with iTerm badge "PM"
    When the user switches to QA mode
    Then the iTerm badge changes to "QA"
    And the iTerm remote control name changes to "<project> - QA"

### QA Scenarios

#### Scenario: Open mode prevents writes @auto

    Given the agent has just started with no mode active
    When the user asks to "edit the config file"
    Then the agent suggests activating Engineer mode first
    And does not write to any file

#### Scenario: Old consolidated skills are deleted @auto

    Given the project after skill consolidation
    When checking .claude/commands/
    Then pl-release-check.md does not exist
    And pl-release-run.md does not exist
    And pl-release-step.md does not exist
    And pl-regression-run.md does not exist
    And pl-regression-author.md does not exist
    And pl-regression-evaluate.md does not exist
    And pl-remote-push.md does not exist
    And pl-remote-pull.md does not exist
    And pl-remote-add.md does not exist
    And pl-edit-base.md does not exist

## Regression Guidance
- Verify all 33 skill files have both legacy and new headers
- Verify no skill file has ONLY the new header (breaks legacy agents)
- Verify cross-mode test execution does not leave QA in Engineer mode
- Verify /pl-anchor mode activation depends on target prefix, not the skill itself
- Verify iTerm badge and remote control name update on every mode switch
- Verify open mode sets badge to "Purlin", not blank
