# QA Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Submodule Environment Verification
When verifying manual scenarios for any tool feature, always test in BOTH deployment modes:
1.  **Standalone mode:** Tools at `<project_root>/tools/`, config at `<project_root>/.purlin/config.json`.
2.  **Submodule mode:** Tools at `<project_root>/<submodule>/tools/`, config at `<project_root>/.purlin/config.json`.

For each scenario, verify:
*   Tool discovers the correct `config.json` (consumer project's, not the submodule's).
*   Generated artifacts (logs, PIDs, caches) are written to `.purlin/runtime/` or `.purlin/cache/`, NOT inside the submodule directory.
*   Tool does not crash if `config.json` is malformed -- it should fall back to defaults with a warning.

Report any submodule-specific failures as `[BUG]` with the tag "submodule-compat" in the description.

## Application Code Location
In this repository, Builder-owned application code lives in `tools/` (consumer-facing framework tools) and `dev/` (Purlin-dev maintenance scripts).
