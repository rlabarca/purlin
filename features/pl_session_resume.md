# Feature: /pl-resume Session Checkpoint and Recovery Skill

> Label: "Agent Skills: /pl-resume"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The `/pl-resume` agent skill provides a two-mode mechanism for saving and restoring agent session state across context clears and terminal restarts. When an agent is about to run out of context, it invokes `/pl-resume save` to write a structured checkpoint file. When a new session starts (with or without the launcher), the agent invokes `/pl-resume` to read the checkpoint, gather fresh project state, and resume from where the previous session left off.

This skill is shared across all roles (Architect, Builder, QA). The launcher scripts handle fresh session bootstrap but provide no mid-session recovery. The delivery plan (`.purlin/cache/delivery_plan.md`) partially addresses multi-phase Builder work but does not capture per-step state within a feature's implementation protocol. This skill fills that gap.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-resume [save | <role>]
```

- **No argument:** Restore mode with role auto-detection.
- **`save`:** Save mode -- write a checkpoint file capturing current session state.
- **`<role>`** (one of `architect`, `builder`, `qa`): Restore mode with explicit role selection.
- **Invalid argument:** Print an error listing valid options (`save`, `architect`, `builder`, `qa`) and exit.

### 2.2 Save Mode (`/pl-resume save`)

The agent writes a structured checkpoint to `.purlin/cache/session_checkpoint.md`. The agent composes the file based on its own understanding of its current state (no automated extraction is needed).

The checkpoint file is written to disk but NOT committed. It survives `/clear` and terminal restarts as a regular file. The `.purlin/cache/` directory is gitignored.

#### 2.2.1 Common Checkpoint Fields (All Roles)

The checkpoint MUST include:

- **Role** (`architect`, `builder`, or `qa`)
- **Timestamp** (ISO 8601 format)
- **Branch** (current git branch)
- **Current Feature** (the feature being worked on, or "none")
- **In Progress** (plain-language description of what is actively in progress)
- **Done** (bulleted list of completed items this session)
- **Next** (numbered list of next steps, in order)
- **Uncommitted Changes** (summary from `git status`, or "None")
- **Notes** (open questions, blockers, or anything the resuming agent should know)

#### 2.2.2 Builder-Specific Fields

When the saving agent is the Builder, the checkpoint MUST additionally include:

- **Protocol Step** (current step in the per-feature implementation protocol: 0-preflight, 1-acknowledge/plan, 2-implement/document, 3-verify locally, 4-commit status tag)
- **Delivery Plan Context** (current phase number, phase status, features completed this phase)
- **Work Queue** (remaining features in priority order with priority labels)
- **Pending Decisions** (builder decisions not yet recorded in companion files)

#### 2.2.3 QA-Specific Fields

When the saving agent is QA, the checkpoint MUST additionally include:

- **Scenario Progress** (e.g., "5 of 8 scenarios completed")
- **Current Scenario** (name of the scenario being verified)
- **Discoveries** (discoveries recorded so far this session)
- **Verification Queue** (features already verified vs. remaining)

#### 2.2.4 Architect-Specific Fields

When the saving agent is the Architect, the checkpoint MUST additionally include:

- **Spec Reviews** (which spec reviews or updates are in progress)
- **Discovery Processing** (which discoveries have been reviewed, which are pending)

#### 2.2.5 Checkpoint File Format

The checkpoint is human-readable Markdown. The structure uses headings and labeled fields:

```markdown
# Session Checkpoint

**Role:** builder
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/cdd_status_monitor.md
**Step:** 3 -- Verify Locally (implementation committed, running tests)

### Done
- Read anchor nodes and prerequisites
- Implemented data layer with test harness
- Recorded [CLARIFICATION] for font-size in impl.md
- Committed implementation: abc1234

### Next
1. Run tests -- verify tests/cdd_status_monitor/tests.json shows PASS
2. Commit status tag: [Ready for Verification]
3. Run tools/cdd/status.sh to confirm TESTING transition
4. Move to next feature: cdd_spec_map.md

## Delivery Plan
Phase 2 of 3 -- IN_PROGRESS
Completed this phase: cdd_status_monitor.md
Remaining: cdd_spec_map.md, cdd_isolated_teams.md

## Work Queue
1. [HIGH] cdd_spec_map.md -- Phase 2
2. [NORMAL] cdd_isolated_teams.md -- Phase 2

## Uncommitted Changes
None

