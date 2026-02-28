**Purlin command: shared (all roles)**

Save or restore agent session state across context clears and terminal restarts.

```
/pl-resume [save | <role>]
```

- **No argument:** Restore mode with role auto-detection.
- **`save`:** Save mode -- write a checkpoint file.
- **`<role>`** (`architect`, `builder`, `qa`): Restore mode with explicit role.
- **Invalid argument:** Print error listing valid options (`save`, `architect`, `builder`, `qa`) and stop.

---

## Save Mode (`/pl-resume save`)

Write a structured checkpoint to `.purlin/cache/session_checkpoint.md`. Compose the file based on your own understanding of your current session state. Do NOT commit the file (`.purlin/cache/` is gitignored).

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

### After Writing

Print confirmation:

```
Checkpoint saved to .purlin/cache/session_checkpoint.md
Role: <role> | Branch: <branch> | Feature: <feature or "none">
You can now /clear or close the terminal. Run /pl-resume to recover.
```

---

## Restore Mode (`/pl-resume` or `/pl-resume <role>`)

Execute this 7-step sequence:

### Step 1 -- Role Detection (3-Tier Fallback)

1. **Explicit argument:** If the user invoked `/pl-resume <role>`, use that role.
2. **System prompt inference:** Check if role identity markers are present in the current system prompt (e.g., "Role Definition: The Builder", "Role Definition: The Architect", "Role Definition: The QA"). If found, use the detected role.
3. **Ask user:** If neither method succeeds, prompt the user to select their role from `architect`, `builder`, `qa`.

### Step 2 -- Checkpoint Detection

Check if `.purlin/cache/session_checkpoint.md` exists.

- **Found:** Read the file. Present the saved state as a summary block. The checkpoint's "Next" list becomes the starting work plan.
- **Not found:** Print `"No checkpoint found -- recovering from project state only."` and continue.

### Step 3 -- Instruction Reload (Fresh Sessions Only)

This step runs ONLY when the system prompt does NOT contain the role's base instructions (i.e., the agent was started without a launcher script).

When instruction reload is needed:
1. Read the 4 instruction layers in order:
   - `instructions/HOW_WE_WORK_BASE.md`
   - `instructions/{ROLE}_BASE.md` (where ROLE is ARCHITECT, BUILDER, or QA)
   - `.purlin/HOW_WE_WORK_OVERRIDES.md`
   - `.purlin/{ROLE}_OVERRIDES.md`
2. Present a condensed "Role Compact" -- key mandates, prohibitions, and protocol summaries extracted from the instructions. This is NOT a full file dump; it is a focused digest of the most critical rules.

When the system prompt already contains the role instructions (agent was started via launcher), skip this step entirely and print: `"Instructions already loaded via launcher -- skipping reload."`

### Step 4 -- Command Table

1. Read `instructions/references/{role}_commands.md` (where role is `architect`, `builder`, or `qa`).
2. Detect the current branch via `git rev-parse --abbrev-ref HEAD`.
3. Print the appropriate variant (main branch or isolated session) verbatim.

### Step 5 -- Gather Fresh Project State

Execute the standard state-gathering sequence:

1. Read `.purlin/config.json` for role-specific settings.
2. Run `tools/cdd/status.sh` to regenerate the Critic report.
3. Read `CRITIC_REPORT.md` -- the role-specific subsection under "Action Items by Role".
4. Read `.purlin/cache/dependency_graph.json` for the feature graph.
5. Run `git status` for uncommitted changes.
6. Run `git log --oneline -10` for recent commit history.

Role-specific additions:
- **Builder:** Read `.purlin/cache/delivery_plan.md` if it exists. Identify features in TODO state.
- **QA:** Identify features in TESTING state from the Critic report.
- **Architect:** Perform spec-level gap analysis on TODO/TESTING features.

### Step 6 -- Present Recovery Summary

Print this structured summary:

```
--- Context Restored ---
Role:           <Architect | Builder | QA>
Branch:         <main | isolated/<name>>
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
Uncommitted:    <none | summary>
---
```

### Step 7 -- Cleanup and Confirm

- If a checkpoint file was read in Step 2, **delete it** (it has been consumed).
- Ask: **"Ready to continue from here, or would you like to adjust?"**
- If the user says "go" (or equivalent), begin executing the work plan.
- If the user provides modifications, adjust accordingly.
