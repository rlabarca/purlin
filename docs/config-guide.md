# Configuration Guide

Purlin has three behavior settings that control how autonomous the agent is during a session. All settings are managed with `purlin:config` and persist across sessions.

---

## Quick Start

```
purlin:config                       # Show all settings
purlin:config yolo on               # Auto-approve all permission prompts
purlin:config find-work off         # Skip the startup scan
purlin:config auto-start on         # Start working immediately
```

---

## Settings

### YOLO Mode

```
purlin:config yolo [on|off]
```

Controls whether Claude Code's permission prompts appear during the session.

| Value | Behavior |
|-------|----------|
| **ON** | Every permission prompt is auto-approved. Bash commands, file writes, network requests — everything runs without asking. |
| **OFF** | Normal Claude Code behavior. Each action that requires permission shows a prompt and waits for you to approve or deny. |

**Default:** ON

**When to use ON:** You trust Purlin to work autonomously and want uninterrupted execution. Best for focused implementation sessions where you'll review the results at the end.

**When to use OFF:** You want to see exactly what Purlin is about to do before it happens. Good for unfamiliar codebases, sensitive operations, or learning how Purlin works.

**How it works:** A `PermissionRequest` hook runs on every permission prompt. It reads the `bypass_permissions` flag from your config. If true, it tells Claude Code to allow the action silently. If false, it does nothing and the normal prompt appears.

---

### Find Work

```
purlin:config find-work [on|off]
```

Controls whether Purlin scans the project for work when entering a mode or recovering a session.

| Value | Behavior |
|-------|----------|
| **ON** | Entering a mode triggers a project scan that finds unfinished features, open discoveries, pending verifications, and other work. Purlin presents what it found and suggests next steps. |
| **OFF** | Purlin enters the mode silently and waits. No scan, no suggestions — you tell it what to do. |

**Default:** ON

**When to use ON:** You want Purlin to orient itself at the start of a session. Useful when you're not sure what needs doing, when resuming after a break, or when you want the agent to find the highest-priority work across modes.

**When to use OFF:** You already know exactly what you want to work on. Skipping the scan saves time and context window, especially in large projects with many features.

---

### Auto Start

```
purlin:config auto-start [on|off]
```

Controls whether Purlin begins executing work immediately after discovering it.

| Value | Behavior |
|-------|----------|
| **ON** | After scanning for work (if find-work is ON), Purlin picks the highest-priority item and starts executing immediately. No pause, no approval prompt. |
| **OFF** | Purlin presents the work plan and waits for you to review it. You can reorder priorities, skip items, or redirect to something else before it starts. |

**Default:** OFF

**When to use ON:** You want fully autonomous sessions. Kick off a session and check back later. Best for well-specced projects where the work queue is clear.

**When to use OFF:** You want to review the work plan before anything happens. You might want to pick a different feature, change the order, or give specific instructions.

**Interaction with find-work:** Auto-start has no effect when find-work is OFF. If Purlin didn't scan for work, there's nothing to auto-start — it waits for your instruction regardless.

---

## Common Combinations

| Style | YOLO | Find Work | Auto Start | What Happens |
|-------|------|-----------|------------|--------------|
| **Supervised** | OFF | ON | OFF | Purlin scans for work, presents a plan, and asks permission for every action. Maximum visibility. |
| **Trusted** | ON | ON | OFF | Purlin scans and presents work, you pick what to do, and it runs without interruption. Good balance of control and speed. |
| **Autopilot** | ON | ON | ON | Purlin scans, picks the top item, and starts building. Full autonomy. |
| **Direct** | ON | OFF | OFF | No scan, no prompts. You tell Purlin exactly what to do and it executes immediately. Fastest for targeted tasks. |

---

## Config File Layering

Purlin uses a two-file config system that separates team defaults from personal preferences.

### Team Config (committed)

`.purlin/config.json` is checked into git. It contains the team's default settings — the baseline every contributor starts from. When someone clones the project and runs their first session, they get these defaults.

### Local Config (per-machine)

`.purlin/config.local.json` is gitignored. It stores your personal overrides. Every `purlin:config` write goes here, so your preferences never leak into the team's committed config.

### How They Interact

1. On first session, `config.local.json` is created as a copy of `config.json`.
2. All reads check `config.local.json` first. If it exists and is valid, it wins entirely.
3. All writes go to `config.local.json`. The committed `config.json` is never modified by the agent.
4. When the team adds new settings to `config.json`, running `purlin:update` syncs the new keys into your `config.local.json` without overwriting your existing values.

This means:
- A team lead sets sensible defaults in `config.json` and commits them.
- Each developer's personal preferences (YOLO on/off, auto-start on/off) stay local.
- New settings introduced by the team appear in your local config after `purlin:update`.

---

## Model and Effort

Model and effort are **not** Purlin settings. They are native Claude Code settings.

- **Model:** Set with `/model` inside a session, or `claude --model <id>` at launch.
- **Effort:** Set with `/effort` inside a session.

These settings are managed by Claude Code directly and apply to all tool use, not just Purlin.

---

## Relationship to `purlin:resume` Flags

`purlin:resume` accepts `--yolo`, `--no-yolo`, `--find-work`, and `--auto-start` as convenience flags. These are shortcuts that write to the same config keys as `purlin:config`. Use whichever is more convenient:

| Flag | Equivalent |
|------|------------|
| `purlin:resume --yolo` | `purlin:config yolo on` |
| `purlin:resume --no-yolo` | `purlin:config yolo off` |
| `purlin:resume --find-work true` | `purlin:config find-work on` |
| `purlin:resume --find-work false` | `purlin:config find-work off` |

The `--no-save` flag on `purlin:resume` applies the setting for the current session only without writing to config. `purlin:config` always persists.
