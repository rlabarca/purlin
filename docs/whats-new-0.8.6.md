# What's New in v0.8.6

Upgrading from v0.8.5? Here's everything that changed.

---

## The Big Changes

### Purlin Is Now a Claude Code Plugin

Purlin is no longer distributed as a git submodule. It's now a **Claude Code plugin** that you install once and enable per-project. This eliminates the submodule onboarding friction (multi-step init, symlink management, path resolution) and replaces the 504-line `pl-run.sh` launcher with skills that run inside your Claude Code session.

| v0.8.5 (Submodule) | v0.8.6 (Plugin) |
|---|---|
| `git submodule add ... purlin` | One-time: register plugin marketplace |
| `pl-init.sh` (808-line script) | `purlin:init` (skill, runs inside session) |
| `./pl-run.sh --mode engineer` | `claude` then `purlin:build` |
| `cd purlin && git pull && cd ..` | `purlin:update` |
| `purlin/tools/cdd/scan.sh` | MCP server (persistent, zero startup overhead) |

**What this means for you:**

- **No submodule in your repo.** The `purlin/` directory is gone. Plugin code lives in Claude Code's plugin cache, completely separate from your project files.
- **Just run `claude`.** The plugin activates automatically when you open a session in a Purlin-enabled project. No special launcher needed.
- **Context recovery prompting.** A `SessionStart` hook reminds the agent to run `purlin:resume` after context clears and compaction events. A `PreCompact` hook auto-saves checkpoints before the context window fills.

### No More Mode Switching

The pm/engineer/qa **mode system is gone**. In v0.8.5, you had to explicitly switch modes (`purlin:mode engineer`) and writes were blocked if you were in the wrong mode. In v0.8.6, PM, Engineer, and QA are **roles** — organizational groupings for skills — not enforced access boundaries.

**What changed:**

- **Write freely.** Everyone can write any classified file type (CODE, SPEC, QA). No role-based restrictions.
- **Sync tracking replaces mode enforcement.** A two-layer system (session + cross-session ledger) watches what you change. `purlin:status` shows which features are synced, which have code ahead of specs, and which need attention.
- **Companion debt is advisory.** `purlin:status` surfaces features where code changed but the companion file wasn't updated. It's a warning, not a gate.
- **Only two hard blocks remain:** INVARIANT files (use `purlin:invariant sync`) and UNKNOWN files (add a classification rule to CLAUDE.md).
- **`purlin:mode` is removed.** Just use skills directly: `purlin:build`, `purlin:spec`, `purlin:verify`.

---

## How to Install (New Projects)

Add the marketplace and install per-project:

```bash
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git
cd my-app && git init
claude plugin install purlin@purlin --scope project
claude
```

Inside the session:

```
purlin:init
```

That's it. No submodule, no init script, no symlinks. See the [Installation Guide](installation-guide.md) for full details.

---

## How to Upgrade from v0.8.5

Inside any agent session on your existing project:

```
purlin:update
```

The update skill detects the submodule-to-plugin transition and handles:

1. Removing the `purlin/` submodule and `.gitmodules` entry.
2. Cleaning stale artifacts (`pl-run.sh`, `pl-init.sh`, `.claude/commands/pl-*.md`).
3. Declaring the plugin in `.claude/settings.json`.
4. Migrating config from `purlin/tools/` paths to plugin paths.
5. Migrating mode system artifacts to sync tracking.

After the update completes, exit and restart `claude`. The plugin takes over.

### Post-Upgrade: Figma Invariant Sync

If your project has Figma-sourced design invariants (created by `purlin:invariant add-figma` or migrated from v0.8.5 Figma references), run these after upgrading:

```
purlin:invariant sync --all
purlin:invariant validate
```

The sync populates new invariant sections introduced in v0.8.6:
- **Design Variables** — variable names and types extracted via `get_variable_defs` (used for Token Map auto-seeding and drift detection)
- **Code Connect** — presence indicator for component-to-code mappings (when your Figma org has Code Connect configured)

