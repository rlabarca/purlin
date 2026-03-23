# Implementation Notes: Local Release Step Management

*   `manage_step.py` must load `global_steps.json` only for ID conflict checking on `create`. It does NOT write to `global_steps.json` under any circumstances.
*   The `--clear-code` and `--clear-agent-instructions` flags are necessary because `--code ""` is ambiguous (empty string vs. null). The flags make "set to null" unambiguous and explicit.
*   Atomic writes must use a temp file in the same directory as the target (not `/tmp`), to ensure the rename is on the same filesystem. Pattern: write to `<file>.tmp`, then `os.replace("<file>.tmp", "<file>")`.
*   The slash command MUST call the CLI tool rather than manipulating JSON directly. This ensures validation is enforced through a single code path.
*   After the Builder implements `manage_step.py`, the `ARCHITECT_BASE.md` Authorized Slash Commands section must be updated to register `/pl-release-step`. Use `/pl-edit-base` to make that change.
*   `global_steps.json` is located via `tools_root` from `.purlin/config.json`, consistent with the path resolution convention in `HOW_WE_WORK_BASE.md` Section 6.
