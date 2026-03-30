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
claude plugin marketplace add boomerangdev/purlin
```

### 2. Install in your project

```bash
# Project scope — committed to .claude/settings.json, shared with teammates
claude plugin install purlin@boomerangdev-purlin --scope project

# Or local scope — gitignored, just for you in this repo
claude plugin install purlin@boomerangdev-purlin --scope local
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

## Join an Existing Project

If a teammate installed Purlin with `--scope project`, the repo's `.claude/settings.json` already has the plugin enabled. Just add the marketplace and the plugin auto-loads:

```bash
git clone <repo-url> && cd <project-name>
claude plugin marketplace add boomerangdev/purlin
claude
```

---

## Update Purlin

Inside any agent session:

```
purlin:update                    # Latest release
purlin:update v0.8.7             # Specific version
purlin:update --dry-run          # Preview only
```

This handles all updates including file/format transitions from v0.8.5 (submodule removal, stale artifact cleanup, plugin model switch). Your specs, config, and toolbox are never touched — only plugin internals are updated. Exit and restart `claude` to complete the transition.

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

**YOLO mode is on by default.** The `PermissionRequest` hook auto-approves remaining permission dialogs (MCP tools, Read access, etc.) when `bypass_permissions: true` in `.purlin/config.json`. Disable with `purlin:config yolo off`.

**Marketplace caveats:**
- MCP tools (`purlin_mode`, `purlin_scan`, etc.) may prompt on first use per session — the PermissionRequest hook auto-approves these when YOLO is on.
- Enterprise environments with `allowManagedHooksOnly: true` or `allowManagedMcpServersOnly: true` can silently disable plugin hooks/MCP — Purlin must be whitelisted by the admin.

See [Plugin Permissions](docs/plugin-permissions.md) for the full details.
