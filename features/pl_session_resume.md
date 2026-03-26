# Feature: /pl-resume Session Checkpoint and Recovery Skill

> Label: "Agent Skills: Common: /pl-resume Session Resume"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_mode_system.md

[TODO]

## 1. Overview

The `/pl-resume` skill is the **entire startup flow** for the Purlin agent. The startup protocol (PURLIN_BASE.md §5) is a single line: "Run `/pl-resume`." All startup logic — merge recovery, terminal identity, command hints, scanning, work discovery, and mode activation — lives here. This prevents startup and resume flows from drifting apart.

There are three entry points that all converge on `/pl-resume`:
1. **Cold start from launcher** (`pl-run.sh` → §5 → `/pl-resume`): Fresh session, no checkpoint, instructions in system prompt.
2. **After `/clear` → `/pl-resume`**: Mid-session recovery, no checkpoint, instructions may be compressed out.
3. **After `/pl-resume save` → `/clear` → `/pl-resume`**: Warm resume, checkpoint exists, instructions may be compressed out.

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

The agent writes a structured checkpoint to a **PID-scoped** path so that concurrent terminals never collide:

- If `PURLIN_SESSION_ID` is set (launcher session): `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`
- If `PURLIN_SESSION_ID` is not set (manual `/pl-resume`): `.purlin/cache/session_checkpoint_purlin.md` (unscoped fallback)

The checkpoint file is written to disk but NOT committed. It survives `/clear` and agent restarts within the same terminal because the shell session (and its PID) persists. The `.purlin/cache/` directory is gitignored.

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

The checkpoint file path is PID-scoped (see Section 2.2). Example: `.purlin/cache/session_checkpoint_46946.md`.

The checkpoint is human-readable Markdown. The structure uses headings and labeled fields:

```markdown
# Session Checkpoint

**Mode:** engineer
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**Protocol Step:** 3 -- Verify Locally (implementation committed, running tests)

### Done
- Read anchor nodes and prerequisites
- Implemented data layer with test harness
- Recorded [CLARIFICATION] for font-size in impl.md
- Committed implementation: abc1234

### Next
1. Run tests -- verify tests/project_init/tests.json shows PASS
2. Commit status tag: [Ready for Verification]
3. Run tools/cdd/scan.sh to confirm TESTING transition
4. Move to next feature: config_layering.md

## Engineer Context
**Protocol Step:** 3 -- Verify Locally
**Delivery Plan:** Phase 2 of 3 -- IN_PROGRESS
**Execution Group:** Group 2 (Phases 2, 3)
**Work Queue:**
1. [HIGH] config_layering.md -- Phase 2
2. [NORMAL] regression_testing.md -- Phase 2
**Pending Decisions:** None

## Uncommitted Changes
None

## Notes
Font-size decision needs PM review -- recorded as [CLARIFICATION] but may escalate.
```

#### 2.2.6 Legacy Checkpoint Compatibility

When restoring, the agent MUST also check for legacy checkpoint files: role-scoped (`session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`) and unscoped (`session_checkpoint_purlin.md`). If a legacy file is found and no PID-scoped checkpoint exists, read the legacy file and map the role to the equivalent mode (`builder`/`architect` -> `engineer`, `qa` -> `qa`, `pm` -> `pm`; unscoped `purlin` preserves whatever mode is in the file). Delete the legacy file after consuming it.

### 2.3 Restore Mode (`/pl-resume`)

Restore mode follows a 7-step sequence. Each step is mandatory unless noted otherwise.

#### 2.3.0 Step 0 -- Merge Recovery and Stale State Cleanup

**Merge breadcrumb check:** Glob `.purlin/cache/merge_pending/*.json`. If any breadcrumbs exist, run the merge recovery protocol (Section 2.4) before proceeding. This check is essential because `/pl-resume` may be invoked standalone (after `/clear`) when no startup protocol ran.

