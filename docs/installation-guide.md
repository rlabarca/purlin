# Installing and Updating Purlin

## Overview

Purlin is added to your project as a git submodule. A single init script
sets up the entire scaffold: config files, agent launchers, slash commands,
and git hooks. When a new version of Purlin is released, you update the
submodule and re-run init to refresh everything.

This guide covers three scenarios:

1. **New project** -- adding Purlin for the first time.
2. **Existing project** -- joining a team that already uses Purlin.
3. **Updating** -- moving to a newer version of Purlin.

---

## Installing Purlin (New Project)

### Prerequisites

- Git (any recent version)
- Python 3.8+ (used by tooling scripts)
- Claude Code CLI (`claude`) **2.1.81 or later**, installed and authenticated
- Node.js (optional, for web testing via Playwright)

> **Note:** Agent launchers (`pl-run-*.sh`) automatically check for Claude Code
> updates at startup and will update the CLI if a newer version is available.
> You can also run `claude update` manually at any time.

### Step-by-Step

**1. Create your project and initialize git:**

```bash
mkdir my-project && cd my-project
git init
```

If you already have a git repository, skip this step.

**2. Add Purlin as a submodule:**

```bash
git submodule add git@bitbucket.org:boomerangdev/purlin.git purlin
```

This clones Purlin into a `purlin/` directory and creates a `.gitmodules`
file.

**3. Run the init script:**

```bash
./purlin/pl-init.sh
```

This is the only command you need to remember. It detects that this is a
first-time setup, checks for missing tools (and tells you how to install
them), then runs **Full Init Mode**, which:

- Copies config templates to `.purlin/` (config, overrides, release setup).
- Sets `tools_root` in your config to `"purlin/tools"`.
- Generates agent launcher scripts (`pl-run-architect.sh`,
  `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`).
- Distributes slash commands to `.claude/commands/`.
- Sets up the `features/` directory.
- Updates `.gitignore` with Purlin-specific patterns.
- Installs Claude Code hooks for session recovery.
- Installs MCP servers from the Purlin manifest.

**4. Commit the scaffold:**

```bash
git add -A && git commit -m "init purlin"
```

**5. Launch an agent:**

```bash
./pl-run-pm.sh       # Start the PM agent (recommended first)
./pl-run-architect.sh # Or start the Architect
```

### What Gets Created

After init, your project root will contain:

```
my-project/
├── .purlin/
│   ├── config.json              # Main config (models, tools_root, agent settings)
│   ├── HOW_WE_WORK_OVERRIDES.md # Workflow rules, submodule safety mandate
│   ├── ARCHITECT_OVERRIDES.md   # Architect rules, submodule compatibility
│   ├── BUILDER_OVERRIDES.md     # Builder rules, submodule safety checklist
│   ├── QA_OVERRIDES.md          # QA rules, test tiers, voice/tone config
│   ├── PM_OVERRIDES.md          # PM customizations
│   ├── .upstream_sha            # Pinned Purlin version SHA
│   ├── release/
│   │   ├── config.json          # Release step ordering
│   │   └── local_steps.json     # Project-specific release steps
│   ├── cache/                   # Auto-generated (not committed)
│   └── runtime/                 # Transient state (not committed)
├── .claude/
│   ├── commands/pl-*.md         # Slash commands for agents
│   └── agents/*.md              # Agent definitions
├── features/                    # Feature specs go here
├── purlin/                      # The submodule (do not edit)
├── pl-init.sh                   # Init shim (committed)
├── pl-run-architect.sh          # Architect launcher
├── pl-run-builder.sh            # Builder launcher
├── pl-run-qa.sh                 # QA launcher
└── pl-run-pm.sh                 # PM launcher
```

### Key Config: `tools_root`

The `tools_root` value in `.purlin/config.json` tells every agent where
Purlin's tools live. For a submodule at `purlin/`, this is set to
`"purlin/tools"`. The init script sets this automatically -- you should not
need to change it.

All agent instructions use `{tools_root}/` as a prefix for tool paths. For
example, `{tools_root}/cdd/status.sh` resolves to `purlin/tools/cdd/status.sh`
in a consumer project.

---

## Joining an Existing Project

If you are cloning a project that already uses Purlin, setup is simpler:

```bash
git clone <repo-url>
cd <project-name>
./pl-init.sh
```

The `pl-init.sh` shim at the project root handles everything:

1. Initializes the submodule if needed (`git submodule update --init`).
2. Detects that `.purlin/` already exists.
3. Runs in **Refresh Mode** -- updates commands, launchers, and symlinks
   without touching your config or override files.

Your team's customizations in `.purlin/config.json` and the `*_OVERRIDES.md`
files are preserved.

---

## Updating Purlin

There are two ways to update: a quick manual update, or the full
agent-assisted update.

