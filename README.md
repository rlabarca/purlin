<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

## Current Release: v0.8.5 &mdash; [RELEASE NOTES](RELEASE_NOTES.md)

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

Then create your project. Copy and paste this block into your terminal:

```bash
mkdir my-app && cd my-app
git init
git submodule add git@bitbucket.org:boomerangdev/purlin.git purlin
./purlin/pl-init.sh
git add -A && git commit -m "init purlin"
```

The init script checks for missing tools and tells you how to install them. It creates `features/`, `.purlin/` (config and overrides), `pl-run.sh` (the agent launcher), and slash commands (`.claude/commands/`).

Start the agent:

```bash
./pl-run.sh
```

On first launch, the agent enters PM mode and asks what you're building. If you have Figma designs, paste the URL when asked. It creates your first spec and tells you what to do next.

Switch modes inside the session:

```
/pl-mode pm        # write specs, design features
/pl-mode engineer  # implement code, run tests
/pl-mode qa        # verify features, record discoveries
```

### Collaborator Setup

When a team member clones your repository, a single command handles everything:

```bash
git clone <repo-url>
cd <project-name>
./pl-init.sh
```

This initializes the submodule if needed, then refreshes commands and config without touching project-specific overrides.

### Updating Purlin

From inside an agent session, run:

```
/pl-update-purlin
```

This fetches the latest release tag, advances the submodule, refreshes commands and config, and resolves any conflicts with your customizations. Use `--dry-run` to preview changes first, or pass a specific version like `/pl-update-purlin v0.8.6`. See the [Installation Guide](docs/installation-guide.md) for manual update steps.

#### Upgrading from v0.8.4 or earlier

v0.8.4 and earlier used separate agents per role (`pl-run-architect.sh`, `pl-run-builder.sh`, etc.). v0.8.5 uses a single unified agent (`pl-run.sh`) with three operating modes.

The old `/pl-update-purlin` skill predates the migration module, so the upgrade takes two passes:

1. **From your current agent session** (any old launcher), run `/pl-update-purlin`. This advances the submodule and installs the new skill files.
2. **Exit the session.**
3. **Start a new session with `./pl-run.sh`** — the unified launcher that init created during step 1.
4. **Run `/pl-update-purlin` again.** The new skill detects the pending migration and runs it automatically:
   - Creates the unified agent config (cloned from your existing settings)
   - Consolidates your override files into one `PURLIN_OVERRIDES.md`
   - Renames role references in your feature specs (Architect → PM, Builder → Engineer)
   - Adds Active Deviations tables to companion files
   - Deletes old launchers (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`)

After step 4, `./pl-run.sh` is the only launcher.

### Configuration

**Startup controls:** Set `find_work: false` in `.purlin/config.local.json` to skip work discovery on launch. Set `auto_start: true` (with `find_work: true`) to begin executing immediately without waiting for approval. See the [Installation Guide](docs/installation-guide.md) for details.

**Python environment:** Core tools use only the standard library. Optional features (e.g., LLM-based logic drift detection) need: `python3 -m venv .venv && .venv/bin/pip install -r purlin/requirements-optional.txt`

---

## Core Concepts

Purlin is built on a few ideas that show up everywhere in the framework. The [full documentation](docs/index.md) covers each in depth.

*   **Specs drive everything.** The project's state lives in specification files in `features/`. Anchor nodes set project-wide rules; feature specs describe requirements as plain-language scenarios. If all source code were deleted, the specs must be enough to rebuild.
*   **Three modes, strict boundaries.** PM mode translates intent into specs, Engineer mode writes code and tests, and QA mode verifies behavior. Each mode can read everything but only writes to its own domain.
*   **Knowledge lives next to specs.** Implementation decisions, gotchas, and visual checklists are stored in companion files alongside the feature spec they belong to — nothing gets lost in a side channel.
*   **Your rules layer on top.** Purlin's built-in rules live inside the submodule. Your project-specific tweaks go in `.purlin/PURLIN_OVERRIDES.md`. The agent combines both at launch — you never need to edit framework files.

## The Agent Modes

One agent, three modes. Each mode can read everything but only writes to its own domain. The Purlin submodule is read-only in all modes.

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

For the full command reference, run `/pl-help` inside a session.

---

## Directory Structure

Created by `pl-init.sh` in your project root:

*   `purlin/` — The Purlin submodule (framework tooling and base rules). Treat as read-only.
*   `.purlin/` — Your project-specific overrides and config.
*   `features/` — Your feature specifications.
*   `pl-run.sh` — The agent launcher. Start all sessions here.
*   `pl-init.sh` — Collaborator setup shim. Commit this.
