# Installation Guide

## Overview

Purlin is added to your project as a git submodule. A single init script sets up everything: config files, the agent launcher, slash commands, and git hooks. When a new version is released, you update the submodule and the agent refreshes the rest.

---

## New Project Setup

### Prerequisites

- Git (any recent version)
- Python 3.8+ (used by tooling scripts)
- Claude Code CLI (`claude`) **2.1.81 or later**, installed and authenticated
- Node.js (optional, for web testing via Playwright)

### Steps

**1. Create your project and initialize git:**

```bash
mkdir my-project && cd my-project
git init
```

If you already have a git repository, skip this step.

**2. Add Purlin as a submodule:**

```bash
git submodule add git@bitbucket.org:boomerangdev/purlin.git purlin
```

**3. Run the init script:**

```bash
./purlin/pl-init.sh
```

This detects a first-time setup and runs **Full Init Mode**:

- Copies config templates to `.purlin/` (config, overrides).
- Sets `tools_root` to `"purlin/tools"` in your config.
- Generates the agent launcher (`pl-run.sh`).
- Distributes slash commands to `.claude/commands/`.
- Creates the `features/` directory.
- Updates `.gitignore` with Purlin-specific patterns.
- Installs Claude Code hooks and MCP servers.

**4. Commit the scaffold:**

```bash
git add -A && git commit -m "init purlin"
```

**5. Start the agent:**

```bash
./pl-run.sh
```

On first launch, the agent enters PM mode, asks what you're building, and creates your first spec.

### What Gets Created

```
my-project/
├── .purlin/
│   ├── config.json              # Main config (models, agent settings)
│   ├── PURLIN_OVERRIDES.md      # Project-specific rules (all modes)
│   ├── .upstream_sha            # Pinned Purlin version SHA
│   ├── cache/                   # Auto-generated (not committed)
│   └── runtime/                 # Transient state (not committed)
├── .claude/
│   ├── commands/pl-*.md         # Slash commands
│   └── agents/*.md              # Agent definitions
├── features/                    # Feature specs go here
├── purlin/                      # The submodule (do not edit)
├── pl-init.sh                   # Init shim (committed)
└── pl-run.sh                    # Agent launcher
```

---

## Joining an Existing Project

If you're cloning a project that already uses Purlin:

```bash
git clone <repo-url>
cd <project-name>
./pl-init.sh
```

The init shim handles everything:

1. Initializes the submodule if needed.
2. Detects that `.purlin/` already exists.
3. Runs in **Refresh Mode** — updates commands and the launcher without touching config or overrides.

---

## Updating Purlin

### Agent-Assisted Update (Recommended)

Inside any agent session:

```
/pl-update-purlin
```

This performs:

1. Fetches the latest version and shows what changed.
2. Scans for conflicts with your local customizations.
3. Advances the submodule.
4. Refreshes commands and config.
5. Resolves conflicts with three-way diffs.
6. Cleans up stale artifacts from previous versions.

Use `--dry-run` to preview changes without modifying anything.

### Manual Update

If you prefer to update without the agent:

```bash
cd purlin
git fetch origin
git checkout <tag-or-sha>    # e.g., git checkout v0.8.5
cd ..
./pl-init.sh
git add purlin .purlin pl-init.sh .claude/commands .claude/agents
git commit -m "update purlin to <version>"
```

Refresh Mode updates commands and the launcher. It never touches:

- `.purlin/config.json` or `config.local.json`
- `.purlin/PURLIN_OVERRIDES.md`
- The `features/` directory

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

`.purlin/PURLIN_OVERRIDES.md` contains project-specific rules organized by mode. Each section is only writable by its corresponding mode. Use `/pl-override-edit` inside a session for guided editing.

### Key Config: `tools_root`

The `tools_root` value in `.purlin/config.json` tells the agent where Purlin's tools live. For a submodule setup, this is `"purlin/tools"`. The init script sets this automatically.

---

## Troubleshooting

**`pl-init.sh` says "submodule not initialized"** — Run `git submodule update --init purlin` manually, then re-run `./pl-init.sh`.

**Slash commands are outdated after update** — Re-run `./pl-init.sh`. It overwrites commands older than the source versions. If you've locally modified a command, init skips it — delete the local copy to force a refresh.

**Agent says "tools_root not found"** — Verify `.purlin/config.json` exists and contains a `"tools_root"` key. If the file is missing, re-run `./pl-init.sh`.
