# Agent Configuration Guide

## Overview

Purlin runs four AI agents -- PM, Architect, Builder, and QA -- each with its own
role and responsibilities. The Agent Config panel in the [CDD Dashboard](status-grid-guide.md) lets you
control how each agent behaves: which Claude model it uses, how much optimization
effort it applies, whether it asks for permission before using tools, and how
autonomously it operates at session start.

You might change these settings to:

- Use a faster, cheaper model for routine QA checks.
- Disable auto-start so an agent waits for your approval before acting.
- Turn off YOLO mode when you want to review every tool invocation.
- Switch the Builder to an extended-context model for large codebases.

All changes take effect on the next agent session launch. The dashboard saves
automatically -- there is no save button.


## The Agent Config Panel

Open the [CDD Dashboard](status-grid-guide.md) and look for the **Agent Config** section below the
Workspace section. It is collapsed by default; click the heading to expand it.

![CDD Dashboard Agent Config Section](images/cdd-dashboard-overview.png)

When expanded, the panel displays a grid with a header row and four agent rows:

```
           MODEL              EFFORT    YOLO    Find     Auto
                                                Work     Start
PM         [Opus 4.6      v]  [high v]   [x]    [ ]      [ ]
ARCHITECT  [Opus 4.6 [1M] v]  [high v]   [x]    [ ]      [ ]
BUILDER    [Opus 4.6 [1M] v]  [high v]   [x]    [x]      [x]
QA         [Sonnet 4.6    v]  [med  v]   [x]    [x]      [x]
```

Each row contains:

- **Agent name** -- PM, Architect, Builder, or QA.
- **Model dropdown** -- selects which Claude model the agent uses.
- **Effort dropdown** -- sets the optimization level (low, medium, high).
- **YOLO checkbox** -- toggles automatic tool permission bypass.
- **Find Work checkbox** -- toggles the startup orientation protocol.
- **Auto Start checkbox** -- toggles immediate execution of the work plan.

When collapsed, the section heading shows a badge summarizing the configured
models, such as `2x Opus 4.6 [1M] | 1x Opus 4.6 | 1x Sonnet 4.6`.


## Choosing a Model

The model dropdown lists all Claude models defined in your project's config.
Each model has different characteristics:

| Model | ID | Best For |
|-------|----|----------|
| **Opus 4.6** | `claude-opus-4-6` | High-stakes work requiring maximum reasoning capability. Good default for PM and Architect roles where accuracy matters more than speed. |
| **Opus 4.6 [1M]** | `claude-opus-4-6[1m]` | Same capabilities as Opus 4.6 with extended context (1M tokens). Ideal for Builder and Architect roles that need to process large codebases or lengthy specs. Note: uses additional credits on Pro plans. |
| **Sonnet 4.6** | `claude-sonnet-4-6` | Balanced capability and speed. A practical choice for QA and PM roles where tasks are more structured and predictable. |
| **Haiku 4.5** | `claude-haiku-4-5-20251001` | Fastest response time, lowest cost. Suitable for simple, repetitive tasks where speed matters more than deep reasoning. |

**Cost guidance:** Opus models consume more credits per interaction than Sonnet,
and Sonnet more than Haiku. The extended-context Opus 4.6 [1M] variant uses
additional credits beyond standard Opus 4.6. If you are on a Pro plan, a warning
appears when you select Opus 4.6 [1M]; you can dismiss this warning and it will
not appear again.

Choose the most capable model you can afford for roles that do complex reasoning
(Architect, Builder) and consider lighter models for roles with more structured
workflows (QA, PM).


## Setting Effort Level

The effort dropdown controls prompt verbosity and optimization depth:

| Level | Behavior |
|-------|----------|
| **low** | Minimal prompt elaboration. The agent works quickly with less detailed reasoning. Best when tasks are simple and well-defined. |
| **medium** | Balanced prompt detail. The agent provides moderate reasoning without excessive elaboration. Good for routine work. |
| **high** | Maximum prompt elaboration. The agent reasons thoroughly and produces detailed output. Best for complex implementation, architectural decisions, and thorough code review. |

Higher effort generally produces better results for ambiguous or complex tasks,
but takes longer and uses more tokens. The default is `high` for Architect and
Builder (where thoroughness matters most) and `medium` for PM and QA.


## Understanding the Checkboxes

### YOLO (Bypass Permissions)

When **checked** (the default for all agents), the agent automatically approves
tool invocations -- file reads, writes, bash commands -- without asking you first.
This is the normal workflow for trusted development environments.

When **unchecked**, the agent pauses before each tool use and asks for your
explicit permission. This is useful when:

- You are running an agent on an unfamiliar or sensitive codebase.
- You want to observe exactly what the agent does step by step.
- You are debugging unexpected agent behavior.

Most users leave YOLO enabled for all agents and disable it selectively when
troubleshooting.

### Find Work

