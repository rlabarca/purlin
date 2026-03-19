# Feature: Quickstart README

> Label: "Tool: Quickstart README"
> Category: "Install, Update & Scripts"
> Prerequisite: features/project_init.md
> Prerequisite: features/init_new_project_mode.md

## 1. Overview

A "Quick Start" section in README.md provides a complete path from a blank terminal to a running Purlin project, written for users who are new to the terminal. It lists prerequisites with exact install commands, shows the single-command project creation flow, and directs users to the PM agent as the guided entry point. The section is short enough to read in under two minutes.

---

## 2. Requirements

### 2.1 Placement and Length

- The Quick Start section MUST appear after the current "Overview" section and before "Core Concepts".
- The section heading MUST be `## Quick Start`.
- Total length MUST NOT exceed 40 lines of rendered markdown (excluding blank lines between blocks).
- The section MUST be self-contained: a user reading only this section can get from zero to a running PM agent session.

### 2.2 Prerequisites Subsection

- MUST list each prerequisite with its exact install command:
  - Homebrew (macOS only): the standard curl-based installer.
  - git: `brew install git` (macOS) with a note that Linux users use their package manager.
  - Node.js: `brew install node` (needed for Playwright web testing; note this is optional).
  - Claude Code: `npm install -g @anthropic-ai/claude-code`.
- Each install command MUST be copy-pasteable with no placeholders.
- MUST note which prerequisites are macOS-specific or optional.

### 2.3 Project Creation Subsection

- MUST show the `--new` flag project creation as the primary path: a single command that creates the project.
- MUST include `cd <name>` after project creation.
- MUST end with `./pl-run-pm.sh` as the final command, framed as "Start designing."
- MUST include a one-sentence explanation: the PM agent will ask what you're building and create the first spec.

### 2.4 Tone and Audience

- Written for non-technical users (product managers, designers).
- Avoid unexplained jargon. Terms like "submodule", "CLI", "stdout", "daemon" MUST NOT appear without a plain-language explanation or MUST be avoided entirely.
- Use second person ("you") and imperative mood ("Install", "Run", "Open").
- No more than 3 terminal commands visible to the user (prerequisites block can be one combined block; project creation is one command; starting the PM is one command).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Quick Start section exists at correct position

    Given the README.md file
    When parsed for level-2 headings
    Then a heading "Quick Start" exists
    And it appears after the "Overview" heading
    And it appears before the "Core Concepts" heading

#### Scenario: Prerequisites include install commands

    Given the Quick Start section of README.md
    Then it contains "brew install git" or equivalent git install command
    And it contains a Claude Code installation command referencing @anthropic-ai/claude-code
    And it contains "brew install node" or equivalent node install command

#### Scenario: Project creation uses --new flag

    Given the Quick Start section of README.md
    Then it contains "init.sh --new" (the single-command project creation)
    And it contains "cd " followed by a project name placeholder

#### Scenario: PM agent is the entry point

    Given the Quick Start section of README.md
    Then it contains "pl-run-pm.sh"
    And "pl-run-pm.sh" appears after the project creation command
    And there is explanatory text near it describing what happens next

#### Scenario: Section length is within limit

    Given the Quick Start section of README.md
    When counting non-blank lines
    Then the count is at most 40

#### Scenario: No unexplained jargon

    Given the Quick Start section of README.md
    Then it does not contain the word "submodule" without explanation
    And it does not contain "CLI" without explanation
    And it does not contain "stdout" or "daemon"

### Manual Scenarios (Human Verification Required)

#### Scenario: A non-technical user can follow the Quick Start

    Given a person unfamiliar with terminal commands
    When they read the Quick Start section top to bottom
    Then every step is unambiguous and copy-pasteable
    And they can reach a running PM agent session by following the steps exactly
    And no step requires knowledge not provided in a preceding step