Invariant Format-Version is bumped from 1.0 to 1.1. Existing 1.0 invariants remain valid — sync upgrades them to 1.1 automatically.

If you don't have Figma MCP set up yet:

```bash
claude mcp add --transport http figma https://mcp.figma.com/mcp
```

Restart the session, run `/mcp` → select Figma → complete OAuth, then run the sync.

---

## Skill Renaming: `/pl-*` to `purlin:*`

All skills have been renamed. The `pl-` prefix is gone, replaced by the `purlin:` plugin namespace.

| v0.8.5 | v0.8.6 |
|---|---|
| `/pl-build` | `purlin:build` |
| `/pl-verify` | `purlin:verify` |
| `/pl-spec` | `purlin:spec` |
| `/pl-mode` | Removed — use skills directly |
| `/pl-status` | `purlin:status` |
| `/pl-resume` | `purlin:resume` |
| `/pl-help` | `purlin:help` |
| `/pl-update-purlin` | `purlin:update` |
| ... (all 36+ skills) | ... |

The skills themselves work the same way. Only the invocation name changed.

### Removed Skills

| Old Skill | Replacement |
|---|---|
| `purlin:mode` | Removed. No mode switching needed. Use skills directly (`purlin:build`, `purlin:spec`, `purlin:verify`). |
| `purlin:start` | Removed. The plugin activates automatically when you run `claude`. Use `purlin:resume` only for session recovery. |

---

## Running Claude with the Purlin Plugin

The plugin model changes how you start sessions. There is no launcher script. You run `claude` and the plugin activates if the project has it enabled.

### Combining Global Plugin + Local Project

The Purlin plugin is installed **globally** (user-level) but **enabled per-project**. Here's how the layers combine:

1. **User-level** (`~/.claude/settings.json`): Registers the plugin source (marketplace). This makes the plugin *available* to all projects but doesn't activate it.

2. **Project-level** (`.claude/settings.json`, committed to git): Enables the plugin for this specific project:
   ```json
   {
     "enabledPlugins": { "purlin@purlin": true }
   }
   ```

3. **When you run `claude` in a Purlin project:**
   - Claude Code loads the Purlin plugin from its cache.
   - The plugin's `settings.json` activates the Purlin agent (`agents/purlin.md`).
   - Hooks register (write guard, session recovery, auto-checkpoint, sync tracking).
   - The MCP server starts (scan engine, dependency graph, file classification).
   - Your project's `CLAUDE.md` layers on top with project-specific context.

4. **When you run `claude` outside a Purlin project:** Nothing happens. Standard Claude Code with zero Purlin interference.

### Session Startup

```bash
claude                              # Plugin auto-activates, hooks set up terminal identity
```

Inside the session, just tell the agent what you want in plain language:

> "spec a login feature, then build and verify it"

Or use skills directly: `purlin:build`, `purlin:spec`, `purlin:verify`.

### When to Use `purlin:resume`

`purlin:resume` is for **session recovery**, not for starting work. You need it in two situations:

1. **After `/clear` or context compaction** — restores your checkpoint (branch, in-progress work):
   ```
   purlin:resume
   ```

2. **After a worktree merge failure** — resolves pending merge conflicts:
   ```
   purlin:resume merge-recovery
   ```

`purlin:resume` also accepts flags for convenience when recovering:

```
purlin:resume --build               # Recover + start building
purlin:resume --verify my_feature   # Recover + start verifying
purlin:resume --worktree --build    # Recover + isolated worktree + build
```

You do **not** need to run `purlin:resume` at the start of every session. The `SessionStart` hook handles automatic context recovery.

### Model Selection

The plugin's agent definition sets a default model (`claude-opus-4-6[1m]`). To override per-session:

```bash
claude --model claude-sonnet-4-6    # Start with Sonnet instead
```

Or set up shell aliases:

```bash
alias purlin='claude'
alias purlin-fast='claude --model claude-sonnet-4-6'
```

