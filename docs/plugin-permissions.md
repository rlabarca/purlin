# Plugin Permissions

How Purlin handles permissions across installation methods, and what to expect in different environments.

## Overview

Claude Code plugins cannot use `bypassPermissions` in marketplace installs — it's silently stripped for security. Purlin solves this with **hook-based permission management**: PreToolUse hooks inspect every tool call, classify it, and return `permissionDecision: "allow"` for authorized actions. No blanket bypass needed.

## How It Works

### Write Guard (`write-guard.sh`)

Every `Write`, `Edit`, and `NotebookEdit` call is intercepted by a PreToolUse hook:

1. Extracts the target file path from the tool input
2. Classifies the file as **CODE**, **SPEC**, **QA**, **INVARIANT**, or **UNKNOWN** using `classify_file()`
3. **INVARIANT files**: blocked — use `purlin:invariant sync` to update from external source
4. **UNKNOWN files**: blocked — add classification to CLAUDE.md
5. **All other classified files**: returns `permissionDecision: "allow"` — the tool call proceeds with no user prompt

### YOLO Mode (`permission-manager.sh`)

A `PermissionRequest` hook auto-approves most permission dialogs (MCP tool calls, Read access, etc.) when `bypass_permissions: true` in `.purlin/config.json`.

**YOLO is on by default.** Disable with:
```
purlin:config yolo off
```

**Excluded from auto-approve** (user always prompted, even in YOLO mode):
- `AskUserQuestion` — agent asking the user to make a choice (migration confirmations, options, etc.)
- `ExitPlanMode` — agent proposing a plan for execution — user must review before it runs
- `RemoteTrigger` — triggers external scheduled agents with side effects outside the local session

## What Works Out of the Box

| Capability | Status |
|---|---|
| Write/Edit guard (file classification) | Auto-approved by hook |
| Bash guard (safety checks) | Auto-approved by hook |
| YOLO auto-approve (MCP tools, Read, etc.) | On by default |
| MCP tool first-use prompt | Skipped (YOLO) |

Purlin does not use `permissionMode: bypassPermissions` (which is stripped for marketplace plugins). The hook-based approach provides the same autonomous experience.

## File Classification

The write guard's `classify_file()` function is the permission gate. It classifies files to determine write access:

| Classification | Writable | Examples |
|---|---|---|
| **CODE** | Yes | `src/`, `scripts/`, `tests/`, `agents/`, `hooks/`, config files, `.impl.md` companions |
| **SPEC** | Yes | `features/*.md` (except `.impl.md`), `design_*.md`, `policy_*.md` |
| **QA** | Yes | `.discoveries.md`, `regression.json`, `tests/qa/scenarios/` |
| **INVARIANT** | No | `features/i_*` (imported standards — use `purlin:invariant sync`) |
| **UNKNOWN** | No | Unclassified files — add a rule to CLAUDE.md |

There are no role-based write restrictions. Any classified file type (CODE, SPEC, QA) is writable by anyone. The write guard only blocks INVARIANT and UNKNOWN files.

## Enterprise Environments

Organizations using Claude Code managed settings should be aware of these controls:

### `allowManagedHooksOnly: true`

When set by an admin, this **silently disables all plugin hooks**. Purlin's write guard, sync tracker, and YOLO hooks will not fire. The agent will operate without INVARIANT enforcement and will be prompted for every tool call.

**Mitigation:** The admin must whitelist Purlin's hooks or disable this restriction for Purlin projects.

### `allowManagedMcpServersOnly: true`

When set, this **blocks all plugin MCP servers**. Purlin's `purlin_sync`, `purlin_scan`, `purlin_classify`, and other tools will not be available.

**Mitigation:** The admin must whitelist the Purlin MCP server.

### Managed Plugin Force-Enable

Admins can force-enable Purlin via managed settings. Force-enabled plugins cannot be disabled by individual users.

## Hook Authoring Rules

For developers extending Purlin's hooks:

**Exit code 2 requires stderr.** Claude Code only blocks a tool call when exit code 2 is returned AND stderr has content. If stderr is empty, the tool call proceeds despite the non-zero exit. Every `echo "..." ; exit 2` MUST use `echo "..." >&2`.

**`permissionDecision: "allow"` on exit 0.** To auto-approve a tool call without user prompting, output JSON with `hookSpecificOutput.permissionDecision: "allow"` on stdout and exit 0. This is how the write guard grants write access.

**Global deny rules still apply.** Even when a hook returns `permissionDecision: "allow"`, the user's global deny rules in `settings.json` take precedence. The hook cannot override an explicit user deny.

## Subagent Permissions

Worker subagents (`engineer-worker`, `pm-worker`, `qa-worker`) do not use `permissionMode: bypassPermissions`. Instead:

1. The write guard hook fires for all subagent tool calls (PreToolUse hooks apply to subagents)
2. Classified writes (CODE, SPEC, QA) are auto-approved via `permissionDecision: "allow"`
3. INVARIANT and UNKNOWN writes are blocked via exit 2
4. Each worker's skill instructions define what it writes — the write guard enforces file classification

This works for all installation methods.
