Modify agent configuration in `.purlin/config.local.json`. Always applies changes to the MAIN project's local config, even from inside an isolated worktree. No git commit is made because the local config is gitignored.

**Owner: All roles** (each role sets its own config by default)

## Usage

```
/pl-agent-config [<role>] <key> <value>
```

**role** (optional): `architect`, `builder`, or `qa`. Defaults to the current agent's role.
**key**: `model`, `effort`, `startup_sequence`, `recommend_next_actions`, or `bypass_permissions`.
**value**: The new value (booleans: `true`/`false`; model IDs as strings; effort as `low`/`medium`/`high`).

**Examples:**
```
/pl-agent-config startup_sequence false
/pl-agent-config architect model claude-opus-4-6
/pl-agent-config builder startup_sequence true
/pl-agent-config qa effort medium
```

---

## Steps

### 1. Parse Arguments

Parse `<role>`, `<key>`, and `<value>` from the command invocation.

If `<role>` is omitted, infer it from the current agent context (Architect → `architect`, Builder → `builder`, QA → `qa`).

Validate `<role>` is one of `architect`, `builder`, `qa`. If not, abort:
```
Error: Unknown role '<role>'. Must be one of: architect, builder, qa
```

### 2. Validate Key

Valid keys and their accepted values:

| Key | Accepted Values |
|-----|----------------|
| `model` | Any `id` from the `models` array in config |
| `effort` | `low`, `medium`, `high` |
| `startup_sequence` | `true`, `false` |
| `recommend_next_actions` | `true`, `false` |
| `bypass_permissions` | `true`, `false` |

If `<key>` is not in this list, abort:
```
Error: Unknown key '<key>'. Valid keys: model, effort, startup_sequence, recommend_next_actions, bypass_permissions
```

For `model` values: read the `models` array from the resolved config and validate that `<value>` matches one of the `id` fields. If not, abort listing the valid model IDs.

For boolean keys: accept `true`/`false` (case-insensitive). Reject any other value.

For `effort`: accept `low`/`medium`/`high`. Reject any other value.

### 3. Detect Session Context

Run: `git rev-parse --abbrev-ref HEAD`

If the result starts with `isolated/`:
- You are in an **isolated worktree** session.
- Extract `<name>` = everything after `isolated/`.
- Proceed to Step 4 (Worktree Warning).

If the branch does NOT start with `isolated/`:
- You are in a **non-isolated session**.
- Skip to Step 5 (Resolve Target Config Path) using the current project root.

### 4. Worktree Warning (isolated sessions only)

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

### 5. Resolve Target Config Path

Set `LOCAL_CONFIG_PATH = <PROJECT_ROOT>/.purlin/config.local.json`.

If the local config file does not exist, create it by copying `<PROJECT_ROOT>/.purlin/config.json` to `LOCAL_CONFIG_PATH` (copy-on-first-access, same as the config resolver).

If neither file exists, abort:
```
Error: No config file found at <PROJECT_ROOT>/.purlin/
```

### 6. Apply the Change

1. Read the current config JSON from `LOCAL_CONFIG_PATH`.
2. Navigate to `agents.<role>.<key>`.
3. Set the value. For boolean keys, convert the string `"true"`/`"false"` to the appropriate JSON boolean.
4. Serialize the updated config to JSON (preserving formatting: 4-space indentation).
5. Write to a temp file alongside the target (`<LOCAL_CONFIG_PATH>.tmp`), then rename to `<LOCAL_CONFIG_PATH>`.

### 7. Confirm

Print a summary:

```
Updated: agents.<role>.<key> = <value>
Config:  <LOCAL_CONFIG_PATH>
```

No git commit is made — `config.local.json` is gitignored.

---

## Notes

- **Never modify the worktree's config directly.** The worktree config is ephemeral and will be discarded at kill time. All persistent changes go to MAIN's local config.
- **Worktree config is intentionally out of sync** after MAIN config is updated. The new value takes effect the next time a new isolation is created from MAIN (which copies the live MAIN config to the worktree).
- This skill is the only sanctioned path for agents to change config. No git commit is needed because `config.local.json` is gitignored.
- **Config resolution:** The skill reads from the resolved local config (same resolution logic as `tools/config/resolve_config.py`). The `models` array for model validation is read from this resolved config.
