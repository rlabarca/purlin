**Purlin command: Purlin agent only (replaces /pl-release-check, /pl-release-run, /pl-release-step)**
**Purlin mode: Engineer**

Legacy agents: Use /pl-release-check, /pl-release-run, or /pl-release-step instead.
Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

## Usage

```
/pl-release check     — Verify release readiness
/pl-release run       — Execute a release step by name
/pl-release step      — Create, modify, or delete a release step
```

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

## Subcommands

### check

Execute the release checklist. Read the release configuration from `.purlin/release/config.json` and `${TOOLS_ROOT}/release/global_steps.json`. For each enabled step in order, verify readiness.

Key invariants:
- Zero-Queue Mandate: every feature MUST have `engineer: "DONE"` and `qa` as `"CLEAN"` or `"N/A"`.
- Dependency graph MUST be acyclic.
- Run `${TOOLS_ROOT}/cdd/scan.sh` to get current project state.

### run

Execute a single named release step. Usage: `/pl-release run <step_name>`.
Read the step's `agent_instructions` from the release config and execute.

### step

Manage individual release steps. Usage: `/pl-release step <add|remove|reorder|enable|disable> [args]`.
Modifies `.purlin/release/config.json`.
