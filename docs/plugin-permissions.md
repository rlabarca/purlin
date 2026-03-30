# Plugin Permissions

How Purlin handles permissions across installation methods, and what to expect in different environments.

## Overview

Claude Code plugins cannot use `bypassPermissions` in marketplace installs — it's silently stripped for security. Purlin solves this with **hook-based permission management**: PreToolUse hooks inspect every tool call, classify it, and return `permissionDecision: "allow"` for authorized actions. No blanket bypass needed.

## How It Works

### Write/Edit Guard (`mode-guard.sh`)

Every `Write`, `Edit`, and `NotebookEdit` call is intercepted by a PreToolUse hook:

1. Extracts the target file path from the tool input
2. Classifies the file as **CODE**, **SPEC**, **QA**, or **INVARIANT** using `classify_file()`
3. Reads the current mode (Engineer, PM, QA, or none)
4. **If the write is authorized** (file class matches mode access): returns `permissionDecision: "allow"` — the tool call proceeds with no user prompt
5. **If the write is unauthorized** (wrong mode or no mode): returns exit code 2 with error on stderr — the tool call is blocked

### Bash Guard (`bash-guard.sh`)

Every `Bash` call is intercepted:

1. If a mode IS active: returns `permissionDecision: "allow"` (per-mode shell classification is too fragile to enforce)
2. If NO mode is active: checks for destructive patterns (`rm`, `git push`, redirects, etc.) and blocks them

### YOLO Mode (`permission-manager.sh`)

A `PermissionRequest` hook auto-approves remaining permission dialogs (MCP tool calls, Read access, etc.) when `bypass_permissions: true` in `.purlin/config.json`.

**YOLO is on by default.** Disable with:
```
purlin:config yolo off
```

## What Works Out of the Box

| Capability | Status |
|---|---|
| Write/Edit guard (mode enforcement) | Auto-approved by hook |
| Bash guard (default-mode safety) | Auto-approved by hook |
| YOLO auto-approve (MCP tools, Read, etc.) | On by default |
| MCP tool first-use prompt | Skipped (YOLO) |

Purlin does not use `permissionMode: bypassPermissions` (which is stripped for marketplace plugins). The hook-based approach provides the same autonomous experience.

## File Classification

The mode guard's `classify_file()` function is the permission gate. It determines which mode can write to which files:

| Classification | Writable by | Examples |
|---|---|---|
| **CODE** | Engineer | `src/`, `scripts/`, `tests/`, `agents/`, `hooks/`, config files, `.impl.md` companions |
| **SPEC** | PM | `features/*.md` (except `.impl.md`), `design_*.md`, `policy_*.md` |
| **QA** | QA | `.discoveries.md`, `regression.json`, `tests/qa/scenarios/` |
| **INVARIANT** | Nobody | `features/i_*` (imported standards) |

Default classification is CODE (most restrictive for PM/QA modes). Unknown files are never accidentally writable by the wrong mode.

## Enterprise Environments

Organizations using Claude Code managed settings should be aware of these controls:

### `allowManagedHooksOnly: true`

When set by an admin, this **silently disables all plugin hooks**. Purlin's mode guard, bash guard, and YOLO hooks will not fire. The agent will operate without write-boundary enforcement and will be prompted for every tool call.

**Mitigation:** The admin must whitelist Purlin's hooks or disable this restriction for Purlin projects.

### `allowManagedMcpServersOnly: true`

When set, this **blocks all plugin MCP servers**. Purlin's `purlin_mode`, `purlin_scan`, `purlin_classify`, and other tools will not be available.

**Mitigation:** The admin must whitelist the Purlin MCP server.

### Managed Plugin Force-Enable

Admins can force-enable Purlin via managed settings. Force-enabled plugins cannot be disabled by individual users.

## Hook Authoring Rules

For developers extending Purlin's hooks:

**Exit code 2 requires stderr.** Claude Code only blocks a tool call when exit code 2 is returned AND stderr has content. If stderr is empty, the tool call proceeds despite the non-zero exit. Every `echo "..." ; exit 2` MUST use `echo "..." >&2`.

**`permissionDecision: "allow"` on exit 0.** To auto-approve a tool call without user prompting, output JSON with `hookSpecificOutput.permissionDecision: "allow"` on stdout and exit 0. This is how the mode guard grants write access.

**Global deny rules still apply.** Even when a hook returns `permissionDecision: "allow"`, the user's global deny rules in `settings.json` take precedence. The hook cannot override an explicit user deny.

## Subagent Permissions

Worker subagents (`engineer-worker`, `pm-worker`, `qa-worker`) do not use `permissionMode: bypassPermissions`. Instead:

1. Each worker activates its mode via `purlin_mode()` as the first workflow step
2. The mode guard hook fires for all subagent tool calls (PreToolUse hooks apply to subagents)
3. Authorized writes are auto-approved via `permissionDecision: "allow"`
4. Unauthorized writes are blocked via exit 2

This works for all installation methods.
