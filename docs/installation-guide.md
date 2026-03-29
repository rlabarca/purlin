# Installation Guide

## Overview

Purlin is a Claude Code plugin. There are two ways to load it: point Claude Code at a local clone with `--plugin-dir`, or register the plugin source in your user settings for automatic loading. Either way, you start sessions with `claude` and initialize projects with `purlin:init` from inside the session.

---

## Prerequisites

- Git (any recent version)
- Python 3.8+ (used by the MCP server and tooling scripts)
- Claude Code CLI (`claude`) **2.1.81 or later**, installed and authenticated
- Node.js (optional, for web testing via Playwright)

---

## Option A: Load from a Local Clone (Simplest)

Clone the Purlin repo and use `--plugin-dir` to load it. No marketplace registration or settings changes needed.

```bash
git clone git@bitbucket.org:boomerangdev/purlin.git
```

Then create your project and initialize:

```bash
mkdir my-project && cd my-project
git init
claude --plugin-dir ../purlin
```

Inside the Claude Code session:

```
purlin:init
```

Every subsequent session, load the plugin the same way:

```bash
claude --plugin-dir ../purlin
```

> **Tip:** Create a shell alias to avoid typing the flag every time:
> ```bash
> alias purlin='claude --plugin-dir /path/to/purlin'
> ```

---

## Option B: Register via Marketplace (Persistent)

Register the plugin source once in your user-level settings. After that, `claude` loads Purlin automatically in any project that has it enabled — no `--plugin-dir` flag needed.

### Step 1: Register the Plugin Source (One Time)

Edit `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__purlin__*"
    ]
  },
  "extraKnownMarketplaces": {
    "purlin": {
      "source": "settings",
      "plugins": [{
        "name": "purlin",
        "source": { "source": "url", "url": "https://bitbucket.org/boomerangdev/purlin.git" }
      }]
    }
  }
}
```

If you already have content in `~/.claude/settings.json`, merge the `permissions` and `extraKnownMarketplaces` keys into your existing file.

The `permissions.allow` entry pre-approves Purlin's MCP tools so you aren't prompted for each one on first use.

### Step 2: Create and Initialize Your Project

```bash
mkdir my-project && cd my-project
git init
claude
```

Inside the Claude Code session:

```
purlin:init
```

Exit and re-enter Claude Code so the plugin loads fully:

```bash
claude
```

---

## What `purlin:init` Creates

Both options produce the same project structure:

