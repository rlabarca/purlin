---
name: resume
description: Session recovery. Saves/restores checkpoints, recovers merge failures, discovers work. Not required to start working — invoke any skill directly instead
---

## Usage

```
purlin:resume [OPTIONS]

Session setup (cold start or post-clear recovery):
  --build                    Shortcut: auto-start + invoke purlin:build
  --verify [feature]         Shortcut: auto-start + invoke purlin:verify [+ feature]
  --worktree                 Enter an isolated git worktree
  --yolo                     Enable auto-approve for all permission prompts (persists)
  --no-yolo                  Disable auto-approve (persists)
  --find-work <true|false>   Enable/disable work discovery (persists)
  --no-save                  Don't persist sticky flags to config (this session only)

Subcommands (do NOT run the startup flow):
  purlin:resume save            Save checkpoint before /clear or terminal close
  purlin:resume merge-recovery  Resolve pending worktree merge failures

  No options: run checkpoint recovery + scan + discover work
```

---

## Subcommand Dispatch

**Check BEFORE running any steps.** If the first argument is a subcommand, jump directly to the matching section. Do NOT execute Steps 0-11.

- `save` -- go to **Save Mode** section below. Stop after save confirmation.
- `merge-recovery` -- go to **Merge Recovery Mode** section below. Stop after summary.
- Any `--flag` or no argument -- continue to **Execution Flow** below.
- Unrecognized argument (not a `--flag`, not `save`, not `merge-recovery`) -- print error: `"Unknown argument '<arg>'. Valid subcommands: save, merge-recovery. Valid flags: --build, --verify, --worktree, --yolo, --no-yolo, --find-work, --no-save."` Stop.

> **Model & effort:** Use `/model` and `/effort` (native Claude Code settings). These are not managed by Purlin config.

---

## When to Run `purlin:resume`

**You do NOT need `purlin:resume` to start working.** Invoke any skill directly:
- `purlin:build feature_name` -- starts building
- `purlin:spec topic` -- starts spec authoring
- `purlin:verify feature_name` -- starts verification

**Run `purlin:resume` when you want to:**
- **Recover a previous session** after `/clear` or context compaction (checkpoint restore)
- **Discover what needs doing** across all roles (scan + work plan)
- **Resolve failed merges** from crashed worktree sessions
- **Save your progress** before intentionally clearing context (`purlin:resume save`)

**What you miss if you skip it:**
- Previous session's work plan and progress (checkpoint not restored)
- Terminal identity badge (cosmetic -- set on first skill invocation anyway)
- Stale checkpoint cleanup (harmless disk clutter, cleaned up eventually)
- Failed merge recovery (deferred until next `purlin:resume` or manual cleanup)

---

## Execution Flow

### Post-Clear Guard

Before running Steps 1-3, check whether this session was already initialized:

**Already initialized** (skip Steps 1-3, jump to Step 4) when ALL of:
- `PURLIN_SESSION_ID` env var is set AND the PID is alive (`kill -0 $PURLIN_SESSION_ID`)
- `.purlin/cache/session_overrides_${PURLIN_SESSION_ID}.json` exists

This means `purlin:resume` already ran once this session (cold start). The agent is resuming after `/clear` or compaction -- flag processing, worktree entry, and initial identity are already done.

**Not yet initialized** (run Steps 0-3) when:
- `PURLIN_SESSION_ID` is not set, or the PID is dead, or session overrides don't exist.

### Step 0 -- Environment Detection

1. Check for `.purlin/` directory. If missing: "Run `purlin:init` first." Stop.
2. Read `.purlin/config.json` for project settings.
3. Check `${CLAUDE_PLUGIN_DATA}/session_state.json` for persisted session flags.

### Step 1 -- Flag Processing (cold start only)

- `--no-save`: When present, sticky flags (`--yolo`, `--no-yolo`, `--find-work`) apply to this session but are NOT written to config.
- `--yolo`: Write `bypass_permissions: true` to `.purlin/config.json` (unless `--no-save`). The PermissionRequest hook reads this and auto-approves all permission dialogs.
- `--no-yolo`: Write `bypass_permissions: false` (unless `--no-save`).
- `--find-work`: Write `find_work` to config (unless `--no-save`).

### Step 2 -- Worktree Entry (cold start only, only if `--worktree`)

1. Call `EnterWorktree` tool (Claude Code built-in).
2. Write `.purlin_worktree_label` (W1, W2, ...) and `.purlin_session.lock`.

### Step 3 -- Session Identity (cold start only)

