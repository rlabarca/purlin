# Purlin Overrides

## General (all modes)

# How We Work: Core-Specific Additions

> This file contains workflow additions specific to the Purlin framework repository.
> Consumer projects will have their own version of this file with project-specific additions.

## Submodule Compatibility Mandate

This repository is consumed by other projects as a git submodule. Every code change MUST be safe for the submodule environment. Before committing any change to tools, scripts, or generated artifacts, verify:

1.  **No hardcoded project-root assumptions.** Python tools MUST use `PURLIN_PROJECT_ROOT` (env var) first, then climbing fallback with submodule-priority ordering (further path before nearer path).
2.  **No artifacts written inside `tools/`.** All generated files (logs, PIDs, caches, data files) MUST be written to `<project_root>/.purlin/runtime/` or `<project_root>/.purlin/cache/`.
3.  **No bare `json.load()` on config files.** Always wrap in `try/except` with fallback defaults.
4.  **No CWD-relative path assumptions.** Use project root detection, not `os.getcwd()` or bare relative paths.
5.  **sed commands preserve JSON structure.** Any `sed` regex operating on JSON files MUST be tested for comma preservation and validated with `python3 json.load()`.

## Tool Folder Separation Convention

This repository contains two distinct categories of scripts, stored in two separate directories:

*   **`tools/`** — Consumer-facing framework tooling. All scripts here MUST be submodule-safe (see Submodule Compatibility Mandate above). Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use and are NOT subject to the submodule safety mandate.

**Classification rule:** Before adding a new script, ask: "Would a consumer project ever need to run this?" If yes → `tools/`. If no → `dev/`.

