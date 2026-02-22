# QA Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Server Interaction Prohibition
You MUST NOT start or interact with the DevOps tool server (CDD Dashboard). Servers are for human use only. Use CLI commands for all tool data: `tools/cdd/status.sh` for feature status, `tools/critic/run.sh` for the Critic report.

## Submodule Environment Verification
When verifying manual scenarios for any tool feature, always test in BOTH deployment modes:
1.  **Standalone mode:** Tools at `<project_root>/tools/`, config at `<project_root>/.purlin/config.json`.
2.  **Submodule mode:** Tools at `<project_root>/<submodule>/tools/`, config at `<project_root>/.purlin/config.json`.

For each scenario, verify:
*   Tool discovers the correct `config.json` (consumer project's, not the submodule's).
*   Generated artifacts (logs, PIDs, caches) are written to `.purlin/runtime/` or `.purlin/cache/`, NOT inside the submodule directory.
*   Tool does not crash if `config.json` is malformed -- it should fall back to defaults with a warning.

Report any submodule-specific failures as `[BUG]` with the tag "submodule-compat" in the description.
