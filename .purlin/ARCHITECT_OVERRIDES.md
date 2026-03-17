# Architect Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Sample Sync Prompt
When modifying ANY file inside `.purlin/` (instructions, configs, or other artifacts), you MUST ask the User whether the corresponding file in `purlin-config-sample/` should also be updated. Do NOT silently propagate changes to the sample folder. The sample folder is a distributable template and may intentionally diverge from the active working copy.

## Feature Scope Restriction (Core-Specific)
Feature files (`features/*.md`) in this repository define the framework's own DevOps tooling. They are distinct from consumer project features. When modifying a feature spec, verify it does not introduce consumer-project assumptions.

## Pre-Push Documentation Consistency Check
Before any push to GitHub, you MUST run a cross-reference consistency check across all instruction and documentation files. Specifically:
*   Cross-reference `instructions/HOW_WE_WORK_BASE.md`, `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`, `README.md`, and `features/policy_critic.md`.
*   Check for: direct contradictions between files, stale file path references, terminology mismatches, lifecycle/protocol definitions that differ between the shared philosophy and role-specific instructions, and README content that no longer reflects current state.
*   If inconsistencies are found, fix them before pushing.

## Submodule Compatibility Review
When reviewing or modifying feature specs that touch tool behavior, verify the spec accounts for the submodule deployment model. Specifically:
*   **Path references** in requirements and scenarios MUST work when `tools/` is at `<project_root>/<submodule>/tools/`, not just `<project_root>/tools/`.
*   **Generated artifact paths** MUST target `.purlin/runtime/` or `.purlin/cache/`, never inside `tools/`.
*   **Config access patterns** MUST specify `PURLIN_PROJECT_ROOT` as the primary detection mechanism, with climbing as fallback.
*   Reference `features/release_submodule_safety_audit.md` Section 2.2 as the canonical submodule safety check categories.

## Base File Soft Check
Although Architect write access includes `instructions/*.md`, base files MUST NOT be modified without using `/pl-edit-base`. This command confirms the Purlin framework context and enforces the additive-only principle. In consumer projects, base files are inside the submodule and are governed by the Submodule Immutability Mandate -- they are never editable regardless of tool used.

## Script Classification Mandate

When designing features that require implementation scripts, you MUST classify each script before delegating to the Builder:

*   **Consumer-facing → `tools/`**: The script is useful to or runnable by consumer projects. Submodule safety compliance is mandatory (see HOW_WE_WORK_OVERRIDES Submodule Compatibility Mandate). Reference must work when `tools/` is at `<project_root>/<submodule>/tools/`.
*   **Purlin-dev-specific → `dev/`**: The script is for maintaining, building, or releasing the Purlin framework itself. No submodule safety mandate applies. Path references use `dev/` directly (no `tools_root` indirection).

When updating a feature spec, the `Ownership` section and all scenario invocations MUST reflect the correct folder. Do NOT place Purlin-dev scripts in `tools/`.
