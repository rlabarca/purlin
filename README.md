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

You describe what you want in plain language and the agent switches modes as the work demands. Each mode can read everything but only writes to its own domain, so specs, code, and test results never get tangled.

## Quick Start

**Prerequisites:** git, Python 3.8+, and [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.1.81+.

### New User

Clone Purlin and load it with `--plugin-dir`:

```bash
git clone git@bitbucket.org:boomerangdev/purlin.git
mkdir my-app && cd my-app && git init
claude --plugin-dir ../purlin
```

Inside the session, run `purlin:init` to scaffold the project. Then just tell the agent what you want:

> "spec a login feature, then build and verify it"

The agent switches modes automatically — PM to write the spec, Engineer to build, QA to verify. You can also use explicit commands like `purlin:spec`, `purlin:build`, `purlin:verify` when you want precision. Run `purlin:help` for the full list.

Every session, pass `--plugin-dir` to load the plugin. Or register it once for automatic loading — see [Persistent Setup](#persistent-setup-optional) below.

### Joining a Team Project

If someone already set up Purlin in a repo you're cloning:

```bash
git clone <repo-url> && cd <project-name>
claude --plugin-dir /path/to/purlin
```

The project's `.claude/settings.json` already has `enabledPlugins` configured. You just need Purlin available to Claude Code (via `--plugin-dir` or the persistent setup).

### Upgrading from v0.8.5

Inside any agent session:

```
purlin:update
```

This detects the submodule, removes it, cleans stale artifacts (`pl-run.sh`, `.claude/commands/pl-*.md`), and declares the plugin. Exit and restart `claude` to complete the transition. See [What's New in v0.8.6](docs/whats-new-0.8.6.md).

### Persistent Setup (Optional)

To avoid passing `--plugin-dir` every session, register the plugin source in `~/.claude/settings.json`:

```json
{
  "permissions": { "allow": ["mcp__purlin__*"] },
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

After this, just run `claude` in any project with `enabledPlugins` configured — no flags needed.

### Session Recovery

You do **not** need to run any startup command. The `SessionStart` hook recovers context automatically. Use `purlin:resume` only when recovering after `/clear` or context compaction, or to resolve a failed worktree merge with `purlin:resume merge-recovery`.

---

## Core Concepts

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

*   **PM mode** — Translates ideas and Figma designs into feature specs with requirements and scenarios. [PM Mode Guide](docs/pm-agent-guide.md)
*   **Engineer mode** — Reads specs, writes code and tests, records implementation decisions. [Engineer Mode Guide](docs/engineer-agent-guide.md)
*   **QA mode** — Verifies features against specs, records findings, builds regression suites. [QA Mode Guide](docs/qa-agent-guide.md)

For the full command reference, run `purlin:help` inside a session. See the [Installation Guide](docs/installation-guide.md) for configuration, updating, and troubleshooting.

---

## Directory Structure

Created by `purlin:init` in your project root:

*   `.claude/settings.json` — Plugin enablement (committed to git).
*   `.purlin/` — Your project-specific overrides, config, and toolbox.
*   `features/` — Your feature specifications.
*   `CLAUDE.md` — References the Purlin plugin for context recovery.
