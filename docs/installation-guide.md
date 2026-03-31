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
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git
```

This registers the Purlin catalog with Claude Code. No plugins are installed yet.

### Step 2: Install in Your Project

```bash
cd my-project
git init  # if not already a git repo

# Project scope — committed to .claude/settings.json, shared with teammates
claude plugin install purlin@purlin --scope project

# Or local scope — gitignored, just for you in this repo
claude plugin install purlin@purlin --scope local
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

```
purlin:spec login             # Create a spec
purlin:build login            # Implement it
purlin:verify login           # Verify it
purlin:status                 # See what needs doing
```

Use skills directly — no mode switching needed.

---

## Joining an Existing Project

When a teammate already installed Purlin with `--scope project`, the repo's `.claude/settings.json` has the plugin enabled. You just need the marketplace registered:

```bash
git clone <repo-url>
cd <project-name>
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git
claude
```

The plugin loads automatically. Run `purlin:resume` if you need to recover a previous session's state.

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
4. Hooks register (write guard, session recovery, checkpoint, sync tracking).
5. The MCP server starts (scan engine, dependency graph, mode state).
6. Your `CLAUDE.md` layers on top with project-specific context.

When you run `claude` in a directory without Purlin enabled, you get standard Claude Code with zero Purlin interference.

### What goes where

| Setting | Where | Scope |
|---|---|---|
| Marketplace registration | `~/.claude/settings.json` | All projects (makes plugin available) |
| Plugin enablement | `.claude/settings.json` (project) | This project only |
| Agent settings (auto-start, YOLO) | `.purlin/config.json` | This project |
| Local overrides (not committed) | `.purlin/config.local.json` | Your machine only |
| Project-specific rules | `CLAUDE.md` | This project |
| Credentials (Figma, deploy tokens) | macOS keychain (via plugin userConfig) | Your machine only |

---

## Updating Purlin

> **Do NOT run `purlin:init` on existing projects.** Init is only for brand new projects. For upgrades (including from v0.8.5 submodule), use `purlin:update`.

### 1. Update the plugin code

This pulls the latest skills, hooks, and scripts from the Purlin repo into your local plugin cache:

```bash
claude plugin update purlin@purlin
```

### 2. Run project migration

Inside a session:

```
purlin:update                    # Migrate project to current version
purlin:update --dry-run          # Preview the migration plan
```

This handles submodule removal, config migration, Figma-to-invariant conversion, file format transitions, and stale artifact cleanup. Your specs, features, and toolbox are never touched.

---

## Removing Purlin

Remove the plugin from your project:

```bash
# Remove from project scope (if installed with --scope project)
claude plugin uninstall purlin@purlin --scope project

# Remove from local scope (if installed with --scope local)
claude plugin uninstall purlin@purlin --scope local
```

This removes the plugin from Claude Code. Your project files (`.purlin/`, `features/`, specs) are left intact.

To also remove the marketplace registration:

```bash
claude plugin marketplace remove purlin
```

---

## Configuration

### Agent Settings

Use `purlin:config` to manage settings:

```
purlin:config                       # Show all settings
purlin:config yolo on               # Auto-approve permission prompts
purlin:config find-work off         # Skip startup scan
purlin:config auto-start on         # Start working immediately
```

Settings are stored in `.purlin/config.local.json` (gitignored). Model and effort are native Claude Code settings — use `/model` and `/effort`.

### Project-Specific Rules

Project-specific rules belong in `CLAUDE.md`, which is loaded automatically by Claude Code. Structured configuration (test tiers, agent settings) lives in `.purlin/config.json`.

### Credentials

Sensitive values (Figma access token, deploy token, Confluence credentials) are stored in the macOS keychain via Claude Code's plugin `userConfig` system. They are never written to plain-text files.

---

## Troubleshooting

**Plugin not loading?** Verify both layers:
1. You've run `claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git`.
2. `.claude/settings.json` in your project has `enabledPlugins: { "purlin@purlin": true }`.

**Skills not found?** Make sure you're running `claude` from the project root where `.claude/settings.json` exists. The plugin only loads when the project has it enabled.

**MCP tools not available?** Run `purlin:config yolo on` to auto-approve MCP tool access. If YOLO is off, you'll be prompted for each MCP tool on first use.

**Stale submodule artifacts?** If you upgraded from v0.8.5 and still see `purlin/`, `pl-run.sh`, or `.claude/commands/pl-*.md`, run `purlin:update` again inside a session to clean them up.

**Writes blocked?** If the write guard blocks a file, check if it's classified as INVARIANT (use `purlin:invariant sync`) or UNKNOWN (add a classification rule to CLAUDE.md). All other file types are writable without restriction.
