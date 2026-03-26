# Feature: /pl-mode Mode Switch

> Label: "Agent Skills: Common: /pl-mode Mode Switch"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_mode_system.md

## 1. Overview

The `/pl-mode` skill explicitly switches the Purlin agent's operating mode (Engineer, PM, or QA). It enforces the pre-switch commit check and companion file gate, updates the iTerm terminal identity, and prints the mode's command subset.

---

## 2. Requirements

### 2.1 Mode Switching

- MUST accept one argument: `pm`, `engineer`, or `qa`.
- MUST enforce the pre-switch check before switching (uncommitted work prompt, companion file gate for Engineer mode exit).
- MUST update iTerm badge and terminal title to reflect the new mode, preserving the current branch context in parentheses (e.g., `Engineer (main)`, not bare `Engineer`). See `features/terminal_identity.md` §2.4.
- MUST print the mode's command subset from `instructions/references/purlin_commands.md`.

### 2.2 Shared Skill

- This skill does NOT activate a mode -- it IS the mode switch.
- Available in all modes including open mode.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Switch from open mode to Engineer

    Given the agent is in open mode
    And the current branch is "main"
    When /pl-mode engineer is invoked
    Then Engineer mode is activated
    And the iTerm badge shows "Engineer (main)"

#### Scenario: Switch prompts for uncommitted work

    Given the agent is in Engineer mode with uncommitted changes
    When /pl-mode pm is invoked
    Then the agent prompts to commit first

### Manual Scenarios (Human Verification Required)

None.
