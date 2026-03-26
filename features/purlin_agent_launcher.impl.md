# Companion: purlin_agent_launcher

## [DISCOVERY] --effort and --find-work flags support interactive selection (2026-03-26)

The `--effort` and `--find-work` flags now accept optional parameters, matching `--model` behavior. When invoked without a value (e.g., `./pl-run.sh --effort`), they present an interactive menu instead of freezing (the previous implementation did an unconditional `shift 2` which consumed the next flag or hung).

The interactive selection block was refactored to support independent menus for `--model`, `--effort`, and `--find-work`:
- `--model` (no param): shows model and effort menus (unchanged behavior)
- `--effort` (no param): shows effort menu only
- `--find-work` (no param): shows work discovery menu only
- Both `--model` and `--effort` without params: same as just `--model` (both menus)
- One with param, other without: only shows menu for the parameterless flag
- All interactive selections respect `--no-save` (first-run always persists)

**Spec alignment:** The spec (Section 2.2.1) defines `--effort <level>` and `--find-work <bool>` as requiring values. This change makes both parameters optional (`--effort [level]`, `--find-work [bool]`), matching the `--model [id]` pattern. The spec should be updated accordingly.