1. Set terminal identity (badge, title, Warp tab all use unified format).
2. Rename session to the same unified string.

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<label>"
```

`<label>` is the project name by default. When `--build` or `--verify` is used, replace it with a short task description (3-4 words) derived from the target feature or plan.

### Step 4 -- Merge Recovery and Stale State Cleanup

**Merge breadcrumb check:** Glob `.purlin/cache/merge_pending/*.json`. If any breadcrumbs exist, run the merge recovery protocol (see Merge Recovery section below) before proceeding.

**Stale checkpoint reaping:** Glob `.purlin/cache/session_checkpoint_*.md`. For each file:
1. Extract the stem after `session_checkpoint_` (e.g., `46946` from `session_checkpoint_46946.md`).
2. Skip known legacy names (`builder`, `architect`, `qa`, `pm`, `purlin`) -- these are handled by the legacy compatibility path in Step 5.
3. If the stem is numeric (a PID), check liveness: `kill -0 <pid> 2>/dev/null`.
4. If the PID is dead, the checkpoint is orphaned (terminal crashed or closed without cleanup). **Delete the file** and log: `"Reaped stale checkpoint for PID <pid>."`
5. If the PID is alive, leave the file -- it belongs to a running terminal.

This reaping runs BEFORE checkpoint detection (Step 5) so that stale files from crashed terminals don't interfere with the current restore.

**Other stale session state:** Clear any additional stale session state carried over from the previous session. If no such state exists, this is a no-op.

### Step 5 -- Checkpoint Detection

Check for checkpoint files in priority order. Use Bash `test -f` for existence detection -- do NOT use the Read tool, which errors on missing files and cancels sibling parallel tool calls.

**Detection priority:**
1. **PID-scoped:** If `PURLIN_SESSION_ID` is set, check `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`. This is the current terminal's own checkpoint.
2. **Unscoped (migration):** Check `.purlin/cache/session_checkpoint_purlin.md`. This is the pre-PID-scoping format -- treat as a one-time migration path.
3. **Legacy role-scoped:** Check for `session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`. These are legacy format — treat as valid checkpoints.

Stop at the first match. A PID-scoped file from a DIFFERENT terminal is never consumed -- only the current terminal's PID matches.

- **EXISTS (any level):** Read the file with the Read tool. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan. Record which file was matched (needed for deletion in Step 11).
- **MISSING (all levels):** Proceed silently to Step 6.

### Step 6 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does NOT contain the Purlin agent instructions (i.e., the session was started with `claude` directly and the plugin has not yet injected context).

When instruction reload is needed:
1. Read the base instructions from the plugin agent definition (`agents/purlin.md`).
2. Present a condensed "Mode Compact" -- key mandates, prohibitions, and protocol summaries. Not a full file dump; a focused digest of the most critical rules.

When the system prompt already contains the Purlin instructions (plugin auto-activated), skip this step silently.

### Step 7 -- Command Hint

Print: `Use purlin:help for commands`

Do NOT read or print the full command table. The command table is owned by `purlin:help`.

### Step 8 -- Orphaned Sub-Agent Branch Recovery

When the checkpoint references Engineer work, check for orphaned worktree branches:

```bash
git branch --list 'worktree-*'
```

*   **If found:** Attempt to merge them using the Robust Merge Protocol from `purlin:build`.
*   **If not found:** The sub-agents either completed and merged, or never started. The scan results tell what remains.

Branch names encode the phase: `worktree-phase<N>-<feature_stem>`.

### Step 9 -- Read Startup Flags and Gather Project State

**Reading startup flags:** Check `$PURLIN_SESSION_ID` env var (set by the launcher, inherited by the agent). If set, look for `.purlin/cache/session_overrides_${PURLIN_SESSION_ID}.json`. This file is PID-scoped so concurrent agents (10+ in the same project) don't clobber each other. If found, verify the PID is still alive (`kill -0 $PURLIN_SESSION_ID`). If alive, read `find_work` and `auto_start` from the file. If dead (stale from crash), delete the file and fall back to config. If `PURLIN_SESSION_ID` is not set (manual `purlin:resume`), fall back to the resolved config (`agents.purlin`). Defaults: `find_work: true`, `auto_start: false`.

**When a checkpoint exists (warm resume):**
- Startup flags (`find_work`, `auto_start`) are NOT consulted -- the checkpoint is the authority for the work plan.
- Run a scan: `purlin_scan(only: "features,discoveries,git,plan", cached: true)`.
- The work plan comes from the checkpoint's "Next" list. The scan provides fresh project state context.

**When no checkpoint exists (cold start):**

1. **Check `find_work`** (before running the scan):
   - `find_work: false` -- output `"find_work disabled -- awaiting instruction."` Skip the scan. Skip work plan generation. Proceed directly to the recovery summary (Step 10) with no action items.
   - `find_work: true` -- continue to step 2.

2. **Run a lightweight startup scan:** `purlin_scan(only: "features,discoveries,git,plan")`. This is enough for mode suggestion and work discovery. Skips `deps`, `smoke`, `deviations`, and `invariants` (~20-30% smaller than a full scan). Individual skills run their own focused scans when activated.

3. **Run `purlin:status`** to interpret the scan results and present work organized by role.

4. **Generate work plan:**
   - Use `purlin:status` output to generate a full work plan organized by role.
   - Suggest the role with highest-priority work.
   - **Delivery plan resumption:** If a delivery plan exists with IN_PROGRESS/PENDING phases, highlight it. If launched with `--build`, invoke `purlin:build` and resume immediately.
   - **Phasing:** If no delivery plan exists and phasing is recommended, run `purlin:delivery-plan` before proposing the work plan.

5. **Check `auto_start`:**
   - `auto_start: false` -- present the work plan and wait for user approval before executing.
   - `auto_start: true` -- present the work plan and begin executing immediately.

**Worktree context:** If `.purlin_worktree_label` exists, read the label and include it in the recovery summary badge.

### Step 10 -- Present Recovery Summary

Print this structured summary:

```
Context Restored
Branch:         <main | <branch-name>>
Checkpoint:     <found -- resuming from <timestamp> | none>

<If checkpoint found:>
Resume Point:   <feature name> -- <what was in progress>
Next Steps:
  1. <first thing to do>
  2. <second thing>

<When checkpoint exists, or find_work is not false:>
Action Items:   <count> items from scan results
  Engineer:     Delivery plan: Phase X of Y -- next: <feature>
  QA:           Verification queue: N features in TESTING
  PM:           Spec gaps, unacknowledged deviations
Uncommitted:    <none | summary>
```

### Step 11 -- Cleanup and Continue

- **Shortcut dispatch:**
  - If `--build`: invoke `purlin:build`.
  - If `--verify`: invoke `purlin:verify`.
- **Update terminal identity:** Run `source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<label>"`. The `<label>` is the project name by default, or a short task description from the checkpoint's current work.
- If a checkpoint file was read in Step 5, **delete whichever file was consumed** (PID-scoped, unscoped, or legacy). The checkpoint has been consumed and must not be restored again.
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 10) gives the user visibility; they can interrupt if needed.

---

## Save Mode (`purlin:resume save`)

Write a structured checkpoint to a **PID-scoped** path so that concurrent terminals never collide:

- If `PURLIN_SESSION_ID` is set (launcher session): `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`
- If `PURLIN_SESSION_ID` is not set (manual `purlin:resume save`): `.purlin/cache/session_checkpoint_purlin.md` (unscoped fallback)

Compose the file based on your own understanding of your current session state. Do NOT commit the file (`.purlin/cache/` is gitignored).

### Checkpoint Format

```markdown
# Session Checkpoint

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

### Role-Specific Context

Append relevant sections after the common fields based on the work in progress:

**If doing Engineer work:**
```markdown
## Engineer Context
**Protocol Step:** <0-preflight | 1-acknowledge/plan | 2-implement/document | 3-verify locally | 4-commit status tag>
**Delivery Plan:** <Phase X of Y -- STATUS, completed: <features>, or "No delivery plan">
**Execution Group:** <"N/A" | "Group K: Phases [X, Y] -- N features">
**Work Queue:**
1. [PRIORITY] feature_name.md
**Pending Decisions:** <decisions not yet recorded in companion files, or "None">
```

**If doing QA work:**
```markdown
## QA Context
**Scenario Progress:** <e.g., "5 of 8 scenarios completed">
**Current Scenario:** <scenario name>
**Discoveries:** <discoveries recorded this session, or "None">
**Verification Queue:** <features verified vs. remaining>
```

**If doing PM work:**
```markdown
## PM Context
**Spec Drafts:** <which feature specs are being authored or refined>
**Figma Context:** <which Figma files or frames are being referenced, or "None">
```

### After Writing

Print confirmation:

```
Checkpoint saved to .purlin/cache/session_checkpoint_<session_id>.md
Branch: <branch> | Feature: <feature or "none">
You can now /clear or close the terminal. Run purlin:resume to recover.
```

---

## Merge Recovery Mode (`purlin:resume merge-recovery`)

Resolve pending worktree merge failures. Called automatically by Step 4 of the startup flow when breadcrumbs exist, or manually by the user.

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
      - **Defer:** Leave the breadcrumb in place. Print warning: `"Deferred merge: <branch> -- unmerged work exists."`

4. **Summary:** After processing all breadcrumbs, report how many were resolved vs deferred. If any were deferred, note that the warning will persist until resolved.

5. **Return control** to the caller (startup flow continues with Step 5).

---

## Session Cleanup Contract

The SessionEnd hook is responsible for cleaning up PID-scoped files when the session ends. It MUST remove:

1. **Session overrides:** `.purlin/cache/session_overrides_${PURLIN_SESSION_ID}.json`
2. **Session checkpoint:** `.purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md`

This ensures that normal session closure does not leave orphaned checkpoint files. The stale checkpoint reaping in Step 4 serves as a safety net for abnormal termination (kill -9, power loss) where the hook cannot run.

---

## Hook Integration

| Hook Event | Script | Purpose |
|---|---|---|
| SessionStart | session-start.sh | Context reminder: "Purlin active, run purlin:resume" |
| SessionEnd | session-end-merge.sh | Merge worktrees, cleanup |
| PreToolUse (Write/Edit) | write-guard.sh | File classification guard (INVARIANT/UNKNOWN) |
| PermissionRequest | permission-manager.sh | YOLO auto-approve |
| PreCompact | pre-compact-checkpoint.sh | Auto-save checkpoint |
| FileChanged | sync-tracker.sh | Real-time sync state tracking |

**Design decision:** SessionStart hook does NOT auto-run the full startup. It only injects a brief reminder. Full protocol runs via `purlin:resume`. This avoids heavy scan+status on every context clear.
