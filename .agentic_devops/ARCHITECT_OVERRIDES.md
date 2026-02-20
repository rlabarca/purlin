# Architect Overrides (agentic-dev-core)

> Core-specific rules for the agentic-dev-core framework repository itself.

## Sample Sync Prompt
When modifying ANY file inside `.agentic_devops/` (instructions, configs, or other artifacts), you MUST ask the User whether the corresponding file in `agentic_devops.sample/` should also be updated. Do NOT silently propagate changes to the sample folder. The sample folder is a distributable template and may intentionally diverge from the active working copy.

## Feature Scope Restriction (Core-Specific)
Feature files (`features/*.md`) in this repository define the framework's own DevOps tooling. They are distinct from consumer project features. When modifying a feature spec, verify it does not introduce consumer-project assumptions.

## Pre-Push Documentation Consistency Check
Before any push to GitHub, you MUST run a cross-reference consistency check across all instruction and documentation files. Specifically:
*   Cross-reference `instructions/HOW_WE_WORK_BASE.md`, `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`, `README.md`, `PROCESS_HISTORY.md`, and `features/arch_critic_policy.md`.
*   Check for: direct contradictions between files, stale file path references, terminology mismatches, lifecycle/protocol definitions that differ between the shared philosophy and role-specific instructions, and README content that no longer reflects current state.
*   If inconsistencies are found, fix them before pushing. Document fixes in `PROCESS_HISTORY.md`.

## Submodule Compatibility Review
When reviewing or modifying feature specs that touch tool behavior, verify the spec accounts for the submodule deployment model. Specifically:
*   **Path references** in requirements and scenarios MUST work when `tools/` is at `<project_root>/<submodule>/tools/`, not just `<project_root>/tools/`.
*   **Generated artifact paths** MUST target `.agentic_devops/runtime/` or `.agentic_devops/cache/`, never inside `tools/`.
*   **Config access patterns** MUST specify `AGENTIC_PROJECT_ROOT` as the primary detection mechanism, with climbing as fallback.
*   Reference `features/submodule_bootstrap.md` Sections 2.10-2.14 as the canonical submodule safety contract.
