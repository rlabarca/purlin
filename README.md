# Purlin

![Purlin Logo](assets/purlin-logo.svg)

## Current Release: v0.8.4 &mdash; [RELEASE NOTES](RELEASE_NOTES.md)

**Collaborative Design-Driven Agentic Development Framework**

**[Documentation](docs/index.md)** | **[Release Notes](RELEASE_NOTES.md)**

[![Watch the video](https://img.youtube.com/vi/ob7_RzriVdI/maxresdefault.jpg)](https://youtu.be/ob7_RzriVdI)

**How to work with the agents:** [English](https://youtu.be/sLk6YqoVW4c) | [Portugues Brasileiro](https://youtu.be/hxARP-1TMk0)

## Overview

Purlin helps AI agents build software together using a shared set of specs. The specs stay in sync with the code -- when code teaches us something new, the specs get updated to match.

The framework is built on four goals:

1. **Agents stay coordinated** -- one agent with three modes (PM, Engineer, QA) always knows what to do next.
2. **Specs are the source of truth** -- if the code disappeared tomorrow, any agent could rebuild it from the specs alone.
3. **People steer, agents execute** -- you set the direction; agents handle the back-and-forth without meetings.
4. **Code stays correct** -- specs and code are always in sync, so bugs from "stale requirements" don't happen.

## Quick Start

You need **git** and **[Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.1.81+** installed. On macOS:

```bash
brew install git node           # node is optional, needed for web testing
npm install -g @anthropic-ai/claude-code
```

Already have Claude Code? Run `claude update` to make sure you're on the latest version.

Then create your project. Copy and paste this block into your terminal:

```bash
mkdir my-app && cd my-app
git init
git submodule add git@bitbucket.org:boomerangdev/purlin.git purlin
./purlin/pl-init.sh
git add -A && git commit -m "init purlin"
```

The setup script checks for missing tools and tells you how to install them. It creates `features/`, `.purlin/` (overrides and config), `pl-run.sh` (the agent launcher), and slash commands (`.claude/commands/`).

Start the Purlin agent:

```bash
./pl-run.sh
```

On first launch, the agent asks what model and effort level to use. Then it enters PM mode and asks what you're building. If you have Figma designs, paste the URL when asked. It creates your first spec and tells you what to do next.

Switch modes inside the session with `/pl-mode`:

```
/pl-mode pm        # write specs, design features
/pl-mode engineer  # implement code, run tests
/pl-mode qa        # verify features, record discoveries
```

### Collaborator Setup

When a team member clones your repository, a single command handles everything:

```bash
./pl-init.sh
```

This initializes the submodule if needed, then creates or repairs the launcher, commands, and config without touching project-specific overrides.

### Updating Purlin

From inside an agent session, run:

```
/pl-update-purlin
```

This fetches the latest version, advances the submodule, refreshes commands and config, and offers merge strategies for any conflicts with your customizations. Use `--dry-run` to preview changes first. See the [Installation Guide](docs/installation-guide.md) for details.

If `git pull` advances the Purlin submodule pointer (you'll see `purlin` in `git status` as modified), sync it with:

```bash
git submodule update --init purlin
```

#### Upgrading from v0.8.4 or earlier

v0.8.4 and earlier used separate agents per role (`pl-run-architect.sh`, `pl-run-builder.sh`, etc.). The current version uses a single unified agent (`pl-run.sh`) with three operating modes.

The old `/pl-update-purlin` skill predates the migration module, so the upgrade takes two passes:

1. **From your current agent session** (any old launcher), run `/pl-update-purlin`. This advances the submodule and installs the new skill files.
2. **Exit the session.**
3. **Start a new session with `./pl-run.sh`** — the unified launcher that `init.sh` created during step 1.
4. **Run `/pl-update-purlin` again.** The new skill detects the pending migration and runs it automatically:
   - Creates `agents.purlin` config (cloned from your `agents.builder` settings)
   - Consolidates your 5 override files into one `PURLIN_OVERRIDES.md`
   - Renames role references in your feature specs (Architect → PM, Builder → Engineer)
   - Adds Active Deviations tables to companion files
   - **Deletes old launchers** (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`)

After step 4, `./pl-run.sh` is the only launcher. There is no transition period.

### Configuration

**Startup controls:** Per-agent flags in `.purlin/config.local.json`. Set `find_work: false` to skip orientation on launch (expert mode). Set `auto_start: true` (with `find_work: true`) to begin executing the work plan immediately without waiting for approval. See the [Agent Configuration Guide](docs/agent-configuration-guide.md) for details.

**Python environment:** Core tools use only the standard library. Optional features (e.g., LLM-based logic drift detection) need: `python3 -m venv .venv && .venv/bin/pip install -r purlin/requirements-optional.txt`

---

## Core Concepts

Purlin is built on a few ideas that show up everywhere in the framework. The [full documentation](docs/index.md) covers each in depth.

*   **Specs drive everything.** The project's state is defined by specification files in `features/`. Anchor nodes set project-wide rules; feature specs describe requirements in plain-language scenarios. If all source code were deleted, the specs must be sufficient to rebuild.
*   **Three modes, strict boundaries.** PM mode translates intent into specs, Engineer mode writes code and tests, and QA mode verifies behavior. Each mode can read everything but only writes to its own domain.
*   **Notes live next to specs.** Implementation decisions, gotchas, and visual checklists are stored in companion files alongside the feature spec they belong to -- nothing gets lost in a side channel.
*   **Your rules layer on top.** Purlin's built-in rules live inside the submodule. Your project-specific tweaks go in `.purlin/`. The agent combines both at launch -- you never need to edit framework files.

## The Agent Modes

The Purlin agent operates in three modes. Each mode can read everything but only writes to its own domain. The Purlin submodule is read-only in all modes.

| Domain | PM | Engineer | QA |
|---|---|---|---|
| Feature specs (`features/*.md`) | **Owner** | Read | Read |
| Anchor nodes (`design_*`, `policy_*`) | **Owner** | Read | Read |
| Technical anchors (`arch_*`) | Read | **Owner** | Read |
| Companion files (`*.impl.md`) | Read | **Owner** | Read |
| Override files (`.purlin/*.md`) | Own section | Own section | Own section |
| Project code and config | Read | **Owner** | Read |
| Tests and traceability | Read | **Owner** | Read |
| QA scripts and discoveries | Read | Read | **Owner** |
| Purlin submodule (`purlin/`) | -- | -- | -- |

*   **PM mode** -- Translates human intent into feature specs with Figma-derived visual specifications. Designs requirements, manages anchors. [PM Agent Guide](docs/pm-agent-guide.md)
*   **Engineer mode** -- Implements code and tests from specifications. Escalates when a spec is infeasible. [Engineer Agent Guide](docs/engineer-agent-guide.md)
*   **QA mode** -- Verifies features against specs, records discoveries, and authors regression suites. [QA Agent Guide](docs/qa-agent-guide.md)

For the full command reference, see the [Skill Reference](docs/index.md#skill-reference) in the docs.

---

## Directory Structure

Created by `pl-init.sh` in your project root:

*   `purlin/` -- The Purlin submodule (framework tooling and base rules). Treat as read-only.
*   `.purlin/` -- Your project-specific overrides and config.
*   `features/` -- Your feature specifications.
*   `pl-run.sh` -- The agent launcher. Start all sessions here.
*   `pl-init.sh` -- Collaborator setup shim. Commit this.