**Stale checkpoint reaping:** Glob `.purlin/cache/session_checkpoint_*.md`. For each file:
1. Extract the stem after `session_checkpoint_` (e.g., `46946` from `session_checkpoint_46946.md`).
2. Skip known legacy names (`builder`, `architect`, `qa`, `pm`, `purlin`) — these are handled by the legacy compatibility path in Step 1.
3. If the stem is numeric (a PID), check liveness: `kill -0 <pid> 2>/dev/null`.
4. If the PID is dead, the checkpoint is orphaned (terminal crashed or closed without cleanup). **Delete the file** and log: `"Reaped stale checkpoint for PID <pid>."`
5. If the PID is alive, leave the file — it belongs to a running terminal.

This reaping runs BEFORE checkpoint detection (Step 1) so that stale files from crashed terminals don't interfere with the current restore.

**Other stale session state:** Clear any additional stale session state carried over from the previous session. If no such state exists, this is a no-op.

#### 2.3.1 Step 1 -- Checkpoint Detection

Check for checkpoint files in priority order. Use Bash `test -f` for existence detection — do NOT use the Read tool, which errors on missing files and cancels sibling parallel tool calls.

**Detection priority:**
1. **PID-scoped:** If `PURLIN_SESSION_ID` is set, check `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`. This is the current terminal's own checkpoint.
2. **Unscoped (migration):** Check `.purlin/cache/session_checkpoint_purlin.md`. This is the pre-PID-scoping format — treat as a one-time migration path.
3. **Legacy role-scoped:** Check for `session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md` (see 2.2.6).

Stop at the first match. A PID-scoped file from a DIFFERENT terminal is never consumed — only the current terminal's PID matches.

- If **EXISTS (any level):** Read the file with the Read tool. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan. The checkpoint's **Mode** field determines which mode to re-enter. Record which file was matched (needed for deletion in Step 6).
- If **MISSING (all levels):** Proceed silently to Step 2.

#### 2.3.2 Step 2 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does not contain the Purlin agent instructions (i.e., the agent was started without `pl-run.sh`). This is the sole instruction-loading mechanism for `/pl-resume` — no separate "startup briefing" step exists.

When instruction reload is needed:
1. Read the instruction layers in order:
   - `instructions/PURLIN_BASE.md`
   - `.purlin/PURLIN_OVERRIDES.md` (if exists)
2. Present a condensed "Mode Compact" -- key mandates, prohibitions, and protocol summaries extracted from the instructions. This is NOT a full file dump; it is a focused digest of the most critical rules.

When the system prompt already contains the Purlin instructions (agent was started via launcher), skip this step silently (no output).

#### 2.3.3 Step 3 -- Command Hint

- Print: `Use /pl-help for commands`
- Do NOT read or print the full command table. The command table is owned by `/pl-help`.

#### 2.3.3b Step 3b -- Orphaned Sub-Agent Branch Recovery (Engineer mode checkpoint only)

When the checkpoint mode is `engineer`, check for orphaned worktree branches (`git branch --list 'worktree-*'`). For each found branch, attempt to merge it into the current branch using the Robust Merge Protocol (safe-file auto-resolution with `--ours` for `delivery_plan.md`, `.purlin/cache/*`; unsafe conflicts fall back to sequential). Report merged branches in the recovery summary.

#### 2.3.4 Step 4 -- Read Startup Flags and Gather Project State

**This step is the shared path for BOTH normal startup and context recovery.** PURLIN_BASE.md §5 delegates entirely to `/pl-resume` — there is no separate implementation of work discovery in the startup protocol.

**Reading startup flags:** Check `$PURLIN_SESSION_ID` env var (set by the launcher, inherited by the agent). If set, look for `.purlin/cache/session_overrides_${PURLIN_SESSION_ID}.json`. This file is PID-scoped so concurrent agents (10+ in the same project) don't clobber each other. If found, verify the PID is still alive (`kill -0 $PURLIN_SESSION_ID`). If alive, read `find_work` and `auto_start` from it. If dead (stale from crash), delete the file and fall back to config. Do NOT delete a live session overrides file — it persists for the lifetime of the terminal session (the launcher's EXIT trap cleans it up on session end, so it survives `/clear`).

If `PURLIN_SESSION_ID` is not set (e.g., manual `/pl-resume` outside a launcher session), fall back to the **resolved config**: `.purlin/config.local.json` if it exists, otherwise `.purlin/config.json`. Extract `find_work` and `auto_start` from `agents.purlin`.

