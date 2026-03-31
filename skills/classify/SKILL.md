---
name: classify
description: Manage write_exceptions — paths classified as OTHER (freely editable without a skill)
---

## Usage

```
purlin:classify add <path>       Add path to OTHER list (freely editable)
purlin:classify remove <path>    Remove path from OTHER list
purlin:classify list             Show all current exceptions
```

---

## Subcommands

### `list` — Show Current Exceptions

1. Read resolved config via `purlin_config` MCP tool (`action: "read"`).
2. Extract `write_exceptions` array (default: `[]` if missing).
3. Print the table:

```
Write Exceptions (OTHER files — freely editable without a skill)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Pattern             Match Type
  ───────             ──────────
  docs/               directory prefix
  README.md           exact filename
  CHANGELOG.md        exact filename
  LICENSE             exact filename
  .gitignore          exact filename
  .gitattributes      exact filename

6 exceptions configured.

Manage: purlin:classify add <path> | purlin:classify remove <path>
```

Match type: trailing `/` = "directory prefix", otherwise = "exact filename".

If no exceptions exist: `"No write exceptions configured. All non-spec, non-system files require purlin:build."`

---

### `add <path>` — Add Exception

1. Read the current config from **both** `.purlin/config.json` and `.purlin/config.local.json`.
2. Check if `<path>` already exists in `write_exceptions`:
   - If duplicate: `"'<path>' is already in write_exceptions. No change needed."` Stop.
3. **Hard gate: Refuse protected file types.** Call `purlin_classify` MCP tool to get the current classification of `<path>`. If the classification is **CODE**, **SPEC**, or **INVARIANT**, refuse immediately — do NOT offer user confirmation:

```
Cannot reclassify '<path>' as OTHER — it is classified as <TYPE>.

  CODE files must be modified through purlin:build.
  SPEC files must be modified through purlin:spec (or related spec skills).
  INVARIANT files are external sources of truth managed by purlin:invariant.

  Reclassifying protected file types would bypass write guard enforcement
  and break sync tracking. Only UNKNOWN files can be added to write_exceptions.
```

   Stop. No override path exists.

4. **User confirmation required (UNKNOWN files only).** Ask the user for explicit approval via `AskUserQuestion`:

```
Reclassifying '<path>' as OTHER (freely editable without a skill).

  Current classification: UNKNOWN
  Effect: This path will no longer require a classification rule.
          Changes will NOT be tracked against any feature.

Confirm? (yes / no)
```

   - If user declines: `"Reclassification cancelled."` Stop.
   - If user confirms: proceed to step 5.
5. Append `<path>` to `write_exceptions` in **both** files. Preserve all other config keys. Write with `indent=4` formatting.
6. Print confirmation:

```
Added '<path>' to write_exceptions.

Match type: directory prefix  (matches docs/anything)
            — or —
Match type: exact filename    (matches README.md at project root)

Files matching this pattern are now freely editable without purlin:build.
```

**Config write protocol:**

Both config files must be updated so the change takes effect immediately (resolve_config reads config.local.json first via copy-on-first-access). Use this approach:

```python
import json, os

project_root = _find_project_root()
purlin_dir = os.path.join(project_root, '.purlin')

for filename in ('config.json', 'config.local.json'):
    filepath = os.path.join(purlin_dir, filename)
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r') as f:
        config = json.load(f)
    exceptions = config.get('write_exceptions', [])
    if path not in exceptions:
        exceptions.append(path)
        config['write_exceptions'] = exceptions
    with open(filepath, 'w') as f:
        json.dump(config, f, indent=4)
        f.write('\n')
```

If neither file exists: `"No Purlin config found. Run purlin:init first."` Stop.

---

### `remove <path>` — Remove Exception

1. Read the current config from **both** `.purlin/config.json` and `.purlin/config.local.json`.
2. Check if `<path>` exists in `write_exceptions`:
   - If not found: `"'<path>' is not in write_exceptions. No change needed."` Stop.
3. Remove `<path>` from `write_exceptions` in **both** files. Preserve all other config keys.
4. Print confirmation:

```
Removed '<path>' from write_exceptions.

Files matching this pattern now require purlin:build (classified as CODE).
```

Use the same dual-file write protocol as `add`.

---

## Error Handling

| Condition | Message | Action |
|---|---|---|
| No subcommand | `"Usage: purlin:classify add <path> \| remove <path> \| list"` | Stop |
| Unknown subcommand | `"Unknown subcommand '<cmd>'. Valid: add, remove, list."` | Stop |
| Missing path argument (add/remove) | `"Missing path argument. Usage: purlin:classify <add\|remove> <path>"` | Stop |
| No config files exist | `"No Purlin config found. Run purlin:init first."` | Stop |
| Config file is malformed JSON | Read whichever file is valid; warn about the malformed one | Continue |

---

## Notes

- **No active_skill marker needed.** This skill writes only to `.purlin/config.json` and `.purlin/config.local.json`, which are system files (`.purlin/*` — always writable per write guard step 1).
- **Immediate effect.** Changes take effect on the very next write attempt — the write guard calls `classify_file()` which reads `write_exceptions` fresh from config each time (no caching of exception list across invocations).
- **Trailing slash convention.** Remind users: `docs/` matches all files under docs/, while `docs` would only match an exact file named "docs" at the project root. If the user provides a directory path without a trailing slash, ask: `"Did you mean 'docs/' (directory prefix)? Without the trailing slash, this only matches an exact file named 'docs'."`