## Notes
Font-size decision needs Architect ack -- recorded as [CLARIFICATION] but may escalate.
```

### 2.3 Restore Mode (`/pl-resume`)

Restore mode follows a 7-step sequence. Each step is mandatory unless noted otherwise.

#### 2.3.1 Step 1 -- Role Detection (3-Tier Fallback)

The skill determines the agent's role using the following priority:

1. **Explicit argument:** If the user invoked `/pl-resume <role>`, use that role.
2. **System prompt inference:** Check if role identity markers are present in the current system prompt (e.g., "You are the Architect", "You are the Builder", "You are the QA"). If found, use the detected role.
3. **Ask user:** If neither method succeeds, prompt the user to select their role from `architect`, `builder`, `qa`.

#### 2.3.2 Step 2 -- Checkpoint Detection

- Check if `.purlin/cache/session_checkpoint.md` exists.
- If **found:** Read the file. Present the saved state as a summary block. Use it to orient the session (the checkpoint's "Next" list becomes the starting work plan).
- If **not found:** Print "No checkpoint found -- recovering from project state only." Proceed to Step 3.

#### 2.3.3 Step 3 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does not contain the role's base instructions (i.e., the agent was started without a launcher script).

When instruction reload is needed:
1. Read the 4 instruction layers in order:
   - `instructions/HOW_WE_WORK_BASE.md`
   - `instructions/{ROLE}_BASE.md`
   - `.purlin/HOW_WE_WORK_OVERRIDES.md`
   - `.purlin/{ROLE}_OVERRIDES.md`
2. Present a condensed "Role Compact" -- key mandates, prohibitions, and protocol summaries extracted from the instructions. This is NOT a full file dump; it is a focused digest of the most critical rules for the role.

When the system prompt already contains the role instructions (agent was started via launcher), skip this step entirely.

#### 2.3.4 Step 4 -- Command Table

- Read `instructions/references/{role}_commands.md`.
- Detect the current branch via `git rev-parse --abbrev-ref HEAD`.
- Print the appropriate variant (main branch or isolated session) verbatim.

#### 2.3.5 Step 5 -- Gather Fresh Project State

Execute the role's startup state-gathering sequence:

- Read `.purlin/config.json` for role-specific settings.
- Run `tools/cdd/status.sh` to regenerate the Critic report.
- Read `CRITIC_REPORT.md` -- the role-specific subsection under "Action Items by Role".
- Read `.purlin/cache/dependency_graph.json` for the feature graph.
- Check `git status` for uncommitted changes.
- Check `git log --oneline -10` for recent commit history.

Additionally, gather role-specific state:
- **Builder:** Read `.purlin/cache/delivery_plan.md` if it exists. Identify features in TODO state.
- **QA:** Identify features in TESTING state from the Critic report.
- **Architect:** Perform spec-level gap analysis on TODO/TESTING features.

#### 2.3.6 Step 6 -- Present Recovery Summary

Print a structured recovery summary:

```
--- Context Restored ---
Role:           [Architect | Builder | QA]
Branch:         [main | isolated/<name>]
Checkpoint:     [found -- resuming from <timestamp> | none]

[If checkpoint found:]
Resume Point:   <feature name> -- <what was in progress>
Next Steps:
  1. <first thing to do>
  2. <second thing>

[Always:]
Action Items:   [count] items from Critic report
[Builder only]  Delivery plan: Phase X of Y -- next: <feature>
[QA only]       Verification queue: N features in TESTING
Uncommitted:    [none | summary]
---
```

#### 2.3.7 Step 7 -- Cleanup and Confirm

- If a checkpoint file was read in Step 2, delete it (it has been consumed).
- Ask: "Ready to continue from here, or would you like to adjust?"
- If the user says "go" (or equivalent), begin executing the work plan starting with the first item.
- If the user provides modifications, adjust accordingly.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Save Writes Checkpoint File

    Given an agent is in an active session with role "builder"
    And the agent is working on features/cdd_status_monitor.md at protocol step 3
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint.md is created
    And the file contains "**Role:** builder"
    And the file contains a valid ISO 8601 timestamp
    And the file contains the current branch name

#### Scenario: Restore With Checkpoint

    Given .purlin/cache/session_checkpoint.md exists with role "builder" and timestamp "2026-02-28T15:30:00Z"
    When the agent invokes /pl-resume
    Then the checkpoint file is read
    And the recovery summary displays "Checkpoint: found -- resuming from 2026-02-28T15:30:00Z"
    And the checkpoint's Next list is presented as the work plan
    And the checkpoint file is deleted after presentation

#### Scenario: Restore Without Checkpoint

    Given .purlin/cache/session_checkpoint.md does not exist
    When the agent invokes /pl-resume builder
    Then the output contains "No checkpoint found -- recovering from project state only"
    And the Critic report is regenerated via tools/cdd/status.sh
    And the recovery summary is displayed with "Checkpoint: none"

#### Scenario: Role From Explicit Argument

    Given the agent's system prompt does not contain role identity markers
    When the agent invokes /pl-resume architect
    Then the role is set to "architect" without prompting the user
    And the Architect command table is printed
    And the Architect-specific state gathering runs

#### Scenario: Invalid Argument Prints Error

    Given the agent invokes /pl-resume invalid
    Then the output contains an error message
    And the error lists valid options: save, architect, builder, qa
    And no checkpoint file is written or read

#### Scenario: Checkpoint Cleanup After Restore

    Given .purlin/cache/session_checkpoint.md exists
    When the agent completes the restore sequence
    Then .purlin/cache/session_checkpoint.md no longer exists on disk

### Manual Scenarios (Human Verification Required)

#### Scenario: Builder Mid-Feature Resume

    Given a Builder agent is mid-implementation of a feature at protocol step 2
    When the Builder invokes /pl-resume save
    And the context is cleared
    And a new Builder session invokes /pl-resume
    Then the recovery summary shows the correct feature and protocol step
    And the Builder continues implementation from the saved step without repeating completed work

#### Scenario: QA Mid-Verification Resume

    Given a QA agent has verified 5 of 8 scenarios for a feature
    When the QA agent invokes /pl-resume save
    And the context is cleared
    And a new QA session invokes /pl-resume
    Then the recovery summary shows "5 of 8 scenarios completed"
    And the QA agent resumes verification at scenario 6

#### Scenario: Full Reboot Without Launcher

    Given a fresh Claude session is started without a launcher script (no system prompt)
    When the user types /pl-resume architect
    Then the skill reads all 4 instruction layers
    And presents a condensed Role Compact with key mandates and prohibitions
    And prints the Architect command table
    And gathers fresh project state
    And presents the recovery summary