Read `default_mode` from the resolved config always (it is not in session overrides). Defaults when absent: `find_work: true`, `auto_start: false`, `default_mode: null`.

**When a checkpoint exists (warm resume):**
- Startup flags (`find_work`, `auto_start`, `default_mode`) are NOT consulted — the checkpoint is the authority for both mode and work plan.
- Run `${TOOLS_ROOT}/cdd/scan.sh` for fresh project state. The work plan comes from the checkpoint's "Next" list.
- Re-enter the mode recorded in the checkpoint.

**When no checkpoint exists (cold start):**

This is the path taken on fresh launch AND on `/clear` without `/pl-resume save`. The agent starts in open mode with no work plan — it discovers work fresh via scan.

1. **Check `find_work`** (before running the scan):
   - `find_work: false` -- output `"find_work disabled -- awaiting instruction."` Skip the scan. Skip work plan generation. Proceed directly to the recovery summary (Step 5) with no action items.
   - `find_work: true` -- continue to step 2.

2. **Run scan and status:** Run `${TOOLS_ROOT}/cdd/scan.sh` to get the current project state. Run `/pl-status` to interpret the results and present work organized by mode.

3. **Generate work plan:**
   - Use `/pl-status` output to generate a full work plan organized by mode.
   - Suggest the mode with highest-priority work.
   - **Delivery plan resumption:** If a delivery plan exists with IN_PROGRESS or PENDING phases, highlight it and suggest Engineer mode.
   - **Engineer phasing:** If no delivery plan exists and phasing is recommended, run `/pl-delivery-plan` before proposing the work plan.

4. **Check `auto_start`:**
   - `auto_start: false` -- present the work plan and wait for user approval before executing.
   - `auto_start: true` -- present the work plan and begin executing immediately without waiting for approval. Requires a resolved mode (see mode activation below); without one, `auto_start` is a no-op and the agent waits for mode selection.

**Mode activation priority (cold start only):**
- CLI `--mode` (inferred from the session message directing mode entry, e.g., "Enter Engineer mode") > config `default_mode` > `.purlin_session.lock` mode > user input.
- **Applying `default_mode`:** If the session message does not direct a specific mode, read `default_mode` from the resolved config. If non-null (`"engineer"`, `"pm"`, or `"qa"`), enter that mode. If null, suggest a mode based on scan results and wait for user input.
- **`auto_start` without a resolved mode** (no CLI `--mode`, `default_mode: null`, no session lock): `auto_start` is a no-op — the agent presents mode suggestions and waits for user selection before executing.

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

#### 2.3.6 Step 6 -- Update Terminal Identity, Cleanup, and Continue

- **Update iTerm badge and title** to reflect the determined mode while preserving branch context. The launcher already set an initial badge at launch (e.g., `Purlin (main)`) — Step 6 updates the mode name but keeps the branch in parentheses. If a mode was resolved (from checkpoint, `default_mode`, or session message), set the badge to `<mode> (<branch>)` — e.g., `Engineer (main)`, `PM (feature-xyz)`. If no mode was resolved, leave the launcher's initial badge in place. Check `.purlin_worktree_label` — if present, the worktree label replaces the branch (e.g., `Engineer (W1)`). The branch is detected via `git rev-parse --abbrev-ref HEAD`. Do not set the badge earlier in the /pl-resume flow — let the launcher's initial badge persist until mode is known.
- If a checkpoint file was read in Step 1, **delete whichever file was consumed** (PID-scoped, unscoped, or legacy). The checkpoint has been consumed and must not be restored again.
- If the checkpoint specified a mode, activate that mode.
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 5) gives the user visibility; they can interrupt if needed.

### 2.4 Merge Recovery Mode (`/pl-resume merge-recovery`)

Resolve pending worktree merge failures. Called automatically by Step 0 of the restore flow when breadcrumbs exist, or manually by the user.

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

### 2.5 Launcher Cleanup Contract

The launcher (`pl-run.sh`) is responsible for cleaning up PID-scoped files when the terminal session ends. Its EXIT trap MUST remove:

1. **Session overrides:** `rm -f "$PURLIN_PROJECT_ROOT/.purlin/cache/session_overrides_$$.json"` (already implemented)
2. **Session checkpoint:** `rm -f "$PURLIN_PROJECT_ROOT/.purlin/cache/session_checkpoint_$$.md"`

