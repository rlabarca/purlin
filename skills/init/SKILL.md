---
name: init
description: Initialize a project for Purlin — creates .purlin/ directory structure and config
---

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
2. **`.purlin/sync_ledger.json`** -- Create empty `{}`. This is the persistent sync tracking ledger (committed to git). Skip if exists.

### Step 4 -- Update .gitignore

Ensure `.gitignore` contains Purlin-specific entries:

```
# Purlin
.purlin/cache/
.purlin/runtime/
.purlin/runtime/sync_state.json
.purlin_session.lock
.purlin_worktree_label
```

### Step 5 -- Create features/ Directory

If `features/` does not exist, create it with a placeholder README:

```
features/
└── README.md    # "Feature specifications live here. See purlin:spec to create one."
```

### Step 6 -- Confirmation

Print:
```
Project initialized for Purlin.

Created:
  .purlin/config.json
  .purlin/sync_ledger.json
  .gitignore (updated)
  features/

Next: Start working by invoking any skill directly:
  purlin:spec <topic>    — create your first feature spec
  purlin:status          — see what needs doing
```

### Step 7 -- Commit

Commit the initialized project structure: `git commit -m "chore: initialize purlin project"`.
