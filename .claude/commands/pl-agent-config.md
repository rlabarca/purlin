Modify agent configuration in `.purlin/config.local.json`. No git commit is made because the local config is gitignored.

**Owner: All roles** (each role sets its own config by default)

## Usage

```
/pl-agent-config [<role>] <key> <value>
```

**role** (optional): `architect`, `builder`, `qa`, or `pm`. Defaults to the current agent's role.
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

If `<role>` is omitted, infer it from the current agent context (Architect → `architect`, Builder → `builder`, QA → `qa`, PM → `pm`).

Validate `<role>` is one of `architect`, `builder`, `qa`, `pm`. If not, abort:
```
Error: Unknown role '<role>'. Must be one of: architect, builder, qa, pm
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

### 3. Resolve Target Config Path

Set `LOCAL_CONFIG_PATH = <PROJECT_ROOT>/.purlin/config.local.json`.

If the local config file does not exist, create it by copying `<PROJECT_ROOT>/.purlin/config.json` to `LOCAL_CONFIG_PATH` (copy-on-first-access, same as the config resolver).

If neither file exists, abort:
```
Error: No config file found at <PROJECT_ROOT>/.purlin/
```

### 4. Apply the Change

1. Read the current config JSON from `LOCAL_CONFIG_PATH`.
2. Navigate to `agents.<role>.<key>`.
3. Set the value. For boolean keys, convert the string `"true"`/`"false"` to the appropriate JSON boolean.
4. Serialize the updated config to JSON (preserving formatting: 4-space indentation).
5. Write to a temp file alongside the target (`<LOCAL_CONFIG_PATH>.tmp`), then rename to `<LOCAL_CONFIG_PATH>`.

### 5. Confirm

Print a summary:

```
Updated: agents.<role>.<key> = <value>
Config:  <LOCAL_CONFIG_PATH>
```

No git commit is made — `config.local.json` is gitignored.

---

## Notes

- This skill is the only sanctioned path for agents to change config. No git commit is needed because `config.local.json` is gitignored.
- **Config resolution:** The skill reads from the resolved local config (same resolution logic as `tools/config/resolve_config.py`). The `models` array for model validation is read from this resolved config.
