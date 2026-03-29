# Feature: purlin:mode Mode Switch

> Label: "Agent Skills: Common: purlin:mode Mode Switch"
> Category: "Agent Skills: Common"
> Prerequisite: purlin_mode_system.md

## 1. Overview

The `purlin:mode` skill explicitly switches the Purlin agent's operating mode (Engineer, PM, or QA). When no mode is active, the agent is in **default mode** — a read-only research state where no file writes or commits are permitted. The skill enforces the pre-switch commit check and companion file gate, updates the iTerm terminal identity, and prints the mode's command subset.

---

## 2. Requirements

### 2.1 Mode Switching

- MUST accept one argument: `pm`, `engineer`, or `qa`.
- MUST enforce the pre-switch check before switching (uncommitted work prompt, companion file gate for Engineer mode exit).
- MUST update iTerm badge and terminal title to reflect the new mode, preserving the current branch context in parentheses (e.g., `Engineer (main)`, not bare `Engineer`). See `features/terminal_identity.md` §2.4.
- MUST print the mode's command subset from `references/purlin_commands.md`.

### 2.2 No-Argument Status Display

When invoked with no arguments, `purlin:mode` displays the current mode status instead of switching:

- Current mode name (or "Default mode (read-only)" if no mode is active)
- Available skills for the current mode (read from `references/purlin_commands.md`)
- If in default mode: remind that changes require activating a mode
- Hint: "Switch with `purlin:mode <pm|engineer|qa>`"

This is read-only — no mode change, no terminal identity update.

### 2.3 Shared Skill

- This skill does NOT activate a mode -- it IS the mode switch.
- Available in all modes including open mode.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Switch from open mode to Engineer

    Given the agent is in open mode
    And the current branch is "main"
    When purlin:mode engineer is invoked
    Then Engineer mode is activated
    And the terminal identity shows "Eng(main) | <project>"

#### Scenario: Switch prompts for uncommitted work

    Given the agent is in Engineer mode with uncommitted changes
    When purlin:mode pm is invoked
    Then the agent prompts to commit first

#### Scenario: No-arg shows current mode and available skills

    Given the agent is in Engineer mode
    When purlin:mode is invoked with no arguments
    Then the output shows "Current mode: Engineer"
    And lists the Engineer mode skills
    And shows "Switch with purlin:mode <pm|engineer|qa>"
    And no mode change occurs

#### Scenario: No-arg in default mode shows read-only status

    Given the agent is in default mode (no mode active)
    When purlin:mode is invoked with no arguments
    Then the output shows "Default mode (read-only)"
    And reminds that changes require activating a mode
    And lists all modes with their descriptions
    And shows "Switch with purlin:mode <pm|engineer|qa>"

### Manual Scenarios (Human Verification Required)

None.
