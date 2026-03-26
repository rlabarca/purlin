**Purlin command: Purlin agent only**
**Purlin mode: shared**

Update the terminal session display name. Available in all modes.

```
/pl-session-name [label]
```

---

## Path Resolution

> See `instructions/references/path_resolution.md`. Produces `TOOLS_ROOT`.

## No-Argument: Refresh from Current Mode

1. Determine the current mode: `Engineer`, `PM`, `QA`, or `Purlin` if no mode is active.
2. Determine the project name from `basename` of the project root.
3. Run:
   ```bash
   source ${TOOLS_ROOT}/terminal/identity.sh && update_session_identity "<mode>" "<project>"
   ```
4. Print the updated badge and which terminal environments were updated. Use `purlin_detect_env` to list active environments. Silently omit environments that are not detected.

Example output:
```
Session: Engineer (main)
Updated: terminal title, iTerm badge
```

## With Argument: Custom Label

1. Use the provided argument as the label (replacing the mode name).
2. Determine the project name from `basename` of the project root.
3. Run:
   ```bash
   source ${TOOLS_ROOT}/terminal/identity.sh && update_session_identity "<label>" "<project>"
   ```
4. Print the updated badge and which environments were updated.

Example output:
```
Session: Deploy (feature-xyz)
Updated: terminal title, Warp tab
```
