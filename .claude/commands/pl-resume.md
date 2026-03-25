**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

Save or restore agent session state across context clears and terminal restarts.

```
/pl-resume [save | <role>]
```

- **No argument:** Restore mode with role auto-detection.
- **`save`:** Save mode -- write a checkpoint file.
- **`<role>`** (`architect`, `builder`, `qa`, `pm`): Restore mode with explicit role.
- **Invalid argument:** Print error listing valid options (`save`, `architect`, `builder`, `qa`, `pm`) and stop.

---

## Save Mode (`/pl-resume save`)

Write a structured checkpoint to a **role-scoped** file: `.purlin/cache/session_checkpoint_<role>.md` (e.g., `session_checkpoint_builder.md`, `session_checkpoint_architect.md`, `session_checkpoint_qa.md`). The agent determines `<role>` from its own identity. Compose the file based on your own understanding of your current session state. Do NOT commit the file (`.purlin/cache/` is gitignored).

Role-scoped files ensure that concurrent agents can save checkpoints independently without overwriting each other. Each role's checkpoint is isolated.

### Checkpoint Format

```markdown
# Session Checkpoint

**Role:** <role>
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

### Role-Specific Fields

Append these sections after the common fields:

**Builder only:**
```markdown
## Builder Context
**Protocol Step:** <0-preflight | 1-acknowledge/plan | 2-implement/document | 3-verify locally | 4-commit status tag>
**Delivery Plan:** <Phase X of Y -- STATUS, completed: <features>, or "No delivery plan">
**Execution Group:** <"N/A" | "Group K: Phases [X, Y] -- N features">
**Parallel B1 State:** <"idle" | "spawned N sub-agents for features [A, B]" | "merging N branches">
**Work Queue:**
1. [PRIORITY] feature_name.md
**Pending Decisions:** <decisions not yet recorded in companion files, or "None">
```

**QA only:**
```markdown
## QA Context
**Scenario Progress:** <e.g., "5 of 8 scenarios completed">
**Current Scenario:** <scenario name>
**Discoveries:** <discoveries recorded this session, or "None">
**Verification Queue:** <features verified vs. remaining>
```

**Architect only:**
```markdown
## Architect Context
**Spec Reviews:** <spec reviews in progress>
**Discovery Processing:** <discoveries reviewed vs. pending>
```

**PM only:**
```markdown
## PM Context
**Spec Drafts:** <which feature specs are being authored or refined>
**Figma Context:** <which Figma files or frames are being referenced, or "None">
**Probing Round:** <current round in the Probing Question Protocol, if active, or "N/A">
```

### After Writing

Print confirmation:

```
Checkpoint saved to .purlin/cache/session_checkpoint_<role>.md
Role: <role> | Branch: <branch> | Feature: <feature or "none">
You can now /clear or close the terminal. Run /pl-resume to recover.
```

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Restore Mode (`/pl-resume` or `/pl-resume <role>`)

Execute this 8-step sequence:

### Step 0 -- Stale Session State Cleanup

Clear any stale session state carried over from the previous session. This includes resetting internal turn counters or budget trackers if the agent runtime maintains them. If no such state exists in the current runtime, this step is a no-op and may be skipped silently.

### Step 1 -- Role Detection (4-Tier Fallback)

1. **Explicit argument:** If the user invoked `/pl-resume <role>`, use that role.
2. **System prompt inference:** Check if role identity markers are present in the current system prompt (e.g., "Role Definition: The Builder", "Role Definition: The Architect", "Role Definition: The QA", "Role Definition: The PM"). If found, use the detected role.
3. **Checkpoint file discovery:** Check which role-scoped checkpoint files exist in `.purlin/cache/` (`session_checkpoint_architect.md`, `session_checkpoint_builder.md`, `session_checkpoint_qa.md`, `session_checkpoint_pm.md`). If exactly one exists, infer the role from that file. If multiple exist, present the list and ask the user which role to resume.
4. **Ask user:** If no method above succeeds, prompt the user to select their role from `architect`, `builder`, `qa`, `pm`.

### Step 2 -- Checkpoint Detection

Use Bash `test -f .purlin/cache/session_checkpoint_<role>.md && echo EXISTS || echo MISSING` to check for the role-scoped checkpoint file. The `<role>` value comes from Step 1. Do NOT use the Read tool for this check — Read errors on missing files and cancels sibling parallel calls.

- **EXISTS:** Read the file with the Read tool. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan.
- **MISSING:** Proceed silently to Step 3. (The recovery summary in Step 6 already shows `Checkpoint: none`.)

### Step 3 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does NOT contain the role's base instructions (i.e., the agent was started without a launcher script).

When instruction reload is needed:
1. Read the 4 instruction layers in order:
   - `instructions/HOW_WE_WORK_BASE.md`
   - `instructions/{ROLE}_BASE.md` (where ROLE is ARCHITECT, BUILDER, QA, or PM)
   - `.purlin/HOW_WE_WORK_OVERRIDES.md`
   - `.purlin/{ROLE}_OVERRIDES.md`
2. Present a condensed "Role Compact" -- key mandates, prohibitions, and protocol summaries extracted from the instructions. This is NOT a full file dump; it is a focused digest of the most critical rules.

When the system prompt already contains the role instructions (agent was started via launcher), skip this step silently (no output).

### Step 4 -- Command Reference

Print a single line: `Commands: /pl-help for full list`

Do NOT read or print the full command table file. The one-liner is sufficient for resumed sessions.

### Step 4b -- Orphaned Sub-Agent Branch Recovery (Builder only)

On resume, the Builder MUST check for orphaned worktree branches matching the pattern `worktree-*`:

```bash
git branch --list 'worktree-*'
```

*   **If found:** Attempt to merge them using the Robust Merge Protocol from `/pl-build`. After successful merges, continue with remaining work.
*   **If not found:** The sub-agents either completed and merged, or never started. The delivery plan + Critic state tells the Builder what remains.

Branch names encode the phase: `worktree-phase<N>-<feature_stem>`. This allows attribution of orphaned branches to specific phases within an execution group.

### Step 5 -- Gather Fresh Project State

Run `${TOOLS_ROOT}/cdd/status.sh --startup <role>` (where `<role>` is the role detected in Step 1).
This single call runs the Critic and returns the full startup briefing with config, git state,
feature summary, action items, dependency graph summary, and role-specific extensions
(Builder: tombstones, anchor constraints, delivery plan state, phasing recommendation;
QA: testing features, discovery summary; Architect: spec completeness, untracked files).

**When a checkpoint exists (warm resume):**
- The startup briefing provides fresh project state. The work plan comes from the
  checkpoint's "Next" list.
- Exception: if the checkpoint's `## Builder Context` lacks delivery plan info, check
  `delivery_plan_state` in the briefing. The briefing uses `current_phases` (array of
  phase numbers in the current execution group) instead of the older `current_phase`.