### Quick Update (Manual)

Use this when you just want to move to a specific Purlin commit or tag:

**1. Enter the submodule and fetch:**

```bash
cd purlin
git fetch origin
git checkout <tag-or-sha>    # e.g., git checkout v2.1.0
cd ..
```

**2. Re-run init to refresh artifacts:**

```bash
./pl-init.sh
```

In Refresh Mode, init will:

- Update slash commands (skip any you have locally modified).
- Regenerate agent launchers.
- Update `.purlin/.upstream_sha` to the new version.
- Sync `.gitignore` patterns (additive only -- never removes patterns).
- Install any new MCP servers.

It will **not** touch:

- `.purlin/config.json` or `config.local.json`
- Any `*_OVERRIDES.md` file
- The `.purlin/release/` directory
- The `features/` directory

**3. Commit the update:**

```bash
git add purlin .purlin pl-init.sh .claude/commands .claude/agents
git commit -m "update purlin to <version>"
```

### Agent-Assisted Update (`/pl-update-purlin`)

For a more thorough update with semantic analysis, use the `/pl-update-purlin`
command inside any agent session. This performs:

1. **Fetch and version check** -- shows what version you are on and what is
   available upstream.
2. **Pre-update conflict scan** -- identifies locally modified commands,
   agents, or launchers that may conflict with the update.
3. **Submodule advance** -- checks out the target SHA.
4. **Artifact refresh** -- runs `pl-init.sh` in quiet mode.
5. **Conflict resolution** -- performs three-way diffs for any modified
   files and asks you how to resolve.
6. **Config sync** -- merges new config keys into `config.local.json`
   without overwriting existing values.
7. **Stale artifact cleanup** -- removes old launcher scripts from
   previous naming conventions.
8. **Customization impact check** -- analyzes whether the update affects
   your local override files and reports potential issues.

To run a dry-run first:

```
/pl-update-purlin --dry-run
```

This shows what would change without modifying anything.

---

## What Refresh Mode Protects

The distinction between Full Init and Refresh Mode is important for teams.
Full Init runs once (on first setup) and copies all templates. Every
subsequent run is Refresh Mode, which is carefully scoped to avoid
overwriting your customizations:

| Artifact | Full Init | Refresh Mode |
|----------|-----------|--------------|
| `.purlin/config.json` | Copied from template | **Never modified** |
| `*_OVERRIDES.md` | Copied from template | **Never modified** |
| `.purlin/release/` | Copied from template | **Never modified** |
| Slash commands | Copied | Updated (skip if locally newer) |
| Agent launchers | Generated | Regenerated |
| `pl-init.sh` shim | Generated | Regenerated if SHA changed |
| `.gitignore` patterns | Merged | Merged (additive only) |
| MCP servers | Installed | New servers added |

---

## Customizing Your Setup

### Agent Configuration

Edit `.purlin/config.json` to change:

- Which Claude model each agent uses.
- Reasoning effort level (low, medium, high).
- Whether agents auto-discover work at startup (`find_work`).
- Whether agents start executing immediately (`auto_start`).

See the [Agent Configuration Guide](agent-configuration-guide.md) for
details.

### Local Config Overrides

Create `.purlin/config.local.json` to override settings without modifying
the shared config. This file is not committed to git (it is gitignored) and
takes precedence over `config.json` for any keys it defines.

### Role Overrides

Each role has an override file in `.purlin/`:

- `ARCHITECT_OVERRIDES.md` -- project-specific Architect rules, submodule compatibility checks
- `BUILDER_OVERRIDES.md` -- project-specific Builder rules, submodule safety checklist
- `QA_OVERRIDES.md` -- project-specific QA rules, test priority tiers, voice/tone config
- `PM_OVERRIDES.md` -- project-specific PM rules
- `HOW_WE_WORK_OVERRIDES.md` -- project-wide workflow additions, submodule safety mandate

These are committed to git and shared with the team. Use `/pl-override-edit`
for guided editing with conflict scanning.

---

## Troubleshooting

### `pl-init.sh` says "submodule not initialized"

Run `git submodule update --init purlin` manually, then re-run `./pl-init.sh`.

### Slash commands are outdated after update

Re-run `./pl-init.sh`. It will overwrite commands that are older than the
source versions in the submodule. If you have locally modified a command
(the destination file is newer than the source), init skips it to protect
your changes. Delete the local copy to force a refresh.

### Agent says "tools_root not found"

Verify `.purlin/config.json` exists and contains a `"tools_root"` key.
If the file is missing, re-run `./pl-init.sh` in Full Init Mode (rename or
remove the `.purlin/` directory first to trigger it).

### Python venv not set up

If tools fail with import errors, create a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r purlin/requirements-optional.txt
```

This is optional but recommended for projects using Confluence sync or other
optional dependencies.