When **checked**, the agent runs its full startup orientation at session start:
it checks CDD status, reads [the Critic](critic-and-cdd-guide.md) report, analyzes dependencies, and
presents a prioritized work plan for your review.

When **unchecked**, the agent skips all orientation. After printing its command
table, it outputs `"find_work disabled -- awaiting instruction."` and waits for
you to tell it what to do. This is useful when:

- You know exactly what you want the agent to do and do not need suggestions.
- You want to minimize startup time and token usage.
- You are running a quick one-off task.

### Auto Start

When **checked** (requires Find Work to also be checked), the agent executes its
work plan immediately after presenting it, without waiting for your approval.

When **unchecked**, the agent presents its work plan and explicitly asks for your
confirmation or adjustments before proceeding. This gives you a chance to review,
reorder, or reject items before work begins.

Auto Start is designed for experienced users who trust the agent's prioritization
and want minimal friction. If you are new to Purlin or working in a sensitive
area, leave it unchecked so you can review plans before execution.


## The Cascade Constraint

Auto Start depends on Find Work. You cannot enable Auto Start if Find Work is
disabled -- there would be no work plan to auto-start from.

The dashboard enforces this constraint automatically:

1. **Uncheck Find Work** -- Auto Start is immediately unchecked and grayed out
   (disabled). The config is saved with both values set to `false`.

2. **Re-check Find Work** -- Auto Start is re-enabled and restored to whatever
   state it had before you unchecked Find Work.

3. **The invalid combination** `find_work: false` + `auto_start: true` is
   rejected at every level: the dashboard prevents it in the UI, the API rejects
   it with a 400 error, and the launcher scripts refuse to start if they
   encounter it in the config file.

**Example:** You have the Builder set to Find Work: on, Auto Start: on (fully
autonomous). You uncheck Find Work because you want to give the Builder a
specific task. Auto Start automatically turns off and grays out. When you later
re-check Find Work, Auto Start flips back on -- restoring the Builder to its
previous fully autonomous configuration.


## Configuration Layering

Purlin uses a two-file configuration system:

| File | Git Status | Purpose |
|------|------------|---------|
| `.purlin/config.json` | Committed | Team defaults. Shared across all collaborators. |
| `.purlin/config.local.json` | Gitignored | Your personal overrides. Never committed. |

### How it works

- **Reading:** The system checks for `config.local.json` first. If it exists, it
  is used as the entire configuration. If it does not exist, `config.json` is
  used instead. There is no merging -- the local file completely replaces the
  shared file when present.

- **Copy-on-first-access:** The first time any tool reads config and no
  `config.local.json` exists, the resolver automatically copies `config.json`
  to `config.local.json`. From that point forward, all reads and writes target
  the local file. This happens on the first read, not just on the first save.

- **Writing:** All changes from the dashboard (and from the `/pl-agent-config`
  command) write to `config.local.json`. The shared `config.json` is never
  modified by these tools.

### Resetting to team defaults

If your team updates `config.json` with new defaults (for example, adding a new
model or changing default effort levels), your local file will not pick up those
changes automatically. To reset:

1. Delete `.purlin/config.local.json`.
2. The next tool or dashboard access reads `config.json` directly and creates a
   fresh local copy.

Alternatively, when you run `/pl-update-purlin`, the config sync step
automatically adds any new keys from `config.json` to your local file without
overwriting your existing preferences.


## Common Configurations

### "I want the Builder to just go"

Set the Builder to maximum autonomy:

| Setting | Value |
|---------|-------|
| Model | Opus 4.6 [1M] |
| Effort | high |
| YOLO | checked |
| Find Work | checked |
| Auto Start | checked |

The Builder starts up, identifies the highest-priority work, and begins
implementing immediately. You only intervene when something needs your attention.

### "I want to review everything before agents act"

Set all agents to supervised mode:

| Setting | Value |
|---------|-------|
| YOLO | unchecked (all agents) |
| Find Work | checked (all agents) |
| Auto Start | unchecked (all agents) |

Every agent presents its work plan for your approval and asks permission before
each tool use. This gives you full visibility and control at the cost of more
interaction.

### "I want to use cheaper models for routine work"

Assign models by task complexity:

| Agent | Model | Rationale |
|-------|-------|-----------|
| Architect | Opus 4.6 | Complex design decisions need top-tier reasoning. |
| Builder | Opus 4.6 [1M] | Implementation benefits from extended context. |
| QA | Sonnet 4.6 | Verification tasks are well-structured. |
| PM | Haiku 4.5 | Status checks and coordination are straightforward. |

This configuration reduces credit usage while keeping the most capable models on
the roles that benefit most from them.

### "I want a quick one-off task from the Builder"

Temporarily disable startup orientation:

| Setting | Value |
|---------|-------|
| Find Work | unchecked |
| Auto Start | (automatically unchecked and disabled) |

The Builder skips all orientation and waits for your direct instruction. When you
are done, re-check Find Work to restore normal behavior.