**When no checkpoint exists (cold start):** additionally:
- Use the briefing to generate a full work plan.
- **Builder phasing:** If `delivery_plan_state.exists` is false and `phasing_recommended`
  is true, run `/pl-delivery-plan` to create a phased delivery plan before proposing the
  work plan.

**Startup flag handling (cold start only):**
When no checkpoint exists, check `find_work` and `auto_start` from the briefing's `config`
object for the detected role:
- `find_work: false` -- output `"find_work disabled -- awaiting instruction."` after the
  recovery summary. Do not auto-generate a work plan.
- `find_work: true, auto_start: false` -- proceed with full work plan generation and wait
  for user approval.
- `find_work: true, auto_start: true` -- proceed with full work plan generation and begin
  executing immediately without waiting for approval.

When a checkpoint exists, startup flags are not consulted -- the checkpoint's "Next" list
is the work plan regardless of flag values.

### Step 6 -- Present Recovery Summary

Print this structured summary:

```
Context Restored
Role:           <Architect | Builder | QA | PM>
Branch:         <main | <branch-name>>
Checkpoint:     <found -- resuming from <timestamp> | none>

<If checkpoint found:>
Resume Point:   <feature name> -- <what was in progress>
Next Steps:
  1. <first thing to do>
  2. <second thing>

<When checkpoint exists, or find_work is not false:>
Action Items:   <count> items from Critic report
<Builder only>  Delivery plan: Phase X of Y -- next: <feature>
<QA only>       Verification queue: N features in TESTING
<PM only>       Figma MCP: <available | not available>
Uncommitted:    <none | summary>
<If role was provided as explicit argument (tier 1) AND system prompt contained a different role (tier 2):>
Session name:   run /rename <ProjectName> | <NewRole> to update
```

**Rename suggestion rules:**
- The rename suggestion appears ONLY when: (1) the user passed an explicit role argument to `/pl-resume` (tier 1 detection), AND (2) the system prompt contains role identity markers for a *different* role (tier 2 detection succeeded with a different role).
- When the role is unchanged (tier 1 == tier 2), or when no system prompt role markers exist (tier 2 did not detect a role), the "Session name:" line is omitted entirely.
- `<ProjectName>` is resolved by reading `project_name` from config (via `${TOOLS_ROOT}/config/resolve_config.py --key project_name`), falling back to the project directory basename when the key is absent or empty.
- `<NewRole>` uses the display name mapping: `architect` -> `Architect`, `builder` -> `Builder`, `qa` -> `QA`, `pm` -> `PM`.

### Step 7 -- Cleanup and Continue

- If a checkpoint file was read in Step 2, **delete it** (the role-scoped file `session_checkpoint_<role>.md` has been consumed). Any other role's checkpoint files remain untouched.
- Do NOT reset the context guard counter here. The restore flow consumes ~25-30 turns of real context during state gathering; resetting the counter at this point would cause the guard to misrepresent remaining budget. The only counter reset occurs in Step 0 (clearing stale state from the previous session).
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 6) gives the user visibility; they can interrupt if needed.
