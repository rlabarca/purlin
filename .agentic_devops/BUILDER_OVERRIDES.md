# Builder Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Server Interaction Prohibition
You MUST NOT start or interact with the DevOps tool server (CDD Dashboard). Servers are for human use only. Use CLI commands for all tool data: `tools/cdd/status.sh` for feature status, `tools/critic/run.sh` for the Critic report, `tools/cdd/status.sh --graph` for the dependency graph.

## Submodule Safety Checklist (Pre-Commit Gate)
Before committing ANY change to Python tools, shell scripts, or file-generation logic, verify each item below. This checklist exists because this codebase runs inside a git submodule in consumer projects -- violations will break consumer projects silently.

1.  **Project Root Detection:** Does the code use `AGENTIC_PROJECT_ROOT` env var as the primary root source? Does the climbing fallback try the submodule path (further) before the standalone path (nearer)?
2.  **Output File Paths:** Are ALL generated files (logs, PIDs, caches, JSON data) written to `.agentic_devops/runtime/` or `.agentic_devops/cache/` relative to the project root? NONE should be written inside `tools/`.
3.  **Config Resilience:** Is every `json.load()` on config files wrapped in `try/except (json.JSONDecodeError, IOError, OSError)` with fallback defaults?
4.  **Path Construction:** Are file paths constructed relative to the detected project root? No bare `"features"` or `"tools/"` relative to CWD?
5.  **JSON Modification Safety:** If any shell script modifies JSON via `sed`, does the regex preserve trailing commas and structural characters? Is there a `python3 json.load()` validation step?
6.  **Test Coverage:** Do tests exercise both standalone AND submodule directory layouts? Tests MUST create a simulated submodule environment (temporary directory with consumer project structure and a cloned submodule) to verify path resolution.

If ANY item fails, fix it before committing. Reference `features/submodule_bootstrap.md` Sections 2.10-2.14 for the full specification.
