**Purlin command: shared (all roles)**

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
**Delivery Plan:** <Phase X of Y -- STATUS, or "No delivery plan">
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

## Restore Mode (`/pl-resume` or `/pl-resume <role>`)

Execute this 8-step sequence:

### Step 0 -- (No-op)

No cleanup needed. The context guard uses a PreCompact hook with no runtime files (no counters, no session metadata). This step is retained as a placeholder for the step numbering sequence.

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

### Step 5 -- Gather Fresh Project State

Execute the core state-gathering sequence (always, both cases):

1. Read `.purlin/config.json` for role-specific settings.
2. Run `tools/cdd/status.sh` to regenerate the Critic report.
3. Read `CRITIC_REPORT.md` -- the role-specific subsection under "Action Items by Role".
4. Run `git status` for uncommitted changes.
5. Run `git log --oneline -10` for recent commit history.

**When no checkpoint exists (cold start):** additionally gather:
- Read `.purlin/cache/dependency_graph.json` for the feature graph.
- **Builder:** Read `.purlin/cache/delivery_plan.md` if it exists. Identify features in TODO state. List `features/tombstones/` for tombstone tasks. Read ALL anchor node files in `features/` (`arch_*.md`, `design_*.md`, `policy_*.md`).
- **QA:** Identify features in TESTING state from the Critic report. For each, read `verification_effort` from `tests/<feature_name>/critic.json`.
- **Architect:** Perform spec-level gap analysis on TODO/TESTING features.
- **PM:** Check for Figma MCP tools in the current session. If not available, inform the user and provide setup instructions.

**Startup flag handling (cold start only):**
When no checkpoint exists, check `startup_sequence` and `recommend_next_actions` from `.purlin/config.json` for the detected role:
- `startup_sequence: false` -- output `"startup_sequence disabled -- awaiting instruction."` after the recovery summary. Do not auto-generate a work plan.
- `recommend_next_actions: false` -- present only a brief status summary (feature counts, open Critic items) instead of a full work plan. Await user direction.
- Both `true` (default) -- proceed with full work plan generation.

When a checkpoint exists, startup flags are not consulted -- the checkpoint's "Next" list is the work plan regardless of flag values.

**When a checkpoint exists:** skip the dependency graph read and role-specific analysis (the checkpoint's work plan already incorporates these). Exception: if the checkpoint's `## Builder Context` lacks delivery plan info, the Builder SHOULD still read `.purlin/cache/delivery_plan.md`.

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

<Always:>
Action Items:   <count> items from Critic report
<Builder only>  Delivery plan: Phase X of Y -- next: <feature>
<QA only>       Verification queue: N features in TESTING
<PM only>       Figma MCP: <available | not available>
Uncommitted:    <none | summary>
```

### Step 7 -- Cleanup and Continue

- If a checkpoint file was read in Step 2, **delete it** (the role-scoped file `session_checkpoint_<role>.md` has been consumed). Any other role's checkpoint files remain untouched.
- Immediately begin executing the work plan starting with the first item. Do NOT ask for confirmation. The recovery summary (Step 6) gives the user visibility; they can interrupt if needed.
