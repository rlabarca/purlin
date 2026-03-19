# Feature: Quickstart README

> Label: "Tool: Quickstart README"
> Category: "Install, Update & Scripts"
> Prerequisite: features/project_init.md
> Prerequisite: features/init_preflight_checks.md

## 1. Overview

A "Quick Start" section in README.md provides a complete path from a blank terminal to a running Purlin project, written for users who are new to the terminal. It lists prerequisites with exact install commands, provides a single copy-paste block for project setup, and directs users to the PM agent as the guided entry point. The section is short enough to read in under two minutes.

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

### 2.3 Project Setup Subsection

- MUST present a single copy-paste code block that performs the full setup sequence:
  1. `mkdir my-app && cd my-app`
  2. `git init`
  3. `git submodule add <purlin-repo-url> purlin`
  4. `./purlin/pl-init.sh`
  5. `git add -A && git commit -m "init purlin"`
- The block MUST use the actual Purlin repository URL.
- If init.sh detects missing prerequisites, it will tell the user what to install (see init_preflight_checks). The README does NOT need to duplicate that logic but SHOULD mention that the setup script checks for you.
- After the setup block, MUST show `./pl-run-pm.sh` as the next step, framed as "Start designing."
- MUST include a one-sentence explanation: the PM agent will ask what you're building and create your first spec.

### 2.4 Tone and Audience

- Written for non-technical users (product managers, designers).
- Avoid unexplained jargon. Terms like "submodule", "CLI", "stdout", "daemon" MUST NOT appear without a plain-language explanation or MUST be avoided entirely. Where "submodule" appears in a command, a parenthetical like "(this adds Purlin to your project)" is sufficient.
- Use second person ("you") and imperative mood ("Install", "Run", "Open").
- The setup block is one copy-paste action even though it contains multiple commands. Frame it that way: "Copy and paste this into your terminal."

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
    Then it contains a git installation command
    And it contains a Claude Code installation command referencing @anthropic-ai/claude-code
    And it contains a Node.js installation command or note that it is optional

#### Scenario: Setup block contains the full sequence

    Given the Quick Start section of README.md
    Then it contains a code block with "mkdir" and "cd"
    And the code block contains "git init"
    And the code block contains "git submodule add" with the Purlin repository URL
    And the code block contains "pl-init.sh"
    And the code block contains "git commit"

#### Scenario: PM agent is the entry point after setup

    Given the Quick Start section of README.md
    Then it contains "pl-run-pm.sh"
    And "pl-run-pm.sh" appears after the setup code block
    And there is explanatory text near it describing what happens next

#### Scenario: Section length is within limit

    Given the Quick Start section of README.md
    When counting non-blank lines
    Then the count is at most 40

#### Scenario: No unexplained jargon

    Given the Quick Start section of README.md
    Then it does not contain the word "submodule" without a parenthetical explanation
    And it does not contain "CLI" without explanation
    And it does not contain "stdout" or "daemon"

### Manual Scenarios (Human Verification Required)

#### Scenario: A non-technical user can follow the Quick Start

    Given a person unfamiliar with terminal commands
    When they read the Quick Start section top to bottom
    Then every step is unambiguous and copy-pasteable
    And they can reach a running PM agent session by following the steps exactly
    And no step requires knowledge not provided in a preceding step
