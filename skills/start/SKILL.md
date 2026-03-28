---
name: start
description: Session entry point — replaces pl-run.sh launcher. Handles checkpoint recovery, mode activation, worktree entry, YOLO toggling, and session naming
---

**Purlin command: shared (all roles)**

Purlin agent: Session entry point that replaces the pl-run.sh launcher. Handles everything the launcher did, from within the running session.

---

## Usage

```
purlin:start [OPTIONS]

Session setup:
  --mode <pm|engineer|qa>    Activate a mode
  --build                    Shortcut: --mode engineer + auto-start
  --verify [feature]         Shortcut: --mode qa + auto-start [+ feature]
  --pm                       Shortcut: --mode pm
  --worktree                 Enter an isolated git worktree
  --yolo                     Enable auto-approve for all permission prompts (persists)
  --no-yolo                  Disable auto-approve (persists)
  --effort <high|medium>     Set effort level for this session
  --find-work <true|false>   Enable/disable work discovery (persists)

  No options: run checkpoint recovery + scan + suggest mode
```

---

## Execution Flow

### Step 0 -- Environment Detection

1. Check for `.purlin/` directory. If missing: "Run `purlin:init` first." Stop.
2. Read `.purlin/config.json` for project settings.
3. Check `${CLAUDE_PLUGIN_DATA}/session_state.json` for persisted session flags.

### Step 1 -- Flag Processing

- `--yolo`: Write `bypass_permissions: true` to `.purlin/config.json`. The PermissionRequest hook reads this and auto-approves all permission dialogs.
- `--no-yolo`: Write `bypass_permissions: false`.
- `--effort`: Execute `/effort <level>` (Claude Code built-in).
- `--find-work`: Write `find_work` to config.

### Step 2 -- Worktree Entry (only if `--worktree`)

1. Call `EnterWorktree` tool (Claude Code built-in).
2. Write `.purlin_worktree_label` (W1, W2, ...) and `.purlin_session.lock`.

### Step 3 -- Session Identity

1. Set terminal identity: iTerm badge + Warp tab + terminal title.
2. Rename session: `"<project> | <badge>"`

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<mode>" "<project>"
```

### Step 4 -- Checkpoint Recovery

Same as `purlin:resume` Steps 0-1. Merge breadcrumb check, stale reaping, checkpoint detection.

### Step 5 -- Work Discovery (if no checkpoint and find_work != false)

1. Run project scan via MCP (`purlin_scan` tool).
2. Run `purlin:status` to interpret results.
3. Suggest mode based on highest-priority work.

### Step 6 -- Mode Activation

Priority: CLI flag > checkpoint mode > config default_mode > user input.

- If `--build`: activate Engineer + invoke `purlin:build`.
- If `--verify`: activate QA + invoke `purlin:verify`.
- If `--pm`: activate PM mode.
- If `--mode <mode>`: activate the specified mode.

---

## Hook Integration

| Hook Event | Script | Purpose |
|---|---|---|
| SessionStart | session-start.sh | Context reminder: "Purlin active, run purlin:start" |
| SessionEnd | session-end-merge.sh | Merge worktrees, cleanup |
| PreToolUse (Write/Edit) | mode-guard.sh | Mechanical mode guard |
| PermissionRequest | permission-manager.sh | YOLO auto-approve |
| PreCompact | pre-compact-checkpoint.sh | Auto-save checkpoint |
| FileChanged | companion-debt-tracker.sh | Real-time companion debt |

**Design decision:** SessionStart hook does NOT auto-run the full startup. It only injects a brief reminder. Full protocol runs via `purlin:start`. This avoids heavy scan+status on every context clear.
