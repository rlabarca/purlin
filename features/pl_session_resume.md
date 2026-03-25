# Feature: /pl-resume Session Checkpoint and Recovery Skill

> Label: "Agent Skills: Common: /pl-resume Session Resume"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_mode_system.md

[TODO]

## 1. Overview

The `/pl-resume` skill is the **single implementation** of "gather state, present work, activate mode" for the Purlin agent. Both fresh startup and mid-session context recovery use this skill — the startup protocol (PURLIN_BASE.md §5) delegates to `/pl-resume` after preamble steps (merge recovery, command table, flag reading). This prevents the startup and resume flows from drifting apart.

When invoked without a checkpoint, `/pl-resume` runs a cold start: scan the project, present work via `/pl-status`, and activate the appropriate mode. When a checkpoint exists, it restores the previous session's state and resumes work. The `/pl-resume save` subcommand captures session state for recovery.

This skill is shared across all modes (Engineer, PM, QA). The checkpoint captures which mode was active and mode-specific context.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-resume [save | merge-recovery]
```

- **No argument:** Restore mode.
- **`save`:** Save mode -- write a checkpoint file capturing current session state.
- **`merge-recovery`:** Resolve pending worktree merge failures (see Section 2.4).
- **Invalid argument:** Print an error listing valid options (`save`, `merge-recovery`) and exit.

### 2.2 Save Mode (`/pl-resume save`)

The agent writes a structured checkpoint to `.purlin/cache/session_checkpoint_purlin.md`. The agent composes the file based on its own understanding of its current state (no automated extraction is needed).

The checkpoint file is written to disk but NOT committed. It survives `/clear` and terminal restarts as a regular file. The `.purlin/cache/` directory is gitignored.

#### 2.2.1 Common Checkpoint Fields

The checkpoint MUST include:

- **Mode** (the active mode: `engineer`, `pm`, `qa`, or `none` if no mode was active)
- **Timestamp** (ISO 8601 format)
- **Branch** (current git branch)
- **Current Feature** (the feature being worked on, or "none")
- **In Progress** (plain-language description of what is actively in progress)
- **Done** (bulleted list of completed items this session)
- **Next** (numbered list of next steps, in order)
- **Uncommitted Changes** (summary from `git status`, or "None")
- **Notes** (open questions, blockers, or anything the resuming agent should know)

#### 2.2.2 Engineer-Specific Fields

When the active mode is Engineer, the checkpoint MUST additionally include:

- **Protocol Step** (current step in the per-feature implementation protocol: 0-preflight, 1-acknowledge/plan, 2-implement/document, 3-verify locally, 4-commit status tag)
- **Delivery Plan** (single line: "Phase X of Y -- STATUS", or "No delivery plan")
- **Execution Group** (current execution group: which phases are in the group, group number, or "N/A" if no delivery plan)
- **Work Queue** (remaining features in priority order with priority labels)
- **Pending Decisions** (decisions not yet recorded in companion files)

#### 2.2.3 QA-Specific Fields

When the active mode is QA, the checkpoint MUST additionally include:

- **Scenario Progress** (e.g., "5 of 8 scenarios completed")
- **Current Scenario** (name of the scenario being verified)
- **Discoveries** (discoveries recorded so far this session)
- **Verification Queue** (features already verified vs. remaining)

#### 2.2.4 PM-Specific Fields

When the active mode is PM, the checkpoint MUST additionally include:

- **Spec Drafts** (which feature specs are being authored or refined)
- **Figma Context** (which Figma files or frames are being referenced, or "None")

#### 2.2.5 Checkpoint File Format

The checkpoint file path is `.purlin/cache/session_checkpoint_purlin.md`.

The checkpoint is human-readable Markdown. The structure uses headings and labeled fields:

```markdown
# Session Checkpoint

**Mode:** engineer
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/cdd_status_monitor.md
**Protocol Step:** 3 -- Verify Locally (implementation committed, running tests)

### Done
- Read anchor nodes and prerequisites
- Implemented data layer with test harness
- Recorded [CLARIFICATION] for font-size in impl.md
- Committed implementation: abc1234