---

## The MCP Server

The scan engine, dependency graph, file classification, and config are now served by a **persistent MCP server** that starts automatically with the plugin. Previously, each scan invocation spawned a fresh Python process (~100-150ms startup). Now the server runs once and responds instantly.

| MCP Tool | What It Does |
|---|---|
| `purlin_scan` | Full project scan (features, tests, status) |
| `purlin_status` | Work items and sync state |
| `purlin_graph` | Dependency graph with cycle detection |
| `purlin_classify` | File path classification (for write guard) |
| `purlin_sync` | Sync state and ledger operations |
| `purlin_config` | Read or write `.purlin/config.json` |

You don't call these directly. Skills and hooks use them behind the scenes. The write guard hook calls `purlin_classify` on every write to determine if the file is writable.

---

## Hooks

Five hooks provide mechanical enforcement and automatic lifecycle management:

| Hook | Event | What It Does |
|---|---|---|
| **Write Guard** | `PreToolUse` (Write/Edit) | Blocks INVARIANT and UNKNOWN file writes. All classified files (CODE, SPEC, QA) are auto-approved. |
| **Session Start** | `SessionStart` | Sets terminal identity on launch; prompts `purlin:resume` after clear/compact. Clears stale session state. |
| **Session End** | `SessionEnd` | Merges worktree branches, cleans session state. |
| **Permission Manager** | `PermissionRequest` | Auto-approves most permission prompts when YOLO is enabled (excludes plan approval, user questions, remote triggers). |
| **Sync Tracker** | `FileChanged` | Tracks file writes per session in `sync_state.json`. Powers the sync ledger and `purlin:status` drift detection. |

The write guard is the key permission mechanism. It classifies every file and auto-approves writes to CODE, SPEC, and QA files. INVARIANT files (externally sourced) and UNKNOWN files (unclassified) are blocked with an error message explaining how to proceed.

---

## Directory Structure Changes

### Your project (consumer)

```
my-project/
├── .claude/
│   └── settings.json          # enabledPlugins: { "purlin@purlin": true }
├── .purlin/
│   ├── config.json            # Agent settings (models, auto-start, etc.)
│   ├── config.local.json      # Local overrides (gitignored)
│   ├── sync_ledger.json       # Cross-session sync state (committed)
│   ├── cache/                 # Scan cache, dependency graph (gitignored)
│   ├── runtime/               # PID files, session state (gitignored)
│   └── toolbox/               # Project and community tools
├── features/                  # Feature specifications
├── CLAUDE.md                  # References Purlin plugin
└── (no purlin/ submodule)     # Gone!
```

### The plugin repo (what you're installing)

```
purlin/
├── .claude-plugin/
│   └── plugin.json            # Plugin manifest (name, version, userConfig)
├── settings.json              # { "agent": "purlin" }
├── agents/
│   ├── purlin.md              # Main agent definition
│   ├── engineer-worker.md     # Parallel build sub-agent
│   └── verification-runner.md # Test execution sub-agent
├── skills/                    # 36+ skills (was .claude/commands/)
│   ├── build/SKILL.md
│   ├── verify/SKILL.md
│   └── ...
├── hooks/
│   ├── hooks.json             # Hook event declarations
│   └── scripts/               # Hook handler scripts
├── scripts/                   # Was tools/
│   ├── mcp/                   # MCP server + engine modules
│   ├── toolbox/               # Toolbox management
│   ├── terminal/              # Terminal identity
│   └── worktree/              # Worktree management
├── references/                # Was instructions/references/
└── templates/                 # Config and override templates
```

---

## What Was Removed

