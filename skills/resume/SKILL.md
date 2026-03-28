---
name: resume
description: Available to all agents and modes
---

**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

Save or restore Purlin agent session state across context clears and terminal restarts.

```
purlin:resume [save | merge-recovery]
```

- **No argument:** Restore mode.
- **`save`:** Save mode -- write a checkpoint file.
- **`merge-recovery`:** Resolve pending worktree merge failures (see below).
- **Invalid argument:** Print error listing valid options (`save`, `merge-recovery`) and stop.

---

## Merge Recovery Mode (`purlin:resume merge-recovery`)

Resolve pending worktree merge failures. Called automatically by Step 0 of the restore flow when breadcrumbs exist, or manually by the user.

### Protocol

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

4. **Summary:** After processing all breadcrumbs, report how many were resolved vs deferred. If any were deferred, note that the warning will persist until resolved.

5. **Return control** to the caller (restore flow continues with Step 1).

---

## Save Mode (`purlin:resume save`)

Write a structured checkpoint to a **PID-scoped** path so that concurrent terminals never collide:

- If `PURLIN_SESSION_ID` is set (launcher session): `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`
- If `PURLIN_SESSION_ID` is not set (manual `purlin:resume`): `.purlin/cache/session_checkpoint_purlin.md` (unscoped fallback)

Compose the file based on your own understanding of your current session state. Do NOT commit the file (`.purlin/cache/` is gitignored).

### Checkpoint Format

```markdown
# Session Checkpoint

**Mode:** <engineer | pm | qa | none>
**Timestamp:** <ISO 8601>
**Branch:** <current git branch>

## Current Work

**Feature:** <feature file path, or "none">
**In Progress:** <plain-language description of what is actively in progress>

### Done
- <completed item 1>
- <completed item 2>

### Next
1. <next step 1>
2. <next step 2>

## Uncommitted Changes
<summary from `git status`, or "None">

## Notes
<open questions, blockers, or anything the resuming agent should know>
```

### Mode-Specific Fields

Append these sections after the common fields:

**Engineer mode:**
```markdown
## Engineer Context
**Protocol Step:** <0-preflight | 1-acknowledge/plan | 2-implement/document | 3-verify locally | 4-commit status tag>
**Delivery Plan:** <Phase X of Y -- STATUS, completed: <features>, or "No delivery plan">
**Execution Group:** <"N/A" | "Group K: Phases [X, Y] -- N features">
**Work Queue:**
1. [PRIORITY] feature_name.md
**Pending Decisions:** <decisions not yet recorded in companion files, or "None">
```

**QA mode:**
```markdown
## QA Context
**Scenario Progress:** <e.g., "5 of 8 scenarios completed">
**Current Scenario:** <scenario name>
**Discoveries:** <discoveries recorded this session, or "None">
**Verification Queue:** <features verified vs. remaining>
```

**PM mode:**
```markdown
## PM Context
**Spec Drafts:** <which feature specs are being authored or refined>
**Figma Context:** <which Figma files or frames are being referenced, or "None">
```

### After Writing

Print confirmation:

```
Checkpoint saved to .purlin/cache/session_checkpoint_<session_id>.md
Mode: <mode> | Branch: <branch> | Feature: <feature or "none">
You can now /clear or close the terminal. Run purlin:resume to recover.
```

