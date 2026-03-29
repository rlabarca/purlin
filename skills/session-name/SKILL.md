---
name: session-name
description: Update the terminal session display name. Available in all modes
---

```
purlin:session-name [label]
```

---

## No-Argument: Refresh from Current Mode

1. Determine the current mode: `Engineer`, `PM`, `QA`, or `Purlin` if no mode is active.
2. Determine the project name: read `project_name` from `.purlin/config.json` (via the MCP `purlin_config` tool with `key: "project_name"`, or read `.purlin/config.json` directly). If absent or empty, fall back to `basename` of the project root.
3. Run:
   ```bash
   source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<mode>" "<project>"
   ```
4. Print the updated badge and which terminal environments were updated. Use `purlin_detect_env` to list active environments. Silently omit environments that are not detected.

Example output:
```
Session: Eng(main) | purlin
Updated: terminal title, iTerm badge
```

## With Argument: Custom Label

1. Use the provided argument as the label (replaces the project name after `|`).
2. Determine the current mode: `Engineer`, `PM`, `QA`, or `Purlin` if no mode is active.
3. Run:
   ```bash
   source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<mode>" "<label>"
   ```
4. Print the updated badge and which environments were updated.

Example output:
```
Session: QA(feature-xyz) | verify auth
Updated: terminal title, Warp tab
```
