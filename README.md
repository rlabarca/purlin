<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

## Current Release: v0.8.6 &mdash; [RELEASE NOTES](RELEASE_NOTES.md)

**Spec-driven development for Claude Code.** One agent, three modes (PM, Engineer, QA). You describe what to build — the agent writes specs, implements code, and verifies the result.

**[Full Documentation](docs/index.md)** | **[Release Notes](RELEASE_NOTES.md)** | **[What's New in v0.8.6](docs/whats-new-0.8.6.md)**

---

## Install

**Prerequisites:** git, Python 3.8+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 1.0.33+

### 1. Add the Purlin marketplace (one-time)

```bash
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git
```

### 2. Install in your project

```bash
# Project scope — committed to .claude/settings.json, shared with teammates
claude plugin install purlin@purlin --scope project

# Or local scope — gitignored, just for you in this repo
claude plugin install purlin@purlin --scope local
```

### 3. Initialize (first time only)

```
purlin:init
```

This scaffolds `.purlin/` and `features/`. Commit the result and start working.

### First steps

Once Purlin is loaded, tell the agent what you want:

> "spec a login feature, then build and verify it"

The agent switches modes automatically. You can also use `purlin:spec`, `purlin:build`, `purlin:verify` directly. Run `purlin:help` for the full command list.

---

## Update Purlin

> **Do NOT run `purlin:init` on existing projects.** Init is only for brand new projects. For upgrades (including from v0.8.5 submodule), use `purlin:update` — it handles submodule removal, config migration, file format transitions, and stale artifact cleanup automatically.

**1. Update the plugin code** (pulls latest skills, hooks, scripts from the repo):

```bash
claude plugin update purlin@purlin
```

**2. Run project migration** inside a session:

```
purlin:update                    # Migrate project to current version
purlin:update --dry-run          # Preview the migration plan
```

Your specs, features, and toolbox are never touched — only plugin internals and project config are updated.

---

## Join an Existing Project

If a teammate already set up Purlin in a repo, add the marketplace, install, and run the project migration:

```bash
git clone <repo-url> && cd <project-name>
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git
claude plugin install purlin@purlin --scope local
claude
```

Inside the session:

```
purlin:update
```

---

## Remove Purlin

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
- [Plugin Permissions](docs/plugin-permissions.md) — How Purlin handles permissions, marketplace vs local

---

## Plugin Permission Model

Purlin uses **hook-based permission management** instead of `bypassPermissions`. This works with both `--plugin-dir` and marketplace installs.

**How it works:** Two `PreToolUse` hooks intercept every Write/Edit and Bash call. The mode guard classifies the target file against the active mode's write-access list. Authorized writes return `permissionDecision: "allow"` (auto-approved, no prompt). Unauthorized writes are blocked with `exit 2` (tool call rejected).

**YOLO mode is on by default.** The `PermissionRequest` hook auto-approves most permission dialogs (MCP tools, Read access, etc.) when `bypass_permissions: true` in `.purlin/config.json`. User-facing decisions (plan approval, migration confirmations, remote triggers) always prompt regardless of YOLO. Disable with `purlin:config yolo off`.

**Marketplace caveats:**
- MCP tools (`purlin_mode`, `purlin_scan`, etc.) may prompt on first use per session — the PermissionRequest hook auto-approves these when YOLO is on.
- Enterprise environments with `allowManagedHooksOnly: true` or `allowManagedMcpServersOnly: true` can silently disable plugin hooks/MCP — Purlin must be whitelisted by the admin.

See [Plugin Permissions](docs/plugin-permissions.md) for the full details.