```
my-project/
├── .claude/
│   └── settings.json          # Plugin enablement (committed)
├── .purlin/
│   ├── config.json            # Agent settings
│   ├── PURLIN_OVERRIDES.md    # Project-specific rules
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

This file is committed to git so that everyone who clones the repo gets the plugin activated automatically (if they have the marketplace source registered, or use `--plugin-dir`).

### Commit the scaffold

```bash
git add -A && git commit -m "init purlin"
```

### Start working

On first launch in a new project, the agent enters PM mode and asks what you're building. If you have Figma designs, paste the URL when asked. It creates your first spec and tells you what to do next.

Switch modes inside the session, or invoke any mode-specific skill directly:

```
purlin:mode engineer          # switch to Engineer mode
purlin:build login            # activates Engineer mode and starts building
purlin:spec login             # activates PM mode and starts a spec
purlin:verify login           # activates QA mode and starts verification
```

---

## Joining an Existing Project

When a team member clones a Purlin project, the plugin is already enabled via the committed `.claude/settings.json`:

```bash
git clone <repo-url>
cd <project-name>
claude                        # if marketplace source registered (Option B)
claude --plugin-dir ../purlin # or point at a local clone (Option A)
```

The plugin loads automatically because `.claude/settings.json` contains `enabledPlugins`. The `SessionStart` hook handles context recovery.

**Prerequisite:** The team member must have either registered the marketplace source ([Option B](#option-b-register-via-marketplace-persistent)) or use `--plugin-dir` to point at a local clone of Purlin.

If `.purlin/` doesn't exist yet (first team member to use Purlin on this project), run `purlin:init` inside the session.

---

## How the Plugin Layers Work

The Purlin plugin combines two layers of configuration:

### Global layer (user-level)

`~/.claude/settings.json` registers the plugin source. This is shared across all projects on your machine. It tells Claude Code "Purlin exists and can be found at this repo." It does NOT activate Purlin in any project.

### Project layer

`.claude/settings.json` (committed to git) enables the plugin for this specific project. When you run `claude` in this directory:

1. Claude Code sees `enabledPlugins: { "purlin@purlin": true }`.
2. It loads the Purlin plugin from its cache.
3. The plugin's `settings.json` activates the Purlin agent, replacing the default Claude behavior.
4. Hooks register (mode guard, session recovery, checkpoint, companion tracking).
5. The MCP server starts (scan engine, dependency graph, mode state).
6. Your `CLAUDE.md` and `.purlin/PURLIN_OVERRIDES.md` layer on top.

When you run `claude` in a directory without Purlin enabled, you get standard Claude Code with zero Purlin interference.

### What goes where

| Setting | Where | Scope |
|---|---|---|
| Plugin source registration | `~/.claude/settings.json` | All projects (makes plugin available) |
| Plugin enablement | `.claude/settings.json` (project) | This project only |
| Agent settings (model, auto-start) | `.purlin/config.json` | This project |
| Local overrides (not committed) | `.purlin/config.local.json` | Your machine only |
| Project-specific rules | `.purlin/PURLIN_OVERRIDES.md` | This project |
| Credentials (Figma, deploy tokens) | macOS keychain (via plugin userConfig) | Your machine only |

---

## Updating Purlin

### Agent-Assisted Update (Recommended)

Inside any agent session:

```
purlin:update                    # Update to latest release tag
purlin:update v0.8.7             # Update to a specific version
purlin:update --dry-run          # Preview without modifying anything
```

The agent fetches the latest version, refreshes skills and hooks, and resolves any conflicts with your local customizations.

### What Gets Updated

- Skills, hooks, agents, references, templates (plugin internals)
- MCP server and script updates

### What Is Never Touched

- `.purlin/config.json` and `config.local.json`
- `.purlin/PURLIN_OVERRIDES.md`
- `features/` directory
- `.purlin/toolbox/` (your project and community tools)

---

## Upgrading from v0.8.5 (Submodule to Plugin)

If your project currently uses the submodule model (has a `purlin/` directory):

1. Complete [Step 1](#step-1-register-the-plugin-one-time) if you haven't already.

2. Inside an agent session on your project:
   ```
   purlin:update
   ```

3. The update skill detects the submodule and handles the transition:
   - Removes the `purlin/` submodule and `.gitmodules` entry
   - Deletes stale artifacts (`pl-run.sh`, `pl-init.sh`, `.claude/commands/pl-*.md`)
   - Creates `.claude/settings.json` with `enabledPlugins`
   - Migrates config paths

4. Exit and restart `claude`. The plugin model takes over.

Your specs, config, overrides, and toolbox tools are preserved. The migration only removes submodule-era artifacts and adds plugin enablement.

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

`.purlin/PURLIN_OVERRIDES.md` contains project-specific rules organized by mode. Each section is only writable by its corresponding mode. Use `purlin:override-edit` inside a session for guided editing.

### Credentials

Sensitive values (Figma access token, deploy token, Confluence credentials) are stored in the macOS keychain via Claude Code's plugin `userConfig` system. They are never written to plain-text files.

---

## Troubleshooting

**Plugin not loading?** If using `--plugin-dir`, verify the path points to the Purlin repo root (containing `.claude-plugin/plugin.json`). If using marketplace registration, verify both layers:
1. `~/.claude/settings.json` has the `extraKnownMarketplaces` entry for Purlin.
2. `.claude/settings.json` in your project has `enabledPlugins: { "purlin@purlin": true }`.

**Skills not found?** Make sure you're running `claude` from the project root where `.claude/settings.json` exists. The plugin only loads when the project has it enabled.

**MCP tools not available?** Check that `~/.claude/settings.json` includes `"permissions": { "allow": ["mcp__purlin__*"] }`. Without this, you'll be prompted for each MCP tool on first use.

**Stale submodule artifacts?** If you upgraded from v0.8.5 and still see `purlin/`, `pl-run.sh`, or `.claude/commands/pl-*.md`, run `purlin:update` again inside a session to clean them up.

**Agent says "no mode active"?** This is expected. In open mode (no mode set), the agent blocks all file writes. Run `purlin:mode engineer` (or pm/qa) to activate a mode.
