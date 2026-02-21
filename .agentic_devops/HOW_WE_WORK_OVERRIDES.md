# How We Work: Core-Specific Additions

> This file contains workflow additions specific to the Purlin framework repository.
> Consumer projects will have their own version of this file with project-specific additions.

## Submodule Compatibility Mandate

This repository is consumed by other projects as a git submodule. Every code change MUST be safe for the submodule environment. Before committing any change to tools, scripts, or generated artifacts, verify:

1.  **No hardcoded project-root assumptions.** Python tools MUST use `AGENTIC_PROJECT_ROOT` (env var) first, then climbing fallback with submodule-priority ordering (further path before nearer path). See `features/submodule_bootstrap.md` Section 2.11.
2.  **No artifacts written inside `tools/`.** All generated files (logs, PIDs, caches, data files) MUST be written to `<project_root>/.agentic_devops/runtime/` or `<project_root>/.agentic_devops/cache/`. See Section 2.12.
3.  **No bare `json.load()` on config files.** Always wrap in `try/except` with fallback defaults. See Section 2.13.
4.  **No CWD-relative path assumptions.** Use project root detection, not `os.getcwd()` or bare relative paths. See Section 2.14.
5.  **sed commands preserve JSON structure.** Any `sed` regex operating on JSON files MUST be tested for comma preservation and validated with `python3 json.load()`. See Section 2.10.
