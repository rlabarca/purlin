**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

Save or restore Purlin agent session state across context clears and terminal restarts.

```
/pl-resume [save | merge-recovery]
```

- **No argument:** Restore mode.
- **`save`:** Save mode -- write a checkpoint file.
- **`merge-recovery`:** Resolve pending worktree merge failures (see below).
- **Invalid argument:** Print error listing valid options (`save`, `merge-recovery`) and stop.

---

## Merge Recovery Mode (`/pl-resume merge-recovery`)

Resolve pending worktree merge failures. Called automatically by the startup protocol (PURLIN_BASE.md §5.0) when breadcrumbs exist, or manually by the user.

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

5. **Return control** to the caller (startup protocol continues with §5.1).

### Behavior during normal restore flow

When `/pl-resume` runs without arguments (restore mode), it MUST also check for merge-pending breadcrumbs as part of Step 0 (stale state cleanup). If breadcrumbs exist, run the merge recovery protocol above before proceeding to Step 1.

---

## Save Mode (`/pl-resume save`)

Write a structured checkpoint to `.purlin/cache/session_checkpoint_purlin.md`. Compose the file based on your own understanding of your current session state. Do NOT commit the file (`.purlin/cache/` is gitignored).

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
Checkpoint saved to .purlin/cache/session_checkpoint_purlin.md
Mode: <mode> | Branch: <branch> | Feature: <feature or "none">
You can now /clear or close the terminal. Run /pl-resume to recover.
```

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Restore Mode (`/pl-resume`)

Execute this 7-step sequence:

### Step 0 -- Stale Session State Cleanup

Clear any stale session state carried over from the previous session. If no such state exists, this step is a no-op and may be skipped silently.

Also check for merge-pending breadcrumbs (`.purlin/cache/merge_pending/*.json`). If any exist, run the merge recovery protocol (below) before proceeding.

### Step 1 -- Checkpoint Detection

Use Bash `test -f .purlin/cache/session_checkpoint_purlin.md && echo EXISTS || echo MISSING`. Do NOT use the Read tool for this check — Read errors on missing files and cancels sibling parallel calls.

Also check for legacy role-scoped files (`session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`). If a legacy file is found and no `session_checkpoint_purlin.md` exists, use the legacy file and map the role to the equivalent mode (`builder`/`architect` -> `engineer`, `qa` -> `qa`, `pm` -> `pm`).

- **EXISTS:** Read the file with the Read tool. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan. The checkpoint's **Mode** field determines which mode to re-enter.
- **MISSING:** Proceed silently to Step 2.

### Step 2 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does NOT contain the Purlin agent instructions (i.e., the agent was started without `pl-run.sh`).

When instruction reload is needed:
1. Read the instruction layers in order:
   - `instructions/PURLIN_BASE.md`
   - `.purlin/PURLIN_OVERRIDES.md` (if exists)
2. Present a condensed "Mode Compact" -- key mandates, prohibitions, and protocol summaries. Not a full file dump; a focused digest of the most critical rules.

When the system prompt already contains the Purlin instructions (agent was started via launcher), skip this step silently.

### Step 3 -- Command Reference

Print a single line: `Commands: /pl-help for full list`

### Step 3b -- Orphaned Sub-Agent Branch Recovery (Engineer mode checkpoint only)

When the checkpoint mode is `engineer`, check for orphaned worktree branches:

```bash
git branch --list 'worktree-*'
```

*   **If found:** Attempt to merge them using the Robust Merge Protocol from `/pl-build`.
*   **If not found:** The sub-agents either completed and merged, or never started. The scan results tell what remains.

Branch names encode the phase: `worktree-phase<N>-<feature_stem>`.

### Step 4 -- Gather Fresh Project State

Run `${TOOLS_ROOT}/cdd/scan.sh` to get the current project state. Then run `/pl-status` to interpret the results and present work organized by mode.

**This step is the shared path for BOTH normal startup (PURLIN_BASE.md §5.3) and context recovery.** There is no separate implementation — `/pl-resume` is the canonical flow.

**When a checkpoint exists (warm resume):**
- The scan provides fresh project state. The work plan comes from the checkpoint's "Next" list.
- Re-enter the mode recorded in the checkpoint.

**When no checkpoint exists (cold start):**
- Use `/pl-status` output to generate a full work plan organized by mode.
- Suggest the mode with highest-priority work.
- **Delivery plan resumption:** If a delivery plan exists with IN_PROGRESS/PENDING phases, highlight it and suggest Engineer mode. If launched with `--auto-build`, enter Engineer mode and resume immediately.
- **Engineer phasing:** If no delivery plan exists and phasing is recommended, run `/pl-delivery-plan` before proposing the work plan.

**Startup flag handling (cold start only):**
- `find_work: false` -- output `"find_work disabled -- awaiting instruction."` Do not auto-generate a work plan.
- `find_work: true, auto_start: false` -- generate work plan and wait for user approval.
- `find_work: true, auto_start: true` -- generate work plan and begin executing immediately.

When a checkpoint exists, startup flags are not consulted.

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

### Step 6 -- Cleanup and Continue

- If a checkpoint file was read in Step 1, **delete it** (it has been consumed).
- If the checkpoint specified a mode, activate that mode.
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 5) gives the user visibility; they can interrupt if needed.
