# Installation Guide

## Overview

Purlin is a Claude Code plugin installed per-project via the marketplace. You register the marketplace once, then install in each project where you want spec-driven development.

---

## Prerequisites

- Git (any recent version)
- Python 3.8+ (used by the MCP server and tooling scripts)
- Claude Code CLI (`claude`) **1.0.33 or later**, installed and authenticated
- Node.js (optional, for web testing via Playwright)

---

## Install

### Step 1: Add the Purlin Marketplace (One Time)

```bash
claude plugin marketplace add boomerangdev/purlin
```

This registers the Purlin catalog with Claude Code. No plugins are installed yet.

### Step 2: Install in Your Project

```bash
cd my-project
git init  # if not already a git repo

# Project scope — committed to .claude/settings.json, shared with teammates
claude plugin install purlin@boomerangdev-purlin --scope project

# Or local scope — gitignored, just for you in this repo
claude plugin install purlin@boomerangdev-purlin --scope local
```

### Step 3: Initialize

```bash
claude
```

Inside the Claude Code session:

```
purlin:init
```

This scaffolds the project structure. Commit the result:

```bash
git add -A && git commit -m "init purlin"
```

---

## What `purlin:init` Creates

```
my-project/
├── .claude/
│   └── settings.json          # Plugin enablement (committed)
├── .purlin/
│   ├── config.json            # Agent settings
│   ├── cache/                 # Scan output (gitignored)
│   ├── runtime/               # Session state (gitignored)
│   └── toolbox/               # Project and community tools
├── features/                  # Feature specifications
├── CLAUDE.md                  # References Purlin plugin
└── .gitignore                 # Updated with Purlin patterns
```

`purlin:init` also creates `.claude/settings.json` with the plugin enabled:

```json
{
  "enabledPlugins": { "purlin@purlin": true }
}
```

This file is committed to git so that everyone who clones the repo gets the plugin activated automatically (once they have the marketplace registered).

### Start working

On first launch in a new project, the agent enters PM mode and asks what you're building. Just tell the agent what you want in plain language:

> "spec a login feature, then build and verify it"

The agent switches modes automatically. You can also use explicit commands:

```
purlin:spec login             # PM mode — create a spec
purlin:build login            # Engineer mode — implement it
purlin:verify login           # QA mode — verify it
purlin:mode engineer          # switch modes without starting a workflow
```

---

## Joining an Existing Project

When a teammate already installed Purlin with `--scope project`, the repo's `.claude/settings.json` has the plugin enabled. You just need the marketplace registered:

```bash
git clone <repo-url>
cd <project-name>
claude plugin marketplace add boomerangdev/purlin
claude
```

The plugin loads automatically. The `SessionStart` hook handles context recovery.

If `.purlin/` doesn't exist yet (first team member to use Purlin on this project), run `purlin:init` inside the session.

---

## How the Plugin Layers Work

### Global layer (user-level)

The marketplace registration tells Claude Code where to find Purlin. It does NOT activate Purlin in any project — it just makes it available for install.

### Project layer

`.claude/settings.json` (committed to git) enables the plugin for this specific project. When you run `claude` in this directory:

1. Claude Code sees `enabledPlugins: { "purlin@purlin": true }`.
2. It loads the Purlin plugin from its cache.
3. The plugin's `settings.json` activates the Purlin agent, replacing the default Claude behavior.
4. Hooks register (mode guard, session recovery, checkpoint, companion tracking).
5. The MCP server starts (scan engine, dependency graph, mode state).
6. Your `CLAUDE.md` layers on top with project-specific context.

When you run `claude` in a directory without Purlin enabled, you get standard Claude Code with zero Purlin interference.

### What goes where

| Setting | Where | Scope |
|---|---|---|
| Marketplace registration | `~/.claude/settings.json` | All projects (makes plugin available) |
| Plugin enablement | `.claude/settings.json` (project) | This project only |
| Agent settings (model, auto-start) | `.purlin/config.json` | This project |
| Local overrides (not committed) | `.purlin/config.local.json` | Your machine only |
| Project-specific rules | `CLAUDE.md` | This project |
| Credentials (Figma, deploy tokens) | macOS keychain (via plugin userConfig) | Your machine only |

---

## Updating Purlin

Inside any agent session:

```
purlin:update                    # Update to latest release tag
purlin:update v0.8.7             # Update to a specific version
purlin:update --dry-run          # Preview without modifying anything
```

This handles all updates including file/format transitions from v0.8.5 (submodule removal, stale artifact cleanup, plugin model switch). Your specs, config, and toolbox are never touched — only plugin internals are updated.

---

## Configuration

### Agent Settings

Edit `.purlin/config.json` to change:

- Which Claude model to use.
- Reasoning effort level (low, medium, high).
- Whether the agent discovers work at startup (`find_work`).
- Whether the agent starts executing immediately (`auto_start`).

### Local Overrides

Create `.purlin/config.local.json` to override settings without modifying the shared config. This file is gitignored and takes precedence over `config.json`.

### Project-Specific Rules

Project-specific rules belong in `CLAUDE.md`, which is loaded automatically by Claude Code. Structured configuration (test tiers, agent settings) lives in `.purlin/config.json`.

### Credentials

Sensitive values (Figma access token, deploy token, Confluence credentials) are stored in the macOS keychain via Claude Code's plugin `userConfig` system. They are never written to plain-text files.

---

## Troubleshooting

**Plugin not loading?** Verify both layers:
1. You've run `claude plugin marketplace add boomerangdev/purlin`.
2. `.claude/settings.json` in your project has `enabledPlugins: { "purlin@purlin": true }`.

**Skills not found?** Make sure you're running `claude` from the project root where `.claude/settings.json` exists. The plugin only loads when the project has it enabled.

**MCP tools not available?** The YOLO mode (`bypass_permissions: true` in `.purlin/config.json`) auto-approves MCP tool access. If you've disabled YOLO, you'll be prompted for each MCP tool on first use.

**Stale submodule artifacts?** If you upgraded from v0.8.5 and still see `purlin/`, `pl-run.sh`, or `.claude/commands/pl-*.md`, run `purlin:update` again inside a session to clean them up.

**Agent says "no mode active"?** This is expected. In open mode (no mode set), the agent blocks all file writes. Run `purlin:mode engineer` (or pm/qa) to activate a mode.