---

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`. This skill reads `config.local.json` first (launcher persists CLI overrides there).
> **Companion files:** See `${CLAUDE_PLUGIN_ROOT}/references/active_deviations.md` for deviation format and PM review protocol.

---

## Restore Mode (`purlin:resume`)

Execute this 7-step sequence:

### Step 0 -- Merge Recovery and Stale State Cleanup

**Merge breadcrumb check:** Glob `.purlin/cache/merge_pending/*.json`. If any breadcrumbs exist, run the merge recovery protocol (see Merge Recovery Mode above) before proceeding. This check is essential because `purlin:resume` may be invoked standalone (after `/clear`) when no startup protocol ran.

**Stale checkpoint reaping:** Glob `.purlin/cache/session_checkpoint_*.md`. For each file:
1. Extract the stem after `session_checkpoint_` (e.g., `46946` from `session_checkpoint_46946.md`).
2. Skip known legacy names (`builder`, `architect`, `qa`, `pm`, `purlin`) — these are handled by the legacy compatibility path in Step 1.
3. If the stem is numeric (a PID), check liveness: `kill -0 <pid> 2>/dev/null`.
4. If the PID is dead, the checkpoint is orphaned (terminal crashed or closed without cleanup). **Delete the file** and log: `"Reaped stale checkpoint for PID <pid>."`
5. If the PID is alive, leave the file — it belongs to a running terminal.

This reaping runs BEFORE checkpoint detection (Step 1) so that stale files from crashed terminals don't interfere with the current restore.

**Other stale session state:** Clear any additional stale session state carried over from the previous session. If no such state exists, this is a no-op.

### Step 1 -- Checkpoint Detection

Check for checkpoint files in priority order. Use Bash `test -f` for existence detection — do NOT use the Read tool, which errors on missing files and cancels sibling parallel tool calls.

**Detection priority:**
1. **PID-scoped:** If `PURLIN_SESSION_ID` is set, check `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`. This is the current terminal's own checkpoint.
2. **Unscoped (migration):** Check `.purlin/cache/session_checkpoint_purlin.md`. This is the pre-PID-scoping format — treat as a one-time migration path.
3. **Legacy role-scoped:** Check for `session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`. Map role to mode (`builder`/`architect` -> `engineer`, `qa` -> `qa`, `pm` -> `pm`).

Stop at the first match. A PID-scoped file from a DIFFERENT terminal is never consumed — only the current terminal's PID matches.

- **EXISTS (any level):** Read the file with the Read tool. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan. The checkpoint's **Mode** field determines which mode to re-enter. Record which file was matched (needed for deletion in Step 6).
- **MISSING (all levels):** Proceed silently to Step 2.

### Step 2 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does NOT contain the Purlin agent instructions (i.e., the session was started with `claude` directly and the plugin has not yet injected context).

When instruction reload is needed:
1. Read the instruction layers in order:
   - `instructions/PURLIN_BASE.md`
   - `.purlin/PURLIN_OVERRIDES.md` (if exists)
2. Present a condensed "Mode Compact" -- key mandates, prohibitions, and protocol summaries. Not a full file dump; a focused digest of the most critical rules.

When the system prompt already contains the Purlin instructions (agent was started via launcher), skip this step silently.

### Step 3 -- Command Hint

Print: `Use purlin:help for commands`

Do NOT read or print the full command table. The command table is owned by `purlin:help`.

### Step 3b -- Orphaned Sub-Agent Branch Recovery (Engineer mode checkpoint only)

When the checkpoint mode is `engineer`, check for orphaned worktree branches:

```bash
git branch --list 'worktree-*'
```

*   **If found:** Attempt to merge them using the Robust Merge Protocol from `purlin:build`.
*   **If not found:** The sub-agents either completed and merged, or never started. The scan results tell what remains.

Branch names encode the phase: `worktree-phase<N>-<feature_stem>`.

### Step 4 -- Read Startup Flags and Gather Project State

**This step is the shared path for BOTH normal startup and context recovery.** PURLIN_BASE.md §5 delegates entirely to `purlin:resume` — there is no separate implementation.

**Reading startup flags:** Check `$PURLIN_SESSION_ID` env var (set by the launcher, inherited by the agent). If set, look for `.purlin/cache/session_overrides_${PURLIN_SESSION_ID}.json`. This file is PID-scoped so concurrent agents (10+ in the same project) don't clobber each other. If found, verify the PID is still alive (`kill -0 $PURLIN_SESSION_ID`). If alive, read `find_work` and `auto_start` from the file. If dead (stale from crash), delete the file and fall back to config. If `PURLIN_SESSION_ID` is not set (manual `purlin:resume`), fall back to the resolved config (`agents.purlin`). Read `default_mode` from the resolved config always (not in session overrides). Defaults: `find_work: true`, `auto_start: false`, `default_mode: null`.

**When a checkpoint exists (warm resume):**
- Startup flags (`find_work`, `auto_start`, `default_mode`) are NOT consulted — the checkpoint is the authority for both mode and work plan.
- Run `${CLAUDE_PLUGIN_ROOT}/scripts/cdd/scan.sh` for fresh project state. The work plan comes from the checkpoint's "Next" list.
- Re-enter the mode recorded in the checkpoint.

**When no checkpoint exists (cold start):**

1. **Check `find_work`** (before running the scan):
   - `find_work: false` -- output `"find_work disabled -- awaiting instruction."` Skip the scan. Skip work plan generation. Proceed directly to the recovery summary (Step 5) with no action items.
   - `find_work: true` -- continue to step 2.

2. **Run scan and status:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/cdd/scan.sh` to get the current project state. Run `purlin:status` to interpret the results and present work organized by mode.

3. **Generate work plan:**
   - Use `purlin:status` output to generate a full work plan organized by mode.
   - Suggest the mode with highest-priority work.
   - **Delivery plan resumption:** If a delivery plan exists with IN_PROGRESS/PENDING phases, highlight it and suggest Engineer mode. If launched with `--auto-build`, enter Engineer mode and resume immediately.
   - **Engineer phasing:** If no delivery plan exists and phasing is recommended, run `purlin:delivery-plan` before proposing the work plan.

4. **Check `auto_start`:**
   - `auto_start: false` -- present the work plan and wait for user approval before executing.
   - `auto_start: true` -- present the work plan and begin executing immediately. Requires a resolved mode (see below); without one, `auto_start` is a no-op.

**Mode activation priority (cold start only):**
- CLI `--mode` (inferred from session message directing mode entry, e.g., "Enter Engineer mode") > config `default_mode` > `.purlin_session.lock` mode > user input.
- **Applying `default_mode`:** If the session message does not direct a specific mode, read `default_mode` from resolved config. If non-null, enter that mode. If null, suggest a mode based on scan results and wait for user input.
- **`auto_start` without a resolved mode** (no CLI `--mode`, `default_mode: null`, no session lock): `auto_start` is a no-op — the agent presents mode suggestions and waits.

**Worktree context:** If `.purlin_worktree_label` exists, read the label and include it in the recovery summary badge. If `.purlin_session.lock` exists and no checkpoint is found, read the mode from the lock as a fallback for mode activation.

### Step 5 -- Present Recovery Summary

Print this structured summary:

```
Context Restored
Mode:           <Engineer | PM | QA | none>
Branch:         <main | <branch-name>>
Checkpoint:     <found -- resuming from <timestamp> | none>

<If checkpoint found:>
Resume Point:   <feature name> -- <what was in progress>
Next Steps:
  1. <first thing to do>
  2. <second thing>

<When checkpoint exists, or find_work is not false:>
Action Items:   <count> items from scan results
<Engineer>      Delivery plan: Phase X of Y -- next: <feature>
<QA>            Verification queue: N features in TESTING
<PM>            Figma MCP: <available | not available>
Uncommitted:    <none | summary>
```

### Step 6 -- Update Terminal Identity, Cleanup, and Continue

- **Update terminal identity** to reflect the determined mode. If a mode was resolved (from checkpoint, `default_mode`, or session message), run `source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<mode>" "<project>"`. This detects branch/worktree context automatically and dispatches to all terminal environments. If no mode was resolved, leave the launcher's initial badge in place. Do not set the badge earlier in the `purlin:resume` flow.
- If a checkpoint file was read in Step 1, **delete whichever file was consumed** (PID-scoped, unscoped, or legacy). The checkpoint has been consumed and must not be restored again.
- If the checkpoint specified a mode, activate that mode.
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 5) gives the user visibility; they can interrupt if needed.
