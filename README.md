<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

## Current Release: v0.8.6 &mdash; [RELEASE NOTES](RELEASE_NOTES.md)

**Spec-First Collaborative Agentic Development**

**[Documentation](docs/index.md)** | **[Release Notes](RELEASE_NOTES.md)**

## Overview

Purlin helps you build software with an AI agent that collaborates through shared specifications. You describe what to build. The agent writes the spec, implements the code, and verifies the result — all driven by a single set of specs that stay in sync with the code.

The core idea: **specs are the source of truth.** If every line of code disappeared, the agent could rebuild the project from specs alone. When implementation reveals something the spec didn't anticipate, the spec gets updated — not just the code.

One agent operates in three modes:

- **PM mode** — translates your ideas (and optionally Figma designs) into detailed feature specs.
- **Engineer mode** — reads specs and writes code, tests, and documentation.
- **QA mode** — verifies that the code matches the specs and automates regression testing.

You switch between modes as the work demands. Each mode can read everything but only writes to its own domain, so specs, code, and test results never get tangled.

## Quick Start

You need **git** and **[Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.1.81+** installed. On macOS:

```bash
brew install git node           # node is optional, needed for web testing
npm install -g @anthropic-ai/claude-code
```

Already have Claude Code? Run `claude update` to make sure you're on the latest version.

### Option A: Load from a Local Clone (Simplest)

Clone the Purlin repo and point Claude Code at it with `--plugin-dir`. No marketplace registration needed.

```bash
git clone https://github.com/rlabarca/purlin.git

mkdir my-app && cd my-app
git init
claude --plugin-dir ../purlin
```

Inside the Claude Code session, initialize your project:

```
purlin:init
```

This creates `features/`, `.purlin/` (config and overrides), and enables the plugin for this project via `.claude/settings.json`.

Every time you start a session in this project, use `--plugin-dir` to load the plugin:

```bash
claude --plugin-dir ../purlin
```

### Option B: Register via Marketplace (Persistent)

Register the plugin source once in your user-level settings. After that, `claude` loads Purlin automatically in any project that has it enabled — no `--plugin-dir` flag needed.

Add to `~/.claude/settings.json`:

```json
{
  "permissions": { "allow": ["mcp__purlin__*"] },
  "extraKnownMarketplaces": {
    "purlin": {
      "source": "settings",
      "plugins": [{
        "name": "purlin",
        "source": { "source": "github", "repo": "rlabarca/purlin" }
      }]
    }
  }
}
```

Then create your project and initialize:

```bash
mkdir my-app && cd my-app
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

### Start Working

Once the plugin is loaded (via either option), the agent enters PM mode on first launch in a new project and asks what you're building. If you have Figma designs, paste the URL when asked. It creates your first spec and tells you what to do next.

Switch modes inside the session:

```
purlin:mode pm        # write specs, design features
purlin:mode engineer  # implement code, run tests
purlin:mode qa        # verify features, record discoveries
```

Or invoke any mode-specific skill directly — it activates the mode automatically:

```
purlin:spec login     # activates PM mode, starts a spec
purlin:build login    # activates Engineer mode, starts building
purlin:verify login   # activates QA mode, starts verification
```

### Collaborator Setup

When a team member clones your repository, the plugin activates automatically (if they've registered the marketplace source):

```bash
git clone <repo-url>
cd <project-name>
claude
```

The committed `.claude/settings.json` enables the plugin. The team member needs to have either registered the marketplace source (Option B) or use `--plugin-dir` to point at a local clone of Purlin. If `.purlin/` doesn't exist yet, run `purlin:init` inside the session.

### Updating Purlin

From inside an agent session:

```
purlin:update
```

This fetches the latest release tag, refreshes skills, hooks, and the MCP server, and resolves any conflicts with your customizations. Use `--dry-run` to preview changes first, or pass a specific version like `purlin:update v0.8.7`. See the [Installation Guide](docs/installation-guide.md) for details.

#### Upgrading from v0.8.5 (Submodule to Plugin)

v0.8.5 distributed Purlin as a git submodule with a launcher script (`pl-run.sh`). v0.8.6 replaces this with the Claude Code plugin system.

Run `purlin:update` inside any agent session. The update skill detects the submodule, removes it, cleans stale artifacts, and declares the plugin. Exit and restart `claude` to complete the transition. See [What's New in v0.8.6](docs/whats-new-0.8.6.md) for the full changelog.

### How the Plugin Layers Work

Purlin uses two configuration layers that combine when you run `claude`:

| Layer | File | What It Does |
|---|---|---|
| **Global** (user) | `~/.claude/settings.json` | Registers the plugin source. Makes Purlin *available*. |
| **Project** | `.claude/settings.json` | Enables the plugin. Activates Purlin in *this project*. |

When you run `claude` in a project with the plugin enabled, the Purlin agent activates, hooks register (mode guard, session recovery, auto-checkpoint), and the MCP server starts. In any other directory, you get standard Claude Code.

### Configuration

**Startup controls:** Set `find_work: false` in `.purlin/config.local.json` to skip work discovery on launch. Set `auto_start: true` (with `find_work: true`) to begin executing immediately without waiting for approval. See the [Installation Guide](docs/installation-guide.md) for details.

**Model override:** The plugin sets a default model. Override per-session with `claude --model claude-sonnet-4-6`.

**Python environment:** The MCP server and core tools use only the Python standard library. No venv or pip install needed.

---

## Core Concepts

Purlin is built on a few ideas that show up everywhere in the framework. The [full documentation](docs/index.md) covers each in depth.

*   **Specs drive everything.** The project's state lives in specification files in `features/`. Anchor nodes set project-wide rules; feature specs describe requirements as plain-language scenarios. If all source code were deleted, the specs must be enough to rebuild.
*   **Three modes, strict boundaries.** PM mode translates intent into specs, Engineer mode writes code and tests, and QA mode verifies behavior. Each mode can read everything but only writes to its own domain.
*   **Knowledge lives next to specs.** Implementation decisions, gotchas, and visual checklists are stored in companion files alongside the feature spec they belong to — nothing gets lost in a side channel.
*   **Your rules layer on top.** Purlin's built-in rules live inside the plugin. Your project-specific tweaks go in `.purlin/PURLIN_OVERRIDES.md`. The agent combines both at launch — you never need to edit framework files.

## The Agent Modes

One agent, three modes. Each mode can read everything but only writes to its own domain. Write boundaries are enforced mechanically by a `PreToolUse` hook.

| Domain | PM | Engineer | QA |
|---|---|---|---|
| Feature specs (`features/*.md`) | **Owner** | Read | Read |
| Anchor nodes (`design_*`, `policy_*`) | **Owner** | Read | Read |
| Technical anchors (`arch_*`) | Read | **Owner** | Read |
| Companion files (`*.impl.md`) | Read | **Owner** | Read |
| Override file (`.purlin/PURLIN_OVERRIDES.md`) | Own section | Own section | Own section |
| Project code and config | Read | **Owner** | Read |
| Tests and traceability | Read | **Owner** | Read |
| QA scripts and discoveries | Read | Read | **Owner** |
| Purlin submodule (`purlin/`) | — | — | — |

*   **PM mode** — Translates ideas and Figma designs into feature specs with requirements and scenarios. [PM Mode Guide](docs/pm-agent-guide.md)
*   **Engineer mode** — Reads specs, writes code and tests, records implementation decisions. [Engineer Mode Guide](docs/engineer-agent-guide.md)
*   **QA mode** — Verifies features against specs, records findings, builds regression suites. [QA Mode Guide](docs/qa-agent-guide.md)

For the full command reference, run `purlin:help` inside a session.

---

## Directory Structure

Created by `purlin:init` in your project root:

*   `.claude/settings.json` — Plugin enablement (committed to git).
*   `.purlin/` — Your project-specific overrides, config, and toolbox.
*   `features/` — Your feature specifications.
*   `CLAUDE.md` — References the Purlin plugin for context recovery.
