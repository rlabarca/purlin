# What's New in v0.8.6

Upgrading from v0.8.5? Here's everything that changed.

---

## The Big Change: Purlin Is Now a Claude Code Plugin

Purlin is no longer distributed as a git submodule. It's now a **Claude Code plugin** that you install once at the user level and enable per-project. This eliminates the submodule onboarding friction (multi-step init, symlink management, path resolution) and replaces the 504-line `pl-run.sh` launcher with skills that run inside your Claude Code session.

| v0.8.5 (Submodule) | v0.8.6 (Plugin) |
|---|---|
| `git submodule add ... purlin` | One-time: register plugin in `~/.claude/settings.json` |
| `pl-init.sh` (808-line script) | `purlin:init` (skill, runs inside session) |
| `./pl-run.sh --mode engineer` | `claude` then `purlin:mode engineer` |
| `cd purlin && git pull && cd ..` | `purlin:update` |
| `purlin/tools/cdd/scan.sh` | MCP server (persistent, zero startup overhead) |

**What this means for you:**

- **No submodule in your repo.** The `purlin/` directory is gone. Plugin code lives in Claude Code's plugin cache, completely separate from your project files.
- **Just run `claude`.** The plugin activates automatically when you open a session in a Purlin-enabled project. No special launcher needed.
- **Mechanical mode guard.** Write-access boundaries are now enforced by a `PreToolUse` hook that physically blocks wrong-mode writes. The agent literally cannot write files outside its mode's domain. This replaces the v0.8.5 prompt-level enforcement.
- **Automatic context recovery.** A `SessionStart` hook restores your session state on every launch. No more depending on the agent to remember `purlin:resume`.
- **Auto-checkpoint before compaction.** A `PreCompact` hook saves session state before the context window fills. You never lose work to context limits.

---

## How to Install (New Projects)

**Quickest path** — clone the repo and use `--plugin-dir`:

```bash
git clone git@bitbucket.org:boomerangdev/purlin.git
mkdir my-app && cd my-app
git init
claude --plugin-dir ../purlin
```

Inside the session:

```
purlin:init
```

That's it. No submodule, no init script, no symlinks, no settings file edits.

Alternatively, register the plugin source in `~/.claude/settings.json` for automatic loading without the `--plugin-dir` flag. See the [Installation Guide](installation-guide.md) for both options.

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

After the update completes, exit and restart `claude`. The plugin model takes over.

---

## Skill Renaming: `/pl-*` to `purlin:*`

All skills have been renamed. The `pl-` prefix is gone, replaced by the `purlin:` plugin namespace.

| v0.8.5 | v0.8.6 |
|---|---|
| `/pl-build` | `purlin:build` |
| `/pl-verify` | `purlin:verify` |
| `/pl-spec` | `purlin:spec` |
| `/pl-mode` | `purlin:mode` |
| `/pl-status` | `purlin:status` |
| `/pl-resume` | `purlin:resume` |
| `/pl-help` | `purlin:help` |
| `/pl-update-purlin` | `purlin:update` |
| ... (all 36+ skills) | ... |

The skills themselves work the same way. Only the invocation name changed.

### New Skills

| Skill | Mode | What It Does |
|---|---|---|
| `purlin:init` | Any | Initializes a project for Purlin (replaces `pl-init.sh`). |

### Removed Skills

| Old Skill | Replacement |
|---|---|
| `purlin:start` | Removed. The plugin activates automatically when you run `claude`. Just invoke any skill directly (e.g., `purlin:build`, `purlin:spec`, `purlin:mode engineer`). Use `purlin:resume` only for session recovery — see below. |

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
   - The plugin's `settings.json` activates the Purlin agent (`agents/purlin.md`), which replaces the default Claude behavior with Purlin's three-mode system.
   - Hooks register (mode guard, session recovery, auto-checkpoint, companion tracking).
   - The MCP server starts (scan engine, dependency graph, mode state, file classification).
   - Your project's `CLAUDE.md` and `.purlin/PURLIN_OVERRIDES.md` layer on top.

4. **When you run `claude` outside a Purlin project:** Nothing happens. Standard Claude Code with zero Purlin interference.

### Session Startup

```bash
claude                              # Plugin auto-activates, SessionStart hook restores context
claude --plugin-dir ../purlin       # Or: load from a local clone
```

Inside the session, start working immediately — no startup command needed:

```
purlin:mode engineer                # Activate a mode
purlin:build login                  # Or just invoke a skill — it activates the mode for you
purlin:spec login                   # Same for PM mode
purlin:verify login                 # Same for QA mode
```

### When to Use `purlin:resume`

`purlin:resume` is for **session recovery**, not for starting work. You need it in two situations:

1. **After `/clear` or context compaction** — restores your checkpoint (mode, branch, in-progress work):
   ```
   purlin:resume
   ```

2. **After a worktree merge failure** — resolves pending merge conflicts:
   ```
   purlin:resume merge-recovery
   ```

