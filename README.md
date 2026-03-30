<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

## Current Release: v0.8.6 &mdash; [RELEASE NOTES](RELEASE_NOTES.md)

**Spec-driven development for Claude Code.** One agent, three modes (PM, Engineer, QA). You describe what to build — the agent writes specs, implements code, and verifies the result.

**[Full Documentation](docs/index.md)** | **[Release Notes](RELEASE_NOTES.md)** | **[What's New in v0.8.6](docs/whats-new-0.8.6.md)**

---

## Install

**Prerequisites:** git, Python 3.8+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.1.81+

### 1. Clone Purlin

```bash
git clone git@bitbucket.org:boomerangdev/purlin.git
```

### 2. Create a project and launch with the plugin

```bash
mkdir my-app && cd my-app && git init
claude --plugin-dir /path/to/purlin
```

### 3. Initialize inside the session

```
purlin:init
```

This scaffolds `.claude/`, `.purlin/`, and `features/`. Commit the result and start working:

```
git add -A && git commit -m "init purlin"
```

Then tell the agent what you want:

> "spec a login feature, then build and verify it"

The agent switches modes automatically. You can also use `purlin:spec`, `purlin:build`, `purlin:verify` directly. Run `purlin:help` for the full command list.

### Every subsequent session

```bash
claude --plugin-dir /path/to/purlin
```

Or skip the flag entirely — see [Persistent Setup](#persistent-setup) below.

---

## Persistent Setup

Register the plugin source once so you never need `--plugin-dir` again.

Add to `~/.claude/settings.json`:

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

Now just run `claude` in any Purlin-enabled project. The `enabledPlugins` in `.claude/settings.json` tells Claude Code to load it.

---

## Join an Existing Project

If a teammate already set up Purlin in a repo:

```bash
git clone <repo-url> && cd <project-name>
claude --plugin-dir /path/to/purlin
```

That's it. The project's `.claude/settings.json` already has the plugin enabled. You just need Purlin available to Claude Code (via `--plugin-dir` or the [persistent setup](#persistent-setup)).

---

## Upgrade from v0.8.5

Inside any agent session:

```
purlin:update
```

This detects the submodule, removes it, cleans stale artifacts, and switches to the plugin model. Exit and restart `claude` to complete the transition.

See [What's New in v0.8.6](docs/whats-new-0.8.6.md) for details.

---

## Update Purlin

Inside any session:

```
purlin:update                    # Latest release
purlin:update v0.8.7             # Specific version
purlin:update --dry-run          # Preview only
```

Your specs, config, overrides, and toolbox are never touched. Only plugin internals (skills, hooks, scripts) are updated.

---

## How It Works

**Specs are the source of truth.** Every feature starts as a spec in `features/`. The agent reads specs to know what to build, what to test, and what done looks like. If implementation reveals something the spec missed, the spec gets updated — not just the code.

**Three modes, strict boundaries.** PM writes specs. Engineer writes code. QA verifies. Each mode can read everything but only writes to its own domain. Write boundaries are enforced mechanically — violations are blocked before they happen.

**You talk, the agent routes.** Describe what you want in plain language. The agent picks the right mode and runs the workflow. Or use explicit commands when you want control.

For deeper coverage, see the [Documentation](docs/index.md):

- [PM Mode Guide](docs/pm-agent-guide.md) — Specs from ideas, Figma designs, or live pages
- [Engineer Mode Guide](docs/engineer-agent-guide.md) — Build, test, delivery plans
- [QA Mode Guide](docs/qa-agent-guide.md) — Verify, regress, smoke test
- [Installation Guide](docs/installation-guide.md) — Configuration, credentials, troubleshooting
- [Invariants Guide](docs/invariants-guide.md) — Import and enforce external standards
