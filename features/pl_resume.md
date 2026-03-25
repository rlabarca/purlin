# Feature: /pl-resume Session Resume

> Label: "Agent Skills: Common: /pl-resume Session Resume"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_agent_launcher.md

## 1. Overview

The `/pl-resume` skill saves and restores agent session state across context clears and session restarts. It detects the agent role (including `purlin`), reads checkpoint files, gathers fresh project state via `scan.sh`, restores active mode, and recovers orphaned worktree branches.

---

## 2. Requirements

### 2.1 Save Mode

- `/pl-resume save` writes a checkpoint file to `.purlin/cache/session_checkpoint_purlin.md`.
- Checkpoint includes: active mode, mode history, delivery plan state, in-progress feature, next steps, uncommitted changes summary.

### 2.2 Restore Mode

- `/pl-resume` (no arguments) executes the recovery sequence.
- Role detection MUST accept `purlin` alongside legacy roles.
- MUST look for `"Role Definition: The Purlin Agent"` in system prompt for auto-detection.
- MUST restore the active mode from the checkpoint.
- MUST detect and offer to resume or clean up orphaned worktree branches.

### 2.3 Merge Recovery

- `/pl-resume merge-recovery` resolves pending merges from `.purlin/cache/merge_pending/*.json`.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Save checkpoint includes active mode

    Given the agent is in Engineer mode working on feature "auth_flow"
    When /pl-resume save is invoked
    Then .purlin/cache/session_checkpoint_purlin.md is created
    And it contains "Active Mode: Engineer"

#### Scenario: Restore detects purlin role

    Given a session_checkpoint_purlin.md exists
    When /pl-resume is invoked in a fresh session
    Then the purlin role is detected
    And the checkpoint is read and presented

### Manual Scenarios (Human Verification Required)

None.
