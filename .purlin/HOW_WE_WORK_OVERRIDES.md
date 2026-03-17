# How We Work: Core-Specific Additions

> This file contains workflow additions specific to the Purlin framework repository.
> Consumer projects will have their own version of this file with project-specific additions.

## Submodule Compatibility Mandate

This repository is consumed by other projects as a git submodule. Every code change MUST be safe for the submodule environment. Before committing any change to tools, scripts, or generated artifacts, verify:

1.  **No hardcoded project-root assumptions.** Python tools MUST use `PURLIN_PROJECT_ROOT` (env var) first, then climbing fallback with submodule-priority ordering (further path before nearer path). See `release_submodule_safety_audit.md` Section 2.2, Category 1.
2.  **No artifacts written inside `tools/`.** All generated files (logs, PIDs, caches, data files) MUST be written to `<project_root>/.purlin/runtime/` or `<project_root>/.purlin/cache/`. See Category 3.
3.  **No bare `json.load()` on config files.** Always wrap in `try/except` with fallback defaults. See Category 4.
4.  **No CWD-relative path assumptions.** Use project root detection, not `os.getcwd()` or bare relative paths. See Category 5.
5.  **sed commands preserve JSON structure.** Any `sed` regex operating on JSON files MUST be tested for comma preservation and validated with `python3 json.load()`. See Category 6.

## Tool Folder Separation Convention

This repository contains two distinct categories of scripts, stored in two separate directories:

*   **`tools/`** — Consumer-facing framework tooling. All scripts here MUST be submodule-safe (see Submodule Compatibility Mandate above). Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use and are NOT subject to the submodule safety mandate.

**Classification rule:** Before adding a new script, ask: "Would a consumer project ever need to run this?" If yes → `tools/`. If no → `dev/`.

**Examples of `dev/` scripts:**
- Workflow animation generator (generates Purlin's own README GIF)
- Framework documentation build scripts
- Release artifact scripts that produce Purlin-specific outputs