`purlin:resume` also accepts flags for convenience when recovering:

```
purlin:resume --build               # Recover + Engineer mode + auto-start
purlin:resume --verify my_feature   # Recover + QA mode + verify a specific feature
purlin:resume --worktree --build    # Recover + isolated worktree + Engineer auto-start
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

The scan engine, dependency graph, file classification, mode state, and config are now served by a **persistent MCP server** that starts automatically with the plugin. Previously, each scan invocation spawned a fresh Python process (~100-150ms startup). Now the server runs once and responds instantly.

| MCP Tool | What It Does |
|---|---|
| `purlin_scan` | Full project scan (features, tests, status) |
| `purlin_status` | Mode-aware work items |
| `purlin_graph` | Dependency graph with cycle detection |
| `purlin_classify` | File path classification (for mode guard) |
| `purlin_mode` | Get or set current mode |
| `purlin_config` | Read or write `.purlin/config.json` |

You don't call these directly. Skills and hooks use them behind the scenes. The mode guard hook calls `purlin_classify` on every write to enforce boundaries mechanically.

---

## Hooks

Six hooks provide mechanical enforcement and automatic lifecycle management:

| Hook | Event | What It Does |
|---|---|---|
| **Mode Guard** | `PreToolUse` (Write/Edit) | Blocks file writes that violate mode boundaries. Exit code 2 = hard block. |
| **Session Start** | `SessionStart` | Restores session context (checkpoint, mode, terminal identity). |
| **Session End** | `SessionEnd` | Merges worktree branches, cleans session state. |
| **Permission Manager** | `PermissionRequest` | Auto-approves permission prompts when YOLO mode is enabled. |
| **Pre-Compact Checkpoint** | `PreCompact` | Auto-saves session state before context compaction. |
| **Companion Debt Tracker** | `FileChanged` | Tracks companion file debt when code files change. |

The mode guard hook is the biggest improvement. In v0.8.5, mode boundaries were enforced by instructing the agent not to write wrong-mode files (prompt-level). In v0.8.6, a script mechanically intercepts every Write/Edit call, checks the file against a classification map and the current mode, and returns a blocking error if the write violates boundaries.

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
│   ├── PURLIN_OVERRIDES.md    # Project-specific rules
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
│   ├── purlin.md              # Main agent definition (replaces PURLIN_BASE.md)
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
| `pl-run.sh` (504 lines) | Replaced by plugin hooks (auto-recovery, mode guard, checkpoint) |
| `pl-init.sh` / `tools/init.sh` (808 lines) | Replaced by `purlin:init` skill |
| `purlin/` submodule directory | Plugin lives in Claude Code's cache |
| `.claude/commands/pl-*.md` (36 files) | Moved to `skills/*/SKILL.md` inside the plugin |
| `instructions/PURLIN_BASE.md` | Content moved to `agents/purlin.md` |
| `instructions/references/` | Moved to `references/` at plugin root |
| `tools/` directory | Renamed to `scripts/`, scan engine wrapped in MCP server |
| `tools/cdd/scan.sh` | MCP server handles scanning directly |
| `tools/resolve_python.sh` | Not needed (MCP server runs persistently) |
| `purlin-config-sample/` | Renamed to `templates/` |

---

## Credential Storage

Plugin `userConfig` in `.claude-plugin/plugin.json` declares optional credentials (Figma token, deploy token, Confluence credentials). These are stored securely in the macOS keychain via Claude Code's native credential system, not in plain-text config files.

Configure credentials with `purlin:credentials` or when prompted at plugin enable time.

---

## Tips and Tricks

**Just run `claude`.** No launcher, no special startup command. The plugin handles everything. Use `--plugin-dir ../purlin` if loading from a local clone, or just `claude` if you registered the marketplace source. Invoke any skill directly to start working.

**Let hooks do the work.** Session recovery, checkpoint saves, and mode enforcement all happen automatically. The `SessionStart` hook restores context on every launch. The `PreCompact` hook saves checkpoints before context compaction.

**Mode guard is mechanical now.** If you accidentally try to write a spec in Engineer mode, the hook blocks it with an error. No more relying on the agent to self-police. This is the single biggest reliability improvement.

**YOLO mode persists.** Run `purlin:resume --yolo` once and all permission prompts are auto-approved for subsequent sessions. The `PermissionRequest` hook reads the flag from config. Run `purlin:resume --no-yolo` to turn it off.

**Model override is simpler.** The plugin sets a default model. Override per-session with `claude --model claude-sonnet-4-6`. No more `--model` flags on a launcher script.

**Upgrading is one command.** `purlin:update` handles the submodule-to-plugin transition automatically. It removes the submodule, cleans artifacts, and declares the plugin.

**Your overrides survive.** `.purlin/config.json`, `.purlin/PURLIN_OVERRIDES.md`, and everything in `features/` are untouched by the migration. Your project-specific rules carry forward exactly as they were.
