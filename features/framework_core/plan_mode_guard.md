# Feature: Plan Mode Exit Guard

> Label: "Tool: Plan Mode Exit Guard"
> Category: "Framework Core"
> Prerequisite: purlin_mode_system.md

## 1. Overview

When an agent exits Claude Code's plan mode via `ExitPlanMode`, the Purlin mode state persists from before plan mode entry. This allows the agent to bypass mode enforcement — writing code without first activating a mode or creating a spec. A `PostToolUse` hook on `ExitPlanMode` clears the persisted mode state, forcing the agent to explicitly re-activate a mode before any writes.

### Problem

1. Agent is in Engineer mode (`.purlin/runtime/current_mode` = `engineer`)
2. Agent enters Claude Code plan mode (read-only)
3. Agent exits plan mode via `ExitPlanMode`
4. Agent calls `Edit` on a code file — mode guard reads stale `engineer` from disk and allows the write
5. No spec was written, no mode was activated, no workflow was followed

### Solution

A `PostToolUse` hook on `ExitPlanMode` clears `.purlin/runtime/current_mode` to force explicit mode reactivation. The existing mode guard (PreToolUse on Write/Edit/NotebookEdit) already blocks writes when no mode is active — the missing piece is resetting the mode on plan exit.

---

## 2. Requirements

### 2.1 PostToolUse Hook on ExitPlanMode

- A `PostToolUse` hook MUST fire after `ExitPlanMode` completes.
- The hook MUST clear `.purlin/runtime/current_mode` (write empty string or delete the file).
- The hook MUST print a message to the agent: `"Plan mode exited. Mode cleared — activate a mode before writing files."`

### 2.2 Mode Guard Interaction

- The existing mode guard (PreToolUse on Write/Edit/NotebookEdit) already blocks writes when mode is `none` or `None`.
- After the ExitPlanMode hook fires, the next Write/Edit attempt MUST be blocked by the mode guard with: `"No mode active. Activate a mode before writing files."`
- No changes to the mode guard script are required.

### 2.3 Agent Behavior After Plan Exit

- After ExitPlanMode, the agent MUST activate a mode via `purlin:mode` or a mode-activating skill before writing any files.
- The agent definition (`agents/purlin.md`) MUST document this: "After ExitPlanMode, your mode has been cleared. Activate the appropriate mode before writing."

### 2.4 Re-Activation is Lightweight

- The agent does not need to re-run the full startup flow.
- A simple `purlin:mode <mode>` or invoking a mode-activating skill (e.g., `purlin:build`, `purlin:spec`) is sufficient.
- Terminal identity updates as part of normal mode activation.

### 2.5 Hook Script

- The hook script MUST be at `hooks/scripts/plan-exit-mode-clear.sh`.
- The script MUST be idempotent — safe to run even if no mode was active.
- The script MUST NOT error if `.purlin/runtime/current_mode` doesn't exist.

---

## 3. Scenarios

### Unit Tests

#### Scenario: ExitPlanMode clears persisted mode state

    Given the agent is in Engineer mode
    And .purlin/runtime/current_mode contains "engineer"
    When ExitPlanMode is called
    Then .purlin/runtime/current_mode is empty or deleted
    And the agent receives message "Plan mode exited. Mode cleared"

#### Scenario: Write blocked after plan exit

    Given the agent was in Engineer mode before plan mode
    And ExitPlanMode has been called (mode cleared by hook)
    When the agent attempts to Edit a code file
    Then the mode guard blocks the write
    And the error message is "No mode active. Activate a mode before writing files."

#### Scenario: Mode reactivation after plan exit allows writes

    Given ExitPlanMode was called (mode cleared)
    When the agent calls purlin:mode engineer
    Then .purlin/runtime/current_mode contains "engineer"
    And the agent can write to code files

#### Scenario: Hook is idempotent when no mode was active

    Given no mode is active (.purlin/runtime/current_mode is empty)
    When ExitPlanMode is called
    Then the hook runs without error
    And .purlin/runtime/current_mode remains empty

#### Scenario: Skill invocation after plan exit activates mode

    Given ExitPlanMode was called (mode cleared)
    When the agent invokes purlin:build (a mode-activating skill)
    Then Engineer mode is activated
    And the agent can write to code files

### QA Scenarios

#### Scenario: Full plan-to-implementation workflow @manual

    Given the agent has a task requiring code changes
    When the agent enters plan mode, creates a plan, and exits
    Then the agent must activate PM mode and write a spec before coding
    And activating Engineer mode and writing code succeeds
    And skipping the spec and writing code directly is blocked

## Regression Guidance

- Verify ExitPlanMode hook fires (PostToolUse matcher works)
- Verify mode state file is cleared after plan exit
- Verify mode guard blocks writes after plan exit
- Verify mode reactivation works normally after plan exit
- Verify hook doesn't interfere with non-Purlin projects (check for .purlin/ directory)
