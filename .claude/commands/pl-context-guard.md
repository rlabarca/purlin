View or modify per-agent context guard settings in `.purlin/config.local.json`. Changes are reflected in the CDD Dashboard on the next auto-refresh cycle. No git commit is made because the local config is gitignored.

**Owner: All roles** (shared skill)

## Usage

```
/pl-context-guard                      # Show status for all roles
/pl-context-guard <role>               # Show status for one role
/pl-context-guard <role> on            # Enable guard for role
/pl-context-guard <role> off           # Disable guard for role
```

**role**: `architect`, `builder`, or `qa`.

**Examples:**
```
/pl-context-guard
/pl-context-guard builder
/pl-context-guard qa off
/pl-context-guard architect on
```

---

## Steps

### 1. Parse Arguments

Parse the arguments from the command invocation:

- **No arguments:** Subcommand is `status` for all roles.
- **One argument (valid role):** Subcommand is `status` for that role.
- **Two arguments where second is `on`/`off`:** Subcommand is `toggle` — role is first arg, state is second.

Validate `<role>` is one of `architect`, `builder`, `qa`. If not, abort:
```
Error: Unknown role '<role>'. Must be one of: architect, builder, qa
```

### 2. Read Config

Read the resolved config using the same resolution logic as `tools/config/resolve_config.py`:
- Read `config.local.json` if it exists, otherwise fall back to `config.json`.
- Extract for each role: `agents.<role>.context_guard` (default `true`).

### 3. Execute Subcommand

#### 3a. Status (all roles)

Print:
```
Context Guard Status
────────────────────
  architect:  ON
  builder:    ON
  qa:         OFF
```

For each role: show `ON` or `OFF` based on `context_guard` (default `true`).

#### 3b. Status (single role)

Print:
```
Context Guard: <role>
  Enabled:    true
```

Where the value is the boolean from `agents.<role>.context_guard` (default `true`).

#### 3c. Toggle (on/off)

Proceed to Step 4 (Detect Session Context) then Step 5 (Apply the Change) to write `agents.<role>.context_guard` as `true` (on) or `false` (off).

### 4. Detect Session Context

Run: `git rev-parse --abbrev-ref HEAD`

If the result starts with `isolated/`:
- You are in an **isolated worktree** session.
- Extract `<name>` = everything after `isolated/`.
- Proceed to Step 4a (Worktree Warning).

If the branch does NOT start with `isolated/`:
- Skip to Step 5 (Apply the Change) using the current project root.

#### 4a. Worktree Warning (isolated sessions only)

Locate the MAIN project root by parsing `git worktree list --porcelain`:
- Find the worktree entry whose `branch` field is `refs/heads/main`.
- If not found, use the first worktree entry (the project root is always listed first).
- Extract the `worktree` path from that entry as `PROJECT_ROOT`.

Display this warning and prompt the user to confirm:

```
⚠  Worktree context: isolated/<name>

Config changes are ALWAYS applied to the MAIN project local config:
  <PROJECT_ROOT>/.purlin/config.local.json

The current worktree's config is ephemeral — it will be discarded
when this team is killed. Your change will take effect the next time
an isolated team is created from main.

Continue? [y/N]
```

If the user responds anything other than `y` or `yes` (case-insensitive), abort:
```
Aborted. No changes made.
```

### 5. Apply the Change

1. Set `LOCAL_CONFIG_PATH = <PROJECT_ROOT>/.purlin/config.local.json`.
2. If the local config file does not exist, create it by copying `<PROJECT_ROOT>/.purlin/config.json` to `LOCAL_CONFIG_PATH` (copy-on-first-access).
3. If neither file exists, abort: `Error: No config file found at <PROJECT_ROOT>/.purlin/`
4. Read the current config JSON from `LOCAL_CONFIG_PATH`.
5. Navigate to `agents.<role>` and set `context_guard` as a boolean (`true` for on, `false` for off).
6. Serialize the updated config to JSON (4-space indentation).
7. Write to a temp file (`<LOCAL_CONFIG_PATH>.tmp`), then rename to `<LOCAL_CONFIG_PATH>`.

### 6. Confirm

Print:
```
Updated: agents.<role>.context_guard = <value>
Config:  <LOCAL_CONFIG_PATH>
```

No git commit is made — `config.local.json` is gitignored.

---

## Notes

- **Never modify the worktree's config directly.** The worktree config is ephemeral. All persistent changes go to MAIN's local config.
- Changes are immediately visible to the CDD Dashboard via its 5-second auto-refresh cycle (the Dashboard reads from the config resolver, which reads `config.local.json`).
- The context guard hook (`tools/hooks/context_guard.sh`) reads config on every invocation, so enabled changes take effect on the very next tool call within the same session.
- This skill is the sanctioned path for agents to change context guard settings. It complements `/pl-agent-config` (which handles model, effort, permissions, startup settings).