This ensures that normal terminal closure (including Ctrl+C) does not leave orphaned checkpoint files. The stale checkpoint reaping in Step 0 (Section 2.3.0) serves as a safety net for abnormal termination (kill -9, power loss) where the EXIT trap cannot run.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Checkpoint file path is PID-scoped

    Given the Purlin agent
    And PURLIN_SESSION_ID is set to "46946"
    When determining the checkpoint file path
    Then the path is .purlin/cache/session_checkpoint_46946.md

#### Scenario: Checkpoint file path falls back to unscoped without session ID

    Given the Purlin agent
    And PURLIN_SESSION_ID is not set
    When determining the checkpoint file path
    Then the path is .purlin/cache/session_checkpoint_purlin.md

#### Scenario: Legacy checkpoint files are recognized

    Given .purlin/cache/session_checkpoint_builder.md exists
    And no PID-scoped or unscoped checkpoint exists
    When the agent checks for checkpoints
    Then the legacy builder checkpoint is found
    And the mode is mapped to "engineer"

### QA Scenarios

#### Scenario: Save writes PID-scoped checkpoint file @auto

    Given the Purlin agent is in Engineer mode
    And PURLIN_SESSION_ID is set to "46946"
    And the agent is working on a feature at protocol step 3
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_46946.md is created
    And the file contains "**Mode:** engineer"
    And the file contains a valid ISO 8601 timestamp
    And the file contains the current branch name

#### Scenario: Restore with PID-scoped checkpoint re-enters mode @auto

    Given PURLIN_SESSION_ID is set to "46946"
    And .purlin/cache/session_checkpoint_46946.md exists with mode "engineer"
    When the agent invokes /pl-resume
    Then the PID-scoped checkpoint file is read
    And the recovery summary displays the checkpoint timestamp
    And the checkpoint's Next list is presented as the work plan
    And the agent re-enters Engineer mode
    And .purlin/cache/session_checkpoint_46946.md is deleted after consumption

#### Scenario: Restore checks merge breadcrumbs in Step 0 @auto

    Given .purlin/cache/merge_pending/branch1.json exists
    When the agent invokes /pl-resume (restore mode)
    Then merge recovery runs before checkpoint detection
    And the breadcrumb is processed before proceeding to Step 1

#### Scenario: Badge set once in Step 6 with branch context @auto

    Given a cold start with no checkpoint and default_mode null
    And the current branch is "main"
    When the agent completes /pl-resume
    Then the iTerm badge is set to "Purlin (main)" in Step 6
    And the badge was NOT set earlier in the flow

#### Scenario: Badge reflects checkpoint mode with branch context @auto

    Given a checkpoint exists with mode "engineer"
    And the current branch is "main"
    When the agent completes /pl-resume
    Then the iTerm badge is set to "Engineer (main)" in Step 6
    And the badge was NOT temporarily set to "Purlin (main)" before Step 6

#### Scenario: Restore prints command hint not full table @auto

    Given any /pl-resume invocation (cold or warm)
    When the agent reaches Step 3
    Then the output contains "Use /pl-help for commands"
    And the full command table is NOT printed

#### Scenario: Restore without checkpoint runs cold start @auto

    Given no PID-scoped, unscoped, or legacy checkpoint file exists
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
    And resolved config sets find_work to false for purlin
    When the agent invokes /pl-resume
    Then the scan is NOT run
    And the recovery summary displays "find_work disabled -- awaiting instruction."
    And the agent does not auto-generate a work plan

#### Scenario: Session overrides take priority over config @auto

    Given no checkpoint file exists
    And PURLIN_SESSION_ID is set to "46946"
    And .purlin/cache/session_overrides_46946.json contains find_work=false
    And config.local.json has agents.purlin.find_work = true
    When the agent invokes /pl-resume
    Then the agent reads session_overrides_46946.json (launcher authority)
    And the agent outputs "find_work disabled -- awaiting instruction."
    And the session_overrides_46946.json file is NOT deleted

