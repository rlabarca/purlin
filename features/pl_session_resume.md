# Feature: /pl-resume Session Checkpoint and Recovery Skill

> Label: "Agent Skills: Common: /pl-resume Session Resume"
> Category: "Agent Skills: Common"
> Prerequisite: features/policy_critic.md

[Complete]

## 1. Overview

The `/pl-resume` agent skill provides a two-mode mechanism for saving and restoring agent session state across context clears and terminal restarts. When an agent is about to run out of context, it invokes `/pl-resume save` to write a structured checkpoint file. When a new session starts (with or without the launcher), the agent invokes `/pl-resume` to read the checkpoint, gather fresh project state, and resume from where the previous session left off.

This skill is shared across all roles (Architect, Builder, QA, PM). The launcher scripts handle fresh session bootstrap but provide no mid-session recovery. The delivery plan (`.purlin/delivery_plan.md`) partially addresses multi-phase Builder work but does not capture per-step state within a feature's implementation protocol. This skill fills that gap.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-resume [save | <role>]
```

- **No argument:** Restore mode with role auto-detection.
- **`save`:** Save mode -- write a checkpoint file capturing current session state.
- **`<role>`** (one of `architect`, `builder`, `qa`, `pm`): Restore mode with explicit role selection.
- **Invalid argument:** Print an error listing valid options (`save`, `architect`, `builder`, `qa`, `pm`) and exit.

### 2.2 Save Mode (`/pl-resume save`)

The agent writes a structured checkpoint to a **role-scoped** file: `.purlin/cache/session_checkpoint_<role>.md` (e.g., `session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`). The agent composes the file based on its own understanding of its current state (no automated extraction is needed).

Role-scoped files ensure that concurrent agents can save checkpoints independently without overwriting each other. Each role's checkpoint is isolated — a Builder save never affects an Architect's saved state, and vice versa.

The checkpoint file is written to disk but NOT committed. It survives `/clear` and terminal restarts as a regular file. The `.purlin/cache/` directory is gitignored.

#### 2.2.1 Common Checkpoint Fields (All Roles)

The checkpoint MUST include:

- **Role** (`architect`, `builder`, `qa`, or `pm`)
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
- **Delivery Plan** (single line: "Phase X of Y -- STATUS", or "No delivery plan")
- **Execution Group** (current execution group: which phases are in the group, group number, or "N/A" if no delivery plan)
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

#### 2.2.5 PM-Specific Fields

When the saving agent is the PM, the checkpoint MUST additionally include:

- **Spec Drafts** (which feature specs are being authored or refined)
- **Figma Context** (which Figma files or frames are being referenced, or "None")
- **Probing Round** (current round in the Probing Question Protocol, if active, or "N/A")

#### 2.2.6 Checkpoint File Format

The checkpoint file path is `.purlin/cache/session_checkpoint_<role>.md` where `<role>` is the agent's current role (`architect`, `builder`, `qa`, or `pm`). For example, a Builder save produces `session_checkpoint_builder.md`.

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
Execution Group: Group 2 (Phases 2, 3)
Completed this phase: cdd_status_monitor.md
Remaining: cdd_spec_map.md, cdd_qa_effort_display.md

## Work Queue
1. [HIGH] cdd_spec_map.md -- Phase 2
2. [NORMAL] cdd_qa_effort_display.md -- Phase 2

## Uncommitted Changes
None

## Notes
Font-size decision needs Architect ack -- recorded as [CLARIFICATION] but may escalate.
```

### 2.3 Restore Mode (`/pl-resume`)

Restore mode follows an 8-step sequence. Each step is mandatory unless noted otherwise.

#### 2.3.0 Step 0 -- Stale Session State Cleanup

Clear any stale session state carried over from the previous session. This includes resetting internal turn counters or budget trackers if the agent runtime maintains them. If no such state exists in the current runtime, this step is a no-op and may be skipped silently.

#### 2.3.1 Step 1 -- Role Detection (4-Tier Fallback)

The skill determines the agent's role using the following priority:

