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

1. **Agents stay coordinated** -- four specialized roles (PM, PM, Engineer, QA) each know exactly what to do next.
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

The setup script checks for missing tools and tells you how to install them. It creates `features/`, `.purlin/` (overrides and config), agent launchers (`pl-run-*.sh`), and slash commands (`.claude/commands/`).

Start the PM agent:

```bash
./pl-run-pm.sh
```

The PM will ask what you're building. If you have Figma designs, paste the URL when asked. It creates your first spec and tells you what to do next.

The other agents are launched the same way:

```bash
./pl-run.sh   # PM agent
./pl-run.sh     # Engineer agent
./pl-run-qa.sh          # QA agent
```

### Collaborator Setup

When a team member clones your repository, a single command handles everything:

```bash
./pl-init.sh
```

This initializes the submodule if needed, then creates or repairs launchers, commands, and symlinks without touching project-specific config.

### Updating Purlin

Use `/pl-update-purlin` from any agent session. It fetches the latest version, analyzes what changed, preserves your `.purlin/` customizations, and offers merge strategies for conflicts. See the [Installation Guide](docs/installation-guide.md) for details.

If `git pull` advances the Purlin submodule pointer (you'll see `purlin` in `git status` as modified), sync it with:

```bash
git submodule update --init purlin
```

#### Upgrading from v0.8.4 or earlier

Older versions use a different agent model. After updating, switch to the new unified launcher and run the update skill a second time to complete the migration:

1. Run `/pl-update-purlin` from your current agent session to advance the submodule.
2. Exit the session.
3. Start a new session with `./pl-run.sh` (the unified launcher).
4. Run `/pl-update-purlin` again. It detects the pending migration and converts your config, override files, specs, and companions to the new model.

After migration, `./pl-run.sh` is the only launcher you need. The old launchers (`pl-run-architect.sh`, etc.) still work during the transition. When ready, run `/pl-update-purlin --complete-transition` to remove them.

### Configuration

**Startup controls:** Per-agent flags in `.purlin/config.json`. Set `find_work: false` to skip orientation on launch (expert mode). Set `auto_start: true` (with `find_work: true`) to begin executing the work plan immediately without waiting for approval. See the [Agent Configuration Guide](docs/agent-configuration-guide.md) for details.

**Python environment:** Core tools use only the standard library. Optional features (e.g., LLM-based logic drift detection) need: `python3 -m venv .venv && .venv/bin/pip install -r purlin/requirements-optional.txt`

---

## Core Concepts

Purlin is built on a few ideas that show up everywhere in the framework. The [full documentation](docs/index.md) covers each in depth.

*   **Specs drive everything.** The project's state is defined by specification files in `features/`. Anchor nodes set project-wide rules; feature specs describe requirements in plain-language scenarios. If all source code were deleted, the specs must be sufficient to rebuild.
*   **Four roles, strict boundaries.** The PM translates intent into specs, the PM designs requirements and constraints, the Engineer writes code and tests, and QA verifies behavior. Each role can read everything but only writes to its own domain.
*   **Notes live next to specs.** Implementation decisions, gotchas, and visual checklists are stored in companion files alongside the feature spec they belong to -- nothing gets lost in a side channel.
*   **Your rules layer on top.** Purlin's built-in rules live inside the submodule. Your project-specific tweaks go in `.purlin/`. The agents combine both at launch -- you never need to edit framework files.

## The Agents

Each role can read everything but only writes to its own domain. The Purlin submodule is read-only for all roles.

| Domain | PM | PM | Engineer | QA |
|---|---|---|---|---|
| Feature specs (`features/*.md`) | Write | **Owner** | Read | Read |
| Anchor nodes (`arch_*`, `design_*`, `policy_*`) | Read | **Owner** | Read | Read |
| Design artifacts (`features/design/`) | **Owner** | Read | Read | Read |
| Companion files (`*.impl.md`) | Read | Create | **Owner** | Read |
| Override files (`.purlin/*.md`) | Own file | **Owner** | Own file | Own file |
| Project code and config | Read | Read | **Owner** | Read |
| Tests and traceability | Read | Read | **Owner** | Read |
| QA scripts and discoveries | Read | Read | Read | **Owner** |
| Purlin submodule (`purlin/`) | -- | -- | -- | -- |

*   **The PM** -- Translates human intent into feature specs with Figma-derived visual specifications. [PM Agent Guide](docs/pm-agent-guide.md)
*   **The PM** -- Designs specifications, enforces architectural integrity, and manages the release process. [PM Agent Guide](docs/pm-agent-guide.md)
*   **The Engineer** -- Implements code and tests from specifications. Escalates when a spec is infeasible. [Engineer Agent Guide](docs/engineer-agent-guide.md)
*   **The QA Agent** -- Verifies features against specs, records discoveries, and authors regression suites. [QA Agent Guide](docs/qa-agent-guide.md)

For the full command reference, see the [Skill Reference](docs/index.md#skill-reference) in the docs.

---

## Directory Structure

Created by `pl-init.sh` in your project root:

*   `purlin/` -- The Purlin submodule (framework tooling and base rules). Treat as read-only.
*   `.purlin/` -- Your project-specific overrides and config.
*   `features/` -- Your feature specifications.
*   `pl-run.sh` / `pl-run.sh` / `pl-run-qa.sh` / `pl-run-pm.sh` -- Agent launcher scripts.
*   `pl-init.sh` -- Collaborator setup shim. Commit this.