| Removed | Why |
|---|---|
| `pl-run.sh` (504 lines) | Replaced by plugin hooks |
| `pl-init.sh` / `tools/init.sh` (808 lines) | Replaced by `purlin:init` skill |
| `purlin/` submodule directory | Plugin lives in Claude Code's cache |
| `.claude/commands/pl-*.md` (36 files) | Moved to `skills/*/SKILL.md` inside the plugin |
| `instructions/PURLIN_BASE.md` | Content moved to `agents/purlin.md` |
| `instructions/references/` | Moved to `references/` at plugin root |
| `tools/` directory | Renamed to `scripts/`, scan engine wrapped in MCP server |
| `purlin:mode` command | Replaced by sync tracking — use skills directly |
| Mode guard hook | Replaced by write guard (classifies files, no role restriction) |
| Companion debt gate | Replaced by advisory sync tracking in `purlin:status` |

---

## Credential Storage

Plugin `userConfig` in `.claude-plugin/plugin.json` declares optional credentials (Figma token, deploy token, Confluence credentials). These are stored securely in the macOS keychain via Claude Code's native credential system, not in plain-text config files.

Configure credentials with `purlin:credentials` or when prompted at plugin enable time.

---

## New: `purlin:config` Skill

Behavior settings that previously required CLI flags on `purlin:resume` or manual JSON editing now have a dedicated skill:

```
purlin:config                       # Show all settings
purlin:config yolo on               # Auto-approve all permission prompts
purlin:config find-work off         # Skip the startup scan
purlin:config auto-start on         # Start working immediately
```

Three settings, each with on/off:

| Setting | What It Controls |
|---------|-----------------|
| **yolo** | Auto-approve most permission prompts (no confirmation dialogs). Remote triggers and plan exits always prompt. |
| **find-work** | Scan for work when starting a session |
| **auto-start** | Begin executing work immediately after scanning |

All writes go to `.purlin/config.local.json` (gitignored), so your preferences stay local. The team's committed `.purlin/config.json` provides defaults for new contributors.

### What Moved Out of Purlin Config

**Model and effort** are no longer Purlin settings. They were removed from `.purlin/config.json` because they're native Claude Code settings:

| Old (v0.8.5) | New |
|---|---|
| `purlin:resume --model claude-sonnet-4-6` | `/model` or `claude --model claude-sonnet-4-6` |
| `purlin:resume --effort high` | `/effort` |
| `agents.purlin.model` in config.json | Not needed — set at Claude Code level |
| `agents.purlin.effort` in config.json | Not needed — set at Claude Code level |
| `agents.purlin.default_mode` in config.json | Removed — modes no longer exist |

See the [Configuration Guide](config-guide.md) for the full reference.

---

## Tips and Tricks

**Just run `claude` and talk.** No launcher, no special startup command. The plugin activates automatically in any Purlin-enabled project. Use explicit skills (`purlin:build`, `purlin:spec`, `purlin:verify`) when you want precision, or describe what you want in plain language.

**Hooks handle the guardrails.** Write classification and checkpoint saves happen automatically. The `PreCompact` hook saves session state before context compaction. On startup, the `SessionStart` hook handles context recovery.

**Sync tracking keeps you honest.** `purlin:status` shows which features have code ahead of specs, which specs changed but code hasn't caught up, and which companion files are stale. It's information, not enforcement — you decide when to address drift.

**Community tools are shareable.** `purlin:toolbox add <git-url>` downloads community tools. `purlin:toolbox push <tool> <git-url>` shares yours. Pull upstream updates with `purlin:toolbox pull`.

**YOLO mode persists.** Run `purlin:config yolo on` and most permission prompts are auto-approved for subsequent sessions. Plan approval, user questions, and remote triggers always prompt regardless — the agent can't approve its own plans. Run `purlin:config yolo off` to turn it off.

**Model and effort are native Claude settings.** Use `/model` and `/effort` inside a session, or `claude --model claude-sonnet-4-6` at launch. These are no longer part of Purlin's config — they're Claude Code built-ins.

**Upgrading is one command.** `purlin:update` handles the submodule-to-plugin transition and the mode-to-sync migration automatically.

**Your config survives.** `.purlin/config.json` and everything in `features/` are untouched by the migration. Project-specific rules carry forward in `CLAUDE.md`.