1. **Explicit argument:** If the user invoked `/pl-resume <role>`, use that role.
2. **System prompt inference:** Check if role identity markers are present in the current system prompt (e.g., "You are the Architect", "You are the Builder", "You are the QA"). If found, use the detected role.
3. **Checkpoint file discovery:** Check which role-scoped checkpoint files exist in `.purlin/cache/` (`session_checkpoint_architect.md`, `session_checkpoint_builder.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`). If exactly one exists, infer the role from that file. If multiple exist, present the list and ask the user which role to resume.
4. **Ask user:** If no method above succeeds, prompt the user to select their role from `architect`, `builder`, `qa`, `pm`.

#### 2.3.2 Step 2 -- Checkpoint Detection

- Use a non-erroring existence check (e.g., Bash `test -f .purlin/cache/session_checkpoint_<role>.md && echo EXISTS || echo MISSING`) to detect the role-scoped checkpoint file. The `<role>` value comes from Step 1. Do NOT use the Read tool for existence detection — it errors on missing files and cancels sibling parallel tool calls.
- If **EXISTS:** Read the file with the Read tool. Present the saved state as a summary block. Use it to orient the session (the checkpoint's "Next" list becomes the starting work plan).
- If **MISSING:** Proceed silently to Step 3. (The recovery summary in Step 6 already shows `Checkpoint: none`.)

#### 2.3.3 Step 3 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does not contain the role's base instructions (i.e., the agent was started without a launcher script).

When instruction reload is needed:
1. Read the 4 instruction layers in order:
   - `instructions/HOW_WE_WORK_BASE.md`
   - `instructions/{ROLE}_BASE.md`
   - `.purlin/HOW_WE_WORK_OVERRIDES.md`
   - `.purlin/{ROLE}_OVERRIDES.md`
2. Present a condensed "Role Compact" -- key mandates, prohibitions, and protocol summaries extracted from the instructions. This is NOT a full file dump; it is a focused digest of the most critical rules for the role.

When the system prompt already contains the role instructions (agent was started via launcher), skip this step silently (no output).

#### 2.3.4 Step 4 -- Command Reference

- Print a single line: `Commands: /pl-help for full list`
- Do NOT read or print the full command table file. The one-liner is sufficient for resumed sessions (the agent already knows its commands from the system prompt or instruction reload).

#### 2.3.4b Step 4b -- Orphaned Sub-Agent Branch Recovery (Builder Only)

When the role is Builder, check for orphaned worktree branches (`git branch --list 'worktree-*'`). For each found branch, attempt to merge it into the current branch using the Robust Merge Protocol (safe-file auto-resolution with `--ours` for `CRITIC_REPORT.md`, `delivery_plan.md`, `.purlin/cache/*`; unsafe conflicts fall back to sequential). Report merged branches in the recovery summary.

#### 2.3.5 Step 5 -- Gather Fresh Project State

Run `tools/cdd/status.sh --startup <role>` (where `<role>` is the role detected in Step 1).
This single call runs the Critic and returns the full startup briefing with config, git state,
feature summary, action items, dependency graph summary, and role-specific extensions.

**Warm resume (checkpoint exists):**
- The startup briefing provides fresh project state. The work plan comes from the checkpoint's
  "Next" list (not the briefing's action items).
- Exception: if the checkpoint's `## Builder Context` lacks delivery plan info, check
  `delivery_plan_state` in the briefing. The briefing uses `current_phases` (array of
  phase numbers in the current execution group) instead of the older `current_phase`.

**Cold start (no checkpoint):**
- Use the briefing to generate a full work plan, following the role's base instruction file
  for plan structure.
- **Builder phasing assessment:** If `delivery_plan_state.exists` is false and
  `phasing_recommended` is true, run `/pl-delivery-plan` to create a phased delivery plan
  before proposing the work plan.
- Check `find_work` and `auto_start` from the briefing's `config` object:
  - `find_work: false` -- output `"find_work disabled -- awaiting instruction."` after the
    recovery summary. Do not auto-generate a work plan.
  - `find_work: true, auto_start: false` -- proceed with full work plan generation and wait
    for user approval.
  - `find_work: true, auto_start: true` -- proceed with full work plan generation and begin
    executing immediately without waiting for approval.

When a checkpoint exists, startup flags are not consulted -- the checkpoint's "Next" list is
the work plan regardless of flag values.

#### 2.3.6 Step 6 -- Present Recovery Summary

Print a structured recovery summary:

```
Context Restored
Role:           [Architect | Builder | QA | PM]
Branch:         [main | collab/<name>]
Checkpoint:     [found -- resuming from <timestamp> | none]

[If checkpoint found:]
Resume Point:   <feature name> -- <what was in progress>
Next Steps:
  1. <first thing to do>
  2. <second thing>

[When checkpoint exists, or find_work is not false:]
Action Items:   [count] items from Critic report
[Builder only]  Delivery plan: Phase X of Y -- next: <feature>
[QA only]       Verification queue: N features in TESTING
[PM only]       Figma MCP: [available | not available]
Uncommitted:    [none | summary]
```

#### 2.3.7 Step 7 -- Cleanup and Continue

- If a checkpoint file was read in Step 2, delete it (it has been consumed).
- Do NOT reset the context guard counter here. The restore flow consumes ~25-30 turns of real context during state gathering; resetting the counter at this point would cause the guard to misrepresent remaining budget. The only counter reset occurs in Step 0 (clearing stale state from the previous session).
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 6) gives the user visibility; they can interrupt if needed.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Save Writes Role-Scoped Checkpoint File

    Given an agent is in an active session with role "builder"
    And the agent is working on features/cdd_status_monitor.md at protocol step 3
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_builder.md is created
    And the file contains "**Role:** builder"
    And the file contains a valid ISO 8601 timestamp
    And the file contains the current branch name
    And no other session_checkpoint_*.md files are modified

#### Scenario: Concurrent Saves Do Not Overwrite

    Given a Builder agent saves a checkpoint to .purlin/cache/session_checkpoint_builder.md
    And an Architect agent saves a checkpoint to .purlin/cache/session_checkpoint_architect.md
    When both checkpoint files are inspected
    Then both checkpoint files exist independently
    And the Builder checkpoint contains "**Role:** builder"
    And the Architect checkpoint contains "**Role:** architect"

#### Scenario: Restore With Checkpoint

    Given .purlin/cache/session_checkpoint_builder.md exists with role "builder" and timestamp "2026-02-28T15:30:00Z"
    When the agent invokes /pl-resume builder
    Then the checkpoint file is read
    And the recovery summary displays "Checkpoint: found -- resuming from 2026-02-28T15:30:00Z"
    And the checkpoint's Next list is presented as the work plan
    And the checkpoint file is deleted after presentation
    And the agent begins executing the work plan without asking for confirmation

#### Scenario: Restore Without Checkpoint

    Given .purlin/cache/session_checkpoint_builder.md does not exist
    When the agent invokes /pl-resume builder
    Then the Critic report is regenerated via tools/cdd/status.sh
    And the recovery summary is displayed with "Checkpoint: none"
    And the agent begins executing the work plan without asking for confirmation

#### Scenario: Role From Explicit Argument

    Given the agent's system prompt does not contain role identity markers
    When the agent invokes /pl-resume architect
    Then the role is set to "architect" without prompting the user
    And checkpoint detection checks .purlin/cache/session_checkpoint_architect.md
    And the output contains "Commands: /pl-help for full list"
    And the Architect-specific state gathering runs

#### Scenario: Invalid Argument Prints Error

    Given an agent is in an active session
    When the agent invokes /pl-resume with an invalid argument
    Then the output contains an error message
    And the error lists valid options: save, architect, builder, qa, pm
    And no checkpoint file is written or read

#### Scenario: Checkpoint Cleanup After Restore

    Given .purlin/cache/session_checkpoint_builder.md exists
    When the Builder agent completes the restore sequence
    Then .purlin/cache/session_checkpoint_builder.md no longer exists on disk
    And any other role's checkpoint files remain untouched

#### Scenario: Role Inferred From Single Checkpoint File

    Given .purlin/cache/session_checkpoint_qa.md exists
    And no other session_checkpoint_*.md files exist
    And the agent's system prompt has no role identity markers
    When the agent invokes /pl-resume with no argument
    Then the role is inferred as "qa" from the checkpoint file
    And the restore proceeds normally

#### Scenario: Multiple Checkpoints Prompt User Selection

    Given .purlin/cache/session_checkpoint_builder.md exists
    And .purlin/cache/session_checkpoint_architect.md exists
    And the agent's system prompt has no role identity markers
    When the agent invokes /pl-resume with no argument
    Then the agent lists the available checkpoint roles (builder, architect)
    And prompts the user to select which role to resume

Note: The three `auto-test-only` scenarios below require an `agent_behavior` harness test with session-boundary simulation (context clear + new session). These are not exercisable via structural tests alone — they require fixture tags with pre-written checkpoint files.

#### Scenario: Builder Mid-Feature Resume (auto-test-only)

    Given a Builder agent is mid-implementation of a feature at protocol step 2
    When the Builder invokes /pl-resume save
    And the context is cleared
    And a new Builder session invokes /pl-resume
    Then the recovery summary shows the correct feature and protocol step
    And the Builder continues implementation from the saved step without repeating completed work

#### Scenario: QA Mid-Verification Resume (auto-test-only)

    Given a QA agent has verified 5 of 8 scenarios for a feature
    When the QA agent invokes /pl-resume save
    And the context is cleared
    And a new QA session invokes /pl-resume
    Then the recovery summary shows "5 of 8 scenarios completed"
    And the QA agent resumes verification at scenario 6

#### Scenario: Full Reboot Without Launcher (auto-test-only)

    Given a fresh Claude session is started without a launcher script (no system prompt)
    When the user types /pl-resume architect
    Then the skill reads all 4 instruction layers
    And presents a condensed Role Compact with key mandates and prohibitions
    And prints the Architect command table
    And gathers fresh project state
    And presents the recovery summary

#### Scenario: PM Save Writes Role-Scoped Checkpoint File

    Given an agent is in an active session with role "pm"
    And the agent is drafting a feature spec with Figma context
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_pm.md is created
    And the file contains "**Role:** pm"
    And the file contains a Spec Drafts field
    And the file contains a Figma Context field
    And the file contains a Probing Round field
    And no other session_checkpoint_*.md files are modified

#### Scenario: PM Cold Start Checks Figma MCP Availability

    Given .purlin/cache/session_checkpoint_pm.md does not exist
    When the agent invokes /pl-resume pm
    Then the PM state-gathering sequence runs
    And the Figma MCP availability check is performed
    And the recovery summary displays "Figma MCP: available" or "Figma MCP: not available"
    And the recovery summary displays "Checkpoint: none"

#### Scenario: Builder Cold Start Loads Tombstones and Anchors

    Given .purlin/cache/session_checkpoint_builder.md does not exist
    And features/tombstones/ contains at least one tombstone file
    And features/ contains at least one anchor node file
    When the agent invokes /pl-resume builder
    Then the startup briefing contains tombstones with file and label per entry
    And the startup briefing contains anchor_constraints with FORBIDDEN patterns
    And the recovery summary includes tombstone tasks as HIGH-priority items

#### Scenario: QA Cold Start Reads Verification Effort

    Given .purlin/cache/session_checkpoint_qa.md does not exist
    And at least one feature is in TESTING state
    When the agent invokes /pl-resume qa
    Then the startup briefing is retrieved
    And the startup briefing contains testing_features with verification_effort per feature
    And the recovery summary includes effort classification per feature

#### Scenario: Cold Start Respects Startup Flags

    Given .purlin/cache/session_checkpoint_builder.md does not exist
    And .purlin/config.json sets find_work to false for the builder role
    When the agent invokes /pl-resume builder
    Then the startup briefing is retrieved
    And the recovery summary displays "find_work disabled -- awaiting instruction."
    And the recovery summary does NOT display an Action Items line or detail table
    And the agent does not auto-generate a full work plan
    And the agent awaits user direction

### Manual Scenarios (Human Verification Required)

None.

## Regression Guidance
- Role-scoped checkpoint files: concurrent agents save independently without overwriting
- Corrupt or missing checkpoint gracefully handled with informative error
- Checkpoint survives /clear and terminal restarts (written to .purlin/cache/, gitignored)
- find_work=false respected during restore (no auto-generated work plan)
