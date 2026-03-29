---
name: config
description: View or change Purlin behavior settings (yolo, find-work, auto-start)
---

## Usage

```
purlin:config                     Show all settings
purlin:config yolo [on|off]       Toggle YOLO mode
purlin:config find-work [on|off]  Toggle work discovery
purlin:config auto-start [on|off] Toggle automatic execution
```

---

## No-Argument: Show All Settings

1. Read the resolved config via the `purlin_config` MCP tool (`action: "read"`).
2. Extract settings from `agents.purlin`:
   - `bypass_permissions` (default: `true`)
   - `find_work` (default: `true`)
   - `auto_start` (default: `false`)
3. Print the status table:

```
Purlin Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Setting       Value   What it does
  ──────        ─────   ────────────
  yolo          ON      Auto-approve all permission prompts
  find-work     ON      Scan for work when entering a mode
  auto-start    OFF     Begin executing work immediately on mode entry

Config file: .purlin/config.local.json
Change a setting: purlin:config <setting> on|off
Model & effort: use /model and /effort (native Claude Code settings)
```

Map values: `true` -> `ON`, `false` -> `OFF`.

---

## Setting: `yolo` (maps to `bypass_permissions`)

**What it controls:** When ON, Purlin auto-approves every permission prompt. No confirmation dialogs for bash commands, file writes, network requests, or any other action. Claude Code runs uninterrupted. When OFF, Claude Code's normal permission prompts appear and you review each action before it runs.

**When to turn it ON:** You trust Purlin to work autonomously and don't want to babysit every action. Best for focused implementation sessions where you'll review the results at the end.

**When to turn it OFF:** You want to see exactly what Purlin is about to do before it happens. Good for unfamiliar codebases, sensitive operations, or learning how Purlin works.

**How it works:** The `PermissionRequest` hook in `hooks/hooks.json` runs `permission-manager.sh` on every permission prompt. That script reads `agents.purlin.bypass_permissions` from config. If `true`, it tells Claude Code to allow the action. If `false`, it does nothing and Claude Code shows the normal prompt.

### Flow

1. Read current value: `purlin_config` MCP tool with `key: "agents.purlin.bypass_permissions"`.
2. **No argument** (just `purlin:config yolo`): Print current state and the description above.
3. **With `on`**: Write `true` via `purlin_config` MCP tool (`action: "write"`, `key: "agents.purlin.bypass_permissions"`, `value: true`). Print: `"YOLO mode is now ON. All permission prompts will be auto-approved."`
4. **With `off`**: Write `false`. Print: `"YOLO mode is now OFF. Permission prompts will appear for each action."`

---

## Setting: `find-work` (maps to `find_work`)

**What it controls:** When ON, entering a mode triggers a project scan that looks for unfinished features, open discoveries, pending verifications, and other work. Purlin presents what it found and suggests next steps. When OFF, Purlin enters the mode silently and waits for you to tell it what to do.

**When to turn it ON:** You want Purlin to orient itself when starting a session. Useful when you're not sure what needs doing, or when resuming after a break. This is the default.

**When to turn it OFF:** You already know exactly what you want to work on and don't want the scan overhead. Just enter a mode and give Purlin a direct instruction.

**How it works:** `purlin:resume` Step 9 reads `agents.purlin.find_work` from the resolved config. If `true`, it runs `purlin_scan` and `purlin:status` to discover work. If `false`, it skips the scan entirely and prints `"find_work disabled -- awaiting instruction."`.

**Interaction with auto-start:** If `find-work` is OFF, `auto-start` has no effect — there's nothing to auto-start because no work was discovered.

### Flow

1. Read current value: `purlin_config` MCP tool with `key: "agents.purlin.find_work"`.
2. **No argument** (just `purlin:config find-work`): Print current state and the description above.
3. **With `on`**: Write `true` via `purlin_config` MCP tool (`action: "write"`, `key: "agents.purlin.find_work"`, `value: true`). Print: `"Find-work is now ON. Mode entry will scan for work and suggest next steps."`
4. **With `off`**: Write `false`. Print: `"Find-work is now OFF. Mode entry will skip scanning — tell Purlin what to do."`

---

## Setting: `auto-start` (maps to `auto_start`)

**What it controls:** When ON, after discovering work (via find-work scan), Purlin begins executing the top-priority item immediately without asking for approval. When OFF, Purlin presents the work plan and waits for you to review it and say go.

**When to turn it ON:** You want fully autonomous sessions. Combined with YOLO mode and find-work, this is full autopilot — Purlin scans, picks the highest priority work, and starts executing. Best for trusted, well-specced projects where you want to kick off work and check back later.

**When to turn it OFF:** You want to review the work plan before Purlin starts. You can reorder priorities, skip items, or redirect Purlin to something else. This is the default and recommended for most workflows.

**How it works:** `purlin:resume` Step 9.5 reads `agents.purlin.auto_start` from the resolved config. If `true` and a mode is resolved, Purlin begins executing immediately after presenting the work plan. If `false`, it waits for user approval.

**Interaction with other settings:**
- **find-work OFF + auto-start ON**: Auto-start has no effect. Nothing was discovered, so there's nothing to start.
- **find-work ON + auto-start ON**: Full autopilot. Purlin scans for work and starts executing the top item.
- **find-work ON + auto-start OFF**: Purlin scans and presents the plan, then waits. This is the default.

### Flow

1. Read current value: `purlin_config` MCP tool with `key: "agents.purlin.auto_start"`.
2. **No argument** (just `purlin:config auto-start`): Print current state and the description above.
3. **With `on`**: Write `true` via `purlin_config` MCP tool (`action: "write"`, `key: "agents.purlin.auto_start"`, `value: true`). Print: `"Auto-start is now ON. Purlin will begin executing work immediately after scanning."`
4. **With `off`**: Write `false`. Print: `"Auto-start is now OFF. Purlin will present the work plan and wait for approval."`

---

## Preset Combinations

When showing the status table (no-argument mode), also print a brief guide to common combinations:

```
Common combinations:
  Supervised:   yolo OFF  + find-work ON  + auto-start OFF  (review everything)
  Trusted:      yolo ON   + find-work ON  + auto-start OFF  (auto-approve, pick your work)
  Autopilot:    yolo ON   + find-work ON  + auto-start ON   (fully autonomous)
  Direct:       yolo ON   + find-work OFF + auto-start OFF  (no scan, just tell me what to do)
```

---

## Error Handling

| Condition | Message | Action |
|---|---|---|
| Unknown setting name | `"Unknown setting '<name>'. Valid settings: yolo, find-work, auto-start."` | Stop |
| Invalid value (not on/off) | `"Invalid value '<value>'. Use 'on' or 'off'."` | Stop |
| Config read failure | `"Could not read Purlin config. Is .purlin/ initialized?"` | Stop |
| Config write failure | `"Could not write to config. Check file permissions on .purlin/config.local.json."` | Stop |