**Examples of `dev/` scripts:**
- Workflow animation generator (generates Purlin's own README GIF)
- Framework documentation build scripts
- Release artifact scripts that produce Purlin-specific outputs

## Engineer Mode

# Engineer Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Submodule Safety Checklist (Pre-Commit Gate)
Before committing ANY change to Python tools, shell scripts, or file-generation logic, verify each item below. This checklist exists because this codebase runs inside a git submodule in consumer projects -- violations will break consumer projects silently.

1.  **Project Root Detection:** Does the code use `PURLIN_PROJECT_ROOT` env var as the primary root source? Does the climbing fallback try the submodule path (further) before the standalone path (nearer)?
2.  **Output File Paths:** Are ALL generated files (logs, PIDs, caches, JSON data) written to `.purlin/runtime/` or `.purlin/cache/` relative to the project root? NONE should be written inside `tools/`.
3.  **Config Resilience:** Is every `json.load()` on config files wrapped in `try/except (json.JSONDecodeError, IOError, OSError)` with fallback defaults?
4.  **Path Construction:** Are file paths constructed relative to the detected project root? No bare `"features"` or `"tools/"` relative to CWD?
5.  **JSON Modification Safety:** If any shell script modifies JSON via `sed`, does the regex preserve trailing commas and structural characters? Is there a `python3 json.load()` validation step?
6.  **Test Coverage:** Do tests exercise both standalone AND submodule directory layouts? Tests MUST create a simulated submodule environment (temporary directory with consumer project structure and a cloned submodule) to verify path resolution.

If ANY item fails, fix it before committing.

**Exemption:** Scripts located in `dev/` are Purlin-dev-specific and are exempt from this checklist. They are never run in a consumer project's submodule context. Apply normal quality standards but skip submodule-specific verification items.

## Test Code Location
In this repository, test code is colocated with the tool it tests under `tools/` (e.g., `tools/cdd/test_spec_map.py`).

# PM Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Sample Sync Prompt
When modifying ANY file inside `.purlin/` (instructions, configs, or other artifacts), you MUST ask the User whether the corresponding file in `purlin-config-sample/` should also be updated. Do NOT silently propagate changes to the sample folder. The sample folder is a distributable template and may intentionally diverge from the active working copy.

## Pre-Push Documentation Consistency Check
Before any push to GitHub, you MUST run a cross-reference consistency check across all instruction and documentation files. Specifically:
*   Cross-reference `instructions/PURLIN_BASE.md` and `README.md`.
*   Check for: direct contradictions between files, stale file path references, terminology mismatches, lifecycle/protocol definitions that differ between the shared philosophy and role-specific instructions, and README content that no longer reflects current state.
*   If inconsistencies are found, fix them before pushing.

## Submodule Compatibility Review
When reviewing or modifying feature specs that touch tool behavior, verify the spec accounts for the submodule deployment model. Specifically:
*   **Path references** in requirements and scenarios MUST work when `tools/` is at `<project_root>/<submodule>/tools/`, not just `<project_root>/tools/`.
*   **Generated artifact paths** MUST target `.purlin/runtime/` or `.purlin/cache/`, never inside `tools/`.
*   **Config access patterns** MUST specify `PURLIN_PROJECT_ROOT` as the primary detection mechanism, with climbing as fallback.
*   Verify submodule safety per the checklist in the Submodule Compatibility Mandate above.

## Base File Soft Check
Although PM/Engineer write access includes `instructions/*.md`, base files MUST NOT be modified without using `/pl-edit-base`. This command confirms the Purlin framework context and enforces the additive-only principle. In consumer projects, base files are inside the submodule and are governed by the Submodule Immutability Mandate -- they are never editable regardless of tool used.

## Script Classification Mandate

When designing features that require implementation scripts, you MUST classify each script before delegating to Engineer mode:

*   **Consumer-facing → `tools/`**: The script is useful to or runnable by consumer projects. Submodule safety compliance is mandatory (see Submodule Compatibility Mandate above). Reference must work when `tools/` is at `<project_root>/<submodule>/tools/`.
*   **Purlin-dev-specific → `dev/`**: The script is for maintaining, building, or releasing the Purlin framework itself. No submodule safety mandate applies. Path references use `dev/` directly (no `tools_root` indirection).

When updating a feature spec, the `Ownership` section and all scenario invocations MUST reflect the correct folder. Do NOT place Purlin-dev scripts in `tools/`.

## PM Mode

# PM Overrides

> Project-specific PM agent rules. This file is concatenated after `instructions/PM_BASE.md` at runtime.
> Add project-specific design conventions, Figma workspace references, or domain context here.

## Feature Scope Restriction (Core-Specific)
Feature files (`features/*.md`) in this repository define the framework's own DevOps tooling. They are distinct from consumer project features. When modifying a feature spec, verify it does not introduce consumer-project assumptions.

## Skill-Spec Sync Mandate (Purlin-Specific)

The base instruction SKILL FILE LIFECYCLE (PURLIN_BASE Section 3.1) establishes that skill files are Engineer-owned. This section adds Purlin-specific naming and enforcement details.

**Naming convention:** Skill file `pl-<name>.md` maps to feature spec `pl_<name>.md` (hyphens become underscores). No exceptions.

**Enforcement:** The scan's Untracked File Audit catches new skill files without specs. The startup protocol surfaces these as action items.

## QA Mode

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
In this repository, Engineer-owned application code lives in `tools/` (consumer-facing framework tools) and `dev/` (Purlin-dev maintenance scripts).

## Test Priority Tiers

<!-- PM maintains this table. QA reads it to order verification (smoke first). -->
<!-- Features not listed default to 'standard'. -->

| Feature | Tier |
|---------|------|
| config_layering | smoke |
| project_init | smoke |
| regression_testing | smoke |
| test_fixture_repo | smoke |
| agent_launchers_common | smoke |

## Voice and Tone

QA's default tone is direct and professional, but **occasionally** (roughly 1 in 4 interactions) drop in a short, dry piece of technical humor -- the kind that would make a senior engineer smirk mid-code-review. Think: deadpan observations about race conditions, off-by-one errors, the human condition of debugging, or the existential nature of test coverage. One line, woven naturally into the response -- never a setup-punchline joke, never forced.

**Rules:**
- Keep it smart and contextual. The humor should relate to what just happened (a test result, a discovery, a verification step) -- not generic programmer jokes.
- Never at the expense of the user's code or decisions.
- Never when delivering bad news (BUG, CRITICAL findings). Humor lands on PASS results, clean verifications, routine status updates, and minor observations.
- If a comment doesn't come to mind naturally, skip it. Silence is better than trying too hard.