#### Scenario: Cold start reads config.local.json over config.json @auto

    Given no checkpoint file exists
    And .purlin/config.json has agents.purlin.find_work = true
    And .purlin/config.local.json has agents.purlin.find_work = false
    When the agent invokes /pl-resume
    Then the agent reads config.local.json (resolved config)
    And the agent outputs "find_work disabled -- awaiting instruction."

#### Scenario: Cold start applies default_mode from config @auto

    Given no checkpoint file exists
    And resolved config sets default_mode to "engineer" for purlin
    And the session message does not specify a mode
    When the agent invokes /pl-resume
    Then the agent enters Engineer mode without prompting for mode selection

#### Scenario: auto_start without resolved mode is a no-op @auto

    Given no checkpoint file exists
    And resolved config sets auto_start to true for purlin
    And resolved config sets default_mode to null for purlin
    And the session message does not specify a mode
    When the agent invokes /pl-resume
    Then the agent presents mode suggestions
    And the agent waits for user selection before executing

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

#### Scenario: Concurrent terminals do not collide on checkpoints @auto

    Given terminal A has PURLIN_SESSION_ID "11111"
    And terminal B has PURLIN_SESSION_ID "22222"
    When terminal A invokes /pl-resume save
    And terminal B invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_11111.md exists
    And .purlin/cache/session_checkpoint_22222.md exists
    And each file contains the respective terminal's session state
    And restoring in terminal A reads only session_checkpoint_11111.md
    And restoring in terminal B reads only session_checkpoint_22222.md

#### Scenario: Stale checkpoint from dead PID is reaped in Step 0 @auto

    Given .purlin/cache/session_checkpoint_99999.md exists
    And PID 99999 is not running
    When the agent invokes /pl-resume (restore mode)
    Then Step 0 detects session_checkpoint_99999.md as stale
    And the file is deleted
    And the log contains "Reaped stale checkpoint for PID 99999"
    And Step 1 proceeds without finding that checkpoint

#### Scenario: Checkpoint from live PID is not reaped @auto

    Given .purlin/cache/session_checkpoint_12345.md exists
    And PID 12345 is running (different terminal)
    And the current PURLIN_SESSION_ID is "67890"
    When the agent invokes /pl-resume (restore mode)
    Then Step 0 leaves session_checkpoint_12345.md in place
    And Step 1 does NOT read session_checkpoint_12345.md (wrong PID)

#### Scenario: Launcher EXIT trap cleans up checkpoint file

    Given the launcher started with PID 46946
    And the agent saved a checkpoint to session_checkpoint_46946.md
    When the terminal session ends (EXIT trap fires)
    Then .purlin/cache/session_checkpoint_46946.md is deleted
    And .purlin/cache/session_overrides_46946.md is deleted

#### Scenario: Unscoped checkpoint consumed as migration path @auto

    Given PURLIN_SESSION_ID is set to "46946"
    And .purlin/cache/session_checkpoint_46946.md does not exist
    And .purlin/cache/session_checkpoint_purlin.md exists with mode "pm"
    When the agent invokes /pl-resume
    Then the unscoped checkpoint is read (migration fallback)
    And the agent re-enters PM mode
    And .purlin/cache/session_checkpoint_purlin.md is deleted after consumption

### Manual Scenarios (Human Verification Required)

None.

## Regression Guidance
- Checkpoint is PID-scoped (`session_checkpoint_${PURLIN_SESSION_ID}.md`) — concurrent terminals never collide
- Checkpoint falls back to unscoped `session_checkpoint_purlin.md` when PURLIN_SESSION_ID is not set
- Unscoped and legacy checkpoints are consumed as a migration path (one-time, then deleted)
- Stale checkpoints (dead PIDs) are reaped in Step 0 before checkpoint detection
- Live checkpoints from other terminals are never consumed or reaped
- Launcher EXIT trap cleans up both session_overrides and session_checkpoint files
- Checkpoint survives /clear and agent restarts within the same terminal (PID persists)
- find_work=false respected during restore (no auto-generated work plan, no scan)
- Session overrides are PID-scoped and read with liveness check
- config.local.json takes priority over config.json for startup flags
- default_mode from resolved config is applied when session message specifies no mode
- auto_start=true without a resolved mode does not cause errors (no-op)
- Merge recovery handles stale branches gracefully (branch deleted externally)
