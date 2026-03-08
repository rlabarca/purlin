# Layered Instruction Architecture

> **Reference file.** Loaded on demand when editing overrides, running `/pl-override-edit`, or onboarding.
> Stub location: HOW_WE_WORK_BASE Section 6.

## Overview

The Purlin framework uses a two-layer instruction model to separate framework rules from project-specific context:

*   **Base Layer** (`instructions/` directory in the framework): Contains the framework's core rules, protocols, and philosophies. These are read-only from the consumer project's perspective and are updated by pulling new versions of the framework.
*   **Override Layer** (`.purlin/` directory in the consumer project): Contains project-specific customizations, domain context, and workflow additions. These are owned and maintained by the consumer project.

## How It Works

At agent launch time, the launcher scripts (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`) concatenate the base and override files into a single prompt:

1. Base HOW_WE_WORK is loaded first (framework philosophy).
2. Role-specific base instructions are appended (framework rules).
3. HOW_WE_WORK overrides are appended (project workflow additions).
4. Role-specific overrides are appended (project-specific rules).

This ordering ensures that project-specific rules can refine or extend (but not silently contradict) the framework's base rules.

## Submodule Consumption Pattern

When used as a git submodule (e.g., at `purlin/`):
1. The submodule provides the base layer (`purlin/instructions/`) and all tools (`purlin/tools/`).
2. The consumer project runs `purlin/tools/init.sh` to initialize `.purlin/` with override templates.
3. Tools resolve their paths via `tools_root` in `.purlin/config.json`.
4. Upstream updates use the `/pl-update-purlin` agent skill for intelligent synchronization.

## Override Management Protocol

### Override File Ownership (Role-Scoped Write Access)

Each override file has a designated set of agents permitted to modify it:

| Override File | Who May Edit |
|---|---|
| `.purlin/HOW_WE_WORK_OVERRIDES.md` | Architect only |
| `.purlin/ARCHITECT_OVERRIDES.md` | Architect only |
| `.purlin/BUILDER_OVERRIDES.md` | Builder (own) and Architect |
| `.purlin/QA_OVERRIDES.md` | QA (own) and Architect |

No agent may modify another agent's exclusive override file. The Architect has universal override access as the process owner.

### Base File Protection

Consumer project agents MUST NOT modify base instruction files under any circumstances -- governed by the Submodule Immutability Mandate (HOW_WE_WORK_BASE Section 6). If a consumer project needs to change framework behavior, changes go into the appropriate override file in `.purlin/`.

Agents in the Purlin framework's own repository (not a consumer project) may modify base files, but MUST use `/pl-edit-base` to do so. Direct editing without this command is prohibited.

### Override Editing Rules (apply in all contexts)

1. Read existing content first. Never overwrite without reading.
2. Additive only. Do not delete or contradict existing rules.
3. No contradictions with base. Surface conflicts with `/pl-override-edit --scan-only` before committing.
4. No code or script content. Override files are prose instruction documents only.
5. Commit after editing.

**Commands:** `/pl-override-edit` (role-scoped edit with built-in conflict scan; use `--scan-only` for read-only conflict scanning), `/pl-edit-base` (base file edit -- Purlin repo only, never distributed to consumers).

## Path Resolution Conventions

In a submodule setup, the project tree contains two `features/` directories and two `tools/` directories. The following conventions prevent ambiguity:

*   **`features/` directory:** Always refers to `<project_root>/features/` -- the **consumer project's** feature specs. In a submodule setup, this is NOT the framework submodule's own `features/` directory. The framework's features are internal to the submodule and are not scanned by consumer project tools.
*   **`tools/` references:** All `tools/` references in instruction files are shorthand that resolves against the `tools_root` value from `.purlin/config.json`. In standalone mode, `tools_root` is `"tools"`. In submodule mode, `tools_root` is `"<submodule>/tools"` (e.g., `"purlin/tools"`). Agents MUST read `tools_root` from config before constructing tool paths -- do NOT assume `tools/` is a direct child of the project root.
*   **`PURLIN_PROJECT_ROOT`:** All launcher scripts (both standalone and bootstrap-generated) export this environment variable as the authoritative project root. All Python and shell tools check this variable first, falling back to directory-climbing detection only when it is not set.
