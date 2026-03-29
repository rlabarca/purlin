---
name: init
description: Initialize a project for Purlin — creates .purlin/ directory structure, config, and override template
---

**Purlin command: shared (all roles)**

Purlin agent: Initialize a new project for use with Purlin. Creates the required directory structure and configuration files.

---

## Path Resolution

> **Output standards:** See `${CLAUDE_PLUGIN_ROOT}/references/output_standards.md`.

## Usage

```
purlin:init [OPTIONS]

Options:
  --force    Re-initialize even if .purlin/ exists (preserves existing config)
```

---

## Execution Flow

### Step 1 -- Pre-flight Check

1. If `.purlin/` exists and `--force` is not set: "Project already initialized. Use `--force` to re-initialize." Stop.
2. If `.purlin/` exists and `--force` is set: proceed but preserve existing `config.json` and `config.local.json`.

### Step 2 -- Create Directory Structure

Create the following directories:

```
.purlin/
├── cache/          # Scan cache, dependency graph, checkpoints
├── runtime/        # PID files, session state
└── toolbox/        # Project-local and community tools
```

### Step 3 -- Create Configuration Files

1. **`.purlin/config.json`** -- Copy from `${CLAUDE_PLUGIN_ROOT}/templates/config.json`. Skip if exists (preserves user config).
2. **`.purlin/PURLIN_OVERRIDES.md`** -- Copy from `${CLAUDE_PLUGIN_ROOT}/templates/PURLIN_OVERRIDES.md`. Skip if exists.

### Step 4 -- Create Project CLAUDE.md

If `CLAUDE.md` does not exist at the project root, create it from `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md`. If `CLAUDE.md` exists, check if it already references Purlin. If not, append the Purlin reference block.

### Step 5 -- Update .gitignore

Ensure `.gitignore` contains Purlin-specific entries:

```
# Purlin
.purlin/cache/
.purlin/runtime/
.purlin_session.lock
.purlin_worktree_label
```

### Step 6 -- Create features/ Directory

If `features/` does not exist, create it with a placeholder README:

```
features/
└── README.md    # "Feature specifications live here. See purlin:spec to create one."
```

### Step 7 -- Confirmation

Print:
```
Project initialized for Purlin.

Created:
  .purlin/config.json
  .purlin/PURLIN_OVERRIDES.md
  .gitignore (updated)
  features/ (created)

Next: Start working by invoking any skill directly:
  purlin:mode pm         — switch to PM mode
  purlin:spec <topic>    — create your first feature spec
  purlin:status          — see what needs doing
```