### Next
1. Run tests -- verify tests/cdd_status_monitor/tests.json shows PASS
2. Commit status tag: [Ready for Verification]
3. Run tools/cdd/scan.sh to confirm TESTING transition
4. Move to next feature: cdd_spec_map.md

## Engineer Context
**Protocol Step:** 3 -- Verify Locally
**Delivery Plan:** Phase 2 of 3 -- IN_PROGRESS
**Execution Group:** Group 2 (Phases 2, 3)
**Work Queue:**
1. [HIGH] cdd_spec_map.md -- Phase 2
2. [NORMAL] cdd_qa_effort_display.md -- Phase 2
**Pending Decisions:** None

## Uncommitted Changes
None

## Notes
Font-size decision needs PM review -- recorded as [CLARIFICATION] but may escalate.
```

#### 2.2.6 Legacy Checkpoint Compatibility

When restoring, the agent MUST also check for legacy role-scoped checkpoint files (`session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`). If a legacy file is found and no `session_checkpoint_purlin.md` exists, read the legacy file and map the role to the equivalent mode (`builder`/`architect` -> `engineer`, `qa` -> `qa`, `pm` -> `pm`). Delete the legacy file after consuming it.

### 2.3 Restore Mode (`/pl-resume`)

Restore mode follows a 7-step sequence. Each step is mandatory unless noted otherwise.

#### 2.3.0 Step 0 -- Stale Session State Cleanup

Clear any stale session state carried over from the previous session. This includes resetting internal turn counters or budget trackers if the agent runtime maintains them. If no such state exists in the current runtime, this step is a no-op and may be skipped silently.

Merge-pending breadcrumbs are handled by the startup protocol (PURLIN_BASE.md §5.0) BEFORE `/pl-resume` is called. Do NOT re-check breadcrumbs here.

#### 2.3.1 Step 1 -- Checkpoint Detection

- Use Bash `test -f .purlin/cache/session_checkpoint_purlin.md && echo EXISTS || echo MISSING` to detect the checkpoint file. Do NOT use the Read tool for existence detection — it errors on missing files and cancels sibling parallel tool calls.
- Also check for legacy role-scoped files (see 2.2.6).
- If **EXISTS:** Read the file with the Read tool. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan. The checkpoint's **Mode** field determines which mode to re-enter.
- If **MISSING:** Proceed silently to Step 2.

#### 2.3.2 Step 2 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does not contain the Purlin agent instructions (i.e., the agent was started without `pl-run.sh`).

When instruction reload is needed:
1. Read the instruction layers in order:
   - `instructions/PURLIN_BASE.md`
   - `.purlin/PURLIN_OVERRIDES.md` (if exists)
2. Present a condensed "Mode Compact" -- key mandates, prohibitions, and protocol summaries extracted from the instructions. This is NOT a full file dump; it is a focused digest of the most critical rules.

When the system prompt already contains the Purlin instructions (agent was started via launcher), skip this step silently (no output).

#### 2.3.3 Step 3 -- Command Reference

- Print a single line: `Commands: /pl-help for full list`
- Do NOT read or print the full command table file.

#### 2.3.3b Step 3b -- Orphaned Sub-Agent Branch Recovery (Engineer mode checkpoint only)

When the checkpoint mode is `engineer`, check for orphaned worktree branches (`git branch --list 'worktree-*'`). For each found branch, attempt to merge it into the current branch using the Robust Merge Protocol (safe-file auto-resolution with `--ours` for `delivery_plan.md`, `.purlin/cache/*`; unsafe conflicts fall back to sequential). Report merged branches in the recovery summary.

#### 2.3.4 Step 4 -- Gather Fresh Project State

Run `${TOOLS_ROOT}/cdd/scan.sh` to get the current project state. Then run `/pl-status` to interpret the scan results and present work organized by mode.

**This step is the shared path used by BOTH normal startup and context recovery.** PURLIN_BASE.md §5.3-5.4 delegate here — there is no separate implementation of work discovery in the startup protocol.

**Warm resume (checkpoint exists):**
- The scan provides fresh project state. The work plan comes from the checkpoint's "Next" list.
- Re-enter the mode recorded in the checkpoint.

**Cold start (no checkpoint):**
- Use `/pl-status` output to generate a full work plan organized by mode.
- Suggest the mode with highest-priority work.
- **Engineer phasing:** If no delivery plan exists and phasing is recommended, run `/pl-delivery-plan` before proposing the work plan.
- **Delivery plan resumption:** If a delivery plan exists with IN_PROGRESS or PENDING phases, highlight it and suggest Engineer mode.
- Check `find_work` and `auto_start` from the config:
  - `find_work: false` -- output `"find_work disabled -- awaiting instruction."` after the recovery summary. Do not auto-generate a work plan.
  - `find_work: true, auto_start: false` -- proceed with full work plan generation and wait for user approval.
  - `find_work: true, auto_start: true` -- proceed with full work plan generation and begin executing immediately without waiting for approval.

When a checkpoint exists, startup flags are not consulted -- the checkpoint is the authority for both mode and work plan.

**Mode activation priority (context-dependent):**
- **Warm resume (checkpoint exists):** checkpoint mode wins. This is the save/resume contract — the user gets back where they were regardless of launcher flags or config defaults.
- **Cold start (no checkpoint):** CLI `--mode` > config `default_mode` > `.purlin_session.lock` mode > user input.

**Worktree context:** If running inside a worktree (`.purlin_worktree_label` exists), read the label and include it in the recovery summary. If `.purlin_session.lock` exists, read the mode from the lock as a fallback when no checkpoint exists.

#### 2.3.5 Step 5 -- Present Recovery Summary

Print a structured recovery summary:

```
Context Restored
Mode:           [Engineer | PM | QA | none]
Branch:         [main | <branch-name>]
Checkpoint:     [found -- resuming from <timestamp> | none]

[If checkpoint found:]
Resume Point:   <feature name> -- <what was in progress>
Next Steps:
  1. <first thing to do>
  2. <second thing>

[When checkpoint exists, or find_work is not false:]
Action Items:   [count] items from scan results
[Engineer]      Delivery plan: Phase X of Y -- next: <feature>
[QA]            Verification queue: N features in TESTING
[PM]            Figma MCP: [available | not available]
Uncommitted:    [none | summary]
```

#### 2.3.6 Step 6 -- Cleanup and Continue

- If a checkpoint file was read in Step 1, **delete it** (it has been consumed).
- If the checkpoint specified a mode, activate that mode.
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 5) gives the user visibility; they can interrupt if needed.

### 2.4 Merge Recovery Mode (`/pl-resume merge-recovery`)

Resolve pending worktree merge failures. Called automatically by the startup protocol (PURLIN_BASE.md §5.0) when breadcrumbs exist, or manually by the user.

#### Protocol

1. **Read breadcrumbs:** Glob `.purlin/cache/merge_pending/*.json`. Read each file to get `branch`, `worktree_path`, `source_branch`, `failed_at`, and `reason`.

2. **Display pending merges:** For each breadcrumb, show:
   ```
   Pending merge: <branch>
     Age: <time since failed_at>
     Worktree: <worktree_path>
     Source: <source_branch>
   ```

3. **Attempt resolution** for each pending merge:
   a. Verify the branch still exists (`git rev-parse --verify <branch>`). If not, delete the stale breadcrumb and skip.
   b. Attempt `git merge <branch> --no-edit`.
   c. **If merge succeeds:** clean up worktree (`git worktree remove <path>`), delete branch (`git branch -d <branch>`), delete breadcrumb, report success.
   d. **If merge conflicts:** abort the merge (`git merge --abort`). Show the conflicting files. Offer two options:
      - **Resolve now:** Read the conflicting files, understand the intent from both sides, and propose a resolution. Apply the resolution, complete the merge, clean up.
      - **Defer:** Leave the breadcrumb in place. Print warning: `"Deferred merge: <branch> — unmerged work exists."`

4. **Summary:** After processing all breadcrumbs, report how many were resolved vs deferred.

5. **Return control** to the caller (startup protocol continues).

---

## 3. Scenarios

### Unit Tests

#### Scenario: Checkpoint file path is correct

    Given the Purlin agent
    When determining the checkpoint file path
    Then the path is .purlin/cache/session_checkpoint_purlin.md

#### Scenario: Legacy checkpoint files are recognized

    Given .purlin/cache/session_checkpoint_builder.md exists
    And .purlin/cache/session_checkpoint_purlin.md does not exist
    When the agent checks for checkpoints
    Then the legacy builder checkpoint is found
    And the mode is mapped to "engineer"

### QA Scenarios

#### Scenario: Save writes checkpoint file @auto

    Given the Purlin agent is in Engineer mode
    And the agent is working on a feature at protocol step 3
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_purlin.md is created
    And the file contains "**Mode:** engineer"
    And the file contains a valid ISO 8601 timestamp
    And the file contains the current branch name

#### Scenario: Restore with checkpoint re-enters mode @auto

    Given .purlin/cache/session_checkpoint_purlin.md exists with mode "engineer"
    When the agent invokes /pl-resume
    Then the checkpoint file is read
    And the recovery summary displays the checkpoint timestamp
    And the checkpoint's Next list is presented as the work plan
    And the agent re-enters Engineer mode
    And the checkpoint file is deleted after consumption

#### Scenario: Restore without checkpoint runs cold start @auto

    Given .purlin/cache/session_checkpoint_purlin.md does not exist
    When the agent invokes /pl-resume
    Then a fresh scan is run
    And the recovery summary displays "Checkpoint: none"
    And the agent presents work organized by mode

#### Scenario: Cold start runs /pl-status for work discovery @auto

    Given no checkpoint file exists
    When the agent invokes /pl-resume (cold start)
    Then scan.sh is run
    And /pl-status interprets the results
    And work is presented organized by mode
    And the mode with highest-priority work is suggested

#### Scenario: Cold start with worktree reads session lock for mode @auto

    Given no checkpoint file exists
    And .purlin_worktree_label contains "W1"
    And .purlin_session.lock contains mode "engineer"
    When the agent invokes /pl-resume
    Then the recovery summary includes "W1" in the badge
    And the agent enters Engineer mode from the session lock

#### Scenario: Cold start respects find_work false @auto

    Given no checkpoint file exists
    And config sets find_work to false for purlin
    When the agent invokes /pl-resume
    Then the recovery summary displays "find_work disabled -- awaiting instruction."
    And the agent does not auto-generate a work plan

#### Scenario: Invalid argument prints error @auto

    Given a Purlin agent session
    When the agent invokes /pl-resume with an invalid argument
    Then the output contains an error message
    And the error lists valid options: save, merge-recovery

#### Scenario: Engineer save includes mode-specific fields @auto

    Given the agent is in Engineer mode working on a delivery plan
    When the agent invokes /pl-resume save
    Then the checkpoint includes Protocol Step
    And the checkpoint includes Delivery Plan
    And the checkpoint includes Work Queue

#### Scenario: QA save includes mode-specific fields @auto

    Given the agent is in QA mode verifying scenarios
    When the agent invokes /pl-resume save
    Then the checkpoint includes Scenario Progress
    And the checkpoint includes Verification Queue

#### Scenario: PM save includes mode-specific fields @auto

    Given the agent is in PM mode drafting specs
    When the agent invokes /pl-resume save
    Then the checkpoint includes Spec Drafts
    And the checkpoint includes Figma Context

#### Scenario: Merge recovery resolves pending merges @auto

    Given .purlin/cache/merge_pending/branch1.json exists
    And the branch referenced in the breadcrumb still exists
    When the agent invokes /pl-resume merge-recovery
    Then the merge is attempted
    And on success the breadcrumb is deleted and the branch cleaned up

### Manual Scenarios (Human Verification Required)

None.

## Regression Guidance
- Checkpoint survives /clear and terminal restarts (written to .purlin/cache/, gitignored)
- Legacy role-scoped checkpoints are recognized and consumed correctly
- find_work=false respected during restore (no auto-generated work plan)
- Merge recovery handles stale branches gracefully (branch deleted externally)
